"""Tier-1 tests for the CT-14 restore primitive (Story 5.2)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import (
    CalendarIdentity,
    Instant,
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
    EvidenceStore,
    HoldoutSeal,
    OffMachineBackup,
    OffMachineRestore,
    ReadBoundary,
    StoragePutAck,
)
from qmf.data.splits import SplitBoundary
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


def _export(store: EvidenceStore, role: RoomRole = RoomRole.IMMUTABLE_RAW_ARCHIVE) -> RoomExport:
    w = _world(store)
    _populate(w)
    result = w.backup_input.read_room(role, for_world=World.LIVE)
    assert is_ok(result)
    return result.value


def _calendar() -> CalendarIdentity:
    built = CalendarIdentity.try_create("forex-17NY", "v3", "2025a")
    assert is_ok(built)
    return built.value


def _instant(value_ns: int) -> Instant:
    built = Instant.try_create(value_ns)
    assert is_ok(built)
    return built.value


def _instant_boundary(value_ns: int) -> SplitBoundary:
    built = SplitBoundary.try_create(_instant(value_ns))
    assert is_ok(built)
    return built.value


def _instant_seal(*, boundary_ns: int, world: World = World.LIVE) -> HoldoutSeal:
    seal = HoldoutSeal.try_create(
        seal_boundary=_instant_boundary(boundary_ns),
        calendar_identity=_calendar(),
        world=world,
        holdout_months=12,
    )
    assert is_ok(seal)
    return seal.value


def test_restore_into_replacement_preserves_timestamps_verbatim(
    store: EvidenceStore, tmp_path: Path
) -> None:
    export = _export(store)
    assert b"1700000000000000000" in export.records[0].canonical

    storage = _MemoryStorage()
    cipher = _XorCipher()
    backup = OffMachineBackup(storage, cipher)
    copied = backup.copy_export(export, for_world=World.LIVE)
    assert is_ok(copied)

    replacement = EvidenceStore(tmp_path / "replacement")
    restore = OffMachineRestore(storage, cipher)
    result = restore.restore_copy(
        world=World.LIVE,
        copy_version=copied.value.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        into=replacement,
        for_world=World.LIVE,
        source_store=store,
    )
    assert is_ok(result)
    receipt = result.value
    assert receipt.record_count == 1
    assert receipt.replacement_root == str(replacement.root.resolve())
    assert receipt.replacement_root != str(store.root.resolve())

    restored = _world(replacement).backup_input.read_room(
        RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE
    )
    assert is_ok(restored)
    assert restored.value.records[0].canonical == export.records[0].canonical
    assert b"1700000000000000000" in restored.value.records[0].canonical

    # Source store still intact — restore never rewrote the only copy.
    source_again = _world(store).backup_input.read_room(
        RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE
    )
    assert is_ok(source_again)
    assert source_again.value.records[0].canonical == export.records[0].canonical
    assert ("live", 1, "immutable raw archive") in storage.objects


def test_in_place_restore_is_policy_rejection(store: EvidenceStore) -> None:
    export = _export(store)
    result = OffMachineRestore(_MemoryStorage(), _XorCipher()).restore_export(
        export, into=store, for_world=World.LIVE, source_store=store
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("signal") == "refuse-in-place-restore"


def test_same_root_path_restore_is_policy_rejection(store: EvidenceStore) -> None:
    export = _export(store)
    # A second EvidenceStore handle over the same filesystem root is still in-place.
    alias = EvidenceStore(store.root)
    result = OffMachineRestore(_MemoryStorage(), _XorCipher()).restore_export(
        export, into=alias, for_world=World.LIVE, source_store=store
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_restored_reads_enforce_seal(store: EvidenceStore, tmp_path: Path) -> None:
    export = _export(store)
    seal = _instant_seal(boundary_ns=1_000)
    replacement = EvidenceStore(tmp_path / "sealed-replacement", seal=seal)
    result = OffMachineRestore(_MemoryStorage(), _XorCipher()).restore_export(
        export, into=replacement, for_world=World.LIVE, source_store=store
    )
    assert is_ok(result)

    bundle = _world(replacement)
    sealed_at = _instant_boundary(2_000)
    open_at = _instant_boundary(500)

    fp = export.records[0].fingerprint
    sealed = bundle.append_store.read_raw(fp, for_world=World.LIVE, at=sealed_at)
    assert is_refusal(sealed)
    assert sealed.category is RefusalCategory.POLICY_REJECTION
    assert sealed.context.get("boundary") == ReadBoundary.RAW_ARCHIVE.value

    backup_sealed = bundle.backup_input.read_room(
        RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE, at=sealed_at
    )
    assert is_refusal(backup_sealed)
    assert backup_sealed.category is RefusalCategory.POLICY_REJECTION
    assert backup_sealed.context.get("boundary") == ReadBoundary.RESTORED_BACKUP.value

    assert is_ok(bundle.append_store.read_raw(fp, for_world=World.LIVE, at=open_at))
    assert is_ok(
        bundle.backup_input.read_room(
            RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE, at=open_at
        )
    )


def test_cross_world_restore_is_policy_rejection(store: EvidenceStore, tmp_path: Path) -> None:
    export = _export(store)
    replacement = EvidenceStore(tmp_path / "replacement")
    result = OffMachineRestore(_MemoryStorage(), _XorCipher()).restore_export(
        export, into=replacement, for_world=World.REPLAY, source_store=store
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("requested") == "replay"


def test_simulated_restore_is_policy_rejection(tmp_path: Path) -> None:
    export = RoomExport(
        world=World.SIMULATED,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        format_version=1,
        records=(
            RecordExport(
                fingerprint="fp1:sha256:abc",
                canonical=b'[{"t":1,"px":1}]',
            ),
        ),
    )
    replacement = EvidenceStore(tmp_path / "replacement")
    result = OffMachineRestore(_MemoryStorage(), _XorCipher()).restore_export(
        export, into=replacement, for_world=World.SIMULATED
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("requested") == "simulated"


def test_discard_local_raw_is_refused(store: EvidenceStore) -> None:
    result = OffMachineRestore(_MemoryStorage(), _XorCipher()).discard_local_raw(store)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("signal") == "refuse-delete-only-copy"
    # Source evidence still readable after the refused discard.
    export = _export(store)
    assert export.record_count == 1


def test_registry_and_journal_restore(store: EvidenceStore, tmp_path: Path) -> None:
    w = _world(store)
    _populate(w)
    registry = w.backup_input.read_room(RoomRole.REGISTRY_ROOM, for_world=World.LIVE)
    journal = w.backup_input.read_room(RoomRole.JOURNAL, for_world=World.LIVE)
    assert is_ok(registry)
    assert is_ok(journal)
    assert registry.value.record_count == 2
    assert journal.value.record_count == 1
    assert journal.value.records[0].stream == "dq"

    replacement = EvidenceStore(tmp_path / "replacement")
    restore = OffMachineRestore(_MemoryStorage(), _XorCipher())
    reg_result = restore.restore_export(
        registry.value, into=replacement, for_world=World.LIVE, source_store=store
    )
    assert is_ok(reg_result)
    assert reg_result.value.record_count == 2
    j_result = restore.restore_export(
        journal.value, into=replacement, for_world=World.LIVE, source_store=store
    )
    assert is_ok(j_result)
    assert j_result.value.record_count == 1

    restored_reg = _world(replacement).backup_input.read_room(
        RoomRole.REGISTRY_ROOM, for_world=World.LIVE
    )
    restored_j = _world(replacement).backup_input.read_room(
        RoomRole.JOURNAL, for_world=World.LIVE
    )
    assert is_ok(restored_reg)
    assert is_ok(restored_j)
    assert restored_reg.value.record_count == 2
    assert restored_j.value.records[0].canonical == journal.value.records[0].canonical
    assert restored_j.value.records[0].stream == "dq"


def test_missing_off_machine_copy_is_storage_failure(
    store: EvidenceStore, tmp_path: Path
) -> None:
    replacement = EvidenceStore(tmp_path / "replacement")
    result = OffMachineRestore(_MemoryStorage(), _XorCipher()).restore_copy(
        world=World.LIVE,
        copy_version=99,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        into=replacement,
        for_world=World.LIVE,
        source_store=store,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE


