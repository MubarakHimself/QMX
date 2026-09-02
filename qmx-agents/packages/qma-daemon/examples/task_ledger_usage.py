"""L27 reference usage: Task Ledger under dispatch_lease, persisted on the wire."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.ledgers import QuantLedgerLease
from qma.daemon.envs.registry import EnvironmentLease
from qma.daemon.ledgers import TaskLedgerStore
from qma.daemon.taskgraph.records import DispatchLease
from qma.wire.envelope import WireEnvelope
from qma.wire.host_request import emit_host_request
from qmf.core import is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.RESEARCH, "lead")
    assert is_ok(minted)
    owner = minted.value
    lease = DispatchLease(
        task_id="task-1",
        holder_agent_id="agent-a",
        mission_id="mission-1",
        owner=owner,
    )
    store = TaskLedgerStore()
    store.open_for_task("task-1", owner=owner)
    assert is_ok(store.grant(lease))
    emission = emit_host_request(
        verb="ledger_append",
        scope_path=[
            {"kind": "desk", "id": "research"},
            {"kind": "quant", "id": "lead"},
            {"kind": "mission", "id": "mission-1"},
            {"kind": "task", "id": "task-1"},
        ],
        correlation_id="corr-1",
        producer_id="analysis-worker",
        id="hr-1",
        v="1.0.0",
        args={
            "entry": {
                "kind": "progress",
                "authored_by": {"agent": "agent-a", "quant": owner.value},
                "model_deployment_ref": "deploy:workhorse",
                "artifact_ref": "artifact:note-1",
            }
        },
    )
    assert is_ok(emission)
    persisted = store.persist_via_wire(emission.value.envelope, dispatch_lease=lease)
    assert is_ok(persisted)
    assert is_refusal(
        store.append(
            {
                "kind": "progress",
                "authored_by": {"agent": "agent-a", "quant": owner.value},
                "model_deployment_ref": "deploy:workhorse",
            },
            lease=EnvironmentLease(task_id="task-1", kind="docker", slot_id="s1"),
        )
    )
    assert is_refusal(
        store.append(
            {
                "kind": "progress",
                "authored_by": {"agent": "agent-a", "quant": owner.value},
                "model_deployment_ref": "deploy:workhorse",
            },
            lease=QuantLedgerLease(owner=owner, holder_agent_id="agent-a"),
        )
    )
    changed = store.record_reassignment(
        task_id="task-1",
        new_lease=DispatchLease(
            task_id="task-1",
            holder_agent_id="agent-b",
            mission_id="mission-1",
            owner=owner,
        ),
    )
    assert is_ok(changed)
    assert changed.value.attempt_no == 1
    resumed = store.resume_from_defer(
        task_id="task-1",
        dispatch_lease=DispatchLease(
            task_id="task-1",
            holder_agent_id="agent-b",
            mission_id="mission-1",
            owner=owner,
        ),
    )
    assert is_ok(resumed)
    assert resumed.value.attempt_no == 1
    inspect = WireEnvelope.try_create(
        v="1.0.0",
        type="inspect_ledger",
        id="q-1",
        producer_id="qma-daemon",
        scope_path=[
            {"kind": "desk", "id": "research"},
            {"kind": "quant", "id": "lead"},
            {"kind": "mission", "id": "mission-1"},
            {"kind": "task", "id": "task-1"},
        ],
        payload={"task_id": "task-1"},
        correlation_id="corr-1",
    )
    assert is_ok(inspect)
    snapshot = store.inspect_via_wire(inspect.value)
    assert is_ok(snapshot)
    assert snapshot.value.payload["survives_worker"] is True


if __name__ == "__main__":
    main()
