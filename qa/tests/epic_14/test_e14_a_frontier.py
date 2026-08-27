"""Epic 14 · Group A — injected frontier clock (Story 14.1, R1-R6).

Requirement-derived. B-2/AD-8: time advances only through an injected frontier
clock that IS qmf-core's AD-8 Clock; replay advance is a pure function of the
data cursor (monotone non-decreasing, min next-emit, never rewind); emitted
instants are AD-8 wall/replay kind, never the monotonic diagnostic; the clock
does not choose world; asserting a simulated instant as wall/replay is refused
until GAP-0048; the loop is never forked.
"""

from __future__ import annotations

import inspect

from _e14 import NS, inst, ok, slices

from qmf.core.chrono import Clock, ClockKind, Instant, MonotonicReading
from qmf.core.refusal import RefusalCategory, is_refusal
from qmb.config import CLOCK_REPLAY, CLOCK_SIMULATED
from qmb.runloop import (
    CLOCK_DOES_NOT_CHOOSE_WORLD,
    FrontierClock,
    StreamNextEmit,
    advance_frontier,
    as_wall_replay_instant,
    min_next_emit,
    run,
    script_replay_clock,
)


def _cursor(stream_id: str, ns: int | None) -> StreamNextEmit:
    return StreamNextEmit(stream_id=stream_id, next_emit=None if ns is None else inst(ns))


# --- T-14.1-a (L1) monotone non-decreasing across a fixed cursor [R2] --------
def test_t141a_advance_is_monotone_non_decreasing() -> None:
    clock = ok(FrontierClock.try_create(boot_epoch_id="boot", clock_binding=CLOCK_REPLAY))
    seen: list[int] = []
    for ns in (NS, NS, NS + 5, NS + 5, NS + 9):
        cursors = [_cursor("a", ns), _cursor("b", ns + 100), _cursor("c", None)]
        seen.append(ok(clock.advance(cursors)).value_ns)
    assert seen == sorted(seen), seen
    assert all(later >= earlier for earlier, later in zip(seen, seen[1:], strict=False))


# --- T-14.1-b (L1) pull is the minimum next-emit; order-invariant [R2,R9] -----
def test_t141b_pull_is_minimum_next_emit_order_invariant() -> None:
    forward = [_cursor("a", NS + 30), _cursor("b", NS + 10), _cursor("c", NS + 20)]
    reversed_ = list(reversed(forward))
    chosen_forward = ok(min_next_emit(forward))
    chosen_reversed = ok(min_next_emit(reversed_))
    assert chosen_forward.value_ns == NS + 10
    # Declaration order must not change the chosen instant (no wall-time tiebreak).
    assert chosen_forward.value_ns == chosen_reversed.value_ns
    # Exhausted (None) streams are ignored by the frontier pull.
    with_exhausted = [_cursor("a", None), _cursor("b", NS + 7), _cursor("c", None)]
    assert ok(min_next_emit(with_exhausted)).value_ns == NS + 7


# --- T-14.1-c (L1) the clock never rewinds [R2] ------------------------------
def test_t141c_advance_refuses_rewind() -> None:
    clock = ok(FrontierClock.try_create(boot_epoch_id="boot", clock_binding=CLOCK_REPLAY))
    ok(clock.advance([_cursor("a", NS + 50)]))
    rewound = clock.advance([_cursor("a", NS + 10)])
    assert is_refusal(rewound), rewound
    assert rewound.category is RefusalCategory.INVALID_INPUT
    # advance_frontier as a pure function refuses the same rewind.
    pure = advance_frontier(inst(NS + 50), [_cursor("a", NS + 10)])
    assert is_refusal(pure)


# --- T-14.1-d (L1) emitted instants are AD-8 wall kind, never monotonic [R3] --
def test_t141d_emits_wall_never_monotonic_diagnostic() -> None:
    clock = ok(FrontierClock.try_create(boot_epoch_id="boot", clock_binding=CLOCK_REPLAY))
    emitted = ok(clock.advance([_cursor("a", NS)]))
    assert isinstance(emitted, Instant)
    assert emitted.kind is ClockKind.WALL
    # A MonotonicReading is never accepted as a wall/replay frontier instant.
    reading = MonotonicReading(value_ns=123, boot_epoch_id="boot")
    refused = as_wall_replay_instant(reading, clock_binding=CLOCK_REPLAY)
    assert is_refusal(refused), refused
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- T-14.1-e (L1) the clock does not choose world [R3] ----------------------
def test_t141e_clock_does_not_choose_world() -> None:
    assert CLOCK_DOES_NOT_CHOOSE_WORLD is True
    clock = ok(FrontierClock.try_create(boot_epoch_id="boot", clock_binding=CLOCK_REPLAY))
    # No world input or output anywhere on the clock seam.
    assert not hasattr(clock, "world")
    assert "world" not in inspect.signature(FrontierClock.advance).parameters
    assert "world" not in inspect.signature(advance_frontier).parameters
    assert "world" not in inspect.signature(min_next_emit).parameters
    # The binding is the compiler's choice, exposed but distinct from world.
    assert clock.clock_binding == CLOCK_REPLAY


# --- T-14.1-f (L3) frontier clock IS an AD-8 Clock (substitutable) [R4] -------
def test_t141f_frontier_clock_satisfies_ad8_clock_protocol() -> None:
    clock = ok(FrontierClock.try_create(boot_epoch_id="boot", clock_binding=CLOCK_REPLAY))
    assert isinstance(clock, Clock)
    # The scripted DataDrivenClock reuse is also an AD-8 Clock (one seam).
    scripted = script_replay_clock(boot_epoch_id="boot", wall_instants=(inst(NS),))
    assert isinstance(scripted, Clock)


# --- T-14.1-h (L3) asserting a simulated instant as wall/replay is refused [R6]
def test_t141h_simulated_assert_refused_until_gap_0048() -> None:
    refused = as_wall_replay_instant(inst(NS), clock_binding=CLOCK_SIMULATED)
    assert is_refusal(refused), refused
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context.get("gap") == "GAP-0048"


# --- T-14.1-i (L4) one un-forked loop; only the injected adapter differs [R5] -
def test_t141i_loop_is_never_forked_only_adapter_differs() -> None:
    stream = ("eurusd",)
    evs = slices(stream, n=2)
    clock = ok(FrontierClock.try_create(boot_epoch_id="boot", clock_binding=CLOCK_REPLAY))
    with_clock = ok(run(slices=evs, stream_set=stream, clock=clock))
    without_clock = ok(run(slices=evs, stream_set=stream))
    # Same loop code path: the injected clock adapter is not identity-bearing;
    # the two runs produce byte-identical loop-outcome identity.
    assert with_clock.fp1_identity() == without_clock.fp1_identity()
    # There is exactly one loop entry point; no per-run-kind fork exists.
    import qmb.runloop as runloop

    forked = [n for n in dir(runloop) if n in {"run_backtest", "run_replay", "run_live"}]
    assert forked == []
