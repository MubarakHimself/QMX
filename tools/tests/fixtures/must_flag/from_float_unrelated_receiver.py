"""MUST FLAG: ``from_float`` on an unrelated receiver launders nothing.

The sanctioned crossing is ``from_float`` on a CT-01 value type. ``from_float``
on any other receiver is an ordinary call that returns a plain float; declaring a
``rounding`` keyword on it does not sanctify it, so the taint flows straight
through to the money-path value (CT-01; DEC-0105).
"""

from qmf.core.exact import Money


class Helper:
    @staticmethod
    def from_float(value: float, *, rounding: str) -> float:
        return value


def to_money(px: float) -> object:
    laundered = Helper.from_float(px, rounding="half-up")
    return Money.try_create(int(laundered * 100), "USD", 2)
