"""CT-15 public value types for external-source ingest.

Split from :mod:`qmf.data.ingest` so the primitive module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.ingest`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol

from qmf.core import Instrument, Ok, Result, TypedRefusal, VenueId
from qmf.data.observation import ForeignMoney, SourceObservation
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.ticks import TickObservation, TickQuote

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "ExternalSourcePort",
    "IntakeKey",
    "IntakeOutcome",
    "IntakeReceipt",
    "ProviderRecord",
    "SourceRequest",
    "clean_str",
    "invalid_field",
    "refuse_schedule_ownership",
    "refuse_source_as_venue",
]

# CT-15's first minted format version (DEC-0103; versioning-from-birth L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

_EMPTY_BOUNDS: Final[Mapping[str, object]] = MappingProxyType({})


def invalid_field(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build an ``invalid input`` refusal naming the offending field (FM-2, FM-6)."""
    return invalid_input(field, reason, **extra)


def clean_str(value: object) -> str | None:
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
        cleaned_source = clean_str(source)
        if cleaned_source is None:
            return invalid_field(
                "source",
                "source is required: a non-empty provenance id, orthogonal to VenueId",
                given=repr(source),
            )
        clean_native = clean_str(source_native_id)
        if clean_native is None:
            return invalid_field(
                "source_native_id",
                "source-native id is required: the provider's own id, never parsed",
                given=repr(source_native_id),
            )
        clean_revision = clean_str(revision)
        if clean_revision is None:
            return invalid_field(
                "revision",
                "revision is required: the provider's revision token; a new revision "
                "is a new artifact",
                given=repr(revision),
            )
        return Ok(
            cls(
                source=cleaned_source,
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

    def observation_with_foreign_money(
        self, foreign_money: ForeignMoney
    ) -> Result[SourceObservation]:
        """Rebuild the CT-10 producer value with exact quote money attached.

        ``foreign_money`` is identity-bearing, so the observation must be rebuilt
        through the validating CT-10 factory rather than mutated after intake.
        """
        observation = self.observation
        return SourceObservation.try_create(
            event_time=observation.event_time,
            known_at=observation.known_at,
            source=observation.source,
            source_native_id=observation.source_native_id,
            revision=observation.revision,
            receive_wall_time=observation.receive_wall_time,
            writer=observation.writer,
            sequence=observation.sequence,
            world=observation.world,
            foreign_timestamp=observation.foreign_timestamp,
            foreign_money=foreign_money,
            market_data=observation.market_data,
            receive_monotonic_diagnostic=observation.receive_monotonic_diagnostic,
            correction_of=observation.correction_of,
        )


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
