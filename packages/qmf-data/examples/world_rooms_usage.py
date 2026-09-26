"""Reference usage — the seven room-roles per world (Story 3.3; COMP-QMF-DATA).

Executable::

    python packages/qmf-data/examples/world_rooms_usage.py

Shows the five things Story 3.3 pins down:

1. The seven room-roles instantiated **independently per world** — ``live`` and
   ``replay`` each get their own set, and ``world = simulated`` is reserved-unusable
   (a policy rejection).
2. A rebuildable analytics view records its pinned engine major AND the original
   calendar identity + tzdata version a rebuild must pin — and is never
   evidence-bearing.
3. Retention: raw evidence is kept forever (deletion never licensed); a rebuildable
   view is deletion-licensed only while no result label cites it.
4. World isolation is storage separation: a read declaring a different world than the
   evidence's is a policy rejection.
5. Time-series evidence resolves within its ``(source, instrument, time-window)``
   partition, and the resolved partition is exactly the one it was placed in.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    Fingerprint,
    Instant,
    Instrument,
    Interval,
    Result,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.data import (
    EvidenceStore,
    RebuildPins,
    RetentionPolicy,
    SeriesPartition,
    WorldRooms,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a call we require to succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    """A real check (not a bare ``assert``, which ``-O`` strips) for a demonstrated fact."""
    if not condition:
        raise AssertionError(f"expected {what}")


class _CitesNothing:
    """A citation index for the demo: no result label cites anything."""

    def cites(self, fingerprint: Fingerprint, /) -> bool:
        return False


class _CitesOne:
    """A citation index that cites exactly one fingerprint."""

    def __init__(self, cited: Fingerprint) -> None:
        self._cited = cited.value

    def cites(self, fingerprint: Fingerprint, /) -> bool:
        return fingerprint.value == self._cited


def seven_roles_per_world(store: EvidenceStore) -> None:
    """Each world instantiates the seven room-roles independently; simulated refuses."""
    live = _unwrap(WorldRooms.for_world(store, World.LIVE), "live rooms")
    replay = _unwrap(WorldRooms.for_world(store, World.REPLAY), "replay rooms")
    _require(len(live.roles) == 7, "seven room-roles")
    _require(live.world != replay.world, "live and replay are independent worlds")
    simulated = WorldRooms.for_world(store, World.SIMULATED)
    _require(is_refusal(simulated), "simulated rooms refused")
    _require(
        is_refusal(simulated) and simulated.category.value == "policy rejection",
        "simulated is a policy rejection",
    )


def rebuildable_view_records_pins(rooms: WorldRooms) -> tuple[str, str, str]:
    """A rebuildable view records its engine major + rebuild calendar/tzdata pins."""
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"), "calendar")
    pins = _unwrap(RebuildPins.try_create(calendar), "rebuild pins")
    receipt = _unwrap(
        rooms.materialize_view([{"bar": 1, "close": 100}], pins=pins), "materialized view"
    )
    _require(not receipt.is_evidence_bearing, "a rebuildable view is never evidence-bearing")
    _require(receipt.engine_major is not None, "the engine major is recorded")
    _require(
        receipt.rebuild_calendar_identity == "forex-17NY:v3", "the calendar identity is pinned"
    )
    _require(receipt.rebuild_tzdata_version == "2025a", "the tzdata version is pinned")
    return (
        receipt.engine_major or "",
        receipt.rebuild_calendar_identity or "",
        receipt.rebuild_tzdata_version or "",
    )


def retention_law(rooms: WorldRooms) -> tuple[bool, bool, bool]:
    """Raw stays forever; a rebuildable view is deletable only while uncited."""
    partition = _series_partition()
    placed = _unwrap(rooms.place_series(partition, [{"t": 1500, "bid": 11, "ask": 12}]), "placed")
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"), "calendar")
    pins = _unwrap(RebuildPins.try_create(calendar), "pins")
    view = _unwrap(rooms.materialize_view([{"bar": 7}], pins=pins), "view")

    raw_forever = RetentionPolicy(_CitesNothing()).may_delete(placed.archive)
    view_uncited = RetentionPolicy(_CitesNothing()).may_delete(view)
    view_cited = RetentionPolicy(_CitesOne(view.fingerprint)).may_delete(view)
    _require(not raw_forever, "raw evidence is never deletable")
    _require(view_uncited, "an uncited rebuildable view is deletion-licensed")
    _require(not view_cited, "a cited rebuildable view is retained forever")
    return (raw_forever, view_uncited, view_cited)


def series_resolves_within_partition(rooms: WorldRooms) -> str:
    """Time-series evidence resolves back within its exact partition."""
    partition = _series_partition()
    placed = _unwrap(
        rooms.place_series(partition, [{"t": 1500, "bid": 11, "ask": 12}]), "placed series"
    )
    resolved = _unwrap(
        rooms.resolve_series(placed.archive.fingerprint.value, for_world=rooms.world),
        "resolved series",
    )
    _require(resolved.partition == partition, "resolves within the placed partition")
    _require(len(resolved.rows) == 1, "the one series row survives")
    return partition.partition_key


def cross_world_read_refused(rooms: WorldRooms) -> str:
    """A read declaring a different world than the evidence's is a policy rejection."""
    partition = _series_partition()
    placed = _unwrap(rooms.place_series(partition, [{"t": 1500, "px": 100}]), "placed")
    other = World.REPLAY if rooms.world is World.LIVE else World.LIVE
    cross = rooms.resolve_series(placed.archive.fingerprint.value, for_world=other)
    _require(is_refusal(cross), "cross-world read refused")
    return cross.category.value if is_refusal(cross) else "unexpected-ok"


def _series_partition() -> SeriesPartition:
    venue = _unwrap(VenueId.try_create("dukascopy"), "venue")
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")
    start = _unwrap(Instant.try_create(1_000), "start")
    end = _unwrap(Instant.try_create(2_000), "end")
    window = _unwrap(Interval.try_create(start, end), "window")
    return _unwrap(SeriesPartition.try_create("dukascopy-ticks", instrument, window), "partition")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qmf-world-rooms-") as tmp:
        store = EvidenceStore(Path(tmp))
        rooms = _unwrap(WorldRooms.for_world(store, World.LIVE), "live rooms")

        seven_roles_per_world(store)
        print("seven room-roles per world; simulated: policy rejection")

        engine_major, calendar, tzdata = rebuildable_view_records_pins(rooms)
        print(f"rebuildable view pins: engine={engine_major}, calendar={calendar}, tzdata={tzdata}")

        raw_forever, view_uncited, view_cited = retention_law(rooms)
        print(
            "retention: raw deletable="
            f"{raw_forever}, uncited-view deletable={view_uncited}, "
            f"cited-view deletable={view_cited}"
        )

        key = series_resolves_within_partition(rooms)
        print(f"series resolves within partition: {key}")

        outcome = cross_world_read_refused(rooms)
        print(f"cross-world read: {outcome}")


if __name__ == "__main__":
    main()
