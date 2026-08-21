"""Reference usage — CT-02 exact time, calendars, and the injected Clock (COMP-QMF-CORE).

Executable::

    python packages/qmf-core/examples/time_usage.py

Shows the five things CT-02 pins down:

1. An :class:`Instant` is an exact ``int64`` UTC-nanosecond count; instant 0 is
   valid, and nanosecond arithmetic that would overflow is refused, never wrapped.
2. :class:`CivilDate` and :class:`TradingDate` are distinct; a trading date carries
   its :class:`CalendarIdentity` in-band, and comparing across two calendars is a
   typed refusal — never a silent answer.
3. Causality compares :class:`Instant`\\ s only (:func:`compare_causal`), and it
   refuses at equal instants rather than tie-break on the ordering key.
4. The :class:`Clock` seam is injected at the composition root; a
   :class:`DataDrivenClock` replays wall instants and boot-scoped monotonic
   readings without ever reading the system clock, and a monotonic reading is a
   :class:`MonotonicReading`, never an :class:`Instant`.
5. A :class:`WriterSequencer` mints ``(instant, writer, sequence)`` ordering keys
   whose sequence strictly increases — a replay order with no causal meaning.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import (
    CalendarIdentity,
    CivilDate,
    Clock,
    DataDrivenClock,
    Duration,
    Instant,
    MonotonicReading,
    TemporalOrder,
    TradingDate,
    WriterId,
    WriterSequencer,
    compare_causal,
    render_utc_iso8601,
)
from qmf.core.refusal import Result, TypedRefusal, is_ok

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def instants_are_exact_and_checked() -> tuple[Instant, Instant]:
    """Instant 0 is valid; nanosecond overflow is refused, never wrapped."""
    epoch = _unwrap(Instant.try_create(0), "instant zero")

    one_second = _unwrap(Duration.try_create(1_000_000_000), "one second")
    later = _unwrap(epoch.add_duration(one_second), "epoch + 1s")

    # Advancing the maximum instant overflows the int64 range — refused.
    at_max = _unwrap(Instant.try_create((2**63) - 1), "max instant")
    overflow = at_max.add_duration(one_second)
    assert isinstance(overflow, TypedRefusal)
    return epoch, later


def trading_dates_are_calendar_scoped() -> TradingDate:
    """A trading date carries its calendar in-band; cross-calendar compare refuses."""
    forex_v3 = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025b"), "forex v3")
    forex_v4 = _unwrap(CalendarIdentity.try_create("forex-17NY", "v4", "2025b"), "forex v4")

    civil = _unwrap(CivilDate.try_create(2026, 8, 21), "civil date")
    day_v3 = _unwrap(TradingDate.try_create(forex_v3, civil), "trading day v3")
    day_v4 = _unwrap(TradingDate.try_create(forex_v4, civil), "trading day v4")

    # Same calendar: an ordinary comparison. Different calendars: a typed refusal.
    same = _unwrap(day_v3.compare(day_v3), "same-calendar compare")
    assert same is TemporalOrder.EQUAL
    cross = day_v3.compare(day_v4)
    assert isinstance(cross, TypedRefusal)
    return day_v3


def causality_reads_instants_only(epoch: Instant, later: Instant) -> None:
    """Causality compares instants; equal instants refuse rather than tie-break."""
    order = _unwrap(compare_causal(epoch, later), "causal order")
    assert order is TemporalOrder.BEFORE

    concurrent = compare_causal(epoch, epoch)
    assert isinstance(concurrent, TypedRefusal)


def clock_is_injected(clock: Clock) -> tuple[Instant, Duration]:
    """The composition root injects the clock; nothing below reads the system clock."""
    first_wall = clock.wall_now()
    start = clock.monotonic_now()
    end = clock.monotonic_now()

    # A monotonic reading is its own type, never an Instant.
    assert isinstance(start, MonotonicReading)
    elapsed = _unwrap(end.elapsed_since(start), "elapsed")
    return first_wall, elapsed


def ordering_has_no_causal_meaning(clock: Clock) -> WriterSequencer:
    """A writer mints a strictly-increasing sequence for replay ordering."""
    writer = _unwrap(
        WriterId.try_create("vps-1", "ingest", "ticks", clock.boot_epoch_id),
        "writer id",
    )
    sequencer = WriterSequencer(writer)
    first = sequencer.mint(clock.wall_now())
    second = sequencer.mint(clock.wall_now())
    assert second.sequence > first.sequence
    return sequencer


def main() -> None:
    epoch, later = instants_are_exact_and_checked()
    display = _unwrap(render_utc_iso8601(epoch), "display")
    print(f"instant 0 renders (display-only, {display.zone}) as {display.text}")

    day = trading_dates_are_calendar_scoped()
    print(f"trading date {day.date_value.isoformat()} is scoped to {day.calendar.rule_set}")

    causality_reads_instants_only(epoch, later)
    print("causality compares instants only; equal instants refuse to tie-break")

    clock: Clock = DataDrivenClock(
        boot_epoch_id="boot-2026-08-21T00:00Z",
        wall_instants=[epoch, later, later],
        monotonic_ns=[10, 42],
    )
    first_wall, elapsed = clock_is_injected(clock)
    print(
        f"injected clock wall_now = {first_wall.value_ns} ns; monotonic elapsed = {elapsed.value_ns} ns"
    )

    sequencer = ordering_has_no_causal_meaning(clock)
    print(f"writer minted a strictly-increasing sequence; next is {sequencer.next_sequence}")


if __name__ == "__main__":
    main()
