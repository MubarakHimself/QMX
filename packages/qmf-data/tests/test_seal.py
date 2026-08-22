"""Tier-1 tests for the CT-12 no-peek seal (Story 3.4; AC4, AC5, AC6)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Fingerprint,
    Instant,
    Instrument,
    Interval,
    RefusalCategory,
    TradingDate,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data.partitions import SeriesPartition
from qmf.data.rooms import WorldRooms
from qmf.data.seal import (
    FINAL_LOOK_SUBTYPE,
    SEAL_CONTROL_STREAM,
    HoldoutSeal,
    ReadBoundary,
)
from qmf.data.splits import ProducerHorizon, SplitBoundary, SplitManifest
from qmf.data.store import EvidenceStore, JournalStore, RoomRole


def _calendar(version: str = "v3") -> CalendarIdentity:
    built = CalendarIdentity.try_create("forex-17NY", version, "2025a")
    assert is_ok(built)
    return built.value


def _trading_boundary(calendar: CalendarIdentity, year: int, month: int, day: int) -> SplitBoundary:
    civil = CivilDate.try_create(year, month, day)
    assert is_ok(civil)
    trading = TradingDate.try_create(calendar, civil.value)
    assert is_ok(trading)
    built = SplitBoundary.try_create(trading.value)
    assert is_ok(built)
    return built.value


def _instant(value_ns: int) -> Instant:
    built = Instant.try_create(value_ns)
    assert is_ok(built)
    return built.value


def _instant_boundary(value_ns: int) -> SplitBoundary:
    built = SplitBoundary.try_create(_instant(value_ns))
    assert is_ok(built)
    return built.value


def _seal(
    *, calendar: CalendarIdentity | None = None, world: World = World.REPLAY, months: int = 12
) -> HoldoutSeal:
    cal = calendar if calendar is not None else _calendar()
    built = HoldoutSeal.try_create(
        seal_boundary=_trading_boundary(cal, 2025, 1, 1),
        calendar_identity=cal,
        world=world,
        holdout_months=months,
    )
    assert is_ok(built)
    return built.value


def _writer() -> WriterId:
    built = WriterId.try_create("workstation", "qmf-data", SEAL_CONTROL_STREAM, "boot-1")
    assert is_ok(built)
    return built.value


def _journal(store: EvidenceStore, world: World = World.REPLAY) -> JournalStore:
    bundle = store.for_world(world)
    assert is_ok(bundle)
    return bundle.value.journal


def _producer(name: str = "p", bound_ns: int = 50) -> ProducerHorizon:
    built = ProducerHorizon.try_create(name, bound_ns)
    assert is_ok(built)
    return built.value


def _instant_seal(*, boundary_ns: int, world: World = World.LIVE, months: int = 12) -> HoldoutSeal:
    # An instant-boundary seal so instant read positions compare cleanly (a trading-date
    # seal against instant rows is the deferred calendar-extension case, GAP-0016).
    built = HoldoutSeal.try_create(
        seal_boundary=_instant_boundary(boundary_ns),
        calendar_identity=_calendar(),
        world=world,
        holdout_months=months,
    )
    assert is_ok(built)
    return built.value


def _series_partition(*, start_ns: int, end_ns: int) -> SeriesPartition:
    venue = VenueId.try_create("dukascopy")
    assert is_ok(venue)
    instrument = Instrument.try_create(venue.value, "EURUSD")
    assert is_ok(instrument)
    start = Instant.try_create(start_ns)
    end = Instant.try_create(end_ns)
    assert is_ok(start)
    assert is_ok(end)
    window = Interval.try_create(start.value, end.value)
    assert is_ok(window)
    part = SeriesPartition.try_create("dukascopy-ticks", instrument.value, window.value)
    assert is_ok(part)
    return part.value


# --- construction -----------------------------------------------------------


def test_try_create_and_properties() -> None:
    cal = _calendar()
    seal = _seal(calendar=cal)
    assert seal.calendar_identity == cal
    assert seal.world is World.REPLAY
    assert seal.holdout_months == 12
    assert seal.fingerprint_label() == "forex-17NY:v3:2025a:2025-01-01"


def test_try_create_refuses_bad_parts() -> None:
    cal = _calendar()
    not_boundary = HoldoutSeal.try_create(
        seal_boundary="2025-01-01", calendar_identity=cal, world=World.REPLAY, holdout_months=12
    )
    assert is_refusal(not_boundary)
    assert not_boundary.context.get("field") == "seal_boundary"
    not_calendar = HoldoutSeal.try_create(
        seal_boundary=_trading_boundary(cal, 2025, 1, 1),
        calendar_identity="forex",
        world=World.REPLAY,
        holdout_months=12,
    )
    assert is_refusal(not_calendar)
    assert not_calendar.context.get("field") == "calendar_identity"
    bad_world = HoldoutSeal.try_create(
        seal_boundary=_trading_boundary(cal, 2025, 1, 1),
        calendar_identity=cal,
        world="nowhere",
        holdout_months=12,
    )
    assert is_refusal(bad_world)
    assert bad_world.context.get("field") == "world"


def test_try_create_refuses_foreign_seal_calendar() -> None:
    result = HoldoutSeal.try_create(
        seal_boundary=_trading_boundary(_calendar("v9"), 2025, 1, 1),
        calendar_identity=_calendar("v3"),
        world=World.REPLAY,
        holdout_months=12,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("field") == "seal_boundary"


def test_try_create_refuses_bad_holdout_months() -> None:
    cal = _calendar()
    for bad in (0, -3, True, "twelve", 1.5):
        result = HoldoutSeal.try_create(
            seal_boundary=_trading_boundary(cal, 2025, 1, 1),
            calendar_identity=cal,
            world=World.REPLAY,
            holdout_months=bad,
        )
        assert is_refusal(result)
        assert result.context.get("field") == "holdout_months"


def test_from_manifest() -> None:
    cal = _calendar()
    segments = SplitManifest.default_split_segments([1_000, 2_000, 3_000])
    assert is_ok(segments)
    manifest = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_trading_boundary(cal, 2025, 1, 1),
        purge_width=50,
        embargo_width=50,
        world=World.REPLAY,
        cited_producers=[_producer()],
    )
    assert is_ok(manifest)
    seal = HoldoutSeal.from_manifest(manifest.value, 12)
    assert is_ok(seal)
    assert seal.value.seal_boundary == manifest.value.seal_boundary
    assert seal.value.world is World.REPLAY
    bad = HoldoutSeal.from_manifest("not-a-manifest", 12)
    assert is_refusal(bad)
    assert bad.context.get("field") == "manifest"


# --- is_sealed --------------------------------------------------------------


def test_is_sealed_reads_the_boundary() -> None:
    cal = _calendar()
    seal = _seal(calendar=cal)
    after = seal.is_sealed(_trading_boundary(cal, 2025, 6, 1))
    at = seal.is_sealed(_trading_boundary(cal, 2025, 1, 1))
    before = seal.is_sealed(_trading_boundary(cal, 2024, 6, 1))
    assert is_ok(after) and after.value is True
    assert (
        is_ok(at) and at.value is True
    )  # at the boundary is sealed (no-peek from the boundary on)
    assert is_ok(before) and before.value is False


def test_is_sealed_refuses_foreign_calendar() -> None:
    seal = _seal(calendar=_calendar("v3"))
    result = seal.is_sealed(_trading_boundary(_calendar("v4"), 2025, 6, 1))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("field") == "calendar_identity"


def test_is_sealed_refuses_cross_kind() -> None:
    seal = _seal()
    result = seal.is_sealed(_instant_boundary(1_000))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_is_sealed_refuses_non_boundary() -> None:
    result = _seal().is_sealed("2025-06-01")
    assert is_refusal(result)
    assert result.context.get("field") == "position"


# --- guard at every read boundary -------------------------------------------


def test_guard_refuses_sealed_read_at_every_boundary(tmp_path: Path) -> None:
    # H3: the seal is wired INTO every read boundary and consulted on a REAL read — the raw
    # archive, processed views, restored backup, and split-governed series resolution — not
    # merely looped against guard() in isolation. A sealed read is a policy rejection at
    # each; a read outside the window reads normally (AC4; DEC-0119).
    seal = _instant_seal(boundary_ns=1_000, world=World.LIVE)
    store = EvidenceStore(tmp_path / "store", seal=seal)
    bundle = store.for_world(World.LIVE)
    assert is_ok(bundle)
    append = bundle.value.append_store
    backup = bundle.value.backup_input
    rooms = WorldRooms.for_world(store, World.LIVE, seal=seal)
    assert is_ok(rooms)

    raw = append.append_raw([{"t": 1, "px": 100}])
    assert is_ok(raw)
    view = append.materialize_view([{"bar": 1}])
    assert is_ok(view)
    sealed_series = rooms.value.place_series(
        _series_partition(start_ns=2_000, end_ns=3_000), [{"t": 2_500, "px": 1}]
    )
    assert is_ok(sealed_series)
    open_series = rooms.value.place_series(
        _series_partition(start_ns=100, end_ns=500), [{"t": 300, "px": 1}]
    )
    assert is_ok(open_series)

    sealed_at = _instant_boundary(2_000)  # >= the seal boundary 1000 -> sealed
    open_at = _instant_boundary(500)  # < 1000 -> outside the sealed window

    # raw archive boundary
    raw_sealed = append.read_raw(raw.value.fingerprint.value, for_world=World.LIVE, at=sealed_at)
    assert is_refusal(raw_sealed)
    assert raw_sealed.category is RefusalCategory.POLICY_REJECTION
    assert raw_sealed.context.get("boundary") == "raw archive"
    assert is_ok(append.read_raw(raw.value.fingerprint.value, for_world=World.LIVE, at=open_at))
    # H3: with a seal wired, a read that declares NO position fails CLOSED. The seal is
    # consulted on every read; a positionless read cannot be proven outside the window, so it
    # is refused rather than served fail-open (never the sealed bytes handed straight back).
    raw_no_pos = append.read_raw(raw.value.fingerprint.value, for_world=World.LIVE)
    assert is_refusal(raw_no_pos)
    assert raw_no_pos.category is RefusalCategory.POLICY_REJECTION
    assert raw_no_pos.context.get("boundary") == "raw archive"

    # processed / views boundary
    view_sealed = append.read_view(view.value.fingerprint.value, for_world=World.LIVE, at=sealed_at)
    assert is_refusal(view_sealed)
    assert view_sealed.context.get("boundary") == "processed"
    assert is_ok(append.read_view(view.value.fingerprint.value, for_world=World.LIVE, at=open_at))
    view_no_pos = append.read_view(view.value.fingerprint.value, for_world=World.LIVE)
    assert is_refusal(view_no_pos)
    assert view_no_pos.category is RefusalCategory.POLICY_REJECTION
    assert view_no_pos.context.get("boundary") == "processed"

    # restored backup boundary
    backup_sealed = backup.read_room(
        RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE, at=sealed_at
    )
    assert is_refusal(backup_sealed)
    assert backup_sealed.context.get("boundary") == "restored backup"
    assert is_ok(backup.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE, at=open_at))
    backup_no_pos = backup.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE)
    assert is_refusal(backup_no_pos)
    assert backup_no_pos.category is RefusalCategory.POLICY_REJECTION
    assert backup_no_pos.context.get("boundary") == "restored backup"

    # split-governed research door — series resolution derives its own position from the
    # series window, so it cannot be bypassed by omitting a declared position.
    series_sealed = rooms.value.resolve_series(
        sealed_series.value.archive.fingerprint.value, for_world=World.LIVE
    )
    assert is_refusal(series_sealed)
    assert series_sealed.category is RefusalCategory.POLICY_REJECTION
    assert series_sealed.context.get("boundary") == "split-governed research door"
    assert is_ok(
        rooms.value.resolve_series(
            open_series.value.archive.fingerprint.value, for_world=World.LIVE
        )
    )

    # Every named read boundary is covered (raw, processed, research door, restored backup).
    assert {member.value for member in ReadBoundary} == {
        "raw archive",
        "processed",
        "split-governed research door",
        "restored backup",
    }


def test_place_series_refuses_row_outside_window_so_the_door_cannot_be_gamed(
    tmp_path: Path,
) -> None:
    # H3 / finding 5: the research door's derived seal position is ungameable only if the
    # stored window truthfully bounds its rows. place_series refuses a row whose event-time
    # falls outside the declared partition window, so a pre-seal window can never carry a
    # sealed-period row that would otherwise resolve through the split-governed door.
    seal = _instant_seal(boundary_ns=1_000, world=World.LIVE)
    store = EvidenceStore(tmp_path / "store", seal=seal)
    rooms = WorldRooms.for_world(store, World.LIVE, seal=seal)
    assert is_ok(rooms)
    leaked = rooms.value.place_series(
        _series_partition(start_ns=100_000, end_ns=200_000),  # a pre-seal window
        [{"t": 5_000_000, "px": 999}],  # a row deep inside the sealed period
    )
    assert is_refusal(leaked)
    assert leaked.category is RefusalCategory.INVALID_INPUT
    assert leaked.context.get("field") == "rows"
    assert leaked.context.get("event_ns") == 5_000_000


def test_resolve_series_derives_seal_position_from_rows_not_just_the_window(
    tmp_path: Path,
) -> None:
    # Defense in depth: even an envelope written straight through the raw-archive seam with a
    # window that under-states its rows cannot leak. resolve_series derives the seal position
    # from the latest of the window end and the rows' own event-times, so a sealed-period row
    # under a pre-seal window is refused at the research door, never resolved.
    seal = _instant_seal(boundary_ns=1_000, world=World.LIVE)
    store = EvidenceStore(tmp_path / "store", seal=seal)
    bundle = store.for_world(World.LIVE)
    assert is_ok(bundle)
    rooms = WorldRooms.for_world(store, World.LIVE, seal=seal)
    assert is_ok(rooms)
    part = _series_partition(start_ns=100_000, end_ns=200_000)  # a pre-seal window
    envelope: dict[str, object] = {
        "partition": part.identity(),
        "series": [{"t": 5_000_000, "px": 999}],  # deep inside the sealed period
    }
    raw = bundle.value.append_store.append_raw([envelope])
    assert is_ok(raw)
    resolved = rooms.value.resolve_series(raw.value.fingerprint.value, for_world=World.LIVE)
    assert is_refusal(resolved)
    assert resolved.category is RefusalCategory.POLICY_REJECTION
    assert resolved.context.get("boundary") == "split-governed research door"


def test_guard_read_coerces_boundary_and_position() -> None:
    # The store seam consults the seal through guard_read with store-neutral inputs: a
    # boundary NAME string and a position as an int64-ns count or a ReadBoundary member.
    seal = _instant_seal(boundary_ns=1_000)
    sealed = seal.guard_read(2_000, boundary="raw archive")
    assert is_refusal(sealed)
    assert sealed.category is RefusalCategory.POLICY_REJECTION
    assert is_ok(seal.guard_read(500, boundary=ReadBoundary.RAW_ARCHIVE))


def test_guard_read_refuses_bad_boundary_and_position() -> None:
    seal = _instant_seal(boundary_ns=1_000)
    bad_boundary = seal.guard_read(500, boundary="not-a-boundary")
    assert is_refusal(bad_boundary)
    assert bad_boundary.context.get("field") == "boundary"
    bad_type = seal.guard_read(500, boundary=7)
    assert is_refusal(bad_type)
    assert bad_type.context.get("field") == "boundary"
    bad_position = seal.guard_read("soon", boundary="raw archive")
    assert is_refusal(bad_position)


def test_guard_allows_pre_seal_read() -> None:
    cal = _calendar()
    seal = _seal(calendar=cal)
    result = seal.guard(_trading_boundary(cal, 2024, 6, 1), boundary=ReadBoundary.RAW_ARCHIVE)
    assert is_ok(result)


def test_guard_refuses_bad_boundary_argument() -> None:
    cal = _calendar()
    seal = _seal(calendar=cal)
    result = seal.guard(_trading_boundary(cal, 2024, 6, 1), boundary="raw")
    assert is_refusal(result)
    assert result.context.get("field") == "boundary"


def test_guard_refuses_non_boundary_position() -> None:
    seal = _seal()
    result = seal.guard("2025-06-01", boundary=ReadBoundary.RESEARCH_DOOR)
    assert is_refusal(result)
    assert result.context.get("field") == "position"


def test_guard_propagates_foreign_calendar_refusal() -> None:
    seal = _seal(calendar=_calendar("v3"))
    result = seal.guard(
        _trading_boundary(_calendar("v4"), 2025, 6, 1), boundary=ReadBoundary.RESEARCH_DOOR
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("field") == "calendar_identity"


# --- authorize_final_look ---------------------------------------------------


def test_final_look_journaled_once(store: EvidenceStore) -> None:
    seal = _seal()
    journal = _journal(store)
    writer = _writer()
    at = _instant(1_700_000_000_000_000_000)
    first = seal.authorize_final_look(journal, writer, at=at, split_id="fp1:sha256:" + "a" * 64)
    assert is_ok(first)
    assert first.value.room_role.value == "journal"
    events = journal.read_stream(SEAL_CONTROL_STREAM, for_world=World.REPLAY)
    assert is_ok(events)
    assert len(events.value) == 1
    event = events.value[0]
    assert event["event_type"] == "control action"
    assert event["control_action_subtype"] == FINAL_LOOK_SUBTYPE
    assert event["holdout_months"] == 12
    assert event["split_id"] == "fp1:sha256:" + "a" * 64


def test_second_final_look_refused(store: EvidenceStore) -> None:
    seal = _seal()
    journal = _journal(store)
    writer = _writer()
    at = _instant(1_700_000_000_000_000_000)
    assert is_ok(seal.authorize_final_look(journal, writer, at=at))
    second = seal.authorize_final_look(journal, writer, at=at)
    assert is_refusal(second)
    assert second.category is RefusalCategory.POLICY_REJECTION
    assert second.context.get("field") == "final_look"
    # The sealed set is never recycled — the seal still refuses research reads.
    still = seal.guard(
        _trading_boundary(seal.calendar_identity, 2025, 6, 1), boundary=ReadBoundary.RESEARCH_DOOR
    )
    assert is_refusal(still)


def test_final_look_records_correlation_id(store: EvidenceStore) -> None:
    seal = _seal()
    journal = _journal(store)
    writer = _writer()
    at = _instant(1_700_000_000_000_000_000)
    result = seal.authorize_final_look(journal, writer, at=at, correlation_id="corr-42")
    assert is_ok(result)
    events = journal.read_stream(SEAL_CONTROL_STREAM, for_world=World.REPLAY)
    assert is_ok(events)
    assert events.value[0]["correlation_id"] == "corr-42"
    assert "split_id" not in events.value[0]


def test_final_look_refuses_bad_arguments(store: EvidenceStore) -> None:
    seal = _seal()
    journal = _journal(store)
    writer = _writer()
    at = _instant(1)
    not_journal = seal.authorize_final_look("journal", writer, at=at)
    assert is_refusal(not_journal)
    assert not_journal.context.get("field") == "journal"
    not_writer = seal.authorize_final_look(journal, "writer", at=at)
    assert is_refusal(not_writer)
    assert not_writer.context.get("field") == "writer"
    bad_at = seal.authorize_final_look(journal, writer, at="soon")
    assert is_refusal(bad_at)
    assert bad_at.context.get("field") == "at"
    bad_split = seal.authorize_final_look(journal, writer, at=at, split_id=123)
    assert is_refusal(bad_split)
    assert bad_split.context.get("field") == "split_id"


def test_final_look_cross_world_journal_refused(store: EvidenceStore) -> None:
    # A replay-world seal handed a live-world journal: the read gate refuses cross-world.
    seal = _seal(world=World.REPLAY)
    live_journal = _journal(store, World.LIVE)
    writer = _writer()
    at = _instant(1)
    result = seal.authorize_final_look(live_journal, writer, at=at)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


# --- coercion edge cases (defensive branches) -------------------------------


def test_try_create_refuses_non_string_world() -> None:
    cal = _calendar()
    result = HoldoutSeal.try_create(
        seal_boundary=_trading_boundary(cal, 2025, 1, 1),
        calendar_identity=cal,
        world=7,
        holdout_months=12,
    )
    assert is_refusal(result)
    assert result.context.get("field") == "world"


def test_final_look_accepts_fingerprint_split_id(store: EvidenceStore) -> None:
    seal = _seal()
    journal = _journal(store)
    writer = _writer()
    at = _instant(1)
    split_fp = Fingerprint.try_create("fp1:sha256:" + "b" * 64)
    assert is_ok(split_fp)
    result = seal.authorize_final_look(journal, writer, at=at, split_id=split_fp.value)
    assert is_ok(result)
    events = journal.read_stream(SEAL_CONTROL_STREAM, for_world=World.REPLAY)
    assert is_ok(events)
    assert events.value[0]["split_id"] == "fp1:sha256:" + "b" * 64
