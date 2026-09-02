"""Governed live-observation intake — accumulator is the single first writer.

Live ticks, trendbars, depth, fills, and lifecycle events enter here, persist
CT-10 identity (event / known-at / revision / source) through the accumulator's
governed intake, journal under the venue WriterId onto CT-13's closed seven,
and only then become foldable. Interpretation waits for persistence (TN-13 /
DEC-0190 / Story 27.2).

Reconnect overlap is idempotent on ``(source, source-native id, revision)``:
the same revision is deduplicated; a changed revision appends. No silent
sibling-feed failover. FTR-01 position/balance mapping is refused.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Instant, Ok, Result, TypedRefusal, World, is_refusal

from qmn.data._refuse import clean_token, invalid, policy
from qmn.data.mapping import (
    CT13_SEVEN_EVENT_TYPES,
    FTR01_BLOCKED_KINDS,
    journal_event_for_kind,
    refuse_ftr01_mapping,
    refuse_observation_journal_type,
)
from qmn.loop.accumulator import RecordingAccumulator, first_writer_for
from qmn.loop.kinds import InboundObservation

__all__ = [
    "CANONICAL_LIVE_SOURCE",
    "FORBIDDEN_FAILOVER_SOURCES",
    "GovernedLiveIntake",
    "IntakeIdentity",
    "LiveIntakeOutcome",
    "LiveIntakeReceipt",
    "refuse_sibling_failover",
]


CANONICAL_LIVE_SOURCE: Final[str] = "ctrader"
FORBIDDEN_FAILOVER_SOURCES: Final[frozenset[str]] = frozenset(
    {"truefx", "histdata", "dukascopy-live-sibling", "sibling-feed"}
)


class LiveIntakeOutcome(StrEnum):
    """Whether this record minted new evidence, reused a revision, or appended."""

    PRODUCED = "produced"
    IDEMPOTENT = "idempotent"
    REVISED = "revised"


@dataclass(frozen=True, slots=True)
class IntakeIdentity:
    """CT-10 venue-native identity persisted before interpretation."""

    source: str
    source_native_id: str
    revision: str
    event_time_ns: int
    known_at_ns: int

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source": self.source,
                "source_native_id": self.source_native_id,
                "revision": self.revision,
                "event_time_ns": self.event_time_ns,
                "known_at_ns": self.known_at_ns,
            }
        )

    @property
    def key(self) -> tuple[str, str, str]:
        """Idempotent intake key ``(source, source-native id, revision)``."""
        return (self.source, self.source_native_id, self.revision)

    @property
    def native_key(self) -> tuple[str, str]:
        """Venue-native identity without revision (gap-replay overlap)."""
        return (self.source, self.source_native_id)


@dataclass(frozen=True, slots=True)
class LiveIntakeReceipt:
    """One governed live record: identity, journal type, foldability."""

    observation: InboundObservation
    outcome: LiveIntakeOutcome
    identity: IntakeIdentity
    journal_event_type: str
    foldable: bool
    raw_payload: Mapping[str, object]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "observation_id": self.observation.observation_id,
                "outcome": self.outcome.value,
                "identity": dict(self.identity.as_mapping()),
                "journal_event_type": self.journal_event_type,
                "foldable": self.foldable,
                "raw_payload": dict(self.raw_payload),
            }
        )


def refuse_sibling_failover(
    *, feed: object, canonical: str = CANONICAL_LIVE_SOURCE
) -> TypedRefusal:
    """Refuse a silent sibling-feed failover off the pinned canonical sensing feed."""
    token = clean_token(feed)
    given = token if token is not None else repr(feed)
    return policy(
        "feed",
        "no silent sibling-feed failover; the pinned canonical sensing feed "
        "fails closed until the same feed gap-replays (TN-13, DEC-0138)",
        failure_id="data.intake.sibling_failover",
        canonical=canonical,
        attempted=given,
        forbidden=sorted(FORBIDDEN_FAILOVER_SOURCES),
    )


@dataclass
class GovernedLiveIntake:
    """Single first-writer path: persist through the accumulator, then fold.

    The accumulator is the only writer of inbound observations for the bound
    ``(VenueId, account)`` stream. This object owns the CT-15 idempotent ledger
    and the CT-13 mapping; it never writes a second copy.
    """

    accumulator: RecordingAccumulator
    world: World = World.LIVE
    canonical_source: str = CANONICAL_LIVE_SOURCE
    _ledger: dict[tuple[str, str, str], LiveIntakeReceipt] = field(
        default_factory=dict[tuple[str, str, str], LiveIntakeReceipt]
    )
    _native_revision: dict[tuple[str, str], str] = field(default_factory=dict[tuple[str, str], str])

    @classmethod
    def try_create(
        cls,
        *,
        accumulator: object,
        world: object = World.LIVE,
        canonical_source: object = CANONICAL_LIVE_SOURCE,
    ) -> Result[GovernedLiveIntake]:
        """Bind one intake to the stream's sole recording accumulator."""
        if not isinstance(accumulator, RecordingAccumulator):
            return invalid(
                "accumulator",
                "governed live intake writes only through a RecordingAccumulator",
                given=repr(type(accumulator).__name__),
            )
        resolved_world = world if isinstance(world, World) else None
        if resolved_world is None and isinstance(world, str):
            try:
                resolved_world = World(world)
            except ValueError:
                resolved_world = None
        if resolved_world is None:
            return invalid(
                "world",
                "live intake is world-scoped evidence (live | replay)",
                given=repr(world),
            )
        if resolved_world is World.SIMULATED:
            return policy(
                "world",
                "writing world=simulated into governed evidence is a policy rejection",
                world=resolved_world.value,
            )
        source = clean_token(canonical_source)
        if source is None:
            return invalid(
                "canonical_source",
                "the pinned canonical sensing feed names a non-empty source",
                given=repr(canonical_source),
            )
        if source in FORBIDDEN_FAILOVER_SOURCES:
            return refuse_sibling_failover(feed=source, canonical=CANONICAL_LIVE_SOURCE)
        registered = first_writer_for(accumulator.venue_id, accumulator.account)
        if registered is not None and registered != accumulator.writer_name:
            return policy(
                "first_writer",
                "the accumulator is the single first writer; a sibling module "
                "cannot bind intake for this stream",
                stream=accumulator.key,
                registered=registered,
                attempted=accumulator.writer_name,
                failure_id="data.intake.sibling_failover",
            )
        return Ok(
            cls(
                accumulator=accumulator,
                world=resolved_world,
                canonical_source=source,
            )
        )

    def record(
        self,
        *,
        observation_id: object,
        stream_id: object,
        receive_wall: object,
        payload: object,
        kind: object = None,
        source: object = None,
        source_native_id: object = None,
        revision: object = None,
        event_time: object = None,
        known_at: object = None,
        venue_instant: object = None,
        raw_payload: object = None,
        closed: object = True,
        feed: object = None,
    ) -> Result[LiveIntakeReceipt]:
        """Persist one inbound observation, then make it foldable.

        Same ``(source, native id, revision)`` is idempotent and does not
        re-enqueue. A changed revision appends a new artifact.
        """
        feed_token = clean_token(feed) if feed is not None else self.canonical_source
        if feed_token is None:
            return invalid(
                "feed",
                "feed is a non-empty source token when supplied",
                given=repr(feed),
            )
        if feed_token in FORBIDDEN_FAILOVER_SOURCES or feed_token != self.canonical_source:
            return refuse_sibling_failover(feed=feed_token, canonical=self.canonical_source)

        kind_token = clean_token(kind)
        payload_map = _as_payload(payload)
        if kind_token is None and payload_map is not None:
            kind_token = clean_token(
                payload_map.get("kind")
                or payload_map.get("wire_kind")
                or payload_map.get("observation_kind")
            )
        if kind_token is not None:
            normalized_kind = kind_token.strip().lower().replace("_", "-")
            if normalized_kind in FTR01_BLOCKED_KINDS:
                return refuse_ftr01_mapping(kind=normalized_kind)
            if normalized_kind == "observation":
                return refuse_observation_journal_type(given=normalized_kind)

        journal_type = journal_event_for_kind(kind_token if kind_token is not None else "system")
        if is_refusal(journal_type):
            return journal_type
        if journal_type.value not in CT13_SEVEN_EVENT_TYPES:
            return refuse_observation_journal_type(given=journal_type.value)

        identity = _resolve_identity(
            observation_id=observation_id,
            receive_wall=receive_wall,
            venue_instant=venue_instant,
            source=source if source is not None else self.canonical_source,
            source_native_id=source_native_id,
            revision=revision,
            event_time=event_time,
            known_at=known_at,
            payload=payload_map,
        )
        if is_refusal(identity):
            return identity
        ident = identity.value

        prior = self._ledger.get(ident.key)
        if prior is not None:
            return Ok(
                LiveIntakeReceipt(
                    observation=prior.observation,
                    outcome=LiveIntakeOutcome.IDEMPOTENT,
                    identity=prior.identity,
                    journal_event_type=prior.journal_event_type,
                    foldable=False,
                    raw_payload=prior.raw_payload,
                )
            )

        previous_rev = self._native_revision.get(ident.native_key)
        outcome = (
            LiveIntakeOutcome.REVISED
            if previous_rev is not None and previous_rev != ident.revision
            else LiveIntakeOutcome.PRODUCED
        )

        raw = _resolve_raw(raw_payload, payload_map)
        body: dict[str, object] = dict(payload_map) if payload_map is not None else {}
        body.update(dict(ident.as_mapping()))
        body["raw_payload"] = dict(raw)
        body["ct13_event_type"] = journal_type.value
        body["world"] = self.world.value
        if kind_token is not None:
            body.setdefault("kind", kind_token)
            body.setdefault("wire_kind", kind_token)

        pushed = self.accumulator.push(
            observation_id=observation_id,
            stream_id=stream_id,
            receive_wall=receive_wall,
            payload=body,
            kind=kind_token,
            venue_instant=venue_instant if venue_instant is not None else _as_instant(event_time),
            closed=closed,
        )
        if is_refusal(pushed):
            return pushed

        receipt = LiveIntakeReceipt(
            observation=pushed.value,
            outcome=outcome,
            identity=ident,
            journal_event_type=journal_type.value,
            foldable=True,
            raw_payload=MappingProxyType(dict(raw)),
        )
        self._ledger[ident.key] = receipt
        self._native_revision[ident.native_key] = ident.revision
        return Ok(receipt)


def _as_payload(payload: object) -> Mapping[str, object] | None:
    if isinstance(payload, Mapping):
        return cast("Mapping[str, object]", payload)
    return None


def _as_instant(value: object) -> Instant | None:
    if isinstance(value, Instant):
        return value
    return None


def _ns_of(value: object) -> int | None:
    if isinstance(value, Instant):
        return value.value_ns
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _resolve_raw(
    raw_payload: object, payload_map: Mapping[str, object] | None
) -> Mapping[str, object]:
    if isinstance(raw_payload, Mapping):
        return cast("Mapping[str, object]", raw_payload)
    if payload_map is not None:
        nested = payload_map.get("raw_payload")
        if isinstance(nested, Mapping):
            return cast("Mapping[str, object]", nested)
        return payload_map
    return {}


def _resolve_identity(
    *,
    observation_id: object,
    receive_wall: object,
    venue_instant: object,
    source: object,
    source_native_id: object,
    revision: object,
    event_time: object,
    known_at: object,
    payload: Mapping[str, object] | None,
) -> Result[IntakeIdentity]:
    src = clean_token(source)
    if src is None and payload is not None:
        src = clean_token(payload.get("source"))
    if src is None:
        return invalid(
            "source",
            "every live observation names a CT-10 source orthogonal to VenueId",
            given=repr(source),
        )
    native = clean_token(source_native_id)
    if native is None and payload is not None:
        native = clean_token(
            payload.get("source_native_id")
            or payload.get("native_id")
            or payload.get("observation_id")
        )
    if native is None:
        native = clean_token(observation_id)
    if native is None:
        return invalid(
            "source_native_id",
            "every live observation carries a venue-native identity key",
            given=repr(source_native_id),
        )
    rev = clean_token(revision)
    if rev is None and payload is not None:
        raw_rev = payload.get("revision")
        if isinstance(raw_rev, int) and not isinstance(raw_rev, bool):
            rev = str(raw_rev)
        else:
            rev = clean_token(raw_rev)
    if rev is None:
        rev = "r1"
    wall_ns = _ns_of(receive_wall)
    if wall_ns is None and payload is not None:
        wall_ns = _ns_of(payload.get("receive_wall_time_ns"))
    if wall_ns is None:
        return invalid(
            "receive_wall",
            "the accumulator stamps a receive-wall Instant as known-at / frontier",
            given=repr(type(receive_wall).__name__),
        )
    event_ns = _ns_of(event_time)
    if event_ns is None:
        event_ns = _ns_of(venue_instant)
    if event_ns is None and payload is not None:
        event_ns = _ns_of(payload.get("event_time_ns") or payload.get("venue_instant_ns"))
    if event_ns is None:
        event_ns = wall_ns
    known_ns = _ns_of(known_at)
    if known_ns is None and payload is not None:
        known_ns = _ns_of(payload.get("known_at_ns"))
    if known_ns is None:
        known_ns = wall_ns
    return Ok(
        IntakeIdentity(
            source=src,
            source_native_id=native,
            revision=rev,
            event_time_ns=event_ns,
            known_at_ns=known_ns,
        )
    )
