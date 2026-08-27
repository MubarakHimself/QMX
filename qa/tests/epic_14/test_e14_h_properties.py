"""Epic 14 · Group I — property-based invariants (L6, R2/R8/R13).

Hypothesis breadth over the input spaces hand-written cases (and the harness's
56%-branch bars.py) cannot enumerate:
 - T-14.1-P [R2]: over arbitrary multi-stream cursors the frontier is monotone
   non-decreasing and equals the min next-emit (rewind refused).
 - T-14.2-P [R8]: over arbitrary phase-5 intent injections, no injected intent
   fills against its own slice.
 - T-14.3-e [R13]: over arbitrary tick sequences and BarSpec boundaries, no
   actionable event ever references a forming bar.
"""

from __future__ import annotations

from _e14 import NS, RecordingHandler, inst, obs, ok

from hypothesis import given, settings
from hypothesis import strategies as st

from qmf.core.refusal import is_ok, is_refusal
from qmb.runloop import (
    COMPLETENESS_COMPLETED,
    COMPLETENESS_FORMING,
    StreamBarPlan,
    StreamNextEmit,
    UnderlyingSeries,
    act_on_bar,
    advance_frontier,
    consume_same_slice,
    readable_bars,
    run_slice,
)


# --- T-14.1-P (L6) frontier is monotone and equals the min next-emit [R2] -----
@settings(max_examples=200, deadline=None)
@given(
    rounds=st.lists(
        st.lists(st.integers(min_value=0, max_value=10**9), min_size=1, max_size=4),
        min_size=1,
        max_size=12,
    )
)
def test_t141p_clock_min_and_monotone(rounds: list[list[int]]) -> None:
    current = None
    for row in rounds:
        cursors = [StreamNextEmit(stream_id=f"s{i}", next_emit=inst(NS + ns)) for i, ns in enumerate(row)]
        result = advance_frontier(current, cursors)
        expected = NS + min(row)
        if current is not None and expected < current.value_ns:
            assert is_refusal(result)  # the frontier never rewinds
        else:
            value = ok(result)
            assert value.value_ns == expected  # equals the minimum next-emit
            assert current is None or value.value_ns >= current.value_ns
            current = value


# --- T-14.2-P (L6) an injected phase-5 intent never fills its own slice [R8] --
@settings(max_examples=200, deadline=None)
@given(k=st.integers(min_value=0, max_value=6))
def test_t142p_minted_intent_never_fills_own_slice(k: int) -> None:
    handler = RecordingHandler(mint_on="eurusd", mint_count=k, fill=True)
    out = ok(
        run_slice(
            (obs("eurusd"), obs("gbpusd")),
            stream_set=("eurusd", "gbpusd"),
            handler=handler,
            resting=(),
        )
    )
    assert len(out.minted) == k
    resting_ids = {item.intent_id for item in out.resting}
    for minted_id in out.minted:
        assert minted_id not in out.filled
        assert minted_id in resting_ids
    assert out.filled == ()  # nothing rested at slice start, so nothing filled


# --- T-14.3-e (L6) no actionable event ever references a forming bar [R13] · P0
@settings(max_examples=200, deadline=None)
@given(
    raw_offsets=st.lists(st.integers(min_value=0, max_value=12), min_size=1, max_size=8),
    period_s=st.integers(min_value=1, max_value=5),
    frontier_off=st.integers(min_value=0, max_value=15),
)
def test_t143e_forming_bar_never_actionable(
    raw_offsets: list[int], period_s: int, frontier_off: int
) -> None:
    period_ns = period_s * 1_000_000_000
    unit = max(1, period_ns // 2)
    offsets = sorted(raw_offsets)
    samples = [{"instant": inst(NS + off * unit), "price": 100 + i} for i, off in enumerate(offsets)]
    series = ok(UnderlyingSeries.try_create("eurusd", samples))
    plan = ok(StreamBarPlan.try_create("eurusd", [{"kind": "time-interval", "seconds": period_s}]))
    frontier = inst(NS + frontier_off * unit)
    consumed = ok(consume_same_slice(plan=plan, series=series, frontier=frontier))
    for state in consumed.forming:
        assert state.actionable is False
        assert state.visible_to_strategy is False
        assert state.bar.completeness == COMPLETENESS_FORMING
        assert state.bar.interval.end.value_ns > frontier.value_ns  # not yet closed
        assert is_refusal(act_on_bar(state))  # acting on it is refused
    for bar in consumed.emitted:
        assert bar.completeness == COMPLETENESS_COMPLETED
        assert bar.interval.end.value_ns <= frontier.value_ns  # completed boundary only
        assert is_ok(act_on_bar(bar))
    for sample in consumed.fill_path:
        assert sample.instant.value_ns <= frontier.value_ns  # never a future print
    readable = ok(readable_bars(consumed.emitted, consumed.forming))
    for bar in readable.bars:
        assert bar.completeness == COMPLETENESS_COMPLETED  # forming never readable
