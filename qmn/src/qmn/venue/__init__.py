"""``qmn.venue`` — the one sanctioned ``qmf-venue`` import and wirer boundary.

Every other ``qmn`` module receives :class:`VenueClientPort` and the CT-19/CT-20
shapes re-exported here; only this subpackage may import ``qmf.venue`` (DEC-0241,
DEC-0228). Story 24.1 lands the port, the FEAT-0023 conformance double, the
FTR-04 parent-disposition record, and the credential-free conformance suite.
Story 24.2 adds CT-18 verify-or-refuse at connection time (D008).
"""

from __future__ import annotations

# Re-export CT-19/CT-20 shapes so non-venue qmn modules never import qmf.venue.
from qmf.venue.commands import (
    Command,
    CommandKind,
    CommandObservation,
    SubmissionOutcome,
    SubmissionResult,
    UnknownTrigger,
)
from qmf.venue.connection import (
    ASYNC_CONFORMANCE_EXEMPTION,
    CTRADER_OPEN_API_PORT,
    ConnectionManager,
)
from qmf.venue.events import (
    ObservationKind,
    ReconciliationVerdict,
    SubjectResolution,
)
from qmf.venue.observation import REQUIRED_CONNECTION_CHECKS

from qmn.venue.conformance import (
    CONFORMANCE_CASES,
    ConformanceCase,
    ConformanceDouble,
    PositionModel,
    compound_command_acceptance_blocked,
    run_conformance_suite,
)
from qmn.venue.disposition import (
    ASYNC_EXEMPTION_MODULE,
    FTR04_DISPOSITION,
    TRANSPORT_LOCUS,
    ParentAsyncExemptionDisposition,
    resolve_transport_locus,
)
from qmn.venue.port import (
    VenueClientKind,
    VenueClientPort,
    VenueClientSelection,
    select_venue_client,
)
from qmn.venue.verify import (
    DATA_QUALITY_EVENT_TYPE,
    BindingRevalidationState,
    DataQualityJournalEvent,
    FieldDefectKind,
    MeasuredFactBundle,
    VenueFactVerification,
    VenueFactVerifier,
    conformance_measured_facts,
    ctrader_static_declaration,
)

__all__ = [
    "ASYNC_CONFORMANCE_EXEMPTION",
    "ASYNC_EXEMPTION_MODULE",
    "CONFORMANCE_CASES",
    "CTRADER_OPEN_API_PORT",
    "DATA_QUALITY_EVENT_TYPE",
    "FTR04_DISPOSITION",
    "REQUIRED_CONNECTION_CHECKS",
    "TRANSPORT_LOCUS",
    "BindingRevalidationState",
    "Command",
    "CommandKind",
    "CommandObservation",
    "ConformanceCase",
    "ConformanceDouble",
    "ConnectionManager",
    "DataQualityJournalEvent",
    "FieldDefectKind",
    "MeasuredFactBundle",
    "ObservationKind",
    "ParentAsyncExemptionDisposition",
    "PositionModel",
    "ReconciliationVerdict",
    "SubjectResolution",
    "SubmissionOutcome",
    "SubmissionResult",
    "UnknownTrigger",
    "VenueClientKind",
    "VenueClientPort",
    "VenueClientSelection",
    "VenueFactVerification",
    "VenueFactVerifier",
    "compound_command_acceptance_blocked",
    "conformance_measured_facts",
    "ctrader_static_declaration",
    "resolve_transport_locus",
    "run_conformance_suite",
    "select_venue_client",
]
