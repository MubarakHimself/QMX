"""CT-01 — exact money, price, and quantity values (COMP-QMF-CORE).

The exact-value vocabulary every QMF package shares, defined here in ``qmf-core``
and nowhere else. Money, Price, and Quantity are **whole-number scaled integers**
— an integer count at a declared scale (number of decimal places) — never binary
floats (CT-01; DEC-0105):

* :class:`Money` — ``Money(currency, scale)``: a count of a currency's minor
  units. ``currency`` is an opaque tag, stored verbatim, never parsed.
* :class:`Price` — ``Price(instrument, scale)``: an instrument-tagged **ratio**,
  never tagged with a single currency. Prices are affine levels: subtracting two
  Prices yields a :class:`PriceDelta`, a first-class value *distinct* from Price.
* :class:`Quantity` — ``Quantity(unit, scale)``: a count in an opaque unit (lot,
  share, coin, contract), never parsed.
* :class:`PriceDelta` — ``PriceDelta(instrument, scale)``: the closed, delta-typed
  result of price subtraction, and the vector companion to the affine Price.
* :class:`ExactRational` — a numerator/denominator pair carrying a declared
  :class:`UnitKind`, extending the exact idiom to every non-integer parameter
  (ratios, multiples, tolerances) so binary floats never appear in identity.
* :class:`ValueFactor` — ``value-factor(instrument, currency)``: money per
  price-delta per quantity (the tick/point/contract value), an exact rational
  sourced only from venue instrument-metadata records.

Three laws this module enforces (CT-01; DEC-0105, DEC-0109, DEC-0154, DEC-0158):

**The money-path taint.** Any value that transitively contributes to an order
quantity, price, P&L, or balance is on the money path, and a binary ``float`` is
banned there. Every ``try_create`` refuses a float value with an ``invalid input``
typed refusal (FM-1). A float re-enters only through a **named conversion
boundary** — :meth:`Money.from_float` and its siblings — that states its rounding
mode explicitly.

**Mixed-scale arithmetic.** Same-currency (or same-unit / same-instrument)
arithmetic auto-promotes losslessly to the finer scale; an incompatible operand
(a different currency, unit, instrument, or value class) returns a typed refusal —
never an implicit rescale or silent rounding (FM-4).

**Canonical identity.** Every value carries a :class:`UnitKind` from the closed,
addable-never-redefined vocabulary — a null unit-kind is a typed refusal, never a
default. When a value enters ``fp1`` identity content it takes the pinned
canonical form (:meth:`Money.fp1_identity` et al.): the exact rational reduced to
lowest terms, denominator strictly positive, sign on the numerator, two-key
serialization, stamped with contract format version 1. The reduced rational is
the scale-normalized canonical storage form for its value class, so one amount
stored at two scales — or ``6/4`` versus ``3/2`` — can never fork identity, and
equal value implies equal fingerprint by construction (DEC-0158).

Every value type follows the one CT-04 construction pattern: an **unchecked
constructor** (the frozen dataclass) for trusted internal use, plus a validating
:meth:`try_create` factory returning ``Result[T] = Ok[T] | TypedRefusal``.

Stdlib only (DEC-0104). Frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from math import isfinite
from typing import Final

from qmf.core.identity import Instrument
from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "ExactRational",
    "Money",
    "Price",
    "PriceDelta",
    "Quantity",
    "RoundingMode",
    "UnitKind",
    "ValueFactor",
]

# Every serialized CT-01 artifact stamps this integer contract format version;
# its meaning never mutates — an incompatible change mints the next version
# (DEC-0103; versioning-from-birth L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1


class UnitKind(StrEnum):
    """The closed unit-kind vocabulary (CT-01; DEC-0154).

    Every exact value carries exactly one member. The set is **addable in a later
    spine amendment, never redefined**, and never extended per-Book or
    per-template. Parenthesised parameters (``currency``, ``instrument``) name the
    tags that live in separate fields on the value; the enum value is the exact
    vocabulary token so the closed set is inspectable verbatim.
    """

    MONEY = "money(currency)"
    PRICE_DELTA = "price-delta(instrument)"
    QUANTITY = "quantity(unit)"
    VALUE_FACTOR = "value-factor(instrument, currency)"
    R_MULTIPLE = "r-multiple"
    RATE = "rate(money-per-r)"
    COUNT = "count"
    DIMENSIONLESS_RATIO = "dimensionless-ratio"
    DURATION = "duration"
    INSTANT = "instant"


class RoundingMode(StrEnum):
    """A rounding mode stated explicitly at a named conversion boundary (CT-01).

    The member set is not pinned by the foundation spine — it is a
    venue/accounting-boundary detail — so this is a reasonable, addable set rather
    than a closed contract enum. Each maps to a stdlib :mod:`decimal` mode.
    """

    HALF_UP = "half-up"
    HALF_EVEN = "half-even"
    DOWN = "down"
    UP = "up"
    FLOOR = "floor"
    CEILING = "ceiling"


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a value factory returns.

    ``retryability`` is ``no`` — a malformed value part is a caller mistake, not a
    transient condition — and ``context`` always names the offending ``field`` and
    a human-legible ``reason`` (returned, never raised; CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unavailable(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unavailable dependency`` refusal a metadata-needing conversion
    returns when its instrument-metadata input is absent (CT-01; DEC-0154)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context=context,
    )


# --- validation helpers -----------------------------------------------------


def _as_plain_int(value: object) -> int | None:
    """Return ``value`` as a genuine ``int``, or ``None``.

    A ``bool`` (an int subclass) and a binary ``float`` are both rejected, keeping
    floats off the money path (FM-1). Returning the narrowed value — rather than a
    bare bool — lets each factory hand a typed ``int`` to its frozen constructor.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _as_scale(value: object) -> int | None:
    """Return ``value`` as a non-negative integer count of decimal places, or
    ``None``."""
    parsed = _as_plain_int(value)
    if parsed is None or parsed < 0:
        return None
    return parsed


def _clean_tag(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    Currency and unit tags are opaque: the returned token is the caller's string
    unchanged — never stripped, cased, or parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _require_instrument(value: object) -> Instrument | None:
    """Return ``value`` if it is a well-formed :class:`Instrument`, else ``None``.

    Defense in depth against an :class:`Instrument` built through the unchecked
    constructor with a blank part.
    """
    if (
        isinstance(value, Instrument)
        and value.symbol.strip() != ""
        and value.venue.value.strip() != ""
    ):
        return value
    return None


def _coerce_unit_kind(value: object) -> UnitKind | None:
    """Resolve ``value`` to a :class:`UnitKind` member, or ``None`` if it names
    none. ``None`` in, ``None`` out — the caller distinguishes a null unit-kind."""
    if isinstance(value, UnitKind):
        return value
    if isinstance(value, str):
        try:
            return UnitKind(value)
        except ValueError:
            return None
    return None


def _coerce_rounding(value: object) -> RoundingMode | None:
    """Resolve ``value`` to a :class:`RoundingMode` member, or ``None``."""
    if isinstance(value, RoundingMode):
        return value
    if isinstance(value, str):
        try:
            return RoundingMode(value)
        except ValueError:
            return None
    return None


def _promote(value_a: int, scale_a: int, value_b: int, scale_b: int) -> tuple[int, int, int]:
    """Promote two scaled integers to their common finer scale, losslessly.

    Promotion to the finer scale multiplies the coarser count by a power of ten,
    so no digit is ever lost or invented — the counterpart of the FM-4 rule that
    forbids implicit rescale or silent rounding.
    """
    scale = max(scale_a, scale_b)
    promoted_a = value_a * 10 ** (scale - scale_a)
    promoted_b = value_b * 10 ** (scale - scale_b)
    return promoted_a, promoted_b, scale


def _round_fraction_to_int(value: Fraction, mode: RoundingMode) -> int:
    """Round an exact :class:`~fractions.Fraction` to an integer under ``mode``.

    Every step is exact integer arithmetic — no decimal context, no binary float
    — so no digit is ever silently rounded before the declared rounding mode runs
    (CT-01; DEC-0105). A :class:`~fractions.Fraction` keeps its denominator
    strictly positive, so ``divmod`` yields the floor and a non-negative remainder.
    """
    floor_value, remainder = divmod(value.numerator, value.denominator)
    if remainder == 0:
        return floor_value
    ceil_value = floor_value + 1
    if mode is RoundingMode.FLOOR:
        return floor_value
    if mode is RoundingMode.CEILING:
        return ceil_value
    if mode is RoundingMode.DOWN:  # toward zero
        return ceil_value if value < 0 else floor_value
    if mode is RoundingMode.UP:  # away from zero
        return floor_value if value < 0 else ceil_value
    # Half modes: compare the doubled remainder against the denominator exactly.
    twice_remainder = 2 * remainder
    if twice_remainder < value.denominator:
        return floor_value
    if twice_remainder > value.denominator:
        return ceil_value
    # Exactly halfway.
    if mode is RoundingMode.HALF_UP:  # ties away from zero
        return floor_value if value < 0 else ceil_value
    # HALF_EVEN: ties to the even neighbour.
    return floor_value if floor_value % 2 == 0 else ceil_value


def _coerce_float_to_scaled_int(
    value: object, scale: object, rounding: object
) -> int | TypedRefusal:
    """The shared float→scaled-integer conversion at the named boundary.

    A binary ``float`` re-enters an exact value only here, and only with an
    explicit rounding mode (CT-01; DEC-0105). The **exact binary value** of the
    float is taken — ``Fraction(value)`` is the float's true dyadic expansion,
    with no decimal approximation and no context-precision cap — then shifted to
    the target scale by an exact power of ten and rounded to an integer under the
    stated mode with exact integer arithmetic. NaN and infinity cannot cross.
    """
    if not isinstance(value, float):
        return _invalid(
            "value",
            "the float conversion boundary requires a binary float; construct exact "
            "values from integers with try_create",
            given=repr(value),
        )
    if not isfinite(value):
        return _invalid(
            "value",
            "NaN and infinity cannot cross the float conversion boundary",
            given=repr(value),
        )
    int_scale = _as_scale(scale)
    if int_scale is None:
        return _invalid(
            "scale",
            "scale is a non-negative integer count of decimal places",
            given=repr(scale),
        )
    mode = _coerce_rounding(rounding)
    if mode is None:
        return _invalid(
            "rounding",
            "the float conversion boundary must state an explicit rounding mode",
            given=repr(rounding),
            allowed=[member.value for member in RoundingMode],
        )
    shifted = Fraction(value) * (10**int_scale)
    return _round_fraction_to_int(shifted, mode)


def _instrument_content(instrument: Instrument) -> dict[str, object]:
    """The canonical ``fp1`` fragment for an instrument tag (its opaque parts)."""
    return {"venue": instrument.venue.value, "symbol": instrument.symbol}


# --- value types ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Money:
    """An exact amount of a currency: a scaled integer count of its minor units
    (CT-01; DEC-0105).

    ``value`` is a whole-number count at ``scale`` decimal places (scale 2 =
    hundredths). ``currency`` is an opaque tag stored verbatim, never tagged onto
    a Price. The unit-kind is fixed at ``money(currency)``.
    """

    value: int
    currency: str
    scale: int

    @property
    def unit_kind(self) -> UnitKind:
        """The fixed unit-kind ``money(currency)`` (CT-01; DEC-0154)."""
        return UnitKind.MONEY

    @classmethod
    def try_create(cls, value: object, currency: object, scale: object) -> Result[Money]:
        """Validate and build a :class:`Money`, returning value-or-refusal.

        A binary ``float`` ``value`` is refused as ``invalid input`` (FM-1); a
        blank ``currency`` or a non-integer/negative ``scale`` is likewise refused.
        """
        int_value = _as_plain_int(value)
        if int_value is None:
            return _invalid(
                "value",
                "money is an exact scaled integer; a binary float on the money path "
                "is refused (FM-1) — a float re-enters only through Money.from_float "
                "with an explicit rounding mode",
                given=repr(value),
            )
        token = _clean_tag(currency)
        if token is None:
            return _invalid(
                "currency",
                "a currency is a non-empty opaque tag, stored verbatim and never parsed",
                given=repr(currency),
            )
        int_scale = _as_scale(scale)
        if int_scale is None:
            return _invalid(
                "scale",
                "scale is a non-negative integer count of decimal places",
                given=repr(scale),
            )
        return Ok(cls(value=int_value, currency=token, scale=int_scale))

    @classmethod
    def from_float(
        cls, value: object, *, currency: object, scale: object, rounding: object
    ) -> Result[Money]:
        """The named float→Money conversion boundary (CT-01; DEC-0105).

        A binary float becomes an exact :class:`Money` only here, under the
        explicitly stated ``rounding`` mode; the raw float is never the stored
        value.
        """
        scaled = _coerce_float_to_scaled_int(value, scale, rounding)
        if isinstance(scaled, TypedRefusal):
            return scaled
        return cls.try_create(scaled, currency, scale)

    def add(self, other: object) -> Result[Money]:
        """Add another :class:`Money` of the same currency, promoting scales."""
        return self._combine(other, subtract=False)

    def subtract(self, other: object) -> Result[Money]:
        """Subtract another :class:`Money` of the same currency, promoting scales."""
        return self._combine(other, subtract=True)

    def _combine(self, other: object, *, subtract: bool) -> Result[Money]:
        if not isinstance(other, Money):
            return _invalid("other", "an operand must be a Money value", given=repr(other))
        if other.currency != self.currency:
            return _invalid(
                "currency",
                "cross-currency arithmetic has no implicit conversion; use a named "
                "value-factor boundary",
                left=self.currency,
                right=other.currency,
            )
        left, right, scale = _promote(self.value, self.scale, other.value, other.scale)
        combined = left - right if subtract else left + right
        return Ok(Money(value=combined, currency=self.currency, scale=scale))

    def as_fraction(self) -> Fraction:
        """The exact rational magnitude ``value / 10**scale``."""
        return Fraction(self.value, 10**self.scale)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this amount (DEC-0158).

        The magnitude is the exact rational reduced to lowest terms (denominator
        strictly positive, sign on the numerator, two keys always present), so an
        amount stored at two scales shares one fingerprint by construction.
        """
        magnitude = self.as_fraction()
        return {
            "class": "money",
            "unit_kind": UnitKind.MONEY.value,
            "currency": self.currency,
            "num": magnitude.numerator,
            "den": magnitude.denominator,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class Price:
    """An instrument-tagged ratio: a scaled integer level, never tagged with a
    single currency (CT-01; DEC-0105).

    A Price is an **affine level**: subtracting two Prices of the same instrument
    yields a :class:`PriceDelta`, the vector companion. Its unit-kind is the
    dimensional ``price-delta(instrument)``; the level-vs-delta distinction is
    carried by the type, and by the ``class`` discriminator in identity content.
    """

    value: int
    instrument: Instrument
    scale: int

    @property
    def unit_kind(self) -> UnitKind:
        """The dimensional unit-kind ``price-delta(instrument)`` (CT-01; DEC-0154)."""
        return UnitKind.PRICE_DELTA

    @classmethod
    def try_create(cls, value: object, instrument: object, scale: object) -> Result[Price]:
        """Validate and build a :class:`Price`, returning value-or-refusal."""
        int_value = _as_plain_int(value)
        if int_value is None:
            return _invalid(
                "value",
                "a price is an exact scaled integer; a binary float on the money path "
                "is refused (FM-1) — a float re-enters only through Price.from_float",
                given=repr(value),
            )
        anchor = _require_instrument(instrument)
        if anchor is None:
            return _invalid(
                "instrument",
                "a price is a ratio quoted for an instrument; a valid Instrument is required",
                given=repr(instrument),
            )
        int_scale = _as_scale(scale)
        if int_scale is None:
            return _invalid(
                "scale",
                "scale is a non-negative integer count of decimal places",
                given=repr(scale),
            )
        return Ok(cls(value=int_value, instrument=anchor, scale=int_scale))

    @classmethod
    def from_float(
        cls, value: object, *, instrument: object, scale: object, rounding: object
    ) -> Result[Price]:
        """The named float→Price conversion boundary (CT-01; DEC-0105)."""
        scaled = _coerce_float_to_scaled_int(value, scale, rounding)
        if isinstance(scaled, TypedRefusal):
            return scaled
        return cls.try_create(scaled, instrument, scale)

    def subtract(self, other: object) -> Result[PriceDelta]:
        """Subtract another :class:`Price` of the same instrument.

        Price subtraction is closed and delta-typed: the result is a first-class
        :class:`PriceDelta`, distinct from Price (CT-01; DEC-0131).
        """
        if not isinstance(other, Price):
            return _invalid("other", "a price subtracts only another Price", given=repr(other))
        if other.instrument != self.instrument:
            return _invalid(
                "instrument",
                "prices of different instruments do not subtract",
                left=repr(self.instrument),
                right=repr(other.instrument),
            )
        left, right, scale = _promote(self.value, self.scale, other.value, other.scale)
        return Ok(PriceDelta(value=left - right, instrument=self.instrument, scale=scale))

    def as_fraction(self) -> Fraction:
        """The exact rational magnitude ``value / 10**scale``."""
        return Fraction(self.value, 10**self.scale)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this price (DEC-0158)."""
        magnitude = self.as_fraction()
        return {
            "class": "price",
            "unit_kind": UnitKind.PRICE_DELTA.value,
            "instrument": _instrument_content(self.instrument),
            "num": magnitude.numerator,
            "den": magnitude.denominator,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class PriceDelta:
    """A first-class price difference, distinct from :class:`Price` (CT-01;
    DEC-0131).

    The vector companion to the affine Price: the closed result of price
    subtraction, and the type in which an instrument-scoped pip or point is
    expressed. Converting a delta to a pip count or to money needs an
    instrument-metadata input (a pip size or a :class:`ValueFactor`); an absent
    one is an ``unavailable dependency`` refusal, never a silent conversion.
    """

    value: int
    instrument: Instrument
    scale: int

    @property
    def unit_kind(self) -> UnitKind:
        """The dimensional unit-kind ``price-delta(instrument)`` (CT-01; DEC-0154)."""
        return UnitKind.PRICE_DELTA

    @classmethod
    def try_create(cls, value: object, instrument: object, scale: object) -> Result[PriceDelta]:
        """Validate and build a :class:`PriceDelta`, returning value-or-refusal."""
        int_value = _as_plain_int(value)
        if int_value is None:
            return _invalid(
                "value",
                "a price delta is an exact scaled integer; a binary float is refused (FM-1)",
                given=repr(value),
            )
        anchor = _require_instrument(instrument)
        if anchor is None:
            return _invalid(
                "instrument",
                "a price delta is instrument-scoped; a valid Instrument is required",
                given=repr(instrument),
            )
        int_scale = _as_scale(scale)
        if int_scale is None:
            return _invalid(
                "scale",
                "scale is a non-negative integer count of decimal places",
                given=repr(scale),
            )
        return Ok(cls(value=int_value, instrument=anchor, scale=int_scale))

    def add(self, other: object) -> Result[PriceDelta]:
        """Add another :class:`PriceDelta` of the same instrument, promoting scales."""
        return self._combine(other, subtract=False)

    def subtract(self, other: object) -> Result[PriceDelta]:
        """Subtract another :class:`PriceDelta` of the same instrument."""
        return self._combine(other, subtract=True)

    def _combine(self, other: object, *, subtract: bool) -> Result[PriceDelta]:
        if not isinstance(other, PriceDelta):
            return _invalid("other", "an operand must be a PriceDelta value", given=repr(other))
        if other.instrument != self.instrument:
            return _invalid(
                "instrument",
                "price deltas of different instruments do not combine",
                left=repr(self.instrument),
                right=repr(other.instrument),
            )
        left, right, scale = _promote(self.value, self.scale, other.value, other.scale)
        combined = left - right if subtract else left + right
        return Ok(PriceDelta(value=combined, instrument=self.instrument, scale=scale))

    def in_pips(self, pip: object) -> Result[ExactRational]:
        """Express this delta as a dimensionless multiple of the instrument pip.

        The pip (or point) size is a :class:`PriceDelta` drawn from a CT-03
        instrument-metadata record — **never hardcoded**. An absent pip is an
        ``unavailable dependency`` refusal (CT-01; DEC-0131, DEC-0154).
        """
        if pip is None:
            return _unavailable(
                "pip",
                "the instrument pip/point comes from a CT-03 instrument-metadata record; "
                "none was supplied",
            )
        if not isinstance(pip, PriceDelta):
            return _invalid(
                "pip", "a pip size is a PriceDelta from instrument metadata", given=repr(pip)
            )
        if pip.instrument != self.instrument:
            return _invalid(
                "pip",
                "the pip size belongs to a different instrument",
                left=repr(self.instrument),
                right=repr(pip.instrument),
            )
        if pip.value == 0:
            return _invalid("pip", "a pip size must be non-zero")
        ratio = self.as_fraction() / pip.as_fraction()
        return ExactRational.try_create(
            ratio.numerator, ratio.denominator, UnitKind.DIMENSIONLESS_RATIO
        )

    def to_money(self, value_factor: object, quantity: object, *, scale: object) -> Result[Money]:
        """Convert this delta to a monetary value via an instrument value-factor.

        ``value_factor`` is money per price-delta per quantity — the tick, point,
        or contract value from a CT-03/venue instrument-metadata record. An absent
        value-factor is an ``unavailable dependency`` refusal, never a silent
        conversion (CT-01; DEC-0154). The result must be exactly representable at
        the requested ``scale``; an inexact result is refused rather than silently
        rounded — a rounding money-path boundary is stated elsewhere (FM-4).
        """
        if value_factor is None:
            return _unavailable(
                "value_factor",
                "the instrument value-factor comes from a CT-03/venue instrument-metadata "
                "record; none was supplied",
            )
        if not isinstance(value_factor, ValueFactor):
            return _invalid(
                "value_factor",
                "a value-factor is a ValueFactor from instrument metadata",
                given=repr(value_factor),
            )
        if value_factor.instrument != self.instrument:
            return _invalid(
                "value_factor",
                "the value-factor belongs to a different instrument",
                left=repr(self.instrument),
                right=repr(value_factor.instrument),
            )
        if not isinstance(quantity, Quantity):
            return _invalid("quantity", "quantity must be a Quantity value", given=repr(quantity))
        int_scale = _as_scale(scale)
        if int_scale is None:
            return _invalid(
                "scale",
                "scale is a non-negative integer count of decimal places",
                given=repr(scale),
            )
        amount = self.as_fraction() * value_factor.as_fraction() * quantity.as_fraction()
        scaled = amount * (10**int_scale)
        if scaled.denominator != 1:
            return _invalid(
                "scale",
                "the money value is not exactly representable at this scale; cross a named "
                "rounding boundary instead of rounding silently",
                amount=str(amount),
            )
        return Money.try_create(scaled.numerator, value_factor.currency, int_scale)

    def as_fraction(self) -> Fraction:
        """The exact rational magnitude ``value / 10**scale``."""
        return Fraction(self.value, 10**self.scale)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this delta (DEC-0158).

        The ``class`` discriminator is ``price-delta`` — distinct from ``price`` —
        so a delta and a level of equal magnitude never share a fingerprint.
        """
        magnitude = self.as_fraction()
        return {
            "class": "price-delta",
            "unit_kind": UnitKind.PRICE_DELTA.value,
            "instrument": _instrument_content(self.instrument),
            "num": magnitude.numerator,
            "den": magnitude.denominator,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class Quantity:
    """An exact count in an opaque unit: a scaled integer (CT-01; DEC-0105).

    ``unit`` (lot, share, coin, contract) is an opaque tag, stored verbatim and
    never parsed. The unit-kind is fixed at ``quantity(unit)``.
    """

    value: int
    unit: str
    scale: int

    @property
    def unit_kind(self) -> UnitKind:
        """The fixed unit-kind ``quantity(unit)`` (CT-01; DEC-0154)."""
        return UnitKind.QUANTITY

    @classmethod
    def try_create(cls, value: object, unit: object, scale: object) -> Result[Quantity]:
        """Validate and build a :class:`Quantity`, returning value-or-refusal."""
        int_value = _as_plain_int(value)
        if int_value is None:
            return _invalid(
                "value",
                "a quantity is an exact scaled integer; a binary float on the money path "
                "is refused (FM-1) — a float re-enters only through Quantity.from_float",
                given=repr(value),
            )
        token = _clean_tag(unit)
        if token is None:
            return _invalid(
                "unit",
                "a unit is a non-empty opaque tag (lot, share, coin, contract), never parsed",
                given=repr(unit),
            )
        int_scale = _as_scale(scale)
        if int_scale is None:
            return _invalid(
                "scale",
                "scale is a non-negative integer count of decimal places",
                given=repr(scale),
            )
        return Ok(cls(value=int_value, unit=token, scale=int_scale))

    @classmethod
    def from_float(
        cls, value: object, *, unit: object, scale: object, rounding: object
    ) -> Result[Quantity]:
        """The named float→Quantity conversion boundary (CT-01; DEC-0105)."""
        scaled = _coerce_float_to_scaled_int(value, scale, rounding)
        if isinstance(scaled, TypedRefusal):
            return scaled
        return cls.try_create(scaled, unit, scale)

    def add(self, other: object) -> Result[Quantity]:
        """Add another :class:`Quantity` of the same unit, promoting scales."""
        return self._combine(other, subtract=False)

    def subtract(self, other: object) -> Result[Quantity]:
        """Subtract another :class:`Quantity` of the same unit, promoting scales."""
        return self._combine(other, subtract=True)

    def _combine(self, other: object, *, subtract: bool) -> Result[Quantity]:
        if not isinstance(other, Quantity):
            return _invalid("other", "an operand must be a Quantity value", given=repr(other))
        if other.unit != self.unit:
            return _invalid(
                "unit",
                "quantities of different units do not combine without a named conversion",
                left=self.unit,
                right=other.unit,
            )
        left, right, scale = _promote(self.value, self.scale, other.value, other.scale)
        combined = left - right if subtract else left + right
        return Ok(Quantity(value=combined, unit=self.unit, scale=scale))

    def as_fraction(self) -> Fraction:
        """The exact rational magnitude ``value / 10**scale``."""
        return Fraction(self.value, 10**self.scale)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this quantity (DEC-0158)."""
        magnitude = self.as_fraction()
        return {
            "class": "quantity",
            "unit_kind": UnitKind.QUANTITY.value,
            "unit": self.unit,
            "num": magnitude.numerator,
            "den": magnitude.denominator,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ExactRational:
    """A numerator/denominator pair carrying a declared :class:`UnitKind` (CT-01;
    DEC-0131, DEC-0154).

    The exact idiom for every non-integer parameter — ratios, multiples,
    tolerances, r-multiples, rates — so binary floats never appear in parameters
    or identity. Stored **reduced to lowest terms**, denominator strictly
    positive, sign on the numerator, via :meth:`try_create`. A null unit-kind is a
    typed refusal, never a default.
    """

    numerator: int
    denominator: int
    unit_kind: UnitKind

    @classmethod
    def try_create(
        cls, numerator: object, denominator: object, unit_kind: object
    ) -> Result[ExactRational]:
        """Validate, reduce, and build an :class:`ExactRational`.

        Refuses a binary-float numerator or denominator (FM-1), a zero
        denominator, and — as ``invalid input`` — a **null** unit-kind (never a
        default) or one outside the closed vocabulary.
        """
        int_numerator = _as_plain_int(numerator)
        if int_numerator is None:
            return _invalid(
                "numerator",
                "an exact rational takes integer parts; a binary float is refused (FM-1)",
                given=repr(numerator),
            )
        int_denominator = _as_plain_int(denominator)
        if int_denominator is None:
            return _invalid(
                "denominator",
                "an exact rational takes integer parts; a binary float is refused (FM-1)",
                given=repr(denominator),
            )
        if int_denominator == 0:
            return _invalid("denominator", "the denominator must be non-zero")
        if unit_kind is None:
            return _invalid(
                "unit_kind", "a null unit-kind is a typed refusal, never a default (DEC-0154)"
            )
        kind = _coerce_unit_kind(unit_kind)
        if kind is None:
            return _invalid(
                "unit_kind",
                "not a member of the closed unit-kind vocabulary",
                given=repr(unit_kind),
                allowed=[member.value for member in UnitKind],
            )
        reduced = Fraction(int_numerator, int_denominator)
        return Ok(cls(numerator=reduced.numerator, denominator=reduced.denominator, unit_kind=kind))

    def as_fraction(self) -> Fraction:
        """The exact rational magnitude ``numerator / denominator``."""
        return Fraction(self.numerator, self.denominator)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this rational (DEC-0158)."""
        magnitude = self.as_fraction()
        return {
            "class": "exact-rational",
            "unit_kind": self.unit_kind.value,
            "num": magnitude.numerator,
            "den": magnitude.denominator,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ValueFactor:
    """``value-factor(instrument, currency)`` — money per price-delta per quantity
    (CT-01; DEC-0154).

    The tick, point, or contract value: an exact rational sourced only from a
    venue instrument-metadata record, tagged with its instrument and its money
    currency. Stored reduced to lowest terms; its unit-kind is fixed at
    ``value-factor(instrument, currency)``.
    """

    numerator: int
    denominator: int
    instrument: Instrument
    currency: str

    @property
    def unit_kind(self) -> UnitKind:
        """The fixed unit-kind ``value-factor(instrument, currency)`` (DEC-0154)."""
        return UnitKind.VALUE_FACTOR

    @classmethod
    def try_create(
        cls, numerator: object, denominator: object, instrument: object, currency: object
    ) -> Result[ValueFactor]:
        """Validate, reduce, and build a :class:`ValueFactor`."""
        int_numerator = _as_plain_int(numerator)
        if int_numerator is None:
            return _invalid(
                "numerator",
                "a value-factor takes integer parts; a binary float is refused (FM-1)",
                given=repr(numerator),
            )
        int_denominator = _as_plain_int(denominator)
        if int_denominator is None:
            return _invalid(
                "denominator",
                "a value-factor takes integer parts; a binary float is refused (FM-1)",
                given=repr(denominator),
            )
        if int_denominator == 0:
            return _invalid("denominator", "the denominator must be non-zero")
        anchor = _require_instrument(instrument)
        if anchor is None:
            return _invalid(
                "instrument",
                "a value-factor is instrument-scoped; a valid Instrument is required",
                given=repr(instrument),
            )
        token = _clean_tag(currency)
        if token is None:
            return _invalid(
                "currency",
                "a value-factor names its money currency as a non-empty opaque tag",
                given=repr(currency),
            )
        reduced = Fraction(int_numerator, int_denominator)
        return Ok(
            cls(
                numerator=reduced.numerator,
                denominator=reduced.denominator,
                instrument=anchor,
                currency=token,
            )
        )

    def as_fraction(self) -> Fraction:
        """The exact rational magnitude ``numerator / denominator``."""
        return Fraction(self.numerator, self.denominator)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this value-factor."""
        magnitude = self.as_fraction()
        return {
            "class": "value-factor",
            "unit_kind": UnitKind.VALUE_FACTOR.value,
            "instrument": _instrument_content(self.instrument),
            "currency": self.currency,
            "num": magnitude.numerator,
            "den": magnitude.denominator,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
