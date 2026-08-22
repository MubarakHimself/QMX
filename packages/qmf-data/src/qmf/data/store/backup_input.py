"""CT-26 — the store-to-backup input boundary (AC1, AC4, AC5).

Presents one room-role's records to the backup primitive as a **consistent,
restorable input, read verbatim and never mutated** (DEC-0118). The backup is an
unlimited reader under one-writer-per-stream; this boundary owns only the input seam,
not the off-machine copy (CT-14), the manifest, or the schedule.

Each exported record carries its fp1 fingerprint and the exact stored canonical bytes,
so a restore is byte-faithful and timestamps pass through verbatim. A cross-world
backup read is a ``policy rejection`` (AC5); an engine failure is a ``storage failure``
refusal (AC4). Stdlib + qmf-core; the engines stay behind their contracts.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from qmf.core import Ok, Result, World, is_refusal
from qmf.data.store.engines import (
    AppendStreamOpener,
    ColumnarEngine,
    MetadataEngine,
    StoreEngineError,
)
from qmf.data.store.receipts import CONTRACT_FORMAT_VERSION
from qmf.data.store.refusals import invalid_input, translate_engine_failure
from qmf.data.store.rooms import RoomRole, require_same_world

__all__ = ["BackupInput", "RecordExport", "RoomExport"]


@dataclass(frozen=True, slots=True)
class RecordExport:
    """One record handed to the backup primitive, verbatim.

    ``fingerprint`` is the fp1 string that keys it and ``canonical`` the exact stored
    identity bytes — a restore rewrites these unchanged (DEC-0106, DEC-0118).
    """

    fingerprint: str
    canonical: bytes


@dataclass(frozen=True, slots=True)
class RoomExport:
    """One room-role's contents for one world, presented to the backup primitive."""

    world: World
    source_room_role: RoomRole
    format_version: int
    records: tuple[RecordExport, ...]

    @property
    def record_count(self) -> int:
        """The number of records in this export."""
        return len(self.records)


def _fp1(digest: str) -> str:
    """The self-describing fp1 string for a digest."""
    return f"fp1:sha256:{digest}"


class BackupInput:
    """The CT-26 store-to-backup input for one world (read-only, verbatim)."""

    def __init__(
        self,
        world: World,
        *,
        raw_engine: ColumnarEngine,
        record_engine: MetadataEngine,
        journal_dir: Path,
        lineage_dir: Path,
        open_stream: AppendStreamOpener,
    ) -> None:
        self._world = world
        self._raw = raw_engine
        self._records = record_engine
        self._journal_dir = journal_dir
        self._lineage_dir = lineage_dir
        self._open = open_stream

    def read_room(self, room_role: object, *, for_world: object) -> Result[RoomExport]:
        """Present ``room_role``'s records verbatim; a cross-world backup read refuses.

        ``for_world`` is required (M4). The evidence rooms (immutable raw archive,
        journal) and the registry room (records + lineage edges) are exported; the
        rebuildable and not-yet-populated rooms export empty in V1. Any engine or
        filesystem failure is a ``storage failure`` refusal, never raised across the
        seam (L1, AC4).
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        role = _coerce_role(room_role)
        if role is None:
            return invalid_input(
                "room_role",
                "room_role is one of the seven room-roles",
                given=repr(room_role),
                allowed=[member.value for member in RoomRole],
            )
        try:
            records = self._records_for(role)
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        return Ok(
            RoomExport(
                world=self._world,
                source_room_role=role,
                format_version=CONTRACT_FORMAT_VERSION,
                records=records,
            )
        )

    def _records_for(self, role: RoomRole) -> tuple[RecordExport, ...]:
        """Gather one room-role's verbatim records (may raise StoreEngineError)."""
        if role is RoomRole.IMMUTABLE_RAW_ARCHIVE:
            return self._export_raw()
        if role is RoomRole.JOURNAL:
            return self._export_streams(self._journal_dir)
        if role is RoomRole.REGISTRY_ROOM:
            return (*self._export_registry_records(), *self._export_streams(self._lineage_dir))
        return ()

    def _export_raw(self) -> tuple[RecordExport, ...]:
        """Every raw-archive artifact's fp1 + embedded canonical bytes, verbatim."""
        exports: list[RecordExport] = []
        for key in self._raw.stored_keys():
            canonical = self._raw.read_canonical(key)
            if canonical is not None:
                exports.append(RecordExport(fingerprint=_fp1(key), canonical=canonical))
        return tuple(sorted(exports, key=lambda record: record.fingerprint))

    def _export_registry_records(self) -> tuple[RecordExport, ...]:
        """Every registry record's fp1 + stored canonical bytes, verbatim."""
        exports: list[RecordExport] = []
        for digest in self._records.digests():
            canonical = self._records.get(digest)
            if canonical is not None:
                exports.append(RecordExport(fingerprint=_fp1(digest), canonical=canonical))
        return tuple(exports)

    def _export_streams(self, base_dir: Path) -> tuple[RecordExport, ...]:
        """Every line of every stream under ``base_dir``, verbatim in stream order.

        Directory enumeration is guarded: a filesystem ``OSError`` (a locked or
        vanished room directory) is normalized to a ``StoreEngineError`` so the
        boundary translates it to a ``storage failure`` refusal rather than letting a
        bare ``OSError`` cross the seam (L1, AC4).
        """
        try:
            if not base_dir.is_dir():
                return ()
            children = sorted(base_dir.iterdir())
        except OSError as exc:
            raise StoreEngineError(
                "could not enumerate the room's streams for backup",
                engine="jsonl",
                retryable=False,
                detail={"room": str(base_dir), "os_error": str(exc)},
            ) from exc
        exports: list[RecordExport] = []
        for sub in children:
            if not sub.is_dir():
                continue
            reader = self._open(sub, "<backup>")
            reader.rebuild_index()
            for line in reader.read_all():
                digest = hashlib.sha256(line).hexdigest()
                exports.append(RecordExport(fingerprint=_fp1(digest), canonical=line))
        return tuple(exports)


def _coerce_role(value: object) -> RoomRole | None:
    """Resolve a :class:`RoomRole` or its string value, or ``None``."""
    if isinstance(value, RoomRole):
        return value
    if isinstance(value, str):
        try:
            return RoomRole(value)
        except ValueError:
            return None
    return None
