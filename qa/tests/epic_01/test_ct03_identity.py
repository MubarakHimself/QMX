"""Epic 1 — CT-03 instrument/venue/account identity (Story 1.3, identity.py). L1.

Independent, requirements-derived assertions (E1-U09..U15). Authored from CT-03
(docs/contracts/ct-03-instrument-identity.yaml), FM (identity nouns), epics.md
Story 1.3. Source code is read-only evidence.
"""

from __future__ import annotations

from qmf.core.identity import Account, AccountRole, DatedRecord, Instrument, Venue, VenueId
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal

FIXED_ROLES = {"live", "demo", "paper-validation", "paper-benched", "prop-firm"}


def _ok(result: Result[object]) -> object:
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def _refusal(result: Result[object]) -> TypedRefusal:
    assert is_refusal(result), f"expected a TypedRefusal, got {result!r}"
    return result


def _venue() -> VenueId:
    return _ok(VenueId.try_create("VEN-1"))


# E1-U09 -----------------------------------------------------------------------
def test_e1_u09_instrument_is_opaque_pair_symbol_stored_verbatim_never_parsed() -> None:
    """CT-03: Instrument is the opaque pair (venue, venue-symbol); the symbol is
    stored verbatim and never parsed (exotic/unicode round-trips byte-identical)."""
    exotic = "EUR/USD..μ_🜛.[weird]"
    instrument = _ok(Instrument.try_create(_venue(), exotic))
    assert instrument.symbol == exotic  # byte-identical, never split/prefixed/cased
    assert isinstance(instrument.venue, VenueId)


# E1-U10 -----------------------------------------------------------------------
def test_e1_u10_venueid_opaque_stable_case_sensitive_distinct() -> None:
    """CT-03: VenueId is an opaque, stable token; two tokens differing only in case
    are distinct (never normalized/derived)."""
    lower = _ok(VenueId.try_create("ctrader-broker-a"))
    upper = _ok(VenueId.try_create("CTRADER-BROKER-A"))
    assert lower != upper
    assert lower.value == "ctrader-broker-a"  # stored verbatim


# E1-U11 -----------------------------------------------------------------------
def test_e1_u11_account_role_exactly_one_of_fixed_set_others_refused() -> None:
    """CT-03 enums: Account carries exactly one role from the fixed set; any other
    role value is refused."""
    assert {member.value for member in AccountRole} == FIXED_ROLES
    for role in FIXED_ROLES:
        acct = _ok(Account.try_create("ACC-1", _venue(), role))
        assert acct.role.value == role
    bad = _refusal(Account.try_create("ACC-1", _venue(), "market-maker"))
    assert bad.category is RefusalCategory.INVALID_INPUT
    assert bad.context["field"] == "role"


# E1-U12 (mutmut pin exact.py:251 / identity venue emptiness) -------------------
def test_e1_u12_missing_empty_blank_venue_refuses_never_defaults() -> None:
    """CT-03 / CT-04 / DEC-0109: try_create for identity with a missing/empty/blank
    venue returns a typed refusal, never a default."""
    good_symbol = "EURUSD"
    for bad_venue in (None, "", "   ", 123):
        # VenueId itself refuses empty/blank/non-string.
        assert is_refusal(VenueId.try_create(bad_venue))
        # Instrument with a blank/invalid venue refuses (never a default venue).
        r = _refusal(Instrument.try_create(bad_venue, good_symbol))
        assert r.context["field"] == "venue"
    # A VenueId forced blank through the unchecked ctor is still rejected downstream.
    blank = VenueId("   ")
    assert is_refusal(Instrument.try_create(blank, good_symbol))


# E1-U13 (mutmut pin exact.py:251 / identity symbol emptiness) ------------------
def test_e1_u13_missing_empty_blank_symbol_refuses_never_defaults() -> None:
    """CT-03 / CT-04 / DEC-0109: try_create for identity with a missing/empty/blank
    symbol returns a typed refusal, never a default."""
    for bad_symbol in (None, "", "   ", 3.14):
        r = _refusal(Instrument.try_create(_venue(), bad_symbol))
        assert r.context["field"] == "symbol"


# E1-U14 -----------------------------------------------------------------------
def test_e1_u14_null_prohibited_in_identity_content() -> None:
    """CT-03 nullability / DEC-0108: null is prohibited in identity content — an
    absent value is an omitted key, never a null field (at any depth)."""
    venue = _venue()
    # A null value anywhere in dated-record content is refused.
    r_top = _refusal(DatedRecord.try_create(venue, "2026-01-02", {"alias": None}))
    assert r_top.context["field"] == "content"
    r_nested = _refusal(
        DatedRecord.try_create(venue, "2026-01-02", {"meta": {"asset_class": None}})
    )
    assert r_nested.context["field"] == "content"
    # An omitted key (a present, non-null field) is accepted.
    good = _ok(DatedRecord.try_create(venue, "2026-01-02", {"asset_class": "forex"}))
    assert good.content["asset_class"] == "forex"


# E1-U15 -----------------------------------------------------------------------
def test_e1_u15_change_is_new_dated_record_history_append_only() -> None:
    """CT-03: a rename/alias/asset-class/metadata change is a NEW dated record
    pointing at the identity; stored history is not rewritten (append-only)."""
    venue = _venue()
    rec1 = _ok(DatedRecord.try_create(venue, "2026-01-01", {"name": "Broker A"}))
    rec2 = _ok(DatedRecord.try_create(venue, "2026-06-01", {"name": "Broker A Renamed"}))
    # Two distinct dated records, both pointing at the same identity target.
    assert rec1 != rec2
    assert rec1.target == rec2.target == venue
    assert rec1.effective_date == "2026-01-01"
    assert rec2.effective_date == "2026-06-01"
    # The record is frozen — history cannot be rewritten in place.
    import dataclasses

    assert dataclasses.is_dataclass(rec1)
    try:
        rec1.content = {"name": "tampered"}  # type: ignore[misc]
        raise AssertionError("dated record content is mutable — history could be rewritten")
    except dataclasses.FrozenInstanceError:
        pass
