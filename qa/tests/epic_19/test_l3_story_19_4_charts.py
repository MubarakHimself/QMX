"""L3 acceptance — Story 19.4: chart series as data, never images.

Requirements R18, R20-R23. Each chart is a machine-readable series derived from
the run's own ordered record; holdings/benchmark series are omitted (never faked)
when absent; a display downsample is AD-10-excluded from artifact identity.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from conftest import NS, NS_PER_DAY, config, equity, instant, interval, mint_args, money, ok, quantity

from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.refusal import is_refusal
from qmb.results.charts import (
    NO_BENCHMARK_DECLARED,
    OMIT_SINGLE_UNLEVERAGED,
    V1_CHART_SERIES_NAMES,
    ChartSet,
    DisplayDownsample,
    HoldingMark,
    assemble_v1_chart_set,
    downsample_chart_series,
)
from qmb.results.ct32 import mint_run_performance_result


def _curve(*rows: tuple[int, int]) -> tuple[object, ...]:
    return tuple(equity(units, NS + day * NS_PER_DAY) for day, units in rows)


def _basic_chart_set() -> ChartSet:
    curve = _curve((0, 100_000), (1, 105_000), (2, 102_000), (3, 108_000))
    return ok(assemble_v1_chart_set(
        starting_capital=money(100_000),
        period=interval(NS, NS + 4 * NS_PER_DAY),
        equity_curve=curve,
    ))


# --- A15: {name, unit_kind, points:[{t, v}]}, no image payload [R18] P0 ------


def test_a15_each_chart_is_a_unit_kinded_series_of_t_v_points() -> None:
    chart_set = _basic_chart_set()
    equity_series = chart_set.series_named("equity")
    assert equity_series is not None
    assert equity_series.unit_kind is UnitKind.MONEY
    assert equity_series.points
    for point in equity_series.points:
        data = point.as_data()
        assert set(data) == {"t", "v"}
        assert isinstance(data["t"], int)
        assert isinstance(point.v, (Money, ExactRational))  # exact, never a float
    # a ratio series carries the ratio unit-kind
    dd = chart_set.series_named("drawdown")
    assert dd is not None and dd.unit_kind is UnitKind.DIMENSIONLESS_RATIO


def test_a15_an_image_payload_is_never_the_canonical_series() -> None:
    # bytes are refused as an equity source
    refused_bytes = assemble_v1_chart_set(
        starting_capital=money(100_000), period=interval(), equity_curve=b"\x89PNG\r\n"
    )
    assert is_refusal(refused_bytes)
    # a base64/png string is refused too
    refused_b64 = assemble_v1_chart_set(
        starting_capital=money(100_000), period=interval(), equity_curve="data:image/png;base64,AAAA"
    )
    assert is_refusal(refused_b64)


# --- A16: V1 series + top-5 worst-periods from the run's own record [R20] P1 --


def test_a16_v1_core_series_and_worst_periods_derive_from_the_curve() -> None:
    # a curve that draws down 20% and recovers => one worst-period row
    curve = _curve((0, 100_000), (1, 80_000), (2, 100_000))
    chart_set = ok(assemble_v1_chart_set(
        starting_capital=money(100_000),
        period=interval(NS, NS + 3 * NS_PER_DAY),
        equity_curve=curve,
    ))
    names = {s.name for s in chart_set.series}
    assert set(V1_CHART_SERIES_NAMES).issubset(names)  # equity/cum/drawdown/underwater
    assert len(chart_set.worst_periods) <= 5
    assert len(chart_set.worst_periods) == 1
    row = chart_set.worst_periods[0]
    data = row.as_data()
    assert set(data) == {"start", "bottom", "recovery", "max_drawdown"}
    assert row.max_drawdown.as_fraction() == Fraction(1, 5)  # exact 20%, not a float
    # the equity series values equal the run's own curve (money(80_000) at scale 2
    # == $800.00), not a parallel log
    equity_series = chart_set.series_named("equity")
    assert equity_series.points[1].v.as_fraction() == money(80_000).as_fraction()


# --- A17: single unleveraged omits holdings; multi reconstructs [R21] P1 ------


def test_a17_single_instrument_unleveraged_omits_holdings_family() -> None:
    chart_set = ok(assemble_v1_chart_set(
        starting_capital=money(100_000),
        period=interval(NS, NS + 2 * NS_PER_DAY),
        equity_curve=_curve((0, 100_000), (1, 101_000)),
        instruments=("eurusd",),
        leveraged=False,
    ))
    omitted = {o.name: o.reason for o in chart_set.omitted}
    for name in ("holdings", "exposure", "allocation", "leverage"):
        assert omitted.get(name) == OMIT_SINGLE_UNLEVERAGED
        # never a faked empty series
        assert chart_set.series_named(name) is None


def test_a17_multi_instrument_reconstructs_holdings_from_the_stream() -> None:
    marks = (
        ok(HoldingMark.try_create(instant(NS + NS_PER_DAY), "eurusd", quantity(1), "long",
                                  money(50_000), money(50_000))),
        ok(HoldingMark.try_create(instant(NS + NS_PER_DAY), "gbpusd", quantity(1), "short",
                                  money(30_000), money(30_000))),
    )
    chart_set = ok(assemble_v1_chart_set(
        starting_capital=money(100_000),
        period=interval(NS, NS + 2 * NS_PER_DAY),
        equity_curve=_curve((0, 100_000), (1, 101_000)),
        holdings=marks,
        instruments=("eurusd", "gbpusd"),
        leveraged=False,
    ))
    names = {s.name for s in chart_set.series}
    assert "holdings.eurusd" in names and "holdings.gbpusd" in names
    assert any(n.startswith("exposure.") for n in names)


# --- A18: benchmark omitted-with-note when none; identity recorded when present [R22] P1


def test_a18_no_benchmark_is_omitted_with_note_never_faked() -> None:
    chart_set = _basic_chart_set()  # benchmark defaults to None
    assert chart_set.benchmark_identity is None
    reasons = {o.reason for o in chart_set.omitted}
    assert NO_BENCHMARK_DECLARED in reasons
    # no faked benchmark-relative series
    assert chart_set.series_named("cumulative_returns_benchmark") is None


def test_a18_declared_benchmark_identity_is_recorded() -> None:
    chart_set = ok(assemble_v1_chart_set(
        starting_capital=money(100_000),
        period=interval(NS, NS + 4 * NS_PER_DAY),
        equity_curve=_curve((0, 100_000), (1, 105_000)),
        benchmark="spx500",
    ))
    assert chart_set.benchmark_identity == "spx500"


# --- A19: display downsample is AD-10-excluded from artifact identity [R23] P1


def test_a19_downsample_declares_its_sampler_and_is_excluded_from_identity() -> None:
    series = _basic_chart_set().series_named("equity")
    down = ok(downsample_chart_series(series, stride=2))
    assert isinstance(down, DisplayDownsample)
    data = down.as_data()
    assert data["sampler_identity"] == "stride-nth"
    assert data["in_identity"] is False
    assert data["ad10_excluded"] is True
    # AD-10 exclusion is structural: the derivative carries no fp1_identity, so it
    # cannot be folded into the artifact fingerprint.
    assert not hasattr(down, "fp1_identity")
    assert not hasattr(ChartSet, "fp1_identity")


def test_a19_artifact_identity_is_invariant_to_charts_and_downsample() -> None:
    # the CT-32 artifact is minted independently of any chart set, so its identity
    # cannot move whether a downsample exists or not.
    body = ok(mint_run_performance_result(**mint_args(config()))).fp1_identity()
    import json

    flat = json.dumps(body).casefold()
    assert "chart" not in flat
    assert "downsample" not in flat
    assert "html" not in flat


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
