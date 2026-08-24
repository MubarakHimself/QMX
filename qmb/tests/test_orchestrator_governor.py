"""Story 15.2 — resource governor, min(cpu, memory), enqueue-on-full (AR-50, B-5, FM-6)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, TypeVar

from qmb.config import ResolvedRunConfig
from qmb.doors import api
from qmb.orchestrator import spawn as spawn_mod
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, Retryability, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_ORCH = Path(__file__).resolve().parents[1] / "src" / "qmb" / "orchestrator"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs("eurusd"),), (_obs("eurusd", _NS + 1),))


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "orch-gov", "tag": tag}))
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


def _request(tag: str, peak: int, cpu_cost: int = 1) -> qmb.GovernedRequest:
    return _ok(qmb.GovernedRequest.try_create(_config(tag=tag).fingerprint, peak, cpu_cost))


def test_governor_identity_names_registry_keys_not_spine_values() -> None:
    identity = qmb.governor_identity()
    assert identity["cpu_budget_key"] == qmb.CPU_BUDGET_KEY == "qmb_governor_cpu_budget"
    assert identity["memory_budget_key"] == qmb.MEMORY_BUDGET_KEY == "qmb_governor_memory_budget"
    assert identity["bound"] == "min-cpu-memory"
    assert identity["on_full_default"] == qmb.ON_FULL_ENQUEUE == "enqueue"
    assert identity["silent_oversubscription"] is False
    assert (
        identity["sandbox_concurrent_motivating_reference"]
        == qmb.SANDBOX_CONCURRENT_MOTIVATING_REFERENCE
        == "not-a-validated-budget"
    )
    assert 12 not in identity.values()
    assert 13 not in identity.values()
    assert 14 not in identity.values()
    orch = qmb.orchestrator_identity()
    assert orch["governor"] == "min-cpu-memory"
    assert orch["cpu_budget_key"] == qmb.CPU_BUDGET_KEY
    assert orch["sandbox_concurrent_motivating_reference"] == "not-a-validated-budget"
    assert qmb.__version__ not in orch.values()
    assert api.ResourceGovernor is qmb.ResourceGovernor
    assert api.spawn_governed is qmb.spawn_governed
    assert api.CPU_BUDGET_KEY is qmb.CPU_BUDGET_KEY
    assert api.governor_identity is qmb.governor_identity


def test_twelve_to_fourteen_is_not_a_validated_budget_in_the_governor() -> None:
    source = (_ORCH / "governor.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_ORCH / "governor.py"))
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value in (12, 13, 14)
    ]
    assert literals == []
    missing = qmb.GovernorBudgets.try_create()
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    assert missing.context["field"] == qmb.CPU_BUDGET_KEY
    # An operator may declare 12 on a machine; that is not a spine default.
    declared = _ok(qmb.GovernorBudgets.try_create(cpu_budget=12, memory_budget=12))
    assert declared.cpu_budget == 12
    assert declared.memory_budget == 12
    assert "cpu_budget_key" in declared.fp1_identity()


def test_budgets_are_required_positive_ints_with_no_default() -> None:
    zero = qmb.GovernorBudgets.try_create(cpu_budget=0, memory_budget=8)
    assert is_refusal(zero)
    assert zero.context["field"] == qmb.CPU_BUDGET_KEY
    negative = qmb.GovernorBudgets.try_create(cpu_budget=2, memory_budget=-1)
    assert is_refusal(negative)
    assert negative.context["field"] == qmb.MEMORY_BUDGET_KEY
    as_bool = qmb.GovernorBudgets.try_create(cpu_budget=True, memory_budget=8)
    assert is_refusal(as_bool)
    keyed = _ok(qmb.GovernorBudgets.try_create({qmb.CPU_BUDGET_KEY: 3, qmb.MEMORY_BUDGET_KEY: 90}))
    assert keyed.cpu_budget == 3
    assert keyed.memory_budget == 90
    alias = _ok(qmb.GovernorBudgets.try_create({"cpu_budget": 2, "memory_budget": 40}))
    assert alias.cpu_budget == 2
    already = _ok(qmb.GovernorBudgets.try_create(keyed))
    assert already is keyed
    both = qmb.GovernorBudgets.try_create(keyed, 1)
    assert is_refusal(both)
    assert both.context["field"] == "budgets"
    mapped_both = qmb.GovernorBudgets.try_create(
        {qmb.CPU_BUDGET_KEY: 2, qmb.MEMORY_BUDGET_KEY: 40},
        1,
    )
    assert is_refusal(mapped_both)
    assert mapped_both.context["field"] == "budgets"


def test_parallelism_bound_is_min_of_cpu_slots_and_memory_slots() -> None:
    budgets = _ok(qmb.GovernorBudgets.try_create(cpu_budget=4, memory_budget=100))
    # memory is tighter: min(4, 100//40) = 2
    assert _ok(budgets.parallelism_bound(40)) == 2
    # cpu is tighter: min(4, 100//10) = 4
    assert _ok(budgets.parallelism_bound(10)) == 4
    never = _ok(budgets.parallelism_bound(101))
    assert never == 0
    gov = _ok(qmb.ResourceGovernor.try_create(budgets=budgets))
    assert _ok(gov.parallelism_bound(40, 1)) == 2


def test_admit_until_cpu_full_then_enqueue() -> None:
    gov = _ok(qmb.ResourceGovernor.try_create(cpu_budget=2, memory_budget=1000))
    first = _ok(gov.submit(_request("cpu-a", 10)))
    second = _ok(gov.submit(_request("cpu-b", 10)))
    third = _ok(gov.submit(_request("cpu-c", 10)))
    assert first.decision == qmb.DECISION_ADMITTED
    assert second.decision == qmb.DECISION_ADMITTED
    assert third.decision == qmb.DECISION_QUEUED
    assert gov.running_count == 2
    assert gov.queue_depth == 1
    assert gov.remaining_cpu == 0
    assert third.limiting_factor == "cpu"


def test_admit_until_memory_full_then_enqueue() -> None:
    gov = _ok(qmb.ResourceGovernor.try_create(cpu_budget=8, memory_budget=100))
    first = _ok(gov.submit(_request("mem-a", 60)))
    second = _ok(gov.submit(_request("mem-b", 60)))
    assert first.decision == qmb.DECISION_ADMITTED
    assert second.decision == qmb.DECISION_QUEUED
    assert gov.reserved_memory == 60
    assert gov.remaining_memory == 40
    assert gov.queue_depth == 1
    assert second.limiting_factor == "memory"


def test_min_cpu_memory_is_the_tighter_of_the_two_budgets() -> None:
    gov = _ok(qmb.ResourceGovernor.try_create(cpu_budget=3, memory_budget=100))
    assert _ok(gov.parallelism_bound(40)) == 2
    assert _ok(gov.submit(_request("min-a", 40))).decision == qmb.DECISION_ADMITTED
    assert _ok(gov.submit(_request("min-b", 40))).decision == qmb.DECISION_ADMITTED
    third = _ok(gov.submit(_request("min-c", 40)))
    assert third.decision == qmb.DECISION_QUEUED
    assert gov.running_count == 2
    assert gov.remaining_cpu == 1  # cpu would allow another; memory does not
    assert gov.remaining_memory == 20


def test_projected_peak_exceeding_total_budget_is_typed_refusal_never_queued() -> None:
    gov = _ok(qmb.ResourceGovernor.try_create(cpu_budget=4, memory_budget=100))
    refused = gov.submit(_request("too-big", 101))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.retryability is Retryability.NO
    assert refused.context["field"] == "projected_peak_memory"
    assert refused.context["memory_budget_key"] == qmb.MEMORY_BUDGET_KEY
    assert gov.running_count == 0
    assert gov.queue_depth == 0
    cpu = gov.submit(_request("heavy-cpu", 10, cpu_cost=5))
    assert is_refusal(cpu)
    assert cpu.context["field"] == "cpu_cost"


def test_on_full_refuse_is_after_condition_not_silent_oversubscription() -> None:
    gov = _ok(
        qmb.ResourceGovernor.try_create(
            cpu_budget=1,
            memory_budget=100,
            on_full=qmb.ON_FULL_REFUSE,
        )
    )
    assert _ok(gov.submit(_request("hold", 40))).decision == qmb.DECISION_ADMITTED
    refused = gov.submit(_request("overflow", 40))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.retryability is Retryability.AFTER_CONDITION
    assert refused.after_condition_descriptor is not None
    assert "finishes" in refused.after_condition_descriptor
    assert refused.context["on_full"] == qmb.ON_FULL_REFUSE
    assert gov.queue_depth == 0
    bad = qmb.ResourceGovernor.try_create(cpu_budget=1, memory_budget=8, on_full="oversub")
    assert is_refusal(bad)
    assert bad.context["field"] == "on_full"


def test_finish_then_admit_next_queued_run_fifo() -> None:
    gov = _ok(qmb.ResourceGovernor.try_create(cpu_budget=1, memory_budget=100))
    a = _request("fifo-a", 10)
    b = _request("fifo-b", 10)
    c = _request("fifo-c", 10)
    assert _ok(gov.submit(a)).decision == qmb.DECISION_ADMITTED
    assert _ok(gov.submit(b)).decision == qmb.DECISION_QUEUED
    assert _ok(gov.submit(c)).decision == qmb.DECISION_QUEUED
    newly = _ok(gov.release(a.run_id))
    assert len(newly) == 1
    assert newly[0].decision == qmb.DECISION_ADMITTED
    assert newly[0].run_id == b.run_id
    assert gov.queued[0].run_id == c.run_id
    again = _ok(gov.release(b.run_id))
    assert again[0].run_id == c.run_id
    assert gov.queue_depth == 0
    assert _ok(gov.release(c.run_id)) == ()


def test_a_run_that_fits_remaining_is_admitted_while_a_larger_job_stays_queued() -> None:
    gov = _ok(qmb.ResourceGovernor.try_create(cpu_budget=2, memory_budget=100))
    a = _request("head-a", 70)
    b = _request("head-b", 50)
    c = _request("head-c", 20)
    assert _ok(gov.submit(a)).decision == qmb.DECISION_ADMITTED
    assert _ok(gov.submit(b)).decision == qmb.DECISION_QUEUED
    # C fits remaining min(cpu, memory); B does not, and stays the next queued run.
    assert _ok(gov.submit(c)).decision == qmb.DECISION_ADMITTED
    assert [item.run_id for item in gov.running] == [a.run_id, c.run_id]
    assert [item.run_id for item in gov.queued] == [b.run_id]
    newly = _ok(gov.release(a.run_id))
    assert [item.run_id for item in newly] == [b.run_id]
    assert gov.queue_depth == 0


def test_duplicate_and_unknown_release_are_typed_refusals() -> None:
    gov = _ok(qmb.ResourceGovernor.try_create(cpu_budget=2, memory_budget=100))
    item = _request("dup", 10)
    assert is_ok(gov.submit(item))
    dup = gov.submit(item)
    assert is_refusal(dup)
    assert dup.category is RefusalCategory.POLICY_REJECTION
    assert dup.context["field"] == "run_id"
    missing = gov.release(_config(tag="absent").fingerprint)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    bad = gov.release(1)
    assert is_refusal(bad)
    assert bad.context["field"] == "run_id"
    not_request = gov.submit("nope")
    assert is_refusal(not_request)
    mapped = _ok(
        gov.submit(
            {
                "run_id": _config(tag="map").fingerprint,
                "projected_peak_memory": 10,
            }
        )
    )
    assert mapped.decision == qmb.DECISION_ADMITTED


def test_two_governor_instances_do_not_share_state() -> None:
    left = _ok(qmb.ResourceGovernor.try_create(cpu_budget=1, memory_budget=50))
    right = _ok(qmb.ResourceGovernor.try_create(cpu_budget=1, memory_budget=50))
    _ok(left.submit(_request("iso-a", 10)))
    assert left.running_count == 1
    assert right.running_count == 0
    _ok(right.submit(_request("iso-a", 10)))
    assert right.running_count == 1


def test_request_and_governor_construction_refusals() -> None:
    bad_peak = qmb.GovernedRequest.try_create(_config(tag="p").fingerprint, 0)
    assert is_refusal(bad_peak)
    assert bad_peak.context["field"] == "projected_peak_memory"
    both = qmb.ResourceGovernor.try_create(
        cpu_budget=1,
        memory_budget=8,
        budgets=_ok(qmb.GovernorBudgets.try_create(1, 8)),
    )
    assert is_refusal(both)
    assert both.context["field"] == "budgets"
    identity = _ok(qmb.ResourceGovernor.try_create(2, 40)).fp1_identity()
    assert identity["silent_oversubscription"] is False
    assert qmb.__version__ not in identity.values()


def test_spawn_governed_cpu_one_finishes_before_the_next_starts(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    first = _config(tag="gov-spawn-a")
    second = _config(tag="gov-spawn-b")
    slices = _slices()
    saw_first_result: list[bool] = []
    real_start = spawn_mod.start_run

    def wrapped(**kwargs: Any) -> Any:
        config = kwargs["config"]
        if saw_first_result or first.fingerprint != config.fingerprint:
            named = _ok(qmb.run_directory_name(first.fingerprint))
            saw_first_result.append((tmp_path / named / qmb.RESULT_NAME).is_file())
        return real_start(**kwargs)

    monkeypatch.setattr(spawn_mod, "start_run", wrapped)
    isolated = _ok(
        qmb.spawn_governed(
            (
                qmb.SpawnJob(config=first, slices=slices, projected_peak_memory=10),
                qmb.SpawnJob(config=second, slices=slices, projected_peak_memory=10),
            ),
            output_root=tmp_path,
            cpu_budget=1,
            memory_budget=1000,
        )
    )
    assert len(isolated) == 2
    assert isolated[0].run_id == first.fingerprint
    assert isolated[1].run_id == second.fingerprint
    assert True in saw_first_result
    in_first = _ok(run(slices=slices, config=first, handler=SilentSliceHandler()))
    in_second = _ok(run(slices=slices, config=second, handler=SilentSliceHandler()))
    assert isolated[0].outcome_identity == in_first.fp1_identity()
    assert isolated[1].outcome_identity == in_second.fp1_identity()


def test_spawn_governed_memory_cap_enqueues_until_finish(tmp_path: Path, monkeypatch: Any) -> None:
    first = _config(tag="gov-mem-a")
    second = _config(tag="gov-mem-b")
    slices = _slices()
    started: list[str] = []
    real_start = spawn_mod.start_run

    def wrapped(**kwargs: Any) -> Any:
        config = kwargs["config"]
        started.append(config.fingerprint.value)
        if len(started) == 2:
            named = _ok(qmb.run_directory_name(first.fingerprint))
            assert (tmp_path / named / qmb.RESULT_NAME).is_file()
        return real_start(**kwargs)

    monkeypatch.setattr(spawn_mod, "start_run", wrapped)
    isolated = _ok(
        qmb.spawn_governed(
            (
                {"config": first, "slices": slices, "projected_peak_memory": 80},
                {"config": second, "slices": slices, "projected_peak_memory": 80},
            ),
            output_root=tmp_path,
            cpu_budget=8,
            memory_budget=100,
        )
    )
    assert len(isolated) == 2
    assert started[0] == first.fingerprint.value
    assert started[1] == second.fingerprint.value


def test_spawn_governed_never_fit_does_not_spawn(tmp_path: Path) -> None:
    config = _config(tag="gov-never")
    refused = qmb.spawn_governed(
        (qmb.SpawnJob(config=config, slices=_slices(), projected_peak_memory=200),),
        output_root=tmp_path,
        cpu_budget=4,
        memory_budget=100,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "projected_peak_memory"
    assert list(tmp_path.iterdir()) == []


def test_spawn_governed_missing_peak_and_empty_jobs_are_invalid(tmp_path: Path) -> None:
    refused = qmb.spawn_governed(
        (qmb.SpawnJob(config=_config(tag="no-peak"), slices=_slices()),),
        output_root=tmp_path,
        cpu_budget=2,
        memory_budget=100,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "projected_peak_memory"
    empty = qmb.spawn_governed((), output_root=tmp_path, cpu_budget=2, memory_budget=100)
    assert is_refusal(empty)
    assert empty.context["field"] == "jobs"
    missing_budget = qmb.spawn_governed(
        (
            qmb.SpawnJob(
                config=_config(tag="no-budget"),
                slices=_slices(),
                projected_peak_memory=10,
            ),
        ),
        output_root=tmp_path,
    )
    assert is_refusal(missing_budget)
    assert missing_budget.context["field"] == qmb.CPU_BUDGET_KEY


def test_spawn_governed_default_peak_and_budgets_object(tmp_path: Path) -> None:
    first = _config(tag="gov-default-a")
    second = _config(tag="gov-default-b")
    slices = _slices()
    budgets = _ok(qmb.GovernorBudgets.try_create(cpu_budget=2, memory_budget=100))
    isolated = _ok(
        qmb.spawn_governed(
            (
                qmb.SpawnJob(config=first, slices=slices),
                qmb.SpawnJob(config=second, slices=slices),
            ),
            output_root=tmp_path,
            budgets=budgets,
            projected_peak_memory=10,
        )
    )
    assert len(isolated) == 2
    assert isolated[0].pid != isolated[1].pid


def test_spawn_governed_on_full_refuse_does_not_start_the_overflow(tmp_path: Path) -> None:
    first = _config(tag="gov-refuse-a")
    second = _config(tag="gov-refuse-b")
    refused = qmb.spawn_governed(
        (
            qmb.SpawnJob(config=first, slices=_slices(), projected_peak_memory=60),
            qmb.SpawnJob(config=second, slices=_slices(), projected_peak_memory=60),
        ),
        output_root=tmp_path,
        cpu_budget=4,
        memory_budget=100,
        on_full=qmb.ON_FULL_REFUSE,
    )
    assert is_refusal(refused)
    assert refused.retryability is Retryability.AFTER_CONDITION
    assert list(tmp_path.iterdir()) == []


def test_spawn_governed_duplicate_run_ids_refuse_before_spawn(tmp_path: Path) -> None:
    config = _config(tag="gov-dup")
    slices = _slices()
    refused = qmb.spawn_governed(
        (
            qmb.SpawnJob(config=config, slices=slices, projected_peak_memory=10),
            qmb.SpawnJob(config=config, slices=slices, projected_peak_memory=10),
        ),
        output_root=tmp_path,
        cpu_budget=2,
        memory_budget=100,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert list(tmp_path.iterdir()) == []
