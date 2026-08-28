"""Reference usage — the injected frontier clock (Story 14.1 / B-2).

Executable::

    python qmb/examples/frontier_clock_usage.py

Shows the things AR-16 / B-2 / FR-037 / SC-06 pin down:

1. Time is read only from an injected AD-8 ``Clock`` (``DataDrivenClock`` or
   ``FrontierClock``) — nothing below the composition root reads the system clock.
2. Replay advance is a pure function of stream next-emit cursors: min next-emit,
   monotonically non-decreasing, never rewinding.
3. Emitted Instants are wall/replay; a ``MonotonicReading`` is refused as a wall
   Instant; simulated Instant assertion is refused until GAP-0048.
4. The clock does not choose ``world`` — ``CLOCK_REPLAY`` / ``CLOCK_SIMULATED``
   come from the compiler (B-7).
5. Backtest/replay/(deferred) live share the same ``read_frontier`` path — the
   loop is never forked.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.config import CLOCK_REPLAY, CLOCK_SIMULATED
from qmb.runloop import (
    CLOCK_DOES_NOT_CHOOSE_WORLD,
    FrontierClock,
    StreamNextEmit,
    advance_frontier,
    as_wall_replay_instant,
    frontier_clock_name,
    min_next_emit,
    read_frontier,
    script_replay_clock,
)
from qmf.core.chrono import Clock, Instant, MonotonicReading
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _stream(stream_id: str, next_ns: int | None) -> StreamNextEmit:
    nxt = None if next_ns is None else _instant(next_ns)
    return _unwrap(StreamNextEmit.try_create(stream_id, nxt), "stream")


def injected_clock_drives_time() -> Instant:
    """Composition root injects a Clock; read_frontier is the only time read."""
    scripted: Clock = script_replay_clock(
        boot_epoch_id="boot-demo",
        wall_instants=(_instant(_NS), _instant(_NS + 1_000)),
        monotonic_ns=(0, 1),
    )
    # read_frontier is value-or-refusal (CT-04; OR-03): a real/replay clock returns Ok,
    # a spent or not-yet-advanced clock returns an unavailable-dependency refusal.
    first = _unwrap(read_frontier(scripted), "wall reading")
    assert first.value_ns == _NS
    return first


def min_next_emit_is_deterministic() -> Instant:
    """Frontier pull is the min next-emit across declared streams."""
    streams = (
        _stream("eurusd", _NS + 30),
        _stream("gbpusd", _NS + 10),
        _stream("usdjpy", _NS + 20),
    )
    pulled = _unwrap(min_next_emit(streams), "min next-emit")
    again = _unwrap(min_next_emit(tuple(reversed(streams))), "min next-emit again")
    assert pulled.value_ns == again.value_ns == _NS + 10
    return pulled


def rewind_is_refused(current: Instant) -> TypedRefusal:
    """A next-emit strictly before the frontier is invalid input."""
    refused = advance_frontier(current, (_stream("late", current.value_ns - 1),))
    assert isinstance(refused, TypedRefusal)
    assert refused.category is RefusalCategory.INVALID_INPUT
    return refused


def monotonic_and_simulated_are_refused() -> None:
    """Monotonic-as-wall and simulated Instant assertion refuse (GAP-0048)."""
    reading = _unwrap(MonotonicReading.try_create(99, "boot-demo"), "monotonic")
    mono = as_wall_replay_instant(reading, clock_binding=CLOCK_REPLAY)
    assert isinstance(mono, TypedRefusal)
    assert mono.category is RefusalCategory.INVALID_INPUT

    simulated = as_wall_replay_instant(_instant(), clock_binding=CLOCK_SIMULATED)
    assert isinstance(simulated, TypedRefusal)
    assert simulated.category is RefusalCategory.POLICY_REJECTION
    assert simulated.context["gap"] == "GAP-0048"


def stream_driven_frontier_clock() -> FrontierClock:
    """FrontierClock IS Clock; advance is pure of the data cursor."""
    clock = _unwrap(
        FrontierClock.try_create(boot_epoch_id="boot-frontier", clock_binding=CLOCK_REPLAY),
        "frontier clock",
    )
    assert isinstance(clock, Clock)
    assert clock.clock_binding == CLOCK_REPLAY
    assert CLOCK_DOES_NOT_CHOOSE_WORLD is True
    assert not hasattr(clock, "world")
    _unwrap(
        clock.advance((_stream("a", _NS + 5), _stream("b", _NS + 9))),
        "first advance",
    )
    assert _unwrap(read_frontier(clock), "wall reading").value_ns == _NS + 5
    return clock


def main() -> None:
    assert frontier_clock_name() == "qmf.core.chrono.Clock"
    assert qmb.frontier_clock_name() == frontier_clock_name()

    injected_clock_drives_time()
    print("injected Clock read via read_frontier")

    pulled = min_next_emit_is_deterministic()
    print(f"min next-emit pull = {pulled.value_ns} ns (deterministic)")

    rewind_is_refused(pulled)
    print("rewind refused: invalid input")

    monotonic_and_simulated_are_refused()
    print("monotonic-as-wall refused; simulated Instant refused until GAP-0048")

    stream_driven_frontier_clock()
    print("frontier clock ok; clock does not choose world")


if __name__ == "__main__":
    main()
