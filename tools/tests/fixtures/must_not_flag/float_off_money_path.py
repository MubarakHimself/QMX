"""MUST NOT FLAG: floats used off the money path (timing, analytics).

A binary float is only a violation when it reaches a money-path value. Wall-clock
timing and ratio analytics that never touch Money/Price/Quantity are fine.
"""

import time


def measure() -> float:
    start = time.perf_counter()
    total = 0.0
    for i in range(100):
        total += i * 1.5
    return time.perf_counter() - start + total
