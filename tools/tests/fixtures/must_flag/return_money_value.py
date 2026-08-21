"""MUST FLAG: a float is returned from a function annotated to yield Money."""

from qmf.core.exact import Money


def realized_pnl(entry: int, exit_: int) -> Money:
    return (exit_ - entry) * 0.0001  # a float P&L on the money path
