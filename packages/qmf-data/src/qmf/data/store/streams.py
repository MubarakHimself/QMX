"""Shared helpers for the JSONL-backed append boundaries (journal + lineage edges).

Both the CT-13 journal and the CT-09 lineage-edge tail persist as one-writer JSONL
append streams, so they share three concerns pinned here: deriving a stream's holding
**hold token** from a writer's identity plus the stream it is acquiring (a restart under
a new boot/epoch keeps the same token so it re-acquires, DEC-0106), validating a
caller-supplied **stream segment** so a stream name can never traverse out of its room
directory, and **canonicalizing** a stream name so one physical directory always maps to
one cache entry regardless of the caller's letter case. The concrete append engine is
never named here — it is injected as an :class:`~qmf.data.store.engines.AppendStreamOpener`
so the JSONL engine stays swappable (M3). Stdlib + qmf-core only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from qmf.core import Ok, Result, WriterId, is_refusal
from qmf.data.store.engines import AppendStreamEngine, AppendStreamOpener, StoreEngineError
from qmf.data.store.refusals import invalid_input, policy_rejection, translate_engine_failure

__all__ = ["HeldStreams", "canonical_stream_key", "hold_token", "safe_segment", "writer_token"]

# A stream segment is a plain token; it becomes a directory name, so no separators,
# no traversal, no absolute roots — a corrupt or hostile name can never escape a room.
_SEGMENT_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def hold_token(machine: str, role: str, stream: str) -> str:
    """The injective one-writer hold token for ``(machine, role, stream)``.

    Encoded as a JSON array with control characters escaped, so no part can smuggle a
    separator into another and two distinct triples never collapse to one token — the
    unescaped ``\\x1f`` join this replaces let ``("m", "role\\x1fA", "s")`` and
    ``("m", "role", "A\\x1fs")`` alias (M1). The boot/epoch id is deliberately excluded:
    a restart is the same writer and must re-acquire its stream, while a different
    ``(machine, role, stream)`` is a distinct writer the second-writer gate refuses
    (DEC-0113, DEC-0106).
    """
    return json.dumps([machine, role, stream], ensure_ascii=True, separators=(",", ":"))


def writer_token(writer: WriterId) -> str:
    """The hold token derived purely from a :class:`WriterId`'s own identity.

    This is ``(machine, role, stream)`` from the writer itself; the stream a writer
    actually holds is set by :meth:`HeldStreams.acquire` from the acquired stream name,
    which may differ (M2). Kept for callers that want the writer's own token.
    """
    return hold_token(writer.machine, writer.role, writer.stream)


def canonical_stream_key(name: str) -> str:
    """The case-folded canonical key for a stream name (H2).

    A stream name is treated case-insensitively so one physical directory always maps
    to exactly one in-memory handle and one on-disk lock, regardless of the caller's
    letter case — on a case-insensitive filesystem (Windows is a tier-1 target) two
    casings name the same directory, and folding the key makes that true on every
    filesystem, so ``"Orders"`` and ``"orders"`` can never become two live handles with
    independent indexes over one journal.
    """
    return name.casefold()


def safe_segment(name: object, *, field: str = "stream") -> Result[str]:
    """Validate a caller-supplied stream/segment name, or refuse (invalid input).

    The name becomes a directory under a room, so it must be a plain token — letters,
    digits, dot, dash, underscore, 1–128 chars, not starting with a separator — with no
    path separators and no traversal. A name that is not a string or fails the shape is
    an ``invalid input`` refusal, never silently coerced.
    """
    if not isinstance(name, str) or _SEGMENT_RE.match(name) is None:
        return invalid_input(
            field,
            "a stream segment is a 1-128 char token of letters, digits, '.', '-', '_' "
            "(no path separators or traversal)",
            given=repr(name),
        )
    return Ok(name)


class HeldStreams:
    """One-writer JSONL streams under a base directory, shared by the journal and the
    registry lineage tail.

    Tracks which hold token owns each named stream and refuses a second distinct writer
    (DEC-0113). :meth:`acquire` returns the held stream for a name (creating and
    on-disk-locking it on first use); :meth:`reader` opens an unlocked reader over an
    existing stream (unlimited readers), or ``None`` when the stream does not exist yet.
    Stream names are canonicalized case-insensitively so one directory is one handle (H2).
    The concrete engine is injected as an ``open_stream`` opener, so JSONL is swappable (M3).
    """

    def __init__(self, base_dir: Path, *, open_stream: AppendStreamOpener) -> None:
        self._base = base_dir
        self._open = open_stream
        self._held: dict[str, tuple[str, AppendStreamEngine]] = {}

    def acquire(self, name: str, writer: WriterId) -> Result[AppendStreamEngine]:
        """The held stream for ``name`` under ``writer``, refusing a second writer.

        The hold token names the acquired stream (its canonical key), not the writer's
        own ``stream`` field, so one writer cannot silently own many streams under one
        token (M2). May return a ``policy rejection`` (a distinct writer already holds
        the name, in this process or via the on-disk lock); an engine failure while
        taking the on-disk lock is translated to a ``storage failure`` refusal.
        """
        key = canonical_stream_key(name)
        token = hold_token(writer.machine, writer.role, key)
        existing = self._held.get(key)
        if existing is not None:
            held_token, stream = existing
            if held_token != token:
                return policy_rejection(
                    "writer",
                    "a second writer may not hold a stream already held by another "
                    "WriterId in this store; the second write does not proceed (DEC-0113)",
                    stream=key,
                    holder=held_token,
                    attempted=token,
                )
            return Ok(stream)
        stream = self._open(self._base / key, token)
        try:
            acquired = stream.acquire()
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if is_refusal(acquired):
            return acquired
        self._held[key] = (token, stream)
        return Ok(stream)

    def reader(self, name: str) -> AppendStreamEngine | None:
        """An unlocked reader over an existing stream, or ``None`` if none exists yet.

        The returned stream's index is not yet built — the caller calls
        ``rebuild_index`` / ``read_all`` inside its own engine-failure guard.
        """
        key = canonical_stream_key(name)
        stream_dir = self._base / key
        if not stream_dir.is_dir():
            return None
        return self._open(stream_dir, "<reader>")

    def release_all(self) -> None:
        """Release every held stream's one-writer lock and forget it (M6).

        Called on a clean shutdown or a deliberate handoff so no stream is left owned
        forever; releasing is idempotent, and only this store's own locks are removed.
        """
        for _token, stream in self._held.values():
            stream.release()
        self._held.clear()

    def stream_names(self) -> tuple[str, ...]:
        """Every stream name present under the base directory, canonical and sorted.

        Enumerates the on-disk stream directories (each created on first :meth:`acquire`)
        unioned with any held only in memory, so a caller enforcing a room-wide invariant
        can scan across all streams rather than a single named one. A base directory that
        does not exist yet (no stream ever written) yields an empty tuple. Names are the
        case-folded canonical keys, ready to pass straight back to :meth:`reader`.
        """
        names: set[str] = set(self._held)
        if self._base.is_dir():
            names.update(entry.name for entry in self._base.iterdir() if entry.is_dir())
        return tuple(sorted(names))
