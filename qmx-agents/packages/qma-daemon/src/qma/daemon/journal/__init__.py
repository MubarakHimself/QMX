"""Single append-only journal, journal_seq, announcement law (AD-6; FR-Q23, FR-Q24).

Durable journal appends go through
:class:`~qma.daemon.persistence.PersistenceSubstrate` (FR-Q22 sole-writer
boundary). This package owns global monotonic ``journal_seq`` allocation, the
closed store list, evidence announcements, and fold ordering by announcement
``journal_seq``.
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
    "TELEMETRY_STORE",
    "AnnouncedRecord",
    "AnnouncementOutcome",
    "AuthoritativeJournal",
    "FoldMetadata",
    "JournalAppendReceipt",
    "JournalEventRecord",
    "ScopeProjectionCursor",
    "StoreClass",
    "StoreDeclaration",
    "StoreRegistry",
    "announce_event_for_store",
    "is_announcement_required",
    "is_closed_store",
    "journal_seq_sort_key",
    "order_by_announcement_journal_seq",
]
