"""MUST FLAG: an aliased time module does not hide the clock read."""

import time as wallclock


def tick():
    return wallclock.monotonic()
