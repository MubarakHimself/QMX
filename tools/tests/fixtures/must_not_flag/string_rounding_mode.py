"""MUST NOT FLAG: the rounding mode may be declared as a string token."""

from qmf.core.exact import Quantity


def to_quantity(raw: float) -> object:
    return Quantity.from_float(raw, unit="lot", scale=2, rounding="half-up")
