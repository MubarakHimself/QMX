"""Reference usage — completed-boundary bar derivation (Story 14.3).

Executable::

    python qmb/examples/completed_boundary_usage.py

Shows the things AR-57 / B-2 / FR-037 / SC-06 pin down:

1. Higher-BarSpec bars derive from the finest declared base stream.
2. A bar is emitted only on its completed (exclusive-end) boundary.
3. A forming bar is never visible or actionable; completeness is inspectable.
4. Same-slice bars and fills consume the same underlying series.
5. Look-ahead prevention ships regardless of GAP-0048.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.runloop import (
    COMPLETENESS_COMPLETED,
    COMPLETENESS_FORMING,
    LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048,
    DeclaredBarSpec,
    SeriesSample,
    StreamBarPlan,
    UnderlyingSeries,
    act_on_bar,
    consume_same_slice,
    finest_base,
    loop_identity,
    readable_bars,
    run_slice,
)
from qmf.core.chrono import Instant
from qmf.core.refusal import Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_SEC = 1_000_000_000
_1M = 60 * _SEC
_5M = 300 * _SEC


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _sample(ns: int, price: int) -> SeriesSample:
    return _unwrap(SeriesSample.try_create(_instant(ns), price, 1), "sample")


def higher_bars_from_finest_base() -> None:
    """5-minute bars fold from the 1-minute base and emit only at 5-minute close."""
    one_m = _unwrap(DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 60}), "1m")
    five_m = _unwrap(DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 300}), "5m")
    assert _unwrap(finest_base((one_m, five_m)), "finest").unit_size == 60
    plan = _unwrap(StreamBarPlan.try_create("eurusd", (one_m, five_m)), "plan")
    samples = [_sample(n * _1M, 10 + n) for n in range(6)]
    series = _unwrap(UnderlyingSeries.try_create("eurusd", samples), "series")
    mid = _unwrap(
        consume_same_slice(plan=plan, series=series, frontier=_instant(4 * _1M)),
        "forming 5m",
    )
    five_forming = [state for state in mid.forming if state.bar.bar_spec.unit_size == 300]
    assert len(five_forming) == 1
    assert five_forming[0].bar.completeness == COMPLETENESS_FORMING
    closed = _unwrap(
        consume_same_slice(plan=plan, series=series, frontier=_instant(_5M)),
        "completed 5m",
    )
    five_done = [bar for bar in closed.emitted if bar.bar_spec.unit_size == 300]
    assert len(five_done) == 1
    assert five_done[0].completeness == COMPLETENESS_COMPLETED
    assert five_done[0].close == 14
    assert five_done[0].series_fp1 == series.fingerprint.value


def forming_never_visible_or_actionable() -> None:
    """Completeness is inspectable; acting on a forming bar is a policy rejection."""
    plan = _unwrap(
        StreamBarPlan.try_create(
            "eurusd",
            (
                _unwrap(
                    DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 60}),
                    "1m",
                ),
                _unwrap(
                    DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 300}),
                    "5m",
                ),
            ),
        ),
        "plan",
    )
    series = _unwrap(
        UnderlyingSeries.try_create("eurusd", [_sample(n * _1M, 100 + n) for n in range(4)]),
        "series",
    )
    consumed = _unwrap(
        consume_same_slice(plan=plan, series=series, frontier=_instant(3 * _1M)),
        "consumed",
    )
    visible = _unwrap(readable_bars(consumed.emitted, consumed.forming), "readable")
    assert all(bar.completeness == COMPLETENESS_COMPLETED for bar in visible.bars)
    forming = consumed.forming[0]
    assert forming.visible_to_strategy is False
    assert forming.actionable is False
    refused = act_on_bar(forming)
    assert is_refusal(refused)
    assert refused.context["completeness"] == COMPLETENESS_FORMING


def same_series_for_bars_and_fills() -> None:
    """Bars and the intra-slice fill path cite one series fingerprint."""
    plan = _unwrap(
        StreamBarPlan.try_create(
            "eurusd",
            (_unwrap(DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 60}), "1m"),),
        ),
        "plan",
    )
    series = _unwrap(
        UnderlyingSeries.try_create("eurusd", [_sample(0, 10), _sample(_1M, 11)]),
        "series",
    )
    consumed = _unwrap(
        consume_same_slice(plan=plan, series=series, frontier=_instant(_1M)),
        "consumed",
    )
    assert consumed.series_fp1 == series.fingerprint.value
    assert consumed.fill_path[-1].price == 11
    assert all(bar.series_fp1 == series.fingerprint.value for bar in consumed.emitted)


def lookahead_independent_of_gap_0048() -> None:
    """Completed-boundary law is identity content and does not wait on GAP-0048."""
    assert LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048 is True
    identity = loop_identity()
    assert identity["completed_boundary_only"] is True
    assert identity["forming_bar_actionable"] is False
    assert identity["lookahead_prevention_independent_of_gap_0048"] is True
    plan = _unwrap(
        StreamBarPlan.try_create(
            "eurusd",
            (
                _unwrap(
                    DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 60}),
                    "1m",
                ),
                _unwrap(
                    DeclaredBarSpec.try_create({"kind": "time-interval", "seconds": 300}),
                    "5m",
                ),
            ),
        ),
        "plan",
    )
    series = _unwrap(
        UnderlyingSeries.try_create("eurusd", [_sample(n * _1M, 10 + n) for n in range(7)]),
        "series",
    )
    outcome = _unwrap(
        run_slice(
            ({"stream_id": "eurusd", "instant": _instant(4 * _1M), "closed": True},),
            stream_set=("eurusd",),
            series=series,
            bar_plan=plan,
        ),
        "slice",
    )
    assert "hold-forming:eurusd" in outcome.trace[0].actions
    five = [state.bar for state in outcome.forming if state.bar.bar_spec.unit_size == 300]
    assert five[0].sample_count == 5
    assert five[0].close == 14


def main() -> None:
    assert qmb.LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048 is True
    higher_bars_from_finest_base()
    print("higher BarSpec derived from finest base on completed boundary")
    forming_never_visible_or_actionable()
    print("forming bar not visible; acting is policy rejection")
    same_series_for_bars_and_fills()
    print("same-slice bars and fills share one series")
    lookahead_independent_of_gap_0048()
    print("look-ahead prevention ships regardless of GAP-0048")
    print("completed-boundary derivation ok")


if __name__ == "__main__":
    main()
