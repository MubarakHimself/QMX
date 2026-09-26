"""Story 3.6 — logbook identity, event class, and payload readers (AC2, AC3).

Sibling modules cover selectors, projections, role scoping, and Records streams.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from qmf.core import (
    LIVE_EVIDENCE_NAMESPACE,
    AccountRole,
    World,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import RefusalCategory
from qmf.data import (
    BOOK_IDENTITY_FIELDS,
    CT25_CONTRACT_FORMAT_VERSION,
    BindingIdentity,
    BotSeat,
    DecisionOutcome,
    EventClass,
    JournalEventType,
    book_journal,
    event_class_of,
    guard_neutral_venue_payload,
    read_binding,
    read_bot_seat,
    read_command_fingerprint,
    read_role,
    records_stream,
    role_namespace,
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
_BOOK = _cases.BOOK
_BMS = _cases.BMS
_VENUE = _cases.VENUE
_ACCOUNT = _cases.ACCOUNT
_BOOK_DEF = _cases.BOOK_DEF
_BOT_DEF = _cases.BOT_DEF
_CMD_A = _cases.CMD_A


def test_event_class_covers_all_seven_types() -> None:
    risk = {
        JournalEventType.DECISION,
        JournalEventType.RISK_TRANSITION,
        JournalEventType.CONTROL_ACTION,
        JournalEventType.PROMOTION,
    }
    venue = {JournalEventType.ORDER, JournalEventType.FILL, JournalEventType.DATA_QUALITY}
    for event_type in JournalEventType:
        expected = EventClass.RISK_AUTHORED if event_type in risk else EventClass.VENUE_AUTHORED
        assert event_class_of(event_type) is expected
    assert risk | venue == set(JournalEventType)


def test_role_namespace_live_is_the_live_evidence_namespace() -> None:
    assert _ok(role_namespace(AccountRole.LIVE)) == LIVE_EVIDENCE_NAMESPACE


def test_role_namespace_gives_each_other_role_its_own_namespace() -> None:
    demo = _ok(role_namespace(AccountRole.DEMO))
    benched = _ok(role_namespace("paper-benched"))
    validation = _ok(role_namespace(AccountRole.PAPER_VALIDATION))
    assert demo == "demo"
    assert benched == "paper-benched"
    assert len({demo, benched, validation, LIVE_EVIDENCE_NAMESPACE}) == 4


def test_role_namespace_refuses_a_non_role() -> None:
    refused = role_namespace("not-a-role")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_binding_identity_round_trips_and_fingerprints() -> None:
    binding = _ok(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    assert binding.venue_id.value == _VENUE
    assert binding.world is World.LIVE
    identity = binding.fp1_identity()
    assert identity["book_instance_id"] == _BOOK
    assert identity["format_version"] == CT25_CONTRACT_FORMAT_VERSION
    # It is a canonical value: qmf-core can fingerprint it.
    assert is_ok(fingerprint(binding))


def test_binding_identity_refuses_each_missing_part() -> None:
    base: dict[str, object] = {
        "book_instance_id": _BOOK,
        "bms_instance_id": _BMS,
        "venue_id": _VENUE,
        "account_id": _ACCOUNT,
        "world": World.LIVE,
    }
    for field_name in ("book_instance_id", "bms_instance_id", "venue_id", "account_id", "world"):
        broken = dict(base)
        broken[field_name] = "" if field_name != "world" else "no-such-world"
        refused = BindingIdentity.try_create(**broken)  # type: ignore[arg-type]
        assert is_refusal(refused), field_name
        assert refused.context["field"] == field_name


def test_read_bot_seat_none_both_and_partial() -> None:
    assert (
        _ok(
            read_bot_seat(_event("decision", _binding_fields(), outcome=DecisionOutcome.AUTHORIZED))
        )
        is None
    )

    both = _event(
        "decision",
        _binding_fields(bot_definition_fp=_BOT_DEF.value, seat_binding="seat-1"),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    seat = _ok(read_bot_seat(both))
    assert seat == BotSeat(bot_definition_fp=_BOT_DEF, seat_binding="seat-1")

    partial_fp = _event(
        "decision",
        _binding_fields(bot_definition_fp=_BOT_DEF.value),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(read_bot_seat(partial_fp))

    partial_seat = _event(
        "decision", _binding_fields(seat_binding="seat-1"), outcome=DecisionOutcome.AUTHORIZED
    )
    assert is_refusal(read_bot_seat(partial_seat))

    bad_fp = _event(
        "decision",
        _binding_fields(bot_definition_fp="not-a-fp", seat_binding="seat-1"),
        outcome=DecisionOutcome.AUTHORIZED,
    )
    assert is_refusal(read_bot_seat(bad_fp))


def test_read_role_and_binding() -> None:
    event = _event(
        "decision", _binding_fields(AccountRole.DEMO), outcome=DecisionOutcome.AUTHORIZED
    )
    assert _ok(read_role(event)) is AccountRole.DEMO
    binding = _ok(read_binding(event))
    assert binding.book_instance_id == _BOOK

    no_role = _event(
        "promotion",
        {
            "book_instance_id": _BOOK,
            "bms_instance_id": _BMS,
            "venue_id": _VENUE,
            "account_id": _ACCOUNT,
        },
    )
    assert is_refusal(read_role(no_role))

    bad_role = _event("promotion", _binding_fields() | {"role": "nope"})
    assert is_refusal(read_role(bad_role))

    partial_binding = _event("promotion", {"book_instance_id": _BOOK, "role": "live"})
    assert is_refusal(read_binding(partial_binding))


def test_guard_neutral_venue_payload_rejects_each_book_identity_field() -> None:
    for leaked in sorted(BOOK_IDENTITY_FIELDS):
        event = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live", leaked: "x"})
        refused = guard_neutral_venue_payload(event)
        assert is_refusal(refused), leaked
        assert leaked in refused.context["leaked_fields"]  # type: ignore[operator]

    clean = _event("order", {"command_fingerprint": _CMD_A.value, "role": "live"})
    assert is_ok(guard_neutral_venue_payload(clean))


def test_read_command_fingerprint_valid_missing_and_leaked() -> None:
    ok = _event("fill", {"command_fingerprint": _CMD_A.value, "role": "live"})
    assert _ok(read_command_fingerprint(ok)) == _CMD_A

    missing = _event("fill", {"role": "live"})
    assert is_refusal(read_command_fingerprint(missing))

    leaked = _event(
        "fill", {"command_fingerprint": _CMD_A.value, "role": "live", "book_instance_id": _BOOK}
    )
    assert is_refusal(read_command_fingerprint(leaked))


def test_coercer_fallthroughs_refuse_wrong_typed_inputs() -> None:
    from qmf.core import VenueId

    assert is_refusal(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=123,
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    assert is_refusal(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=VenueId(""),
            account_id=_ACCOUNT,
            world=World.LIVE,
        )
    )
    assert is_refusal(
        BindingIdentity.try_create(
            book_instance_id=_BOOK,
            bms_instance_id=_BMS,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            world=123,
        )
    )
    assert is_refusal(book_journal([], _BOOK, cross_role=123))
    assert is_refusal(records_stream([], 123))
