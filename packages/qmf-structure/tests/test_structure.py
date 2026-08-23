"""Tier-1 tests for the `qmf.structure` scaffold: identity and benchmark harness."""

from __future__ import annotations

import qmf.structure
from qmf.structure import _bench
from qmf.structure.budget import BenchmarkRung


def test_version_is_semver_0x() -> None:
    assert qmf.structure.__version__ == "0.1.0"


def test_bench_harness_runs_every_rung_across_the_full_ladder() -> None:
    results = _bench.run()
    # One measurement per (rung, load) — the three CT-17 structure rungs across the ladder.
    assert len(results) == len(BenchmarkRung) * len(_bench.DEFAULT_LADDER)
    for rung in BenchmarkRung:
        loads = [result.load for result in results if result.rung is rung]
        assert loads == list(_bench.DEFAULT_LADDER)
    assert all(result.seconds >= 0.0 for result in results)
    assert all(result.peak_bytes >= 0 for result in results)
    assert all(result.module == "qmf.structure" for result in results)


def test_bench_rungs_are_the_three_structure_rungs() -> None:
    assert {rung.value for rung in BenchmarkRung} == {
        "active-object-set-size",
        "objects-minted-per-bar",
        "interaction-records-per-bar",
    }
