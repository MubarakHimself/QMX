"""Story 19.4 — chart series as data, never images."""

from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
from typing import TypeVar, cast

from qmb.doors import api
from qmb.results import (
    BENCHMARK_KEY,
    CHART_SERIES_IN_IDENTITY,
    DISPLAY_DOWNSAMPLE_IN_IDENTITY,
    DISPLAY_SAMPLER_IDENTITY,
    NO_BENCHMARK_DECLARED,
    OMIT_SINGLE_UNLEVERAGED,
    TOP_WORST_PERIODS,
    V1_CHART_SERIES_NAMES,
    ClosedTrade,
    EquityPoint,
    HoldingMark,
    TradeSide,
    assemble_v1_chart_set,
    downsample_chart_series,
    result_identity,
)
from qmf.core.chrono import Instant, Interval, WriterId
from qmf.core.exact import ExactRational, Money, Quantity, UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.data.journal import JournalEvent, JournalEventType
from qmf.risk.door import Direction

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _money(value: int, scale: int = 2) -> Money:
    return _ok(Money.try_create(value, "USD", scale))


def _qty(value: int) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", 0))


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _interval(start_ns: int, end_ns: int) -> Interval:
    return _ok(Interval.try_create(_instant(start_ns), _instant(end_ns)))


def _month_ns(year: int, month: int, day: int = 15) -> int:
    start = datetime(1970, 1, 1, tzinfo=timezone.utc)
    moment = datetime(year, month, day, tzinfo=timezone.utc)
    return int((moment - start).total_seconds()) * 1_000_000_000


def _trade(
    pnl: int,
    *,
    fees: int = 0,
    side: TradeSide = TradeSide.LONG,
    at: int = _NS,
) -> ClosedTrade:
    return _ok(ClosedTrade.try_create(_money(pnl), _money(fees), side, _instant(at)))


def _point(at: int, equity: int) -> EquityPoint:
    return _ok(EquityPoint.try_create(_instant(at), _money(equity)))


def _holding(
    at: int,
    instrument: str,
    *,
    quantity: int = 1,
    direction: Direction = Direction.LONG,
    market_value: int,
    notional: int | None = None,
) -> HoldingMark:
    gross = _money(notional) if notional is not None else None
    return _ok(
        HoldingMark.try_create(
            _instant(at),
            instrument,
            _qty(quantity),
            direction,
            _money(market_value),
            gross,
        )
    )


def _keys(payload: object) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        body = cast("dict[str, object]", payload)
        found.update(body)
        for item in body.values():
            found.update(_keys(item))
    elif isinstance(payload, list):
        for item in cast("list[object]", payload):
            found.update(_keys(item))
    return found


def test_series_shape_is_name_unit_kind_points_never_image() -> None:
    seed = _money(1_000_000)
    period = _interval(_NS, _NS + 3)
    charts = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=period,
            trades=(_trade(50_000, at=_NS + 1), _trade(-20_000, at=_NS + 2)),
        )
    )
    payload = charts.as_data()
    assert payload["canonical_payload"] == "series-data"
    assert payload["in_identity"] is False
    assert payload["ad10_excluded"] is True
    names = [series.name for series in charts.series]
    for required in V1_CHART_SERIES_NAMES:
        assert required in names
    equity = charts.series_named("equity")
    assert equity is not None
    assert equity.unit_kind is UnitKind.MONEY
    assert all(point.t.value_ns == point.as_data()["t"] for point in equity.points)
    assert all(isinstance(point.as_data()["t"], int) for point in equity.points)
    assert all(isinstance(point.v, Money) for point in equity.points)
    cumulative = charts.series_named("cumulative_returns")
    assert cumulative is not None
    assert cumulative.unit_kind is UnitKind.DIMENSIONLESS_RATIO
    assert all(isinstance(point.v, ExactRational) for point in cumulative.points)
    keys = _keys(payload)
    for banned in ("color", "style", "bin", "bins", "png", "image", "base64", "svg"):
        assert banned not in keys
    assert "downsample" not in payload
    assert "sampler_identity" not in payload
    png = assemble_v1_chart_set(
        starting_capital=seed,
        period=period,
        equity_curve=b"\x89PNG\r\n",
    )
    assert is_refusal(png)
    assert png.category is RefusalCategory.INVALID_INPUT
    colored = assemble_v1_chart_set(
        starting_capital=seed,
        period=period,
        equity_curve=({"at": _instant(_NS), "equity": seed, "color": "#818CF8"},),
    )
    assert is_refusal(colored)
    assert colored.context["field"] == "renderer"


def test_v1_set_derives_from_run_record_and_matches_measures() -> None:
    seed = _money(1_000_000)
    period = _interval(_NS, _NS + 4)
    trades = (
        _trade(40_000, side=TradeSide.LONG, at=_NS + 1),
        _trade(-10_000, side=TradeSide.SHORT, at=_NS + 2),
    )
    curve = (
        _point(_NS, 1_000_000),
        _point(_NS + 1, 1_040_000),
        _point(_NS + 2, 1_030_000),
        _point(_NS + 4, 1_030_000),
    )
    charts = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=period,
            trades=trades,
            equity_curve=curve,
        )
    )
    equity = charts.series_named("equity")
    assert equity is not None
    assert isinstance(equity.points[-1].v, Money)
    assert equity.points[-1].v.value == 1_030_000
    reconstructed = _ok(assemble_v1_chart_set(starting_capital=seed, period=period, trades=trades))
    rebuilt = reconstructed.series_named("equity")
    assert rebuilt is not None
    assert isinstance(rebuilt.points[-1].v, Money)
    assert rebuilt.points[-1].v.value == equity.points[-1].v.value
    drawdown = charts.series_named("drawdown")
    underwater = charts.series_named("underwater")
    assert drawdown is not None and underwater is not None
    assert all(
        dd.v.as_fraction() == -under.v.as_fraction()
        for dd, under in zip(drawdown.points, underwater.points, strict=True)
    )
    assert charts.trade_pnl_distribution.unit_kind is UnitKind.MONEY
    pnls = charts.trade_pnl_distribution.values
    assert len(pnls) == 2
    assert isinstance(pnls[0], Money) and isinstance(pnls[1], Money)
    assert pnls[0].value == 40_000
    assert pnls[1].value == -10_000
    assert "bin" not in charts.trade_pnl_distribution.as_data()
    assert "bins" not in charts.trade_pnl_distribution.as_data()


def test_top_five_worst_periods_table() -> None:
    seed = _money(1_200_000)
    times = [_NS + index for index in range(13)]
    equities = (
        1_200_000,
        1_000_000,
        1_200_000,
        1_100_000,
        1_200_000,
        900_000,
        1_200_000,
        800_000,
        1_200_000,
        700_000,
        1_200_000,
        1_150_000,
        1_200_000,
    )
    curve = tuple(_point(at, equity) for at, equity in zip(times, equities, strict=True))
    charts = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=_interval(times[0], times[-1]),
            equity_curve=curve,
        )
    )
    assert len(charts.worst_periods) == TOP_WORST_PERIODS
    ordered = [row.max_drawdown.as_fraction() for row in charts.worst_periods]
    assert ordered == sorted(ordered, reverse=True)
    worst = charts.worst_periods[0]
    assert worst.start.value_ns == times[8]
    assert worst.bottom.value_ns == times[9]
    assert worst.recovery.value_ns == times[10]
    assert worst.max_drawdown.as_fraction() == Fraction(1_200_000 - 700_000, 1_200_000)
    row = worst.as_data()
    assert set(row) == {"start", "bottom", "recovery", "max_drawdown"}


def test_monthly_returns_grid_and_raw_distributions() -> None:
    seed = _money(1_000_000)
    n0 = _month_ns(2023, 11, 1)
    n1 = _month_ns(2023, 12, 1)
    n2 = _month_ns(2024, 1, 1)
    n3 = _month_ns(2024, 2, 1)
    curve = (
        _point(n0, 1_000_000),
        _point(n1, 1_100_000),
        _point(n2, 1_210_000),
        _point(n3, 1_089_000),
    )
    charts = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=_interval(n0, n3),
            equity_curve=curve,
        )
    )
    cells = {(cell.year, cell.month): cell.value.as_fraction() for cell in charts.monthly_returns}
    assert (2023, 12) in cells
    assert (2024, 1) in cells
    assert cells[(2023, 12)] == Fraction(1_100_000 - 1_000_000, 1_000_000)
    years = {row.year for row in charts.annual_returns}
    assert 2023 in years and 2024 in years
    dist = charts.monthly_return_distribution
    assert dist.unit_kind is UnitKind.DIMENSIONLESS_RATIO
    assert "bin" not in dist.as_data()
    assert len(dist.values) == len(charts.monthly_returns)


def test_holdings_omitted_unless_multi_instrument_or_leveraged() -> None:
    seed = _money(1_000_000)
    period = _interval(_NS, _NS + 2)
    single = _ok(assemble_v1_chart_set(starting_capital=seed, period=period))
    omitted = {row.name: row.reason for row in single.omitted}
    for family in ("holdings", "exposure", "allocation", "leverage"):
        assert omitted[family] == OMIT_SINGLE_UNLEVERAGED
    assert all(not series.name.startswith("holdings.") for series in single.series)
    marks = (
        _holding(_NS + 1, "eurusd", market_value=400_000, notional=400_000),
        _holding(_NS + 1, "gbpusd", market_value=300_000, notional=300_000),
    )
    multi = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=period,
            equity_curve=(_point(_NS, 1_000_000), _point(_NS + 1, 1_000_000)),
            holdings=marks,
        )
    )
    names = [series.name for series in multi.series]
    assert "holdings.eurusd" in names
    assert "holdings.gbpusd" in names
    assert "exposure.eurusd" in names
    assert "allocation.gbpusd" in names
    assert all(row.name not in {"holdings", "exposure", "allocation"} for row in multi.omitted)
    leveraged = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=period,
            equity_curve=(_point(_NS, 1_000_000), _point(_NS + 1, 1_000_000)),
            holdings=(_holding(_NS + 1, "eurusd", market_value=400_000, notional=2_000_000),),
            leveraged=True,
        )
    )
    assert leveraged.series_named("leverage") is not None
    empty_lev = _ok(assemble_v1_chart_set(starting_capital=seed, period=period, leveraged=True))
    assert {row.name: row.reason for row in empty_lev.omitted}["leverage"] != ""
    assert empty_lev.series_named("leverage") is None


def test_benchmark_relative_omitted_with_explicit_note() -> None:
    seed = _money(1_000_000)
    period = _interval(_NS, _NS + 1)
    none = _ok(assemble_v1_chart_set(starting_capital=seed, period=period))
    notes = {row.name: row.reason for row in none.omitted}
    assert notes["cumulative_returns_benchmark"] == NO_BENCHMARK_DECLARED
    assert notes["alpha"] == NO_BENCHMARK_DECLARED
    assert notes["beta"] == NO_BENCHMARK_DECLARED
    assert none.benchmark_identity is None
    declared = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=period,
            equity_curve=(_point(_NS, 1_000_000), _point(_NS + 1, 1_100_000)),
            benchmark="spx",
            benchmark_curve=(_point(_NS, 1_000_000), _point(_NS + 1, 1_050_000)),
        )
    )
    assert declared.benchmark_identity == "spx"
    bench = declared.series_named("cumulative_returns_benchmark")
    assert bench is not None
    assert bench.unit_kind is UnitKind.DIMENSIONLESS_RATIO
    assert all(row.reason != NO_BENCHMARK_DECLARED for row in declared.omitted)
    assert BENCHMARK_KEY == "benchmark"


def test_display_downsample_is_derivative_excluded_from_identity() -> None:
    seed = _money(1_000_000)
    curve = tuple(_point(_NS + index, 1_000_000 + index * 1000) for index in range(8))
    charts = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=_interval(_NS, _NS + 7),
            equity_curve=curve,
        )
    )
    equity = charts.series_named("equity")
    assert equity is not None
    derived = _ok(downsample_chart_series(equity, stride=2))
    assert derived.sampler_identity == DISPLAY_SAMPLER_IDENTITY
    assert derived.stride == 2
    assert len(derived.series.points) < len(equity.points)
    assert derived.series.points[0].t == equity.points[0].t
    assert derived.series.points[-1].t == equity.points[-1].t
    assert not hasattr(derived, "fp1_identity")
    assert not hasattr(charts, "fp1_identity")
    display = derived.as_data()
    assert display["ad10_excluded"] is True
    assert display["in_identity"] is False
    assert display["sampler_identity"] == DISPLAY_SAMPLER_IDENTITY
    canonical = charts.as_data()
    assert "sampler_identity" not in canonical
    assert "downsample" not in canonical
    identity = result_identity()
    assert identity["chart_series_in_identity"] is False
    assert identity["display_downsample_in_identity"] is False
    assert CHART_SERIES_IN_IDENTITY is False
    assert DISPLAY_DOWNSAMPLE_IN_IDENTITY is False
    assert DISPLAY_SAMPLER_IDENTITY not in identity.values()
    refused = downsample_chart_series(equity, sampler_identity="lttb")
    assert is_refusal(refused)
    assert refused.context["field"] == "sampler_identity"


def test_journal_fills_feed_charts_parallel_log_refused() -> None:
    seed = _money(1_000_000)
    period = _interval(_NS, _NS + 2)
    writer = _ok(WriterId.try_create("qmb-replay", "risk", "fills", "boot-1"))
    fill = _ok(
        JournalEvent.try_create(
            event_type=JournalEventType.FILL,
            writer=writer,
            sequence=0,
            instant=_NS + 1,
            world=World.REPLAY,
            payload={
                "realized_pnl": _money(25_000),
                "fees": _money(100),
                "side": TradeSide.LONG.value,
            },
        )
    )
    charts = _ok(
        assemble_v1_chart_set(
            starting_capital=seed,
            period=period,
            journal_events=(fill,),
        )
    )
    pnls = charts.trade_pnl_distribution.values
    assert len(pnls) == 1
    assert isinstance(pnls[0], Money)
    assert pnls[0].value == 25_000
    parallel = assemble_v1_chart_set(
        starting_capital=seed,
        period=period,
        journal_events=({"pnl": 1, "log": "bespoke"},),
    )
    assert is_refusal(parallel)
    assert parallel.context["field"] == "journal_events"


def test_door_exports_the_chart_series_surface() -> None:
    assert api.assemble_v1_chart_set is qmb.assemble_v1_chart_set
    assert api.downsample_chart_series is qmb.downsample_chart_series
    assert api.ChartSeries is qmb.ChartSeries
    assert api.ChartSet is qmb.ChartSet
    assert api.HoldingMark is qmb.HoldingMark
    assert api.DISPLAY_SAMPLER_IDENTITY == DISPLAY_SAMPLER_IDENTITY
    assert api.NO_BENCHMARK_DECLARED == NO_BENCHMARK_DECLARED
    assert api.V1_CHART_SERIES_NAMES == V1_CHART_SERIES_NAMES
    assert api.DISPLAY_DOWNSAMPLE_IN_IDENTITY is False
    assert api.CHART_SERIES_IN_IDENTITY is False
