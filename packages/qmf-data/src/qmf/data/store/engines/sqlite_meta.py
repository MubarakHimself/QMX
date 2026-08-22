"""SQLite transactional-metadata engine — registry records (AC1; DEC-0114).

The concrete :class:`~qmf.data.store.engines.MetadataEngine`. Registry per-kind
versioned records persist as rows in one SQLite database keyed on the record's fp1
digest, **append-only**: a record is inserted once and never rewritten in place
(a correction is a new record with a new digest and a lineage edge). The stored
``canonical`` bytes are the record's exact identity content, so the guard reconciles
a re-write against them exactly.

SQLite is the stdlib ``sqlite3`` module — no database server (DEC-0117). A locked,
truncated, or corrupt database surfaces as a
:class:`~qmf.data.store.engines.StoreEngineError`, which the boundary translates to a
``storage failure`` refusal (AC4). Retryability is classified by exception **type**,
never by string-matching the message (L3): only a locked/busy database is retryable;
a constraint violation (``IntegrityError``) and a corrupt/malformed database are
permanent, so neither is reported as a retryable failure that would invite an
infinite retry.

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
                retryable=_retryable(exc),
                detail={"db": str(self._db_path), "error": str(exc)},
            ) from exc
        try:
            conn.execute(_SCHEMA)
        except sqlite3.Error as exc:
            conn.close()  # never leak the handle when the schema step fails (corrupt db)
            raise StoreEngineError(
                "could not initialize the SQLite metadata schema (corrupt database)",
                engine="sqlite",
                retryable=_retryable(exc),
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
                retryable=_retryable(exc),
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
                retryable=_retryable(exc),
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
                retryable=_retryable(exc),
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
                retryable=_retryable(exc),
                detail={"db": str(self._db_path), "error": str(exc)},
            ) from exc
        finally:
            conn.close()
        return [cast("str", row[0]) for row in rows]


def _retryable(exc: Exception) -> bool:
    """Whether a SQLite/OS failure is worth retrying, classified by exception TYPE (L3).

    A constraint violation (``sqlite3.IntegrityError`` — e.g. a duplicate primary key)
    is permanent: retrying re-fails, so it must never be reported as retryable (an
    infinite-retry invitation). A locked or busy database (``sqlite3.OperationalError``
    naming "locked"/"busy") is transient and retryable. Any other ``sqlite3.DatabaseError``
    (a corrupt or malformed database, "file is not a database") is permanent. A bare
    ``OSError`` (a disk that may free up) is retryable by default.
    """
    if isinstance(exc, sqlite3.IntegrityError):
        return False
    if isinstance(exc, sqlite3.OperationalError):
        text = str(exc).lower()
        return "locked" in text or "busy" in text
    # Any other sqlite3.DatabaseError (corrupt/malformed) is permanent; a bare OSError
    # (a disk that may free up) is transient.
    return not isinstance(exc, sqlite3.DatabaseError)
