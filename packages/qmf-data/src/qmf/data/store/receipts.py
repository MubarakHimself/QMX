"""The receipt every store boundary returns for an accepted write.

A :class:`StoreReceipt` records what landed and where: the fp1 fingerprint that keys
it, the world and room-role it occupies, the engine that physically wrote it, whether
that room-role is evidence-bearing, the contract format version stamped into the
artifact, and — for a rebuildable analytics view — the pinned engine major a rebuild
must honor. It is the store-layer outcome of a write, never the artifact's business
meaning. Stdlib + qmf-core only.
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core import Fingerprint, World, WriteOutcome
from qmf.data.store.rooms import RoomRole

__all__ = ["StoreReceipt"]

# The CT-11/CT-09/CT-13/CT-26 boundaries all mint format version 1 (DEC-0103).
CONTRACT_FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class StoreReceipt:
    """The store-layer outcome of an accepted write (AC1, AC2).

    ``outcome`` is ``stored`` (a first write of this fingerprint) or ``idempotent``
    (a byte-identical re-write accepted silently). ``fingerprint`` is the artifact's
    fp1 identity. ``room_role`` and ``world`` name the room instance it landed in;
    ``engine`` names the one engine that physically wrote it. ``is_evidence_bearing``
    is true only for the immutable raw archive and journal; ``retained_forever`` is
    true for evidence rooms (kept regardless of citation) and defaults false for a
    rebuildable view (deletion licensed until a result label cites it). ``engine_major``
    is set only for a rebuildable analytics view; ``sequence`` only for an append
    stream (the per-writer position).
    """

    outcome: WriteOutcome
    fingerprint: Fingerprint
    world: World
    room_role: RoomRole
    engine: str
    is_evidence_bearing: bool
    retained_forever: bool
    format_version: int = CONTRACT_FORMAT_VERSION
    engine_major: str | None = None
    sequence: int | None = None
