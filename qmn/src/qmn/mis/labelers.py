"""Six rule-based MIS labelers and the governed snapshot fold (Story 26.17).

identity, spread-state, gap-event, feed-state, SQS, and degraded-sensors. SQS is
the Spread Quality Sensor (AD-39): ``score = baseline ÷ live spread``. Every
producer reads as-of the slice frontier, never wall-now; late work publishes
``not_ready`` rather than a late number (DEC-0153, DEC-0204).
"""

from __future__ import annotations

from typing import Final

from qmf.core import (
    Duration,
    ExactRational,
    Ok,
    PriceDelta,
    Result,
    TypedRefusal,
    UnitKind,
    is_refusal,
)

from qmn.mis._refuse import invalid, policy
from qmn.mis.catalog import (
    DEGRADED_SENSORS_PRODUCER_ID,
    FEED_STATE_PRODUCER_ID,
    GAP_EVENT_PRODUCER_ID,
    IDENTITY_PRODUCER_ID,
    LIQUIDITY_STRESS_PRODUCER_ID,
    SPREAD_STATE_PRODUCER_ID,
    V1_GOVERNED_PRODUCER_IDS,
    ConfiguredMisProducer,
    FrontierFrame,
    MisProducerCatalog,
    ProducerEmission,
    SpreadState,
    SqsBaselineArtifact,
)
from qmn.mis.liquidity import evaluate_liquidity_stress
from qmn.mis.signal_snapshot import (
    SQS_PRODUCER_ID,
    CanonicalFeedState,
    ProducerReadiness,
    ProducerSlot,
    SignalSnapshot,
    SqsReading,
    mint_signal_snapshot,
    sqs_baseline_key,
)

__all__ = [
    "LABELERS_SURFACE",
    "SQS_TICK_CADENCES",
    "assemble_governed_snapshot",
    "evaluate_degraded_sensors",
    "evaluate_feed_state",
    "evaluate_gap_event",
    "evaluate_identity",
    "evaluate_mis_producer",
    "evaluate_spread_state",
    "evaluate_sqs",
    "live_spread",
    "require_frontier_bound",
]

LABELERS_SURFACE: Final[str] = "qmn.mis.labelers"
SQS_TICK_CADENCES: Final[frozenset[str]] = frozenset({"tick", "quote"})
_BAR_CADENCE: Final[str] = "bar"


def evaluate_mis_producer(
    producer: object,
    frame: object,
    *,
    sqs_baseline: object = None,
    liquidity_fit: object = None,
    decision_freshness_bound: object = None,
) -> Result[ProducerEmission]:
    """Dispatch one configured V1 producer at the frontier."""
    if not isinstance(producer, ConfiguredMisProducer):
        return invalid(
            "producer",
            "evaluation takes a ConfiguredMisProducer",
            given=type(producer).__name__,
        )
    bound = require_frontier_bound(producer, frame, decision_freshness_bound)
    if is_refusal(bound):
        return bound
    if bound.value is not None:
        return Ok(bound.value)
    pid = producer.producer_id
    if pid == IDENTITY_PRODUCER_ID:
        return evaluate_identity(producer, frame)
    if pid == SPREAD_STATE_PRODUCER_ID:
        return evaluate_spread_state(producer, frame)
    if pid == GAP_EVENT_PRODUCER_ID:
        return evaluate_gap_event(producer, frame)
    if pid == FEED_STATE_PRODUCER_ID:
        return evaluate_feed_state(producer, frame)
    if pid == SQS_PRODUCER_ID:
        return evaluate_sqs(
            producer,
            frame,
            baseline=sqs_baseline,
            decision_freshness_bound=decision_freshness_bound,
        )
    if pid == DEGRADED_SENSORS_PRODUCER_ID:
        return evaluate_degraded_sensors(producer, frame)
    if pid == LIQUIDITY_STRESS_PRODUCER_ID:
        return evaluate_liquidity_stress(producer, frame, fit=liquidity_fit)
    return invalid(
        "producer_id",
        "unknown governed MIS producer",
        given=pid,
        allowed=list(V1_GOVERNED_PRODUCER_IDS),
    )


def require_frontier_bound(
    producer: ConfiguredMisProducer,
    frame: object,
    decision_freshness_bound: object,
) -> Result[ProducerEmission | None]:
    """Refuse look-ahead; publish not_ready/stale rather than a late value."""
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "evaluation reads a FrontierFrame", given=type(frame).__name__)
    if producer.producer_id in {IDENTITY_PRODUCER_ID, DEGRADED_SENSORS_PRODUCER_ID}:
        return Ok(None)
    if frame.known_at is not None and frame.known_at.value_ns > frame.frontier_instant.value_ns:
        return policy(
            "known_at",
            "producers read as-of the slice frontier instant; a known-at after "
            "the frontier is look-ahead and is refused",
            known_at_ns=frame.known_at.value_ns,
            frontier_ns=frame.frontier_instant.value_ns,
        )
    # SQS owns its sentinel (stale/not_ready + hard block) inside evaluate_sqs.
    if producer.producer_id == SQS_PRODUCER_ID:
        return Ok(None)
    if frame.known_at is None:
        return Ok(_not_ready(producer, "unbounded-to-frontier"))
    if decision_freshness_bound is None:
        return Ok(None)
    if not isinstance(decision_freshness_bound, Duration):
        return invalid(
            "decision_freshness_bound",
            "freshness is a Duration; no second bound is invented",
            given=repr(decision_freshness_bound),
        )
    age = frame.frontier_instant.difference(frame.known_at)
    if is_refusal(age):
        return age
    if age.value.value_ns > decision_freshness_bound.value_ns:
        return Ok(_not_ready(producer, "cannot-publish-inside-bound"))
    return Ok(None)


def evaluate_identity(producer: object, frame: object) -> Result[ProducerEmission]:
    """Stamp the compute-once (instrument, resolution, version) identity key."""
    checked = _require_configured(producer, IDENTITY_PRODUCER_ID)
    if is_refusal(checked):
        return checked
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "evaluation reads a FrontierFrame", given=type(frame).__name__)
    key = (
        f"{frame.instrument.venue.value}:{frame.instrument.symbol}:"
        f"{frame.resolution}:{checked.value.version}"
    )
    return Ok(
        ProducerEmission(
            producer_id=IDENTITY_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version=checked.value.version,
            marker_detail=key,
            identity_key=key,
        )
    )


def evaluate_spread_state(producer: object, frame: object) -> Result[ProducerEmission]:
    """Rule-based ``normal | elevated | extreme`` from declared point thresholds."""
    configured = _require_configured(producer, SPREAD_STATE_PRODUCER_ID)
    if is_refusal(configured):
        return configured
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "evaluation reads a FrontierFrame", given=type(frame).__name__)
    params = configured.value.parameters
    normal_max = _as_ratio(params.get("normal_max"), "normal_max")
    if is_refusal(normal_max):
        return normal_max
    elevated_max = _as_ratio(params.get("elevated_max"), "elevated_max")
    if is_refusal(elevated_max):
        return elevated_max
    if normal_max.value.as_fraction() > elevated_max.value.as_fraction():
        return invalid(
            "parameters",
            "normal_max must be at or below elevated_max",
        )
    points = frame.spread_points
    if points is None:
        spread = live_spread(frame)
        if is_refusal(spread):
            return spread
        if spread.value is None:
            return Ok(_not_ready(configured.value, "spread-missing"))
        if frame.pip is None:
            return invalid(
                "pip",
                "spread-state converts a PriceDelta through the instrument pip "
                "from metadata; none was supplied (unavailable dependency at "
                "the call site must not be invented here)",
            )
        pip_points = spread.value.in_pips(frame.pip)
        if is_refusal(pip_points):
            return pip_points
        points = pip_points.value
    if points.unit_kind not in {UnitKind.DIMENSIONLESS_RATIO, UnitKind.COUNT}:
        return invalid(
            "spread_points",
            "spread points are a dimensionless ratio or count",
            given=points.unit_kind.value,
        )
    value = points.as_fraction()
    if value <= normal_max.value.as_fraction():
        state = SpreadState.NORMAL
    elif value <= elevated_max.value.as_fraction():
        state = SpreadState.ELEVATED
    else:
        state = SpreadState.EXTREME
    return Ok(
        ProducerEmission(
            producer_id=SPREAD_STATE_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version=configured.value.version,
            marker_detail=state.value,
            spread_state=state,
        )
    )


def evaluate_gap_event(producer: object, frame: object) -> Result[ProducerEmission]:
    """True when tick gap or bar-gap count exceeds the declared maxima."""
    configured = _require_configured(producer, GAP_EVENT_PRODUCER_ID)
    if is_refusal(configured):
        return configured
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "evaluation reads a FrontierFrame", given=type(frame).__name__)
    params = configured.value.parameters
    max_tick = params.get("max_expected_tick_gap")
    max_bars = params.get("max_expected_bar_gap_count")
    if not isinstance(max_tick, Duration):
        return invalid(
            "max_expected_tick_gap",
            "gap-event max tick gap is a Duration",
            given=repr(max_tick),
        )
    if not isinstance(max_bars, int) or isinstance(max_bars, bool) or max_bars < 0:
        return invalid(
            "max_expected_bar_gap_count",
            "max expected bar-gap count is a non-negative integer",
            given=repr(max_bars),
        )
    tick_gap: Duration | None = None
    if frame.last_tick_at is not None:
        delta = frame.frontier_instant.difference(frame.last_tick_at)
        if is_refusal(delta):
            return delta
        tick_gap = delta.value
    bar_gap = frame.bar_gap_count
    if tick_gap is None and bar_gap is None:
        return Ok(_not_ready(configured.value, "gap-observation-missing"))
    gap = False
    if tick_gap is not None and tick_gap.value_ns > max_tick.value_ns:
        gap = True
    if bar_gap is not None and bar_gap > max_bars:
        gap = True
    return Ok(
        ProducerEmission(
            producer_id=GAP_EVENT_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version=configured.value.version,
            marker_detail="true" if gap else "false",
            gap_event=gap,
        )
    )


def evaluate_feed_state(producer: object, frame: object) -> Result[ProducerEmission]:
    """Canonical ``live | degraded | dead`` from declared age bounds (DEC-0204)."""
    configured = _require_configured(producer, FEED_STATE_PRODUCER_ID)
    if is_refusal(configured):
        return configured
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "evaluation reads a FrontierFrame", given=type(frame).__name__)
    params = configured.value.parameters
    live_max = params.get("live_max_age")
    degraded_max = params.get("degraded_max_age")
    if not isinstance(live_max, Duration) or not isinstance(degraded_max, Duration):
        return invalid(
            "parameters",
            "feed-state live_max_age and degraded_max_age are Durations",
        )
    if live_max.value_ns > degraded_max.value_ns:
        return invalid(
            "parameters",
            "live_max_age must be at or below degraded_max_age",
        )
    if frame.last_tick_at is None:
        return Ok(_not_ready(configured.value, "feed-age-unbounded"))
    age = frame.frontier_instant.difference(frame.last_tick_at)
    if is_refusal(age):
        return age
    age_ns = age.value.value_ns
    if age_ns <= live_max.value_ns:
        state = CanonicalFeedState.LIVE
    elif age_ns <= degraded_max.value_ns:
        state = CanonicalFeedState.DEGRADED
    else:
        state = CanonicalFeedState.DEAD
    return Ok(
        ProducerEmission(
            producer_id=FEED_STATE_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version=configured.value.version,
            marker_detail=state.value,
            feed_state=state,
        )
    )


def evaluate_sqs(
    producer: object,
    frame: object,
    *,
    baseline: object,
    decision_freshness_bound: object = None,
) -> Result[ProducerEmission]:
    """AD-39 Spread Quality Sensor: baseline ÷ live spread, conservative sentinel."""
    configured = _require_configured(producer, SQS_PRODUCER_ID)
    if is_refusal(configured):
        return configured
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "evaluation reads a FrontierFrame", given=type(frame).__name__)
    params = configured.value.parameters
    cadence = params.get("sample_cadence")
    cadence_token = cadence if isinstance(cadence, str) else frame.sample_cadence
    if cadence_token == _BAR_CADENCE:
        return policy(
            "sample_cadence",
            "a bar-sampled SQS is refused at the door, never blocked through (DEC-0153)",
            sample_cadence=cadence_token,
        )
    if cadence_token is None or cadence_token not in SQS_TICK_CADENCES:
        return invalid(
            "sample_cadence",
            "SQS live-spread cadence is tick or quote",
            given=repr(cadence_token),
            allowed=sorted(SQS_TICK_CADENCES),
        )
    horizon = params.get("staleness_horizon")
    if not isinstance(horizon, Duration):
        return invalid(
            "staleness_horizon",
            "SQS staleness_horizon is a Duration",
            given=repr(horizon),
        )
    bound = params.get("decision_freshness_bound", decision_freshness_bound)
    if not isinstance(bound, Duration):
        return invalid(
            "decision_freshness_bound",
            "SQS freshness is the Book decision_freshness_bound — mandatory, "
            "no second bound, no invented default (DEC-0153)",
            given=repr(bound),
        )
    if horizon.value_ns > bound.value_ns:
        return invalid(
            "staleness_horizon",
            "SQS staleness_horizon must not exceed decision_freshness_bound",
            horizon_ns=horizon.value_ns,
            bound_ns=bound.value_ns,
        )
    if frame.known_at is None:
        return _sqs_non_ok(
            configured.value,
            frame,
            ProducerReadiness.NOT_READY,
            "unbounded-to-frontier",
        )
    age = frame.frontier_instant.difference(frame.known_at)
    if is_refusal(age):
        return age
    limit_ns = min(horizon.value_ns, bound.value_ns)
    if age.value.value_ns > limit_ns:
        return _sqs_non_ok(
            configured.value,
            frame,
            ProducerReadiness.STALE,
            "sqs-stale",
        )
    if baseline is None:
        return _sqs_non_ok(
            configured.value,
            frame,
            ProducerReadiness.NOT_READY,
            "baseline-missing",
        )
    if not isinstance(baseline, SqsBaselineArtifact):
        return invalid(
            "baseline",
            "SQS consumes a fingerprinted SqsBaselineArtifact",
            given=type(baseline).__name__,
        )
    artifact = baseline
    key = artifact.key
    if key.environment != frame.environment:
        return policy(
            "environment",
            "a demo-conditioned SQS baseline never satisfies a live environment (DEC-0230)",
            baseline_environment=key.environment,
            frame_environment=frame.environment,
        )
    if key.instrument != frame.instrument:
        return invalid(
            "instrument",
            "SQS baseline instrument must match the frontier frame",
        )
    threshold = _as_ratio(params.get("hard_block_threshold"), "hard_block_threshold")
    if is_refusal(threshold):
        return threshold
    band = _as_ratio(params.get("hysteresis_band"), "hysteresis_band")
    if is_refusal(band):
        return band
    guard = _as_ratio(params.get("outlier_guard_multiple"), "outlier_guard_multiple")
    if is_refusal(guard):
        return guard
    spread = live_spread(frame)
    if is_refusal(spread):
        return spread
    if spread.value is None or spread.value.value == 0:
        return _sqs_non_ok(
            configured.value,
            frame,
            ProducerReadiness.UNAVAILABLE,
            "live-spread-undefined",
        )
    average = artifact.average_spread
    if average.instrument != frame.instrument:
        return invalid("average_spread", "baseline spread is a different instrument")
    if average.value == 0:
        return _sqs_non_ok(
            configured.value,
            frame,
            ProducerReadiness.UNAVAILABLE,
            "baseline-undefined",
        )
    ratio = average.as_fraction() / spread.value.as_fraction()
    score = ExactRational.try_create(
        ratio.numerator, ratio.denominator, UnitKind.DIMENSIONLESS_RATIO
    )
    if is_refusal(score):
        return score
    hard_block = _sqs_hard_block(
        score=score.value,
        threshold=threshold.value,
        band=band.value,
        previous=frame.previous_sqs_hard_block,
        live_spread=spread.value,
        average=average,
        dispersion=artifact.dispersion,
        guard_multiple=guard.value,
    )
    if is_refusal(hard_block):
        return hard_block
    reading = SqsReading.try_create(
        key,
        readiness=ProducerReadiness.OK,
        labeler_version=configured.value.version,
        score=score.value,
        hard_block=hard_block.value,
    )
    if is_refusal(reading):
        return reading
    return Ok(
        ProducerEmission(
            producer_id=SQS_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version=configured.value.version,
            marker_detail="hard-block" if hard_block.value else "pass",
            sqs=reading.value,
        )
    )


def evaluate_degraded_sensors(producer: object, frame: object) -> Result[ProducerEmission]:
    """List peer producers whose readiness is not ``ok`` (DEC-0042 / DEC-0204)."""
    configured = _require_configured(producer, DEGRADED_SENSORS_PRODUCER_ID)
    if is_refusal(configured):
        return configured
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "evaluation reads a FrontierFrame", given=type(frame).__name__)
    degraded: list[str] = []
    for emission in frame.peer_emissions:
        readiness = emission.readiness
        token = readiness.value if isinstance(readiness, ProducerReadiness) else str(readiness)
        if token != ProducerReadiness.OK.value:
            degraded.append(emission.producer_id)
    return Ok(
        ProducerEmission(
            producer_id=DEGRADED_SENSORS_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version=configured.value.version,
            marker_detail=",".join(degraded) if degraded else "none",
            degraded_sensors=tuple(degraded),
        )
    )


def assemble_governed_snapshot(
    catalog: object,
    frame: object,
    *,
    decision_freshness_bound: object,
    sqs_baseline: object = None,
    liquidity_fit: object = None,
) -> Result[SignalSnapshot]:
    """Evaluate every registered V1 producer and mint one immutable snapshot."""
    if not isinstance(catalog, MisProducerCatalog):
        return invalid(
            "catalog",
            "assemble reads a MisProducerCatalog",
            given=type(catalog).__name__,
        )
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "assemble reads a FrontierFrame", given=type(frame).__name__)
    if SQS_PRODUCER_ID not in catalog.producers:
        return invalid(
            "catalog",
            "the signal snapshot carries the SQS producer slot",
        )
    emissions: list[ProducerEmission] = []
    remaining = [
        pid
        for pid in V1_GOVERNED_PRODUCER_IDS
        if pid in catalog.producers and pid != DEGRADED_SENSORS_PRODUCER_ID
    ]
    for producer_id in remaining:
        emission = evaluate_mis_producer(
            catalog.producers[producer_id],
            frame,
            sqs_baseline=sqs_baseline,
            liquidity_fit=liquidity_fit,
            decision_freshness_bound=decision_freshness_bound,
        )
        if is_refusal(emission):
            return emission
        emissions.append(emission.value)
    degraded_frame = FrontierFrame(
        frontier_instant=frame.frontier_instant,
        instrument=frame.instrument,
        environment=frame.environment,
        resolution=frame.resolution,
        known_at=frame.known_at,
        bid=frame.bid,
        ask=frame.ask,
        spread=frame.spread,
        pip=frame.pip,
        last_tick_at=frame.last_tick_at,
        bar_gap_count=frame.bar_gap_count,
        sample_cadence=frame.sample_cadence,
        previous_sqs_hard_block=frame.previous_sqs_hard_block,
        current_depth=frame.current_depth,
        spread_points=frame.spread_points,
        current_spread_ticks=frame.current_spread_ticks,
        peer_emissions=tuple(emissions),
    )
    if DEGRADED_SENSORS_PRODUCER_ID in catalog.producers:
        degraded = evaluate_degraded_sensors(
            catalog.producers[DEGRADED_SENSORS_PRODUCER_ID],
            degraded_frame,
        )
        if is_refusal(degraded):
            return degraded
        emissions.append(degraded.value)
    slots: list[ProducerSlot] = []
    feed_state = CanonicalFeedState.DEAD
    sensors: tuple[str, ...] = ()
    for emission in emissions:
        slot = _emission_to_slot(emission)
        if is_refusal(slot):
            return slot
        slots.append(slot.value)
        if (
            emission.producer_id == FEED_STATE_PRODUCER_ID
            and emission.readiness is ProducerReadiness.OK
            and isinstance(emission.feed_state, CanonicalFeedState)
        ):
            feed_state = emission.feed_state
        if (
            emission.producer_id == DEGRADED_SENSORS_PRODUCER_ID
            and emission.degraded_sensors is not None
        ):
            sensors = emission.degraded_sensors
    return mint_signal_snapshot(
        frontier_instant=frame.frontier_instant,
        environment=frame.environment,
        feed_state=feed_state,
        producers=tuple(slots),
        decision_freshness_bound=decision_freshness_bound,
        degraded_sensors=sensors,
    )


def live_spread(frame: FrontierFrame) -> Result[PriceDelta | None]:
    """Ask − bid when both sides are present; else the declared spread."""
    if frame.spread is not None:
        return Ok(frame.spread)
    if frame.bid is not None and frame.ask is not None:
        delta = frame.ask.subtract(frame.bid)
        if isinstance(delta, TypedRefusal):
            return delta
        return Ok(delta.value)
    return Ok(None)


def _sqs_hard_block(
    *,
    score: ExactRational,
    threshold: ExactRational,
    band: ExactRational,
    previous: bool | None,
    live_spread: PriceDelta,
    average: PriceDelta,
    dispersion: object,
    guard_multiple: ExactRational,
) -> Result[bool]:
    """At-or-above threshold passes; strictly below blocks. Hysteresis on clear."""
    score_q = score.as_fraction()
    threshold_q = threshold.as_fraction()
    blocked = score_q < threshold_q
    if not blocked and previous is True:
        clear_line = threshold_q + band.as_fraction()
        if score_q < clear_line:
            blocked = True
        elif isinstance(dispersion, PriceDelta) and dispersion.value != 0:
            deviation = abs(live_spread.as_fraction() - average.as_fraction())
            limit = guard_multiple.as_fraction() * dispersion.as_fraction()
            if deviation > limit:
                # Outlier excluded from the re-crossing test — stay blocked.
                blocked = True
    return Ok(blocked)


def _sqs_non_ok(
    producer: ConfiguredMisProducer,
    frame: FrontierFrame,
    readiness: ProducerReadiness,
    marker: str,
) -> Result[ProducerEmission]:
    key = sqs_baseline_key(frame.instrument.venue, frame.environment, frame.instrument)
    if is_refusal(key):
        return key
    reading = SqsReading.try_create(
        key.value,
        readiness=readiness,
        labeler_version=producer.version,
    )
    if is_refusal(reading):
        return reading
    return Ok(
        ProducerEmission(
            producer_id=SQS_PRODUCER_ID,
            readiness=readiness,
            labeler_version=producer.version,
            marker_detail=marker,
            sqs=reading.value,
        )
    )


def _emission_to_slot(emission: ProducerEmission) -> Result[ProducerSlot]:
    return ProducerSlot.try_create(
        emission.producer_id,
        readiness=emission.readiness,
        labeler_version=emission.labeler_version,
        sqs=emission.sqs,
        marker_detail=emission.marker_detail,
    )


def _require_configured(producer: object, expected: str) -> Result[ConfiguredMisProducer]:
    if not isinstance(producer, ConfiguredMisProducer):
        return invalid(
            "producer",
            "evaluation takes a ConfiguredMisProducer",
            given=type(producer).__name__,
        )
    if producer.producer_id != expected:
        return invalid(
            "producer_id",
            f"this evaluator is {expected}",
            given=producer.producer_id,
        )
    return Ok(producer)


def _as_ratio(value: object, field: str) -> Result[ExactRational]:
    if not isinstance(value, ExactRational):
        return invalid(
            field,
            f"{field} is an ExactRational (no invented default)",
            given=repr(value),
        )
    if value.unit_kind not in {UnitKind.DIMENSIONLESS_RATIO, UnitKind.COUNT}:
        return invalid(
            field,
            f"{field} unit-kind is dimensionless-ratio or count",
            given=value.unit_kind.value,
        )
    return Ok(value)


def _not_ready(producer: ConfiguredMisProducer, marker: str) -> ProducerEmission:
    return ProducerEmission(
        producer_id=producer.producer_id,
        readiness=ProducerReadiness.NOT_READY,
        labeler_version=producer.version,
        marker_detail=marker,
    )
