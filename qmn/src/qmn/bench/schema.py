"""Hot-path benchmark output schema — measure-then-budget, no invented gates.

Story 25.15 / 28.7 / TN-23 / DEC-0208 / FTR-07 / E9-F04. The schema records
wall time, peak RSS, queue behaviour, the six named AD-13 live-path rungs,
and deployment provenance. Story 28.7 records first-hours baselines and
states regression thresholds as a declared multiple of measured run-to-run
variance. The watched ~50 ms figure is recorded and is never a gate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal

from qmn.observability.metrics import LATENCY_RUNGS

__all__ = [
    "BUDGET_SLOT_NAMES",
    "DESIGN_BOT_CONCURRENCY_REFERENCE",
    "HOT_PATH_RUNGS",
    "SEAT_LADDER",
    "VARIANCE_METHOD",
    "VARIANCE_METHOD_DESCRIPTION",
    "WATCHED_LATENCY_TARGET",
    "WATCHED_LATENCY_TARGET_IS_GATE",
    "BaselineEligibility",
    "BenchLifecycle",
    "BudgetSlot",
    "BudgetStatus",
    "DeploymentProvenance",
    "HarnessReport",
    "HotPathRung",
    "QueueBehaviorSample",
    "RungSample",
    "SeatMarkResult",
    "VarianceMethod",
    "baseline_eligible",
    "budget_slots_unset",
    "gate_may_enforce",
]

# registry:design_bot_concurrency — sizing reference, never an SLO (DEC-0111).
DESIGN_BOT_CONCURRENCY_REFERENCE: Final[int] = 40

# Four-point seat sweep (TN-23 / AR-84 / DEC-0208).
SEAT_LADDER: Final[tuple[int, ...]] = (10, 40, 100, 200)

# Six AD-13 live-path rungs — names only; numeric budgets await baselines.
HOT_PATH_RUNGS: Final[tuple[str, ...]] = LATENCY_RUNGS

# Operator ~50 ms figure is a watched target, never a budget or gate (DEC-0208).
WATCHED_LATENCY_TARGET_IS_GATE: Final[bool] = False
WATCHED_LATENCY_TARGET: Final[Mapping[str, object]] = MappingProxyType(
    {
        "approx_ms": 50,
        "is_gate": False,
        "role": "watched-target",
        "source": "DEC-0208",
        "used_as_regression_threshold": False,
    }
)

VARIANCE_METHOD: Final[str] = "multiple-of-measured-run-to-run-variance"
VARIANCE_METHOD_DESCRIPTION: Final[str] = (
    "When a baseline is recorded, each benchmark's regression threshold is "
    "stated as a declared multiple of measured run-to-run variance on the same "
    "(OS, CPU-class) deployment tuple. A baseline without a stated threshold "
    "is not a gate (DEC-0208, DEC-0111). Story 28.7 records the first-hours "
    "baseline; CI runs the harness for correctness only and never enforces "
    "the derived threshold as a merge gate. The watched ~50 ms figure is "
    "recorded and is never that threshold."
)

BUDGET_SLOT_NAMES: Final[tuple[str, ...]] = (
    "max_slice_latency",
    "tick_received_budget",
    "evidence_write_budget",
    "indicator_update_budget",
    "decision_budget",
    "risk_evaluation_budget",
    "order_submitted_budget",
    "peak_rss_budget",
    "regression_threshold",
    "variance_multiple",
    "governor_cpu_budget",
    "governor_memory_budget",
)


class HotPathRung(StrEnum):
    """Named AD-13 live-path latency rungs (DEC-0138, DEC-0208)."""

    TICK_RECEIVED = "tick_received"
    EVIDENCE_WRITE = "evidence_write"
    INDICATOR_UPDATE = "indicator_update"
    DECISION = "decision"
    RISK_EVALUATION = "risk_evaluation"
    ORDER_SUBMITTED = "order_submitted"


class BenchLifecycle(StrEnum):
    """Lifecycle state recorded at measurement (DEC-0208, DEC-0236).

    A run recorded while the loop was driving slices is neither a baseline nor
    a gate — the harness must not contaminate slice latency and the node must
    not contaminate the baseline.
    """

    PRE_DOORS_OPEN = "pre-doors-open"
    STAND_DOWN_ALIVE = "stand-down-alive"
    RUNNING_SLICE_DRIVING = "running-slice-driving"
    DRAINING = "draining"
    STOPPED = "stopped"


class BudgetStatus(StrEnum):
    """Standing of a budget slot — unset until a measured baseline exists."""

    UNSET = "unset"
    PROVISIONAL_EVIDENCE = "provisional-evidence"
    RATIFIED = "ratified"


class BaselineEligibility(StrEnum):
    """Whether a harness report may become a baseline or gate."""

    ELIGIBLE = "eligible"
    CONTAMINATED_SLICE_DRIVING = "contaminated-slice-driving"
    BUDGETS_UNSET = "budgets-unset"


@dataclass(frozen=True, slots=True)
class VarianceMethod:
    """How a regression threshold is derived from measured run-to-run variance.

    ``variance_multiple`` is the declared multiplier, never a latency budget.
    Per-seat / per-rung nanosecond ceilings live on the first-hours baseline
    rows. A method-level ``regression_threshold`` stays unset so a single
    invented latency number cannot masquerade as the gate (FTR-07).
    """

    method_id: str = VARIANCE_METHOD
    description: str = VARIANCE_METHOD_DESCRIPTION
    variance_multiple: int | float | None = None
    regression_threshold: int | float | None = None
    status: BudgetStatus = BudgetStatus.UNSET


@dataclass(frozen=True, slots=True)
class BudgetSlot:
    """One named limit represented honestly when unmeasured (FTR-07 / E9-F04)."""

    name: str
    status: BudgetStatus = BudgetStatus.UNSET
    value: int | float | None = None
    unit: str | None = None
    gate_enforced: bool = False

    @classmethod
    def unset(cls, name: str, *, unit: str | None = None) -> BudgetSlot:
        """Build an unset placeholder — never silently enforced."""
        return cls(
            name=name,
            status=BudgetStatus.UNSET,
            value=None,
            unit=unit,
            gate_enforced=False,
        )


@dataclass(frozen=True, slots=True)
class DeploymentProvenance:
    """OS / CPU / deployment / lifecycle provenance for one harness run."""

    os_name: str
    os_release: str
    cpu_class: str
    machine: str
    python_implementation: str
    python_version: str
    deployment_id: str
    lifecycle: BenchLifecycle
    platform_tuple: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "os_name": self.os_name,
                "os_release": self.os_release,
                "cpu_class": self.cpu_class,
                "machine": self.machine,
                "python_implementation": self.python_implementation,
                "python_version": self.python_version,
                "deployment_id": self.deployment_id,
                "lifecycle": self.lifecycle.value,
                "platform_tuple": self.platform_tuple,
            }
        )


@dataclass(frozen=True, slots=True)
class RungSample:
    """One named hot-path rung measurement (wall ns + peak RSS at rung end)."""

    rung: HotPathRung
    wall_time_ns: int
    peak_rss_bytes: int


@dataclass(frozen=True, slots=True)
class QueueBehaviorSample:
    """Pacer / accumulator queue evidence — measured, never a invented bound."""

    enqueue_count: int
    admit_count: int
    protective_priority_waits: int
    local_queue_bound_refusals: int
    max_pending_depth: int
    accumulator_overflow_events: int
    backpressure_observed: bool


@dataclass(frozen=True, slots=True)
class SeatMarkResult:
    """One seat-count mark on the four-point sweep."""

    seat_count: int
    wall_time_ns: int
    peak_rss_bytes: int
    rungs: tuple[RungSample, ...]
    queue: QueueBehaviorSample
    conformance_double_kind: str
    slices_driven: int


@dataclass(frozen=True, slots=True)
class HarnessReport:
    """Full portable harness output — schema complete without numeric gates."""

    module: str
    seat_ladder: tuple[int, ...]
    design_bot_concurrency_reference: int
    provenance: DeploymentProvenance
    marks: tuple[SeatMarkResult, ...]
    budgets: tuple[BudgetSlot, ...]
    variance_method: VarianceMethod
    hot_path_rungs: tuple[str, ...]
    watched_latency_target_is_gate: bool
    baseline_eligibility: BaselineEligibility
    story_28_7_owns_vps_baselines: bool = True
    schema_version: int = 1
    extra: Mapping[str, object] = field(default_factory=dict[str, object])

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "schema_version": self.schema_version,
                "module": self.module,
                "seat_ladder": list(self.seat_ladder),
                "design_bot_concurrency_reference": self.design_bot_concurrency_reference,
                "provenance": dict(self.provenance.as_mapping()),
                "marks": [_mark_mapping(mark) for mark in self.marks],
                "budgets": [_budget_mapping(slot) for slot in self.budgets],
                "variance_method": {
                    "method_id": self.variance_method.method_id,
                    "description": self.variance_method.description,
                    "variance_multiple": self.variance_method.variance_multiple,
                    "regression_threshold": self.variance_method.regression_threshold,
                    "status": self.variance_method.status.value,
                },
                "hot_path_rungs": list(self.hot_path_rungs),
                "watched_latency_target_is_gate": self.watched_latency_target_is_gate,
                "baseline_eligibility": self.baseline_eligibility.value,
                "story_28_7_owns_vps_baselines": self.story_28_7_owns_vps_baselines,
                "extra": dict(self.extra),
            }
        )


def baseline_eligible(lifecycle: BenchLifecycle) -> bool:
    """True only when the harness may record a baseline or gate (DEC-0208)."""
    return lifecycle in {
        BenchLifecycle.PRE_DOORS_OPEN,
        BenchLifecycle.STAND_DOWN_ALIVE,
    }


def budget_slots_unset(names: Sequence[str] = BUDGET_SLOT_NAMES) -> tuple[BudgetSlot, ...]:
    """Every named placeholder as unset evidence (never enforced)."""
    units: dict[str, str] = {
        "max_slice_latency": "ns",
        "tick_received_budget": "ns",
        "evidence_write_budget": "ns",
        "indicator_update_budget": "ns",
        "decision_budget": "ns",
        "risk_evaluation_budget": "ns",
        "order_submitted_budget": "ns",
        "peak_rss_budget": "bytes",
        "regression_threshold": "variance-multiple",
        "variance_multiple": "dimensionless",
        "governor_cpu_budget": "cpu-share",
        "governor_memory_budget": "bytes",
    }
    return tuple(BudgetSlot.unset(name, unit=units.get(name)) for name in names)


def gate_may_enforce(report: HarnessReport) -> Result[Literal[False]]:
    """Refuse any attempt to treat unset budgets as a pass/fail gate (FTR-07).

    Always returns ``Ok(False)`` while budgets are unset, or a typed refusal when
    a caller tries to assert enforcement against unset slots / contaminated runs.
    """
    if report.baseline_eligibility is BaselineEligibility.CONTAMINATED_SLICE_DRIVING:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "baseline_eligibility",
                "reason": "a run recorded while the loop was driving slices is "
                "neither a baseline nor a gate (DEC-0208)",
                "lifecycle": report.provenance.lifecycle.value,
            },
        )
    if report.watched_latency_target_is_gate:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "watched_latency_target_is_gate",
                "reason": "the watched ~50 ms figure is recorded and is never "
                "a gate (FTR-07 / DEC-0208)",
            },
        )
    enforced = [slot.name for slot in report.budgets if slot.gate_enforced]
    if enforced:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "budgets",
                "reason": "placeholder or measured budgets must not be silently "
                "enforced; CI runs the harness for correctness only (DEC-0208)",
                "enforced": enforced,
            },
        )
    valued = [
        slot.name
        for slot in report.budgets
        if slot.status is BudgetStatus.UNSET and slot.value is not None
    ]
    if valued:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "budgets",
                "reason": "unset budget slots must not carry invented numeric values (FTR-07)",
                "valued_while_unset": valued,
            },
        )
    return Ok(False)


def _mark_mapping(mark: SeatMarkResult) -> dict[str, object]:
    return {
        "seat_count": mark.seat_count,
        "wall_time_ns": mark.wall_time_ns,
        "peak_rss_bytes": mark.peak_rss_bytes,
        "rungs": [
            {
                "rung": sample.rung.value,
                "wall_time_ns": sample.wall_time_ns,
                "peak_rss_bytes": sample.peak_rss_bytes,
            }
            for sample in mark.rungs
        ],
        "queue": {
            "enqueue_count": mark.queue.enqueue_count,
            "admit_count": mark.queue.admit_count,
            "protective_priority_waits": mark.queue.protective_priority_waits,
            "local_queue_bound_refusals": mark.queue.local_queue_bound_refusals,
            "max_pending_depth": mark.queue.max_pending_depth,
            "accumulator_overflow_events": mark.queue.accumulator_overflow_events,
            "backpressure_observed": mark.queue.backpressure_observed,
        },
        "conformance_double_kind": mark.conformance_double_kind,
        "slices_driven": mark.slices_driven,
    }


def _budget_mapping(slot: BudgetSlot) -> dict[str, object]:
    return {
        "name": slot.name,
        "status": slot.status.value,
        "value": slot.value,
        "unit": slot.unit,
        "gate_enforced": slot.gate_enforced,
    }
