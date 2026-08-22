"""MUST NOT FLAG: neutral defaults. A None sentinel, a boolean switch, a zero, an
empty string and an empty container are identity values, not fabricated data."""

from __future__ import annotations


def build(
    price: int | None = None,
    quantity: int = 0,
    symbol: str = "",
    bars: tuple[int, ...] = (),
    verbose: bool = False,
) -> object:
    return (price, quantity, symbol, bars, verbose)
