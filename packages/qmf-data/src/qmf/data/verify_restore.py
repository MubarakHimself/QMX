"""CT-14 sample-restore and full-restore rehearsal primitives.

Split from :mod:`qmf.data.verify` so the public module stays under the Skylos
god-file limits. Callers keep importing :class:`OffMachineVerify` from
:mod:`qmf.data.verify`.
"""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core import Ok, Result, World, is_refusal
from qmf.data.backup import ObjectStorage, OffMachineRestore, PayloadCipher
from qmf.data.store.backup_input import RoomExport
from qmf.data.store.facade import EvidenceStore
from qmf.data.store.refusals import invalid_input
from qmf.data.store.rooms import RoomRole
from qmf.data.verify_match import (
    as_verify_storage_failure,
    confirm_restored_room,
    documented_path,
    normalize_copies,
)
from qmf.data.verify_types import RecoverabilityClaim, VerifiedRoom, VerifyKind

__all__ = ["OffMachineVerify"]


class OffMachineVerify:
    """First-class CT-14 verify primitives (sample-restore + full-restore rehearsal).

    Constructed with the same :class:`ObjectStorage` / :class:`PayloadCipher` ports as
    backup and restore. Every successful verify restores into a **replacement** store,
    reads the restored evidence back, and compares it to the documented expected export
    — only then is a :class:`RecoverabilityClaim` returned (AC1, AC2).
    """

    def __init__(
        self,
        storage: ObjectStorage,
        cipher: PayloadCipher,
        *,
        restore: OffMachineRestore | None = None,
    ) -> None:
        self._storage = storage
        self._cipher = cipher
        self._restore = restore if restore is not None else OffMachineRestore(storage, cipher)

    def sample_restore(
        self,
        *,
        world: object,
        copy_version: int,
        source_room_role: object,
        into: EvidenceStore,
        for_world: object,
        expected: RoomExport,
        source_store: EvidenceStore | None = None,
        documented_restore_path: str | None = None,
    ) -> Result[RecoverabilityClaim]:
        """Restore one room-role sample and confirm it against ``expected`` (AC1, AC2).

        A corrupt or mismatched restore is a ``storage failure`` — no recoverability
        claim is issued. ``documented_restore_path`` defaults to ``source_store.root``
        when the source is supplied.
        """
        path = documented_path(documented_restore_path, source_store)
        if is_refusal(path):
            return path

        restored = self._restore.restore_copy(
            world=world,
            copy_version=copy_version,
            source_room_role=source_room_role,
            into=into,
            for_world=for_world,
            source_store=source_store,
        )
        if is_refusal(restored):
            return as_verify_storage_failure(restored)

        checked = confirm_restored_room(
            into,
            expected=expected,
            for_world=for_world,
            copy_version=copy_version,
            restore_receipt=restored.value,
        )
        if is_refusal(checked):
            return checked

        room = checked.value
        return Ok(
            RecoverabilityClaim(
                kind=VerifyKind.SAMPLE_RESTORE,
                world=expected.world,
                rooms=(room,),
                record_count=room.record_count,
                replacement_root=restored.value.replacement_root,
                documented_restore_path=path.value,
            )
        )

    def full_restore_rehearsal(
        self,
        *,
        world: object,
        copies: object,
        into: EvidenceStore,
        for_world: object,
        expected: Mapping[RoomRole, RoomExport],
        source_store: EvidenceStore | None = None,
        documented_restore_path: str | None = None,
    ) -> Result[RecoverabilityClaim]:
        """Restore every listed room-role and confirm each against ``expected`` (AC1, AC2).

        ``copies`` is a ``{RoomRole: copy_version}`` mapping or a sequence of
        ``(room_role, copy_version)`` pairs. One corrupt room aborts the rehearsal with
        a ``storage failure`` and no claim.
        """
        path = documented_path(documented_restore_path, source_store)
        if is_refusal(path):
            return path

        pairs = normalize_copies(copies)
        if is_refusal(pairs):
            return pairs
        if not pairs.value:
            return invalid_input(
                "copies",
                "a full-restore rehearsal names at least one (room-role, copy_version) pair",
                given=repr(copies),
            )

        restored_rooms = rehearse_rooms(
            self._restore,
            world=world,
            pairs=pairs.value,
            into=into,
            for_world=for_world,
            expected=expected,
            source_store=source_store,
        )
        if is_refusal(restored_rooms):
            return restored_rooms
        rooms, total, claim_world, claim_root = restored_rooms.value
        return Ok(
            RecoverabilityClaim(
                kind=VerifyKind.FULL_RESTORE_REHEARSAL,
                world=claim_world,
                rooms=tuple(rooms),
                record_count=total,
                replacement_root=claim_root,
                documented_restore_path=path.value,
            )
        )


def rehearse_rooms(
    restore: OffMachineRestore,
    *,
    world: object,
    pairs: tuple[tuple[RoomRole, int], ...],
    into: EvidenceStore,
    for_world: object,
    expected: Mapping[RoomRole, RoomExport],
    source_store: EvidenceStore | None,
) -> Result[tuple[list[VerifiedRoom], int, World, str]]:
    rooms: list[VerifiedRoom] = []
    total = 0
    claim_world: World | None = None
    claim_root: str | None = None
    for role, version in pairs:
        one = _rehearse_one_room(
            restore,
            world=world,
            role=role,
            version=version,
            into=into,
            for_world=for_world,
            expected=expected,
            source_store=source_store,
        )
        if is_refusal(one):
            return one
        room, room_world, room_root = one.value
        rooms.append(room)
        total += room.record_count
        claim_world = room_world
        claim_root = room_root
    if claim_world is None or claim_root is None:
        return invalid_input(
            "copies",
            "a full-restore rehearsal names at least one (room-role, copy_version) pair",
        )
    return Ok((rooms, total, claim_world, claim_root))


def _rehearse_one_room(
    restore: OffMachineRestore,
    *,
    world: object,
    role: RoomRole,
    version: int,
    into: EvidenceStore,
    for_world: object,
    expected: Mapping[RoomRole, RoomExport],
    source_store: EvidenceStore | None,
) -> Result[tuple[VerifiedRoom, World, str]]:
    exp = expected.get(role)
    if exp is None:
        return invalid_input(
            "expected",
            "every rehearsed room-role must have an expected CT-26 export to "
            "compare against the documented restore path",
            missing_role=role.value,
        )
    restored = restore.restore_copy(
        world=world,
        copy_version=version,
        source_room_role=role,
        into=into,
        for_world=for_world,
        source_store=source_store,
    )
    if is_refusal(restored):
        return as_verify_storage_failure(restored)
    checked = confirm_restored_room(
        into,
        expected=exp,
        for_world=for_world,
        copy_version=version,
        restore_receipt=restored.value,
    )
    if is_refusal(checked):
        return checked
    return Ok((checked.value, exp.world, restored.value.replacement_root))
