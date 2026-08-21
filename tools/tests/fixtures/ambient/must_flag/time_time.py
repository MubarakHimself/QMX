"""MUST FLAG: time.time() reads the system clock."""

import time


def now_seconds():
    return time.time()
