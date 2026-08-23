"""Tier-1 tests for the cTrader adapter — ratified venue facts (Story 8.8; DEC-0135).

Exercises the five acceptance-criteria blocks of Story 8.8:

1. Inbound decode at the named money-path boundary: per-field Unix-ms UTC timestamps with
   mandatory receive-time recording (no server clock), the 1/100000 market-data wire scale,
   execution prices as raw doubles crossing the boundary, and a ``moneyDigits`` exponent on
   the nine money-bearing messages — an absent exponent refusing that message's money decode.
2. Connection limits: 50/s non-historical + 5/s historical per connection, the 10-second
   heartbeat bound, the one-week historical tick-span cap, and the two-connection topology.
3. Token lifecycle and session duties as schedulable work; session recovery never resubmits.
4. The demoted daily boundary and trendbar basis measured per broker in the profile, never
   hardcoded.
5. Broker identity as deployment configuration — opaque identity, no broker named.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from typing import TypeVar, cast

from qmf.core import (
    Account,
    AccountRole,
    Instant,
    Instrument,
    Money,
    MonotonicReading,
    Price,
    RefusalCategory,
    Result,
    Retryability,
    RoundingMode,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.venue import (
    ACCESS_TOKEN_LIFETIME_CLASS,
    HEARTBEAT_BOUND_SECONDS,
    HISTORICAL_RATE_LIMIT_PER_SECOND,
    HISTORICAL_TICK_SPAN_CAP_MS,
    INVALIDATION_ANCHOR,
    MARKET_DATA_WIRE_SCALE_EXPONENT,
    MONEY_BEARING_MESSAGES,
    NON_HISTORICAL_RATE_LIMIT_PER_SECOND,
    REFRESH_TOKEN_LIFETIME_CLASS,
    SESSION_DUTIES,
    CapabilityFieldName,
    ConnectionEndpoint,
    CTraderAdapter,
    CTraderBrokerConfiguration,
    DecodedExecutionPrice,
    DecodedTimestamp,
    InFlightResolution,
    ProbeCheck,
    ProbeVerdict,
    RatePacer,
    RequestClass,
    SchedulableDuty,
    SessionDuty,
    SessionRecovery,
    SessionTopology,
    SubmissionOutcome,
    TimestampUnit,
    TokenLifecycle,
    UnknownTrigger,
    VenueEnvironment,
    VenueObservationProfile,
    decode_execution_price,
    decode_market_data_price,
    decode_money,
    decode_timestamp,
    tick_span_within_cap,
)
from qmf.venue.observation import MeasuredFact

T = TypeVar("T")

# --- fixtures ---------------------------------------------------------------


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _venue(value: str = "vx-ct") -> VenueId:
    built = VenueId.try_create(value)
    assert is_ok(built)
    return built.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    built = Instrument.try_create(_venue(), symbol)
    assert is_ok(built)
    return built.value


def _account(account_id: str = "acc-1", venue: VenueId | None = None) -> Account:
    built = Account.try_create(
        account_id, venue if venue is not None else _venue(), AccountRole.DEMO
    )
    assert is_ok(built)
    return built.value


def _instant(ns: int) -> Instant:
    built = Instant.try_create(ns)
    assert is_ok(built)
    return built.value


def _mono(ns: int, boot: str = "boot-1") -> MonotonicReading:
    built = MonotonicReading.try_create(ns, boot)
    assert is_ok(built)
    return built.value


def _profile_with(*facts: MeasuredFact) -> VenueObservationProfile:
    """A profile for the shared (venue, account) with the given facts appended in order."""
    venue = _venue()
    account = _account(venue=venue)
    built = VenueObservationProfile.try_create(venue, account)
    assert is_ok(built)
    profile = built.value
    for fact in facts:
        appended = profile.with_fact(fact)
        assert is_ok(appended)
        profile = appended.value
    return profile


def _fact(
    check: ProbeCheck, verdict: ProbeVerdict, measured: dict[str, object] | None = None
) -> MeasuredFact:
    built = MeasuredFact.try_create(
        check, verdict, _instant(1_000), "sess-1", "cred-ref-1", measured=measured
    )
    assert is_ok(built)
    return built.value


def _topology() -> SessionTopology:
    return _ok(SessionTopology.try_create("demo-host", "live-host"))


def _config(profile: VenueObservationProfile) -> CTraderBrokerConfiguration:
    return _ok(CTraderBrokerConfiguration.try_create(profile.venue_id, profile.account, profile))


# === AC1: inbound decode at the named money-path boundary ===================


def test_decode_timestamp_milliseconds_to_utc_nanoseconds() -> None:
    received = _instant(1_700_000_000_500_000_000)
    result = decode_timestamp(1_700_000_000_000, TimestampUnit.MILLISECONDS, received)
    assert is_ok(result)
    decoded = result.value
    assert isinstance(decoded, DecodedTimestamp)
    assert decoded.instant.value_ns == 1_700_000_000_000 * 1_000_000
    assert decoded.raw_value == 1_700_000_000_000
    assert decoded.unit is TimestampUnit.MILLISECONDS
    # Receive-time recording is mandatory — no server clock exists.
    assert decoded.received_at == received


def test_decode_timestamp_named_epoch_exception_units() -> None:
    received = _instant(1_000)
    minutes = decode_timestamp(28_000_000, "minutes", received)
    assert is_ok(minutes)
    assert minutes.value.instant.value_ns == 28_000_000 * 60 * 1_000_000_000
    seconds = decode_timestamp(1_700, "seconds", received)
    assert is_ok(seconds)
    assert seconds.value.instant.value_ns == 1_700 * 1_000_000_000
    days = decode_timestamp(19_000, "days", received)
    assert is_ok(days)
    assert days.value.instant.value_ns == 19_000 * 86_400 * 1_000_000_000


def test_decode_timestamp_requires_receive_instant_no_server_clock() -> None:
    # No server clock exists on the Open API, so a receive instant is mandatory.
    missing = decode_timestamp(1_700_000_000_000, "milliseconds", None)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    assert missing.context["field"] == "received_at"
    not_instant = decode_timestamp(1_700_000_000_000, "milliseconds", 1_700_000_000_000)
    assert is_refusal(not_instant)


def test_decode_timestamp_rejects_bad_unit_and_value() -> None:
    received = _instant(1_000)
    bad_unit = decode_timestamp(1_000, "microseconds", received)
    assert is_refusal(bad_unit)
    assert bad_unit.context["field"] == "unit"
    bad_value = decode_timestamp("1000", "milliseconds", received)
    assert is_refusal(bad_value)
    assert bad_value.context["field"] == "raw_value"
    bool_value = decode_timestamp(True, "milliseconds", received)
    assert is_refusal(bool_value)


def test_decode_timestamp_refuses_out_of_range_instant() -> None:
    received = _instant(1_000)
    # A days value large enough to overflow the int64 nanosecond range is refused, never wrapped.
    overflow = decode_timestamp(10**15, "days", received)
    assert is_refusal(overflow)


def test_decode_market_data_price_uses_wire_scale_verbatim() -> None:
    inst = _instrument()
    result = decode_market_data_price(108_523, inst)
    assert is_ok(result)
    price = result.value
    assert isinstance(price, Price)
    # The 1/100000 wire scale is an exact scale-5 integer, stored verbatim — no float divide.
    assert price.value == 108_523
    assert price.scale == MARKET_DATA_WIRE_SCALE_EXPONENT == 5
    assert price.instrument == inst


def test_decode_market_data_price_rejects_negative_and_non_integer() -> None:
    inst = _instrument()
    negative = decode_market_data_price(-1, inst)
    assert is_refusal(negative)
    assert negative.context["field"] == "wire_value"
    non_int = decode_market_data_price(1.5, inst)
    assert is_refusal(non_int)
    boolean = decode_market_data_price(True, inst)
    assert is_refusal(boolean)


def test_decode_market_data_price_rejects_bad_instrument() -> None:
    bad = decode_market_data_price(100, "EURUSD")
    assert is_refusal(bad)
    assert bad.context["field"] == "instrument"


def test_decode_execution_price_crosses_boundary_retaining_raw_float() -> None:
    inst = _instrument()
    result = decode_execution_price(1.08523, inst, 5, RoundingMode.HALF_EVEN)
    assert is_ok(result)
    decoded = result.value
    assert isinstance(decoded, DecodedExecutionPrice)
    assert decoded.price.value == 108_523
    assert decoded.price.scale == 5
    # The raw double is retained only as integrity-checked provenance.
    assert decoded.raw_double == 1.08523
    assert decoded.digits == 5
    assert decoded.rounding is RoundingMode.HALF_EVEN


def test_decode_execution_price_requires_float_not_integer() -> None:
    inst = _instrument()
    # An integer wire value uses its own decoder; the execution boundary is for raw doubles.
    as_int = decode_execution_price(108_523, inst, 5, RoundingMode.HALF_EVEN)
    assert is_refusal(as_int)
    assert as_int.context["field"] == "raw_double"


def test_decode_execution_price_rejects_bad_digits_rounding_instrument() -> None:
    inst = _instrument()
    bad_digits = decode_execution_price(1.0, inst, -1, RoundingMode.HALF_EVEN)
    assert is_refusal(bad_digits)
    assert bad_digits.context["field"] == "digits"
    non_int_digits = decode_execution_price(1.0, inst, "5", RoundingMode.HALF_EVEN)
    assert is_refusal(non_int_digits)
    bad_rounding = decode_execution_price(1.0, inst, 5, "sideways")
    assert is_refusal(bad_rounding)
    assert bad_rounding.context["field"] == "rounding"
    bad_instrument = decode_execution_price(1.0, "EURUSD", 5, RoundingMode.HALF_EVEN)
    assert is_refusal(bad_instrument)
    assert bad_instrument.context["field"] == "instrument"


def test_decode_execution_price_refuses_nan_and_infinity() -> None:
    inst = _instrument()
    assert is_refusal(decode_execution_price(math.nan, inst, 5, RoundingMode.HALF_EVEN))
    assert is_refusal(decode_execution_price(math.inf, inst, 5, RoundingMode.HALF_EVEN))


def test_money_bearing_messages_are_exactly_nine() -> None:
    assert len(MONEY_BEARING_MESSAGES) == 9


def test_decode_money_accepts_each_of_the_nine_messages() -> None:
    for message in MONEY_BEARING_MESSAGES:
        result = decode_money(message, 12_345, "USD", 2)
        assert is_ok(result), message
        assert isinstance(result.value, Money)
        assert result.value.value == 12_345
        assert result.value.scale == 2
        assert result.value.currency == "USD"


def test_decode_money_absent_exponent_refuses_that_messages_money_decode() -> None:
    # An absent moneyDigits refuses the money decode — never a default to 2.
    result = decode_money("ProtoOADeal", 12_345, "USD", None)
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert result.context["field"] == "money_digits"
    assert result.context["message"] == "ProtoOADeal"


def test_decode_money_rejects_message_outside_the_nine() -> None:
    result = decode_money("ProtoOASpotEvent", 1, "USD", 2)
    assert is_refusal(result)
    assert result.context["field"] == "message"
    not_a_string = decode_money(123, 1, "USD", 2)
    assert is_refusal(not_a_string)


def test_decode_money_rejects_bad_exponent_units_and_currency() -> None:
    bad_exponent = decode_money("ProtoOADeal", 1, "USD", -2)
    assert is_refusal(bad_exponent)
    assert bad_exponent.context["field"] == "money_digits"
    non_int_exponent = decode_money("ProtoOADeal", 1, "USD", "2")
    assert is_refusal(non_int_exponent)
    float_units = decode_money("ProtoOADeal", 1.5, "USD", 2)
    assert is_refusal(float_units)
    assert float_units.context["field"] == "raw_units"
    blank_currency = decode_money("ProtoOADeal", 1, "  ", 2)
    assert is_refusal(blank_currency)


# === AC2: connection limits — pacing, heartbeat bound, span cap, topology ===


def test_rate_pacer_ceilings_match_ratified_facts() -> None:
    non_hist = RatePacer.ceiling_for(RequestClass.NON_HISTORICAL)
    assert is_ok(non_hist)
    assert non_hist.value == NON_HISTORICAL_RATE_LIMIT_PER_SECOND == 50
    hist = RatePacer.ceiling_for("historical")
    assert is_ok(hist)
    assert hist.value == HISTORICAL_RATE_LIMIT_PER_SECOND == 5
    assert is_refusal(RatePacer.ceiling_for("bogus"))
    # A non-string, non-enum request class names no member and is refused.
    assert is_refusal(RatePacer.ceiling_for(123))


def test_rate_pacer_admits_up_to_historical_ceiling_then_refuses() -> None:
    pacer = RatePacer()
    for i in range(HISTORICAL_RATE_LIMIT_PER_SECOND):
        assert is_ok(pacer.admit(RequestClass.HISTORICAL, _mono(i)))
    over = pacer.admit(RequestClass.HISTORICAL, _mono(HISTORICAL_RATE_LIMIT_PER_SECOND))
    assert is_refusal(over)
    assert over.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert over.retryability is Retryability.AFTER_CONDITION
    assert over.context["field"] == "rate_limit"


def test_rate_pacer_budgets_are_separate_per_class() -> None:
    pacer = RatePacer()
    # Exhaust the historical budget; the non-historical budget is untouched.
    for i in range(HISTORICAL_RATE_LIMIT_PER_SECOND):
        assert is_ok(pacer.admit("historical", _mono(i)))
    assert is_refusal(pacer.admit("historical", _mono(100)))
    assert is_ok(pacer.admit("non-historical", _mono(101)))


def test_rate_pacer_non_historical_ceiling_is_fifty() -> None:
    pacer = RatePacer()
    for i in range(NON_HISTORICAL_RATE_LIMIT_PER_SECOND):
        assert is_ok(pacer.admit(RequestClass.NON_HISTORICAL, _mono(i)))
    assert is_refusal(
        pacer.admit(RequestClass.NON_HISTORICAL, _mono(NON_HISTORICAL_RATE_LIMIT_PER_SECOND))
    )


def test_rate_pacer_prunes_the_one_second_window() -> None:
    pacer = RatePacer()
    for i in range(HISTORICAL_RATE_LIMIT_PER_SECOND):
        assert is_ok(pacer.admit("historical", _mono(i)))
    assert is_refusal(pacer.admit("historical", _mono(5)))
    # More than one second later every stale entry is pruned and admission resumes.
    later = _mono(1_000_000_000 + 10)
    assert is_ok(pacer.admit("historical", later))


def test_rate_pacer_resets_window_on_new_boot_epoch() -> None:
    pacer = RatePacer()
    for i in range(HISTORICAL_RATE_LIMIT_PER_SECOND):
        assert is_ok(pacer.admit("historical", _mono(i, boot="boot-1")))
    assert is_refusal(pacer.admit("historical", _mono(6, boot="boot-1")))
    # A monotonic counter has no meaning across boots — a new boot resets every window.
    assert is_ok(pacer.admit("historical", _mono(0, boot="boot-2")))


def test_rate_pacer_rejects_bad_class_and_non_monotonic_now() -> None:
    pacer = RatePacer()
    assert is_refusal(pacer.admit("bogus", _mono(0)))
    not_mono = pacer.admit("historical", _instant(0))
    assert is_refusal(not_mono)
    assert not_mono.context["field"] == "now"


def test_tick_span_within_the_one_week_cap() -> None:
    assert HISTORICAL_TICK_SPAN_CAP_MS == 604_800_000
    assert is_ok(tick_span_within_cap(0, 1_000))
    # Exactly one week is within the cap.
    assert is_ok(tick_span_within_cap(0, HISTORICAL_TICK_SPAN_CAP_MS))


def test_tick_span_over_cap_and_inverted_and_malformed_refused() -> None:
    over = tick_span_within_cap(0, HISTORICAL_TICK_SPAN_CAP_MS + 1)
    assert is_refusal(over)
    assert over.context["cap_ms"] == HISTORICAL_TICK_SPAN_CAP_MS
    inverted = tick_span_within_cap(1_000, 0)
    assert is_refusal(inverted)
    malformed = tick_span_within_cap("0", 1_000)
    assert is_refusal(malformed)


def test_heartbeat_bound_is_ten_seconds() -> None:
    assert HEARTBEAT_BOUND_SECONDS == 10


def test_session_topology_requires_two_connections_separate_hosts() -> None:
    topology = SessionTopology.try_create("demo-host", "live-host")
    assert is_ok(topology)
    value = topology.value
    assert SessionTopology.required_connection_count == 2
    assert value.required_connection_count == 2
    assert value.demo.environment is VenueEnvironment.DEMO
    assert value.live.environment is VenueEnvironment.LIVE
    assert value.demo.host_ref == "demo-host"
    assert isinstance(value.demo, ConnectionEndpoint)


def test_session_topology_rejects_shared_host_and_blank_refs() -> None:
    shared = SessionTopology.try_create("same", "same")
    assert is_refusal(shared)
    assert shared.context["field"] == "host_ref"
    assert is_refusal(SessionTopology.try_create("  ", "live"))
    assert is_refusal(SessionTopology.try_create("demo", ""))


def test_session_topology_endpoint_for_resolves_environments() -> None:
    topology = _topology()
    demo = topology.endpoint_for("demo")
    assert is_ok(demo)
    assert demo.value.host_ref == "demo-host"
    live = topology.endpoint_for(VenueEnvironment.LIVE)
    assert is_ok(live)
    assert live.value.host_ref == "live-host"
    assert is_refusal(topology.endpoint_for("staging"))


# === AC3: token lifecycle and session duties; recovery never resubmits ======


def test_token_lifecycle_declared_class() -> None:
    lifecycle = TokenLifecycle.declared()
    assert lifecycle.access_token_class == ACCESS_TOKEN_LIFETIME_CLASS == "approximately-30-day"
    assert lifecycle.refresh_token_class == REFRESH_TOKEN_LIFETIME_CLASS == "never-expiring"
    assert lifecycle.invalidation_anchor == INVALIDATION_ANCHOR == "ctid-reauthorization"


def test_session_duties_are_the_five_declared_schedulable_duties() -> None:
    duties = {duty.duty for duty in SESSION_DUTIES}
    assert duties == {
        SessionDuty.HEARTBEAT,
        SessionDuty.TOKEN_REFRESH,
        SessionDuty.RECONNECT,
        SessionDuty.GAP_REPLAY,
        SessionDuty.VERIFICATION_MONITOR,
    }


def test_only_heartbeat_carries_the_venue_declared_bound() -> None:
    by_duty = {duty.duty: duty for duty in SESSION_DUTIES}
    heartbeat = by_duty[SessionDuty.HEARTBEAT]
    assert heartbeat.is_venue_bounded is True
    assert heartbeat.venue_bound_seconds == HEARTBEAT_BOUND_SECONDS
    # Every other duty's cadence is a node value under do-not-default — no bound here.
    for duty in SESSION_DUTIES:
        if duty.duty is not SessionDuty.HEARTBEAT:
            assert duty.is_venue_bounded is False
            assert duty.venue_bound_seconds is None


def test_schedulable_duty_is_venue_bounded_property() -> None:
    bounded = SchedulableDuty(duty=SessionDuty.HEARTBEAT, venue_bound_seconds=10)
    unbounded = SchedulableDuty(duty=SessionDuty.RECONNECT)
    assert bounded.is_venue_bounded is True
    assert unbounded.is_venue_bounded is False


def test_session_recovery_never_resubmits_and_marks_in_flight_unknown() -> None:
    recovery = SessionRecovery()
    assert SessionRecovery.resubmits_command is False
    assert recovery.resubmits_command is False
    resolved = recovery.on_disconnect(["cmd-a", "cmd-b"])
    assert is_ok(resolved)
    resolutions = resolved.value
    assert [r.command_id for r in resolutions] == ["cmd-a", "cmd-b"]
    for resolution in resolutions:
        assert isinstance(resolution, InFlightResolution)
        # In-flight becomes UNKNOWN (a state) with the disconnect trigger — never resubmitted.
        assert resolution.outcome is SubmissionOutcome.UNKNOWN
        assert resolution.trigger is UnknownTrigger.DISCONNECT


def test_session_recovery_empty_and_malformed_inputs() -> None:
    recovery = SessionRecovery()
    empty = recovery.on_disconnect([])
    assert is_ok(empty)
    assert empty.value == ()
    not_a_sequence = recovery.on_disconnect("cmd-a")
    assert is_refusal(not_a_sequence)
    blank_id = recovery.on_disconnect(["cmd-a", "  "])
    assert is_refusal(blank_id)
    non_str_id = recovery.on_disconnect([123])
    assert is_refusal(non_str_id)


# === AC4: measured-per-broker facts, never hardcoded ========================


def test_broker_config_requires_matching_profile() -> None:
    venue = _venue()
    account = _account(venue=venue)
    profile = _profile_with()
    config = CTraderBrokerConfiguration.try_create(venue, account, profile)
    assert is_ok(config)
    assert config.value.venue_id == venue
    assert config.value.account == account


def test_broker_config_rejects_mismatched_nouns_and_profile() -> None:
    venue = _venue()
    other_venue = _venue("vx-other")
    account = _account(venue=venue)
    profile = _profile_with()
    # account not belonging to the venue
    foreign_account = _account("acc-2", other_venue)
    assert is_refusal(CTraderBrokerConfiguration.try_create(venue, foreign_account, profile))
    # profile for a different (venue, account)
    other_profile = _ok(
        VenueObservationProfile.try_create(other_venue, _account("acc-2", other_venue))
    )
    assert is_refusal(CTraderBrokerConfiguration.try_create(venue, account, other_profile))
    # malformed nouns
    assert is_refusal(CTraderBrokerConfiguration.try_create("vx", account, profile))
    assert is_refusal(CTraderBrokerConfiguration.try_create(venue, "acc", profile))
    assert is_refusal(CTraderBrokerConfiguration.try_create(venue, account, object()))


def test_daily_boundary_verify_or_refuse_never_hardcoded() -> None:
    # Unmeasured boundary: venue daily bars stay ungoverned (an unavailable-dependency refusal).
    unmeasured = _profile_with()
    config = _config(unmeasured)
    refused = config.require_daily_boundary()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert is_refusal(config.daily_boundary_calendar("v1", "2026a"))
    # Measured and verified: the boundary governs and mints a calendar identity from the
    # measured minute-of-day — never the demoted 17:00-New-York claim.
    measured = _profile_with(
        _fact(ProbeCheck.DAILY_BOUNDARY, ProbeVerdict.VERIFIED, {"utc_minute_of_day": 1020})
    )
    config2 = _config(measured)
    assert is_ok(config2.require_daily_boundary())
    calendar = config2.daily_boundary_calendar("v1", "2026a")
    assert is_ok(calendar)
    assert "1020" in calendar.value.rule_set
    assert "17:00" not in calendar.value.rule_set


def test_trendbar_price_basis_read_from_profile_never_hardcoded() -> None:
    # A verified bar-basis fact returns whatever quote side was reconciled — not a hardcoded BID.
    verified = _profile_with(
        _fact(ProbeCheck.BAR_BASIS, ProbeVerdict.VERIFIED, {"quote_type": "ask"})
    )
    config = _config(verified)
    basis = config.trendbar_price_basis()
    assert is_ok(basis)
    assert basis.value == "ask"


def test_trendbar_price_basis_refuses_when_unverified() -> None:
    refused_profile = _profile_with(_fact(ProbeCheck.BAR_BASIS, ProbeVerdict.REFUSED))
    config = _config(refused_profile)
    refused = config.trendbar_price_basis()
    assert is_refusal(refused)
    # No profile fact at all is likewise a refusal, never a default.
    empty = _profile_with()
    config2 = _config(empty)
    assert is_refusal(config2.trendbar_price_basis())


# === AC5: broker identity as deployment configuration, no broker named ======


def test_deployment_identity_is_opaque_and_names_no_broker() -> None:
    venue = _venue("vx-deploy")
    account = _account("acc-9", venue)
    profile = _ok(VenueObservationProfile.try_create(venue, account))
    config = _config(profile)
    identity = config.deployment_identity()
    assert identity == {"venue_id": "vx-deploy", "account_id": "acc-9"}
    # The identity is opaque tokens only — no broker name anywhere in the surface.
    assert set(identity) == {"venue_id", "account_id"}


def test_ctrader_adapter_assembles_and_stays_venue_blind() -> None:
    venue = _venue()
    account = _account(venue=venue)
    profile = _ok(VenueObservationProfile.try_create(venue, account))
    config = _config(profile)
    topology = _topology()
    adapter = CTraderAdapter.try_create(config, topology)
    assert is_ok(adapter)
    value = adapter.value
    assert value.token_lifecycle == TokenLifecycle.declared()
    assert value.session_duties == SESSION_DUTIES
    assert isinstance(value.recovery, SessionRecovery)
    assert isinstance(CTraderAdapter.new_pacer(), RatePacer)


def test_ctrader_adapter_accepts_explicit_token_lifecycle() -> None:
    venue = _venue()
    account = _account(venue=venue)
    profile = _ok(VenueObservationProfile.try_create(venue, account))
    config = _config(profile)
    topology = _topology()
    custom = dataclasses.replace(
        TokenLifecycle.declared(), access_token_class="approximately-30-day"
    )
    adapter = CTraderAdapter.try_create(config, topology, custom)
    assert is_ok(adapter)
    assert adapter.value.token_lifecycle == custom


def test_ctrader_adapter_rejects_bad_components() -> None:
    venue = _venue()
    account = _account(venue=venue)
    profile = _ok(VenueObservationProfile.try_create(venue, account))
    config = _config(profile)
    topology = _topology()
    assert is_refusal(CTraderAdapter.try_create(object(), topology))
    assert is_refusal(CTraderAdapter.try_create(config, object()))
    assert is_refusal(CTraderAdapter.try_create(config, topology, object()))


def test_static_capability_facts_are_platform_facts_not_broker_facts() -> None:
    facts = CTraderAdapter.static_capability_facts()
    rate = cast("Mapping[str, object]", facts[CapabilityFieldName.RATE_LIMITS])
    assert rate["non_historical_per_second"] == 50
    assert rate["historical_per_second"] == 5
    span = cast("Mapping[str, object]", facts[CapabilityFieldName.SPAN_CAPS_AND_PAGING])
    assert span["historical_tick_span_cap_ms"] == HISTORICAL_TICK_SPAN_CAP_MS
    token = cast("Mapping[str, object]", facts[CapabilityFieldName.TOKEN_LIFECYCLE_CLASS])
    assert token["access_token"] == ACCESS_TOKEN_LIFETIME_CLASS
    # No server clock exists on the Open API — receive-time recording is mandatory.
    assert facts[CapabilityFieldName.SERVER_CLOCK_AVAILABILITY] is False
