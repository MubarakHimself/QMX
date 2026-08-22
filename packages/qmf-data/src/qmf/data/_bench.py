"""Benchmark harness for `qmf.data` — a package-native append/read ladder (AR-22 / NFR-04).

Measures wall-clock speed and peak memory of the store seam at a load ladder
(10 / 100 / 200 marks, sized around the ~40-bot reference scenario). Each mark builds
a fresh :class:`~qmf.data.store.EvidenceStore` in a throwaway directory, **appends** N
fp1-keyed journal events through the CT-13 boundary (the append leg), then **reads**
them all back through the same boundary (the read leg) — so the harness exercises the
real engines (JSONL fsync + rotation, the identity guard), not a placeholder loop.

The harness carries the same status as unit tests, so a test exercises it every run;
its first real measurements become the fingerprinted (OS, CPU-class) baselines recorded
in later stories. Stdlib + qmf-core + the store; the two ``perf_counter`` reads are the
sanctioned measurement-harness reads (AR-22), marked for the ambient-nondeterminism gate.
"""

from __future__ import annotations

import tempfile
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

from qmf.core import World, WriterId, is_ok
from qmf.data.store import EvidenceStore

MODULE = "qmf.data"
DEFAULT_LADDER: tuple[int, ...] = (10, 100, 200)


@dataclass(frozen=True)
class BenchResult:
    """One measurement taken at a single load mark."""

    module: str
    load: int
    seconds: float
    peak_bytes: int


def _writer() -> WriterId:
    """The one benchmark writer (a construction, never an ambient read)."""
    built = WriterId.try_create("bench-node", "data", "bench", "boot-bench")
    if not is_ok(built):  # pragma: no cover - constant inputs always construct
        raise RuntimeError("benchmark writer failed to construct")
    return built.value


def _append_read(store: EvidenceStore, writer: WriterId, load: int) -> None:
    """Append ``load`` journal events, then read them all back (the ladder step)."""
    world = store.for_world(World.LIVE)
    if not is_ok(world):  # pragma: no cover - live always resolves
        raise RuntimeError("benchmark could not open the live world store")
    journal = world.value.journal
    for index in range(load):
        result = journal.append("bench", writer, {"event_type": "data quality", "n": index})
        if not is_ok(result):  # pragma: no cover - the bench path never refuses
            raise RuntimeError(f"benchmark append refused at {index}: {result}")
    read = journal.read_stream("bench", for_world=World.LIVE)
    if not is_ok(read) or len(read.value) != load:  # pragma: no cover - read matches appends
        raise RuntimeError("benchmark read did not return every appended event")


def _measure(load: int) -> BenchResult:
    writer = _writer()
    with tempfile.TemporaryDirectory(prefix="qmf-data-bench-") as tmp:
        store = EvidenceStore(Path(tmp))
        tracemalloc.start()
        start = time.perf_counter()  # ambient-scan: allow - AR-22 benchmark wall-clock
        _append_read(store, writer, load)
        seconds = time.perf_counter() - start  # ambient-scan: allow - AR-22 benchmark wall-clock
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return BenchResult(module=MODULE, load=load, seconds=seconds, peak_bytes=peak_bytes)


def run(ladder: tuple[int, ...] = DEFAULT_LADDER) -> list[BenchResult]:
    """Run the load ladder and return one `BenchResult` per mark."""
    return [_measure(load) for load in ladder]
