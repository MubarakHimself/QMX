"""COMP-CALENDAR-FEED — news-calendar CT-15 provider with fail-closed degradation.

Story 6.4. Distinct from the market-hours calendar and the day-boundary calendar
(DEC-0106). This module is QMF-authored adapter surface for the external
news-calendar feed consumed by the standalone recorder: provider-native identity
and revisions through idempotent ``(source, source-native id, revision)`` intake,
verbatim impact labels (QMX mints no severity scale), every import journaled as a
CT-13 ``data quality`` event, and fail-closed degradation on failed refresh /
unknown coverage / missing per-instrument currency-exposure — treated-as-affected
downstream, no live skip button. The feed defines no blackout window and holds no
permission; CT-31 owns that. Legal archiving/retention stays an open operator
item — this adapter never claims operational retention is authorized (DEC-0119,
DEC-0052, DEC-0152).

Transport bytes are injected (:class:`CalendarFeedTransport`) so tests never hit
the live CDN. Stdlib + qmf-core + the CT-15 ingest / CT-13 journal types already
in this package.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    Instrument,
    Ok,
    Result,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    is_refusal,
)
from qmf.data.ingest import (
    ExternalSourceIngest,
    IntakeOutcome,
    IntakeReceipt,
    ProviderRecord,
    SourceRequest,
)
from qmf.data.journal_producer import JournalAppendReceipt, JournalWriter
from qmf.data.source_boundary import ObservationReceipt, SourceObservationBoundary
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CALENDAR_FEED_SOURCE",
    "CALENDAR_FEED_VENUE",
    "CONTRACT_FORMAT_VERSION",
    "LEGAL_ARCHIVING_POSTURE",
    "CalendarEvent",
    "CalendarFeedAdapter",
    "CalendarFeedImport",
    "CalendarFeedTransport",
    "CalendarImportReceipt",
    "FailClosedReason",
    "FailClosedSignal",
    "decode_calendar_snapshot",
    "fail_closed",
    "journal_fail_closed",
    "journal_import",
    "refuse_authorized_retention_claim",
    "refuse_live_skip",
    "refuse_minted_severity_scale",
]

# Story 6.4 vocabulary format version — meaning never mutates in place (L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

# Read-only provenance noun for this provider (DEC-0117) — never a VenueId.
CALENDAR_FEED_SOURCE: Final[str] = "news-calendar"

# CT-03 venue used only to host opaque currency-code instruments for event evidence.
# Scope for blackouts is CT-31 currency-exposure records, never this symbol.
CALENDAR_FEED_VENUE: Final[str] = "news-calendar"

# DEC-0119 / FM-3: legal archiving posture is an open operator item — recorded,
# never resolved, never claimed authorized by this adapter.
LEGAL_ARCHIVING_POSTURE: Final[str] = "open-operator-item"

_EMPTY: Final[Mapping[str, object]] = MappingProxyType({})


# --- fail-closed vocabulary -------------------------------------------------


class FailClosedReason(StrEnum):
    """Visible degradation reasons that must fail closed (AC4 / SCN-0008).

    Downstream CT-31 treats the instrument as affected (blocks new entries). The
    feed itself supplies no permission and no live skip (FM-4, DEC-0152).
    """

    FAILED_REFRESH = "failed-refresh"
    UNKNOWN_COVERAGE = "unknown-coverage"
    MISSING_CURRENCY_EXPOSURE = "missing-currency-exposure"


@dataclass(frozen=True, slots=True)
class FailClosedSignal:
    """A journaled, alarmed, treated-as-affected degradation signal (AC4).

    Always ``treated_as_affected=True`` and ``alarm=True``. There is no live skip
    button — :func:`refuse_live_skip` is the only answer to a skip ask.
    """

    reason: FailClosedReason
    detail: Mapping[str, object] = field(default_factory=lambda: _EMPTY)
    treated_as_affected: bool = True
    alarm: bool = True
    format_version: int = CONTRACT_FORMAT_VERSION

    def to_payload(self) -> dict[str, object]:
        """CT-13 data-quality payload for this signal."""
        payload: dict[str, object] = {
            "signal": "calendar-fail-closed",
            "reason": self.reason.value,
            "treated_as_affected": True,
            "alarm": True,
            "source": CALENDAR_FEED_SOURCE,
            "component": "COMP-CALENDAR-FEED",
            "contract": "CT-15",
            "legal_archiving_posture": LEGAL_ARCHIVING_POSTURE,
            "format_version": self.format_version,
        }
        payload.update(dict(self.detail))
        return payload


def fail_closed(
    reason: object,
    *,
    detail: Mapping[str, object] | None = None,
) -> Result[FailClosedSignal]:
    """Build a fail-closed signal, or refuse an unknown reason token."""
    if isinstance(reason, FailClosedReason):
        resolved = reason
    elif isinstance(reason, str):
        try:
            resolved = FailClosedReason(reason)
        except ValueError:
            return invalid_input(
                "reason",
                "fail-closed reason must be failed-refresh | unknown-coverage | "
                "missing-currency-exposure (AC4, SCN-0008)",
                given=repr(reason),
            )
    else:
        return invalid_input(
            "reason",
            "fail-closed reason must be a FailClosedReason or its wire token",
            given=repr(reason),
        )
    det: Mapping[str, object] = _EMPTY if detail is None else MappingProxyType(dict(detail))
    return Ok(FailClosedSignal(reason=resolved, detail=det))


def refuse_live_skip(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse any ask for a live skip around fail-closed calendar degradation (AC4).

    SCN-0008 / DEC-0152: there is no live skip button; operator control is upstream
    configuration between sessions.
    """
    context: dict[str, object] = {
        "signal": "refuse-live-skip",
        "component": "COMP-CALENDAR-FEED",
        "contract": "CT-15",
        "treated_as_affected": True,
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "skip",
        "a failed calendar refresh, unknown coverage, or missing currency-exposure "
        "fails closed with no live skip button — treated-as-affected downstream "
        "(AC4, FM-4, DEC-0152, SCN-0008)",
        **context,
    )


def refuse_minted_severity_scale(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse minting a QMX severity scale over provider impact labels (AC2).

    Provider impact labels are stored verbatim; severity-to-window is a declared
    node mapping outside this feed (DEC-0152, DEC-0156).
    """
    context: dict[str, object] = {
        "signal": "refuse-minted-severity",
        "component": "COMP-CALENDAR-FEED",
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "severity",
        "QMX mints no severity scale of its own in V1 — provider impact labels are "
        "stored verbatim; severity-to-window is a declared node mapping, not this "
        "feed (AC2, DEC-0152, DEC-0156)",
        **context,
    )


def refuse_authorized_retention_claim(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse claiming operational retention is authorized (AC5 / FM-3).

    Legal archiving/retention posture remains an open operator item (DEC-0119).
    """
    context: dict[str, object] = {
        "signal": "refuse-authorized-retention",
        "component": "COMP-CALENDAR-FEED",
        "legal_archiving_posture": LEGAL_ARCHIVING_POSTURE,
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "retention",
        "news-calendar legal archiving/retention is an open operator item — this "
        "adapter does not claim operational retention is authorized (AC5, FM-3, "
        "DEC-0119, DEC-0052)",
        **context,
    )


# --- event evidence ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """One news-calendar event as governed source evidence (AC1, AC2).

    Carries event-time, known-at, source, and revision. ``impact_label`` is the
    provider's label stored verbatim — never remapped to a QMX severity. ``currency``
    is the provider's opaque currency/country token for CT-31 exposure lookup; this
    value defines no window and holds no permission.
    """

    source: str
    source_native_id: str
    revision: str
    event_time_ns: int
    known_at_ns: int
    impact_label: str
    currency: str
    title: str
    foreign_timestamp: Mapping[str, object] | None = None
    format_version: int = CONTRACT_FORMAT_VERSION

    def to_provider_record(self, instrument: Instrument) -> ProviderRecord:
        """CT-15 :class:`ProviderRecord` for idempotent intake (AC1)."""
        return ProviderRecord(
            source=self.source,
            source_native_id=self.source_native_id,
            revision=self.revision,
            event_time=self.event_time_ns,
            known_at=self.known_at_ns,
            instrument=instrument,
            foreign_timestamp=dict(self.foreign_timestamp)
            if self.foreign_timestamp is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class CalendarImportReceipt:
    """Receipt of one journaled news-calendar import (AC1–AC5).

    ``legal_archiving_posture`` is always :data:`LEGAL_ARCHIVING_POSTURE` — open,
    never claimed authorized.
    """

    events: tuple[CalendarEvent, ...]
    intake_receipts: tuple[IntakeReceipt, ...]
    journal_receipt: JournalAppendReceipt
    legal_archiving_posture: str = LEGAL_ARCHIVING_POSTURE
    format_version: int = CONTRACT_FORMAT_VERSION


# --- decode -----------------------------------------------------------------


def _clean_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _parse_event_time_ns(raw: object) -> Result[tuple[int, dict[str, object]]]:
    """Parse a provider date string into UTC ns + verbatim foreign timestamp."""
    verbatim = _clean_str(raw)
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
    offset = dt.utcoffset()
    if offset is None:
        offset_str = "+00:00"
    else:
        total = int(offset.total_seconds())
        sign = "+" if total >= 0 else "-"
        total = abs(total)
        hours, rem = divmod(total, 3600)
        minutes = rem // 60
        offset_str = f"{sign}{hours:02d}:{minutes:02d}"
    foreign: dict[str, object] = {
        "verbatim": verbatim,
        "zone": "provider-declared",
        "offset": offset_str,
        "resolution": "seconds",
    }
    return Ok((int(utc.timestamp() * 1_000_000_000), foreign))


def _opaque_native_id(title: str, currency: str, date_verbatim: str) -> str:
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
    clean_source = _clean_str(source)
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
    clean_revision = _clean_str(revision)
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

    events: list[CalendarEvent] = []
    for index, raw in enumerate(cast("list[object]", items)):
        if not isinstance(raw, Mapping):
            return invalid_input(
                "event",
                "each calendar snapshot item is a mapping of provider fields",
                index=index,
                given=repr(raw),
            )
        block = cast("Mapping[str, object]", raw)
        title = _clean_str(block.get("title") or block.get("Title")) or ""
        currency = _clean_str(block.get("country") or block.get("Country") or block.get("currency"))
        if currency is None:
            return invalid_input(
                "country",
                "a calendar event carries a non-empty provider currency/country token",
                index=index,
            )
        impact = _clean_str(block.get("impact") or block.get("Impact"))
        if impact is None:
            return invalid_input(
                "impact",
                "a calendar event carries the provider's impact label verbatim",
                index=index,
            )
        date_raw = block.get("date") or block.get("Date")
        parsed = _parse_event_time_ns(date_raw)
        if is_refusal(parsed):
            return parsed
        event_ns, foreign = parsed.value
        native = _clean_str(block.get("id") or block.get("source_native_id"))
        if native is None:
            native = _opaque_native_id(title, currency, str(date_raw))
        events.append(
            CalendarEvent(
                source=clean_source,
                source_native_id=native,
                revision=clean_revision,
                event_time_ns=event_ns,
                known_at_ns=known_at_ns,
                impact_label=impact,
                currency=currency,
                title=title,
                foreign_timestamp=MappingProxyType(foreign),
            )
        )
    return Ok(tuple(events))


# --- transport / adapter ----------------------------------------------------


class CalendarFeedTransport(Protocol):
    """Injected byte source for one news-calendar snapshot (AC1, AC4).

    Production wires the standalone recorder / HTTPS client; tests inject fixtures.
    An unreachable provider is ``unavailable dependency``; a rate-limit is
    ``transient venue failure``.
    """

    def fetch_snapshot(self, bounds: Mapping[str, object], /) -> Result[bytes]:
        """Return raw snapshot bytes for ``bounds``, or a typed refusal."""
        ...


def _currency_instrument(
    currency: str, instruments: Mapping[str, Instrument]
) -> Result[Instrument]:
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
        revision = _clean_str(bounds.get("revision")) or "r1"

        fetched = self._transport.fetch_snapshot(MappingProxyType(bounds))
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

        records: list[ProviderRecord] = []
        for event in decoded.value:
            instrument = _currency_instrument(event.currency, self._instruments)
            if is_refusal(instrument):
                return invalid_input(
                    "instrument",
                    "calendar currency cannot map to a CT-03 Instrument; no evidence "
                    "is emitted (FM-6, DEC-0107)",
                    currency=event.currency,
                )
            records.append(event.to_provider_record(instrument.value))

        self._last_events = decoded.value
        return Ok(tuple(records))


# --- journalled import ------------------------------------------------------


def journal_import(
    writer: JournalWriter,
    *,
    instant: object,
    events: Sequence[CalendarEvent],
    intake_receipts: Sequence[IntakeReceipt] | None = None,
    extra: Mapping[str, object] | None = None,
) -> Result[JournalAppendReceipt]:
    """Journal one news-calendar import as a CT-13 ``data quality`` event (AC3)."""
    produced = 0
    idempotent = 0
    if intake_receipts is not None:
        for receipt in intake_receipts:
            if receipt.outcome is IntakeOutcome.PRODUCED:
                produced += 1
            else:
                idempotent += 1
    payload: dict[str, object] = {
        "signal": "calendar-import",
        "source": CALENDAR_FEED_SOURCE,
        "component": "COMP-CALENDAR-FEED",
        "contract": "CT-15",
        "event_type_wire": "data quality",
        "event_count": len(events),
        "produced_count": produced,
        "idempotent_count": idempotent,
        "impact_labels": [event.impact_label for event in events],
        "currencies": sorted({event.currency for event in events}),
        "legal_archiving_posture": LEGAL_ARCHIVING_POSTURE,
        "defines_window": False,
        "holds_permission": False,
        "format_version": CONTRACT_FORMAT_VERSION,
    }
    if extra is not None:
        payload.update(dict(extra))
    return writer.record_data_quality(payload, instant=instant)


def journal_fail_closed(
    writer: JournalWriter,
    signal: FailClosedSignal,
    *,
    instant: object,
) -> Result[JournalAppendReceipt]:
    """Journal a fail-closed degradation as a CT-13 ``data quality`` event (AC4)."""
    return writer.record_data_quality(signal.to_payload(), instant=instant)


class CalendarFeedImport:
    """Standalone-recorder-facing import: fetch → intake → journal (AC1–AC5).

    Scheduling stays outside this class — the application drives each call. On
    transport failure / unknown coverage / missing currency-exposure the import
    journals a fail-closed data-quality event and returns the signal; it never
    fabricates permission to trade.
    """

    def __init__(
        self,
        adapter: CalendarFeedAdapter,
        ingest: ExternalSourceIngest,
        journal: JournalWriter,
        *,
        currency_exposures: Mapping[str, object] | None = None,
    ) -> None:
        self._adapter = adapter
        self._ingest = ingest
        self._journal = journal
        # Presence of a key means exposure is known; absence → fail closed.
        self._exposures = {
            code.strip().upper(): value for code, value in (currency_exposures or {}).items()
        }

    @property
    def legal_archiving_posture(self) -> str:
        return LEGAL_ARCHIVING_POSTURE

    def run(
        self,
        request: SourceRequest,
        *,
        writer: WriterId,
        world: World,
        receive_wall_time: object,
        journal_instant: object,
        sequence_start: int = 0,
        boundary: SourceObservationBoundary | None = None,
        require_exposures_for: Sequence[str] | None = None,
        coverage_known: bool = True,
    ) -> Result[CalendarImportReceipt | FailClosedSignal]:
        """Run one import; on degradation return a journaled fail-closed signal.

        Success yields :class:`CalendarImportReceipt` (import journaled). Failure
        modes journal a ``data quality`` fail-closed event and return the
        :class:`FailClosedSignal` (still ``Ok`` wrapping the signal so the caller
        can alarm without mistaking it for permission).
        """
        if not coverage_known:
            signal_result = fail_closed(
                FailClosedReason.UNKNOWN_COVERAGE,
                detail={"coverage_known": False},
            )
            if is_refusal(signal_result):
                return signal_result
            journaled = journal_fail_closed(
                self._journal, signal_result.value, instant=journal_instant
            )
            if is_refusal(journaled):
                return journaled
            return Ok(signal_result.value)

        if require_exposures_for is not None:
            for code in require_exposures_for:
                token = code.strip().upper()
                if token not in self._exposures:
                    signal_result = fail_closed(
                        FailClosedReason.MISSING_CURRENCY_EXPOSURE,
                        detail={"currency": token, "instrument_scope": "unknown"},
                    )
                    if is_refusal(signal_result):
                        return signal_result
                    journaled = journal_fail_closed(
                        self._journal, signal_result.value, instant=journal_instant
                    )
                    if is_refusal(journaled):
                        return journaled
                    return Ok(signal_result.value)

        fetched = self._ingest.fetch_and_intake(
            request,
            writer=writer,
            world=world,
            receive_wall_time=receive_wall_time,
            sequence_start=sequence_start,
        )
        if is_refusal(fetched):
            # Provider unavailable / rate-limited / malformed → fail closed (AC4).
            detail: dict[str, object] = {
                "refusal_category": fetched.category.value,
                "retryability": fetched.retryability.value,
                "provider_context": dict(fetched.context),
            }
            signal_result = fail_closed(FailClosedReason.FAILED_REFRESH, detail=detail)
            if is_refusal(signal_result):
                return signal_result
            journaled = journal_fail_closed(
                self._journal, signal_result.value, instant=journal_instant
            )
            if is_refusal(journaled):
                return journaled
            return Ok(signal_result.value)

        events = self._adapter.last_events
        intake_receipts = fetched.value
        if boundary is not None:
            for receipt in intake_receipts:
                if receipt.outcome is IntakeOutcome.PRODUCED:
                    admitted: Result[ObservationReceipt] = self._ingest.submit(
                        receipt.observation, boundary
                    )
                    if is_refusal(admitted):
                        return admitted

        journaled = journal_import(
            self._journal,
            instant=journal_instant,
            events=events,
            intake_receipts=intake_receipts,
        )
        if is_refusal(journaled):
            return journaled
        return Ok(
            CalendarImportReceipt(
                events=events,
                intake_receipts=intake_receipts,
                journal_receipt=journaled.value,
            )
        )
