"""Research-lane bot with zero qml imports.

Conformance is the ticket into governed evidence and Book seats, never tunnel
entry (DEC-0171, DEC-0178). This module must keep importing nothing from qml.
"""

from __future__ import annotations


class PlainResearchBot:
    """A host can drive this callback without the authoring library present."""

    def on_instant(self, instant: object) -> tuple[()]:
        """Emit no intents. The evaluation instant is host-supplied."""
        del instant
        return ()
