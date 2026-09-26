"""Reference usage — cost port exact-integer itemized commissions (Story 17.4).

Executable::

    python qmb/examples/cost_port_usage.py

Shows the things FEE-1 / FEE-2 / FEE-3 / FEE-5 / B-6 pin down:

1. Commission is a typed fee in its own currency as exact-integer Money.
2. No float commission rate touches the money path.
3. Each partial carries its own pro-rated commission, never folded into fill P&L.
4. Shapes: zero | percent-of-notional | per-lot/per-1k-units |
   notional-proportional-with-per-order-minimum, parameterized by a versioned
   per-broker calibration whose rates stay deferred to GAP-0048.
5. Admission query and fill-time charge return the identical amount.
6. Missing calibration is a typed refusal, never a silent zero.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.execution import (
    COST_ADAPTER_NOTIONAL_MINIMUM,
    COST_ADAPTER_PER_LOT,
    COST_ADAPTER_PERCENT_OF_NOTIONAL,
    COST_COMPONENT_COMMISSION,
    COST_MODELS,
    CommissionCalibration,
    Fill,
    NotionalProportionalMinimumCostAdapter,
    PartialFill,
    PercentOfNotionalCostAdapter,
    PerLotCostAdapter,
    ZeroCostAdapter,
)
from qmf.core.exact import ExactRational, Money, Price, Quantity, UnitKind, ValueFactor
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.door import Direction

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="venue-replay"), symbol="EURUSD")


def _price(value: int) -> Price:
    return _unwrap(Price.try_create(value, _instrument(), 5), "price")


def _qty(value: int) -> Quantity:
    return _unwrap(Quantity.try_create(value, "lot", 0), "quantity")


def _ratio(num: int, den: int) -> ExactRational:
    return _unwrap(
        ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO),
        "ratio",
    )


def _fill(*, quantity: int = 1, requested: int | None = None) -> Fill:
    wanted = quantity if requested is None else requested
    price = _price(1_10000)
    return _unwrap(
        Fill.try_create(
            _qty(quantity),
            _qty(wanted),
            price,
            post_slip_price=price,
            side=Direction.LONG,
        ),
        "fill",
    )


def _partial(*, quantity: int = 1, requested: int = 2) -> PartialFill:
    price = _price(1_10000)
    return _unwrap(
        PartialFill.try_create(
            _qty(quantity),
            _qty(requested),
            price,
            post_slip_price=price,
            side=Direction.LONG,
        ),
        "partial",
    )


def main() -> None:
    factor = _unwrap(ValueFactor.try_create(100_000, 1, _instrument(), "USD"), "value-factor")
    percent = _unwrap(
        CommissionCalibration.try_create(
            COST_ADAPTER_PERCENT_OF_NOTIONAL,
            "broker-a",
            currency="USD",
            percent=_ratio(1, 10_000),
            value_factor=factor,
            money_scale=2,
        ),
        "percent-cal",
    )
    adapter = PercentOfNotionalCostAdapter(calibration=percent)
    fill = _fill()
    quoted = _unwrap(adapter.quote(fill), "quote")
    assert quoted.currency == "USD"
    assert quoted.as_fraction() == _unwrap(Money.try_create(1_100, "USD", 2), "11.00").as_fraction()
    print("exact-integer Money in its own currency")
    print("no float on the money path")

    first = _unwrap(adapter.itemize(_partial(quantity=1, requested=2)), "partial-a")
    second = _unwrap(adapter.itemize(_partial(quantity=1, requested=2)), "partial-b")
    assert first.costs[0].name == COST_COMPONENT_COMMISSION
    assert first.costs[0].amount.as_fraction() == quoted.as_fraction()
    assert second.costs[0].amount.as_fraction() == quoted.as_fraction()
    assert first.fill.pre_slip_price.as_fraction() == fill.pre_slip_price.as_fraction()
    print("each partial has its own pro-rated commission")
    print("commission is a distinct line item")

    assert COST_MODELS == (
        "zero",
        "percent-of-notional",
        "per-lot/per-1k-units",
        "notional-proportional-with-per-order-minimum",
    )
    lot = _unwrap(
        CommissionCalibration.try_create(
            COST_ADAPTER_PER_LOT,
            "broker-a",
            currency="USD",
            per_lot=_unwrap(Money.try_create(700, "USD", 2), "per-lot"),
        ),
        "lot-cal",
    )
    lot_fee = _unwrap(PerLotCostAdapter(calibration=lot).quote(fill), "per-lot")
    assert lot_fee.as_fraction() == _unwrap(Money.try_create(700, "USD", 2), "7.00").as_fraction()
    floor = _unwrap(
        CommissionCalibration.try_create(
            COST_ADAPTER_NOTIONAL_MINIMUM,
            "broker-a",
            currency="USD",
            percent=_ratio(1, 100_000),
            minimum=_unwrap(Money.try_create(700, "USD", 2), "min"),
            value_factor=factor,
            money_scale=2,
        ),
        "min-cal",
    )
    floored = _unwrap(
        NotionalProportionalMinimumCostAdapter(calibration=floor).quote(fill),
        "minimum",
    )
    expected_min = _unwrap(Money.try_create(700, "USD", 2), "7.00-min")
    assert floored.as_fraction() == expected_min.as_fraction()
    print(
        "zero | percent-of-notional | per-lot/per-1k-units | "
        "notional-proportional-with-per-order-minimum"
    )

    admitted = _unwrap(adapter.quote(fill), "admit")
    charged = _unwrap(adapter.itemize(fill), "charge")
    assert admitted.as_fraction() == charged.costs[0].amount.as_fraction()
    print("admission query matches fill-time charge")

    missing = PercentOfNotionalCostAdapter().quote(fill)
    assert is_refusal(missing)
    named_zero = _unwrap(ZeroCostAdapter().itemize(fill), "zero")
    assert named_zero.costs == ()
    print("missing calibration is typed refusal, never silent zero")
    print("cost port ok")


if __name__ == "__main__":
    main()
