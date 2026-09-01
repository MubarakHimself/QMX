"""``store_schema_version`` stamping and open gate (FR-Q37; AD-27; DEC-0326).

The journal and the SQLite store each stamp a ``store_schema_version``. The
daemon validates the stamp before reading records, refuses an unknown or newer
version with a typed refusal naming the store and both versions, never reads a
newer store optimistically, and never silently upgrades one.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

from qma.core.refusals import StoreVersionMismatch
from qmf.core import Ok, Result, is_refusal

__all__ = [
    "JOURNAL_SCHEMA_MARKER_NAME",
    "JOURNAL_STORE_NAME",
    "KNOWN_STORE_SCHEMA_VERSION",
    "SQLITE_META_SCHEMA_KEY",
    "SQLITE_STORE_NAME",
    "VERSIONED_OPEN_STORES",
    "ensure_journal_schema_version",
    "ensure_sqlite_schema_version",
    "read_journal_schema_version",
    "refuse_unknown_store_schema",
    "stamp_journal_schema_version",
    "validate_store_schema_version",
]

# V1 known schema — a newer or otherwise unknown stamp is refused (DEC-0326).
KNOWN_STORE_SCHEMA_VERSION: Final[int] = 1

JOURNAL_STORE_NAME: Final[str] = "journal"
SQLITE_STORE_NAME: Final[str] = "sqlite"
VERSIONED_OPEN_STORES: Final[frozenset[str]] = frozenset(
    {JOURNAL_STORE_NAME, SQLITE_STORE_NAME}
)

JOURNAL_SCHEMA_MARKER_NAME: Final[str] = "journal.store_schema_version"
SQLITE_META_SCHEMA_KEY: Final[str] = "store_schema_version"


def refuse_unknown_store_schema(
    *,
    store: str,
    expected_schema_version: int,
    store_schema_version: int,
) -> StoreVersionMismatch:
    """Typed refusal naming the store and both schema versions (FM-17)."""
    return StoreVersionMismatch.of(
        store=store,
        expected_schema_version=expected_schema_version,
        store_schema_version=store_schema_version,
    )


def validate_store_schema_version(
    *,
    store: str,
    stamped: int,
    known: int = KNOWN_STORE_SCHEMA_VERSION,
) -> Result[int]:
    """Accept only a stamp equal to the daemon's known schema version.

    An unknown or newer stamp is refused — never read optimistically and never
    silently upgraded (FR-Q37; AD-27).
    """
    if isinstance(stamped, bool) or stamped < 1:
        return refuse_unknown_store_schema(
            store=store,
            expected_schema_version=known,
            store_schema_version=-1 if isinstance(stamped, bool) else stamped,
        )
    if stamped != known:
        return refuse_unknown_store_schema(
            store=store,
            expected_schema_version=known,
            store_schema_version=stamped,
        )
    return Ok(stamped)


def _journal_marker_path(daemon_dir: Path) -> Path:
    return daemon_dir / JOURNAL_SCHEMA_MARKER_NAME


def read_journal_schema_version(daemon_dir: Path | str) -> int | None:
    """Return the stamped journal schema version, or ``None`` when unmarked."""
    path = _journal_marker_path(Path(daemon_dir))
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return -1


def stamp_journal_schema_version(
    daemon_dir: Path | str,
    *,
    version: int = KNOWN_STORE_SCHEMA_VERSION,
) -> Path:
    """Write the journal ``store_schema_version`` marker (first-open stamp)."""
    path = _journal_marker_path(Path(daemon_dir))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{version}\n", encoding="utf-8")
    return path


def ensure_journal_schema_version(
    daemon_dir: Path | str,
    *,
    known: int = KNOWN_STORE_SCHEMA_VERSION,
) -> Result[int]:
    """Validate or stamp the journal schema marker before reading records."""
    stamped = read_journal_schema_version(daemon_dir)
    if stamped is None:
        stamp_journal_schema_version(daemon_dir, version=known)
        return Ok(known)
    return validate_store_schema_version(
        store=JOURNAL_STORE_NAME,
        stamped=stamped,
        known=known,
    )


def ensure_sqlite_schema_version(
    *,
    read_value: str | None,
    write_value: Callable[[int], None],
    known: int = KNOWN_STORE_SCHEMA_VERSION,
) -> Result[int]:
    """Validate or stamp SQLite ``daemon_meta.store_schema_version``.

    ``read_value`` is the existing meta row (or ``None``). ``write_value`` is a
    callable ``(version: int) -> None`` that persists the stamp on first open.
    """
    if read_value is None:
        write_value(known)
        return Ok(known)
    try:
        stamped = int(read_value)
    except (TypeError, ValueError):
        return refuse_unknown_store_schema(
            store=SQLITE_STORE_NAME,
            expected_schema_version=known,
            store_schema_version=-1,
        )
    checked = validate_store_schema_version(
        store=SQLITE_STORE_NAME,
        stamped=stamped,
        known=known,
    )
    if is_refusal(checked):
        return checked
    return checked
