"""Epic 14 · Group C — completed-boundary & forming-bar (Story 14.3, R12-R15).

B-2/AR-57/FR-037/SC-06: higher-BarSpec bars fold from the finest declared base
and emit ONLY on a completed boundary; a forming bar is never visible or
actionable and carries an inspectable completeness state; same-slice bars and
fills consume ONE underlying series; look-ahead prevention ships regardless of
GAP-0048. Weak spot: bars.py (line 68% / branch 56% in the harness metrics).
"""

from __future__ import annotations

from _e14 import NS, inst, ok

from qmf.core.refusal import RefusalCategory, is_refusal
from qmb.runloop import (
    COMPLETED_BOUNDARY_ONLY,
    COMPLETENESS_COMPLETED,
    COMPLETENESS_FORMING,
    FORMING_BAR_ACTIONABLE,
    FORMING_BAR_VISIBLE,
    LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048,
    DeclaredBarSpec,
    ReadableBarSet,
    StreamBarPlan,
    UnderlyingSeries,
    act_on_bar,
    consume_same_slice,
    readable_bars,
    require_same_series,
)

_SEC = 1_000_000_000  # ns


def _plan(stream_id: str = "eurusd") -> StreamBarPlan:
    # Finest base = 1s; higher = 2s (an integer multiple, boundaries align).
    return ok(
        StreamBarPlan.try_create(
            stream_id,
            [{"kind": "time-interval", "seconds": 1}, {"kind": "time-interval", "seconds": 2}],
        )
    )


def _series(stream_id: str, offsets: tuple[int, ...]) -> UnderlyingSeries:
    samples = [{"instant": inst(NS + off), "price": 100 + i} for i, off in enumerate(offsets)]
    return ok(UnderlyingSeries.try_create(stream_id, samples))


# --- T-14.3-a (L1) higher bar from finest base, emitted only on boundary [R12] P0
def test_t143a_completed_boundary_only_emission() -> None:
    plan = _plan()
    series = _series("eurusd", (0, _SEC))
    # frontier completes the 1s base window [NS, NS+1s) but not the 2s window.
    frontier = inst(NS + _SEC)
    consumed = ok(consume_same_slice(plan=plan, series=series, frontier=frontier))
    assert COMPLETED_BOUNDARY_ONLY is True
    # Nothing is emitted mid-interval: every emitted bar closed on its boundary.
    for bar in consumed.emitted:
        assert bar.completeness == COMPLETENESS_COMPLETED
        assert bar.closed is True
        assert bar.interval.end.value_ns <= frontier.value_ns
    # The 2s higher bar is still forming at this frontier (not emitted).
    emitted_seconds = {bar.bar_spec.parameters.get("seconds") for bar in consumed.emitted}
    forming_seconds = {state.bar.bar_spec.parameters.get("seconds") for state in consumed.forming}
    assert 1 in emitted_seconds
    assert 2 in forming_seconds
    assert 2 not in emitted_seconds
    # Advancing the frontier to the 2s boundary completes the higher bar.
    later = ok(consume_same_slice(plan=plan, series=series, frontier=inst(NS + 2 * _SEC)))
    assert 2 in {bar.bar_spec.parameters.get("seconds") for bar in later.emitted}


# --- T-14.3-b (L2) a forming bar is never visible or actionable [R13] · P0 ----
def test_t143b_forming_bar_not_visible_or_actionable() -> None:
    consumed = ok(consume_same_slice(plan=_plan(), series=_series("eurusd", (0,)), frontier=inst(NS)))
    assert consumed.forming, "expected a forming higher bar at the base boundary"
    forming = consumed.forming[0]
    assert forming.actionable is False
    assert forming.visible_to_strategy is False
    # Acting on a forming bar (or its wrapped bar) is a typed policy rejection.
    refused_state = act_on_bar(forming)
    assert is_refusal(refused_state) and refused_state.category is RefusalCategory.POLICY_REJECTION
    refused_bar = act_on_bar(forming.bar)
    assert is_refusal(refused_bar) and refused_bar.category is RefusalCategory.POLICY_REJECTION
    # A forming bar can never enter the strategy-readable set.
    leaked = ReadableBarSet.try_create([forming.bar])
    assert is_refusal(leaked) and leaked.category is RefusalCategory.POLICY_REJECTION
    # The completed base bar, by contrast, is actionable.
    if consumed.emitted:
        assert act_on_bar(consumed.emitted[0]).value.completeness == COMPLETENESS_COMPLETED


# --- T-14.3-c (L1) inspectable completeness distinguishes forming vs done [R13]
def test_t143c_completeness_state_is_inspectable() -> None:
    assert COMPLETENESS_FORMING != COMPLETENESS_COMPLETED
    assert FORMING_BAR_VISIBLE is False
    assert FORMING_BAR_ACTIONABLE is False
    consumed = ok(consume_same_slice(plan=_plan(), series=_series("eurusd", (0,)), frontier=inst(NS)))
    forming = consumed.forming[0]
    assert forming.bar.completeness == COMPLETENESS_FORMING
    assert forming.bar.closed is False
    ident = forming.fp1_identity()
    assert ident["completeness"] == COMPLETENESS_FORMING
    assert ident["actionable"] is False
    assert ident["visible_to_strategy"] is False


# --- T-14.3-d (L2) bars and fills consume the SAME series [R14] · P0 ----------
def test_t143d_bars_and_fills_same_series() -> None:
    series = _series("eurusd", (0, _SEC))
    consumed = ok(consume_same_slice(plan=_plan(), series=series, frontier=inst(NS + _SEC)))
    expected = series.fingerprint.value
    assert consumed.series_fp1 == expected
    for bar in consumed.emitted:
        assert bar.series_fp1 == expected
    for sample in consumed.fill_path:
        assert isinstance(sample.price, int)
    # The same-series guard: identical fp accepts, a divergent fp refuses.
    assert ok(require_same_series(expected, expected)) is None
    diverged = require_same_series(expected, "fp1:sha256:" + "0" * 64)
    assert is_refusal(diverged) and diverged.category is RefusalCategory.INVALID_INPUT


# --- T-14.3-f (L4) look-ahead prevention holds with GAP-0048 open [R15] -------
def test_t143f_no_lookahead_independent_of_gap_0048() -> None:
    assert LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048 is True
    # A print AFTER the frontier must never be consumed (by construction).
    series = _series("eurusd", (0, _SEC // 2, 3 * _SEC))  # last print is in the future
    frontier = inst(NS + _SEC)
    consumed = ok(consume_same_slice(plan=_plan(), series=series, frontier=frontier))
    for sample in consumed.fill_path:
        assert sample.instant.value_ns <= frontier.value_ns
    for bar in consumed.emitted:
        assert bar.interval.start.value_ns <= frontier.value_ns
        assert bar.interval.end.value_ns <= frontier.value_ns
    assert consumed.lookahead_prevention_independent_of_gap_0048 is True


# --- extra: finest-base ranking is genuinely the finest [R12] ----------------
def test_t143_finest_base_is_the_finest_declared() -> None:
    from qmb.runloop import finest_base

    base = ok(
        finest_base(
            [
                ok(DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 4})),
                ok(DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 1})),
                ok(DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 2})),
            ]
        )
    )
    assert base.parameters.get("seconds") == 1
