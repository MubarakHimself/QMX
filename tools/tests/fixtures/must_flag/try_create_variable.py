"""MUST FLAG: a float flows through a local variable into ``Price.try_create``."""

from qmf.core.exact import Price


def quote(instrument: object) -> object:
    raw_price = 1.08925  # a broker quote read as a binary float
    return Price.try_create(raw_price, instrument, 5)
