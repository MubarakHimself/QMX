"""``qmn.loop`` — unforked QMB ``run_slice`` behind the recording accumulator (TN-5).

Story 24.4: one push-to-pull accumulator is the single first writer of
VenueClientPort observations for one ``(VenueId, account)`` stream. Record
through governed intake, journal under the venue WriterId, then foldable. On
frontier close the node calls QMB ``run_slice`` unforked through its six pinned
sub-phases; the durable interpretation cursor commits only after the slice
completes. Forming bars are never visible or actionable.
"""

from __future__ import annotations

from qmn.loop.accumulator import (
    RecordingAccumulator,
    clear_first_writer_registry,
    first_writer_for,
    stream_key,
)
from qmn.loop.driver import (
    PINNED_SUBPHASES,
    CommandStreamLoop,
    InterpretationCursor,
    SliceDriveResult,
    forming_bars_actionable,
    forming_bars_visible,
)
from qmn.loop.kinds import (
    DATA_QUALITY_EVENT_TYPE,
    CycleBand,
    InboundObservation,
    ObservationClass,
    classify_observation,
    entry_side_refused,
    protection_enactable,
)

__all__ = [
    "DATA_QUALITY_EVENT_TYPE",
    "PINNED_SUBPHASES",
    "CommandStreamLoop",
    "CycleBand",
    "InboundObservation",
    "InterpretationCursor",
    "ObservationClass",
    "RecordingAccumulator",
    "SliceDriveResult",
    "classify_observation",
    "clear_first_writer_registry",
    "entry_side_refused",
    "first_writer_for",
    "forming_bars_actionable",
    "forming_bars_visible",
    "protection_enactable",
    "stream_key",
]
