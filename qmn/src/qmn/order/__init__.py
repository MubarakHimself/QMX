"""``qmn.order`` — command identity, protection priority, submission timing (TN-6).

Story 24.5: after a Book-authorized intent clears the protection gate the node
allocates a lifetime-monotone command ordinal distinct from the CT-13 journal
sequence, recovers the ordinal high-water before opening the sequencer, and
persists the command-fingerprint-to-venue-id binding before wire handoff.
``place_order`` without a proven venue-resident protective stop is refused.
Protective reserve capacity is unavailable to entry work; the submission
deadline begins only at wire handoff; a local queue-bound breach is a door
refusal (never UNKNOWN); no retry after handoff. Compound all-rejected child
outcomes stay blocked on FTR-02.

Story 24.6: UNKNOWN is enforced at the exact ``(VenueId, account)`` command-stream
boundary (QMX-F062) — whole-stream block including protection, standing
protection intents with reserved-extent fallback, and two-path resolve.
"""

from __future__ import annotations

from qmn.order.identity import (
    VENUE_CLIENT_ID_PREFIX,
    CommandIdentityBinder,
    mint_venue_client_id,
)
from qmn.order.ordinal import (
    COMMAND_ORDINAL_RECORD_CLASS,
    JOURNAL_SEQUENCE_RECORD_CLASS,
    CommandOrdinalHighWater,
    CommandOrdinalStore,
    JournalSequenceCursor,
)
from qmn.order.pacer import (
    PACER_DOOR,
    AdmissionClass,
    ConnectionCommandPacer,
    PacerAdmission,
    WireHandoff,
    admission_class_for,
    local_queue_bound_refusal,
)
from qmn.order.path import (
    FTR02_COMPOUND_BLOCKED,
    OrderPath,
    OrderPathSubmission,
    compound_all_rejected_acceptance_blocked,
)
from qmn.order.protection import (
    ENTRY_RELATIVE_FORM,
    require_venue_resident_protective_stop,
    resolved_protective_stop_form,
)
from qmn.order.unknown import (
    OPERATOR_PRINCIPAL,
    UNDELIVERABLE_ALARM_CLASS,
    CommandStreamUnknownBoundary,
    HeldProtectionAct,
    HoldDisposition,
    ProtectionIntentExtent,
    ReadbackClarity,
    ResolveDecision,
    ResolvePath,
    UndeliverableProtectionIntent,
    UnknownStreamRegistry,
    decide_resolve_path,
    unknown_never_rejection,
)

__all__ = [
    "COMMAND_ORDINAL_RECORD_CLASS",
    "ENTRY_RELATIVE_FORM",
    "FTR02_COMPOUND_BLOCKED",
    "JOURNAL_SEQUENCE_RECORD_CLASS",
    "OPERATOR_PRINCIPAL",
    "PACER_DOOR",
    "UNDELIVERABLE_ALARM_CLASS",
    "VENUE_CLIENT_ID_PREFIX",
    "AdmissionClass",
    "CommandIdentityBinder",
    "CommandOrdinalHighWater",
    "CommandOrdinalStore",
    "CommandStreamUnknownBoundary",
    "ConnectionCommandPacer",
    "HeldProtectionAct",
    "HoldDisposition",
    "JournalSequenceCursor",
    "OrderPath",
    "OrderPathSubmission",
    "PacerAdmission",
    "ProtectionIntentExtent",
    "ReadbackClarity",
    "ResolveDecision",
    "ResolvePath",
    "UndeliverableProtectionIntent",
    "UnknownStreamRegistry",
    "WireHandoff",
    "admission_class_for",
    "compound_all_rejected_acceptance_blocked",
    "decide_resolve_path",
    "local_queue_bound_refusal",
    "mint_venue_client_id",
    "require_venue_resident_protective_stop",
    "resolved_protective_stop_form",
    "unknown_never_rejection",
]
