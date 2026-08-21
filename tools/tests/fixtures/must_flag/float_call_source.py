"""MUST FLAG: a ``float(...)`` conversion feeds a money-path value."""

from qmf.core.exact import Quantity


def parse_size(raw: str) -> object:
    return Quantity.try_create(float(raw), "lot", 0)
