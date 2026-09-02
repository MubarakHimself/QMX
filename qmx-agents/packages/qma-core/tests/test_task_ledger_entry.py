"""Story 46.1 / 46.2 — Task Ledger entry schema, leases, and evidence validation."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.ledgers import (
    DAEMON_AUTHORED_ENTRY_KINDS,
    HOOK_RETURNED_LEDGER_KIND,
    LEDGER_ENTRY_OPTIONAL_REFS,
    LEDGER_ENTRY_REQUIRED_FIELDS,
    TASK_COMPLETED_FIELDS,
    QuantLedgerLease,
    missing_task_completed_fields,
    named_lease_kind,
    parse_task_ledger_entry,
    stamp_hook_returned_ledger_entry,
)
from qma.core.vocabulary import CLOSED_VOCABULARIES, LeaseKind, TaskLedgerEntryKind, parse_closed
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, "lead")
    assert is_ok(minted)
    return minted.value


def test_closed_vocabs_cover_leases_and_entry_kinds() -> None:
    names = {entry.name for entry in CLOSED_VOCABULARIES}
    assert "lease_kind" in names
    assert "task_ledger_entry_kind" in names
    assert parse_closed(LeaseKind, "dispatch_lease") is LeaseKind.DISPATCH_LEASE
    assert parse_closed(TaskLedgerEntryKind, "reassigned") is TaskLedgerEntryKind.REASSIGNED
    assert TaskLedgerEntryKind.REASSIGNED in DAEMON_AUTHORED_ENTRY_KINDS
    assert TaskLedgerEntryKind.UNKNOWN_TAIL in DAEMON_AUTHORED_ENTRY_KINDS
    assert TaskLedgerEntryKind.PROGRESS not in DAEMON_AUTHORED_ENTRY_KINDS


def test_non_daemon_entry_requires_attempt_author_and_model() -> None:
    owner = _owner()
    parsed = parse_task_ledger_entry(
        {
            "id": "entry-1",
            "kind": "progress",
            "attempt_no": 0,
            "authored_by": {"agent": "agent-a", "quant": owner.value},
            "recorded_at": 1_700_000_000_000_000_000,
            "model_deployment_ref": "deploy:workhorse",
            "trace_ref": "trace:run-1",
        }
    )
    assert is_ok(parsed)
    payload = parsed.value.to_payload()
    assert payload["attempt_no"] == 0
    authored = payload["authored_by"]
    assert isinstance(authored, dict)
    assert authored["agent"] == "agent-a"
    assert authored["quant"] == owner.value
    assert payload["model_deployment_ref"] == "deploy:workhorse"
    assert payload["trace_ref"] == "trace:run-1"
    assert "artifact" not in payload


def test_optional_refs_are_references_never_shared_semantics() -> None:
    owner = _owner()
    refused = parse_task_ledger_entry(
        {
            "id": "entry-2",
            "kind": "progress",
            "attempt_no": 0,
            "authored_by": {"agent": "agent-a", "quant": owner.value},
            "recorded_at": 1,
            "model_deployment_ref": "deploy:workhorse",
            "trace": {"shared": "object"},
        }
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "entry"
    for field in LEDGER_ENTRY_OPTIONAL_REFS:
        assert field.endswith("_ref")
    assert {
        "id",
        "kind",
        "attempt_no",
        "authored_by",
        "recorded_at",
    } == LEDGER_ENTRY_REQUIRED_FIELDS


def test_daemon_reassigned_names_no_model_deployment() -> None:
    parsed = parse_task_ledger_entry(
        {
            "id": "entry-r",
            "kind": "reassigned",
            "attempt_no": 1,
            "authored_by": "daemon",
            "recorded_at": 2,
            "holder_agent_id": "agent-b",
        }
    )
    assert is_ok(parsed)
    assert parsed.value.authored_by.daemon is True
    assert "model_deployment_ref" not in parsed.value.to_payload()
    with_model = parse_task_ledger_entry(
        {
            "id": "entry-bad",
            "kind": "reassigned",
            "attempt_no": 1,
            "authored_by": "daemon",
            "recorded_at": 2,
            "model_deployment_ref": "deploy:x",
        }
    )
    assert is_refusal(with_model)


def test_quant_ledger_lease_is_distinct_named_lease() -> None:
    owner = _owner()
    lease = QuantLedgerLease(owner=owner, holder_agent_id="agent-lead")
    parsed = named_lease_kind(lease)
    assert is_ok(parsed)
    assert parsed.value is LeaseKind.QUANT_LEDGER_LEASE
    assert lease.to_payload()["lease"] == "quant_ledger_lease"
    dispatch = named_lease_kind({"lease": "dispatch_lease"})
    env = named_lease_kind({"lease": "environment_lease"})
    assert is_ok(dispatch) and dispatch.value is LeaseKind.DISPATCH_LEASE
    assert is_ok(env) and env.value is LeaseKind.ENVIRONMENT_LEASE
    bare = named_lease_kind("lease")
    assert is_refusal(bare)


def test_incomplete_task_completed_parses_for_persistence() -> None:
    owner = _owner()
    parsed = parse_task_ledger_entry(
        {
            "id": "entry-c",
            "kind": "task_completed",
            "attempt_no": 0,
            "authored_by": {"agent": "agent-a", "quant": owner.value},
            "recorded_at": 3,
            "model_deployment_ref": "deploy:workhorse",
            "task_completed": {"what_was_done": "wrote notes"},
        }
    )
    assert is_ok(parsed)
    payload = parsed.value.to_payload()
    assert payload["kind"] == "task_completed"
    assert payload["task_completed"] == {"what_was_done": "wrote notes"}
    assert parsed.value.task_completed is None
    assert parsed.value.task_completed_complete is False
    missing = missing_task_completed_fields(payload["task_completed"])
    assert "what_changed" in missing
    assert "evidence_and_artifact_refs" in missing
    assert "unresolved_issues" in missing
    assert "next_recommendation" in missing
    assert len(TASK_COMPLETED_FIELDS) == 5


def test_complete_task_completed_parses_five_fields() -> None:
    owner = _owner()
    parsed = parse_task_ledger_entry(
        {
            "id": "entry-done",
            "kind": "task_completed",
            "attempt_no": 0,
            "authored_by": {"agent": "agent-a", "quant": owner.value},
            "recorded_at": 4,
            "model_deployment_ref": "deploy:workhorse",
            "task_completed": {
                "what_was_done": "ran the sweep",
                "what_changed": "new artifact",
                "evidence_and_artifact_refs": ["artifact:a1"],
                "unresolved_issues": "none",
                "next_recommendation": "promote candidate",
            },
        }
    )
    assert is_ok(parsed)
    assert parsed.value.task_completed_complete is True
    assert missing_task_completed_fields(parsed.value.to_payload()["task_completed"]) == ()


def test_hook_returned_ledger_entry_requires_daemon_and_registry_id() -> None:
    stamped = stamp_hook_returned_ledger_entry(
        {
            "id": "hook-1",
            "attempt_no": 0,
            "recorded_at": 5,
            "kind": "progress",
            "authored_by": {"agent": "agent-a", "quant": "quant:x"},
            "model_deployment_ref": "deploy:x",
        },
        hook_registry_id="hook:before_task_complete:reg-1",
    )
    assert stamped["kind"] == HOOK_RETURNED_LEDGER_KIND.value
    assert stamped["authored_by"] == "daemon"
    assert stamped["hook_registry_id"] == "hook:before_task_complete:reg-1"
    assert "model_deployment_ref" not in stamped
    parsed = parse_task_ledger_entry(stamped)
    assert is_ok(parsed)
    assert parsed.value.authored_by.daemon is True
    assert parsed.value.hook_registry_id == "hook:before_task_complete:reg-1"
    missing_id = parse_task_ledger_entry(
        {
            "id": "hook-2",
            "kind": "ledger_entry",
            "attempt_no": 0,
            "authored_by": "daemon",
            "recorded_at": 6,
        }
    )
    assert is_refusal(missing_id)
    assert missing_id.context["field"] == "hook_registry_id"


def test_unknown_tail_is_daemon_authored_without_model() -> None:
    parsed = parse_task_ledger_entry(
        {
            "id": "entry-u",
            "kind": "unknown_tail",
            "attempt_no": 0,
            "authored_by": "daemon",
            "recorded_at": 7,
            "last_acked_id": "ack-9",
        }
    )
    assert is_ok(parsed)
    assert parsed.value.kind is TaskLedgerEntryKind.UNKNOWN_TAIL
    assert parsed.value.authored_by.daemon is True
    assert parsed.value.last_acked_id == "ack-9"
    assert "model_deployment_ref" not in parsed.value.to_payload()
