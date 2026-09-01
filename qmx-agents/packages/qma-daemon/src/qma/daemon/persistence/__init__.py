"""Sole-writer persistence substrate (FR-Q22; AD-4, AD-6).

One Python asyncio daemon owns durable writes to the event journal, SQLite store,
and artifact store through qmf-data sinks. Folds may open files read-only and never
checkpoint; DuckDB holds rebuildable views only.
"""

from __future__ import annotations

from qma.daemon.persistence.fold import (
    DUCKDB_IS_EVIDENCE,
    FoldSqliteReader,
    FoldViewEngine,
    open_fold_views,
)
from qma.daemon.persistence.lock import DAEMON_LOCK_NAME, DaemonWriterLock, WriterLockToken
from qma.daemon.persistence.sqlite_writer import SingleSqliteWriter, SqliteStartupEvidence
from qma.daemon.persistence.substrate import (
    DAEMON_WRITER_ROLE,
    PersistenceStartupEvidence,
    PersistenceSubstrate,
)

__all__ = [
    "DAEMON_LOCK_NAME",
    "DAEMON_WRITER_ROLE",
    "DUCKDB_IS_EVIDENCE",
    "DaemonWriterLock",
    "FoldSqliteReader",
    "FoldViewEngine",
    "PersistenceStartupEvidence",
    "PersistenceSubstrate",
    "SingleSqliteWriter",
    "SqliteStartupEvidence",
    "WriterLockToken",
    "open_fold_views",
]
