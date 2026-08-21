"""CT-13 — the durable journal boundary (AC1, AC3, AC4, AC5).

Persists journal evidence as **N append-only streams**, one per producing component,
each a one-writer JSONL stream for one world. A record is one fp1-canonical object per
line, LF-terminated, appended with fsync and rotated under a monotonic ordinal (AC3).
Exactly one ``WriterId`` holds a named stream; a second, distinct writer reaching for
it is a ``policy rejection`` and does not proceed (DEC-0113). A byte-identical
re-append is idempotent (no duplicate line); a cross-world read is a ``policy
rejection`` (AC5); any engine failure is translated to a ``storage failure`` refusal
at this boundary (AC4).

This boundary owns only physical persistence and the one-writer discipline — the
seven journal event *types*, the decision ``outcome`` field, and the entity-journal
projections are qmf-data policy (Stories 3.5/3.6), not the store seam. JSONL is the
ratified append engine (AC1); the stream instances are constructed here rooted at the
world's journal room. Stdlib + qmf-core.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from qmf.core import Ok, Result, World, WriterId, is_refusal
from qmf.data.store.engines import StoreEngineError
from qmf.data.store.engines.jsonl import DEFAULT_ROTATION_BYTES
from qmf.data.store.identity import admit
from qmf.data.store.receipts import StoreReceipt
from qmf.data.store.refusals import translate_engine_failure
from qmf.data.store.rooms import RoomRole, namespace_block, require_same_world
from qmf.data.store.streams import HeldStreams, safe_segment

__all__ = ["JournalStore"]


class JournalStore:
    """The CT-13 journal for one world — N one-writer JSONL streams (AC1, AC3)."""

    def __init__(
        self,
        world: World,
        *,
        journal_dir: Path,
        rotation_bytes: int = DEFAULT_ROTATION_BYTES,
    ) -> None:
        self._world = world
        self._streams = HeldStreams(journal_dir, rotation_bytes=rotation_bytes)

    @property
    def world(self) -> World:
        """The world whose journal room this boundary writes and reads."""
        return self._world

    # --- append (write) -----------------------------------------------------

    def append(
        self,
        stream_name: object,
        writer: WriterId,
        event: Mapping[str, object],
        *,
        presented_fingerprint: object | None = None,
    ) -> Result[StoreReceipt]:
        """Append ``event`` to the named per-writer stream (AC3).

        The first ``WriterId`` to acquire ``stream_name`` holds it; a second distinct
        writer is a ``policy rejection`` and does not proceed. A ``world = simulated``
        append is refused before any bytes are touched, and any engine failure is a
        ``storage failure`` refusal — no success is reported on failure (AC4, AC5).
        """
        blocked = namespace_block(self._world)
        if blocked is not None:
            return blocked
        name = safe_segment(stream_name)
        if is_refusal(name):
            return name
        acquired = self._streams.acquire(name.value, writer)
        if is_refusal(acquired):
            return acquired
        stream = acquired.value
        content = dict(event)
        try:
            admission = admit(
                content,
                existing_bytes=stream.find,
                persist=lambda _fp, canonical: _discard(stream.append(canonical)),
                presented_fingerprint=presented_fingerprint,
            )
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        if is_refusal(admission):
            return admission
        admitted = admission.value
        location = stream.location_of(admitted.fingerprint.digest)
        return Ok(
            StoreReceipt(
                outcome=admitted.outcome,
                fingerprint=admitted.fingerprint,
                world=self._world,
                room_role=RoomRole.JOURNAL,
                engine="jsonl",
                is_evidence_bearing=True,
                retained_forever=True,
                sequence=location.sequence if location is not None else None,
            )
        )

    # --- read (unlimited readers) -------------------------------------------

    def read_stream(
        self, stream_name: object, *, for_world: object | None = None
    ) -> Result[list[dict[str, object]]]:
        """Read every event in a named stream in order; a cross-world read refuses (AC5)."""
        gate = require_same_world(self._world, for_world)
        if is_refusal(gate):
            return gate
        name = safe_segment(stream_name)
        if is_refusal(name):
            return name
        reader = self._streams.reader(name.value)
        if reader is None:
            return Ok([])
        try:
            reader.rebuild_index()
            lines = reader.read_all()
        except StoreEngineError as exc:
            return translate_engine_failure(exc)
        return Ok([_load(line) for line in lines])


def _discard(_location: object) -> None:
    """Swallow the append location the persist callback does not surface."""


def _load(line: bytes) -> dict[str, object]:
    """Parse one canonical JSONL line back to a dict (an unlimited-reader decode)."""
    decoded: object = json.loads(line)
    if isinstance(decoded, dict):
        return cast("dict[str, object]", decoded)
    return {"_value": decoded}
