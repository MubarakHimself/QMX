"""Epic 5 — Story 5.3: verify primitives (sample-restore + full-restore rehearsal) + migration.

Independent tests for 5.3 AC1-AC4 (PLAN 5.3-U1..U6, P1..P2). Recoverability is claimed ONLY
through the verify primitives; a corrupt/failed restore yields a storage failure, never a
success claim; a migration runs preflight -> backup-first -> dry-run -> migrate -> verify and
never mutates the only copy. Refusals check the CT-04 category.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import World, is_ok, is_refusal
from qmf.data.backup import OffMachineBackup, OffMachineRestore
from qmf.data.store.rooms import RoomRole
from qmf.data.verify import (
    MIGRATION_SEQUENCE,
    NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE,
    NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE,
    NODE_OPS_BACKUP_RETENTION_PERIOD,
    NODE_OPS_RESTORE_VERIFICATION_CADENCE,
    MigrationStage,
    OffMachineVerify,
    RecoverabilityClaim,
    StoreMigrationReport,
    VerifyKind,
    migrate_evidence,
    refuse_snapshot_alone_claim,
)

import _epic5_helpers as H

_ROWS = [{"t": 1_700_000_000_000_000_000, "px": 100}]
_ROWS_B = [{"t": 42, "px": 7}]


def _seed_source(root: Path) -> object:
    src = H.make_store(root, name="src")
    H.seed_raw(src, _ROWS)
    H.seed_journal(src, "s1", {"event_type": "data quality", "world": "live", "n": 1})
    H.seed_registry(src, {"a": 1})
    return src


def _kit(root: Path):
    storage = H.MemStorage()
    cipher = H.IdentityCipher()
    return (
        storage,
        OffMachineBackup(storage, cipher),
        OffMachineRestore(storage, cipher),
        OffMachineVerify(storage, cipher),
    )


# --- 5.3-U1 (L1): recoverability claimed ONLY through verify; snapshot alone refused ---


def test_5_3_u1_snapshot_alone_yields_no_claim(tmp_path: Path) -> None:
    """AC1: a snapshot / upload acknowledgement alone yields NO recoverability claim."""
    res = refuse_snapshot_alone_claim(world=World.LIVE, copy_version=1, source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE)
    ref = H.assert_refusal(res, "policy rejection")
    assert ref.context.get("signal") == "refuse-snapshot-alone-claim"


# --- 5.3-U2 (L1): both verify primitives exposed as first-class operations ---------


def test_5_3_u2_both_verify_primitives_run(tmp_path: Path) -> None:
    """AC1/AC4: sample-restore AND full-restore rehearsal each run and return a verdict/claim."""
    src = _seed_source(tmp_path)
    storage, backup, restore, verify = _kit(tmp_path)
    raw_export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    jrn_export = H.export_of(src, RoomRole.JOURNAL)
    raw_copy = H.unwrap(backup.copy_export(raw_export, for_world=World.LIVE))
    jrn_copy = H.unwrap(backup.copy_export(jrn_export, for_world=World.LIVE))

    sample = H.unwrap(
        verify.sample_restore(
            world=World.LIVE, copy_version=raw_copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="s1"),
            for_world=World.LIVE, expected=raw_export, source_store=src,
        )
    )
    assert sample.kind is VerifyKind.SAMPLE_RESTORE

    full = H.unwrap(
        verify.full_restore_rehearsal(
            world=World.LIVE,
            copies={RoomRole.IMMUTABLE_RAW_ARCHIVE: raw_copy.copy_version, RoomRole.JOURNAL: jrn_copy.copy_version},
            into=H.make_store(tmp_path, name="f1"), for_world=World.LIVE,
            expected={RoomRole.IMMUTABLE_RAW_ARCHIVE: raw_export, RoomRole.JOURNAL: jrn_export},
            source_store=src,
        )
    )
    assert full.kind is VerifyKind.FULL_RESTORE_REHEARSAL


# --- 5.3-U3 (L1): a matching sample-restore confirms recoverable --------------------


def test_5_3_u3_matching_sample_restore_confirms_recoverable(tmp_path: Path) -> None:
    """AC2: a sample-restore whose read-back byte/fp matches the source confirms recoverability."""
    src = _seed_source(tmp_path)
    storage, backup, restore, verify = _kit(tmp_path)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    claim = H.unwrap(
        verify.sample_restore(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="s"),
            for_world=World.LIVE, expected=export, source_store=src,
        )
    )
    assert claim.documented_restore_path == str(src.root.resolve())
    assert claim.record_count == export.record_count
    assert claim.rooms[0].source_room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE


# --- 5.3-U4 (L1): a corrupt/failed restore yields NO recoverability claim -----------


def test_5_3_u4_corrupt_restore_no_claim(tmp_path: Path) -> None:
    """AC2: a corrupt restore returns a storage failure, never a success/recoverability claim."""
    src = _seed_source(tmp_path)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.CorruptStorage()
    cipher = H.IdentityCipher()
    backup = OffMachineBackup(storage, cipher)
    verify = OffMachineVerify(storage, cipher)
    copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    res = verify.sample_restore(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="s"),
        for_world=World.LIVE, expected=export, source_store=src,
    )
    ref = H.assert_refusal(res, "storage failure")
    assert not isinstance(ref, RecoverabilityClaim), "a corrupt restore must never return a claim"


def test_5_3_u4_mismatch_restore_no_claim(tmp_path: Path) -> None:
    """AC2: a restore whose read-back does NOT match the expected evidence yields no claim."""
    src = _seed_source(tmp_path)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage, backup, restore, verify = _kit(tmp_path)
    copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    # a DIFFERENT expected export (built from other rows) than what was backed up
    other_src = H.make_store(tmp_path, name="other")
    H.seed_raw(other_src, _ROWS_B)
    wrong_expected = H.export_of(other_src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    res = verify.sample_restore(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="s"),
        for_world=World.LIVE, expected=wrong_expected, source_store=src,
    )
    ref = H.assert_refusal(res, "storage failure")
    assert ref.context.get("signal") == "verify-mismatch"


# --- 5.3-U5 (L1): migration runs the ordered sequence; only copy backed up first ---


def test_5_3_u5_migration_ordered_sequence_never_in_place(tmp_path: Path) -> None:
    """AC3: a migration runs preflight -> backup-first -> dry-run -> migrate -> verify; source intact."""
    src = _seed_source(tmp_path)
    storage, backup, restore, verify = _kit(tmp_path)
    before = {r: H.record_keyset(H.export_of(src, r)) for r in (RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL, RoomRole.REGISTRY_ROOM)}
    dest = H.make_store(tmp_path, name="dest")
    vfy = H.make_store(tmp_path, name="vfy")
    report = H.unwrap(
        migrate_evidence(
            source=src, destination=dest, verify_into=vfy, world=World.LIVE,
            backup=backup, restore=restore, verify=verify,
        )
    )
    assert report.stages_completed == MIGRATION_SEQUENCE, "the exact ordered 5-stage sequence"
    assert report.stages_completed[0] is MigrationStage.PREFLIGHT
    assert report.stages_completed[1] is MigrationStage.BACKUP_FIRST, "backup-first precedes migrate"
    assert report.backed_up is True and len(report.backup_receipts) >= 1
    assert report.recoverability.kind is VerifyKind.FULL_RESTORE_REHEARSAL
    # the source (documented restore path) is UNTOUCHED; the destination received the evidence
    after = {r: H.record_keyset(H.export_of(src, r)) for r in before}
    assert after == before, "a migration never mutates the only copy in place"
    assert report.destination_root == str(dest.root.resolve())
    assert report.restore_path == str(src.root.resolve())


def test_5_3_u5_migration_in_place_refused(tmp_path: Path) -> None:
    """AC3: a migration whose destination is the source root is a policy rejection (never in-place)."""
    src = _seed_source(tmp_path)
    storage, backup, restore, verify = _kit(tmp_path)
    same = H.make_store(tmp_path, name="src")
    res = migrate_evidence(
        source=src, destination=same, verify_into=H.make_store(tmp_path, name="vfy"), world=World.LIVE,
        backup=backup, restore=restore, verify=verify,
    )
    H.assert_refusal(res, "policy rejection")


# --- 5.3-U6 (L1): primitives exposed WITHOUT filling the numeric registry keys -----


def test_5_3_u6_numeric_targets_unfilled(tmp_path: Path) -> None:
    """AC4: the primitives expose sample/full-restore WITHOUT filling the four numeric registry keys."""
    # the node/ops-sitting numeric pointers stay null (unfilled) — never a recommendation
    assert NODE_OPS_RESTORE_VERIFICATION_CADENCE is None
    assert NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE is None
    assert NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE is None
    assert NODE_OPS_BACKUP_RETENTION_PERIOD is None
    # a real recoverability claim carries NO rpo/rto/retention/cadence field (independent observation)
    src = _seed_source(tmp_path)
    storage, backup, restore, verify = _kit(tmp_path)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    claim = H.unwrap(
        verify.sample_restore(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="s"),
            for_world=World.LIVE, expected=export, source_store=src,
        )
    )
    claim_fields = {f.name.lower() for f in dataclasses.fields(claim)}
    for banned in ("rpo", "rto", "recovery_point", "recovery_time", "retention", "cadence"):
        assert not any(banned in n for n in claim_fields), f"a claim must not carry a numeric {banned} field"


# --- 5.3-P1 (L2, R-INTEGRITY): verify NEVER fabricates a claim ----------------------


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mode=st.sampled_from(["corrupt", "empty", "truncated"]))
def test_5_3_p1_verify_never_claims_on_bad_copy(mode: str) -> None:
    """R-INTEGRITY: for any corrupt/missing/truncated copy, verify returns a storage failure and no claim."""
    root = H.new_root()
    src = H.make_store(root, name="src")
    H.seed_raw(src, _ROWS)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = {"corrupt": H.CorruptStorage, "empty": H.EmptyStorage, "truncated": H.TruncatingStorage}[mode]()
    cipher = H.IdentityCipher()
    backup = OffMachineBackup(storage, cipher)
    verify = OffMachineVerify(storage, cipher)
    copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    res = verify.sample_restore(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(root, name="s"),
        for_world=World.LIVE, expected=export, source_store=src,
    )
    assert is_refusal(res) and res.category.value == "storage failure", f"{mode}: no claim on a bad copy"


# --- 5.3-P2 (L2, R-EVIDENCE): migration preserves the only copy; cannot-back-up refuses ---


def test_5_3_p2_migration_that_cannot_back_up_first_refuses(tmp_path: Path) -> None:
    """R-EVIDENCE: if the backup-first step fails, the migration REFUSES before writing the destination."""
    src = _seed_source(tmp_path)
    before = {r: H.record_keyset(H.export_of(src, r)) for r in (RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL, RoomRole.REGISTRY_ROOM)}
    # backup storage is unreachable -> copy_export fails at backup-first
    dead_storage = H.UnreachableStorage()
    cipher = H.IdentityCipher()
    backup = OffMachineBackup(dead_storage, cipher)
    restore = OffMachineRestore(dead_storage, cipher)
    verify = OffMachineVerify(dead_storage, cipher)
    dest = H.make_store(tmp_path, name="dest")
    res = migrate_evidence(
        source=src, destination=dest, verify_into=H.make_store(tmp_path, name="vfy"), world=World.LIVE,
        backup=backup, restore=restore, verify=verify,
    )
    H.assert_refusal(res, "storage failure")
    # the destination received NOTHING and the source is unchanged
    assert H.export_of(dest, RoomRole.IMMUTABLE_RAW_ARCHIVE).record_count == 0, "no migrate write before a good backup"
    after = {r: H.record_keyset(H.export_of(src, r)) for r in before}
    assert after == before, "the only copy stays intact when backup-first fails"


def test_5_3_p2_successful_migration_leaves_source_and_fresh_backup(tmp_path: Path) -> None:
    """R-EVIDENCE: after a successful migration the source is intact AND a fresh backup version exists."""
    src = _seed_source(tmp_path)
    storage, backup, restore, verify = _kit(tmp_path)
    before = H.record_keyset(H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE))
    report = H.unwrap(
        migrate_evidence(
            source=src, destination=H.make_store(tmp_path, name="dest"),
            verify_into=H.make_store(tmp_path, name="vfy"), world=World.LIVE,
            backup=backup, restore=restore, verify=verify,
        )
    )
    assert H.record_keyset(H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)) == before
    # a fresh off-machine backup object exists for the raw room (observed in the sink)
    raw_keys = [k for k in storage.objs if k[2] == RoomRole.IMMUTABLE_RAW_ARCHIVE.value]
    assert raw_keys, "backup-first produced a fresh off-machine copy of the raw evidence"
    assert report.recoverability.kind is VerifyKind.FULL_RESTORE_REHEARSAL
