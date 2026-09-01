"""Sole-writer persistence substrate (FR-Q22; AD-4, AD-6).

One Python asyncio daemon owns durable writes to the event journal, SQLite store,
and artifact store through qmf-data sinks. Folds may open files read-only and never
checkpoint; DuckDB holds rebuildable views only.

Store lifecycle (FR-Q37) lives in :mod:`qma.daemon.persistence.lifecycle` and
:mod:`qma.daemon.persistence.schema`; those modules are imported by callers
directly so this package init does not cycle with the journal package.
"""

from __future__ import annotations

from qma.daemon.persistence.fold import (
    DUCKDB_IS_EVIDENCE,
    FoldSqliteReader,
    FoldViewEngine,
    open_fold_views,
)
from qma.daemon.persistence.lock import DAEMON_LOCK_NAME, DaemonWriterLock, WriterLockToken
from qma.daemon.persistence.schema import (
    JOURNAL_STORE_NAME,
    KNOWN_STORE_SCHEMA_VERSION,
    SQLITE_STORE_NAME,
    VERSIONED_OPEN_STORES,
    ensure_journal_schema_version,
    ensure_sqlite_schema_version,
    refuse_unknown_store_schema,
    stamp_journal_schema_version,
    validate_store_schema_version,
)
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
    "JOURNAL_STORE_NAME",
    "KNOWN_STORE_SCHEMA_VERSION",
    "SQLITE_STORE_NAME",
    "VERSIONED_OPEN_STORES",
    "DaemonWriterLock",
    "FoldSqliteReader",
    "FoldViewEngine",
    "PersistenceStartupEvidence",
    "PersistenceSubstrate",
    "SingleSqliteWriter",
    "SqliteStartupEvidence",
    "WriterLockToken",
    "ensure_journal_schema_version",
    "ensure_sqlite_schema_version",
    "open_fold_views",
    "refuse_unknown_store_schema",
    "stamp_journal_schema_version",
    "validate_store_schema_version",
]
