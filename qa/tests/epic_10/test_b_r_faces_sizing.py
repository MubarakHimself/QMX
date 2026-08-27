"""Epic 10 independent audit — Cluster B (Story 10.2).

R as three typed faces frozen at admission, the units-only sizing ladder, and the
mandatory declared full-loss price. Assertions authored from Story 10.2 ACs,
CT-22, CT-23, the P0-8 (R frozen + full-loss price required) and R-001 gates.

Planned IDs: B1-B16.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

import pytest
from qmf.core import (
    ExactRational,
    Instrument,
    Money,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    UnitKind,
    ValueFactor,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.risk.dimensional import LADDER_FORMULAS, BinOp, FormulaOp, Ref
from qmf.risk.grammar import (
    AdmissionImpact,
    NotYetRuled,
    TemplateSection,
    TemplateVariable,
    UiEditability,
)
from qmf.risk.r_faces import (
    BREAKEVEN,
    FULL_ORIGINAL_LOSS,
    Direction,
    RFaces,
    admit_entry_r_faces,
    average_r_multiple,
    check_no_scale_in,
    derive_original_risk_distance,
    money_to_r,
    r_to_money,
)
from qmf.risk.sizing import (
    BENCH_THRESHOLD_VARIABLE,
    MONEY_RULES_UNIT_KINDS,
    SEAT_LOSS_RUN_ALLOWANCE_VARIABLE,
    check_b_split,
    check_seat_r_ceiling,
    reconcile_loss_floor,
    validate_money_rules,
)


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _price(value: int) -> Price:
    result = Price.try_create(value, _instrument(), 5)
    assert is_ok(result)
    return result.value


def _usd(minor: int) -> Money:
    return Money(value=minor, currency="USD", scale=2)


def _r(num: int, den: int = 1) -> ExactRational:
    result = ExactRational.try_create(num, den, UnitKind.R_MULTIPLE)
    assert is_ok(result)
    return result.value


def _rate(num: int, den: int = 1) -> ExactRational:
    result = ExactRational.try_create(num, den, UnitKind.RATE)
    assert is_ok(result)
    return result.value


def _count(value: int) -> ExactRational:
    result = ExactRational.try_create(value, 1, UnitKind.COUNT)
    assert is_ok(result)
    return result.value


def _lot(value: int = 1) -> Quantity:
    result = Quantity.try_create(value, "lot", 0)
    assert is_ok(result)
    return result.value


def _vf(num: int) -> ValueFactor:
    result = ValueFactor.try_create(num, 1, _instrument(), "USD")
    assert is_ok(result)
    return result.value


def _blank(gap: str = "GAP-0048") -> NotYetRuled:
    result = NotYetRuled.try_create(gap)
    assert is_ok(result)
    return result.value


def _variable(name: str, unit_kind: UnitKind, value: object) -> TemplateVariable:
    result = TemplateVariable.try_create(
        name=name,
        unit_kind=unit_kind,
        value=value,
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.RESIGN,
    )
    assert is_ok(result)
    return result.value


def _money_rules(
    *,
    seat_loss_run_allowance: TemplateVariable | None = None,
    seat_r_ceiling: TemplateVariable | None = None,
) -> TemplateSection:
    variables = {
        "book_capital": _variable("book_capital", UnitKind.MONEY, _usd(1_000_000)),
        "loss_floor": _variable("loss_floor", UnitKind.MONEY, _usd(800_000)),
        "loss_runway": _variable("loss_runway", UnitKind.MONEY, _usd(200_000)),
        "period_loss_budget": _variable("period_loss_budget", UnitKind.MONEY, _usd(10_000)),
        "r_unit_price": _variable("r_unit_price", UnitKind.RATE, _rate(25)),
        SEAT_LOSS_RUN_ALLOWANCE_VARIABLE: seat_loss_run_allowance
        or _variable(SEAT_LOSS_RUN_ALLOWANCE_VARIABLE, UnitKind.R_MULTIPLE, _r(4)),
        "seat_r_ceiling": seat_r_ceiling
        or _variable("seat_r_ceiling", UnitKind.R_MULTIPLE, _r(2)),
        "position_risk_amount": _variable("position_risk_amount", UnitKind.MONEY, _usd(5_000)),
    }
    result = TemplateSection.try_create("money_rules", variables)
    assert is_ok(result)
    return result.value


def _faces() -> RFaces:
    result = RFaces.try_create(
        PriceDelta(value=1_000, instrument=_instrument(), scale=5), _usd(100_000)
    )
    assert is_ok(result)
    return result.value


# --- B1: R is three typed faces with correct unit-kinds ----------------------


def test_B1_r_is_three_typed_faces_with_correct_unit_kinds() -> None:
    faces = _faces()
    assert faces.original_risk_distance.unit_kind is UnitKind.PRICE_DELTA
    assert faces.original_risk_amount.unit_kind is UnitKind.MONEY
    assert faces.original_risk_amount.currency == "USD"
    r = faces.r_multiple_of(_usd(-100_000))
    assert is_ok(r)
    assert r.value.unit_kind is UnitKind.R_MULTIPLE


# --- B2 [P0-8]: a stop move never re-bases the frozen faces -------------------


def test_B2_stop_move_never_re_bases_frozen_faces() -> None:
    faces = admit_entry_r_faces(
        _price(110_000), _price(109_000), Direction.LONG, _lot(), _vf(100_000), money_scale=2
    )
    assert is_ok(faces)
    distance_at_admission = faces.value.original_risk_distance.as_fraction()
    amount_at_admission = faces.value.original_risk_amount.as_fraction()
    # A stop move to a tighter level yields a NEW, smaller distance...
    moved = derive_original_risk_distance(_price(110_000), _price(109_500), Direction.LONG)
    assert is_ok(moved)
    assert moved.value.as_fraction() < distance_at_admission
    # ...but the admitted frozen faces are unchanged, and no mutator exists.
    assert faces.value.original_risk_distance.as_fraction() == distance_at_admission
    assert faces.value.original_risk_amount.as_fraction() == amount_at_admission
    with pytest.raises(dataclasses.FrozenInstanceError):
        faces.value.original_risk_amount = _usd(1)  # type: ignore[misc]


# --- B3 [P0-8]: a protection amendment never re-bases the frozen faces --------


def test_B3_protection_amendment_never_re_bases_frozen_faces() -> None:
    faces = _faces()
    amount_before = faces.original_risk_amount
    distance_before = faces.original_risk_distance
    # A protection amendment (a breakeven ratchet) recomputes a resting stop, not R.
    amended = derive_original_risk_distance(_price(110_000), _price(110_000 - 1), Direction.LONG)
    assert is_ok(amended)
    assert faces.original_risk_amount == amount_before
    assert faces.original_risk_distance == distance_before


# --- B4 [P0-8]: a budget re-derivation never re-bases the frozen faces --------


def test_B4_budget_re_derivation_never_re_bases_frozen_faces() -> None:
    faces = _faces()
    amount_before = faces.original_risk_amount
    # Re-deriving a position risk amount against a live budget is a SEPARATE value
    # (r_to_money), and it does not reach back into the frozen face.
    rederived = r_to_money(_r(3), _rate(25), scale=2)
    assert is_ok(rederived)
    assert rederived.value != faces.original_risk_amount
    assert faces.original_risk_amount == amount_before


# --- B5: r_multiple semantics -1 full loss, 0 breakeven ----------------------


def test_B5_r_multiple_anchors_minus_one_and_zero() -> None:
    assert FULL_ORIGINAL_LOSS.as_fraction() == Fraction(-1)
    assert FULL_ORIGINAL_LOSS.unit_kind is UnitKind.R_MULTIPLE
    assert BREAKEVEN.as_fraction() == Fraction(0)
    faces = _faces()  # amount = 1000.00 USD
    full_loss = faces.r_multiple_of(_usd(-100_000))
    assert is_ok(full_loss)
    assert full_loss.value == FULL_ORIGINAL_LOSS
    breakeven = faces.r_multiple_of(_usd(0))
    assert is_ok(breakeven)
    assert breakeven.value == BREAKEVEN


# --- B6 [P0-8]: no full-loss price -> invalid input, no admission -------------


def test_B6_no_full_loss_price_is_invalid_input_no_admission() -> None:
    result = derive_original_risk_distance(_price(110_000), None, Direction.LONG)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "full_loss_price"
    # And admission itself refuses, minting no faces.
    admitted = admit_entry_r_faces(
        _price(110_000), None, Direction.LONG, _lot(), _vf(100_000), money_scale=2
    )
    assert is_refusal(admitted)


# --- B7: V1 admits no scale-in -----------------------------------------------


def test_B7_scale_in_is_a_policy_rejection() -> None:
    assert is_ok(check_no_scale_in(False))
    result = check_no_scale_in(True)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


# --- B8: money_rules carries units only; loss_runway = book_capital-loss_floor -


def test_B8_money_rules_units_only_and_loss_runway_formula() -> None:
    # Units-only: a money_rules section of ALL blanks still validates (no ratified values).
    all_blank = {
        name: _variable(name, kind, _blank()) for name, kind in MONEY_RULES_UNIT_KINDS.items()
    }
    section = TemplateSection.try_create("money_rules", all_blank)
    assert is_ok(section)
    assert is_ok(validate_money_rules(section.value))
    # loss_runway = book_capital - loss_floor is the ratified ladder shape.
    loss_runway = next(f for f in LADDER_FORMULAS if f.formula_id == "FORM-loss-runway")
    expr = loss_runway.expression
    assert isinstance(expr, BinOp)
    assert expr.op is FormulaOp.SUBTRACT
    assert {expr.left, expr.right} == {Ref("book_capital"), Ref("loss_floor")}


# --- B9: seat_r_ceiling <= seat_loss_run_allowance ---------------------------


def test_B9_seat_r_ceiling_bound_is_enforced() -> None:
    assert is_ok(check_seat_r_ceiling(_r(2), _r(4)))
    assert is_ok(check_seat_r_ceiling(_r(4), _r(4)))
    over = check_seat_r_ceiling(_r(5), _r(4))
    assert is_refusal(over)
    assert over.category is RefusalCategory.POLICY_REJECTION
    # Enforced at the shape level too.
    ceiling = _variable("seat_r_ceiling", UnitKind.R_MULTIPLE, _r(5))
    assert is_refusal(validate_money_rules(_money_rules(seat_r_ceiling=ceiling)))


# --- B10: position_risk_amount = requested_r x r_unit_price, frozen ----------


def test_B10_position_risk_amount_is_requested_r_times_r_unit_price() -> None:
    # 2 R x 25 (USD per R) = 50.00 USD, crossed over the NAMED rate.
    result = r_to_money(_r(2), _rate(25), scale=2)
    assert is_ok(result)
    assert result.value == _usd(5_000)
    # money_rules declares position_risk_amount as a money unit-kind (frozen at admission).
    assert MONEY_RULES_UNIT_KINDS["position_risk_amount"] is UnitKind.MONEY


# --- B11: loss_floor is one value read by both (the kill line) ---------------


def test_B11_loss_floor_is_one_value_read_by_both() -> None:
    assert is_ok(reconcile_loss_floor(_usd(800_000), _usd(800_000)))
    drift = reconcile_loss_floor(_usd(800_000), _usd(750_000))
    assert is_refusal(drift)
    assert drift.category is RefusalCategory.POLICY_REJECTION
    assert MONEY_RULES_UNIT_KINDS["loss_floor"] is UnitKind.MONEY


# --- B12 [R-001]: the B-split (count vs r_multiple) --------------------------


def test_B12_b_split_refuses_a_count_where_an_r_multiple_is_declared() -> None:
    miscast = _variable(SEAT_LOSS_RUN_ALLOWANCE_VARIABLE, UnitKind.COUNT, _count(4))
    result = validate_money_rules(_money_rules(seat_loss_run_allowance=miscast))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["declared"] == "count"
    assert result.context["expected"] == "r-multiple"
    # And across sections: bench threshold is a count, seat allowance an r-multiple.
    leash = TemplateSection.try_create(
        "leash_grammar",
        {BENCH_THRESHOLD_VARIABLE: _variable(BENCH_THRESHOLD_VARIABLE, UnitKind.COUNT, _count(2))},
    )
    assert is_ok(leash)
    assert is_ok(check_b_split(_money_rules(), leash.value))


# --- B13 [R-001]: an absent value-factor -> unavailable dependency ------------


def test_B13_absent_value_factor_is_unavailable_dependency_never_silent() -> None:
    result = admit_entry_r_faces(
        _price(110_000), _price(109_000), Direction.LONG, _lot(), None, money_scale=2
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# --- B14: V1 never sizes by margin -------------------------------------------


def test_B14_sizing_uses_a_value_factor_not_margin() -> None:
    # The only sizing input to the amount is a venue value-factor (money per delta
    # per quantity) — never a margin figure. A present value-factor sizes; nothing
    # else is accepted in its place.
    ok = admit_entry_r_faces(
        _price(110_000), _price(109_000), Direction.LONG, _lot(), _vf(100_000), money_scale=2
    )
    assert is_ok(ok)
    # A non-value-factor object (e.g. a raw margin number) is refused, never used.
    not_a_vf = admit_entry_r_faces(
        _price(110_000), _price(109_000), Direction.LONG, _lot(), "5000", money_scale=2
    )
    assert is_refusal(not_a_vf)
    assert not_a_vf.context["field"] == "value_factor"


# --- B15 [R-001]: a Money<->R crossing names a rate; implicit crossing refuses -


def test_B15_money_r_crossing_names_a_rate() -> None:
    assert is_ok(r_to_money(_r(2), _rate(25), scale=2))
    assert is_ok(money_to_r(_usd(5_000), _rate(25)))
    # An implicit crossing (r_unit_price is not a rate) refuses.
    implicit = r_to_money(_r(2), _r(25), scale=2)
    assert is_refusal(implicit)
    assert implicit.context["field"] == "r_unit_price"
    implicit_back = money_to_r(_usd(5_000), _r(25))
    assert is_refusal(implicit_back)


# --- B16: only r_multiple averages across instruments and accounts -----------


def test_B16_only_r_multiple_averages() -> None:
    avg = average_r_multiple([_r(1), _r(2), _r(0)])
    assert is_ok(avg)
    assert avg.value.as_fraction() == Fraction(1)
    # Money never averages across instruments — it would need a conversion.
    money_avg = average_r_multiple([_r(1), _usd(100)])
    assert is_refusal(money_avg)
    price_delta_avg = average_r_multiple([PriceDelta(value=1, instrument=_instrument(), scale=5)])
    assert is_refusal(price_delta_avg)
