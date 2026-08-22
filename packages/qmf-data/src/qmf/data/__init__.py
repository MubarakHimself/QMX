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
:data:`RECORDS_STREAM_MAPPING` table (:func:`records_stream`). Story 5.1 lands the
CT-14 off-machine backup primitive (:mod:`qmf.data.backup`):
:class:`OffMachineBackup` consumes CT-26 :class:`~qmf.data.store.RoomExport` input,
encrypts through an injected :class:`PayloadCipher`, and puts a new versioned artifact
through an injected :class:`ObjectStorage` port — encryption required as a pointer,
no provider/credentials/RPO baked in. Story 5.2 lands the matching restore primitive
(:class:`OffMachineRestore`): fetch + decrypt into a **replacement** store root, never
rewriting or deleting the only local copy; restored reads still enforce the 12-month
seal and world isolation as policy rejections. Story 5.3 lands the verify primitives
(:class:`OffMachineVerify`): automated :meth:`~OffMachineVerify.sample_restore` and
:meth:`~OffMachineVerify.full_restore_rehearsal` are the **only** source of a
:class:`RecoverabilityClaim` (never a snapshot alone), corrupt restores are
``storage failure``, and :func:`migrate_evidence` runs preflight → backup-first →
dry-run → migrate → verify without mutating the only copy; numeric RPO/RTO/retention/
cadence stay null node/ops pointers. Story 5.4 lands the application-owned nightly
cycle helper (:class:`OffMachineCycle`): :meth:`~OffMachineCycle.run_once` runs one
CT-26 → CT-14 → sample-restore (+ optional full-restore rehearsal) cycle with no
threads, cron, or daemon in ``qmf-data``; asking the boundary to own the schedule or a
numeric RPO/RTO is a typed refusal (:func:`refuse_schedule_ownership`,
:func:`refuse_numeric_rpo_rto`). Story 6.1 lands the CT-15 external-source ingest
seam (:mod:`qmf.data.ingest`, ``COMP-QMF-DATA-INGEST``): :class:`ExternalSourceIngest`
owns and calls the injected :class:`ExternalSourcePort`, normalizes
:class:`ProviderRecord` responses into CT-10 producer values under idempotent
:class:`IntakeKey` ``(source, source-native id, revision)`` intake, application-routes
them to :class:`SourceObservationBoundary`, and refuses scheduler/daemon/retry-loop
ownership (:func:`~qmf.data.ingest.refuse_schedule_ownership`). Story 6.2 lands bid/ask
preservation and source-disagreement edges (:mod:`qmf.data.ticks`): :class:`TickQuote`
keeps bid and ask separate with source timestamps and refuses mid-merge;
:func:`~qmf.data.ticks.relate_source_facts` emits ``corroborates`` /
``disagrees-with`` :class:`CausalEdge` values; :func:`~qmf.data.ticks.link_revision`
links a later ``(source, id, revision)`` artifact via ``supersedes`` — never overwrite,
never a ``qmf-registry`` import (DEC-0119, DEC-0120). Story 6.3 lands the Dukascopy
download-once historical tick adapter (:mod:`qmf.data.dukascopy`, ``COMP-DUKASCOPY``):
:class:`DukascopyAdapter` is CT-15 provider #1 under personal-use licensing, decodes
bounded bi5 evidence through an injected :class:`DukascopyTransport` (no donor
``dukascopy-node`` code), stamps every window with a :class:`LicenseTag`, and refuses
unlicensed governed-evidence use, complete-corpus downloads, and external-recovery
ownership (DEC-0166, DEC-0170, DEC-0051).

``qmf.data`` imports only ``qmf-core`` (the fp1 vocabulary and typed refusals) plus
its own engine libraries — the default-deny dependency direction (L30) holds, and the
ratified ``qmf-registry → qmf-data`` edge points AT this package.
"""

from __future__ import annotations

from qmf.data.backup import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    ENCRYPTION_REQUIRED,
    BackupCopyReceipt,
    ObjectStorage,
    OffMachineBackup,
    OffMachineCopy,
    OffMachineRestore,
    PayloadCipher,
    RestoreReceipt,
    StoragePutAck,
)
from qmf.data.cycle import (
    BACKUP_CADENCE,
    CYCLE_ROOM_ROLES,
    NightlyCycleReport,
    OffMachineCycle,
    refuse_numeric_rpo_rto,
    refuse_schedule_ownership,
)
from qmf.data.dukascopy import (
    DUKASCOPY_SOURCE,
    FACTORY_MAX_WINDOW_NS,
    PERSONAL_USE_LICENSE,
    DecodedTick,
    DukascopyAdapter,
    DukascopyHourKey,
    DukascopyTransport,
    LicensedSourceWindow,
    LicenseTag,
    decode_bi5_ticks,
    offer_for_governed_evidence,
    refuse_complete_corpus_download,
    refuse_external_recovery,
)
from qmf.data.ingest import (
    ExternalSourceIngest,
    ExternalSourcePort,
    IntakeKey,
    IntakeOutcome,
    IntakeReceipt,
    ProviderRecord,
    SourceRequest,
    refuse_source_as_venue,
)
from qmf.data.ingest import (
    refuse_schedule_ownership as refuse_ingest_schedule_ownership,
)
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
from qmf.data.ticks import (
    EDGE_CORROBORATES,
    EDGE_DISAGREES_WITH,
    EDGE_SUPERSEDES,
    TickObservation,
    TickQuote,
    link_revision,
    refuse_mid_merge,
    relate_source_facts,
)
from qmf.data.verify import (
    MIGRATION_SEQUENCE,
    NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE,
    NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE,
    NODE_OPS_BACKUP_RETENTION_PERIOD,
    NODE_OPS_RESTORE_VERIFICATION_CADENCE,
    RESTORABLE_ROOM_ROLES,
    MigrationStage,
    OffMachineVerify,
    RecoverabilityClaim,
    StoreMigrationReport,
    VerifiedRoom,
    VerifyKind,
    migrate_evidence,
    refuse_snapshot_alone_claim,
)

__all__ = [
    "ACCOUNT_ID_KEY",
    "BACKUP_CADENCE",
    "BACKUP_CONTRACT_FORMAT_VERSION",
    "BMS_INSTANCE_ID_KEY",
    "BOOK_DEFINITION_FP_KEY",
    "BOOK_IDENTITY_FIELDS",
    "BOOK_INSTANCE_ID_KEY",
    "BOT_DEFINITION_FP_KEY",
    "COMMAND_FINGERPRINT_KEY",
    "CT25_CONTRACT_FORMAT_VERSION",
    "CYCLE_ROOM_ROLES",
    "DEFAULT_SPLIT_ROLES",
    "DUKASCOPY_SOURCE",
    "EDGE_CORROBORATES",
    "EDGE_DISAGREES_WITH",
    "EDGE_SUPERSEDES",
    "ENCRYPTION_REQUIRED",
    "FACTORY_MAX_WINDOW_NS",
    "FINAL_LOOK_SUBTYPE",
    "MIGRATION_SEQUENCE",
    "NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE",
    "NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE",
    "NODE_OPS_BACKUP_RETENTION_PERIOD",
    "NODE_OPS_RESTORE_VERIFICATION_CADENCE",
    "PERSONAL_USE_LICENSE",
    "RECORDS_STREAM_MAPPING",
    "RESTORABLE_ROOM_ROLES",
    "ROLE_KEY",
    "SEAL_CONTROL_STREAM",
    "SEAT_BINDING_KEY",
    "VENUE_ID_KEY",
    "BackupCopyReceipt",
    "BindingIdentity",
    "BotSeat",
    "CausalEdge",
    "CitationIndex",
    "CommandAttribution",
    "CommandIndex",
    "CrossRoleRead",
    "DecisionOutcome",
    "DecodedTick",
    "DukascopyAdapter",
    "DukascopyHourKey",
    "DukascopyTransport",
    "EdgeWrite",
    "EntityKind",
    "EntitySelector",
    "EventClass",
    "EvidenceStore",
    "ExternalSourceIngest",
    "ExternalSourcePort",
    "ForeignMoney",
    "ForeignTimestamp",
    "HoldoutSeal",
    "IntakeKey",
    "IntakeOutcome",
    "IntakeReceipt",
    "JournalAppendReceipt",
    "JournalEvent",
    "JournalEventType",
    "JournalReader",
    "JournalWriter",
    "KnowledgeKind",
    "KnowledgeRecord",
    "LicenseTag",
    "LicensedSourceWindow",
    "LineageEdgeAppender",
    "Logbook",
    "MigrationStage",
    "NightlyCycleReport",
    "ObjectStorage",
    "ObservationReceipt",
    "OffMachineBackup",
    "OffMachineCopy",
    "OffMachineCycle",
    "OffMachineRestore",
    "OffMachineVerify",
    "PayloadCipher",
    "ProducerHorizon",
    "ProjectedRow",
    "ProviderRecord",
    "ReadBoundary",
    "RebuildPins",
    "RecordsStreamName",
    "RecordsStreamRule",
    "RecoverabilityClaim",
    "ResolvedSeries",
    "RestoreReceipt",
    "RetentionPolicy",
    "RetentionVerdict",
    "SegmentRole",
    "SeriesPartition",
    "SeriesPlacement",
    "SourceObservation",
    "SourceObservationBoundary",
    "SourceRequest",
    "SplitBoundary",
    "SplitManifest",
    "SplitSegment",
    "StoragePutAck",
    "StoreMigrationReport",
    "TickObservation",
    "TickQuote",
    "VerifiedRoom",
    "VerifyKind",
    "WorldRooms",
    "__version__",
    "bms_journal",
    "book_journal",
    "bot_logbook",
    "decay_cohort_read",
    "decode_bi5_ticks",
    "detect_sequence_gaps",
    "entity_journal",
    "event_class_of",
    "guard_neutral_venue_payload",
    "link_revision",
    "migrate_evidence",
    "offer_for_governed_evidence",
    "read_binding",
    "read_bot_seat",
    "read_command_fingerprint",
    "read_role",
    "records_stream",
    "refuse_complete_corpus_download",
    "refuse_external_recovery",
    "refuse_ingest_schedule_ownership",
    "refuse_mid_merge",
    "refuse_numeric_rpo_rto",
    "refuse_schedule_ownership",
    "refuse_snapshot_alone_claim",
    "refuse_source_as_venue",
    "relate_source_facts",
    "role_namespace",
    "select_decisions",
    "veto_ledger",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
