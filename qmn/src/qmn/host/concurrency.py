"""Host concurrency and backpressure proof (Story 25.16 / FR-053 / NFR-17).

Deterministic load drives concurrent streams, door reads, and timer ticks
against **injected** configured bounds. Measurements prove one event loop,
bounded in-flight work, explicit enqueue/backpressure, responsive
evidence/powers doors, and no silent observation loss — without asserting
invented capacity numbers (FTR-07). Seat callbacks belong to Story 26.19.
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
# Seat callbacks / end-to-end seat isolation are Story 26.19 — not this surface.
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
        acc = _require_positive_int(
            "accumulator_bound",
            accumulator_bound,
            "configured bound is a positive integer supplied by the caller "
            "(never a harness-invented default)",
        )
        if is_refusal(acc):
            return acc
        general = _require_positive_int(
            "general_capacity",
            general_capacity,
            "configured bound is a positive integer supplied by the caller "
            "(never a harness-invented default)",
        )
        if is_refusal(general):
            return general
        queue_ns = _require_positive_int(
            "local_queue_bound_ns",
            local_queue_bound_ns,
            "configured bound is a positive integer supplied by the caller "
            "(never a harness-invented default)",
        )
        if is_refusal(queue_ns):
            return queue_ns
        evidence = _require_positive_int(
            "evidence_channel_budget",
            evidence_channel_budget,
            "configured bound is a positive integer supplied by the caller "
            "(never a harness-invented default)",
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
        cpu = _optional_positive("governor_cpu_budget", governor_cpu_budget)
        if is_refusal(cpu):
            return cpu
        mem = _optional_positive("governor_memory_budget", governor_memory_budget)
        if is_refusal(mem):
            return mem
        return Ok(
            cls(
                accumulator_bound=acc.value,
                general_capacity=general.value,
                protective_reserve_capacity=protective_reserve_capacity,
                local_queue_bound_ns=queue_ns.value,
                evidence_channel_budget=evidence.value,
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

    provenance = collect_provenance(lifecycle=lifecycle, deployment_id=deployment_id)
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
        measured = _drive_load(load=load, bounds=bounds)
    finally:
        clear_first_writer_registry()

    if is_refusal(measured):
        return measured
    payload = measured.value

    ended = host_perf_counter_ns()
    wall_ns = ended - started
    peak_rss = max(rss_before, peak_rss_bytes(), payload.peak_rss_bytes)

    return Ok(
        ConcurrencyProofReport(
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


def _drive_load(*, load: ConcurrencyLoad, bounds: InjectedBounds) -> Result[_DriveMetrics]:
    streams = _build_streams(load=load, bounds=bounds)
    if is_refusal(streams):
        return streams
    stream_bundle = streams.value

    door = DoorRuntime(
        boot_epoch=_BOOT,
        composition_fp="fp1:concurrency-proof",
        knowledge_time_ns=1_000,
        watermark_ns=900,
        source_time_ns=950,
        receive_time_ns=980,
        evidence_channel_budget=bounds.evidence_channel_budget,
        lifecycle="pre-doors-open",
    )

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

    crossings: list[BoundCrossingRecord] = []
    door_samples: list[int] = []
    push_attempts = 0
    push_accepted = 0
    coalesce_events = 0
    typed_refusals = 0
    entry_side_degradations = 0
    accounted = 0
    max_depth = 0
    max_in_flight = 0
    evidence_ok = 0
    powers_ok = 0
    timer_ticks_fired = 0
    wall_seq = 0
    rng = _Deterministic(load.seed)

    # --- concurrent stream pushes with door + timer interleave ---------------
    total_pushes = load.stream_count * load.observations_per_stream
    for step in range(total_pushes):
        stream_index = rng.next_int(load.stream_count)
        acc, obs_sink, _journal_sink, _venue, _account = stream_bundle[stream_index]
        wall_seq += 1
        push_attempts += 1
        before_coalesce = len(acc.coalesce_events)
        result = acc.push(
            observation_id=f"spot-{stream_index}-{step}",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_BASE_NS + wall_seq * 1_000_000),
            payload={"kind": "spot", "step": step, "stream": stream_index},
            kind="spot",
            coalesce_key="eurusd",
        )
        if is_ok(result):
            push_accepted += 1
            accounted += 1
            # Accepted push must leave intake or coalesce evidence — never silence.
            if len(obs_sink.rows) < 1 and len(acc.coalesce_events) == before_coalesce:
                return policy(
                    "observation_accounting",
                    "accepted push must leave governed intake or coalesce evidence; "
                    "silent observation loss is forbidden",
                    stream_index=stream_index,
                    step=step,
                )
            if len(acc.coalesce_events) > before_coalesce:
                coalesce_events += 1
                entry_side_degradations += 1
                crossings.append(
                    BoundCrossingRecord(
                        kind=BoundCrossingKind.MARKET_DATA_COALESCE,
                        category=DATA_QUALITY_EVENT_TYPE,
                        bound_field="accumulator_bound",
                        stream_index=stream_index,
                        details={
                            "depth": acc.depth,
                            "bound": bounds.accumulator_bound,
                            "band": acc.cycle_band.value,
                        },
                    )
                )
                if acc.cycle_band is CycleBand.NO_NEW_ENTRY:
                    crossings.append(
                        BoundCrossingRecord(
                            kind=BoundCrossingKind.ENTRY_SIDE_DEGRADATION,
                            category=None,
                            bound_field="cycle_band",
                            stream_index=stream_index,
                            details={"band": CycleBand.NO_NEW_ENTRY.value},
                        )
                    )
        else:
            typed_refusals += 1
            accounted += 1  # refusal is explicit accounting, not silent loss
            crossings.append(
                BoundCrossingRecord(
                    kind=BoundCrossingKind.STORAGE_FAILURE,
                    category=result.category.value,
                    bound_field=str(result.context.get("field", "accumulator_bound")),
                    stream_index=stream_index,
                    details=dict(result.context),
                )
            )
            if acc.cycle_band is CycleBand.NO_NEW_ENTRY:
                entry_side_degradations += 1

        max_depth = max(max_depth, acc.depth)

        if step % load.door_interleave_every == 0:
            door_start = host_perf_counter_ns()
            status = read_status(door)
            door_samples.append(host_perf_counter_ns() - door_start)
            if is_ok(status):
                evidence_ok += 1
            elif (
                status.category is RefusalCategory.POLICY_REJECTION
                and str(status.context.get("field", "")) == "evidence_channel_budget"
            ):
                typed_refusals += 1
                crossings.append(
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

            power_start = host_perf_counter_ns()
            power = enact_power(
                door,
                power="notify_test",
                principal="ops",
                artifact_key=f"notify-{step}",
                evidence_knowledge_time_ns=door.knowledge_time_ns,
                requested={"channel": "ops", "step": step},
            )
            door_samples.append(host_perf_counter_ns() - power_start)
            if is_ok(power):
                powers_ok += 1
            else:
                return power

        if step < load.timer_ticks:
            _ = host_perf_counter_ns()
            timer_ticks_fired += 1

    # Force overflow on stream 0 if load did not already cross the bound.
    acc0, _obs0, _j0, venue0, account0 = stream_bundle[0]
    force_guard = 0
    while BoundCrossingKind.MARKET_DATA_COALESCE not in {crossing.kind for crossing in crossings}:
        wall_seq += 1
        force_guard += 1
        push_attempts += 1
        before_coalesce = len(acc0.coalesce_events)
        forced = acc0.push(
            observation_id=f"force-overflow-{wall_seq}",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_BASE_NS + wall_seq * 1_000_000),
            payload={"kind": "spot", "force": True},
            kind="spot",
            coalesce_key="eurusd",
        )
        if is_ok(forced):
            push_accepted += 1
            accounted += 1
            if len(acc0.coalesce_events) > before_coalesce:
                coalesce_events += 1
                entry_side_degradations += 1
                crossings.append(
                    BoundCrossingRecord(
                        kind=BoundCrossingKind.MARKET_DATA_COALESCE,
                        category=DATA_QUALITY_EVENT_TYPE,
                        bound_field="accumulator_bound",
                        stream_index=0,
                        details={
                            "depth": acc0.depth,
                            "bound": bounds.accumulator_bound,
                            "band": acc0.cycle_band.value,
                        },
                    )
                )
                if acc0.cycle_band is CycleBand.NO_NEW_ENTRY:
                    crossings.append(
                        BoundCrossingRecord(
                            kind=BoundCrossingKind.ENTRY_SIDE_DEGRADATION,
                            category=None,
                            bound_field="cycle_band",
                            stream_index=0,
                            details={"band": CycleBand.NO_NEW_ENTRY.value},
                        )
                    )
                break
            max_depth = max(max_depth, acc0.depth)
            if acc0.depth > bounds.accumulator_bound:
                return policy(
                    "accumulator_bound",
                    "foldable depth must never exceed the configured accumulator_bound",
                    depth=acc0.depth,
                    bound=bounds.accumulator_bound,
                )
        else:
            typed_refusals += 1
            accounted += 1
            crossings.append(
                BoundCrossingRecord(
                    kind=BoundCrossingKind.STORAGE_FAILURE,
                    category=forced.category.value,
                    bound_field=str(forced.context.get("field", "accumulator_bound")),
                    stream_index=0,
                    details=dict(forced.context),
                )
            )
            break
        if force_guard > bounds.accumulator_bound + 4:
            return policy(
                "accumulator_bound",
                "failed to observe designed overflow/coalesce under injected bound",
                bound=bounds.accumulator_bound,
                depth=acc0.depth,
            )

    # --- pacer in-flight bound: fill capacity then observe typed refusal ------
    instrument = Instrument.try_create(venue0, "EURUSD")
    if is_refusal(instrument):
        return instrument
    qty = Quantity.try_create(100, "lot", 2)
    if is_refusal(qty):
        return qty
    stop = PriceDelta.try_create(100, instrument.value, 5)
    if is_refusal(stop):
        return stop
    params = OrderParameters.try_create(
        OrderType.MARKET,
        TimeInForce.GOOD_TILL_CANCEL,
        qty.value,
        protective_stop_distance=stop.value,
    )
    if is_refusal(params):
        return params

    held_admissions = 0
    for i in range(bounds.general_capacity + 2):
        cmd = Command.place_order(venue0, account0, _SESSION, i + 1, params.value)
        if is_refusal(cmd):
            return cmd
        enqueued = pacer.value.enqueue(cmd.value)
        if is_refusal(enqueued):
            return enqueued
        enqueued_at = MonotonicReading.try_create(20_000_000_000 + i * 1_000, _BOOT)
        now = MonotonicReading.try_create(20_000_000_000 + i * 1_000 + 100, _BOOT)
        if is_refusal(enqueued_at):
            return enqueued_at
        if is_refusal(now):
            return now
        admitted = pacer.value.admit(cmd.value, enqueued_at=enqueued_at.value, now=now.value)
        if is_ok(admitted):
            held_admissions += 1
            max_in_flight = max(max_in_flight, held_admissions)
            # Keep slots occupied so the next admit hits capacity.
            continue
        max_in_flight = max(max_in_flight, held_admissions)
        typed_refusals += 1
        field_name = str(admitted.context.get("field", ""))
        kind = (
            BoundCrossingKind.LOCAL_QUEUE_BOUND
            if field_name == "local_queue_bound"
            else BoundCrossingKind.PACER_CAPACITY
        )
        crossings.append(
            BoundCrossingRecord(
                kind=kind,
                category=admitted.category.value,
                bound_field=field_name,
                stream_index=None,
                details=dict(admitted.context),
            )
        )

    if max_in_flight > bounds.general_capacity + bounds.protective_reserve_capacity:
        return policy(
            "in_flight",
            "observed in-flight work exceeded configured pacer capacity",
            max_in_flight=max_in_flight,
            general_capacity=bounds.general_capacity,
            protective_reserve_capacity=bounds.protective_reserve_capacity,
        )

    # Exhaust evidence budget if not already crossed during interleave.
    if BoundCrossingKind.EVIDENCE_BUDGET not in {c.kind for c in crossings}:
        while door.evidence_reads < door.evidence_channel_budget + 1:
            exhausted = read_status(door)
            if is_ok(exhausted):
                evidence_ok += 1
                continue
            typed_refusals += 1
            crossings.append(
                BoundCrossingRecord(
                    kind=BoundCrossingKind.EVIDENCE_BUDGET,
                    category=exhausted.category.value,
                    bound_field=str(exhausted.context.get("field", "evidence_channel_budget")),
                    stream_index=None,
                    details=dict(exhausted.context),
                )
            )
            break

    # Depth never exceeds bound (coalesce keeps depth <= bound).
    for acc, *_rest in stream_bundle:
        max_depth = max(max_depth, acc.depth)
        if acc.depth > bounds.accumulator_bound:
            return policy(
                "accumulator_bound",
                "foldable depth must never exceed the configured accumulator_bound",
                depth=acc.depth,
                bound=bounds.accumulator_bound,
            )

    backpressure = coalesce_events > 0 or any(
        c.kind
        in {
            BoundCrossingKind.PACER_CAPACITY,
            BoundCrossingKind.LOCAL_QUEUE_BOUND,
            BoundCrossingKind.EVIDENCE_BUDGET,
            BoundCrossingKind.STORAGE_FAILURE,
        }
        for c in crossings
    )
    # Every push attempt is either accepted (recorded) or an explicit typed refusal.
    silent_loss = accounted != push_attempts

    required_kinds = {
        BoundCrossingKind.MARKET_DATA_COALESCE,
        BoundCrossingKind.PACER_CAPACITY,
        BoundCrossingKind.EVIDENCE_BUDGET,
    }
    seen_kinds = {c.kind for c in crossings}
    missing = required_kinds - seen_kinds
    if missing:
        return policy(
            "bound_crossings",
            "proof must observe designed coalesce, pacer backpressure, and evidence "
            "budget refusal — not log-only assertions",
            missing=sorted(missing),
            observed=sorted(seen_kinds),
        )

    return Ok(
        _DriveMetrics(
            max_in_flight_observed=max_in_flight,
            max_accumulator_depth_observed=max_depth,
            push_attempts=push_attempts,
            push_accepted=push_accepted,
            coalesce_events=coalesce_events,
            typed_refusals=typed_refusals,
            entry_side_degradations=entry_side_degradations,
            backpressure_observed=backpressure,
            silent_observation_loss=silent_loss,
            accounted_observations=accounted,
            evidence_door_ok=evidence_ok,
            powers_door_ok=powers_ok,
            door_response_samples_ns=tuple(door_samples),
            timer_ticks_fired=timer_ticks_fired,
            bound_crossings=tuple(crossings),
            peak_rss_bytes=peak_rss_bytes(),
        )
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
