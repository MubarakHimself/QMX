"""MUST NOT FLAG: defaults that reference a named constant, and real data bound
to a name that does not claim to be fabricated."""

from __future__ import annotations

DEFAULT_PRICE_PRECISION = 5
PRICE_LADDER = [1, 2, 3, 4]


def quote(price: int = DEFAULT_PRICE_PRECISION) -> int:
    return price
