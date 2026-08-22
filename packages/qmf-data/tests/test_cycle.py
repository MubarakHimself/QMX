"""Tier-1 tests for the application-owned nightly off-machine cycle (Story 5.4)."""

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
    BACKUP_CADENCE,
    CYCLE_ROOM_ROLES,
    ENCRYPTION_REQUIRED,
    NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE,
    NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE,
    EvidenceStore,
    NightlyCycleReport,
    OffMachineCycle,
    StoragePutAck,
    VerifyKind,
    refuse_numeric_rpo_rto,
    refuse_schedule_ownership,
)
from qmf.data.store import RoomRole, WorldStore


def _world(store: EvidenceStore) -> WorldStore:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return world.value


def _populate(w: WorldStore) -> None:
    assert is_ok(w.append_store.append_raw([{"t": 1_700_000_000_000_000_000, "px": 100}]))
    jw = WriterId.try_create("node-a", "data", "dq", "boot-1")
    assert is_ok(jw)
    assert is_ok(w.journal.append("dq", jw.value, {"event_type": "data quality", "n": 0}))
    assert is_ok(
        w.registry_room.put_record({"kind": "producer"}, kind="producer", format_version=1)
    )
    writer = WriterId.try_create("node-a", "registry", "lineage", "boot-1")
    assert is_ok(writer)
    assert is_ok(w.registry_room.append_lineage_edge("lineage", writer.value, {"edge": "a"}))


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


def test_backup_cadence_is_nightly_design_pointer() -> None:
    """AC1: registry:backup_cadence = nightly is the design pointer, not a scheduler."""
    assert BACKUP_CADENCE == "nightly"
    assert ENCRYPTION_REQUIRED is True
    assert NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE is None
    assert NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE is None
    assert len(CYCLE_ROOM_ROLES) == 7
    assert RoomRole.REGISTRY_ROOM in CYCLE_ROOM_ROLES


def test_run_once_backs_up_every_room_and_sample_restores(
    store: EvidenceStore, tmp_path: Path
) -> None:
    """AC1/AC3: one cycle covers every room-role including registry, then sample-restores."""
    _populate(_world(store))
    cycle = OffMachineCycle(_MemoryStorage(), _XorCipher())
    report = cycle.run_once(
        store=store,
        world=World.LIVE,
        sample_into=EvidenceStore(tmp_path / "sample"),
    )
    assert is_ok(report)
    assert isinstance(report.value, NightlyCycleReport)
    assert report.value.world is World.LIVE
    assert report.value.cadence == "nightly"
    assert report.value.encryption_required is True
    assert "credential" not in report.value.__dataclass_fields__
    assert report.value.rooms_backed_up == CYCLE_ROOM_ROLES
    assert len(report.value.backup_receipts) == 7
    assert RoomRole.REGISTRY_ROOM in {r.source_room_role for r in report.value.backup_receipts}
    assert report.value.sample_restore.kind is VerifyKind.SAMPLE_RESTORE
    assert report.value.full_restore is None
    # Local evidence untouched.
    reread = _world(store).backup_input.read_room(
        RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE
    )
    assert is_ok(reread)
    assert reread.value.record_count == 1


def test_run_once_with_full_rehearsal(store: EvidenceStore, tmp_path: Path) -> None:
    """AC1: application opts into the periodic full-restore rehearsal for this cycle."""
    _populate(_world(store))
    cycle = OffMachineCycle(_MemoryStorage(), _XorCipher())
    report = cycle.run_once(
        store=store,
        world=World.LIVE,
        sample_into=EvidenceStore(tmp_path / "sample"),
        full_into=EvidenceStore(tmp_path / "full"),
        include_full_rehearsal=True,
    )
    assert is_ok(report)
    assert report.value.full_restore is not None
    assert report.value.full_restore.kind is VerifyKind.FULL_RESTORE_REHEARSAL
    assert len(report.value.full_restore.rooms) == 3


def test_refuse_schedule_ownership_is_policy_rejection() -> None:
    """AC2 / FM-9: asking QMF to own the schedule is refused."""
    result = refuse_schedule_ownership(request="install-cron")
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("signal") == "refuse-schedule-ownership"


def test_refuse_numeric_rpo_rto_is_policy_rejection() -> None:
    """AC2 / FM-6: asking QMF to own numeric RPO/RTO is refused."""
    result = refuse_numeric_rpo_rto(target="backup_recovery_point_objective")
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("signal") == "refuse-numeric-rpo-rto"
    assert result.context.get("backup_recovery_point_objective") is None


def test_cycle_methods_refuse_schedule_and_rpo() -> None:
    """AC2: own_schedule / start_daemon / set_rpo / set_rto always refuse."""
    cycle = OffMachineCycle(_MemoryStorage(), _XorCipher())
    for result in (
        cycle.own_schedule(),
        cycle.start_daemon(),
        cycle.set_recovery_point_objective(seconds=3600),
        cycle.set_recovery_time_objective(seconds=900),
    ):
        assert is_refusal(result)
        assert result.category is RefusalCategory.POLICY_REJECTION


def test_simulated_and_cross_world_are_policy_rejection(
    store: EvidenceStore, tmp_path: Path
) -> None:
    """AC3: world=simulated and a cross-world copy are policy rejections."""
    from qmf.data import OffMachineBackup

    _populate(_world(store))
    cycle = OffMachineCycle(_MemoryStorage(), _XorCipher())
    simulated = cycle.run_once(
        store=store,
        world=World.SIMULATED,
        sample_into=EvidenceStore(tmp_path / "sample-sim"),
    )
    assert is_refusal(simulated)
    assert simulated.category is RefusalCategory.POLICY_REJECTION

    live = _world(store)
    export = live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE)
    assert is_ok(export)
    cross = OffMachineBackup(_MemoryStorage(), _XorCipher()).copy_export(
        export.value, for_world=World.REPLAY
    )
    assert is_refusal(cross)
    assert cross.category is RefusalCategory.POLICY_REJECTION


def test_in_place_sample_root_is_policy_rejection(store: EvidenceStore) -> None:
    """Sample-restore into the source root is refused (never mutate the only copy)."""
    _populate(_world(store))
    cycle = OffMachineCycle(_MemoryStorage(), _XorCipher())
    result = cycle.run_once(store=store, world=World.LIVE, sample_into=store)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("signal") == "refuse-in-place-restore"


def test_no_threads_cron_or_daemon_imported() -> None:
    """qmf.data.cycle must not import threading/sched/cron machinery."""
    import qmf.data.cycle as cycle_mod

    banned = {"threading", "sched", "asyncio", "concurrent", "multiprocessing", "crontab"}
    imported = set(cycle_mod.__dict__) | set(getattr(cycle_mod, "__builtins__", {}))
    # Module globals should not bind banned scheduler names; also check source.
    source = Path(cycle_mod.__file__).read_text(encoding="utf-8")
    for name in banned:
        assert f"import {name}" not in source
        assert f"from {name}" not in source
    assert "Thread" not in imported
    assert "Timer" not in imported
