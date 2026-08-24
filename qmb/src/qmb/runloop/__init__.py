"""Event-slice run loop, frontier clock port, and in-loop warm-up (B-2).

Time advances only through an injected frontier clock that IS qmf-core's AD-8
``Clock`` protocol. The loop is never forked: backtest, replay, and live differ
only by which clock and adapters the run-config binds (DEC-0169).
"""

from __future__ import annotations

from typing import Final

from qmf.core.chrono import Clock

from qmb.runloop.frontier import (
    CLOCK_DOES_NOT_CHOOSE_WORLD,
    FrontierClock,
    NextEmitStream,
    StreamNextEmit,
    advance_frontier,
    as_wall_replay_instant,
    min_next_emit,
    read_frontier,
    script_replay_clock,
)

__all__ = [
    "CLOCK_DOES_NOT_CHOOSE_WORLD",
    "LOOP_KIND",
    "SUBPHASES",
    "FrontierClock",
    "NextEmitStream",
    "StreamNextEmit",
    "advance_frontier",
    "as_wall_replay_instant",
    "frontier_clock_name",
    "loop_identity",
    "min_next_emit",
    "read_frontier",
    "script_replay_clock",
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
        "clock_chooses_world": False,
        "clock_does_not_choose_world": CLOCK_DOES_NOT_CHOOSE_WORLD,
    }
