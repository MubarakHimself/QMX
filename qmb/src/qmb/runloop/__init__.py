"""Event-slice run loop, frontier clock port, and in-loop warm-up (B-2).

Time advances only through an injected frontier clock that IS qmf-core's AD-8
``Clock`` protocol. The loop is never forked: backtest, replay, and live differ
only by which clock and adapters the run-config binds (DEC-0169).
"""

from __future__ import annotations

from typing import Final

from qmf.core.chrono import Clock

__all__ = [
    "LOOP_KIND",
    "SUBPHASES",
    "frontier_clock_name",
    "loop_identity",
]

LOOP_KIND: Final[str] = "event-slice"
SUBPHASES: Final[tuple[str, ...]] = (
    "frontier-advance",
    "scheduled-position-events",
    "resting-orders",
    "closed-data-indicators-structure",
    "strategy-callbacks",
    "new-intents-rest",
)


def frontier_clock_name() -> str:
    """Qualified name of the injected frontier clock protocol (AD-8)."""
    return f"{Clock.__module__}.{Clock.__qualname__}"


def loop_identity() -> dict[str, object]:
    """Identity-bearing loop fields. Package SemVer is omitted."""
    return {
        "loop_kind": LOOP_KIND,
        "frontier_clock": frontier_clock_name(),
        "subphases": SUBPHASES,
    }
