"""MUST FLAG: from_float with ``rounding=None`` declares no rounding mode."""

from qmf.core.exact import Price


def to_price(raw: float, instrument: object) -> object:
    # rounding=None is the absence of a declared mode, not a declaration.
    return Price.from_float(raw, instrument=instrument, scale=5, rounding=None)
