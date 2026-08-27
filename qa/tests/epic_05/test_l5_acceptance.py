"""Epic 5 — L5 acceptance: SCN-0004 (backup does not claim recoverability before its
boundaries exist).

ACC-1: the store holds an original observation, its correction, and their lineage. An agent
snapshots, transmits off-machine, restores into a replacement store, runs a migration, and asks
to declare disaster recovery complete. Then: recoverability is claimed ONLY through the verify
primitives; the migration runs preflight -> backup-first -> dry-run -> migrate -> verify and never
mutates the only copy; the restored read still enforces the seal and world isolation; timestamps
round-trip verbatim; no credential enters evidence. This asserts CHAIN integrity + lineage +
no-only-copy-mutation (the component refusals are covered lower).
"""

from __future__ import annotations

from pathlib import Path

from qmf.core import World, is_ok, is_refusal
from qmf.data.backup import OffMachineBackup, OffMachineRestore
from qmf.data.store.rooms import RoomRole
from qmf.data.verify import (
    MIGRATION_SEQUENCE,
    OffMachineVerify,
    VerifyKind,
    migrate_evidence,
    refuse_snapshot_alone_claim,
)

import _epic5_helpers as H

_ORIGINAL_T = 1_700_000_000_123_456_789  # a precise int64 UTC-ns instant
_ORIGINAL = [{"t": _ORIGINAL_T, "px": 100}]
_RESTORABLE = (RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL, RoomRole.REGISTRY_ROOM)


def _seed_original_and_correction(store: object) -> str:
    """Seed an original raw observation, a correction registry record, and a lineage edge.

    Returns the original raw fingerprint so a restored read can be checked."""
    raw = H.seed_raw(store, _ORIGINAL)
    ws = H.world_store(store, World.LIVE)
    original_rec = H.unwrap(ws.registry_room.put_record({"obs": "original", "px": 100}, kind="observation", format_version=1))
    correction_rec = H.unwrap(ws.registry_room.put_record({"obs": "correction", "px": 101}, kind="observation", format_version=1))
    # a lineage edge linking the correction to the original (correction_of)
    H.unwrap(
        ws.registry_room.append_lineage_edge(
            "corrections", H.writer(stream="corrections"),
            {"supersedes": original_rec.fingerprint.value, "by": correction_rec.fingerprint.value},
        )
    )
    return raw.fingerprint.value


def test_acc_1_scn_0004_backup_restore_migrate_chain(tmp_path: Path) -> None:
    src = H.make_store(tmp_path, name="src")
    original_fp = _seed_original_and_correction(src)
    storage = H.MemStorage()
    cipher = H.XorCipher(key=0x2B)  # a real (non-identity) cipher; its key stays node/ops
    backup = OffMachineBackup(storage, cipher)
    restore = OffMachineRestore(storage, cipher)
    verify = OffMachineVerify(storage, cipher)

    baseline = {r: H.record_keyset(H.export_of(src, r)) for r in _RESTORABLE}

    # --- snapshot off-machine (every restorable room) ---
    copies: dict[RoomRole, int] = {}
    for role in _RESTORABLE:
        rc = H.unwrap(backup.copy_export(H.export_of(src, role), for_world=World.LIVE))
        copies[role] = rc.copy_version
        assert rc.encryption_required is True

    # --- Then: recoverability is claimed ONLY through the verify primitives ---
    H.assert_refusal(refuse_snapshot_alone_claim(world=World.LIVE), "policy rejection")
    claim = H.unwrap(
        verify.sample_restore(
            world=World.LIVE, copy_version=copies[RoomRole.IMMUTABLE_RAW_ARCHIVE],
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="v"),
            for_world=World.LIVE, expected=H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE), source_store=src,
        )
    )
    assert claim.kind is VerifyKind.SAMPLE_RESTORE

    # --- restore into a replacement store (never rewriting the only copy) ---
    repl = H.make_store(tmp_path, name="repl")
    for role in _RESTORABLE:
        H.unwrap(
            restore.restore_copy(
                world=World.LIVE, copy_version=copies[role], source_room_role=role,
                into=repl, for_world=World.LIVE, source_store=src,
            )
        )
    # lineage + all rooms round-trip byte/fingerprint identical
    for role in _RESTORABLE:
        assert H.exports_identical(H.export_of(src, role), H.export_of(repl, role)), f"{role.value} lineage/round-trip"

    # --- timestamps round-trip verbatim ---
    restored_rows = H.unwrap(
        repl.for_world(World.LIVE).value.append_store.read_raw(original_fp, for_world=World.LIVE)
    )
    assert restored_rows[0]["t"] == _ORIGINAL_T and type(restored_rows[0]["t"]) is int

    # --- migration runs the ordered sequence and never mutates the only copy ---
    report = H.unwrap(
        migrate_evidence(
            source=src, destination=H.make_store(tmp_path, name="dest"),
            verify_into=H.make_store(tmp_path, name="mvfy"), world=World.LIVE,
            backup=backup, restore=restore, verify=verify,
        )
    )
    assert report.stages_completed == MIGRATION_SEQUENCE
    assert report.recoverability.kind is VerifyKind.FULL_RESTORE_REHEARSAL
    assert {r: H.record_keyset(H.export_of(src, r)) for r in _RESTORABLE} == baseline, "only copy never mutated"

    # --- the restored read still enforces the seal and world isolation ---
    seal = H.instant_seal(seal_ns=1_000_000, world=World.LIVE)
    sealed_repl = H.make_store(tmp_path, name="sealed_repl", seal=seal)
    H.unwrap(
        restore.restore_copy(
            world=World.LIVE, copy_version=copies[RoomRole.IMMUTABLE_RAW_ARCHIVE],
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=sealed_repl, for_world=World.LIVE,
        )
    )
    sws = sealed_repl.for_world(World.LIVE).value
    H.assert_refusal(sws.append_store.read_raw(original_fp, for_world=World.LIVE, at=1_500_000), "policy rejection")  # seal
    H.assert_refusal(sws.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.REPLAY), "policy rejection")  # world isolation

    # --- no credential enters evidence ---
    # the cipher key lives only inside the injected cipher; it never surfaces in any receipt,
    # claim, or migration report the chain produced.
    evidence_blob = (repr(report) + repr(claim) + repr(report.backup_receipts)).lower()
    for token in ("credential", "secret", "password", "private_key", "access_key"):
        assert token not in evidence_blob, f"no {token} may enter backup evidence (SCN-0004)"
    for rc in report.backup_receipts:
        assert rc.encryption_required is True, "every off-machine copy carries the encryption-required pointer"
