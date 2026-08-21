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


def test_import_completes_well_under_one_second() -> None:
    elapsed = _bench.import_time_budget_seconds()
    assert elapsed < _bench.IMPORT_BUDGET_SECONDS
