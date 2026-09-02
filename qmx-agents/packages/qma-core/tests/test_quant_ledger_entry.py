"""Story 46.3 — Quant Ledger declared entry schema (FR-Q59; CT-51)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.ledgers import (
    QUANT_LEDGER_ENTRY_REQUIRED_FIELDS,
    QUANT_LEDGER_FORBIDDEN_TASK_KEYS,
    parse_quant_ledger_entry,
)
from qma.core.vocabulary import CLOSED_VOCABULARIES, QuantLedgerEntryKind, parse_closed
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, "lead")
    assert is_ok(minted)
    return minted.value


def test_declared_quant_ledger_kinds_are_closed() -> None:
    names = {entry.name for entry in CLOSED_VOCABULARIES}
    assert "quant_ledger_entry_kind" in names
    assert parse_closed(QuantLedgerEntryKind, "mission_opened") is (
        QuantLedgerEntryKind.MISSION_OPENED
    )
    assert {member.value for member in QuantLedgerEntryKind} == {
        "mission_opened",
        "mission_closed",
        "delegation",
        "escalation",
        "standing_decision",
    }
    assert "id" in QUANT_LEDGER_ENTRY_REQUIRED_FIELDS
    assert "task_completed" in QUANT_LEDGER_FORBIDDEN_TASK_KEYS


def test_quant_ledger_entry_parses_declared_schema() -> None:
    owner = _owner()
    parsed = parse_quant_ledger_entry(
        {
            "id": "ql-1",
            "kind": "standing_decision",
            "authored_by": {"agent": "agent-lead", "quant": owner.value},
            "recorded_at": 1_700_000_000_000_000_000,
            "model_deployment_ref": "deploy:workhorse",
            "mission_ref": "mission-1",
            "body": {"decision": "cover EURUSD overnight"},
        }
    )
    assert is_ok(parsed)
    payload = parsed.value.to_payload()
    assert payload["kind"] == "standing_decision"
    authored = payload["authored_by"]
    assert isinstance(authored, dict)
    assert authored["agent"] == "agent-lead"
    assert authored["quant"] == owner.value


def test_quant_ledger_entry_refuses_task_ledger_restatement() -> None:
    owner = _owner()
    refused = parse_quant_ledger_entry(
        {
            "id": "ql-bad",
            "kind": "delegation",
            "authored_by": {"agent": "agent-lead", "quant": owner.value},
            "recorded_at": 1,
            "model_deployment_ref": "deploy:workhorse",
            "task_completed": {"what_was_done": "no"},
        }
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "entry"
    invented = parse_quant_ledger_entry(
        {
            "id": "ql-kind",
            "kind": "progress",
            "authored_by": {"agent": "agent-lead", "quant": owner.value},
            "recorded_at": 1,
            "model_deployment_ref": "deploy:workhorse",
        }
    )
    assert is_refusal(invented)
    assert invented.context["field"] == "kind"
