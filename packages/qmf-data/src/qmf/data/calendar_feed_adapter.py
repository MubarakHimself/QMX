"""CT-15 news-calendar adapter — provider-native identity, verbatim impact."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Protocol

from qmf.core import (
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    is_refusal,
)
from qmf.data.calendar_feed_decode import clean_str, decode_calendar_snapshot
from qmf.data.calendar_feed_types import (
    CALENDAR_FEED_SOURCE,
    CALENDAR_FEED_VENUE,
    CalendarEvent,
    refuse_authorized_retention_claim,
    refuse_live_skip,
    refuse_minted_severity_scale,
)
from qmf.data.ingest import ProviderRecord, SourceRequest
from qmf.data.store.refusals import invalid_input


class CalendarFeedTransport(Protocol):
    """Injected byte source for one news-calendar snapshot (AC1, AC4).

    Production wires the standalone recorder / HTTPS client; tests inject fixtures.
    An unreachable provider is ``unavailable dependency``; a rate-limit is
    ``transient venue failure``.
    """

    def fetch_snapshot(self, bounds: Mapping[str, object], /) -> Result[bytes]:
        """Return raw snapshot bytes for ``bounds``, or a typed refusal."""
        ...


def currency_instrument(currency: str, instruments: Mapping[str, Instrument]) -> Result[Instrument]:
    """Resolve a CT-03 instrument for the event's opaque currency token."""
    key = currency.strip().upper()
    found = instruments.get(key) or instruments.get(currency)
    if found is not None:
        return Ok(found)
    venue = VenueId.try_create(CALENDAR_FEED_VENUE)
    if is_refusal(venue):
        return venue
    return Instrument.try_create(venue.value, key)


class CalendarFeedAdapter:
    """CT-15 news-calendar adapter — provider-native identity, verbatim impact.

    Constructed with an injected :class:`CalendarFeedTransport` and an optional
    currency→:class:`~qmf.core.Instrument` map. Implements the ingest
    :class:`~qmf.data.ingest.ExternalSourcePort` ``fetch`` shape. Does not schedule,
    does not define windows, and does not claim retention authorization.
    """

    def __init__(
        self,
        transport: CalendarFeedTransport,
        *,
        instruments: Mapping[str, Instrument] | None = None,
    ) -> None:
        self._transport = transport
        self._instruments = {
            code.strip().upper(): instrument for code, instrument in (instruments or {}).items()
        }
        self._last_events: tuple[CalendarEvent, ...] = ()

    @property
    def source(self) -> str:
        return CALENDAR_FEED_SOURCE

    @property
    def last_events(self) -> tuple[CalendarEvent, ...]:
        """Events from the most recent successful fetch, with verbatim impact."""
        return self._last_events

    def mint_severity_scale(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — QMX mints no severity scale (AC2)."""
        return refuse_minted_severity_scale(request="mint_severity_scale")

    def claim_retention_authorized(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — legal archiving stays an open operator item (AC5)."""
        return refuse_authorized_retention_claim(request="claim_retention_authorized")

    def live_skip(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — no live skip button (AC4)."""
        return refuse_live_skip(request="live_skip")

    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        """Fetch one snapshot and emit CT-15 :class:`ProviderRecord` values (AC1).

        Required bounds: ``known_at_ns``. Optional: ``revision`` (default ``r1``).
        """
        header = self._fetch_header(request)
        if is_refusal(header):
            return header
        known_at, revision, bounds = header.value
        fetched = self._fetch_snapshot_bytes(bounds)
        if is_refusal(fetched):
            return fetched
        decoded = decode_calendar_snapshot(
            fetched.value,
            known_at_ns=known_at,
            revision=revision,
            source=CALENDAR_FEED_SOURCE,
        )
        if is_refusal(decoded):
            return decoded
        records = self._records_from_events(decoded.value)
        if is_refusal(records):
            return records
        self._last_events = decoded.value
        return Ok(tuple(records.value))

    def _fetch_header(self, request: SourceRequest) -> Result[tuple[int, str, dict[str, object]]]:
        if request.source != CALENDAR_FEED_SOURCE:
            return invalid_input(
                "source",
                "CalendarFeedAdapter serves source 'news-calendar' only",
                given=request.source,
            )
        bounds = dict(request.bounds)
        known_at = bounds.get("known_at_ns")
        if isinstance(known_at, bool) or not isinstance(known_at, int):
            return invalid_input(
                "known_at_ns",
                "bounds.known_at_ns is required: int64 UTC-ns when the snapshot became knowable",
                given=repr(known_at),
            )
        revision = clean_str(bounds.get("revision")) or "r1"
        return Ok((known_at, revision, bounds))

    def _fetch_snapshot_bytes(self, bounds: dict[str, object]) -> Result[bytes]:
        try:
            fetched = self._transport.fetch_snapshot(MappingProxyType(bounds))
        except Exception as exc:  # R-007: returned, never raised across CT-15
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.YES,
                context={
                    "field": "transport",
                    "reason": (
                        "the injected calendar transport raised instead of returning; a "
                        "boundary failure is returned as a typed refusal, never raised "
                        "across the CT-15 boundary, so the outage reaches the fail-closed "
                        "data-quality journal (R-007, CT-04, 6.4-AC1)"
                    ),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
        return fetched

    def _records_from_events(
        self, events: tuple[CalendarEvent, ...]
    ) -> Result[list[ProviderRecord]]:
        records: list[ProviderRecord] = []
        for event in events:
            instrument = currency_instrument(event.currency, self._instruments)
            if is_refusal(instrument):
                return invalid_input(
                    "instrument",
                    "calendar currency cannot map to a CT-03 Instrument; no evidence "
                    "is emitted (FM-6, DEC-0107)",
                    currency=event.currency,
                )
            records.append(event.to_provider_record(instrument.value))
        return Ok(records)
