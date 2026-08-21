"""MUST FLAG: time.perf_counter_ns() reads the system clock."""

import time


def tick():
    return time.perf_counter_ns()
