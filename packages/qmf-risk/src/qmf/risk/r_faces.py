"""Story 10.2 — R as three typed faces and the full-loss-price law (COMP-QMF-RISK).

R is **one relationship with three typed faces, not a number** (AD-40; DEC-0076,
DEC-0154):

* ``original_risk_distance`` — a :class:`~qmf.core.PriceDelta` (``price-delta(instrument)``),
  entry to the position's declared original full-loss price;
* ``original_risk_amount`` — a :class:`~qmf.core.Money` (``money(numeraire)``), the
  cost of a full-loss fill at the admitted quantity;
* ``r_multiple`` — a dimensionless exact :class:`~qmf.core.ExactRational`
  (``r-multiple``), realized result ÷ ``original_risk_amount``, where **−1 is a full
  original loss and 0 is breakeven**.

Both money-bearing faces are **frozen at admission** and never re-based — not by a
stop move, a protection amendment, or an intraday budget re-derivation. Frozenness
is structural here: :class:`RFaces` is an immutable frozen dataclass minted once at
admission and never mutated by this module, so a later ratchet moves the resting
stop while the faces stand, and −1R keeps meaning a full original loss (DEC-0148,
DEC-0154). This module never re-derives a face from live book state — computing the
ladder against a live budget is the node's (DEC-0142); it only mints the frozen
faces from supplied exact values and crosses Money↔R over a **named rate**.

The full-loss-price law (CT-23; DEC-0154): an admitted entry must resolve to a
declared full-loss price — **no price, no ``original_risk_distance``, no admission,
an ``invalid input`` refusal** — because a strategy that deliberately runs with no
planned loss point cannot trade in QMX. V1 admits **no scale-in**: adding to an open
position is a ``policy rejection``. The ``original_risk_amount`` is derived from the
risk distance through an instrument **value-factor** sourced only from venue
instrument-metadata (an absent one is an ``unavailable dependency`` refusal, never a
silent conversion); V1 never sizes by margin (DEC-0154).

Every Money↔R crossing **names a rate** — ``r_unit_price`` (``rate(money-per-r)``);
an implicit crossing refuses, and **only ``r_multiple`` averages** across instruments
and accounts (DEC-0154). Imports only ``qmf-core`` and sibling ``qmf.risk`` modules;
nothing imports ``qmf.risk`` (default-deny, L30/DEC-0120). Ratified
``defined-unwired`` surface — no wiring is authorized here (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from typing import Final, cast

from qmf.core import (
    ExactRational,
    Money,
    Price,
    PriceDelta,
    Quantity,
    Result,
    TypedRefusal,
    UnitKind,
    ValueFactor,
    is_refusal,
)
from qmf.core import (
    Ok as _Ok,
)
from qmf.risk._common import coerce_enum, invalid, policy
from qmf.risk.numeraire import V1_NUMERAIRE

__all__ = [
    "BREAKEVEN",
    "FULL_ORIGINAL_LOSS",
    "Direction",
    "RFaces",
    "admit_entry_r_faces",
    "average_r_multiple",
    "check_no_scale_in",
    "derive_original_risk_distance",
    "money_to_r",
    "r_to_money",
]

# This module's own contract format version stamped into fp1 identity content; its
# meaning never mutates — an incompatible change mints the next version (L15).
_R_FACES_FORMAT_VERSION = 1

# The documented maximum scale a crossing accepts, mirroring CT-01's MAX_SCALE
# (DEC-0105): it keeps ``10**scale`` a cheap integer rather than a caller-supplied
# denial-of-service foot-gun. Set generously above any real instrument precision.
_MAX_SCALE: Final[int] = 72

# The two anchor r-multiples the law names: -1 is a full original loss, 0 is
# breakeven (AD-40; DEC-0154). Exact rationals, fp1-clean, float-free.
FULL_ORIGINAL_LOSS: Final[ExactRational] = ExactRational(
    numerator=-1, denominator=1, unit_kind=UnitKind.R_MULTIPLE
)
BREAKEVEN: Final[ExactRational] = ExactRational(
    numerator=0, denominator=1, unit_kind=UnitKind.R_MULTIPLE
)


class Direction(StrEnum):
    """A position's direction (AD-40; DEC-0154).

    The side the position opens on. It fixes which side of entry a genuine
    full-loss price must sit: a ``LONG``'s full-loss price is strictly below entry
    and a ``SHORT``'s strictly above, so a declared price on the wrong side is not a
    planned loss point and is refused.
    """

    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class RFaces:
    """The two money-bearing R faces, frozen at admission (AD-40; DEC-0154).

    Carries ``original_risk_distance`` (:class:`~qmf.core.PriceDelta`, the positive
    loss-direction distance from entry to the declared full-loss price) and
    ``original_risk_amount`` (:class:`~qmf.core.Money` in the numeraire, the cost of a
    full-loss fill at the admitted quantity). Both are **frozen** — this is an
    immutable value minted once at admission; the third face, ``r_multiple``, is the
    *realized* outcome and is derived on demand by :meth:`r_multiple_of`, never stored,
    so a stop move or a protection amendment can never re-base R.
    """

    original_risk_distance: PriceDelta
    original_risk_amount: Money

    @classmethod
    def try_create(
        cls, original_risk_distance: object, original_risk_amount: object
    ) -> Result[RFaces]:
        """Validate and build the frozen money-bearing R faces, value-or-refusal.

        The distance must be a strictly-positive :class:`~qmf.core.PriceDelta` (a
        zero or negative risk distance is not a loss point); the amount must be a
        strictly-positive :class:`~qmf.core.Money` in the numeraire (a full-loss cost
        is a positive amount, and V1 money is the USD numeraire). Returned never
        raised.
        """
        if not isinstance(original_risk_distance, PriceDelta):
            return invalid(
                "original_risk_distance",
                "original_risk_distance is a PriceDelta(instrument) from entry to the "
                "declared full-loss price",
                given=repr(original_risk_distance),
            )
        if original_risk_distance.as_fraction() <= 0:
            return invalid(
                "original_risk_distance",
                "the risk distance is the positive loss-direction magnitude; a zero or "
                "negative distance is not a planned loss point",
                given=str(original_risk_distance.as_fraction()),
            )
        if not isinstance(original_risk_amount, Money):
            return invalid(
                "original_risk_amount",
                "original_risk_amount is a Money(numeraire) — the cost of a full-loss fill",
                given=repr(original_risk_amount),
            )
        if original_risk_amount.currency != V1_NUMERAIRE:
            return policy(
                "original_risk_amount",
                "original_risk_amount is denominated in the numeraire; a non-numeraire "
                "amount needs a ratified rate source and is refused (no silent conversion)",
                given=original_risk_amount.currency,
                numeraire=V1_NUMERAIRE,
            )
        if original_risk_amount.as_fraction() <= 0:
            return invalid(
                "original_risk_amount",
                "original_risk_amount is the positive cost of a full-loss fill; a zero or "
                "negative amount is not a risk amount",
                given=str(original_risk_amount.as_fraction()),
            )
        return _Ok(
            cls(
                original_risk_distance=original_risk_distance,
                original_risk_amount=original_risk_amount,
            )
        )

    def r_multiple_of(self, realized_result: object) -> Result[ExactRational]:
        """Derive the realized ``r_multiple`` face — realized result ÷ frozen amount.

        ``realized_result`` is a signed :class:`~qmf.core.Money` in the numeraire; the
        result is a dimensionless exact ``r-multiple`` where **−1 is a full original
        loss** (realized = −``original_risk_amount``) and **0 is breakeven**. A
        different currency is an ``invalid input`` refusal — an implicit cross-currency
        crossing is never silent. Exact by construction (rational division).
        """
        if not isinstance(realized_result, Money):
            return invalid(
                "realized_result",
                "a realized result is a Money(numeraire) value",
                given=repr(realized_result),
            )
        if realized_result.currency != self.original_risk_amount.currency:
            return invalid(
                "realized_result",
                "an r-multiple never crosses currencies implicitly; the realized result "
                "must share the original_risk_amount's currency",
                realized=realized_result.currency,
                amount=self.original_risk_amount.currency,
            )
        ratio = realized_result.as_fraction() / self.original_risk_amount.as_fraction()
        return ExactRational.try_create(ratio.numerator, ratio.denominator, UnitKind.R_MULTIPLE)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the frozen R faces."""
        return {
            "class": "r-faces",
            "original_risk_distance": self.original_risk_distance.fp1_identity(),
            "original_risk_amount": self.original_risk_amount.fp1_identity(),
            "format_version": _R_FACES_FORMAT_VERSION,
        }


def derive_original_risk_distance(
    entry_price: object, full_loss_price: object, direction: object
) -> Result[PriceDelta]:
    """Derive ``original_risk_distance`` from entry to the declared full-loss price.

    The full-loss price is mandatory: a missing (``None``) or non-:class:`~qmf.core.Price`
    price is an ``invalid input`` refusal — **no price, no original_risk_distance, no
    admission** (CT-23; DEC-0154). Both prices must be the same instrument (else
    ``invalid input`` via CT-01 subtraction). The price must sit on the loss side of
    entry for the direction — strictly below for a ``LONG``, strictly above for a
    ``SHORT`` — else it is not a planned loss point and is refused. Returns the
    positive loss-direction :class:`~qmf.core.PriceDelta`.
    """
    if not isinstance(entry_price, Price):
        return invalid(
            "entry_price", "the entry price is a Price(instrument)", given=repr(entry_price)
        )
    if full_loss_price is None:
        return invalid(
            "full_loss_price",
            "an admitted entry must declare a full-loss price; no price, no "
            "original_risk_distance, no admission — a strategy with no planned loss point "
            "cannot trade in QMX",
        )
    if not isinstance(full_loss_price, Price):
        return invalid(
            "full_loss_price",
            "the declared full-loss price is a Price(instrument)",
            given=repr(full_loss_price),
        )
    resolved_direction = coerce_enum(Direction, direction)
    if resolved_direction is None:
        return invalid(
            "direction",
            "a position declares its direction",
            given=repr(direction),
            allowed=[member.value for member in Direction],
        )
    if resolved_direction is Direction.LONG:
        distance = entry_price.subtract(full_loss_price)
    else:
        distance = full_loss_price.subtract(entry_price)
    if is_refusal(distance):
        return distance
    if distance.value.as_fraction() <= 0:
        return invalid(
            "full_loss_price",
            "the declared full-loss price is not on the loss side of entry for this "
            "direction (a long's full-loss is below entry, a short's above); a price at "
            "or beyond entry is not a planned loss point",
            direction=resolved_direction.value,
        )
    return distance


def admit_entry_r_faces(
    entry_price: object,
    full_loss_price: object,
    direction: object,
    admitted_quantity: object,
    value_factor: object,
    *,
    money_scale: object,
) -> Result[RFaces]:
    """Mint the frozen R faces at admission (AD-40; DEC-0154).

    Derives ``original_risk_distance`` under the full-loss-price law
    (:func:`derive_original_risk_distance`), then ``original_risk_amount`` — the cost
    of a full-loss fill at ``admitted_quantity`` — through the instrument
    ``value_factor``. The value-factor comes only from a venue instrument-metadata
    record; an **absent one is an ``unavailable dependency`` refusal**, never a silent
    conversion, and V1 never sizes by margin (margin enters no rung). A non-numeraire
    result is a ``policy rejection``. Returns the frozen :class:`RFaces`.
    """
    distance = derive_original_risk_distance(entry_price, full_loss_price, direction)
    if is_refusal(distance):
        return distance
    if not isinstance(admitted_quantity, Quantity):
        return invalid(
            "admitted_quantity",
            "the admitted quantity is a Quantity(unit)",
            given=repr(admitted_quantity),
        )
    if value_factor is not None and not isinstance(value_factor, ValueFactor):
        return invalid(
            "value_factor",
            "a value-factor is a ValueFactor(instrument, currency) from venue "
            "instrument-metadata; V1 never sizes by margin",
            given=repr(value_factor),
        )
    # CT-01's PriceDelta.to_money refuses an absent value-factor as an
    # ``unavailable dependency`` — never a silent conversion (DEC-0154).
    amount = distance.value.to_money(value_factor, admitted_quantity, scale=money_scale)
    if is_refusal(amount):
        return amount
    return RFaces.try_create(distance.value, amount.value)


def check_no_scale_in(has_open_position: object) -> Result[None]:
    """Refuse a scale-in: V1 admits none (CT-23; DEC-0154).

    Adding to an already-open virtual position is a ``policy rejection`` — V1 opens a
    fresh position or none. ``has_open_position`` is a bool; a non-bool is ``invalid
    input``. Returns ``Ok(None)`` only when no open position exists on the seat.
    """
    if not isinstance(has_open_position, bool):
        return invalid(
            "has_open_position",
            "the scale-in guard takes a bool naming whether the seat holds an open position",
            given=repr(has_open_position),
        )
    if has_open_position:
        return policy(
            "has_open_position",
            "V1 admits no scale-in; adding to an open position is refused",
        )
    return _Ok(None)


# --- the Money <-> R crossing over a named rate (DEC-0154) --------------------


def _require_r_multiple(field: str, value: object) -> Result[ExactRational]:
    """Resolve ``value`` as an ``r-multiple`` :class:`~qmf.core.ExactRational`."""
    if not isinstance(value, ExactRational) or value.unit_kind is not UnitKind.R_MULTIPLE:
        return invalid(
            field,
            "an r-multiple is a dimensionless ExactRational of unit-kind r-multiple",
            given=repr(value),
        )
    return _Ok(value)


def _require_rate(value: object) -> Result[ExactRational]:
    """Resolve ``r_unit_price`` as a non-zero ``rate(money-per-r)`` rational.

    A Money↔R crossing must **name a rate**; a value that is not a ``rate``-kind
    ExactRational is an implicit crossing and is refused (``invalid input``).
    """
    if not isinstance(value, ExactRational) or value.unit_kind is not UnitKind.RATE:
        return invalid(
            "r_unit_price",
            "a Money<->R crossing names a rate; r_unit_price is a rate(money-per-r) "
            "ExactRational, and an implicit crossing (no named rate) is refused",
            given=repr(value),
        )
    if value.numerator == 0:
        return invalid("r_unit_price", "the r_unit_price rate must be non-zero")
    return _Ok(value)


def _resolve_scale(value: object) -> int | TypedRefusal:
    """Resolve a money target scale in ``[0, _MAX_SCALE]``, or a refusal."""
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            "scale", "a money scale is an integer count of decimal places", given=repr(value)
        )
    if value < 0 or value > _MAX_SCALE:
        return invalid(
            "scale",
            f"a money scale is an integer count of decimal places in [0, {_MAX_SCALE}]",
            given=repr(value),
            max_scale=_MAX_SCALE,
        )
    return value


def r_to_money(requested_r: object, r_unit_price: object, *, scale: object) -> Result[Money]:
    """Cross R→Money over a named rate: ``position_risk_amount = requested_r × r_unit_price``.

    ``requested_r`` is an ``r-multiple`` (dimensionless) and ``r_unit_price`` a named
    ``rate(money-per-r)`` (AD-40; DEC-0154) — the crossing must name the rate, so an
    ``r_unit_price`` that is not a rate is refused. The product is money in the
    numeraire; if it is not exactly representable at ``scale`` the crossing is refused
    (cross a named rounding boundary rather than round silently). Returns the
    numeraire :class:`~qmf.core.Money`.
    """
    r = _require_r_multiple("requested_r", requested_r)
    if is_refusal(r):
        return r
    rate = _require_rate(r_unit_price)
    if is_refusal(rate):
        return rate
    int_scale = _resolve_scale(scale)
    if isinstance(int_scale, TypedRefusal):
        return int_scale
    product = r.value.as_fraction() * rate.value.as_fraction()
    shifted = product * (10**int_scale)
    if shifted.denominator != 1:
        return invalid(
            "scale",
            "position_risk_amount is not exactly representable at this scale; cross a "
            "named rounding boundary rather than rounding silently",
            amount=str(product),
        )
    return Money.try_create(shifted.numerator, V1_NUMERAIRE, int_scale)


def money_to_r(amount: object, r_unit_price: object) -> Result[ExactRational]:
    """Cross Money→R over a named rate: ``r_multiple = amount ÷ r_unit_price``.

    ``amount`` is a numeraire :class:`~qmf.core.Money` and ``r_unit_price`` a named
    ``rate(money-per-r)``; the crossing must name the rate, and an implicit crossing
    refuses (AD-40; DEC-0154). The quotient is a dimensionless ``r-multiple``, exact
    by construction. Returns the ``r-multiple`` :class:`~qmf.core.ExactRational`.
    """
    if not isinstance(amount, Money):
        return invalid("amount", "a Money<->R crossing takes a Money amount", given=repr(amount))
    if amount.currency != V1_NUMERAIRE:
        return policy(
            "amount",
            "a Money<->R crossing is in the numeraire; a non-numeraire amount needs a "
            "ratified rate source and is refused (no silent conversion)",
            given=amount.currency,
            numeraire=V1_NUMERAIRE,
        )
    rate = _require_rate(r_unit_price)
    if is_refusal(rate):
        return rate
    quotient = amount.as_fraction() / rate.value.as_fraction()
    return ExactRational.try_create(quotient.numerator, quotient.denominator, UnitKind.R_MULTIPLE)


def average_r_multiple(values: object) -> Result[ExactRational]:
    """Average a sequence of ``r-multiple`` values (AD-40; DEC-0154).

    **Only ``r_multiple`` averages across instruments and accounts** — a money,
    price-delta, or any non-``r-multiple`` value in the sequence is an ``invalid
    input`` refusal, because averaging currency amounts across instruments would
    demand an unratified conversion. An empty sequence or a non-sequence is refused.
    The mean is exact (rational). Returns the ``r-multiple``
    :class:`~qmf.core.ExactRational`.
    """
    if isinstance(values, str) or not isinstance(values, Sequence):
        return invalid(
            "values",
            "only r-multiple averages; supply a sequence of r-multiple ExactRational values",
            given=repr(type(values).__name__),
        )
    items = cast("Sequence[object]", values)
    if len(items) == 0:
        return invalid("values", "an average is over at least one r-multiple value")
    total = Fraction(0)
    for item in items:
        if not isinstance(item, ExactRational) or item.unit_kind is not UnitKind.R_MULTIPLE:
            return invalid(
                "values",
                "only r-multiple averages across instruments and accounts; a money or "
                "price-delta value may not be averaged",
                given=repr(item),
            )
        total += item.as_fraction()
    mean = total / len(items)
    return ExactRational.try_create(mean.numerator, mean.denominator, UnitKind.R_MULTIPLE)
