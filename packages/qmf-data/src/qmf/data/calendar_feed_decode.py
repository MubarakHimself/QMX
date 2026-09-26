"""Decode a FairEconomy-shaped news-calendar snapshot into CalendarEvent values."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from types import MappingProxyType
from typing import cast

from qmf.core import Ok, Result, is_refusal
from qmf.data.calendar_feed_types import (
    CALENDAR_FEED_SOURCE,
    CalendarEvent,
)
from qmf.data.store.refusals import invalid_input


def clean_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def offset_string(dt: datetime) -> str:
    """ISO-8601 offset token for a timezone-aware datetime."""
    offset = dt.utcoffset()
    if offset is None:
        return "+00:00"
    total = int(offset.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def parse_event_time_ns(raw: object) -> Result[tuple[int, dict[str, object]]]:
    """Parse a provider date string into UTC ns + verbatim foreign timestamp."""
    verbatim = clean_str(raw)
    if verbatim is None:
        return invalid_input(
            "date",
            "a calendar event carries a non-empty provider date/time string",
            given=repr(raw),
        )
    text = verbatim
    # Provider samples use offset forms like 2026-08-16T18:30:00-04:00.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return invalid_input(
            "date",
            "calendar event date must parse as an ISO-8601 timestamp with zone/offset",
            given=verbatim,
        )
    if dt.tzinfo is None:
        return invalid_input(
            "date",
            "calendar event date must carry a declared zone/offset; naive civil times "
            "are refused (DEC-0106)",
            given=verbatim,
        )
    utc = dt.astimezone(timezone.utc)
    foreign: dict[str, object] = {
        "verbatim": verbatim,
        "zone": "provider-declared",
        "offset": offset_string(dt),
        "resolution": "seconds",
    }
    return Ok((int(utc.timestamp() * 1_000_000_000), foreign))


def opaque_native_id(title: str, currency: str, date_verbatim: str) -> str:
    """Opaque provider-native id when the feed omits a stable id field.

    Built from provider fields only — never parsed into trading-symbol scope.
    """
    return f"{currency}|{date_verbatim}|{title}"


def decode_calendar_snapshot(
    payload: object,
    *,
    known_at_ns: object,
    revision: object = "r1",
    source: object = CALENDAR_FEED_SOURCE,
) -> Result[tuple[CalendarEvent, ...]]:
    """Decode a FairEconomy-shaped JSON snapshot into :class:`CalendarEvent` values.

    Accepts ``bytes`` / ``str`` JSON, or an already-parsed list of event mappings.
    Impact labels are kept verbatim; no severity enum is minted (AC2).
    """
    header = calendar_snapshot_header(source, revision, known_at_ns)
    if is_refusal(header):
        return header
    clean_source, clean_revision, known_at = header.value
    items = calendar_snapshot_items(payload)
    if is_refusal(items):
        return items
    events: list[CalendarEvent] = []
    for index, raw in enumerate(items.value):
        decoded = decode_one_calendar_event(
            raw,
            index=index,
            source=clean_source,
            revision=clean_revision,
            known_at_ns=known_at,
        )
        if is_refusal(decoded):
            return decoded
        events.append(decoded.value)
    return Ok(tuple(events))


def calendar_snapshot_header(
    source: object, revision: object, known_at_ns: object
) -> Result[tuple[str, str, int]]:
    clean_source = clean_str(source)
    if clean_source is None:
        return invalid_input(
            "source",
            "calendar decode names a non-empty read-only source",
            given=repr(source),
        )
    if clean_source != CALENDAR_FEED_SOURCE:
        return invalid_input(
            "source",
            "COMP-CALENDAR-FEED serves source 'news-calendar' only",
            given=clean_source,
        )
    clean_revision = clean_str(revision)
    if clean_revision is None:
        return invalid_input(
            "revision",
            "revision is required: the provider's revision token; a new revision is a new artifact",
            given=repr(revision),
        )
    if isinstance(known_at_ns, bool) or not isinstance(known_at_ns, int):
        return invalid_input(
            "known_at_ns",
            "known_at_ns is required: int64 UTC-ns when the snapshot became knowable",
            given=repr(known_at_ns),
        )
    return Ok((clean_source, clean_revision, known_at_ns))


def calendar_snapshot_items(payload: object) -> Result[list[object]]:
    items: object
    if isinstance(payload, (bytes, bytearray)):
        try:
            items = json.loads(bytes(payload).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return invalid_input(
                "payload",
                "calendar snapshot must be UTF-8 JSON; malformed bytes are invalid input",
            )
    elif isinstance(payload, str):
        try:
            items = json.loads(payload)
        except json.JSONDecodeError:
            return invalid_input(
                "payload",
                "calendar snapshot must be JSON; malformed text is invalid input",
            )
    else:
        items = payload
    if not isinstance(items, list):
        return invalid_input(
            "payload",
            "a calendar snapshot is a JSON array of event objects",
            given=repr(type(items)),
        )
    return Ok(cast("list[object]", items))


def event_provider_fields(
    block: Mapping[str, object], *, index: int
) -> Result[tuple[str, str, str, object]]:
    """Extract verbatim title, currency, impact, and date from one provider row."""
    title = clean_str(block.get("title") or block.get("Title")) or ""
    currency = clean_str(block.get("country") or block.get("Country") or block.get("currency"))
    if currency is None:
        return invalid_input(
            "country",
            "a calendar event carries a non-empty provider currency/country token",
            index=index,
        )
    impact = clean_str(block.get("impact") or block.get("Impact"))
    if impact is None:
        return invalid_input(
            "impact",
            "a calendar event carries the provider's impact label verbatim",
            index=index,
        )
    date_raw = block.get("date") or block.get("Date")
    return Ok((title, currency, impact, date_raw))


def decode_one_calendar_event(
    raw: object,
    *,
    index: int,
    source: str,
    revision: str,
    known_at_ns: int,
) -> Result[CalendarEvent]:
    if not isinstance(raw, Mapping):
        return invalid_input(
            "event",
            "each calendar snapshot item is a mapping of provider fields",
            index=index,
            given=repr(raw),
        )
    block = cast("Mapping[str, object]", raw)
    fields = event_provider_fields(block, index=index)
    if is_refusal(fields):
        return fields
    title, currency, impact, date_raw = fields.value
    parsed = parse_event_time_ns(date_raw)
    if is_refusal(parsed):
        return parsed
    event_ns, foreign = parsed.value
    native = clean_str(block.get("id") or block.get("source_native_id"))
    if native is None:
        native = opaque_native_id(title, currency, str(date_raw))
    return Ok(
        CalendarEvent(
            source=source,
            source_native_id=native,
            revision=revision,
            event_time_ns=event_ns,
            known_at_ns=known_at_ns,
            impact_label=impact,
            currency=currency,
            title=title,
            foreign_timestamp=MappingProxyType(foreign),
        )
    )
