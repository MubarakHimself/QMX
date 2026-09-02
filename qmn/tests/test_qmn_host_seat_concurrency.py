"""Story 26.19 — prove seat concurrency and end-to-end backpressure (E15-F02)."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core import Duration, RefusalCategory, Result, is_ok, is_refusal
from qmn.bench import BenchLifecycle
from qmn.host import (
    ASYNC_ALLOWED_SURFACES,
    DOMAIN_BACKGROUND_THREADS_ALLOWED,
    EVENT_LOOP_COUNT,
    SEAT_CONCURRENCY_OWNED_BY,
    SEAT_CONCURRENCY_SURFACE,
    BoundCrossingKind,
    SeatConcurrencyLoad,
    SeatInjectedBounds,
    prove_seat_concurrency,
    supervision_process_model,
)
from qmn.seats import (
    GAP_0054_ID,
    GAP_0054_STATUS,
    V1_HARDENED_OS_CONFINEMENT,
    GovernedSeatState,
    scan_os_confinement_apis,
)

T = TypeVar("T")

_HOST_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "host"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _bounds(
    *,
    accumulator_bound: int = 2,
    general_capacity: int = 1,
    protective_reserve_capacity: int = 1,
    local_queue_bound_ns: int = 1_000_000_000,
    evidence_channel_budget: int = 4,
    deadline_ns: int = 1_000_000,
    memory_ceiling_bytes: int = 10_000,
    governor_cpu_budget: int | None = None,
    governor_memory_budget: int | None = None,
) -> SeatInjectedBounds:
    return _ok(
        SeatInjectedBounds.try_create(
            accumulator_bound=accumulator_bound,
            general_capacity=general_capacity,
            protective_reserve_capacity=protective_reserve_capacity,
            local_queue_bound_ns=local_queue_bound_ns,
            evidence_channel_budget=evidence_channel_budget,
            callback_deadline=_duration(deadline_ns),
            memory_ceiling_bytes=memory_ceiling_bytes,
            governor_cpu_budget=governor_cpu_budget,
            governor_memory_budget=governor_memory_budget,
        )
    )


def _load(
    *,
    seed: int = 26_19,
    stream_count: int = 2,
    observations_per_stream: int = 6,
    timer_ticks: int = 3,
    door_interleave_every: int = 2,
    seat_count: int = 3,
    callbacks_per_seat: int = 2,
) -> SeatConcurrencyLoad:
    return _ok(
        SeatConcurrencyLoad.try_create(
            seed=seed,
            stream_count=stream_count,
            observations_per_stream=observations_per_stream,
            timer_ticks=timer_ticks,
            door_interleave_every=door_interleave_every,
            seat_count=seat_count,
            callbacks_per_seat=callbacks_per_seat,
        )
    )


def test_surface_one_event_loop_and_no_os_confinement_claim() -> None:
    assert SEAT_CONCURRENCY_SURFACE == "qmn.host.seat_concurrency"
    assert SEAT_CONCURRENCY_OWNED_BY == "26.19"
    model = supervision_process_model()
    assert model["event_loop_count"] == EVENT_LOOP_COUNT == 1
    assert model["domain_background_threads_allowed"] is DOMAIN_BACKGROUND_THREADS_ALLOWED
    assert DOMAIN_BACKGROUND_THREADS_ALLOWED is False
    assert V1_HARDENED_OS_CONFINEMENT is False
    assert GAP_0054_STATUS == "deferred"
    assert scan_os_confinement_apis(_HOST_SRC) == ()


def test_injected_bounds_refuse_invented_deadline_memory_and_os_cap() -> None:
    none_deadline = SeatInjectedBounds.try_create(
        accumulator_bound=2,
        general_capacity=1,
        protective_reserve_capacity=1,
        local_queue_bound_ns=1,
        evidence_channel_budget=1,
        callback_deadline=None,
        memory_ceiling_bytes=10_000,
    )
    assert is_refusal(none_deadline)
    invented_ns = SeatInjectedBounds.try_create(
        accumulator_bound=2,
        general_capacity=1,
        protective_reserve_capacity=1,
        local_queue_bound_ns=1,
        evidence_channel_budget=1,
        callback_deadline=15,
        memory_ceiling_bytes=10_000,
    )
    assert is_refusal(invented_ns)
    none_memory = SeatInjectedBounds.try_create(
        accumulator_bound=2,
        general_capacity=1,
        protective_reserve_capacity=1,
        local_queue_bound_ns=1,
        evidence_channel_budget=1,
        callback_deadline=_duration(1_000_000),
        memory_ceiling_bytes=None,
    )
    assert is_refusal(none_memory)
    too_few = _refusal(SeatConcurrencyLoad.try_create(seed=1, seat_count=2))
    assert too_few.category is RefusalCategory.INVALID_INPUT
    claimed = _refusal(
        prove_seat_concurrency(
            load=_load(),
            bounds=_bounds(),
            close_gap_0054=True,
        )
    )
    assert claimed.category is RefusalCategory.POLICY_REJECTION
    assert claimed.context["gap_id"] == GAP_0054_ID
    cap = _refusal(
        prove_seat_concurrency(
            load=_load(),
            bounds=_bounds(),
            os_hard_cap_bytes=8_388_608,
        )
    )
    assert cap.category is RefusalCategory.POLICY_REJECTION


def test_proof_records_load_seed_deployment_lifecycle_wall_rss() -> None:
    report = _ok(
        prove_seat_concurrency(
            load=_load(seed=42),
            bounds=_bounds(),
            lifecycle=BenchLifecycle.PRE_DOORS_OPEN,
            deployment_id="ci-seat-concurrency",
        )
    )
    assert report.surface == SEAT_CONCURRENCY_SURFACE
    assert report.load.seed == 42
    assert report.provenance.deployment_id == "ci-seat-concurrency"
    assert report.provenance.lifecycle is BenchLifecycle.PRE_DOORS_OPEN
    assert report.provenance.os_name
    assert "|" in report.provenance.platform_tuple
    assert report.wall_time_ns >= 0
    assert report.peak_rss_bytes >= 0
    mapping = report.as_mapping()
    load_map = cast("Mapping[str, object]", mapping["load"])
    prov_map = cast("Mapping[str, object]", mapping["provenance"])
    assert load_map["seed"] == 42
    assert load_map["seat_count"] == 3
    assert prov_map["lifecycle"] == "pre-doors-open"
    assert mapping["os_level_confinement"] is False
    assert mapping["gap_0054"] == GAP_0054_ID
    assert mapping["gap_0054_closed"] is False
    assert mapping["v1_hardened_os_confinement"] is False


def test_one_loop_bounded_inflight_backpressure_doors_seats_no_silent_loss() -> None:
    report = _ok(
        prove_seat_concurrency(
            load=_load(),
            bounds=_bounds(accumulator_bound=2, general_capacity=1, evidence_channel_budget=3),
            lifecycle=BenchLifecycle.STAND_DOWN_ALIVE,
            deployment_id="proof-seats",
        )
    )
    assert report.event_loop_count == 1
    assert report.domain_background_threads_allowed is False
    assert report.async_allowed_surfaces == ASYNC_ALLOWED_SURFACES
    assert report.max_overlapping_seat_callbacks == 1
    assert report.max_accumulator_depth_observed <= report.bounds.host.accumulator_bound
    assert report.max_in_flight_observed <= (
        report.bounds.host.general_capacity + report.bounds.host.protective_reserve_capacity
    )

    assert report.backpressure_observed is True
    kinds = {crossing.kind for crossing in report.bound_crossings}
    assert BoundCrossingKind.MARKET_DATA_COALESCE in kinds
    assert BoundCrossingKind.PACER_CAPACITY in kinds
    assert BoundCrossingKind.EVIDENCE_BUDGET in kinds
    assert BoundCrossingKind.LOCAL_QUEUE_BOUND in kinds
    assert BoundCrossingKind.ENTRY_SIDE_DEGRADATION in kinds
    assert BoundCrossingKind.SEAT_DEADLINE_QUARANTINE in kinds
    assert BoundCrossingKind.SEAT_MEMORY_QUARANTINE in kinds
    assert report.coalesce_events >= 1
    assert report.typed_refusals >= 1
    assert report.entry_side_degradations >= 1
    assert report.callbacks_attempted >= report.load.seat_count
    assert report.callbacks_quarantined >= 2

    coalesce = next(
        c for c in report.bound_crossings if c.kind == BoundCrossingKind.MARKET_DATA_COALESCE
    )
    assert coalesce.category == "data quality"
    deadline = next(
        c for c in report.bound_crossings if c.kind == BoundCrossingKind.SEAT_DEADLINE_QUARANTINE
    )
    assert deadline.bound_field == "seat_callback_deadline"
    assert deadline.details.get("stream_failure") is False
    assert deadline.details.get("node_restart") is False
    assert deadline.details.get("os_level_confinement") is False
    memory = next(
        c for c in report.bound_crossings if c.kind == BoundCrossingKind.SEAT_MEMORY_QUARANTINE
    )
    assert memory.bound_field == "seat_memory_ceiling"

    assert report.evidence_door_ok >= 1
    assert report.powers_door_ok >= 1
    assert len(report.door_response_samples_ns) >= 2
    assert all(sample >= 0 for sample in report.door_response_samples_ns)
    assert report.timer_ticks_fired >= 1

    assert report.silent_observation_loss is False
    assert report.accounted_observations == report.push_attempts
    assert report.push_attempts >= report.push_accepted


def test_quarantine_isolates_seats_and_preserves_exits_protection() -> None:
    report = _ok(
        prove_seat_concurrency(
            load=_load(seat_count=4, callbacks_per_seat=2),
            bounds=_bounds(protective_reserve_capacity=1),
        )
    )
    for row in report.isolation:
        assert row.stream_failure is False
        assert row.node_restart is False
        assert row.os_level_confinement is False
    healthy = [row for row in report.isolation if row.role == "healthy"]
    deadline = [row for row in report.isolation if row.role == "deadline"]
    memory = [row for row in report.isolation if row.role == "memory"]
    assert len(healthy) >= 2
    assert len(deadline) == 1
    assert len(memory) == 1
    assert all(row.final_state == GovernedSeatState.ADMITTED.value for row in healthy)
    assert deadline[0].final_state == GovernedSeatState.QUARANTINED.value
    assert memory[0].final_state == GovernedSeatState.QUARANTINED.value
    assert report.protection_preserved is True
    assert report.exits_preserved is True
    assert report.protective_command_admitted is True
    assert report.os_level_confinement is False
    assert report.gap_0054_closed is False


def test_configured_governor_budgets_recorded_never_invented() -> None:
    unset = _ok(
        prove_seat_concurrency(
            load=_load(observations_per_stream=4),
            bounds=_bounds(governor_cpu_budget=None, governor_memory_budget=None),
        )
    )
    bound_map = cast("Mapping[str, object]", unset.as_mapping()["bounds"])
    assert bound_map["governor_cpu_budget"] is None
    assert bound_map["governor_memory_budget"] is None
    assert bound_map["governor_cpu_budget_status"] == "unset"
    assert bound_map["governor_memory_budget_status"] == "unset"
    assert "callback_deadline_ns" in bound_map
    assert bound_map["memory_ceiling_bytes"] == 10_000

    configured = _ok(
        prove_seat_concurrency(
            load=_load(observations_per_stream=4),
            bounds=_bounds(governor_cpu_budget=2, governor_memory_budget=64 * 1024 * 1024),
        )
    )
    cfg = cast("Mapping[str, object]", configured.as_mapping()["bounds"])
    assert cfg["governor_cpu_budget"] == 2
    assert cfg["governor_memory_budget"] == 64 * 1024 * 1024
    assert cfg["governor_cpu_budget_status"] == "configured"


def test_deterministic_seed_reproduces_stream_and_seat_accounting() -> None:
    a = _ok(
        prove_seat_concurrency(
            load=_load(seed=7, stream_count=3, observations_per_stream=5, seat_count=3),
            bounds=_bounds(accumulator_bound=2, evidence_channel_budget=5),
        )
    )
    b = _ok(
        prove_seat_concurrency(
            load=_load(seed=7, stream_count=3, observations_per_stream=5, seat_count=3),
            bounds=_bounds(accumulator_bound=2, evidence_channel_budget=5),
        )
    )
    assert a.push_attempts == b.push_attempts
    assert a.push_accepted == b.push_accepted
    assert a.coalesce_events == b.coalesce_events
    assert a.callbacks_attempted == b.callbacks_attempted
    assert a.callbacks_quarantined == b.callbacks_quarantined
    assert a.max_accumulator_depth_observed == b.max_accumulator_depth_observed
    assert [c.kind for c in a.bound_crossings] == [c.kind for c in b.bound_crossings]
    assert [row.final_state for row in a.isolation] == [row.final_state for row in b.isolation]


def test_no_capacity_or_latency_gate_literals_in_seat_concurrency_module() -> None:
    """NFR-17 / FTR-07: seat proof must not mint a latency or capacity pass criterion."""
    banned_names = {
        "MAX_CONCURRENT_SEATS",
        "MAX_IN_FLIGHT",
        "CAPACITY_GATE",
        "THROUGHPUT_TARGET",
        "CALLBACK_DEADLINE_DEFAULT",
        "MEMORY_CEILING_DEFAULT",
        "LATENCY_BUDGET",
        "SEAT_CALLBACK_DEADLINE_NS",
        "GOVERNOR_CPU_DEFAULT",
        "GOVERNOR_MEMORY_DEFAULT",
        "DESIGN_LOAD_ASSERT",
    }
    path = _HOST_SRC / "seat_concurrency.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in banned_names:
                    found.append(target.id)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id in banned_names
        ):
            found.append(node.target.id)
    assert found == []


def test_prove_refuses_non_injected_bounds_object() -> None:
    refused = _refusal(
        prove_seat_concurrency(load=_load(), bounds={"accumulator_bound": 2})  # type: ignore[arg-type]
    )
    assert refused.category is RefusalCategory.INVALID_INPUT
