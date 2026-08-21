"""MUST NOT FLAG: money-path values built from exact scaled integers."""

from qmf.core.exact import Money, Price, Quantity


def order(instrument: object) -> tuple[object, object, object]:
    price = Price.try_create(108925, instrument, 5)
    quantity = Quantity.try_create(100, "lot", 2)
    balance = Money.try_create(1_000_00, "USD", 2)
    return price, quantity, balance
