"""DuckDB analytics engine — rebuildable views ONLY (AC1; DEC-0117, DEC-0103).

The concrete :class:`~qmf.data.store.engines.AnalyticsEngine`. A processed/analytics
artifact is materialized as rows in one local DuckDB database and is **never
evidence-bearing**: its pinned engine major is recorded, a format break costs a
rebuild rather than evidence, and deletion is licensed for any view no result label
cites. Each artifact's rows are stored as queryable JSON payloads (DuckDB's native
JSON), and the exact fp1 canonical bytes are held in an identity table so a rebuild
reconciles against the original bytes.

DuckDB is embedded — no database server (DEC-0117). Every ``duckdb.Error`` /
``OSError`` is wrapped into the one :class:`~qmf.data.store.engines.StoreEngineError`
so the boundary translates it (AC4). DuckDB ships type stubs, so this module stays
strictly typed.

Stdlib + duckdb only; DuckDB is a store engine declared only in qmf-data's pyproject.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import duckdb
from qmf.data.store.engines import StoreEngineError

__all__ = ["DuckDbAnalyticsEngine"]

_IDENTITY_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS _qmf_identity (key VARCHAR PRIMARY KEY, canonical BLOB)"
)
_ROWS_SCHEMA = "CREATE TABLE IF NOT EXISTS _qmf_view_rows (key VARCHAR, seq BIGINT, payload JSON)"


class DuckDbAnalyticsEngine:
    """Rebuildable analytics-view storage over one embedded DuckDB database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self) -> duckdb.DuckDBPyConnection:
        """Open a connection with the identity + rows tables ensured (raises)."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = duckdb.connect(str(self._db_path))
            conn.execute(_IDENTITY_SCHEMA)
            conn.execute(_ROWS_SCHEMA)
            return conn
        except (OSError, duckdb.Error) as exc:
            raise StoreEngineError(
                "could not open the DuckDB analytics database",
                engine="duckdb",
                detail={"db": str(self._db_path), "error": str(exc)},
            ) from exc

    def materialize(
        self, key: str, rows: Sequence[Mapping[str, object]], canonical: bytes, /
    ) -> None:
        """(Re)build the view ``key`` from ``rows``, embedding ``canonical`` (raises).

        Rebuildable: an existing view under this key is dropped and rewritten, since a
        materialized view is never evidence and a rebuild is always licensed.
        """
        conn = self._connect()
        try:
            conn.execute("DELETE FROM _qmf_view_rows WHERE key = ?", [key])
            conn.execute("DELETE FROM _qmf_identity WHERE key = ?", [key])
            for seq, row in enumerate(rows):
                conn.execute(
                    "INSERT INTO _qmf_view_rows (key, seq, payload) VALUES (?, ?, ?)",
                    [key, seq, json.dumps(dict(row), sort_keys=True)],
                )
            conn.execute(
                "INSERT INTO _qmf_identity (key, canonical) VALUES (?, ?)", [key, canonical]
            )
            conn.commit()
        except (OSError, duckdb.Error, TypeError, ValueError) as exc:
            raise StoreEngineError(
                "could not materialize the DuckDB analytics view",
                engine="duckdb",
                detail={"key": key, "error": str(exc)},
            ) from exc
        finally:
            conn.close()

    def query(self, key: str, /) -> list[dict[str, object]]:
        """Query the materialized view ``key`` (raises if absent or corrupt)."""
        conn = self._connect()
        try:
            present = conn.execute("SELECT 1 FROM _qmf_identity WHERE key = ?", [key]).fetchone()
            if present is None:
                raise StoreEngineError(
                    "the DuckDB analytics view is not materialized",
                    engine="duckdb",
                    retryable=False,
                    detail={"key": key},
                )
            result = conn.execute(
                "SELECT payload FROM _qmf_view_rows WHERE key = ? ORDER BY seq", [key]
            ).fetchall()
        except duckdb.Error as exc:
            raise StoreEngineError(
                "could not query the DuckDB analytics view (locked or corrupt)",
                engine="duckdb",
                retryable=False,
                detail={"key": key, "error": str(exc)},
            ) from exc
        finally:
            conn.close()
        return [cast("dict[str, object]", json.loads(cast("str", row[0]))) for row in result]

    def read_canonical(self, key: str, /) -> bytes | None:
        """The embedded fp1 canonical bytes for the view ``key``, or ``None``."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT canonical FROM _qmf_identity WHERE key = ?", [key]
            ).fetchone()
        except duckdb.Error as exc:
            raise StoreEngineError(
                "could not read the DuckDB view identity",
                engine="duckdb",
                retryable=False,
                detail={"key": key, "error": str(exc)},
            ) from exc
        finally:
            conn.close()
        if row is None:
            return None
        return bytes(cast("bytes", row[0]))

    def drop(self, key: str, /) -> None:
        """Drop the rebuildable view ``key`` (licensed for any uncited view; raises)."""
        conn = self._connect()
        try:
            conn.execute("DELETE FROM _qmf_view_rows WHERE key = ?", [key])
            conn.execute("DELETE FROM _qmf_identity WHERE key = ?", [key])
            conn.commit()
        except duckdb.Error as exc:
            raise StoreEngineError(
                "could not drop the DuckDB analytics view",
                engine="duckdb",
                detail={"key": key, "error": str(exc)},
            ) from exc
        finally:
            conn.close()

    def has(self, key: str, /) -> bool:
        """Whether the view ``key`` is materialized (raises on failure)."""
        conn = self._connect()
        try:
            row = conn.execute("SELECT 1 FROM _qmf_identity WHERE key = ?", [key]).fetchone()
        except duckdb.Error as exc:
            raise StoreEngineError(
                "could not check the DuckDB analytics view",
                engine="duckdb",
                retryable=False,
                detail={"key": key, "error": str(exc)},
            ) from exc
        finally:
            conn.close()
        return row is not None

    def engine_major(self) -> str:
        """The pinned analytics-engine major recorded on every rebuildable view.

        A format break at this major costs a rebuild, never evidence (DEC-0103).
        """
        major = duckdb.__version__.split(".", 1)[0]
        return f"duckdb-{major}"
