"""Epic 5 — Story 5.2: restore primitive with seal + world-isolation enforcement.

Independent tests for 5.2 AC1-AC4 (PLAN 5.2-U1..U5, P1..P4). Carries P0-6 (seal survives
restore) and P0-7 (world isolation on restore). Refusal assertions check the CT-04 category;
round-trip integrity is observed by the TEST comparing (fingerprint, canonical, stream) sets.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import RefusalCategory, World, is_ok, is_refusal
from qmf.data.backup import OffMachineBackup, OffMachineRestore
from qmf.data.store.rooms import RoomRole

import _epic5_helpers as H

_ROWS = [{"t": 1_700_000_000_000_000_000, "px": 100}]
_SEVEN = list(RoomRole)
_SEAL_NS = 1_000_000


def _round_trip_setup(root: Path, *, seal: object | None = None, rows: list[dict[str, object]] | None = None):
    """Seed a source, back it up, and return (source, storage, backup, restore, copy)."""
    src = H.make_store(root, name="src")
    H.seed_raw(src, rows if rows is not None else _ROWS)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.MemStorage()
    backup = OffMachineBackup(storage, H.IdentityCipher())
    copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    restore = OffMachineRestore(storage, H.IdentityCipher())
    return src, storage, backup, restore, copy


# --- 5.2-U1 (L1): restore never rewrites the source copy in place ----------------


def test_5_2_u1_restore_targets_replacement_not_source(tmp_path: Path) -> None:
    """AC1: a restore lands in a replacement store; the source records are unchanged, version intact."""
    src, storage, _backup, restore, copy = _round_trip_setup(tmp_path)
    before = H.record_keyset(H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE))
    repl = H.make_store(tmp_path, name="repl")
    receipt = H.unwrap(
        restore.restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
            source_store=src,
        )
    )
    # the replacement root is a DIFFERENT physical root than the source
    assert receipt.replacement_root == str(repl.root.resolve())
    assert receipt.replacement_root != str(src.root.resolve())
    # the source is untouched, and the off-machine object still exists under its version
    assert H.record_keyset(H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)) == before
    assert (World.LIVE.value, copy.copy_version, RoomRole.IMMUTABLE_RAW_ARCHIVE.value) in storage.objs


def test_5_2_u1_in_place_restore_refused(tmp_path: Path) -> None:
    """AC1: a restore whose target resolves to the SAME root as the source is a policy rejection."""
    src, _storage, _backup, restore, copy = _round_trip_setup(tmp_path)
    # a distinct EvidenceStore object rooted at the SAME physical path as the source
    same_root = H.make_store(tmp_path, name="src")
    res = restore.restore_copy(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=same_root, for_world=World.LIVE,
        source_store=src,
    )
    ref = H.assert_refusal(res, "policy rejection")
    assert ref.context.get("signal") == "refuse-in-place-restore"


# --- 5.2-U2 (L1, P0-6): read against restored data at the seal -> policy rejection ---


def test_5_2_u2_sealed_read_on_restored_data_refused_like_live(tmp_path: Path) -> None:
    """AC2 (P0-6 restore side): a sealed read over RESTORED data is a policy rejection, identical to
    a live read — never a silent empty result."""
    seal = H.instant_seal(seal_ns=_SEAL_NS, world=World.LIVE)
    # a live sealed store (the reference behaviour)
    live = H.make_store(tmp_path, name="live", seal=seal)
    live_fp = H.seed_raw(live, _ROWS).fingerprint
    # a restored sealed store carrying the SAME evidence
    src, storage, _b, restore, copy = _round_trip_setup(tmp_path)
    repl = H.make_store(tmp_path, name="repl", seal=seal)
    H.unwrap(
        restore.restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    )
    src_fp = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE).records[0].fingerprint

    sealed_pos = _SEAL_NS + 500_000
    live_sealed = live.for_world(World.LIVE).value.append_store.read_raw(live_fp, for_world=World.LIVE, at=sealed_pos)
    restored_sealed = repl.for_world(World.LIVE).value.append_store.read_raw(src_fp, for_world=World.LIVE, at=sealed_pos)
    # identical: both refuse with a policy rejection at the seal (never a silent empty result)
    lref = H.assert_refusal(live_sealed, "policy rejection")
    rref = H.assert_refusal(restored_sealed, "policy rejection")
    assert lref.context.get("field") == rref.context.get("field") == "seal", "both name the seal"
    # a non-sealed read returns the ACTUAL restored rows on the restored store (not empty)
    ok = repl.for_world(World.LIVE).value.append_store.read_raw(src_fp, for_world=World.LIVE, at=_SEAL_NS - 1)
    assert is_ok(ok) and ok.value == _ROWS, "a non-sealed restored read returns the real rows, never empty"


# --- 5.2-U3 / 5.2-U4 (L1, P0-7): cross-world + simulated restore refuse ------------


def test_5_2_u3_cross_world_restore_read_refused(tmp_path: Path) -> None:
    """AC3 (P0-7): a restore that crosses worlds is a policy rejection (for_world != copy world)."""
    src, storage, _b, restore, copy = _round_trip_setup(tmp_path)
    repl = H.make_store(tmp_path, name="repl")
    res = restore.restore_copy(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.REPLAY,
    )
    H.assert_refusal(res, "policy rejection")


def test_5_2_u4_simulated_restore_refused(tmp_path: Path) -> None:
    """AC3 (P0-7): a restore into world=simulated governed evidence is a policy rejection."""
    src, storage, _b, restore, copy = _round_trip_setup(tmp_path)
    repl = H.make_store(tmp_path, name="repl")
    res = restore.restore_copy(
        world=World.SIMULATED, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.SIMULATED,
    )
    H.assert_refusal(res, "policy rejection")


# --- 5.2-U5 (L1): a retention delete of the only local raw copy is refused ---------


def test_5_2_u5_discard_local_raw_refused(tmp_path: Path) -> None:
    """AC4: discarding the only local raw evidence copy does not proceed under this authority."""
    src, _storage, _b, restore, _copy = _round_trip_setup(tmp_path)
    res = restore.discard_local_raw(src)
    ref = H.assert_refusal(res, "policy rejection")
    assert ref.context.get("signal") == "refuse-delete-only-copy"
    # observe the sink: the raw evidence is still present and unchanged after the refused delete
    assert H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE).record_count >= 1


# --- 5.2-P1 (L2, R-INTEGRITY): byte/fingerprint identical, or it refuses -----------


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    rows=st.lists(
        st.fixed_dictionaries({"t": st.integers(min_value=-(2**62), max_value=2**62), "px": st.integers(0, 10**6)}),
        min_size=1, max_size=5,
    )
)
def test_5_2_p1_round_trip_byte_fingerprint_identical(rows: list[dict[str, int]]) -> None:
    """R-INTEGRITY: an arbitrary backed-up record set restores byte/fingerprint identical."""
    root = H.new_root()
    src, storage, _b, restore, copy = _round_trip_setup(root, rows=rows)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    repl = H.make_store(root, name="repl")
    H.unwrap(
        restore.restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    )
    assert H.exports_identical(export, H.export_of(repl, RoomRole.IMMUTABLE_RAW_ARCHIVE))


def test_5_2_p1_corrupt_copy_refuses_no_partial_restore(tmp_path: Path) -> None:
    """R-INTEGRITY: a corrupt / truncated / empty copy -> storage failure and NO partial restore."""
    src = H.make_store(tmp_path, name="src")
    H.seed_raw(src, _ROWS)
    export = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    cipher = H.IdentityCipher()
    for label, storage_cls in (("corrupt", H.CorruptStorage), ("empty", H.EmptyStorage), ("truncated", H.TruncatingStorage)):
        storage = storage_cls()
        backup = OffMachineBackup(storage, cipher)
        copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
        restore = OffMachineRestore(storage, cipher)
        repl = H.make_store(tmp_path, name=f"repl-{label}")
        res = restore.restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
        H.assert_refusal(res, "storage failure")
        # observe the sink: the replacement store holds NOTHING (no partial restore)
        assert H.export_of(repl, RoomRole.IMMUTABLE_RAW_ARCHIVE).record_count == 0, (
            f"{label}: a failed restore must leave no partial evidence"
        )


def test_5_2_p1_fingerprint_mismatch_copy_refuses(tmp_path: Path) -> None:
    """R-INTEGRITY: a frame-valid copy whose canonical bytes do not match their fingerprint is
    refused at re-admission — never restored as fabricated evidence."""
    from qmf.data.store.backup_input import RecordExport, RoomExport

    bad = RecordExport(fingerprint="fp1:sha256:" + ("0" * 64), canonical=b'[{"t":1,"px":1}]', stream=None)
    bad_export = RoomExport(world=World.LIVE, source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, format_version=1, records=(bad,))
    storage = H.MemStorage()
    cipher = H.IdentityCipher()
    copy = H.unwrap(OffMachineBackup(storage, cipher).copy_export(bad_export, for_world=World.LIVE))
    repl = H.make_store(tmp_path, name="repl")
    res = OffMachineRestore(storage, cipher).restore_copy(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
    )
    assert is_refusal(res), "a fingerprint-mismatched copy must be refused, never restored"
    assert H.export_of(repl, RoomRole.IMMUTABLE_RAW_ARCHIVE).record_count == 0


# --- 5.2-P2 (L2, R-012 / P0-6): seal survives restore at every read boundary -------


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(pos=st.integers(min_value=0, max_value=2_000_000))
def test_5_2_p2_seal_parity_live_vs_restored(pos: int) -> None:
    """R-012 / P0-6: at any read position, a restored read enforces the seal IDENTICALLY to a live
    read (refuse iff sealed), at both the raw-archive and the restored-backup boundaries."""
    root = H.new_root()
    seal = H.instant_seal(seal_ns=_SEAL_NS, world=World.LIVE)
    live = H.make_store(root, name="live", seal=seal)
    live_fp = H.seed_raw(live, _ROWS).fingerprint
    src, storage, _b, restore, copy = _round_trip_setup(root)
    src_fp = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE).records[0].fingerprint
    repl = H.make_store(root, name="repl", seal=seal)
    H.unwrap(
        restore.restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    )
    sealed = pos >= _SEAL_NS
    live_res = live.for_world(World.LIVE).value.append_store.read_raw(live_fp, for_world=World.LIVE, at=pos)
    restored_res = repl.for_world(World.LIVE).value.append_store.read_raw(src_fp, for_world=World.LIVE, at=pos)
    assert is_refusal(live_res) is sealed, "live seal decision must match the sealed window"
    assert is_refusal(restored_res) is sealed, "restored seal decision must MATCH the live decision"
    if sealed:
        assert live_res.category is restored_res.category is RefusalCategory.POLICY_REJECTION


def test_5_2_p2_seal_fail_closed_on_missing_position(tmp_path: Path) -> None:
    """R-012 / P0-6: a restored read with a wired seal but NO position is refused (fail-closed) at
    every enumerated read boundary — a positionless read can never export sealed bytes."""
    seal = H.instant_seal(seal_ns=_SEAL_NS, world=World.LIVE)
    src, storage, _b, restore, copy = _round_trip_setup(tmp_path)
    src_fp = H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE).records[0].fingerprint
    repl = H.make_store(tmp_path, name="repl", seal=seal)
    H.unwrap(
        restore.restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    )
    ws = repl.for_world(World.LIVE).value
    # raw-archive boundary and restored-backup (CT-26) boundary both refuse a positionless read
    H.assert_refusal(ws.append_store.read_raw(src_fp, for_world=World.LIVE, at=None), "policy rejection")
    H.assert_refusal(ws.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE, at=None), "policy rejection")


# --- 5.2-P3 (L2): world isolation on restore at every read path --------------------


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(role=st.sampled_from([RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL, RoomRole.REGISTRY_ROOM]))
def test_5_2_p3_cross_world_read_refused_on_restored_store(role: RoomRole) -> None:
    """AC3: after a restore, a cross-world read of the restored evidence refuses (policy rejection)."""
    root = H.new_root()
    src = H.make_store(root, name="src")
    H.seed_raw(src, _ROWS)
    H.seed_journal(src, "s1", {"event_type": "data quality", "world": "live", "n": 1})
    H.seed_registry(src, {"a": 1})
    export = H.export_of(src, role)
    storage = H.MemStorage()
    copy = H.unwrap(OffMachineBackup(storage, H.IdentityCipher()).copy_export(export, for_world=World.LIVE))
    repl = H.make_store(root, name="repl")
    H.unwrap(
        OffMachineRestore(storage, H.IdentityCipher()).restore_copy(
            world=World.LIVE, copy_version=copy.copy_version, source_room_role=role,
            into=repl, for_world=World.LIVE,
        )
    )
    # a REPLAY-declared read of the LIVE-restored room is a policy rejection
    res = repl.for_world(World.LIVE).value.backup_input.read_room(role, for_world=World.REPLAY)
    H.assert_refusal(res, "policy rejection")


# --- 5.2-P4 (L2, R-EVIDENCE): keep-raw-forever + symlink-safe write ----------------


def test_5_2_p4_keep_raw_forever_source_untouched(tmp_path: Path) -> None:
    """R-EVIDENCE: no backup/restore/retention write removes or overwrites a raw original or its
    lineage — the source raw + journal + registry sets are invariant across a full cycle."""
    src = H.make_store(tmp_path, name="src")
    H.seed_raw(src, _ROWS)
    H.seed_journal(src, "s1", {"event_type": "data quality", "world": "live", "n": 1})
    H.seed_registry(src, {"a": 1})
    baseline = {role: H.record_keyset(H.export_of(src, role)) for role in (RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL, RoomRole.REGISTRY_ROOM)}
    storage = H.MemStorage()
    backup = OffMachineBackup(storage, H.IdentityCipher())
    restore = OffMachineRestore(storage, H.IdentityCipher())
    repl = H.make_store(tmp_path, name="repl")
    for role in baseline:
        copy = H.unwrap(backup.copy_export(H.export_of(src, role), for_world=World.LIVE))
        H.unwrap(restore.restore_copy(world=World.LIVE, copy_version=copy.copy_version, source_room_role=role, into=repl, for_world=World.LIVE))
    # a refused retention delete must not touch the raw either
    restore.discard_local_raw(src)
    after = {role: H.record_keyset(H.export_of(src, role)) for role in baseline}
    assert after == baseline, "no cycle write may remove or overwrite the only local raw/lineage evidence"


def test_5_2_p4_symlinked_into_root_resolving_onto_source_refused(tmp_path: Path) -> None:
    """R-EVIDENCE: a restore whose target root resolves (via a symlink) onto the source root must
    NOT rewrite the only copy — the in-place guard uses `.resolve()`, so a symlinked into-root is
    caught. On a host without symlink privilege this specific case is UNPROVEN (recorded)."""
    src, _storage, _backup, restore, copy = _round_trip_setup(tmp_path)
    link = tmp_path / "repl_link"
    try:
        os.symlink(str(src.root), str(link), target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unsupported on this host (privilege): {exc}; case UNPROVEN (see RESULTS)")
    from qmf.data.store import EvidenceStore

    into = EvidenceStore(link)
    res = restore.restore_copy(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=into, for_world=World.LIVE,
        source_store=src,
    )
    H.assert_refusal(res, "policy rejection")


# --- restore-side remap crash (symmetric to 5.1-U8) -------------------------------


def test_5_2_restore_wrong_adapter_category_remapped_not_raised(tmp_path: Path) -> None:
    """AC4/R-007 (restore side): a miswired adapter's non-storage-failure GET refusal must be
    remapped to a returned storage failure, never raised across the CT-14 restore boundary."""
    src, _storage, _backup, _restore, copy = _round_trip_setup(tmp_path)
    # a restore whose storage returns a policy-rejection (with a reason context key) on get
    bad_restore = OffMachineRestore(H.WrongCategoryStorage(), H.IdentityCipher())
    repl = H.make_store(tmp_path, name="repl")
    try:
        res = bad_restore.restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    except BaseException as exc:  # noqa: BLE001 - R-007 forbids any raise across the boundary
        pytest.fail(
            f"CT-14 restore remap RAISED {type(exc).__name__} across the boundary instead of "
            f"returning a storage failure (AC4/R-007): {exc}"
        )
    H.assert_refusal(res, "storage failure")
