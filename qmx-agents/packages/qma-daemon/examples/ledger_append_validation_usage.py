"""L27 reference usage: before_ledger_append validates without discarding evidence."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.plugins.hooks import build_hook_result
from qma.core.vocabulary.enums import HookResultDecision
from qma.daemon.hooks.ledger_gate import LedgerQuarantineStream, evaluate_before_ledger_append
from qma.daemon.journal.stores import StoreRegistry
from qma.daemon.ledgers import TaskLedgerStore
from qma.daemon.taskgraph.records import DispatchLease
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

    recorded = store.append(
        {
            "kind": "progress",
            "authored_by": {"agent": "agent-a", "quant": owner.value},
            "model_deployment_ref": "deploy:workhorse",
        },
        lease=lease,
    )
    assert is_ok(recorded)

    stores = StoreRegistry()
    stream = LedgerQuarantineStream()
    stream.bind_projection(stores)
    denied = evaluate_before_ledger_append(
        {"id": "bad", "kind": "progress"},
        dispatch_lease_holder="agent-a",
        ct51_schema=True,
        attempted_result=build_hook_result(HookResultDecision.DENY, reason="schema_invalid"),
        quarantine=stream,
    )
    assert denied.disposition == "quarantine"
    assert stream.projection_materialized is True
    assert stream.discarded_count == 0

    reassigned = store.record_reassignment(
        task_id="task-1",
        new_lease=DispatchLease(
            task_id="task-1",
            holder_agent_id="agent-b",
            mission_id="mission-1",
            owner=owner,
        ),
    )
    assert is_ok(reassigned)
    tailed = store.record_unknown_tail(task_id="task-1", last_acked_id="ack-1")
    assert is_ok(tailed)
    hooked = store.record_hook_ledger_entry(
        {"kind": "progress"},
        task_id="task-1",
        hook_registry_id="hook:before_task_complete:reg-1",
    )
    assert is_ok(hooked)
    assert hooked.value.entries[-1]["authored_by"] == "daemon"

    holder = DispatchLease(
        task_id="task-1",
        holder_agent_id="agent-b",
        mission_id="mission-1",
        owner=owner,
    )
    incomplete = store.propose_completion(
        {
            "authored_by": {"agent": "agent-b", "quant": owner.value},
            "model_deployment_ref": "deploy:workhorse",
            "task_completed": {"what_was_done": "partial"},
        },
        lease=holder,
        timed_out=True,
    )
    assert is_ok(incomplete)
    assert incomplete.value.completion_admitted is False
    assert incomplete.value.entry.get("hook_timeout") is True
    assert incomplete.value.refusal is not None
    assert is_refusal(incomplete.value.refusal)


if __name__ == "__main__":
    main()
