"""Tier-1 tests for the CT-14 encrypted versioned off-machine copy (Story 5.1)."""

from __future__ import annotations

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    WriterId,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.data import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    ENCRYPTION_REQUIRED,
    BackupCopyReceipt,
    EvidenceStore,
    OffMachineBackup,
    StoragePutAck,
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
    """Demo cipher: XOR with a fixed mask — stands in for a node/ops crypto adapter."""

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in plaintext))


class _MemoryStorage:
    """In-memory ObjectStorage double — no provider, keys, or credentials."""

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
        key = (world, copy_version, source_room_role)
        if key in self.objects:
            return unpersistable(
                "object storage refused to mutate an existing versioned copy",
                retryability=Retryability.NO,
                context={"signal": "version-collision", "copy_version": copy_version},
            )
        self.objects[key] = payload
        return Ok(StoragePutAck(detail=(("objects", str(len(self.objects))),)))


class _UnreachableStorage:
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


class _RaisingStorage:
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
        raise ConnectionError("bucket down")


class _MiswiredStorage:
    """Adapter that returns the wrong refusal category — boundary must still AC4."""

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
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=Retryability.YES,
            context={"signal": "miswired-adapter"},
        )


class _RejectingCipher:
    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        del plaintext
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=Retryability.NO,
            context={"field": "cipher", "reason": "encryption key custody unresolved"},
        )


class _EmptyCipher:
    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        del plaintext
        return Ok(b"")


class _RaisingCipher:
    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        del plaintext
        raise RuntimeError("crypto backend exploded")


def _export(store: EvidenceStore, role: RoomRole = RoomRole.IMMUTABLE_RAW_ARCHIVE) -> RoomExport:
    w = _world(store)
    _populate(w)
    result = w.backup_input.read_room(role, for_world=World.LIVE)
    assert is_ok(result)
    return result.value


def test_encryption_required_pointer_is_standing() -> None:
    assert ENCRYPTION_REQUIRED is True
    assert BACKUP_CONTRACT_FORMAT_VERSION == 1


def test_copy_is_encrypted_versioned_and_leaves_local_evidence(
    store: EvidenceStore,
) -> None:
    export = _export(store)
    assert export.record_count == 1
    # verbatim int64 UTC-ns timestamp still inside the canonical bytes
    assert b"1700000000000000000" in export.records[0].canonical

    storage = _MemoryStorage()
    backup = OffMachineBackup(storage, _XorCipher())
    first = backup.copy_export(export, for_world=World.LIVE)
    assert is_ok(first)
    receipt = first.value
    assert isinstance(receipt, BackupCopyReceipt)
    assert receipt.copy_version == 1
    assert receipt.encryption_required is True
    assert receipt.world is World.LIVE
    assert receipt.source_room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE
    assert receipt.payload_fingerprint.startswith("fp1:sha256:")
    assert receipt.record_count == 1

    stored = storage.objects[("live", 1, "immutable raw archive")]
    # ciphertext differs from plaintext framing (encryption actually applied)
    assert stored != export.records[0].canonical
    assert stored[0] != ord("Q")  # magic is encrypted away

    # local evidence untouched — CT-26 still reads the same verbatim bytes
    again = _world(store).backup_input.read_room(
        RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE
    )
    assert is_ok(again)
    assert again.value.records[0].canonical == export.records[0].canonical

    # second copy is a new version, never mutates version 1
    second = backup.copy_export(export, for_world=World.LIVE)
    assert is_ok(second)
    assert second.value.copy_version == 2
    assert ("live", 1, "immutable raw archive") in storage.objects
    assert ("live", 2, "immutable raw archive") in storage.objects
    assert storage.objects[("live", 1, "immutable raw archive")] == stored


def test_registry_room_is_covered(store: EvidenceStore) -> None:
    export = _export(store, RoomRole.REGISTRY_ROOM)
    assert export.record_count == 2
    storage = _MemoryStorage()
    result = OffMachineBackup(storage, _XorCipher()).copy_export(export, for_world=World.LIVE)
    assert is_ok(result)
    assert result.value.source_room_role is RoomRole.REGISTRY_ROOM
    assert ("live", 1, "registry room") in storage.objects


def test_cross_world_copy_is_policy_rejection(store: EvidenceStore) -> None:
    export = _export(store)
    result = OffMachineBackup(_MemoryStorage(), _XorCipher()).copy_export(
        export, for_world=World.REPLAY
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("requested") == "replay"


def test_simulated_world_is_policy_rejection() -> None:
    export = RoomExport(
        world=World.SIMULATED,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        format_version=1,
        records=(RecordExport(fingerprint="fp1:sha256:abc", canonical=b'{"t":1}'),),
    )
    result = OffMachineBackup(_MemoryStorage(), _XorCipher()).copy_export(
        export, for_world=World.SIMULATED
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("requested") == "simulated"


def test_unreachable_storage_is_storage_failure_not_completion(
    store: EvidenceStore,
) -> None:
    export = _export(store)
    backup = OffMachineBackup(_UnreachableStorage(), _XorCipher())
    result = backup.copy_export(export, for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE
    assert backup.next_copy_version == 2  # ordinal advanced; no completion claimed


def test_storage_raise_is_storage_failure_never_raised(store: EvidenceStore) -> None:
    export = _export(store)
    result = OffMachineBackup(_RaisingStorage(), _XorCipher()).copy_export(
        export, for_world=World.LIVE
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE
    assert result.context.get("signal") == "storage-raised"


def test_miswired_storage_refusal_is_remapped_to_storage_failure(
    store: EvidenceStore,
) -> None:
    export = _export(store)
    result = OffMachineBackup(_MiswiredStorage(), _XorCipher()).copy_export(
        export, for_world=World.LIVE
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE
    assert result.context.get("signal") == "storage-refused"
    assert result.context.get("adapter_category") == "unavailable dependency"


def test_empty_ciphertext_is_corrupt_copy_refusal(store: EvidenceStore) -> None:
    export = _export(store)
    result = OffMachineBackup(_MemoryStorage(), _EmptyCipher()).copy_export(
        export, for_world=World.LIVE
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE
    assert result.context.get("signal") == "corrupt-copy"


def test_cipher_refusal_propagates_without_completion(store: EvidenceStore) -> None:
    export = _export(store)
    result = OffMachineBackup(_MemoryStorage(), _RejectingCipher()).copy_export(
        export, for_world=World.LIVE
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_cipher_raise_is_storage_failure(store: EvidenceStore) -> None:
    export = _export(store)
    result = OffMachineBackup(_MemoryStorage(), _RaisingCipher()).copy_export(
        export, for_world=World.LIVE
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE
    assert result.context.get("signal") == "cipher-raised"


def test_missing_for_world_is_invalid_input(store: EvidenceStore) -> None:
    export = _export(store)
    result = OffMachineBackup(_MemoryStorage(), _XorCipher()).copy_export(export, for_world=None)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_receipt_carries_no_credential_fields(store: EvidenceStore) -> None:
    export = _export(store)
    result = OffMachineBackup(_MemoryStorage(), _XorCipher()).copy_export(export, for_world="live")
    assert is_ok(result)
    fields = set(result.value.__dataclass_fields__)
    assert "credential" not in fields
    assert "secret" not in fields
    assert "key" not in fields
    assert "password" not in fields
    assert result.value.encryption_required is True
