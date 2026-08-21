"""MUST FLAG: ``Decimal(px)`` of a binary float does not clear the taint.

``Decimal(str(x))`` reparses decimal text and is exact, but ``Decimal(px)`` on a
binary float captures the float's representation error verbatim — the money value
still carries the binary error, with no declared rounding mode (CT-01; DEC-0105).
"""

from decimal import Decimal

from qmf.core.exact import Money


def to_money(px: float) -> object:
    return Money.try_create(int(Decimal(px) * 100), "USD", 2)
