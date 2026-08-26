"""Named AD-22 / AD-7 price conversion for provider payloads (B-11, CT-01).

Provider-native floats/decimals never enter evidence unconverted. Exact scaled
integers already at the source scale pass through; floats cross
:meth:`Price.from_float` with a declared rounding mode and target scale.
"""

from __future__ import annotations

from typing import Final

from qmf.core.exact import Price, RoundingMode
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.observation import ForeignMoney

from qmb._refuse import invalid

__all__ = [
    "CONVERSION_BOUNDARY",
    "CONVERSION_ROUNDING",
    "conversion_identity",
    "fingerprint_conversion",
    "provider_price_to_exact",
]

CONVERSION_BOUNDARY: Final[str] = "qmb.data.convert.provider_price_to_exact"
CONVERSION_ROUNDING: Final[RoundingMode] = RoundingMode.HALF_EVEN


def provider_price_to_exact(
    value: object,
    *,
    instrument: object,
    scale: object,
    rounding: object = CONVERSION_ROUNDING,
) -> Result[ForeignMoney]:
    """Convert a provider price into exact scaled-integer :class:`ForeignMoney`.

    * Exact ``int`` at ``scale`` — pass through (already money-path legal).
    * ``float`` / numeric text — named AD-22 crossing via :meth:`Price.from_float`.
    * Anything else — ``invalid input``.
    """
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0:
        return invalid(
            "scale",
            "provider price scale is a non-negative int digit count",
            given=repr(scale),
            boundary=CONVERSION_BOUNDARY,
        )
    if isinstance(value, bool):
        return invalid(
            "value",
            "a provider price is an exact scaled int or a float crossing the "
            "named AD-22 boundary — never a bool",
            given=repr(value),
            boundary=CONVERSION_BOUNDARY,
        )
    if isinstance(value, int):
        built = ForeignMoney.try_create(value, scale)
        if is_refusal(built):
            return built
        return Ok(built.value)
    if isinstance(value, float):
        priced = Price.from_float(
            value,
            instrument=instrument,
            scale=scale,
            rounding=rounding,
        )
        if is_refusal(priced):
            return priced
        built = ForeignMoney.try_create(priced.value.value, priced.value.scale)
        if is_refusal(built):
            return built
        return Ok(built.value)
    return invalid(
        "value",
        "provider-native floats/decimals must cross provider_price_to_exact; "
        "unconverted non-integer prices are refused (CT-01/AR-15)",
        given=repr(value),
        boundary=CONVERSION_BOUNDARY,
    )


def conversion_identity() -> dict[str, object]:
    """Identity-bearing conversion fields. Package SemVer is omitted."""
    return {
        "boundary": CONVERSION_BOUNDARY,
        "rounding": CONVERSION_ROUNDING.value,
    }


def fingerprint_conversion() -> Result[Fingerprint]:
    """Fingerprint of the named conversion boundary."""
    return fingerprint(conversion_identity())
