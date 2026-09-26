"""Read-only store-boundary accessors for one world's rooms.

Disconnected from :class:`~qmf.data.rooms.WorldRooms` role-catalog and
series-policy groups (LCOM4). Every accessor shares ``_store``.
"""

from __future__ import annotations

from qmf.core import World
from qmf.data.store import AppendStore, BackupInput, JournalStore, RegistryRoom, WorldStore


class WorldRoomBoundaries:
    """The four physical store boundaries for exactly one world, surfaced read-only."""

    def __init__(self, world_store: WorldStore) -> None:
        self._store = world_store

    @property
    def world(self) -> World:
        """The one world whose seven rooms this facade owns."""
        return self._store.world

    @property
    def append_store(self) -> AppendStore:
        """The CT-11 append-store — immutable raw archive + processed views (this world)."""
        return self._store.append_store

    @property
    def journal(self) -> JournalStore:
        """The CT-13 journal store for this world's journal room."""
        return self._store.journal

    @property
    def registry_room(self) -> RegistryRoom:
        """The CT-09 registry room — records + lineage edges for this world."""
        return self._store.registry_room

    @property
    def backup_input(self) -> BackupInput:
        """The CT-26 store-to-backup input for this world's rooms."""
        return self._store.backup_input
