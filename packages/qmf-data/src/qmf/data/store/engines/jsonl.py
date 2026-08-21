"""JSONL append-stream engine — journal and lineage-edge streams (AC3; DEC-0114).

The concrete :class:`~qmf.data.store.engines.AppendStreamEngine`. One stream is one
directory of rotation files; each record is **one fp1-canonical object per line,
LF-terminated**, appended with an fsync so a committed line is durable. When a file
would exceed the rotation size it rolls to the next file under a **monotonic
ordinal** (``000000.jsonl``, ``000001.jsonl``, …), so no line is ever split. The
in-memory index (digest → location, and stream order) is a **locally rebuildable
index** (AR-31): it is reconstructed by scanning the data files, never the authority.

Exactly one ``WriterId`` holds a stream, with unlimited readers (DEC-0113). The hold
is a ``.writer`` lock file naming the holding writer's ``(machine, role, stream)``
identity — a restart under a new boot/epoch is the *same* writer and re-acquires,
while a **second distinct writer does not proceed** (a ``policy rejection``). Physical
failures raise :class:`~qmf.data.store.engines.StoreEngineError`; the boundary
translates them (AC4).

Stdlib only (no engine library needed — JSONL is plain files); the digest keyed here
is ``sha256(canonical).hexdigest()``, identical to the fp1 digest hashed over the
same canonical bytes, so the identity guard and this index agree.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from qmf.core import Ok, Result
from qmf.data.store.engines import AppendLocation, StoreEngineError
from qmf.data.store.refusals import policy_rejection

__all__ = ["JsonlAppendStream"]

_LOCK_NAME = ".writer"
_ORDINAL_RE = re.compile(r"\A(\d{6})\.jsonl\Z")
_ORDINAL_WIDTH = 6
# Default rotation size; journal trimming/partition thresholds are set only after
# measured volume (DEC-0118), so this is a construction-time argument, not a ratified
# registry constant.
DEFAULT_ROTATION_BYTES = 8 * 1024 * 1024


def _ordinal_filename(ordinal: int) -> str:
    """The zero-padded rotation filename for ``ordinal``."""
    return f"{ordinal:0{_ORDINAL_WIDTH}d}.jsonl"


class JsonlAppendStream:
    """A single append-only JSONL stream held by one writer (AC3).

    Construct it bound to a ``stream_dir`` and a ``writer_token`` (the holding
    writer's stable ``(machine, role, stream)`` identity), then :meth:`acquire` the
    one-writer hold before appending. Readers may construct and :meth:`read_all`
    without acquiring.
    """

    def __init__(
        self,
        stream_dir: Path,
        *,
        writer_token: str,
        rotation_bytes: int = DEFAULT_ROTATION_BYTES,
    ) -> None:
        self._dir = stream_dir
        self._writer_token = writer_token
        self._rotation_bytes = max(1, rotation_bytes)
        self._index: dict[str, AppendLocation] = {}
        self._order: list[str] = []
        self._current_ordinal = 0
        self._current_size = 0
        self._held = False

    # --- one-writer hold ----------------------------------------------------

    def acquire(self) -> Result[None]:
        """Take the single-writer hold, refusing a second distinct writer (AC3).

        A ``.writer`` lock naming a *different* writer is a ``policy rejection`` — the
        second writer does not proceed (DEC-0113). The same writer (a restart under a
        new boot/epoch keeps the same ``(machine, role, stream)`` identity) re-acquires
        silently. The index is (re)built from the data files on acquire.
        """
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            lock = self._dir / _LOCK_NAME
            if lock.exists():
                holder = lock.read_text(encoding="utf-8")
                if holder != self._writer_token:
                    return policy_rejection(
                        "writer",
                        "a second writer may not hold a stream already owned by another "
                        "WriterId; the second write does not proceed (DEC-0113)",
                        stream=str(self._dir),
                        holder=holder,
                        attempted=self._writer_token,
                    )
            else:
                lock.write_text(self._writer_token, encoding="utf-8")
        except OSError as exc:
            raise StoreEngineError(
                "could not acquire the JSONL stream lock",
                engine="jsonl",
                detail={"stream": str(self._dir), "os_error": str(exc)},
            ) from exc
        self.rebuild_index()
        self._held = True
        return Ok(None)

    # --- append (write) -----------------------------------------------------

    def append(self, canonical: bytes, /) -> AppendLocation:
        """Append one LF-terminated line with fsync, rotating under the ordinal (AC3).

        Raises :class:`StoreEngineError` on any physical failure — the boundary
        translates it to a ``storage failure`` refusal and never reports success (AC4).
        """
        line = canonical + b"\n"
        digest = hashlib.sha256(canonical).hexdigest()
        try:
            if self._current_size > 0 and self._current_size + len(line) > self._rotation_bytes:
                self._current_ordinal += 1
                self._current_size = 0
            path = self._dir / _ordinal_filename(self._current_ordinal)
            offset = self._current_size
            with path.open("ab") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise StoreEngineError(
                "could not durably append to the JSONL stream",
                engine="jsonl",
                detail={"stream": str(self._dir), "os_error": str(exc)},
            ) from exc
        location = AppendLocation(
            ordinal=self._current_ordinal,
            byte_offset=offset,
            length=len(line),
            sequence=len(self._order),
        )
        self._current_size += len(line)
        self._index[digest] = location
        self._order.append(digest)
        return location

    # --- reads (unlimited readers) ------------------------------------------

    def find(self, digest: str, /) -> bytes | None:
        """The stored canonical bytes for ``digest`` (LF stripped), or ``None``.

        Used by the identity guard to reconcile a re-write. A short read — the file
        was truncated under the recorded length — raises :class:`StoreEngineError`
        (a corrupt/truncated store, AC4), never a silent wrong answer.
        """
        location = self._index.get(digest)
        if location is None:
            return None
        path = self._dir / _ordinal_filename(location.ordinal)
        try:
            with path.open("rb") as handle:
                handle.seek(location.byte_offset)
                raw = handle.read(location.length)
        except OSError as exc:
            raise StoreEngineError(
                "could not read the JSONL stream",
                engine="jsonl",
                detail={"stream": str(self._dir), "digest": digest, "os_error": str(exc)},
            ) from exc
        if len(raw) != location.length:
            raise StoreEngineError(
                "the JSONL stream is truncated: fewer bytes than the index records",
                engine="jsonl",
                retryable=False,
                detail={"stream": str(self._dir), "digest": digest},
            )
        return raw[:-1] if raw.endswith(b"\n") else raw

    def location_of(self, digest: str, /) -> AppendLocation | None:
        """The indexed location for ``digest`` (ordinal, offset, sequence), or ``None``.

        Reads only the in-memory index — no file I/O — so a boundary can report the
        per-writer sequence of an idempotently re-presented record without a re-read.
        """
        return self._index.get(digest)

    def read_all(self) -> list[bytes]:
        """Every line's canonical bytes in stream order — an unlimited reader."""
        return [self._require(digest) for digest in self._order]

    def _require(self, digest: str) -> bytes:
        """Read a digest that the index says exists; a miss is a corrupt store."""
        found = self.find(digest)
        if found is None:  # pragma: no cover - order and index are populated together
            raise StoreEngineError(
                "the JSONL index references a line it cannot locate",
                engine="jsonl",
                retryable=False,
                detail={"stream": str(self._dir), "digest": digest},
            )
        return found

    # --- rebuildable index --------------------------------------------------

    def rebuild_index(self) -> None:
        """Rebuild the in-memory index by scanning the data files (AR-31).

        The index is never the authority — it is reconstructed from the LF-delimited
        lines across the ordinal files in order, so a lost index costs a rescan, never
        evidence. Sets the current rotation ordinal and size for the next append.
        """
        self._index = {}
        self._order = []
        self._current_ordinal = 0
        self._current_size = 0
        try:
            ordinals = self._ordinals_on_disk()
            for ordinal in ordinals:
                self._scan_file(ordinal)
            if ordinals:
                self._current_ordinal = ordinals[-1]
                self._current_size = (
                    (self._dir / _ordinal_filename(self._current_ordinal)).stat().st_size
                )
        except OSError as exc:
            raise StoreEngineError(
                "could not rebuild the JSONL index",
                engine="jsonl",
                detail={"stream": str(self._dir), "os_error": str(exc)},
            ) from exc

    def _ordinals_on_disk(self) -> list[int]:
        """The rotation ordinals present in the stream directory, ascending."""
        ordinals: list[int] = []
        for child in self._dir.iterdir():
            match = _ORDINAL_RE.match(child.name)
            if match is not None and child.is_file():
                ordinals.append(int(match.group(1)))
        return sorted(ordinals)

    def _scan_file(self, ordinal: int) -> None:
        """Index every LF-terminated line in one ordinal file, in order."""
        path = self._dir / _ordinal_filename(ordinal)
        offset = 0
        with path.open("rb") as handle:
            for raw in handle:
                length = len(raw)
                if not raw.endswith(b"\n"):
                    raise StoreEngineError(
                        "the JSONL stream has a partial trailing line (no LF terminator)",
                        engine="jsonl",
                        retryable=False,
                        detail={"stream": str(self._dir), "ordinal": ordinal},
                    )
                digest = hashlib.sha256(raw[:-1]).hexdigest()
                self._index[digest] = AppendLocation(
                    ordinal=ordinal,
                    byte_offset=offset,
                    length=length,
                    sequence=len(self._order),
                )
                self._order.append(digest)
                offset += length

    # --- introspection (tests / diagnostics) --------------------------------

    @property
    def held(self) -> bool:
        """Whether this stream currently holds the one-writer lock."""
        return self._held

    @property
    def record_count(self) -> int:
        """The number of indexed records in the stream."""
        return len(self._order)

    @property
    def current_ordinal(self) -> int:
        """The current rotation ordinal (the file the next append targets)."""
        return self._current_ordinal
