"""Event-slice run loop, frontier clock port, and in-loop warm-up (B-2).

Time advances only through an injected frontier clock that IS qmf-core's AD-8
``Clock`` protocol. The loop is never forked: backtest, replay, and live differ
only by which clock and adapters the run-config binds (DEC-0169). Per slice the
six sub-phases in :data:`SUBPHASES` run in pinned identity-bearing order.
"""

from __future__ import annotations

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
from qmb.runloop.loop import (
    LOOP_KIND,
    SAME_SLICE_NEW_INTENT_FILL,
    STREAM_ROLE_DATA_ONLY,
    STREAM_ROLE_TRADING,
    STREAM_SET_KEY,
    SUBPHASES,
    DeclaredStream,
    EventSlice,
    LoopOutcome,
    RestingIntent,
    SilentSliceHandler,
    SliceHandler,
    SliceObservation,
    SliceOutcome,
    StreamSet,
    SubphaseTrace,
    fingerprint_loop,
    frontier_clock_name,
    loop_identity,
    run,
    run_slice,
    stream_set_from_config,
)

__all__ = [
    "CLOCK_DOES_NOT_CHOOSE_WORLD",
    "LOOP_KIND",
    "SAME_SLICE_NEW_INTENT_FILL",
    "STREAM_ROLE_DATA_ONLY",
    "STREAM_ROLE_TRADING",
    "STREAM_SET_KEY",
    "SUBPHASES",
    "DeclaredStream",
    "EventSlice",
    "FrontierClock",
    "LoopOutcome",
    "NextEmitStream",
    "RestingIntent",
    "SilentSliceHandler",
    "SliceHandler",
    "SliceObservation",
    "SliceOutcome",
    "StreamNextEmit",
    "StreamSet",
    "SubphaseTrace",
    "advance_frontier",
    "as_wall_replay_instant",
    "fingerprint_loop",
    "frontier_clock_name",
    "loop_identity",
    "min_next_emit",
    "read_frontier",
    "run",
    "run_slice",
    "script_replay_clock",
    "stream_set_from_config",
]
