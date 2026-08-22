"""Reference usage — CT-14 encrypted versioned off-machine copy (Story 5.1).

Executable::

    python packages/qmf-data/examples/backup_usage.py

Shows the five things Story 5.1 pins down:

1. CT-26 :class:`~qmf.data.store.BackupInput` presents one room-role's records
   verbatim (including the registry room); the read never mutates evidence and
   int64 UTC-ns timestamps pass through unchanged.
2. CT-14 :class:`~qmf.data.OffMachineBackup` encrypts that input through an
   injected :class:`~qmf.data.PayloadCipher` and puts a **new** versioned artifact
   through an injected :class:`~qmf.data.ObjectStorage` port — never mutating the
   only local copy or an earlier off-machine version.
3. A cross-world copy or ``world = simulated`` is a ``policy rejection``.
4. Unreachable / rejected / corrupt object storage yields a ``storage failure``
   typed refusal — completion is never claimed, and nothing is raised across the
   boundary.
5. Encryption is required as a pointer; provider, object-key layout, numeric
   RPO/RTO/retention, and credentials are not baked in — and no credential enters
   the receipt.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Ok,
    Result,
    Retryability,
    World,
    WriterId,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.data import (
    ENCRYPTION_REQUIRED,
    EvidenceStore,
    OffMachineBackup,
    StoragePutAck,
)
from qmf.data.store import RoomRole

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a call we require to succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    """A real check (not a bare ``assert``, which ``-O`` strips) for a demonstrated fact."""
    if not condition:
        raise AssertionError(f"expected {what}")


class _XorCipher:
    """Stand-in crypto adapter — real key custody is node/ops-owned (AC5)."""

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in plaintext))


class _MemoryBucket:
    """Stand-in object storage — provider and credentials stay outside QMF (AC5)."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, int, str], bytes] = {}

    def put(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        payload: bytes,
        format_version: int,
    ) -> Result[StoragePutAck]:
        del format_version
        self.objects[(world, copy_version, source_room_role)] = payload
        return Ok(StoragePutAck())


class _DownBucket:
    """Object storage that is unreachable — FM-2."""

    def put(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        payload: bytes,
        format_version: int,
    ) -> Result[StoragePutAck]:
        del world, copy_version, source_room_role, payload, format_version
        return unpersistable(
            "object storage bucket unreachable",
            retryability=Retryability.YES,
            context={"signal": "unreachable"},
        )


def main() -> None:
    """Drive the CT-26 → CT-14 path end-to-end with injected seams."""
    _require(ENCRYPTION_REQUIRED is True, "encryption-required pointer is standing")

    with tempfile.TemporaryDirectory() as tmp:
        store = EvidenceStore(Path(tmp))
        live = _unwrap(store.for_world(World.LIVE), "live world store")

        # Populate evidence rooms the backup must cover (raw + registry).
        _unwrap(
            live.append_store.append_raw([{"t": 1_700_000_000_000_000_000, "px": 42}]),
            "raw append",
        )
        writer = _unwrap(
            WriterId.try_create("node-a", "registry", "lineage", "boot-1"),
            "writer id",
        )
        _unwrap(
            live.registry_room.put_record({"kind": "producer"}, kind="producer", format_version=1),
            "registry record",
        )
        _unwrap(
            live.registry_room.append_lineage_edge("lineage", writer, {"edge": "a"}),
            "lineage edge",
        )

        raw = _unwrap(
            live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE),
            "CT-26 raw export",
        )
        _require(raw.record_count == 1, "raw export has one record")
        _require(
            b"1700000000000000000" in raw.records[0].canonical,
            "int64 UTC-ns timestamp passes through CT-26 verbatim",
        )
        registry = _unwrap(
            live.backup_input.read_room(RoomRole.REGISTRY_ROOM, for_world=World.LIVE),
            "CT-26 registry export",
        )
        _require(registry.record_count == 2, "registry export covers records + edges")
        print(
            "CT-26 input: raw records=1 (timestamps verbatim), "
            f"registry records={registry.record_count}"
        )

        bucket = _MemoryBucket()
        backup = OffMachineBackup(bucket, _XorCipher())
        receipt = _unwrap(
            backup.copy_export(raw, for_world=World.LIVE),
            "CT-14 encrypted copy",
        )
        _require(receipt.copy_version == 1, "first copy is version 1")
        _require(receipt.encryption_required is True, "receipt carries encryption pointer")
        _require(
            "credential" not in receipt.__dataclass_fields__,
            "receipt embeds no credential field",
        )
        second = _unwrap(
            backup.copy_export(raw, for_world=World.LIVE),
            "second CT-14 copy",
        )
        _require(second.copy_version == 2, "second copy is a new version")
        _require(
            ("live", 1, "immutable raw archive") in bucket.objects
            and ("live", 2, "immutable raw archive") in bucket.objects,
            "both versioned artifacts retained; nothing mutated in place",
        )
        # Local evidence still intact after off-machine copies.
        reread = _unwrap(
            live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE),
            "post-backup CT-26 reread",
        )
        _require(
            reread.records[0].canonical == raw.records[0].canonical,
            "backup never mutates the only local copy",
        )
        print(
            f"CT-14 copy: versions={receipt.copy_version},{second.copy_version}; "
            "encrypted; local evidence untouched"
        )

        cross = backup.copy_export(raw, for_world=World.REPLAY)
        _require(is_refusal(cross), "cross-world copy refuses")
        _require(
            is_refusal(cross) and cross.category.value == "policy rejection",
            "cross-world is policy rejection",
        )
        print("cross-world / simulated path: policy rejection")

        down = OffMachineBackup(_DownBucket(), _XorCipher())
        failed = down.copy_export(raw, for_world=World.LIVE)
        _require(is_refusal(failed), "unreachable storage refuses")
        _require(
            is_refusal(failed) and failed.category.value == "storage failure",
            "unreachable storage is storage failure, not completion",
        )
        print(
            "object-storage failure: storage failure typed refusal "
            "(no completion claimed; nothing raised)"
        )


if __name__ == "__main__":
    main()
