"""Story 25.16 — prove host concurrency and backpressure without inventing caps."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core import RefusalCategory, Result, is_ok, is_refusal
from qmn.bench import BenchLifecycle
from qmn.host import (
    ASYNC_ALLOWED_SURFACES,
    CONCURRENCY_SURFACE,
    DOMAIN_BACKGROUND_THREADS_ALLOWED,
    EVENT_LOOP_COUNT,
    SEAT_CONCURRENCY_OWNED_BY,
    BoundCrossingKind,
    ConcurrencyLoad,
    InjectedBounds,
    prove_host_concurrency,
    supervision_process_model,
)

T = TypeVar("T")

_HOST_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "host"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _bounds(
    *,
    accumulator_bound: int = 2,
    general_capacity: int = 1,
    protective_reserve_capacity: int = 0,
    local_queue_bound_ns: int = 1_000_000_000,
    evidence_channel_budget: int = 4,
    governor_cpu_budget: int | None = None,
    governor_memory_budget: int | None = None,
) -> InjectedBounds:
    return _ok(
        InjectedBounds.try_create(
            accumulator_bound=accumulator_bound,
            general_capacity=general_capacity,
            protective_reserve_capacity=protective_reserve_capacity,
            local_queue_bound_ns=local_queue_bound_ns,
            evidence_channel_budget=evidence_channel_budget,
            governor_cpu_budget=governor_cpu_budget,
            governor_memory_budget=governor_memory_budget,
        )
    )


def _load(
    *,
    seed: int = 25_16,
    stream_count: int = 2,
    observations_per_stream: int = 6,
    timer_ticks: int = 3,
    door_interleave_every: int = 2,
) -> ConcurrencyLoad:
    return _ok(
        ConcurrencyLoad.try_create(
            seed=seed,
            stream_count=stream_count,
            observations_per_stream=observations_per_stream,
            timer_ticks=timer_ticks,
            door_interleave_every=door_interleave_every,
        )
    )


def test_surface_and_seat_ownership() -> None:
    assert CONCURRENCY_SURFACE == "qmn.host.concurrency"
    assert SEAT_CONCURRENCY_OWNED_BY == "26.19"
    model = supervision_process_model()
    assert model["event_loop_count"] == EVENT_LOOP_COUNT == 1
    assert model["domain_background_threads_allowed"] is DOMAIN_BACKGROUND_THREADS_ALLOWED
    assert DOMAIN_BACKGROUND_THREADS_ALLOWED is False
    assert model["async_allowed_surfaces"] == ASYNC_ALLOWED_SURFACES


def test_injected_bounds_refuse_invented_non_positive() -> None:
    refused = _refusal(
        InjectedBounds.try_create(
            accumulator_bound=0,
            general_capacity=1,
            protective_reserve_capacity=0,
            local_queue_bound_ns=1,
            evidence_channel_budget=1,
        )
    )
    assert refused.category is RefusalCategory.INVALID_INPUT
    refused_gov = _refusal(
        InjectedBounds.try_create(
            accumulator_bound=2,
            general_capacity=1,
            protective_reserve_capacity=0,
            local_queue_bound_ns=1,
            evidence_channel_budget=1,
            governor_cpu_budget=0,
        )
    )
    assert refused_gov.category is RefusalCategory.INVALID_INPUT


def test_proof_records_load_seed_deployment_lifecycle_wall_rss() -> None:
    report = _ok(
        prove_host_concurrency(
            load=_load(seed=42),
            bounds=_bounds(),
            lifecycle=BenchLifecycle.PRE_DOORS_OPEN,
            deployment_id="ci-concurrency",
        )
    )
    assert report.surface == CONCURRENCY_SURFACE
    assert report.load.seed == 42
    assert report.provenance.deployment_id == "ci-concurrency"
    assert report.provenance.lifecycle is BenchLifecycle.PRE_DOORS_OPEN
    assert report.provenance.os_name
    assert "|" in report.provenance.platform_tuple
    assert report.wall_time_ns >= 0
    assert report.peak_rss_bytes >= 0
    mapping = report.as_mapping()
    load_map = cast("Mapping[str, object]", mapping["load"])
    prov_map = cast("Mapping[str, object]", mapping["provenance"])
    assert load_map["seed"] == 42
    assert prov_map["lifecycle"] == "pre-doors-open"
    assert mapping["seat_concurrency_owned_by"] == "26.19"


def test_one_event_loop_bounded_inflight_backpressure_doors_no_silent_loss() -> None:
    report = _ok(
        prove_host_concurrency(
            load=_load(),
            bounds=_bounds(accumulator_bound=2, general_capacity=1, evidence_channel_budget=3),
            lifecycle=BenchLifecycle.STAND_DOWN_ALIVE,
            deployment_id="proof-core",
        )
    )
    # One event loop; domain work never on undeclared background threads.
    assert report.event_loop_count == 1
    assert report.domain_background_threads_allowed is False
    assert report.async_allowed_surfaces == ("venue_edge", "doors")

    # Bounded in-flight / depth — measured against injected config, never invented.
    assert report.max_accumulator_depth_observed <= report.bounds.accumulator_bound
    assert report.max_in_flight_observed <= (
        report.bounds.general_capacity + report.bounds.protective_reserve_capacity
    )

    # Explicit enqueue/backpressure and designed bound crossings (not log-only).
    assert report.backpressure_observed is True
    kinds = {crossing.kind for crossing in report.bound_crossings}
    assert BoundCrossingKind.MARKET_DATA_COALESCE in kinds
    assert BoundCrossingKind.PACER_CAPACITY in kinds
    assert BoundCrossingKind.EVIDENCE_BUDGET in kinds
    assert BoundCrossingKind.ENTRY_SIDE_DEGRADATION in kinds
    assert report.coalesce_events >= 1
    assert report.typed_refusals >= 1
    assert report.entry_side_degradations >= 1

    coalesce = next(
        c for c in report.bound_crossings if c.kind == BoundCrossingKind.MARKET_DATA_COALESCE
    )
    assert coalesce.category == "data quality"
    assert coalesce.bound_field == "accumulator_bound"
    pacer = next(c for c in report.bound_crossings if c.kind == BoundCrossingKind.PACER_CAPACITY)
    assert pacer.category == RefusalCategory.POLICY_REJECTION.value
    evidence = next(
        c for c in report.bound_crossings if c.kind == BoundCrossingKind.EVIDENCE_BUDGET
    )
    assert evidence.bound_field == "evidence_channel_budget"

    # Evidence / powers doors stayed responsive under load.
    assert report.evidence_door_ok >= 1
    assert report.powers_door_ok >= 1
    assert len(report.door_response_samples_ns) >= 2
    assert all(sample >= 0 for sample in report.door_response_samples_ns)
    assert report.timer_ticks_fired >= 1

    # No silent observation loss — every push is accepted or typed-refused.
    assert report.silent_observation_loss is False
    assert report.accounted_observations == report.push_attempts
    assert report.push_attempts >= report.push_accepted


def test_configured_governor_budgets_recorded_never_invented() -> None:
    unset = _ok(
        prove_host_concurrency(
            load=_load(observations_per_stream=4),
            bounds=_bounds(governor_cpu_budget=None, governor_memory_budget=None),
        )
    )
    bound_map = cast("Mapping[str, object]", unset.as_mapping()["bounds"])
    assert bound_map["governor_cpu_budget"] is None
    assert bound_map["governor_memory_budget"] is None
    assert bound_map["governor_cpu_budget_status"] == "unset"
    assert bound_map["governor_memory_budget_status"] == "unset"

    configured = _ok(
        prove_host_concurrency(
            load=_load(observations_per_stream=4),
            bounds=_bounds(governor_cpu_budget=2, governor_memory_budget=64 * 1024 * 1024),
        )
    )
    cfg = cast("Mapping[str, object]", configured.as_mapping()["bounds"])
    assert cfg["governor_cpu_budget"] == 2
    assert cfg["governor_memory_budget"] == 64 * 1024 * 1024
    assert cfg["governor_cpu_budget_status"] == "configured"
    assert cfg["governor_memory_budget_status"] == "configured"


def test_deterministic_seed_reproduces_stream_accounting() -> None:
    a = _ok(
        prove_host_concurrency(
            load=_load(seed=7, stream_count=3, observations_per_stream=5),
            bounds=_bounds(accumulator_bound=2, evidence_channel_budget=5),
        )
    )
    b = _ok(
        prove_host_concurrency(
            load=_load(seed=7, stream_count=3, observations_per_stream=5),
            bounds=_bounds(accumulator_bound=2, evidence_channel_budget=5),
        )
    )
    assert a.push_attempts == b.push_attempts
    assert a.push_accepted == b.push_accepted
    assert a.coalesce_events == b.coalesce_events
    assert a.max_accumulator_depth_observed == b.max_accumulator_depth_observed
    assert [c.kind for c in a.bound_crossings] == [c.kind for c in b.bound_crossings]


def test_no_capacity_gate_literals_in_concurrency_module() -> None:
    """NFR-17 / FTR-07: concurrency proof must not mint a capacity pass criterion."""
    banned_names = {
        "MAX_CONCURRENT_STREAMS",
        "MAX_IN_FLIGHT",
        "CAPACITY_GATE",
        "THROUGHPUT_TARGET",
        "DESIGN_LOAD_ASSERT",
        "GOVERNOR_CPU_DEFAULT",
        "GOVERNOR_MEMORY_DEFAULT",
        "ACCUMULATOR_BOUND_DEFAULT",
    }
    path = _HOST_SRC / "concurrency.py"
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
        prove_host_concurrency(load=_load(), bounds={"accumulator_bound": 2})  # type: ignore[arg-type]
    )
    assert refused.category is RefusalCategory.INVALID_INPUT
