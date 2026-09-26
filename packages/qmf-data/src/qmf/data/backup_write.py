"""Restore writers that re-admit a CT-26 export into a replacement store."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final, cast

from qmf.core import Ok, Result, WriterId, is_refusal
from qmf.data.backup_storage import storage_failure
from qmf.data.store.backup_input import RecordExport, RoomExport
from qmf.data.store.facade import WorldStore
from qmf.data.store.receipts import StoreReceipt
from qmf.data.store.refusals import invalid_input
from qmf.data.store.rooms import RoomRole

# Writer identity used when re-appending journal / lineage lines during restore.
# The acquired stream name (not this token's stream field) owns the one-writer hold.
_RESTORE_MACHINE: Final[str] = "qmf-restore"
_RESTORE_ROLE: Final[str] = "backup"
_RESTORE_BOOT: Final[str] = "restore-1"


def write_export(export: RoomExport, bundle: WorldStore) -> Result[int]:
    """Persist every record of ``export`` into ``bundle``; return the written count."""
    role = export.source_room_role
    if role is RoomRole.IMMUTABLE_RAW_ARCHIVE:
        return restore_raw(export.records, bundle)
    if role is RoomRole.REGISTRY_ROOM:
        return restore_registry(export.records, bundle)
    if role is RoomRole.JOURNAL:
        return restore_journal(export.records, bundle)
    # Rebuildable / unpopulated rooms export empty in V1 — nothing to write.
    if export.record_count == 0:
        return Ok(0)
    return invalid_input(
        "source_room_role",
        "this room-role has no restore writer in V1; only the immutable raw archive, "
        "journal, and registry room are restored from a CT-26 export",
        given=role.value,
    )


def restore_raw(records: tuple[RecordExport, ...], bundle: WorldStore) -> Result[int]:
    """Re-admit raw-archive artifacts from verbatim canonical bytes."""
    count = 0
    for record in records:
        rows = decode_rows(record.canonical)
        if is_refusal(rows):
            return rows
        result = bundle.append_store.append_raw(
            rows.value, presented_fingerprint=record.fingerprint
        )
        if is_refusal(result):
            return result
        count += 1
    return Ok(count)


def restore_registry(records: tuple[RecordExport, ...], bundle: WorldStore) -> Result[int]:
    """Re-admit registry records and lineage edges from verbatim canonical bytes."""
    count = 0
    for record in records:
        restored = restore_one_registry(record, bundle)
        if is_refusal(restored):
            return restored
        count += 1
    return Ok(count)


def restore_one_registry(record: RecordExport, bundle: WorldStore) -> Result[None]:
    """Re-admit one registry record or lineage edge from verbatim canonical bytes."""
    decoded = decode_mapping(record.canonical)
    if is_refusal(decoded):
        return decoded
    payload = decoded.value
    if is_registry_envelope(payload):
        result = put_registry_envelope(record, bundle, payload)
    else:
        result = append_registry_lineage(record, bundle, payload)
    if is_refusal(result):
        return result
    return Ok(None)


def put_registry_envelope(
    record: RecordExport, bundle: WorldStore, payload: dict[str, object]
) -> Result[StoreReceipt]:
    """Put one CT-09 full-record envelope back into the replacement registry room."""
    body = payload["body"]
    if not isinstance(body, Mapping):
        return invalid_input(
            "canonical",
            "a registry record envelope's body must be a mapping",
            given=repr(body),
        )
    return bundle.registry_room.put_record(
        cast("Mapping[str, object]", body),
        kind=payload["kind"],
        format_version=payload["format_version"],
        presented_fingerprint=record.fingerprint,
    )


def append_registry_lineage(
    record: RecordExport, bundle: WorldStore, payload: dict[str, object]
) -> Result[StoreReceipt]:
    """Re-append one registry lineage edge from verbatim canonical bytes."""
    stream = record.stream if record.stream is not None else "restored-lineage"
    writer = restore_writer(stream)
    if is_refusal(writer):
        return writer
    return bundle.registry_room.append_lineage_edge(
        stream, writer.value, payload, presented_fingerprint=record.fingerprint
    )


def restore_journal(records: tuple[RecordExport, ...], bundle: WorldStore) -> Result[int]:
    """Re-admit journal events from verbatim canonical bytes into their streams."""
    count = 0
    for record in records:
        decoded = decode_mapping(record.canonical)
        if is_refusal(decoded):
            return decoded
        stream = record.stream if record.stream is not None else "restored"
        writer = restore_writer(stream)
        if is_refusal(writer):
            return writer
        result = bundle.journal.append(
            stream, writer.value, decoded.value, presented_fingerprint=record.fingerprint
        )
        if is_refusal(result):
            return result
        count += 1
    return Ok(count)


def restore_writer(stream: str) -> Result[WriterId]:
    """A WriterId for restore re-appends under ``stream``."""
    return WriterId.try_create(_RESTORE_MACHINE, _RESTORE_ROLE, stream, _RESTORE_BOOT)


def is_registry_envelope(payload: Mapping[str, object]) -> bool:
    """Whether ``payload`` is the CT-09 full-record envelope (kind/format_version/body)."""
    return (
        "kind" in payload
        and "format_version" in payload
        and "body" in payload
        and isinstance(payload["kind"], str)
        and isinstance(payload["format_version"], int)
        and not isinstance(payload["format_version"], bool)
    )


def decode_rows(canonical: bytes) -> Result[list[dict[str, object]]]:
    """Decode raw-archive canonical bytes to the ordered row list."""
    try:
        decoded: object = json.loads(canonical)
    except ValueError as exc:
        return storage_failure(
            "restored raw-archive canonical bytes are corrupt JSON; completion is not "
            "claimed (DEC-0109, DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "error": str(exc)},
        )
    if not isinstance(decoded, list):
        return invalid_input(
            "canonical",
            "raw-archive canonical bytes must decode to a non-empty list of row mappings",
            given=repr(decoded)[:200],
        )
    decoded_rows = cast("list[object]", decoded)
    if not decoded_rows:
        return invalid_input(
            "canonical",
            "raw-archive canonical bytes must decode to a non-empty list of row mappings",
            given=repr(decoded_rows)[:200],
        )
    return row_mappings(decoded_rows)


def row_mappings(decoded_rows: list[object]) -> Result[list[dict[str, object]]]:
    """Require every decoded raw-archive item to be a mapping."""
    rows: list[dict[str, object]] = []
    for item in decoded_rows:
        if not isinstance(item, Mapping):
            return invalid_input(
                "canonical",
                "each raw-archive row must be a mapping",
                given=repr(item)[:200],
            )
        rows.append(dict(cast("Mapping[str, object]", item)))
    return Ok(rows)


def decode_mapping(canonical: bytes) -> Result[dict[str, object]]:
    """Decode journal / registry / lineage canonical bytes to a mapping."""
    try:
        decoded: object = json.loads(canonical)
    except ValueError as exc:
        return storage_failure(
            "restored record canonical bytes are corrupt JSON; completion is not "
            "claimed (DEC-0109, DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "error": str(exc)},
        )
    if not isinstance(decoded, Mapping):
        return invalid_input(
            "canonical",
            "journal / registry / lineage canonical bytes must decode to a mapping",
            given=repr(decoded)[:200],
        )
    return Ok(dict(cast("Mapping[str, object]", decoded)))
