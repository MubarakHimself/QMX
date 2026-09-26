"""Rebuildable-view and time-series policy over one world's append-store (AC2, AC5).

Disconnected from :class:`~qmf.data.rooms.WorldRooms` role-catalog and
store-boundary groups (LCOM4). Helpers are module functions so the policy
class stays one connected component over ``_store`` / ``_seal``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from qmf.core import Instant, Ok, Result, Retryability, TypedRefusal, is_ok, is_refusal
from qmf.data.partitions import ResolvedSeries, SeriesPartition, SeriesPlacement
from qmf.data.rooms_pins import RebuildPins
from qmf.data.store import ReadSeal, StoreReceipt, WorldStore, guard_sealed_read
from qmf.data.store.refusals import invalid_input, storage_failure

# The CT-12 read-boundary name a split-governed series resolution is guarded at
# (DEC-0119); the pinned ReadBoundary value, coerced back by the injected seal.
RESEARCH_DOOR_BOUNDARY = "split-governed research door"


def row_outside_window(
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


def series_seal_position(resolved: ResolvedSeries) -> int:
    """The knowledge position a series resolution guards the no-peek seal at (AC4; DEC-0119).

    The latest of the series' declared window end and its rows' own event-times, taken
    from the resolved evidence. Because :meth:`WorldRooms.place_series` keeps every row
    inside the window, the window end normally dominates; taking the maximum with the rows'
    own event-times additionally closes any artifact archived directly through the
    raw-archive seam with an under-stated window, so the derived position is never earlier
    than the data it guards and the seal cannot be bypassed.
    """
    latest_ns = resolved.partition.window.end.value_ns
    for row in resolved.rows:
        event = row.get("t")
        if isinstance(event, int) and not isinstance(event, bool) and event > latest_ns:
            latest_ns = event
    return latest_ns


def resolve_envelope(
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


def derive_series_position(
    rows: list[dict[str, object]],
    *,
    archive_fingerprint: object,
    seal: ReadSeal | None,
    resolved_holder: list[ResolvedSeries],
) -> Result[object]:
    """Derive the seal position from one stored series envelope, or refuse."""
    if len(rows) != 1:
        return storage_failure(
            "a time-series artifact holds exactly one series envelope, but the stored "
            f"artifact held {len(rows)} rows; the evidence is corrupt",
            retryability=Retryability.NO,
            context={"rows": len(rows), "fingerprint": repr(archive_fingerprint)},
        )
    resolved = resolve_envelope(rows[0], archive_fingerprint)
    if is_refusal(resolved):
        return resolved
    resolved_holder.append(resolved.value)
    position: object = series_seal_position(resolved.value)
    # Consult the facade-level no-peek seal at the research door too, so the seal
    # holds whichever place it is wired: a caller that wires it ONLY here (over a
    # store with no seal) still gets a guarded door, and the store-level seal is
    # guarded separately by read_raw_self_guarded below. Both consult the same
    # derived position, so neither can be bypassed (AC4; DEC-0119).
    sealed = guard_sealed_read(seal, position, boundary=RESEARCH_DOOR_BOUNDARY)
    if sealed is not None:
        return sealed
    return Ok(position)


class WorldRoomPolicy:
    """Rebuildable views and series placement/resolution over one world's append-store."""

    def __init__(self, world_store: WorldStore, seal: ReadSeal | None) -> None:
        self._store = world_store
        self._seal = seal

    def materialize_view(
        self,
        rows: Sequence[Mapping[str, object]],
        *,
        pins: object,
        presented_fingerprint: object | None = None,
    ) -> Result[StoreReceipt]:
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

    def place_series(
        self,
        partition: object,
        rows: Sequence[Mapping[str, object]],
        *,
        presented_fingerprint: object | None = None,
    ) -> Result[SeriesPlacement]:
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
            outside = row_outside_window(partition, row, index)
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
        resolved_holder: list[ResolvedSeries] = []

        def _derive(rows: list[dict[str, object]]) -> Result[object]:
            return derive_series_position(
                rows,
                archive_fingerprint=archive_fingerprint,
                seal=self._seal,
                resolved_holder=resolved_holder,
            )

        read = self._store.append_store.read_raw_self_guarded(
            archive_fingerprint,
            for_world=for_world,
            boundary=RESEARCH_DOOR_BOUNDARY,
            derive_position=_derive,
        )
        if is_refusal(read):
            return read
        return Ok(resolved_holder[0])
