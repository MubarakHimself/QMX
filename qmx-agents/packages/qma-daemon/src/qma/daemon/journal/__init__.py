"""Single append-only journal, journal_seq, clock and fold law (AD-6; FR-Q23–FR-Q25).

Durable journal appends go through
:class:`~qma.daemon.persistence.PersistenceSubstrate` (FR-Q22 sole-writer
boundary). This package owns global monotonic ``journal_seq`` allocation, the
closed store list, evidence announcements, durable-clock stamps, v1 fold
contracts, and fold ordering by announcement ``journal_seq``.
"""

from __future__ import annotations

from qma.daemon.journal.authoritative import (
    DAEMON_JOURNAL_STREAM,
    AnnouncementOutcome,
    AuthoritativeJournal,
    JournalAppendReceipt,
    JournalEventRecord,
    ScopeProjectionCursor,
)
from qma.daemon.journal.clock import (
    DaemonClock,
    DurableTimestamps,
    DurationPolicy,
    WallClockPolicy,
    refuse_host_local_time,
    refuse_worker_evidence_timestamp,
)
from qma.daemon.journal.fold_contracts import (
    FILTERED_PROJECTIONS_NOT_FOLDS,
    V1_FOLD_IDS,
    FoldContract,
    FoldContractRegistry,
    v1_fold_contract,
)
from qma.daemon.journal.ordering import (
    AnnouncedRecord,
    journal_seq_sort_key,
    order_by_announcement_journal_seq,
)
from qma.daemon.journal.stores import (
    ANNOUNCEMENT_EVENT_BY_STORE,
    ANNOUNCEMENT_REQUIRED_STORES,
    CLOSED_INDEPENDENT_STORES,
    CLOSED_PROJECTIONS,
    CLOSED_STORE_NAMES,
    DEFINITION_STORE_MEMBERS,
    TELEMETRY_STORE,
    FoldMetadata,
    StoreClass,
    StoreDeclaration,
    StoreRegistry,
    announce_event_for_store,
    is_announcement_required,
    is_closed_store,
)

__all__ = [
    "ANNOUNCEMENT_EVENT_BY_STORE",
    "ANNOUNCEMENT_REQUIRED_STORES",
    "CLOSED_INDEPENDENT_STORES",
    "CLOSED_PROJECTIONS",
    "CLOSED_STORE_NAMES",
    "DAEMON_JOURNAL_STREAM",
    "DEFINITION_STORE_MEMBERS",
    "FILTERED_PROJECTIONS_NOT_FOLDS",
    "TELEMETRY_STORE",
    "V1_FOLD_IDS",
    "AnnouncedRecord",
    "AnnouncementOutcome",
    "AuthoritativeJournal",
    "DaemonClock",
    "DurableTimestamps",
    "DurationPolicy",
    "FoldContract",
    "FoldContractRegistry",
    "FoldMetadata",
    "JournalAppendReceipt",
    "JournalEventRecord",
    "ScopeProjectionCursor",
    "StoreClass",
    "StoreDeclaration",
    "StoreRegistry",
    "WallClockPolicy",
    "announce_event_for_store",
    "is_announcement_required",
    "is_closed_store",
    "journal_seq_sort_key",
    "order_by_announcement_journal_seq",
    "refuse_host_local_time",
    "refuse_worker_evidence_timestamp",
    "v1_fold_contract",
]
