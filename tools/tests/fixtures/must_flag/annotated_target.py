"""MUST FLAG: a float is bound to a money-path-typed target."""

from qmf.core.exact import Money


def settle() -> None:
    pnl: Money = 42.5  # a float assigned where a Money value is declared
    record(pnl)


def record(value: object) -> None:
    del value
