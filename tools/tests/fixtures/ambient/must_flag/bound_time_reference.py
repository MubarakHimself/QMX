"""MUST FLAG: a clock reader laundered through a bound reference, then called.

Stashing ``time.time`` in a local does not launder the clock read: the bound name
resolves to the banned callable and the later call is flagged.
"""

import time


def elapsed() -> float:
    f = time.time
    return f()
