"""EvidenceStore — the dependency-free store seam, wired per world (AC1, AC5).

The composition point of Story 3.1: one filesystem-rooted store that instantiates the
room-roles **per world** and exposes the four ratified boundaries — CT-11 append-store,
CT-13 journal, CT-09 registry room, and CT-26 store-to-backup — each over the one
engine ratified for it (Parquet, DuckDB, SQLite, JSONL). World isolation is storage
separation: each world's rooms live under their own namespace directory, so a
``world = simulated`` store is refused outright (it has no governed namespace) and a
live store's rooms never resolve to a replay world's (DEC-0110, DEC-0117).

``COMP-QMF-DATA-STORE`` declares zero component dependencies: this module imports only
``qmf-core`` (the fp1 vocabulary and typed refusals) and the local engine adapters. It
is the seam Epic 2's registry persistence writes through and Epic 3's later data
policies build on. Stdlib + qmf-core.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qmf.core import Ok, Result, World, is_ok
from qmf.data.store.append_store import AppendStore
from qmf.data.store.backup_input import BackupInput
from qmf.data.store.engines.duckdb_views import DuckDbAnalyticsEngine
from qmf.data.store.engines.jsonl import DEFAULT_ROTATION_BYTES, jsonl_opener
from qmf.data.store.engines.parquet import ParquetColumnarEngine
from qmf.data.store.engines.sqlite_meta import SqliteMetadataEngine
from qmf.data.store.journal import JournalStore
from qmf.data.store.registry_room import RegistryRoom
from qmf.data.store.rooms import ReadSeal, namespace_for_write

__all__ = ["EvidenceStore", "WorldStore"]


@dataclass(frozen=True, slots=True)
class WorldStore:
    """The four store boundaries for one world, sharing one set of engine instances.

    All four are wired over the same engines, so a CT-26 backup read sees exactly what
    the CT-11/CT-13/CT-09 writes committed.
    """

    world: World
    append_store: AppendStore
    journal: JournalStore
    registry_room: RegistryRoom
    backup_input: BackupInput


class EvidenceStore:
    """A filesystem-rooted store that hands out per-world boundary bundles (AC1, AC5)."""

    def __init__(
        self,
        root: Path,
        *,
        rotation_bytes: int = DEFAULT_ROTATION_BYTES,
        seal: ReadSeal | None = None,
    ) -> None:
        self._root = root
        self._rotation_bytes = rotation_bytes
        self._seal = seal
        self._worlds: dict[World, WorldStore] = {}

    @property
    def root(self) -> Path:
        """The store's root directory."""
        return self._root

    def for_world(self, world: object) -> Result[WorldStore]:
        """The :class:`WorldStore` for ``world``, or a refusal.

        ``world = simulated`` has no governed namespace in V1, so requesting its store
        is a ``policy rejection`` — no simulated evidence can be written (DEC-0110).
        ``live`` and ``replay`` each resolve to their own namespace directory; the
        bundle is built once per world and cached so the four boundaries share engines.
        """
        namespace = namespace_for_write(world)
        if not is_ok(namespace):
            return namespace
        resolved = world if isinstance(world, World) else World(str(world))
        cached = self._worlds.get(resolved)
        if cached is not None:
            return Ok(cached)
        bundle = self._build(resolved, namespace.value)
        self._worlds[resolved] = bundle
        return Ok(bundle)

    def _build(self, world: World, namespace: str) -> WorldStore:
        """Wire the four boundaries for ``world`` under its namespace directory.

        This is the composition root — the one place the concrete JSONL engine is
        named. It builds one :class:`~qmf.data.store.engines.AppendStreamOpener` bound
        to the JSONL engine and the rotation size, and injects it into every append
        boundary, so no boundary signature names the concrete engine (M3).
        """
        base = self._root / namespace
        registry_dir = base / "registry-room"
        raw_engine = ParquetColumnarEngine(base / "immutable-raw-archive")
        view_engine = DuckDbAnalyticsEngine(base / "processed" / "views.duckdb")
        record_engine = SqliteMetadataEngine(registry_dir / "records.sqlite")
        journal_dir = base / "journal"
        lineage_dir = registry_dir / "lineage"
        open_stream = jsonl_opener(self._rotation_bytes)
        return WorldStore(
            world=world,
            append_store=AppendStore(
                world, raw_engine=raw_engine, view_engine=view_engine, seal=self._seal
            ),
            journal=JournalStore(world, journal_dir=journal_dir, open_stream=open_stream),
            registry_room=RegistryRoom(
                world,
                record_engine=record_engine,
                lineage_dir=lineage_dir,
                open_stream=open_stream,
            ),
            backup_input=BackupInput(
                world,
                raw_engine=raw_engine,
                record_engine=record_engine,
                journal_dir=journal_dir,
                lineage_dir=lineage_dir,
                open_stream=open_stream,
                seal=self._seal,
            ),
        )
