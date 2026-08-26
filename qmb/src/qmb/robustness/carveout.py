"""The bounded B-14 return-space float carve-out and its AD-41 identity (AC2, AC3).

A robustness procedure that computes a return-space statistic — mean log-return,
Sharpe, Calmar, and kin — leaves the exact-rational domain only for the statistic
itself. P&L and equity paths stay **exact scaled integers** (AD-7); a binary float
exists only transiently inside the statistic and re-enters an exact value through
ONE named ``ExactRational.from_float`` boundary under a fixed declared rounding
contract (:data:`RETURN_SPACE_STAT_ROUNDING` at :data:`RETURN_SPACE_STAT_SCALE`).
The raw float is never the stored value, so the tier-1 money-path float scanner
(NFR-02, FR-001) sees no binary float on the money path.

A float-valued measure the carve-out produces takes **label-derived identity**
(AD-41): its identity is the caller's label plus the reduced exact rational, never
the bit-identity of the float. Identical inputs therefore yield identical measure
identity (NFR-03) — two floats that round to the same scaled rational share one
identity by construction, and no float bits ever enter the fingerprint.

Any re-entry to the money path itself passes a named AD-22 conversion with a
declared rounding mode (:func:`reenter_money_path`) — a float becomes exact
:class:`Money` only there, never by construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from qmf.core.exact import ExactRational, Money, RoundingMode, UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid

__all__ = [
    "IDENTITY_IS_LABEL_DERIVED",
    "IDENTITY_USES_FLOAT_BITS",
    "MONEY_PATH_STAYS_EXACT_INTEGER",
    "RETURN_SPACE_MEASURE_CLASS",
    "RETURN_SPACE_MEASURE_FORMAT_VERSION",
    "RETURN_SPACE_STAT_ROUNDING",
    "RETURN_SPACE_STAT_SCALE",
    "ReturnSpaceMeasure",
    "carve_return_statistic",
    "carveout_identity",
    "reenter_money_path",
]

# The one fixed rounding contract every return-space statistic crosses back through.
# A float re-enters an exact value only here, at this scale and mode, so the stored
# value is a label-derived scaled rational and never a raw binary float (AC2, AD-7).
RETURN_SPACE_STAT_SCALE: Final[int] = 12
RETURN_SPACE_STAT_ROUNDING: Final[RoundingMode] = RoundingMode.HALF_EVEN

RETURN_SPACE_MEASURE_CLASS: Final[str] = "qmb-return-space-measure"
RETURN_SPACE_MEASURE_FORMAT_VERSION: Final[int] = 1

# Identity-bearing discipline flags (AC2, AC3). Money-path values stay exact
# integers; identity is label-derived and never the bit-identity of a float.
MONEY_PATH_STAYS_EXACT_INTEGER: Final[bool] = True
IDENTITY_IS_LABEL_DERIVED: Final[bool] = True
IDENTITY_USES_FLOAT_BITS: Final[bool] = False


@dataclass(frozen=True, slots=True)
class ReturnSpaceMeasure:
    """One float-valued return-space statistic with AD-41 label-derived identity (AC3).

    The magnitude is the reduced exact rational the carve-out produced; identity is
    the ``label`` plus that rational under the declared ``scale`` / ``rounding``
    contract. No binary float enters identity, so identical inputs fingerprint
    identically (NFR-03).
    """

    label: str
    unit_kind: str
    num: int
    den: int
    scale: int
    rounding: str

    @property
    def magnitude(self) -> Fraction:
        """The exact scaled-rational magnitude of the statistic."""
        return Fraction(self.num, self.den)

    def fp1_identity(self) -> dict[str, object]:
        """Label-derived identity content — never the bit-identity of the float (AD-41)."""
        return {
            "class": RETURN_SPACE_MEASURE_CLASS,
            "den": self.den,
            "format_version": RETURN_SPACE_MEASURE_FORMAT_VERSION,
            "label": self.label,
            "num": self.num,
            "rounding": self.rounding,
            "scale": self.scale,
            "unit_kind": self.unit_kind,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The qmf-core ``fp1`` over the label-derived identity content."""
        return fingerprint(self.fp1_identity())


def carve_return_statistic(
    label: object,
    value: object,
    *,
    unit_kind: UnitKind = UnitKind.DIMENSIONLESS_RATIO,
) -> Result[ReturnSpaceMeasure]:
    """Cross ONE float-domain return-space statistic to an exact label-derived measure (AC2, AC3).

    ``value`` is the transient float the statistic produced (a Sharpe, a Calmar, a
    mean log-return). It re-enters an exact value through the single named
    ``ExactRational.from_float`` boundary under the fixed rounding contract, and the
    returned :class:`ReturnSpaceMeasure` stores that reduced rational with the
    caller's ``label`` as its identity. A non-real or non-finite value is a typed
    refusal, never coerced to zero. P&L and equity never enter here — they stay
    exact scaled integers on the money path.
    """
    token = clean_token(label)
    if token is None:
        return invalid(
            "label",
            "a return-space measure carries a non-blank identity label (AD-41)",
            given=repr(label),
        )
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return invalid(
            "value",
            "a return-space statistic is a real-valued number crossing the carve-out; "
            "P&L and equity stay exact integers and never enter here as raw money",
            label=token,
            given=repr(type(value).__name__),
        )
    number = float(value)
    if not math.isfinite(number):
        return invalid(
            "value",
            "NaN and infinity cannot express a return-space statistic; never coerced to zero",
            label=token,
        )
    converted = ExactRational.from_float(
        number,
        unit_kind=unit_kind,
        scale=RETURN_SPACE_STAT_SCALE,
        rounding=RETURN_SPACE_STAT_ROUNDING,
    )
    if is_refusal(converted):
        return converted
    exact = converted.value
    return Ok(
        ReturnSpaceMeasure(
            label=token,
            unit_kind=exact.unit_kind.value,
            num=exact.numerator,
            den=exact.denominator,
            scale=RETURN_SPACE_STAT_SCALE,
            rounding=RETURN_SPACE_STAT_ROUNDING.value,
        )
    )


def reenter_money_path(
    value: object,
    *,
    currency: object,
    scale: object,
    rounding: object,
) -> Result[Money]:
    """The named AD-22 money re-entry: a float becomes exact Money only here (AC2).

    A return-space result re-enters the money path exclusively through this named
    conversion, which requires an explicitly declared ``rounding`` mode. A null
    rounding mode, or a non-real / non-finite value, is a typed refusal — a float
    never becomes :class:`Money` by construction.
    """
    if rounding is None:
        return invalid(
            "rounding",
            "re-entering the money path requires an explicitly declared rounding mode; "
            "a float never becomes Money without one (AD-22, CT-01)",
        )
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return invalid(
            "value",
            "the money re-entry boundary converts a real-valued return-space result; "
            "construct exact Money from integers with try_create",
            given=repr(type(value).__name__),
        )
    number = float(value)
    if not math.isfinite(number):
        return invalid(
            "value",
            "NaN and infinity cannot cross the money re-entry boundary",
        )
    return Money.from_float(number, currency=currency, scale=scale, rounding=rounding)


def carveout_identity() -> dict[str, object]:
    """Identity-bearing return-space-carve-out fields. Package SemVer is omitted."""
    return {
        "class": RETURN_SPACE_MEASURE_CLASS,
        "format_version": RETURN_SPACE_MEASURE_FORMAT_VERSION,
        "identity_is_label_derived": IDENTITY_IS_LABEL_DERIVED,
        "identity_uses_float_bits": IDENTITY_USES_FLOAT_BITS,
        "money_path_stays_exact_integer": MONEY_PATH_STAYS_EXACT_INTEGER,
        "stat_rounding": RETURN_SPACE_STAT_ROUNDING.value,
        "stat_scale": RETURN_SPACE_STAT_SCALE,
    }
