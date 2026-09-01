"""One writable SQLite connection in one dedicated thread (FR-Q22; AD-6).

Every checkpoint — automatic or explicit — runs on that same connection. A second
writable connection is never opened from this writer. Read-only folds use
:class:`~qma.daemon.persistence.fold.FoldSqliteReader` instead and never
checkpoint.
"""

from __future__ import annotations

import contextlib
import queue
import sqlite3
import threading
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, cast

from qma.daemon.persistence.schema import (
    KNOWN_STORE_SCHEMA_VERSION,
    SQLITE_META_SCHEMA_KEY,
    ensure_sqlite_schema_version,
)
from qmf.core import Ok, Result, TypedRefusal, is_refusal
from qmf.data.store.refusals import policy_rejection, storage_failure

__all__ = ["SingleSqliteWriter", "SqliteStartupEvidence"]

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class SqliteStartupEvidence:
    """Startup assertion of ``sqlite3.sqlite_version`` — evidence, not a floor."""

    sqlite_version: str
    db_path: str
    journal_mode: str
    thread_name: str
    store_schema_version: int = KNOWN_STORE_SCHEMA_VERSION


class SingleSqliteWriter:
    """Sole writable SQLite handle for the daemon store (one connection, one thread)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._thread_id: int | None = None
        self._closed = False
        self._queue: queue.Queue[tuple[Callable[[], object], Future[object]] | None] = queue.Queue()
        self._thread = threading.Thread(
            target=self._run,
            name="qma-daemon-sqlite",
            daemon=True,
        )
        self._started = threading.Event()
        self._start_error: BaseException | None = None
        self._schema_refusal: TypedRefusal | None = None
        self._store_schema_version: int = KNOWN_STORE_SCHEMA_VERSION

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def thread_name(self) -> str:
        return self._thread.name

    def start(self) -> Result[SqliteStartupEvidence]:
        """Open the one writable WAL connection on the dedicated writer thread."""
        if self._closed:
            return policy_rejection(
                "sqlite_writer",
                "the sole writable SQLite connection is closed and cannot restart",
                db=str(self._db_path),
            )
        if self._started.is_set() and self._conn is not None:
            return Ok(self._evidence())
        self._thread.start()
        self._started.wait(timeout=30)
        if self._start_error is not None:
            return storage_failure(
                f"could not open the sole writable SQLite connection: {self._start_error}",
                context={"field": "sqlite_writer", "db": str(self._db_path)},
            )
        if self._schema_refusal is not None:
            return self._schema_refusal
        if self._conn is None:
            return storage_failure(
                "sole writable SQLite connection failed to start",
                context={"field": "sqlite_writer", "db": str(self._db_path)},
            )
        return Ok(self._evidence())

    def _require_conn(self) -> sqlite3.Connection:
        conn = self._conn
        if conn is None:
            raise RuntimeError("sole writable SQLite connection is not open")
        return conn

    def _evidence(self) -> SqliteStartupEvidence:
        def _mode() -> str:
            row = self._require_conn().execute("PRAGMA journal_mode").fetchone()
            if row is None:
                return "unknown"
            return str(row[0])

        mode = self._submit(_mode)
        return SqliteStartupEvidence(
            sqlite_version=sqlite3.sqlite_version,
            db_path=str(self._db_path),
            journal_mode=mode,
            thread_name=self._thread.name,
            store_schema_version=self._store_schema_version,
        )

    def _run(self) -> None:
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._db_path, check_same_thread=True)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS daemon_meta ("
                "key TEXT PRIMARY KEY NOT NULL, "
                "value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO daemon_meta (key, value) VALUES (?, ?)",
                ("sqlite_version", sqlite3.sqlite_version),
            )
            row = conn.execute(
                "SELECT value FROM daemon_meta WHERE key = ?",
                (SQLITE_META_SCHEMA_KEY,),
            ).fetchone()
            existing = None if row is None else str(row[0])

            def _stamp(version: int) -> None:
                conn.execute(
                    "INSERT OR REPLACE INTO daemon_meta (key, value) VALUES (?, ?)",
                    (SQLITE_META_SCHEMA_KEY, str(version)),
                )

            gated = ensure_sqlite_schema_version(
                read_value=existing,
                write_value=_stamp,
            )
            if is_refusal(gated):
                conn.close()
                self._schema_refusal = gated
                self._started.set()
                return
            self._store_schema_version = gated.value
            conn.commit()
            self._conn = conn
            self._thread_id = threading.get_ident()
        except BaseException as exc:
            self._start_error = exc
            self._started.set()
            return
        self._started.set()
        while True:
            item = self._queue.get()
            if item is None:
                break
            fn, fut = item
            try:
                fut.set_result(fn())
            except BaseException as exc:
                fut.set_exception(exc)

    def _submit(self, fn: Callable[[], _T]) -> _T:
        if self._closed or self._conn is None:
            raise RuntimeError("sole writable SQLite connection is not open")
        if threading.get_ident() == self._thread_id:
            return fn()
        fut: Future[object] = Future()
        self._queue.put((fn, fut))
        return cast("_T", fut.result())

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
        """Run ``sql`` on the sole writable connection."""

        def _work() -> list[tuple[object, ...]]:
            conn = self._require_conn()
            cur = conn.execute(sql, parameters)
            rows = cur.fetchall()
            conn.commit()
            return list(rows)

        return self._submit(_work)

    def checkpoint(self, mode: str = "PASSIVE") -> tuple[int, int, int]:
        """Run ``PRAGMA wal_checkpoint`` on the sole writable connection only."""
        allowed = {"PASSIVE", "FULL", "RESTART", "TRUNCATE"}
        if mode not in allowed:
            raise ValueError(f"unsupported wal_checkpoint mode {mode!r}")

        def _work() -> tuple[int, int, int]:
            conn = self._require_conn()
            row = conn.execute(f"PRAGMA wal_checkpoint({mode})").fetchone()
            if row is None:
                raise RuntimeError("wal_checkpoint returned no row")
            return int(row[0]), int(row[1]), int(row[2])

        return self._submit(_work)

    def recorded_sqlite_version(self) -> str:
        """The ``sqlite3.sqlite_version`` stamped into daemon_meta at open."""
        rows = self.execute(
            "SELECT value FROM daemon_meta WHERE key = ?",
            ("sqlite_version",),
        )
        if not rows:
            return sqlite3.sqlite_version
        return str(rows[0][0])

    def recorded_store_schema_version(self) -> int:
        """The ``store_schema_version`` stamped into daemon_meta at open."""
        rows = self.execute(
            "SELECT value FROM daemon_meta WHERE key = ?",
            (SQLITE_META_SCHEMA_KEY,),
        )
        if not rows:
            return self._store_schema_version
        return int(str(rows[0][0]))

    def connection_count_evidence(self) -> int:
        """Always 1 while open — the sole writable connection in this writer."""
        if self._conn is None or self._closed:
            return 0
        return 1

    def close(self) -> None:
        """Checkpoint, close the sole connection, and stop the writer thread."""
        if self._closed:
            return
        if self._conn is not None and self._started.is_set() and self._start_error is None:

            def _shutdown() -> None:
                conn = self._require_conn()
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.close()

            with contextlib.suppress(RuntimeError):
                self._submit(_shutdown)
            self._queue.put(None)
            self._thread.join(timeout=30)
            self._conn = None
        self._closed = True
