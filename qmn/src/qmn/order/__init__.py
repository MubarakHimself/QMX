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

Story 24.7: amend atomicity gates dynamic protection to the single-sided
breakeven ratchet (or refuse-before-origination per Book policy); originated
risk-non-increasing ``amend_protection`` is never suppressed by
``amend_min_improvement`` and is journaled before dispatch; ``close_partial``
and close-then-replace stay unsupported; the five CT-19 kinds remain closed
(QMX-F063).

Story 24.9: duplicate fills dedup by venue-native deal/execution identity
(TN-24b); node-close vs venue-terminal races resolve as named
``rejected-by-venue (superseded-by-terminal-subject)`` with CT-29 venue
authority, never UNKNOWN; absent/terminal subjects resolve without submission
(TN-24j).
"""

from __future__ import annotations

from qmn.order.amend import (
    AMEND_JOURNAL_KIND,
    CT19_CLOSED_KINDS,
    AmendAtomicity,
    AmendJournalRecord,
    AmendSequencePlan,
    BookDynamicProtectionPolicy,
    DynamicProtectionOrigin,
    admit_risk_non_increasing_amend_protection,
    ct19_kinds_are_closed,
    enforce_closed_ct19_vocabulary,
    gate_amend_protection,
    is_breakeven_ratchet_amendment,
    is_single_sided_amendment,
    journal_amend_before_dispatch,
    refuse_close_partial,
    refuse_close_then_replace,
    refuse_invented_amend_sequence,
    resolve_amend_atomicity,
)
from qmn.order.fills import (
    DATA_QUALITY_EVENT_TYPE,
    DUPLICATE_FILL_ALARM_CLASS,
    AccountFillStore,
    DurableFill,
    FillIngestDisposition,
    FillIngestResult,
)
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
    OrderPathTerminalResolution,
    compound_all_rejected_acceptance_blocked,
)
from qmn.order.protection import (
    ENTRY_RELATIVE_FORM,
    require_venue_resident_protective_stop,
    resolved_protective_stop_form,
)
from qmn.order.terminal import (
    CLOSING_AUTHORITY_VENUE,
    CT29_VENUE_INITIATED_CLOSE,
    CT29_VENUE_LIQUIDATION,
    SUPERSEDED_BY_TERMINAL_SUBJECT,
    Ct29VenueCloseReason,
    TerminalSubjectDisposition,
    resolve_node_close_against_subject,
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
    "AMEND_JOURNAL_KIND",
    "CLOSING_AUTHORITY_VENUE",
    "COMMAND_ORDINAL_RECORD_CLASS",
    "CT19_CLOSED_KINDS",
    "CT29_VENUE_INITIATED_CLOSE",
    "CT29_VENUE_LIQUIDATION",
    "DATA_QUALITY_EVENT_TYPE",
    "DUPLICATE_FILL_ALARM_CLASS",
    "ENTRY_RELATIVE_FORM",
    "FTR02_COMPOUND_BLOCKED",
    "JOURNAL_SEQUENCE_RECORD_CLASS",
    "OPERATOR_PRINCIPAL",
    "PACER_DOOR",
    "SUPERSEDED_BY_TERMINAL_SUBJECT",
    "UNDELIVERABLE_ALARM_CLASS",
    "VENUE_CLIENT_ID_PREFIX",
    "AccountFillStore",
    "AdmissionClass",
    "AmendAtomicity",
    "AmendJournalRecord",
    "AmendSequencePlan",
    "BookDynamicProtectionPolicy",
    "CommandIdentityBinder",
    "CommandOrdinalHighWater",
    "CommandOrdinalStore",
    "CommandStreamUnknownBoundary",
    "ConnectionCommandPacer",
    "Ct29VenueCloseReason",
    "DurableFill",
    "DynamicProtectionOrigin",
    "FillIngestDisposition",
    "FillIngestResult",
    "HeldProtectionAct",
    "HoldDisposition",
    "JournalSequenceCursor",
    "OrderPath",
    "OrderPathSubmission",
    "OrderPathTerminalResolution",
    "PacerAdmission",
    "ProtectionIntentExtent",
    "ReadbackClarity",
    "ResolveDecision",
    "ResolvePath",
    "TerminalSubjectDisposition",
    "UndeliverableProtectionIntent",
    "UnknownStreamRegistry",
    "WireHandoff",
    "admission_class_for",
    "admit_risk_non_increasing_amend_protection",
    "compound_all_rejected_acceptance_blocked",
    "ct19_kinds_are_closed",
    "decide_resolve_path",
    "enforce_closed_ct19_vocabulary",
    "gate_amend_protection",
    "is_breakeven_ratchet_amendment",
    "is_single_sided_amendment",
    "journal_amend_before_dispatch",
    "local_queue_bound_refusal",
    "mint_venue_client_id",
    "refuse_close_partial",
    "refuse_close_then_replace",
    "refuse_invented_amend_sequence",
    "require_venue_resident_protective_stop",
    "resolve_amend_atomicity",
    "resolve_node_close_against_subject",
    "resolved_protective_stop_form",
    "unknown_never_rejection",
]
