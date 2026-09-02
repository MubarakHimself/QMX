"""Story 28.7 — first-hours VPS and storage baselines (test-status harness)."""

from __future__ import annotations

import math
import statistics
from pathlib import Path
from typing import TypeVar

from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmn.bench import (
    CI_ENFORCES_LATENCY_GATE,
    E9_F04_CLOSED,
    FIRST_HOURS_CLASS,
    FIRST_HOURS_SURFACE,
    PROCURES_VPS,
    REQUIRES_REAL_VPS,
    SEAT_LADDER,
    SOAK_LOCAL_PROCUREMENT_SKIPPED,
    STORAGE_LINE_ITEMS,
    WATCHED_LATENCY_TARGET,
    WATCHED_LATENCY_TARGET_IS_GATE,
    BaselineEligibility,
    BenchLifecycle,
    BudgetStatus,
    CapacityBand,
    FirstHoursInputs,
    HotPathRung,
    derive_regression_thresholds,
    evaluate_storage_capacity,
    gate_may_enforce,
    materialize_representative_day,
    measure_storage_trees,
    record_first_hours_baselines,
    refuse_ci_latency_gate,
    refuse_drop_observability,
    refuse_invented_latency_budget,
    refuse_procure_vps,
    refuse_watched_target_as_gate,
    refuse_weaken_thresholds,
    run,
)
from qmn.observability.failures_gate import DESIGNED_TYPED_FAILURE_IDS

T = TypeVar("T")

_MULTIPLE = 3
_HEADROOM = 1_000
_BUDGET: dict[str, int] = {
    "journal": 8_192,
    "log": 8_192,
    "metrics": 8_192,
    "backup": 8_192,
    "hot_room": 8_192,
    "observability": 8_192,
    "commit_trees": 8_192,
    "protection_intent_reserve": 8_192,
}
_TREES: dict[str, int] = dict.fromkeys(STORAGE_LINE_ITEMS, 256)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _inputs(**overrides: object) -> FirstHoursInputs:
    kwargs: dict[str, object] = {
        "variance_multiple": _MULTIPLE,
        "disk_headroom_min": _HEADROOM,
        "vps_disk_budget": dict(_BUDGET),
        "lifecycle": BenchLifecycle.PRE_DOORS_OPEN,
        "ladder": (10,),
        "repeats": 2,
        "deployment_id": "ci-28-7",
        "injected_tree_bytes": dict(_TREES),
        "injected_commit_tree_depth": 3,
        "free_bytes": 4_000,
    }
    kwargs.update(overrides)
    return FirstHoursInputs(**kwargs)  # type: ignore[arg-type]


def test_surface_markers_pin_ftr07_and_skip_real_vps() -> None:
    assert FIRST_HOURS_SURFACE == "qmn.bench.baselines"
    assert FIRST_HOURS_CLASS == "first-hours-vps-storage-baselines"
    assert REQUIRES_REAL_VPS is False
    assert PROCURES_VPS is False
    assert SOAK_LOCAL_PROCUREMENT_SKIPPED is True
    assert CI_ENFORCES_LATENCY_GATE is False
    assert E9_F04_CLOSED is True
    assert WATCHED_LATENCY_TARGET_IS_GATE is False
    assert WATCHED_LATENCY_TARGET["approx_ms"] == 50
    assert WATCHED_LATENCY_TARGET["is_gate"] is False
    assert WATCHED_LATENCY_TARGET["used_as_regression_threshold"] is False
    assert SEAT_LADDER == (10, 40, 100, 200)
    assert STORAGE_LINE_ITEMS[-1] == "protection_intent_reserve"
    assert "observability" in STORAGE_LINE_ITEMS


def test_full_ladder_records_wall_rss_rungs_queue_and_variance_thresholds(
    tmp_path: Path,
) -> None:
    root = _ok(
        materialize_representative_day(
            tmp_path / "day",
            sizes=_TREES,
            commit_trees=3,
        )
    )
    report = _ok(
        record_first_hours_baselines(
            _inputs(
                ladder=SEAT_LADDER,
                storage_root=root,
                injected_tree_bytes=None,
                injected_commit_tree_depth=None,
            )
        )
    )
    assert report.seat_ladder == SEAT_LADDER
    assert [row.seat_count for row in report.seat_baselines] == list(SEAT_LADDER)
    assert report.repeats == 2
    assert report.baseline_eligibility is BaselineEligibility.ELIGIBLE
    assert report.watched_latency_target_is_gate is False
    assert report.watched_latency_target["approx_ms"] == 50
    assert report.ci_enforces_latency_gate is False
    assert report.e9_f04_closed is True
    assert report.requires_real_vps is False
    assert report.soak_local_procurement_skipped is True
    assert report.variance_method.variance_multiple == _MULTIPLE
    assert report.variance_method.regression_threshold is None
    assert report.variance_method.status is BudgetStatus.PROVISIONAL_EVIDENCE
    assert report.provenance.lifecycle is BenchLifecycle.PRE_DOORS_OPEN
    assert "|" in report.provenance.platform_tuple

    for row in report.seat_baselines:
        expected_wall = row.mean_wall_ns + _MULTIPLE * row.stdev_wall_ns
        expected_rss = row.mean_peak_rss_bytes + _MULTIPLE * row.stdev_peak_rss_bytes
        assert row.regression_threshold_wall_ns == expected_wall
        assert row.regression_threshold_rss_bytes == expected_rss
        assert row.regression_threshold_wall_ns != 50
        assert [item.rung for item in row.rungs] == [
            HotPathRung(name)
            for name in (
                "tick_received",
                "evidence_write",
                "indicator_update",
                "decision",
                "risk_evaluation",
                "order_submitted",
            )
        ]
        for item in row.rungs:
            expected = item.mean_wall_ns + _MULTIPLE * item.stdev_wall_ns
            assert item.regression_threshold_wall_ns == expected

    for harness in report.harness_reports:
        assert _ok(gate_may_enforce(harness)) is False
        assert harness.watched_latency_target_is_gate is False
        assert all(slot.gate_enforced is False for slot in harness.budgets)
        assert all(
            slot.status is BudgetStatus.UNSET and slot.value is None
            for slot in harness.budgets
            if slot.name not in {"regression_threshold", "variance_multiple"}
        )

    storage = report.storage
    assert storage.representative_day_complete is True
    assert storage.first_hours_complete is True
    assert storage.bytes_per_day == storage.journal_growth_bytes + storage.log_growth_bytes + (
        storage.metrics_growth_bytes + storage.backup_growth_bytes
    )
    assert storage.retained_commit_tree_depth == 3
    assert storage.observability_quota_bytes == _BUDGET["observability"]
    assert storage.hot_room_headroom_bytes >= 0
    assert storage.protection_intent_reserve_bytes >= 0
    names = [item.name for item in storage.line_items]
    assert names == list(STORAGE_LINE_ITEMS)
    assert all(item.within_budget for item in storage.line_items)
    assert storage.capacity.trips_before_exhaustion is True
    assert storage.capacity.band is CapacityBand.OK
    assert storage.capacity.entries_refused is False
    mapping = report.as_mapping()
    assert mapping["fingerprint"] == report.fingerprint.value
    assert mapping["watched_latency_target_is_gate"] is False


def test_capacity_no_new_entry_trips_before_disk_exhaustion() -> None:
    ok = _ok(
        evaluate_storage_capacity(
            used_bytes=1_000,
            budget_bytes=10_000,
            disk_headroom_min=2_000,
            free_bytes=5_000,
        )
    )
    assert ok.band is CapacityBand.OK
    assert ok.entries_refused is False
    assert ok.trips_before_exhaustion is True

    degraded = _ok(
        evaluate_storage_capacity(
            used_bytes=9_000,
            budget_bytes=10_000,
            disk_headroom_min=2_000,
            free_bytes=1_000,
        )
    )
    assert degraded.band is CapacityBand.NO_NEW_ENTRY
    assert degraded.entries_refused is True
    assert degraded.free_bytes > 0

    full = _ok(
        evaluate_storage_capacity(
            used_bytes=10_000,
            budget_bytes=10_000,
            disk_headroom_min=2_000,
            free_bytes=0,
        )
    )
    assert full.band is CapacityBand.FULL
    assert full.entries_refused is True

    over = _ok(
        evaluate_storage_capacity(
            used_bytes=12_000,
            budget_bytes=10_000,
            disk_headroom_min=2_000,
        )
    )
    assert over.band is CapacityBand.CAPACITY_REFUSAL
    assert over.entries_refused is True


def test_measure_storage_trees_from_fixture(tmp_path: Path) -> None:
    root = _ok(materialize_representative_day(tmp_path / "trees", sizes=_TREES, commit_trees=2))
    measured = _ok(
        measure_storage_trees(
            root,
            vps_disk_budget=_BUDGET,
            disk_headroom_min=_HEADROOM,
            free_bytes=4_000,
        )
    )
    assert measured.retained_commit_tree_depth == 2
    assert measured.journal_growth_bytes == 256
    assert measured.log_growth_bytes == 256
    assert measured.metrics_growth_bytes == 256
    assert measured.backup_growth_bytes == 256
    assert measured.bytes_per_day == 1_024


def test_derive_regression_thresholds_from_synthetic_marks() -> None:
    first = _ok(run(lifecycle=BenchLifecycle.PRE_DOORS_OPEN, ladder=(10,)))
    second = _ok(run(lifecycle=BenchLifecycle.STAND_DOWN_ALIVE, ladder=(10,)))
    rows = _ok(
        derive_regression_thresholds(
            (first.marks, second.marks),
            variance_multiple=2,
        )
    )
    assert len(rows) == 1
    walls = [first.marks[0].wall_time_ns, second.marks[0].wall_time_ns]
    mean = sum(walls) // 2
    stdev = math.ceil(statistics.pstdev(walls))
    assert rows[0].mean_wall_ns == mean
    assert rows[0].stdev_wall_ns == stdev
    assert rows[0].regression_threshold_wall_ns == mean + 2 * stdev


def test_refuses_procure_vps_and_watched_gate_and_invented_budget() -> None:
    procure = _refusal(record_first_hours_baselines(_inputs(procure_vps=True)))
    assert procure.category is RefusalCategory.POLICY_REJECTION
    assert procure.context["failure_id"] == "first_hours.procure_vps"
    assert refuse_procure_vps().context["failure_id"] == "first_hours.procure_vps"

    watched = _refusal(record_first_hours_baselines(_inputs(use_watched_latency_as_gate=True)))
    assert watched.context["failure_id"] == "first_hours.watched_target_as_gate"
    assert refuse_watched_target_as_gate().context["failure_id"] == (
        "first_hours.watched_target_as_gate"
    )

    invented = _refusal(record_first_hours_baselines(_inputs(invent_latency_budget=True)))
    assert invented.context["failure_id"] == "first_hours.invented_latency_budget"
    assert refuse_invented_latency_budget().context["failure_id"] == (
        "first_hours.invented_latency_budget"
    )

    ci_gate = _refusal(record_first_hours_baselines(_inputs(ci_enforce_latency_gate=True)))
    assert ci_gate.context["failure_id"] == "first_hours.ci_latency_gate"
    assert refuse_ci_latency_gate().context["failure_id"] == "first_hours.ci_latency_gate"

    weaken = _refusal(record_first_hours_baselines(_inputs(weaken_thresholds=True)))
    assert weaken.context["failure_id"] == "first_hours.weaken_thresholds"
    assert refuse_weaken_thresholds().context["failure_id"] == "first_hours.weaken_thresholds"

    dropped = _refusal(record_first_hours_baselines(_inputs(drop_observability=True)))
    assert dropped.context["failure_id"] == "first_hours.drop_observability"
    assert refuse_drop_observability().context["failure_id"] == "first_hours.drop_observability"


def test_refuses_slice_driving_lifecycle() -> None:
    refused = _refusal(
        record_first_hours_baselines(
            _inputs(lifecycle=BenchLifecycle.RUNNING_SLICE_DRIVING)
        )
    )
    assert refused.context["failure_id"] == "first_hours.contaminated_lifecycle"


def test_refuses_invalid_variance_multiple_and_missing_observability() -> None:
    zero = _refusal(record_first_hours_baselines(_inputs(variance_multiple=0)))
    assert zero.context["failure_id"] == "first_hours.inputs"
    as_bool = _refusal(record_first_hours_baselines(_inputs(variance_multiple=True)))
    assert as_bool.context["failure_id"] == "first_hours.inputs"
    budget = dict(_BUDGET)
    del budget["observability"]
    missing = _refusal(record_first_hours_baselines(_inputs(vps_disk_budget=budget)))
    assert missing.context["failure_id"] == "first_hours.drop_observability"


def test_failure_ids_are_designed() -> None:
    for failure_id in (
        "first_hours.inputs",
        "first_hours.contaminated_lifecycle",
        "first_hours.procure_vps",
        "first_hours.watched_target_as_gate",
        "first_hours.invented_latency_budget",
        "first_hours.ci_latency_gate",
        "first_hours.weaken_thresholds",
        "first_hours.drop_observability",
    ):
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS
