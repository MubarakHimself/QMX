"""CT-15 — external-source adapter seam owned by COMP-QMF-DATA-INGEST (AC1–AC6).

The middleware door that **owns and calls** the CT-15 provider port, validates and
normalizes provider responses into CT-10 :class:`~qmf.data.observation.SourceObservation`
**producer values**, and applies idempotent intake keyed on
``(source, source-native id, revision)``. A provider revision is a **new** artifact with
its own ``fp1`` — never an fp1 collision and never an overwrite of earlier evidence
(DEC-0119, DEC-0108).

What this seam guarantees:

* **AC1** — COMP-QMF-DATA-INGEST is the QMF caller of CT-15; COMP-QMF-DATA does not
  accept CT-15 as a public inbound on the store. Normalized observations are
  **application-routed** to the Data-owned CT-10 boundary
  (:class:`~qmf.data.source_boundary.SourceObservationBoundary`); producing values
  adds no package edge beyond ``qmf-data``'s existing ``qmf-core`` dependency
  (DEC-0117, DEC-0119, DEC-0120).
* **AC2** — duplicate / out-of-order arrivals under the same intake key are idempotent;
  a new ``revision`` mints a distinct observation fingerprint.
* **AC3** — foreign timestamps and foreign money ride through verbatim (zone / offset /
  resolution and the source's scaled integer) via the CT-10 value types; this seam never
  converts or rescales them.
* **AC4 / FM-2 / FM-6** — missing event-time, known-at, source, source-native id,
  revision, or a CT-03 :class:`~qmf.core.Instrument` mapping is an ``invalid input``
  refusal; no CT-10 value is emitted.
* **AC5 / FM-1 / FM-7** — a provider that is down or rate-limits returns
  ``unavailable dependency`` or ``transient venue failure`` through the port; the seam
  fabricates no observation. A read-only ``source`` is never a tradeable
  :class:`~qmf.core.VenueId`.
* **AC6 / FM-5** — asking the seam to own a scheduler, daemon, process supervisor, or
  retry loop is a ``policy rejection``; the adapter is a called port, not a running
  downloader (DEC-0051, DEC-0119).

Stdlib + qmf-core + the CT-10 value / boundary types already in this package.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    Instrument,
    Ok,
    Result,
    TypedRefusal,
    VenueId,
    is_refusal,
)
from qmf.data.observation import ForeignMoney, ForeignTimestamp, SourceObservation
from qmf.data.source_boundary import ObservationReceipt, SourceObservationBoundary
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.ticks import TickObservation, TickQuote, refuse_mid_merge

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "ExternalSourceIngest",
    "ExternalSourcePort",
    "IntakeKey",
    "IntakeOutcome",
    "IntakeReceipt",
    "ProviderRecord",
    "SourceRequest",
    "refuse_schedule_ownership",
    "refuse_source_as_venue",
]

# CT-15's first minted format version (DEC-0103; versioning-from-birth L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

_EMPTY_BOUNDS: Final[Mapping[str, object]] = MappingProxyType({})


# --- refusal helpers --------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build an ``invalid input`` refusal naming the offending field (FM-2, FM-6)."""
    return invalid_input(field, reason, **extra)


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def refuse_schedule_ownership(
    *,
    request: str | None = None,
) -> Result[IntakeReceipt]:
    """Refuse any ask that this seam own a scheduler, daemon, or retry loop (AC6).

    FM-5 / DEC-0119 / DEC-0051: COMP-QMF-DATA-INGEST is a called port; applications
    own scheduling, retries, supervision, and UI.
    """
    context: dict[str, object] = {
        "signal": "refuse-schedule-ownership",
        "component": "COMP-QMF-DATA-INGEST",
        "contract": "CT-15",
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "schedule",
        "COMP-QMF-DATA-INGEST is a called CT-15 port; owning a scheduler, daemon, "
        "process supervisor, or retry loop is outside the component — the application "
        "drives each bounded fetch (FM-5, DEC-0119, DEC-0051)",
        **context,
    )


def refuse_source_as_venue(
    *,
    given: object | None = None,
) -> TypedRefusal:
    """Refuse conflating a read-only ``source`` with a tradeable ``VenueId`` (AC5/FM-7).

    DEC-0117 / DEC-0107: a provider QMF only reads from is a source; a provider it
    can trade at is a venue. The same read-only provider is never both.
    """
    context: dict[str, object] = {
        "signal": "refuse-source-as-venue",
        "component": "COMP-QMF-DATA-INGEST",
    }
    if given is not None:
        context["given"] = repr(given)
    return policy_rejection(
        "source",
        "a read-only source is a provenance noun orthogonal to VenueId and is never "
        "conflated with a tradeable venue (FM-7, DEC-0117, DEC-0107)",
        **context,
    )


# --- intake identity --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IntakeKey:
    """The idempotent CT-15 intake key ``(source, source-native id, revision)``.

    A provider revision is a distinct key and therefore a new CT-10 artifact with its
    own ``fp1`` — never an overwrite and never an fp1 collision (AC2; DEC-0119).
    """

    source: str
    source_native_id: str
    revision: str

    @classmethod
    def try_create(
        cls, source: object, source_native_id: object, revision: object
    ) -> Result[IntakeKey]:
        """Validate the three opaque tokens, returning value-or-refusal."""
        if isinstance(source, VenueId):
            return refuse_source_as_venue(given=source)
        clean_source = _clean_str(source)
        if clean_source is None:
            return _invalid(
                "source",
                "source is required: a non-empty provenance id, orthogonal to VenueId",
                given=repr(source),
            )
        clean_native = _clean_str(source_native_id)
        if clean_native is None:
            return _invalid(
                "source_native_id",
                "source-native id is required: the provider's own id, never parsed",
                given=repr(source_native_id),
            )
        clean_revision = _clean_str(revision)
        if clean_revision is None:
            return _invalid(
                "revision",
                "revision is required: the provider's revision token; a new revision "
                "is a new artifact",
                given=repr(revision),
            )
        return Ok(
            cls(
                source=clean_source,
                source_native_id=clean_native,
                revision=clean_revision,
            )
        )


class IntakeOutcome(StrEnum):
    """Whether this intake minted a new observation or reused an idempotent prior."""

    PRODUCED = "produced"
    IDEMPOTENT = "idempotent"


@dataclass(frozen=True, slots=True)
class IntakeReceipt:
    """One normalized CT-10 producer value plus its CT-15 intake key (AC1, AC2).

    The application routes :attr:`observation` into
    :meth:`SourceObservationBoundary.admit`; this receipt itself does not persist.
    When the provider record carried bid/ask, :attr:`quote` holds them separately
    (never a mid) and :attr:`tick` is the bound :class:`~qmf.data.ticks.TickObservation`
    for source-disagreement edges (Story 6.2; DEC-0119).
    """

    observation: SourceObservation
    intake_key: IntakeKey
    instrument: Instrument
    outcome: IntakeOutcome
    quote: TickQuote | None = None
    tick: TickObservation | None = None
    format_version: int = CONTRACT_FORMAT_VERSION


# --- provider request / record ----------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceRequest:
    """A bounded CT-15 request from Data-Ingest to one external provider (AC1, AC6).

    ``source`` names the read-only provider. ``bounds`` carries opaque, provider-specific
    window / paging tokens — never interpreted here. The seam issues one call and
    returns; it never schedules the next.
    """

    source: str
    bounds: Mapping[str, object] = field(default_factory=lambda: _EMPTY_BOUNDS)


@dataclass(frozen=True, slots=True)
class ProviderRecord:
    """One provider-native fact on the CT-15 response path, before CT-10 minting.

    Required for a valid CT-10 emission (AC4): ``event_time``, ``known_at``, ``source``,
    ``source_native_id``, ``revision``, and a CT-03 :class:`~qmf.core.Instrument`
    mapping. Optional foreign timestamp / money blocks are stored verbatim when present
    (AC3). ``correction_of`` is set only when this record revises an earlier observation's
    ``fp1``.

    Tick sides (Story 6.2): optional ``bid`` / ``ask`` (scaled integers) with optional
    per-side source timestamps are preserved separately and never merged. A presented
    ``mid`` is a ``policy rejection``. When either side is present both are required.
    """

    source: object
    source_native_id: object
    revision: object
    event_time: object
    known_at: object
    instrument: object
    foreign_timestamp: object | None = None
    foreign_money: object | None = None
    correction_of: object | None = None
    bid: object | None = None
    ask: object | None = None
    bid_timestamp: object | None = None
    ask_timestamp: object | None = None
    mid: object | None = None


class ExternalSourcePort(Protocol):
    """CT-15 provider port — injected at the composition root, called by ingest (AC1).

    Implementations (Dukascopy, news-calendar feed, future venue market-data adapters)
    return provider records or a typed refusal. Rate-limits are
    ``transient venue failure`` (retryability as the provider states); an unreachable
    provider is ``unavailable dependency``. The port never fabricates observations —
    that refusal path is how AC5 / FM-1 stay honest.
    """

    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        """Return the bounded provider response, or a typed refusal."""
        ...


# --- seam -------------------------------------------------------------------


class ExternalSourceIngest:
    """COMP-QMF-DATA-INGEST — owns CT-15 calls and CT-10 producer normalization.

    Constructed with an injected :class:`ExternalSourcePort`. Each successful
    :meth:`intake` / :meth:`fetch_and_intake` yields :class:`IntakeReceipt` values the
    application routes to :class:`SourceObservationBoundary` (or via :meth:`submit`).
    An in-process ledger keys prior intakes by :class:`IntakeKey` so a duplicate
    arrival is idempotent (AC2).
    """

    def __init__(self, port: ExternalSourcePort) -> None:
        self._port = port
        self._ledger: dict[IntakeKey, IntakeReceipt] = {}

    @property
    def port(self) -> ExternalSourcePort:
        """The injected CT-15 provider port."""
        return self._port

    def normalize(
        self,
        record: object,
        *,
        writer: object,
        sequence: object,
        world: object,
        receive_wall_time: object,
        receive_monotonic_diagnostic: object | None = None,
    ) -> Result[tuple[SourceObservation, IntakeKey, Instrument, TickQuote | None]]:
        """Validate a provider record and mint a CT-10 :class:`SourceObservation` (AC1–AC4).

        Does not consult the idempotent ledger and does not persist — pure
        normalize. A missing bitemporal field, intake key part, or CT-03 instrument
        mapping is ``invalid input`` and emits no observation. When bid/ask are
        present they are preserved as a :class:`~qmf.data.ticks.TickQuote` (fourth
        tuple element); a presented mid is refused (Story 6.2).
        """
        if not isinstance(record, ProviderRecord):
            return _invalid(
                "record",
                "a CT-15 provider response item is a ProviderRecord",
                given=repr(record),
            )
        key = IntakeKey.try_create(record.source, record.source_native_id, record.revision)
        if is_refusal(key):
            return key
        instrument = _resolve_instrument(record.instrument)
        if is_refusal(instrument):
            return instrument
        foreign_ts = _resolve_optional_foreign_timestamp(record.foreign_timestamp)
        if is_refusal(foreign_ts):
            return foreign_ts
        foreign_money = _resolve_optional_foreign_money(record.foreign_money)
        if is_refusal(foreign_money):
            return foreign_money
        quote = _resolve_optional_tick_quote(record)
        if is_refusal(quote):
            return quote
        built = SourceObservation.try_create(
            event_time=record.event_time,
            known_at=record.known_at,
            source=key.value.source,
            source_native_id=key.value.source_native_id,
            revision=key.value.revision,
            receive_wall_time=receive_wall_time,
            writer=writer,
            sequence=sequence,
            world=world,
            foreign_timestamp=foreign_ts.value,
            foreign_money=foreign_money.value,
            receive_monotonic_diagnostic=receive_monotonic_diagnostic,
            correction_of=record.correction_of,
        )
        if is_refusal(built):
            return built
        return Ok((built.value, key.value, instrument.value, quote.value))

    def intake(
        self,
        record: object,
        *,
        writer: object,
        sequence: object,
        world: object,
        receive_wall_time: object,
        receive_monotonic_diagnostic: object | None = None,
    ) -> Result[IntakeReceipt]:
        """Normalize under the idempotent ``(source, native id, revision)`` key (AC2).

        A previously seen key returns the prior receipt with
        :attr:`IntakeOutcome.IDEMPOTENT` — earlier evidence is never erased or silently
        merged. A new revision is a new artifact with its own ``fp1``.
        """
        normalized = self.normalize(
            record,
            writer=writer,
            sequence=sequence,
            world=world,
            receive_wall_time=receive_wall_time,
            receive_monotonic_diagnostic=receive_monotonic_diagnostic,
        )
        if is_refusal(normalized):
            return normalized
        observation, key, instrument, quote = normalized.value
        prior = self._ledger.get(key)
        if prior is not None:
            return Ok(
                IntakeReceipt(
                    observation=prior.observation,
                    intake_key=key,
                    instrument=prior.instrument,
                    outcome=IntakeOutcome.IDEMPOTENT,
                    quote=prior.quote,
                    tick=prior.tick,
                )
            )
        tick = (
            TickObservation(observation=observation, quote=quote, instrument=instrument)
            if quote is not None
            else None
        )
        receipt = IntakeReceipt(
            observation=observation,
            intake_key=key,
            instrument=instrument,
            outcome=IntakeOutcome.PRODUCED,
            quote=quote,
            tick=tick,
        )
        self._ledger[key] = receipt
        return Ok(receipt)

    def fetch_and_intake(
        self,
        request: object,
        *,
        writer: object,
        world: object,
        receive_wall_time: object,
        sequence_start: int = 0,
        receive_monotonic_diagnostic: object | None = None,
    ) -> Result[tuple[IntakeReceipt, ...]]:
        """Call the CT-15 port once and intake every returned record (AC1, AC5).

        A port refusal (rate-limit / unavailable) propagates unchanged — no fabricated
        observation is minted. ``sequence_start`` is the per-writer sequence of the first
        produced record; subsequent produced (non-idempotent) records increment it.
        """
        if not isinstance(request, SourceRequest):
            return _invalid(
                "request",
                "a CT-15 call carries a SourceRequest naming the provider and opaque bounds",
                given=repr(request),
            )
        if _clean_str(request.source) is None:
            return _invalid(
                "source",
                "a CT-15 request names a non-empty read-only source, never a VenueId",
                given=repr(request.source),
            )
        fetched = self._port.fetch(request)
        if is_refusal(fetched):
            # Provider unavailable / rate-limited — surface as-is; emit nothing (AC5).
            return fetched
        receipts: list[IntakeReceipt] = []
        sequence = sequence_start
        for record in fetched.value:
            result = self.intake(
                record,
                writer=writer,
                sequence=sequence,
                world=world,
                receive_wall_time=receive_wall_time,
                receive_monotonic_diagnostic=receive_monotonic_diagnostic,
            )
            if is_refusal(result):
                return result
            receipts.append(result.value)
            if result.value.outcome is IntakeOutcome.PRODUCED:
                sequence += 1
        return Ok(tuple(receipts))

    def submit(
        self,
        observation: object,
        boundary: SourceObservationBoundary,
    ) -> Result[ObservationReceipt]:
        """Application-routed hand-off to the Data-owned CT-10 boundary (AC1).

        Thin composition helper: ingest never reaches into the store itself for CT-15
        payloads; the application injects the boundary and routes producer values.
        """
        return boundary.admit(observation)

    def known_key(self, key: IntakeKey) -> bool:
        """Whether ``key`` has already been intake'd in this process ledger."""
        return key in self._ledger

    def start_scheduler(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        """Always refuse — scheduling is application-owned (AC6 / FM-5)."""
        return refuse_schedule_ownership(request="start_scheduler")

    def run_daemon(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        """Always refuse — process supervision is application-owned (AC6 / FM-5)."""
        return refuse_schedule_ownership(request="run_daemon")

    def run_retry_loop(self, *_args: object, **_kwargs: object) -> Result[IntakeReceipt]:
        """Always refuse — retries are application-owned (AC6 / FM-5)."""
        return refuse_schedule_ownership(request="run_retry_loop")


# --- field resolvers --------------------------------------------------------


def _resolve_instrument(value: object) -> Result[Instrument]:
    """Require a CT-03 :class:`~qmf.core.Instrument` mapping (AC4 / FM-6)."""
    if isinstance(value, Instrument):
        return Instrument.try_create(value.venue, value.symbol)
    if isinstance(value, Mapping):
        block = cast("Mapping[str, object]", value)
        venue = block.get("venue")
        symbol = block.get("symbol")
        if isinstance(venue, VenueId):
            return Instrument.try_create(venue, symbol)
        if isinstance(venue, str):
            venue_id = VenueId.try_create(venue)
            if is_refusal(venue_id):
                return _invalid(
                    "instrument",
                    "a source record must map to a CT-03 Instrument (venue, opaque "
                    "symbol); without that mapping no CT-10 observation is emitted "
                    "(FM-6)",
                    given=repr(block),
                )
            return Instrument.try_create(venue_id.value, symbol)
        return _invalid(
            "instrument",
            "a source record must map to a CT-03 Instrument (venue, opaque symbol); "
            "without that mapping no CT-10 observation is emitted (FM-6)",
            given=repr(block),
        )
    return _invalid(
        "instrument",
        "a source record must map to a CT-03 Instrument (venue, opaque symbol); "
        "without that mapping no CT-10 observation is emitted (FM-6)",
        given=repr(value),
    )


def _resolve_optional_foreign_timestamp(
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
    return _invalid(
        "foreign_timestamp",
        "foreign timestamp is a ForeignTimestamp or a mapping of "
        "verbatim/zone/offset/resolution (or omitted)",
        given=repr(value),
    )


def _resolve_optional_foreign_money(value: object | None) -> Result[ForeignMoney | None]:
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
    return _invalid(
        "foreign_money",
        "foreign money is a ForeignMoney or a mapping of verbatim/scale (or omitted)",
        given=repr(value),
    )


def _resolve_optional_tick_quote(record: ProviderRecord) -> Result[TickQuote | None]:
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
            return _invalid(
                "bid",
                "per-side source timestamps require both bid and ask; tick sides are "
                "never partial (DEC-0119)",
            )
        return Ok(None)
    if has_bid != has_ask:
        return _invalid(
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
