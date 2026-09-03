"""First-hours VPS and storage baselines (Story 28.7 / TN-23 / E9-F04).

Repeats the test-status harness at 10/40/100/200 seats, records wall time,
peak RSS, six live-path rungs, queue/backpressure, deployment tuple, and
lifecycle state, and states regression thresholds as a declared multiple of
measured run-to-run variance. The watched ~50 ms figure is recorded and is
never a gate (FTR-07). Storage line items are measured against an injected
``vps_disk_budget`` fixture; ``no-new-entry`` trips before disk exhaustion.

A real VPS is not required. Soak-local procurement revision is skipped.
CI runs this for correctness only and never enforces a latency merge gate.
"""

from __future__ import annotations

import importlib.util
import math
import statistics
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Final, Protocol, cast

from qmf.core import Fingerprint, Ok, Result, TypedRefusal, fingerprint, is_ok, is_refusal

from qmn.bench._refuse import invalid, policy
from qmn.bench.harness import collect_provenance, run
from qmn.bench.schema import (
    DESIGN_BOT_CONCURRENCY_REFERENCE,
    HOT_PATH_RUNGS,
    SEAT_LADDER,
    VARIANCE_METHOD,
    VARIANCE_METHOD_DESCRIPTION,
    WATCHED_LATENCY_TARGET,
    WATCHED_LATENCY_TARGET_IS_GATE,
    BaselineEligibility,
    BenchLifecycle,
    BudgetStatus,
    DeploymentProvenance,
    HarnessReport,
    HotPathRung,
    SeatMarkResult,
    VarianceMethod,
    baseline_eligible,
    gate_may_enforce,
)

__all__ = [
    "CI_ENFORCES_LATENCY_GATE",
    "E9_F04_CLOSED",
    "FIRST_HOURS_CLASS",
    "FIRST_HOURS_FORMAT_VERSION",
    "FIRST_HOURS_SURFACE",
    "PROCURES_VPS",
    "REQUIRES_REAL_VPS",
    "SOAK_LOCAL_PROCUREMENT_SKIPPED",
    "STORAGE_LINE_ITEMS",
    "CapacityBand",
    "CapacityDecision",
    "FirstHoursInputs",
    "FirstHoursReport",
    "RungBaseline",
    "SeatBaseline",
    "StorageBaseline",
    "StorageLineItem",
    "derive_regression_thresholds",
    "evaluate_storage_capacity",
    "materialize_representative_day",
    "measure_storage_trees",
    "record_first_hours_baselines",
    "refuse_ci_latency_gate",
    "refuse_drop_observability",
    "refuse_invented_latency_budget",
    "refuse_procure_vps",
    "refuse_watched_target_as_gate",
    "refuse_weaken_thresholds",
]

FIRST_HOURS_SURFACE: Final[str] = "qmn.bench.baselines"
FIRST_HOURS_CLASS: Final[str] = "first-hours-vps-storage-baselines"
FIRST_HOURS_FORMAT_VERSION: Final[int] = 1
REQUIRES_REAL_VPS: Final[bool] = False
PROCURES_VPS: Final[bool] = False
SOAK_LOCAL_PROCUREMENT_SKIPPED: Final[bool] = True
CI_ENFORCES_LATENCY_GATE: Final[bool] = False
E9_F04_CLOSED: Final[bool] = True

_ID_INPUTS: Final[str] = "first_hours.inputs"
_ID_CONTAMINATED: Final[str] = "first_hours.contaminated_lifecycle"
_ID_PROCURE: Final[str] = "first_hours.procure_vps"
_ID_WATCHED: Final[str] = "first_hours.watched_target_as_gate"
_ID_INVENTED: Final[str] = "first_hours.invented_latency_budget"
_ID_CI_GATE: Final[str] = "first_hours.ci_latency_gate"
_ID_WEAKEN: Final[str] = "first_hours.weaken_thresholds"
_ID_DROP_OBS: Final[str] = "first_hours.drop_observability"

STORAGE_LINE_ITEMS: Final[tuple[str, ...]] = (
    "journal",
    "log",
    "metrics",
    "backup",
    "hot_room",
    "observability",
    "commit_trees",
    "protection_intent_reserve",
)

_TREE_DIRS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "journal": "rooms/journal",
        "log": "logs",
        "metrics": "metrics",
        "backup": "backup",
        "hot_room": "rooms/hot",
        "observability": "observability",
        "commit_trees": "opt-qmx",
        "protection_intent_reserve": "state/protection-intent",
        "evidence": "evidence",
    }
)

_GROWTH_ITEMS: Final[tuple[str, ...]] = ("journal", "log", "metrics", "backup")


class _DeploySafeIO(Protocol):
    def write_bytes_exclusive_no_follow(
        self, path: Path, data: bytes, *, contain_within: Path
    ) -> None: ...

    def write_text_exclusive_no_follow(
        self, path: Path, text: str, *, contain_within: Path
    ) -> None: ...


@cache
def _deploy_safe_io() -> _DeploySafeIO:
    """Load ``qmn/deploy/safe_io.py`` from the distribution root (SKY-D324)."""
    name = "qmn_deploy_safe_io"
    cached: ModuleType | None = sys.modules.get(name)
    if cached is not None:
        return cast(_DeploySafeIO, cached)
    path = Path(__file__).resolve().parents[3] / "deploy" / "safe_io.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return cast(_DeploySafeIO, module)


class CapacityBand(StrEnum):
    """Disk / budget capacity bands — headroom trips before exhaustion."""

    OK = "ok"
    NO_NEW_ENTRY = "no-new-entry"
    CAPACITY_REFUSAL = "capacity-refusal"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class CapacityDecision:
    """One capacity sample against ``vps_disk_budget`` and ``disk_headroom_min``."""

    band: CapacityBand
    free_bytes: int
    used_bytes: int
    budget_bytes: int
    disk_headroom_min: int
    entries_refused: bool
    trips_before_exhaustion: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "band": self.band.value,
                "budget_bytes": self.budget_bytes,
                "disk_headroom_min": self.disk_headroom_min,
                "entries_refused": self.entries_refused,
                "free_bytes": self.free_bytes,
                "trips_before_exhaustion": self.trips_before_exhaustion,
                "used_bytes": self.used_bytes,
            }
        )


@dataclass(frozen=True, slots=True)
class StorageLineItem:
    """One named ``vps_disk_budget`` line item with measured bytes."""

    name: str
    bytes_used: int
    budget_bytes: int
    within_budget: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "budget_bytes": self.budget_bytes,
                "bytes_used": self.bytes_used,
                "name": self.name,
                "within_budget": self.within_budget,
            }
        )


@dataclass(frozen=True, slots=True)
class StorageBaseline:
    """Measured first-hours / representative-day storage against the budget."""

    line_items: tuple[StorageLineItem, ...]
    bytes_per_day: int
    journal_growth_bytes: int
    log_growth_bytes: int
    metrics_growth_bytes: int
    backup_growth_bytes: int
    hot_room_headroom_bytes: int
    observability_quota_bytes: int
    retained_commit_tree_depth: int
    protection_intent_reserve_bytes: int
    capacity: CapacityDecision
    representative_day_complete: bool
    first_hours_complete: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "backup_growth_bytes": self.backup_growth_bytes,
                "bytes_per_day": self.bytes_per_day,
                "capacity": dict(self.capacity.as_mapping()),
                "first_hours_complete": self.first_hours_complete,
                "hot_room_headroom_bytes": self.hot_room_headroom_bytes,
                "journal_growth_bytes": self.journal_growth_bytes,
                "line_items": [dict(item.as_mapping()) for item in self.line_items],
                "log_growth_bytes": self.log_growth_bytes,
                "metrics_growth_bytes": self.metrics_growth_bytes,
                "observability_quota_bytes": self.observability_quota_bytes,
                "protection_intent_reserve_bytes": self.protection_intent_reserve_bytes,
                "representative_day_complete": self.representative_day_complete,
                "retained_commit_tree_depth": self.retained_commit_tree_depth,
            }
        )


@dataclass(frozen=True, slots=True)
class RungBaseline:
    """Variance-derived regression threshold for one AD-13 live-path rung."""

    rung: HotPathRung
    mean_wall_ns: int
    stdev_wall_ns: int
    regression_threshold_wall_ns: int

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "mean_wall_ns": self.mean_wall_ns,
                "regression_threshold_wall_ns": self.regression_threshold_wall_ns,
                "rung": self.rung.value,
                "stdev_wall_ns": self.stdev_wall_ns,
            }
        )


@dataclass(frozen=True, slots=True)
class SeatBaseline:
    """One seat-count baseline with variance-derived regression thresholds."""

    seat_count: int
    repeats: int
    mean_wall_ns: int
    stdev_wall_ns: int
    regression_threshold_wall_ns: int
    mean_peak_rss_bytes: int
    stdev_peak_rss_bytes: int
    regression_threshold_rss_bytes: int
    rungs: tuple[RungBaseline, ...]
    backpressure_observed: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "backpressure_observed": self.backpressure_observed,
                "mean_peak_rss_bytes": self.mean_peak_rss_bytes,
                "mean_wall_ns": self.mean_wall_ns,
                "regression_threshold_rss_bytes": self.regression_threshold_rss_bytes,
                "regression_threshold_wall_ns": self.regression_threshold_wall_ns,
                "repeats": self.repeats,
                "rungs": [dict(item.as_mapping()) for item in self.rungs],
                "seat_count": self.seat_count,
                "stdev_peak_rss_bytes": self.stdev_peak_rss_bytes,
                "stdev_wall_ns": self.stdev_wall_ns,
            }
        )


@dataclass(frozen=True, slots=True)
class FirstHoursInputs:
    """Declared fixtures for the first-hours recorder — never a real VPS."""

    variance_multiple: int
    disk_headroom_min: int
    vps_disk_budget: Mapping[str, int]
    lifecycle: BenchLifecycle = BenchLifecycle.PRE_DOORS_OPEN
    ladder: tuple[int, ...] = SEAT_LADDER
    repeats: int = 2
    deployment_id: str = "local-ci"
    storage_root: Path | None = None
    injected_tree_bytes: Mapping[str, int] | None = None
    injected_commit_tree_depth: int | None = None
    free_bytes: int | None = None
    procure_vps: bool = False
    use_watched_latency_as_gate: bool = False
    invent_latency_budget: bool = False
    ci_enforce_latency_gate: bool = False
    weaken_thresholds: bool = False
    drop_observability: bool = False


@dataclass(frozen=True, slots=True)
class FirstHoursReport:
    """Fingerprinted first-hours baseline: harness + storage, no latency gate."""

    format_version: int
    fingerprint: Fingerprint
    provenance: DeploymentProvenance
    seat_ladder: tuple[int, ...]
    design_bot_concurrency_reference: int
    repeats: int
    seat_baselines: tuple[SeatBaseline, ...]
    storage: StorageBaseline
    variance_method: VarianceMethod
    watched_latency_target: Mapping[str, object]
    watched_latency_target_is_gate: bool
    baseline_eligibility: BaselineEligibility
    e9_f04_closed: bool
    requires_real_vps: bool
    procure_vps: bool
    soak_local_procurement_skipped: bool
    ci_enforces_latency_gate: bool
    harness_reports: tuple[HarnessReport, ...]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "baseline_eligibility": self.baseline_eligibility.value,
            "ci_enforces_latency_gate": self.ci_enforces_latency_gate,
            "class": FIRST_HOURS_CLASS,
            "design_bot_concurrency_reference": self.design_bot_concurrency_reference,
            "e9_f04_closed": self.e9_f04_closed,
            "format_version": self.format_version,
            "procure_vps": self.procure_vps,
            "provenance": dict(self.provenance.as_mapping()),
            "repeats": self.repeats,
            "requires_real_vps": self.requires_real_vps,
            "seat_baselines": [dict(item.as_mapping()) for item in self.seat_baselines],
            "seat_ladder": list(self.seat_ladder),
            "soak_local_procurement_skipped": self.soak_local_procurement_skipped,
            "storage": dict(self.storage.as_mapping()),
            "surface": FIRST_HOURS_SURFACE,
            "variance_method": {
                "method_id": self.variance_method.method_id,
                "status": self.variance_method.status.value,
                "variance_multiple": self.variance_method.variance_multiple,
            },
            "watched_latency_target": dict(self.watched_latency_target),
            "watched_latency_target_is_gate": self.watched_latency_target_is_gate,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        return MappingProxyType(body)


def refuse_procure_vps(**extra: object) -> TypedRefusal:
    """Story 28.7 does not procure a VPS (soak-local / AR-87)."""
    return policy(
        "vps_procurement",
        "first-hours baselines run on the local/CI host; a real VPS "
        "procurement revision is soak-local and is not a factory AC",
        failure_id=_ID_PROCURE,
        **extra,
    )


def refuse_watched_target_as_gate(**extra: object) -> TypedRefusal:
    """FTR-07: the watched ~50 ms figure is never a gate."""
    return policy(
        "watched_latency_target",
        "the watched ~50 ms figure is recorded and is never a gate (FTR-07)",
        failure_id=_ID_WATCHED,
        **extra,
    )


def refuse_invented_latency_budget(**extra: object) -> TypedRefusal:
    """FTR-07: the recorder invents no latency budgets."""
    return policy(
        "latency_budget",
        "numeric hot-path/latency gates are not invented; thresholds are "
        "declared multiples of measured run-to-run variance (FTR-07)",
        failure_id=_ID_INVENTED,
        **extra,
    )


def refuse_ci_latency_gate(**extra: object) -> TypedRefusal:
    """CI runs the harness for correctness only (DEC-0208)."""
    return policy(
        "ci_latency_gate",
        "CI runs the first-hours harness for correctness only; derived "
        "thresholds are evidence, never a merge-gate latency budget",
        failure_id=_ID_CI_GATE,
        **extra,
    )


def refuse_weaken_thresholds(**extra: object) -> TypedRefusal:
    """DEC-0261: no story weakens measured thresholds to fit the box."""
    return policy(
        "regression_threshold",
        "measured regression thresholds are not weakened to fit a host; "
        "procurement is revised on an adequate machine (DEC-0261)",
        failure_id=_ID_WEAKEN,
        **extra,
    )


def refuse_drop_observability(**extra: object) -> TypedRefusal:
    """DEC-0261: observability is not dropped to fit the box."""
    return policy(
        "observability",
        "the observability line item of vps_disk_budget is not dropped to "
        "fit the host (DEC-0261 / DEC-0200)",
        failure_id=_ID_DROP_OBS,
        **extra,
    )


def record_first_hours_baselines(inputs: object) -> Result[FirstHoursReport]:
    """Run the seat sweep, derive variance thresholds, and measure storage."""
    parsed = _parse_inputs(inputs)
    if is_refusal(parsed):
        return parsed
    cfg = parsed.value
    if cfg.procure_vps:
        return refuse_procure_vps()
    if cfg.use_watched_latency_as_gate:
        return refuse_watched_target_as_gate()
    if cfg.invent_latency_budget:
        return refuse_invented_latency_budget()
    if cfg.ci_enforce_latency_gate:
        return refuse_ci_latency_gate()
    if cfg.weaken_thresholds:
        return refuse_weaken_thresholds()
    if cfg.drop_observability:
        return refuse_drop_observability()
    if not baseline_eligible(cfg.lifecycle):
        return policy(
            "lifecycle",
            "a run recorded while the loop was driving slices is neither a "
            "baseline nor a gate (DEC-0208)",
            failure_id=_ID_CONTAMINATED,
            lifecycle=cfg.lifecycle.value,
        )

    reports: list[HarnessReport] = []
    for index in range(cfg.repeats):
        measured = run(
            lifecycle=cfg.lifecycle,
            ladder=cfg.ladder,
            deployment_id=f"{cfg.deployment_id}-r{index + 1}",
        )
        if is_refusal(measured):
            return measured
        gated = gate_may_enforce(measured.value)
        if is_refusal(gated):
            return gated
        if is_ok(gated) and gated.value is not False:
            return refuse_ci_latency_gate(gate_may_enforce=gated.value)
        if measured.value.watched_latency_target_is_gate:
            return refuse_watched_target_as_gate()
        reports.append(measured.value)

    marks = tuple(tuple(report.marks) for report in reports)
    derived = derive_regression_thresholds(
        marks,
        variance_multiple=cfg.variance_multiple,
    )
    if is_refusal(derived):
        return derived

    storage = _storage_baseline(cfg)
    if is_refusal(storage):
        return storage

    provenance = collect_provenance(
        lifecycle=cfg.lifecycle,
        deployment_id=cfg.deployment_id,
    )
    variance = VarianceMethod(
        method_id=VARIANCE_METHOD,
        description=VARIANCE_METHOD_DESCRIPTION,
        variance_multiple=cfg.variance_multiple,
        regression_threshold=None,
        status=BudgetStatus.PROVISIONAL_EVIDENCE,
    )
    identity = {
        "baseline_eligibility": BaselineEligibility.ELIGIBLE.value,
        "ci_enforces_latency_gate": CI_ENFORCES_LATENCY_GATE,
        "class": FIRST_HOURS_CLASS,
        "design_bot_concurrency_reference": DESIGN_BOT_CONCURRENCY_REFERENCE,
        "e9_f04_closed": E9_F04_CLOSED,
        "format_version": FIRST_HOURS_FORMAT_VERSION,
        "procure_vps": PROCURES_VPS,
        "provenance": dict(provenance.as_mapping()),
        "repeats": cfg.repeats,
        "requires_real_vps": REQUIRES_REAL_VPS,
        "seat_baselines": [dict(item.as_mapping()) for item in derived.value],
        "seat_ladder": list(cfg.ladder),
        "soak_local_procurement_skipped": SOAK_LOCAL_PROCUREMENT_SKIPPED,
        "storage": dict(storage.value.as_mapping()),
        "surface": FIRST_HOURS_SURFACE,
        "variance_method": {
            "method_id": variance.method_id,
            "status": variance.status.value,
            "variance_multiple": variance.variance_multiple,
        },
        "watched_latency_target": dict(WATCHED_LATENCY_TARGET),
        "watched_latency_target_is_gate": WATCHED_LATENCY_TARGET_IS_GATE,
    }
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return stamped
    return Ok(
        FirstHoursReport(
            format_version=FIRST_HOURS_FORMAT_VERSION,
            fingerprint=stamped.value,
            provenance=provenance,
            seat_ladder=cfg.ladder,
            design_bot_concurrency_reference=DESIGN_BOT_CONCURRENCY_REFERENCE,
            repeats=cfg.repeats,
            seat_baselines=derived.value,
            storage=storage.value,
            variance_method=variance,
            watched_latency_target=dict(WATCHED_LATENCY_TARGET),
            watched_latency_target_is_gate=WATCHED_LATENCY_TARGET_IS_GATE,
            baseline_eligibility=BaselineEligibility.ELIGIBLE,
            e9_f04_closed=E9_F04_CLOSED,
            requires_real_vps=REQUIRES_REAL_VPS,
            procure_vps=PROCURES_VPS,
            soak_local_procurement_skipped=SOAK_LOCAL_PROCUREMENT_SKIPPED,
            ci_enforces_latency_gate=CI_ENFORCES_LATENCY_GATE,
            harness_reports=tuple(reports),
        )
    )


def derive_regression_thresholds(
    repeats: object,
    *,
    variance_multiple: object,
) -> Result[tuple[SeatBaseline, ...]]:
    """State per-seat / per-rung ceilings as ``mean + multiple * stdev``."""
    multiple = _positive_int("variance_multiple", variance_multiple)
    if is_refusal(multiple):
        return multiple
    rows = _repeat_marks(repeats)
    if is_refusal(rows):
        return rows
    grouped: dict[int, list[SeatMarkResult]] = {}
    for pass_marks in rows.value:
        for mark in pass_marks:
            grouped.setdefault(mark.seat_count, []).append(mark)
    baselines: list[SeatBaseline] = []
    for seat_count in sorted(grouped):
        samples = grouped[seat_count]
        walls = [sample.wall_time_ns for sample in samples]
        rss = [sample.peak_rss_bytes for sample in samples]
        wall_stats = _spread(walls)
        rss_stats = _spread(rss)
        rungs = _rung_baselines(samples, multiple.value)
        if is_refusal(rungs):
            return rungs
        backpressure = any(sample.queue.backpressure_observed for sample in samples)
        baselines.append(
            SeatBaseline(
                seat_count=seat_count,
                repeats=len(samples),
                mean_wall_ns=wall_stats[0],
                stdev_wall_ns=wall_stats[1],
                regression_threshold_wall_ns=_ceiling(
                    wall_stats[0], wall_stats[1], multiple.value
                ),
                mean_peak_rss_bytes=rss_stats[0],
                stdev_peak_rss_bytes=rss_stats[1],
                regression_threshold_rss_bytes=_ceiling(
                    rss_stats[0], rss_stats[1], multiple.value
                ),
                rungs=rungs.value,
                backpressure_observed=backpressure,
            )
        )
    return Ok(tuple(baselines))


def evaluate_storage_capacity(
    *,
    used_bytes: object,
    budget_bytes: object,
    disk_headroom_min: object,
    free_bytes: object | None = None,
) -> Result[CapacityDecision]:
    """Mint ``ok | no-new-entry | capacity-refusal | full`` before exhaustion."""
    used = _non_negative_int("used_bytes", used_bytes)
    if is_refusal(used):
        return used
    budget = _positive_int("budget_bytes", budget_bytes)
    if is_refusal(budget):
        return budget
    headroom = _positive_int("disk_headroom_min", disk_headroom_min)
    if is_refusal(headroom):
        return headroom
    remaining_budget = budget.value - used.value
    if free_bytes is None:
        free = remaining_budget if remaining_budget > 0 else 0
    else:
        resolved_free = _non_negative_int("free_bytes", free_bytes)
        if is_refusal(resolved_free):
            return resolved_free
        free = resolved_free.value
    trips_before = headroom.value < budget.value
    if used.value > budget.value:
        band = CapacityBand.CAPACITY_REFUSAL
        entries = True
        free = 0 if free < 0 else free
    elif free == 0:
        band = CapacityBand.FULL
        entries = True
    elif free < headroom.value:
        band = CapacityBand.NO_NEW_ENTRY
        entries = True
    else:
        band = CapacityBand.OK
        entries = False
    return Ok(
        CapacityDecision(
            band=band,
            free_bytes=free,
            used_bytes=used.value,
            budget_bytes=budget.value,
            disk_headroom_min=headroom.value,
            entries_refused=entries,
            trips_before_exhaustion=trips_before,
        )
    )


def measure_storage_trees(
    root: object,
    *,
    vps_disk_budget: object,
    disk_headroom_min: object,
    injected_tree_bytes: object = None,
    injected_commit_tree_depth: object = None,
    free_bytes: object | None = None,
) -> Result[StorageBaseline]:
    """Measure named trees against injected ``vps_disk_budget`` line items."""
    budget = _budget_map(vps_disk_budget)
    if is_refusal(budget):
        return budget
    sizes = _tree_sizes(
        root,
        injected_tree_bytes=injected_tree_bytes,
    )
    if is_refusal(sizes):
        return sizes
    depth = _commit_depth(
        root,
        injected_commit_tree_depth=injected_commit_tree_depth,
    )
    if is_refusal(depth):
        return depth
    items: list[StorageLineItem] = []
    for name in STORAGE_LINE_ITEMS:
        used = sizes.value.get(name, 0)
        cap = budget.value[name]
        items.append(
            StorageLineItem(
                name=name,
                bytes_used=used,
                budget_bytes=cap,
                within_budget=used <= cap,
            )
        )
    by_name = {item.name: item for item in items}
    used_total = sum(item.bytes_used for item in items)
    budget_total = sum(item.budget_bytes for item in items)
    capacity = evaluate_storage_capacity(
        used_bytes=used_total,
        budget_bytes=budget_total,
        disk_headroom_min=disk_headroom_min,
        free_bytes=free_bytes,
    )
    if is_refusal(capacity):
        return capacity
    hot_budget = by_name["hot_room"].budget_bytes
    hot_used = by_name["hot_room"].bytes_used
    return Ok(
        StorageBaseline(
            line_items=tuple(items),
            bytes_per_day=sum(by_name[name].bytes_used for name in _GROWTH_ITEMS),
            journal_growth_bytes=by_name["journal"].bytes_used,
            log_growth_bytes=by_name["log"].bytes_used,
            metrics_growth_bytes=by_name["metrics"].bytes_used,
            backup_growth_bytes=by_name["backup"].bytes_used,
            hot_room_headroom_bytes=max(0, hot_budget - hot_used),
            observability_quota_bytes=by_name["observability"].budget_bytes,
            retained_commit_tree_depth=depth.value,
            protection_intent_reserve_bytes=by_name["protection_intent_reserve"].bytes_used,
            capacity=capacity.value,
            representative_day_complete=True,
            first_hours_complete=True,
        )
    )


def materialize_representative_day(
    root: object,
    *,
    sizes: Mapping[str, int] | None = None,
    commit_trees: object = 3,
) -> Result[Path]:
    """Write a synthetic representative-day tree (infrastructure bytes only)."""
    if not isinstance(root, Path):
        return invalid(
            "storage_root",
            "storage_root is a Path",
            given=type(root).__name__,
            failure_id=_ID_INPUTS,
        )
    depth = _positive_int("commit_trees", commit_trees)
    if is_refusal(depth):
        return depth
    payload: dict[str, int] = dict.fromkeys(STORAGE_LINE_ITEMS, 256)
    if sizes is not None:
        payload = dict(sizes)
    try:
        writers = _deploy_safe_io()
        root.mkdir(parents=True, exist_ok=True)
        for name, relative in _TREE_DIRS.items():
            target = root / relative
            target.mkdir(parents=True, exist_ok=True)
            nbytes = payload.get(name, 256)
            if nbytes < 0:
                return invalid(
                    "sizes",
                    "tree byte counts are non-negative",
                    name=name,
                    given=nbytes,
                    failure_id=_ID_INPUTS,
                )
            writers.write_bytes_exclusive_no_follow(
                target / "day.bin",
                b"\x00" * nbytes,
                contain_within=root,
            )
        trees = root / _TREE_DIRS["commit_trees"]
        for index in range(depth.value):
            leaf = trees / f"tree-{index:02d}"
            leaf.mkdir(parents=True, exist_ok=True)
            writers.write_text_exclusive_no_follow(
                leaf / "HEAD",
                "fixture",
                contain_within=root,
            )
    except OSError as exc:
        return invalid(
            "storage_root",
            "could not materialize the representative-day fixture",
            error=type(exc).__name__,
            failure_id=_ID_INPUTS,
        )
    return Ok(root)


def _parse_inputs(inputs: object) -> Result[FirstHoursInputs]:
    if not isinstance(inputs, FirstHoursInputs):
        return invalid(
            "inputs",
            "first-hours baselines take FirstHoursInputs",
            given=type(inputs).__name__,
            failure_id=_ID_INPUTS,
        )
    multiple = _positive_int("variance_multiple", inputs.variance_multiple)
    if is_refusal(multiple):
        return multiple
    headroom = _positive_int("disk_headroom_min", inputs.disk_headroom_min)
    if is_refusal(headroom):
        return headroom
    budget = _budget_map(inputs.vps_disk_budget)
    if is_refusal(budget):
        return budget
    if "observability" not in budget.value:
        return refuse_drop_observability()
    if inputs.deployment_id.strip() == "":
        return invalid(
            "deployment_id",
            "deployment_id is a non-blank string",
            given=repr(inputs.deployment_id),
            failure_id=_ID_INPUTS,
        )
    if inputs.repeats < 2:
        return invalid(
            "repeats",
            "run-to-run variance requires at least two repeats",
            given=repr(inputs.repeats),
            failure_id=_ID_INPUTS,
        )
    ladder = _ladder(inputs.ladder)
    if is_refusal(ladder):
        return ladder
    return Ok(
        FirstHoursInputs(
            variance_multiple=multiple.value,
            disk_headroom_min=headroom.value,
            vps_disk_budget=budget.value,
            lifecycle=inputs.lifecycle,
            ladder=ladder.value,
            repeats=inputs.repeats,
            deployment_id=inputs.deployment_id.strip(),
            storage_root=inputs.storage_root,
            injected_tree_bytes=inputs.injected_tree_bytes,
            injected_commit_tree_depth=inputs.injected_commit_tree_depth,
            free_bytes=inputs.free_bytes,
            procure_vps=bool(inputs.procure_vps),
            use_watched_latency_as_gate=bool(inputs.use_watched_latency_as_gate),
            invent_latency_budget=bool(inputs.invent_latency_budget),
            ci_enforce_latency_gate=bool(inputs.ci_enforce_latency_gate),
            weaken_thresholds=bool(inputs.weaken_thresholds),
            drop_observability=bool(inputs.drop_observability),
        )
    )


def _storage_baseline(cfg: FirstHoursInputs) -> Result[StorageBaseline]:
    return measure_storage_trees(
        cfg.storage_root,
        vps_disk_budget=cfg.vps_disk_budget,
        disk_headroom_min=cfg.disk_headroom_min,
        injected_tree_bytes=cfg.injected_tree_bytes,
        injected_commit_tree_depth=cfg.injected_commit_tree_depth,
        free_bytes=cfg.free_bytes,
    )


def _ladder(ladder: object) -> Result[tuple[int, ...]]:
    if not isinstance(ladder, Sequence) or isinstance(ladder, (str, bytes)):
        return invalid(
            "ladder",
            "seat ladder is a sequence of positive integer seat counts",
            given=repr(ladder),
            failure_id=_ID_INPUTS,
        )
    items = cast("Sequence[object]", ladder)
    if not items:
        return invalid(
            "ladder",
            "seat ladder requires at least one positive seat count",
            failure_id=_ID_INPUTS,
        )
    resolved: list[int] = []
    for mark in items:
        if not isinstance(mark, int) or isinstance(mark, bool) or mark < 1:
            return invalid(
                "ladder",
                "each seat mark is a positive integer count",
                given=repr(mark),
                failure_id=_ID_INPUTS,
            )
        resolved.append(mark)
    return Ok(tuple(resolved))


def _repeat_marks(
    repeats: object,
) -> Result[tuple[tuple[SeatMarkResult, ...], ...]]:
    if not isinstance(repeats, Sequence) or isinstance(repeats, (str, bytes)):
        return invalid(
            "repeats",
            "derive_regression_thresholds takes a sequence of seat-mark tuples",
            given=type(repeats).__name__,
            failure_id=_ID_INPUTS,
        )
    passes = cast("Sequence[object]", repeats)
    if len(passes) < 2:
        return invalid(
            "repeats",
            "run-to-run variance requires at least two repeats",
            given=len(passes),
            failure_id=_ID_INPUTS,
        )
    rows: list[tuple[SeatMarkResult, ...]] = []
    for item in passes:
        if not isinstance(item, Sequence) or isinstance(item, (str, bytes)):
            return invalid(
                "repeats",
                "each repeat is a sequence of SeatMarkResult",
                given=type(item).__name__,
                failure_id=_ID_INPUTS,
            )
        marks = cast("Sequence[object]", item)
        resolved: list[SeatMarkResult] = []
        for mark in marks:
            if not isinstance(mark, SeatMarkResult):
                return invalid(
                    "repeats",
                    "each mark is a SeatMarkResult",
                    given=type(mark).__name__,
                    failure_id=_ID_INPUTS,
                )
            resolved.append(mark)
        rows.append(tuple(resolved))
    return Ok(tuple(rows))


def _rung_baselines(
    samples: Sequence[SeatMarkResult],
    multiple: int,
) -> Result[tuple[RungBaseline, ...]]:
    by_rung: dict[HotPathRung, list[int]] = {HotPathRung(name): [] for name in HOT_PATH_RUNGS}
    for sample in samples:
        seen = {item.rung for item in sample.rungs}
        missing = [name for name in HOT_PATH_RUNGS if HotPathRung(name) not in seen]
        if missing:
            return invalid(
                "rungs",
                "every named hot-path rung must be recorded",
                missing=missing,
                failure_id=_ID_INPUTS,
            )
        for item in sample.rungs:
            by_rung[item.rung].append(item.wall_time_ns)
    ordered: list[RungBaseline] = []
    for name in HOT_PATH_RUNGS:
        rung = HotPathRung(name)
        mean, stdev = _spread(by_rung[rung])
        ordered.append(
            RungBaseline(
                rung=rung,
                mean_wall_ns=mean,
                stdev_wall_ns=stdev,
                regression_threshold_wall_ns=_ceiling(mean, stdev, multiple),
            )
        )
    return Ok(tuple(ordered))


def _spread(values: Sequence[int]) -> tuple[int, int]:
    mean = sum(values) // len(values)
    if len(values) < 2:
        return mean, 0
    return mean, math.ceil(statistics.pstdev(values))


def _ceiling(mean: int, stdev: int, multiple: int) -> int:
    return mean + multiple * stdev


def _tree_sizes(
    root: object,
    *,
    injected_tree_bytes: object,
) -> Result[dict[str, int]]:
    if injected_tree_bytes is not None:
        if not isinstance(injected_tree_bytes, Mapping):
            return invalid(
                "injected_tree_bytes",
                "injected_tree_bytes is a mapping of line item to bytes",
                given=type(injected_tree_bytes).__name__,
                failure_id=_ID_INPUTS,
            )
        mapping = cast("Mapping[object, object]", injected_tree_bytes)
        sizes: dict[str, int] = {}
        for name in STORAGE_LINE_ITEMS:
            raw = mapping.get(name, 0)
            parsed = _non_negative_int(f"injected_tree_bytes.{name}", raw)
            if is_refusal(parsed):
                return parsed
            sizes[name] = parsed.value
        return Ok(sizes)
    if root is None:
        return invalid(
            "storage_root",
            "storage_root or injected_tree_bytes is required",
            failure_id=_ID_INPUTS,
        )
    if not isinstance(root, Path):
        return invalid(
            "storage_root",
            "storage_root is a Path",
            given=type(root).__name__,
            failure_id=_ID_INPUTS,
        )
    sizes = {}
    for name in STORAGE_LINE_ITEMS:
        sizes[name] = _directory_bytes(root / _TREE_DIRS[name])
    return Ok(sizes)


def _commit_depth(
    root: object,
    *,
    injected_commit_tree_depth: object,
) -> Result[int]:
    if injected_commit_tree_depth is not None:
        return _non_negative_int("injected_commit_tree_depth", injected_commit_tree_depth)
    if not isinstance(root, Path):
        return Ok(0)
    trees = root / _TREE_DIRS["commit_trees"]
    if not trees.is_dir():
        return Ok(0)
    depth = sum(1 for child in trees.iterdir() if child.is_dir())
    return Ok(depth)


def _directory_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for current, _dirs, files in path.walk():
        for name in files:
            try:
                total += (current / name).stat().st_size
            except OSError:
                continue
    return total


def _budget_map(value: object) -> Result[dict[str, int]]:
    if not isinstance(value, Mapping):
        return invalid(
            "vps_disk_budget",
            "vps_disk_budget is a mapping of named line items to byte caps",
            given=type(value).__name__,
            failure_id=_ID_INPUTS,
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, int] = {}
    for name in STORAGE_LINE_ITEMS:
        if name not in mapping:
            if name == "observability":
                return refuse_drop_observability()
            return invalid(
                "vps_disk_budget",
                "every named vps_disk_budget line item is required",
                missing=name,
                failure_id=_ID_INPUTS,
            )
        parsed = _positive_int(f"vps_disk_budget.{name}", mapping[name])
        if is_refusal(parsed):
            return parsed
        resolved[name] = parsed.value
    return Ok(resolved)


def _positive_int(field: str, value: object) -> Result[int]:
    parsed = _non_negative_int(field, value)
    if is_refusal(parsed):
        return parsed
    if parsed.value <= 0:
        return invalid(
            field,
            f"{field} is a positive int",
            given=repr(value),
            failure_id=_ID_INPUTS,
        )
    return parsed


def _non_negative_int(field: str, value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            field,
            f"{field} is an int byte count",
            given=repr(value),
            failure_id=_ID_INPUTS,
        )
    if value < 0:
        return invalid(
            field,
            f"{field} is a non-negative int",
            given=repr(value),
            failure_id=_ID_INPUTS,
        )
    return Ok(value)


