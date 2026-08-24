"""Story 14.3 — completed-boundary bar derivation; forming is never actionable."""

from __future__ import annotations

from typing import TypeVar

from qmb.config import CLOCK_SIMULATED
from qmb.doors import api
from qmb.runloop import (
    BARSPEC_KINDS,
    COMPLETED_BOUNDARY_ONLY,
    COMPLETENESS_COMPLETED,
    COMPLETENESS_FORMING,
    FORMING_BAR_ACTIONABLE,
    FORMING_BAR_VISIBLE,
    LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048,
    DeclaredBarSpec,
    FrontierClock,
    SeriesSample,
    StreamBarPlan,
    UnderlyingSeries,
    act_on_bar,
    consume_same_slice,
    finest_base,
    fingerprint_loop,
    loop_identity,
    readable_bars,
    require_same_series,
    run,
    run_slice,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_SEC = 1_000_000_000
_1M = 60 * _SEC
_5M = 300 * _SEC


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _sample(ns: int, price: int, volume: int = 1) -> SeriesSample:
    return _ok(SeriesSample.try_create(_instant(ns), price, volume))


def _spec(kind: str, **params: int | str) -> DeclaredBarSpec:
    payload: dict[str, object] = {"kind": kind, **params}
    return _ok(DeclaredBarSpec.try_create(payload))


def _plan(stream_id: str, *specs: DeclaredBarSpec) -> StreamBarPlan:
    return _ok(StreamBarPlan.try_create(stream_id, specs))


def _series(stream_id: str, samples: list[SeriesSample]) -> UnderlyingSeries:
    return _ok(UnderlyingSeries.try_create(stream_id, samples))


def test_higher_bars_derive_from_finest_base_on_completed_boundary() -> None:
    one_m = _spec("time-interval", seconds=60)
    five_m = _spec("time-interval", seconds=300)
    assert _ok(finest_base((one_m, five_m))).unit_size == 60
    plan = _plan("eurusd", one_m, five_m)
    assert plan.base.fp1_identity() == one_m.fp1_identity()
    assert [item.unit_size for item in plan.higher] == [300]
    samples = [_sample(n * _1M, 10 + n) for n in range(6)]
    series = _series("eurusd", samples)
    mid = _ok(consume_same_slice(plan=plan, series=series, frontier=_instant(4 * _1M)))
    five_emitted = [bar for bar in mid.emitted if bar.bar_spec.unit_size == 300]
    five_forming = [state for state in mid.forming if state.bar.bar_spec.unit_size == 300]
    assert five_emitted == []
    assert len(five_forming) == 1
    forming = five_forming[0]
    assert forming.bar.completeness == COMPLETENESS_FORMING
    assert forming.visible_to_strategy is False
    assert forming.actionable is False
    assert forming.filled_units == 4 * _1M
    assert forming.required_units == _5M
    assert forming.bar.close == 14
    closed = _ok(consume_same_slice(plan=plan, series=series, frontier=_instant(_5M)))
    five_done = [bar for bar in closed.emitted if bar.bar_spec.unit_size == 300]
    assert len(five_done) == 1
    done = five_done[0]
    assert done.completeness == COMPLETENESS_COMPLETED
    assert done.closed is True
    assert done.open == 10
    assert done.high == 14
    assert done.low == 10
    assert done.close == 14
    assert done.completed_at is not None
    assert done.completed_at.value_ns == _5M
    assert done.series_fp1 == series.fingerprint.value
    assert done.sample_count == 5


def test_forming_bar_never_visible_or_actionable() -> None:
    plan = _plan("eurusd", _spec("time-interval", seconds=60), _spec("time-interval", seconds=300))
    series = _series("eurusd", [_sample(n * _1M, 100 + n) for n in range(4)])
    consumed = _ok(consume_same_slice(plan=plan, series=series, frontier=_instant(3 * _1M)))
    readable = _ok(readable_bars(consumed.emitted, consumed.forming))
    assert all(bar.completeness == COMPLETENESS_COMPLETED for bar in readable.bars)
    assert all(bar.bar_spec.unit_size == 60 for bar in readable.bars)
    forming = consumed.forming[0]
    assert forming.bar.completeness == COMPLETENESS_FORMING
    refused = act_on_bar(forming)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["completeness"] == COMPLETENESS_FORMING
    also = act_on_bar(forming.bar)
    assert is_refusal(also)
    assert also.category is RefusalCategory.POLICY_REJECTION
    sneak = readable_bars((*consumed.emitted, forming.bar), ())
    assert is_refusal(sneak)
    assert sneak.category is RefusalCategory.POLICY_REJECTION
    allowed = act_on_bar(consumed.emitted[0])
    assert is_ok(allowed)


def test_same_slice_bars_and_fills_share_the_series() -> None:
    plan = _plan("eurusd", _spec("time-interval", seconds=60), _spec("time-interval", seconds=300))
    samples = [_sample(n * _1M, 20 + n, volume=2) for n in range(5)]
    series = _series("eurusd", samples)
    consumed = _ok(consume_same_slice(plan=plan, series=series, frontier=_instant(4 * _1M)))
    assert consumed.series_fp1 == series.fingerprint.value
    assert all(bar.series_fp1 == series.fingerprint.value for bar in consumed.emitted)
    assert all(state.bar.series_fp1 == series.fingerprint.value for state in consumed.forming)
    assert consumed.fill_path[-1].instant.value_ns == 4 * _1M
    assert _ok(require_same_series(consumed.series_fp1, series.fingerprint.value)) is None
    other = _series("eurusd", [_sample(0, 99)])
    diverged = require_same_series(series.fingerprint.value, other.fingerprint.value)
    assert is_refusal(diverged)
    assert diverged.category is RefusalCategory.INVALID_INPUT
    foreign = UnderlyingSeries.try_create("gbpusd", samples)
    assert is_ok(foreign)
    mismatched = consume_same_slice(plan=plan, series=foreign.value, frontier=_instant(_1M))
    assert is_refusal(mismatched)
    assert mismatched.context["field"] == "series_id"


def test_future_prints_cannot_complete_a_bar() -> None:
    plan = _plan("eurusd", _spec("time-interval", seconds=60), _spec("time-interval", seconds=300))
    samples = [_sample(n * _1M, 10 + n) for n in range(7)]
    series = _series("eurusd", samples)
    frontier = _instant(4 * _1M)
    consumed = _ok(consume_same_slice(plan=plan, series=series, frontier=frontier))
    five = [state.bar for state in consumed.forming if state.bar.bar_spec.unit_size == 300]
    assert len(five) == 1
    assert five[0].sample_count == 5
    assert five[0].close == 14
    assert all(sample.instant.value_ns <= frontier.value_ns for sample in consumed.fill_path)
    assert all(bar.completeness == COMPLETENESS_COMPLETED for bar in consumed.emitted)
    assert all(bar.bar_spec.unit_size == 60 for bar in consumed.emitted)


def test_lookahead_prevention_ships_regardless_of_gap_0048() -> None:
    assert LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048 is True
    assert qmb.LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048 is True
    identity = loop_identity()
    assert identity["completed_boundary_only"] is True
    assert identity["forming_bar_actionable"] is False
    assert identity["forming_bar_visible"] is False
    assert identity["higher_barspec_from_finest_base"] is True
    assert identity["same_series_bars_and_fills"] is True
    assert identity["lookahead_prevention_independent_of_gap_0048"] is True
    canonical = _ok(fingerprint_loop())
    flipped = dict(identity)
    flipped["forming_bar_actionable"] = True
    assert _ok(fingerprint(flipped)).value != canonical.value
    clock = _ok(FrontierClock.try_create(boot_epoch_id="boot-sim", clock_binding=CLOCK_SIMULATED))
    refused = run_slice(
        ({"stream_id": "eurusd", "instant": _instant(0), "closed": True},),
        stream_set=("eurusd",),
        clock=clock,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["gap"] == "GAP-0048"
    plan = _plan("eurusd", _spec("time-interval", seconds=60))
    series = _series("eurusd", [_sample(0, 1), _sample(_1M, 2)])
    derived = _ok(consume_same_slice(plan=plan, series=series, frontier=_instant(_1M)))
    assert derived.lookahead_prevention_independent_of_gap_0048 is True
    assert derived.emitted[0].completeness == COMPLETENESS_COMPLETED


def test_tick_count_completes_on_observation_count() -> None:
    plan = _plan("eurusd", _spec("tick-count", count=3))
    samples = [_sample(n, 50 + n) for n in (0, 10, 20, 30, 40)]
    series = _series("eurusd", samples)
    early = _ok(consume_same_slice(plan=plan, series=series, frontier=_instant(10)))
    assert early.emitted == ()
    assert len(early.forming) == 1
    assert early.forming[0].filled_units == 2
    assert early.forming[0].required_units == 3
    done = _ok(consume_same_slice(plan=plan, series=series, frontier=_instant(20)))
    assert len(done.emitted) == 1
    assert done.emitted[0].sample_count == 3
    assert done.emitted[0].completeness == COMPLETENESS_COMPLETED
    assert done.emitted[0].close == 70
    assert len(done.forming) == 0
    later = _ok(consume_same_slice(plan=plan, series=series, frontier=_instant(40)))
    assert len(later.emitted) == 1
    assert later.forming[0].filled_units == 2


def test_non_multiple_and_banned_timeframe_refuse() -> None:
    mixed = StreamBarPlan.try_create(
        "eurusd",
        (_spec("time-interval", seconds=60), _spec("time-interval", seconds=90)),
    )
    assert is_refusal(mixed)
    assert mixed.category is RefusalCategory.INVALID_INPUT
    kinds = StreamBarPlan.try_create(
        "eurusd",
        (_spec("time-interval", seconds=60), _spec("tick-count", count=10)),
    )
    assert is_refusal(kinds)
    timeframe = DeclaredBarSpec.try_create({"kind": "timeframe", "seconds": 60})
    assert is_refusal(timeframe)
    float_spec = DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 1.5})
    assert is_refusal(float_spec)
    session = DeclaredBarSpec.try_create({"kind": "session", "session": "NY"})
    assert is_ok(session)
    session_plan = _ok(StreamBarPlan.try_create("eurusd", (session.value,)))
    refused = consume_same_slice(
        plan=session_plan,
        series=_series("eurusd", [_sample(0, 1)]),
        frontier=_instant(0),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert sorted(BARSPEC_KINDS) == sorted(qmb.BARSPEC_KINDS)


def test_run_slice_emits_completed_higher_bars_in_subphase_one() -> None:
    plan = _plan("eurusd", _spec("time-interval", seconds=60), _spec("time-interval", seconds=300))
    samples = [_sample(n * _1M, 10 + n) for n in range(6)]
    series = _series("eurusd", samples)
    forming_slice = _ok(
        run_slice(
            ({"stream_id": "eurusd", "instant": _instant(4 * _1M), "closed": True},),
            stream_set=("eurusd",),
            series=series,
            bar_plan=plan,
        )
    )
    assert "hold-forming:eurusd" in forming_slice.trace[0].actions
    assert all(bar.bar_spec.unit_size == 60 for bar in forming_slice.emitted_bars)
    five_forming = [state for state in forming_slice.forming if state.bar.bar_spec.unit_size == 300]
    assert len(five_forming) == 1
    assert five_forming[0].visible_to_strategy is False
    closed_slice = _ok(
        run_slice(
            ({"stream_id": "eurusd", "instant": _instant(_5M), "closed": True},),
            stream_set=("eurusd",),
            current_frontier=_instant(4 * _1M),
            series=series,
            bar_plan=plan,
        )
    )
    assert "emit-completed:eurusd" in closed_slice.trace[0].actions
    five = [bar for bar in closed_slice.emitted_bars if bar.bar_spec.unit_size == 300]
    assert len(five) == 1
    assert five[0].completeness == COMPLETENESS_COMPLETED
    assert closed_slice.series_fp1 == (series.fingerprint.value,)
    missing = run_slice(
        ({"stream_id": "eurusd", "instant": _instant(0), "closed": True},),
        stream_set=("eurusd",),
        series=series,
    )
    assert is_refusal(missing)
    outcome = _ok(
        run(
            slices=(
                ({"stream_id": "eurusd", "instant": _instant(4 * _1M), "closed": True},),
                ({"stream_id": "eurusd", "instant": _instant(_5M), "closed": True},),
            ),
            stream_set=("eurusd",),
            series=series,
            bar_plan=plan,
        )
    )
    assert outcome.self_assessment["completed_boundary_only"] is True
    assert outcome.self_assessment["forming_bar_actionable"] is False
    assert outcome.self_assessment["lookahead_prevention_independent_of_gap_0048"] is True
    assert outcome.slices[0].forming[0].actionable is False
    assert any(bar.bar_spec.unit_size == 300 for bar in outcome.slices[1].emitted_bars)


def test_observation_completeness_is_inspectable() -> None:
    from qmb.runloop import SliceObservation

    forming = _ok(SliceObservation.try_create("eurusd", _instant(0), False))
    assert forming.closed is False
    assert forming.completeness == COMPLETENESS_FORMING
    closed = _ok(SliceObservation.try_create("eurusd", _instant(0), True))
    assert closed.completeness == COMPLETENESS_COMPLETED
    assert COMPLETED_BOUNDARY_ONLY is True
    assert FORMING_BAR_ACTIONABLE is False
    assert FORMING_BAR_VISIBLE is False


def test_public_exports_and_door_parity() -> None:
    assert qmb.act_on_bar is act_on_bar
    assert qmb.consume_same_slice is consume_same_slice
    assert qmb.readable_bars is readable_bars
    assert api.act_on_bar is qmb.act_on_bar
    assert api.consume_same_slice is qmb.consume_same_slice
    assert api.StreamBarPlan is qmb.StreamBarPlan
    assert api.COMPLETED_BOUNDARY_ONLY is qmb.COMPLETED_BOUNDARY_ONLY
    assert "act_on_bar" in qmb.__all__
    assert "consume_same_slice" in qmb.__all__
    assert "StreamBarPlan" in qmb.__all__
    unsorted = UnderlyingSeries.try_create("eurusd", [_sample(_1M, 1), _sample(0, 2)])
    assert is_refusal(unsorted)
