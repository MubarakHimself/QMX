"""CT-14 verify comparison, copy-list, and storage-failure helpers.

Split from :mod:`qmf.data.verify` so the public module stays under the Skylos
god-file limits. Callers keep importing public names from :mod:`qmf.data.verify`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)
from qmf.data.backup import RestoreReceipt
from qmf.data.backup_gate import coerce_role
from qmf.data.backup_storage import storage_failure
from qmf.data.store.backup_input import RecordExport, RoomExport
from qmf.data.store.facade import EvidenceStore
from qmf.data.store.refusals import invalid_input
from qmf.data.store.rooms import RoomRole
from qmf.data.verify_types import RESTORABLE_ROOM_ROLES, VerifiedRoom

__all__ = [
    "as_verify_storage_failure",
    "confirm_restored_room",
    "documented_path",
    "exports_match",
    "normalize_copies",
    "resolve_roles",
]


def documented_path(
    documented_restore_path: str | None, source_store: EvidenceStore | None
) -> Result[str]:
    """Resolve the documented restore path the claim will cite."""
    if documented_restore_path is not None and documented_restore_path.strip():
        return Ok(documented_restore_path)
    if source_store is not None:
        return Ok(str(source_store.root.resolve()))
    return invalid_input(
        "documented_restore_path",
        "a verify primitive must name a documented restore path (or supply source_store "
        "so the source root can be cited) — recoverability is never asserted from a "
        "snapshot alone (SCN-0004, DEC-0118)",
    )


def confirm_restored_room(
    into: EvidenceStore,
    *,
    expected: RoomExport,
    for_world: object,
    copy_version: int,
    restore_receipt: RestoreReceipt,
) -> Result[VerifiedRoom]:
    """Read the restored room back and compare fingerprints/canonical bytes to expected."""
    bundle = into.for_world(expected.world)
    if is_refusal(bundle):
        return as_verify_storage_failure(bundle)
    reread = bundle.value.backup_input.read_room(expected.source_room_role, for_world=for_world)
    if is_refusal(reread):
        return as_verify_storage_failure(reread)
    if not exports_match(expected, reread.value):
        return storage_failure(
            "restored evidence does not match the documented restore path; a corrupt "
            "or incomplete restore yields no recoverability claim (DEC-0109, DEC-0118)",
            retryable=False,
            context={
                "signal": "verify-mismatch",
                "role": expected.source_room_role.value,
                "copy_version": copy_version,
                "expected_count": expected.record_count,
                "actual_count": reread.value.record_count,
            },
        )
    return Ok(
        VerifiedRoom(
            source_room_role=expected.source_room_role,
            copy_version=copy_version,
            record_count=expected.record_count,
            restore_receipt=restore_receipt,
        )
    )


def exports_match(expected: RoomExport, actual: RoomExport) -> bool:
    """Byte-faithful comparison of two CT-26 room exports (order-independent)."""
    if expected.world is not actual.world:
        return False
    if expected.source_room_role is not actual.source_room_role:
        return False
    if expected.record_count != actual.record_count:
        return False
    exp = {_record_key(record) for record in expected.records}
    act = {_record_key(record) for record in actual.records}
    return exp == act


def _record_key(record: RecordExport) -> tuple[str, bytes, str | None]:
    """Identity key for one exported record."""
    return (record.fingerprint, record.canonical, record.stream)


def normalize_copies(copies: object) -> Result[tuple[tuple[RoomRole, int], ...]]:
    """Normalize a copies mapping/sequence into an ordered tuple of pairs."""
    raw = _raw_copy_pairs(copies)
    if is_refusal(raw):
        return raw
    pairs: list[tuple[RoomRole, int]] = []
    for role_raw, version_raw in raw.value:
        bound = _bound_copy_pair(role_raw, version_raw)
        if is_refusal(bound):
            return bound
        pairs.append(bound.value)
    return Ok(tuple(pairs))


def _raw_copy_pairs(copies: object) -> Result[list[tuple[object, object]]]:
    raw_pairs: list[tuple[object, object]] = []
    if isinstance(copies, Mapping):
        mapping = cast("Mapping[object, object]", copies)
        raw_pairs.extend(mapping.items())
        return Ok(raw_pairs)
    if isinstance(copies, Sequence) and not isinstance(copies, (str, bytes)):
        return _sequence_copy_pairs(cast("Sequence[object]", copies))
    return invalid_input(
        "copies",
        "copies is a {room_role: copy_version} mapping or a sequence of pairs",
        given=repr(copies),
    )


def _sequence_copy_pairs(sequence: Sequence[object]) -> Result[list[tuple[object, object]]]:
    raw_pairs: list[tuple[object, object]] = []
    for item_obj in sequence:
        item: object = item_obj
        if not isinstance(item, tuple):
            return invalid_input(
                "copies",
                "each copies entry is a (room_role, copy_version) pair",
                given=repr(item),
            )
        pair = cast("tuple[object, ...]", item)
        if len(pair) != 2:
            return invalid_input(
                "copies",
                "each copies entry is a (room_role, copy_version) pair",
                given=f"tuple(len={len(pair)})",
            )
        raw_pairs.append((pair[0], pair[1]))
    return Ok(raw_pairs)


def _bound_copy_pair(role_raw: object, version_raw: object) -> Result[tuple[RoomRole, int]]:
    role = role_raw if isinstance(role_raw, RoomRole) else coerce_role(role_raw)
    if role is None:
        return invalid_input(
            "copies",
            "each rehearsed room-role must be a RoomRole",
            given=repr(role_raw),
        )
    if not isinstance(version_raw, int) or isinstance(version_raw, bool) or version_raw < 1:
        return invalid_input(
            "copies",
            "each copy_version is a positive ordinal identifying one off-machine artifact",
            given=repr(version_raw),
            role=role.value,
        )
    return Ok((role, version_raw))


def resolve_roles(room_roles: Sequence[object] | None) -> Result[tuple[RoomRole, ...]]:
    """Resolve the room-roles a migration covers; default to the V1 restorable set."""
    if room_roles is None:
        return Ok(RESTORABLE_ROOM_ROLES)
    resolved: list[RoomRole] = []
    for raw in room_roles:
        role = coerce_role(raw)
        if role is None:
            return invalid_input(
                "room_roles",
                "each room_role is one of the seven room-roles",
                given=repr(raw),
                allowed=[member.value for member in RoomRole],
            )
        if role not in RESTORABLE_ROOM_ROLES:
            return invalid_input(
                "room_roles",
                "this room-role has no restore writer in V1; only the immutable raw "
                "archive, journal, and registry room are migratable from a CT-26 export",
                given=role.value,
            )
        if role not in resolved:
            resolved.append(role)
    if not resolved:
        return invalid_input(
            "room_roles",
            "a migration names at least one restorable room-role",
            given=repr(room_roles),
        )
    return Ok(tuple(resolved))


def as_verify_storage_failure(result: TypedRefusal) -> TypedRefusal:
    """Map a failed restore/read into a storage-failure with no recoverability claim.

    Policy / invalid-input refusals from the restore gate (cross-world, in-place) pass
    through unchanged — they are not corrupt-copy outcomes. Every other refusal category
    becomes ``storage failure`` so a corrupt restore never reports success (AC2).
    """
    if result.category in {
        RefusalCategory.POLICY_REJECTION,
        RefusalCategory.INVALID_INPUT,
    }:
        return result
    if result.category is RefusalCategory.STORAGE_FAILURE:
        return result
    remapped: dict[str, object] = dict(result.context)
    remapped["signal"] = remapped.get("signal", "verify-storage-failure")
    remapped["adapter_category"] = result.category.value
    return storage_failure(
        "verify restore failed; no recoverability claim is issued (DEC-0109, DEC-0118)",
        retryable=result.retryability is Retryability.YES,
        context=remapped,
    )
