"""qmn — the QMX trading node (code name only).

One uv-installable application-layer distribution (``import qmn``), built ON QMF
exactly as QMB and QML are. Never a roster package, never a framework, never an
engine, and never an operator CLI (DEC-0186, DEC-0211, DEC-0220).

``qmn.venue`` is the one sanctioned importer and wirer of ``qmf-venue`` (DEC-0241);
every other ``qmn`` module receives :class:`~qmn.venue.VenueClientPort` and the
CT-19/CT-20 shapes re-exported there. ``qmn.loop`` drives QMB ``run_slice``
unforked behind the recording accumulator (DEC-0190). ``qmn.order`` wires
command identity, protection priority, submission timing, and the exact
``(VenueId, account)`` UNKNOWN stream boundary (DEC-0224, QMX-F062).
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
    CommandStreamUnknownBoundary,
    ConnectionCommandPacer,
    JournalSequenceCursor,
    OrderPath,
    UnknownStreamRegistry,
    compound_all_rejected_acceptance_blocked,
    decide_resolve_path,
    require_venue_resident_protective_stop,
)
from qmn.venue import (
    ASYNC_EXEMPTION_MODULE,
    CONFORMANCE_CASES,
    FTR04_DISPOSITION,
    PORT_CONTRACT_CAPABILITY_KEYS,
    TRANSPORT_LOCUS,
    ConformanceCase,
    ConformanceDouble,
    LiveCTraderClient,
    ParentAsyncExemptionDisposition,
    PositionModel,
    ReceiveFrontier,
    ReconnectGapRecovery,
    ReplayAdapter,
    VenueClientKind,
    VenueClientPort,
    VenueClientSelection,
    WireKind,
    compare_port_contract_shapes,
    compound_command_acceptance_blocked,
    resolve_transport_locus,
    run_port_contract_suite,
    select_venue_client,
)

__all__ = [
    "ASYNC_EXEMPTION_MODULE",
    "CONFORMANCE_CASES",
    "DATA_QUALITY_EVENT_TYPE",
    "FTR02_COMPOUND_BLOCKED",
    "FTR04_DISPOSITION",
    "PINNED_SUBPHASES",
    "PORT_CONTRACT_CAPABILITY_KEYS",
    "TRANSPORT_LOCUS",
    "AdmissionClass",
    "CommandIdentityBinder",
    "CommandOrdinalStore",
    "CommandStreamLoop",
    "CommandStreamUnknownBoundary",
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
    "ReceiveFrontier",
    "ReconnectGapRecovery",
    "RecordingAccumulator",
    "ReplayAdapter",
    "SliceDriveResult",
    "UnknownStreamRegistry",
    "VenueClientKind",
    "VenueClientPort",
    "VenueClientSelection",
    "WireKind",
    "__version__",
    "classify_observation",
    "clear_first_writer_registry",
    "compare_port_contract_shapes",
    "compound_all_rejected_acceptance_blocked",
    "compound_command_acceptance_blocked",
    "decide_resolve_path",
    "entry_side_refused",
    "first_writer_for",
    "forming_bars_actionable",
    "forming_bars_visible",
    "protection_enactable",
    "require_venue_resident_protective_stop",
    "resolve_transport_locus",
    "run_port_contract_suite",
    "select_venue_client",
    "stream_key",
]

# Display-only provenance — never part of fp1 identity (DEC-0186).
__version__ = "0.1.0"
