"""Benchmark-harness slot for `qmf.venue` (AR-22 / NFR-04).

Measures wall-clock speed and peak memory at a package-native load ladder
(10 / 100 / 200 marks, sized around the ~40-bot reference scenario). The harness
carries the same status as unit tests, so a test exercises it every run; its
first real measurements become the fingerprinted (OS, CPU-class) baselines
recorded in later stories. The workload is a deliberate placeholder, replaced by
real package operations as `qmf.venue` gains primitives. Stdlib only.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass

MODULE = "qmf.venue"
DEFAULT_LADDER: tuple[int, ...] = (10, 100, 200)


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
    start = time.perf_counter()  # ambient-scan: allow - AR-22 benchmark wall-clock
    _workload(load)
    seconds = time.perf_counter() - start  # ambient-scan: allow - AR-22 benchmark wall-clock
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return BenchResult(module=MODULE, load=load, seconds=seconds, peak_bytes=peak_bytes)


def run(ladder: tuple[int, ...] = DEFAULT_LADDER) -> list[BenchResult]:
    """Run the load ladder and return one `BenchResult` per mark."""
    return [_measure(load) for load in ladder]
