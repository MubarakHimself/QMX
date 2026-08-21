"""MUST FLAG: a float-annotated parameter reaches a money-path value."""

from qmf.core.exact import Money


def deposit(amount: float, currency: str) -> object:
    return Money.try_create(amount, currency, 2)
