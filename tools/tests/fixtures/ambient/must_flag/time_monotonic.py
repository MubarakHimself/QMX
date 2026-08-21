"""MUST FLAG: time.monotonic() reads the system clock (AC example)."""

import time


def measure(work):
    start = time.monotonic()
    work()
    return time.monotonic() - start
