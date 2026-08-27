"""Independent test helpers for the Epic 3 (qmf-data) verification lane.

Builders and refusal-assertion utilities used by the epic_03 test suite. These are
authored to exercise the CT-10/CT-11/CT-12/CT-13/CT-25 boundaries from the requirements
side: every builder returns exactly what a producer/consumer of the boundary would hand
it, and the refusal helpers assert the CT-04 *category* (never a parsed message string),
per the plan's Section 7 refusal harness.

Nothing here edits or weakens a production assertion; a failing planned test is a FINDING.
"""

from __future__ import annotations

from pathlib import Path

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Duration,
    Fingerprint,
    Instant,
    Instrument,
    Interval,
    TradingDate,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data.observation import ForeignMoney, ForeignTimestamp, SourceObservation
from qmf.data.seal import HoldoutSeal
from qmf.data.splits import (
    ProducerHorizon,
    SplitBoundary,
    SplitManifest,
    SplitSegment,
)
from qmf.data.store import EvidenceStore


# --- result / refusal harness (CT-04 category, never a parsed string) -------


def unwrap(result: object) -> object:
    """Assert ``result`` is Ok and return its value, with a helpful message on refusal."""
    if is_refusal(result):
        raise AssertionError(
            f"expected Ok, got refusal category={result.category.value!r} context={result.context!r}"
        )
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def assert_refusal(result: object, category: str | None = None) -> object:
    """Assert ``result`` is a typed refusal (optionally of ``category``); return it.

    Checks the CT-04 ``category`` value and never a parsed exception/message string.
    """
    if is_ok(result):
        raise AssertionError(f"expected a typed refusal, got Ok({result.value!r})")
    assert is_refusal(result), f"expected a typed refusal, got {result!r}"
    if category is not None:
        assert result.category.value == category, (
            f"expected refusal category {category!r}, got {result.category.value!r}; "
            f"context={result.context!r}"
        )
    return result


# --- core value-type builders -----------------------------------------------


def calendar(version: str = "v3", tzdata: str = "2025a") -> CalendarIdentity:
    return unwrap(CalendarIdentity.try_create("forex-17NY", version, tzdata))


def writer(
    machine: str = "node-a",
    role: str = "data",
    stream: str = "dq",
    boot: str = "boot-1",
) -> WriterId:
    return unwrap(WriterId.try_create(machine, role, stream, boot))


def instant(value_ns: int) -> Instant:
    return unwrap(Instant.try_create(value_ns))


def civil(year: int, month: int, day: int) -> CivilDate:
    return unwrap(CivilDate.try_create(year, month, day))


def trading_date(cal: CalendarIdentity, year: int, month: int, day: int) -> TradingDate:
    return unwrap(TradingDate.try_create(cal, civil(year, month, day)))


def trading_boundary(cal: CalendarIdentity, year: int, month: int, day: int) -> SplitBoundary:
    return unwrap(SplitBoundary.try_create(trading_date(cal, year, month, day)))


def instant_boundary(value_ns: int) -> SplitBoundary:
    return unwrap(SplitBoundary.try_create(instant(value_ns)))


def venue(value: str = "cTrader") -> VenueId:
    return unwrap(VenueId.try_create(value))


def instrument(venue_id: VenueId | None = None, symbol: str = "EURUSD") -> Instrument:
    return unwrap(Instrument.try_create(venue_id if venue_id is not None else venue(), symbol))


def interval(start_ns: int, end_ns: int) -> Interval:
    return unwrap(Interval.try_create(instant(start_ns), instant(end_ns)))


def duration(value_ns: int) -> Duration:
    return Duration(value_ns=value_ns)


def fp(hex_char: str = "0") -> Fingerprint:
    """A syntactically-valid fp1 fingerprint (for presented-fp / collision tests)."""
    return unwrap(Fingerprint.try_create("fp1:sha256:" + (hex_char * 64)))


# --- store ------------------------------------------------------------------


def make_store(root: Path, *, rotation_bytes: int = 256, seal: object | None = None) -> EvidenceStore:
    return EvidenceStore(root / "store", rotation_bytes=rotation_bytes, seal=seal)


# --- CT-10 source observation -----------------------------------------------


def observation(
    *,
    event_time: object = 1_000,
    known_at: object = 2_000,
    source: object = "dukascopy",
    source_native_id: object = "occ-1",
    revision: object = "r1",
    receive_wall_time: object = 2_500,
    writer_id: object | None = None,
    sequence: object = 0,
    world: object = World.LIVE,
    foreign_timestamp: object | None = None,
    foreign_money: object | None = None,
    correction_of: object | None = None,
) -> object:
    """Build a SourceObservation via try_create, returning the Result (Ok or refusal)."""
    return SourceObservation.try_create(
        event_time=event_time,
        known_at=known_at,
        source=source,
        source_native_id=source_native_id,
        revision=revision,
        receive_wall_time=receive_wall_time,
        writer=writer_id if writer_id is not None else writer(),
        sequence=sequence,
        world=world,
        foreign_timestamp=foreign_timestamp,
        foreign_money=foreign_money,
        correction_of=correction_of,
    )


def foreign_timestamp(
    verbatim: str = "2025-01-02T03:04:05.123",
    zone: str = "Europe/Zurich",
    offset: str = "+01:00",
    resolution: str = "milliseconds",
) -> ForeignTimestamp:
    return unwrap(ForeignTimestamp.try_create(verbatim, zone, offset, resolution))


def foreign_money(verbatim: int = 123456, scale: int = 5) -> ForeignMoney:
    return unwrap(ForeignMoney.try_create(verbatim, scale))


# --- CT-12 splits + seal ----------------------------------------------------


def instant_manifest(
    cal: CalendarIdentity | None = None,
    *,
    world: World = World.REPLAY,
    train_end_ns: int = 1_000_000,
    validation_end_ns: int = 2_000_000,
    sealed_end_ns: int = 3_000_000,
    seal_boundary_ns: int = 2_000_000,
    purge_ns: int = 0,
    embargo_ns: int = 0,
    producers: tuple[ProducerHorizon, ...] = (),
) -> object:
    """Build a default 3-segment instant-boundary manifest; returns the Result."""
    cal = cal if cal is not None else calendar()
    segments = unwrap(
        SplitManifest.default_split_segments(
            [
                instant_boundary(train_end_ns),
                instant_boundary(validation_end_ns),
                instant_boundary(sealed_end_ns),
            ]
        )
    )
    return SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments,
        seal_boundary=instant_boundary(seal_boundary_ns),
        purge_width=duration(purge_ns),
        embargo_width=duration(embargo_ns),
        world=world,
        cited_producers=producers,
    )


def trading_seal(
    cal: CalendarIdentity | None = None,
    *,
    world: World = World.REPLAY,
    year: int = 2025,
    month: int = 1,
    day: int = 1,
    months: int = 12,
) -> object:
    """Build a HoldoutSeal at a frozen trading-date boundary; returns the Result."""
    cal = cal if cal is not None else calendar()
    return HoldoutSeal.try_create(
        seal_boundary=trading_boundary(cal, year, month, day),
        calendar_identity=cal,
        world=world,
        holdout_months=months,
    )


def instant_seal(
    *,
    world: World = World.LIVE,
    seal_ns: int = 1_000_000,
    months: int = 12,
    cal: CalendarIdentity | None = None,
) -> object:
    """A seal whose frozen boundary is an Instant (calendar-neutral position guarding)."""
    cal = cal if cal is not None else calendar()
    return HoldoutSeal.try_create(
        seal_boundary=instant_boundary(seal_ns),
        calendar_identity=cal,
        world=world,
        holdout_months=months,
    )
