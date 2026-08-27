"""L5 concurrency isolation of assembly/render (R28).

12-14 concurrent assembly tasks each write their own artifact into their own
output directory with no shared mutable render state and no cross-run contention:
every artifact is independent and each fp1 is stable and equal to its
single-threaded value.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from conftest import config, mint_args, ok

from qmb.results.ct32 import assemble_run_performance_result, mint_run_performance_result

N = 14


def _fp_for(streams: tuple[str, ...]) -> str:
    cfg = config(streams=streams)
    artifact = ok(mint_run_performance_result(**mint_args(cfg, stream_order=streams)))
    return ok(artifact.fingerprint()).value


def test_concurrent_assembly_is_isolated_and_deterministic(tmp_path: Path) -> None:
    stream_sets = [(f"sym{i:02d}",) for i in range(N)]
    # single-threaded baseline fingerprints
    baseline = {s: _fp_for(s) for s in stream_sets}

    def task(index: int) -> tuple[tuple[str, ...], str, bool]:
        streams = stream_sets[index]
        cfg = config(streams=streams)
        artifact = ok(mint_run_performance_result(**mint_args(cfg, stream_order=streams)))
        run_dir = tmp_path / f"run-{index:02d}"
        run_dir.mkdir()
        stamped = ok(assemble_run_performance_result(artifact, output_dir=run_dir))
        wrote = (run_dir / "results" / "ct-32.json").is_file()
        return streams, stamped.value, wrote

    with ThreadPoolExecutor(max_workers=N) as pool:
        results = list(pool.map(task, range(N)))

    seen: dict[tuple[str, ...], str] = {}
    for streams, fp, wrote in results:
        assert wrote, streams
        # concurrency did not corrupt identity — matches the single-threaded value
        assert fp == baseline[streams], streams
        seen[streams] = fp
    # every run produced a distinct artifact (no cross-run contention/aliasing)
    assert len(set(seen.values())) == N


def test_same_config_across_threads_yields_one_fingerprint() -> None:
    streams = ("eurusd", "gbpusd")

    def compute() -> str:
        return _fp_for(streams)

    with ThreadPoolExecutor(max_workers=8) as pool:
        fps = list(pool.map(lambda _: compute(), range(24)))
    # no shared mutable render state => identical inputs give one stable fingerprint
    assert len(set(fps)) == 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
