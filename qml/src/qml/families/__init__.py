"""Strategy-family keying token (QL-6).

A family is an opaque operator-minted id with no authority — the same AD-9
discipline as ``instrument_class``. Constraining stays the Book's job (DEC-0176).
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core.refusal import Ok, Result

from qml._refuse import clean_token, invalid

__all__ = ["StrategyFamilyId"]


@dataclass(frozen=True, slots=True)
class StrategyFamilyId:
    """Opaque family key. One per Bot definition; the token itself decides nothing."""

    value: str

    @classmethod
    def try_create(cls, value: object) -> Result[StrategyFamilyId]:
        """Validate and build a family id, value-or-refusal.

        The token is stored verbatim and never parsed. A blank or non-string is
        ``invalid input``.
        """
        token = clean_token(value)
        if token is None:
            return invalid(
                "value",
                "a strategy family is a non-empty opaque operator-minted token; it is a "
                "key never an authority",
                given=repr(value),
            )
        return Ok(cls(token))
