"""Reference usage — CT-14 restore into a replacement store (Story 5.2).

Executable::

    python packages/qmf-data/examples/restore_usage.py

Shows the four things Story 5.2 pins down:

1. A versioned off-machine copy restores into a **replacement** store root — never
   rewriting the only local copy in place; int64 UTC-ns timestamps stay verbatim.
2. Restored reads still enforce the 12-month seal as a ``policy rejection`` when a
   :class:`~qmf.data.HoldoutSeal` is wired into the replacement store.
3. Cross-world restore and ``world = simulated`` are ``policy rejection`` refusals.
4. Discarding the only local raw copy is refused under this component's authority.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    Instant,
    Ok,
    Result,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data import (
    EvidenceStore,
    HoldoutSeal,
    OffMachineBackup,
    OffMachineRestore,
    StoragePutAck,
)
from qmf.data.splits import SplitBoundary
from qmf.data.store import RoomRole

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


class _XorCipher:
    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in plaintext))

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return self.encrypt(ciphertext)


class _MemoryBucket:
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

    def get(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        format_version: int,
    ) -> Result[bytes]:
        del format_version
        return Ok(self.objects[(world, copy_version, source_room_role)])


def _calendar() -> CalendarIdentity:
    return _unwrap(
        CalendarIdentity.try_create("forex-17NY", "v3", "2025a"),
        "calendar identity",
    )


def _instant_boundary(value_ns: int) -> SplitBoundary:
    instant = _unwrap(Instant.try_create(value_ns), "instant")
    return _unwrap(SplitBoundary.try_create(instant), "split boundary")


def main() -> None:
    """Drive backup → restore into a replacement store with seal and world gates."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = EvidenceStore(root / "source")
        live = _unwrap(source.for_world(World.LIVE), "live world store")
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

        export = _unwrap(
            live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE),
            "CT-26 raw export",
        )
        _require(
            b"1700000000000000000" in export.records[0].canonical,
            "int64 UTC-ns timestamp present in source export",
        )

        bucket = _MemoryBucket()
        cipher = _XorCipher()
        receipt = _unwrap(
            OffMachineBackup(bucket, cipher).copy_export(export, for_world=World.LIVE),
            "CT-14 encrypted copy",
        )

        seal = _unwrap(
            HoldoutSeal.try_create(
                seal_boundary=_instant_boundary(1_000),
                calendar_identity=_calendar(),
                world=World.LIVE,
                holdout_months=12,
            ),
            "holdout seal",
        )
        replacement = EvidenceStore(root / "replacement", seal=seal)
        restore = OffMachineRestore(bucket, cipher)
        restored = _unwrap(
            restore.restore_copy(
                world=World.LIVE,
                copy_version=receipt.copy_version,
                source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
                into=replacement,
                for_world=World.LIVE,
                source_store=source,
            ),
            "CT-14 restore into replacement",
        )
        _require(
            restored.replacement_root != str(source.root.resolve()),
            "restore targeted a distinct replacement root",
        )
        restored_live = _unwrap(replacement.for_world(World.LIVE), "replacement live")
        reread = _unwrap(
            restored_live.append_store.read_raw(
                export.records[0].fingerprint,
                for_world=World.LIVE,
                at=_instant_boundary(500),
            ),
            "restored raw read outside seal",
        )
        _require(
            any(row.get("t") == 1_700_000_000_000_000_000 for row in reread),
            "restored timestamps are verbatim int64 UTC-ns",
        )
        # Source still intact after restore.
        source_again = _unwrap(
            live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE),
            "source CT-26 reread",
        )
        _require(
            source_again.records[0].canonical == export.records[0].canonical,
            "restore never rewrote the only local copy",
        )
        print(
            "restore into replacement: timestamps verbatim; "
            "source untouched; off-machine version retained"
        )

        sealed = restored_live.append_store.read_raw(
            export.records[0].fingerprint,
            for_world=World.LIVE,
            at=_instant_boundary(2_000),
        )
        _require(is_refusal(sealed), "sealed restored read refuses")
        _require(
            is_refusal(sealed) and sealed.category.value == "policy rejection",
            "sealed restored read is policy rejection",
        )
        print("restored seal enforcement: policy rejection on sealed holdout")

        cross = restore.restore_export(
            export, into=EvidenceStore(root / "cross"), for_world=World.REPLAY, source_store=source
        )
        _require(
            is_refusal(cross) and cross.category.value == "policy rejection",
            "cross-world restore is policy rejection",
        )
        in_place = restore.restore_export(
            export, into=source, for_world=World.LIVE, source_store=source
        )
        _require(
            is_refusal(in_place) and in_place.category.value == "policy rejection",
            "in-place restore is policy rejection",
        )
        discard = restore.discard_local_raw(source)
        _require(
            is_refusal(discard) and discard.category.value == "policy rejection",
            "discard of only local raw is policy rejection",
        )
        print(
            "cross-world / in-place / discard-only-copy: policy rejection "
            "(raw originals kept forever)"
        )


if __name__ == "__main__":
    main()
