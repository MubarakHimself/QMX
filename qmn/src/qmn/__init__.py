"""qmn — the QMX trading node (code name only).

One uv-installable application-layer distribution (``import qmn``), built ON QMF
exactly as QMB and QML are. Never a roster package, never a framework, never an
engine, and never an operator CLI (DEC-0186, DEC-0211, DEC-0220).

``qmn.venue`` is the one sanctioned importer and wirer of ``qmf-venue`` (DEC-0241);
every other ``qmn`` module receives :class:`~qmn.venue.VenueClientPort` and the
CT-19/CT-20 shapes re-exported there. ``qmn.loop`` drives QMB ``run_slice``
unforked behind the recording accumulator (DEC-0190). ``qmn.order`` wires
command identity, protection priority, and submission timing (DEC-0224).
Nothing imports ``qmn``.

``__version__`` is display-only SemVer provenance and never enters ``fp1``
(DEC-0186).
"""

from __future__ import annotations

from qmn.loop import (
    DATA_QUALITY_EVENT_TYPE,
    PINNED_SUBPHASES,
    CommandStreamLoop,
    CycleBand,
    InboundObservation,
    InterpretationCursor,
    ObservationClass,
    RecordingAccumulator,
    SliceDriveResult,
    classify_observation,
    clear_first_writer_registry,
    entry_side_refused,
    first_writer_for,
    forming_bars_actionable,
    forming_bars_visible,
    protection_enactable,
    stream_key,
)
from qmn.order import (
    FTR02_COMPOUND_BLOCKED,
    AdmissionClass,
    CommandIdentityBinder,
    CommandOrdinalStore,
    ConnectionCommandPacer,
    JournalSequenceCursor,
    OrderPath,
    compound_all_rejected_acceptance_blocked,
    require_venue_resident_protective_stop,
)
from qmn.venue import (
    ASYNC_EXEMPTION_MODULE,
    CONFORMANCE_CASES,
    FTR04_DISPOSITION,
    TRANSPORT_LOCUS,
    ConformanceCase,
    ConformanceDouble,
    LiveCTraderClient,
    ParentAsyncExemptionDisposition,
    PositionModel,
    VenueClientKind,
    VenueClientPort,
    VenueClientSelection,
    WireKind,
    compound_command_acceptance_blocked,
    resolve_transport_locus,
    select_venue_client,
)

__all__ = [
    "ASYNC_EXEMPTION_MODULE",
    "CONFORMANCE_CASES",
    "DATA_QUALITY_EVENT_TYPE",
    "FTR02_COMPOUND_BLOCKED",
    "FTR04_DISPOSITION",
    "PINNED_SUBPHASES",
    "TRANSPORT_LOCUS",
    "AdmissionClass",
    "CommandIdentityBinder",
    "CommandOrdinalStore",
    "CommandStreamLoop",
    "ConformanceCase",
    "ConformanceDouble",
    "ConnectionCommandPacer",
    "CycleBand",
    "InboundObservation",
    "InterpretationCursor",
    "JournalSequenceCursor",
    "LiveCTraderClient",
    "ObservationClass",
    "OrderPath",
    "ParentAsyncExemptionDisposition",
    "PositionModel",
    "RecordingAccumulator",
    "SliceDriveResult",
    "VenueClientKind",
    "VenueClientPort",
    "VenueClientSelection",
    "WireKind",
    "__version__",
    "classify_observation",
    "clear_first_writer_registry",
    "compound_all_rejected_acceptance_blocked",
    "compound_command_acceptance_blocked",
    "entry_side_refused",
    "first_writer_for",
    "forming_bars_actionable",
    "forming_bars_visible",
    "protection_enactable",
    "require_venue_resident_protective_stop",
    "resolve_transport_locus",
    "select_venue_client",
    "stream_key",
]

# Display-only provenance — never part of fp1 identity (DEC-0186).
__version__ = "0.1.0"
