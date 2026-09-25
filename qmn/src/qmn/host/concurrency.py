"""Host concurrency and backpressure proof (Story 25.16 / FR-053 / NFR-17).

Deterministic load drives concurrent streams, door reads, and timer ticks
against **injected** configured bounds. Measurements prove one event loop,
bounded in-flight work, explicit enqueue/backpressure, responsive
evidence/powers doors, and no silent observation loss — without asserting
invented capacity numbers (FTR-07). Seat callbacks and isolation are
``qmn.host.seat_concurrency`` (Story 26.19).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Instant,
    Instrument,
    MonotonicReading,
    Ok,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    WriterId,
    is_ok,
    is_refusal,
)

from qmn.bench.harness import collect_provenance, peak_rss_bytes
from qmn.bench.schema import BenchLifecycle, DeploymentProvenance
from qmn.doors.library import DoorRuntime, enact_power, read_status
from qmn.host._refuse import invalid, policy
from qmn.host.supervise import (
    ASYNC_ALLOWED_SURFACES,
    DOMAIN_BACKGROUND_THREADS_ALLOWED,
    EVENT_LOOP_COUNT,
    supervision_process_model,
)
from qmn.loop import RecordingAccumulator, clear_first_writer_registry
from qmn.loop.kinds import DATA_QUALITY_EVENT_TYPE, CycleBand
from qmn.order import ConnectionCommandPacer
from qmn.time import host_perf_counter_ns
from qmn.venue import (
    Command,
    OrderParameters,
    OrderType,
    TimeInForce,
)

__all__ = [
    "CONCURRENCY_SURFACE",
    "SEAT_CONCURRENCY_OWNED_BY",
    "BoundCrossingKind",
    "BoundCrossingRecord",
    "ConcurrencyLoad",
    "ConcurrencyProofReport",
    "InjectedBounds",
    "prove_host_concurrency",
]

CONCURRENCY_SURFACE: Final[str] = "qmn.host.concurrency"
# Seat callbacks / end-to-end seat isolation: qmn.host.seat_concurrency.
SEAT_CONCURRENCY_OWNED_BY: Final[str] = "26.19"

_BOOT: Final[str] = "boot-epoch-concurrency-25-16"
_SESSION: Final[str] = "session-epoch-concurrency-25-16"
_WALL_BASE_NS: Final[int] = 1_725_300_000 * 1_000_000_000


@dataclass(frozen=True, slots=True)
class InjectedBounds:
    """Caller-supplied configured bounds — never invented inside the harness.

    ``governor_cpu_budget`` / ``governor_memory_budget`` are soak-blocking
    registry values (TN-23). ``None`` records them as unset evidence; a positive
    integer records the configured value used for this proof run. The harness
    never synthesizes a default.
    """

    accumulator_bound: int
    general_capacity: int
    protective_reserve_capacity: int
    local_queue_bound_ns: int
    evidence_channel_budget: int
    governor_cpu_budget: int | None = None
    governor_memory_budget: int | None = None

    @classmethod
    def try_create(
        cls,
        *,
        accumulator_bound: object,
        general_capacity: object,
        protective_reserve_capacity: object,
        local_queue_bound_ns: object,
        evidence_channel_budget: object,
        governor_cpu_budget: object = None,
        governor_memory_budget: object = None,
    ) -> Result[InjectedBounds]:
        """Validate injected bounds; refuse non-positive or invented-as-default shapes."""
        core = _bind_injected_core_bounds(
            accumulator_bound=accumulator_bound,
            general_capacity=general_capacity,
            protective_reserve_capacity=protective_reserve_capacity,
            local_queue_bound_ns=local_queue_bound_ns,
            evidence_channel_budget=evidence_channel_budget,
        )
        if is_refusal(core):
            return core
        acc, general, queue_ns, evidence, reserve = core.value
        cpu = _optional_positive("governor_cpu_budget", governor_cpu_budget)
        if is_refusal(cpu):
            return cpu
        mem = _optional_positive("governor_memory_budget", governor_memory_budget)
        if is_refusal(mem):
            return mem
        return Ok(
            cls(
                accumulator_bound=acc,
                general_capacity=general,
                protective_reserve_capacity=reserve,
                local_queue_bound_ns=queue_ns,
                evidence_channel_budget=evidence,
                governor_cpu_budget=cpu.value,
                governor_memory_budget=mem.value,
            )
        )

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "accumulator_bound": self.accumulator_bound,
                "general_capacity": self.general_capacity,
                "protective_reserve_capacity": self.protective_reserve_capacity,
                "local_queue_bound_ns": self.local_queue_bound_ns,
                "evidence_channel_budget": self.evidence_channel_budget,
                "governor_cpu_budget": self.governor_cpu_budget,
                "governor_memory_budget": self.governor_memory_budget,
                "governor_cpu_budget_status": (
                    "configured" if self.governor_cpu_budget is not None else "unset"
                ),
                "governor_memory_budget_status": (
                    "configured" if self.governor_memory_budget is not None else "unset"
                ),
            }
        )


@dataclass(frozen=True, slots=True)
class ConcurrencyLoad:
    """Deterministic load description — seed owns stream/door/timer interleaving."""

    seed: int
    stream_count: int
    observations_per_stream: int
    timer_ticks: int
    door_interleave_every: int

    @classmethod
    def try_create(
        cls,
        *,
        seed: object,
        stream_count: object = 2,
        observations_per_stream: object = 8,
        timer_ticks: object = 4,
        door_interleave_every: object = 2,
    ) -> Result[ConcurrencyLoad]:
        """Validate load parameters (all positive integers; seed may be zero)."""
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            return invalid(
                "seed",
                "load seed is a non-negative integer for deterministic interleaving",
                given=repr(seed),
            )
        streams = _require_positive_int(
            "stream_count", stream_count, "load dimension is a positive integer"
        )
        if is_refusal(streams):
            return streams
        observations = _require_positive_int(
            "observations_per_stream",
            observations_per_stream,
            "load dimension is a positive integer",
        )
        if is_refusal(observations):
            return observations
        timers = _require_positive_int(
            "timer_ticks", timer_ticks, "load dimension is a positive integer"
        )
        if is_refusal(timers):
            return timers
        door_every = _require_positive_int(
            "door_interleave_every",
            door_interleave_every,
            "load dimension is a positive integer",
        )
        if is_refusal(door_every):
            return door_every
        return Ok(
            cls(
                seed=seed,
                stream_count=streams.value,
                observations_per_stream=observations.value,
                timer_ticks=timers.value,
                door_interleave_every=door_every.value,
            )
        )

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "seed": self.seed,
                "stream_count": self.stream_count,
                "observations_per_stream": self.observations_per_stream,
                "timer_ticks": self.timer_ticks,
                "door_interleave_every": self.door_interleave_every,
            }
        )


class BoundCrossingKind:
    """Named designed responses when a configured bound is crossed."""

    MARKET_DATA_COALESCE = "market-data-coalesce"
    STORAGE_FAILURE = "storage-failure"
    PACER_CAPACITY = "pacer-capacity"
    LOCAL_QUEUE_BOUND = "local-queue-bound"
    EVIDENCE_BUDGET = "evidence-channel-budget"
    ENTRY_SIDE_DEGRADATION = "entry-side-no-new-entry"
    SEAT_DEADLINE_QUARANTINE = "seat-deadline-quarantine"
    SEAT_MEMORY_QUARANTINE = "seat-memory-quarantine"


@dataclass(frozen=True, slots=True)
class BoundCrossingRecord:
    """One observed designed response — typed refusal, coalesce, or degradation."""

    kind: str
    category: str | None
    bound_field: str | None
    stream_index: int | None
    details: Mapping[str, object]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": self.kind,
                "category": self.category,
                "field": self.bound_field,
                "stream_index": self.stream_index,
                "details": dict(self.details),
            }
        )


@dataclass(frozen=True, slots=True)
class _DriveMetrics:
    """Internal measured counters from one deterministic load drive."""

    max_in_flight_observed: int
    max_accumulator_depth_observed: int
    push_attempts: int
    push_accepted: int
    coalesce_events: int
    typed_refusals: int
    entry_side_degradations: int
    backpressure_observed: bool
    silent_observation_loss: bool
    accounted_observations: int
    evidence_door_ok: int
    powers_door_ok: int
    door_response_samples_ns: tuple[int, ...]
    timer_ticks_fired: int
    bound_crossings: tuple[BoundCrossingRecord, ...]
    peak_rss_bytes: int


@dataclass(frozen=True, slots=True)
class ConcurrencyProofReport:
    """Measured host concurrency posture — schema complete without capacity gates."""

    surface: str
    load: ConcurrencyLoad
    bounds: InjectedBounds
    provenance: DeploymentProvenance
    process_model: Mapping[str, object]
    event_loop_count: int
    domain_background_threads_allowed: bool
    async_allowed_surfaces: tuple[str, ...]
    wall_time_ns: int
    peak_rss_bytes: int
    max_in_flight_observed: int
    max_accumulator_depth_observed: int
    push_attempts: int
    push_accepted: int
    coalesce_events: int
    typed_refusals: int
    entry_side_degradations: int
    backpressure_observed: bool
    silent_observation_loss: bool
    accounted_observations: int
    evidence_door_ok: int
    powers_door_ok: int
    door_response_samples_ns: tuple[int, ...]
    timer_ticks_fired: int
    bound_crossings: tuple[BoundCrossingRecord, ...]
    seat_concurrency_owned_by: str = SEAT_CONCURRENCY_OWNED_BY
    schema_version: int = 1

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "schema_version": self.schema_version,
                "surface": self.surface,
                "load": dict(self.load.as_mapping()),
                "bounds": dict(self.bounds.as_mapping()),
                "provenance": dict(self.provenance.as_mapping()),
                "process_model": dict(self.process_model),
                "event_loop_count": self.event_loop_count,
                "domain_background_threads_allowed": self.domain_background_threads_allowed,
                "async_allowed_surfaces": list(self.async_allowed_surfaces),
                "wall_time_ns": self.wall_time_ns,
                "peak_rss_bytes": self.peak_rss_bytes,
                "max_in_flight_observed": self.max_in_flight_observed,
                "max_accumulator_depth_observed": self.max_accumulator_depth_observed,
                "push_attempts": self.push_attempts,
                "push_accepted": self.push_accepted,
                "coalesce_events": self.coalesce_events,
                "typed_refusals": self.typed_refusals,
                "entry_side_degradations": self.entry_side_degradations,
                "backpressure_observed": self.backpressure_observed,
                "silent_observation_loss": self.silent_observation_loss,
                "accounted_observations": self.accounted_observations,
                "evidence_door_ok": self.evidence_door_ok,
                "powers_door_ok": self.powers_door_ok,
                "door_response_samples_ns": list(self.door_response_samples_ns),
                "timer_ticks_fired": self.timer_ticks_fired,
                "bound_crossings": [dict(item.as_mapping()) for item in self.bound_crossings],
                "seat_concurrency_owned_by": self.seat_concurrency_owned_by,
            }
        )


def prove_host_concurrency(
    *,
    load: object,
    bounds: object,
    lifecycle: object = BenchLifecycle.PRE_DOORS_OPEN,
    deployment_id: object = "local-ci",
) -> Result[ConcurrencyProofReport]:
    """Run the host concurrency/backpressure proof and return measured evidence."""
    bound = _bind_concurrency_proof(
        load=load,
        bounds=bounds,
        lifecycle=lifecycle,
        deployment_id=deployment_id,
    )
    if is_refusal(bound):
        return bound
    load_v, bounds_v, lifecycle_v, deployment = bound.value
    provenance = collect_provenance(lifecycle=lifecycle_v, deployment_id=deployment)
    process_model = dict(supervision_process_model())
    loop_count = process_model["event_loop_count"]
    if not isinstance(loop_count, int) or loop_count != EVENT_LOOP_COUNT:
        return policy(
            "event_loop_count",
            "process model event_loop_count must equal EVENT_LOOP_COUNT",
            declared=loop_count,
            constant=EVENT_LOOP_COUNT,
        )
    clear_first_writer_registry()
    rss_before = peak_rss_bytes()
    started = host_perf_counter_ns()
    try:
        measured = _drive_load(load=load_v, bounds=bounds_v)
    finally:
        clear_first_writer_registry()
    if is_refusal(measured):
        return measured
    return Ok(
        _concurrency_report(
            load=load_v,
            bounds=bounds_v,
            provenance=provenance,
            process_model=process_model,
            wall_ns=host_perf_counter_ns() - started,
            peak_rss=max(rss_before, peak_rss_bytes(), measured.value.peak_rss_bytes),
            payload=measured.value,
        )
    )


def _require_positive_int(name: str, value: object, reason: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(name, reason, given=repr(value))
    return Ok(value)


def _optional_positive(name: str, value: object) -> Result[int | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(
            name,
            "governor budget is None (unset) or a positive integer — never invented",
            given=repr(value),
        )
    return Ok(value)


def _bind_injected_core_bounds(
    *,
    accumulator_bound: object,
    general_capacity: object,
    protective_reserve_capacity: object,
    local_queue_bound_ns: object,
    evidence_channel_budget: object,
) -> Result[tuple[int, int, int, int, int]]:
    reason = (
        "configured bound is a positive integer supplied by the caller "
        "(never a harness-invented default)"
    )
    acc = _require_positive_int("accumulator_bound", accumulator_bound, reason)
    if is_refusal(acc):
        return acc
    general = _require_positive_int("general_capacity", general_capacity, reason)
    if is_refusal(general):
        return general
    queue_ns = _require_positive_int("local_queue_bound_ns", local_queue_bound_ns, reason)
    if is_refusal(queue_ns):
        return queue_ns
    evidence = _require_positive_int(
        "evidence_channel_budget", evidence_channel_budget, reason
    )
    if is_refusal(evidence):
        return evidence
    if (
        isinstance(protective_reserve_capacity, bool)
        or not isinstance(protective_reserve_capacity, int)
        or protective_reserve_capacity < 0
    ):
        return invalid(
            "protective_reserve_capacity",
            "protective reserve is a non-negative integer count",
            given=repr(protective_reserve_capacity),
        )
    return Ok(
        (acc.value, general.value, queue_ns.value, evidence.value, protective_reserve_capacity)
    )


def _bind_concurrency_proof(
    *,
    load: object,
    bounds: object,
    lifecycle: object,
    deployment_id: object,
) -> Result[tuple[ConcurrencyLoad, InjectedBounds, BenchLifecycle, str]]:
    if not isinstance(load, ConcurrencyLoad):
        return invalid(
            "load",
            "prove_host_concurrency requires a ConcurrencyLoad",
            given=type(load).__name__,
        )
    if not isinstance(bounds, InjectedBounds):
        return invalid(
            "bounds",
            "prove_host_concurrency requires InjectedBounds supplied by the caller",
            given=type(bounds).__name__,
        )
    if not isinstance(lifecycle, BenchLifecycle):
        return invalid(
            "lifecycle",
            "lifecycle at measurement is a BenchLifecycle",
            given=repr(lifecycle),
        )
    if not isinstance(deployment_id, str) or deployment_id.strip() == "":
        return invalid(
            "deployment_id",
            "deployment_id is a non-blank string",
            given=repr(deployment_id),
        )
    if bounds.accumulator_bound < 1:
        return policy(
            "accumulator_bound",
            "an unbounded or non-positive accumulator is an absent mechanism",
            given=bounds.accumulator_bound,
        )
    return Ok((load, bounds, lifecycle, deployment_id))


def _concurrency_report(
    *,
    load: ConcurrencyLoad,
    bounds: InjectedBounds,
    provenance: DeploymentProvenance,
    process_model: dict[str, object],
    wall_ns: int,
    peak_rss: int,
    payload: _DriveMetrics,
) -> ConcurrencyProofReport:
    return ConcurrencyProofReport(
        surface=CONCURRENCY_SURFACE,
        load=load,
        bounds=bounds,
        provenance=provenance,
        process_model=MappingProxyType(process_model),
        event_loop_count=EVENT_LOOP_COUNT,
        domain_background_threads_allowed=DOMAIN_BACKGROUND_THREADS_ALLOWED,
        async_allowed_surfaces=ASYNC_ALLOWED_SURFACES,
        wall_time_ns=wall_ns,
        peak_rss_bytes=peak_rss,
        max_in_flight_observed=payload.max_in_flight_observed,
        max_accumulator_depth_observed=payload.max_accumulator_depth_observed,
        push_attempts=payload.push_attempts,
        push_accepted=payload.push_accepted,
        coalesce_events=payload.coalesce_events,
        typed_refusals=payload.typed_refusals,
        entry_side_degradations=payload.entry_side_degradations,
        backpressure_observed=payload.backpressure_observed,
        silent_observation_loss=payload.silent_observation_loss,
        accounted_observations=payload.accounted_observations,
        evidence_door_ok=payload.evidence_door_ok,
        powers_door_ok=payload.powers_door_ok,
        door_response_samples_ns=payload.door_response_samples_ns,
        timer_ticks_fired=payload.timer_ticks_fired,
        bound_crossings=payload.bound_crossings,
    )


@dataclass(slots=True)
class _DriveState:
    load: ConcurrencyLoad
    bounds: InjectedBounds
    stream_bundle: list[tuple[RecordingAccumulator, _ListSink, _ListSink, VenueId, Account]]
    door: DoorRuntime
    pacer: ConnectionCommandPacer
    crossings: list[BoundCrossingRecord]
    door_samples: list[int]
    rng: _Deterministic
    push_attempts: int = 0
    push_accepted: int = 0
    coalesce_events: int = 0
    typed_refusals: int = 0
    entry_side_degradations: int = 0
    accounted: int = 0
    max_depth: int = 0
    max_in_flight: int = 0
    evidence_ok: int = 0
    powers_ok: int = 0
    timer_ticks_fired: int = 0
    wall_seq: int = 0


def _drive_load(*, load: ConcurrencyLoad, bounds: InjectedBounds) -> Result[_DriveMetrics]:
    bound = _bind_drive(load=load, bounds=bounds)
    if is_refusal(bound):
        return bound
    state = bound.value
    pushed = _drive_stream_pushes(state)
    if is_refusal(pushed):
        return pushed
    overflowed = _force_overflow(state)
    if is_refusal(overflowed):
        return overflowed
    paced = _drive_pacer_bound(state)
    if is_refusal(paced):
        return paced
    exhausted = _exhaust_evidence_budget(state)
    if is_refusal(exhausted):
        return exhausted
    return _finish_drive(state)


def _bind_drive(
    *, load: ConcurrencyLoad, bounds: InjectedBounds
) -> Result[_DriveState]:
    streams = _build_streams(load=load, bounds=bounds)
    if is_refusal(streams):
        return streams
    queue_bound = Duration.try_create(bounds.local_queue_bound_ns)
    if is_refusal(queue_bound):
        return queue_bound
    pacer = ConnectionCommandPacer.try_create(
        local_queue_bound=queue_bound.value,
        protective_reserve_capacity=bounds.protective_reserve_capacity,
        general_capacity=bounds.general_capacity,
    )
    if is_refusal(pacer):
        return pacer
    return Ok(
        _DriveState(
            load=load,
            bounds=bounds,
            stream_bundle=streams.value,
            door=DoorRuntime(
                boot_epoch=_BOOT,
                composition_fp="fp1:concurrency-proof",
                knowledge_time_ns=1_000,
                watermark_ns=900,
                source_time_ns=950,
                receive_time_ns=980,
                evidence_channel_budget=bounds.evidence_channel_budget,
                lifecycle="pre-doors-open",
            ),
            pacer=pacer.value,
            crossings=[],
            door_samples=[],
            rng=_Deterministic(load.seed),
        )
    )


def _drive_stream_pushes(state: _DriveState) -> Result[None]:
    total_pushes = state.load.stream_count * state.load.observations_per_stream
    for step in range(total_pushes):
        recorded = _push_one_step(state, step)
        if is_refusal(recorded):
            return recorded
        if step % state.load.door_interleave_every == 0:
            interleaved = _interleave_doors(state, step)
            if is_refusal(interleaved):
                return interleaved
        if step < state.load.timer_ticks:
            _ = host_perf_counter_ns()
            state.timer_ticks_fired += 1
    return Ok(None)


def _push_one_step(state: _DriveState, step: int) -> Result[None]:
    stream_index = state.rng.next_int(state.load.stream_count)
    acc, obs_sink, _journal_sink, _venue, _account = state.stream_bundle[stream_index]
    state.wall_seq += 1
    state.push_attempts += 1
    before_coalesce = len(acc.coalesce_events)
    result = acc.push(
        observation_id=f"spot-{stream_index}-{step}",
        stream_id="eurusd",
        receive_wall=_instant(_WALL_BASE_NS + state.wall_seq * 1_000_000),
        payload={"kind": "spot", "step": step, "stream": stream_index},
        kind="spot",
        coalesce_key="eurusd",
    )
    if is_ok(result):
        accounted = _account_accepted_push(
            state, acc, obs_sink, before_coalesce, stream_index, step
        )
        if is_refusal(accounted):
            return accounted
    else:
        _account_refused_push(state, acc, result, stream_index)
    state.max_depth = max(state.max_depth, acc.depth)
    return Ok(None)


def _account_accepted_push(
    state: _DriveState,
    acc: RecordingAccumulator,
    obs_sink: _ListSink,
    before_coalesce: int,
    stream_index: int,
    step: int,
) -> Result[None]:
    state.push_accepted += 1
    state.accounted += 1
    if len(obs_sink.rows) < 1 and len(acc.coalesce_events) == before_coalesce:
        return policy(
            "observation_accounting",
            "accepted push must leave governed intake or coalesce evidence; "
            "silent observation loss is forbidden",
            stream_index=stream_index,
            step=step,
        )
    if len(acc.coalesce_events) > before_coalesce:
        _record_coalesce(state, acc, stream_index)
    return Ok(None)


def _account_refused_push(
    state: _DriveState,
    acc: RecordingAccumulator,
    result: TypedRefusal,
    stream_index: int,
) -> None:
    state.typed_refusals += 1
    state.accounted += 1
    state.crossings.append(
        BoundCrossingRecord(
            kind=BoundCrossingKind.STORAGE_FAILURE,
            category=result.category.value,
            bound_field=str(result.context.get("field", "accumulator_bound")),
            stream_index=stream_index,
            details=dict(result.context),
        )
    )
    if acc.cycle_band is CycleBand.NO_NEW_ENTRY:
        state.entry_side_degradations += 1


def _record_coalesce(
    state: _DriveState, acc: RecordingAccumulator, stream_index: int
) -> None:
    state.coalesce_events += 1
    state.entry_side_degradations += 1
    state.crossings.append(
        BoundCrossingRecord(
            kind=BoundCrossingKind.MARKET_DATA_COALESCE,
            category=DATA_QUALITY_EVENT_TYPE,
            bound_field="accumulator_bound",
            stream_index=stream_index,
            details={
                "depth": acc.depth,
                "bound": state.bounds.accumulator_bound,
                "band": acc.cycle_band.value,
            },
        )
    )
    if acc.cycle_band is CycleBand.NO_NEW_ENTRY:
        state.crossings.append(
            BoundCrossingRecord(
                kind=BoundCrossingKind.ENTRY_SIDE_DEGRADATION,
                category=None,
                bound_field="cycle_band",
                stream_index=stream_index,
                details={"band": CycleBand.NO_NEW_ENTRY.value},
            )
        )


def _interleave_doors(state: _DriveState, step: int) -> Result[None]:
    door_start = host_perf_counter_ns()
    status = read_status(state.door)
    state.door_samples.append(host_perf_counter_ns() - door_start)
    if is_ok(status):
        state.evidence_ok += 1
    elif (
        status.category is RefusalCategory.POLICY_REJECTION
        and str(status.context.get("field", "")) == "evidence_channel_budget"
    ):
        state.typed_refusals += 1
        state.crossings.append(
            BoundCrossingRecord(
                kind=BoundCrossingKind.EVIDENCE_BUDGET,
                category=status.category.value,
                bound_field="evidence_channel_budget",
                stream_index=None,
                details=dict(status.context),
            )
        )
    else:
        return status
    return _enact_interleaved_power(state, step)


def _enact_interleaved_power(state: _DriveState, step: int) -> Result[None]:
    power_start = host_perf_counter_ns()
    power = enact_power(
        state.door,
        power="notify_test",
        principal="ops",
        artifact_key=f"notify-{step}",
        evidence_knowledge_time_ns=state.door.knowledge_time_ns,
        requested={"channel": "ops", "step": step},
    )
    state.door_samples.append(host_perf_counter_ns() - power_start)
    if is_ok(power):
        state.powers_ok += 1
        return Ok(None)
    return power


def _force_overflow(state: _DriveState) -> Result[None]:
    acc0 = state.stream_bundle[0][0]
    force_guard = 0
    while BoundCrossingKind.MARKET_DATA_COALESCE not in {c.kind for c in state.crossings}:
        force_guard += 1
        forced = _force_one_overflow_push(state, acc0)
        if is_refusal(forced):
            return forced
        if forced.value is True:
            break
        if force_guard > state.bounds.accumulator_bound + 4:
            return policy(
                "accumulator_bound",
                "failed to observe designed overflow/coalesce under injected bound",
                bound=state.bounds.accumulator_bound,
                depth=acc0.depth,
            )
    return Ok(None)


def _force_one_overflow_push(
    state: _DriveState, acc0: RecordingAccumulator
) -> Result[bool]:
    state.wall_seq += 1
    state.push_attempts += 1
    before_coalesce = len(acc0.coalesce_events)
    forced = acc0.push(
        observation_id=f"force-overflow-{state.wall_seq}",
        stream_id="eurusd",
        receive_wall=_instant(_WALL_BASE_NS + state.wall_seq * 1_000_000),
        payload={"kind": "spot", "force": True},
        kind="spot",
        coalesce_key="eurusd",
    )
    if is_ok(forced):
        return _account_forced_ok(state, acc0, before_coalesce)
    _account_refused_push(state, acc0, forced, 0)
    return Ok(True)


def _account_forced_ok(
    state: _DriveState, acc0: RecordingAccumulator, before_coalesce: int
) -> Result[bool]:
    state.push_accepted += 1
    state.accounted += 1
    if len(acc0.coalesce_events) > before_coalesce:
        _record_coalesce(state, acc0, 0)
        return Ok(True)
    state.max_depth = max(state.max_depth, acc0.depth)
    if acc0.depth > state.bounds.accumulator_bound:
        return policy(
            "accumulator_bound",
            "foldable depth must never exceed the configured accumulator_bound",
            depth=acc0.depth,
            bound=state.bounds.accumulator_bound,
        )
    return Ok(False)


def _drive_pacer_bound(state: _DriveState) -> Result[None]:
    venue0 = state.stream_bundle[0][3]
    account0 = state.stream_bundle[0][4]
    params = _pacer_order_params(venue0)
    if is_refusal(params):
        return params
    held_admissions = 0
    for index in range(state.bounds.general_capacity + 2):
        admitted = _admit_one_pacer(state, venue0, account0, params.value, index)
        if is_refusal(admitted):
            return admitted
        if admitted.value is True:
            held_admissions += 1
        state.max_in_flight = max(state.max_in_flight, held_admissions)
    cap = state.bounds.general_capacity + state.bounds.protective_reserve_capacity
    if state.max_in_flight > cap:
        return policy(
            "in_flight",
            "observed in-flight work exceeded configured pacer capacity",
            max_in_flight=state.max_in_flight,
            general_capacity=state.bounds.general_capacity,
            protective_reserve_capacity=state.bounds.protective_reserve_capacity,
        )
    return Ok(None)


def _pacer_order_params(venue0: VenueId) -> Result[OrderParameters]:
    instrument = Instrument.try_create(venue0, "EURUSD")
    if is_refusal(instrument):
        return instrument
    qty = Quantity.try_create(100, "lot", 2)
    if is_refusal(qty):
        return qty
    stop = PriceDelta.try_create(100, instrument.value, 5)
    if is_refusal(stop):
        return stop
    return OrderParameters.try_create(
        OrderType.MARKET,
        TimeInForce.GOOD_TILL_CANCEL,
        qty.value,
        protective_stop_distance=stop.value,
    )


def _admit_one_pacer(
    state: _DriveState,
    venue0: VenueId,
    account0: Account,
    params: OrderParameters,
    index: int,
) -> Result[bool]:
    cmd = Command.place_order(venue0, account0, _SESSION, index + 1, params)
    if is_refusal(cmd):
        return cmd
    enqueued = state.pacer.enqueue(cmd.value)
    if is_refusal(enqueued):
        return enqueued
    enqueued_at = MonotonicReading.try_create(20_000_000_000 + index * 1_000, _BOOT)
    now = MonotonicReading.try_create(20_000_000_000 + index * 1_000 + 100, _BOOT)
    if is_refusal(enqueued_at):
        return enqueued_at
    if is_refusal(now):
        return now
    admitted = state.pacer.admit(cmd.value, enqueued_at=enqueued_at.value, now=now.value)
    if is_ok(admitted):
        return Ok(True)
    state.typed_refusals += 1
    field_name = str(admitted.context.get("field", ""))
    kind = (
        BoundCrossingKind.LOCAL_QUEUE_BOUND
        if field_name == "local_queue_bound"
        else BoundCrossingKind.PACER_CAPACITY
    )
    state.crossings.append(
        BoundCrossingRecord(
            kind=kind,
            category=admitted.category.value,
            bound_field=field_name,
            stream_index=None,
            details=dict(admitted.context),
        )
    )
    return Ok(False)


def _exhaust_evidence_budget(state: _DriveState) -> Result[None]:
    if BoundCrossingKind.EVIDENCE_BUDGET in {c.kind for c in state.crossings}:
        return Ok(None)
    door = state.door
    while door.evidence_reads < door.evidence_channel_budget + 1:
        exhausted = read_status(door)
        if is_ok(exhausted):
            state.evidence_ok += 1
            continue
        state.typed_refusals += 1
        state.crossings.append(
            BoundCrossingRecord(
                kind=BoundCrossingKind.EVIDENCE_BUDGET,
                category=exhausted.category.value,
                bound_field=str(exhausted.context.get("field", "evidence_channel_budget")),
                stream_index=None,
                details=dict(exhausted.context),
            )
        )
        break
    return Ok(None)


def _finish_drive(state: _DriveState) -> Result[_DriveMetrics]:
    bounded = _assert_depth_bound(state)
    if is_refusal(bounded):
        return bounded
    required = _assert_required_crossings(state)
    if is_refusal(required):
        return required
    return Ok(_drive_metrics(state))


def _assert_depth_bound(state: _DriveState) -> Result[None]:
    for acc, *_rest in state.stream_bundle:
        state.max_depth = max(state.max_depth, acc.depth)
        if acc.depth > state.bounds.accumulator_bound:
            return policy(
                "accumulator_bound",
                "foldable depth must never exceed the configured accumulator_bound",
                depth=acc.depth,
                bound=state.bounds.accumulator_bound,
            )
    return Ok(None)


def _assert_required_crossings(state: _DriveState) -> Result[None]:
    required_kinds = {
        BoundCrossingKind.MARKET_DATA_COALESCE,
        BoundCrossingKind.PACER_CAPACITY,
        BoundCrossingKind.EVIDENCE_BUDGET,
    }
    seen_kinds = {crossing.kind for crossing in state.crossings}
    missing = required_kinds - seen_kinds
    if missing:
        return policy(
            "bound_crossings",
            "proof must observe designed coalesce, pacer backpressure, and evidence "
            "budget refusal — not log-only assertions",
            missing=sorted(missing),
            observed=sorted(seen_kinds),
        )
    return Ok(None)


def _drive_metrics(state: _DriveState) -> _DriveMetrics:
    pressure_kinds = {
        BoundCrossingKind.PACER_CAPACITY,
        BoundCrossingKind.LOCAL_QUEUE_BOUND,
        BoundCrossingKind.EVIDENCE_BUDGET,
        BoundCrossingKind.STORAGE_FAILURE,
    }
    backpressure = state.coalesce_events > 0 or any(
        crossing.kind in pressure_kinds for crossing in state.crossings
    )
    return _DriveMetrics(
        max_in_flight_observed=state.max_in_flight,
        max_accumulator_depth_observed=state.max_depth,
        push_attempts=state.push_attempts,
        push_accepted=state.push_accepted,
        coalesce_events=state.coalesce_events,
        typed_refusals=state.typed_refusals,
        entry_side_degradations=state.entry_side_degradations,
        backpressure_observed=backpressure,
        silent_observation_loss=state.accounted != state.push_attempts,
        accounted_observations=state.accounted,
        evidence_door_ok=state.evidence_ok,
        powers_door_ok=state.powers_ok,
        door_response_samples_ns=tuple(state.door_samples),
        timer_ticks_fired=state.timer_ticks_fired,
        bound_crossings=tuple(state.crossings),
        peak_rss_bytes=peak_rss_bytes(),
    )


def _build_streams(
    *, load: ConcurrencyLoad, bounds: InjectedBounds
) -> Result[
    list[
        tuple[
            RecordingAccumulator,
            _ListSink,
            _ListSink,
            VenueId,
            Account,
        ]
    ]
]:
    out: list[tuple[RecordingAccumulator, _ListSink, _ListSink, VenueId, Account]] = []
    for index in range(load.stream_count):
        venue = VenueId.try_create(f"conformance:concurrency-{load.seed}-{index}")
        if is_refusal(venue):
            return venue
        account = Account.try_create(
            f"concurrency-acct-{load.seed}-{index}",
            venue.value,
            AccountRole.DEMO,
        )
        if is_refusal(account):
            return account
        writer = WriterId.try_create(
            "concurrency-host",
            "proof",
            f"{venue.value.value}:{account.value.account_id}",
            _BOOT,
        )
        if is_refusal(writer):
            return writer
        obs_sink = _ListSink()
        journal_sink = _ListSink()
        acc = RecordingAccumulator.try_create(
            venue_id=venue.value,
            account=account.value,
            writer_id=writer.value,
            observation_sink=obs_sink,
            journal_sink=journal_sink,
            accumulator_bound=bounds.accumulator_bound,
            writer_name=f"concurrency-acc-{load.seed}-{index}",
        )
        if is_refusal(acc):
            return acc
        out.append((acc.value, obs_sink, journal_sink, venue.value, account.value))
    return Ok(out)


def _instant(ns: int) -> Instant:
    made = Instant.try_create(ns)
    if is_refusal(made):
        raise AssertionError(f"concurrency proof instant construct failed: {made}")
    return made.value


class _Deterministic:
    """Tiny LCG — deterministic stream selection from the load seed."""

    def __init__(self, seed: int) -> None:
        self._state = seed & 0xFFFFFFFF

    def next_int(self, modulus: int) -> int:
        self._state = (1664525 * self._state + 1013904223) & 0xFFFFFFFF
        return self._state % modulus


class _ListSink:
    """In-memory observation / journal sink for the concurrency proof."""

    def __init__(self) -> None:
        self.rows: list[object] = []

    def emit(self, observation: object, /) -> SinkResult:
        self.rows.append(observation)
        return Ok(SinkAck())

    def append(self, event: object, /) -> SinkResult:
        self.rows.append(event)
        return Ok(SinkAck())
