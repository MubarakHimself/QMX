"""MUST NOT FLAG: a float crosses the named boundary declaring its rounding mode.

This is the sanctioned crossing: ``from_float`` with an explicit rounding mode
(CT-01; DEC-0105).
"""

from qmf.core.exact import Money, RoundingMode


def to_money(raw: float) -> object:
    return Money.from_float(raw, currency="USD", scale=2, rounding=RoundingMode.HALF_UP)
