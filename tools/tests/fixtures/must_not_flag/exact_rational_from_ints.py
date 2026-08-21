"""MUST NOT FLAG: exact parameters built from integer numerator/denominator."""

from qmf.core.exact import ExactRational, UnitKind


def half() -> object:
    return ExactRational.try_create(1, 2, UnitKind.DIMENSIONLESS_RATIO)
