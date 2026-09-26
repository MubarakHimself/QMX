"""Story 3.6 — legacy Records streams as projection names (AC4)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from qmf.core import is_refusal
from qmf.core.refusal import RefusalCategory
from qmf.data import (
    RECORDS_STREAM_MAPPING,
    DecisionOutcome,
    JournalEventType,
    RecordsStreamName,
    RecordsStreamRule,
    records_stream,
)

_path = Path(__file__).resolve().parent / "logbooks_cases.py"
_name = "qmf.data.tests.logbooks_cases"
_existing = sys.modules.get(_name)
if _existing is not None:
    _cases = _existing
else:
    _spec = importlib.util.spec_from_file_location(_name, _path)
    assert _spec is not None and _spec.loader is not None
    _cases = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _cases
    _spec.loader.exec_module(_cases)

_ok = _cases.ok
_binding_fields = _cases.binding_fields
_event = _cases.event
_CMD_A = _cases.CMD_A


def test_records_stream_veto_ledger_selects_on_declared_outcome() -> None:
    authorized = _event(
        "decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED, sequence=0
    )
    refused = _event(
        "decision",
        _binding_fields(refusing_door="spread-door"),
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        sequence=1,
    )
    veto = _ok(records_stream([authorized, refused], "veto_ledger"))
    assert veto == [refused]
    assert _ok(records_stream([authorized, refused], RecordsStreamName.VETO_LEDGER)) == [refused]


def test_records_stream_maps_each_legacy_name_onto_event_types() -> None:
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=0)
    fill = _event("fill", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=1)
    decision = _event("decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED, sequence=2)
    transition = _event("risk transition", _binding_fields(), sequence=3)
    promotion = _event("promotion", _binding_fields(), sequence=4)
    control = _event(
        "control action", _binding_fields() | {"control_action_subtype": "kill"}, sequence=5
    )
    events = [order, fill, decision, transition, promotion, control]

    # records_stream preserves input order, so compare ordered lists (events are unhashable).
    assert _ok(records_stream(events, "trade_journal")) == [order, fill]
    assert _ok(records_stream(events, "book_journal")) == [decision, transition, promotion]
    assert _ok(records_stream(events, "ksa_audit_log")) == [control]
    assert _ok(records_stream(events, "correlation_ledger")) == [transition]


def test_records_stream_unknown_name_is_refused() -> None:
    refused = records_stream([], "not_a_records_stream")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_records_stream_mapping_is_the_one_versioned_table() -> None:
    assert set(RECORDS_STREAM_MAPPING) == set(RecordsStreamName)
    veto_rule = RECORDS_STREAM_MAPPING[RecordsStreamName.VETO_LEDGER]
    assert isinstance(veto_rule, RecordsStreamRule)
    assert veto_rule.outcome is DecisionOutcome.REFUSED_BY_DOOR
    assert veto_rule.event_types == frozenset({JournalEventType.DECISION})
    # Every mapped type is one of the seven; no second catalog exists.
    mapped: set[JournalEventType] = set()
    for rule in RECORDS_STREAM_MAPPING.values():
        mapped |= rule.event_types
    assert mapped <= set(JournalEventType)
