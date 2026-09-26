"""Story 3.6 — entity-journal projections and the command-fingerprint join (AC1, AC2)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from qmf.core import AccountRole, is_refusal
from qmf.data import (
    BotSeat,
    CommandIndex,
    DecisionOutcome,
    EntitySelector,
    EventClass,
    JournalEventType,
    Logbook,
    ProjectedRow,
    bms_journal,
    book_journal,
    bot_logbook,
    entity_journal,
    read_binding,
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
_fp = _cases.fp
_binding_fields = _cases.binding_fields
_event = _cases.event
_BOOK = _cases.BOOK
_BMS = _cases.BMS
_VENUE = _cases.VENUE
_ACCOUNT = _cases.ACCOUNT
_BOT_DEF = _cases.BOT_DEF
_CMD_A = _cases.CMD_A
_CMD_B = _cases.CMD_B


def test_book_journal_risk_authored_only_without_join() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    control = _event(
        "control action", _binding_fields() | {"control_action_subtype": "kill"}, sequence=1
    )
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=2)
    logbook = _ok(book_journal([decision, control, order], _BOOK, role=AccountRole.LIVE))
    # No command_index -> venue order is not joined; only the two risk-authored events.
    assert [row.event.event_type for row in logbook.rows] == [
        JournalEventType.DECISION,
        JournalEventType.CONTROL_ACTION,
    ]
    assert all(row.event_class is EventClass.RISK_AUTHORED for row in logbook.rows)


def test_book_journal_joins_orders_and_fills_through_command_fingerprint() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=1)
    fill = _event("fill", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=2)
    unrelated = _event("order", {"command_fingerprint": _CMD_B.value, "role": "live"}, sequence=3)
    events = [decision, order, fill, unrelated]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))
    classes = [row.event_class for row in logbook.rows]
    assert classes == [
        EventClass.RISK_AUTHORED,
        EventClass.VENUE_AUTHORED,
        EventClass.VENUE_AUTHORED,
    ]
    # The joined venue rows carry the binding they inherited, never from their own payload.
    assert all(
        row.binding is not None and row.binding.book_instance_id == _BOOK for row in logbook.rows
    )


def test_bms_and_binding_projections() -> None:
    event = _event("risk transition", _binding_fields(), sequence=0)
    other = _event(
        "risk transition", _binding_fields() | {"bms_instance_id": "other-bms"}, sequence=1
    )
    bms = _ok(bms_journal([event, other], _BMS, role=AccountRole.LIVE))
    assert [row.event for row in bms.rows] == [event]

    binding = _ok(read_binding(event))
    selector = _ok(EntitySelector.for_binding(binding))
    combined = _ok(entity_journal([event, other], selector=selector, role=AccountRole.LIVE))
    assert [row.event for row in combined.rows] == [event]


def test_bot_logbook_matches_risk_and_joined_venue() -> None:
    decision = _event(
        "decision",
        _binding_fields(
            bot_definition_fp=_BOT_DEF.value,
            seat_binding="seat-1",
            command_fingerprint=_CMD_A.value,
        ),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=1)
    other_bot = _event(
        "decision",
        _binding_fields(bot_definition_fp=_fp({"bot": "other"}).value, seat_binding="seat-2"),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=2,
    )
    events = [decision, order, other_bot]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(
        bot_logbook(events, _BOT_DEF, "seat-1", role=AccountRole.LIVE, command_index=index)
    )
    assert [row.event for row in logbook.rows] == [decision, order]
    assert logbook.rows[1].bot_seat == BotSeat(bot_definition_fp=_BOT_DEF, seat_binding="seat-1")


def test_risk_authored_event_without_binding_is_skipped() -> None:
    # A qmf-data control action with no binding does not match any entity selector.
    control = _event("control action", {"control_action_subtype": "seal-look", "role": "live"})
    decision = _event("decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED, sequence=1)
    logbook = _ok(book_journal([control, decision], _BOOK, role=AccountRole.LIVE))
    assert [row.event for row in logbook.rows] == [decision]


def test_partial_binding_and_partial_bot_are_refused_during_selection() -> None:
    partial = _event(
        "decision", {"book_instance_id": _BOOK, "role": "live"}, outcome=DecisionOutcome.AUTHORIZED
    )
    assert is_refusal(book_journal([partial], _BOOK, role=AccountRole.LIVE))

    bad_bot = _event(
        "decision",
        _binding_fields(bot_definition_fp="bad", seat_binding="seat-1"),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(book_journal([bad_bot], _BOOK, role=AccountRole.LIVE))


def test_matched_row_missing_role_is_refused() -> None:
    no_role = _event(
        "decision",
        {
            "book_instance_id": _BOOK,
            "bms_instance_id": _BMS,
            "venue_id": _VENUE,
            "account_id": _ACCOUNT,
        },
        outcome=DecisionOutcome.AUTHORIZED,
    )
    refused = book_journal([no_role], _BOOK, role=AccountRole.LIVE)
    assert is_refusal(refused)


def test_venue_leak_in_join_path_refuses() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    leaked_order = _event(
        "order",
        {"command_fingerprint": _CMD_A.value, "role": "live", "book_instance_id": _BOOK},
        sequence=1,
    )
    events = [decision, leaked_order]
    index = _ok(CommandIndex.build(events))
    assert is_refusal(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))


def test_venue_leak_on_another_book_does_not_poison_this_projection() -> None:
    # L8: a leaked-key venue event that joins to a DIFFERENT book must not refuse THIS book's
    # clean projection. The neutral-payload guard is scoped to events matched into the
    # requested read; an unrelated leaky producer on another book is not grounds to refuse.
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    other_decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_B.value) | {"book_instance_id": "other-book"},
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=1,
    )
    leaked_other_order = _event(
        "order",
        {"command_fingerprint": _CMD_B.value, "role": "live", "book_instance_id": "other-book"},
        sequence=2,
    )
    events = [decision, other_decision, leaked_other_order]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))
    # The unrelated leaked order attributes to other-book, is not matched here, and is simply
    # not joined — never a refusal that would poison this Book's read.
    assert [row.event for row in logbook.rows] == [decision]


def test_venue_event_with_untracked_command_is_skipped() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order_untracked = _event(
        "order", {"command_fingerprint": _CMD_B.value, "role": "live"}, sequence=1
    )
    order_no_cmd = _event("data quality", {"role": "live", "metric": "spread"}, sequence=2)
    events = [decision, order_untracked, order_no_cmd]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))
    assert [row.event for row in logbook.rows] == [decision]


def test_logbook_and_projected_row_properties() -> None:
    event = _event("decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED)
    binding = _ok(read_binding(event))
    row = ProjectedRow(
        event=event, event_class=EventClass.RISK_AUTHORED, role=AccountRole.LIVE, binding=binding
    )
    logbook = Logbook(rows=(row,))
    assert logbook.events == (event,)
    assert logbook.roles == frozenset({AccountRole.LIVE})
    assert logbook.selector is None
    assert logbook.cross_role is None


def test_venue_join_binding_mismatch_is_skipped() -> None:
    # The command is indexed to book-7, but we project a different book: the joined venue
    # event's inherited binding does not match the selector, so it is skipped.
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"}, sequence=1)
    events = [decision, order]
    index = _ok(CommandIndex.build(events))
    logbook = _ok(book_journal(events, "other-book", role=AccountRole.LIVE, command_index=index))
    assert logbook.rows == ()


def test_joined_venue_row_missing_role_is_refused() -> None:
    decision = _event(
        "decision",
        _binding_fields(command_fingerprint=_CMD_A.value),
        outcome=DecisionOutcome.AUTHORIZED,
        sequence=0,
    )
    order_no_role = _event("order", {"command_fingerprint": _CMD_A.value}, sequence=1)
    events = [decision, order_no_role]
    index = _ok(CommandIndex.build(events))
    assert is_refusal(book_journal(events, _BOOK, role=AccountRole.LIVE, command_index=index))
