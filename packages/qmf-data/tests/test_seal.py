"""Tier-1 tests for the CT-12 no-peek seal (Story 3.4; AC4, AC5, AC6)."""

from __future__ import annotations

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Fingerprint,
    Instant,
    RefusalCategory,
    TradingDate,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data.seal import (
    FINAL_LOOK_SUBTYPE,
    SEAL_CONTROL_STREAM,
    HoldoutSeal,
    ReadBoundary,
)
from qmf.data.splits import ProducerHorizon, SplitBoundary, SplitManifest
from qmf.data.store import EvidenceStore, JournalStore


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


def test_guard_refuses_sealed_read_at_every_boundary() -> None:
    cal = _calendar()
    seal = _seal(calendar=cal)
    sealed_position = _trading_boundary(cal, 2025, 6, 1)
    for boundary in ReadBoundary:
        result = seal.guard(sealed_position, boundary=boundary)
        assert is_refusal(result)
        assert result.category is RefusalCategory.POLICY_REJECTION
        assert result.context.get("boundary") == boundary.value
    # Every named read boundary is covered (raw, processed, research door, restored backup).
    assert {member.value for member in ReadBoundary} == {
        "raw archive",
        "processed",
        "split-governed research door",
        "restored backup",
    }


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
