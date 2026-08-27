"""L1 minimal pure-unit laws for Epic 19 (U1-U4).

Laws not reachable at L3: exact money, the undefined-vs-zero distinction, null
unit-kind refusal, and the canonical chart-point shape. Each names its failing
counter-case; U1 uses hypothesis for the exactness property.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from conftest import equity, interval, money, trade

from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.performance import PerformanceMeasure, UndefinedMeasure
from qmb.results.measures import (
    CODE_INSUFFICIENT_SAMPLE,
    CODE_UNDEFINED,
    NS_PER_DAY,
    assemble_v1_measure_set,
    emit_measure,
)

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

NS = 1_700_000_000_000_000_000


def _slot(measures: tuple[object, ...], identity: str) -> object:
    for row in measures:
        ident = getattr(row, "measure_identity", None)
        if ident == identity:
            return row
    raise AssertionError(f"{identity} not in measure set")


# --- U1: money is an exact scaled integer, never binary float [R10] ----------


@settings(max_examples=200)
@given(units=st.integers(min_value=-10**15, max_value=10**15), scale=st.integers(0, 18))
def test_u1_money_is_exact_scaled_integer(units: int, scale: int) -> None:
    m = money(units, scale)
    # The magnitude is exactly value / 10**scale — no binary-float drift.
    assert m.as_fraction() == Fraction(units, 10**scale)
    ident = m.fp1_identity()
    assert Fraction(int(ident["num"]), int(ident["den"])) == Fraction(units, 10**scale)
    # identity carries integer num/den, never a float byte
    assert isinstance(ident["num"], int) and isinstance(ident["den"], int)


def test_u1_binary_float_money_is_refused_not_coerced() -> None:
    # Counter-case: a float on the money path must be a typed refusal, not silently
    # coerced (the refuse arm is reachable).
    refused = Money.try_create(1.5, "USD", 2)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_u1_money_measure_reflects_exact_integer_sum() -> None:
    # net_profit over exact trades is exact Money, not a float aggregate.
    trades = (trade(10_000, at_ns=NS + NS_PER_DAY), trade(-2_500, at_ns=NS + 2 * NS_PER_DAY))
    measures = assemble_v1_measure_set(
        starting_capital=money(100_000), period=interval(), trades=trades
    )
    net = _slot(measures.value, "net_profit")
    assert isinstance(net, PerformanceMeasure)
    assert isinstance(net.quantity, Money)
    assert net.quantity.as_fraction() == Fraction(10_000 - 2_500, 100)


# --- U2: undefined != zero; never a cap-of-10, never NaN->0 [R12] ------------


def test_u2_profit_factor_with_no_losing_trades_is_undefined_not_ten() -> None:
    trades = (trade(5_000), trade(3_000))  # two wins, zero losses
    measures = assemble_v1_measure_set(
        starting_capital=money(100_000), period=interval(), trades=trades
    )
    pf = _slot(measures.value, "profit_factor")
    # A reader branches on TYPE, not magnitude: no losing trades => UndefinedMeasure,
    # never a magic PerformanceMeasure(10) and never a coerced 0.
    assert isinstance(pf, UndefinedMeasure)
    assert not isinstance(pf, PerformanceMeasure)
    assert pf.refusal.context["code"] == CODE_UNDEFINED


def test_u2_sharpe_with_under_two_samples_is_insufficient_sample() -> None:
    # A single daily equity point => fewer than 2 daily return samples.
    curve = (equity(100_000, NS),)
    measures = assemble_v1_measure_set(
        starting_capital=money(100_000), period=interval(NS, NS + 1000), equity_curve=curve
    )
    sharpe = _slot(measures.value, "sharpe_ratio")
    assert isinstance(sharpe, UndefinedMeasure)
    assert sharpe.refusal.context["code"] in {CODE_INSUFFICIENT_SAMPLE, CODE_UNDEFINED}


def test_u2_a_genuine_zero_is_a_measure_not_undefined() -> None:
    # net_profit == 0 must be a real PerformanceMeasure(0), distinguishable from
    # an undefined metric — the whole point of the undefined/zero split.
    measures = assemble_v1_measure_set(
        starting_capital=money(100_000), period=interval(), trades=()
    )
    net = _slot(measures.value, "net_profit")
    assert isinstance(net, PerformanceMeasure)
    assert net.quantity.as_fraction() == Fraction(0)


# --- U3: a null unit-kind is an invalid-input refusal, never defaulted [R9] --


def test_u3_null_unit_kind_is_refused_never_defaulted() -> None:
    accepted = emit_measure("net_profit", money(10), unit_kind=UnitKind.MONEY)
    assert is_ok(accepted)  # accept arm reachable

    refused = emit_measure("net_profit", money(10), unit_kind=None)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "unit_kind"

    # The exact-value layer refuses a null unit-kind too, never a silent default.
    null_rational = ExactRational.try_create(1, 2, None)
    assert is_refusal(null_rational)
    assert null_rational.context["field"] == "unit_kind"


def test_u3_declared_unit_kind_must_match_quantity() -> None:
    # A mismatched declared unit-kind is caught, not silently overwritten.
    refused = emit_measure("net_profit", money(10), unit_kind=UnitKind.COUNT)
    assert is_refusal(refused)
    assert refused.context["field"] == "unit_kind"


# --- U4: a chart point is exactly {t, v}; no color/style/bin [R18, R19] ------


def test_u4_series_point_shape_is_t_and_v_only() -> None:
    from qmb.results.charts import assemble_v1_chart_set

    curve = tuple(equity(100_000 + i * 1000, NS + i * NS_PER_DAY) for i in range(4))
    chart_set = assemble_v1_chart_set(
        starting_capital=money(100_000), period=interval(NS, NS + 4 * NS_PER_DAY), equity_curve=curve
    )
    equity_series = chart_set.value.series_named("equity")
    assert equity_series is not None
    assert equity_series.points
    for point in equity_series.points:
        data = point.as_data()
        assert set(data.keys()) == {"t", "v"}
        assert isinstance(data["t"], int)  # int64 UTC-ns
        # v carries a unit-kind (exact), never a bare float
        assert isinstance(data["v"], dict)
        assert data["v"]["unit_kind"] in {member.value for member in UnitKind}
    # No renderer concern leaks into the series payload.
    series_data = equity_series.as_data()
    assert "color" not in series_data and "style" not in series_data and "bin" not in series_data


def test_u4_a_banned_renderer_key_in_source_data_is_refused() -> None:
    from qmb.results.charts import assemble_v1_chart_set

    # Counter-case: a color/bin embedded in the run's own record is refused,
    # proving the banned-key gate can fail (never a silent strip).
    tainted = ({"at": None, "equity": None, "color": "red"},)
    refused = assemble_v1_chart_set(
        starting_capital=money(100_000), period=interval(), equity_curve=tainted
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "renderer"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
