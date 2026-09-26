"""World, room-role, and in-place gates for CT-14 backup/restore."""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    is_refusal,
)
from qmf.data.store.facade import EvidenceStore
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.store.rooms import RoomRole


@dataclass(frozen=True, slots=True)
class RestoreCopySpec:
    """Bound restore-copy identity after world/role/in-place gates."""

    world: World
    copy_version: int
    role: RoomRole


def coerce_world(value: object) -> World | None:
    """Resolve a :class:`World` or its string value, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def coerce_role(value: object) -> RoomRole | None:
    """Resolve a :class:`RoomRole` or its string value, or ``None``."""
    if isinstance(value, RoomRole):
        return value
    if isinstance(value, str):
        try:
            return RoomRole(value)
        except ValueError:
            return None
    return None


def refuse_ungoverned_world(resolved: World, expected: World, *, field_label: str) -> Result[World]:
    """Refuse simulated or cross-world backup/restore requests."""
    if resolved is World.SIMULATED:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": (
                    "world = simulated has no governed namespace in V1; a backup/restore "
                    "into governed evidence is refused (DEC-0110, DEC-0117)"
                ),
                "requested": resolved.value,
            },
        )
    if resolved is not expected:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": (
                    "a backup/restore that crosses worlds is refused; storage separation "
                    "delivers world isolation (DEC-0117)"
                ),
                "requested": resolved.value,
                field_label: expected.value,
            },
        )
    return Ok(resolved)


def governed_world(expected: World, for_world: object, *, field_label: str) -> Result[World]:
    """Resolve and gate ``for_world`` against ``expected``; refuse simulated/cross-world."""
    if for_world is None:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "for_world",
                "reason": (
                    "a backup/restore must declare the world it operates as; there is "
                    "no implicit same-world default (M4)"
                ),
            },
        )
    resolved = coerce_world(for_world)
    if resolved is None:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": "world is a World or one of the closed set live | replay | simulated",
                "given": repr(for_world),
            },
        )
    return refuse_ungoverned_world(resolved, expected, field_label=field_label)


def refuse_in_place(into: EvidenceStore, source_store: EvidenceStore | None) -> TypedRefusal | None:
    """A policy rejection when restore would rewrite the only local store in place."""
    if source_store is None:
        return None
    if into is source_store or into.root.resolve() == source_store.root.resolve():
        return policy_rejection(
            "replacement_store",
            "a restore must target a replacement store root; rewriting the only local "
            "copy in place is refused (DEC-0118)",
            signal="refuse-in-place-restore",
            replacement_root=str(into.root.resolve()),
            source_root=str(source_store.root.resolve()),
        )
    return None


def bind_restore_copy(
    *,
    world: object,
    copy_version: int,
    source_room_role: object,
    into: EvidenceStore,
    for_world: object,
    source_store: EvidenceStore | None,
) -> Result[RestoreCopySpec]:
    """Validate restore-copy identity and refuse in-place rewrite of the only copy."""
    role = coerce_role(source_room_role)
    if role is None:
        return invalid_input(
            "source_room_role",
            "source_room_role is one of the seven room-roles",
            given=repr(source_room_role),
            allowed=[member.value for member in RoomRole],
        )
    if isinstance(copy_version, bool) or copy_version < 1:
        return invalid_input(
            "copy_version",
            "copy_version is a positive ordinal identifying one off-machine artifact",
            given=repr(copy_version),
        )
    resolved_world = coerce_world(world)
    if resolved_world is None:
        return invalid_input(
            "world",
            "world is a World or one of the closed set live | replay | simulated",
            given=repr(world),
        )
    gate = governed_world(resolved_world, for_world, field_label="copy_world")
    if is_refusal(gate):
        return gate
    blocked = refuse_in_place(into, source_store)
    if blocked is not None:
        return blocked
    return Ok(RestoreCopySpec(world=resolved_world, copy_version=copy_version, role=role))
