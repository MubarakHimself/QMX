"""Bind WorldRooms collaborators and resolve a world bundle.

Factory and collaborator bag live here so :class:`~qmf.data.rooms.WorldRooms`
stays a facade over one instance field (LCOM4).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from qmf.core import Ok, Result, is_refusal
from qmf.data.rooms_roles import WorldRoomRoles
from qmf.data.rooms_series import WorldRoomPolicy
from qmf.data.rooms_store import WorldRoomBoundaries
from qmf.data.store import EvidenceStore, ReadSeal, WorldStore

TWorldRooms = TypeVar("TWorldRooms")


@dataclass(frozen=True, slots=True)
class WorldRoomCollaborators:
    """Store boundaries, role catalog, and series/view policy for one world."""

    boundaries: WorldRoomBoundaries
    roles: WorldRoomRoles
    policy: WorldRoomPolicy


def bind_world_rooms(
    world_store: WorldStore, seal: ReadSeal | None
) -> WorldRoomCollaborators:
    """Wire the three disconnected WorldRooms groups onto one collaborator bag."""
    return WorldRoomCollaborators(
        boundaries=WorldRoomBoundaries(world_store),
        roles=WorldRoomRoles(),
        policy=WorldRoomPolicy(world_store, seal),
    )


def resolve_world_rooms(
    cls: Callable[..., TWorldRooms],
    store: EvidenceStore,
    world: object,
    *,
    seal: ReadSeal | None = None,
) -> Result[TWorldRooms]:
    """The rooms for ``world``, or a refusal (AC1, AC4)."""
    bundle = store.for_world(world)
    if is_refusal(bundle):
        return bundle
    return Ok(cls(bundle.value, seal=seal))
