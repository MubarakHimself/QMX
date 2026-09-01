"""Story 45.2 — environment-slot governance (FR-Q49)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.execution import (
    ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT,
    ENVIRONMENT_MAX_IN_FLIGHT_KEY,
    ExecutionEnvironmentDeclaration,
)
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    JobHandleState,
    TaskMissionState,
    VariableEditability,
)
from qma.daemon import CompileRequest, MissionCompiler, TaskGraphDispatcher
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qma.daemon.journal.variables import GovernedVariableRegistry
from qma.daemon.taskgraph import JobHandleEvidence
from qmf.core import is_ok, is_refusal


def _quant(*, slug: str = "alpha") -> Quant:
    minted = ActorId.mint(DeskSlug.RESEARCH, slug)
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
    )


def _docker(
    *,
    max_in_flight: int = ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT,
) -> ExecutionEnvironmentDeclaration:
    return ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        max_in_flight=max_in_flight,
    )


def _remote_host() -> ExecutionEnvironmentDeclaration:
    return ExecutionEnvironmentDeclaration.try_parse(
        kind="remote_host",
        network="none",
        reachable_hosts=(),
        provider_ref="research-box",
        host="research-box",
        lifecycle="persistent",
    )


def _bound_router(
    declaration: ExecutionEnvironmentDeclaration | None = None,
) -> ComputeRouter:
    registry = ExecutionEnvironmentRegistry()
    parsed = declaration if declaration is not None else _docker()
    assert is_ok(registry.register_declaration(parsed))
    return ComputeRouter(environments=registry)


def test_place_grants_one_slot_from_declared_capacity() -> None:
    router = _bound_router(_docker(max_in_flight=2))
    first = router.place_job(task_id="task:a", kind="docker")
    assert is_ok(first)
    assert first.value.granted is True
    assert first.value.lease is not None
    assert first.value.lease.slot_id == "slot:docker:0"
    assert first.value.lease.task_id == "task:a"
    assert first.value.max_in_flight == 2
    assert first.value.occupied == 1
    assert first.value.to_payload()["capacity_key"] == ENVIRONMENT_MAX_IN_FLIGHT_KEY
    stored = router.environments.declaration("docker")
    assert stored is not None
    assert stored.max_in_flight == 2
    cited = router.capacity_for("docker")
    assert is_ok(cited)
    assert cited.value == 2


def test_full_occupancy_queues_and_never_over_allocates() -> None:
    router = _bound_router(_docker(max_in_flight=1))
    granted = router.place_job(task_id="task:hold", kind="docker")
    assert is_ok(granted)
    assert granted.value.granted is True
    queued = router.place_job(task_id="task:wait", kind="docker")
    assert is_ok(queued)
    assert queued.value.is_queued is True
    assert queued.value.lease is None
    assert queued.value.queued is not None
    assert queued.value.queued.queue_position == 1
    assert queued.value.occupied == 1
    assert queued.value.max_in_flight == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT
    assert router.occupied_count("docker") == 1
    assert router.lease_for("task:wait") is None
    assert router.queued_task_ids("docker") == ("task:wait",)
    third = router.place_job(task_id="task:also-wait", kind="docker")
    assert is_ok(third)
    assert third.value.queued is not None
    assert third.value.queued.queue_position == 2
    assert router.occupied_count("docker") == 1


def test_agent_machine_or_vendor_is_ignored() -> None:
    router = _bound_router()
    placed = router.place_job(
        task_id="task:choice",
        kind="docker",
        agent_machine="agent-chosen-box",
        agent_vendor="modal",
        machine="other-box",
        vendor="e2b",
    )
    assert is_ok(placed)
    assert placed.value.agent_choice_ignored is True
    assert placed.value.lease is not None
    assert placed.value.lease.provider_id == "local-docker"
    payload = placed.value.lease.to_payload()
    assert "agent-chosen-box" not in str(dict(payload))
    assert "modal" not in str(dict(payload))


def test_remote_host_and_desktop_capacity_pinned_uneditable() -> None:
    router = _bound_router(_remote_host())
    capacity = router.capacity_for(ExecutionEnvironmentKind.REMOTE_HOST)
    assert is_ok(capacity)
    assert capacity.value == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT
    occupancy = router.occupancy("remote_host")
    assert occupancy["pinned_single_slot"] is True
    assert occupancy["editability"] == VariableEditability.UNEDITABLE.value
    assert occupancy["capacity_key"] == ENVIRONMENT_MAX_IN_FLIGHT_KEY

    refused_write = router.write_max_in_flight("remote_host", 2)
    assert is_refusal(refused_write)
    assert str(refused_write.context.get("reason", "")).startswith(
        "registry:environment.max_in_flight"
    )
    assert refused_write.context["editability"] == "uneditable"
    assert refused_write.context["pinned"] == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT

    granted = router.place_job(task_id="task:remote-1", kind="remote_host")
    assert is_ok(granted)
    assert granted.value.granted is True
    queued = router.place_job(task_id="task:remote-2", kind="remote_host")
    assert is_ok(queued)
    assert queued.value.is_queued is True
    assert router.occupied_count("remote_host") == 1

    desktop = ExecutionEnvironmentDeclaration.try_parse(
        kind="desktop",
        network="none",
        reachable_hosts=(),
        provider_ref="research-box",
        host="research-box",
        lifecycle="persistent",
        max_in_flight=2,
    )
    other = ExecutionEnvironmentRegistry()
    refused_desktop = other.register_declaration(desktop)
    assert is_refusal(refused_desktop)
    assert refused_desktop.context["reason"] == "max_in_flight_pinned"


def test_editable_kind_capacity_write_and_shrink_guard() -> None:
    router = _bound_router(_docker(max_in_flight=2))
    assert is_ok(router.place_job(task_id="t1", kind="docker"))
    assert is_ok(router.place_job(task_id="t2", kind="docker"))
    assert router.occupied_count("docker") == 2
    shrink = router.write_max_in_flight("docker", 1)
    assert is_refusal(shrink)
    assert "occupied" in str(shrink.context.get("reason", ""))
    raised = router.write_max_in_flight("docker", 4)
    assert is_ok(raised)
    assert raised.value.max_in_flight == 4


def test_unknown_holds_slot_until_recorded_resolution() -> None:
    router = _bound_router(_docker(max_in_flight=1))
    granted = router.place_job(task_id="task:unk", kind="docker")
    assert is_ok(granted)
    held = router.hold_unknown("task:unk")
    assert is_ok(held)
    assert router.is_unknown("task:unk")
    assert router.occupied_count("docker") == 1

    queued = router.place_job(task_id="task:queued-behind-unknown", kind="docker")
    assert is_ok(queued)
    assert queued.value.is_queued is True

    retry = router.retry_unknown("task:unk")
    assert is_refusal(retry)
    assume = router.assume_outcome("task:unk", "failed")
    assert is_refusal(assume)
    invent = router.invent_terminal("task:unk", "done")
    assert is_refusal(invent)
    unrecorded = router.resolve_unknown("task:unk", recorded=False)
    assert is_refusal(unrecorded)
    silent_release = router.release("task:unk")
    assert is_refusal(silent_release)
    assert router.occupied_count("docker") == 1
    assert router.lease_for("task:unk") is not None

    resolved = router.resolve_unknown("task:unk", recorded=True)
    assert is_ok(resolved)
    assert resolved.value is not None
    assert resolved.value.granted is True
    assert resolved.value.lease is not None
    assert resolved.value.lease.task_id == "task:queued-behind-unknown"
    assert router.lease_for("task:unk") is None
    assert router.occupied_count("docker") == 1
    assert router.is_unknown("task:unk") is False


def test_dispatcher_queues_at_capacity_and_unknown_keeps_lease() -> None:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(envs.register_declaration(_docker(max_in_flight=1)))
    router = ComputeRouter(environments=envs)

    first = compiler.compile(CompileRequest(goal=Goal(text="first slot"), owner=owner))
    assert is_ok(first)
    dispatcher = TaskGraphDispatcher(environments=envs, router=router)
    dispatcher.materialize(first.value.task_graph, mission=first.value.mission)
    decision = dispatcher.dispatch_task(
        task_id=first.value.task_graph.tasks[0].id,
        holder_agent_id="agent:w1",
    )
    assert is_ok(decision)
    assert decision.value.environment_lease is not None
    assert decision.value.queued_placement is None

    second = compiler.compile(CompileRequest(goal=Goal(text="queued slot"), owner=owner))
    assert is_ok(second)
    dispatcher.materialize(second.value.task_graph, mission=second.value.mission)
    queued = dispatcher.dispatch_task(
        task_id=second.value.task_graph.tasks[0].id,
        holder_agent_id="agent:w2",
    )
    assert is_ok(queued)
    assert queued.value.environment_lease is None
    assert queued.value.queued_placement is not None
    assert queued.value.environment_available is False
    assert queued.value.environment_refusal is None

    task = first.value.task_graph.tasks[0]
    unknown = dispatcher.apply_job_handle_evidence(
        JobHandleEvidence(
            job_id="job-unk",
            task_id=task.id,
            state=JobHandleState.UNKNOWN,
        )
    )
    assert is_ok(unknown)
    assert unknown.value.environment_lease_retained is True
    assert router.is_unknown(task.id)
    assert router.occupied_count("docker") == 1
    assert dispatcher.store.environment_lease_for(task.id) is not None

    resolved = dispatcher.resolve_unknown_job_handle(
        JobHandleEvidence(
            job_id="job-unk",
            task_id=task.id,
            state=JobHandleState.FAILED,
        )
    )
    assert is_ok(resolved)
    assert resolved.value.task.state is TaskMissionState.FAILED
    assert resolved.value.environment_lease_retained is False
    assert router.lease_for(task.id) is None
    promoted = second.value.task_graph.tasks[0].id
    assert router.lease_for(promoted) is not None
    assert dispatcher.store.environment_lease_for(promoted) is not None


def test_record_homed_capacity_is_not_a_variable_set() -> None:
    registry = GovernedVariableRegistry.with_builtins()
    row = registry.get("environment.max_in_flight")
    assert is_ok(row)
    assert row.value.registry_key == ENVIRONMENT_MAX_IN_FLIGHT_KEY
    assert row.value.home == "execution_environment_declaration"
    assert row.value.is_record_homed is True
    assert row.value.default == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT


def test_unbound_kind_is_no_environment_not_a_queue() -> None:
    router = ComputeRouter()
    missing = router.place_job(task_id="task:none", kind="docker")
    assert is_refusal(missing)
    assert missing.context.get("variant") == "NoEnvironment"


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "environment_slot_governance_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
