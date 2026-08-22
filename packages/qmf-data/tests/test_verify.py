"""Tier-1 tests for CT-14 verify primitives (Story 5.3)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import (
    Ok,
    RefusalCategory,
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
    MigrationStage,
    OffMachineBackup,
    OffMachineRestore,
    OffMachineVerify,
    RecoverabilityClaim,
    StoragePutAck,
    VerifyKind,
    migrate_evidence,
    refuse_snapshot_alone_claim,
)
from qmf.data.store import RoomExport, RoomRole, WorldStore
from qmf.data.store.backup_input import RecordExport


def _world(store: EvidenceStore) -> WorldStore:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return world.value


def _writer() -> WriterId:
    built = WriterId.try_create("node-a", "registry", "lineage", "boot-1")
    assert is_ok(built)
    return built.value


def _populate(w: WorldStore) -> None:
    assert is_ok(w.append_store.append_raw([{"t": 1_700_000_000_000_000_000, "px": 100}]))
    jw = WriterId.try_create("node-a", "data", "dq", "boot-1")
    assert is_ok(jw)
    assert is_ok(w.journal.append("dq", jw.value, {"event_type": "data quality", "n": 0}))
    assert is_ok(
        w.registry_room.put_record({"kind": "producer"}, kind="producer", format_version=1)
    )
    assert is_ok(w.registry_room.append_lineage_edge("lineage", _writer(), {"edge": "a"}))


class _XorCipher:
    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in plaintext))

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return self.encrypt(ciphertext)


class _MemoryStorage:
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
                "object storage has no such versioned copy",
                retryability=Retryability.NO,
                context={"signal": "missing-copy", "copy_version": copy_version},
            )
        return Ok(payload)

    def corrupt(self, world: str, copy_version: int, source_room_role: str) -> None:
        self.objects[(world, copy_version, source_room_role)] = b"not-a-ct14-envelope!!!!"


def _export(store: EvidenceStore, role: RoomRole = RoomRole.IMMUTABLE_RAW_ARCHIVE) -> RoomExport:
    w = _world(store)
    _populate(w)
    result = w.backup_input.read_room(role, for_world=World.LIVE)
    assert is_ok(result)
    return result.value


def test_node_ops_numeric_pointers_stay_unfilled() -> None:
    """AC4: never fill cadence/RPO/RTO/retention from a recommendation."""
    assert NODE_OPS_RESTORE_VERIFICATION_CADENCE is None
    assert NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE is None
    assert NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE is None
    assert NODE_OPS_BACKUP_RETENTION_PERIOD is None
    assert MIGRATION_SEQUENCE == (
        MigrationStage.PREFLIGHT,
        MigrationStage.BACKUP_FIRST,
        MigrationStage.DRY_RUN,
        MigrationStage.MIGRATE,
        MigrationStage.VERIFY,
    )


def test_refuse_snapshot_alone_claim_never_asserts_recoverability() -> None:
    """AC1: a snapshot existing is not a recoverability claim."""
    result = refuse_snapshot_alone_claim(
        world=World.LIVE, copy_version=1, source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("signal") == "refuse-snapshot-alone-claim"


def test_sample_restore_issues_recoverability_claim(store: EvidenceStore, tmp_path: Path) -> None:
    """AC1/AC2: sample-restore confirms restored evidence against the documented path."""
    export = _export(store)
    storage = _MemoryStorage()
    cipher = _XorCipher()
    backup = OffMachineBackup(storage, cipher)
    copied = backup.copy_export(export, for_world=World.LIVE)
    assert is_ok(copied)

    verify = OffMachineVerify(storage, cipher)
    claim = verify.sample_restore(
        world=World.LIVE,
        copy_version=copied.value.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        into=EvidenceStore(tmp_path / "sample-replacement"),
        for_world=World.LIVE,
        expected=export,
        source_store=store,
    )
    assert is_ok(claim)
    assert isinstance(claim.value, RecoverabilityClaim)
    assert claim.value.kind is VerifyKind.SAMPLE_RESTORE
    assert claim.value.record_count == 1
    assert claim.value.documented_restore_path == str(store.root.resolve())
    assert len(claim.value.rooms) == 1
    assert claim.value.rooms[0].source_room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE


def test_corrupt_sample_restore_is_storage_failure_not_claim(
    store: EvidenceStore, tmp_path: Path
) -> None:
    """AC2: corrupt restore => storage failure, never a recoverability claim."""
    export = _export(store)
    storage = _MemoryStorage()
    cipher = _XorCipher()
    backup = OffMachineBackup(storage, cipher)
    copied = backup.copy_export(export, for_world=World.LIVE)
    assert is_ok(copied)
    storage.corrupt("live", copied.value.copy_version, "immutable raw archive")

    verify = OffMachineVerify(storage, cipher)
    result = verify.sample_restore(
        world=World.LIVE,
        copy_version=copied.value.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        into=EvidenceStore(tmp_path / "corrupt-replacement"),
        for_world=World.LIVE,
        expected=export,
        source_store=store,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE
    assert not isinstance(result, RecoverabilityClaim)


def test_mismatched_expected_is_storage_failure(store: EvidenceStore, tmp_path: Path) -> None:
    """AC2: restored bytes that do not match the documented export are not success."""
    export = _export(store)
    storage = _MemoryStorage()
    cipher = _XorCipher()
    copied = OffMachineBackup(storage, cipher).copy_export(export, for_world=World.LIVE)
    assert is_ok(copied)

    wrong = RoomExport(
        world=World.LIVE,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        format_version=export.format_version,
        records=(
            RecordExport(
                fingerprint="fp1:sha256:" + ("ab" * 32),
                canonical=b'[{"t":1,"px":999}]',
            ),
        ),
    )
    result = OffMachineVerify(storage, cipher).sample_restore(
        world=World.LIVE,
        copy_version=copied.value.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        into=EvidenceStore(tmp_path / "mismatch-replacement"),
        for_world=World.LIVE,
        expected=wrong,
        source_store=store,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE
    assert result.context.get("signal") == "verify-mismatch"


def test_full_restore_rehearsal_covers_restorable_rooms(
    store: EvidenceStore, tmp_path: Path
) -> None:
    """AC1: full-restore rehearsal verifies every named room-role."""
    w = _world(store)
    _populate(w)
    storage = _MemoryStorage()
    cipher = _XorCipher()
    backup = OffMachineBackup(storage, cipher)

    expected: dict[RoomRole, RoomExport] = {}
    copies: dict[RoomRole, int] = {}
    for role in (
        RoomRole.IMMUTABLE_RAW_ARCHIVE,
        RoomRole.JOURNAL,
        RoomRole.REGISTRY_ROOM,
    ):
        export = w.backup_input.read_room(role, for_world=World.LIVE)
        assert is_ok(export)
        expected[role] = export.value
        copied = backup.copy_export(export.value, for_world=World.LIVE)
        assert is_ok(copied)
        copies[role] = copied.value.copy_version

    claim = OffMachineVerify(storage, cipher).full_restore_rehearsal(
        world=World.LIVE,
        copies=copies,
        into=EvidenceStore(tmp_path / "full-replacement"),
        for_world=World.LIVE,
        expected=expected,
        source_store=store,
    )
    assert is_ok(claim)
    assert claim.value.kind is VerifyKind.FULL_RESTORE_REHEARSAL
    assert len(claim.value.rooms) == 3
    assert claim.value.record_count == sum(e.record_count for e in expected.values())


def test_migration_runs_full_sequence_never_in_place(store: EvidenceStore, tmp_path: Path) -> None:
    """AC3: preflight → backup-first → dry-run → migrate → verify; source untouched."""
    w = _world(store)
    _populate(w)
    before = w.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE)
    assert is_ok(before)

    storage = _MemoryStorage()
    cipher = _XorCipher()
    backup = OffMachineBackup(storage, cipher)
    restore = OffMachineRestore(storage, cipher)
    verify = OffMachineVerify(storage, cipher)

    destination = EvidenceStore(tmp_path / "destination")
    verify_into = EvidenceStore(tmp_path / "verify-into")
    report = migrate_evidence(
        source=store,
        destination=destination,
        verify_into=verify_into,
        world=World.LIVE,
        backup=backup,
        restore=restore,
        verify=verify,
        room_roles=(RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL, RoomRole.REGISTRY_ROOM),
    )
    assert is_ok(report)
    assert report.value.stages_completed == MIGRATION_SEQUENCE
    assert report.value.backed_up is True
    assert len(report.value.backup_receipts) == 3
    assert report.value.restore_path == str(store.root.resolve())
    assert report.value.destination_root == str(destination.root.resolve())
    assert report.value.recoverability.kind is VerifyKind.FULL_RESTORE_REHEARSAL
    assert report.value.preflight_count == before.value.record_count + 1 + 2

    after = w.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE)
    assert is_ok(after)
    assert after.value.records[0].canonical == before.value.records[0].canonical

    dest_raw = _world(destination).backup_input.read_room(
        RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE
    )
    assert is_ok(dest_raw)
    assert dest_raw.value.records[0].canonical == before.value.records[0].canonical


def test_in_place_migration_is_policy_rejection(store: EvidenceStore, tmp_path: Path) -> None:
    """AC3: migrating into the source root is refused."""
    _populate(_world(store))
    storage = _MemoryStorage()
    cipher = _XorCipher()
    result = migrate_evidence(
        source=store,
        destination=store,
        verify_into=EvidenceStore(tmp_path / "verify-into"),
        world=World.LIVE,
        backup=OffMachineBackup(storage, cipher),
        restore=OffMachineRestore(storage, cipher),
        verify=OffMachineVerify(storage, cipher),
        room_roles=(RoomRole.IMMUTABLE_RAW_ARCHIVE,),
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("signal") == "refuse-in-place-migration"


def test_overlapping_verify_root_is_policy_rejection(store: EvidenceStore, tmp_path: Path) -> None:
    _populate(_world(store))
    storage = _MemoryStorage()
    cipher = _XorCipher()
    destination = EvidenceStore(tmp_path / "destination")
    result = migrate_evidence(
        source=store,
        destination=destination,
        verify_into=destination,
        world=World.LIVE,
        backup=OffMachineBackup(storage, cipher),
        restore=OffMachineRestore(storage, cipher),
        verify=OffMachineVerify(storage, cipher),
        room_roles=(RoomRole.IMMUTABLE_RAW_ARCHIVE,),
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("signal") == "refuse-overlapping-verify-root"
