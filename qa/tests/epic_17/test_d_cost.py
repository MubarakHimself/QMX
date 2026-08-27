"""Epic 17 · Group D — cost port: exact-integer itemized commissions (Story 17.4, R24-R28).

Independent, requirements-derived assertions (T-17.4-a..f). Commission is a typed
fee in its own currency as exact-integer Money; each partial carries its own
pro-rated line, never folded into fill P&L; catalog shapes are parameterized by a
versioned per-broker calibration whose absence refuses (never a silent zero); the
admission query and the fill-time charge agree (CT-01, FEE-1..5, DEC-0135, SC-07).
A failing test is a FINDING, never a licence to soften the assertion or edit source.
"""

from __future__ import annotations

from _e17 import money, ok, price, qty, ratio, refusal, value_factor

from qmf.core.exact import Money
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.door import Direction
from qmf.risk.exit_record import CostComponent
from qmb.execution.cost import (
    COST_COMPONENT_COMMISSION,
    CommissionCalibration,
    NotionalProportionalMinimumCostAdapter,
    PercentOfNotionalCostAdapter,
    PerLotCostAdapter,
    ZeroCostAdapter,
    charge_commission,
)
from qmb.execution.ports import Fill, PartialFill


def _fill(q=10):
    return ok(Fill.try_create(qty(q), qty(q), price(100_000), post_slip_price=price(100_000),
                              side=Direction.LONG))


def _partial(filled=4, requested=10):
    return ok(PartialFill.try_create(qty(filled), qty(requested), price(100_000),
                                     post_slip_price=price(100_000), side=Direction.LONG))


def _per_lot(per_lot_minor=200):
    return ok(CommissionCalibration.try_create("per-lot/per-1k-units", "broker-x",
                                               per_lot=money(per_lot_minor), currency="USD"))


def _percent(num=1, den=100):
    return ok(CommissionCalibration.try_create("percent-of-notional", "broker-x",
                                               percent=ratio(num, den), value_factor=value_factor(),
                                               currency="USD", money_scale=2))


def _notional_min(num, den, minimum_minor):
    return ok(CommissionCalibration.try_create("notional-proportional-with-per-order-minimum",
                                               "broker-x", percent=ratio(num, den),
                                               minimum=money(minimum_minor),
                                               value_factor=value_factor(), currency="USD",
                                               money_scale=2))


# --- T-17.4-a (L2) typed fee in own currency, exact-integer Money, no float [R24] P0
def test_t174a_typed_fee_exact_money_no_float_rate() -> None:
    adapter = PerLotCostAdapter(calibration=_per_lot())
    costed = ok(adapter.itemize(_fill()))
    assert len(costed.costs) == 1
    component = costed.costs[0]
    assert isinstance(component, CostComponent)
    assert isinstance(component.amount, Money)
    assert component.amount.currency == "USD"  # the fee's own currency
    # A float commission rate never enters the money path — the calibration refuses it.
    assert is_refusal(
        CommissionCalibration.try_create("percent-of-notional", "broker-x", percent=0.01,
                                         currency="USD")
    )


# --- T-17.4-b (L1) commission-shape math is exact-integer for each shape [R26] --
def test_t174b_commission_shape_math_is_exact() -> None:
    fill = _fill(10)
    # zero shape: exactly zero.
    assert ok(charge_commission(fill, model="zero", calibration=None)) == money(0)
    # per-lot: per_lot ($2.00) x quantity (10) = $20.00.
    assert ok(charge_commission(fill, model="per-lot/per-1k-units",
                                calibration=_per_lot())) == money(2000)
    # percent-of-notional: 1% x notional ($10.00) = $0.10.
    assert ok(charge_commission(fill, model="percent-of-notional",
                                calibration=_percent())) == money(10)
    # notional-min = max(prorated minimum, percent x notional): 1% x $10 = $0.10 < $5 min -> $5.00.
    assert ok(charge_commission(fill, model="notional-proportional-with-per-order-minimum",
                                calibration=_notional_min(1, 100, 500))) == money(500)
    # 10% x $10 = $1.00 > $0.01 min -> proportional wins ($1.00).
    assert ok(charge_commission(fill, model="notional-proportional-with-per-order-minimum",
                                calibration=_notional_min(10, 100, 1))) == money(100)


# --- T-17.4-c (L2) each partial its own pro-rated line, never folded into P&L [R25] P0
def test_t174c_per_partial_prorated_commission_itemized_separately() -> None:
    adapter = PerLotCostAdapter(calibration=_per_lot())
    partial = _partial(filled=4, requested=10)
    costed = ok(adapter.itemize(partial))
    # A distinct commission line (never folded into fill P&L).
    assert len(costed.costs) == 1 and costed.costs[0].name == COST_COMPONENT_COMMISSION
    # The partial's commission is per_lot x its filled quantity: $2.00 x 4 = $8.00.
    assert costed.costs[0].amount == money(800)
    # A full fill of 10 charges $20.00 — the partial is a strict pro-rata (4/10).
    full = ok(adapter.itemize(_fill(10)))
    assert full.costs[0].amount == money(2000)


# --- T-17.4-d (L3) double-call determinism: admission == charge; no fill, no charge [R27] P0
def test_t174d_admission_and_charge_agree() -> None:
    adapter = PerLotCostAdapter(calibration=_per_lot())
    fill = _fill(10)
    admission = ok(adapter.quote(fill))
    charge = ok(adapter.itemize(fill)).costs[0].amount
    # The admission query and the fill-time charge return the identical amount (FEE-3).
    assert admission == charge == money(2000)
    # The admission query is a pure re-computation — two calls agree, and it charges nothing
    # on its own (it emits no CostedFill line); only itemize emits the charge.
    assert ok(adapter.quote(fill)) == admission


# --- T-17.4-e (L3) absent calibration refuses, never a silent zero [R28] P0 -----
def test_t174e_absent_calibration_refuses_never_silent_zero() -> None:
    # A non-zero shape with no calibration is an unavailable-dependency refusal.
    missing = refusal(PercentOfNotionalCostAdapter(calibration=None).itemize(_fill()))
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert is_refusal(charge_commission(_fill(), model="per-lot/per-1k-units", calibration=None))
    # The named zero shape is a legitimate empty cost set — NOT a silent zero of a real model.
    zero = ok(ZeroCostAdapter().itemize(_fill()))
    assert zero.costs == ()
    # Counter-case: with calibration the same non-zero adapter charges (proves refusal is real).
    assert is_ok(PercentOfNotionalCostAdapter(calibration=_percent()).itemize(_fill()))


# --- T-17.4-f (L3) each shape is versioned + per-broker; model must match adapter [R26]
def test_t174f_calibration_is_versioned_per_broker_and_model_matched() -> None:
    from qmf.core.fingerprint import Fingerprint

    cal = _per_lot()
    assert isinstance(cal.fingerprint, Fingerprint)
    assert cal.broker_id == "broker-x" and cal.format_version >= 1
    # A calibration whose model disagrees with the bound cost adapter is refused
    # (no cross-shape substitution of an invented rate).
    mismatch = refusal(charge_commission(_fill(), model="percent-of-notional", calibration=cal))
    assert mismatch.category is RefusalCategory.INVALID_INPUT
    # A calibration for a non-catalog model is refused at construction.
    assert is_refusal(CommissionCalibration.try_create("mystery-shape", "broker-x"))
    # And the notional-minimum adapter also honours its own calibration content.
    assert is_ok(NotionalProportionalMinimumCostAdapter(
        calibration=_notional_min(1, 100, 500)).itemize(_fill()))
