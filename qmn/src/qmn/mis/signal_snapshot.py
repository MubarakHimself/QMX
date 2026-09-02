"""Immutable environment-keyed signal snapshot at the Book door (Story 26.3).

Compute-once, versioned, immutable per-instant MIS artifact dispatched to a
CLOSED consumer set — the Book door and the KSA, never bots. Carries exactly
one value/marker per producer including SQS, keyed by environment, bounded by
the Book's ``registry:decision_freshness_bound`` with no second bound
(DEC-0204, DEC-0230, TN-8 / TN-19).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Duration,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Ok,
    Result,
    TypedRefusal,
    UnitKind,
    VenueId,
    fingerprint,
    is_refusal,
)

from qmn.mis._refuse import clean_token, invalid, policy, stale

__all__ = [
    "DECISION_FRESHNESS_BOUND_VARIABLE",
    "GOVERNED_CONSUMERS",
    "SIGNAL_SNAPSHOT_FORMAT_VERSION",
    "SIGNAL_SNAPSHOT_SURFACE",
    "SQS_PRODUCER_ID",
    "CanonicalFeedState",
    "GovernedConsumer",
    "ProducerReadiness",
    "ProducerSlot",
    "SignalSnapshot",
    "SnapshotLane",
    "SqsBaselineKey",
    "SqsReading",
    "check_snapshot_freshness",
    "consume_signal_snapshot",
    "mint_signal_snapshot",
    "refuse_bot_consumer",
    "sqs_baseline_key",
]

SIGNAL_SNAPSHOT_SURFACE: Final[str] = "qmn.mis.signal_snapshot"
SIGNAL_SNAPSHOT_FORMAT_VERSION: Final[int] = 1
DECISION_FRESHNESS_BOUND_VARIABLE: Final[str] = "decision_freshness_bound"
SQS_PRODUCER_ID: Final[str] = "sqs"


class GovernedConsumer(StrEnum):
    """CLOSED consumer set for the signal snapshot (DEC-0204)."""

    BOOK_DOOR = "book_door"
    KSA = "ksa"


GOVERNED_CONSUMERS: Final[frozenset[GovernedConsumer]] = frozenset(GovernedConsumer)


class SnapshotLane(StrEnum):
    """Governed money-path lane versus zero-authority shadow publish (DEC-0204)."""

    GOVERNED = "governed"
    SHADOW = "shadow"


class ProducerReadiness(StrEnum):
    """Typed availability markers replacing the legacy sentinel (DEC-0153)."""

    OK = "ok"
    NOT_READY = "not_ready"
    UNAVAILABLE = "unavailable"
    STALE = "stale"
    REFUSED = "refused"


class CanonicalFeedState(StrEnum):
    """Pinned canonical feed state on the snapshot (DEC-0204)."""

    LIVE = "live"
    DEGRADED = "degraded"
    DEAD = "dead"


@dataclass(frozen=True, slots=True)
class SqsBaselineKey:
    """SQS baseline identity ``(VenueId, environment, instrument)`` (DEC-0230).

    A demo-conditioned baseline never satisfies a ``role = live`` binding.
    """

    venue: VenueId
    environment: str
    instrument: Instrument

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "sqs-baseline-key",
            "venue": self.venue.value,
            "environment": self.environment,
            "instrument": {
                "venue": self.instrument.venue.value,
                "symbol": self.instrument.symbol,
            },
            "format_version": SIGNAL_SNAPSHOT_FORMAT_VERSION,
        }


def sqs_baseline_key(
    venue: object,
    environment: object,
    instrument: object,
) -> Result[SqsBaselineKey]:
    """Mint the environment-keyed SQS baseline key."""
    if not isinstance(venue, VenueId):
        return invalid(
            "venue",
            "SQS baseline key names a VenueId",
            given=repr(venue),
        )
    env = clean_token(environment)
    if env is None:
        return invalid(
            "environment",
            "SQS baseline is keyed by a non-empty environment token "
            "(demo vs live are distinct)",
            given=repr(environment),
        )
    if not isinstance(instrument, Instrument):
        return invalid(
            "instrument",
            "SQS baseline key names an Instrument",
            given=repr(instrument),
        )
    return Ok(SqsBaselineKey(venue=venue, environment=env, instrument=instrument))


@dataclass(frozen=True, slots=True)
class SqsReading:
    """One per-instrument SQS value inside the snapshot (AD-39 / DEC-0230).

    Score is an exact rational dimensionless ratio. Non-``ok`` readiness is a
    conservative hard block — never last-known-good.
    """

    baseline_key: SqsBaselineKey
    score: ExactRational | None
    hard_block: bool
    readiness: ProducerReadiness
    labeler_version: str

    @classmethod
    def try_create(
        cls,
        baseline_key: object,
        *,
        readiness: object,
        labeler_version: object,
        score: object = None,
        hard_block: object = None,
    ) -> Result[SqsReading]:
        if not isinstance(baseline_key, SqsBaselineKey):
            return invalid(
                "baseline_key",
                "an SQS reading carries an environment-keyed SqsBaselineKey",
                given=repr(baseline_key),
            )
        marker = _coerce_readiness(readiness)
        if isinstance(marker, TypedRefusal):
            return marker
        version = clean_token(labeler_version)
        if version is None:
            return invalid(
                "labeler_version",
                "every producer slot carries a non-empty labeler version stamp",
                given=repr(labeler_version),
            )
        resolved_score: ExactRational | None = None
        if score is not None:
            if not isinstance(score, ExactRational):
                return invalid(
                    "score",
                    "SQS score is an ExactRational dimensionless ratio when present",
                    given=repr(score),
                )
            if score.unit_kind is not UnitKind.DIMENSIONLESS_RATIO:
                return invalid(
                    "score",
                    "SQS score unit-kind is dimensionless-ratio",
                    given=score.unit_kind.value,
                )
            resolved_score = score
        if marker is ProducerReadiness.OK:
            if resolved_score is None:
                return invalid(
                    "score",
                    "an ok SQS reading carries an ExactRational score",
                )
            if hard_block is None:
                return invalid(
                    "hard_block",
                    "an ok SQS reading declares hard_block explicitly",
                )
            if not isinstance(hard_block, bool):
                return invalid(
                    "hard_block",
                    "hard_block is a boolean",
                    given=repr(hard_block),
                )
            block = hard_block
        else:
            # Conservative sentinel: non-ok means hard block; score omitted.
            block = True
            if hard_block is False:
                return policy(
                    "hard_block",
                    "undefined, unreachable, stale, or refused SQS means hard block; "
                    "never last-known-good",
                    readiness=marker.value,
                )
            if hard_block is True:
                block = True
            resolved_score = None
        return Ok(
            cls(
                baseline_key=baseline_key,
                score=resolved_score,
                hard_block=block,
                readiness=marker,
                labeler_version=version,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "class": "sqs-reading",
            "baseline_key": self.baseline_key.fp1_identity(),
            "hard_block": self.hard_block,
            "readiness": self.readiness.value,
            "labeler_version": self.labeler_version,
            "format_version": SIGNAL_SNAPSHOT_FORMAT_VERSION,
        }
        if self.score is not None:
            content["score"] = self.score.fp1_identity()
        return content


@dataclass(frozen=True, slots=True)
class ProducerSlot:
    """Exactly one value/marker per producer id on the snapshot."""

    producer_id: str
    readiness: ProducerReadiness
    labeler_version: str
    sqs: SqsReading | None = None
    marker_detail: str | None = None

    @classmethod
    def try_create(
        cls,
        producer_id: object,
        *,
        readiness: object,
        labeler_version: object,
        sqs: object = None,
        marker_detail: object = None,
    ) -> Result[ProducerSlot]:
        pid = clean_token(producer_id)
        if pid is None:
            return invalid(
                "producer_id",
                "a producer slot names a non-empty opaque producer id",
                given=repr(producer_id),
            )
        marker = _coerce_readiness(readiness)
        if isinstance(marker, TypedRefusal):
            return marker
        version = clean_token(labeler_version)
        if version is None:
            return invalid(
                "labeler_version",
                "every producer slot carries a non-empty labeler version stamp",
                given=repr(labeler_version),
            )
        sqs_reading: SqsReading | None = None
        if pid == SQS_PRODUCER_ID:
            if not isinstance(sqs, SqsReading):
                return invalid(
                    "sqs",
                    "the SQS producer slot carries an SqsReading",
                    given=repr(sqs),
                )
            if sqs.readiness is not marker:
                return invalid(
                    "readiness",
                    "SQS slot readiness must match the SqsReading readiness",
                )
            sqs_reading = sqs
        elif sqs is not None:
            return invalid(
                "sqs",
                "only the sqs producer slot carries an SqsReading",
                producer_id=pid,
            )
        detail: str | None = None
        if marker_detail is not None:
            detail = clean_token(marker_detail)
            if detail is None:
                return invalid(
                    "marker_detail",
                    "marker_detail is a non-empty token when present",
                    given=repr(marker_detail),
                )
        return Ok(
            cls(
                producer_id=pid,
                readiness=marker,
                labeler_version=version,
                sqs=sqs_reading,
                marker_detail=detail,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "class": "producer-slot",
            "producer_id": self.producer_id,
            "readiness": self.readiness.value,
            "labeler_version": self.labeler_version,
            "format_version": SIGNAL_SNAPSHOT_FORMAT_VERSION,
        }
        if self.sqs is not None:
            content["sqs"] = self.sqs.fp1_identity()
        if self.marker_detail is not None:
            content["marker_detail"] = self.marker_detail
        return content


@dataclass(frozen=True, slots=True)
class SignalSnapshot:
    """Immutable per-instant signal snapshot (DEC-0204, DEC-0230).

    One slot per producer id. SQS reaches the Book door and KSA only inside this
    artifact so one instant carries exactly one SQS value.
    """

    frontier_instant: Instant
    environment: str
    feed_state: CanonicalFeedState
    producers: Mapping[str, ProducerSlot]
    degraded_sensors: tuple[str, ...]
    decision_freshness_bound: Duration
    lane: SnapshotLane = SnapshotLane.GOVERNED

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "signal-snapshot",
            "lane": self.lane.value,
            "frontier_instant": self.frontier_instant.fp1_identity(),
            "environment": self.environment,
            "feed_state": self.feed_state.value,
            "producers": {
                pid: slot.fp1_identity()
                for pid, slot in sorted(self.producers.items(), key=lambda item: item[0])
            },
            "degraded_sensors": list(self.degraded_sensors),
            DECISION_FRESHNESS_BOUND_VARIABLE: self.decision_freshness_bound.fp1_identity(),
            "format_version": SIGNAL_SNAPSHOT_FORMAT_VERSION,
        }

    def sqs_for(self, instrument: Instrument) -> SqsReading | None:
        """The single SQS reading for ``instrument`` when present."""
        slot = self.producers.get(SQS_PRODUCER_ID)
        if slot is None or slot.sqs is None:
            return None
        if slot.sqs.baseline_key.instrument != instrument:
            return None
        return slot.sqs


def mint_signal_snapshot(
    *,
    frontier_instant: object,
    environment: object,
    feed_state: object,
    producers: object,
    decision_freshness_bound: object,
    degraded_sensors: object = (),
    lane: object = SnapshotLane.GOVERNED,
) -> Result[SignalSnapshot]:
    """Mint one immutable snapshot with exactly one slot per producer id."""
    if not isinstance(frontier_instant, Instant):
        return invalid(
            "frontier_instant",
            "a signal snapshot is frontier-bound to an Instant — never wall-now",
            given=repr(frontier_instant),
        )
    env = clean_token(environment)
    if env is None:
        return invalid(
            "environment",
            "a signal snapshot is keyed by a non-empty environment token",
            given=repr(environment),
        )
    feed = _coerce_feed_state(feed_state)
    if isinstance(feed, TypedRefusal):
        return feed
    if not isinstance(decision_freshness_bound, Duration):
        return invalid(
            DECISION_FRESHNESS_BOUND_VARIABLE,
            "decision_freshness_bound is a mandatory resolved Duration — "
            "no second bound and no invented default",
            given=repr(decision_freshness_bound),
        )
    if decision_freshness_bound.value_ns < 0:
        return invalid(
            DECISION_FRESHNESS_BOUND_VARIABLE,
            "decision_freshness_bound is a non-negative Duration",
            given=decision_freshness_bound.value_ns,
        )
    resolved_lane = _coerce_lane(lane)
    if isinstance(resolved_lane, TypedRefusal):
        return resolved_lane
    require_sqs = resolved_lane is SnapshotLane.GOVERNED
    slots = _coerce_producer_slots(producers, require_sqs=require_sqs)
    if isinstance(slots, TypedRefusal):
        return slots
    sensors = _coerce_sensor_list(degraded_sensors)
    if isinstance(sensors, TypedRefusal):
        return sensors
    return Ok(
        SignalSnapshot(
            frontier_instant=frontier_instant,
            environment=env,
            feed_state=feed,
            producers=MappingProxyType(slots),
            degraded_sensors=sensors,
            decision_freshness_bound=decision_freshness_bound,
            lane=resolved_lane,
        )
    )


def check_snapshot_freshness(
    snapshot: object,
    *,
    decision_at: object,
) -> Result[None]:
    """Refuse consumption past ``decision_freshness_bound`` (stale evidence)."""
    if not isinstance(snapshot, SignalSnapshot):
        return invalid(
            "snapshot",
            "freshness check reads a SignalSnapshot",
            given=repr(snapshot),
        )
    if not isinstance(decision_at, Instant):
        return invalid(
            "decision_at",
            "freshness is evaluated at an Instant decision time",
            given=repr(decision_at),
        )
    age = decision_at.difference(snapshot.frontier_instant)
    if is_refusal(age):
        return age
    if age.value.value_ns > snapshot.decision_freshness_bound.value_ns:
        return stale(
            DECISION_FRESHNESS_BOUND_VARIABLE,
            "signal snapshot age exceeds decision_freshness_bound; "
            "consumption is a stale-evidence refusal with no second bound",
            age_ns=age.value.value_ns,
            bound_ns=snapshot.decision_freshness_bound.value_ns,
        )
    return Ok(None)


def consume_signal_snapshot(
    snapshot: object,
    *,
    consumer: object,
    decision_at: object,
) -> Result[SignalSnapshot]:
    """Dispatch the snapshot to a governed consumer after freshness check."""
    resolved = _coerce_consumer(consumer)
    if isinstance(resolved, TypedRefusal):
        return resolved
    if resolved not in GOVERNED_CONSUMERS:
        bot = refuse_bot_consumer(resolved.value)
        if not isinstance(bot, TypedRefusal):
            return invalid(
                "consumer",
                "bot consumers must be refused as a policy rejection",
                consumer=resolved.value,
            )
        return bot
    if not isinstance(snapshot, SignalSnapshot):
        return invalid(
            "snapshot",
            "Book door / KSA consume a SignalSnapshot",
            given=repr(snapshot),
        )
    if snapshot.lane is SnapshotLane.SHADOW:
        return policy(
            "lane",
            "a shadow-lane snapshot is publish-only; the Book door, KSA, bots, "
            "venue, and command/control folds never consume candidate output",
            lane=snapshot.lane.value,
            consumer=resolved.value,
        )
    fresh = check_snapshot_freshness(snapshot, decision_at=decision_at)
    if is_refusal(fresh):
        return fresh
    return Ok(snapshot)


def refuse_bot_consumer(consumer: object) -> Result[None]:
    """Bots never receive the market-condition / signal snapshot (DEC-0230)."""
    token = clean_token(consumer) or repr(consumer)
    return policy(
        "consumer",
        "the signal snapshot dispatches to the Book door and the KSA only; "
        "bots never receive the market-condition snapshot",
        consumer=token,
        allowed=[member.value for member in GovernedConsumer],
    )


def _coerce_readiness(value: object) -> ProducerReadiness | TypedRefusal:
    if isinstance(value, ProducerReadiness):
        return value
    if isinstance(value, str):
        try:
            return ProducerReadiness(value)
        except ValueError:
            pass
    return invalid(
        "readiness",
        "producer readiness is ok|not_ready|unavailable|stale|refused",
        given=repr(value),
        allowed=[member.value for member in ProducerReadiness],
    )


def _coerce_feed_state(value: object) -> CanonicalFeedState | TypedRefusal:
    if isinstance(value, CanonicalFeedState):
        return value
    if isinstance(value, str):
        try:
            return CanonicalFeedState(value)
        except ValueError:
            pass
    return invalid(
        "feed_state",
        "canonical feed_state is live|degraded|dead",
        given=repr(value),
        allowed=[member.value for member in CanonicalFeedState],
    )


def _coerce_consumer(value: object) -> GovernedConsumer | TypedRefusal:
    if isinstance(value, GovernedConsumer):
        return value
    if isinstance(value, str):
        try:
            return GovernedConsumer(value)
        except ValueError:
            return policy(
                "consumer",
                "the signal snapshot dispatches to the Book door and the KSA only; "
                "bots never receive the market-condition snapshot",
                consumer=value,
                allowed=[member.value for member in GovernedConsumer],
            )
    return invalid(
        "consumer",
        "consumer is book_door|ksa",
        given=repr(value),
    )


def _coerce_lane(value: object) -> SnapshotLane | TypedRefusal:
    if isinstance(value, SnapshotLane):
        return value
    token = clean_token(value)
    if token is not None:
        try:
            return SnapshotLane(token)
        except ValueError:
            pass
    return invalid(
        "lane",
        "snapshot lane is governed|shadow",
        given=repr(value),
        allowed=[member.value for member in SnapshotLane],
    )


def _coerce_producer_slots(
    value: object,
    *,
    require_sqs: bool = True,
) -> dict[str, ProducerSlot] | TypedRefusal:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        return invalid(
            "producers",
            "producers is a collection of ProducerSlot values with unique producer ids",
            given=repr(value),
        )
    if isinstance(value, Mapping):
        return invalid(
            "producers",
            "pass an ordered collection of ProducerSlot values, not a mapping",
        )
    slots: dict[str, ProducerSlot] = {}
    for item in cast("Iterable[object]", value):
        if not isinstance(item, ProducerSlot):
            return invalid(
                "producers",
                "each producer is a ProducerSlot",
                given=repr(item),
            )
        if item.producer_id in slots:
            return invalid(
                "producers",
                "exactly one value/marker per producer id — duplicate refused",
                producer_id=item.producer_id,
            )
        slots[item.producer_id] = item
    if require_sqs and SQS_PRODUCER_ID not in slots:
        return invalid(
            "producers",
            "the signal snapshot carries the SQS producer slot (one value per instant)",
        )
    return slots


def _coerce_sensor_list(value: object) -> tuple[str, ...] | TypedRefusal:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "degraded_sensors",
            "degraded_sensors is a collection of opaque sensor tokens",
            given=type(cast("object", value)).__name__,
        )
    items: list[str] = []
    for item in cast("Iterable[object]", value):
        token = clean_token(item)
        if token is None:
            return invalid(
                "degraded_sensors",
                "each degraded sensor is a non-empty opaque token",
                given=repr(item),
            )
        items.append(token)
    return tuple(items)
