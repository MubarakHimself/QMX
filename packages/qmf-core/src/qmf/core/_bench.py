"""Benchmark-harness slot for `qmf.core` (AR-22 / NFR-04).

Two measurements ship with the same status as unit tests, so a test exercises
them every run:

* a package-native load ladder (10 / 100 / 200 marks, sized around the ~40-bot
  reference scenario) that exercises **real `qmf.core` operations** — exact-value
  construction (`Money.try_create`), scale-promoting arithmetic (`add`/
  `subtract`), and `fp1` fingerprinting — measuring wall-clock speed and peak
  memory. The workload calls into the package it benchmarks, not a bare arithmetic
  loop, so the numbers track `qmf.core` itself.
* the import-time budget — `qmf.core` must import well under one second
  (`IMPORT_BUDGET_SECONDS`), the one performance constraint the architecture
  states now (NFR-04). It is measured as the cost of importing `qmf.core`
  **itself**, isolated from full interpreter cold-start: a fresh interpreter runs
  `-X importtime -c "import qmf.core"`, and the cumulative time CPython attributes
  to the `qmf.core` import is read back — the minimum of several runs, which tames
  scheduler jitter without inventing a number. (A plain wall-clock around the
  subprocess would fold interpreter startup into the figure; `-X importtime`
  attributes it to the import alone.)

First real measurements become the fingerprinted (OS, CPU-class) baselines
recorded in later stories. Stdlib only (the workload calls into `qmf.core`, which
itself takes zero outside dependencies).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

from qmf.core.exact import Money
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import is_ok

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
    """Exercise real `qmf.core` operations so the ladder measures the package.

    For each mark: construct an exact :class:`~qmf.core.exact.Money` value
    (`try_create`), combine it with scale-promoting arithmetic (`add`/`subtract`),
    and fingerprint the result (`fp1`) — the CT-01 / CT-05 hot paths. Returns the
    count of values that fingerprinted, so the loop's work cannot be optimized away.
    """
    fingerprinted = 0
    for i in range(load):
        made = Money.try_create(i, "USD", 2)
        if not is_ok(made):
            continue
        amount = made.value
        doubled = amount.add(amount)
        if is_ok(doubled):
            amount = doubled.value
        reduced = amount.subtract(made.value)
        if is_ok(reduced):
            amount = reduced.value
        if is_ok(fingerprint(amount)):
            fingerprinted += 1
    return fingerprinted


def _measure(load: int) -> BenchResult:
    tracemalloc.start()
    start = time.perf_counter()  # ambient-scan: allow - AR-22 benchmark wall-clock
    _workload(load)
    seconds = time.perf_counter() - start  # ambient-scan: allow - AR-22 benchmark wall-clock
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return BenchResult(module=MODULE, load=load, seconds=seconds, peak_bytes=peak_bytes)


def run(ladder: tuple[int, ...] = DEFAULT_LADDER) -> list[BenchResult]:
    """Run the load ladder and return one `BenchResult` per mark."""
    return [_measure(load) for load in ladder]


def cumulative_import_seconds(importtime_stderr: str) -> float:
    """Parse `-X importtime` stderr and return the cumulative seconds of the
    `qmf.core` row.

    Each data line is ``import time: <self_us> | <cumulative_us> | <name>``; the
    cumulative column of the `qmf.core` row is its whole import cost — the package
    and everything it pulls in. Microseconds convert to seconds. A missing row
    (module already imported in the child) reads as ``0.0``.
    """
    for line in importtime_stderr.splitlines():
        if not line.startswith("import time:"):
            continue
        parts = line.split("|")
        if len(parts) == 3 and parts[2].strip() == MODULE:
            return int(parts[1].strip()) / 1_000_000
    return 0.0


def _import_time_once(env: dict[str, str]) -> float:
    """One `-X importtime` measurement: the cumulative seconds CPython attributes to
    the `qmf.core` import in a fresh interpreter."""
    # Fixed argv, absolute sys.executable, no shell — a benign subprocess.
    proc = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", f"import {MODULE}"],
        capture_output=True,
        check=True,
        env=env,
        text=True,
    )
    return cumulative_import_seconds(proc.stderr)


def import_time_budget_seconds(runs: int = 3) -> float:
    """Cold-import cost of `qmf.core` itself, the minimum of `runs` fresh-interpreter
    `-X importtime` measurements. Compare against `IMPORT_BUDGET_SECONDS`.

    The figure is the time CPython attributes to importing `qmf.core` (and the
    modules it pulls in), not a full interpreter cold start — the budget is about
    the package's own import weight (NFR-04).
    """
    existing = os.environ.get("PYTHONPATH", "")
    child_path = os.pathsep.join([str(_SRC_ROOT), existing]) if existing else str(_SRC_ROOT)
    env = {**os.environ, "PYTHONPATH": child_path}
    best = float("inf")
    for _ in range(runs):
        best = min(best, _import_time_once(env))
    return best
