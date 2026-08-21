"""MUST FLAG: ``datetime.now`` laundered through a bound reference, then called."""

from datetime import datetime


def stamp() -> datetime:
    n = datetime.now
    return n()
