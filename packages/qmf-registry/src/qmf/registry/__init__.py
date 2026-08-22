"""qmf.registry — governed records, lineage, and promotion.

Roster package of the QMF V1 uv workspace. It re-exports the public CT-* surface as
it lands story by story.

Landed (Story 2.1): CT-06 per-kind, fingerprint-keyed registration records — the tiny
common header plus a kind-specific body, the addable-never-redefined
:class:`KindRegistry`, and a pure in-memory :class:`Registrar` whose stable id is
derived from an ``fp1`` fingerprint and whose byte-identical re-write is idempotent
while a true collision is refused and alarmed (DEC-0114, DEC-0108, DEC-0110).

Landed (Story 2.2): CT-07 append-only typed lineage edges — the ratified
:class:`EdgeType` vocabulary, the frozen :class:`LineageEdge` whose id is derived from
its ``fp1`` fingerprint and which serializes to the pinned JSONL line, and a pure
in-memory single-writer :class:`EdgeLog` that holds ``supersedes`` linear (one
resolvable head), leaves ``branches-from`` multi-headed, keeps a byte-identical
re-append idempotent while refusing and alarming a true collision, and rebuilds its
derived indexes from the edge evidence (DEC-0114, DEC-0158, DEC-0144, DEC-0119).

Landed (Story 2.3): the human-signed promotion occurrence — the only path to live money.
:class:`PromotionCard` mints the reserved CT-06 ``promotion-occurrence-card`` kind with a
human-only signer, a mandatory plain-words summary declared an identity field, the
attested record's ``fp1``, and (for an AD-32 risk admission) the Book/BMS-definition
fingerprint as an identity field; :func:`authorize_live_promotion` refuses a live
promotion with no such card present (FM-4); :func:`correct_summary` mints a NEW card with
a CT-07 ``supersedes`` edge rather than editing the signed words; and
:class:`PromotionEvent` / :func:`emit_promotion_event` emit the CT-13 ``promotion`` event
— only the card's ``fp1`` plus ``correlation_id`` — through the core
:class:`~qmf.core.JournalSink` seam (DEC-0116, DEC-0158, DEC-0041).

Landed (Story 2.4): CT-09 registry persistence through ``qmf-data``'s CT-11 append-store
— the single ratified inter-library edge ``qmf-registry → qmf-data``.
:class:`RegistryPersistence` persists CT-06 records (SQLite metadata) and CT-07 edges
(JSONL append streams) into the **per-world registry room**, content-addressed on
``fp1`` (:func:`persistence_fingerprint`) with no database server and stdlib-typed
signatures at the seam; a byte-identical re-write is idempotent while a true collision is
refused and alarmed at the store boundary; a cross-world read and a ``world = simulated``
write are policy rejections (FM-7); an underlying store failure is a ``storage failure``
typed refusal translated at the qmf-data boundary, never raised across the seam (FM-8); a
persisted record reads back as a :class:`LoadedRecord` and an edge as a
:class:`LineageEdge`; and :func:`migrate_registry_format` runs the staged
preflight→backup-first→dry-run→migrate→verify format migration, never in-place, with the
source store as the documented restore path (DEC-0120, DEC-0108, DEC-0110, DEC-0109,
DEC-0118, DEC-0103).

Every ``fp1`` fingerprint is computed in ``qmf-core`` and nowhere else; this package
imports ``qmf.core``, its own siblings (``records``, ``lineage``, ``promotion``), and —
through the one ratified edge — ``qmf.data.store`` for persistence (DEC-0120). Under
default-deny no library imports ``qmf-registry`` — registration, lineage, promotion, and
persistence are invoked by the application at the composition root.
"""

from __future__ import annotations

from qmf.registry.lineage import (
    EDGE_CONTRACT_FORMAT_VERSION,
    EdgeAppendReceipt,
    EdgeLog,
    EdgeType,
    LineageEdge,
)
from qmf.registry.persistence import (
    BackupSink,
    LoadedRecord,
    MigrationReport,
    RecordTransform,
    RegistryPersistence,
    StoreReceipt,
    migrate_registry_format,
    persistence_fingerprint,
)
from qmf.registry.promotion import (
    KIND_PROMOTION_OCCURRENCE_CARD,
    PROMOTION_CARD_CONTRACT_FORMAT_VERSION,
    PromotionAuthorization,
    PromotionCard,
    PromotionCorrection,
    PromotionEvent,
    authorize_live_promotion,
    correct_summary,
    emit_promotion_event,
)
from qmf.registry.records import (
    CONTRACT_FORMAT_VERSION,
    RESERVED_KIND_NAMES,
    FieldSetKind,
    KindContract,
    KindRegistry,
    Registrar,
    RegistrationReceipt,
    RegistrationRecord,
    WriteOutcome,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "EDGE_CONTRACT_FORMAT_VERSION",
    "KIND_PROMOTION_OCCURRENCE_CARD",
    "PROMOTION_CARD_CONTRACT_FORMAT_VERSION",
    "RESERVED_KIND_NAMES",
    "BackupSink",
    "EdgeAppendReceipt",
    "EdgeLog",
    "EdgeType",
    "FieldSetKind",
    "KindContract",
    "KindRegistry",
    "LineageEdge",
    "LoadedRecord",
    "MigrationReport",
    "PromotionAuthorization",
    "PromotionCard",
    "PromotionCorrection",
    "PromotionEvent",
    "RecordTransform",
    "Registrar",
    "RegistrationReceipt",
    "RegistrationRecord",
    "RegistryPersistence",
    "StoreReceipt",
    "WriteOutcome",
    "__version__",
    "authorize_live_promotion",
    "correct_summary",
    "emit_promotion_event",
    "migrate_registry_format",
    "persistence_fingerprint",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
