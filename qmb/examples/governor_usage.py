"""Reference usage — resource governor with min(cpu, memory) and enqueue-on-full.

Executable::

    python qmb/examples/governor_usage.py

Shows the things Story 15.2 / AR-50 / B-5 / FM-6 pin down:

1. Parallelism is bounded by min(qmb_governor_cpu_budget, qmb_governor_memory_budget).
2. A run whose projected peak exceeds remaining budget enqueues (enqueue-on-full)
   or is a typed refusal — never silent oversubscription.
3. When a run finishes, the next queued run is admitted.
4. 12-14 concurrent is a motivating reference, never a validated budget.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.orchestrator import (
    CPU_BUDGET_KEY,
    DECISION_ADMITTED,
    DECISION_QUEUED,
    MEMORY_BUDGET_KEY,
    ON_FULL_REFUSE,
    SANDBOX_CONCURRENT_MOTIVATING_REFERENCE,
    SpawnJob,
    governor_identity,
    spawn_governed,
)
from qmb.runloop import STREAM_SET_KEY, SliceObservation
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, Retryability, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _unwrap(SliceObservation.try_create(stream_id, _instant(ns), True), "observation")


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs("eurusd"),), (_obs("eurusd", _NS + 1),))


def _config(tag: str) -> ResolvedRunConfig:
    stamp = _unwrap(fingerprint({"n": "gov-example", "tag": tag}), "stamp")
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _request(tag: str, peak: int) -> qmb.GovernedRequest:
    return _unwrap(
        qmb.GovernedRequest.try_create(_config(tag).fingerprint, peak),
        "request",
    )


def identity_names_registry_keys_not_a_spine_budget() -> None:
    identity = governor_identity()
    assert identity["cpu_budget_key"] == CPU_BUDGET_KEY == "qmb_governor_cpu_budget"
    assert identity["memory_budget_key"] == MEMORY_BUDGET_KEY == "qmb_governor_memory_budget"
    assert identity["bound"] == "min-cpu-memory"
    assert identity["silent_oversubscription"] is False
    assert identity["sandbox_concurrent_motivating_reference"] == (
        SANDBOX_CONCURRENT_MOTIVATING_REFERENCE
    )
    assert 12 not in identity.values()
    assert 13 not in identity.values()
    assert 14 not in identity.values()


def min_cpu_memory_is_the_tighter_budget() -> None:
    gov = _unwrap(qmb.ResourceGovernor.try_create(cpu_budget=3, memory_budget=100), "gov")
    assert _unwrap(gov.parallelism_bound(40), "bound") == 2
    assert _unwrap(gov.submit(_request("a", 40)), "a").decision == DECISION_ADMITTED
    assert _unwrap(gov.submit(_request("b", 40)), "b").decision == DECISION_ADMITTED
    queued = _unwrap(gov.submit(_request("c", 40)), "c")
    assert queued.decision == DECISION_QUEUED


def enqueue_on_full_then_admit_next() -> None:
    gov = _unwrap(qmb.ResourceGovernor.try_create(cpu_budget=1, memory_budget=100), "gov")
    first = _request("run-1", 10)
    second = _request("run-2", 10)
    assert _unwrap(gov.submit(first), "first").decision == DECISION_ADMITTED
    assert _unwrap(gov.submit(second), "second").decision == DECISION_QUEUED
    newly = _unwrap(gov.release(first.run_id), "release")
    assert newly[0].run_id == second.run_id
    assert newly[0].decision == DECISION_ADMITTED


def too_large_for_the_declared_budget_is_typed_refusal() -> None:
    gov = _unwrap(qmb.ResourceGovernor.try_create(cpu_budget=4, memory_budget=100), "gov")
    refused = gov.submit(_request("huge", 101))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    remaining = _unwrap(
        qmb.ResourceGovernor.try_create(1, 100, on_full=ON_FULL_REFUSE),
        "refuse-full",
    )
    _unwrap(remaining.submit(_request("held", 40)), "held")
    overflow = remaining.submit(_request("wait", 40))
    assert is_refusal(overflow)
    assert overflow.retryability is Retryability.AFTER_CONDITION


def governed_spawn_under_cpu_one(output_root: Path) -> None:
    slices = _slices()
    isolated = _unwrap(
        spawn_governed(
            (
                SpawnJob(config=_config("spawn-a"), slices=slices, projected_peak_memory=10),
                SpawnJob(config=_config("spawn-b"), slices=slices, projected_peak_memory=10),
            ),
            output_root=output_root,
            cpu_budget=1,
            memory_budget=1000,
        ),
        "spawn",
    )
    assert len(isolated) == 2
    assert isolated[0].output_dir != isolated[1].output_dir


def main() -> None:
    assert qmb.CPU_BUDGET_KEY == CPU_BUDGET_KEY
    assert qmb.spawn_governed is spawn_governed
    identity_names_registry_keys_not_a_spine_budget()
    print("min(cpu budget, memory budget)")
    min_cpu_memory_is_the_tighter_budget()
    print("enqueue-on-full")
    enqueue_on_full_then_admit_next()
    print("finish then admit next")
    too_large_for_the_declared_budget_is_typed_refusal()
    print("typed refusal when projected peak exceeds the declared budget")
    with tempfile.TemporaryDirectory(prefix="qmb_gov_", ignore_cleanup_errors=True) as tmp:
        governed_spawn_under_cpu_one(Path(tmp))
    print("12-14 concurrent is a motivating reference, never a validated budget")
    print("governor ok")


if __name__ == "__main__":
    main()
