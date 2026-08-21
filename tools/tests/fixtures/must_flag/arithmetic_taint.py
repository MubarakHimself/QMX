"""MUST FLAG: float taint propagates through arithmetic onto the money path."""

from qmf.core.exact import Quantity


def sized_order(lots: int) -> object:
    slippage = 0.25  # a binary float
    adjusted = lots + slippage  # arithmetic keeps the taint
    return Quantity.try_create(adjusted, "lot", 2)
