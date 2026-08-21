"""MUST FLAG: a float crosses the from_float boundary without a rounding mode.

The named conversion boundary is only sanctioned when it declares its rounding
mode explicitly (CT-01; DEC-0105). This crossing declares none.
"""

from qmf.core.exact import Money


def to_money(raw: float) -> object:
    return Money.from_float(raw, currency="USD", scale=2)
