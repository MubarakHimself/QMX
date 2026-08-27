"""L3 acceptance tests — the cTrader adapter's ratified venue facts (Story 8.8).

Oracle: Story 8.8 acceptance criteria, AR-46, DEC-0135, and CT-18 money nullability.

Covers QA-E08-L3-009, L3-010, L3-016.
"""

from __future__ import annotations

from qmf.core import RefusalCategory, RoundingMode, is_ok, is_refusal
from qmf.venue import (
    HEARTBEAT_BOUND_SECONDS,
    HISTORICAL_RATE_LIMIT_PER_SECOND,
    HISTORICAL_TICK_SPAN_CAP_MS,
    MARKET_DATA_WIRE_SCALE_EXPONENT,
    MONEY_BEARING_MESSAGES,
    NON_HISTORICAL_RATE_LIMIT_PER_SECOND,
    CTraderBrokerConfiguration,
    MeasuredFact,
    ProbeCheck,
    ProbeVerdict,
    RatePacer,
    RequestClass,
    SessionRecovery,
    SessionTopology,
    TimestampUnit,
    VenueEvidenceClass,
    VenueObservationProfile,
    decode_execution_price,
    decode_market_data_price,
    decode_money,
    decode_timestamp,
    tick_span_within_cap,
)

import _helpers as H


# --- QA-E08-L3-009 — the named money-path decode boundary (P0) --------------


def test_l3_009_timestamp_decode_records_mandatory_receive_time():
    """Story 8.8 AC-1: per-field Unix-ms UTC timestamps with mandatory receive-time
    recording (no server clock exists) — an absent receive time is refused, never
    defaulted."""
    # A millisecond wire value converts to UTC nanoseconds; receive time is mandatory.
    good = decode_timestamp(1_700_000_000_000, TimestampUnit.MILLISECONDS, H.mk_instant(42))
    assert is_ok(good)
    assert good.value.instant.value_ns == 1_700_000_000_000 * 1_000_000
    assert good.value.received_at.value_ns == 42
    # Absent receive time is refused (no server clock to fall back on).
    assert is_refusal(decode_timestamp(1_700_000_000_000, TimestampUnit.MILLISECONDS, None))


def test_l3_009_market_data_price_is_exact_scaled_integer_at_wire_scale():
    """Story 8.8 AC-1: the 1/100000 market-data wire scale is stored verbatim as an exact
    scale-5 integer — never a binary /100000 divide."""
    assert MARKET_DATA_WIRE_SCALE_EXPONENT == 5
    ins = H.mk_instrument(H.mk_venue())
    res = decode_market_data_price(110005, ins)
    assert is_ok(res)
    assert res.value.value == 110005
    assert res.value.scale == 5
    # A negative wire value (uint64 is non-negative) is refused.
    assert is_refusal(decode_market_data_price(-1, ins))


def test_l3_009_execution_price_raw_double_crosses_the_named_boundary():
    """Story 8.8 AC-1: execution prices are raw doubles crossing the named money-path
    boundary at the instrument's declared digits under a declared rounding mode."""
    ins = H.mk_instrument(H.mk_venue())
    res = decode_execution_price(1.10005, ins, 5, RoundingMode.HALF_UP)
    assert is_ok(res)
    assert res.value.price.value == 110005  # crossed to a scaled integer at digits=5
    assert res.value.raw_double == 1.10005  # the raw float kept only as provenance


def test_l3_009_money_decode_governs_nine_messages_absent_exponent_refuses():
    """Story 8.8 AC-1 / CT-18: a moneyDigits exponent governs the nine money-bearing
    messages; an absent exponent refuses that message's money decode, never a default
    to 2."""
    assert len(MONEY_BEARING_MESSAGES) == 9
    # A present exponent decodes to exact Money at the declared money scale.
    good = decode_money("ProtoOADeal", 12345, "USD", 2)
    assert is_ok(good)
    assert good.value.value == 12345 and good.value.scale == 2
    # An ABSENT exponent refuses the money decode (unavailable dependency, never a
    # silent default to 2).
    absent = decode_money("ProtoOADeal", 12345, "USD", None)
    assert is_refusal(absent)
    assert absent.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # A message outside the nine is not a moneyDigits decode.
    assert is_refusal(decode_money("ProtoOANotMoney", 12345, "USD", 2))


# --- QA-E08-L3-010 — daily boundary / BID basis never hardcoded (P1) --------


def _profile_with(v, a, facts):
    profile = H.ok(VenueObservationProfile.try_create(v, a))
    for fact in facts:
        profile = H.ok(profile.with_fact(fact))
    return profile


def test_l3_010_daily_boundary_and_bar_basis_read_from_profile_not_hardcoded():
    """Story 8.8 AC-4 / Story 8.1 AC-2: the daily boundary and trendbar basis are
    measured per broker and read from the venue-observation profile — neither the
    17:00-New-York boundary nor the BID basis is hardcoded."""
    v = H.mk_venue()
    a = H.mk_account(v)
    # A profile measured for THIS broker: boundary at UTC minute 480 (not 17:00-NY), and
    # a bar basis reconciled as ASK (not BID).
    boundary = H.ok(
        MeasuredFact.try_create(
            ProbeCheck.DAILY_BOUNDARY, ProbeVerdict.VERIFIED, H.mk_instant(1), "se", "sref",
            measured={"utc_minute_of_day": 480, "bars": 3},
        )
    )
    basis = H.ok(
        MeasuredFact.try_create(
            ProbeCheck.BAR_BASIS, ProbeVerdict.VERIFIED, H.mk_instant(2), "se", "sref",
            measured={"quote_type": "ASK", "reconciled_bars": 5},
        )
    )
    profile = _profile_with(v, a, [boundary, basis])
    config = H.ok(CTraderBrokerConfiguration.try_create(v, a, profile))

    # The trendbar basis is whatever the profile measured — ASK here, never a hardcoded BID.
    assert H.ok(config.trendbar_price_basis()) == "ASK"

    # The minted daily-boundary calendar encodes the MEASURED minute, never a 17:00-NY value.
    cal = config.daily_boundary_calendar("v1", "2024a")
    assert is_ok(cal)
    assert "utc_minute_of_day=480" in cal.value.rule_set
    assert "17:00" not in cal.value.rule_set
    assert "New_York" not in cal.value.rule_set and "America" not in cal.value.rule_set


def test_l3_010_unmeasured_daily_boundary_refuses_never_defaults():
    """Story 8.1 AC-3 / AR-45: an unmeasured daily boundary leaves venue daily bars
    ungoverned (an unavailable-dependency refusal), never a hardcoded default."""
    v = H.mk_venue()
    a = H.mk_account(v)
    empty_profile = H.ok(VenueObservationProfile.try_create(v, a))
    config = H.ok(CTraderBrokerConfiguration.try_create(v, a, empty_profile))
    res = config.require_daily_boundary()
    assert is_refusal(res)
    assert res.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # The calendar cannot be minted from an unmeasured boundary.
    assert is_refusal(config.daily_boundary_calendar("v1", "2024a"))


def test_l3_010_config_names_no_broker_only_opaque_identity():
    """Story 8.8 AC-5: only opaque VenueId/AccountId identity is held; no broker is named
    in code — the platform stays venue-blind above the port."""
    v = H.mk_venue()
    a = H.mk_account(v)
    profile = H.ok(VenueObservationProfile.try_create(v, a))
    config = H.ok(CTraderBrokerConfiguration.try_create(v, a, profile))
    ident = dict(config.deployment_identity())
    assert set(ident) == {"venue_id", "account_id"}
    assert ident["venue_id"] == v.value
    assert ident["account_id"] == a.account_id


# --- QA-E08-L3-016 — connection limits, session topology, recovery (P2) -----


def test_l3_016_rate_pacer_enforces_per_connection_ceilings():
    """Story 8.8 AC-2: the adapter paces itself at 50/s non-historical + 5/s historical
    per connection; a request at the ceiling is a transient-venue-failure."""
    assert NON_HISTORICAL_RATE_LIMIT_PER_SECOND == 50
    assert HISTORICAL_RATE_LIMIT_PER_SECOND == 5
    pacer = RatePacer()
    # Five historical requests inside one second are admitted; the sixth is refused.
    for t in range(HISTORICAL_RATE_LIMIT_PER_SECOND):
        assert is_ok(pacer.admit(RequestClass.HISTORICAL, H.mk_mono(t)))
    over = pacer.admit(RequestClass.HISTORICAL, H.mk_mono(HISTORICAL_RATE_LIMIT_PER_SECOND))
    assert is_refusal(over)
    assert over.category is RefusalCategory.TRANSIENT_VENUE_FAILURE


def test_l3_016_heartbeat_bound_span_cap_and_two_host_topology():
    """Story 8.8 AC-2: the 10-second heartbeat bound, the one-week historical tick-span
    cap, and demo/live as separate hosts requiring two simultaneous connections."""
    assert HEARTBEAT_BOUND_SECONDS == 10
    assert HISTORICAL_TICK_SPAN_CAP_MS == 7 * 24 * 60 * 60 * 1000
    # Exactly one week is within the cap; one ms more is refused.
    assert is_ok(tick_span_within_cap(0, HISTORICAL_TICK_SPAN_CAP_MS))
    assert is_refusal(tick_span_within_cap(0, HISTORICAL_TICK_SPAN_CAP_MS + 1))
    # Demo and live are separate hosts (two connections); one host serving both is refused.
    topo = SessionTopology.try_create("host-demo", "host-live")
    assert is_ok(topo)
    assert SessionTopology.required_connection_count == 2
    assert is_refusal(SessionTopology.try_create("same-host", "same-host"))


def test_l3_016_session_recovery_never_resubmits():
    """Story 8.8 AC-3: session recovery never resubmits a command."""
    assert SessionRecovery.resubmits_command is False
