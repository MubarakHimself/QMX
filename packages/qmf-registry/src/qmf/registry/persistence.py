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
is content-addressed. A record's persistence key is the store's fp1 fingerprint over the
CT-09 persisted envelope — the kind, the per-kind contract format version, and the
record's **full CT-06 fp1 identity content** — computed only by ``qmf-core``; it is a
pure function of the record's stable identity (:func:`persistence_fingerprint`), so the
same record from two sandboxes lands on one key and dedups by construction, and no
occurrence fact (writer, sequence, created-at) enters it. A lineage edge is persisted
under **its own** CT-07 ``fp1`` edge fingerprint exactly: the store fingerprints the
edge's identity content directly and this module presents the edge fingerprint, so the
storage key IS the edge's fp1 stable id. A byte-identical re-write is accepted silently
(idempotent); a true collision (one fp1 addressing differing bytes) is refused and
alarmed at the store boundary, never overwritten.

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
backup-first → dry-run → migrate → verify — from a source persistence to a **distinct**
destination (a same-root migration is refused), so the only copy is never mutated in
place and the source store IS the documented restore path. Every serialized registry
artifact stamps its contract format version (the store receipt echoes it and the fp1
identity carries it), so history stays readable forever.

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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from qmf.core import (
    Fingerprint,
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
from qmf.registry.lineage import LineageEdge
from qmf.registry.records import RegistrationRecord

__all__ = [
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


# --- the persisted record identity view -------------------------------------


@dataclass(frozen=True, slots=True)
class LoadedRecord:
    """A CT-06 record read back from the per-world registry room (AC6; DEC-0114).

    The identity-bearing view of a persisted record: ``kind``, the per-kind
    ``contract_format_version``, the canonically-ordered ``at_birth_parent_refs``, the
    kind-specific ``body``, the CT-06 envelope ``format_version``, and the derived
    ``stable_id`` — recomputed on read and asserted equal to the original's. The
    occurrence facts (writer, per-writer sequence, created-at) are **display-only and
    excluded from identity**, so they are deliberately not part of the identity-keyed
    persisted record — a record deduplicates on identity alone, and its occurrence
    evidence rides the CT-13 journal, never the record store (DEC-0110, DEC-0114).
    ``persisted_fingerprint`` is the store's content-addressed key the record was read
    under.
    """

    kind: str
    contract_format_version: int
    at_birth_parent_refs: tuple[Fingerprint, ...]
    body: Mapping[str, object]
    format_version: int
    stable_id: Fingerprint
    persisted_fingerprint: Fingerprint


# --- content-addressed key derivation ---------------------------------------


def _record_envelope(record: RegistrationRecord) -> dict[str, object]:
    """The CT-09 persisted envelope for a record — kind + version + fp1 identity content.

    The store fingerprints and stores exactly this whole envelope (H6): the record's kind
    and per-kind contract format version sit *outside* the body so two distinct records
    can never alias, and the body is the record's **full CT-06 fp1 identity content**
    (:meth:`~qmf.registry.RegistrationRecord.fp1_identity`) so every identity field —
    the at-birth parent references included — is captured and no occurrence fact leaks in.
    """
    return {
        "kind": record.kind,
        "format_version": record.contract_format_version,
        "body": record.fp1_identity(),
    }


def persistence_fingerprint(record: object) -> Result[Fingerprint]:
    """The content-addressed store key a record persists under, or a refusal (AC2).

    A pure function of the record's stable identity, computed only through ``qmf-core``:
    the ``fp1`` fingerprint of the CT-09 persisted envelope (:func:`_record_envelope`).
    A caller derives it from a record to read the record back without holding the persist
    receipt — it never depends on a timestamp, a writer, a sequence, or a minted id, so
    identical work from two sandboxes derives one key (DEC-0108). A non-record argument is
    an ``invalid input`` refusal.
    """
    if not isinstance(record, RegistrationRecord):
        return _invalid(
            "record",
            "a persistence key is derived for a RegistrationRecord",
            given=repr(record),
        )
    return fingerprint(_record_envelope(record))


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
        registry room as the persisted body, keyed on the content-addressed store
        fingerprint (:func:`persistence_fingerprint`). A first write is ``stored``, a
        byte-identical re-write is ``idempotent`` and accepted silently (identical work
        from two sandboxes dedups), and a true collision is refused and alarmed. A
        ``world = simulated`` room, an underlying store failure, and a corrupt engine are
        surfaced as the store's own typed refusals — never raised across the seam. A
        non-record argument is an ``invalid input`` refusal.
        """
        if not isinstance(record, RegistrationRecord):
            return _invalid(
                "record",
                "persistence writes a RegistrationRecord (the CT-06 per-kind record)",
                given=repr(record),
            )
        return self._ws.registry_room.put_record(
            record.fp1_identity(),
            kind=record.kind,
            format_version=record.contract_format_version,
        )

    def load_record(self, key: object, *, for_world: object) -> Result[LoadedRecord]:
        """Read a persisted record back as its CT-06 identity, returning value-or-refusal
        (AC3, AC6).

        ``key`` is the record's content-addressed persistence fingerprint (a
        :class:`~qmf.core.Fingerprint` or ``fp1:sha256:<hex>`` string), from a persist
        receipt or :func:`persistence_fingerprint`. ``for_world`` is required — a read
        that crosses worlds is a ``policy rejection`` (M4; FM-7). A well-formed key that
        names nothing is a ``stale evidence`` refusal; a malformed key an ``invalid
        input`` refusal; a corrupt stored artifact a ``storage failure`` refusal. The
        recomputed ``fp1`` stable id is asserted equal to the original's, so a silently
        altered record can never read back as valid.
        """
        got = self._ws.registry_room.get_record(key, for_world=for_world)
        if is_refusal(got):
            return got
        resolved_key = _coerce_fingerprint(key)
        if resolved_key is None:  # pragma: no cover - get_record already parsed the key
            return _invalid("key", "a persistence key is an fp1 fingerprint", given=repr(key))
        return _reconstruct_record(resolved_key, got.value)

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
        """
        if not isinstance(edge, LineageEdge):
            return _invalid(
                "edge",
                "persistence appends a LineageEdge (the CT-07 typed lineage edge)",
                given=repr(edge),
            )
        return self._ws.registry_room.append_lineage_edge(
            edge_stream,
            edge.writer,
            edge.fp1_identity(),
            presented_fingerprint=edge.edge_fingerprint,
        )

    def read_edges(
        self, edge_stream: object, *, for_world: object
    ) -> Result[tuple[LineageEdge, ...]]:
        """Read a lineage-edge stream back as CT-07 edges, in append order (AC3, AC6).

        ``for_world`` is required — a read that crosses worlds is a ``policy rejection``
        (M4; FM-7). A never-written stream reads as an empty tuple (streams are lazily
        created). Every line reconstructs a full :class:`~qmf.registry.LineageEdge` —
        edges carry no occurrence-only fields, so the round trip is total — and each
        recomputed edge fingerprint is asserted equal, so a corrupt line is a ``storage
        failure`` refusal, never a silently wrong edge. A bad stream name is an ``invalid
        input`` refusal (surfaced by the store).
        """
        raw = self._ws.registry_room.read_lineage(edge_stream, for_world=for_world)
        if is_refusal(raw):
            return raw
        edges: list[LineageEdge] = []
        for line in raw.value:
            rebuilt = _reconstruct_edge(line)
            if is_refusal(rebuilt):
                return rebuilt
            edges.append(rebuilt.value)
        return Ok(tuple(edges))


# --- record / edge reconstruction (the read round trip) ---------------------


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
    """Reconstruct a :class:`LoadedRecord` from a persisted record envelope (AC6).

    Parses the ``{kind, format_version, body}`` envelope, extracts the record's CT-06 fp1
    identity content (the ``body``), recomputes the ``fp1`` stable id from it, and returns
    the identity view. A shape the writer could never have produced is corrupt stored
    evidence, surfaced as a ``storage failure`` refusal (AC4).
    """
    envelope = _load_object(raw)
    if is_refusal(envelope):  # pragma: no cover - defensive
        return envelope
    identity_obj = envelope.value.get("body")
    if not isinstance(identity_obj, dict):  # pragma: no cover - defensive
        return _corrupt("a persisted record envelope carries no identity body")
    identity = cast("dict[str, object]", identity_obj)
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
    derived = fingerprint(identity)
    if is_refusal(derived):  # pragma: no cover - defensive: identity content is fp1-clean
        return _corrupt("a persisted record identity is not fp1-clean")
    return Ok(
        LoadedRecord(
            kind=kind,
            contract_format_version=version,
            at_birth_parent_refs=tuple(refs),
            body=cast("Mapping[str, object]", body_obj),
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


@dataclass(frozen=True, slots=True)
class MigrationReport:
    """The outcome of a staged registry format migration (AC5; AR-32, AR-25).

    ``restore_path`` is the source store root — untouched by the migration, so it is the
    documented path a restore reads from. ``backed_up`` records that the source's
    restorable backup input was read before any write. ``preflight_count`` /
    ``dry_run_count`` / ``migrated_count`` / ``verified_count`` are the per-stage tallies,
    and ``to_format_version`` the target contract format version every migrated artifact
    now stamps. ``receipts`` are the destination store receipts, each echoing its stamped
    format version.
    """

    restore_path: str
    backed_up: bool
    preflight_count: int
    dry_run_count: int
    migrated_count: int
    verified_count: int
    to_format_version: int
    receipts: tuple[StoreReceipt, ...]


def migrate_registry_format(
    records: Sequence[RegistrationRecord],
    *,
    source: RegistryPersistence,
    destination: RegistryPersistence,
    transform: RecordTransform,
    to_format_version: object,
) -> Result[MigrationReport]:
    """Run the ratified five-stage registry format migration, returning value-or-refusal
    (AC5; AR-32, AR-25).

    **preflight → backup-first → dry-run → migrate → verify**, never in-place:

    * **never-in-place** — ``source`` and ``destination`` must be *distinct* store roots;
      a same-root migration is refused (``invalid input``), so the only copy is never
      mutated in place (AR-32).
    * **preflight** — every ``records`` entry must already read back from ``source`` (a
      migration migrates what is stored); a read refusal aborts before anything is written.
    * **backup-first** — the source registry room is read through its restorable backup
      input before any write, and ``source.root`` is recorded as the restore path; the
      source, being append-only and only read here, remains the intact original.
    * **dry-run** — ``transform`` is applied to every record in memory and each result is
      validated as a well-formed record stamping ``to_format_version``; **no writes** occur,
      and any transform refusal aborts with nothing written.
    * **migrate** — each migrated record is persisted to ``destination``; a store refusal
      aborts and no partial migration is claimed complete.
    * **verify** — every migrated record is read back from ``destination`` (its recomputed
      stable id and stamped format version confirmed) and the source originals are confirmed
      still readable and unchanged.

    Every serialized artifact stamps its contract format version throughout, so history
    stays readable forever (AR-25).
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

    # preflight — every record must already read back from the source.
    for record in records:
        key = persistence_fingerprint(record)
        if is_refusal(key):
            return key
        present = source.load_record(key.value, for_world=source.world)
        if is_refusal(present):
            return present
    preflight_count = len(records)

    # backup-first — read the source's restorable backup input before any write.
    export = source.backup_export()
    if is_refusal(export):
        return export

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
            preflight_count=preflight_count,
            dry_run_count=dry_run_count,
            migrated_count=len(receipts),
            verified_count=verified,
            to_format_version=to_format_version,
            receipts=tuple(receipts),
        )
    )
