"""Story 17.4 — cost port exact-integer itemized commissions."""

from __future__ import annotations

from typing import TypeVar

from qmb.doors import api
from qmb.execution import (
    COST_ADAPTER_CATALOG,
    COST_ADAPTER_NOTIONAL_MINIMUM,
    COST_ADAPTER_PER_LOT,
    COST_ADAPTER_PERCENT_OF_NOTIONAL,
    COST_ADAPTER_ZERO,
    COST_COMPONENT_COMMISSION,
    COST_CONTENT_DEFERRED_TO,
    COST_MODELS,
    TAINT_OPTIMISTIC,
    CommissionCalibration,
    CostPort,
    Fill,
    NotionalProportionalMinimumCostAdapter,
    PartialFill,
    PercentOfNotionalCostAdapter,
    PerLotCostAdapter,
    ZeroCostAdapter,
    charge_commission,
    cost_identity,
    fingerprint_cost,
)
from qmf.core.exact import ExactRational, Money, Price, Quantity, UnitKind, ValueFactor
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.door import Direction

import qmb

T = TypeVar("T")

_VENUE = "venue-replay"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value=_VENUE), symbol="EURUSD")


def _price(value: int) -> Price:
    return _ok(Price.try_create(value, _instrument(), 5))


def _qty(value: int) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", 0))


def _ratio(num: int, den: int) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


def _money(value: int, currency: str = "USD", scale: int = 2) -> Money:
    return _ok(Money.try_create(value, currency, scale))


def _factor() -> ValueFactor:
    return _ok(ValueFactor.try_create(100_000, 1, _instrument(), "USD"))


def _fill(
    *,
    quantity: int = 1,
    requested: int | None = None,
    price: int = 1_10000,
    post: int | None = None,
) -> Fill:
    wanted = quantity if requested is None else requested
    post_price = _price(price if post is None else post)
    return _ok(
        Fill.try_create(
            _qty(quantity),
            _qty(wanted),
            _price(price),
            post_slip_price=post_price,
            side=Direction.LONG,
        )
    )


def _partial(
    *,
    quantity: int = 1,
    requested: int = 2,
    price: int = 1_10000,
    post: int | None = None,
) -> PartialFill:
    post_price = _price(price if post is None else post)
    return _ok(
        PartialFill.try_create(
            _qty(quantity),
            _qty(requested),
            _price(price),
            post_slip_price=post_price,
            side=Direction.LONG,
        )
    )


def _cal(
    model: str,
    *,
    currency: str = "USD",
    percent: ExactRational | None = None,
    per_lot: Money | None = None,
    per_1k_units: Money | None = None,
    units_per_lot: Quantity | None = None,
    minimum: Money | None = None,
    value_factor: ValueFactor | None = None,
    money_scale: int = 2,
) -> CommissionCalibration:
    return _ok(
        CommissionCalibration.try_create(
            model,
            "broker-a",
            currency=currency,
            percent=percent,
            per_lot=per_lot,
            per_1k_units=per_1k_units,
            units_per_lot=units_per_lot,
            minimum=minimum,
            value_factor=value_factor,
            money_scale=money_scale,
        )
    )


def test_cost_identity_catalog_and_api_door() -> None:
    identity = cost_identity()
    assert identity["models"] == COST_MODELS
    assert COST_MODELS == (
        "zero",
        "percent-of-notional",
        "per-lot/per-1k-units",
        "notional-proportional-with-per-order-minimum",
    )
    assert identity["silent_zero_on_missing_calibration"] is False
    assert identity["folded_into_fill_pnl"] is False
    assert identity["admission_matches_charge"] is True
    assert identity["content_deferred_to"] == COST_CONTENT_DEFERRED_TO == "GAP-0048"
    assert identity["component_name"] == COST_COMPONENT_COMMISSION
    assert "version" not in identity
    assert qmb.__version__ not in identity.values()
    assert tuple(COST_ADAPTER_CATALOG) == COST_MODELS
    stamped = fingerprint_cost()
    assert is_ok(stamped)
    assert stamped.value.value.startswith("fp1:sha256:")
    assert isinstance(ZeroCostAdapter(), CostPort)
    assert api.COST_MODELS is qmb.COST_MODELS is COST_MODELS
    assert api.charge_commission is qmb.charge_commission is charge_commission
    assert api.CommissionCalibration is qmb.CommissionCalibration is CommissionCalibration
    assert api.cost_identity() == qmb.cost_identity() == identity


def test_typed_fee_is_exact_integer_money_in_own_currency() -> None:
    fill = _fill()
    cal = _cal(
        COST_ADAPTER_PERCENT_OF_NOTIONAL,
        percent=_ratio(1, 10_000),
        value_factor=_factor(),
    )
    quoted = _ok(PercentOfNotionalCostAdapter(calibration=cal).quote(fill))
    assert isinstance(quoted, Money)
    assert quoted.currency == "USD"
    assert quoted.as_fraction() == _money(1_100).as_fraction()
    float_pct = CommissionCalibration.try_create(
        COST_ADAPTER_PERCENT_OF_NOTIONAL,
        "broker-a",
        percent=0.01,
    )
    assert is_refusal(float_pct)
    assert float_pct.category is RefusalCategory.INVALID_INPUT
    eur = _cal(
        COST_ADAPTER_PER_LOT,
        currency="EUR",
        per_lot=_money(700, "EUR"),
    )
    own = _ok(PerLotCostAdapter(calibration=eur).quote(fill))
    assert own.currency == "EUR"
    assert own.as_fraction() == _money(700, "EUR").as_fraction()
    itemized = PerLotCostAdapter(calibration=eur).itemize(fill)
    assert is_refusal(itemized)
    assert itemized.category is RefusalCategory.POLICY_REJECTION


def test_each_partial_carries_its_own_prorated_commission_line() -> None:
    cal = _cal(
        COST_ADAPTER_PERCENT_OF_NOTIONAL,
        percent=_ratio(1, 10_000),
        value_factor=_factor(),
    )
    adapter = PercentOfNotionalCostAdapter(calibration=cal)
    first = _ok(adapter.itemize(_partial(quantity=1, requested=2)))
    second = _ok(adapter.itemize(_partial(quantity=1, requested=2)))
    full = _ok(adapter.itemize(_fill(quantity=2)))
    assert first.fill.kind.value == "partial-fill"
    assert len(first.costs) == 1
    assert first.costs[0].name == COST_COMPONENT_COMMISSION
    assert first.costs[0].amount.as_fraction() == _money(1_100).as_fraction()
    assert second.costs[0].amount.as_fraction() == first.costs[0].amount.as_fraction()
    combined = first.costs[0].amount.add(second.costs[0].amount)
    assert is_ok(combined)
    assert combined.value.as_fraction() == full.costs[0].amount.as_fraction()
    assert first.fill.quantity.as_fraction() == _qty(1).as_fraction()
    assert first.fill.pre_slip_price.as_fraction() == _price(1_10000).as_fraction()
    assert first.fill.post_slip_price is not None
    assert first.fill.post_slip_price.as_fraction() == first.fill.pre_slip_price.as_fraction()


def test_commission_is_never_folded_into_fill_pnl() -> None:
    fill = _fill()
    cal = _cal(COST_ADAPTER_PER_LOT, per_lot=_money(700))
    costed = _ok(PerLotCostAdapter(calibration=cal).itemize(fill))
    assert costed.fill.quantity.as_fraction() == fill.quantity.as_fraction()
    assert costed.fill.pre_slip_price.as_fraction() == fill.pre_slip_price.as_fraction()
    assert costed.fill.post_slip_price is not None
    assert fill.post_slip_price is not None
    assert costed.fill.post_slip_price.as_fraction() == fill.post_slip_price.as_fraction()
    assert costed.costs[0].name == COST_COMPONENT_COMMISSION
    assert costed.taint == TAINT_OPTIMISTIC
    zeroed = _ok(ZeroCostAdapter().itemize(fill))
    assert zeroed.costs == ()
    assert zeroed.fill.quantity.as_fraction() == fill.quantity.as_fraction()


def test_catalog_shapes_are_calibration_parameterized() -> None:
    fill = _fill()
    percent = _ok(
        PercentOfNotionalCostAdapter(
            calibration=_cal(
                COST_ADAPTER_PERCENT_OF_NOTIONAL,
                percent=_ratio(1, 10_000),
                value_factor=_factor(),
            )
        ).quote(fill)
    )
    assert percent.as_fraction() == _money(1_100).as_fraction()

    per_lot = _ok(
        PerLotCostAdapter(calibration=_cal(COST_ADAPTER_PER_LOT, per_lot=_money(700))).quote(fill)
    )
    assert per_lot.as_fraction() == _money(700).as_fraction()

    per_1k = _ok(
        PerLotCostAdapter(
            calibration=_cal(
                COST_ADAPTER_PER_LOT,
                per_1k_units=_money(60),
                units_per_lot=_ok(Quantity.try_create(100_000, "unit", 0)),
            )
        ).quote(fill)
    )
    assert per_1k.as_fraction() == _money(6_000).as_fraction()

    floor = _ok(
        NotionalProportionalMinimumCostAdapter(
            calibration=_cal(
                COST_ADAPTER_NOTIONAL_MINIMUM,
                percent=_ratio(1, 100_000),
                minimum=_money(700),
                value_factor=_factor(),
            )
        ).quote(fill)
    )
    assert floor.as_fraction() == _money(700).as_fraction()

    above = _ok(
        NotionalProportionalMinimumCostAdapter(
            calibration=_cal(
                COST_ADAPTER_NOTIONAL_MINIMUM,
                percent=_ratio(1, 10_000),
                minimum=_money(700),
                value_factor=_factor(),
            )
        ).quote(fill)
    )
    assert above.as_fraction() == _money(1_100).as_fraction()

    zero = _ok(ZeroCostAdapter().quote(fill))
    assert zero.as_fraction() == 0
    assert COST_ADAPTER_ZERO in COST_ADAPTER_CATALOG
    assert COST_ADAPTER_PERCENT_OF_NOTIONAL in COST_ADAPTER_CATALOG
    assert COST_ADAPTER_PER_LOT in COST_ADAPTER_CATALOG
    assert COST_ADAPTER_NOTIONAL_MINIMUM in COST_ADAPTER_CATALOG


def test_minimum_is_prorated_per_partial_not_reapplied() -> None:
    cal = _cal(
        COST_ADAPTER_NOTIONAL_MINIMUM,
        percent=_ratio(1, 100_000),
        minimum=_money(700),
        value_factor=_factor(),
    )
    adapter = NotionalProportionalMinimumCostAdapter(calibration=cal)
    full = _ok(adapter.quote(_fill(quantity=2)))
    half = _ok(adapter.quote(_partial(quantity=1, requested=2)))
    assert full.as_fraction() == _money(700).as_fraction()
    assert half.as_fraction() == _money(350).as_fraction()


def test_admission_query_matches_fill_time_charge() -> None:
    fill = _fill()
    cal = _cal(
        COST_ADAPTER_PERCENT_OF_NOTIONAL,
        percent=_ratio(1, 10_000),
        value_factor=_factor(),
    )
    adapter = PercentOfNotionalCostAdapter(calibration=cal)
    admitted = _ok(adapter.quote(fill))
    charged = _ok(adapter.quote(fill))
    itemized = _ok(adapter.itemize(fill))
    assert admitted.as_fraction() == charged.as_fraction()
    assert itemized.costs[0].amount.as_fraction() == admitted.as_fraction()
    assert itemized.costs[0].amount.fp1_identity() == admitted.fp1_identity()
    unfilled = _fill()
    quoted_only = _ok(adapter.quote(unfilled))
    assert quoted_only.as_fraction() == admitted.as_fraction()


def test_missing_calibration_is_typed_refusal_never_silent_zero() -> None:
    fill = _fill()
    missing = PercentOfNotionalCostAdapter().quote(fill)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert missing.context["field"] == "cost_calibration"
    assert missing.context["gap"] == COST_CONTENT_DEFERRED_TO

    empty = _cal(COST_ADAPTER_PERCENT_OF_NOTIONAL)
    deferred = PercentOfNotionalCostAdapter(calibration=empty).quote(fill)
    assert is_refusal(deferred)
    assert deferred.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert deferred.context["field"] == "percent"

    lot_empty = PerLotCostAdapter(calibration=_cal(COST_ADAPTER_PER_LOT)).quote(fill)
    assert is_refusal(lot_empty)
    assert lot_empty.category is RefusalCategory.UNAVAILABLE_DEPENDENCY

    named_zero = _ok(ZeroCostAdapter().quote(fill))
    assert named_zero.as_fraction() == 0
    itemized_zero = _ok(ZeroCostAdapter().itemize(fill))
    assert itemized_zero.costs == ()
