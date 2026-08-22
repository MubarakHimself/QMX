"""Benchmark-harness slot for `qmf.calendar_forex` (AR-22 / NFR-04).

Measures wall-clock speed and peak memory at a package-native load ladder
(10 / 100 / 200 marks, sized around the ~40-bot reference scenario). The harness
carries the same status as unit tests, so a test exercises it every run; its
first real measurements become the fingerprinted (OS, CPU-class) baselines
recorded in later stories. Workload is trading-date and session-window lookups
over a fixed Instant ladder. Stdlib only beyond the calendar provider.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass

from qmf.calendar_forex._provider import Forex17NYCalendar
from qmf.core.chrono import Instant
from qmf.core.refusal import is_ok

MODULE = "qmf.calendar_forex"
DEFAULT_LADDER: tuple[int, ...] = (10, 100, 200)

# Fixed probe: 2026-08-19 12:00:00 UTC ≈ mid-session Wednesday under 17NY.
_PROBE_NS: int = 1_787_140_800_000_000_000


@dataclass(frozen=True)
class BenchResult:
    """One measurement taken at a single load mark."""

    module: str
    load: int
    seconds: float
    peak_bytes: int


def _workload(load: int, calendar: Forex17NYCalendar) -> int:
    instant = Instant(value_ns=_PROBE_NS)
    total = 0
    for i in range(load):
        day = calendar.trading_date_of(instant)
        window = calendar.session_window(instant)
        if is_ok(day):
            total += day.value.date_value.day
        if is_ok(window) and window.value is not None:
            total += window.value.open_instant.value_ns % 97
        total += i % 3
    return total


def _measure(load: int, calendar: Forex17NYCalendar) -> BenchResult:
    tracemalloc.start()
    start = time.perf_counter()  # ambient-scan: allow - AR-22 benchmark wall-clock
    _workload(load, calendar)
    seconds = time.perf_counter() - start  # ambient-scan: allow - AR-22 benchmark wall-clock
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return BenchResult(module=MODULE, load=load, seconds=seconds, peak_bytes=peak_bytes)


def run(
    ladder: tuple[int, ...] = DEFAULT_LADDER,
    *,
    calendar: Forex17NYCalendar,
) -> list[BenchResult]:
    """Run the load ladder and return one `BenchResult` per mark."""
    return [_measure(load, calendar) for load in ladder]
