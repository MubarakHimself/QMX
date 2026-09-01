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
from qma.daemon.journal.ownership import (
    DURABLE_POSTURE_CLASSES,
    EIGHT_STORE_CLASSES,
    INVOCATION_ONLY_CLASSES,
    OwnershipRule,
    PersistenceClass,
    StoreOwnershipRegistry,
    default_ownership_table,
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
from qma.daemon.journal.variables import (
    REGISTRY_HOME,
    STORE_BACKUP_CADENCE_KEY,
    STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
    STORE_LIFECYCLE_KEYS,
    STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
    VARIABLE_SET_COMMAND,
    VARIABLE_SET_EVENT,
    GovernedVariableRegistry,
    VariableRow,
    VariableSetReceipt,
    builtin_qma_variable_rows,
    cite_store_lifecycle_key,
    has_variable_edit_kind,
    registry_key,
)

__all__ = [
    "ANNOUNCEMENT_EVENT_BY_STORE",
    "ANNOUNCEMENT_REQUIRED_STORES",
    "CLOSED_INDEPENDENT_STORES",
    "CLOSED_PROJECTIONS",
    "CLOSED_STORE_NAMES",
    "DAEMON_JOURNAL_STREAM",
    "DEFINITION_STORE_MEMBERS",
    "DURABLE_POSTURE_CLASSES",
    "EIGHT_STORE_CLASSES",
    "FILTERED_PROJECTIONS_NOT_FOLDS",
    "INVOCATION_ONLY_CLASSES",
    "REGISTRY_HOME",
    "STORE_BACKUP_CADENCE_KEY",
    "STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY",
    "STORE_LIFECYCLE_KEYS",
    "STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY",
    "TELEMETRY_STORE",
    "V1_FOLD_IDS",
    "VARIABLE_SET_COMMAND",
    "VARIABLE_SET_EVENT",
    "AnnouncedRecord",
    "AnnouncementOutcome",
    "AuthoritativeJournal",
    "DaemonClock",
    "DurableTimestamps",
    "DurationPolicy",
    "FoldContract",
    "FoldContractRegistry",
    "FoldMetadata",
    "GovernedVariableRegistry",
    "JournalAppendReceipt",
    "JournalEventRecord",
    "OwnershipRule",
    "PersistenceClass",
    "ScopeProjectionCursor",
    "StoreClass",
    "StoreDeclaration",
    "StoreOwnershipRegistry",
    "StoreRegistry",
    "VariableRow",
    "VariableSetReceipt",
    "WallClockPolicy",
    "announce_event_for_store",
    "builtin_qma_variable_rows",
    "cite_store_lifecycle_key",
    "default_ownership_table",
    "has_variable_edit_kind",
    "is_announcement_required",
    "is_closed_store",
    "journal_seq_sort_key",
    "order_by_announcement_journal_seq",
    "refuse_host_local_time",
    "refuse_worker_evidence_timestamp",
    "registry_key",
    "v1_fold_contract",
]
