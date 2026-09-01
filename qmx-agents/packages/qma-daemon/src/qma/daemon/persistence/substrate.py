"""Single-process sole-writer persistence substrate (Story 42.1; FR-Q22; AD-4, AD-6).

Exactly one Python 3.14 asyncio daemon owns durable writes. Journal (JSONL), the
daemon SQLite store (WAL, one connection in one thread), and the artifact store
reach disk only through qmf-data sinks behind this boundary. A second daemon or
writer is refused before it can open an alternate durable-write path.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from qma.daemon.persistence.fold import (
    FoldSqliteReader,
    FoldViewEngine,
    open_fold_views,
)
from qma.daemon.persistence.lock import DaemonWriterLock, WriterLockToken
from qma.daemon.persistence.schema import ensure_journal_schema_version
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter, SqliteStartupEvidence
from qmf.core import Ok, Result, World, WriterId, is_ok, is_refusal
from qmf.data import EvidenceStore
from qmf.data.store.append_store import AppendStore
from qmf.data.store.facade import WorldStore
from qmf.data.store.journal import JournalStore
from qmf.data.store.refusals import policy_rejection

__all__ = [
    "DAEMON_WRITER_ROLE",
    "PersistenceStartupEvidence",
    "PersistenceSubstrate",
]

DAEMON_WRITER_ROLE = "qma-daemon"


class _ProcessGate:
    """In-process singleton gate — at most one open PersistenceSubstrate."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.holder: PersistenceSubstrate | None = None


_process_gate = _ProcessGate()


@dataclass(frozen=True, slots=True)
class PersistenceStartupEvidence:
    """Evidence recorded when the sole-writer substrate opens."""

    sqlite_version: str
    journal_mode: str
    sqlite_thread_name: str
    db_path: str
    root: str
    writer_token: str


class PersistenceSubstrate:
    """Sole durable-write boundary for journal, SQLite, and artifact store."""

    def __init__(
        self,
        root: Path,
        *,
        lock: DaemonWriterLock,
        evidence_store: EvidenceStore,
        world_store: WorldStore,
        sqlite: SingleSqliteWriter,
        startup: PersistenceStartupEvidence,
        writer: WriterId,
    ) -> None:
        self._root = root
        self._lock = lock
        self._evidence_store = evidence_store
        self._world_store = world_store
        self._sqlite = sqlite
        self._startup = startup
        self._writer = writer
        self._closed = False

    @classmethod
    def open(
        cls,
        root: Path | str,
        *,
        machine: str,
        boot_epoch_id: str,
        world: World = World.LIVE,
    ) -> Result[PersistenceSubstrate]:
        """Establish the one sole-writer persistence boundary for this process.

        Refuses when another PersistenceSubstrate is already open in-process or when
        the on-disk sole-writer lock is held by a distinct writer.
        """
        resolved = Path(root)
        writer_result = WriterId.try_create(
            machine, DAEMON_WRITER_ROLE, "daemon-persistence", boot_epoch_id
        )
        if is_refusal(writer_result):
            return writer_result
        writer = writer_result.value

        with _process_gate.lock:
            holder = _process_gate.holder
            if holder is not None and not holder._closed:
                return policy_rejection(
                    "daemon_runtime",
                    "exactly one Python asyncio daemon may own the persistence "
                    "substrate in a process; a second daemon runtime is refused "
                    "(FR-Q22; AD-4, AD-6)",
                    holder_root=str(holder.root),
                    attempted_root=str(resolved),
                )

            token = WriterLockToken(
                machine=machine,
                role=DAEMON_WRITER_ROLE,
                boot_epoch_id=boot_epoch_id,
                pid=os.getpid(),
            )
            lock = DaemonWriterLock(resolved, token)
            acquired = lock.acquire()
            if is_refusal(acquired):
                return acquired

            evidence_store = EvidenceStore(resolved / "qmf-data")
            world_bundle = evidence_store.for_world(world)
            if not is_ok(world_bundle):
                lock.release()
                return world_bundle

            daemon_dir = resolved / "daemon"
            journal_schema = ensure_journal_schema_version(daemon_dir)
            if is_refusal(journal_schema):
                lock.release()
                return journal_schema

            sqlite_path = daemon_dir / "daemon.sqlite"
            sqlite = SingleSqliteWriter(sqlite_path)
            sqlite_started = sqlite.start()
            if is_refusal(sqlite_started):
                lock.release()
                return sqlite_started
            sqlite_evidence: SqliteStartupEvidence = sqlite_started.value

            startup = PersistenceStartupEvidence(
                sqlite_version=sqlite_evidence.sqlite_version,
                journal_mode=sqlite_evidence.journal_mode,
                sqlite_thread_name=sqlite_evidence.thread_name,
                db_path=sqlite_evidence.db_path,
                root=str(resolved),
                writer_token=token.encode(),
            )
            substrate = cls(
                resolved,
                lock=lock,
                evidence_store=evidence_store,
                world_store=world_bundle.value,
                sqlite=sqlite,
                startup=startup,
                writer=writer,
            )
            _process_gate.holder = substrate
            return Ok(substrate)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def startup_evidence(self) -> PersistenceStartupEvidence:
        """``sqlite3.sqlite_version`` and open facts recorded at startup."""
        return self._startup

    @property
    def writer(self) -> WriterId:
        return self._writer

    @property
    def evidence_store(self) -> EvidenceStore:
        """qmf-data EvidenceStore — JSONL journal, SQLite registry room, artifacts."""
        return self._evidence_store

    @property
    def world_store(self) -> WorldStore:
        """Per-world qmf-data sinks (journal, append/artifact, registry, backup)."""
        return self._world_store

    @property
    def journal(self) -> JournalStore:
        """JSONL append journal sink (CT-13) — sole durable append path for events."""
        return self._world_store.journal

    @property
    def artifact_store(self) -> AppendStore:
        """Artifact / raw-archive sink through qmf-data AppendStore (CT-11)."""
        return self._world_store.append_store

    @property
    def sqlite(self) -> SingleSqliteWriter:
        """The one writable SQLite connection (checkpoints only through here)."""
        return self._sqlite

    def open_fold_reader(self) -> Result[FoldSqliteReader]:
        """Open the daemon SQLite file read-only for a fold rebuild (never checkpoints)."""
        reader = FoldSqliteReader(self._sqlite.db_path)
        opened = reader.open()
        if is_refusal(opened):
            return opened
        return Ok(reader)

    def open_fold_views(self) -> FoldViewEngine:
        """DuckDB rebuildable fold views only — never an evidence store."""
        return open_fold_views(self._root / "qmf-data" / "live" / "processed" / "views.duckdb")

    def close(self) -> None:
        """Release the sole-writer lock and close the SQLite writer."""
        if self._closed:
            return
        self._closed = True
        self._world_store.journal.close()
        self._sqlite.close()
        self._lock.release()
        with _process_gate.lock:
            if _process_gate.holder is self:
                _process_gate.holder = None

    def __enter__(self) -> PersistenceSubstrate:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
