"""Story 25.15 — hot-path benchmark harness without invented budgets."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core import RefusalCategory, Result, is_ok, is_refusal
from qmn.bench import (
    BENCH_SURFACE,
    BUDGET_SLOT_NAMES,
    DESIGN_BOT_CONCURRENCY_REFERENCE,
    HOT_PATH_RUNGS,
    MODULE,
    SEAT_LADDER,
    VARIANCE_METHOD,
    WATCHED_LATENCY_TARGET_IS_GATE,
    BaselineEligibility,
    BenchLifecycle,
    BudgetSlot,
    BudgetStatus,
    HotPathRung,
    baseline_eligible,
    budget_slots_unset,
    gate_may_enforce,
    peak_rss_bytes,
    run,
)
from qmn.observability import LATENCY_RUNGS

T = TypeVar("T")

_BENCH_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "bench"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def test_surface_and_ladder_match_tn23() -> None:
    assert BENCH_SURFACE == "qmn.bench"
    assert MODULE == "qmn.bench"
    assert SEAT_LADDER == (10, 40, 100, 200)
    assert DESIGN_BOT_CONCURRENCY_REFERENCE == 40
    assert 40 in SEAT_LADDER
    assert HOT_PATH_RUNGS == LATENCY_RUNGS
    assert tuple(member.value for member in HotPathRung) == HOT_PATH_RUNGS
    assert WATCHED_LATENCY_TARGET_IS_GATE is False
    assert VARIANCE_METHOD == "multiple-of-measured-run-to-run-variance"


def test_unset_budgets_are_honest_and_unenforced() -> None:
    slots = budget_slots_unset()
    names = {slot.name for slot in slots}
    assert names == set(BUDGET_SLOT_NAMES)
    for slot in slots:
        assert slot.status is BudgetStatus.UNSET
        assert slot.value is None
        assert slot.gate_enforced is False


def test_baseline_eligible_only_pre_doors_or_stand_down() -> None:
    assert baseline_eligible(BenchLifecycle.PRE_DOORS_OPEN) is True
    assert baseline_eligible(BenchLifecycle.STAND_DOWN_ALIVE) is True
    assert baseline_eligible(BenchLifecycle.RUNNING_SLICE_DRIVING) is False
    assert baseline_eligible(BenchLifecycle.DRAINING) is False
    assert baseline_eligible(BenchLifecycle.STOPPED) is False


def test_peak_rss_bytes_is_non_negative() -> None:
    assert peak_rss_bytes() >= 0


def test_harness_records_wall_rss_rungs_queue_and_provenance() -> None:
    report = _ok(run(lifecycle=BenchLifecycle.PRE_DOORS_OPEN, deployment_id="ci-test"))
    assert report.seat_ladder == SEAT_LADDER
    assert report.design_bot_concurrency_reference == DESIGN_BOT_CONCURRENCY_REFERENCE
    assert report.hot_path_rungs == HOT_PATH_RUNGS
    assert report.watched_latency_target_is_gate is False
    assert report.story_28_7_owns_vps_baselines is True
    assert report.baseline_eligibility is BaselineEligibility.BUDGETS_UNSET

    prov = report.provenance
    assert prov.lifecycle is BenchLifecycle.PRE_DOORS_OPEN
    assert prov.deployment_id == "ci-test"
    assert prov.os_name
    assert prov.cpu_class
    assert prov.machine
    assert "|" in prov.platform_tuple

    assert [mark.seat_count for mark in report.marks] == list(SEAT_LADDER)
    for mark in report.marks:
        assert mark.wall_time_ns >= 0
        assert mark.peak_rss_bytes >= 0
        assert [sample.rung.value for sample in mark.rungs] == list(HOT_PATH_RUNGS)
        for sample in mark.rungs:
            assert sample.wall_time_ns >= 0
            assert sample.peak_rss_bytes >= 0
        assert mark.queue.enqueue_count >= 1
        assert mark.conformance_double_kind == "conformance"
        assert mark.slices_driven >= 0

    assert all(slot.status is BudgetStatus.UNSET for slot in report.budgets)
    assert all(slot.value is None for slot in report.budgets)
    assert all(slot.gate_enforced is False for slot in report.budgets)
    assert report.variance_method.variance_multiple is None
    assert report.variance_method.regression_threshold is None
    assert report.variance_method.status is BudgetStatus.UNSET

    mapping = report.as_mapping()
    assert mapping["baseline_eligibility"] == "budgets-unset"
    assert mapping["watched_latency_target_is_gate"] is False
    variance = cast("Mapping[str, object]", mapping["variance_method"])
    assert variance["variance_multiple"] is None


def test_gate_may_enforce_refuses_silent_enforcement() -> None:
    report = _ok(run(lifecycle=BenchLifecycle.PRE_DOORS_OPEN, ladder=(10,)))
    assert _ok(gate_may_enforce(report)) is False

    tainted = _ok(run(lifecycle=BenchLifecycle.RUNNING_SLICE_DRIVING, ladder=(10,)))
    assert tainted.baseline_eligibility is BaselineEligibility.CONTAMINATED_SLICE_DRIVING
    refused = _refusal(gate_may_enforce(tainted))
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_run_refuses_invented_unset_budget_values() -> None:
    invented = BudgetSlot(
        name="max_slice_latency",
        status=BudgetStatus.UNSET,
        value=50_000_000,
        unit="ns",
        gate_enforced=False,
    )
    refused = _refusal(run(ladder=(10,), budgets=(invented,)))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert (
        "invented" in str(refused.context["reason"]).lower()
        or "unset" in str(refused.context["reason"]).lower()
    )


def test_run_refuses_silently_enforced_unset_budget() -> None:
    enforced = BudgetSlot(
        name="peak_rss_budget",
        status=BudgetStatus.UNSET,
        value=None,
        unit="bytes",
        gate_enforced=True,
    )
    refused = _refusal(run(ladder=(10,), budgets=(enforced,)))
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_no_numeric_latency_gate_literals_in_bench_package() -> None:
    """FTR-07: the harness package must not mint a release-gate latency constant."""
    banned_names = {
        "MAX_SLICE_LATENCY",
        "LATENCY_BUDGET",
        "LATENCY_GATE",
        "RSS_BUDGET",
        "REGRESSION_THRESHOLD",
        "VARIANCE_MULTIPLE_DEFAULT",
        "WATCHED_LATENCY_MS",
        "FIFTY_MS",
        "TARGET_LATENCY_NS",
    }
    found: list[str] = []
    for path in sorted(_BENCH_SRC.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in banned_names:
                        found.append(f"{path.name}:{target.id}")
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id in banned_names
            ):
                found.append(f"{path.name}:{node.target.id}")
    assert found == []


def test_harness_stand_down_lifecycle_is_eligible_shape() -> None:
    report = _ok(
        run(lifecycle=BenchLifecycle.STAND_DOWN_ALIVE, ladder=(10, 40), deployment_id="standdown")
    )
    assert report.provenance.lifecycle is BenchLifecycle.STAND_DOWN_ALIVE
    assert report.baseline_eligibility is BaselineEligibility.BUDGETS_UNSET
    assert [mark.seat_count for mark in report.marks] == [10, 40]
