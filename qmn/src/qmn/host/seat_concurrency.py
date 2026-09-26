"""Seat concurrency and end-to-end backpressure proof (Story 26.19 / E15-F02).

Deterministic local/CI load drives concurrent streams, door reads, timers, and
QL-7 seat callbacks against **injected** bounds (Stories 25.16 and 26.8).
Measurements prove one event loop, bounded in-flight work, explicit
enqueue/backpressure, responsive doors, seat isolation, and no silent
observation loss — without inventing latency or capacity numbers (FTR-07) and
without claiming OS-level confinement (GAP-0054 deferred; NFR-13/21).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qmb.runloop import CancelToken, ScriptedLimitProbe
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
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import FunctionFactory

from qmn.bench.harness import collect_provenance, peak_rss_bytes
from qmn.bench.schema import BenchLifecycle, DeploymentProvenance
from qmn.doors.library import DoorRuntime, enact_power, read_status
from qmn.host._refuse import invalid, policy
from qmn.host.concurrency import (
    BoundCrossingKind,
    BoundCrossingRecord,
    ConcurrencyLoad,
    InjectedBounds,
)
from qmn.host.supervise import (
    ASYNC_ALLOWED_SURFACES,
    DOMAIN_BACKGROUND_THREADS_ALLOWED,
    EVENT_LOOP_COUNT,
    supervision_process_model,
)
from qmn.loop import (
    DATA_QUALITY_EVENT_TYPE,
    CycleBand,
    RecordingAccumulator,
    clear_first_writer_registry,
    protection_enactable,
)
from qmn.order import ConnectionCommandPacer
from qmn.seats.containment_limit import (
    GAP_0054_ID,
    GAP_0054_STATUS,
    V1_HARDENED_OS_CONFINEMENT,
    refuse_invented_os_hard_cap,
)
from qmn.seats.host import (
    GovernedSeat,
    SeatContainment,
    construct_governed_seat,
    drive_governed_seat,
)
from qmn.seats.state import (
    GovernedSeatState,
    QuarantineTrigger,
    SeatTransitionStream,
    fold_seat_state,
)
from qmn.time import host_perf_counter_ns
from qmn.venue import Command, OrderParameters, OrderType, TimeInForce

__all__ = [
    "SEAT_CONCURRENCY_SURFACE",
    "SeatConcurrencyLoad",
    "SeatConcurrencyProofReport",
    "SeatInjectedBounds",
    "SeatIsolationRecord",
    "prove_seat_concurrency",
]

SEAT_CONCURRENCY_SURFACE: Final[str] = "qmn.host.seat_concurrency"

_BOOT: Final[str] = "boot-epoch-seat-concurrency-26-19"
_SESSION: Final[str] = "session-epoch-seat-concurrency-26-19"
_WALL_BASE_NS: Final[int] = 1_725_400_000 * 1_000_000_000
_SOURCE: Final[dict[str, str]] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_MIN_SEATS_FOR_ISOLATION: Final[int] = 3
_ROLE_HEALTHY: Final[str] = "healthy"
_ROLE_DEADLINE: Final[str] = "deadline"
_ROLE_MEMORY: Final[str] = "memory"


@dataclass(frozen=True, slots=True)
class SeatConcurrencyLoad:
    """Deterministic load — seed owns stream/door/timer/callback interleaving."""

    host: ConcurrencyLoad
    seat_count: int
    callbacks_per_seat: int

    @property
    def seed(self) -> int:
        return self.host.seed

    @classmethod
    def try_create(
        cls,
        *,
        seed: object,
        stream_count: object = 2,
        observations_per_stream: object = 6,
        timer_ticks: object = None,
        door_interleave_every: object = 2,
        seat_count: object = 3,
        callbacks_per_seat: object = 2,
    ) -> Result[SeatConcurrencyLoad]:
        """Validate load; seat_count must isolate healthy vs deadline vs memory."""
        if timer_ticks is None:
            host = ConcurrencyLoad.try_create(
                seed=seed,
                stream_count=stream_count,
                observations_per_stream=observations_per_stream,
                door_interleave_every=door_interleave_every,
            )
        else:
            host = ConcurrencyLoad.try_create(
                seed=seed,
                stream_count=stream_count,
                observations_per_stream=observations_per_stream,
                timer_ticks=timer_ticks,
                door_interleave_every=door_interleave_every,
            )
        if is_refusal(host):
            return host
        seats = _require_positive_int(
            "seat_count",
            seat_count,
            "load dimension is a positive integer",
        )
        if is_refusal(seats):
            return seats
        if seats.value < _MIN_SEATS_FOR_ISOLATION:
            return invalid(
                "seat_count",
                "isolation proof needs a healthy seat plus one deadline-breach "
                "seat and one memory-ceiling seat",
                given=seats.value,
                minimum=_MIN_SEATS_FOR_ISOLATION,
            )
        callbacks = _require_positive_int(
            "callbacks_per_seat",
            callbacks_per_seat,
            "load dimension is a positive integer",
        )
        if is_refusal(callbacks):
            return callbacks
        return Ok(
            cls(
                host=host.value,
                seat_count=seats.value,
                callbacks_per_seat=callbacks.value,
            )
        )

    def as_mapping(self) -> Mapping[str, object]:
        body = dict(self.host.as_mapping())
        body["seat_count"] = self.seat_count
        body["callbacks_per_seat"] = self.callbacks_per_seat
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class SeatInjectedBounds:
    """Caller-supplied host bounds plus registry-resolved seat containment.

    Deadline and memory ceiling are never defaulted here (FTR-07).
    """

    host: InjectedBounds
    containment: SeatContainment

    @classmethod
    def try_create(
        cls,
        *,
        accumulator_bound: object,
        general_capacity: object,
        protective_reserve_capacity: object,
        local_queue_bound_ns: object,
        evidence_channel_budget: object,
        callback_deadline: object,
        memory_ceiling_bytes: object,
        governor_cpu_budget: object = None,
        governor_memory_budget: object = None,
    ) -> Result[SeatInjectedBounds]:
        """Admit injected host and seat bounds; refuse blanks and invented numbers."""
        host = InjectedBounds.try_create(
            accumulator_bound=accumulator_bound,
            general_capacity=general_capacity,
            protective_reserve_capacity=protective_reserve_capacity,
            local_queue_bound_ns=local_queue_bound_ns,
            evidence_channel_budget=evidence_channel_budget,
            governor_cpu_budget=governor_cpu_budget,
            governor_memory_budget=governor_memory_budget,
        )
        if is_refusal(host):
            return host
        containment = SeatContainment.try_create(
            callback_deadline=callback_deadline,
            memory_ceiling_bytes=memory_ceiling_bytes,
        )
        if is_refusal(containment):
            return containment
        return Ok(cls(host=host.value, containment=containment.value))

    def as_mapping(self) -> Mapping[str, object]:
        body = dict(self.host.as_mapping())
        body.update(dict(self.containment.as_mapping()))
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class SeatIsolationRecord:
    """One seat's isolation outcome under concurrent load."""

    seat_id: str
    role: str
    final_state: str
    stream_failure: bool
    node_restart: bool
    os_level_confinement: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "seat_id": self.seat_id,
                "role": self.role,
                "final_state": self.final_state,
                "stream_failure": self.stream_failure,
                "node_restart": self.node_restart,
                "os_level_confinement": self.os_level_confinement,
            }
        )


@dataclass(frozen=True, slots=True)
class SeatConcurrencyProofReport:
    """Measured seat-concurrency posture — schema complete without capacity gates."""

    surface: str
    load: SeatConcurrencyLoad
    bounds: SeatInjectedBounds
    provenance: DeploymentProvenance
    process_model: Mapping[str, object]
    event_loop_count: int
    domain_background_threads_allowed: bool
    async_allowed_surfaces: tuple[str, ...]
    wall_time_ns: int
    peak_rss_bytes: int
    max_in_flight_observed: int
    max_accumulator_depth_observed: int
    max_overlapping_seat_callbacks: int
    push_attempts: int
    push_accepted: int
    coalesce_events: int
    typed_refusals: int
    entry_side_degradations: int
    callbacks_attempted: int
    callbacks_ok: int
    callbacks_quarantined: int
    backpressure_observed: bool
    silent_observation_loss: bool
    accounted_observations: int
    evidence_door_ok: int
    powers_door_ok: int
    door_response_samples_ns: tuple[int, ...]
    timer_ticks_fired: int
    bound_crossings: tuple[BoundCrossingRecord, ...]
    isolation: tuple[SeatIsolationRecord, ...]
    protection_preserved: bool
    exits_preserved: bool
    protective_command_admitted: bool
    os_level_confinement: bool
    gap_0054: str
    gap_0054_closed: bool
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
                "domain_background_threads_allowed": (self.domain_background_threads_allowed),
                "async_allowed_surfaces": list(self.async_allowed_surfaces),
                "wall_time_ns": self.wall_time_ns,
                "peak_rss_bytes": self.peak_rss_bytes,
                "max_in_flight_observed": self.max_in_flight_observed,
                "max_accumulator_depth_observed": self.max_accumulator_depth_observed,
                "max_overlapping_seat_callbacks": self.max_overlapping_seat_callbacks,
                "push_attempts": self.push_attempts,
                "push_accepted": self.push_accepted,
                "coalesce_events": self.coalesce_events,
                "typed_refusals": self.typed_refusals,
                "entry_side_degradations": self.entry_side_degradations,
                "callbacks_attempted": self.callbacks_attempted,
                "callbacks_ok": self.callbacks_ok,
                "callbacks_quarantined": self.callbacks_quarantined,
                "backpressure_observed": self.backpressure_observed,
                "silent_observation_loss": self.silent_observation_loss,
                "accounted_observations": self.accounted_observations,
                "evidence_door_ok": self.evidence_door_ok,
                "powers_door_ok": self.powers_door_ok,
                "door_response_samples_ns": list(self.door_response_samples_ns),
                "timer_ticks_fired": self.timer_ticks_fired,
                "bound_crossings": [dict(item.as_mapping()) for item in self.bound_crossings],
                "isolation": [dict(item.as_mapping()) for item in self.isolation],
                "protection_preserved": self.protection_preserved,
                "exits_preserved": self.exits_preserved,
                "protective_command_admitted": self.protective_command_admitted,
                "os_level_confinement": self.os_level_confinement,
                "gap_0054": self.gap_0054,
                "gap_0054_closed": self.gap_0054_closed,
                "v1_hardened_os_confinement": V1_HARDENED_OS_CONFINEMENT,
            }
        )


def prove_seat_concurrency(
    *,
    load: object,
    bounds: object,
    lifecycle: object = BenchLifecycle.PRE_DOORS_OPEN,
    deployment_id: object = "local-ci",
    close_gap_0054: object = False,
    os_hard_cap_bytes: object = None,
) -> Result[SeatConcurrencyProofReport]:
    """Run the seat-concurrency/backpressure proof and return measured evidence."""
    if close_gap_0054 is True or os_hard_cap_bytes is not None:
        invented = refuse_invented_os_hard_cap(
            close_gap_0054=close_gap_0054,
            os_hard_cap_bytes=os_hard_cap_bytes,
        )
        if is_refusal(invented):
            return invented
    if not isinstance(load, SeatConcurrencyLoad):
        return invalid(
            "load",
            "prove_seat_concurrency requires a SeatConcurrencyLoad",
            given=type(load).__name__,
        )
    if not isinstance(bounds, SeatInjectedBounds):
        return invalid(
            "bounds",
            "prove_seat_concurrency requires SeatInjectedBounds supplied by the caller",
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
    if bounds.host.accumulator_bound < 1:
        return policy(
            "accumulator_bound",
            "an unbounded or non-positive accumulator is an absent mechanism",
            given=bounds.host.accumulator_bound,
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
        SeatConcurrencyProofReport(
            surface=SEAT_CONCURRENCY_SURFACE,
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
            max_overlapping_seat_callbacks=payload.max_overlapping_seat_callbacks,
            push_attempts=payload.push_attempts,
            push_accepted=payload.push_accepted,
            coalesce_events=payload.coalesce_events,
            typed_refusals=payload.typed_refusals,
            entry_side_degradations=payload.entry_side_degradations,
            callbacks_attempted=payload.callbacks_attempted,
            callbacks_ok=payload.callbacks_ok,
            callbacks_quarantined=payload.callbacks_quarantined,
            backpressure_observed=payload.backpressure_observed,
            silent_observation_loss=payload.silent_observation_loss,
            accounted_observations=payload.accounted_observations,
            evidence_door_ok=payload.evidence_door_ok,
            powers_door_ok=payload.powers_door_ok,
            door_response_samples_ns=payload.door_response_samples_ns,
            timer_ticks_fired=payload.timer_ticks_fired,
            bound_crossings=payload.bound_crossings,
            isolation=payload.isolation,
            protection_preserved=payload.protection_preserved,
            exits_preserved=payload.exits_preserved,
            protective_command_admitted=payload.protective_command_admitted,
            os_level_confinement=V1_HARDENED_OS_CONFINEMENT,
            gap_0054=GAP_0054_ID,
            gap_0054_closed=False,
        )
    )


@dataclass
class _DriveMetrics:
    max_in_flight_observed: int
    max_accumulator_depth_observed: int
    max_overlapping_seat_callbacks: int
    push_attempts: int
    push_accepted: int
    coalesce_events: int
    typed_refusals: int
    entry_side_degradations: int
    callbacks_attempted: int
    callbacks_ok: int
    callbacks_quarantined: int
    backpressure_observed: bool
    silent_observation_loss: bool
    accounted_observations: int
    evidence_door_ok: int
    powers_door_ok: int
    door_response_samples_ns: tuple[int, ...]
    timer_ticks_fired: int
    bound_crossings: tuple[BoundCrossingRecord, ...]
    isolation: tuple[SeatIsolationRecord, ...]
    protection_preserved: bool
    exits_preserved: bool
    protective_command_admitted: bool
    peak_rss_bytes: int


@dataclass
class _DriveBox:
    crossings: list[BoundCrossingRecord] = field(default_factory=list[BoundCrossingRecord])
    door_samples: list[int] = field(default_factory=list[int])
    push_attempts: int = 0
    push_accepted: int = 0
    coalesce_events: int = 0
    typed_refusals: int = 0
    entry_side_degradations: int = 0
    accounted: int = 0
    max_depth: int = 0
    max_in_flight: int = 0
    max_overlapping: int = 0
    overlapping: int = 0
    evidence_ok: int = 0
    powers_ok: int = 0
    timer_ticks_fired: int = 0
    wall_seq: int = 0
    callbacks_attempted: int = 0
    callbacks_ok: int = 0
    callbacks_quarantined: int = 0
    protective_admitted: bool = False
    protection_preserved: bool = False
    exits_preserved: bool = False


def _drive_load(*, load: SeatConcurrencyLoad, bounds: SeatInjectedBounds) -> Result[_DriveMetrics]:
    streams = _build_streams(load=load, bounds=bounds.host)
    if is_refusal(streams):
        return streams
    stream_bundle = streams.value
    seats = _build_seats(load=load, containment=bounds.containment)
    if is_refusal(seats):
        return seats
    seat_bundle = seats.value

    door = DoorRuntime(
        boot_epoch=_BOOT,
        composition_fp="fp1:seat-concurrency-proof",
        knowledge_time_ns=1_000,
        watermark_ns=900,
        source_time_ns=950,
        receive_time_ns=980,
        evidence_channel_budget=bounds.host.evidence_channel_budget,
        lifecycle="pre-doors-open",
    )
    queue_bound = Duration.try_create(bounds.host.local_queue_bound_ns)
    if is_refusal(queue_bound):
        return queue_bound
    pacer = ConnectionCommandPacer.try_create(
        local_queue_bound=queue_bound.value,
        protective_reserve_capacity=bounds.host.protective_reserve_capacity,
        general_capacity=bounds.host.general_capacity,
    )
    if is_refusal(pacer):
        return pacer

    box = _DriveBox()
    rng = _Deterministic(load.seed)
    stream_obj = SeatTransitionStream()
    actions = _plan_actions(load)
    _shuffle(actions, rng)

    pushes_done = 0
    for action in actions:
        if action.kind == "push":
            pushed = _push_one(
                box=box,
                stream_bundle=stream_bundle,
                bounds=bounds.host,
                rng=rng,
                stream_count=load.host.stream_count,
            )
            if is_refusal(pushed):
                return pushed
            pushes_done += 1
            if pushes_done % load.host.door_interleave_every == 0:
                door_step = _interleave_doors(box=box, door=door, step=pushes_done)
                if is_refusal(door_step):
                    return door_step
        elif action.kind == "seat":
            driven = _drive_one_seat(
                box=box,
                seat_row=seat_bundle[action.index],
                stream=stream_obj,
            )
            if is_refusal(driven):
                return driven
        else:
            _ = host_perf_counter_ns()
            box.timer_ticks_fired += 1

    overflow = _force_overflow(box=box, stream_bundle=stream_bundle, bounds=bounds.host)
    if is_refusal(overflow):
        return overflow

    acc0 = stream_bundle[0][0]
    box.exits_preserved = protection_enactable(acc0.cycle_band, act="close_all")
    box.protection_preserved = box.exits_preserved or acc0.cycle_band is CycleBand.OK

    venue0 = stream_bundle[0][3]
    account0 = stream_bundle[0][4]
    pacer_step = _force_pacer_and_protection(
        box=box,
        pacer=pacer.value,
        bounds=bounds.host,
        venue=venue0,
        account=account0,
    )
    if is_refusal(pacer_step):
        return pacer_step

    budget = _force_evidence_budget(box=box, door=door)
    if is_refusal(budget):
        return budget

    for acc, *_rest in stream_bundle:
        box.max_depth = max(box.max_depth, acc.depth)
        if acc.depth > bounds.host.accumulator_bound:
            return policy(
                "accumulator_bound",
                "foldable depth must never exceed the configured accumulator_bound",
                depth=acc.depth,
                bound=bounds.host.accumulator_bound,
            )

    isolation = _fold_isolation(seat_bundle=seat_bundle, stream=stream_obj)
    if is_refusal(isolation):
        return isolation

    if not box.exits_preserved:
        return policy(
            "exits_preserved",
            "entry-side degradation must leave exits and protection enactable",
            band=acc0.cycle_band.value,
        )
    if any(row.stream_failure or row.node_restart for row in isolation.value):
        return policy(
            "isolation",
            "a seat quarantine is never a stream failure and never a node restart",
            isolation=[dict(row.as_mapping()) for row in isolation.value],
        )
    if any(row.os_level_confinement for row in isolation.value):
        return policy(
            "os_level_confinement",
            "V1 seat concurrency proof must not claim OS-level confinement",
            gap_id=GAP_0054_ID,
            gap_status=GAP_0054_STATUS,
        )

    backpressure = box.coalesce_events > 0 or any(
        crossing.kind
        in {
            BoundCrossingKind.PACER_CAPACITY,
            BoundCrossingKind.LOCAL_QUEUE_BOUND,
            BoundCrossingKind.EVIDENCE_BUDGET,
            BoundCrossingKind.STORAGE_FAILURE,
            BoundCrossingKind.SEAT_DEADLINE_QUARANTINE,
            BoundCrossingKind.SEAT_MEMORY_QUARANTINE,
        }
        for crossing in box.crossings
    )
    silent_loss = box.accounted != box.push_attempts
    required_kinds = {
        BoundCrossingKind.MARKET_DATA_COALESCE,
        BoundCrossingKind.PACER_CAPACITY,
        BoundCrossingKind.EVIDENCE_BUDGET,
        BoundCrossingKind.LOCAL_QUEUE_BOUND,
        BoundCrossingKind.SEAT_DEADLINE_QUARANTINE,
        BoundCrossingKind.SEAT_MEMORY_QUARANTINE,
        BoundCrossingKind.ENTRY_SIDE_DEGRADATION,
    }
    seen = {crossing.kind for crossing in box.crossings}
    missing = required_kinds - seen
    if missing:
        return policy(
            "bound_crossings",
            "proof must observe designed coalesce, pacer, queue-bound, evidence "
            "budget, seat deadline/memory quarantine, and entry-side degradation "
            "— not log-only assertions",
            missing=sorted(missing),
            observed=sorted(seen),
        )
    if box.max_overlapping > 1:
        return policy(
            "seat_callbacks",
            "domain seat callbacks run on the one event-loop thread; overlapping "
            "callbacks would imply an undeclared background thread",
            max_overlapping_seat_callbacks=box.max_overlapping,
        )

    return Ok(
        _DriveMetrics(
            max_in_flight_observed=box.max_in_flight,
            max_accumulator_depth_observed=box.max_depth,
            max_overlapping_seat_callbacks=box.max_overlapping,
            push_attempts=box.push_attempts,
            push_accepted=box.push_accepted,
            coalesce_events=box.coalesce_events,
            typed_refusals=box.typed_refusals,
            entry_side_degradations=box.entry_side_degradations,
            callbacks_attempted=box.callbacks_attempted,
            callbacks_ok=box.callbacks_ok,
            callbacks_quarantined=box.callbacks_quarantined,
            backpressure_observed=backpressure,
            silent_observation_loss=silent_loss,
            accounted_observations=box.accounted,
            evidence_door_ok=box.evidence_ok,
            powers_door_ok=box.powers_ok,
            door_response_samples_ns=tuple(box.door_samples),
            timer_ticks_fired=box.timer_ticks_fired,
            bound_crossings=tuple(box.crossings),
            isolation=isolation.value,
            protection_preserved=box.protection_preserved,
            exits_preserved=box.exits_preserved,
            protective_command_admitted=box.protective_admitted,
            peak_rss_bytes=peak_rss_bytes(),
        )
    )


@dataclass(frozen=True, slots=True)
class _Action:
    kind: str
    index: int


@dataclass(frozen=True, slots=True)
class _SeatRow:
    seat: GovernedSeat
    role: str
    cancel: CancelToken
    probe: ScriptedLimitProbe


def _plan_actions(load: SeatConcurrencyLoad) -> list[_Action]:
    actions: list[_Action] = []
    total_pushes = load.host.stream_count * load.host.observations_per_stream
    actions.extend(_Action("push", 0) for _ in range(total_pushes))
    for seat_index in range(load.seat_count):
        actions.extend(_Action("seat", seat_index) for _ in range(load.callbacks_per_seat))
    actions.extend(_Action("timer", 0) for _ in range(load.host.timer_ticks))
    return actions


def _shuffle(items: list[_Action], rng: _Deterministic) -> None:
    for i in range(len(items) - 1, 0, -1):
        j = rng.next_int(i + 1)
        items[i], items[j] = items[j], items[i]


def _push_one(
    *,
    box: _DriveBox,
    stream_bundle: Sequence[tuple[RecordingAccumulator, _ListSink, _ListSink, VenueId, Account]],
    bounds: InjectedBounds,
    rng: _Deterministic,
    stream_count: int,
) -> Result[None]:
    stream_index = rng.next_int(stream_count)
    acc, obs_sink, _journal_sink, _venue, _account = stream_bundle[stream_index]
    box.wall_seq += 1
    box.push_attempts += 1
    before_coalesce = len(acc.coalesce_events)
    result = acc.push(
        observation_id=f"spot-{stream_index}-{box.wall_seq}",
        stream_id="eurusd",
        receive_wall=_instant(_WALL_BASE_NS + box.wall_seq * 1_000_000),
        payload={"kind": "spot", "step": box.wall_seq, "stream": stream_index},
        kind="spot",
        coalesce_key="eurusd",
    )
    if is_ok(result):
        box.push_accepted += 1
        box.accounted += 1
        if len(obs_sink.rows) < 1 and len(acc.coalesce_events) == before_coalesce:
            return policy(
                "observation_accounting",
                "accepted push must leave governed intake or coalesce evidence; "
                "silent observation loss is forbidden",
                stream_index=stream_index,
                step=box.wall_seq,
            )
        if len(acc.coalesce_events) > before_coalesce:
            _record_coalesce(box=box, acc=acc, bounds=bounds, stream_index=stream_index)
        box.max_depth = max(box.max_depth, acc.depth)
        return Ok(None)
    box.typed_refusals += 1
    box.accounted += 1
    box.crossings.append(
        BoundCrossingRecord(
            kind=BoundCrossingKind.STORAGE_FAILURE,
            category=result.category.value,
            bound_field=str(result.context.get("field", "accumulator_bound")),
            stream_index=stream_index,
            details=dict(result.context),
        )
    )
    if acc.cycle_band is CycleBand.NO_NEW_ENTRY:
        box.entry_side_degradations += 1
    box.max_depth = max(box.max_depth, acc.depth)
    return Ok(None)


def _record_coalesce(
    *,
    box: _DriveBox,
    acc: RecordingAccumulator,
    bounds: InjectedBounds,
    stream_index: int,
) -> None:
    box.coalesce_events += 1
    box.entry_side_degradations += 1
    box.crossings.append(
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
        box.crossings.append(
            BoundCrossingRecord(
                kind=BoundCrossingKind.ENTRY_SIDE_DEGRADATION,
                category=None,
                bound_field="cycle_band",
                stream_index=stream_index,
                details={"band": CycleBand.NO_NEW_ENTRY.value},
            )
        )


def _interleave_doors(*, box: _DriveBox, door: DoorRuntime, step: int) -> Result[None]:
    door_start = host_perf_counter_ns()
    status = read_status(door)
    box.door_samples.append(host_perf_counter_ns() - door_start)
    if is_ok(status):
        box.evidence_ok += 1
    elif (
        status.category is RefusalCategory.POLICY_REJECTION
        and str(status.context.get("field", "")) == "evidence_channel_budget"
    ):
        box.typed_refusals += 1
        box.crossings.append(
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
    box.door_samples.append(host_perf_counter_ns() - power_start)
    if is_ok(power):
        box.powers_ok += 1
        return Ok(None)
    return power


def _drive_one_seat(
    *,
    box: _DriveBox,
    seat_row: _SeatRow,
    stream: SeatTransitionStream,
) -> Result[None]:
    box.wall_seq += 1
    box.callbacks_attempted += 1
    box.overlapping += 1
    box.max_overlapping = max(box.max_overlapping, box.overlapping)
    instant = _instant(_WALL_BASE_NS + box.wall_seq * 1_000_000)
    result = drive_governed_seat(
        seat_row.seat,
        instant,
        stream=stream,
        cancel=seat_row.cancel,
        probe=seat_row.probe,
        transition_instant=instant,
    )
    box.overlapping -= 1
    if is_ok(result):
        box.callbacks_ok += 1
        return Ok(None)
    box.typed_refusals += 1
    stream_failure = result.context.get("stream_failure") is True
    node_restart = result.context.get("node_restart") is True
    if stream_failure or node_restart:
        return policy(
            "seat",
            "a seat-callback containment breach must not fail the stream or restart the node",
            seat_id=seat_row.seat.seat_id,
            stream_failure=stream_failure,
            node_restart=node_restart,
        )
    if result.context.get("os_level_confinement") is True:
        return policy(
            "os_level_confinement",
            "V1 seat concurrency proof must not claim OS-level confinement",
            gap_id=GAP_0054_ID,
            gap_status=GAP_0054_STATUS,
            seat_id=seat_row.seat.seat_id,
        )
    trigger = str(result.context.get("trigger", ""))
    if trigger == QuarantineTrigger.DEADLINE_BREACH.value:
        box.callbacks_quarantined += 1
        box.crossings.append(
            BoundCrossingRecord(
                kind=BoundCrossingKind.SEAT_DEADLINE_QUARANTINE,
                category=result.category.value,
                bound_field="seat_callback_deadline",
                stream_index=None,
                details=dict(result.context),
            )
        )
    elif trigger == QuarantineTrigger.MEMORY_CEILING_BREACH.value:
        box.callbacks_quarantined += 1
        box.crossings.append(
            BoundCrossingRecord(
                kind=BoundCrossingKind.SEAT_MEMORY_QUARANTINE,
                category=result.category.value,
                bound_field="seat_memory_ceiling",
                stream_index=None,
                details=dict(result.context),
            )
        )
    return Ok(None)


def _force_overflow(
    *,
    box: _DriveBox,
    stream_bundle: Sequence[tuple[RecordingAccumulator, _ListSink, _ListSink, VenueId, Account]],
    bounds: InjectedBounds,
) -> Result[None]:
    if BoundCrossingKind.MARKET_DATA_COALESCE in {c.kind for c in box.crossings}:
        return Ok(None)
    acc0, _obs0, _j0, _venue0, _account0 = stream_bundle[0]
    force_guard = 0
    while BoundCrossingKind.MARKET_DATA_COALESCE not in {c.kind for c in box.crossings}:
        box.wall_seq += 1
        force_guard += 1
        box.push_attempts += 1
        before_coalesce = len(acc0.coalesce_events)
        forced = acc0.push(
            observation_id=f"force-overflow-{box.wall_seq}",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_BASE_NS + box.wall_seq * 1_000_000),
            payload={"kind": "spot", "force": True},
            kind="spot",
            coalesce_key="eurusd",
        )
        if is_ok(forced):
            box.push_accepted += 1
            box.accounted += 1
            if len(acc0.coalesce_events) > before_coalesce:
                _record_coalesce(box=box, acc=acc0, bounds=bounds, stream_index=0)
                return Ok(None)
            box.max_depth = max(box.max_depth, acc0.depth)
            if acc0.depth > bounds.accumulator_bound:
                return policy(
                    "accumulator_bound",
                    "foldable depth must never exceed the configured accumulator_bound",
                    depth=acc0.depth,
                    bound=bounds.accumulator_bound,
                )
        else:
            box.typed_refusals += 1
            box.accounted += 1
            box.crossings.append(
                BoundCrossingRecord(
                    kind=BoundCrossingKind.STORAGE_FAILURE,
                    category=forced.category.value,
                    bound_field=str(forced.context.get("field", "accumulator_bound")),
                    stream_index=0,
                    details=dict(forced.context),
                )
            )
            return Ok(None)
        if force_guard > bounds.accumulator_bound + 4:
            return policy(
                "accumulator_bound",
                "failed to observe designed overflow/coalesce under injected bound",
                bound=bounds.accumulator_bound,
                depth=acc0.depth,
            )
    return Ok(None)


def _force_pacer_and_protection(
    *,
    box: _DriveBox,
    pacer: ConnectionCommandPacer,
    bounds: InjectedBounds,
    venue: VenueId,
    account: Account,
) -> Result[None]:
    instrument = Instrument.try_create(venue, "EURUSD")
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

    queue = _observe_queue_bound(
        box=box,
        pacer=pacer,
        bounds=bounds,
        venue=venue,
        account=account,
        params=params.value,
    )
    if is_refusal(queue):
        return queue

    held = 0
    ordinal = 10
    for i in range(bounds.general_capacity + 2):
        ordinal += 1
        cmd = Command.place_order(venue, account, _SESSION, ordinal, params.value)
        if is_refusal(cmd):
            return cmd
        enqueued = pacer.enqueue(cmd.value)
        if is_refusal(enqueued):
            return enqueued
        enqueued_at = MonotonicReading.try_create(30_000_000_000 + i * 1_000, _BOOT)
        now = MonotonicReading.try_create(30_000_000_000 + i * 1_000 + 100, _BOOT)
        if is_refusal(enqueued_at):
            return enqueued_at
        if is_refusal(now):
            return now
        admitted = pacer.admit(cmd.value, enqueued_at=enqueued_at.value, now=now.value)
        if is_ok(admitted):
            held += 1
            box.max_in_flight = max(box.max_in_flight, held)
            continue
        box.max_in_flight = max(box.max_in_flight, held)
        box.typed_refusals += 1
        field_name = str(admitted.context.get("field", ""))
        kind = (
            BoundCrossingKind.LOCAL_QUEUE_BOUND
            if field_name == "local_queue_bound"
            else BoundCrossingKind.PACER_CAPACITY
        )
        box.crossings.append(
            BoundCrossingRecord(
                kind=kind,
                category=admitted.category.value,
                bound_field=field_name,
                stream_index=None,
                details=dict(admitted.context),
            )
        )

    cap = bounds.general_capacity + bounds.protective_reserve_capacity
    if box.max_in_flight > cap:
        return policy(
            "in_flight",
            "observed in-flight work exceeded configured pacer capacity",
            max_in_flight=box.max_in_flight,
            general_capacity=bounds.general_capacity,
            protective_reserve_capacity=bounds.protective_reserve_capacity,
        )

    close_cmd = Command.close_all(
        venue,
        account,
        _SESSION,
        ordinal + 1,
        "account",
        account.account_id,
    )
    if is_refusal(close_cmd):
        return close_cmd
    enqueued_close = pacer.enqueue(close_cmd.value)
    if is_refusal(enqueued_close):
        return enqueued_close
    close_at = MonotonicReading.try_create(40_000_000_000, _BOOT)
    close_now = MonotonicReading.try_create(40_000_000_000 + 100, _BOOT)
    if is_refusal(close_at):
        return close_at
    if is_refusal(close_now):
        return close_now
    closed = pacer.admit(close_cmd.value, enqueued_at=close_at.value, now=close_now.value)
    if is_ok(closed):
        box.protective_admitted = True
        box.max_in_flight = max(box.max_in_flight, held + 1)
        box.protection_preserved = True
        box.exits_preserved = True
        return Ok(None)
    if bounds.protective_reserve_capacity < 1:
        # Reserve was not configured; cycle-band enactability still stands.
        return Ok(None)
    return policy(
        "protection_preserved",
        "protective close_all must admit from reserve after entry capacity is "
        "held and seats have quarantined; exits/protection stay enactable",
        category=closed.category.value,
        details=dict(closed.context),
    )


def _observe_queue_bound(
    *,
    box: _DriveBox,
    pacer: ConnectionCommandPacer,
    bounds: InjectedBounds,
    venue: VenueId,
    account: Account,
    params: OrderParameters,
) -> Result[None]:
    cmd = Command.place_order(venue, account, _SESSION, 1, params)
    if is_refusal(cmd):
        return cmd
    enqueued = pacer.enqueue(cmd.value)
    if is_refusal(enqueued):
        return enqueued
    enqueued_at = MonotonicReading.try_create(10_000_000_000, _BOOT)
    late = MonotonicReading.try_create(10_000_000_000 + bounds.local_queue_bound_ns + 1, _BOOT)
    if is_refusal(enqueued_at):
        return enqueued_at
    if is_refusal(late):
        return late
    refused = pacer.admit(cmd.value, enqueued_at=enqueued_at.value, now=late.value)
    if is_ok(refused):
        return policy(
            "local_queue_bound",
            "a wait past the injected local_queue_bound must be a typed refusal",
            bound_ns=bounds.local_queue_bound_ns,
        )
    box.typed_refusals += 1
    box.crossings.append(
        BoundCrossingRecord(
            kind=BoundCrossingKind.LOCAL_QUEUE_BOUND,
            category=refused.category.value,
            bound_field=str(refused.context.get("field", "local_queue_bound")),
            stream_index=None,
            details=dict(refused.context),
        )
    )
    return Ok(None)


def _force_evidence_budget(*, box: _DriveBox, door: DoorRuntime) -> Result[None]:
    if BoundCrossingKind.EVIDENCE_BUDGET in {c.kind for c in box.crossings}:
        return Ok(None)
    while door.evidence_reads < door.evidence_channel_budget + 1:
        exhausted = read_status(door)
        if is_ok(exhausted):
            box.evidence_ok += 1
            continue
        box.typed_refusals += 1
        box.crossings.append(
            BoundCrossingRecord(
                kind=BoundCrossingKind.EVIDENCE_BUDGET,
                category=exhausted.category.value,
                bound_field=str(exhausted.context.get("field", "evidence_channel_budget")),
                stream_index=None,
                details=dict(exhausted.context),
            )
        )
        return Ok(None)
    return policy(
        "evidence_channel_budget",
        "failed to observe designed evidence-channel budget refusal",
        budget=door.evidence_channel_budget,
        reads=door.evidence_reads,
    )


def _fold_isolation(
    *, seat_bundle: Sequence[_SeatRow], stream: SeatTransitionStream
) -> Result[tuple[SeatIsolationRecord, ...]]:
    rows: list[SeatIsolationRecord] = []
    for item in seat_bundle:
        folded = fold_seat_state(stream, item.seat.seat_id)
        if is_refusal(folded):
            return folded
        state = folded.value
        if item.role == _ROLE_HEALTHY and state is not GovernedSeatState.ADMITTED:
            return policy(
                "isolation",
                "a healthy seat must stay admitted while sibling seats quarantine",
                seat_id=item.seat.seat_id,
                state=state.value,
            )
        if item.role in {_ROLE_DEADLINE, _ROLE_MEMORY} and (
            state is not GovernedSeatState.QUARANTINED
        ):
            return policy(
                "isolation",
                "deadline and memory-ceiling seats must quarantine under injected "
                "containment; siblings stay admitted",
                seat_id=item.seat.seat_id,
                role=item.role,
                state=state.value,
            )
        rows.append(
            SeatIsolationRecord(
                seat_id=item.seat.seat_id,
                role=item.role,
                final_state=state.value,
                stream_failure=False,
                node_restart=False,
                os_level_confinement=False,
            )
        )
    return Ok(tuple(rows))


def _build_streams(
    *, load: SeatConcurrencyLoad, bounds: InjectedBounds
) -> Result[list[tuple[RecordingAccumulator, _ListSink, _ListSink, VenueId, Account]]]:
    out: list[tuple[RecordingAccumulator, _ListSink, _ListSink, VenueId, Account]] = []
    for index in range(load.host.stream_count):
        venue = VenueId.try_create(f"conformance:seat-concurrency-{load.seed}-{index}")
        if is_refusal(venue):
            return venue
        account = Account.try_create(
            f"seat-concurrency-acct-{load.seed}-{index}",
            venue.value,
            AccountRole.DEMO,
        )
        if is_refusal(account):
            return account
        writer = WriterId.try_create(
            "seat-concurrency-host",
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
            writer_name=f"seat-concurrency-acc-{load.seed}-{index}",
        )
        if is_refusal(acc):
            return acc
        out.append((acc.value, obs_sink, journal_sink, venue.value, account.value))
    return Ok(out)


def _build_seats(
    *, load: SeatConcurrencyLoad, containment: SeatContainment
) -> Result[list[_SeatRow]]:
    declaration = _bot_declaration()
    if is_refusal(declaration):
        return declaration
    rows: list[_SeatRow] = []
    for index in range(load.seat_count):
        role = _role_for(index)
        factory = FunctionFactory(logic=_silent_logic)
        seat = construct_governed_seat(
            factory,
            seat_id=f"seat-{index}",
            binding_ref=f"binding-seat-{index}",
            declaration=declaration.value,
            containment=containment,
            read_surfaces={},
            stream_id=f"stream-seat-{index}",
        )
        if is_refusal(seat):
            return seat
        rows.append(
            _SeatRow(
                seat=seat.value,
                role=role,
                cancel=CancelToken(),
                probe=_probe_for(role, containment),
            )
        )
    return Ok(rows)


def _role_for(index: int) -> str:
    if index == 1:
        return _ROLE_DEADLINE
    if index == 2:
        return _ROLE_MEMORY
    return _ROLE_HEALTHY


def _probe_for(role: str, containment: SeatContainment) -> ScriptedLimitProbe:
    if role == _ROLE_DEADLINE:
        return ScriptedLimitProbe(
            elapsed_ns=(containment.callback_deadline.value_ns,),
            memory_bytes=(1,),
        )
    if role == _ROLE_MEMORY:
        return ScriptedLimitProbe(
            elapsed_ns=(0,),
            memory_bytes=(containment.memory_ceiling_bytes,),
        )
    return ScriptedLimitProbe(elapsed_ns=(0,), memory_bytes=(1,))


def _silent_logic(evidence: object) -> object:
    del evidence
    return ()


def _bot_declaration() -> Result[BotDefinition]:
    calendar = CalendarIdentity.try_create("forex-17NY", "v3", "2025.2")
    if is_refusal(calendar):
        return calendar
    zone = fingerprint({"class": "test-producer", "tag": "zone"})
    if is_refusal(zone):
        return zone
    zone_binding = ProducerBinding.try_create(zone.value)
    if is_refusal(zone_binding):
        return zone_binding
    confluence = mint_confluence([{"role": "level", "producer_binding": zone_binding.value}])
    if is_refusal(confluence):
        return confluence
    sma = fingerprint({"class": "test-producer", "tag": "sma"})
    if is_refusal(sma):
        return sma
    sma_binding = ProducerBinding.try_create(sma.value)
    if is_refusal(sma_binding):
        return sma_binding
    footprint = mint_footprint(
        [
            {
                "instrument_role": "primary",
                "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                "stream_role": "trading",
            }
        ],
        [calendar.value],
        [sma_binding.value],
    )
    if is_refusal(footprint):
        return footprint
    logic = mint_logic_identity("research-bot", "1.0.0", _SOURCE)
    if is_refusal(logic):
        return logic
    return mint_bot_definition(
        strategy_family_id="trend-follow",
        confluence_set=[confluence.value],
        parameter_space=[
            {
                "name": "lookback",
                "type": "exact integer",
                "bounds": {"min": 1, "max": 200},
                "step": 1,
                "default": 20,
                "unit_kind": UnitKind.COUNT,
                "ui": "ui-editable",
            }
        ],
        footprint=footprint.value,
        permitted_exit_intents=(),
        logic_reference=logic.value,
    )


def _require_positive_int(name: str, value: object, reason: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(name, reason, given=repr(value))
    return Ok(value)


def _instant(ns: int) -> Instant:
    made = Instant.try_create(ns)
    if is_refusal(made):
        raise AssertionError(f"seat concurrency proof instant construct failed: {made}")
    return made.value


class _Deterministic:
    """Tiny LCG — deterministic stream selection and action shuffle from seed."""

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
