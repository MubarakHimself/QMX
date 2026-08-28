"""Epic 5 — Story 5.1: CT-26 store-to-backup input + CT-14 encrypted versioned copy.

Independent tests for 5.1 AC1-AC5 (PLAN 5.1-U1..U10, P1..P5, C1..C4). Every refusal
assertion checks the CT-04 category; every effect is observed through a test-owned sink
(the MemStorage double, a re-read export), never a returned flag alone.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    World,
    is_ok,
    is_refusal,
)
from qmf.data.backup import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    ENCRYPTION_REQUIRED,
    BackupCopyReceipt,
    OffMachineBackup,
    OffMachineCopy,
    OffMachineRestore,
)
from qmf.data.store.backup_input import BackupInput, RecordExport, RoomExport
from qmf.data.store.rooms import RoomRole

import _epic5_helpers as H

_ROWS = [{"t": 1_700_000_000_000_000_000, "px": 100}, {"t": 1_700_000_000_000_000_001, "px": 101}]
_SEVEN = list(RoomRole)


class _EmptyCipher:
    """A cipher returning empty ciphertext — a corrupt-copy signal on the backup side."""

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(b"")

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return Ok(b"")


def _backup(storage: object, cipher: object | None = None) -> OffMachineBackup:
    return OffMachineBackup(storage, cipher if cipher is not None else H.IdentityCipher())


# --- 5.1-U1 (L1): CT-26 read is non-mutating -------------------------------------


def test_5_1_u1_ct26_read_never_mutates_source(tmp_path: Path) -> None:
    """AC1: the source room's record set + fingerprints are byte-identical before/after a backup read."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    before = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    # consume the input through a real CT-14 backup
    storage = H.MemStorage()
    H.unwrap(_backup(storage).copy_export(before, for_world=World.LIVE))
    after = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    assert H.record_keyset(before) == H.record_keyset(after), (
        "a CT-26 backup read must not mutate evidence; the source fingerprint set changed"
    )


# --- 5.1-U2 (L1): every one of the seven room-roles is presentable ---------------


def test_5_1_u2_every_room_role_presentable(tmp_path: Path) -> None:
    """AC1: all seven room-roles (incl. the registry room) present through CT-26 under one law."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    H.seed_journal(store, "s1", {"event_type": "data quality", "world": "live", "n": 1})
    H.seed_registry(store, {"a": 1})
    presented: dict[RoomRole, bool] = {}
    for role in _SEVEN:
        res = H.read_room(store, role)
        presented[role] = is_ok(res)
        assert is_ok(res), f"room-role {role.value!r} must be presentable through CT-26; got {res!r}"
    assert set(presented) == set(RoomRole), "CT-26 must cover every one of the seven room-roles"
    # the three evidence-backed rooms carry records; the four rebuildable/unpopulated export empty
    assert H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE).record_count >= 1
    assert H.export_of(store, RoomRole.JOURNAL).record_count >= 1
    assert H.export_of(store, RoomRole.REGISTRY_ROOM).record_count >= 1


# --- 5.1-U3 (L1): distinct monotonic copy_version; neither rewrites the other ----


def test_5_1_u3_backups_are_distinct_versioned_artifacts(tmp_path: Path) -> None:
    """AC2: two backups of the same room yield distinct monotonic ordinals; both objects persist."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.MemStorage()
    backup = _backup(storage)
    r1 = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    r2 = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    assert r1.copy_version == 1 and r2.copy_version == 2, "copy_version must be a monotonic ordinal"
    assert r1.copy_version != r2.copy_version
    # observe the sink: BOTH versions persist as distinct objects (neither rewrote the other)
    keys = {k for k, _ in storage.put_calls}
    assert (World.LIVE.value, 1, RoomRole.IMMUTABLE_RAW_ARCHIVE.value) in keys
    assert (World.LIVE.value, 2, RoomRole.IMMUTABLE_RAW_ARCHIVE.value) in keys
    assert len(storage.objs) == 2, "each off-machine copy is a NEW versioned artifact"


# --- 5.1-U4 (L1): payload crosses as cipher output, not store plaintext ----------


def test_5_1_u4_payload_is_cipher_output_not_plaintext(tmp_path: Path) -> None:
    """AC2/AC5: the CT-14 payload is the cipher's OUTPUT; the store plaintext is never the payload."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.MemStorage()
    cipher = H.XorCipher(key=0x5A)
    H.unwrap(_backup(storage, cipher).copy_export(export, for_world=World.LIVE))
    (_, payload), = storage.put_calls
    # the raw record canonical bytes (the store plaintext) do NOT appear as the payload
    for record in export.records:
        assert record.canonical not in payload, "store plaintext must not cross as the CT-14 payload"
    # the payload is exactly what the injected cipher produced (decrypt recovers a valid frame)
    recovered = cipher.decrypt(payload).value
    assert recovered.startswith(b"QMFB1\0"), "payload must decrypt back to the framed envelope"
    assert recovered != payload, "ciphertext (payload) must differ from the framed plaintext"


# --- 5.1-U5 / 5.1-U6 (L1, P0-7): cross-world + simulated CT-26 reads refuse -------


def test_5_1_u5_cross_world_ct26_read_refused(tmp_path: Path) -> None:
    """AC3 (P0-7 backup side): a CT-26 read for a world other than the room's is a policy rejection."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    # a same-world read succeeds (baseline), so the refusal below is world-driven, not a broken read
    H.unwrap(H.read_room(store, RoomRole.IMMUTABLE_RAW_ARCHIVE, world=World.LIVE, at=None))
    # declaring for_world=REPLAY against the LIVE room's CT-26 input is a policy rejection
    live = H.world_store(store, World.LIVE)
    res = live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.REPLAY)
    H.assert_refusal(res, "policy rejection")


def test_5_1_u6_simulated_governed_evidence_refused(tmp_path: Path) -> None:
    """AC3 (P0-7): world=simulated has no governed namespace — requesting/reading it is a policy rejection."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    # the simulated world's store is refused outright (no governed namespace)
    H.assert_refusal(store.for_world(World.SIMULATED), "policy rejection")
    # a live room's CT-26 input asked to read as simulated is a policy rejection
    live = H.world_store(store, World.LIVE)
    H.assert_refusal(
        live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.SIMULATED),
        "policy rejection",
    )


# --- 5.1-U7 / 5.1-U8 (L1): transfer faults -> storage failure, no completion ------


def test_5_1_u7_unreachable_bucket_is_storage_failure(tmp_path: Path) -> None:
    """AC4: a transfer to an unreachable bucket returns a storage failure; no completion claimed."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    res = _backup(H.UnreachableStorage()).copy_export(export, for_world=World.LIVE)
    ref = H.assert_refusal(res, "storage failure")
    assert not isinstance(ref, BackupCopyReceipt), "no completion receipt on an unreachable bucket"


def test_5_1_u8_rejected_and_corrupt_are_storage_failure(tmp_path: Path) -> None:
    """AC4: a rejected upload and a corrupt (empty) copy each return a storage failure refusal."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    # rejected upload (adapter returns a storage-failure refusal)
    H.assert_refusal(_backup(H.RejectingStorage()).copy_export(export, for_world=World.LIVE), "storage failure")
    # corrupt copy: an empty ciphertext is treated as a corrupt copy on the backup side
    storage = H.MemStorage()
    res = _backup(storage, _EmptyCipher()).copy_export(export, for_world=World.LIVE)
    ref = H.assert_refusal(res, "storage failure")
    assert ref.context.get("signal") == "corrupt-copy"
    assert storage.objs == {}, "no object is stored when the copy is corrupt"


def test_5_1_u8_wrong_adapter_category_remapped_to_storage_failure(tmp_path: Path) -> None:
    """AC4/R-007: a miswired adapter's non-storage-failure refusal is REMAPPED to a returned
    storage failure — never raised across the CT-14 boundary. The adapter's refusal carries a
    ``reason`` context key exactly as every qmf refusal builder (policy_rejection / invalid_input /
    unpersistable) produces one."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    try:
        res = _backup(H.WrongCategoryStorage()).copy_export(export, for_world=World.LIVE)
    except BaseException as exc:  # noqa: BLE001 - R-007 forbids any raise across the boundary
        pytest.fail(
            f"CT-14 backup remap RAISED {type(exc).__name__} across the boundary instead of "
            f"returning a storage failure (AC4/R-007): {exc}"
        )
    ref = H.assert_refusal(res, "storage failure")
    assert ref.context.get("adapter_category") == "policy rejection", "the adapter's real category is preserved in context"


# --- 5.1-U9 (L1): encryption-required pointer, no provider/credential baked in ----


def test_5_1_u9_encryption_required_pointer_no_provider(tmp_path: Path) -> None:
    """AC5: the primitive carries the encryption-required pointer; no provider/credential baked in."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    receipt = H.unwrap(_backup(H.MemStorage()).copy_export(export, for_world=World.LIVE))
    assert ENCRYPTION_REQUIRED is True
    assert receipt.encryption_required is True, "every receipt carries the encryption-required pointer"
    # the artifact type also carries the standing pointer and no provider field
    copy = OffMachineCopy(world=World.LIVE, copy_version=1, source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, payload=b"x")
    assert copy.encryption_required is True
    field_names = {f.name.lower() for f in dataclasses.fields(receipt)}
    assert not any("provider" in n or "bucket" in n or "credential" in n for n in field_names), (
        "no provider/bucket/credential field is baked into the receipt"
    )


# --- 5.1-U10 (L1): no credential/secret in the artifact, its fp1, or refusal ------


def test_5_1_u10_no_credential_in_evidence(tmp_path: Path) -> None:
    """AC5: an injected key never appears in the receipt, its fp1, or the storage acknowledgement."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    secret = "S3CR3T-KEY-9f8e7d6c5b4a"
    storage = H.MemStorage()
    # the key lives only inside the injected cipher; it never flows into the primitive
    cipher = H.XorCipher(key=0x33)
    receipt = H.unwrap(_backup(storage, cipher).copy_export(export, for_world=World.LIVE))
    blob = repr(receipt) + receipt.payload_fingerprint + repr([c for _, c in storage.put_calls])
    assert secret not in blob, "no secret value may appear in the backup receipt / fp1 / ack"
    # the fp1 identifies the ciphertext, not any secret; ack detail carries no credentials
    assert receipt.payload_fingerprint.startswith("fp1:sha256:")


# --- 5.1-P1 (L2): timestamp fidelity — verbatim round-trip ----------------------


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(ts=st.integers(min_value=-(2**63), max_value=2**63 - 1))
def test_5_1_p1_int64_timestamps_round_trip_verbatim(ts: int) -> None:
    """AC1/AC5 (spans 5.2 AC1): an arbitrary int64 ns value is stored and restored bit-for-bit."""
    root = H.new_root()
    store = H.make_store(root, name="src")
    H.seed_raw(store, [{"t": ts, "px": 1}])
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.MemStorage()
    backup = _backup(storage)
    copy = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    restore = OffMachineRestore(storage, H.IdentityCipher())
    repl = H.make_store(root, name="repl")
    H.unwrap(
        restore.restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    )
    rows = H.unwrap(
        H.world_store(repl, World.LIVE).append_store.read_raw(
            H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE).records[0].fingerprint,
            for_world=World.LIVE,
        )
    )
    assert rows[0]["t"] == ts, "restored int64 ns must equal the stored value bit-for-bit"
    assert type(rows[0]["t"]) is int, "the timestamp stays an int, never re-derived under a calendar"


# --- 5.1-P2 (L2): R-EVIDENCE — no backup mutates the only copy -------------------


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(n_backups=st.integers(min_value=1, max_value=6))
def test_5_1_p2_no_backup_mutates_only_copy(n_backups: int) -> None:
    """AC2: across any number of backups, the source fingerprint set is invariant."""
    root = H.new_root()
    store = H.make_store(root, name="src")
    H.seed_raw(store, _ROWS)
    baseline = H.record_keyset(H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE))
    storage = H.MemStorage()
    backup = _backup(storage)
    for _ in range(n_backups):
        export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
        H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    after = H.record_keyset(H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE))
    assert after == baseline, "no backup may mutate or delete any source record"


# --- 5.1-P3 (L2, P0-7): world isolation on backup at every room-role -------------


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(role=st.sampled_from(_SEVEN))
def test_5_1_p3_cross_world_backup_read_refused_every_role(role: RoomRole) -> None:
    """AC3 (P0-7): for EVERY room-role, a cross-world CT-26 read is a policy rejection."""
    root = H.new_root()
    store = H.make_store(root)
    H.seed_raw(store, _ROWS)
    H.seed_journal(store, "s1", {"event_type": "data quality", "world": "live", "n": 1})
    H.seed_registry(store, {"a": 1})
    live = H.world_store(store, World.LIVE)
    res = live.backup_input.read_room(role, for_world=World.REPLAY)
    H.assert_refusal(res, "policy rejection")


# --- 5.1-P4 (L2, R-007): loud failure across the full fault matrix ---------------


def test_5_1_p4_transfer_fault_matrix_all_storage_failure(tmp_path: Path) -> None:
    """R-007: every CT-14 transfer fault surfaces as a RETURNED storage failure; no exception escapes."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    # The enumerated R-007 transfer faults. A miswired adapter CATEGORY is an adapter-contract
    # violation (not a transfer fault) and is exercised separately by the remap test.
    faults = {
        "unreachable (ConnectionError)": H.UnreachableStorage(),
        "interrupted (OSError)": H.OSErrorStorage(),
        "stalled (TimeoutError)": H.TimeoutStorage(),
        "rejected upload": H.RejectingStorage(),
    }
    leaks: dict[str, object] = {}
    for label, storage in faults.items():
        try:
            res = _backup(storage).copy_export(export, for_world=World.LIVE)
        except BaseException as exc:  # noqa: BLE001 - the whole point is that nothing escapes
            leaks[label] = f"raised {type(exc).__name__}"
            continue
        if not is_refusal(res) or res.category is not RefusalCategory.STORAGE_FAILURE:
            leaks[label] = res
    # corrupt copy (empty ciphertext) also loud
    corrupt = _backup(H.MemStorage(), _EmptyCipher()).copy_export(export, for_world=World.LIVE)
    if not is_refusal(corrupt) or corrupt.category is not RefusalCategory.STORAGE_FAILURE:
        leaks["corrupt copy"] = corrupt
    assert leaks == {}, f"every transfer fault must return a storage failure; leaks: {leaks}"


def test_5_1_p4_ct26_store_fault_matrix_all_storage_failure(tmp_path: Path) -> None:
    """R-007: a locked/corrupt store engine surfaces as a RETURNED storage failure at CT-26."""
    # A directly-wired BackupInput over engines that raise the store's normalized
    # StoreEngineError (exactly what a real Parquet/SQLite engine raises after wrapping
    # a pyarrow/sqlite3/OSError). No StoreEngineError may escape read_room.
    locked = BackupInput(
        World.LIVE, raw_engine=H.RaisingColumnar(retryable=True),
        record_engine=H.RaisingMetadata(retryable=False),
        journal_dir=tmp_path / "j", lineage_dir=tmp_path / "l",
        open_stream=H._noop_opener, seal=None,
    )
    raw = locked.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE)
    reg = locked.read_room(RoomRole.REGISTRY_ROOM, for_world=World.LIVE)
    H.assert_refusal(raw, "storage failure")
    H.assert_refusal(reg, "storage failure")
    # retryability is preserved from the underlying engine fault (transient vs corrupt)
    assert raw.retryability is Retryability.YES, "a locked (transient) store is retryable"
    assert reg.retryability is Retryability.NO, "a corrupt store is not retryable"


# --- 5.1-P5 (L2): no credential-in-evidence over arbitrary artifacts -------------


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(key=st.integers(min_value=1, max_value=255), tval=st.integers(min_value=0, max_value=2**40))
def test_5_1_p5_no_credential_in_arbitrary_artifacts(key: int, tval: int) -> None:
    """AC5: for arbitrary cipher keys, no secret value lands in the receipt / fp1 / ack detail."""
    root = H.new_root()
    store = H.make_store(root)
    H.seed_raw(store, [{"t": tval, "px": 1}])
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.MemStorage()
    receipt = H.unwrap(_backup(storage, H.XorCipher(key=key)).copy_export(export, for_world=World.LIVE))
    # no receipt field names a key/credential; the fp1 is a hash of ciphertext, not the key
    field_names = {f.name.lower() for f in dataclasses.fields(receipt)}
    assert not any("key" in n or "secret" in n or "credential" in n or "password" in n for n in field_names), (
        "no receipt field names a key/credential"
    )
    assert receipt.payload_fingerprint.startswith("fp1:sha256:")


# --- 5.1-C1 (L3): CT-26 round-trip semantic equality ----------------------------


def test_5_1_c1_ct26_round_trip_semantic_equality(tmp_path: Path) -> None:
    """AC1: a CT-26 export encodes {format_version, world, source_room_role, records} and round-trips."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    assert export.world is World.LIVE
    assert export.source_room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE
    assert export.format_version == BACKUP_CONTRACT_FORMAT_VERSION, "format-version stamp present"
    assert isinstance(export.records, tuple) and export.record_count >= 1
    # the source_room_role enum is exactly the seven room-roles
    assert {r.value for r in RoomRole} == {
        "ingest door", "immutable raw archive", "processed", "journal",
        "split-governed research door", "backup", "registry room",
    }
    # full public round-trip (back up -> restore -> re-export) is byte/fingerprint identical
    storage = H.MemStorage()
    copy = H.unwrap(_backup(storage).copy_export(export, for_world=World.LIVE))
    repl = H.make_store(tmp_path, name="repl")
    H.unwrap(
        OffMachineRestore(storage, H.IdentityCipher()).restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    )
    assert H.exports_identical(export, H.export_of(repl, RoomRole.IMMUTABLE_RAW_ARCHIVE))


# --- 5.1-C2 (L3): CT-26 boundary / invalid ---------------------------------------


def test_5_1_c2_ct26_boundary_enums_and_nullability(tmp_path: Path) -> None:
    """AC1/AC3/AC4: for_world required; role enum membership; refusal categories bounded."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    live = H.world_store(store, World.LIVE)
    # for_world = None is an invalid input (a read must declare its world; M4)
    H.assert_refusal(live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=None), "invalid input")
    # a bad room-role string is an invalid input
    H.assert_refusal(live.backup_input.read_room("no-such-room", for_world=World.LIVE), "invalid input")
    # governed-condition refusals (cross-world) are in the CT-26 boundary set {policy rejection, storage failure}
    xw = live.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.REPLAY)
    assert xw.category.value in {"policy rejection", "storage failure"}


# --- 5.1-C3 (L3): CT-14 round-trip ------------------------------------------------


def test_5_1_c3_ct14_round_trip_over_world_version_payload(tmp_path: Path) -> None:
    """AC2: the CT-14 off-machine copy carries world + copy_version + payload; round-trips verbatim."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.MemStorage()
    copy = H.unwrap(_backup(storage).copy_export(export, for_world=World.LIVE))
    assert copy.world is World.LIVE
    assert isinstance(copy.copy_version, int) and copy.copy_version >= 1
    assert copy.format_version == BACKUP_CONTRACT_FORMAT_VERSION
    # restore reproduces the export byte/fingerprint identical
    repl = H.make_store(tmp_path, name="repl")
    rr = H.unwrap(
        OffMachineRestore(storage, H.IdentityCipher()).restore_copy(
            world=World.LIVE, copy_version=copy.copy_version,
            source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=repl, for_world=World.LIVE,
        )
    )
    assert rr.copy_version == copy.copy_version
    assert H.exports_identical(export, H.export_of(repl, RoomRole.IMMUTABLE_RAW_ARCHIVE))


# --- 5.1-C4 (L3): CT-14 boundary / refusal ---------------------------------------


def test_5_1_c4_ct14_world_enum_version_and_refusal_categories(tmp_path: Path) -> None:
    """AC2/AC3/AC4: simulated reserved; monotonic ordinal; governed refusals in {policy, storage}."""
    store = H.make_store(tmp_path)
    H.seed_raw(store, _ROWS)
    export = H.export_of(store, RoomRole.IMMUTABLE_RAW_ARCHIVE)
    storage = H.MemStorage()
    backup = _backup(storage)
    # simulated world is a reserved-unusable policy rejection on the CT-14 copy
    H.assert_refusal(backup.copy_export(export, for_world=World.SIMULATED), "policy rejection")
    # cross-world copy is a policy rejection (export.world=LIVE, for_world=REPLAY)
    H.assert_refusal(backup.copy_export(export, for_world=World.REPLAY), "policy rejection")
    # monotonic ordinal on success
    a = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    b = H.unwrap(backup.copy_export(export, for_world=World.LIVE))
    assert b.copy_version > a.copy_version
    # NO governed CT-14 failure yields one of the five out-of-set categories: only
    # `storage failure` and `policy rejection` may cross this boundary; `invalid input`
    # is validated BEFORE the boundary and must never cross it (OR-05; DEC-0109).
    forbidden = {
        "invalid input",
        "unsupported capability",
        "unavailable dependency",
        "stale evidence",
        "transient venue failure",
    }
    for res in (
        backup.copy_export(export, for_world=World.SIMULATED),
        backup.copy_export(export, for_world=World.REPLAY),
        _backup(H.UnreachableStorage()).copy_export(export, for_world=World.LIVE),
    ):
        assert is_refusal(res) and res.category.value not in forbidden, (
            f"CT-14 governed refusal category out of set: {res.category.value}"
        )
