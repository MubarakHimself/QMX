"""Read-only fold access over daemon persistence files (FR-Q22; AD-6).

A fold process may open SQLite and journal files read-only on the daemon host and
may never checkpoint or write them. DuckDB is limited to rebuildable fold views
and is never an evidence store.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from qmf.core import Ok, Result
from qmf.data.store.engines.duckdb_views import DuckDbAnalyticsEngine
from qmf.data.store.refusals import policy_rejection, storage_failure

__all__ = ["DUCKDB_IS_EVIDENCE", "FoldSqliteReader", "FoldViewEngine"]

# DuckDB holds rebuildable fold views only — never evidence (AD-6).
DUCKDB_IS_EVIDENCE = False


@dataclass(frozen=True, slots=True)
class FoldViewEngine:
    """DuckDB fold views — rebuildable only, never evidence-bearing."""

    engine: DuckDbAnalyticsEngine
    is_evidence_bearing: bool = DUCKDB_IS_EVIDENCE

    def __post_init__(self) -> None:
        if self.is_evidence_bearing:
            msg = "DuckDB fold views are never evidence-bearing (FR-Q22; AD-6)"
            raise ValueError(msg)


class FoldSqliteReader:
    """Read-only SQLite handle for fold rebuilds — never writes, never checkpoints."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @property
    def db_path(self) -> Path:
        return self._db_path

    def open(self) -> Result[None]:
        """Open the daemon SQLite file read-only (URI ``mode=ro``)."""
        if not self._db_path.is_file():
            return storage_failure(
                "daemon SQLite file does not exist for read-only fold open",
                context={"field": "fold_sqlite", "db": str(self._db_path)},
            )
        try:
            uri = self._db_path.resolve().as_uri() + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            # Guard against accidental write APIs on this handle.
            conn.execute("PRAGMA query_only = ON")
        except sqlite3.Error as exc:
            return storage_failure(
                f"could not open daemon SQLite read-only for fold: {exc}",
                context={"field": "fold_sqlite", "db": str(self._db_path)},
            )
        self._conn = conn
        return Ok(None)

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
        """Run a read query on the fold connection."""
        if self._conn is None:
            raise RuntimeError("fold SQLite reader is not open")
        cur = self._conn.execute(sql, parameters)
        return list(cur.fetchall())

    def checkpoint(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — folds may never checkpoint (FR-Q22; AD-6)."""
        return policy_rejection(
            "fold_checkpoint",
            "a read-only fold process may open persistence files read-only and may "
            "never checkpoint or write them (FR-Q22; AD-6)",
            db=str(self._db_path),
        )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def open_fold_views(duckdb_path: Path) -> FoldViewEngine:
    """Bind DuckDB as rebuildable fold views only (never evidence)."""
    return FoldViewEngine(engine=DuckDbAnalyticsEngine(duckdb_path), is_evidence_bearing=False)
