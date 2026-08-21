"""Tier-1 tests for the `qmf.indicators` scaffold: identity and benchmark harness."""

from __future__ import annotations

import qmf.indicators
from qmf.indicators import _bench


def test_version_is_semver_0x() -> None:
    assert qmf.indicators.__version__ == "0.1.0"


def test_bench_harness_runs_full_ladder() -> None:
    results = _bench.run()
    assert [result.load for result in results] == list(_bench.DEFAULT_LADDER)
    assert all(result.seconds >= 0.0 for result in results)
    assert all(result.peak_bytes >= 0 for result in results)
    assert all(result.module == "qmf.indicators" for result in results)
