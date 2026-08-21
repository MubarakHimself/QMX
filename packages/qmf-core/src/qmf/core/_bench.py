"""Benchmark-harness slot for `qmf.core` (AR-22 / NFR-04).

Two measurements ship with the same status as unit tests, so a test exercises
them every run:

* a package-native load ladder (10 / 100 / 200 marks, sized around the ~40-bot
  reference scenario) measuring wall-clock speed and peak memory; and
* the import-time budget — `qmf.core` must import well under one second
  (`IMPORT_BUDGET_SECONDS`), the one performance constraint the architecture
  states now (NFR-04). It is measured by cold-importing `qmf.core` in a fresh
  interpreter and taking the minimum of several runs, which tames scheduler
  jitter without inventing a number.

First real measurements become the fingerprinted (OS, CPU-class) baselines
recorded in later stories. The load-ladder workload is a deliberate placeholder,
replaced by real primitives as `qmf.core` grows. Stdlib only.
"""

from __future__ import annotations

# ambient-scan: allow — benchmark harness; measures real wall-clock speed and import
# time (AR-22 / NFR-04), so its time.perf_counter() reads are the sanctioned
# exception to FR-002 (no system-clock reads below the composition root) for this file.
import os
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

MODULE = "qmf.core"
DEFAULT_LADDER: tuple[int, ...] = (10, 100, 200)
IMPORT_BUDGET_SECONDS: float = 1.0

# .../packages/qmf-core/src — the fresh interpreter used for the import-time
# budget is pointed here so it resolves `qmf.core` whether or not the package is
# installed. `qmf.core` takes zero outside dependencies, so its src root plus the
# stdlib is the entire import surface.
_SRC_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class BenchResult:
    """One measurement taken at a single load mark."""

    module: str
    load: int
    seconds: float
    peak_bytes: int


def _workload(load: int) -> int:
    total = 0
    for i in range(load):
        total += sum(range(i % 64))
    return total


def _measure(load: int) -> BenchResult:
    tracemalloc.start()
    start = time.perf_counter()
    _workload(load)
    seconds = time.perf_counter() - start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return BenchResult(module=MODULE, load=load, seconds=seconds, peak_bytes=peak_bytes)


def run(ladder: tuple[int, ...] = DEFAULT_LADDER) -> list[BenchResult]:
    """Run the load ladder and return one `BenchResult` per mark."""
    return [_measure(load) for load in ladder]


def import_time_budget_seconds(runs: int = 3) -> float:
    """Cold-import wall time of `qmf.core`, the minimum of `runs` fresh-interpreter
    measurements. Compare against `IMPORT_BUDGET_SECONDS`.
    """
    existing = os.environ.get("PYTHONPATH", "")
    child_path = os.pathsep.join([str(_SRC_ROOT), existing]) if existing else str(_SRC_ROOT)
    env = {**os.environ, "PYTHONPATH": child_path}
    best = float("inf")
    for _ in range(runs):
        start = time.perf_counter()
        # Fixed argv, absolute sys.executable, no shell — a benign subprocess.
        subprocess.run(
            [sys.executable, "-c", "import qmf.core"],
            capture_output=True,
            check=True,
            env=env,
        )
        best = min(best, time.perf_counter() - start)
    return best
