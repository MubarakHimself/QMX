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
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from qmf.core import (
    CalendarIdentity,
    Instant,
    Ok,
    Result,
    Retryability,
    TypedRefusal,
    World,
    is_ok,
    is_refusal,
)
from qmf.data.partitions import ResolvedSeries, SeriesPartition, SeriesPlacement
from qmf.data.store import (
    EVIDENCE_BEARING_ROLES,
    AppendStore,
    BackupInput,
    EvidenceStore,
    JournalStore,
    ReadSeal,
    RegistryRoom,
    RoomRole,
    StoreReceipt,
    WorldStore,
    guard_sealed_read,
)
from qmf.data.store.refusals import invalid_input, storage_failure

__all__ = ["RebuildPins", "WorldRooms"]

# The CT-12 read-boundary name a split-governed series resolution is guarded at
# (DEC-0119); the pinned ReadBoundary value, coerced back by the injected seal.
_RESEARCH_DOOR_BOUNDARY = "split-governed research door"


@dataclass(frozen=True, slots=True)
class RebuildPins:
    """The pins a rebuild of a rebuildable analytics view must honor (AC2).

    A processed/analytics view is never evidence: an engine format break costs a rebuild.
    A faithful rebuild must replay against the **exact** calendar the view was built
    under, so this value carries the original :class:`~qmf.core.CalendarIdentity` — which
    itself pins the ``tzdata_version`` — and the view's receipt records both the calendar
    identity and the tzdata version, so a rebuild can never silently re-derive the seal or
    a session boundary under a later tzdata release (DEC-0117, DEC-0103, DEC-0106).

    The analytics-engine major is *not* carried here: the engine records its own major on
    the receipt, so this value holds only what the caller must declare — the calendar the
    view was computed under.
    """

    calendar_identity: CalendarIdentity

    @classmethod
    def try_create(cls, calendar_identity: object) -> Result[RebuildPins]:
        """Validate and build :class:`RebuildPins`, returning value-or-refusal.

        ``calendar_identity`` must be a ``qmf-core`` :class:`CalendarIdentity` (which
        already pins its rule set, rule-set version, and tzdata version); anything else is
        an ``invalid input`` refusal (CT-04; DEC-0109).
        """
        if not isinstance(calendar_identity, CalendarIdentity):
            return invalid_input(
                "calendar_identity",
                "rebuild pins carry a qmf-core CalendarIdentity — the original calendar a "
                "rebuild must replay against (DEC-0106)",
                given=repr(calendar_identity),
            )
        return Ok(cls(calendar_identity=calendar_identity))

    def calendar_identity_label(self) -> str:
        """The calendar identity a rebuild pins, as an opaque ``rule_set:version`` label.

        The tzdata version is recorded separately (:attr:`tzdata_version`), matching the
        CT-11 ``rebuild_calendar_identity`` / ``rebuild_tzdata_version`` split.
        """
        return f"{self.calendar_identity.rule_set}:{self.calendar_identity.rule_set_version}"

    @property
    def tzdata_version(self) -> str:
        """The original tzdata version a rebuild pins (from the calendar identity)."""
        return self.calendar_identity.tzdata_version


class WorldRooms:
    """The seven room-roles for exactly one world, over the Story 3.1 store seam (AC1).

    Constructed from a resolved :class:`~qmf.data.store.WorldStore`; use
    :meth:`for_world` to obtain one from an :class:`~qmf.data.store.EvidenceStore` (which
    refuses ``world = simulated``). The four store boundaries are surfaced read-only, and
    the data-policy operations (rebuildable views, series placement/resolution) sit on top
    of them.
    """

    def __init__(self, world_store: WorldStore, *, seal: ReadSeal | None = None) -> None:
        self._store = world_store
        self._seal = seal

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
        bundle = store.for_world(world)
        if is_refusal(bundle):
            return bundle
        return Ok(cls(bundle.value, seal=seal))

    @property
    def world(self) -> World:
        """The one world whose seven rooms this facade owns."""
        return self._store.world

    @property
    def roles(self) -> tuple[RoomRole, ...]:
        """The seven room-roles this world instantiates, in CT-11's declared order (AC1)."""
        return tuple(RoomRole)

    @property
    def evidence_bearing_roles(self) -> frozenset[RoomRole]:
        """The two evidence-bearing roles — immutable raw archive and journal (AC2, AC5)."""
        return EVIDENCE_BEARING_ROLES

    def is_evidence_bearing(self, role: RoomRole) -> bool:
        """Whether ``role`` is evidence-bearing — true only for raw archive and journal.

        Processed data and analytics views are rebuildable, so they are never
        evidence-bearing; an engine format break over them costs a rebuild, not evidence
        (AC2, AC5; DEC-0117).
        """
        return role in EVIDENCE_BEARING_ROLES

    # --- the four physical boundaries, surfaced read-only --------------------

    @property
    def append_store(self) -> AppendStore:
        """The CT-11 append-store — immutable raw archive + processed views (this world)."""
        return self._store.append_store

    @property
    def journal(self) -> JournalStore:
        """The CT-13 journal store for this world's journal room."""
        return self._store.journal

    @property
    def registry_room(self) -> RegistryRoom:
        """The CT-09 registry room — records + lineage edges for this world."""
        return self._store.registry_room

    @property
    def backup_input(self) -> BackupInput:
        """The CT-26 store-to-backup input for this world's rooms."""
        return self._store.backup_input

    # --- rebuildable analytics views (AC2) ----------------------------------

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
        if not isinstance(pins, RebuildPins):
            return invalid_input(
                "pins",
                "a governed rebuildable view must record the calendar a rebuild pins; "
                "build RebuildPins.try_create(calendar_identity) first (AC2, DEC-0117)",
                given=repr(pins),
            )
        return self._store.append_store.materialize_view(
            rows,
            presented_fingerprint=presented_fingerprint,
            rebuild_calendar_identity=pins.calendar_identity_label(),
            rebuild_tzdata_version=pins.tzdata_version,
        )

    # --- time-series partitioning (AC5) -------------------------------------

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
        if not isinstance(partition, SeriesPartition):
            return invalid_input(
                "partition",
                "time-series evidence is placed within a SeriesPartition "
                "(source, instrument, time-window); build one via SeriesPartition.try_create",
                given=repr(partition),
            )
        series = [dict(row) for row in rows]
        if not series:
            return invalid_input(
                "rows",
                "a time-series artifact must carry at least one row; an empty series is "
                "refused rather than archived as evidence for nothing (L5)",
            )
        for index, row in enumerate(series):
            outside = self._row_outside_window(partition, row, index)
            if outside is not None:
                return outside
        envelope: dict[str, object] = {"partition": partition.identity(), "series": series}
        appended = self._store.append_store.append_raw(
            [envelope], presented_fingerprint=presented_fingerprint
        )
        if is_refusal(appended):
            return appended
        return Ok(SeriesPlacement(partition=partition, archive=appended.value))

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
        resolved_holder: list[ResolvedSeries] = []

        def _derive(rows: list[dict[str, object]]) -> Result[object]:
            if len(rows) != 1:
                return storage_failure(
                    "a time-series artifact holds exactly one series envelope, but the stored "
                    f"artifact held {len(rows)} rows; the evidence is corrupt",
                    retryability=Retryability.NO,
                    context={"rows": len(rows), "fingerprint": repr(archive_fingerprint)},
                )
            resolved = self._resolve_envelope(rows[0], archive_fingerprint)
            if is_refusal(resolved):
                return resolved
            resolved_holder.append(resolved.value)
            position: object = self._series_seal_position(resolved.value)
            # Consult the facade-level no-peek seal at the research door too, so the seal
            # holds whichever place it is wired: a caller that wires it ONLY here (over a
            # store with no seal) still gets a guarded door, and the store-level seal is
            # guarded separately by read_raw_self_guarded below. Both consult the same
            # derived position, so neither can be bypassed (AC4; DEC-0119).
            sealed = guard_sealed_read(self._seal, position, boundary=_RESEARCH_DOOR_BOUNDARY)
            if sealed is not None:
                return sealed
            return Ok(position)

        read = self._store.append_store.read_raw_self_guarded(
            archive_fingerprint,
            for_world=for_world,
            boundary=_RESEARCH_DOOR_BOUNDARY,
            derive_position=_derive,
        )
        if is_refusal(read):
            return read
        return Ok(resolved_holder[0])

    @staticmethod
    def _row_outside_window(
        partition: SeriesPartition, row: Mapping[str, object], index: int
    ) -> TypedRefusal | None:
        """A refusal if ``row``'s event-time is missing or outside ``partition``'s window (AC5).

        The event-time is the int64 UTC-ns count under key ``t``. A row without one cannot be
        checked against the window, and a row whose event-time falls outside the half-open
        ``[start, end)`` window would let an under-stated window hide a later (possibly sealed)
        row — both are ``invalid input`` refusals naming the offending row ``index`` (DEC-0119).
        Returns ``None`` when the row sits truthfully inside the declared window.
        """
        event = row.get("t")
        if not isinstance(event, int) or isinstance(event, bool):
            return invalid_input(
                "rows",
                "each time-series row must carry an int64 UTC-ns event-time under key 't' so "
                "it can be checked against the declared partition window; a row without one "
                "cannot be placed (AC5; DEC-0119)",
                index=index,
            )
        instant = Instant.try_create(event)
        if is_refusal(instant):
            return instant
        contains = partition.contains_event(instant.value)
        if not is_ok(contains) or not contains.value:
            return invalid_input(
                "rows",
                "a time-series row's event-time falls outside the declared partition window; "
                "the partition window must truthfully bound its rows, so an under-stated "
                "window can never place a sealed-period row behind an open-window front "
                "(AC5; DEC-0119)",
                index=index,
                event_ns=event,
                window_start_ns=partition.window.start.value_ns,
                window_end_ns=partition.window.end.value_ns,
            )
        return None

    @staticmethod
    def _series_seal_position(resolved: ResolvedSeries) -> int:
        """The knowledge position a series resolution guards the no-peek seal at (AC4; DEC-0119).

        The latest of the series' declared window end and its rows' own event-times, taken
        from the resolved evidence. Because :meth:`place_series` keeps every row inside the
        window, the window end normally dominates; taking the maximum with the rows' own
        event-times additionally closes any artifact archived directly through the raw-archive
        seam with an under-stated window, so the derived position is never earlier than the
        data it guards and the seal cannot be bypassed.
        """
        latest_ns = resolved.partition.window.end.value_ns
        for row in resolved.rows:
            event = row.get("t")
            if isinstance(event, int) and not isinstance(event, bool) and event > latest_ns:
                latest_ns = event
        return latest_ns

    @staticmethod
    def _resolve_envelope(
        envelope: Mapping[str, object], archive_fingerprint: object
    ) -> Result[ResolvedSeries]:
        """Rebuild a :class:`ResolvedSeries` from one stored series envelope, or refuse.

        A missing/ill-typed ``partition`` or ``series``, or a partition that no longer
        rebuilds (a corrupt venue token, a start after its end), is a ``storage failure``
        — the artifact is stored evidence that no longer matches the series shape, not a
        caller mistake — so a corrupt series is never resolved as valid evidence.
        """
        raw_partition = envelope.get("partition")
        raw_series = envelope.get("series")
        if not isinstance(raw_partition, Mapping) or not isinstance(raw_series, list):
            return storage_failure(
                "the stored artifact is not a time-series envelope (missing its partition "
                "or series); the evidence is corrupt",
                retryability=Retryability.NO,
                context={"fingerprint": repr(archive_fingerprint)},
            )
        partition = SeriesPartition.from_identity(cast("Mapping[str, object]", raw_partition))
        if not is_ok(partition):
            return storage_failure(
                "the stored series partition no longer rebuilds; the evidence is corrupt",
                retryability=Retryability.NO,
                context={"fingerprint": repr(archive_fingerprint)},
            )
        series_rows: list[dict[str, object]] = []
        for row in cast("list[object]", raw_series):
            if not isinstance(row, Mapping):
                return storage_failure(
                    "a stored series row is not a mapping; the evidence is corrupt",
                    retryability=Retryability.NO,
                    context={"fingerprint": repr(archive_fingerprint)},
                )
            series_rows.append(dict(cast("Mapping[str, object]", row)))
        return Ok(ResolvedSeries(partition=partition.value, rows=tuple(series_rows)))
