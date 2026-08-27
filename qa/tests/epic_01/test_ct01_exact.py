"""Epic 1 — CT-01 exact money/price/quantity (Story 1.4, exact.py). L1 (100% branch).

Independent, requirements-derived assertions (E1-U16..U28), incl. mutmut pins
(E1-U24 rounding-at-zero, E1-U25 scale-range, E1-U26 NaN/inf, E1-U27
missing-rounding-mode). Authored from CT-01 (docs/contracts/ct-01-money-quantity.yaml),
FM-1/FM-4, epics.md Story 1.4. Source code is read-only evidence.
"""

from __future__ import annotations

from fractions import Fraction

from qmf.core.exact import (
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
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal

CLOSED_UNIT_KIND_VOCAB = {
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


def _ok(result: Result[object]) -> object:
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def _refusal(result: Result[object]) -> TypedRefusal:
    assert is_refusal(result), f"expected a TypedRefusal, got {result!r}"
    return result


def _instrument() -> Instrument:
    return _ok(Instrument.try_create(_ok(VenueId.try_create("VEN-1")), "EURUSD"))


# E1-U16 -----------------------------------------------------------------------
def test_e1_u16_values_are_scaled_integers_price_instrument_tagged() -> None:
    """CT-01: Money/Price/Quantity construct as whole-number scaled integers; Price
    is instrument-tagged (never single-currency-tagged); Quantity's unit is opaque."""
    money = _ok(Money.try_create(150, "USD", 2))
    assert (money.value, money.currency, money.scale) == (150, "USD", 2)
    price = _ok(Price.try_create(110000, _instrument(), 5))
    assert isinstance(price.instrument, Instrument)
    assert not hasattr(price, "currency")  # a price is never single-currency-tagged
    qty = _ok(Quantity.try_create(3, "lot", 0))
    assert (qty.value, qty.unit, qty.scale) == (3, "lot", 0)
    # non-integer value refused (whole-number scaled integer only)
    assert is_refusal(Money.try_create("150", "USD", 2))


# E1-U17 -----------------------------------------------------------------------
def test_e1_u17_unit_kind_from_closed_vocab_null_is_refusal() -> None:
    """CT-01 / DEC-0154: every value carries a unit-kind from the closed vocabulary;
    a null/absent unit-kind is a typed refusal, never a default."""
    assert {m.value for m in UnitKind} == CLOSED_UNIT_KIND_VOCAB
    assert _ok(Money.try_create(1, "USD", 0)).unit_kind is UnitKind.MONEY
    assert _ok(Quantity.try_create(1, "lot", 0)).unit_kind is UnitKind.QUANTITY
    # ExactRational takes an explicit unit-kind: null -> refusal (never default).
    r_null = _refusal(ExactRational.try_create(1, 2, None))
    assert r_null.context["field"] == "unit_kind"
    r_bad = _refusal(ExactRational.try_create(1, 2, "not-a-unit-kind"))
    assert r_bad.context["field"] == "unit_kind"
    assert _ok(ExactRational.try_create(1, 2, UnitKind.DIMENSIONLESS_RATIO)).unit_kind is (
        UnitKind.DIMENSIONLESS_RATIO
    )


# E1-U18 -----------------------------------------------------------------------
def test_e1_u18_binary_float_on_money_path_refused_invalid_input() -> None:
    """CT-01 FM-1 / DEC-0105: a binary float passed to try_create(Money/Price/
    Quantity) -> invalid input refusal."""
    for result in (
        Money.try_create(1.5, "USD", 2),
        Price.try_create(1.5, _instrument(), 5),
        Quantity.try_create(1.5, "lot", 0),
    ):
        r = _refusal(result)
        assert r.category is RefusalCategory.INVALID_INPUT
        assert r.context["field"] == "value"
    # bool is an int subclass but is NOT a valid money value.
    assert is_refusal(Money.try_create(True, "USD", 2))


# E1-U19 -----------------------------------------------------------------------
def test_e1_u19_float_reenters_only_through_named_boundary_with_rounding() -> None:
    """CT-01 / DEC-0105: a float re-enters only through the named conversion boundary
    that states its rounding mode explicitly; an unstated crossing refuses."""
    sanctioned = Money.from_float(1.55, currency="USD", scale=2, rounding=RoundingMode.HALF_UP)
    money = _ok(sanctioned)
    assert (money.value, money.currency, money.scale) == (155, "USD", 2)
    # Unstated crossing (try_create) refuses the same float.
    assert is_refusal(Money.try_create(1.55, "USD", 2))


# E1-U20 -----------------------------------------------------------------------
def test_e1_u20_mixed_scale_same_currency_auto_promotes_to_finer_scale() -> None:
    """CT-01 FM-4: mixed-scale, same currency, losslessly promotable -> auto-promotes
    to the finer scale, result value correct."""
    a = _ok(Money.try_create(150, "USD", 2))  # 1.50
    b = _ok(Money.try_create(5, "USD", 1))  # 0.50
    total = _ok(a.add(b))
    assert total.scale == 2  # promoted to finer scale
    assert total.value == 200  # 1.50 + 0.50 = 2.00 exactly
    assert total.as_fraction() == Fraction(2)


# E1-U21 -----------------------------------------------------------------------
def test_e1_u21_not_losslessly_representable_refuses_never_silent_round() -> None:
    """CT-01 FM-4 / DEC-0109: an arithmetic result not exactly representable at the
    requested scale -> typed refusal; never an implicit rescale or silent round."""
    instrument = _instrument()
    pd = _ok(PriceDelta.try_create(1, instrument, 0))  # magnitude 1
    vf = _ok(ValueFactor.try_create(1, 3, instrument, "USD"))  # 1/3, non-terminating
    qty = _ok(Quantity.try_create(1, "lot", 0))
    # amount = 1 * 1/3 * 1 = 1/3, which is not exact at scale 2 -> refusal.
    r = _refusal(pd.to_money(vf, qty, scale=2))
    assert r.category is RefusalCategory.INVALID_INPUT
    assert "exactly representable" in r.context["reason"] or "round" in r.context["reason"]


# E1-U22 -----------------------------------------------------------------------
def test_e1_u22_price_minus_price_is_first_class_pricedelta() -> None:
    """CT-01 / DEC-0131: Price - Price -> first-class PriceDelta(instrument, scale), a
    type distinct from Price; pip/point comes from CT-03 metadata, never hardcoded."""
    instrument = _instrument()
    p1 = _ok(Price.try_create(110500, instrument, 5))
    p2 = _ok(Price.try_create(110000, instrument, 5))
    delta = _ok(p1.subtract(p2))
    assert isinstance(delta, PriceDelta)
    assert not isinstance(delta, Price)
    assert delta.value == 500 and delta.scale == 5
    # pip/point comes from a metadata-supplied PriceDelta, not a hardcoded constant.
    pip = _ok(PriceDelta.try_create(1, instrument, 4))  # 1 pip = 0.0001
    pips = _ok(delta.in_pips(pip))
    assert pips.as_fraction() == delta.as_fraction() / pip.as_fraction()


# E1-U23 -----------------------------------------------------------------------
def test_e1_u23_absent_value_factor_is_unavailable_dependency() -> None:
    """CT-01 / DEC-0154: an absent value-factor -> unavailable dependency refusal,
    never a silent conversion."""
    instrument = _instrument()
    pd = _ok(PriceDelta.try_create(10, instrument, 5))
    qty = _ok(Quantity.try_create(1, "lot", 0))
    r = _refusal(pd.to_money(None, qty, scale=2))
    assert r.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # An absent pip is likewise unavailable-dependency, never a silent 0/default.
    r_pip = _refusal(pd.in_pips(None))
    assert r_pip.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# E1-U24 (mutmut pin exact.py:304 rounding direction at zero) -------------------
def test_e1_u24_rounding_direction_at_zero_boundary_exact() -> None:
    """CT-01 / DEC-0105 (pin exact.py:304): the required rounding mode selects the
    exact integer at value < 0, = 0, and > 0. Asserts the exact integer per mode —
    kills the <=0/<1 shifts and the ceil/floor swap."""

    def scaled(v: float, mode: RoundingMode) -> int:
        return _ok(Money.from_float(v, currency="USD", scale=0, rounding=mode)).value

    # Exactly zero -> zero under every mode (no direction ambiguity).
    for mode in RoundingMode:
        assert scaled(0.0, mode) == 0

    # Half away from zero (HALF_UP): +0.5 -> 1, -0.5 -> -1.
    assert scaled(0.5, RoundingMode.HALF_UP) == 1
    assert scaled(-0.5, RoundingMode.HALF_UP) == -1
    # Half to even (HALF_EVEN): 0.5 -> 0, 1.5 -> 2, 2.5 -> 2, -1.5 -> -2.
    assert scaled(0.5, RoundingMode.HALF_EVEN) == 0
    assert scaled(1.5, RoundingMode.HALF_EVEN) == 2
    assert scaled(2.5, RoundingMode.HALF_EVEN) == 2
    assert scaled(-1.5, RoundingMode.HALF_EVEN) == -2
    # FLOOR toward -inf: 0.5 -> 0, -0.5 -> -1.
    assert scaled(0.5, RoundingMode.FLOOR) == 0
    assert scaled(-0.5, RoundingMode.FLOOR) == -1
    # CEILING toward +inf: 0.5 -> 1, -0.5 -> 0.
    assert scaled(0.5, RoundingMode.CEILING) == 1
    assert scaled(-0.5, RoundingMode.CEILING) == 0
    # DOWN toward zero: 0.5 -> 0, -0.5 -> 0.
    assert scaled(0.5, RoundingMode.DOWN) == 0
    assert scaled(-0.5, RoundingMode.DOWN) == 0
    # UP away from zero: 0.5 -> 1, -0.5 -> -1.
    assert scaled(0.5, RoundingMode.UP) == 1
    assert scaled(-0.5, RoundingMode.UP) == -1


# E1-U25 (mutmut pin exact.py:225 scale range) ---------------------------------
def test_e1_u25_scale_range_endpoints_refused_with_given_echo() -> None:
    """CT-01 (pin exact.py:225): a scale outside [0, MAX_SCALE] (negative, or above
    the cap) -> refusal echoing the offending scale; scale 0 accepted."""
    assert _ok(Money.try_create(1, "USD", 0)).scale == 0  # lower endpoint accepted
    neg = _refusal(Money.try_create(1, "USD", -1))
    assert neg.category is RefusalCategory.INVALID_INPUT
    assert neg.context["field"] == "scale"
    assert neg.context["given"] == repr(-1)  # `given` echoes the offending scale
    huge = _refusal(Money.try_create(1, "USD", 10**6))
    assert huge.context["field"] == "scale"


# E1-U26 (mutmut pin exact.py:337 NaN/inf) -------------------------------------
def test_e1_u26_nan_and_infinity_cannot_cross_float_boundary() -> None:
    """CT-01 / DEC-0105: NaN and infinity cannot cross the float conversion boundary
    -> invalid input refusal."""
    for bad in (float("nan"), float("inf"), float("-inf")):
        r = _refusal(Money.from_float(bad, currency="USD", scale=2, rounding=RoundingMode.HALF_UP))
        assert r.category is RefusalCategory.INVALID_INPUT
        assert r.context["field"] == "value"


# E1-U27 (mutmut pin exact.py:337 missing rounding) ----------------------------
def test_e1_u27_named_boundary_requires_explicit_rounding_mode() -> None:
    """CT-01 / DEC-0105: the named float boundary requires an explicit rounding mode;
    a missing/None rounding mode -> refusal listing the allowed modes."""
    r = _refusal(Money.from_float(1.5, currency="USD", scale=2, rounding=None))
    assert r.context["field"] == "rounding"
    assert set(r.context["allowed"]) == {m.value for m in RoundingMode}
    # An unknown rounding-mode string is likewise refused.
    assert is_refusal(Money.from_float(1.5, currency="USD", scale=2, rounding="banker"))


# E1-U28 -----------------------------------------------------------------------
def test_e1_u28_foreign_money_verbatim_absent_scale_refused() -> None:
    """CT-01 / DEC-0105/0141: foreign money is stored verbatim at its declared scale;
    an absent declared scale is a refusal, never an assumed default."""
    # A JPY amount declared at scale 0 (no minor units) is stored verbatim.
    jpy = _ok(Money.try_create(1234, "JPY", 0))
    assert (jpy.value, jpy.currency, jpy.scale) == (1234, "JPY", 0)
    # Absent scale -> refusal (never defaulted to 2 or any value).
    r = _refusal(Money.try_create(1234, "JPY", None))
    assert r.context["field"] == "scale"
