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

from qmf.core import Ok, Result, World, WriterId, is_refusal
from qmf.data.store.engines import MetadataEngine, StoreEngineError
from qmf.data.store.engines.jsonl import DEFAULT_ROTATION_BYTES
from qmf.data.store.identity import admit, resolve_fingerprint
from qmf.data.store.receipts import StoreReceipt
from qmf.data.store.refusals import invalid_input, translate_engine_failure
from qmf.data.store.rooms import RoomRole, namespace_block, require_same_world
from qmf.data.store.streams import HeldStreams, safe_segment

__all__ = ["RegistryRoom"]


class RegistryRoom:
    """The CT-09 registry room for one world — SQLite records + JSONL lineage edges."""

    def __init__(
        self,
        world: World,
        *,
        record_engine: MetadataEngine,
        lineage_dir: Path,
        rotation_bytes: int = DEFAULT_ROTATION_BYTES,
    ) -> None:
        self._world = world
        self._records = record_engine
        self._lineage = HeldStreams(lineage_dir, rotation_bytes=rotation_bytes)

    @property
    def world(self) -> World:
        """The world whose registry room this boundary writes and reads."""
        return self._world

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
        integer contract format version. A byte-identical re-write is idempotent, a
        true collision is refused and alarmed; a ``world = simulated`` write is a
        ``policy rejection``; an engine failure is a ``storage failure`` refusal.
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
                dict(record),
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
            )
        )

    def get_record(self, fingerprint: object, *, for_world: object | None = None) -> Result[bytes]:
        """The canonical bytes of a record by fp1 fingerprint; a cross-world read refuses."""
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
            return invalid_input(
                "fingerprint",
                "no registry record is stored under this fingerprint",
                given=key.value.value,
            )
        return Ok(stored)

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

    def read_lineage(
        self, edge_stream: object, *, for_world: object | None = None
    ) -> Result[list[dict[str, object]]]:
        """Read a lineage-edge stream in order; a cross-world read refuses (AC5)."""
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
            lines = reader.read_all()
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        return Ok([_load(line) for line in lines])


def _discard(_location: object) -> None:
    """Swallow the append location the persist callback does not surface."""


def _load(line: bytes) -> dict[str, object]:
    """Parse one canonical JSONL edge line back to a dict."""
    decoded: object = json.loads(line)
    if isinstance(decoded, dict):
        return cast("dict[str, object]", decoded)
    return {"_value": decoded}
