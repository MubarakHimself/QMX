"""MUST NOT FLAG: real code that takes its inputs from the caller.

Nothing here is constructed: every value arrives through a parameter, and the
seams are named for what they are rather than for the double a test would pass.
"""

from __future__ import annotations


class VenueAdapter:
    def __init__(self, clock: object, transport: object) -> None:
        self._clock = clock
        self._transport = transport

    def submit(self, order: object) -> object:
        return self._transport
