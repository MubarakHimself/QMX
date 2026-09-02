"""Story 46.1 — persist the Task Ledger under dispatch_lease (FR-Q57; CT-51)."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import cast

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.ledgers import QuantLedgerLease
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.envs.registry import EnvironmentLease
from qma.daemon.hooks.controls import ControlOutcomeController
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.ledgers import TASK_LEDGER_STORE_NAME, TaskLedgerStore
from qma.daemon.taskgraph import CompileRequest, MissionCompiler, TaskGraphDispatcher
from qma.daemon.taskgraph.records import DispatchLease
from qma.wire.envelope import WireEnvelope
from qma.wire.host_request import emit_host_request
from qma.wire.vocabulary import WireEvent, WireQuery
from qmf.core import is_ok, is_refusal

_SCOPE = [
    {"kind": "desk", "id": "research"},
    {"kind": "quant", "id": "lead"},
    {"kind": "mission", "id": "mission-1"},
    {"kind": "task", "id": "task-1"},
]


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, "lead")
    assert is_ok(minted)
    return minted.value


def _quant() -> Quant:
    owner = _owner()
    return Quant(
        actor_id=owner,
        desk=DeskSlug.RESEARCH,
        quant_slug="lead",
        role=RoleName.RESEARCHER,
        name="Quant lead",
    )


def _lease(*, task_id: str = "task-1", holder: str = "agent-a") -> DispatchLease:
    return DispatchLease(
        task_id=task_id,
        holder_agent_id=holder,
        mission_id="mission-1",
        owner=_owner(),
    )


def _progress(*, agent: str = "agent-a", attempt_no: int = 0) -> dict[str, object]:
    return {
        "kind": "progress",
        "attempt_no": attempt_no,
        "authored_by": {"agent": agent, "quant": _owner().value},
        "model_deployment_ref": "deploy:workhorse",
        "trace_ref": "trace:run-1",
    }


def test_one_task_owned_ledger_for_life_does_not_span_tasks_or_workers() -> None:
    store = TaskLedgerStore()
    owner = _owner()
    first = store.open_for_task("task-1", owner=owner)
    again = store.open_for_task("task-1", owner=owner)
    other = store.open_for_task("task-2", owner=owner)
    assert first is again
    assert other is not first
    assert first.task_id == "task-1"
    assert other.task_id == "task-2"
    lease = _lease()
    granted = store.grant(lease)
    assert is_ok(granted)
    appended = store.append(_progress(), lease=lease)
    assert is_ok(appended)
    # Worker handle is never stored; dropping the caller still leaves the ledger.
    del lease
    surviving = store.get("task-1")
    assert surviving is not None
    assert len(surviving.entries) == 1
    assert store.get("task-2") is not None
    assert store.get("task-2") is not surviving
    crossed = store.append(_progress(), lease=_lease(task_id="task-2"), task_id="task-1")
    assert is_refusal(crossed)
    assert crossed.context["field"] == "dispatch_lease"


def test_append_requires_dispatch_lease_not_env_or_quant_ledger_lease() -> None:
    store = TaskLedgerStore()
    lease = _lease()
    store.grant(lease)
    ok = store.append(_progress(), lease=lease)
    assert is_ok(ok)
    authored = ok.value.entries[0]["authored_by"]
    assert isinstance(authored, dict)
    assert authored["agent"] == "agent-a"
    assert authored["quant"] == _owner().value
    assert ok.value.entries[0]["model_deployment_ref"] == "deploy:workhorse"
    assert ok.value.entries[0]["attempt_no"] == 0
    outsider = store.append(_progress(agent="agent-b"), lease=_lease(holder="agent-b"))
    assert is_refusal(outsider)
    env = store.append(
        _progress(),
        lease=EnvironmentLease(task_id="task-1", kind="docker", slot_id="slot-1"),
    )
    assert is_refusal(env)
    assert env.context["field"] == "lease"
    quant = store.append(
        _progress(),
        lease=QuantLedgerLease(owner=_owner(), holder_agent_id="agent-a"),
    )
    assert is_refusal(quant)
    assert quant.context["field"] == "lease"


def test_reassignment_writes_daemon_entry_and_increments_attempt_no() -> None:
    store = TaskLedgerStore()
    first = _lease(holder="agent-a")
    store.grant(first)
    store.append(_progress(), lease=first)
    before = store.get("task-1")
    assert before is not None
    assert before.attempt_no == 0
    changed = store.record_reassignment(
        task_id="task-1",
        new_lease=_lease(holder="agent-b"),
    )
    assert is_ok(changed)
    assert changed.value.attempt_no == 1
    kinds = [entry["kind"] for entry in changed.value.entries]
    assert kinds[-1] == "reassigned"
    assert changed.value.entries[-1]["authored_by"] == "daemon"
    assert "model_deployment_ref" not in changed.value.entries[-1]
    same = store.record_reassignment(
        task_id="task-1",
        new_lease=_lease(holder="agent-b"),
    )
    assert is_ok(same)
    assert same.value.attempt_no == 1
    assert sum(1 for entry in same.value.entries if entry["kind"] == "reassigned") == 1


def test_resume_from_defer_retains_lease_without_reassigned_or_attempt_bump() -> None:
    store = TaskLedgerStore()
    lease = _lease()
    store.grant(lease)
    store.append(_progress(), lease=lease)
    resumed = store.resume_from_defer(task_id="task-1", dispatch_lease=lease)
    assert is_ok(resumed)
    assert resumed.value.attempt_no == 0
    assert all(entry["kind"] != "reassigned" for entry in resumed.value.entries)
    assert store.lease_for("task-1") is not None
    assert store.lease_for("task-1") == lease


def test_persist_and_inspect_through_the_wire_survive_the_worker() -> None:
    store = TaskLedgerStore()
    lease = _lease()
    store.grant(lease)
    emission = emit_host_request(
        verb="ledger_append",
        scope_path=_SCOPE,
        correlation_id="corr-task-1",
        producer_id="analysis-worker",
        id="hr-ledger-1",
        v="1.0.0",
        args={"entry": _progress()},
    )
    assert is_ok(emission)
    persisted = store.persist_via_wire(emission.value.envelope, dispatch_lease=lease)
    assert is_ok(persisted)
    assert persisted.value.event.type == WireEvent.LEDGER_UPDATED.value
    assert persisted.value.event.payload["survives_worker"] is True
    assert persisted.value.event.payload["store"] == TASK_LEDGER_STORE_NAME
    worker_stamp = emit_host_request(
        verb="ledger_append",
        scope_path=_SCOPE,
        correlation_id="corr-task-1",
        producer_id="analysis-worker",
        id="hr-ledger-2",
        v="1.0.0",
        args={"entry": {**_progress(), "recorded_at": 99}},
    )
    assert is_ok(worker_stamp)
    refused = store.persist_via_wire(worker_stamp.value.envelope, dispatch_lease=lease)
    assert is_refusal(refused)
    inspect = WireEnvelope.try_create(
        v="1.0.0",
        type=WireQuery.INSPECT_LEDGER.value,
        id="q-inspect-1",
        producer_id="desktop-ui",
        scope_path=_SCOPE,
        payload={"task_id": "task-1"},
        correlation_id="corr-task-1",
    )
    assert is_ok(inspect)
    snapshot = store.inspect_via_wire(inspect.value)
    assert is_ok(snapshot)
    assert snapshot.value.payload["survives_worker"] is True
    entries = cast("list[object]", snapshot.value.payload["entries"])
    assert len(entries) == 1


def test_dispatcher_reassign_and_defer_resume_use_the_task_ledger() -> None:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    compiled = compiler.compile(CompileRequest(goal=Goal(text="cover a desk"), owner=owner))
    assert is_ok(compiled)
    ledgers = TaskLedgerStore()
    dispatcher = TaskGraphDispatcher(ledgers=ledgers)
    graph = compiled.value.task_graph
    dispatcher.materialize(graph, mission=compiled.value.mission)
    task = graph.tasks[0]
    decision = dispatcher.dispatch_task(task_id=task.id, holder_agent_id="agent-a")
    assert is_ok(decision)
    assert decision.value.dispatch_lease.to_payload()["lease"] == "dispatch_lease"
    first = ledgers.append(
        {
            "kind": "progress",
            "authored_by": {"agent": "agent-a", "quant": owner.actor_id.value},
            "model_deployment_ref": "deploy:workhorse",
        },
        lease=decision.value.dispatch_lease,
        task_id=task.id,
    )
    assert is_ok(first)
    reassigned = dispatcher.reassign(task_id=task.id, new_holder_agent_id="agent-b")
    assert is_ok(reassigned)
    held = ledgers.get(task.id)
    assert held is not None
    assert held.attempt_no == 1
    assert held.entries[-1]["kind"] == "reassigned"
    stored = dispatcher.store.for_mission(compiled.value.mission.id)
    assert stored is not None
    live = stored.task_by_id(task.id)
    assert live is not None
    assert live.ledger is not None
    assert live.ledger.attempt_no == 1

    dispatcher.store.record_environment_lease(
        EnvironmentLease(
            task_id=task.id,
            kind=ExecutionEnvironmentKind.DOCKER.value,
            slot_id="slot-1",
        )
    )
    controller = ControlOutcomeController(task_store=dispatcher.store, ledgers=ledgers)
    parked = controller.persist_defer(
        event="before_tool",
        mission_id=compiled.value.mission.id,
        task_id=task.id,
    )
    assert is_ok(parked)
    assert parked.value.parking.reassignment_recorded is False
    assert parked.value.parking.attempt_no_unchanged is True
    resumed = controller.resume_defer(parked.value.parking.parking_id, HookRegistry())
    assert is_ok(resumed)
    after = ledgers.get(task.id)
    assert after is not None
    assert after.attempt_no == 1
    assert sum(1 for entry in after.entries if entry["kind"] == "reassigned") == 1


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "task_ledger_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
