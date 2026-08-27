"""Epic 5 — fault-translation + tamper-isolation branches on the CT-14 boundary.

Targets the refusal branches this epic is built to guarantee (WS-1/WS-2): the cipher-fault
arms (encrypt/decrypt raise or refuse), the storage.get raise arm, the corrupt-envelope arms,
and — the security-load-bearing ones — a decrypted copy whose EMBEDDED world or room-role does
not match the requested restore is refused as a `policy rejection` (a tampered copy can never
cross worlds or masquerade as another room on restore). Maps to 5.1 AC4 / 5.2 AC1/AC3 / R-007 /
R-INTEGRITY / P0-7. Refusals check the CT-04 category.
"""

from __future__ import annotations

from pathlib import Path

from qmf.core import World, is_ok, is_refusal
from qmf.data.backup import OffMachineBackup, OffMachineRestore
from qmf.data.store.rooms import RoomRole

import _epic5_helpers as H

_ROWS = [{"t": 1_700_000_000_000_000_000, "px": 100}]


def _seed_export(root: Path, *, world: World = World.LIVE):
    src = H.make_store(root, name="src")
    H.seed_raw(src, _ROWS, world=world)
    return src, H.export_of(src, RoomRole.IMMUTABLE_RAW_ARCHIVE, world=world)


# --- backup-side cipher faults -> storage failure (R-007) --------------------------


def test_backup_cipher_raise_is_storage_failure(tmp_path: Path) -> None:
    """5.1 AC4 / R-007: a cipher that RAISES during encrypt -> returned storage failure, no completion."""
    _src, export = _seed_export(tmp_path)
    storage = H.MemStorage()
    res = OffMachineBackup(storage, H.RaisingCipher(ValueError("no key"))).copy_export(export, for_world=World.LIVE)
    ref = H.assert_refusal(res, "storage failure")
    assert ref.context.get("signal") == "cipher-raised"
    assert storage.objs == {}, "no object stored when encryption raises"


def test_backup_cipher_refusal_is_returned(tmp_path: Path) -> None:
    """5.1 AC4: a cipher that RETURNS a typed refusal (missing key) surfaces that refusal, no completion."""
    _src, export = _seed_export(tmp_path)
    storage = H.MemStorage()
    res = OffMachineBackup(storage, H.RefusingCipher()).copy_export(export, for_world=World.LIVE)
    H.assert_refusal(res, "storage failure")
    assert storage.objs == {}


# --- restore-side fault translation -> storage failure (R-007) ---------------------


def test_restore_storage_get_raise_is_storage_failure(tmp_path: Path) -> None:
    """5.2 AC1 / R-007: a storage.get that RAISES during restore -> returned storage failure."""
    _src, export = _seed_export(tmp_path)
    good = H.MemStorage()
    cipher = H.IdentityCipher()
    copy = H.unwrap(OffMachineBackup(good, cipher).copy_export(export, for_world=World.LIVE))
    faulted = H.UnreachableStorage()
    faulted.objs = dict(good.objs)
    res = OffMachineRestore(faulted, cipher).restore_copy(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="r"), for_world=World.LIVE,
    )
    ref = H.assert_refusal(res, "storage failure")
    assert ref.context.get("signal") == "storage-raised"


def test_restore_cipher_decrypt_raise_is_storage_failure(tmp_path: Path) -> None:
    """5.2 AC1 / R-007: a cipher that RAISES during decrypt -> returned storage failure."""
    _src, export = _seed_export(tmp_path)
    storage = H.MemStorage()
    copy = H.unwrap(OffMachineBackup(storage, H.IdentityCipher()).copy_export(export, for_world=World.LIVE))
    # backup with identity, restore with a decrypt-raising cipher over the same objects
    res = OffMachineRestore(storage, H.RaisingCipher(RuntimeError("decrypt failed"))).restore_copy(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(tmp_path, name="r"), for_world=World.LIVE,
    )
    ref = H.assert_refusal(res, "storage failure")
    assert ref.context.get("signal") == "cipher-raised"


# --- restore invalid arguments -> invalid input ------------------------------------


def test_restore_invalid_arguments_are_invalid_input(tmp_path: Path) -> None:
    """5.2 AC1: a malformed role / copy_version / world is an invalid input refusal (CT-04 caller-error)."""
    restore = OffMachineRestore(H.MemStorage(), H.IdentityCipher())
    into = H.make_store(tmp_path, name="r")
    H.assert_refusal(
        restore.restore_copy(world=World.LIVE, copy_version=1, source_room_role="no-such-room", into=into, for_world=World.LIVE),
        "invalid input",
    )
    H.assert_refusal(
        restore.restore_copy(world=World.LIVE, copy_version=0, source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=into, for_world=World.LIVE),
        "invalid input",
    )
    H.assert_refusal(
        restore.restore_copy(world="mars", copy_version=1, source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=into, for_world=World.LIVE),
        "invalid input",
    )


# --- tamper-isolation: a decrypted copy claiming a different world/role is refused --


def test_restore_decrypted_world_mismatch_refused(tmp_path: Path) -> None:
    """P0-7 / R-INTEGRITY: a copy whose DECRYPTED world differs from the requested restore world is a
    policy rejection — a tampered/misfiled copy can never cross worlds on restore."""
    root = tmp_path
    src, export = _seed_export(root, world=World.LIVE)  # export.world == LIVE
    storage = H.MemStorage()
    cipher = H.IdentityCipher()
    copy = H.unwrap(OffMachineBackup(storage, cipher).copy_export(export, for_world=World.LIVE))
    # misfile the LIVE-framed ciphertext under the REPLAY object key (tamper)
    live_key = (World.LIVE.value, copy.copy_version, RoomRole.IMMUTABLE_RAW_ARCHIVE.value)
    replay_key = (World.REPLAY.value, copy.copy_version, RoomRole.IMMUTABLE_RAW_ARCHIVE.value)
    storage.objs[replay_key] = storage.objs[live_key]
    res = OffMachineRestore(storage, cipher).restore_copy(
        world=World.REPLAY, copy_version=copy.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, into=H.make_store(root, name="r"), for_world=World.REPLAY,
    )
    ref = H.assert_refusal(res, "policy rejection")
    assert ref.context.get("field") == "world", "the refusal names the world mismatch"


def test_restore_decrypted_role_mismatch_refused(tmp_path: Path) -> None:
    """R-INTEGRITY: a copy whose DECRYPTED room-role differs from the requested role is refused."""
    root = tmp_path
    src, export = _seed_export(root, world=World.LIVE)  # a RAW-archive export
    storage = H.MemStorage()
    cipher = H.IdentityCipher()
    copy = H.unwrap(OffMachineBackup(storage, cipher).copy_export(export, for_world=World.LIVE))
    raw_key = (World.LIVE.value, copy.copy_version, RoomRole.IMMUTABLE_RAW_ARCHIVE.value)
    journal_key = (World.LIVE.value, copy.copy_version, RoomRole.JOURNAL.value)
    storage.objs[journal_key] = storage.objs[raw_key]  # misfile RAW copy under the JOURNAL key
    res = OffMachineRestore(storage, cipher).restore_copy(
        world=World.LIVE, copy_version=copy.copy_version,
        source_room_role=RoomRole.JOURNAL, into=H.make_store(root, name="r"), for_world=World.LIVE,
    )
    ref = H.assert_refusal(res, "policy rejection")
    assert ref.context.get("field") == "source_room_role", "the refusal names the room-role mismatch"
