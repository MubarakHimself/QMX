"""MUST FLAG: a from-imported clock reader called by bare name."""

from time import monotonic


def tick():
    return monotonic()
