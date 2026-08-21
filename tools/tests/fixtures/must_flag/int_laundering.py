"""MUST FLAG: laundering a float through ``int()`` does not clear the taint.

``int(...)`` truncates — an undeclared silent rounding — so the value reaching
Money is still a money-path float (CT-01; DEC-0105).
"""

from qmf.core.exact import Money


def to_cents(dollars: float) -> object:
    return Money.try_create(int(dollars * 100), "USD", 2)
