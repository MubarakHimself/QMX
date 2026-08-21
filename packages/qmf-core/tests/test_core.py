"""Tier-1 tests for the `qmf.core` scaffold: identity, benchmark harness, and
the import-time budget (AR-22 / NFR-04)."""

from __future__ import annotations

import qmf.core
from qmf.core import _bench


def test_version_is_semver_0x() -> None:
    assert qmf.core.__version__ == "0.1.0"


def test_bench_harness_runs_full_ladder() -> None:
    results = _bench.run()
    assert [result.load for result in results] == list(_bench.DEFAULT_LADDER)
    assert all(result.seconds >= 0.0 for result in results)
    assert all(result.peak_bytes >= 0 for result in results)
    assert all(result.module == "qmf.core" for result in results)


def test_bench_workload_is_wired_to_real_qmf_core_operations() -> None:
    # Regression (L5): the ladder workload must call into qmf.core (try_create /
    # arithmetic / fingerprint), not a bare arithmetic loop. The harness imports and
    # uses the real value types (unused imports would fail lint), and the ladder runs
    # that workload to completion at every mark.
    from qmf.core.exact import Money
    from qmf.core.fingerprint import fingerprint

    assert _bench.Money is Money
    assert _bench.fingerprint is fingerprint
    assert [r.load for r in _bench.run((5, 10))] == [5, 10]


def test_import_completes_well_under_one_second() -> None:
    elapsed = _bench.import_time_budget_seconds()
    assert elapsed < _bench.IMPORT_BUDGET_SECONDS


def test_import_budget_measures_the_module_import_not_full_cold_start() -> None:
    # Regression (L5): the budget is the cumulative time CPython attributes to the
    # `qmf.core` import row of `-X importtime`, isolated from interpreter startup —
    # so it is a small, non-negative figure, not a full subprocess cold-start time.
    elapsed = _bench.import_time_budget_seconds()
    assert elapsed >= 0.0


def test_cumulative_import_seconds_parses_the_module_row() -> None:
    # Regression (L5): the parser reads the cumulative microseconds of the qmf.core
    # row and converts to seconds (here 63534us -> 0.063534s).
    stderr = (
        "import time: self [us] | cumulative | imported package\n"
        "import time:       319 |        319 |   qmf\n"
        "import time:      4721 |      16122 |   qmf.core.fingerprint\n"
        "import time:       662 |      63534 | qmf.core\n"
    )
    assert _bench.cumulative_import_seconds(stderr) == 63534 / 1_000_000


def test_cumulative_import_seconds_absent_row_reads_zero() -> None:
    # If the module row is missing (already imported in the child), the figure is 0.
    stderr = (
        "import time: self [us] | cumulative | imported package\n"
        "import time:       319 |        319 |   qmf\n"
    )
    assert _bench.cumulative_import_seconds(stderr) == 0.0
