"""Story 10.2 AC1/AC2/AC5/AC6 — R's three typed faces and the full-loss-price law.

Verifies R as three typed faces frozen at admission (original_risk_distance =
PriceDelta, original_risk_amount = Money, r_multiple = dimensionless exact rational
with −1 a full original loss and 0 breakeven), the full-loss-price law (no price → no
distance → no admission, an invalid-input refusal) and the no-scale-in policy
rejection, the value-factor-sourced amount (an absent value-factor an
unavailable-dependency refusal, never a silent conversion; V1 never sizes by margin),
and the Money↔R crossing over a named rate (an implicit crossing refuses; only
r_multiple averages across instruments and accounts) (FR-028; CT-22, CT-23; DEC-0154).
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


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _other_instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="GBPUSD")


def _price(value: int) -> Price:
    result = Price.try_create(value, _instrument(), 5)
    assert is_ok(result)
    return result.value


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    result = ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE)
    assert is_ok(result)
    return result.value


def _rate(numerator: int, denominator: int = 1) -> ExactRational:
    result = ExactRational.try_create(numerator, denominator, UnitKind.RATE)
    assert is_ok(result)
    return result.value


def _value_factor(numerator: int) -> ValueFactor:
    result = ValueFactor.try_create(numerator, 1, _instrument(), "USD")
    assert is_ok(result)
    return result.value


def _lot() -> Quantity:
    result = Quantity.try_create(1, "lot", 0)
    assert is_ok(result)
    return result.value


# --- the anchor r-multiples --------------------------------------------------


def test_full_original_loss_is_minus_one_and_breakeven_is_zero() -> None:
    assert FULL_ORIGINAL_LOSS.unit_kind is UnitKind.R_MULTIPLE
    assert FULL_ORIGINAL_LOSS.as_fraction() == Fraction(-1)
    assert BREAKEVEN.unit_kind is UnitKind.R_MULTIPLE
    assert BREAKEVEN.as_fraction() == Fraction(0)


def test_direction_values() -> None:
    assert {member.value for member in Direction} == {"long", "short"}


# --- the full-loss-price law (AC2): no price -> no distance -> no admission ---


def test_long_risk_distance_is_entry_minus_full_loss() -> None:
    distance = derive_original_risk_distance(_price(110_000), _price(109_000), Direction.LONG)
    assert is_ok(distance)
    assert isinstance(distance.value, PriceDelta)
    assert distance.value.as_fraction() == Fraction(1_000, 100_000)


def test_short_risk_distance_is_full_loss_minus_entry() -> None:
    distance = derive_original_risk_distance(_price(109_000), _price(110_000), Direction.SHORT)
    assert is_ok(distance)
    assert distance.value.as_fraction() == Fraction(1_000, 100_000)


def test_missing_full_loss_price_is_invalid_input_no_admission() -> None:
    result = derive_original_risk_distance(_price(110_000), None, Direction.LONG)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "full_loss_price"


def test_non_price_full_loss_is_invalid_input() -> None:
    result = derive_original_risk_distance(_price(110_000), "1.09000", Direction.LONG)
    assert is_refusal(result)
    assert result.context["field"] == "full_loss_price"


def test_non_price_entry_is_invalid_input() -> None:
    result = derive_original_risk_distance("1.10", _price(109_000), Direction.LONG)
    assert is_refusal(result)
    assert result.context["field"] == "entry_price"


def test_unknown_direction_is_invalid_input() -> None:
    result = derive_original_risk_distance(_price(110_000), _price(109_000), "sideways")
    assert is_refusal(result)
    assert result.context["field"] == "direction"


def test_full_loss_on_wrong_side_for_long_is_refused() -> None:
    # A long's full-loss price above entry is not a planned loss point.
    result = derive_original_risk_distance(_price(110_000), _price(111_000), Direction.LONG)
    assert is_refusal(result)
    assert result.context["field"] == "full_loss_price"


def test_full_loss_equal_to_entry_is_refused() -> None:
    result = derive_original_risk_distance(_price(110_000), _price(110_000), Direction.LONG)
    assert is_refusal(result)


def test_full_loss_on_wrong_side_for_short_is_refused() -> None:
    result = derive_original_risk_distance(_price(110_000), _price(109_000), Direction.SHORT)
    assert is_refusal(result)


def test_distance_across_instruments_is_refused() -> None:
    other = Price.try_create(109_000, _other_instrument(), 5)
    assert is_ok(other)
    result = derive_original_risk_distance(_price(110_000), other.value, Direction.LONG)
    assert is_refusal(result)


# --- admission mints the frozen faces via a venue value-factor (AC1/AC5) ------


def test_admit_entry_r_faces_derives_both_money_faces() -> None:
    faces = admit_entry_r_faces(
        _price(110_000),
        _price(109_000),
        Direction.LONG,
        _lot(),
        _value_factor(100_000),
        money_scale=2,
    )
    assert is_ok(faces)
    assert faces.value.original_risk_distance.as_fraction() == Fraction(1_000, 100_000)
    # 0.01 price-delta x 100000 (money per delta per lot) x 1 lot = 1000.00 USD.
    assert faces.value.original_risk_amount == Money(value=100_000, currency="USD", scale=2)
    assert faces.value.original_risk_amount.currency == "USD"


def test_admit_absent_value_factor_is_unavailable_dependency_never_silent() -> None:
    faces = admit_entry_r_faces(
        _price(110_000), _price(109_000), Direction.LONG, _lot(), None, money_scale=2
    )
    assert is_refusal(faces)
    assert faces.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_admit_rejects_non_value_factor() -> None:
    faces = admit_entry_r_faces(
        _price(110_000), _price(109_000), Direction.LONG, _lot(), "100000", money_scale=2
    )
    assert is_refusal(faces)
    assert faces.context["field"] == "value_factor"


def test_admit_rejects_non_quantity() -> None:
    faces = admit_entry_r_faces(
        _price(110_000),
        _price(109_000),
        Direction.LONG,
        "1 lot",
        _value_factor(100_000),
        money_scale=2,
    )
    assert is_refusal(faces)
    assert faces.context["field"] == "admitted_quantity"


def test_admit_propagates_the_full_loss_law_refusal() -> None:
    faces = admit_entry_r_faces(
        _price(110_000), None, Direction.LONG, _lot(), _value_factor(100_000), money_scale=2
    )
    assert is_refusal(faces)
    assert faces.context["field"] == "full_loss_price"


def test_admit_value_factor_belonging_to_other_instrument_is_refused() -> None:
    other_vf = ValueFactor.try_create(100_000, 1, _other_instrument(), "USD")
    assert is_ok(other_vf)
    faces = admit_entry_r_faces(
        _price(110_000), _price(109_000), Direction.LONG, _lot(), other_vf.value, money_scale=2
    )
    assert is_refusal(faces)


# --- RFaces.try_create validation --------------------------------------------


def test_rfaces_try_create_rejects_non_price_delta_distance() -> None:
    result = RFaces.try_create("delta", Money(value=100_000, currency="USD", scale=2))
    assert is_refusal(result)
    assert result.context["field"] == "original_risk_distance"


def test_rfaces_try_create_rejects_non_positive_distance() -> None:
    zero = PriceDelta(value=0, instrument=_instrument(), scale=5)
    result = RFaces.try_create(zero, Money(value=100_000, currency="USD", scale=2))
    assert is_refusal(result)
    assert result.context["field"] == "original_risk_distance"


def test_rfaces_try_create_rejects_non_money_amount() -> None:
    distance = PriceDelta(value=1_000, instrument=_instrument(), scale=5)
    result = RFaces.try_create(distance, "1000")
    assert is_refusal(result)
    assert result.context["field"] == "original_risk_amount"


def test_rfaces_try_create_rejects_non_numeraire_amount() -> None:
    distance = PriceDelta(value=1_000, instrument=_instrument(), scale=5)
    result = RFaces.try_create(distance, Money(value=100_000, currency="JPY", scale=2))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_rfaces_try_create_rejects_non_positive_amount() -> None:
    distance = PriceDelta(value=1_000, instrument=_instrument(), scale=5)
    result = RFaces.try_create(distance, Money(value=0, currency="USD", scale=2))
    assert is_refusal(result)
    assert result.context["field"] == "original_risk_amount"


# --- the realized r_multiple face: -1 full loss, 0 breakeven (AC1) ------------


def _faces() -> RFaces:
    result = RFaces.try_create(
        PriceDelta(value=1_000, instrument=_instrument(), scale=5),
        Money(value=100_000, currency="USD", scale=2),  # 1000.00 USD
    )
    assert is_ok(result)
    return result.value


def test_r_multiple_of_a_full_loss_is_minus_one() -> None:
    realized = Money(value=-100_000, currency="USD", scale=2)  # -1000.00 USD
    r = _faces().r_multiple_of(realized)
    assert is_ok(r)
    assert r.value.as_fraction() == Fraction(-1)
    assert r.value.unit_kind is UnitKind.R_MULTIPLE


def test_r_multiple_of_breakeven_is_zero() -> None:
    r = _faces().r_multiple_of(Money(value=0, currency="USD", scale=2))
    assert is_ok(r)
    assert r.value.as_fraction() == Fraction(0)


def test_r_multiple_of_a_two_r_win() -> None:
    r = _faces().r_multiple_of(Money(value=200_000, currency="USD", scale=2))  # +2000.00
    assert is_ok(r)
    assert r.value.as_fraction() == Fraction(2)


def test_r_multiple_rejects_non_money_realized() -> None:
    r = _faces().r_multiple_of("1000")
    assert is_refusal(r)


def test_r_multiple_rejects_cross_currency_realized() -> None:
    r = _faces().r_multiple_of(Money(value=100_000, currency="JPY", scale=2))
    assert is_refusal(r)
    assert r.context["field"] == "realized_result"


# --- frozen at admission, never re-based (AC1) --------------------------------


def test_rfaces_is_frozen_and_never_re_based() -> None:
    faces = _faces()
    with pytest.raises(dataclasses.FrozenInstanceError):
        faces.original_risk_amount = Money(value=1, currency="USD", scale=2)  # type: ignore[misc]


def test_a_later_stop_move_leaves_the_frozen_faces_unchanged() -> None:
    # Admission mints the faces; a later ratchet/stop move recomputes a *new* distance
    # but the frozen faces stand — the module offers no mutator and never re-bases R.
    faces = _faces()
    admission_distance = faces.original_risk_distance.as_fraction()
    admission_amount = faces.original_risk_amount.as_fraction()
    # A ratchet to a tighter stop (a new, smaller risk distance) — a separate value.
    tightened = derive_original_risk_distance(_price(110_000), _price(109_500), Direction.LONG)
    assert is_ok(tightened)
    assert tightened.value.as_fraction() != admission_distance
    assert faces.original_risk_distance.as_fraction() == admission_distance
    assert faces.original_risk_amount.as_fraction() == admission_amount


def test_rfaces_fp1_identity_is_deterministic() -> None:
    faces = _faces()
    assert faces.fp1_identity() == faces.fp1_identity()
    assert faces.fp1_identity()["class"] == "r-faces"


def test_a_changed_face_changes_fp1_identity() -> None:
    one = _faces()
    two = RFaces.try_create(
        PriceDelta(value=2_000, instrument=_instrument(), scale=5),
        Money(value=100_000, currency="USD", scale=2),
    )
    assert is_ok(two)
    assert one.fp1_identity() != two.value.fp1_identity()


# --- no scale-in (AC2) -------------------------------------------------------


def test_no_open_position_admits() -> None:
    assert is_ok(check_no_scale_in(False))


def test_scale_in_is_a_policy_rejection() -> None:
    result = check_no_scale_in(True)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_scale_in_guard_rejects_non_bool() -> None:
    result = check_no_scale_in("open")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


# --- the Money<->R crossing names a rate (AC6) -------------------------------


def test_r_to_money_crosses_over_a_named_rate() -> None:
    # position_risk_amount = requested_r x r_unit_price = 2 x 25 = 50.00 USD.
    result = r_to_money(_r(2), _rate(25), scale=2)
    assert is_ok(result)
    assert result.value == Money(value=5_000, currency="USD", scale=2)


def test_money_to_r_crosses_over_a_named_rate() -> None:
    result = money_to_r(Money(value=5_000, currency="USD", scale=2), _rate(25))
    assert is_ok(result)
    assert result.value.as_fraction() == Fraction(2)
    assert result.value.unit_kind is UnitKind.R_MULTIPLE


def test_r_to_money_refuses_an_implicit_crossing_without_a_named_rate() -> None:
    # An r_unit_price that is not a rate(money-per-r) is an implicit crossing.
    result = r_to_money(_r(2), _r(25), scale=2)
    assert is_refusal(result)
    assert result.context["field"] == "r_unit_price"


def test_r_to_money_refuses_a_non_r_multiple_requested_r() -> None:
    result = r_to_money(_rate(2), _rate(25), scale=2)
    assert is_refusal(result)
    assert result.context["field"] == "requested_r"


def test_money_to_r_refuses_an_implicit_crossing() -> None:
    result = money_to_r(Money(value=5_000, currency="USD", scale=2), _r(25))
    assert is_refusal(result)
    assert result.context["field"] == "r_unit_price"


def test_money_to_r_refuses_a_zero_rate() -> None:
    result = money_to_r(Money(value=5_000, currency="USD", scale=2), _rate(0))
    assert is_refusal(result)


def test_money_to_r_refuses_non_money_amount() -> None:
    result = money_to_r("50", _rate(25))
    assert is_refusal(result)
    assert result.context["field"] == "amount"


def test_money_to_r_refuses_non_numeraire_amount() -> None:
    result = money_to_r(Money(value=5_000, currency="JPY", scale=2), _rate(25))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_r_to_money_refuses_inexact_scale() -> None:
    # 1 x (1/3) = 1/3 money is not exactly representable at scale 2.
    result = r_to_money(_r(1), _rate(1, 3), scale=2)
    assert is_refusal(result)
    assert result.context["field"] == "scale"


def test_r_to_money_refuses_bad_scale() -> None:
    assert is_refusal(r_to_money(_r(2), _rate(25), scale="two"))
    assert is_refusal(r_to_money(_r(2), _rate(25), scale=-1))
    assert is_refusal(r_to_money(_r(2), _rate(25), scale=999))
    assert is_refusal(r_to_money(_r(2), _rate(25), scale=True))


# --- only r_multiple averages across instruments and accounts (AC6) ----------


def test_average_r_multiple_of_a_cross_instrument_book() -> None:
    result = average_r_multiple([_r(1), _r(2), _r(0)])
    assert is_ok(result)
    assert result.value.as_fraction() == Fraction(1)
    assert result.value.unit_kind is UnitKind.R_MULTIPLE


def test_average_refuses_a_money_value() -> None:
    # Money never averages across instruments/accounts — it would need a conversion.
    result = average_r_multiple([_r(1), Money(value=100, currency="USD", scale=2)])
    assert is_refusal(result)
    assert result.context["field"] == "values"


def test_average_refuses_a_price_delta_value() -> None:
    result = average_r_multiple([PriceDelta(value=1, instrument=_instrument(), scale=5)])
    assert is_refusal(result)


def test_average_refuses_a_non_r_multiple_rational() -> None:
    result = average_r_multiple([_r(1), _rate(2)])
    assert is_refusal(result)


def test_average_refuses_empty_and_non_sequence() -> None:
    assert is_refusal(average_r_multiple([]))
    assert is_refusal(average_r_multiple("not a sequence"))
    assert is_refusal(average_r_multiple(42))
