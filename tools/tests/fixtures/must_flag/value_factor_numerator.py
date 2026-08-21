"""MUST FLAG: a float numerator reaches the rational-backed ValueFactor."""

from qmf.core.exact import ValueFactor


def tick_value(instrument: object) -> object:
    return ValueFactor.try_create(10.0, 1, instrument, "USD")
