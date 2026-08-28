"""Epic 1 — CT-02 exact time/calendars/injected Clock (Story 1.5, chrono.py). L1.

Independent, requirements-derived assertions (E1-U29..U46), incl. mutmut pins
(E1-U30 int64 boundary, E1-U36 equal-instant causality, E1-U41 exhaustion,
E1-U42 advance-per-call, E1-U43 WriterSequencer, E1-U44 tzdb pin). Authored from
CT-02 (docs/contracts/ct-02-time-calendar.yaml), FM-2/FM-3/FM-5, epics.md Story 1.5.
Source code is read-only evidence.
"""

from __future__ import annotations

import pytest
from qmf.core.chrono import (
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
    TemporalOrder,
    TradingDate,
    WriterId,
    WriterSequencer,
    compare_causal,
    render_utc_iso8601,
    verify_tzdb_pin,
)
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal

# The int64 nanosecond range IS the representable instant range 1677..2262 (CT-02).
INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


def _ok(result: Result[object]) -> object:
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def _refusal(result: Result[object]) -> TypedRefusal:
    assert is_refusal(result), f"expected a TypedRefusal, got {result!r}"
    return result


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _calendar(tz: str = "2025a", rule: str = "forex-17NY", ver: str = "v3") -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create(rule, ver, tz))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("machine-1", "recorder", "stream-a", "boot-1"))


# E1-U29 -----------------------------------------------------------------------
def test_e1_u29_instant_is_int64_utc_ns_zero_is_valid() -> None:
    """CT-02 / DEC-0106: Instant is an int64 UTC-ns count since the Unix epoch;
    instant 0 is a valid instant."""
    zero = _ok(Instant.try_create(0))
    assert zero.value_ns == 0
    assert _ok(Instant.try_create(1_700_000_000_000_000_000)).value_ns == 1_700_000_000_000_000_000


# E1-U30 (mutmut pin chrono.py:171) --------------------------------------------
def test_e1_u30_int64_min_max_boundary_accepted_one_beyond_refused() -> None:
    """CT-02 FM-2 (pin chrono.py:171): int64 min/max accepted at the edge; one ns
    beyond the range -> invalid input refusal, never a wrap."""
    assert _ok(Instant.try_create(INT64_MIN)).value_ns == INT64_MIN
    assert _ok(Instant.try_create(INT64_MAX)).value_ns == INT64_MAX
    below = _refusal(Instant.try_create(INT64_MIN - 1))
    assert below.category is RefusalCategory.INVALID_INPUT
    above = _refusal(Instant.try_create(INT64_MAX + 1))
    assert above.category is RefusalCategory.INVALID_INPUT
    # Arithmetic overflow is refused, never wrapped.
    dur = _ok(Duration.try_create(1))
    assert is_refusal(_ok(Instant.try_create(INT64_MAX)).add_duration(dur))


# E1-U31 -----------------------------------------------------------------------
def test_e1_u31_absent_time_is_absent_field_not_zero_sentinel() -> None:
    """CT-02 / DEC-0106: an absent time is an absent field, never a zero sentinel —
    Instant(0) is a real instant, and None is not a valid instant."""
    assert _ok(Instant.try_create(0)).value_ns == 0  # 0 is a value, not "absent"
    assert is_refusal(Instant.try_create(None))  # absence is not an Instant


# E1-U32 -----------------------------------------------------------------------
def test_e1_u32_civil_date_and_trading_date_are_distinct_types() -> None:
    """CT-02: CivilDate and TradingDate are distinct types."""
    civil = _ok(CivilDate.try_create(2026, 1, 2))
    trading = _ok(TradingDate.try_create(_calendar(), civil))
    assert type(civil) is not type(trading)
    assert not isinstance(civil, TradingDate)
    assert not isinstance(trading, CivilDate)


# E1-U33 -----------------------------------------------------------------------
def test_e1_u33_trading_date_carries_calendar_identity_equality_within_calendar() -> None:
    """CT-02: TradingDate carries calendar identity + version in-band; equality holds
    only within one calendar identity."""
    civil = _ok(CivilDate.try_create(2026, 1, 2))
    cal = _calendar()
    td1 = _ok(TradingDate.try_create(cal, civil))
    td2 = _ok(TradingDate.try_create(cal, civil))
    assert _ok(td1.equals(td2)) is True
    assert isinstance(td1.calendar, CalendarIdentity)
    assert td1.calendar.rule_set_version == "v3"
    assert td1.calendar.tzdata_version == "2025a"


# E1-U34 -----------------------------------------------------------------------
def test_e1_u34_cross_calendar_comparison_is_refusal() -> None:
    """CT-02 FM-3: a cross-calendar TradingDate comparison -> typed refusal (category
    not over-fit; spine leaves it open)."""
    civil = _ok(CivilDate.try_create(2026, 1, 2))
    td_a = _ok(TradingDate.try_create(_calendar(tz="2025a"), civil))
    td_b = _ok(TradingDate.try_create(_calendar(tz="2025b"), civil))
    r = _refusal(td_a.compare(td_b))
    assert r.context["field"] == "calendar"
    assert is_refusal(td_a.equals(td_b))  # cross-calendar equality is a refusal, not False


# E1-U35 -----------------------------------------------------------------------
def test_e1_u35_trading_date_not_derived_from_instant_not_causality_proxy() -> None:
    """CT-02: a TradingDate is never derived by formatting an instant, and is never a
    causality proxy — there is deliberately no from_instant constructor."""
    assert not hasattr(TradingDate, "from_instant")
    # causality compares Instants only; a TradingDate is not an accepted operand.
    civil = _ok(CivilDate.try_create(2026, 1, 2))
    td = _ok(TradingDate.try_create(_calendar(), civil))
    assert is_refusal(compare_causal(td, td))


# E1-U36 (mutmut pin chrono.py:995) --------------------------------------------
def test_e1_u36_compare_causal_equal_instants_refuses_bad_input_named() -> None:
    """CT-02 / DEC-0106 (pin chrono.py:995): compare_causal on equal instants ->
    refusal (concurrent; no tie-break, carrying the equal instant); a non-Instant
    input -> invalid input refusal with the exact field."""
    before = compare_causal(_instant(10), _instant(20))
    assert _ok(before) is TemporalOrder.BEFORE
    after = compare_causal(_instant(20), _instant(10))
    assert _ok(after) is TemporalOrder.AFTER
    equal = _refusal(compare_causal(_instant(42), _instant(42)))
    assert "tie-break" in equal.context["reason"]
    assert equal.context["instant"] == 42  # kills the instant=None mutant
    bad = _refusal(compare_causal("not-an-instant", _instant(1)))
    assert bad.category is RefusalCategory.INVALID_INPUT
    assert bad.context["field"] == "earlier"


# E1-U37 -----------------------------------------------------------------------
def test_e1_u37_duration_is_signed_int64_freely_storable() -> None:
    """CT-02: Duration is a signed int64 ns quantity, clock-agnostic and freely
    storable; overflow on arithmetic is refused."""
    neg = _ok(Duration.try_create(-5_000))
    assert neg.value_ns == -5_000
    assert _ok(Duration.try_create(INT64_MAX)).value_ns == INT64_MAX
    # signed negation of int64-min has no counterpart -> refused, never wrapped.
    assert is_refusal(_ok(Duration.try_create(INT64_MIN)).negate())


# E1-U38 -----------------------------------------------------------------------
def test_e1_u38_interval_half_open_contains_overlaps_end_exclusive() -> None:
    """CT-02: Interval is half-open [start, end); contains/overlaps correct at both
    boundaries (end exclusive)."""
    iv = _ok(Interval.try_create(_instant(10), _instant(20)))
    assert _ok(iv.contains(_instant(10))) is True  # start included
    assert _ok(iv.contains(_instant(19))) is True
    assert _ok(iv.contains(_instant(20))) is False  # end excluded
    assert _ok(iv.contains(_instant(9))) is False
    other = _ok(Interval.try_create(_instant(20), _instant(30)))
    assert _ok(iv.overlaps(other)) is False  # abutting, end exclusive -> no overlap
    overlapping = _ok(Interval.try_create(_instant(15), _instant(25)))
    assert _ok(iv.overlaps(overlapping)) is True


# E1-U39 -----------------------------------------------------------------------
def test_e1_u39_wall_and_monotonic_type_separated() -> None:
    """CT-02: wall and monotonic kinds are type-separated; a MonotonicReading is never
    an Instant and is a boot-scoped opaque diagnostic (excluded from identity)."""
    instant = _instant(1_000)
    mono = _ok(MonotonicReading.try_create(1_000, "boot-1"))
    assert not isinstance(mono, Instant)
    assert instant.kind is ClockKind.WALL
    assert mono.kind is ClockKind.MONOTONIC
    assert not hasattr(mono, "fp1_identity")  # excluded from identity


# E1-U40 -----------------------------------------------------------------------
def test_e1_u40_clock_protocol_seam_data_driven_replays_in_order() -> None:
    """CT-02 / DEC-0022: Clock is a core-defined protocol seam; DataDrivenClock
    returns its scripted instants in order (replay)."""
    i0, i1 = _instant(10), _instant(20)
    clock = DataDrivenClock(boot_epoch_id="boot-1", wall_instants=[i0, i1], monotonic_ns=[5, 6])
    assert isinstance(clock, Clock)  # runtime-checkable protocol
    assert clock.wall_now() is i0
    assert clock.wall_now() is i1


# E1-U41 (mutmut pin chrono.py:756/764 exhaustion) -----------------------------
def test_e1_u41_data_driven_clock_exhaustion_is_a_clean_boundary() -> None:
    """CT-02 / CT-04 (pin chrono.py:756/764): exhaustion fires at EXACTLY len(script)
    via the `>= len` guard and raises a clean LookupError -- the boundary, NOT the
    English message. PLAN section 5 declares the exhaustion message string not ratified
    surface; OR-03 constrains this seam toward a typed refusal, so the message prose is
    re-pointed away. Asserting the exact exception type distinguishes the deliberate
    exhaustion raise from the IndexError a `> len` off-by-one would produce (IndexError
    is a LookupError subclass, so `pytest.raises(LookupError)` alone would not catch the
    off-by-one)."""
    clock = DataDrivenClock(boot_epoch_id="boot-1", wall_instants=[_instant(1)], monotonic_ns=[7])
    assert clock.wall_now().value_ns == 1  # consumes the only wall instant
    with pytest.raises(LookupError) as exc_w:
        clock.wall_now()
    assert type(exc_w.value) is LookupError  # clean exhaustion boundary, not IndexError
    assert clock.monotonic_now().value_ns == 7
    with pytest.raises(LookupError) as exc_m:
        clock.monotonic_now()
    assert type(exc_m.value) is LookupError


# E1-U42 (mutmut pin chrono.py:756 advance-per-call) ---------------------------
def test_e1_u42_data_driven_clock_advances_exactly_one_per_call() -> None:
    """CT-02 (pin chrono.py:756): the cursor advances exactly one per call (+= 1, not
    reset to 1): three sequential reads return script[0], [1], [2]."""
    i0, i1, i2 = _instant(10), _instant(20), _instant(30)
    clock = DataDrivenClock(
        boot_epoch_id="boot-1", wall_instants=[i0, i1, i2], monotonic_ns=[1, 2, 3]
    )
    assert [clock.wall_now().value_ns for _ in range(3)] == [10, 20, 30]
    assert [clock.monotonic_now().value_ns for _ in range(3)] == [1, 2, 3]


# E1-U43 (mutmut pin chrono.py:881/895 WriterSequencer) ------------------------
def test_e1_u43_writer_sequencer_strictly_increasing_from_declared_start() -> None:
    """CT-02 / DEC-0106 (pin chrono.py:881/895): WriterSequencer mints a per-writer
    strictly-increasing sequence from the declared start (default 0 and custom);
    OrderingKey carries the real instant and writer (not None)."""
    writer = _writer()
    seq = WriterSequencer(writer)  # default start
    assert seq.next_sequence == 0
    instant = _instant(100)
    key0 = seq.mint(instant)
    assert isinstance(key0, OrderingKey)
    assert key0.sequence == 0
    assert key0.instant is instant  # real instant, not None
    assert key0.writer is writer  # real writer, not None
    key1 = seq.mint(_instant(200))
    assert key1.sequence == 1  # strictly increasing by exactly one
    # custom start honored
    custom = WriterSequencer(writer, start=5)
    assert custom.mint(_instant(1)).sequence == 5


# E1-U44 (mutmut pin chrono.py:1022 verify_tzdb_pin) ---------------------------
def test_e1_u44_verify_tzdb_pin_mismatch_and_empty_versions() -> None:
    """CT-02 FM-5 (pin chrono.py:1022): resolved != pinned -> unavailable dependency
    refusal whose context field is tzdata_version; an empty pinned or resolved version
    is itself refused; a match returns the pinned version."""
    match = verify_tzdb_pin("2025a", "2025a")
    assert _ok(match) == "2025a"
    mismatch = _refusal(verify_tzdb_pin("2025a", "2025b"))
    assert mismatch.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert mismatch.context["field"] == "tzdata_version"
    empty_pinned = _refusal(verify_tzdb_pin("", "2025a"))
    assert empty_pinned.context["field"] == "pinned_version"
    empty_resolved = _refusal(verify_tzdb_pin("2025a", ""))
    assert empty_resolved.context["field"] == "resolved_version"


# E1-U45 -----------------------------------------------------------------------
def test_e1_u45_render_utc_iso8601_display_only_non_instant_refused() -> None:
    """CT-02 / DEC-0108: render_utc_iso8601 is display-only and labelled; a non-Instant
    input -> invalid input refusal."""
    display = _ok(render_utc_iso8601(_instant(0)))
    assert isinstance(display, DisplayTime)
    assert display.zone == "UTC"
    assert display.text.endswith("Z")
    assert not hasattr(DisplayTime, "fp1_identity")  # excluded from identity
    r = _refusal(render_utc_iso8601("2026-01-02"))
    assert r.category is RefusalCategory.INVALID_INPUT


# E1-U46 -----------------------------------------------------------------------
def test_e1_u46_writer_id_minted_per_tuple_monotonic_scoped_to_boot() -> None:
    """CT-02 / DEC-0106: WriterId is minted per (machine, role, stream) with a
    boot/epoch id; a monotonic reading is scoped to its boot and never compared
    across boots."""
    writer = _ok(WriterId.try_create("m", "r", "s", "boot-1"))
    assert (writer.machine, writer.role, writer.stream, writer.boot_epoch_id) == (
        "m",
        "r",
        "s",
        "boot-1",
    )
    a = _ok(MonotonicReading.try_create(2_000, "boot-1"))
    b = _ok(MonotonicReading.try_create(1_000, "boot-2"))  # different boot
    assert is_refusal(a.elapsed_since(b))  # never compared across boots
    same_boot = _ok(MonotonicReading.try_create(1_000, "boot-1"))
    assert _ok(a.elapsed_since(same_boot)).value_ns == 1_000
