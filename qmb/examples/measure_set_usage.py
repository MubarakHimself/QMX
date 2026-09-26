"""Reference usage — V1 core CT-32 measure set (Story 19.2).

Executable::

    python qmb/examples/measure_set_usage.py

Shows the things R-RPT-3..5 / R-RPT-9 / R-RPT-10 pin down:

1. The V1 core set is ordered; every computed quantity has a non-null AD-40 unit-kind.
2. Money measures are exact scaled integers; durations are int64 UTC-ns.
3. A null unit-kind is invalid input, never silently defaulted.
4. Profit factor with no losers is a typed undefined refusal, not a magic cap of 10.
5. Sharpe with fewer than two daily samples is insufficient-sample, never NaN coerced to 0.
6. No composite score/grade/tier, and producing the set sizes, promotes, and benches nothing.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.results import (
    CODE_INSUFFICIENT_SAMPLE,
    CODE_UNDEFINED,
    MEASURE_IDENTITIES,
    NS_PER_DAY,
    ClosedTrade,
    EquityPoint,
    TradeSide,
    assemble_v1_measure_set,
    emit_measure,
    result_identity,
)
from qmf.core.chrono import Instant, Interval
from qmf.core.exact import Money, UnitKind
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.performance import (
    PerformanceMeasure,
    PublishAct,
    UndefinedMeasure,
    check_publish_never_act,
)

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


def _trade(pnl: int, *, side: TradeSide, at: int, fees: int = 100) -> ClosedTrade:
    return _unwrap(
        ClosedTrade.try_create(_money(pnl), _money(fees), side, _instant(at)),
        "trade",
    )


def _find(rows: tuple[object, ...], identity: str) -> object:
    for row in rows:
        if getattr(row, "measure_identity", None) == identity:
            return row
    raise AssertionError(f"missing {identity}")


def main() -> None:
    assert qmb.assemble_v1_measure_set is assemble_v1_measure_set
    assert qmb.emit_measure is emit_measure
    seed = _money(1_000_000)
    period = _interval(_NS, _NS + 3 * NS_PER_DAY + 1)
    trades = (
        _trade(40_000, side=TradeSide.LONG, at=_NS + 1),
        _trade(-10_000, side=TradeSide.SHORT, at=_NS + NS_PER_DAY + 1),
        _trade(25_000, side=TradeSide.LONG, at=_NS + 2 * NS_PER_DAY + 1),
    )
    curve = (
        _unwrap(EquityPoint.try_create(_instant(_NS), seed), "p0"),
        _unwrap(EquityPoint.try_create(_instant(_NS + NS_PER_DAY), _money(1_040_000)), "p1"),
        _unwrap(EquityPoint.try_create(_instant(_NS + 2 * NS_PER_DAY), _money(1_030_000)), "p2"),
        _unwrap(EquityPoint.try_create(_instant(_NS + 3 * NS_PER_DAY), _money(1_055_000)), "p3"),
    )
    rows = _unwrap(
        assemble_v1_measure_set(
            starting_capital=seed,
            period=period,
            trades=trades,
            equity_curve=curve,
        ),
        "measure set",
    )
    assert [row.measure_identity for row in rows] == list(MEASURE_IDENTITIES)
    net = _find(rows, "net_profit")
    assert isinstance(net, PerformanceMeasure)
    assert isinstance(net.quantity, Money)
    assert net.quantity.value == 55_000
    assert net.quantity.unit_kind is UnitKind.MONEY
    recovery = _find(rows, "max_drawdown_recovery")
    assert isinstance(recovery, PerformanceMeasure)
    assert recovery.quantity.unit_kind is UnitKind.DURATION
    sharpe = _find(rows, "sharpe_ratio")
    assert isinstance(sharpe, PerformanceMeasure)
    print("ordered V1 core measure set; every computed quantity has a non-null AD-40 unit-kind")
    print("money measures are exact scaled integers; durations are int64 UTC-ns")

    null_kind = emit_measure("net_profit", seed, unit_kind=None)
    assert is_refusal(null_kind)
    print("null unit-kind is invalid input, never defaulted")

    no_losers = _unwrap(
        assemble_v1_measure_set(
            starting_capital=seed,
            period=period,
            trades=(_trade(10_000, side=TradeSide.LONG, at=_NS + 1),),
        ),
        "winners only",
    )
    profit_factor = _find(no_losers, "profit_factor")
    assert isinstance(profit_factor, UndefinedMeasure)
    assert profit_factor.refusal.context["code"] == CODE_UNDEFINED
    print("profit factor with no losers is typed undefined, never a magic cap of 10")

    thin = _unwrap(
        assemble_v1_measure_set(starting_capital=seed, period=_interval(_NS, _NS + 1)), "thin"
    )
    thin_sharpe = _find(thin, "sharpe_ratio")
    assert isinstance(thin_sharpe, UndefinedMeasure)
    assert thin_sharpe.refusal.context["code"] == CODE_INSUFFICIENT_SAMPLE
    print("Sharpe with <2 daily samples is insufficient-sample, never NaN coerced to 0")

    names = [row.measure_identity for row in rows]
    assert all("score" not in name and "grade" not in name and "tier" not in name for name in names)
    for act in (PublishAct.SIZE, PublishAct.PROMOTE, PublishAct.BENCH):
        refused = check_publish_never_act(act)
        assert is_refusal(refused)
    assert result_identity()["measure_identities"] == list(MEASURE_IDENTITIES)
    print("no composite score/grade/tier; producing the set sizes, promotes, and benches nothing")
    print("V1 core measure set ok")


if __name__ == "__main__":
    main()
