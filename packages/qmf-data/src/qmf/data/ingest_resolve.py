"""CT-15 provider-record field resolvers for instrument, foreign blocks, and ticks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from qmf.core import Instrument, Ok, Result, VenueId, is_refusal
from qmf.data.ingest_types import ProviderRecord, invalid_field
from qmf.data.observation import ForeignMoney, ForeignTimestamp
from qmf.data.ticks import TickQuote, refuse_mid_merge


def resolve_instrument(value: object) -> Result[Instrument]:
    """Require a CT-03 :class:`~qmf.core.Instrument` mapping (AC4 / FM-6)."""
    if isinstance(value, Instrument):
        return Instrument.try_create(value.venue, value.symbol)
    if isinstance(value, Mapping):
        return _instrument_from_mapping(cast("Mapping[str, object]", value))
    return invalid_field(
        "instrument",
        "a source record must map to a CT-03 Instrument (venue, opaque symbol); "
        "without that mapping no CT-10 observation is emitted (FM-6)",
        given=repr(value),
    )


def _instrument_from_mapping(block: Mapping[str, object]) -> Result[Instrument]:
    venue = block.get("venue")
    symbol = block.get("symbol")
    if isinstance(venue, VenueId):
        return Instrument.try_create(venue, symbol)
    if isinstance(venue, str):
        venue_id = VenueId.try_create(venue)
        if is_refusal(venue_id):
            return invalid_field(
                "instrument",
                "a source record must map to a CT-03 Instrument (venue, opaque "
                "symbol); without that mapping no CT-10 observation is emitted "
                "(FM-6)",
                given=repr(block),
            )
        return Instrument.try_create(venue_id.value, symbol)
    return invalid_field(
        "instrument",
        "a source record must map to a CT-03 Instrument (venue, opaque symbol); "
        "without that mapping no CT-10 observation is emitted (FM-6)",
        given=repr(block),
    )


def resolve_optional_foreign_timestamp(
    value: object | None,
) -> Result[ForeignTimestamp | None]:
    """Pass through / build a verbatim foreign timestamp, or refuse a malformed block."""
    if value is None:
        return Ok(None)
    if isinstance(value, ForeignTimestamp):
        return Ok(value)
    if isinstance(value, Mapping):
        block = cast("Mapping[str, object]", value)
        built = ForeignTimestamp.try_create(
            block.get("verbatim"),
            block.get("zone"),
            block.get("offset"),
            block.get("resolution"),
        )
        if is_refusal(built):
            return built
        resolved: ForeignTimestamp | None = built.value
        return Ok(resolved)
    return invalid_field(
        "foreign_timestamp",
        "foreign timestamp is a ForeignTimestamp or a mapping of "
        "verbatim/zone/offset/resolution (or omitted)",
        given=repr(value),
    )


def resolve_optional_foreign_money(value: object | None) -> Result[ForeignMoney | None]:
    """Pass through / build verbatim foreign money at the source scale, or refuse."""
    if value is None:
        return Ok(None)
    if isinstance(value, ForeignMoney):
        return Ok(value)
    if isinstance(value, Mapping):
        block = cast("Mapping[str, object]", value)
        built = ForeignMoney.try_create(block.get("verbatim"), block.get("scale"))
        if is_refusal(built):
            return built
        resolved: ForeignMoney | None = built.value
        return Ok(resolved)
    return invalid_field(
        "foreign_money",
        "foreign money is a ForeignMoney or a mapping of verbatim/scale (or omitted)",
        given=repr(value),
    )


def resolve_optional_tick_quote(record: ProviderRecord) -> Result[TickQuote | None]:
    """Build a :class:`TickQuote` when bid/ask are present; refuse a mid (Story 6.2).

    A record with neither side is a non-tick fact (news calendar, etc.) and returns
    ``None``. Either side alone, or a presented mid, is refused — sides stay paired
    and never collapsed.
    """
    if record.mid is not None:
        return refuse_mid_merge(given=record.mid)
    has_bid = record.bid is not None
    has_ask = record.ask is not None
    if not has_bid and not has_ask:
        if record.bid_timestamp is not None or record.ask_timestamp is not None:
            return invalid_field(
                "bid",
                "per-side source timestamps require both bid and ask; tick sides are "
                "never partial (DEC-0119)",
            )
        return Ok(None)
    if has_bid != has_ask:
        return invalid_field(
            "bid" if not has_bid else "ask",
            "tick observations preserve bid and ask together — one side alone is "
            "invalid input (DEC-0119, DEC-0105)",
            bid=repr(record.bid),
            ask=repr(record.ask),
        )
    built = TickQuote.try_create(
        bid=record.bid,
        ask=record.ask,
        bid_timestamp=record.bid_timestamp,
        ask_timestamp=record.ask_timestamp,
        mid=record.mid,
    )
    if is_refusal(built):
        return built
    resolved: TickQuote | None = built.value
    return Ok(resolved)
