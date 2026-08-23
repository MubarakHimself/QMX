"""Benchmark harness for `qmf.structure` (AR-22 / NFR-04; CT-17 DEC-0129, DEC-0111).

Measures wall-clock speed and peak memory at the **three CT-17 structure rungs** —
active object-set size, objects minted per bar, and interaction records per bar — across a
package-native load ladder (10 / 100 / 200 marks, sized around the ~40-bot reference
scenario). The harness carries the **same standing as the unit tests**, so a test exercises
it every run; its first real measurements become the fingerprinted (OS, CPU-class) baselines
recorded in later stories. Unlike a placeholder workload, each rung drives **real**
``qmf.structure`` operations: minting objects, holding a live object set, and appending
interaction records.

The light/heavy verdict and the regression gate that police these measurements live in
:mod:`qmf.structure.budget`; this module only produces the measurements. Stdlib plus
qmf-core / qmf-structure only.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass
from typing import TypeVar

from qmf.core import (
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Price,
    Result,
    UnitKind,
    VenueId,
    is_ok,
)
from qmf.structure.budget import BenchmarkRung
from qmf.structure.lifecycle import InteractionRecord
from qmf.structure.objects import (
    AnchorSpan,
    ConfirmationRule,
    DeclaredFamily,
    FamilyIdentity,
    StructureObject,
)

MODULE = "qmf.structure"
DEFAULT_LADDER: tuple[int, ...] = (10, 100, 200)
_BASE_NS = 1_700_000_000_000_000_000
_STEP_NS = 60_000_000_000

_T = TypeVar("_T")


@dataclass(frozen=True)
class BenchResult:
    """One measurement taken at a single (rung, load) mark."""

    module: str
    rung: BenchmarkRung
    load: int
    seconds: float
    peak_bytes: int


def _unwrap(result: Result[_T], what: str) -> _T:
    """Unwrap a benchmark construction that must succeed, or fail loudly (harness only)."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"benchmark setup: expected {what} to construct, got {result}")


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _price(value: int) -> Price:
    return _unwrap(Price.try_create(value, _instrument(), 5), "price")


def _family() -> DeclaredFamily:
    identity = _unwrap(FamilyIdentity.try_create("swing-point", 1, "point"), "identity")
    rule = _unwrap(
        ConfirmationRule.try_create(
            "confirmed the moment a later bar closes beyond the pivot", confirmation_delay_bound=3
        ),
        "rule",
    )
    return _unwrap(DeclaredFamily.try_create(identity, rule), "family")


def _parameters() -> dict[str, ExactRational]:
    ratio = _unwrap(ExactRational.try_create(1, 4, UnitKind.DIMENSIONLESS_RATIO), "ratio")
    return {"tolerance": ratio}


def _mint(index: int) -> StructureObject:
    start = Instant(value_ns=_BASE_NS + index * _STEP_NS)
    anchor = _unwrap(
        AnchorSpan.try_create(start, start, _price(108_000 + index), _price(108_000 + index)),
        "anchor",
    )
    return _unwrap(
        StructureObject.try_create(
            _family(),
            _parameters(),
            anchor,
            Instant(value_ns=_BASE_NS + (index + 1) * _STEP_NS),
            EvidenceClass.UNCONFIRMED,
        ),
        "object",
    )


def _minted_fingerprint() -> Fingerprint:
    return _unwrap(_mint(0).content_fingerprint(), "fingerprint")


def _run_active_object_set(load: int) -> None:
    """Hold `load` minted objects live at once — the active object-set-size rung."""
    live = [_mint(index) for index in range(load)]
    if len(live) != load:  # pragma: no cover - the comprehension always yields `load` objects
        raise AssertionError("active object-set-size workload built the wrong count")


def _run_objects_minted_per_bar(load: int) -> None:
    """Mint `load` objects — the objects-minted-per-bar rung."""
    for index in range(load):
        _mint(index)


def _run_interaction_records_per_bar(load: int) -> None:
    """Append `load` interaction records to one object — the interaction-records-per-bar rung."""
    ref = _minted_fingerprint()
    for index in range(load):
        _unwrap(
            InteractionRecord.try_create(
                ref,
                Instant(value_ns=_BASE_NS + index * _STEP_NS),
                _price(108_500),
                "touch",
                _unwrap(ExactRational.try_create(index, 1, UnitKind.DIMENSIONLESS_RATIO), "mag"),
            ),
            "interaction record",
        )


_RUNGS = {
    BenchmarkRung.ACTIVE_OBJECT_SET_SIZE: _run_active_object_set,
    BenchmarkRung.OBJECTS_MINTED_PER_BAR: _run_objects_minted_per_bar,
    BenchmarkRung.INTERACTION_RECORDS_PER_BAR: _run_interaction_records_per_bar,
}


def _measure(rung: BenchmarkRung, load: int) -> BenchResult:
    workload = _RUNGS[rung]
    tracemalloc.start()
    start = time.perf_counter()  # ambient-scan: allow - AR-22 benchmark wall-clock
    workload(load)
    seconds = time.perf_counter() - start  # ambient-scan: allow - AR-22 benchmark wall-clock
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return BenchResult(module=MODULE, rung=rung, load=load, seconds=seconds, peak_bytes=peak_bytes)


def run(ladder: tuple[int, ...] = DEFAULT_LADDER) -> list[BenchResult]:
    """Run every rung across the load ladder and return one `BenchResult` per (rung, load)."""
    return [_measure(rung, load) for rung in BenchmarkRung for load in ladder]
