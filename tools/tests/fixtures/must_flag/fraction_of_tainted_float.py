"""MUST FLAG: ``Fraction(px)`` of a binary float does not clear the taint.

``Fraction(px)`` on a binary float is its exact dyadic expansion — the float's
representation error preserved to the last bit — so the value reaching Money is
still a money-path float (CT-01; DEC-0105). Only ``Fraction(str(x))`` reparses
decimal text.
"""

from fractions import Fraction

from qmf.core.exact import Money


def to_money(px: float) -> object:
    scaled = Fraction(px) * 100
    return Money.try_create(scaled.numerator, "USD", 2)
