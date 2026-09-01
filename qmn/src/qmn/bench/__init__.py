"""Hot-path benchmark harness (TN-23 / Story 25.15).

Test-status portable harness measuring wall-clock and peak RSS across the
four-point seat sweep. Unmeasured limits are unset evidence — never invented
numeric latency gates (FTR-07). Story 28.7 owns first-hours VPS baselines.
"""

from __future__ import annotations

from typing import Final

from qmn.bench.harness import (
    MODULE,
    collect_provenance,
    peak_rss_bytes,
    run,
    run_seat_mark,
)
from qmn.bench.schema import (
    BUDGET_SLOT_NAMES,
    DESIGN_BOT_CONCURRENCY_REFERENCE,
    HOT_PATH_RUNGS,
    SEAT_LADDER,
    VARIANCE_METHOD,
    VARIANCE_METHOD_DESCRIPTION,
    WATCHED_LATENCY_TARGET_IS_GATE,
    BaselineEligibility,
    BenchLifecycle,
    BudgetSlot,
    BudgetStatus,
    DeploymentProvenance,
    HarnessReport,
    HotPathRung,
    QueueBehaviorSample,
    RungSample,
    SeatMarkResult,
    VarianceMethod,
    baseline_eligible,
    budget_slots_unset,
    gate_may_enforce,
)

__all__ = [
    "BENCH_SURFACE",
    "BUDGET_SLOT_NAMES",
    "DESIGN_BOT_CONCURRENCY_REFERENCE",
    "HOT_PATH_RUNGS",
    "MODULE",
    "SEAT_LADDER",
    "VARIANCE_METHOD",
    "VARIANCE_METHOD_DESCRIPTION",
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
    "collect_provenance",
    "gate_may_enforce",
    "peak_rss_bytes",
    "run",
    "run_seat_mark",
]

BENCH_SURFACE: Final[str] = "qmn.bench"
