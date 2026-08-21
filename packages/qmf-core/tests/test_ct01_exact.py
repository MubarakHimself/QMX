"""Executable CT-01 contract test, owned by qmf-core.

Verifies the exact money/price/quantity vocabulary: scaled-integer values, the
closed unit-kind vocabulary, the money-path float ban and its named conversion
boundary, mixed-scale auto-promotion, delta-typed price subtraction, the
value-factor / pip dependency refusals, and the pinned canonical ``fp1`` identity
form where equal value implies equal fingerprint (CT-01; DEC-0105, DEC-0109,
DEC-0131, DEC-0154, DEC-0158). Written to exercise 100% branch coverage of
``qmf.core.exact``.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

import pytest
from qmf.core.exact import (
    CONTRACT_FORMAT_VERSION,
    MAX_SCALE,
    ExactRational,
    Money,
    Price,
    PriceDelta,
    Quantity,
    RoundingMode,
    UnitKind,
    ValueFactor,
)
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Retryability, is_ok, is_refusal


def _instrument(symbol: str = "EURUSD", venue: str = "venue-1") -> Instrument:
    venue_result = VenueId.try_create(venue)
    assert is_ok(venue_result)
    result = Instrument.try_create(venue_result.value, symbol)
    assert is_ok(result)
    return result.value


def _money(value: int, currency: str = "USD", scale: int = 2) -> Money:
    result = Money.try_create(value, currency, scale)
    assert is_ok(result)
    return result.value


def _delta(value: int, scale: int = 5, instrument: Instrument | None = None) -> PriceDelta:
    result = PriceDelta.try_create(value, instrument or _instrument(), scale)
    assert is_ok(result)
    return result.value


def _quantity(value: int, unit: str = "lot", scale: int = 2) -> Quantity:
    result = Quantity.try_create(value, unit, scale)
    assert is_ok(result)
    return result.value


# --- the closed unit-kind vocabulary ----------------------------------------


def test_unit_kind_vocabulary_is_exactly_the_closed_set() -> None:
    assert {member.value for member in UnitKind} == {
        "money(currency)",
        "price-delta(instrument)",
        "quantity(unit)",
        "value-factor(instrument, currency)",
        "r-multiple",
        "rate(money-per-r)",
        "count",
        "dimensionless-ratio",
        "duration",
        "instant",
    }


def test_each_primitive_carries_its_fixed_unit_kind() -> None:
    assert _money(150).unit_kind is UnitKind.MONEY
    assert Price(15000, _instrument(), 5).unit_kind is UnitKind.PRICE_DELTA
    assert _delta(5).unit_kind is UnitKind.PRICE_DELTA
    assert _quantity(100).unit_kind is UnitKind.QUANTITY
    vf = ValueFactor.try_create(1, 1, _instrument(), "USD")
    assert is_ok(vf)
    assert vf.value.unit_kind is UnitKind.VALUE_FACTOR


# --- Money: scaled integer, float ban, construction pattern -----------------


def test_money_is_a_frozen_scaled_integer() -> None:
    money = _money(150)
    assert dataclasses.is_dataclass(money)
    assert money.value == 150
    assert money.currency == "USD"
    assert money.scale == 2
    with pytest.raises(dataclasses.FrozenInstanceError):
        money.value = 200  # type: ignore[misc]


def test_money_refuses_binary_float_on_the_money_path() -> None:
    # FM-1: a binary float reaching a money-path value is an invalid-input refusal.
    result = Money.try_create(1.5, "USD", 2)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.retryability is Retryability.NO
    assert result.context["field"] == "value"


def test_money_refuses_bool_masquerading_as_int() -> None:
    result = Money.try_create(True, "USD", 2)
    assert is_refusal(result)
    assert result.context["field"] == "value"


def test_money_refuses_blank_currency() -> None:
    result = Money.try_create(150, "   ", 2)
    assert is_refusal(result)
    assert result.context["field"] == "currency"


def test_money_refuses_negative_scale() -> None:
    result = Money.try_create(150, "USD", -1)
    assert is_refusal(result)
    assert result.context["field"] == "scale"


def test_money_currency_stored_verbatim() -> None:
    assert _money(150, "us dollar/USD").currency == "us dollar/USD"


# --- named float conversion boundary ----------------------------------------


def test_money_from_float_is_the_named_boundary_with_explicit_rounding() -> None:
    # A float re-enters Money only here, under an explicitly stated rounding mode.
    result = Money.from_float(1.005, currency="USD", scale=2, rounding=RoundingMode.HALF_UP)
    assert is_ok(result)
    # 1.005 as a binary float is just below 1.005; HALF_UP on its true value yields 100.
    assert result.value.value == 100
    assert result.value.scale == 2


def test_money_from_float_accepts_string_rounding_mode() -> None:
    result = Money.from_float(2.5, currency="USD", scale=0, rounding="half-even")
    assert is_ok(result)
    assert result.value.value == 2  # banker's rounding


def test_money_from_float_refuses_non_float() -> None:
    result = Money.from_float(5, currency="USD", scale=2, rounding=RoundingMode.DOWN)
    assert is_refusal(result)
    assert result.context["field"] == "value"


def test_money_from_float_refuses_nan_and_infinity() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        result = Money.from_float(bad, currency="USD", scale=2, rounding=RoundingMode.DOWN)
        assert is_refusal(result)
        assert result.context["field"] == "value"


def test_money_from_float_refuses_bad_scale() -> None:
    result = Money.from_float(1.5, currency="USD", scale=1.5, rounding=RoundingMode.DOWN)
    assert is_refusal(result)
    assert result.context["field"] == "scale"


def test_money_from_float_refuses_missing_or_unknown_rounding() -> None:
    missing = Money.from_float(1.5, currency="USD", scale=2, rounding=None)
    assert is_refusal(missing)
    assert missing.context["field"] == "rounding"
    unknown = Money.from_float(1.5, currency="USD", scale=2, rounding="nearest-ish")
    assert is_refusal(unknown)
    assert unknown.context["field"] == "rounding"


def test_all_rounding_modes_map_to_a_decimal_mode() -> None:
    # Exercise every RoundingMode member through the boundary.
    for mode in RoundingMode:
        result = Money.from_float(1.5, currency="USD", scale=0, rounding=mode)
        assert is_ok(result)


def test_from_float_takes_the_exact_binary_value_at_large_scale() -> None:
    # Regression (H1): the boundary must take the float's EXACT binary expansion,
    # never a context-precision-capped Decimal.scaleb that silently rounds first.
    # 0.1 as a binary float is exactly 3602879701896397 / 2**55; at scale 30 its
    # true value rounds HALF_UP to ...5551115123126 (the old scaleb path stored
    # ...5551115123100, off by 26).
    result = Money.from_float(0.1, currency="USD", scale=30, rounding=RoundingMode.HALF_UP)
    assert is_ok(result)
    assert result.value.value == 100000000000000005551115123126
    # And it equals the exact Fraction expansion rounded by hand.
    exact = Fraction(0.1) * 10**30
    floor_value, remainder = divmod(exact.numerator, exact.denominator)
    expected = floor_value if 2 * remainder < exact.denominator else floor_value + 1
    assert result.value.value == expected


def test_from_float_is_exact_at_large_magnitude() -> None:
    # Regression (H1): 1e30 as a binary float is exactly 10**30's nearest double;
    # at scale 2 the exact scaled integer is ...483865600 (the old scaleb path was
    # off by 34,400 minor units).
    result = Money.from_float(1e30, currency="USD", scale=2, rounding=RoundingMode.HALF_UP)
    assert is_ok(result)
    assert result.value.value == 100000000000000001988462483865600
    assert result.value.value == Fraction(1e30).numerator * 100


def test_from_float_half_modes_break_ties_exactly() -> None:
    # 2.5 is exactly representable; HALF_UP goes away from zero, HALF_EVEN to even.
    up = Money.from_float(2.5, currency="USD", scale=0, rounding=RoundingMode.HALF_UP)
    even = Money.from_float(2.5, currency="USD", scale=0, rounding=RoundingMode.HALF_EVEN)
    assert is_ok(up)
    assert is_ok(even)
    assert up.value.value == 3
    assert even.value.value == 2
    # Negative ties: HALF_UP is away from zero, DOWN toward zero, FLOOR to -inf.
    neg_up = Money.from_float(-2.5, currency="USD", scale=0, rounding=RoundingMode.HALF_UP)
    neg_down = Money.from_float(-2.7, currency="USD", scale=0, rounding=RoundingMode.DOWN)
    neg_floor = Money.from_float(-2.3, currency="USD", scale=0, rounding=RoundingMode.FLOOR)
    assert is_ok(neg_up)
    assert is_ok(neg_down)
    assert is_ok(neg_floor)
    assert neg_up.value.value == -3
    assert neg_down.value.value == -2
    assert neg_floor.value.value == -3


def test_from_float_boundary_is_shared_and_exact_for_price_and_quantity() -> None:
    # H1 applies to every from_float boundary sharing _coerce_float_to_scaled_int.
    price = Price.from_float(0.1, instrument=_instrument(), scale=30, rounding=RoundingMode.HALF_UP)
    quantity = Quantity.from_float(0.1, unit="lot", scale=30, rounding=RoundingMode.HALF_UP)
    assert is_ok(price)
    assert is_ok(quantity)
    assert price.value.value == 100000000000000005551115123126
    assert quantity.value.value == 100000000000000005551115123126


# --- mixed-scale arithmetic (FM-4) ------------------------------------------


def test_mixed_scale_addition_auto_promotes_to_finer_scale() -> None:
    # 1.50 (scale 2) + 0.2500 (scale 4) = 1.7500, promoted losslessly to scale 4.
    coarse = _money(150, "USD", 2)
    fine = _money(2500, "USD", 4)
    result = coarse.add(fine)
    assert is_ok(result)
    assert result.value.value == 17500
    assert result.value.scale == 4


def test_mixed_scale_subtraction_auto_promotes() -> None:
    result = _money(150, "USD", 2).subtract(_money(2500, "USD", 4))
    assert is_ok(result)
    assert result.value.value == 12500
    assert result.value.scale == 4


def test_arithmetic_refuses_cross_currency_never_silently_converts() -> None:
    result = _money(150, "USD", 2).add(_money(150, "EUR", 2))
    assert is_refusal(result)
    assert result.context["field"] == "currency"


def test_arithmetic_refuses_non_money_operand() -> None:
    result = _money(150).add("not money")
    assert is_refusal(result)
    assert result.context["field"] == "other"


# --- Price and delta-typed subtraction --------------------------------------


def test_price_is_instrument_tagged_and_refuses_float() -> None:
    instrument = _instrument()
    ok = Price.try_create(108925, instrument, 5)
    assert is_ok(ok)
    assert ok.value.instrument is instrument
    floaty = Price.try_create(1.08925, instrument, 5)
    assert is_refusal(floaty)
    assert floaty.context["field"] == "value"


def test_price_refuses_missing_instrument_and_bad_scale() -> None:
    bad_instrument = Price.try_create(1, "EURUSD", 5)
    assert is_refusal(bad_instrument)
    assert bad_instrument.context["field"] == "instrument"
    bad_scale = Price.try_create(1, _instrument(), -2)
    assert is_refusal(bad_scale)
    assert bad_scale.context["field"] == "scale"


def test_price_subtraction_yields_a_first_class_price_delta() -> None:
    instrument = _instrument()
    high = Price.try_create(108930, instrument, 5)
    low = Price.try_create(108925, instrument, 5)
    assert is_ok(high)
    assert is_ok(low)
    result = high.value.subtract(low.value)
    assert is_ok(result)
    delta = result.value
    assert isinstance(delta, PriceDelta)
    assert not isinstance(delta, Price)  # distinct type, not just a Price
    assert delta.value == 5
    assert delta.instrument is instrument


def test_price_subtraction_promotes_mixed_scales() -> None:
    instrument = _instrument()
    a = Price.try_create(10893, instrument, 4)
    b = Price.try_create(108925, instrument, 5)
    assert is_ok(a)
    assert is_ok(b)
    result = a.value.subtract(b.value)
    assert is_ok(result)
    assert result.value.value == 108930 - 108925
    assert result.value.scale == 5


def test_price_subtraction_refuses_other_instrument_and_non_price() -> None:
    instrument = _instrument()
    price = Price.try_create(1, instrument, 5)
    assert is_ok(price)
    other = Price.try_create(1, _instrument("GBPUSD"), 5)
    assert is_ok(other)
    mismatch = price.value.subtract(other.value)
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == "instrument"
    not_price = price.value.subtract(42)
    assert is_refusal(not_price)
    assert not_price.context["field"] == "other"


def test_price_from_float_boundary() -> None:
    ok = Price.from_float(1.08925, instrument=_instrument(), scale=5, rounding=RoundingMode.HALF_UP)
    assert is_ok(ok)
    assert ok.value.value == 108925
    bad = Price.from_float(float("nan"), instrument=_instrument(), scale=5, rounding="down")
    assert is_refusal(bad)


# --- PriceDelta arithmetic, pips, and money conversion ----------------------


def test_price_delta_refuses_float_missing_instrument_and_bad_scale() -> None:
    floaty = PriceDelta.try_create(1.0, _instrument(), 5)
    assert is_refusal(floaty)
    assert floaty.context["field"] == "value"
    no_instrument = PriceDelta.try_create(1, None, 5)
    assert is_refusal(no_instrument)
    assert no_instrument.context["field"] == "instrument"
    bad_scale = PriceDelta.try_create(1, _instrument(), "five")
    assert is_refusal(bad_scale)
    assert bad_scale.context["field"] == "scale"


def test_price_delta_add_and_subtract_promote_and_refuse() -> None:
    instrument = _instrument()
    a = _delta(5, 5, instrument)
    b = _delta(30, 6, instrument)
    added = a.add(b)
    assert is_ok(added)
    assert added.value.value == 50 + 30  # a promoted to scale 6
    assert added.value.scale == 6
    subtracted = b.subtract(a)
    assert is_ok(subtracted)
    assert subtracted.value.value == 30 - 50
    mismatch = a.add(_delta(1, 5, _instrument("GBPUSD")))
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == "instrument"
    not_delta = a.add(7)
    assert is_refusal(not_delta)
    assert not_delta.context["field"] == "other"


def test_delta_in_pips_uses_metadata_pip_never_hardcoded() -> None:
    instrument = _instrument()
    move = _delta(50, 5, instrument)  # 0.00050
    pip = _delta(10, 5, instrument)  # a pip = 0.00010, sourced from metadata
    result = move.in_pips(pip)
    assert is_ok(result)
    assert result.value.unit_kind is UnitKind.DIMENSIONLESS_RATIO
    assert result.value.as_fraction() == 5  # five pips


def test_delta_in_pips_refuses_absent_pip_as_unavailable_dependency() -> None:
    result = _delta(50).in_pips(None)
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert result.context["field"] == "pip"


def test_delta_in_pips_refuses_bad_pip_shapes() -> None:
    instrument = _instrument()
    move = _delta(50, 5, instrument)
    not_a_delta = move.in_pips(10)
    assert is_refusal(not_a_delta)
    assert not_a_delta.category is RefusalCategory.INVALID_INPUT
    other_instrument = move.in_pips(_delta(10, 5, _instrument("GBPUSD")))
    assert is_refusal(other_instrument)
    assert other_instrument.context["field"] == "pip"
    zero_pip = move.in_pips(_delta(0, 5, instrument))
    assert is_refusal(zero_pip)
    assert zero_pip.context["field"] == "pip"


def test_delta_to_money_needs_a_value_factor_from_metadata() -> None:
    instrument = _instrument()
    move = _delta(100, 5, instrument)  # 0.00100
    quantity = _quantity(100, "unit", 0)  # 100 units
    absent = move.to_money(None, quantity, scale=2)
    assert is_refusal(absent)
    assert absent.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert absent.context["field"] == "value_factor"


def test_delta_to_money_converts_exactly_via_value_factor() -> None:
    instrument = _instrument()
    move = _delta(100, 5, instrument)  # 0.00100 price units
    quantity = _quantity(2, "lot", 0)  # 2 lots
    # value-factor: 100000 money-minor-units of price-delta per lot => 1.0 money per full price unit.
    vf = ValueFactor.try_create(100000, 1, instrument, "USD")
    assert is_ok(vf)
    result = move.to_money(vf.value, quantity, scale=2)
    assert is_ok(result)
    # 0.00100 * 100000 * 2 = 200 money units -> at scale 2 that is 20000.
    assert result.value.value == 20000
    assert result.value.currency == "USD"


def test_delta_to_money_refuses_bad_operands_and_inexact_scale() -> None:
    instrument = _instrument()
    move = _delta(1, 0, instrument)
    quantity = _quantity(1, "lot", 0)
    vf = ValueFactor.try_create(1, 1, instrument, "USD")
    assert is_ok(vf)
    not_vf = move.to_money(42, quantity, scale=2)
    assert is_refusal(not_vf)
    assert not_vf.context["field"] == "value_factor"
    other_vf = ValueFactor.try_create(1, 1, _instrument("GBPUSD"), "USD")
    assert is_ok(other_vf)
    mismatch = move.to_money(other_vf.value, quantity, scale=2)
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == "value_factor"
    not_qty = move.to_money(vf.value, "two", scale=2)
    assert is_refusal(not_qty)
    assert not_qty.context["field"] == "quantity"
    bad_scale = move.to_money(vf.value, quantity, scale=-1)
    assert is_refusal(bad_scale)
    assert bad_scale.context["field"] == "scale"
    # An inexact result (value-factor 1/3) is refused, never silently rounded.
    inexact_vf = ValueFactor.try_create(1, 3, instrument, "USD")
    assert is_ok(inexact_vf)
    inexact = move.to_money(inexact_vf.value, quantity, scale=2)
    assert is_refusal(inexact)
    assert inexact.context["field"] == "scale"


# --- Quantity ---------------------------------------------------------------


def test_quantity_construction_and_refusals() -> None:
    ok = Quantity.try_create(100, "lot", 2)
    assert is_ok(ok)
    assert ok.value.unit == "lot"
    floaty = Quantity.try_create(1.0, "lot", 2)
    assert is_refusal(floaty)
    assert floaty.context["field"] == "value"
    blank_unit = Quantity.try_create(100, "  ", 2)
    assert is_refusal(blank_unit)
    assert blank_unit.context["field"] == "unit"
    bad_scale = Quantity.try_create(100, "lot", -3)
    assert is_refusal(bad_scale)
    assert bad_scale.context["field"] == "scale"


def test_quantity_arithmetic_promotes_and_refuses_cross_unit() -> None:
    added = _quantity(100, "lot", 2).add(_quantity(5000, "lot", 4))
    assert is_ok(added)
    assert added.value.value == 10000 + 5000  # 1.00 lot promoted to scale 4
    assert added.value.scale == 4
    subtracted = _quantity(100, "lot", 2).subtract(_quantity(5000, "lot", 4))
    assert is_ok(subtracted)
    assert subtracted.value.value == 10000 - 5000
    cross_unit = _quantity(1, "lot").add(_quantity(1, "share"))
    assert is_refusal(cross_unit)
    assert cross_unit.context["field"] == "unit"
    not_qty = _quantity(1, "lot").subtract(3)
    assert is_refusal(not_qty)
    assert not_qty.context["field"] == "other"


def test_quantity_from_float_boundary() -> None:
    ok = Quantity.from_float(1.25, unit="lot", scale=2, rounding=RoundingMode.HALF_UP)
    assert is_ok(ok)
    assert ok.value.value == 125
    bad = Quantity.from_float("1.25", unit="lot", scale=2, rounding="half-up")
    assert is_refusal(bad)


# --- ExactRational and ValueFactor ------------------------------------------


def test_exact_rational_reduces_and_requires_a_unit_kind() -> None:
    result = ExactRational.try_create(6, 4, UnitKind.DIMENSIONLESS_RATIO)
    assert is_ok(result)
    assert (result.value.numerator, result.value.denominator) == (3, 2)


def test_exact_rational_normalizes_sign_onto_numerator() -> None:
    result = ExactRational.try_create(1, -2, "r-multiple")
    assert is_ok(result)
    assert result.value.numerator == -1
    assert result.value.denominator == 2  # denominator strictly positive


def test_exact_rational_refuses_float_parts_and_zero_denominator() -> None:
    float_num = ExactRational.try_create(1.5, 2, UnitKind.COUNT)
    assert is_refusal(float_num)
    assert float_num.context["field"] == "numerator"
    float_den = ExactRational.try_create(1, 2.0, UnitKind.COUNT)
    assert is_refusal(float_den)
    assert float_den.context["field"] == "denominator"
    zero_den = ExactRational.try_create(1, 0, UnitKind.COUNT)
    assert is_refusal(zero_den)
    assert zero_den.context["field"] == "denominator"


def test_exact_rational_null_unit_kind_is_a_typed_refusal_never_a_default() -> None:
    null_kind = ExactRational.try_create(1, 2, None)
    assert is_refusal(null_kind)
    assert null_kind.category is RefusalCategory.INVALID_INPUT
    assert null_kind.context["field"] == "unit_kind"
    unknown_kind = ExactRational.try_create(1, 2, 123)
    assert is_refusal(unknown_kind)
    assert unknown_kind.context["field"] == "unit_kind"
    unknown_str = ExactRational.try_create(1, 2, "not-a-kind")
    assert is_refusal(unknown_str)
    assert unknown_str.context["field"] == "unit_kind"


def test_value_factor_construction_and_refusals() -> None:
    instrument = _instrument()
    ok = ValueFactor.try_create(2, 4, instrument, "USD")
    assert is_ok(ok)
    assert (ok.value.numerator, ok.value.denominator) == (1, 2)  # reduced
    assert ok.value.currency == "USD"
    float_num = ValueFactor.try_create(1.0, 1, instrument, "USD")
    assert is_refusal(float_num)
    assert float_num.context["field"] == "numerator"
    float_den = ValueFactor.try_create(1, 1.0, instrument, "USD")
    assert is_refusal(float_den)
    assert float_den.context["field"] == "denominator"
    zero_den = ValueFactor.try_create(1, 0, instrument, "USD")
    assert is_refusal(zero_den)
    assert zero_den.context["field"] == "denominator"
    bad_instrument = ValueFactor.try_create(1, 1, "EURUSD", "USD")
    assert is_refusal(bad_instrument)
    assert bad_instrument.context["field"] == "instrument"
    blank_currency = ValueFactor.try_create(1, 1, instrument, " ")
    assert is_refusal(blank_currency)
    assert blank_currency.context["field"] == "currency"


# --- canonical fp1 identity: equal value implies equal fingerprint ----------


def test_money_canonical_form_is_scale_invariant() -> None:
    # The same amount stored at two scales cannot fork identity (DEC-0158).
    a = _money(150, "USD", 2).fp1_identity()  # 1.50
    b = _money(15000, "USD", 4).fp1_identity()  # 1.5000
    assert a == b
    assert a["num"] == 3 and a["den"] == 2  # reduced to lowest terms
    assert a["format_version"] == CONTRACT_FORMAT_VERSION == 1


def test_canonical_form_reduces_and_keeps_sign_on_numerator() -> None:
    negative = _money(-150, "USD", 2).fp1_identity()
    assert negative["num"] == -3
    assert negative["den"] == 2  # denominator strictly positive, both keys present


def test_zero_canonical_form_is_stable() -> None:
    content = _money(0, "USD", 2).fp1_identity()
    assert content["num"] == 0
    assert content["den"] == 1


def test_price_and_delta_never_share_a_fingerprint() -> None:
    instrument = _instrument()
    price = Price.try_create(15000, instrument, 4)
    delta = PriceDelta.try_create(15000, instrument, 4)
    assert is_ok(price)
    assert is_ok(delta)
    # Same magnitude, same instrument, but a level and a delta are distinct
    # identities — the class discriminator separates them.
    assert price.value.fp1_identity() != delta.value.fp1_identity()
    assert price.value.fp1_identity()["class"] == "price"
    assert delta.value.fp1_identity()["class"] == "price-delta"


def test_every_canonical_form_stamps_format_version_one() -> None:
    instrument = _instrument()
    vf = ValueFactor.try_create(1, 2, instrument, "USD")
    rational = ExactRational.try_create(3, 2, UnitKind.R_MULTIPLE)
    assert is_ok(vf)
    assert is_ok(rational)
    forms = [
        _money(150).fp1_identity(),
        Price(15000, instrument, 5).fp1_identity(),
        _delta(5).fp1_identity(),
        _quantity(100).fp1_identity(),
        rational.value.fp1_identity(),
        vf.value.fp1_identity(),
    ]
    for form in forms:
        assert form["format_version"] == 1
        assert "num" in form and "den" in form  # two-key serialization always present


def test_quantity_and_value_factor_canonical_content() -> None:
    instrument = _instrument("EURUSD", "venue-x")
    quantity = _quantity(250, "lot", 2)  # 2.50 lots
    q_form = quantity.fp1_identity()
    assert q_form == {
        "class": "quantity",
        "unit_kind": "quantity(unit)",
        "unit": "lot",
        "num": 5,
        "den": 2,
        "format_version": 1,
    }
    vf = ValueFactor.try_create(10, 1, instrument, "USD")
    assert is_ok(vf)
    vf_form = vf.value.fp1_identity()
    assert vf_form["class"] == "value-factor"
    assert vf_form["instrument"] == {"venue": "venue-x", "symbol": "EURUSD"}
    assert vf_form["currency"] == "USD"


def test_unchecked_constructor_is_available_for_trusted_use() -> None:
    money = Money(150, "USD", 2)
    assert money.value == 150
    assert money.as_fraction() == Fraction(3, 2)


# --- L2: the maximum scale bound --------------------------------------------


def test_scale_at_the_maximum_is_accepted() -> None:
    assert is_ok(Money.try_create(1, "USD", MAX_SCALE))


def test_scale_above_the_maximum_is_refused_as_invalid_input() -> None:
    # Regression (L2): scale sits in the exponent of 10**scale, so an unbounded
    # scale (e.g. 10**6) is a DoS foot-gun. A scale above MAX_SCALE is refused
    # before as_fraction() ever computes a pathological power of ten.
    result = Money.try_create(1, "USD", MAX_SCALE + 1)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "scale"
    assert result.context["max_scale"] == MAX_SCALE


def test_absurd_scale_is_refused_across_all_value_types() -> None:
    instrument = _instrument()
    huge = 10**6
    assert is_refusal(Money.try_create(1, "USD", huge))
    assert is_refusal(Price.try_create(1, instrument, huge))
    assert is_refusal(PriceDelta.try_create(1, instrument, huge))
    assert is_refusal(Quantity.try_create(1, "lot", huge))
    # The float conversion boundary and the delta->money boundary bound scale too.
    assert is_refusal(Money.from_float(1.5, currency="USD", scale=huge, rounding="half-up"))


# --- L7: Price + PriceDelta = Price (the affine/vector split) ----------------


def test_price_plus_delta_yields_a_price() -> None:
    # Regression (L7): Price - Price = PriceDelta (a vector); the missing companion
    # is Price + PriceDelta = Price (a level again). It completes the affine split.
    instrument = _instrument()
    level = Price.try_create(11000, instrument, 4)
    delta = PriceDelta.try_create(250, instrument, 4)
    assert is_ok(level)
    assert is_ok(delta)
    result = level.value.add(delta.value)
    assert is_ok(result)
    moved = result.value
    assert isinstance(moved, Price)
    assert moved.value == 11250
    assert moved.instrument is instrument


def test_price_add_promotes_mixed_scales_like_subtraction() -> None:
    instrument = _instrument()
    level = Price.try_create(11000, instrument, 4)
    delta = PriceDelta.try_create(5, instrument, 5)
    assert is_ok(level)
    assert is_ok(delta)
    result = level.value.add(delta.value)
    assert is_ok(result)
    assert result.value.scale == 5
    assert result.value.value == 110000 + 5


def test_price_add_refuses_a_price_operand() -> None:
    # Adding two affine levels is meaningless — a Price adds only a delta (a vector).
    instrument = _instrument()
    level = Price.try_create(11000, instrument, 4)
    other_level = Price.try_create(9000, instrument, 4)
    assert is_ok(level)
    assert is_ok(other_level)
    result = level.value.add(other_level.value)
    assert is_refusal(result)
    assert result.context["field"] == "other"


def test_price_add_refuses_a_differently_instrumented_delta() -> None:
    instrument = _instrument()
    level = Price.try_create(11000, instrument, 4)
    foreign = PriceDelta.try_create(1, _instrument("GBPUSD"), 4)
    assert is_ok(level)
    assert is_ok(foreign)
    result = level.value.add(foreign.value)
    assert is_refusal(result)
    assert result.context["field"] == "instrument"


def test_price_add_is_the_inverse_of_subtraction() -> None:
    # (a - b) is a delta; b + (a - b) recovers a — the affine round-trip.
    instrument = _instrument()
    a = Price.try_create(108930, instrument, 5)
    b = Price.try_create(108925, instrument, 5)
    assert is_ok(a)
    assert is_ok(b)
    delta = b.value.subtract(a.value)  # note: b - a
    assert is_ok(delta)
    recovered = a.value.add(delta.value)
    assert is_ok(recovered)
    assert recovered.value.value == b.value.value
    assert recovered.value.scale == b.value.scale
