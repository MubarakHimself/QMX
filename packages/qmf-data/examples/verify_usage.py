"""Reference usage — CT-14 verify primitives (Story 5.3).

Executable::

    python packages/qmf-data/examples/verify_usage.py

Shows the four things Story 5.3 pins down:

1. Recoverability is claimed only through sample-restore and full-restore rehearsal —
   never from a snapshot alone (SCN-0004, DEC-0118).
2. A corrupt restore yields a ``storage failure`` refusal, not a recoverability claim.
3. Migrations run preflight → backup-first → dry-run → migrate → verify against a
   documented restore path and never mutate the only copy in place.
4. Numeric restore-verification cadence / RPO / RTO / retention stay null
   node/ops pointers — never filled from a recommendation.
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
    MIGRATION_SEQUENCE,
    NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE,
    NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE,
    NODE_OPS_BACKUP_RETENTION_PERIOD,
    NODE_OPS_RESTORE_VERIFICATION_CADENCE,
    EvidenceStore,
    OffMachineBackup,
    OffMachineRestore,
    OffMachineVerify,
    StoragePutAck,
    VerifyKind,
    migrate_evidence,
    refuse_snapshot_alone_claim,
)
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
        payload = self.objects.get((world, copy_version, source_room_role))
        if payload is None:
            return unpersistable(
                "missing copy",
                retryability=Retryability.NO,
                context={"signal": "missing-copy"},
            )
        return Ok(payload)


def main() -> None:
    """Drive sample-restore, corrupt refusal, migration sequence, and null pointers."""
    _require(NODE_OPS_RESTORE_VERIFICATION_CADENCE is None, "cadence stays null")
    _require(NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE is None, "RPO stays null")
    _require(NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE is None, "RTO stays null")
    _require(NODE_OPS_BACKUP_RETENTION_PERIOD is None, "retention stays null")
    print(
        "node/ops pointers: cadence/RPO/RTO/retention remain null "
        "(never filled from a recommendation)"
    )

    alone = refuse_snapshot_alone_claim(world=World.LIVE, copy_version=1)
    _require(
        is_refusal(alone) and alone.category.value == "policy rejection",
        "snapshot-alone recoverability is policy rejection",
    )
    print("snapshot alone: policy rejection (no recoverability claim)")

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
        jw = _unwrap(WriterId.try_create("node-a", "data", "dq", "boot-1"), "journal writer")
        _unwrap(
            live.journal.append("dq", jw, {"event_type": "data quality", "n": 0}),
            "journal append",
        )

        export = _unwrap(
            live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE),
            "CT-26 raw export",
        )
        bucket = _MemoryBucket()
        cipher = _XorCipher()
        receipt = _unwrap(
            OffMachineBackup(bucket, cipher).copy_export(export, for_world=World.LIVE),
            "CT-14 encrypted copy",
        )

        claim = _unwrap(
            OffMachineVerify(bucket, cipher).sample_restore(
                world=World.LIVE,
                copy_version=receipt.copy_version,
                source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
                into=EvidenceStore(root / "sample-replacement"),
                for_world=World.LIVE,
                expected=export,
                source_store=source,
            ),
            "sample-restore verify",
        )
        _require(claim.kind is VerifyKind.SAMPLE_RESTORE, "claim kind is sample-restore")
        _require(claim.record_count == 1, "sample claim covers one record")
        print(
            f"sample-restore: recoverability claimed "
            f"(kind={claim.kind.value}; records={claim.record_count})"
        )

        bucket.objects[("live", receipt.copy_version, "immutable raw archive")] = b"CORRUPT!!"
        corrupt = OffMachineVerify(bucket, cipher).sample_restore(
            world=World.LIVE,
            copy_version=receipt.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
            into=EvidenceStore(root / "corrupt-replacement"),
            for_world=World.LIVE,
            expected=export,
            source_store=source,
        )
        _require(
            is_refusal(corrupt) and corrupt.category.value == "storage failure",
            "corrupt restore is storage failure",
        )
        print("corrupt restore: storage failure (no recoverability claim)")

        # Fresh bucket for the migration rehearsal (prior corruption stays isolated).
        mig_bucket = _MemoryBucket()
        mig_cipher = _XorCipher()
        report = _unwrap(
            migrate_evidence(
                source=source,
                destination=EvidenceStore(root / "destination"),
                verify_into=EvidenceStore(root / "verify-into"),
                world=World.LIVE,
                backup=OffMachineBackup(mig_bucket, mig_cipher),
                restore=OffMachineRestore(mig_bucket, mig_cipher),
                verify=OffMachineVerify(mig_bucket, mig_cipher),
                room_roles=(
                    RoomRole.IMMUTABLE_RAW_ARCHIVE,
                    RoomRole.JOURNAL,
                    RoomRole.REGISTRY_ROOM,
                ),
            ),
            "staged migration",
        )
        _require(report.stages_completed == MIGRATION_SEQUENCE, "all five stages ran")
        _require(report.backed_up is True, "backup-first wrote off-machine copies")
        _require(
            report.recoverability.kind is VerifyKind.FULL_RESTORE_REHEARSAL,
            "migration verify used full-restore rehearsal",
        )
        source_again = _unwrap(
            live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE),
            "source reread after migration",
        )
        _require(
            source_again.records[0].canonical == export.records[0].canonical,
            "migration never mutated the only local copy",
        )
        print(
            "migration: preflight -> backup-first -> dry-run -> migrate -> verify; "
            "source untouched; recoverability via full-restore rehearsal"
        )


if __name__ == "__main__":
    main()
