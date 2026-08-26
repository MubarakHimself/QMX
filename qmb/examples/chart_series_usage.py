"""Reference usage — chart series as data, never images (Story 19.4).

Executable::

    python qmb/examples/chart_series_usage.py

Shows the things R-RPT-11..15 / B-10 pin down:

1. Every chart is ``{name, unit_kind, points:[{t, v}]}`` with int64 UTC-ns ``t``
   and unit-kinded ``v`` (exact money or exact-rational ratio).
2. No image, base64, PNG, color, style, or histogram bin is in the data.
3. The V1 set derives from the run's own position/order/journal record.
4. Holdings/exposure/allocation/leverage are omitted on a single-instrument
   unleveraged run rather than faked.
5. Benchmark-relative series are omitted with ``no benchmark declared``.
6. Display downsample carries a declared sampler identity and is AD-10-excluded.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.results import (
    DISPLAY_SAMPLER_IDENTITY,
    NO_BENCHMARK_DECLARED,
    V1_CHART_SERIES_NAMES,
    ClosedTrade,
    EquityPoint,
    HoldingMark,
    TradeSide,
    assemble_v1_chart_set,
    downsample_chart_series,
    result_identity,
)
from qmf.core.chrono import Instant, Interval
from qmf.core.exact import Money, Quantity, UnitKind
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.door import Direction

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _money(value: int) -> Money:
    return _unwrap(Money.try_create(value, "USD", 2), "money")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _interval(start: int, end: int) -> Interval:
    return _unwrap(Interval.try_create(_instant(start), _instant(end)), "interval")


def _trade(pnl: int, *, at: int, side: TradeSide = TradeSide.LONG) -> ClosedTrade:
    return _unwrap(
        ClosedTrade.try_create(_money(pnl), _money(100), side, _instant(at)),
        "trade",
    )


def main() -> None:
    assert qmb.assemble_v1_chart_set is assemble_v1_chart_set
    assert qmb.downsample_chart_series is downsample_chart_series
    seed = _money(1_000_000)
    period = _interval(_NS, _NS + 4)
    trades = (
        _trade(40_000, at=_NS + 1),
        _trade(-15_000, at=_NS + 2, side=TradeSide.SHORT),
    )
    curve = (
        _unwrap(EquityPoint.try_create(_instant(_NS), seed), "p0"),
        _unwrap(EquityPoint.try_create(_instant(_NS + 1), _money(1_040_000)), "p1"),
        _unwrap(EquityPoint.try_create(_instant(_NS + 2), _money(1_025_000)), "p2"),
        _unwrap(EquityPoint.try_create(_instant(_NS + 4), _money(1_025_000)), "p3"),
    )
    charts = _unwrap(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=period,
            trades=trades,
            equity_curve=curve,
        ),
        "chart set",
    )
    payload = charts.as_data()
    names = [series.name for series in charts.series]
    assert all(name in names for name in V1_CHART_SERIES_NAMES)
    equity = charts.series_named("equity")
    assert equity is not None
    assert equity.unit_kind is UnitKind.MONEY
    point = equity.points[0].as_data()
    assert set(point) == {"t", "v"}
    assert isinstance(point["t"], int)
    for banned in ("color", "style", "bin", "png", "image", "base64"):
        assert banned not in payload
    assert payload["canonical_payload"] == "series-data"
    print("each chart is {name, unit_kind, points:[{t, v}]}; t is int64 UTC-ns")
    print("no image, base64, PNG, color, style, or histogram bin in the data")

    omitted = {row.name: row.reason for row in charts.omitted}
    assert omitted["holdings"] == "single-instrument unleveraged run"
    assert omitted["cumulative_returns_benchmark"] == NO_BENCHMARK_DECLARED
    print("single-instrument unleveraged run omits holdings rather than faking them")
    print("benchmark-relative series omitted with 'no benchmark declared'")

    qty = _unwrap(Quantity.try_create(1, "lot", 0), "qty")
    multi = _unwrap(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=period,
            equity_curve=curve,
            holdings=(
                _unwrap(
                    HoldingMark.try_create(
                        _instant(_NS + 1),
                        "eurusd",
                        qty,
                        Direction.LONG,
                        _money(400_000),
                    ),
                    "h1",
                ),
                _unwrap(
                    HoldingMark.try_create(
                        _instant(_NS + 1),
                        "gbpusd",
                        qty,
                        Direction.SHORT,
                        _money(-250_000),
                    ),
                    "h2",
                ),
            ),
        ),
        "multi",
    )
    assert multi.series_named("holdings.eurusd") is not None
    assert multi.series_named("allocation.gbpusd") is not None
    print("multi-instrument run reconstructs holdings/exposure/allocation from the position stream")

    derived = _unwrap(downsample_chart_series(equity, stride=2), "downsample")
    assert derived.sampler_identity == DISPLAY_SAMPLER_IDENTITY
    assert "sampler_identity" not in payload
    assert result_identity()["chart_series_in_identity"] is False
    assert result_identity()["display_downsample_in_identity"] is False
    print("display downsample is a derivative with declared sampler identity; AD-10-excluded")

    png = assemble_v1_chart_set(starting_capital=seed, period=period, equity_curve=b"\x89PNG")
    assert is_refusal(png)
    print("PNG/base64 is refused as canonical payload")
    print("chart series as data ok")


if __name__ == "__main__":
    main()
