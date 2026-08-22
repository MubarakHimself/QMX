"""CT-09 — registry persistence through the qmf-data store-seam (COMP-QMF-REGISTRY).

The durable tail of the registry: CT-06 per-kind records and CT-07 lineage edges
persist through ``qmf-data``'s CT-11 append-store into the **per-world registry room**,
over the single ratified inter-library edge ``qmf-registry → qmf-data`` (DEC-0120). The
pure in-memory guards of Stories 2.1/2.2 (:class:`~qmf.registry.Registrar`,
:class:`~qmf.registry.EdgeLog`) stay the reference identity guards; this module is the
one place the registry reaches real storage, and it does so **only** by consuming the
already-ratified store seam — the per-world registry room, the fp1-keyed
idempotent/collision semantics, the world guards, and the storage-failure translation
already live in ``qmf.data.store`` and are never re-implemented here (L30; CT-09; CT-11).

Six laws this module pins down.

**Persisted through CT-11 into the per-world registry room, no database server (AC1;
CT-09, CT-11, L30).** :class:`RegistryPersistence` wraps one world's
:class:`~qmf.data.store.RegistryRoom`. A record persists through
:meth:`~qmf.data.store.RegistryRoom.put_record` (SQLite metadata engine) and a lineage
edge through :meth:`~qmf.data.store.RegistryRoom.append_lineage_edge` (JSONL append
stream) — the two evidence-bearing formats of the registry room, one of ``qmf-data``'s
seven room-roles held under the same retention/backup/migration law as every evidence
room. Every signature at the seam is **stdlib-typed** — a ``Mapping``, a ``str``, an
``int`` — so no ``qmf-registry`` value type and no ``qmf-data`` engine ever crosses the
boundary; the registry hands the store the record's canonical identity content and takes
back bytes.

**Content-addressed on fp1, never a timestamp or minted id (AC2; DEC-0108).** The store
is content-addressed. A record's persistence key **is the record's own fp1 stable id** —
the store fingerprints the record's **full CT-06 fp1 identity content** directly (never a
second wrapping envelope over it), so :func:`persistence_fingerprint` is exactly the
record's :attr:`~qmf.registry.RegistrationRecord.stable_id` and the persist receipt's
fingerprint equals it (CT-09 ``record_stable_id`` is the storage key). It is a pure
function of the record's stable identity, so the same record from two sandboxes lands on
one key and dedups by construction, and no occurrence fact (writer, sequence, created-at)
enters it — those ride a **display-only occurrence sidecar** keyed by the same digest and
outside identity, so who wrote a registration and in what order still round-trips
(DEC-0110). A lineage edge is persisted under **its own** CT-07 ``fp1`` edge fingerprint
exactly: the store fingerprints the edge's identity content directly and this module
presents the edge fingerprint, so the storage key IS the edge's fp1 stable id. A
byte-identical re-write is accepted silently (idempotent); a true collision (one fp1
addressing differing bytes) is refused and alarmed at the store boundary, never
overwritten. ``supersedes`` stays **pinned linear on the durable path too, and room-wide**:
before a new ``supersedes`` edge is appended, the persisted edge set **across every edge
stream in the registry room** is consulted and a fork (a second outgoing/incoming edge on any
stream, a self-loop, or a cycle) is a ``policy rejection``, so CT-07's one-resolvable-head
invariant holds for persisted evidence room-wide — a fork can never hide by landing on a
second stream — not only within one stream or the in-memory :class:`~qmf.registry.EdgeLog`.

**Rooms per world; cross-world reads and simulated writes refuse (AC3; FM-7).** A
:class:`RegistryPersistence` is bound to exactly one world's room. :meth:`open` for
``world = simulated`` is a ``policy rejection`` (it has no governed namespace in V1), so
a non-live world never writes the live evidence namespace. Every read declares the world
it reads as — there is no implicit same-world default — and a read that names a different
world than the room's is a ``policy rejection``. World isolation is storage separation.

**Storage failures are typed refusals, never exceptions across the seam (AC4; FM-8).**
An underlying store failure — disk-full, corrupt, locked, truncated — is translated to a
``storage failure`` typed refusal **at the qmf-data boundary** and returned as a value;
no store-library exception ever crosses the package seam, and no partial registration is
claimed successful. This module simply propagates the store's value-or-refusal, and a
corrupt persisted artifact it reads back is itself surfaced as a ``storage failure``.

**Migrations are staged, backup-first, never in-place (AC5; AR-32, AR-25).**
:func:`migrate_registry_format` runs the ratified five-stage procedure — preflight →
backup-first → dry-run → migrate → verify — from a source persistence to a **distinct
destination in the same world** (a same-root migration and a cross-world migration are
both refused: a live corpus is never copied into the replay namespace, FM-7). The
backup-first stage does not merely *read* the source's restorable export and drop it — it
**writes a real backup artifact** (through a caller-supplied ``backup_sink`` or, by
default, to a file under the destination root) and ``backed_up`` reflects that a backup
was actually written, never a hard-coded constant. The only copy is never mutated in place
and the source store IS the documented restore path. The procedure migrates **records
only**; CT-07 lineage edges are append-only and format-stamped per line and are not
transformed here, which the report states explicitly (``records_only``). Every serialized
registry artifact stamps its contract format version (the store receipt echoes it and the
fp1 identity carries it), so history stays readable forever.

**Reference identity round-trips (AC6; L27).** A persisted record reads back as its
CT-06 identity (:class:`LoadedRecord`), whose recomputed ``fp1`` stable id equals the
original's; a persisted edge reads back as a full :class:`~qmf.registry.LineageEdge`
whose recomputed edge fingerprint equals the original's. The CT-09 contract test
exercises this against the real CT-11 store-seam, and the reference-usage example ships.

Default-deny holds and is *widened by exactly one ratified edge*: this module imports
``qmf.core``, its own siblings ``qmf.registry.records`` / ``qmf.registry.lineage``, and
``qmf.data.store`` — the sole inter-library persistence edge (DEC-0120). Every ``fp1``
fingerprint is computed in ``qmf-core`` and nowhere else. Every operation succeeds or
RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain failure is never raised across
the boundary. Stdlib plus qmf-core, package siblings, and the qmf-data store seam;
frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Final, Self, cast

from qmf.core import (
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.data.store import (
    EvidenceStore,
    RoomExport,
    RoomRole,
    StoreReceipt,
    WorldStore,
)
from qmf.registry.lineage import EdgeType, LineageEdge
from qmf.registry.records import (
    RESERVED_KIND_NAMES,
    RegistrationRecord,
    is_genuine_reserved_record,
)

__all__ = [
    "BackupSink",
    "LoadedRecord",
    "MigrationReport",
    "RecordTransform",
    "RegistryPersistence",
    "StoreReceipt",
    "migrate_registry_format",
    "persistence_fingerprint",
]


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a persistence wiring mistake returns.

    ``retryability`` is ``no`` — a non-record persist argument, a same-root migration, or
    a bad edge stream name is a caller/wiring mistake, not a transient condition — and
    ``context`` always names the offending ``field`` (returned, never raised; CT-04;
    DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _corrupt(reason: str, **extra: object) -> TypedRefusal:
    """Build a ``storage failure`` refusal for a corrupt persisted artifact (AC4; FM-8).

    A read that returns bytes the registry cannot parse back into its own CT-06/CT-07
    shape can only be corrupt stored evidence — the writes here are canonical by
    construction. It is surfaced as a ``storage failure`` (retryability ``no``, exactly
    how qmf-data surfaces a torn line or a corrupt store), never served as a valid record
    or edge, so a corrupt store never masquerades as an absent or a wrong artifact.
    """
    return unpersistable(reason, retryability=Retryability.NO, context=dict(extra))


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build a ``policy rejection`` refusal for a governance/integrity refusal at the seam.

    A forged reserved-kind record presented for persistence (a look-alike of the
    human-signed promotion-occurrence card, the only path to live money) is refused as a
    policy rejection — the same category the promotion gate returns — never stored as if it
    were a signed card (H2; DEC-0116; FM-4). ``retryability`` is ``no``; nothing is written.
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


# --- lineage-edge integrity witness (H3; FM-8) ------------------------------

# A lineage edge persists to an append-only JSONL stream whose per-line index is
# rebuilt from the line bytes on read (AR-31), so the JSONL tail carries no
# tamper-independent authority: a canonical-preserving edit of a stored line re-derives a
# self-consistent edge fingerprint and would otherwise read back as a valid edge pointing
# elsewhere. To close that, every persisted edge is also anchored by a tiny **integrity
# witness** in the registry room's SQLite record store — content-addressed and keyed by
# digest, so it is tamper-evident on its own. On read-back the reconstructed edge's fp1
# fingerprint must resolve to its witness; an edge whose witness is absent is a silently
# altered (or forged) line and is refused as a ``storage failure`` (never served as a valid
# edge). The witness kind is internal and is not a CT-06 registration kind.
_EDGE_WITNESS_KIND: Final[str] = "ct07-lineage-edge-integrity-witness"
_EDGE_WITNESS_FORMAT_VERSION: Final[int] = 1
_EDGE_WITNESS_FP_KEY: Final[str] = "witnessed_edge_fp1"


def _edge_witness_body(edge_fingerprint: Fingerprint) -> dict[str, object]:
    """The witness record body — the edge's own ``fp1`` fingerprint, nothing else."""
    return {_EDGE_WITNESS_FP_KEY: edge_fingerprint.value}


def _edge_witness_key(edge_fingerprint: Fingerprint) -> Result[Fingerprint]:
    """The content-addressed store key an edge's integrity witness persists under.

    Derived from the edge fingerprint alone by mirroring the store's ``put_record``
    envelope (``{kind, format_version, body}``), so a reader recomputes the same key from a
    reconstructed edge without holding any receipt — a pure function of the edge's identity.
    """
    envelope: dict[str, object] = {
        "kind": _EDGE_WITNESS_KIND,
        "format_version": _EDGE_WITNESS_FORMAT_VERSION,
        "body": _edge_witness_body(edge_fingerprint),
    }
    return fingerprint(envelope)


# --- the persisted record identity view -------------------------------------


@dataclass(frozen=True, slots=True)
class LoadedRecord:
    """A CT-06 record read back from the per-world registry room (AC6; DEC-0114).

    The identity-bearing view of a persisted record: ``kind``, the per-kind
    ``contract_format_version``, the canonically-ordered ``at_birth_parent_refs``, the
    kind-specific ``body`` (deep-frozen on read-back exactly as the write side freezes it,
    so a caller can never mutate a nested container through the returned mapping — L5), the
    CT-06 envelope ``format_version``, and the derived ``stable_id`` — recomputed on read
    and asserted equal to the original's. ``persisted_fingerprint`` is the store's
    content-addressed key the record was read under; because the key IS the record's fp1
    stable id, it equals :attr:`stable_id`.

    The occurrence facts (``writer``, per-writer ``sequence``, ``created_at``) are
    **display-only and excluded from identity** — a record deduplicates on identity alone —
    but they are persisted in a display-only occurrence sidecar keyed by the same digest and
    surfaced here, so who wrote a registration and in what order survives the round trip
    (M5; DEC-0110). They are ``None`` for a record persisted without occurrence facts (or
    read from an engine without the sidecar).
    """

    kind: str
    contract_format_version: int
    at_birth_parent_refs: tuple[Fingerprint, ...]
    body: Mapping[str, object]
    format_version: int
    stable_id: Fingerprint
    persisted_fingerprint: Fingerprint
    writer: WriterId | None = None
    sequence: int | None = None
    created_at: Instant | None = None


def _deep_freeze(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form (L5).

    Mirrors :func:`qmf.registry.records._deep_freeze`: a ``Mapping`` becomes a
    :class:`~types.MappingProxyType` over deep-frozen values and a list/tuple a tuple, so a
    body read back from the store is frozen identically to the write side and a caller can
    never mutate a nested container through the reference :class:`LoadedRecord` hands back.
    """
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: _deep_freeze(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(_deep_freeze(item) for item in sequence)
    return value


# --- content-addressed key derivation ---------------------------------------


def persistence_fingerprint(record: object) -> Result[Fingerprint]:
    """The content-addressed store key a record persists under, or a refusal (AC2).

    **The record's own fp1 stable id** — the storage key is the record's
    :attr:`~qmf.registry.RegistrationRecord.stable_id`, never a second fingerprint wrapping
    it (CT-09 ``record_stable_id`` is the storage key; DEC-0108). It is a pure function of
    the record's stable identity, so a caller derives it from a record to read the record
    back without holding the persist receipt, and it never depends on a timestamp, a writer,
    a sequence, or a minted id — identical work from two sandboxes derives one key. A
    non-record argument is an ``invalid input`` refusal.
    """
    if not isinstance(record, RegistrationRecord):
        return _invalid(
            "record",
            "a persistence key is derived for a RegistrationRecord",
            given=repr(record),
        )
    return Ok(record.stable_id)


# --- display-only occurrence facts (M5; DEC-0110) ---------------------------

_OCC_WRITER_KEY: Final[str] = "writer"
_OCC_SEQUENCE_KEY: Final[str] = "sequence"
_OCC_CREATED_AT_KEY: Final[str] = "created_at_ns"


def _occurrence_facts(record: RegistrationRecord) -> dict[str, object]:
    """The record's display-only occurrence facts — writer, per-writer sequence, created-at.

    Excluded from the record's fp1 identity (DEC-0110); persisted in the occurrence sidecar
    keyed by the record's digest, so who wrote a registration and in what order survives a
    persist/load round trip (M5). The writer is its four opaque string parts and created-at
    its int64 nanosecond count, so the mapping is fp1-clean.
    """
    return {
        _OCC_WRITER_KEY: {
            "machine": record.writer.machine,
            "role": record.writer.role,
            "stream": record.writer.stream,
            "boot_epoch_id": record.writer.boot_epoch_id,
        },
        _OCC_SEQUENCE_KEY: record.sequence,
        _OCC_CREATED_AT_KEY: record.created_at.value_ns,
    }


def _occurrence_from_sidecar(
    occurrence: Mapping[str, object] | None,
) -> tuple[WriterId | None, int | None, Instant | None]:
    """Reconstruct the display-only occurrence facts from the sidecar mapping (M5).

    Returns ``(writer, sequence, created_at)`` — each ``None`` when absent or unparseable,
    since occurrence facts are display-only and never gate correctness. A malformed part is
    simply dropped rather than failing the load.
    """
    if occurrence is None:
        return (None, None, None)
    writer: WriterId | None = None
    writer_obj = occurrence.get(_OCC_WRITER_KEY)
    if isinstance(writer_obj, Mapping):
        parts = cast("Mapping[str, object]", writer_obj)
        built = WriterId.try_create(
            parts.get("machine"),
            parts.get("role"),
            parts.get("stream"),
            parts.get("boot_epoch_id"),
        )
        if is_ok(built):
            writer = built.value
    seq_obj = occurrence.get(_OCC_SEQUENCE_KEY)
    sequence = seq_obj if isinstance(seq_obj, int) and not isinstance(seq_obj, bool) else None
    created_at: Instant | None = None
    created_obj = occurrence.get(_OCC_CREATED_AT_KEY)
    if isinstance(created_obj, int) and not isinstance(created_obj, bool):
        instant = Instant.try_create(created_obj)
        if is_ok(instant):
            created_at = instant.value
    return (writer, sequence, created_at)


# --- the per-world persistence boundary -------------------------------------


class RegistryPersistence:
    """The CT-09 registry-persistence boundary for one world (AC1, AC2, AC3).

    Wraps one world's :class:`~qmf.data.store.RegistryRoom` (and its
    :class:`~qmf.data.store.WorldStore` for the backup-first migration input), and offers
    the persist/load surface for CT-06 records and CT-07 edges over the ratified store
    seam. It owns registry business rules only — identity, the record/edge shapes, and
    the round trip; the data layer owns physical persistence, the fp1-keyed
    idempotent/collision decision, the per-world guards, and the storage-failure
    translation, and this boundary never re-implements any of them (DEC-0120).
    """

    def __init__(self, store: EvidenceStore, world_store: WorldStore) -> None:
        self._store = store
        self._ws = world_store

    def close(self) -> None:
        """Release the registry room's one-writer locks so a handoff is clean (M6).

        :meth:`persist_edge` takes the on-disk ``.writer`` lock on each JSONL lineage stream
        through the store; this surfaces the release at the registry seam — delegating to
        :meth:`~qmf.data.store.RegistryRoom.close` — so a writer handoff or clean shutdown
        never has to reach into ``qmf.data`` internals to drop the lock. Releasing is
        idempotent, and only this store's own locks are removed; reads (unlimited) are
        unaffected.
        """
        self._ws.registry_room.close()

    def __enter__(self) -> Self:
        """Enter a ``with`` block; the persistence is returned unchanged."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Release the one-writer locks on block exit (M6), success or error alike."""
        self.close()

    @classmethod
    def open(cls, store: object, world: object) -> Result[RegistryPersistence]:
        """Open the registry persistence for ``world`` on ``store``, returning
        value-or-refusal (AC3; FM-7).

        ``store`` is a wired :class:`~qmf.data.store.EvidenceStore`. ``world = simulated``
        is a ``policy rejection`` — it has no governed namespace in V1, so a non-live
        world never writes the live evidence namespace — surfaced by the store when the
        per-world bundle is resolved (DEC-0110). ``live`` and ``replay`` each resolve to
        their own room instance. A non-store argument is an ``invalid input`` refusal.
        """
        if not isinstance(store, EvidenceStore):
            return _invalid(
                "store",
                "registry persistence opens over a wired qmf-data EvidenceStore",
                given=repr(store),
            )
        bundle = store.for_world(world)
        if is_refusal(bundle):
            return bundle
        return Ok(cls(store, bundle.value))

    @property
    def world(self) -> World:
        """The single world whose registry room this boundary writes and reads."""
        return self._ws.world

    @property
    def root(self) -> Path:
        """The backing store's root directory (the restore path for a migration)."""
        return self._store.root

    def backup_export(self) -> Result[RoomExport]:
        """The registry room's restorable, verbatim backup input for this world (AC5).

        Reads the per-world registry room through ``qmf-data``'s CT-26 store-to-backup
        boundary — every record's fp1 plus its exact stored canonical bytes, read-only and
        never mutated — so a migration can prove restorability *before* it writes anything
        (backup-first). A cross-world or storage failure surfaces as the store's own typed
        refusal (DEC-0118).
        """
        return self._ws.backup_input.read_room(RoomRole.REGISTRY_ROOM, for_world=self.world)

    # --- records ------------------------------------------------------------

    def persist_record(self, record: object) -> Result[StoreReceipt]:
        """Persist a CT-06 record through the CT-11 append-store, returning
        value-or-refusal (AC1, AC2, AC4).

        The record's full CT-06 fp1 identity content is handed to the store's per-world
        registry room, keyed on **the record's own fp1 stable id**
        (:func:`persistence_fingerprint` is exactly
        :attr:`~qmf.registry.RegistrationRecord.stable_id`,
        and the receipt's fingerprint equals it — CT-09 ``record_stable_id`` is the storage
        key). The display-only occurrence facts (writer, per-writer sequence, created-at)
        ride an occurrence sidecar keyed by the same digest and **outside identity**
        (DEC-0110), so a dedup on identity is unaffected while who wrote the registration and
        in what order still round-trips (M5). A first write is ``stored``, a byte-identical
        re-write is ``idempotent`` and accepted silently (identical work from two sandboxes
        dedups, keeping the first occurrence), and a true collision is refused and alarmed. A
        ``world = simulated`` room, an underlying store failure, and a corrupt engine are
        surfaced as the store's own typed refusals — never raised across the seam. A
        non-record argument is an ``invalid input`` refusal.

        A record of a **reserved** CT-06 kind (the human-signed promotion-occurrence card,
        the only path to live money) is persisted **only** when it was minted through its
        dedicated path (:func:`~qmf.registry.records.is_genuine_reserved_record`); a forged
        look-alike — even one byte-identical to a genuine card — is a ``policy rejection``,
        never stored as if it were a signed card, so the generic persist surface can never
        forge a promotion card (H2; DEC-0116, DEC-0158; FM-4).
        """
        if not isinstance(record, RegistrationRecord):
            return _invalid(
                "record",
                "persistence writes a RegistrationRecord (the CT-06 per-kind record)",
                given=repr(record),
            )
        if record.kind in RESERVED_KIND_NAMES and not is_genuine_reserved_record(record):
            return _policy(
                "record",
                "a reserved CT-06 kind (the human-signed promotion-occurrence card) is "
                "persisted only when minted through its dedicated signing path; a forged "
                "look-alike is refused, never stored as a signed card (H2; DEC-0116; FM-4)",
                kind=record.kind,
                reserved=True,
            )
        return self._ws.registry_room.put_identity_record(
            record.fp1_identity(),
            kind=record.kind,
            format_version=record.contract_format_version,
            occurrence=_occurrence_facts(record),
            presented_fingerprint=record.stable_id,
        )

    def load_record(self, key: object, *, for_world: object) -> Result[LoadedRecord]:
        """Read a persisted record back as its CT-06 identity, returning value-or-refusal
        (AC3, AC6).

        ``key`` is the record's content-addressed persistence fingerprint — the record's
        own fp1 stable id (a :class:`~qmf.core.Fingerprint` or ``fp1:sha256:<hex>`` string),
        from a persist receipt, :func:`persistence_fingerprint`, or the record's
        :attr:`~qmf.registry.RegistrationRecord.stable_id` directly. ``for_world`` is
        required — a read that crosses worlds is a ``policy rejection`` (M4; FM-7). A
        well-formed key that names nothing is a ``stale evidence`` refusal; a malformed key
        an ``invalid input`` refusal; a corrupt stored artifact a ``storage failure``
        refusal. The recomputed ``fp1`` stable id is asserted equal to the original's, so a
        silently altered record can never read back as valid. The display-only occurrence
        facts (writer, per-writer sequence, created-at) are read from the occurrence sidecar
        and surfaced on the :class:`LoadedRecord` (``None`` when none were persisted; M5).
        """
        got = self._ws.registry_room.get_record(key, for_world=for_world)
        if is_refusal(got):
            return got
        resolved_key = _coerce_fingerprint(key)
        if resolved_key is None:  # pragma: no cover - get_record already parsed the key
            return _invalid("key", "a persistence key is an fp1 fingerprint", given=repr(key))
        rebuilt = _reconstruct_record(resolved_key, got.value)
        if is_refusal(rebuilt):
            return rebuilt
        occurrence = self._ws.registry_room.get_record_occurrence(resolved_key, for_world=for_world)
        if is_refusal(occurrence):  # pragma: no cover - defensive: the same-world read just passed
            return occurrence
        writer, sequence, created_at = _occurrence_from_sidecar(occurrence.value)
        return Ok(replace(rebuilt.value, writer=writer, sequence=sequence, created_at=created_at))

    # --- lineage edges ------------------------------------------------------

    def persist_edge(self, edge: object, *, edge_stream: object) -> Result[StoreReceipt]:
        """Append a CT-07 lineage edge to a one-writer JSONL stream, returning
        value-or-refusal (AC1, AC2, AC4).

        The edge's own ``fp1`` identity content is appended to the named ``edge_stream``
        under the edge's :class:`~qmf.core.WriterId`, keyed on **its own** edge fingerprint
        exactly (the store fingerprints the identity content directly and this call presents
        the edge fingerprint). A byte-identical re-append is ``idempotent``; a true collision
        is refused and alarmed; a second writer on the stream, a simulated room, and a store
        failure are the store's typed refusals. A non-edge argument, or a bad stream name, is
        an ``invalid input`` refusal.

        ``supersedes`` is held **pinned linear on the durable path** (CT-07; DEC-0158), and
        the invariant is **room-wide, not per-stream**: a genuinely new ``supersedes`` edge is
        refused (``policy rejection``) when the persisted edge set **across every edge stream
        in this room** already carries an outgoing ``supersedes`` from its subject, an incoming
        ``supersedes`` into its superseded record, a self-loop, or a cycle — so a fork can
        never hide on a second stream, and persisted evidence keeps one resolvable "current",
        not only the in-memory :class:`~qmf.registry.EdgeLog`. A byte-identical re-append of an
        existing ``supersedes`` edge is idempotent (the store decides that on its own fp1),
        never a linearity violation.

        After the append lands, the edge is anchored by a tamper-evident **integrity
        witness** in the (SQLite, content-addressed) record store, so a silently altered
        JSONL line — which the rebuilt-from-content JSONL index cannot catch on its own —
        reconstructs to an edge fingerprint with no witness and is refused on read-back
        (:meth:`read_edges`; H3; FM-8). A witness store failure is returned as itself; a
        byte-identical re-persist re-writes the witness idempotently.
        """
        if not isinstance(edge, LineageEdge):
            return _invalid(
                "edge",
                "persistence appends a LineageEdge (the CT-07 typed lineage edge)",
                given=repr(edge),
            )
        if edge.edge_type is EdgeType.SUPERSEDES:
            guard = self._guard_durable_supersedes(edge)
            if is_refusal(guard):
                return guard
        appended = self._ws.registry_room.append_lineage_edge(
            edge_stream,
            edge.writer,
            edge.fp1_identity(),
            presented_fingerprint=edge.edge_fingerprint,
        )
        if is_refusal(appended):
            return appended
        witness = self._ws.registry_room.put_record(
            _edge_witness_body(edge.edge_fingerprint),
            kind=_EDGE_WITNESS_KIND,
            format_version=_EDGE_WITNESS_FORMAT_VERSION,
        )
        if is_refusal(witness):
            return witness
        return appended

    def read_edges(
        self, edge_stream: object, *, for_world: object
    ) -> Result[tuple[LineageEdge, ...]]:
        """Read a lineage-edge stream back as CT-07 edges, in append order (AC3, AC6).

        ``for_world`` is required — a read that crosses worlds is a ``policy rejection``
        (M4; FM-7). A never-written stream reads as an empty tuple (streams are lazily
        created). Every line reconstructs a full :class:`~qmf.registry.LineageEdge` —
        edges carry no occurrence-only fields, so the round trip is total. Each
        reconstructed edge's ``fp1`` fingerprint is then verified against its tamper-evident
        integrity witness in the record store (:meth:`persist_edge`): a line whose witness
        is absent is a silently altered (or forged) edge and is refused as a ``storage
        failure``, never served as a valid edge pointing elsewhere (AC6; FM-8). A bad
        stream name is an ``invalid input`` refusal (surfaced by the store).
        """
        raw = self._ws.registry_room.read_lineage(edge_stream, for_world=for_world)
        if is_refusal(raw):
            return raw
        edges: list[LineageEdge] = []
        for line in raw.value:
            rebuilt = _reconstruct_edge(line)
            if is_refusal(rebuilt):
                return rebuilt
            witnessed = self._verify_edge_witness(rebuilt.value, for_world=for_world)
            if is_refusal(witnessed):
                return witnessed
            edges.append(rebuilt.value)
        return Ok(tuple(edges))

    def _verify_edge_witness(self, edge: LineageEdge, *, for_world: object) -> Result[None]:
        """Assert a reconstructed edge resolves to its tamper-evident integrity witness.

        Recomputes the witness store key from the edge's ``fp1`` fingerprint and reads it
        back from the (content-addressed, tamper-evident) record store. A present witness is
        the edge unaltered; an **absent** witness (``stale evidence``) means the stored line
        was silently altered or forged — the reconstructed fingerprint has no witness — and
        is surfaced as a ``storage failure`` refusal, never a valid edge (H3; AC6; FM-8). A
        cross-world or store failure on the witness read surfaces as the store's own refusal.
        """
        key = _edge_witness_key(edge.edge_fingerprint)
        if is_refusal(key):  # pragma: no cover - the edge fingerprint is fp1-clean by construction
            return _corrupt("a persisted lineage edge fingerprint is not fp1-clean")
        witness = self._ws.registry_room.get_record(key.value, for_world=for_world)
        if is_refusal(witness):
            if witness.category is RefusalCategory.STALE_EVIDENCE:
                return _corrupt(
                    "a persisted lineage edge has no integrity witness; the stored line was "
                    "altered or forged, so the edge is not served (AC6; FM-8)",
                    edge_fingerprint=edge.edge_fingerprint.value,
                )
            return witness
        return Ok(None)

    def _guard_durable_supersedes(self, edge: LineageEdge) -> Result[None]:
        """Refuse a new ``supersedes`` edge that would fork the durable chain (M1; CT-07).

        Consults the **persisted** ``supersedes`` edges **across every edge stream in this
        room** — CT-07's one-resolvable-head invariant is room-wide, not per-stream, so a fork
        that lands on a *different* stream (a second superseder of the same record, a second
        outgoing edge from the same subject, a self-loop, or a cycle) must be refused exactly
        as an in-stream fork (DEC-0158, DEC-0144). Every stream is read back and
        witness-verified through :meth:`read_edges` in this room's world. A ``supersedes`` edge
        already present with this exact fingerprint is a byte-identical re-append the store
        handles as idempotent, so it is excluded from the fork test and never trips linearity.
        A read failure (corrupt/tampered stream, cross-world) propagates as itself, so nothing
        is appended over an unreadable chain.
        """
        existing = self._read_all_supersedes_edges()
        if is_refusal(existing):
            return existing
        return _durable_supersedes_violation(edge, existing.value)

    def _read_all_supersedes_edges(self) -> Result[tuple[LineageEdge, ...]]:
        """Every persisted ``supersedes`` edge across all edge streams in this room (M1).

        Enumerates the room's edge streams
        (:meth:`~qmf.data.store.RegistryRoom.lineage_stream_names`)
        and reads each back — witness-verified — through :meth:`read_edges`, collecting the
        ``supersedes`` edges so the room-wide linearity guard sees the whole chain, not only one
        named stream. A read failure on any stream (corrupt/tampered stream, cross-world)
        propagates unchanged, so a fork is never admitted over an unreadable room.
        """
        names = self._ws.registry_room.lineage_stream_names(for_world=self.world)
        if is_refusal(names):  # pragma: no cover - defensive: the room's own world always matches
            return names
        collected: list[LineageEdge] = []
        for name in names.value:
            edges = self.read_edges(name, for_world=self.world)
            if is_refusal(edges):
                return edges
            collected.extend(edge for edge in edges.value if edge.edge_type is EdgeType.SUPERSEDES)
        return Ok(tuple(collected))


# --- record / edge reconstruction (the read round trip) ---------------------


def _durable_supersedes_violation(
    new_edge: LineageEdge, existing_edges: Sequence[LineageEdge]
) -> Result[None]:
    """The CT-07 linearity refusal a new durable ``supersedes`` edge earns, or ``Ok(None)``.

    Mirrors :meth:`qmf.registry.EdgeLog._supersedes_violation` over the room-wide persisted
    edge set (every stream's ``supersedes`` edges, not one named stream):
    ``supersedes`` is pinned linear (at most one outgoing per subject, at most one incoming
    per superseded record, no self-loop, no cycle), so "current" never forks. A branching
    version graph uses ``branches-from`` instead, which carries no such constraint (DEC-0158,
    DEC-0144). The edge sharing ``new_edge``'s fingerprint (an idempotent re-append) is
    excluded from the indexes so it never reads as its own conflict.
    """
    out: dict[str, str] = {}
    incoming: dict[str, str] = {}
    for edge in existing_edges:
        if edge.edge_type is not EdgeType.SUPERSEDES:
            continue
        if edge.edge_fingerprint == new_edge.edge_fingerprint:
            continue  # a byte-identical re-append: idempotent, not a fork
        out[edge.from_ref.value] = edge.to_ref.value
        incoming[edge.to_ref.value] = edge.from_ref.value
    subject = new_edge.from_ref.value
    superseded = new_edge.to_ref.value
    if subject == superseded:
        return _policy(
            "supersedes",
            "a supersedes edge cannot point a record at itself",
            subject=subject,
        )
    existing_out = out.get(subject)
    if existing_out is not None:
        return _policy(
            "supersedes",
            "supersedes is pinned linear: a subject already has a persisted outgoing "
            "supersedes edge, so a second would make 'current' ambiguous — record a "
            "branches-from edge for a branching version graph instead (DEC-0158)",
            subject=subject,
            existing_to=existing_out,
            attempted_to=superseded,
        )
    existing_in = incoming.get(superseded)
    if existing_in is not None:
        return _policy(
            "supersedes",
            "supersedes is pinned linear: this record is already superseded by another "
            "persisted edge, so a second superseder would fork 'current' — record a "
            "branches-from edge for a branching version graph instead (DEC-0158)",
            superseded=superseded,
            existing_from=existing_in,
            attempted_from=subject,
        )
    seen: set[str] = set()
    cursor: str | None = superseded
    while cursor is not None and cursor not in seen:
        if cursor == subject:
            return _policy(
                "supersedes",
                "a supersedes edge would close a cycle in the persisted version chain, "
                "leaving no resolvable head",
                subject=subject,
                superseded=superseded,
            )
        seen.add(cursor)
        cursor = out.get(cursor)
    return Ok(None)


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or valid ``fp1:sha256:<hex>`` string, or
    ``None`` — parsing goes through qmf-core, never a local hash."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    return parsed.value if is_ok(parsed) else None


def _load_object(raw: bytes) -> Result[dict[str, object]]:
    """Parse persisted canonical bytes back to a JSON object, or a ``storage failure``.

    The writes here are canonical by construction, so bytes that do not parse to a JSON
    object are corrupt stored evidence, surfaced as a ``storage failure`` (AC4).
    """
    try:
        decoded: object = json.loads(raw)
    except ValueError as exc:  # pragma: no cover - defensive: our writes are canonical JSON
        return _corrupt("a persisted registry artifact is not valid JSON", error=str(exc))
    if not isinstance(decoded, dict):  # pragma: no cover - defensive
        return _corrupt("a persisted registry artifact is not a JSON object")
    return Ok(cast("dict[str, object]", decoded))


def _reconstruct_record(persisted_fp: Fingerprint, raw: bytes) -> Result[LoadedRecord]:
    """Reconstruct a :class:`LoadedRecord` from a persisted record's fp1 identity (AC6).

    The stored bytes ARE the record's **full CT-06 fp1 identity content** — the store keys a
    record on its own fp1 stable id, so there is no second envelope wrapping it (M2; CT-09).
    Parses that identity, extracts its fields, recomputes the ``fp1`` stable id from it, and
    returns the identity view with the body **deep-frozen** exactly as the write side freezes
    it (L5). A shape the writer could never have produced is corrupt stored evidence,
    surfaced as a ``storage failure`` refusal (AC4).
    """
    parsed = _load_object(raw)
    if is_refusal(parsed):  # pragma: no cover - defensive
        return parsed
    identity = parsed.value
    kind = identity.get("kind")
    version = identity.get("contract_format_version")
    refs_obj = identity.get("at_birth_parent_refs")
    body_obj = identity.get("body")
    envelope_version = identity.get("format_version")
    if not (
        isinstance(kind, str)
        and isinstance(version, int)
        and not isinstance(version, bool)
        and isinstance(refs_obj, list)
        and isinstance(body_obj, dict)
        and isinstance(envelope_version, int)
        and not isinstance(envelope_version, bool)
    ):  # pragma: no cover - defensive: our writes always carry the full identity shape
        return _corrupt("a persisted record identity is missing a required field")
    refs: list[Fingerprint] = []
    for ref in cast("list[object]", refs_obj):
        resolved = _coerce_fingerprint(ref)
        if resolved is None:  # pragma: no cover - defensive
            return _corrupt("a persisted at-birth parent reference is not an fp1 fingerprint")
        refs.append(resolved)
    # Recompute the record's fp1 stable id over its identity content and assert it equals the
    # key the record was read under. The store key is the digest the SQLite engine filed the
    # row under — retained independently of the ``canonical`` bytes it returns — so a silently
    # altered record (its bytes tampered while the key is unchanged) recomputes to a different
    # fingerprint and is refused as a ``storage failure``, never served (AC6; FM-8). Because
    # the key IS the stable id (M2), this one recompute both verifies integrity and yields the
    # stable id.
    derived = fingerprint(identity)
    if is_refusal(derived):  # pragma: no cover - the identity is fp1-clean by construction
        return _corrupt("a persisted record identity is not fp1-clean")
    if derived.value != persisted_fp:
        return _corrupt(
            "a persisted record's recomputed fingerprint does not match its storage key; "
            "the stored bytes were altered, so the record is not served (AC6; FM-8)",
            expected=persisted_fp.value,
            recomputed=derived.value.value,
        )
    frozen_body = cast("Mapping[str, object]", _deep_freeze(cast("dict[str, object]", body_obj)))
    return Ok(
        LoadedRecord(
            kind=kind,
            contract_format_version=version,
            at_birth_parent_refs=tuple(refs),
            body=frozen_body,
            format_version=envelope_version,
            stable_id=derived.value,
            persisted_fingerprint=persisted_fp,
        )
    )


def _reconstruct_edge(line: Mapping[str, object]) -> Result[LineageEdge]:
    """Reconstruct a :class:`~qmf.registry.LineageEdge` from a persisted JSONL line (AC6).

    Every CT-07 edge field is identity — nothing is excluded — so a persisted edge round
    trips totally: the edge type, both fp1 endpoints, the contract format version, and the
    reconstituted :class:`~qmf.core.WriterId`. :meth:`~qmf.registry.LineageEdge.try_create`
    re-derives the edge fingerprint, so a corrupt line the writer could never have produced
    is a ``storage failure`` refusal, never a silently wrong edge (AC4).
    """
    edge_type = line.get("edge_type")
    from_ref = line.get("from_ref")
    to_ref = line.get("to_ref")
    version = line.get("contract_format_version")
    writer_obj = line.get("writer")
    if not isinstance(
        writer_obj, dict
    ):  # pragma: no cover - defensive: our writes embed the writer
        return _corrupt("a persisted lineage edge carries no writer identity")
    writer_map = cast("dict[str, object]", writer_obj)
    writer = WriterId.try_create(
        writer_map.get("machine"),
        writer_map.get("role"),
        writer_map.get("stream"),
        writer_map.get("boot_epoch_id"),
    )
    if is_refusal(writer):  # pragma: no cover - defensive: the writer was valid when written
        return _corrupt("a persisted lineage edge carries a malformed writer identity")
    rebuilt = LineageEdge.try_create(edge_type, from_ref, to_ref, writer.value, version)
    if is_refusal(rebuilt):  # pragma: no cover - defensive: the edge was valid when written
        return _corrupt("a persisted lineage edge does not reconstruct to a valid CT-07 edge")
    return rebuilt


# --- staged format migration (AR-32, AR-25) ---------------------------------

RecordTransform = Callable[[RegistrationRecord], Result[RegistrationRecord]]
"""A pure per-record migration step: a record in, its migrated form (or a refusal) out."""

BackupSink = Callable[[RoomExport], Result[str]]
"""A durable backup writer: the source's restorable export in, ``Ok(<location>)`` out.

The backup-first stage hands the source registry room's verbatim :class:`~qmf.data.store.RoomExport`
to this sink; a durable write returns ``Ok`` of a location string (a path, an object id) and
a failure returns a refusal that aborts the migration before anything is written. When no
sink is supplied, the migration writes a default backup file under the destination root and
uses its path.
"""


@dataclass(frozen=True, slots=True)
class MigrationReport:
    """The outcome of a staged registry format migration (AC5; AR-32, AR-25).

    ``restore_path`` is the source store root — untouched by the migration, so it is the
    documented path a restore reads from. ``backed_up`` records that a **real backup
    artifact was written** before any migrate write (through the caller's ``backup_sink`` or
    a default file), never a hard-coded constant, and ``backup_path`` names that artifact.
    ``records_only`` states this procedure migrates records only — CT-07 lineage edges are
    append-only and format-stamped per line and are NOT transformed here, so a reader never
    mistakes a verified record migration for an edge migration (M4). ``preflight_count`` /
    ``dry_run_count`` / ``migrated_count`` / ``verified_count`` are the per-stage tallies,
    and ``to_format_version`` the target contract format version every migrated artifact now
    stamps. ``receipts`` are the destination store receipts, each echoing its stamped format
    version.
    """

    restore_path: str
    backed_up: bool
    backup_path: str
    records_only: bool
    preflight_count: int
    dry_run_count: int
    migrated_count: int
    verified_count: int
    to_format_version: int
    receipts: tuple[StoreReceipt, ...]


# The default backup artifact is created with an **exclusive, no-follow** open so a
# pre-planted symlink at the target can never redirect the write onto another file: the
# create fails if anything already exists there (``O_EXCL``) and, where the platform
# offers it (POSIX), refuses to open through a final symlink (``O_NOFOLLOW``). Windows has
# no ``O_NOFOLLOW`` (the flag is POSIX), so the containment + ``islink`` check in
# :func:`_write_bytes_no_follow` carries the guard there. ``O_WRONLY`` completes the mode.
_O_NOFOLLOW: Final[int] = getattr(os, "O_NOFOLLOW", 0)
_BACKUP_OPEN_FLAGS: Final[int] = os.O_CREAT | os.O_EXCL | os.O_WRONLY | _O_NOFOLLOW


def _write_bytes_no_follow(path: Path, data: bytes, *, contain_within: Path) -> Result[None]:
    """Create *path* and write *data*, refusing a symlink-following or out-of-root write.

    The pre-migration backup lands on a path under the destination store root. An attacker
    who plants a symlink at that path — or arranges a parent that resolves outside the root
    — could otherwise redirect a plain ``write_text`` onto a file of their choosing. Two
    guards prevent that: the resolved target must stay inside ``contain_within`` and the
    target must not itself be a symlink, and the file is then created **exclusively**
    (``O_CREAT | O_EXCL``, plus ``O_NOFOLLOW`` on POSIX), so an existing target — a symlink
    included — refuses instead of being followed. Any violation is a ``storage failure``
    refusal and nothing is written (AC5; the Skylos symlink-write finding).
    """
    resolved = Path(os.path.realpath(path))
    root_real = Path(os.path.realpath(contain_within))
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        return _corrupt(
            "refusing to write the pre-migration backup through a symlink or to a path that "
            "resolves outside the intended backup root; a symlink-following write could "
            "redirect it onto another file (AC5)",
            path=str(path),
            root=str(contain_within),
        )
    try:
        # SKY-D215 is suppressed HERE, on this line, and only for this rule.
        #
        # The taint it reports is not real. The path is
        # ``<destination.root>/pre-migration-backup/<world>-registry-room.backup.json``:
        # its only variable segment is a ``World`` enum value ("live" / "replay"), and
        # the rest is the caller's own store root plus literals. No user-supplied string
        # reaches it, and the three lines above prove containment before this runs —
        # realpath resolution inside ``contain_within``, a symlink refusal, and then an
        # exclusive create (``O_CREAT | O_EXCL``, plus ``O_NOFOLLOW`` where the platform
        # has it) that refuses an existing target rather than following it.
        #
        # It is suppressed rather than restructured because SKY-D215 has no guard escape
        # to restructure toward: unlike SKY-D324/D325, it flags any tainted or
        # interpolated path at a filesystem sink unconditionally, consulting no safety
        # state, and every parameter counts as tainted. The only shapes that clear it
        # drop the caller's directory (wrong behaviour) or require POSIX-only ``dir_fd``
        # (this workspace also runs on Windows). Skylos's own codebase suppresses the
        # same rule the same way at an equivalent bounded, no-follow write.
        fd = os.open(  # skylos: ignore[SKY-D215] contained, no-follow, exclusive create
            path, _BACKUP_OPEN_FLAGS, 0o600
        )
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        return _corrupt(
            "could not durably write the pre-migration backup artifact; migration does not "
            "proceed without a backup (AC5)",
            error=str(exc),
            path=str(path),
        )
    return Ok(None)


def _write_backup_artifact(
    export: RoomExport, backup_dir: Path, *, contain_within: Path
) -> Result[str]:
    """Write the source's restorable export to a real backup file, or refuse (AC5; M4).

    The default backup sink: serializes the verbatim :class:`~qmf.data.store.RoomExport`
    (each record's fp1 plus its exact stored canonical bytes) to one file under
    ``backup_dir`` and returns its path, so ``backed_up`` reflects a real artifact rather
    than a hard-coded constant. The write is symlink-safe and contained within
    ``contain_within`` (the destination store root) — a planted symlink or an out-of-root
    target is refused rather than followed (see :func:`_write_bytes_no_follow`). A
    filesystem failure is a ``storage failure`` refusal that aborts the migration before any
    migrate write (backup-first). Canonical bytes are UTF-8 (fp1-canonical JSON / JSONL
    lines), so they round-trip through the JSON text field.

    A destination that **already holds** a pre-migration backup is refused by name — an
    ``invalid input`` on ``field: destination``, the same family as the same-root guard —
    rather than clobbering that backup or surfacing a raw errno. A migration targets a
    fresh destination root; a second migration into an already-migrated one is a wiring
    mistake with a stated remedy (FR-15).
    """
    try:
        records = [
            {"fingerprint": record.fingerprint, "canonical": record.canonical.decode("utf-8")}
            for record in export.records
        ]
        payload = {
            "world": export.world.value,
            "source_room_role": export.source_room_role.value,
            "format_version": export.format_version,
            "records": records,
        }
        backup_dir.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (OSError, ValueError) as exc:  # pragma: no cover - defensive: the store bytes are UTF-8
        return _corrupt(
            "could not write the pre-migration backup artifact; migration does not proceed "
            "without a backup (AC5)",
            error=str(exc),
            backup_dir=str(backup_dir),
        )
    path = backup_dir / f"{export.world.value}-registry-room.backup.json"
    # A backup artifact is never clobbered and never silently multiplied. The exclusive
    # create below already refuses an existing target, but it does so as a raw OS errno;
    # a destination that ALREADY holds a pre-migration backup is a designed, named
    # refusal instead, in the same `invalid input` / `field: destination` family as the
    # same-root guard: a migration targets a FRESH destination root, so a second
    # migration into one that has already been migrated into is a wiring mistake, not a
    # storage fault (AC5; AR-32; FR-15).
    #
    # Deliberately NOT solved by making the filename unique. A timestamped name would
    # have to read the system clock below the composition root, which FR-002 bans and
    # the ambient-nondeterminism gate fails closed on; an ordinal name would need a
    # directory scan, reintroducing exactly the check-then-create race the exclusive
    # create exists to remove — and both would quietly normalise repeat migrations into
    # a non-fresh destination, which the ratified never-in-place semantics forbid.
    #
    # A symlink at the target is left to `_write_bytes_no_follow`: that is a hostile
    # path, not an already-taken one, and it stays a `storage failure`.
    if not path.is_symlink() and path.exists():
        return _invalid(
            "destination",
            f"a pre-migration backup already exists at {path}; a migration writes its "
            "backup to a fresh destination root and never overwrites an existing backup "
            "artifact. Remove that backup once it is no longer the restore path, or "
            "re-run the migration against a fresh destination root (AC5; AR-32)",
            backup_path=str(path),
            destination_root=str(contain_within),
        )
    written = _write_bytes_no_follow(path, data, contain_within=contain_within)
    if is_refusal(written):
        return written
    return Ok(str(path))


def migrate_registry_format(
    records: Sequence[RegistrationRecord],
    *,
    source: RegistryPersistence,
    destination: RegistryPersistence,
    transform: RecordTransform,
    to_format_version: object,
    backup_sink: BackupSink | None = None,
) -> Result[MigrationReport]:
    """Run the ratified five-stage registry format migration, returning value-or-refusal
    (AC5; AR-32, AR-25).

    **preflight → backup-first → dry-run → migrate → verify**, never in-place:

    * **never-in-place, one world** — ``source`` and ``destination`` must be *distinct*
      store roots (a same-root migration is ``invalid input``, so the only copy is never
      mutated in place; AR-32) **in the same world** (a cross-world migration is a ``policy
      rejection``: a live corpus is never copied into the replay namespace, FM-7).
    * **preflight** — every ``records`` entry must already read back from ``source`` (a
      migration migrates what is stored); a read refusal aborts before anything is written.
    * **backup-first** — the source registry room's restorable export is read AND written to
      a real backup artifact (through ``backup_sink`` or a default file under the destination
      root) before any migrate write; ``backed_up`` reflects that real write and
      ``backup_path`` names it. ``source.root`` is the documented restore path; the source,
      append-only and only read here, stays the intact original. The default sink never
      overwrites an existing backup: a destination root that already holds one is
      ``invalid input`` on ``field: destination``, naming the path and the remedy.
    * **dry-run** — ``transform`` is applied to every record in memory and each result is
      validated as a well-formed record stamping ``to_format_version``; **no writes** occur,
      and any transform refusal aborts with nothing written.
    * **migrate** — each migrated record is persisted to ``destination``; a store refusal
      aborts and no partial migration is claimed complete.
    * **verify** — every migrated record is read back from ``destination`` (its recomputed
      stable id and stamped format version confirmed) and the source originals are confirmed
      still readable and unchanged.

    The procedure migrates **records only** (``records_only`` in the report); CT-07 lineage
    edges are append-only and format-stamped per line and are not transformed here. Every
    serialized artifact stamps its contract format version throughout, so history stays
    readable forever (AR-25).
    """
    if (
        not isinstance(to_format_version, int)
        or isinstance(to_format_version, bool)
        or to_format_version < 1
    ):
        return _invalid(
            "to_format_version",
            "a migration targets a positive integer contract format version (DEC-0103)",
            given=repr(to_format_version),
        )
    if source.root == destination.root:
        return _invalid(
            "destination",
            "a migration never mutates the only copy in place; the source and destination "
            "stores must be distinct roots so the source stays the intact restore path (AR-32)",
            root=str(source.root),
        )
    if source.world != destination.world:
        return _policy(
            "destination",
            "a format migration stays within one world; a cross-world migration would copy "
            "one world's registry evidence into another's namespace (a live corpus into the "
            "replay namespace), which world isolation forbids (FM-7; DEC-0110, DEC-0117)",
            source_world=source.world.value,
            destination_world=destination.world.value,
        )

    # preflight — every record must already read back from the source.
    for record in records:
        key = persistence_fingerprint(record)
        if is_refusal(key):
            return key
        present = source.load_record(key.value, for_world=source.world)
        if is_refusal(present):
            return present
    preflight_count = len(records)

    # backup-first — read the source's restorable export AND write a real backup artifact
    # before any migrate write (backed_up reflects that real write, never a constant; M4).
    export = source.backup_export()
    if is_refusal(export):
        return export
    if backup_sink is not None:
        written = backup_sink(export.value)
    else:
        written = _write_backup_artifact(
            export.value,
            destination.root / "pre-migration-backup",
            contain_within=destination.root,
        )
    if is_refusal(written):
        return written
    backup_path = written.value

    # dry-run — transform every record in memory; validate; write nothing.
    migrated: list[RegistrationRecord] = []
    for record in records:
        result = transform(record)
        if is_refusal(result):
            return result
        # A RecordTransform is *typed* to return a record, but a mistyped transform can
        # return anything at runtime; erase the static type so the guard is real (never a
        # raised AttributeError when the version below is read off a non-record).
        candidate = cast("object", result.value)
        if not isinstance(candidate, RegistrationRecord):
            return _invalid(
                "transform",
                "a migration transform returns a RegistrationRecord",
                given=repr(candidate),
            )
        if candidate.contract_format_version != to_format_version:
            return _invalid(
                "transform",
                "a migrated record stamps the target contract format version so history "
                "stays readable (AR-25)",
                expected=to_format_version,
                given=candidate.contract_format_version,
            )
        migrated.append(candidate)
    dry_run_count = len(migrated)

    # migrate — persist each migrated record to the destination (never the source).
    receipts: list[StoreReceipt] = []
    for candidate in migrated:
        written = destination.persist_record(candidate)
        if is_refusal(written):
            return written
        receipts.append(written.value)

    # verify — read every migrated record back, and confirm the source is unchanged.
    verified = 0
    for candidate in migrated:
        key = persistence_fingerprint(candidate)
        if is_refusal(key):  # pragma: no cover - candidate already persisted, so it is clean
            return key
        loaded = destination.load_record(key.value, for_world=destination.world)
        if is_refusal(loaded):  # pragma: no cover - just written, so it reads back
            return loaded
        if (
            loaded.value.stable_id != candidate.stable_id
            or loaded.value.contract_format_version != to_format_version
        ):  # pragma: no cover - defensive
            return _corrupt("a migrated record did not read back with its stamped identity")
        verified += 1
    for record in records:
        key = persistence_fingerprint(record)
        if is_refusal(key):  # pragma: no cover - preflight already resolved it
            return key
        still = source.load_record(key.value, for_world=source.world)
        if is_refusal(still):  # pragma: no cover - the source is only read, never mutated
            return still

    return Ok(
        MigrationReport(
            restore_path=str(source.root),
            backed_up=True,
            backup_path=backup_path,
            records_only=True,
            preflight_count=preflight_count,
            dry_run_count=dry_run_count,
            migrated_count=len(receipts),
            verified_count=verified,
            to_format_version=to_format_version,
            receipts=tuple(receipts),
        )
    )
