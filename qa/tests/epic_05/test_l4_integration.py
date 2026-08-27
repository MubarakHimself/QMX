"""Epic 5 — L4 integration (tier-2 backup/restore targets).

5.1-I1 object-storage fault simulation + durability-not-from-ack; 5.2-I1 real multi-room
round-trip (byte/fp identical or refuses); 5.2-I2 seal survives a real restore; 5.3-I1
migration integration; 5.4-I1 nightly-cycle wiring. These physically cross the CT-14/CT-26
boundary through the real store engines; a failing case is a FINDING.
"""

from __future__ import annotations

from pathlib import Path

from qmf.core import World, is_ok, is_refusal
from qmf.data.backup import OffMachineBackup, OffMachineRestore
from qmf.data.cycle import OffMachineCycle
from qmf.data.store.rooms import RoomRole
from qmf.data.verify import OffMachineVerify, VerifyKind, migrate_evidence, refuse_snapshot_alone_claim

import _epic5_helpers as H

_ROWS = [{"t": 1_700_000_000_000_000_000, "px": 100}, {"t": 1_700_000_000_000_000_050, "px": 101}]
_RESTORABLE = (RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL, RoomRole.REGISTRY_ROOM)


def _seed(store: object) -> None:
    H.seed_raw(store, _ROWS)
    H.seed_journal(store, "s1", {"event_type": "data quality", "world": "live", "n": 1})
    H.seed_registry(store, {"a": 1})


# --- 5.1-I1 (L4): object-storage fault sim + durability never inferred from an ack --


def test_5_1_i1_object_storage_fault_sim(tmp_path: Path) -> None:
    """R-007: each object-storage fault -> RETURNED storage failure (never raised)."""
    src = H.make_store(tmp_path, name="src")
    _seed(src)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    cipher = H.IdentityCipher()
    # put-side faults (backup)
    for storage in (H.UnreachableStorage(), H.OSErrorStorage(), H.TimeoutStorage(), H.RejectingStorage()):
        res = OffMachineBackup(storage, cipher).copy_export(export, for_world=World.LIVE)
        H.assert_refusal(res, "storage failure")
    # get-side faults (restore): corrupt / empty / truncated object
    good = H.MemStorage()
    copy = H.unwrap(OffMachineBackup(good, cipher).copy_export(export, for_world=World.LIVE))
    for storage_cls in (H.CorruptStorage, H.EmptyStorage, H.TruncatingStorage):
        storage = storage_cls()
        storage.objs = dict(good.objs)  # same objects, faulted read
        res = OffMachineRestore(storage, cipher).restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name=f"r-{storage_cls.__name__}"),
            for_world=World.LIVE,
        )
        H.assert_refusal(res, "storage failure")


def test_5_1_i1_durability_not_inferred_from_ack(tmp_path: Path) -> None:
    """A successful put ACK alone never establishes recoverability — only a verify primitive does."""
    src = H.make_store(tmp_path, name="src")
    _seed(src)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.MemStorage()
    cipher = H.IdentityCipher()
    receipt = H.unwrap(OffMachineBackup(storage, cipher).copy_export(export, for_world=World.LIVE))
    assert storage.put_calls, "the put was acknowledged"
    # a snapshot/ack alone yields no claim
    H.assert_refusal(refuse_snapshot_alone_claim(copy_version=receipt.copy_version), "policy rejection")
    # only the verify primitive, after a read-back, yields a recoverability claim
    claim = H.unwrap(
        OffMachineVerify(storage, cipher).sample_restore(
            world=World.LIVE, copy_version=receipt.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="v"),
            for_world=World.LIVE, expected=export, source_store=src,
        )
    )
    assert claim.kind is VerifyKind.SAMPLE_RESTORE


# --- 5.2-I1 (L4): real multi-room round-trip — byte/fp identical, or refuses --------


def test_5_2_i1_real_multi_room_round_trip_identical(tmp_path: Path) -> None:
    """R-INTEGRITY: back up raw+journal+registry -> restore into a replacement -> every record identical."""
    src = H.make_store(tmp_path, name="src")
    _seed(src)
    storage = H.MemStorage()
    cipher = H.IdentityCipher()
    backup = OffMachineBackup(storage, cipher)
    restore = OffMachineRestore(storage, cipher)
    repl = H.make_store(tmp_path, name="repl")
    for role in _RESTORABLE:
        export = H.export_of(src, role)
        copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
        H.unwrap(
            restore.restore_copy(
                world=World.LIVE, copy_version=copy.copy_version, source_room_role=role,
                into=repl, for_world=World.LIVE, source_store=src,
            )
        )
        assert H.exports_identical(export, H.export_of(repl, role)), f"{role.value} round-trip not identical"


def test_5_2_i1_corrupt_in_transit_no_partial_restore(tmp_path: Path) -> None:
    """R-INTEGRITY: a copy corrupted in transit -> storage failure, and NO partial restore lands."""
    src = H.make_store(tmp_path, name="src")
    _seed(src)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    cipher = H.IdentityCipher()
    good = H.MemStorage()
    copy = H.unwrap(OffMachineBackup(good, cipher).copy_export(export, for_world=World.LIVE))
    corrupt = H.CorruptStorage()
    corrupt.objs = dict(good.objs)
    repl = H.make_store(tmp_path, name="repl")
    res = OffMachineRestore(corrupt, cipher).restore_copy(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
    )
    H.assert_refusal(res, "storage failure")
    assert H.export_of(repl, RoomRole.IMMUTABLE_RAW_ARCHIVE).record_count == 0


# --- 5.2-I2 (L4): seal survives a real restore -------------------------------------


def test_5_2_i2_seal_survives_real_restore(tmp_path: Path) -> None:
    """R-012 / P0-6: a read into the sealed period through a REAL restored backup is a policy rejection."""
    seal = H.instant_seal(seal_ns=1_000_000, world=World.LIVE)
    src = H.make_store(tmp_path, name="src")
    fp = H.seed_raw(src, _ROWS).fingerprint
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE, at=None)
    storage = H.MemStorage()
    cipher = H.IdentityCipher()
    copy = H.unwrap(OffMachineBackup(storage, cipher).copy_export(export, for_world=World.LIVE))
    repl = H.make_store(tmp_path, name="repl", seal=seal)
    H.unwrap(
        OffMachineRestore(storage, cipher).restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    )
    ws = repl.for_world(World.LIVE).value
    # sealed position -> refused; the same read on a live store with the same seal also refuses
    H.assert_refusal(ws.append_store.read_raw(fp, for_world=World.LIVE, at=1_500_000), "policy rejection")
    live = H.make_store(tmp_path, name="live", seal=seal)
    live_fp = H.seed_raw(live, _ROWS).fingerprint
    H.assert_refusal(
        live.for_world(World.LIVE).value.append_store.read_raw(live_fp, for_world=World.LIVE, at=1_500_000),
        "policy rejection",
    )


# --- 5.3-I1 (L4): migration integration --------------------------------------------


def test_5_3_i1_migration_integration_only_copy_intact(tmp_path: Path) -> None:
    """R-EVIDENCE: a real migration keeps the source intact + mints a fresh backup; bad backup-first aborts."""
    src = H.make_store(tmp_path, name="src")
    _seed(src)
    before = {r: H.record_keyset(H.export_of(src, r)) for r in _RESTORABLE}
    storage = H.MemStorage()
    cipher = H.IdentityCipher()
    report = H.unwrap(
        migrate_evidence(
            source=src, destination=H.make_store(tmp_path, name="dest"),
            verify_into=H.make_store(tmp_path, name="vfy"), world=World.LIVE,
            backup=OffMachineBackup(storage, cipher), restore=OffMachineRestore(storage, cipher),
            verify=OffMachineVerify(storage, cipher),
        )
    )
    assert {r: H.record_keyset(H.export_of(src, r)) for r in _RESTORABLE} == before, "source intact"
    assert len(report.backup_receipts) >= 1 and report.backed_up is True
    # a migration whose backup-first fails aborts before any migrate write
    dead = H.UnreachableStorage()
    dest2 = H.make_store(tmp_path, name="dest2")
    res = migrate_evidence(
        source=src, destination=dest2, verify_into=H.make_store(tmp_path, name="vfy2"), world=World.LIVE,
        backup=OffMachineBackup(dead, cipher), restore=OffMachineRestore(dead, cipher),
        verify=OffMachineVerify(dead, cipher),
    )
    H.assert_refusal(res, "storage failure")
    assert H.export_of(dest2, RoomRole.IMMUTABLE_RAW_ARCHIVE).record_count == 0, "no migrate write after a failed backup-first"


# --- 5.4-I1 (L4): nightly-cycle wiring (app-driven) --------------------------------


def test_5_4_i1_nightly_cycle_wiring(tmp_path: Path) -> None:
    """AC1/AC3: the app driver wires CT-14 copy + sample-restore + full-restore rehearsal per world;
    a simulated cycle is refused (the schedule is app-driven, not a QMF-owned scheduler)."""
    store = H.make_store(tmp_path, name="store")
    _seed(store)
    storage = H.MemStorage()
    cycle = OffMachineCycle(storage, H.IdentityCipher())
    report = H.unwrap(
        cycle.run_once(
            store=store, world=World.LIVE, sample_into=H.make_store(tmp_path, name="s"),
            full_into=H.make_store(tmp_path, name="f"), include_full_rehearsal=True,
        )
    )
    # backup (CT-14) + sample-restore + full-restore rehearsal all ran as one app-driven cycle
    assert len(report.backup_receipts) == 7
    assert report.sample_restore.kind is VerifyKind.SAMPLE_RESTORE
    assert report.full_restore is not None and report.full_restore.kind is VerifyKind.FULL_RESTORE_REHEARSAL
    # the cycle is app-invoked; a simulated cycle is a policy rejection (no QMF-owned scheduler)
    H.assert_refusal(
        cycle.run_once(store=store, world=World.SIMULATED, sample_into=H.make_store(tmp_path, name="s2")),
        "policy rejection",
    )
