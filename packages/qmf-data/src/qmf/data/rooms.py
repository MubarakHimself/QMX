"""The seven room-roles per world — the data-policy owner (AC1, AC2, AC4, AC5).

`COMP-QMF-DATA` owns the seven room-roles — ingest door, immutable raw archive,
processed, journal, split-governed research door, backup, and the registry room — each
instantiated **independently per world** (DEC-0117, AD-19, AR-33). :class:`WorldRooms`
is that ownership made concrete: one instance binds the seven roles for exactly one
world over the Story 3.1 store seam, and it is the data-policy surface every later
room-scoped operation reaches the world's rooms through.

The four physical boundaries (CT-11 append-store, CT-13 journal, CT-09 registry room,
CT-26 backup input) are wired by the store per world and surfaced here read-only. On top
of them this facade adds the three data-policy guarantees Story 3.3 pins:

* **AC1/AC4** — a world is instantiated with :meth:`WorldRooms.for_world`; ``live`` and
  ``replay`` each get their own independent set of seven rooms, and ``world = simulated``
  is reserved-unusable, so requesting it is a ``policy rejection``. A read declaring a
  different world than the room's is a ``policy rejection`` — world isolation is storage
  separation, delivered by the store seam and never overridden here.
* **AC2** — :meth:`materialize_view` writes a rebuildable analytics view that records its
  pinned analytics-engine major (from the engine) and the original calendar identity and
  tzdata version (from the caller's :class:`RebuildPins`), so an engine format break costs
  a rebuild against the exact calendar, never evidence. A rebuildable view is never
  evidence-bearing.
* **AC5** — :meth:`place_series` archives time-series evidence *within* its
  ``(source, instrument, time-window)`` partition (the partition rides into the artifact's
  fp1 identity), and :meth:`resolve_series` reads it back resolved to exactly that
  partition. Series resolution runs only over the evidence-bearing raw archive; a
  rebuildable view is never treated as series evidence.

Retention (AC3) is a separate concern — see :mod:`qmf.data.retention`.

Stdlib + qmf-core + the qmf-data store seam.

Role catalog, store boundaries, and series policy live in sibling collaborator
modules; this module keeps the public facade and re-exports :class:`RebuildPins`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from qmf.core import Result, World
from qmf.data.partitions import ResolvedSeries, SeriesPlacement
from qmf.data.rooms_bind import bind_world_rooms, resolve_world_rooms
from qmf.data.rooms_pins import RebuildPins
from qmf.data.store import (
    AppendStore,
    BackupInput,
    EvidenceStore,
    JournalStore,
    ReadSeal,
    RegistryRoom,
    RoomRole,
    StoreReceipt,
    WorldStore,
)

__all__ = ["RebuildPins", "WorldRooms"]


class WorldRooms:
    """The seven room-roles for exactly one world, over the Story 3.1 store seam (AC1).

    Constructed from a resolved :class:`~qmf.data.store.WorldStore`; use
    :meth:`for_world` to obtain one from an :class:`~qmf.data.store.EvidenceStore` (which
    refuses ``world = simulated``). The four store boundaries are surfaced read-only, and
    the data-policy operations (rebuildable views, series placement/resolution) sit on top
    of them.
    """

    def __init__(self, world_store: WorldStore, *, seal: ReadSeal | None = None) -> None:
        self._collaborators = bind_world_rooms(world_store, seal)

    @classmethod
    def for_world(
        cls, store: EvidenceStore, world: object, *, seal: ReadSeal | None = None
    ) -> Result[WorldRooms]:
        """The :class:`WorldRooms` for ``world``, or a refusal (AC1, AC4).

        ``live`` and ``replay`` each resolve to their own independent set of seven rooms;
        ``world = simulated`` is reserved-unusable and its store has no governed namespace,
        so requesting it is a ``policy rejection`` — no simulated evidence is ever
        instantiated (DEC-0110, DEC-0117). An optional no-peek ``seal`` is consulted at the
        split-governed research door on :meth:`resolve_series` (AC4; DEC-0119).
        """
        return resolve_world_rooms(cls, store, world, seal=seal)

    @property
    def world(self) -> World:
        """The one world whose seven rooms this facade owns."""
        return self._collaborators.boundaries.world

    @property
    def roles(self) -> tuple[RoomRole, ...]:
        """The seven room-roles this world instantiates, in CT-11's declared order (AC1)."""
        return self._collaborators.roles.roles

    @property
    def evidence_bearing_roles(self) -> frozenset[RoomRole]:
        """The two evidence-bearing roles — immutable raw archive and journal (AC2, AC5)."""
        return self._collaborators.roles.evidence_bearing_roles

    def is_evidence_bearing(self, role: RoomRole) -> bool:
        """Whether ``role`` is evidence-bearing — true only for raw archive and journal.

        Processed data and analytics views are rebuildable, so they are never
        evidence-bearing; an engine format break over them costs a rebuild, not evidence
        (AC2, AC5; DEC-0117).
        """
        return self._collaborators.roles.is_evidence_bearing(role)

    @property
    def append_store(self) -> AppendStore:
        """The CT-11 append-store — immutable raw archive + processed views (this world)."""
        return self._collaborators.boundaries.append_store

    @property
    def journal(self) -> JournalStore:
        """The CT-13 journal store for this world's journal room."""
        return self._collaborators.boundaries.journal

    @property
    def registry_room(self) -> RegistryRoom:
        """The CT-09 registry room — records + lineage edges for this world."""
        return self._collaborators.boundaries.registry_room

    @property
    def backup_input(self) -> BackupInput:
        """The CT-26 store-to-backup input for this world's rooms."""
        return self._collaborators.boundaries.backup_input

    def materialize_view(
        self,
        rows: Sequence[Mapping[str, object]],
        *,
        pins: object,
        presented_fingerprint: object | None = None,
    ) -> Result[StoreReceipt]:
        """Materialize a rebuildable analytics view recording its rebuild pins (AC2).

        The view lands in the processed room, is never evidence-bearing, and its receipt
        records the pinned analytics-engine major (from the engine) plus the calendar
        identity and tzdata version from ``pins`` — so an engine format break replays a
        rebuild against the exact calendar and costs a rebuild, never evidence (DEC-0117,
        DEC-0103). ``pins`` is required: a governed rebuildable view must always record
        what a rebuild must honor, so a value that is not :class:`RebuildPins` is an
        ``invalid input`` refusal.
        """
        return self._collaborators.policy.materialize_view(
            rows, pins=pins, presented_fingerprint=presented_fingerprint
        )

    def place_series(
        self,
        partition: object,
        rows: Sequence[Mapping[str, object]],
        *,
        presented_fingerprint: object | None = None,
    ) -> Result[SeriesPlacement]:
        """Archive time-series ``rows`` within their ``(source, instrument, window)`` partition.

        The partition is embedded in the archived artifact and so enters its fp1 identity,
        meaning the same series bytes under two windows are two distinct artifacts and the
        stored evidence resolves back to exactly this partition (AC5; DEC-0118). The write
        lands in the evidence-bearing immutable raw archive, keyed on its fp1; a
        ``world = simulated`` write and a cross-world read stay refused by the store seam.
        A non-:class:`SeriesPartition` partition, or an empty series, is an ``invalid
        input`` refusal.

        Every row's event-time (int64 UTC-ns under key ``t``) must fall inside the declared
        partition window ``[start, end)``; a row missing its event-time, or one whose
        event-time falls outside the window, is an ``invalid input`` refusal. This keeps the
        stored window a truthful bound on its rows, so the split-governed research door can
        derive a no-peek seal position from the window that a caller cannot under-state to
        smuggle a sealed-period row behind an open-window front (AC5; DEC-0119).
        """
        return self._collaborators.policy.place_series(
            partition, rows, presented_fingerprint=presented_fingerprint
        )

    def resolve_series(
        self, archive_fingerprint: object, *, for_world: object
    ) -> Result[ResolvedSeries]:
        """Resolve archived time-series evidence back within its partition (AC5).

        ``archive_fingerprint`` is the key from a :class:`SeriesPlacement`
        (``placement.archive.fingerprint``); ``for_world`` is the world the caller declares
        it is reading as. A cross-world read is a ``policy rejection`` and a miss is a
        ``stale evidence`` refusal — both surfaced by the store seam. The stored artifact
        must be exactly one series envelope carrying a rebuildable ``(source, instrument,
        window)`` partition and its rows; a corrupt or non-series artifact is a ``storage
        failure`` refusal, never resolved as valid series evidence. The returned partition
        proves the evidence resolves inside its declared partition.

        When a no-peek seal is wired, series resolution is guarded at the split-governed
        research door: a series reaching into the sealed no-peek period is a ``policy
        rejection`` — never a silent empty result — so research never resolves its own
        held-out evaluation period (AC4; DEC-0119). The read position is **derived from the
        resolved evidence itself** — the latest of the series' declared window end and its
        rows' own event-times — never a caller argument, so the seal cannot be bypassed by
        omitting a position nor by an under-stated window (the read is composed through
        :meth:`AppendStore.read_raw_self_guarded`, which guards the seal at that derived
        position and never returns sealed raw bytes unguarded).

        The seal is honored **whichever place it is wired**: a seal wired here on
        :meth:`for_world` is consulted at the derived position, and a seal wired into the
        store's :class:`~qmf.data.store.AppendStore` is consulted at the same position by
        ``read_raw_self_guarded`` — so wiring the seal at either surface (or both) leaves no
        unguarded research door, and neither can be bypassed by wiring only the other.
        """
        return self._collaborators.policy.resolve_series(
            archive_fingerprint, for_world=for_world
        )
