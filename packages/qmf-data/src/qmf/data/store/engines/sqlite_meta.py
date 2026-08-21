"""SQLite transactional-metadata engine — registry records (AC1; DEC-0114).

The concrete :class:`~qmf.data.store.engines.MetadataEngine`. Registry per-kind
versioned records persist as rows in one SQLite database keyed on the record's fp1
digest, **append-only**: a record is inserted once and never rewritten in place
(a correction is a new record with a new digest and a lineage edge). The stored
``canonical`` bytes are the record's exact identity content, so the guard reconciles
a re-write against them exactly.

SQLite is the stdlib ``sqlite3`` module — no database server (DEC-0117). A locked,
truncated, or corrupt database surfaces as a
:class:`~qmf.data.store.engines.StoreEngineError` (a locked db is retryable; a corrupt
one is not), which the boundary translates to a ``storage failure`` refusal (AC4).

Stdlib only.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from qmf.data.store.engines import StoreEngineError

__all__ = ["SqliteMetadataEngine"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    digest         TEXT PRIMARY KEY,
    canonical      BLOB NOT NULL,
    kind           TEXT NOT NULL,
    format_version INTEGER NOT NULL
)
"""


class SqliteMetadataEngine:
    """Append-only content-addressed record storage over one SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with the schema ensured (raises on physical failure)."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._db_path)
        except (OSError, sqlite3.Error) as exc:
            raise StoreEngineError(
                "could not open the SQLite metadata database",
                engine="sqlite",
                retryable=not _is_corruption(exc),
                detail={"db": str(self._db_path), "error": str(exc)},
            ) from exc
        try:
            conn.execute(_SCHEMA)
        except sqlite3.Error as exc:
            conn.close()  # never leak the handle when the schema step fails (corrupt db)
            raise StoreEngineError(
                "could not initialize the SQLite metadata schema (corrupt database)",
                engine="sqlite",
                retryable=not _is_corruption(exc),
                detail={"db": str(self._db_path), "error": str(exc)},
            ) from exc
        return conn

    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        """Insert a record's canonical bytes under ``digest`` (append-only; raises).

        A plain ``INSERT`` — never ``INSERT OR REPLACE`` — so an existing row is never
        overwritten; the guard admits only a genuine first write here.
        """
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO records (digest, canonical, kind, format_version) VALUES (?, ?, ?, ?)",
                (digest, canonical, kind, format_version),
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise StoreEngineError(
                "could not insert the registry record",
                engine="sqlite",
                retryable=not _is_corruption(exc),
                detail={"digest": digest, "error": str(exc)},
            ) from exc
        finally:
            conn.close()

    def get(self, digest: str, /) -> bytes | None:
        """The canonical bytes stored under ``digest``, or ``None`` (raises on failure)."""
        conn = self._connect()
        try:
            cursor = conn.execute("SELECT canonical FROM records WHERE digest = ?", (digest,))
            row = cursor.fetchone()
        except sqlite3.Error as exc:
            raise StoreEngineError(
                "could not read the registry record",
                engine="sqlite",
                retryable=not _is_corruption(exc),
                detail={"digest": digest, "error": str(exc)},
            ) from exc
        finally:
            conn.close()
        if row is None:
            return None
        return cast("bytes", row[0])

    def meta(self, digest: str, /) -> Mapping[str, object] | None:
        """The ``kind`` / ``format_version`` metadata for ``digest``, or ``None``."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT kind, format_version FROM records WHERE digest = ?", (digest,)
            )
            row = cursor.fetchone()
        except sqlite3.Error as exc:
            raise StoreEngineError(
                "could not read the registry record metadata",
                engine="sqlite",
                retryable=not _is_corruption(exc),
                detail={"digest": digest, "error": str(exc)},
            ) from exc
        finally:
            conn.close()
        if row is None:
            return None
        return {"kind": cast("str", row[0]), "format_version": cast("int", row[1])}

    def digests(self) -> list[str]:
        """Every stored record digest, ascending (raises on failure)."""
        conn = self._connect()
        try:
            cursor = conn.execute("SELECT digest FROM records ORDER BY digest")
            rows = cursor.fetchall()
        except sqlite3.Error as exc:
            raise StoreEngineError(
                "could not list the registry records",
                engine="sqlite",
                retryable=not _is_corruption(exc),
                detail={"db": str(self._db_path), "error": str(exc)},
            ) from exc
        finally:
            conn.close()
        return [cast("str", row[0]) for row in rows]


def _is_corruption(exc: Exception) -> bool:
    """Whether a SQLite error names a corrupt/malformed database (not retryable)."""
    return isinstance(exc, sqlite3.DatabaseError) and "malformed" in str(exc).lower()
