"""CT-09 — the per-world registry-room persistence boundary (AC1, AC2, AC5).

The registry room is one of the seven room-roles, reached through the single ratified
inter-library edge ``qmf-registry → qmf-data`` (qmf-data never imports qmf-registry).
It accepts two shapes, under the same retention/backup/migration law as every room:

* **per-kind versioned records**, fp1-keyed, physically SQLite (transactional
  metadata), append-only — a record is never rewritten in place; a correction is a new
  record with a new fp1 and a lineage edge; and
* **pinned-JSONL lineage edges**, append-only one-writer streams.

Every artifact is keyed on its fp1 fingerprint (never a timestamp or minted id): a
byte-identical re-write is idempotent, a true collision is refused and alarmed (AC2).
A ``world = simulated`` write and a cross-world read are each a ``policy rejection``
(AC5). Engine failures are translated to ``storage failure`` refusals at this boundary
(AC4). Stdlib + qmf-core; the SQLite / JSONL engines never appear in a signature.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from qmf.core import Ok, Result, World, WriterId, canonical_bytes, is_refusal
from qmf.data.store.engines import (
    AppendStreamOpener,
    MetadataEngine,
    OccurrenceSink,
    StoreEngineError,
)
from qmf.data.store.identity import admit, resolve_fingerprint
from qmf.data.store.receipts import StoreReceipt
from qmf.data.store.refusals import invalid_input, missing_artifact, translate_engine_failure
from qmf.data.store.rooms import RoomRole, namespace_block, require_same_world
from qmf.data.store.streams import HeldStreams, safe_segment

__all__ = ["RegistryRoom"]


class RegistryRoom:
    """The CT-09 registry room for one world — SQLite records + JSONL lineage edges.

    The lineage append-stream engine is injected as ``open_stream`` (an
    :class:`~qmf.data.store.engines.AppendStreamOpener`), so the concrete JSONL engine
    never appears in this boundary's signature and stays swappable (M3).
    """

    def __init__(
        self,
        world: World,
        *,
        record_engine: MetadataEngine,
        lineage_dir: Path,
        open_stream: AppendStreamOpener,
    ) -> None:
        self._world = world
        self._records = record_engine
        self._lineage = HeldStreams(lineage_dir, open_stream=open_stream)

    @property
    def world(self) -> World:
        """The world whose registry room this boundary writes and reads."""
        return self._world

    def close(self) -> None:
        """Release every held lineage-edge stream's one-writer lock (M6)."""
        self._lineage.release_all()

    # --- per-kind versioned records (SQLite) --------------------------------

    def put_record(
        self,
        record: Mapping[str, object],
        *,
        kind: object,
        format_version: object,
        presented_fingerprint: object | None = None,
    ) -> Result[StoreReceipt]:
        """Persist a per-kind versioned record, fp1-keyed and append-only (AC2, AC5).

        ``kind`` names the registry kind; ``format_version`` is the record's positive
        integer contract format version. The fp1 identity is computed over the **full**
        record — the body plus its ``kind`` and ``format_version`` — per CT-05's
        identity-by-default law, so the same body under a different kind or format
        version is a *different* fingerprint and a *distinct* stored record, never a
        silent idempotent collapse (H6, DEC-0108). The receipt echoes the actual stored
        ``format_version``. A byte-identical re-write is idempotent, a true collision is
        refused and alarmed; a ``world = simulated`` write is a ``policy rejection``; an
        engine failure is a ``storage failure`` refusal.
        """
        blocked = namespace_block(self._world)
        if blocked is not None:
            return blocked
        if not isinstance(kind, str) or kind.strip() == "":
            return invalid_input(
                "kind", "a registry record names a non-empty kind", given=repr(kind)
            )
        if (
            isinstance(format_version, bool)
            or not isinstance(format_version, int)
            or format_version < 1
        ):
            return invalid_input(
                "format_version",
                "a record's contract format version is a positive integer (DEC-0103)",
                given=repr(format_version),
            )
        engine = self._records
        version = format_version
        record_kind = kind
        # The stored artifact is the full record: kind and format_version are inside the
        # fingerprinted identity, so they can never sit outside it and let two distinct
        # records alias (H6). The body nests under "body", so a body key named "kind" or
        # "format_version" never collides with the envelope's fields.
        full_record: dict[str, object] = {
            "kind": record_kind,
            "format_version": version,
            "body": dict(record),
        }
        try:
            admission = admit(
                full_record,
                existing_bytes=engine.get,
                persist=lambda fp, canonical: engine.put(
                    fp.digest, canonical, kind=record_kind, format_version=version
                ),
                presented_fingerprint=presented_fingerprint,
            )
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if is_refusal(admission):
            return admission
        admitted = admission.value
        return Ok(
            StoreReceipt(
                outcome=admitted.outcome,
                fingerprint=admitted.fingerprint,
                world=self._world,
                room_role=RoomRole.REGISTRY_ROOM,
                engine="sqlite",
                is_evidence_bearing=True,
                retained_forever=True,
                format_version=version,
            )
        )

    def put_identity_record(
        self,
        identity: Mapping[str, object],
        *,
        kind: object,
        format_version: object,
        occurrence: Mapping[str, object] | None = None,
        presented_fingerprint: object | None = None,
    ) -> Result[StoreReceipt]:
        """Persist a record keyed on its OWN fp1 identity, append-only (AC2, AC5; CT-09).

        Unlike :meth:`put_record`, the fp1 key is computed over ``identity`` **exactly** — a
        record's full CT-06 fp1 identity content, whose fingerprint IS the record's stable id
        — so the storage key is the record's fp1 stable id, never a second wrapping
        fingerprint (CT-09 ``record_stable_id`` is the storage key; DEC-0108). ``kind`` and
        ``format_version`` are still recorded as the engine's metadata columns and echoed on
        the receipt. ``occurrence``, when present and the engine supports it
        (:class:`~qmf.data.store.engines.OccurrenceSink`), is stored in a display-only
        per-record sidecar (writer, per-writer sequence, created-at) keyed by the record's
        digest and **excluded from identity**, first-write-wins so an idempotent dedup never
        collides (M5; DEC-0110). Idempotent/collision, ``world = simulated``/cross-world, and
        storage-failure semantics all match :meth:`put_record`.
        """
        blocked = namespace_block(self._world)
        if blocked is not None:
            return blocked
        if not isinstance(kind, str) or kind.strip() == "":
            return invalid_input(
                "kind", "a registry record names a non-empty kind", given=repr(kind)
            )
        if (
            isinstance(format_version, bool)
            or not isinstance(format_version, int)
            or format_version < 1
        ):
            return invalid_input(
                "format_version",
                "a record's contract format version is a positive integer (DEC-0103)",
                given=repr(format_version),
            )
        engine = self._records
        version = format_version
        record_kind = kind
        try:
            admission = admit(
                dict(identity),
                existing_bytes=engine.get,
                persist=lambda fp, canonical: engine.put(
                    fp.digest, canonical, kind=record_kind, format_version=version
                ),
                presented_fingerprint=presented_fingerprint,
            )
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if is_refusal(admission):
            return admission
        admitted = admission.value
        if occurrence is not None and isinstance(engine, OccurrenceSink):
            serialized = canonical_bytes(dict(occurrence))
            if is_refusal(serialized):
                return serialized
            try:
                engine.put_occurrence(admitted.fingerprint.digest, serialized.value)
            except StoreEngineError as exc:
                return translate_engine_failure(exc)
        return Ok(
            StoreReceipt(
                outcome=admitted.outcome,
                fingerprint=admitted.fingerprint,
                world=self._world,
                room_role=RoomRole.REGISTRY_ROOM,
                engine="sqlite",
                is_evidence_bearing=True,
                retained_forever=True,
                format_version=version,
            )
        )

    def get_record(self, fingerprint: object, *, for_world: object) -> Result[bytes]:
        """The canonical bytes of the full record by fp1 fingerprint; cross-world refuses.

        ``for_world`` is required (M4). A well-formed fingerprint that no record is
        stored under is a ``stale evidence`` not-found refusal, not ``invalid input`` —
        the fingerprint parsed, the reference is simply absent (M5). The returned bytes
        are the full record envelope (kind + format_version + body) the write stored (H6).
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        key = resolve_fingerprint(fingerprint)
        if is_refusal(key):
            return key
        try:
            stored = self._records.get(key.value.digest)
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if stored is None:
            return missing_artifact(
                "fingerprint",
                "no registry record is stored under this fingerprint",
                given=key.value.value,
            )
        return Ok(stored)

    def get_record_occurrence(
        self, fingerprint: object, *, for_world: object
    ) -> Result[Mapping[str, object] | None]:
        """The display-only occurrence facts stored for a record, or ``None`` (M5; AC5).

        ``for_world`` is required; a cross-world read is a ``policy rejection``. A well-formed
        fingerprint with no occurrence sidecar — a record persisted without occurrence facts,
        or an engine that does not support the sidecar — reads back ``Ok(None)``: absence is a
        normal answer, not a failure. The facts (writer, per-writer sequence, created-at) are
        display-only and were never part of the record's fp1 identity (DEC-0110).
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        key = resolve_fingerprint(fingerprint)
        if is_refusal(key):
            return key
        engine = self._records
        if not isinstance(engine, OccurrenceSink):
            return Ok(None)
        try:
            raw = engine.get_occurrence(key.value.digest)
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if raw is None:
            return Ok(None)
        try:
            decoded: object = json.loads(raw)
        except ValueError:  # pragma: no cover - occurrence writes are canonical by construction
            return Ok(None)
        if not isinstance(decoded, dict):  # pragma: no cover - defensive
            return Ok(None)
        return Ok(cast("dict[str, object]", decoded))

    # --- pinned-JSONL lineage edges -----------------------------------------

    def append_lineage_edge(
        self,
        edge_stream: object,
        writer: WriterId,
        edge: Mapping[str, object],
        *,
        presented_fingerprint: object | None = None,
    ) -> Result[StoreReceipt]:
        """Append a lineage edge to a one-writer pinned-JSONL stream (AC2, AC5).

        Lineage accrues after a record's birth and lives only in append-only edges — a
        record is never rewritten in place to add lineage (DEC-0114). One-writer,
        idempotent re-append, simulated/cross-world refusals, and storage-failure
        translation all hold exactly as for the journal.
        """
        blocked = namespace_block(self._world)
        if blocked is not None:
            return blocked
        name = safe_segment(edge_stream, field="edge_stream")
        if is_refusal(name):
            return name
        acquired = self._lineage.acquire(name.value, writer)
        if is_refusal(acquired):
            return acquired
        stream = acquired.value
        try:
            admission = admit(
                dict(edge),
                existing_bytes=stream.find,
                persist=lambda _fp, canonical: _discard(stream.append(canonical)),
                presented_fingerprint=presented_fingerprint,
            )
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if is_refusal(admission):
            return admission
        admitted = admission.value
        location = stream.location_of(admitted.fingerprint.digest)
        return Ok(
            StoreReceipt(
                outcome=admitted.outcome,
                fingerprint=admitted.fingerprint,
                world=self._world,
                room_role=RoomRole.REGISTRY_ROOM,
                engine="jsonl",
                is_evidence_bearing=True,
                retained_forever=True,
                sequence=location.sequence if location is not None else None,
            )
        )

    def lineage_stream_names(self, *, for_world: object) -> Result[tuple[str, ...]]:
        """Every lineage-edge stream name present in this room; a cross-world read refuses.

        ``for_world`` is required (M4) — a cross-world read is a ``policy rejection``. Returns
        the canonical names of every edge stream ever written in this room (an empty tuple
        when none exist yet), so a caller enforcing a **room-wide** invariant over the CT-07
        supersedes chain can read every stream, not only a single named one. Enumeration only;
        each stream's edges are read through :meth:`read_lineage`.
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        return Ok(self._lineage.stream_names())

    def read_lineage(
        self, edge_stream: object, *, for_world: object
    ) -> Result[list[dict[str, object]]]:
        """Read a lineage-edge stream in order; a cross-world read refuses (AC5).

        ``for_world`` is required (M4). A never-written edge stream reads as ``Ok([])``
        (lazily created). A corrupt edge line is a ``storage failure`` refusal, never a
        raw decode error across the seam (H3, AC4).
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        name = safe_segment(edge_stream, field="edge_stream")
        if is_refusal(name):
            return name
        reader = self._lineage.reader(name.value)
        if reader is None:
            return Ok([])
        try:
            reader.rebuild_index()
            edges = [_load(line) for line in reader.read_all()]
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        return Ok(edges)


def _discard(_location: object) -> None:
    """Swallow the append location the persist callback does not surface."""


def _load(line: bytes) -> dict[str, object]:
    """Parse one canonical JSONL edge line back to a dict."""
    decoded: object = json.loads(line)
    if isinstance(decoded, dict):
        return cast("dict[str, object]", decoded)
    return {"_value": decoded}
