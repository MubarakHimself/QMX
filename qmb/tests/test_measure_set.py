"""Story 19.2 — ordered, unit-kinded, exact V1 core measure set."""

from __future__ import annotations

from typing import TypeVar, cast

from qmb.doors import api
from qmb.results import (
    ANNUALIZATION_PERIODS,
    CODE_INSUFFICIENT_SAMPLE,
    CODE_UNDEFINED,
    MEASURE_ARITHMETIC,
    MEASURE_IDENTITIES,
    METRIC_CONTRACT_FORMAT_VERSIONS,
    NS_PER_DAY,
    RATIO_DDOF,
    ClosedTrade,
    EquityPoint,
    TradeSide,
    assemble_v1_measure_set,
    emit_measure,
    result_identity,
)
from qmf.core.chrono import Instant, Interval
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import (
    PerformanceMeasure,
    PublishAct,
    UndefinedMeasure,
    check_publish_never_act,
)

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _money(value: int, scale: int = 2) -> Money:
    return _ok(Money.try_create(value, "USD", scale))


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _interval(start_ns: int = _NS, end_ns: int = _NS + NS_PER_DAY) -> Interval:
    return _ok(Interval.try_create(_instant(start_ns), _instant(end_ns)))


def _trade(
    pnl: int,
    *,
    fees: int = 0,
    side: TradeSide = TradeSide.LONG,
    at: int = _NS,
) -> ClosedTrade:
    return _ok(ClosedTrade.try_create(_money(pnl), _money(fees), side, _instant(at)))


def _slot(rows: tuple[object, ...], identity: str) -> object:
    for row in rows:
        if getattr(row, "measure_identity", None) == identity:
            return row
    raise AssertionError(f"missing measure {identity}")


def test_empty_run_is_ordered_unit_kinded_and_pins_arithmetic() -> None:
    rows = _ok(assemble_v1_measure_set(starting_capital=_money(0), period=_interval()))
    assert [row.measure_identity for row in rows] == list(MEASURE_IDENTITIES)
    payload = result_identity()
    assert payload["measure_identities"] == list(MEASURE_IDENTITIES)
    arithmetic = cast("dict[str, object]", payload["measure_arithmetic"])
    assert arithmetic["annualization_periods"] == ANNUALIZATION_PERIODS
    assert arithmetic["ddof"] == RATIO_DDOF
    assert arithmetic["rf_model"] == "zero"
    versions = cast("list[dict[str, object]]", payload["metric_contract_format_versions"])
    assert [item["measure_identity"] for item in versions] == list(MEASURE_IDENTITIES)
    assert all(item["version"] == 1 for item in versions)
    for row in rows:
        assert (
            row.metric_contract_format_version
            == METRIC_CONTRACT_FORMAT_VERSIONS[row.measure_identity]
        )
        if isinstance(row, PerformanceMeasure):
            assert row.quantity.unit_kind is not None
            assert row.quantity.unit_kind in UnitKind
        else:
            assert isinstance(row, UndefinedMeasure)
            assert row.refusal.context["code"] in {CODE_UNDEFINED, CODE_INSUFFICIENT_SAMPLE}


def test_null_unit_kind_is_invalid_input_never_defaulted() -> None:
    refused = emit_measure("net_profit", _money(1), unit_kind=None)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "unit_kind"
    missing = emit_measure("net_profit", None)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    raw = ExactRational.try_create(1, 1, None)
    assert is_refusal(raw)
    assert raw.context["field"] == "unit_kind"


def test_money_measures_are_exact_scaled_ints_and_durations_are_ns() -> None:
    rows = _ok(
        assemble_v1_measure_set(
            starting_capital=_money(1_000_000),
            period=_interval(_NS, _NS + NS_PER_DAY),
            trades=(
                _trade(50_000, fees=250, at=_NS + 1),
                _trade(-20_000, fees=250, side=TradeSide.SHORT, at=_NS + 2),
            ),
        )
    )
    net = _slot(rows, "net_profit")
    start = _slot(rows, "start_equity")
    end = _slot(rows, "end_equity")
    fees = _slot(rows, "fees")
    recovery = _slot(rows, "max_drawdown_recovery")
    assert isinstance(net, PerformanceMeasure)
    assert isinstance(start, PerformanceMeasure)
    assert isinstance(end, PerformanceMeasure)
    assert isinstance(fees, PerformanceMeasure)
    assert isinstance(recovery, PerformanceMeasure)
    assert isinstance(net.quantity, Money)
    assert net.quantity.value == 30_000
    assert net.quantity.currency == "USD"
    assert net.quantity.scale == 2
    assert isinstance(start.quantity, Money)
    assert start.quantity.value == 1_000_000
    assert isinstance(end.quantity, Money)
    assert end.quantity.value == 1_030_000
    assert isinstance(fees.quantity, Money)
    assert fees.quantity.value == 500
    assert recovery.quantity.unit_kind is UnitKind.DURATION
    assert isinstance(recovery.quantity, ExactRational)
    assert recovery.quantity.denominator == 1


def test_profit_factor_undefined_is_not_zero_or_cap_ten() -> None:
    winners = _ok(
        assemble_v1_measure_set(
            starting_capital=_money(1_000_000),
            period=_interval(),
            trades=(_trade(10_000, at=_NS + 1), _trade(5_000, at=_NS + 2)),
        )
    )
    undefined = _slot(winners, "profit_factor")
    assert isinstance(undefined, UndefinedMeasure)
    assert undefined.refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert undefined.refusal.context["code"] == CODE_UNDEFINED
    identity = undefined.fp1_identity()
    assert "quantity" not in identity
    refusal_body = cast("dict[str, object]", identity["refusal"])
    context = cast("dict[str, object]", refusal_body["context"])
    assert context["code"] == CODE_UNDEFINED
    losers = _ok(
        assemble_v1_measure_set(
            starting_capital=_money(1_000_000),
            period=_interval(),
            trades=(_trade(-10_000, at=_NS + 1), _trade(-5_000, at=_NS + 2)),
        )
    )
    zero = _slot(losers, "profit_factor")
    assert isinstance(zero, PerformanceMeasure)
    assert zero.quantity.as_fraction() == 0
    assert zero.quantity.unit_kind is UnitKind.DIMENSIONLESS_RATIO


def test_sharpe_insufficient_sample_is_not_nan_or_zero() -> None:
    rows = _ok(assemble_v1_measure_set(starting_capital=_money(1_000_000), period=_interval()))
    sharpe = _slot(rows, "sharpe_ratio")
    sortino = _slot(rows, "sortino_ratio")
    assert isinstance(sharpe, UndefinedMeasure)
    assert isinstance(sortino, UndefinedMeasure)
    assert sharpe.refusal.context["code"] == CODE_INSUFFICIENT_SAMPLE
    assert sortino.refusal.context["code"] == CODE_INSUFFICIENT_SAMPLE
    curve = (
        _ok(EquityPoint.try_create(_instant(_NS), _money(1_000_000))),
        _ok(EquityPoint.try_create(_instant(_NS + NS_PER_DAY), _money(1_010_000))),
        _ok(EquityPoint.try_create(_instant(_NS + 2 * NS_PER_DAY), _money(1_000_000))),
        _ok(EquityPoint.try_create(_instant(_NS + 3 * NS_PER_DAY), _money(1_030_000))),
    )
    enough = _ok(
        assemble_v1_measure_set(
            starting_capital=_money(1_000_000),
            period=_interval(_NS, _NS + 3 * NS_PER_DAY + 1),
            equity_curve=curve,
        )
    )
    computed = _slot(enough, "sharpe_ratio")
    assert isinstance(computed, PerformanceMeasure)
    assert computed.quantity.unit_kind is UnitKind.DIMENSIONLESS_RATIO
    assert computed.quantity.as_fraction() != 0


def test_win_rate_split_streaks_and_counts() -> None:
    rows = _ok(
        assemble_v1_measure_set(
            starting_capital=_money(1_000_000),
            period=_interval(),
            trades=(
                _trade(10_000, side=TradeSide.LONG, at=_NS + 1),
                _trade(4_000, side=TradeSide.LONG, at=_NS + 2),
                _trade(-3_000, side=TradeSide.SHORT, at=_NS + 3),
                _trade(6_000, side=TradeSide.SHORT, at=_NS + 4),
            ),
        )
    )
    total = _slot(rows, "total_trades")
    wins = _slot(rows, "winning_trades")
    losses = _slot(rows, "losing_trades")
    win_rate = _slot(rows, "win_rate")
    long_rate = _slot(rows, "long_win_rate")
    short_rate = _slot(rows, "short_win_rate")
    win_streak = _slot(rows, "winning_streak")
    loss_streak = _slot(rows, "losing_streak")
    factor = _slot(rows, "profit_factor")
    assert isinstance(total, PerformanceMeasure)
    assert total.quantity.as_fraction() == 4
    assert isinstance(wins, PerformanceMeasure)
    assert wins.quantity.as_fraction() == 3
    assert isinstance(losses, PerformanceMeasure)
    assert losses.quantity.as_fraction() == 1
    assert isinstance(win_rate, PerformanceMeasure)
    assert isinstance(win_rate.quantity, ExactRational)
    assert win_rate.quantity.numerator == 3
    assert win_rate.quantity.denominator == 4
    assert isinstance(long_rate, PerformanceMeasure)
    assert long_rate.quantity.as_fraction() == 1
    assert isinstance(short_rate, PerformanceMeasure)
    assert isinstance(short_rate.quantity, ExactRational)
    assert short_rate.quantity.numerator == 1
    assert short_rate.quantity.denominator == 2
    assert isinstance(win_streak, PerformanceMeasure)
    assert win_streak.quantity.as_fraction() == 2
    assert isinstance(loss_streak, PerformanceMeasure)
    assert loss_streak.quantity.as_fraction() == 1
    assert isinstance(factor, PerformanceMeasure)
    assert isinstance(factor.quantity, ExactRational)
    assert factor.quantity.as_fraction() != 10


def test_no_composite_score_and_measurement_never_acts() -> None:
    rows = _ok(assemble_v1_measure_set(starting_capital=_money(1_000_000), period=_interval()))
    names = [row.measure_identity for row in rows]
    for banned in ("score", "grade", "tier", "rating", "composite"):
        assert all(banned not in name for name in names)
    for act in PublishAct:
        refused = check_publish_never_act(act)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
    assert is_refusal(emit_measure("composite-score", _money(1)))
    assert "score" not in result_identity()
    assert "grade" not in result_identity()
    assert MEASURE_ARITHMETIC["rounding"] == "half-even"


def test_door_exports_the_measure_set_surface() -> None:
    assert api.assemble_v1_measure_set is qmb.assemble_v1_measure_set
    assert api.emit_measure is qmb.emit_measure
    assert api.ClosedTrade is qmb.ClosedTrade
    assert api.EquityPoint is qmb.EquityPoint
    assert api.TradeSide is qmb.TradeSide
    assert api.UndefinedMeasure is qmb.UndefinedMeasure
    assert api.MEASURE_IDENTITIES == MEASURE_IDENTITIES
    assert api.CODE_UNDEFINED == CODE_UNDEFINED
    assert api.CODE_INSUFFICIENT_SAMPLE == CODE_INSUFFICIENT_SAMPLE
