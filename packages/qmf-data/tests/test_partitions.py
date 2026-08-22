"""Tier-1 tests for the ``(source, instrument, time-window)`` series partition (AC5)."""

from __future__ import annotations

from qmf.core import Instant, Instrument, Interval, RefusalCategory, VenueId, is_ok, is_refusal
from qmf.data.partitions import ResolvedSeries, SeriesPartition, SeriesPlacement


def _instrument(symbol: str = "EURUSD") -> Instrument:
    venue = VenueId.try_create("dukascopy")
    assert is_ok(venue)
    built = Instrument.try_create(venue.value, symbol)
    assert is_ok(built)
    return built.value


def _window(start_ns: int, end_ns: int) -> Interval:
    start = Instant.try_create(start_ns)
    end = Instant.try_create(end_ns)
    assert is_ok(start)
    assert is_ok(end)
    interval = Interval.try_create(start.value, end.value)
    assert is_ok(interval)
    return interval.value


def _partition(source: str = "dukascopy-ticks") -> SeriesPartition:
    built = SeriesPartition.try_create(source, _instrument(), _window(1_000, 2_000))
    assert is_ok(built)
    return built.value


def test_try_create_builds_a_partition() -> None:
    part = _partition()
    assert part.source == "dukascopy-ticks"
    assert part.instrument.symbol == "EURUSD"
    assert part.window.start.value_ns == 1_000


def test_try_create_trims_source() -> None:
    built = SeriesPartition.try_create("  dukascopy-ticks  ", _instrument(), _window(1, 2))
    assert is_ok(built)
    assert built.value.source == "dukascopy-ticks"


def test_try_create_refuses_blank_source() -> None:
    for bad in ("", "   ", 42, None):
        result = SeriesPartition.try_create(bad, _instrument(), _window(1, 2))
        assert is_refusal(result)
        assert result.category is RefusalCategory.INVALID_INPUT
        assert result.context.get("field") == "source"


def test_try_create_refuses_non_instrument() -> None:
    result = SeriesPartition.try_create("src", "EURUSD", _window(1, 2))
    assert is_refusal(result)
    assert result.context.get("field") == "instrument"


def test_try_create_refuses_non_interval() -> None:
    result = SeriesPartition.try_create("src", _instrument(), (1, 2))
    assert is_refusal(result)
    assert result.context.get("field") == "window"


def test_partition_key_is_deterministic_and_legible() -> None:
    part = _partition()
    assert part.partition_key == "dukascopy-ticks | dukascopy:EURUSD | 1000-2000"
    assert _partition().partition_key == part.partition_key


def test_identity_round_trips_through_from_identity() -> None:
    part = _partition()
    rebuilt = SeriesPartition.from_identity(part.identity())
    assert is_ok(rebuilt)
    assert rebuilt.value == part


def test_identity_is_integer_only_for_time() -> None:
    identity = _partition().identity()
    assert identity["window_start_ns"] == 1_000
    assert identity["window_end_ns"] == 2_000
    assert isinstance(identity["window_start_ns"], int)
    assert identity["source"] == "dukascopy-ticks"


def test_from_identity_refuses_corrupt_parts() -> None:
    good = _partition().identity()
    # A missing venue token no longer rebuilds the instrument.
    broken_venue = {**good, "venue": ""}
    assert is_refusal(SeriesPartition.from_identity(broken_venue))
    # A blank symbol no longer rebuilds the instrument (venue still valid).
    broken_symbol = {**good, "symbol": ""}
    assert is_refusal(SeriesPartition.from_identity(broken_symbol))
    # A non-integer start is refused by Instant.
    broken_start = {**good, "window_start_ns": "soon"}
    assert is_refusal(SeriesPartition.from_identity(broken_start))
    # A start after the end no longer forms a valid interval.
    broken_window = {**good, "window_start_ns": 5_000}
    assert is_refusal(SeriesPartition.from_identity(broken_window))
    # A non-integer end is refused by Instant.
    broken_time = {**good, "window_end_ns": "later"}
    assert is_refusal(SeriesPartition.from_identity(broken_time))


def test_two_partitions_differ_by_any_axis() -> None:
    base = _partition()
    other_source = SeriesPartition.try_create("other", _instrument(), _window(1_000, 2_000))
    other_symbol = SeriesPartition.try_create(
        "dukascopy-ticks", _instrument("GBPUSD"), _window(1_000, 2_000)
    )
    other_window = SeriesPartition.try_create(
        "dukascopy-ticks", _instrument(), _window(1_000, 3_000)
    )
    assert is_ok(other_source)
    assert is_ok(other_symbol)
    assert is_ok(other_window)
    assert base != other_source.value
    assert base != other_symbol.value
    assert base != other_window.value


def test_contains_event_reads_the_half_open_window() -> None:
    part = _partition()
    inside = Instant.try_create(1_500)
    at_start = Instant.try_create(1_000)
    at_end = Instant.try_create(2_000)
    assert is_ok(inside)
    assert is_ok(at_start)
    assert is_ok(at_end)
    within = part.contains_event(inside.value)
    assert is_ok(within)
    assert within.value is True
    start_within = part.contains_event(at_start.value)
    assert is_ok(start_within)
    assert start_within.value is True
    end_within = part.contains_event(at_end.value)
    assert is_ok(end_within)
    assert end_within.value is False


def test_contains_event_refuses_non_instant() -> None:
    result = _partition().contains_event(1_500)
    assert is_refusal(result)
    assert result.context.get("field") == "event"


def test_placement_and_resolved_carry_the_partition() -> None:
    # These are plain value records; construct directly to confirm their shape.
    part = _partition()
    resolved = ResolvedSeries(partition=part, rows=({"t": 1_500},))
    assert resolved.partition == part
    assert resolved.rows[0]["t"] == 1_500
    # SeriesPlacement is exercised end-to-end in test_world_rooms; here confirm the field.
    assert SeriesPlacement.__dataclass_fields__.keys() == {"partition", "archive"}
