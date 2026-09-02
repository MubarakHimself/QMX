"""Story 46.1 — Task Ledger entry schema and named leases (FR-Q57; CT-51)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.ledgers import (
    DAEMON_AUTHORED_ENTRY_KINDS,
    LEDGER_ENTRY_OPTIONAL_REFS,
    LEDGER_ENTRY_REQUIRED_FIELDS,
    QuantLedgerLease,
    named_lease_kind,
    parse_task_ledger_entry,
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
