"""qmf.data — evidence rooms, splits, journals, and backups.

Roster package of the QMF V1 uv workspace. Story 3.1 lands the dependency-free
persistence seam ``COMP-QMF-DATA-STORE`` (:mod:`qmf.data.store`): the CT-11
append-store, CT-13 journal, CT-09 registry room, and CT-26 store-to-backup
boundaries, over the four ratified engines (Parquet, DuckDB, SQLite, JSONL), keyed
on fp1 fingerprints and instantiated per world. Story 3.2 lands the CT-10
source-observation boundary on top of that seam: the bitemporal fact law
(:class:`SourceObservation` with verbatim :class:`ForeignTimestamp` /
:class:`ForeignMoney`), append-only corrections, and the world/refusal gates
(:class:`SourceObservationBoundary`). Story 3.3 lands the data-policy owner of the
seven room-roles per world (:class:`WorldRooms`): rebuildable analytics views that
record their rebuild pins (:class:`RebuildPins`), the ``(source, instrument,
time-window)`` series partition (:class:`SeriesPartition`, :class:`SeriesPlacement`,
:class:`ResolvedSeries`), and the keep-forever-vs-deletion-licensed retention law
(:class:`RetentionPolicy` over the injected :class:`CitationIndex`, yielding a
:class:`RetentionVerdict`). Story 3.4 lands the CT-12 dataset splits and the no-peek seal:
fingerprinted, time-ordered, non-overlapping :class:`SplitManifest`\\ s whose ``split_id`` is
derived from their fp1 (:class:`SplitSegment`, :class:`SplitBoundary`, :class:`SegmentRole`,
required purge/embargo widths leak-guarded against every cited :class:`ProducerHorizon`, and
knowledge-time record partitioning via :class:`KnowledgeRecord`), plus the newest
~12-month :class:`HoldoutSeal` enforced as a policy-rejection refusal at every
:class:`ReadBoundary` with exactly one journaled final look. Story 3.5 lands the durable
journal data-policy over the same seam: the seven ratified event types
(:class:`JournalEventType`) as fp1-canonical :class:`JournalEvent` values with
``correlation_id`` and ``display_time`` excluded from identity, the decision event's
mandatory closed :class:`DecisionOutcome` selected by projection (:func:`select_decisions`,
:func:`veto_ledger`), cross-stream causal linkage as typed :class:`CausalEdge` records,
gapless per-(writer, boot-epoch) sequences with loss surfaced (:func:`detect_sequence_gaps`),
and the :class:`JournalWriter` producer (block-on-unpersistable) / :class:`JournalReader`
pair. Story 3.6 lands the CT-25 read-time entity-journal projections (logbooks) over the same
recorded streams: the Book journal, BMS journal, and per-bot journal (the operator's logbook)
as :class:`Logbook` views selected by :class:`EntitySelector` entity identity
(:func:`entity_journal`, :func:`book_journal`, :func:`bms_journal`, :func:`bot_logbook`), the
risk-authored / venue-authored :class:`EventClass` split with binding identity
(:class:`BindingIdentity`) and the pinned command-fingerprint join (:class:`CommandIndex`),
role-scoped namespaces with the FM-11 cross-role guard and its two declared
:class:`CrossRoleRead` exceptions (:func:`role_namespace`, :func:`decay_cohort_read`), and the
legacy five Records streams as projection names over the one versioned
:data:`RECORDS_STREAM_MAPPING` table (:func:`records_stream`).

``qmf.data`` imports only ``qmf-core`` (the fp1 vocabulary and typed refusals) plus
its own engine libraries — the default-deny dependency direction (L30) holds, and the
ratified ``qmf-registry → qmf-data`` edge points AT this package.
"""

from __future__ import annotations

from qmf.data.journal import (
    CausalEdge,
    DecisionOutcome,
    JournalEvent,
    JournalEventType,
    detect_sequence_gaps,
    select_decisions,
    veto_ledger,
)
from qmf.data.journal_producer import (
    EdgeWrite,
    JournalAppendReceipt,
    JournalReader,
    JournalWriter,
    LineageEdgeAppender,
)
from qmf.data.logbooks import (
    ACCOUNT_ID_KEY,
    BMS_INSTANCE_ID_KEY,
    BOOK_DEFINITION_FP_KEY,
    BOOK_IDENTITY_FIELDS,
    BOOK_INSTANCE_ID_KEY,
    BOT_DEFINITION_FP_KEY,
    COMMAND_FINGERPRINT_KEY,
    CT25_CONTRACT_FORMAT_VERSION,
    RECORDS_STREAM_MAPPING,
    ROLE_KEY,
    SEAT_BINDING_KEY,
    VENUE_ID_KEY,
    BindingIdentity,
    BotSeat,
    CommandAttribution,
    CommandIndex,
    CrossRoleRead,
    EntityKind,
    EntitySelector,
    EventClass,
    Logbook,
    ProjectedRow,
    RecordsStreamName,
    RecordsStreamRule,
    bms_journal,
    book_journal,
    bot_logbook,
    decay_cohort_read,
    entity_journal,
    event_class_of,
    guard_neutral_venue_payload,
    read_binding,
    read_bot_seat,
    read_command_fingerprint,
    read_role,
    records_stream,
    role_namespace,
)
from qmf.data.observation import ForeignMoney, ForeignTimestamp, SourceObservation
from qmf.data.partitions import ResolvedSeries, SeriesPartition, SeriesPlacement
from qmf.data.retention import CitationIndex, RetentionPolicy, RetentionVerdict
from qmf.data.rooms import RebuildPins, WorldRooms
from qmf.data.seal import (
    FINAL_LOOK_SUBTYPE,
    SEAL_CONTROL_STREAM,
    HoldoutSeal,
    ReadBoundary,
)
from qmf.data.source_boundary import ObservationReceipt, SourceObservationBoundary
from qmf.data.splits import (
    DEFAULT_SPLIT_ROLES,
    KnowledgeKind,
    KnowledgeRecord,
    ProducerHorizon,
    SegmentRole,
    SplitBoundary,
    SplitManifest,
    SplitSegment,
)
from qmf.data.store import EvidenceStore

__all__ = [
    "ACCOUNT_ID_KEY",
    "BMS_INSTANCE_ID_KEY",
    "BOOK_DEFINITION_FP_KEY",
    "BOOK_IDENTITY_FIELDS",
    "BOOK_INSTANCE_ID_KEY",
    "BOT_DEFINITION_FP_KEY",
    "COMMAND_FINGERPRINT_KEY",
    "CT25_CONTRACT_FORMAT_VERSION",
    "DEFAULT_SPLIT_ROLES",
    "FINAL_LOOK_SUBTYPE",
    "RECORDS_STREAM_MAPPING",
    "ROLE_KEY",
    "SEAL_CONTROL_STREAM",
    "SEAT_BINDING_KEY",
    "VENUE_ID_KEY",
    "BindingIdentity",
    "BotSeat",
    "CausalEdge",
    "CitationIndex",
    "CommandAttribution",
    "CommandIndex",
    "CrossRoleRead",
    "DecisionOutcome",
    "EdgeWrite",
    "EntityKind",
    "EntitySelector",
    "EventClass",
    "EvidenceStore",
    "ForeignMoney",
    "ForeignTimestamp",
    "HoldoutSeal",
    "JournalAppendReceipt",
    "JournalEvent",
    "JournalEventType",
    "JournalReader",
    "JournalWriter",
    "KnowledgeKind",
    "KnowledgeRecord",
    "LineageEdgeAppender",
    "Logbook",
    "ObservationReceipt",
    "ProducerHorizon",
    "ProjectedRow",
    "ReadBoundary",
    "RebuildPins",
    "RecordsStreamName",
    "RecordsStreamRule",
    "ResolvedSeries",
    "RetentionPolicy",
    "RetentionVerdict",
    "SegmentRole",
    "SeriesPartition",
    "SeriesPlacement",
    "SourceObservation",
    "SourceObservationBoundary",
    "SplitBoundary",
    "SplitManifest",
    "SplitSegment",
    "WorldRooms",
    "__version__",
    "bms_journal",
    "book_journal",
    "bot_logbook",
    "decay_cohort_read",
    "detect_sequence_gaps",
    "entity_journal",
    "event_class_of",
    "guard_neutral_venue_payload",
    "read_binding",
    "read_bot_seat",
    "read_command_fingerprint",
    "read_role",
    "records_stream",
    "role_namespace",
    "select_decisions",
    "veto_ledger",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
