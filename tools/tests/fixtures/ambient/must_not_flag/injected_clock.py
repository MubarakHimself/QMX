"""MUST NOT FLAG: time read through the injected Clock protocol seam (CT-02 / AR-16).

Usage of the injected ``Clock`` reads a value, not the ``datetime``/``time``/``random``
modules, so it never matches a banned shape.
"""

from __future__ import annotations


def observe(clock):
    instant = clock.wall_now()
    reading = clock.monotonic_now()
    return instant, reading


class Sequencer:
    def __init__(self, clock) -> None:
        self._clock = clock

    def mint(self):
        return self._clock.wall_now()
