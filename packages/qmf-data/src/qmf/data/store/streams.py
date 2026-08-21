"""Shared helpers for the JSONL-backed append boundaries (journal + lineage edges).

Both the CT-13 journal and the CT-09 lineage-edge tail persist as one-writer JSONL
append streams, so they share two concerns pinned here: deriving a stream's holding
**writer token** from a :class:`~qmf.core.WriterId` (identity is ``(machine, role,
stream)``; a restart under a new boot/epoch keeps the same token so it re-acquires,
DEC-0106), and validating a caller-supplied **stream segment** so a stream name can
never traverse out of its room directory. Stdlib + qmf-core only.
"""

from __future__ import annotations

import re
from pathlib import Path

from qmf.core import Ok, Result, WriterId, is_refusal
from qmf.data.store.engines import StoreEngineError
from qmf.data.store.engines.jsonl import DEFAULT_ROTATION_BYTES, JsonlAppendStream
from qmf.data.store.refusals import invalid_input, policy_rejection, translate_engine_failure

__all__ = ["HeldStreams", "safe_segment", "writer_token"]

# A stream segment is a plain token; it becomes a directory name, so no separators,
# no traversal, no absolute roots — a corrupt or hostile name can never escape a room.
_SEGMENT_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_UNIT_SEP = "\x1f"


def writer_token(writer: WriterId) -> str:
    """The one-writer hold token for ``writer`` — its ``(machine, role, stream)``.

    The boot/epoch id is deliberately excluded: a restart is the same writer and must
    re-acquire its stream, while a different ``(machine, role, stream)`` is a distinct
    writer that the second-writer gate refuses (DEC-0113, DEC-0106).
    """
    return _UNIT_SEP.join((writer.machine, writer.role, writer.stream))


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

    Tracks which ``WriterId`` holds each named stream and refuses a second distinct
    writer (DEC-0113). :meth:`acquire` returns the held stream for a name (creating and
    on-disk-locking it on first use); :meth:`reader` opens an unlocked reader over an
    existing stream (unlimited readers), or ``None`` when the stream does not exist yet.
    """

    def __init__(self, base_dir: Path, *, rotation_bytes: int = DEFAULT_ROTATION_BYTES) -> None:
        self._base = base_dir
        self._rotation_bytes = rotation_bytes
        self._held: dict[str, tuple[str, JsonlAppendStream]] = {}

    def acquire(self, name: str, writer: WriterId) -> Result[JsonlAppendStream]:
        """The held stream for ``name`` under ``writer``, refusing a second writer.

        May return a ``policy rejection`` (a distinct writer already holds the name,
        in this process or via the on-disk lock) or raise nothing — an engine failure
        while taking the on-disk lock is translated to a ``storage failure`` refusal.
        """
        token = writer_token(writer)
        existing = self._held.get(name)
        if existing is not None:
            held_token, stream = existing
            if held_token != token:
                return policy_rejection(
                    "writer",
                    "a second writer may not hold a stream already held by another "
                    "WriterId in this store; the second write does not proceed (DEC-0113)",
                    stream=name,
                    holder=held_token,
                    attempted=token,
                )
            return Ok(stream)
        stream = JsonlAppendStream(
            self._base / name, writer_token=token, rotation_bytes=self._rotation_bytes
        )
        try:
            acquired = stream.acquire()
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if is_refusal(acquired):
            return acquired
        self._held[name] = (token, stream)
        return Ok(stream)

    def reader(self, name: str) -> JsonlAppendStream | None:
        """An unlocked reader over an existing stream, or ``None`` if none exists yet.

        The returned stream's index is not yet built — the caller calls
        ``rebuild_index`` / ``read_all`` inside its own engine-failure guard.
        """
        stream_dir = self._base / name
        if not stream_dir.is_dir():
            return None
        return JsonlAppendStream(stream_dir, writer_token="<reader>")
