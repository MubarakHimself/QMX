"""Tier-1 tests for WorldRooms — seven room-roles per world (AC1, AC2, AC4, AC5)."""

from __future__ import annotations

from qmf.core import (
    CalendarIdentity,
    Instant,
    Instrument,
    Interval,
    RefusalCategory,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.data.partitions import SeriesPartition
from qmf.data.rooms import RebuildPins, WorldRooms
from qmf.data.store import EvidenceStore, RoomRole


def _rooms(store: EvidenceStore, world: World = World.LIVE) -> WorldRooms:
    built = WorldRooms.for_world(store, world)
    assert is_ok(built), built
    return built.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    venue = VenueId.try_create("dukascopy")
    assert is_ok(venue)
    instrument = Instrument.try_create(venue.value, symbol)
    assert is_ok(instrument)
    return instrument.value


def _partition(
    source: str = "dukascopy-ticks", start: int = 1_000, end: int = 2_000
) -> SeriesPartition:
    s = Instant.try_create(start)
    e = Instant.try_create(end)
    assert is_ok(s)
    assert is_ok(e)
    window = Interval.try_create(s.value, e.value)
    assert is_ok(window)
    part = SeriesPartition.try_create(source, _instrument(), window.value)
    assert is_ok(part)
    return part.value


def _pins() -> RebuildPins:
    calendar = CalendarIdentity.try_create("forex-17NY", "v3", "2025a")
    assert is_ok(calendar)
    pins = RebuildPins.try_create(calendar.value)
    assert is_ok(pins)
    return pins.value


# --- AC1: seven room-roles instantiated independently per world ------------


def test_for_world_exposes_the_seven_roles_in_order(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    assert rooms.world is World.LIVE
    assert [role.value for role in rooms.roles] == [
        "ingest door",
        "immutable raw archive",
        "processed",
        "journal",
        "split-governed research door",
        "backup",
        "registry room",
    ]


def test_live_and_replay_are_instantiated_independently(store: EvidenceStore) -> None:
    live = _rooms(store, World.LIVE)
    replay = _rooms(store, World.REPLAY)
    assert live.world is World.LIVE
    assert replay.world is World.REPLAY
    # Storage separation: a series placed in live is absent from replay's own room.
    placed = live.place_series(_partition(), [{"t": 1_500, "px": 100}])
    assert is_ok(placed)
    absent = replay.resolve_series(placed.value.archive.fingerprint.value, for_world=World.REPLAY)
    assert is_refusal(absent)
    assert absent.category is RefusalCategory.STALE_EVIDENCE


def test_simulated_world_is_reserved_unusable(store: EvidenceStore) -> None:
    result = WorldRooms.for_world(store, World.SIMULATED)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_evidence_bearing_classification(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    assert rooms.evidence_bearing_roles == frozenset(
        {RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL}
    )
    assert rooms.is_evidence_bearing(RoomRole.IMMUTABLE_RAW_ARCHIVE)
    assert rooms.is_evidence_bearing(RoomRole.JOURNAL)
    assert not rooms.is_evidence_bearing(RoomRole.PROCESSED)
    assert not rooms.is_evidence_bearing(RoomRole.REGISTRY_ROOM)


def test_boundaries_surface_the_store_seam(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    bundle = store.for_world(World.LIVE)
    assert is_ok(bundle)
    assert rooms.append_store is bundle.value.append_store
    assert rooms.journal is bundle.value.journal
    assert rooms.registry_room is bundle.value.registry_room
    assert rooms.backup_input is bundle.value.backup_input


# --- AC2: rebuildable views record engine major + rebuild pins -------------


def test_materialize_view_records_engine_major_and_rebuild_pins(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    receipt = rooms.materialize_view([{"bar": 1, "close": 100}], pins=_pins())
    assert is_ok(receipt)
    view = receipt.value
    assert view.is_evidence_bearing is False
    assert view.retained_forever is False
    assert view.engine_major is not None and view.engine_major.startswith("duckdb-")
    assert view.rebuild_calendar_identity == "forex-17NY:v3"
    assert view.rebuild_tzdata_version == "2025a"
    assert view.room_role is RoomRole.PROCESSED


def test_materialize_view_requires_rebuild_pins(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    for bad in (None, "forex-17NY", 3):
        result = rooms.materialize_view([{"bar": 1}], pins=bad)
        assert is_refusal(result)
        assert result.category is RefusalCategory.INVALID_INPUT
        assert result.context.get("field") == "pins"


def test_rebuild_pins_try_create_refuses_non_calendar() -> None:
    result = RebuildPins.try_create("forex-17NY")
    assert is_refusal(result)
    assert result.context.get("field") == "calendar_identity"


def test_rebuild_pins_expose_label_and_tzdata() -> None:
    pins = _pins()
    assert pins.calendar_identity_label() == "forex-17NY:v3"
    assert pins.tzdata_version == "2025a"


# --- AC4: cross-world read is a policy rejection ---------------------------


def test_cross_world_series_read_is_policy_rejection(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    placed = rooms.place_series(_partition(), [{"t": 1_500, "px": 100}])
    assert is_ok(placed)
    cross = rooms.resolve_series(placed.value.archive.fingerprint.value, for_world=World.REPLAY)
    assert is_refusal(cross)
    assert cross.category is RefusalCategory.POLICY_REJECTION


def test_resolve_series_requires_a_world_declaration(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    placed = rooms.place_series(_partition(), [{"t": 1_500, "px": 100}])
    assert is_ok(placed)
    missing = rooms.resolve_series(placed.value.archive.fingerprint.value, for_world=None)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT


# --- AC5: time-series evidence resolves within its partition ---------------


def test_place_and_resolve_series_round_trips_within_partition(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    partition = _partition()
    placed = rooms.place_series(partition, [{"t": 1_500, "bid": 11, "ask": 12}])
    assert is_ok(placed)
    assert placed.value.partition == partition
    assert placed.value.archive.is_evidence_bearing is True
    assert placed.value.archive.room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE
    resolved = rooms.resolve_series(placed.value.archive.fingerprint.value, for_world=World.LIVE)
    assert is_ok(resolved)
    assert resolved.value.partition == partition
    assert resolved.value.rows == ({"ask": 12, "bid": 11, "t": 1_500},)


def test_same_series_bytes_under_two_windows_are_distinct_artifacts(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    rows = [{"t": 1_500, "px": 100}]
    a = rooms.place_series(_partition(start=1_000, end=2_000), rows)
    b = rooms.place_series(_partition(start=1_000, end=3_000), rows)
    assert is_ok(a)
    assert is_ok(b)
    # The window rode into the artifact's fp1 identity, so the partitions do not alias.
    assert a.value.archive.fingerprint != b.value.archive.fingerprint


def test_place_series_refuses_non_partition(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    result = rooms.place_series("dukascopy-ticks", [{"t": 1_500}])
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context.get("field") == "partition"


def test_place_series_refuses_empty_series(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    result = rooms.place_series(_partition(), [])
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context.get("field") == "rows"


def test_place_series_refuses_row_outside_window(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    # A row whose event-time falls outside the declared partition window is refused: the
    # window must truthfully bound its rows so the no-peek seal cannot be gamed (AC5; DEC-0119).
    result = rooms.place_series(_partition(start=1_000, end=2_000), [{"t": 5_000, "px": 1}])
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context.get("field") == "rows"
    assert result.context.get("event_ns") == 5_000
    # The half-open window excludes its end: a row exactly at `end` is outside it.
    at_end = rooms.place_series(_partition(start=1_000, end=2_000), [{"t": 2_000, "px": 1}])
    assert is_refusal(at_end)
    assert at_end.category is RefusalCategory.INVALID_INPUT


def test_place_series_refuses_row_without_valid_event_time(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    # A row missing its int64-ns event-time under key 't' cannot be bounded, so it is refused.
    missing = rooms.place_series(_partition(), [{"px": 1}])
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    assert missing.context.get("field") == "rows"
    # A non-int event-time is likewise refused.
    non_int = rooms.place_series(_partition(), [{"t": "soon", "px": 1}])
    assert is_refusal(non_int)
    assert non_int.category is RefusalCategory.INVALID_INPUT
    # A bool is an int subclass but is not an int64 event-time.
    boolean = rooms.place_series(_partition(), [{"t": True, "px": 1}])
    assert is_refusal(boolean)
    assert boolean.category is RefusalCategory.INVALID_INPUT
    # An out-of-int64-range event-time is refused by the Instant factory.
    huge = rooms.place_series(_partition(), [{"t": 2**63, "px": 1}])
    assert is_refusal(huge)
    assert huge.category is RefusalCategory.INVALID_INPUT


def test_place_series_surfaces_a_store_refusal(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    # A binary float in identity content is refused by the store's fp1 serializer, and
    # place_series surfaces that refusal rather than reporting a placement (DEC-0108).
    result = rooms.place_series(_partition(), [{"t": 1_500, "px": 1.5}])
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_resolve_series_miss_is_stale_evidence(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    absent = "fp1:sha256:" + "0" * 64
    result = rooms.resolve_series(absent, for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category is RefusalCategory.STALE_EVIDENCE


def test_rebuildable_view_is_never_resolved_as_series_evidence(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    view = rooms.materialize_view([{"bar": 1}], pins=_pins())
    assert is_ok(view)
    # A view lives in the processed room, never the raw archive, so resolving it as
    # series evidence finds nothing — a rebuildable view is never treated as evidence.
    resolved = rooms.resolve_series(view.value.fingerprint.value, for_world=World.LIVE)
    assert is_refusal(resolved)
    assert resolved.category is RefusalCategory.STALE_EVIDENCE


def test_multi_row_artifact_is_not_a_series_envelope(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    # A raw artifact holding two rows is not a single series envelope.
    raw = rooms.append_store.append_raw([{"a": 1}, {"b": 2}])
    assert is_ok(raw)
    result = rooms.resolve_series(raw.value.fingerprint.value, for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category is RefusalCategory.STORAGE_FAILURE


def test_corrupt_series_envelopes_are_storage_failures(store: EvidenceStore) -> None:
    rooms = _rooms(store)
    good_identity = _partition().identity()
    corrupt_artifacts: list[dict[str, object]] = [
        {"nope": 1},  # missing partition + series
        {"partition": good_identity, "series": "not-a-list"},  # series not a list
        {"partition": {"venue": ""}, "series": [{"t": 1}]},  # partition no longer rebuilds
        {"partition": good_identity, "series": [{"t": 1}, "not-a-map"]},  # a row is not a mapping
    ]
    for artifact in corrupt_artifacts:
        raw = rooms.append_store.append_raw([artifact])
        assert is_ok(raw), artifact
        result = rooms.resolve_series(raw.value.fingerprint.value, for_world=World.LIVE)
        assert is_refusal(result), artifact
        assert result.category is RefusalCategory.STORAGE_FAILURE
