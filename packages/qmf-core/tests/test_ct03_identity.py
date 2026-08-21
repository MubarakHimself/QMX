"""Executable CT-03 contract test, owned by qmf-core.

Verifies instrument/venue/account identity: the opaque never-parsed
``(venue, symbol)`` pair, VenueId opacity, the fixed account-role set, dated
records that never rewrite history, value-or-refusal construction via CT-04, and
the fp1 null prohibition (CT-03; DEC-0107, DEC-0108, DEC-0109, DEC-0100).
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

import pytest
from qmf.core.identity import (
    Account,
    AccountRole,
    DatedRecord,
    Instrument,
    Venue,
    VenueId,
)
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_ok, is_refusal


def _venue(value: str = "venue-1") -> VenueId:
    result = VenueId.try_create(value)
    assert is_ok(result)
    return result.value


# --- VenueId: operator-minted, opaque, stable token -------------------------


def test_venue_id_is_a_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(VenueId)
    venue = VenueId("venue-1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        venue.value = "venue-2"  # type: ignore[misc]


def test_venue_id_try_create_accepts_opaque_token() -> None:
    result = VenueId.try_create("venue-ic-markets-01")
    assert is_ok(result)
    assert result.value.value == "venue-ic-markets-01"


def test_venue_id_stored_verbatim_never_transformed() -> None:
    # Surrounding content is preserved exactly; the token is opaque, not parsed.
    result = VenueId.try_create("Venue/IC-Markets_01")
    assert is_ok(result)
    assert result.value.value == "Venue/IC-Markets_01"


def test_venue_id_refuses_empty_or_blank() -> None:
    for bad in ("", "   ", "\t"):
        result = VenueId.try_create(bad)
        assert is_refusal(result)
        assert result.category is RefusalCategory.INVALID_INPUT
        assert result.retryability is Retryability.NO
        assert result.context["field"] == "value"


def test_venue_id_refuses_non_string() -> None:
    result = VenueId.try_create(None)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "value"


def test_two_venue_ids_are_distinct_identities() -> None:
    # A prop firm white-labeling cTrader is its own venue: distinct tokens,
    # distinct identities, even on shared infrastructure.
    broker = _venue("venue-ctrader-broker")
    prop = _venue("venue-ctrader-propfirm")
    assert broker != prop


# --- Instrument: opaque (venue, symbol), symbol never parsed ----------------


def test_instrument_is_the_opaque_pair() -> None:
    venue = _venue()
    result = Instrument.try_create(venue, "EURUSD")
    assert is_ok(result)
    instrument = result.value
    assert instrument.venue is venue
    assert instrument.symbol == "EURUSD"


def test_instrument_symbol_stored_verbatim_never_parsed() -> None:
    venue = _venue()
    # A structured-looking symbol is stored whole — never split on '/', cased,
    # or otherwise interpreted.
    result = Instrument.try_create(venue, "eur/usd.spot")
    assert is_ok(result)
    assert result.value.symbol == "eur/usd.spot"


def test_same_symbol_on_two_venues_never_mix() -> None:
    a = Instrument.try_create(_venue("venue-a"), "EURUSD")
    b = Instrument.try_create(_venue("venue-b"), "EURUSD")
    assert is_ok(a)
    assert is_ok(b)
    assert a.value != b.value


def test_instrument_refuses_missing_venue() -> None:
    result = Instrument.try_create(None, "EURUSD")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "venue"


def test_instrument_refuses_venue_that_is_not_a_venue_id() -> None:
    result = Instrument.try_create("venue-a", "EURUSD")  # a raw string, not a VenueId
    assert is_refusal(result)
    assert result.context["field"] == "venue"


def test_instrument_refuses_venue_id_with_blank_value() -> None:
    # Defense in depth: an unchecked-constructed VenueId with a blank token.
    result = Instrument.try_create(VenueId("   "), "EURUSD")
    assert is_refusal(result)
    assert result.context["field"] == "venue"


def test_instrument_refuses_missing_symbol() -> None:
    result = Instrument.try_create(_venue(), "")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "symbol"


def test_instrument_refuses_non_string_symbol() -> None:
    result = Instrument.try_create(_venue(), 42)
    assert is_refusal(result)
    assert result.context["field"] == "symbol"


# --- Venue and Account: first-class nouns -----------------------------------


def test_venue_noun_wraps_a_valid_venue_id() -> None:
    venue_id = _venue()
    result = Venue.try_create(venue_id)
    assert is_ok(result)
    assert result.value.venue_id is venue_id


def test_venue_noun_refuses_invalid_identity() -> None:
    result = Venue.try_create("not-a-venue-id")
    assert is_refusal(result)
    assert result.context["field"] == "venue_id"


def test_account_carries_exactly_one_role() -> None:
    venue = _venue()
    result = Account.try_create("acct-1", venue, AccountRole.LIVE)
    assert is_ok(result)
    account = result.value
    assert account.account_id == "acct-1"
    assert account.venue is venue
    assert account.role is AccountRole.LIVE


def test_account_role_accepts_the_canonical_string() -> None:
    result = Account.try_create("acct-1", _venue(), "paper-validation")
    assert is_ok(result)
    assert result.value.role is AccountRole.PAPER_VALIDATION


def test_account_role_set_is_exactly_the_five_values() -> None:
    assert {member.value for member in AccountRole} == {
        "live",
        "demo",
        "paper-validation",
        "paper-benched",
        "prop-firm",
    }


def test_account_refuses_blank_id() -> None:
    result = Account.try_create("  ", _venue(), AccountRole.DEMO)
    assert is_refusal(result)
    assert result.context["field"] == "account_id"


def test_account_refuses_invalid_venue() -> None:
    result = Account.try_create("acct-1", "venue-a", AccountRole.DEMO)
    assert is_refusal(result)
    assert result.context["field"] == "venue"


def test_account_refuses_unknown_role() -> None:
    result = Account.try_create("acct-1", _venue(), "supervisor")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "role"
    assert "prop-firm" in result.context["allowed"]  # type: ignore[operator]


def test_account_refuses_non_string_role() -> None:
    result = Account.try_create("acct-1", _venue(), 7)
    assert is_refusal(result)
    assert result.context["field"] == "role"


# --- DatedRecord: append-only, history never rewrites -----------------------


def test_dated_record_points_at_an_identity() -> None:
    venue = _venue()
    result = DatedRecord.try_create(venue, date(2025, 1, 1), {"name": "IC Markets"})
    assert is_ok(result)
    record = result.value
    assert record.target is venue
    assert record.effective_date == "2025-01-01"
    assert record.content["name"] == "IC Markets"


def test_dated_record_may_point_at_an_instrument() -> None:
    instrument_result = Instrument.try_create(_venue(), "EURUSD")
    assert is_ok(instrument_result)
    instrument = instrument_result.value
    result = DatedRecord.try_create(instrument, "2025-02-01", {"asset_class": "fx"})
    assert is_ok(result)
    assert result.value.target is instrument


def test_dated_record_accepts_iso_string_date() -> None:
    result = DatedRecord.try_create(_venue(), "2025-06-15", {"alias": "ICM"})
    assert is_ok(result)
    assert result.value.effective_date == "2025-06-15"


def test_dated_record_refuses_bad_date() -> None:
    result = DatedRecord.try_create(_venue(), "not-a-date", {"name": "x"})
    assert is_refusal(result)
    assert result.context["field"] == "effective_date"


def test_dated_record_returns_a_refusal_for_a_non_date_type() -> None:
    # Regression (H3/CT-04): a non-string, non-date effective_date makes
    # date.fromisoformat raise TypeError, not ValueError. The refusal must be
    # RETURNED, never raised.
    result = DatedRecord.try_create(_venue(), 12345, {"name": "x"})  # type: ignore[arg-type]
    assert is_refusal(result)
    assert result.context["field"] == "effective_date"


def test_dated_record_is_frozen_and_content_immutable() -> None:
    result = DatedRecord.try_create(_venue(), "2025-01-01", {"name": "x"})
    assert is_ok(result)
    record = result.value
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.effective_date = "2025-01-02"  # type: ignore[misc]
    with pytest.raises(TypeError):
        record.content["name"] = "y"  # type: ignore[index]


def test_dated_record_content_is_snapshotted() -> None:
    source: dict[str, object] = {"name": "x"}
    result = DatedRecord.try_create(_venue(), "2025-01-01", source)
    assert is_ok(result)
    source["name"] = "mutated"  # must not leak into the frozen record
    assert result.value.content["name"] == "x"


def test_dated_record_content_is_deep_frozen() -> None:
    # Regression (L3): __post_init__ froze only the top level, leaving nested
    # mappings and arrays shared and mutable — append-only history must never
    # rewrite, not even through a nested reference the caller still holds.
    source: dict[str, object] = {"meta": {"alias": "ICM"}, "aliases": ["ICM", "IC-Markets"]}
    result = DatedRecord.try_create(_venue(), "2025-01-01", source)
    assert is_ok(result)
    record = result.value
    # A later mutation of the caller's nested dict cannot leak into the record.
    source["meta"]["alias"] = "TAMPERED"  # type: ignore[index]
    assert record.content["meta"]["alias"] == "ICM"  # type: ignore[index]
    # The stored nested mapping is itself immutable, and arrays freeze to tuples.
    with pytest.raises(TypeError):
        record.content["meta"]["alias"] = "y"  # type: ignore[index]
    assert record.content["aliases"] == ("ICM", "IC-Markets")


def test_correction_is_a_new_record_not_an_edit() -> None:
    venue = _venue()
    first = DatedRecord.try_create(venue, "2024-01-05", {"name": "IC Markets"})
    corrected = DatedRecord.try_create(venue, "2025-03-20", {"name": "IC Markets Global"})
    assert is_ok(first)
    assert is_ok(corrected)
    # Both point at the same identity; the original is untouched — a correction
    # is a new dated record, history never rewrites.
    assert first.value.target is corrected.value.target
    assert first.value.content["name"] == "IC Markets"
    assert corrected.value.content["name"] == "IC Markets Global"
    assert first.value != corrected.value


# --- fp1 null prohibition ---------------------------------------------------


def test_dated_record_refuses_null_field() -> None:
    # Null is prohibited in identity content: absent metadata is an omitted key,
    # never a null value (DEC-0108).
    result = DatedRecord.try_create(_venue(), "2025-01-01", {"asset_class": None})
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "content"
    assert result.context["key"] == "asset_class"


def test_dated_record_refuses_empty_content() -> None:
    result = DatedRecord.try_create(_venue(), "2025-01-01", {})
    assert is_refusal(result)
    assert result.context["field"] == "content"


def test_dated_record_refuses_empty_key() -> None:
    result = DatedRecord.try_create(_venue(), "2025-01-01", {"": "x"})
    assert is_refusal(result)
    assert result.context["field"] == "content"


def test_absent_metadata_is_an_omitted_key_not_a_null() -> None:
    # The positive counterpart: a record simply omits the fields it does not
    # carry; the mapping never holds a null placeholder.
    result = DatedRecord.try_create(_venue(), "2025-01-01", {"name": "ICM"})
    assert is_ok(result)
    assert "asset_class" not in result.value.content


# --- M2/M3: dated-record validation depth -----------------------------------


def test_dated_record_refuses_target_that_is_not_an_identity() -> None:
    # Regression (M2): the target must be a valid VenueId or Instrument; a raw
    # string, None, or an arbitrary object is refused rather than stored.
    for bad in ("not-a-venue", None, 42, object()):
        result = DatedRecord.try_create(bad, "2025-01-01", {"name": "x"})  # type: ignore[arg-type]
        assert is_refusal(result)
        assert result.category is RefusalCategory.INVALID_INPUT
        assert result.context["field"] == "target"


def test_dated_record_refuses_venue_id_target_with_blank_value() -> None:
    # Defense in depth (M2): an unchecked-constructed VenueId with a blank token
    # is not a valid target.
    result = DatedRecord.try_create(VenueId("   "), "2025-01-01", {"name": "x"})
    assert is_refusal(result)
    assert result.context["field"] == "target"


def test_dated_record_refuses_instrument_target_with_blank_symbol() -> None:
    # Defense in depth (M2): an unchecked-constructed Instrument with a blank
    # symbol is not a valid target.
    result = DatedRecord.try_create(Instrument(_venue(), "  "), "2025-01-01", {"name": "x"})
    assert is_refusal(result)
    assert result.context["field"] == "target"


def test_dated_record_refuses_datetime_effective_date() -> None:
    # Regression (M3): datetime is a date subclass, but its isoformat carries a
    # time component ('2026-08-21T13:45:00') that is not a canonical ISO date, so
    # a datetime is refused rather than silently truncated or stored as a stamp.
    stamp = datetime(2026, 8, 21, 13, 45, tzinfo=timezone.utc)
    result = DatedRecord.try_create(_venue(), stamp, {"name": "x"})
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "effective_date"


def test_dated_record_refuses_null_nested_in_a_mapping() -> None:
    # Regression (M2): null is prohibited ANYWHERE, not just at the top level.
    result = DatedRecord.try_create(_venue(), "2025-01-01", {"meta": {"alias": None}})
    assert is_refusal(result)
    assert result.context["field"] == "content"
    assert result.context["key"] == "alias"


def test_dated_record_refuses_null_nested_in_an_array() -> None:
    # Regression (M2): a null element inside an order-significant array is refused.
    result = DatedRecord.try_create(_venue(), "2025-01-01", {"aliases": ["ICM", None]})
    assert is_refusal(result)
    assert result.context["field"] == "content"


def test_dated_record_refuses_non_string_key() -> None:
    # Regression (M2): non-string keys were accepted ({7: 'x'} returned Ok).
    result = DatedRecord.try_create(_venue(), "2025-01-01", {7: "x"})  # type: ignore[dict-item]
    assert is_refusal(result)
    assert result.context["field"] == "content"


def test_dated_record_refuses_non_string_key_nested() -> None:
    # Regression (M2): the non-string-key check applies at every depth.
    result = DatedRecord.try_create(_venue(), "2025-01-01", {"meta": {7: "x"}})
    assert is_refusal(result)
    assert result.context["field"] == "content"


def test_dated_record_refuses_whitespace_only_key() -> None:
    # Regression (M2): a blank-but-not-empty key ('   ') was accepted.
    result = DatedRecord.try_create(_venue(), "2025-01-01", {"   ": "x"})
    assert is_refusal(result)
    assert result.context["field"] == "content"


def test_dated_record_refuses_non_mapping_content() -> None:
    # Defense in depth (M2): content is a key->value mapping, never a bare value.
    result = DatedRecord.try_create(_venue(), "2025-01-01", "not-a-mapping")  # type: ignore[arg-type]
    assert is_refusal(result)
    assert result.context["field"] == "content"


def test_dated_record_accepts_clean_nested_content() -> None:
    # The positive counterpart: nested mappings and arrays with no null and only
    # non-blank string keys construct cleanly.
    content = {"meta": {"alias": "ICM"}, "aliases": ["ICM", "IC-Markets"]}
    result = DatedRecord.try_create(_venue(), "2025-01-01", content)
    assert is_ok(result)
    assert result.value.content["meta"] == {"alias": "ICM"}


# --- construction pattern ---------------------------------------------------


def test_invalid_construction_is_returned_not_raised() -> None:
    # A domain-invalid request yields a value, never an exception across the
    # boundary — the caller branches on it (CT-04; DEC-0109).
    result = VenueId.try_create("")
    assert isinstance(result, TypedRefusal)


def test_unchecked_constructor_is_available_for_trusted_use() -> None:
    # The unchecked path builds without validation for callers that already hold
    # valid parts.
    venue = VenueId("venue-1")
    account = Account("acct-1", venue, AccountRole.LIVE)
    assert account.venue.value == "venue-1"
