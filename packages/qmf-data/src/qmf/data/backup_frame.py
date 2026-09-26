"""Framed plaintext envelope for one CT-14 room export."""

from __future__ import annotations

import struct
from typing import Final, TypedDict

from qmf.core import Ok, Result
from qmf.data.backup_gate import coerce_role, coerce_world
from qmf.data.backup_storage import storage_failure
from qmf.data.store.backup_input import RecordExport, RoomExport

# Framing magic so restore can recognize the plaintext envelope.
_PLAINTEXT_MAGIC: Final[bytes] = b"QMFB1\0"


class BackupMeta(TypedDict):
    """Typed fields from the framed UTF-8 backup meta block."""

    format_version: int
    world: str
    role: str
    count: int


def frame_plaintext(export: RoomExport) -> bytes:
    """Frame one room export so record canonical bytes (timestamps) pass through verbatim.

    Metadata is length-prefixed UTF-8; each record's fingerprint, optional stream
    segment, and canonical bytes follow as length-prefixed blobs. The canonical payload
    is never re-serialized, so int64 UTC-ns timestamps remain exactly the stored bytes
    (DEC-0106).
    """
    chunks: list[bytes] = [_PLAINTEXT_MAGIC]
    meta = (
        f"v={export.format_version}\n"
        f"world={export.world.value}\n"
        f"role={export.source_room_role.value}\n"
        f"count={export.record_count}\n"
    ).encode()
    chunks.append(struct.pack(">I", len(meta)))
    chunks.append(meta)
    for record in export.records:
        append_record(chunks, record)
    return b"".join(chunks)


def append_record(chunks: list[bytes], record: RecordExport) -> None:
    """Append one verbatim record frame (fingerprint, stream, canonical) to ``chunks``."""
    fp = record.fingerprint.encode("utf-8")
    chunks.append(struct.pack(">I", len(fp)))
    chunks.append(fp)
    stream = (record.stream or "").encode("utf-8")
    chunks.append(struct.pack(">I", len(stream)))
    chunks.append(stream)
    chunks.append(struct.pack(">Q", len(record.canonical)))
    chunks.append(record.canonical)


def unframe_plaintext(plaintext: bytes) -> Result[RoomExport]:
    """Parse a framed plaintext envelope back into a :class:`RoomExport`."""
    if not plaintext.startswith(_PLAINTEXT_MAGIC):
        return storage_failure(
            "decrypted payload is not a CT-14 backup envelope; the copy is corrupt "
            "and restore completion is not claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "detail": "bad-magic"},
        )
    try:
        meta, records = read_framed_body(plaintext, len(_PLAINTEXT_MAGIC))
    except (ValueError, KeyError, UnicodeDecodeError, struct.error) as exc:
        return storage_failure(
            "decrypted backup envelope is corrupt or truncated; restore completion "
            "is not claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "error": str(exc)},
        )
    return room_export_from_meta(meta, records)


def read_framed_body(plaintext: bytes, offset: int) -> tuple[BackupMeta, list[RecordExport]]:
    """Read meta + records from a framed plaintext body; raise on truncation."""
    meta_len, offset = read_u32(plaintext, offset)
    meta_raw = plaintext[offset : offset + meta_len]
    offset += meta_len
    if len(meta_raw) != meta_len:
        raise ValueError("truncated meta")
    meta = parse_meta(meta_raw.decode("utf-8"))
    records: list[RecordExport] = []
    for _ in range(meta["count"]):
        record, offset = read_record(plaintext, offset)
        records.append(record)
    if offset != len(plaintext):
        raise ValueError("trailing bytes after framed records")
    return meta, records


def room_export_from_meta(meta: BackupMeta, records: list[RecordExport]) -> Result[RoomExport]:
    """Bind framed meta world/role into a :class:`RoomExport`."""
    world = coerce_world(meta["world"])
    if world is None:
        return storage_failure(
            "decrypted backup envelope carries an unknown world; restore completion "
            "is not claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "world": meta["world"]},
        )
    role = coerce_role(meta["role"])
    if role is None:
        return storage_failure(
            "decrypted backup envelope carries an unknown room-role; restore "
            "completion is not claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "role": meta["role"]},
        )
    return Ok(
        RoomExport(
            world=world,
            source_room_role=role,
            format_version=meta["format_version"],
            records=tuple(records),
        )
    )


def parse_meta(text: str) -> BackupMeta:
    """Parse the framed UTF-8 meta block into typed fields."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key] = value
    return {
        "format_version": int(fields["v"]),
        "world": fields["world"],
        "role": fields["role"],
        "count": int(fields["count"]),
    }


def read_record(buf: bytes, offset: int) -> tuple[RecordExport, int]:
    """Read one framed record starting at ``offset``; return it and the new offset."""
    fp_len, offset = read_u32(buf, offset)
    fp = buf[offset : offset + fp_len].decode("utf-8")
    offset += fp_len
    stream_len, offset = read_u32(buf, offset)
    stream_raw = buf[offset : offset + stream_len].decode("utf-8")
    offset += stream_len
    can_len, offset = read_u64(buf, offset)
    canonical = buf[offset : offset + can_len]
    offset += can_len
    if len(canonical) != can_len:
        raise ValueError("truncated canonical")
    return (
        RecordExport(
            fingerprint=fp,
            canonical=canonical,
            stream=stream_raw or None,
        ),
        offset,
    )


def read_u32(buf: bytes, offset: int) -> tuple[int, int]:
    """Read a big-endian uint32 from ``buf`` at ``offset``."""
    end = offset + 4
    if end > len(buf):
        raise ValueError("truncated u32")
    return struct.unpack(">I", buf[offset:end])[0], end


def read_u64(buf: bytes, offset: int) -> tuple[int, int]:
    """Read a big-endian uint64 from ``buf`` at ``offset``."""
    end = offset + 8
    if end > len(buf):
        raise ValueError("truncated u64")
    return struct.unpack(">Q", buf[offset:end])[0], end
