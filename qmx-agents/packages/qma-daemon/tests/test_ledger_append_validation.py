"""Story 46.2 — validate every Task Ledger append without discarding evidence (FR-Q58)."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import cast

from qma.core.ontology import ActorId, DeskSlug
from qma.core.plugins.hooks import build_hook_result
from qma.core.vocabulary.enums import HookResultDecision
from qma.core.vocabulary.hooks import HOOK_TIMEOUT_REASON
from qma.daemon.hooks.ledger_gate import (
    LEDGER_QUARANTINE_STREAM,
    LedgerQuarantineStream,
    evaluate_before_ledger_append,
)
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.journal.stores import StoreRegistry
from qma.daemon.ledgers import TaskLedgerStore
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, "lead")
    assert is_ok(minted)
    return minted.value


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
    }


def _ct51_progress(*, agent: str = "agent-a") -> dict[str, object]:
    return {
        "id": "entry-1",
        "kind": "progress",
        "attempt_no": 0,
        "authored_by": {"agent": agent, "quant": _owner().value},
        "recorded_at": 1_700_000_000_000_000_000,
        "model_deployment_ref": "deploy:workhorse",
    }


def test_valid_schema_and_author_are_recorded() -> None:
    store = TaskLedgerStore()
    lease = _lease()
    store.grant(lease)
    recorded = store.append(_progress(), lease=lease)
    assert is_ok(recorded)
    assert recorded.value.entries[0]["kind"] == "progress"
    gate = evaluate_before_ledger_append(
        _ct51_progress(),
        dispatch_lease_holder="agent-a",
        ct51_schema=True,
    )
    assert gate.decision is HookResultDecision.ALLOW
    assert gate.disposition == "record"
    assert gate.quarantine is None


def test_schema_invalid_or_wrong_author_quarantines_never_discards() -> None:
    stores = StoreRegistry()
    stream = LedgerQuarantineStream()
    stream.bind_projection(stores)
    assert stream.projection_materialized is False
    invalid = evaluate_before_ledger_append(
        {"id": "bad", "kind": "progress", "attempt_no": 0},
        dispatch_lease_holder="agent-a",
        ct51_schema=True,
        quarantine=stream,
    )
    assert invalid.disposition == "quarantine"
    assert invalid.quarantine is not None
    assert invalid.quarantine.denial_source == "schema"
    assert invalid.to_payload()["discarded"] is False
    assert stream.projection_materialized is True
    declared = stores.declared()[LEDGER_QUARANTINE_STREAM]
    assert declared.materialized is True

    outsider = evaluate_before_ledger_append(
        _ct51_progress(agent="agent-b"),
        dispatch_lease_holder="agent-a",
        ct51_schema=True,
        quarantine=stream,
    )
    assert outsider.disposition == "quarantine"
    assert outsider.quarantine is not None
    assert outsider.quarantine.denial_source == "lease"
    assert stream.discarded_count == 0
    assert len(stream.records) == 2


def test_daemon_reassigned_and_unknown_tail_exempt_from_lease_still_schema_validated() -> None:
    store = TaskLedgerStore()
    first = _lease(holder="agent-a")
    store.grant(first)
    changed = store.record_reassignment(task_id="task-1", new_lease=_lease(holder="agent-b"))
    assert is_ok(changed)
    assert changed.value.entries[-1]["kind"] == "reassigned"
    assert changed.value.entries[-1]["authored_by"] == "daemon"
    tailed = store.record_unknown_tail(task_id="task-1", last_acked_id="ack-4")
    assert is_ok(tailed)
    assert tailed.value.entries[-1]["kind"] == "unknown_tail"
    assert tailed.value.entries[-1]["last_acked_id"] == "ack-4"
    assert "model_deployment_ref" not in tailed.value.entries[-1]

    schema_bad = evaluate_before_ledger_append(
        {
            "id": "re-bad",
            "kind": "reassigned",
            "attempt_no": 1,
            "authored_by": "daemon",
            "recorded_at": 2,
            "model_deployment_ref": "deploy:x",
        },
        dispatch_lease_holder=None,
        ct51_schema=True,
    )
    assert schema_bad.disposition == "quarantine"
    assert schema_bad.quarantine is not None
    assert schema_bad.quarantine.denial_source == "schema"

    lease_exempt = evaluate_before_ledger_append(
        {
            "id": "tail-ok",
            "kind": "unknown_tail",
            "attempt_no": 1,
            "authored_by": "daemon",
            "recorded_at": 3,
            "last_acked_id": "ack-4",
        },
        dispatch_lease_holder=None,
        ct51_schema=True,
    )
    assert lease_exempt.disposition == "record"
    assert lease_exempt.decision is HookResultDecision.ALLOW


def test_hook_returned_ledger_entry_stamps_daemon_and_registry_id() -> None:
    store = TaskLedgerStore()
    store.open_for_task("task-1", owner=_owner())
    recorded = store.record_hook_ledger_entry(
        {
            "kind": "progress",
            "authored_by": {"agent": "agent-a", "quant": _owner().value},
            "model_deployment_ref": "deploy:workhorse",
        },
        task_id="task-1",
        hook_registry_id="hook:before_task_complete:reg-9",
    )
    assert is_ok(recorded)
    entry = recorded.value.entries[-1]
    assert entry["kind"] == "ledger_entry"
    assert entry["authored_by"] == "daemon"
    assert entry["hook_registry_id"] == "hook:before_task_complete:reg-9"
    assert "model_deployment_ref" not in entry

    registry = HookRegistry()
    gated = registry.record_hook_ledger_entry(
        {
            "id": "hook-e",
            "attempt_no": 0,
            "recorded_at": 8,
        },
        hook_registry_id="hook:review_required:reg-2",
    )
    assert is_ok(gated)
    assert gated.value.disposition == "record"
    assert gated.value.entry["authored_by"] == "daemon"
    assert gated.value.entry["hook_registry_id"] == "hook:review_required:reg-2"

    missing = registry.record_hook_ledger_entry(
        {"id": "hook-bad", "attempt_no": 0, "recorded_at": 8},
        hook_registry_id="   ",
    )
    assert is_ok(missing)
    assert missing.value.disposition == "quarantine"


def test_incomplete_task_completed_writes_append_and_refuses_completion() -> None:
    store = TaskLedgerStore()
    lease = _lease()
    store.grant(lease)
    outcome = store.propose_completion(
        {
            "authored_by": {"agent": "agent-a", "quant": _owner().value},
            "model_deployment_ref": "deploy:workhorse",
            "task_completed": {"what_was_done": "partial notes"},
        },
        lease=lease,
    )
    assert is_ok(outcome)
    result = outcome.value
    assert result.completion_admitted is False
    assert result.refusal is not None
    assert result.refusal.context["field"] == "task_completed"
    assert result.entry["kind"] == "task_completed"
    assert result.ledger.entries[-1]["task_completed"] == {"what_was_done": "partial notes"}
    assert "what_changed" in result.missing_fields
    assert result.to_payload()["discarded"] is False
    surviving = store.get("task-1")
    assert surviving is not None
    assert len(surviving.entries) == 1


def test_complete_task_completed_admits_completion() -> None:
    store = TaskLedgerStore()
    lease = _lease()
    store.grant(lease)
    outcome = store.propose_completion(
        {
            "authored_by": {"agent": "agent-a", "quant": _owner().value},
            "model_deployment_ref": "deploy:workhorse",
            "task_completed": {
                "what_was_done": "finished the task",
                "what_changed": "ledger updated",
                "evidence_and_artifact_refs": ["artifact:a1"],
                "unresolved_issues": "none",
                "next_recommendation": "close the mission",
            },
        },
        lease=lease,
    )
    assert is_ok(outcome)
    assert outcome.value.completion_admitted is True
    assert outcome.value.refusal is None
    assert outcome.value.missing_fields == ()


def test_first_explicit_denial_materializes_quarantine_timeout_annotates() -> None:
    stores = StoreRegistry()
    stream = LedgerQuarantineStream()
    stream.bind_projection(stores)
    denied = evaluate_before_ledger_append(
        {"id": "x", "kind": "progress"},
        dispatch_lease_holder="agent-a",
        ct51_schema=True,
        attempted_result=build_hook_result(HookResultDecision.DENY, reason="schema_invalid"),
        quarantine=stream,
    )
    assert denied.disposition == "quarantine"
    assert denied.quarantine is not None
    assert denied.quarantine.reason == "schema_invalid"
    assert stream.projection_materialized is True
    second = evaluate_before_ledger_append(
        _ct51_progress(agent="other"),
        dispatch_lease_holder="agent-a",
        ct51_schema=True,
        quarantine=stream,
    )
    assert second.disposition == "quarantine"
    assert stream.projection_materialized is True
    assert stream.discarded_count == 0

    timed = evaluate_before_ledger_append(
        _ct51_progress(),
        dispatch_lease_holder="agent-a",
        timed_out=True,
        ct51_schema=True,
    )
    assert timed.disposition == "record"
    assert timed.decision is HookResultDecision.ALLOW
    assert timed.result.reason == HOOK_TIMEOUT_REASON
    assert timed.entry["hook_timeout"] is True
    notes = cast("list[object]", timed.entry["annotations"])
    assert HOOK_TIMEOUT_REASON in notes

    store = TaskLedgerStore()
    lease = _lease()
    store.grant(lease)
    incomplete_timeout = store.propose_completion(
        {
            "authored_by": {"agent": "agent-a", "quant": _owner().value},
            "model_deployment_ref": "deploy:workhorse",
            "task_completed": {"what_was_done": "timed out mid-write"},
        },
        lease=lease,
        timed_out=True,
    )
    assert is_ok(incomplete_timeout)
    assert incomplete_timeout.value.completion_admitted is False
    assert incomplete_timeout.value.entry.get("hook_timeout") is True
    assert incomplete_timeout.value.to_payload()["discarded"] is False


def test_store_schema_invalid_append_lands_in_quarantine() -> None:
    store = TaskLedgerStore()
    lease = _lease()
    store.grant(lease)
    refused = store.append(
        {
            "kind": "progress",
            "authored_by": {"agent": "agent-a", "quant": _owner().value},
        },
        lease=lease,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "entry"
    assert refused.context["discarded"] is False
    held = store.get("task-1")
    assert held is not None
    assert held.entries == ()
    assert len(store.quarantine.records) == 1


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "ledger_append_validation_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
