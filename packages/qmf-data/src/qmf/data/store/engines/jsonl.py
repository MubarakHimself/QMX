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
import json
import os
import re
from pathlib import Path

from qmf.core import Ok, Result
from qmf.data.store.engines import (
    AppendLocation,
    AppendStreamEngine,
    AppendStreamOpener,
    StoreEngineError,
)
from qmf.data.store.refusals import policy_rejection

__all__ = [
    "DEFAULT_MAX_SCAN_BYTES",
    "DEFAULT_ROTATION_BYTES",
    "JsonlAppendStream",
    "jsonl_opener",
]

_LOCK_NAME = ".writer"
_ORDINAL_RE = re.compile(r"\A(\d{6})\.jsonl\Z")
_ORDINAL_WIDTH = 6
# Default rotation size; journal trimming/partition thresholds are set only after
# measured volume (DEC-0118), so this is a construction-time argument, not a ratified
# registry constant.
DEFAULT_ROTATION_BYTES = 8 * 1024 * 1024
# A whole rotation file is scanned line-by-line on index rebuild. A file far larger than
# any rotation size is a corrupt or hostile stream (for instance a symlink swapped in for
# an endless/huge file), so a whole-file scan refuses above a generous absolute ceiling
# rather than reading unbounded bytes. Overridable per stream for the regression test.
DEFAULT_MAX_SCAN_BYTES = 1 << 30  # 1 GiB


def _ordinal_filename(ordinal: int) -> str:
    """The zero-padded rotation filename for ``ordinal``."""
    return f"{ordinal:0{_ORDINAL_WIDTH}d}.jsonl"


def _guard_stream_file(root: Path, path: Path, *, must_exist: bool) -> None:
    """Refuse a stream file that is a symlink, out-of-root, or the wrong kind (AC4).

    Every evidence stream file the engine opens is a real file directly inside its stream
    directory: never a symlink, and never a path that resolves outside the stream root, so
    a planted link can neither redirect a read onto a file off the evidence tree nor make a
    write follow it elsewhere. Reads and the in-place torn-tail truncate require an existing
    regular file (``must_exist``); the ``.torn`` sidecar is created on first quarantine, so
    it need only be absent-or-regular. A violation raises a corrupt-store
    :class:`StoreEngineError` (``retryable=False``) the boundary translates to a
    ``storage failure`` refusal, never a silent follow of an attacker-controlled path.
    """
    resolved = Path(os.path.realpath(path))
    root_real = Path(os.path.realpath(root))
    is_link = path.is_symlink()
    wrong_kind = (must_exist or path.exists()) and not path.is_file()
    if is_link or wrong_kind or not resolved.is_relative_to(root_real):
        raise StoreEngineError(
            "refusing to open an evidence stream file that is not a regular in-root file "
            "(a symlink or an out-of-root path could redirect the I/O)",
            engine="jsonl",
            retryable=False,
            detail={"stream": str(root), "path": str(path)},
        )


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
        max_scan_bytes: int = DEFAULT_MAX_SCAN_BYTES,
    ) -> None:
        self._dir = stream_dir
        self._writer_token = writer_token
        self._rotation_bytes = max(1, rotation_bytes)
        self._max_scan_bytes = max(1, max_scan_bytes)
        self._index: dict[str, AppendLocation] = {}
        self._order: list[str] = []
        self._current_ordinal = 0
        self._current_size = 0
        self._held = False

    # --- one-writer hold ----------------------------------------------------

    def acquire(self) -> Result[None]:
        """Take the single-writer hold, refusing a second distinct writer (AC3).

        The hold is taken by an **atomic** ``O_CREAT | O_EXCL`` create of the
        ``.writer`` lock, so two writers racing to acquire a fresh stream can never
        both win: exactly one create succeeds (that writer stamps its token), and
        every other caller lands on the ``FileExistsError`` read-and-compare path.
        A lock naming a *different* writer is a ``policy rejection`` — the second
        writer does not proceed (DEC-0113). The same writer (a restart under a new
        boot/epoch keeps the same ``(machine, role, stream)`` identity) re-acquires
        silently. The index is (re)built from the data files on acquire.
        """
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            lock = self._dir / _LOCK_NAME
            token = self._writer_token.encode("utf-8")
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                # Another caller already holds (or is taking) the lock. Read its
                # stamped token and let only the *same* writer re-acquire; anyone
                # else — including a caller that observes a not-yet-stamped empty
                # lock mid-race — is refused, so the lock is never double-taken.
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
                try:
                    os.write(fd, token)
                finally:
                    os.close(fd)
        except OSError as exc:
            raise StoreEngineError(
                "could not acquire the JSONL stream lock",
                engine="jsonl",
                detail={"stream": str(self._dir), "os_error": str(exc)},
            ) from exc
        self.rebuild_index()
        self._held = True
        return Ok(None)

    def release(self) -> None:
        """Release this writer's one-writer hold, removing its ``.writer`` lock (M6).

        Only a lock that names *this* writer is removed — a reader or backup handle
        (which never acquired) can never unlock another writer's stream. Idempotent:
        releasing an unheld or already-released stream is a no-op. After release the
        stream is free for the same or another writer to acquire, so a clean shutdown
        or a deliberate handoff never leaves a stream owned forever.
        """
        lock = self._dir / _LOCK_NAME
        try:
            if lock.is_file() and lock.read_text(encoding="utf-8") == self._writer_token:
                lock.unlink()
        except OSError as exc:
            raise StoreEngineError(
                "could not release the JSONL stream lock",
                engine="jsonl",
                retryable=False,
                detail={"stream": str(self._dir), "os_error": str(exc)},
            ) from exc
        self._held = False

    # --- append (write) -----------------------------------------------------

    def append(self, canonical: bytes, /) -> AppendLocation:
        """Append one LF-terminated line with fsync, rotating under the ordinal (AC3).

        The one-writer hold is verified first: a handle that does not hold the stream
        (a reader or backup handle, or a writer that never acquired) may not append,
        so a read handle is structurally unable to write (M6, DEC-0113). The rotation
        target is then guarded exactly as every read target is — a symlink, an
        out-of-root path, or a non-regular file is refused rather than written through,
        so the next ordinal cannot be pre-seeded with a link that redirects the append
        (AC4). Raises :class:`StoreEngineError` on either guard and on any physical
        failure — the boundary translates it to a ``storage failure`` refusal and never
        reports success (AC4).
        """
        if not self._held:
            raise StoreEngineError(
                "append attempted on a stream this handle does not hold; only the "
                "acquiring writer may append (M6, DEC-0113)",
                engine="jsonl",
                retryable=False,
                detail={"stream": str(self._dir)},
            )
        line = canonical + b"\n"
        digest = hashlib.sha256(canonical).hexdigest()
        try:
            if self._current_size > 0 and self._current_size + len(line) > self._rotation_bytes:
                self._current_ordinal += 1
                self._current_size = 0
            path = self._dir / _ordinal_filename(self._current_ordinal)
            # The write path carries the same guard as every read path. The exposure it
            # closes is the NEXT rotation ordinal: acquire scans only the files that
            # exist then, so a link planted at an ordinal this stream has not reached
            # yet is never seen at acquire — and an unguarded open-for-append would
            # follow it on rotation. `must_exist=False` because a fresh rotation target
            # is legitimately absent; an existing one must still be a regular in-root
            # file (AC4).
            _guard_stream_file(self._dir, path, must_exist=False)
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
        _guard_stream_file(self._dir, path, must_exist=True)
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

        A torn (no-LF) trailing line at the very tail of the last rotation file — a
        crash mid-write whose LF/fsync never completed — is recovered by standard WAL
        tail handling: the partial tail is quarantined to a ``.torn`` sidecar and the
        data file truncated to the durable committed prefix, so the committed lines stay
        readable and appendable rather than making the whole stream unreadable forever
        (H2). A torn line anywhere else (a non-tail rotation file) is real corruption and
        stays a ``storage failure`` refusal.
        """
        self._index = {}
        self._order = []
        self._current_ordinal = 0
        self._current_size = 0
        try:
            ordinals = self._ordinals_on_disk()
            last = len(ordinals) - 1
            for position, ordinal in enumerate(ordinals):
                self._scan_file(ordinal, is_last_file=position == last)
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

    def _scan_file(self, ordinal: int, *, is_last_file: bool) -> None:
        """Index every LF-terminated line in one ordinal file, in order.

        Each line is validated as one JSON object at index time: a corrupt
        (non-JSON) line is store corruption and surfaces as a ``StoreEngineError``
        the boundary translates to a ``storage failure`` refusal, never a raw
        ``JSONDecodeError`` across the package seam (AC4; H3). A byte-identical
        duplicate line — a line whose digest is already indexed — is skipped rather
        than re-ordered, so a physically duplicated append can never make a read
        return the same record twice under a wrong sequence (L4).

        Only the final chunk of a file can lack an LF terminator. A torn (no-LF) tail is
        tolerable ONLY as the very tail of the stream (``is_last_file``): it is
        quarantined and the committed prefix kept (H2). A torn line in any earlier
        rotation file is real corruption and is a ``storage failure`` refusal.
        """
        path = self._dir / _ordinal_filename(ordinal)
        _guard_stream_file(self._dir, path, must_exist=True)
        size = path.stat().st_size
        if size > self._max_scan_bytes:
            raise StoreEngineError(
                "the JSONL rotation file exceeds the maximum scannable size; refusing to "
                "read it whole (a corrupt or hostile stream)",
                engine="jsonl",
                retryable=False,
                detail={
                    "stream": str(self._dir),
                    "ordinal": ordinal,
                    "size": size,
                    "cap": self._max_scan_bytes,
                },
            )
        offset = 0
        torn_tail: bytes | None = None
        with path.open("rb") as handle:
            for raw in handle:
                if not raw.endswith(b"\n"):
                    if is_last_file:
                        torn_tail = raw
                        break
                    raise StoreEngineError(
                        "the JSONL stream has a partial line without an LF terminator "
                        "before the stream tail (corruption in an earlier rotation file)",
                        engine="jsonl",
                        retryable=False,
                        detail={"stream": str(self._dir), "ordinal": ordinal},
                    )
                length = len(raw)
                payload = raw[:-1]
                try:
                    json.loads(payload)
                except ValueError as exc:
                    raise StoreEngineError(
                        "the JSONL stream has a corrupt (non-JSON) line",
                        engine="jsonl",
                        retryable=False,
                        detail={"stream": str(self._dir), "ordinal": ordinal},
                    ) from exc
                digest = hashlib.sha256(payload).hexdigest()
                if digest not in self._index:
                    self._index[digest] = AppendLocation(
                        ordinal=ordinal,
                        byte_offset=offset,
                        length=length,
                        sequence=len(self._order),
                    )
                    self._order.append(digest)
                offset += length
        if torn_tail is not None:
            self._quarantine_torn_tail(ordinal, committed_prefix_len=offset, torn=torn_tail)

    def _quarantine_torn_tail(
        self, ordinal: int, *, committed_prefix_len: int, torn: bytes
    ) -> None:
        """Quarantine a torn (no-LF) trailing line, keeping the committed prefix (H2).

        A crash mid-write can leave the final line without its LF terminator (the fsync
        had not completed). Standard WAL tail handling: the durable committed prefix —
        every LF-terminated line before it — stays readable and appendable, and the
        partial tail is preserved to a ``<ordinal>.jsonl.torn`` sidecar for evidence
        rather than making the whole stream unreadable forever. The data file is then
        truncated to the committed prefix so the next append lands cleanly after it and a
        later re-scan never re-reads the partial bytes. The read handle is already closed
        before this runs, so the truncate never contends with the scan on Windows.
        """
        data_name = _ordinal_filename(ordinal)
        sidecar = self._dir / f"{data_name}.torn"
        data_path = self._dir / data_name
        # The sidecar is created on first quarantine (absent-or-regular); the data file
        # already exists and is truncated in place. Both must stay regular, in-root, and
        # never a symlink, so neither write is redirected off the evidence tree (AC4).
        _guard_stream_file(self._dir, sidecar, must_exist=False)
        _guard_stream_file(self._dir, data_path, must_exist=True)
        try:
            with sidecar.open("ab") as handle:
                handle.write(torn)
                handle.flush()
                os.fsync(handle.fileno())
            with data_path.open("r+b") as handle:
                handle.truncate(committed_prefix_len)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise StoreEngineError(
                "could not quarantine a torn trailing JSONL line",
                engine="jsonl",
                detail={"stream": str(self._dir), "ordinal": ordinal, "os_error": str(exc)},
            ) from exc

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


def jsonl_opener(rotation_bytes: int = DEFAULT_ROTATION_BYTES) -> AppendStreamOpener:
    """An :class:`AppendStreamOpener` bound to the JSONL engine and one rotation size.

    The composition root builds this once and injects it into every append boundary
    (journal, lineage edges, backup), so the concrete :class:`JsonlAppendStream`
    never appears in a boundary signature and the engine stays swappable (M3). Each
    call opens (or re-opens) the stream rooted at ``stream_dir`` for ``writer_token``.
    """

    def _open(stream_dir: Path, writer_token: str, /) -> AppendStreamEngine:
        return JsonlAppendStream(
            stream_dir, writer_token=writer_token, rotation_bytes=rotation_bytes
        )

    return _open
