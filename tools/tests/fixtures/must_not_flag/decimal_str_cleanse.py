"""MUST NOT FLAG: ``Decimal(str(...))`` is the exact cleanse, not a money float.

Once the value is an exact Decimal it is no longer a binary float, so scaling it
to an integer for Money is on the exact path (CT-01).
"""

from decimal import Decimal

from qmf.core.exact import Money


def to_money(raw: float) -> object:
    cents = int(Decimal(str(raw)) * 100)
    return Money.try_create(cents, "USD", 2)
