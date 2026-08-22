"""The four swappable store engines, each behind its owned contract (AC1; AR-30).

Every artifact the store persists is physically written by **exactly one** of four
ratified local engines, and no database server, graph database, or engine outside
the set is introduced (DEC-0117):

* **Parquet** (:class:`ColumnarEngine`) — columnar time-series (the immutable raw
  archive, evidence-bearing);
* **DuckDB** (:class:`AnalyticsEngine`) — rebuildable analytics views **only**, never
  evidence-bearing;
* **SQLite** (:class:`MetadataEngine`) — transactional metadata (registry records);
* **JSONL** (:class:`AppendStreamEngine`) — append streams (journal + lineage edges).

Each engine is a :class:`typing.Protocol` with **stdlib-typed boundary signatures** —
``str``, ``bytes``, ``int``, ``Mapping``, ``Sequence`` — so no engine-native type
(a ``pyarrow.Table``, a ``duckdb`` connection) ever leaks across the seam and the
engine stays swappable behind its contract. A concrete engine imports its library;
the contract here does not.

A physical failure (engine unavailable, disk full, a locked / truncated / corrupt
file) surfaces as a **single** normalized :class:`StoreEngineError` — the concrete
engine wraps its library's exception into this one type, so a boundary catches one
thing and translates it to a ``storage failure`` refusal without importing any
engine's exception classes (AC4; DEC-0109). ``StoreEngineError`` is raised only
across the *internal* engine seam and is always caught before a package boundary.

Stdlib + qmf-core only in this contract module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from qmf.core import Result

__all__ = [
    "AnalyticsEngine",
    "AppendLocation",
    "AppendStreamEngine",
    "AppendStreamOpener",
    "ColumnarEngine",
    "MetadataEngine",
    "OccurrenceSink",
    "StoreEngineError",
]


class StoreEngineError(Exception):
    """A normalized physical-storage failure raised across the internal engine seam.

    Every concrete engine wraps its library's exception — ``OSError`` (disk full,
    locked, truncated), a ``pyarrow`` error, an ``sqlite3`` error, a ``duckdb``
    error — into this one type, so the boundary catches ``StoreEngineError`` alone
    and translates it to a ``storage failure`` typed refusal (AC4). It never crosses
    a package boundary: it is an internal signal, always caught at the seam.

    ``retryable`` distinguishes a transient outage (a locked file, a disk that may
    free up) from a permanent fault (a corrupt or truncated store); the boundary maps
    it to the refusal's retryability.
    """

    def __init__(
        self,
        reason: str,
        *,
        engine: str,
        retryable: bool = True,
        detail: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.engine = engine
        self.retryable = retryable
        self.detail: dict[str, object] = dict(detail) if detail is not None else {}


@dataclass(frozen=True, slots=True)
class AppendLocation:
    """Where an appended JSONL record landed (AC3).

    ``ordinal`` is the monotonic rotation ordinal of the file it was written to,
    ``byte_offset`` its start within that file, ``length`` the line's byte length
    (LF included), and ``sequence`` its strictly-increasing per-stream position. All
    are plain ints — engine-native types never appear here.
    """

    ordinal: int
    byte_offset: int
    length: int
    sequence: int


class ColumnarEngine(Protocol):
    """Owned contract for the Parquet columnar time-series engine (evidence).

    Stores a whole artifact — an ordered set of JSON-native rows — as one
    content-addressed columnar file keyed by ``key`` (the fp1 digest). The exact
    ``canonical`` identity bytes are embedded in the file so a re-write is reconciled
    against them without a lossy round-trip; :meth:`read` reconstructs the rows.
    Raises :class:`StoreEngineError` on any physical failure.
    """

    def write(
        self, key: str, rows: Sequence[Mapping[str, object]], canonical: bytes, /
    ) -> None:  # pragma: no cover
        """Write ``rows`` under ``key``, embedding ``canonical`` (raises on failure)."""
        ...

    def read(self, key: str, /) -> list[dict[str, object]]:  # pragma: no cover
        """Read the rows stored under ``key`` (raises on failure or if absent)."""
        ...

    def read_canonical(self, key: str, /) -> bytes | None:  # pragma: no cover
        """The embedded fp1 canonical bytes for ``key`` (for reconcile), or ``None``."""
        ...

    def has(self, key: str, /) -> bool:  # pragma: no cover
        """Whether an artifact is stored under ``key`` (raises on failure)."""
        ...

    def stored_keys(self) -> list[str]:  # pragma: no cover
        """Every stored key (the rebuildable content index; raises on failure)."""
        ...


class AnalyticsEngine(Protocol):
    """Owned contract for the DuckDB analytics engine — rebuildable views ONLY.

    A materialized view is never evidence-bearing: its pinned engine major is
    recorded and a format break costs a rebuild, never evidence, so deletion is
    licensed. The ``canonical`` identity bytes are embedded so a rebuild reconciles
    exactly. Raises :class:`StoreEngineError` on any physical failure.
    """

    def materialize(
        self, key: str, rows: Sequence[Mapping[str, object]], canonical: bytes, /
    ) -> None:  # pragma: no cover
        """(Re)build the view ``key`` from ``rows``, embedding ``canonical``."""
        ...

    def query(self, key: str, /) -> list[dict[str, object]]:  # pragma: no cover
        """Query the materialized view ``key`` (raises on failure or if absent)."""
        ...

    def read_canonical(self, key: str, /) -> bytes | None:  # pragma: no cover
        """The embedded fp1 canonical bytes for the view ``key``, or ``None``."""
        ...

    def drop(self, key: str, /) -> None:  # pragma: no cover
        """Drop the rebuildable view ``key`` (raises on failure)."""
        ...

    def has(self, key: str, /) -> bool:  # pragma: no cover
        """Whether the view ``key`` is materialized (raises on failure)."""
        ...

    def engine_major(self) -> str:  # pragma: no cover
        """The pinned analytics-engine major recorded on every rebuildable view."""
        ...


class MetadataEngine(Protocol):
    """Owned contract for the SQLite transactional-metadata engine (registry records).

    Persists a per-kind versioned record keyed on its fp1 digest, append-only: a
    record is never rewritten in place. Raises :class:`StoreEngineError` on any
    physical failure.
    """

    def put(
        self, digest: str, canonical: bytes, /, *, kind: str, format_version: int
    ) -> None:  # pragma: no cover
        """Insert a record's canonical bytes under ``digest`` (raises on failure)."""
        ...

    def get(self, digest: str, /) -> bytes | None:  # pragma: no cover
        """The canonical bytes stored under ``digest``, or ``None`` (raises on failure)."""
        ...

    def meta(self, digest: str, /) -> Mapping[str, object] | None:  # pragma: no cover
        """The ``kind`` / ``format_version`` metadata for ``digest`` (raises on failure)."""
        ...

    def digests(self) -> list[str]:  # pragma: no cover
        """Every stored record digest (raises on failure)."""
        ...


@runtime_checkable
class OccurrenceSink(Protocol):
    """Optional metadata-engine capability: a per-record display-only occurrence sidecar.

    A registry record is content-addressed on its fp1 identity, which **excludes** every
    occurrence fact — the writer, the per-writer sequence, and created-at (DEC-0110) — so
    those facts have no home in the identity key. An engine that also satisfies this
    protocol keeps them recoverable in a sidecar keyed by the record's fp1 digest, outside
    identity: who wrote a registration and in what order survives a persist/load round trip
    (M5). ``put_occurrence`` is **first-write-wins** (an idempotent re-persist of the same
    identity by a second writer keeps the first occurrence, so a dedup never collides). The
    capability is optional — an engine without it simply carries no occurrence facts — so it
    is checked with :func:`isinstance` at the boundary rather than widening
    :class:`MetadataEngine`.
    """

    def put_occurrence(self, digest: str, occurrence: bytes, /) -> None:  # pragma: no cover
        """Store display-only occurrence bytes under ``digest``, first-write-wins (raises)."""
        ...

    def get_occurrence(self, digest: str, /) -> bytes | None:  # pragma: no cover
        """The occurrence bytes stored under ``digest``, or ``None`` (raises on failure)."""
        ...


class AppendStreamEngine(Protocol):
    """Owned contract for the JSONL append-stream engine (journal + lineage edges).

    One fp1-canonical object per line, LF-terminated, append-with-fsync, rotated
    under a monotonic ordinal, with a locally rebuildable index and exactly one
    holding ``WriterId`` (AC3). :meth:`acquire` is the one-writer gate and returns a
    ``policy rejection`` refusal for a second writer; the I/O methods raise
    :class:`StoreEngineError` on physical failure. This is the seam the append
    boundaries (journal, lineage edges, backup) inject and depend on — a concrete
    engine is opened through an :class:`AppendStreamOpener`, never named at a
    boundary — so the JSONL engine is swappable behind this contract (AC1; M3).
    """

    def acquire(self) -> Result[None]:  # pragma: no cover
        """Take the single-writer hold, or refuse a second distinct writer (AC3)."""
        ...

    def append(self, canonical: bytes, /) -> AppendLocation:  # pragma: no cover
        """Append one LF-terminated line with fsync + rotation (raises on failure)."""
        ...

    def find(self, digest: str, /) -> bytes | None:  # pragma: no cover
        """The stored line bytes for ``digest`` (for reconcile), or ``None``."""
        ...

    def location_of(self, digest: str, /) -> AppendLocation | None:  # pragma: no cover
        """The indexed location for ``digest`` (ordinal, offset, sequence), or ``None``."""
        ...

    def read_all(self) -> list[bytes]:  # pragma: no cover
        """Every line's bytes in stream order — an unlimited reader (raises on failure)."""
        ...

    def rebuild_index(self) -> None:  # pragma: no cover
        """Rebuild the in-memory index by scanning the data files (raises on failure)."""
        ...

    def release(self) -> None:  # pragma: no cover
        """Release the one-writer hold (remove this writer's lock), so a later handoff
        or clean shutdown does not leave the stream owned forever (M6)."""
        ...


class AppendStreamOpener(Protocol):
    """A factory that opens a named append stream behind :class:`AppendStreamEngine`.

    The composition root (the ``EvidenceStore`` facade) builds one opener bound to a
    concrete engine and a rotation size, and injects it into every append boundary,
    so the concrete engine (JSONL) never appears in a boundary signature and the
    engine stays swappable (M3). ``writer_token`` is the holding writer's stable
    identity for the stream (a reader passes a non-writer sentinel).
    """

    def __call__(
        self, stream_dir: Path, writer_token: str, /
    ) -> AppendStreamEngine:  # pragma: no cover
        """Open the stream rooted at ``stream_dir`` for ``writer_token``."""
        ...
