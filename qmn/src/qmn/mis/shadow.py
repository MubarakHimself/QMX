"""Zero-authority MIS shadow seam (Story 26.18 / TN-19 / DEC-0204).

Candidate labelers publish through a distinct WriterId and manifest prefix onto
``shadow_composition_fp``. Comparison is an ungoverned diagnostic on the
evidence channel. Candidates never reach the Book door, KSA, bot, venue, or
any command/control fold. Missing, late, refused, or disagreeing candidate
output is recorded with source identity and instant without substituting
governed output or delaying the slice. The lane can be disabled or removed
without changing node decisions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence, Sized
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Duration,
    Fingerprint,
    Instant,
    Ok,
    Result,
    TypedRefusal,
    WriterId,
    is_refusal,
)

from qmn.mis._refuse import clean_token, invalid, policy
from qmn.mis.catalog import (
    DEGRADED_SENSORS_PRODUCER_ID,
    FEED_STATE_PRODUCER_ID,
    ConfiguredMisProducer,
    FormulaNature,
    FrontierFrame,
    ProducerEmission,
    refuse_trained_regime_classifier,
    refuse_unauthoritative_candidate,
)
from qmn.mis.labelers import evaluate_mis_producer
from qmn.mis.signal_snapshot import (
    SQS_PRODUCER_ID,
    CanonicalFeedState,
    GovernedConsumer,
    ProducerReadiness,
    ProducerSlot,
    SignalSnapshot,
    SnapshotLane,
    SqsReading,
    mint_signal_snapshot,
    sqs_baseline_key,
)

__all__ = [
    "MONEY_PATH_CONSUMERS",
    "SHADOW_COMPARISON_PROJECTION_KEY",
    "SHADOW_COUNTED_TOWARD_MAX_SLICE_LATENCY",
    "SHADOW_HAS_MONEY_PATH_AUTHORITY",
    "SHADOW_ISOLATION_FAILURE_ID",
    "SHADOW_LANE_PUBLISH_BOUND_VARIABLE",
    "SHADOW_MANIFEST_PREFIX",
    "SHADOW_SURFACE",
    "SHADOW_WRITER_ROLE",
    "SHADOW_WRITER_STREAM",
    "ShadowCandidateCatalog",
    "ShadowComparisonRecord",
    "ShadowCondition",
    "ShadowEvaluation",
    "ShadowLaneConfig",
    "ShadowPublication",
    "allocate_shadow_writer",
    "assemble_shadow_snapshot",
    "compare_shadow_to_governed",
    "empty_shadow_catalog",
    "evaluate_shadow_lane",
    "publish_shadow_snapshot",
    "refuse_shadow_governed_wiring",
    "refuse_shadow_light_claim",
    "refuse_shadow_money_path",
    "register_shadow_candidate",
    "shadow_candidate_identities",
    "shadow_comparison_projection",
    "shadow_writer_stream_pair",
]

SHADOW_SURFACE: Final[str] = "qmn.mis.shadow"
SHADOW_WRITER_ROLE: Final[str] = "mis-shadow"
SHADOW_WRITER_STREAM: Final[str] = "shadow-snapshot"
SHADOW_MANIFEST_PREFIX: Final[str] = "mis/shadow/"
SHADOW_LANE_PUBLISH_BOUND_VARIABLE: Final[str] = "shadow_lane_publish_bound"
SHADOW_COMPARISON_PROJECTION_KEY: Final[str] = "mis_shadow_comparison"
SHADOW_ISOLATION_FAILURE_ID: Final[str] = "compose.shadow_isolation"
SHADOW_COUNTED_TOWARD_MAX_SLICE_LATENCY: Final[bool] = False
SHADOW_HAS_MONEY_PATH_AUTHORITY: Final[bool] = False
_DATA_QUALITY_EVENT_TYPE: Final[str] = "data quality"

MONEY_PATH_CONSUMERS: Final[frozenset[str]] = frozenset(
    {
        GovernedConsumer.BOOK_DOOR.value,
        GovernedConsumer.KSA.value,
        "bot",
        "venue",
        "venue_client",
        "command",
        "control",
        "command_fold",
        "control_fold",
        "seat",
    }
)


class ShadowCondition(StrEnum):
    """Per-instant comparison outcome — diagnostic, never a decision input."""

    AGREE = "agree"
    DISAGREE = "disagree"
    MISSING = "missing"
    LATE = "late"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class ShadowCandidateCatalog:
    """Candidate-role catalog. Identity never enters governed composition_fp."""

    candidates: Mapping[str, ConfiguredMisProducer]

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", MappingProxyType(dict(self.candidates)))

    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.candidates))


@dataclass(frozen=True, slots=True)
class ShadowLaneConfig:
    """Enable flag plus the registry-resolved publish bound (never invented)."""

    enabled: bool
    publish_bound: Duration

    @classmethod
    def try_create(
        cls,
        *,
        enabled: object,
        publish_bound: object,
    ) -> Result[ShadowLaneConfig]:
        if not isinstance(enabled, bool):
            return invalid(
                "enabled",
                "shadow lane enabled is a bool; disabling must not change decisions",
                given=repr(enabled),
            )
        if not isinstance(publish_bound, Duration):
            return invalid(
                SHADOW_LANE_PUBLISH_BOUND_VARIABLE,
                "shadow_lane_publish_bound is a resolved Duration; blank refuses "
                "to compose (blocks-boot)",
                given=repr(publish_bound),
            )
        if publish_bound.value_ns < 0:
            return invalid(
                SHADOW_LANE_PUBLISH_BOUND_VARIABLE,
                "shadow_lane_publish_bound is a non-negative Duration",
                given=publish_bound.value_ns,
            )
        return Ok(cls(enabled=enabled, publish_bound=publish_bound))


@dataclass(frozen=True, slots=True)
class ShadowPublication:
    """One shadow-lane snapshot write — own writer, prefix, and fingerprint."""

    snapshot: SignalSnapshot
    writer: WriterId
    manifest_prefix: str
    shadow_composition_fp: Fingerprint
    sequence: int
    counted_toward_max_slice_latency: bool = False
    authority: str = "none"

    def as_journal_row(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "class": "shadow-snapshot",
                "event_kind": "shadow-snapshot",
                "writer": _writer_fields(self.writer),
                "manifest_prefix": self.manifest_prefix,
                "shadow_composition_fp": self.shadow_composition_fp.value,
                "sequence": self.sequence,
                "frontier_instant_ns": self.snapshot.frontier_instant.value_ns,
                "snapshot": self.snapshot.fp1_identity(),
                "counted_toward_max_slice_latency": self.counted_toward_max_slice_latency,
                "authority": self.authority,
                "gating": False,
                "authorizes": False,
                "publishes": True,
                "acts": False,
            }
        )


@dataclass(frozen=True, slots=True)
class ShadowComparisonRecord:
    """One producer-id comparison at one frontier instant (ungoverned)."""

    producer_id: str
    source_identity: str
    frontier_instant: Instant
    condition: ShadowCondition
    governed_readiness: str | None = None
    candidate_readiness: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "producer_id": self.producer_id,
            "source_identity": self.source_identity,
            "frontier_instant_ns": self.frontier_instant.value_ns,
            "condition": self.condition.value,
            "gating": False,
            "authorizes": False,
            "substitutes_governed": False,
        }
        if self.governed_readiness is not None:
            body["governed_readiness"] = self.governed_readiness
        if self.candidate_readiness is not None:
            body["candidate_readiness"] = self.candidate_readiness
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class ShadowEvaluation:
    """Slice-local shadow outcome. Governed snapshot is never rewritten."""

    governed: SignalSnapshot
    publication: ShadowPublication | None
    comparison: tuple[ShadowComparisonRecord, ...]
    data_quality: tuple[Mapping[str, object], ...]
    lane_enabled: bool
    slice_delayed: bool
    counted_toward_max_slice_latency: bool
    substituted_governed: bool

    def as_projection(self) -> Mapping[str, object]:
        return shadow_comparison_projection(self)


def empty_shadow_catalog() -> ShadowCandidateCatalog:
    """An empty candidate catalog — removing it cannot change node decisions."""
    return ShadowCandidateCatalog(candidates={})


def register_shadow_candidate(
    catalog: object,
    producer: object,
) -> Result[ShadowCandidateCatalog]:
    """Register a candidate-role producer. Never mutates the governed catalog."""
    if not isinstance(catalog, ShadowCandidateCatalog):
        return invalid(
            "catalog",
            "candidates register onto a ShadowCandidateCatalog",
            given=type(catalog).__name__,
        )
    if not isinstance(producer, ConfiguredMisProducer):
        return invalid(
            "producer",
            "shadow registration takes a ConfiguredMisProducer",
            given=type(producer).__name__,
        )
    trained = refuse_trained_regime_classifier(producer.producer_id)
    if is_refusal(trained):
        return trained
    trained_formula = refuse_trained_regime_classifier(producer.formula_id)
    if is_refusal(trained_formula):
        return trained_formula
    unauth = refuse_unauthoritative_candidate(producer.producer_id)
    if is_refusal(unauth):
        return unauth
    if producer.nature is FormulaNature.TRAINED:
        return policy(
            "nature",
            "trained producers are not selected, trained, registered, or bound "
            "in V1; the shadow seam holds untrained candidates only (DEC-0262)",
            producer_id=producer.producer_id,
        )
    light = refuse_shadow_light_claim(producer)
    if is_refusal(light):
        return light
    if producer.producer_id in catalog.candidates:
        return invalid(
            "producer_id",
            "exactly one shadow registration per producer id",
            producer_id=producer.producer_id,
        )
    next_map = dict(catalog.candidates)
    next_map[producer.producer_id] = producer
    return Ok(ShadowCandidateCatalog(candidates=next_map))


def shadow_candidate_identities(catalog: object) -> Result[Mapping[str, str]]:
    """Distribution identities for ``shadow_composition_fp`` — never governed."""
    if not isinstance(catalog, ShadowCandidateCatalog):
        return invalid(
            "catalog",
            "shadow identities derive from a ShadowCandidateCatalog",
            given=type(catalog).__name__,
        )
    return Ok(
        MappingProxyType(
            {pid: producer.version for pid, producer in sorted(catalog.candidates.items())}
        )
    )


def shadow_writer_stream_pair() -> tuple[str, str]:
    """Compose ``(role, stream)`` pair — pairwise distinct from governed writers."""
    return (SHADOW_WRITER_ROLE, SHADOW_WRITER_STREAM)


def allocate_shadow_writer(*, machine: object, boot_epoch_id: object) -> Result[WriterId]:
    """Mint the shadow-lane WriterId. Compose still proves pairwise distinctness."""
    return WriterId.try_create(
        machine,
        SHADOW_WRITER_ROLE,
        SHADOW_WRITER_STREAM,
        boot_epoch_id,
    )


def refuse_shadow_light_claim(producer: object) -> Result[None]:
    """Candidates are heavy by construction (TN-19 / DEC-0204)."""
    if not isinstance(producer, ConfiguredMisProducer):
        return invalid(
            "producer",
            "a light-claim check reads a ConfiguredMisProducer",
            given=type(producer).__name__,
        )
    if producer.declared_budget is not None:
        return policy(
            "declared_budget",
            "candidate labelers are heavy by construction and never count toward "
            "max_slice_latency; a light claim is refused at the shadow seam",
            producer_id=producer.producer_id,
        )
    return Ok(None)


def refuse_shadow_money_path(consumer: object) -> Result[None]:
    """Candidate output has zero Book/KSA/bot/venue/command/control authority."""
    token = clean_token(consumer)
    if token is None:
        return invalid(
            "consumer",
            "a consumer name is a non-empty token",
            given=repr(consumer),
        )
    lowered = token.lower().replace("-", "_")
    if lowered in MONEY_PATH_CONSUMERS or token in MONEY_PATH_CONSUMERS:
        return policy(
            "consumer",
            "no candidate output reaches the Book door, KSA, bot, venue, or any "
            "command/control fold; the shadow lane is publish-only (DEC-0204)",
            consumer=token,
            failure_id=SHADOW_ISOLATION_FAILURE_ID,
            allowed=[],
        )
    return Ok(None)


def refuse_shadow_governed_wiring(wiring: object) -> Result[None]:
    """A composition that wires shadow output into a governed consumer refuses boot."""
    if wiring is None:
        return Ok(None)
    if (
        isinstance(wiring, (Mapping, Sequence))
        and not isinstance(wiring, (str, bytes))
        and len(cast("Sized", wiring)) == 0
    ):
        return Ok(None)
    if isinstance(wiring, Mapping):
        consumers: list[object] = list(cast("Mapping[object, object]", wiring).values())
    elif isinstance(wiring, (str, bytes)):
        consumers = [wiring]
    elif isinstance(wiring, Sequence):
        consumers = list(cast("Sequence[object]", wiring))
    elif isinstance(wiring, Iterable):
        consumers = list(cast("Iterable[object]", wiring))
    else:
        return invalid(
            "shadow_consumer_wiring",
            "wiring is a sequence of consumer names or a candidate->consumer map",
            given=type(wiring).__name__,
        )
    for consumer in consumers:
        refused = refuse_shadow_money_path(consumer)
        if is_refusal(refused):
            return refused
    return Ok(None)


def assemble_shadow_snapshot(
    catalog: object,
    frame: object,
    *,
    decision_freshness_bound: object,
    sqs_baseline: object = None,
    liquidity_fit: object = None,
) -> Result[SignalSnapshot]:
    """Evaluate candidates at the frontier. Refusals become refused slots."""
    if not isinstance(catalog, ShadowCandidateCatalog):
        return invalid(
            "catalog",
            "shadow assemble reads a ShadowCandidateCatalog",
            given=type(catalog).__name__,
        )
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "shadow assemble reads a FrontierFrame", given=type(frame).__name__)
    emissions: list[ProducerEmission] = []
    for producer_id in catalog.candidate_ids():
        producer = catalog.candidates[producer_id]
        emission = evaluate_mis_producer(
            producer,
            frame,
            sqs_baseline=sqs_baseline,
            liquidity_fit=liquidity_fit,
            decision_freshness_bound=decision_freshness_bound,
        )
        if is_refusal(emission):
            fallback = _refused_emission(
                producer,
                frame,
                str(emission.context.get("reason", "refused")),
            )
            emissions.append(fallback)
            continue
        emissions.append(emission.value)
    slots: list[ProducerSlot] = []
    feed_state = CanonicalFeedState.DEAD
    sensors: tuple[str, ...] = ()
    for emission in emissions:
        slot = _emission_to_slot(emission)
        if is_refusal(slot):
            marker = emission.marker_detail or "refused"
            refused_slot = ProducerSlot.try_create(
                emission.producer_id,
                readiness=ProducerReadiness.REFUSED,
                labeler_version=emission.labeler_version,
                marker_detail=marker,
            )
            if is_refusal(refused_slot):
                continue
            slots.append(refused_slot.value)
            continue
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
        lane=SnapshotLane.SHADOW,
    )


def publish_shadow_snapshot(
    snapshot: object,
    *,
    writer: object,
    shadow_composition_fp: object,
    sequence: object,
    journal_sink: object,
) -> Result[ShadowPublication]:
    """Write one shadow snapshot under the distinct WriterId and manifest prefix."""
    if not isinstance(snapshot, SignalSnapshot):
        return invalid(
            "snapshot",
            "shadow publication writes a SignalSnapshot",
            given=type(snapshot).__name__,
        )
    if snapshot.lane is not SnapshotLane.SHADOW:
        return policy(
            "lane",
            "the shadow stream writes only shadow-lane snapshots; a governed "
            "snapshot on this WriterId would re-identify money-path evidence",
            lane=snapshot.lane.value,
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "shadow publication writes under an allocated WriterId",
            given=type(writer).__name__,
        )
    if writer.role != SHADOW_WRITER_ROLE or writer.stream != SHADOW_WRITER_STREAM:
        return policy(
            "writer",
            "shadow publication uses the distinct mis-shadow WriterId, never a "
            "governed command, risk, adapter, or supervisor stream",
            role=writer.role,
            stream=writer.stream,
            expected_role=SHADOW_WRITER_ROLE,
            expected_stream=SHADOW_WRITER_STREAM,
        )
    if not isinstance(shadow_composition_fp, Fingerprint):
        return invalid(
            "shadow_composition_fp",
            "shadow publication stamps shadow_composition_fp, never composition_fp",
            given=type(shadow_composition_fp).__name__,
        )
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        return invalid(
            "sequence",
            "shadow sequence is a non-negative int, gapless per writer",
            given=repr(sequence),
        )
    publication = ShadowPublication(
        snapshot=snapshot,
        writer=writer,
        manifest_prefix=SHADOW_MANIFEST_PREFIX,
        shadow_composition_fp=shadow_composition_fp,
        sequence=sequence,
        counted_toward_max_slice_latency=SHADOW_COUNTED_TOWARD_MAX_SLICE_LATENCY,
        authority="none",
    )
    written = _append_journal(journal_sink, publication.as_journal_row())
    if is_refusal(written):
        return written
    return Ok(publication)


def compare_shadow_to_governed(
    governed: object,
    shadow: object,
    *,
    catalog: object = None,
    late_producer_ids: object = (),
) -> Result[tuple[ShadowComparisonRecord, ...]]:
    """Diff shadow against governed per producer id. Never rewrites governed."""
    if not isinstance(governed, SignalSnapshot):
        return invalid(
            "governed",
            "comparison reads the governed SignalSnapshot",
            given=type(governed).__name__,
        )
    if governed.lane is SnapshotLane.SHADOW:
        return policy(
            "governed",
            "comparison treats a governed-lane snapshot as the money-path side; "
            "a shadow snapshot cannot stand in for it",
        )
    shadow_snap: SignalSnapshot | None
    if shadow is None:
        shadow_snap = None
    elif isinstance(shadow, SignalSnapshot):
        shadow_snap = shadow
    else:
        return invalid(
            "shadow",
            "comparison reads a shadow SignalSnapshot or None",
            given=type(shadow).__name__,
        )
    late_ids = _token_set(late_producer_ids, "late_producer_ids")
    if isinstance(late_ids, TypedRefusal):
        return late_ids
    versions: dict[str, str] = {}
    if isinstance(catalog, ShadowCandidateCatalog):
        versions = {pid: row.version for pid, row in catalog.candidates.items()}
    governed_ids = set(governed.producers)
    shadow_ids: set[str] = set()
    if shadow_snap is not None:
        shadow_ids = set(shadow_snap.producers)
    candidate_ids: set[str] = set(versions) | shadow_ids | set(late_ids)
    records: list[ShadowComparisonRecord] = []
    for producer_id in sorted(governed_ids | candidate_ids):
        source = _source_identity(producer_id, versions, governed, shadow_snap)
        gov_slot = governed.producers.get(producer_id)
        sh_slot = None if shadow_snap is None else shadow_snap.producers.get(producer_id)
        gov_ready = None if gov_slot is None else gov_slot.readiness.value
        cand_ready = None if sh_slot is None else sh_slot.readiness.value
        if producer_id in late_ids:
            condition = ShadowCondition.LATE
        elif sh_slot is None:
            condition = ShadowCondition.MISSING
        elif sh_slot.readiness is ProducerReadiness.REFUSED:
            condition = ShadowCondition.REFUSED
        elif gov_slot is None or gov_slot.fp1_identity() != sh_slot.fp1_identity():
            condition = ShadowCondition.DISAGREE
        else:
            condition = ShadowCondition.AGREE
        records.append(
            ShadowComparisonRecord(
                producer_id=producer_id,
                source_identity=source,
                frontier_instant=governed.frontier_instant,
                condition=condition,
                governed_readiness=gov_ready,
                candidate_readiness=cand_ready,
            )
        )
    return Ok(tuple(records))


def shadow_comparison_projection(evaluation: object) -> Mapping[str, object]:
    """Evidence-channel payload — publish-never-act, gating nothing."""
    if not isinstance(evaluation, ShadowEvaluation):
        return MappingProxyType(
            {
                "capability": SHADOW_COMPARISON_PROJECTION_KEY,
                "publishes": True,
                "acts": False,
                "gating": False,
                "authorizes": False,
            }
        )
    return MappingProxyType(
        {
            "capability": SHADOW_COMPARISON_PROJECTION_KEY,
            "publishes": True,
            "acts": False,
            "gating": False,
            "authorizes": False,
            "substitutes_governed": evaluation.substituted_governed,
            "slice_delayed": evaluation.slice_delayed,
            "lane_enabled": evaluation.lane_enabled,
            "counted_toward_max_slice_latency": evaluation.counted_toward_max_slice_latency,
            "manifest_prefix": SHADOW_MANIFEST_PREFIX,
            "governed_frontier_ns": evaluation.governed.frontier_instant.value_ns,
            "governed_lane": evaluation.governed.lane.value,
            "publication": (
                None
                if evaluation.publication is None
                else dict(evaluation.publication.as_journal_row())
            ),
            "comparison": [dict(row.as_mapping()) for row in evaluation.comparison],
            "data_quality": [dict(row) for row in evaluation.data_quality],
        }
    )


def evaluate_shadow_lane(
    *,
    governed: object,
    catalog: object,
    frame: object,
    config: object,
    elapsed: object,
    writer: object,
    shadow_composition_fp: object,
    sequence: object = 0,
    journal_sink: object = None,
    decision_freshness_bound: object = None,
    sqs_baseline: object = None,
    liquidity_fit: object = None,
) -> Result[ShadowEvaluation]:
    """Run one shadow evaluation. Never delays the slice or rewrites governed."""
    if not isinstance(governed, SignalSnapshot):
        return invalid(
            "governed",
            "shadow evaluation diffs against a governed SignalSnapshot",
            given=type(governed).__name__,
        )
    if governed.lane is SnapshotLane.SHADOW:
        return policy(
            "governed",
            "shadow evaluation cannot treat a shadow snapshot as governed output",
        )
    if not isinstance(catalog, ShadowCandidateCatalog):
        return invalid(
            "catalog",
            "shadow evaluation reads a ShadowCandidateCatalog",
            given=type(catalog).__name__,
        )
    if not isinstance(config, ShadowLaneConfig):
        return invalid(
            "config",
            "shadow evaluation takes a ShadowLaneConfig",
            given=type(config).__name__,
        )
    if not isinstance(elapsed, Duration):
        return invalid(
            "elapsed",
            "shadow publish elapsed is an injected Duration — never wall-now",
            given=repr(elapsed),
        )
    if not config.enabled:
        return Ok(
            ShadowEvaluation(
                governed=governed,
                publication=None,
                comparison=(),
                data_quality=(),
                lane_enabled=False,
                slice_delayed=False,
                counted_toward_max_slice_latency=SHADOW_COUNTED_TOWARD_MAX_SLICE_LATENCY,
                substituted_governed=False,
            )
        )
    late = elapsed.value_ns > config.publish_bound.value_ns
    late_ids: tuple[str, ...] = catalog.candidate_ids() if late else ()
    if late:
        dq = _late_data_quality(
            catalog=catalog,
            governed=governed,
            writer=writer,
            elapsed=elapsed,
            bound=config.publish_bound,
        )
        written = _append_journal(journal_sink, dq)
        if is_refusal(written):
            return written
        compared = compare_shadow_to_governed(
            governed,
            None,
            catalog=catalog,
            late_producer_ids=late_ids,
        )
        if is_refusal(compared):
            return compared
        return Ok(
            ShadowEvaluation(
                governed=governed,
                publication=None,
                comparison=compared.value,
                data_quality=(dq,),
                lane_enabled=True,
                slice_delayed=False,
                counted_toward_max_slice_latency=SHADOW_COUNTED_TOWARD_MAX_SLICE_LATENCY,
                substituted_governed=False,
            )
        )
    bound = (
        governed.decision_freshness_bound
        if decision_freshness_bound is None
        else decision_freshness_bound
    )
    snapshot = assemble_shadow_snapshot(
        catalog,
        frame,
        decision_freshness_bound=bound,
        sqs_baseline=sqs_baseline,
        liquidity_fit=liquidity_fit,
    )
    if is_refusal(snapshot):
        return snapshot
    publication: ShadowPublication | None = None
    if catalog.candidates:
        published = publish_shadow_snapshot(
            snapshot.value,
            writer=writer,
            shadow_composition_fp=shadow_composition_fp,
            sequence=sequence,
            journal_sink=journal_sink,
        )
        if is_refusal(published):
            return published
        publication = published.value
    compared = compare_shadow_to_governed(
        governed,
        snapshot.value if catalog.candidates else None,
        catalog=catalog,
    )
    if is_refusal(compared):
        return compared
    return Ok(
        ShadowEvaluation(
            governed=governed,
            publication=publication,
            comparison=compared.value,
            data_quality=(),
            lane_enabled=True,
            slice_delayed=False,
            counted_toward_max_slice_latency=SHADOW_COUNTED_TOWARD_MAX_SLICE_LATENCY,
            substituted_governed=False,
        )
    )


def _writer_fields(writer: WriterId) -> Mapping[str, object]:
    return MappingProxyType(
        {
            "machine": writer.machine,
            "role": writer.role,
            "stream": writer.stream,
            "boot_epoch_id": writer.boot_epoch_id,
        }
    )


def _append_journal(sink: object, row: Mapping[str, object]) -> Result[None]:
    if sink is None:
        return invalid(
            "journal_sink",
            "an enabled shadow lane writes through a JournalSink under the "
            "distinct mis-shadow WriterId",
        )
    append = getattr(sink, "append", None)
    if not callable(append):
        return invalid(
            "journal_sink",
            "shadow publication writes through a JournalSink",
            given=type(sink).__name__,
        )
    result = append(MappingProxyType(dict(row)))
    if isinstance(result, TypedRefusal):
        return result
    return Ok(None)


def _late_data_quality(
    *,
    catalog: ShadowCandidateCatalog,
    governed: SignalSnapshot,
    writer: object,
    elapsed: Duration,
    bound: Duration,
) -> Mapping[str, object]:
    writer_body = dict(_writer_fields(writer)) if isinstance(writer, WriterId) else None
    identities = {pid: f"{row.formula_id}:{row.version}" for pid, row in catalog.candidates.items()}
    return MappingProxyType(
        {
            "event_type": _DATA_QUALITY_EVENT_TYPE,
            "kind": "shadow-lane-late-drop",
            "condition": ShadowCondition.LATE.value,
            "producer_ids": list(catalog.candidate_ids()),
            "source_identity": identities,
            "frontier_instant_ns": governed.frontier_instant.value_ns,
            "elapsed_ns": elapsed.value_ns,
            "bound_ns": bound.value_ns,
            "bound_variable": SHADOW_LANE_PUBLISH_BOUND_VARIABLE,
            "writer": writer_body,
            "manifest_prefix": SHADOW_MANIFEST_PREFIX,
            "counted_toward_max_slice_latency": False,
            "slice_delayed": False,
            "substitutes_governed": False,
            "gating": False,
            "authorizes": False,
        }
    )


def _source_identity(
    producer_id: str,
    versions: Mapping[str, str],
    governed: SignalSnapshot,
    shadow: SignalSnapshot | None,
) -> str:
    if producer_id in versions:
        return f"{producer_id}:{versions[producer_id]}"
    if shadow is not None and producer_id in shadow.producers:
        return f"{producer_id}:{shadow.producers[producer_id].labeler_version}"
    if producer_id in governed.producers:
        return f"{producer_id}:{governed.producers[producer_id].labeler_version}"
    return producer_id


def _token_set(value: object, field: str) -> frozenset[str] | TypedRefusal:
    if value is None or value == ():
        return frozenset()
    if isinstance(value, str):
        token = clean_token(value)
        if token is None:
            return invalid(field, f"{field} tokens are non-empty strings", given=repr(value))
        return frozenset({token})
    if isinstance(value, (bytes, bytearray)) or not isinstance(value, Iterable):
        return invalid(field, f"{field} is a collection of producer ids", given=repr(value))
    items: set[str] = set()
    for item in cast("Iterable[object]", value):
        token = clean_token(item)
        if token is None:
            return invalid(field, f"{field} tokens are non-empty strings", given=repr(item))
        items.add(token)
    return frozenset(items)


def _emission_to_slot(emission: ProducerEmission) -> Result[ProducerSlot]:
    return ProducerSlot.try_create(
        emission.producer_id,
        readiness=emission.readiness,
        labeler_version=emission.labeler_version,
        sqs=emission.sqs,
        marker_detail=emission.marker_detail,
    )


def _refused_emission(
    producer: ConfiguredMisProducer,
    frame: FrontierFrame,
    reason: str,
) -> ProducerEmission:
    sqs: SqsReading | None = None
    if producer.producer_id == SQS_PRODUCER_ID:
        key = sqs_baseline_key(frame.instrument.venue, frame.environment, frame.instrument)
        if not is_refusal(key):
            reading = SqsReading.try_create(
                key.value,
                readiness=ProducerReadiness.REFUSED,
                labeler_version=producer.version,
            )
            if not is_refusal(reading):
                sqs = reading.value
    return ProducerEmission(
        producer_id=producer.producer_id,
        readiness=ProducerReadiness.REFUSED,
        labeler_version=producer.version,
        marker_detail=reason,
        sqs=sqs,
    )
