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

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from qmf.core import Ok, Result, TypedRefusal, World, fingerprint_bytes, is_refusal
from qmf.data.store.engines import (
    AppendStreamOpener,
    ColumnarEngine,
    MetadataEngine,
    StoreEngineError,
)
from qmf.data.store.receipts import CONTRACT_FORMAT_VERSION
from qmf.data.store.refusals import invalid_input, translate_engine_failure
from qmf.data.store.rooms import (
    ReadSeal,
    RoomRole,
    guard_derived_content,
    guard_sealed_read,
    require_same_world,
)

__all__ = ["BackupInput", "RecordExport", "RoomExport"]

# The CT-12 read-boundary name a restored-backup read is guarded at (DEC-0119). A plain
# string so the dependency-free store seam never imports the ReadBoundary enum; it is the
# pinned ReadBoundary value and the seal coerces it back (M3).
_RESTORED_BACKUP_BOUNDARY = "restored backup"


@dataclass(frozen=True, slots=True)
class RecordExport:
    """One record handed to the backup primitive, verbatim.

    ``fingerprint`` is the fp1 string that keys it and ``canonical`` the exact stored
    identity bytes — a restore rewrites these unchanged (DEC-0106, DEC-0118).
    ``stream`` carries the JSONL stream segment for journal / lineage-backed records so
    a restore can re-append under the same stream name; raw and registry-record exports
    leave it ``None``.
    """

    fingerprint: str
    canonical: bytes
    stream: str | None = None


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
        seal: ReadSeal | None = None,
    ) -> None:
        self._world = world
        self._raw = raw_engine
        self._records = record_engine
        self._journal_dir = journal_dir
        self._lineage_dir = lineage_dir
        self._open = open_stream
        self._seal = seal

    def read_room(
        self, room_role: object, *, for_world: object, at: object | None = None
    ) -> Result[RoomExport]:
        """Present ``room_role``'s records verbatim; a cross-world backup read refuses.

        ``for_world`` is required (M4). The evidence rooms (immutable raw archive,
        journal) and the registry room (records + lineage edges) are exported; the
        rebuildable and not-yet-populated rooms export empty in V1. Any engine or
        filesystem failure is a ``storage failure`` refusal, never raised across the
        seam (L1, AC4).

        A restored-backup read still enforces the no-peek seal exactly as a live read
        does, consulted on **every** read (DEC-0119): a read declaring a knowledge position
        ``at`` that reaches into the sealed window is a ``policy rejection`` at the
        restored-backup boundary — never a silent empty result — and a read that declares
        **no** ``at`` while a seal is wired is *also* refused (fail-closed), since a
        positionless read cannot be proven outside the sealed window and must never export
        the sealed bytes verbatim (AC4). The declared ``at`` alone is bypassable by
        under-statement, so the seal is additionally guarded at the position derived from
        the exported records' own content (their canonical JSON event-times) before the
        export is returned; records carrying no derivable event-time contribute nothing.
        """
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        sealed = guard_sealed_read(self._seal, at, boundary=_RESTORED_BACKUP_BOUNDARY)
        if sealed is not None:
            return sealed
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
        content_sealed = self._guard_export_content(records)
        if content_sealed is not None:
            return content_sealed
        return Ok(
            RoomExport(
                world=self._world,
                source_room_role=role,
                format_version=CONTRACT_FORMAT_VERSION,
                records=records,
            )
        )

    def _guard_export_content(self, records: tuple[RecordExport, ...]) -> TypedRefusal | None:
        """Guard a wired seal at the position derived from the exported bytes (AC4; DEC-0119).

        Each record's canonical bytes are stored JSON; the derivable event-times inside
        them (row ``t`` values, series-envelope window ends and nested rows) are the
        content the export would hand out, so the seal is guarded at their latest —
        exactly the store-level derivation the raw and processed reads use. A record
        whose bytes do not parse as JSON rows (journal control lines, registry records)
        contributes nothing; with no wired seal this is a pass.
        """
        if self._seal is None:
            return None
        rows: list[object] = []
        for record in records:
            try:
                parsed: object = json.loads(record.canonical)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(parsed, list):
                rows.extend(cast("list[object]", parsed))
            elif isinstance(parsed, dict):
                rows.append(cast("dict[str, object]", parsed))
        return guard_derived_content(self._seal, rows, boundary=_RESTORED_BACKUP_BOUNDARY)

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
                exports.append(
                    RecordExport(
                        fingerprint=fingerprint_bytes(canonical).value, canonical=canonical
                    )
                )
        return tuple(sorted(exports, key=lambda record: record.fingerprint))

    def _export_registry_records(self) -> tuple[RecordExport, ...]:
        """Every registry record's fp1 + stored canonical bytes, verbatim."""
        exports: list[RecordExport] = []
        for digest in self._records.digests():
            canonical = self._records.get(digest)
            if canonical is not None:
                exports.append(
                    RecordExport(
                        fingerprint=fingerprint_bytes(canonical).value, canonical=canonical
                    )
                )
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
                exports.append(
                    RecordExport(
                        fingerprint=fingerprint_bytes(line).value,
                        canonical=line,
                        stream=sub.name,
                    )
                )
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
