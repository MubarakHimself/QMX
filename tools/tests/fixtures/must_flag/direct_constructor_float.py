"""MUST FLAG: a binary float literal reaches a money-path value constructor."""

from qmf.core.exact import Money


def account_balance() -> Money:
    # A float literal on the money path is banned (FR-001; CT-01, DEC-0105).
    return Money(1234.56, "USD", 2)
