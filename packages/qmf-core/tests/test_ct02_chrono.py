"""Executable CT-02 contract test, owned by qmf-core.

Verifies exact time: int64 UTC-nanosecond Instants with checked arithmetic (no
silent wrap), the CivilDate/TradingDate split with in-band calendar identity and
cross-calendar refusal, causality on instants only (refusing at equal instants),
the type-separated wall/monotonic kinds behind an injected Clock protocol, the
tzdb-pin verification seam, per-writer strictly-increasing ordering keys with no
causal meaning, and display-only labelled rendering excluded from identity
(CT-02; DEC-0022, DEC-0106, DEC-0108, DEC-0109). Written to exercise 100% branch
coverage of ``qmf.core.chrono`` (AR-20).
"""

from __future__ import annotations

import dataclasses

import pytest
from qmf.core.chrono import (
    CONTRACT_FORMAT_VERSION,
    CalendarIdentity,
    CivilDate,
    Clock,
    ClockKind,
    DataDrivenClock,
    DisplayTime,
    Duration,
    Instant,
    Interval,
    MonotonicReading,
    OrderingKey,
    SessionWindow,
    TemporalOrder,
    TradingDate,
    WriterId,
    WriterSequencer,
    compare_causal,
    render_utc_iso8601,
    verify_tzdb_pin,
)
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_ok, is_refusal

_INT64_MIN = -(2**63)
_INT64_MAX = (2**63) - 1


# --- helpers ----------------------------------------------------------------


def _instant(value_ns: int) -> Instant:
    result = Instant.try_create(value_ns)
    assert is_ok(result)
    return result.value


def _duration(value_ns: int) -> Duration:
    result = Duration.try_create(value_ns)
    assert is_ok(result)
    return result.value


def _calendar(version: str = "v3") -> CalendarIdentity:
    result = CalendarIdentity.try_create("forex-17NY", version, "2025b")
    assert is_ok(result)
    return result.value


def _civil(year: int = 2026, month: int = 8, day: int = 21) -> CivilDate:
    result = CivilDate.try_create(year, month, day)
    assert is_ok(result)
    return result.value


def _writer(stream: str = "ticks", boot: str = "boot-1") -> WriterId:
    result = WriterId.try_create("vps-1", "ingest", stream, boot)
    assert is_ok(result)
    return result.value


def _monotonic(value_ns: int, boot: str = "boot-1") -> MonotonicReading:
    result = MonotonicReading.try_create(value_ns, boot)
    assert is_ok(result)
    return result.value


# --- instants: range, zero, checked arithmetic (FM-2) -----------------------


def test_instant_zero_is_valid_not_a_sentinel() -> None:
    epoch = _instant(0)
    assert epoch.value_ns == 0
    assert epoch.kind is ClockKind.WALL


def test_absent_time_is_an_absent_field_never_zero() -> None:
    # The discipline: an absent time is None, and Instant(0) is a real instant, so
    # the two are never confused.
    absent: Instant | None = None
    present = _instant(0)
    assert absent is None
    assert present is not None
    assert present.value_ns == 0


def test_instant_accepts_the_full_int64_range() -> None:
    assert is_ok(Instant.try_create(_INT64_MIN))
    assert is_ok(Instant.try_create(_INT64_MAX))


def test_instant_refuses_out_of_range_and_non_integers() -> None:
    for bad in (_INT64_MIN - 1, _INT64_MAX + 1, True, 1.0, "0", None):
        refusal = Instant.try_create(bad)
        assert is_refusal(refusal)
        assert refusal.category is RefusalCategory.INVALID_INPUT
        assert refusal.retryability is Retryability.NO
        assert refusal.context["field"] == "value_ns"


def test_instant_add_duration_success_and_overflow_refusal() -> None:
    one_second = _duration(1_000_000_000)
    advanced = _instant(0).add_duration(one_second)
    assert is_ok(advanced)
    assert advanced.value.value_ns == 1_000_000_000

    # Positive overflow at the ceiling and negative overflow at the floor are both
    # refused, never wrapped.
    over = _instant(_INT64_MAX).add_duration(one_second)
    assert is_refusal(over)
    assert over.category is RefusalCategory.INVALID_INPUT
    under = _instant(_INT64_MIN).add_duration(_duration(-1))
    assert is_refusal(under)

    wrong = _instant(0).add_duration(_instant(1))
    assert is_refusal(wrong)
    assert wrong.context["field"] == "duration"


def test_instant_difference_is_an_evidence_span_and_checks_overflow() -> None:
    span = _instant(5).difference(_instant(2))
    assert is_ok(span)
    assert span.value.value_ns == 3

    overflow = _instant(_INT64_MAX).difference(_instant(_INT64_MIN))
    assert is_refusal(overflow)
    assert overflow.category is RefusalCategory.INVALID_INPUT

    wrong = _instant(5).difference("2")
    assert is_refusal(wrong)
    assert wrong.context["field"] == "earlier"


def test_instant_fp1_identity_is_the_nanosecond_count() -> None:
    content = _instant(1234).fp1_identity()
    assert content == {
        "class": "instant",
        "value_ns": 1234,
        "format_version": CONTRACT_FORMAT_VERSION,
    }


def test_instant_is_frozen() -> None:
    epoch = _instant(0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        epoch.value_ns = 1  # type: ignore[misc]


# --- durations --------------------------------------------------------------


def test_duration_construction_and_refusal() -> None:
    assert is_ok(Duration.try_create(-5))
    bad = Duration.try_create(1.5)
    assert is_refusal(bad)
    assert bad.context["field"] == "value_ns"


def test_duration_add_and_subtract_promote_and_check() -> None:
    added = _duration(10).add(_duration(5))
    assert is_ok(added)
    assert added.value.value_ns == 15

    subtracted = _duration(10).subtract(_duration(5))
    assert is_ok(subtracted)
    assert subtracted.value.value_ns == 5

    over = _duration(_INT64_MAX).add(_duration(1))
    assert is_refusal(over)
    assert over.category is RefusalCategory.INVALID_INPUT

    under = _duration(_INT64_MIN).subtract(_duration(1))
    assert is_refusal(under)

    wrong = _duration(1).add("nope")
    assert is_refusal(wrong)
    assert wrong.context["field"] == "other"


def test_duration_negate_checks_the_int64_floor() -> None:
    negated = _duration(5).negate()
    assert is_ok(negated)
    assert negated.value.value_ns == -5

    overflow = _duration(_INT64_MIN).negate()
    assert is_refusal(overflow)
    assert overflow.category is RefusalCategory.INVALID_INPUT


def test_duration_fp1_identity() -> None:
    assert _duration(7).fp1_identity()["value_ns"] == 7


# --- intervals --------------------------------------------------------------


def test_interval_construction_validates_bounds() -> None:
    assert is_ok(Interval.try_create(_instant(0), _instant(0)))  # empty is allowed
    assert is_ok(Interval.try_create(_instant(0), _instant(10)))

    assert is_refusal(Interval.try_create("0", _instant(10)))
    assert is_refusal(Interval.try_create(_instant(0), "10"))

    inverted = Interval.try_create(_instant(10), _instant(0))
    assert is_refusal(inverted)
    assert inverted.context["field"] == "start"


def test_interval_contains_is_half_open() -> None:
    result = Interval.try_create(_instant(0), _instant(10))
    assert is_ok(result)
    interval = result.value

    inside = interval.contains(_instant(0))
    assert is_ok(inside) and inside.value is True
    excluded_end = interval.contains(_instant(10))
    assert is_ok(excluded_end) and excluded_end.value is False
    outside = interval.contains(_instant(20))
    assert is_ok(outside) and outside.value is False

    wrong = interval.contains("5")
    assert is_refusal(wrong)


def test_interval_overlaps() -> None:
    a = Interval.try_create(_instant(0), _instant(10))
    b = Interval.try_create(_instant(5), _instant(15))
    c = Interval.try_create(_instant(10), _instant(20))
    assert is_ok(a) and is_ok(b) and is_ok(c)

    overlap = a.value.overlaps(b.value)
    assert is_ok(overlap) and overlap.value is True
    touching = a.value.overlaps(c.value)  # half-open: [0,10) and [10,20) do not overlap
    assert is_ok(touching) and touching.value is False

    wrong = a.value.overlaps("b")
    assert is_refusal(wrong)


def test_interval_fp1_identity() -> None:
    result = Interval.try_create(_instant(1), _instant(2))
    assert is_ok(result)
    content = result.value.fp1_identity()
    assert content["start_ns"] == 1 and content["end_ns"] == 2


# --- civil dates ------------------------------------------------------------


def test_civil_date_validates_real_dates() -> None:
    assert is_ok(CivilDate.try_create(2026, 8, 21))

    bad_year = CivilDate.try_create(True, 8, 21)
    assert is_refusal(bad_year) and bad_year.context["field"] == "year"
    bad_month = CivilDate.try_create(2026, "8", 21)
    assert is_refusal(bad_month) and bad_month.context["field"] == "month"
    bad_day = CivilDate.try_create(2026, 8, 1.0)
    assert is_refusal(bad_day) and bad_day.context["field"] == "day"

    not_a_date = CivilDate.try_create(2026, 2, 30)
    assert is_refusal(not_a_date) and not_a_date.context["field"] == "date"


def test_civil_date_isoformat_is_display() -> None:
    assert _civil(2026, 8, 5).isoformat() == "2026-08-05"


def test_civil_date_is_a_distinct_type_from_trading_date() -> None:
    assert CivilDate is not TradingDate
    assert not isinstance(_civil(), TradingDate)


# --- calendar identity ------------------------------------------------------


def test_calendar_identity_requires_all_three_parts() -> None:
    assert is_ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025b"))

    blank_rule = CalendarIdentity.try_create("  ", "v3", "2025b")
    assert is_refusal(blank_rule) and blank_rule.context["field"] == "rule_set"
    blank_version = CalendarIdentity.try_create("forex-17NY", "", "2025b")
    assert is_refusal(blank_version) and blank_version.context["field"] == "rule_set_version"
    blank_tzdata = CalendarIdentity.try_create("forex-17NY", "v3", None)
    assert is_refusal(blank_tzdata) and blank_tzdata.context["field"] == "tzdata_version"


def test_calendar_identity_fp1_is_rule_set_plus_tzdata_only() -> None:
    content = _calendar().fp1_identity()
    assert content == {
        "class": "calendar-identity",
        "rule_set": "forex-17NY",
        "rule_set_version": "v3",
        "tzdata_version": "2025b",
        "format_version": CONTRACT_FORMAT_VERSION,
    }


# --- trading dates: in-band identity, cross-calendar refusal (FM-3) ----------


def test_trading_date_construction_validates_parts() -> None:
    assert is_ok(TradingDate.try_create(_calendar(), _civil()))

    bad_cal = TradingDate.try_create("forex", _civil())
    assert is_refusal(bad_cal) and bad_cal.context["field"] == "calendar"
    bad_value = TradingDate.try_create(_calendar(), "2026-08-21")
    assert is_refusal(bad_value) and bad_value.context["field"] == "date_value"


def test_trading_date_compares_only_within_one_calendar() -> None:
    cal = _calendar()
    early = TradingDate.try_create(cal, _civil(2026, 8, 20))
    late = TradingDate.try_create(cal, _civil(2026, 8, 21))
    assert is_ok(early) and is_ok(late)

    before = early.value.compare(late.value)
    assert is_ok(before) and before.value is TemporalOrder.BEFORE
    after = late.value.compare(early.value)
    assert is_ok(after) and after.value is TemporalOrder.AFTER
    equal = early.value.compare(early.value)
    assert is_ok(equal) and equal.value is TemporalOrder.EQUAL

    wrong = early.value.compare("2026-08-20")
    assert is_refusal(wrong) and wrong.context["field"] == "other"


def test_trading_date_cross_calendar_comparison_refuses() -> None:
    v3 = TradingDate.try_create(_calendar("v3"), _civil())
    v4 = TradingDate.try_create(_calendar("v4"), _civil())
    assert is_ok(v3) and is_ok(v4)

    refusal = v3.value.compare(v4.value)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "calendar"


def test_trading_date_equals_within_and_across_calendars() -> None:
    cal = _calendar()
    a = TradingDate.try_create(cal, _civil(2026, 8, 21))
    b = TradingDate.try_create(cal, _civil(2026, 8, 21))
    c = TradingDate.try_create(cal, _civil(2026, 8, 22))
    assert is_ok(a) and is_ok(b) and is_ok(c)

    same = a.value.equals(b.value)
    assert is_ok(same) and same.value is True
    different = a.value.equals(c.value)
    assert is_ok(different) and different.value is False

    cross = a.value.equals(TradingDate.try_create(_calendar("v4"), _civil(2026, 8, 21)).value)  # type: ignore[union-attr]
    assert is_refusal(cross)


def test_trading_date_fp1_carries_calendar_identity() -> None:
    result = TradingDate.try_create(_calendar(), _civil(2026, 8, 21))
    assert is_ok(result)
    content = result.value.fp1_identity()
    assert content["class"] == "trading-date"
    assert content["calendar"]["rule_set"] == "forex-17NY"  # type: ignore[index]
    assert content["date_value"] == "2026-08-21"


# --- monotonic readings: type-separated, boot-scoped (AR-16) ----------------


def test_monotonic_reading_is_not_an_instant() -> None:
    reading = _monotonic(100)
    assert isinstance(reading, MonotonicReading)
    assert not isinstance(reading, Instant)
    assert reading.kind is ClockKind.MONOTONIC


def test_monotonic_reading_construction_refusals() -> None:
    bad_value = MonotonicReading.try_create(1.0, "boot-1")
    assert is_refusal(bad_value) and bad_value.context["field"] == "value_ns"
    blank_boot = MonotonicReading.try_create(100, "  ")
    assert is_refusal(blank_boot) and blank_boot.context["field"] == "boot_epoch_id"


def test_monotonic_elapsed_requires_one_boot_and_checks_overflow() -> None:
    start = _monotonic(10, "boot-1")
    end = _monotonic(42, "boot-1")
    elapsed = end.elapsed_since(start)
    assert is_ok(elapsed) and elapsed.value.value_ns == 32

    cross_boot = end.elapsed_since(_monotonic(10, "boot-2"))
    assert is_refusal(cross_boot) and cross_boot.context["field"] == "boot_epoch_id"

    overflow = _monotonic(_INT64_MAX, "boot-1").elapsed_since(_monotonic(_INT64_MIN, "boot-1"))
    assert is_refusal(overflow) and overflow.category is RefusalCategory.INVALID_INPUT

    wrong = end.elapsed_since("start")
    assert is_refusal(wrong) and wrong.context["field"] == "earlier"


# --- the injected Clock seam ------------------------------------------------


def test_data_driven_clock_conforms_to_the_clock_protocol() -> None:
    clock = DataDrivenClock(
        boot_epoch_id="boot-1",
        wall_instants=[_instant(0), _instant(1)],
        monotonic_ns=[5, 9],
    )
    assert isinstance(clock, Clock)
    typed: Clock = clock  # structural conformance, checked by the type checker
    assert typed.boot_epoch_id == "boot-1"


def test_data_driven_clock_replays_wall_and_monotonic() -> None:
    clock = DataDrivenClock(
        boot_epoch_id="boot-1",
        wall_instants=[_instant(0), _instant(1_000)],
        monotonic_ns=[5, 9],
    )
    assert clock.wall_now().value_ns == 0
    assert clock.wall_now().value_ns == 1_000

    first = clock.monotonic_now()
    assert isinstance(first, MonotonicReading)
    assert first.value_ns == 5 and first.boot_epoch_id == "boot-1"
    assert clock.monotonic_now().value_ns == 9


def test_data_driven_clock_raises_when_its_script_is_exhausted() -> None:
    clock = DataDrivenClock(boot_epoch_id="boot-1", wall_instants=[_instant(0)], monotonic_ns=[5])
    assert clock.wall_now().value_ns == 0
    with pytest.raises(LookupError):
        clock.wall_now()

    assert clock.monotonic_now().value_ns == 5
    with pytest.raises(LookupError):
        clock.monotonic_now()


# --- writers, sequences, ordering keys (no causal meaning) ------------------


def test_writer_id_requires_every_part() -> None:
    assert is_ok(WriterId.try_create("vps-1", "ingest", "ticks", "boot-1"))

    for field, args in (
        ("machine", ("", "ingest", "ticks", "boot-1")),
        ("role", ("vps-1", " ", "ticks", "boot-1")),
        ("stream", ("vps-1", "ingest", None, "boot-1")),
        ("boot_epoch_id", ("vps-1", "ingest", "ticks", "")),
    ):
        refusal = WriterId.try_create(*args)
        assert is_refusal(refusal)
        assert refusal.context["field"] == field


def test_ordering_key_construction_and_sequence_validation() -> None:
    assert is_ok(OrderingKey.try_create(_instant(0), _writer(), 0))

    bad_instant = OrderingKey.try_create("0", _writer(), 0)
    assert is_refusal(bad_instant) and bad_instant.context["field"] == "instant"
    bad_writer = OrderingKey.try_create(_instant(0), "writer", 0)
    assert is_refusal(bad_writer) and bad_writer.context["field"] == "writer"
    non_int_seq = OrderingKey.try_create(_instant(0), _writer(), 1.5)
    assert is_refusal(non_int_seq) and non_int_seq.context["field"] == "sequence"
    negative_seq = OrderingKey.try_create(_instant(0), _writer(), -1)
    assert is_refusal(negative_seq) and negative_seq.context["field"] == "sequence"


def test_ordering_key_total_order_has_no_causal_meaning() -> None:
    early = OrderingKey.try_create(_instant(0), _writer(), 0)
    late = OrderingKey.try_create(_instant(0), _writer(), 1)  # same instant, later sequence
    across_instant = OrderingKey.try_create(_instant(5), _writer(), 0)
    assert is_ok(early) and is_ok(late) and is_ok(across_instant)

    by_sequence = early.value.precedes(late.value)
    assert is_ok(by_sequence) and by_sequence.value is True
    reverse = late.value.precedes(early.value)
    assert is_ok(reverse) and reverse.value is False
    by_instant = early.value.precedes(across_instant.value)
    assert is_ok(by_instant) and by_instant.value is True

    wrong = early.value.precedes("late")
    assert is_refusal(wrong)


def test_writer_sequencer_mints_strictly_increasing_sequences() -> None:
    sequencer = WriterSequencer(_writer(), start=7)
    assert sequencer.writer.stream == "ticks"
    assert sequencer.next_sequence == 7

    first = sequencer.mint(_instant(0))
    second = sequencer.mint(_instant(0))  # same instant, strictly-increasing sequence
    third = sequencer.mint(_instant(1_000))
    assert first.sequence == 7
    assert second.sequence == 8
    assert third.sequence == 9
    assert second.sequence > first.sequence
    assert sequencer.next_sequence == 10


# --- session windows --------------------------------------------------------


def test_session_window_construction_and_containment() -> None:
    ok = SessionWindow.try_create(_instant(0), _instant(100), "America/New_York")
    assert is_ok(ok)
    window = ok.value

    inside = window.contains(_instant(50))
    assert is_ok(inside) and inside.value is True
    at_close = window.contains(_instant(100))
    assert is_ok(at_close) and at_close.value is False
    wrong = window.contains("50")
    assert is_refusal(wrong)

    assert is_refusal(SessionWindow.try_create("0", _instant(100), "UTC"))
    assert is_refusal(SessionWindow.try_create(_instant(0), "100", "UTC"))
    inverted = SessionWindow.try_create(_instant(100), _instant(0), "UTC")
    assert is_refusal(inverted) and inverted.context["field"] == "open_instant"
    blank_zone = SessionWindow.try_create(_instant(0), _instant(100), " ")
    assert is_refusal(blank_zone) and blank_zone.context["field"] == "zone"


# --- causality: instants only, refuse at equal instants ---------------------


def test_compare_causal_reads_instants_only() -> None:
    before = compare_causal(_instant(1), _instant(2))
    assert is_ok(before) and before.value is TemporalOrder.BEFORE
    after = compare_causal(_instant(2), _instant(1))
    assert is_ok(after) and after.value is TemporalOrder.AFTER


def test_compare_causal_refuses_at_equal_instants() -> None:
    concurrent = compare_causal(_instant(5), _instant(5))
    assert is_refusal(concurrent)
    assert concurrent.category is RefusalCategory.POLICY_REJECTION
    assert concurrent.context["field"] == "instant"


def test_compare_causal_refuses_non_instants() -> None:
    left = compare_causal("1", _instant(2))
    assert is_refusal(left) and left.context["field"] == "earlier"
    right = compare_causal(_instant(1), "2")
    assert is_refusal(right) and right.context["field"] == "later"


# --- display rendering: labelled, never identity ----------------------------


def test_render_utc_iso8601_is_labelled_and_excludes_identity() -> None:
    epoch = render_utc_iso8601(_instant(0))
    assert is_ok(epoch)
    assert epoch.value == DisplayTime(text="1970-01-01T00:00:00.000000000Z", zone="UTC")

    with_nanos = render_utc_iso8601(_instant(1_234_000_005))
    assert is_ok(with_nanos)
    assert with_nanos.value.text == "1970-01-01T00:00:01.234000005Z"

    before_epoch = render_utc_iso8601(_instant(-1))
    assert is_ok(before_epoch)
    assert before_epoch.value.text == "1969-12-31T23:59:59.999999999Z"

    # A DisplayTime is display-only: it carries no fp1_identity (excluded from identity).
    assert not hasattr(epoch.value, "fp1_identity")

    wrong = render_utc_iso8601("0")
    assert is_refusal(wrong) and wrong.context["field"] == "instant"


# --- tzdb pin verification seam (FM-5) --------------------------------------


def test_verify_tzdb_pin_matches_and_refuses_mismatch() -> None:
    match = verify_tzdb_pin("2025b", "2025b")
    assert is_ok(match) and match.value == "2025b"

    mismatch = verify_tzdb_pin("2025b", "2024a")
    assert is_refusal(mismatch)
    assert mismatch.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert mismatch.context["pinned"] == "2025b"
    assert mismatch.context["resolved"] == "2024a"


def test_verify_tzdb_pin_refuses_blank_versions() -> None:
    blank_pin = verify_tzdb_pin("", "2025b")
    assert is_refusal(blank_pin) and blank_pin.context["field"] == "pinned_version"
    blank_resolved = verify_tzdb_pin("2025b", None)
    assert is_refusal(blank_resolved) and blank_resolved.context["field"] == "resolved_version"


# --- refusals are returned, never raised ------------------------------------


def test_every_refusal_is_a_returned_value() -> None:
    refusal = Instant.try_create("not-a-number")
    assert isinstance(refusal, TypedRefusal)
    assert not is_ok(refusal)
