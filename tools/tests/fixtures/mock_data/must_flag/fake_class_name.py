"""MUST FLAG: a Fake* adapter class shipped outside a test tree."""

from __future__ import annotations


class FakeVenueAdapter:
    def submit(self, order: object) -> None:
        return None
