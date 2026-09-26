"""Reference usage — process-per-run spawn with isolated output directories.

Executable::

    python qmb/examples/orchestrator_spawn_usage.py

Shows the things Story 15.1 / AR-50 / B-5 pin down:

1. The orchestrator spawns each run as a separate OS process via stdlib
   process management, with an isolated output directory named by the run id.
2. The library ``run()`` stays pure: no log, no ledger, no threads, no processes.
3. No Ray, no required Docker, and no daemon.
4. Two concurrent runs never share a writer for any file or stream.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.orchestrator import (
    DAEMON,
    DOCKER,
    PROCESS_MANAGEMENT,
    RAY,
    SPAWN_MODEL,
    WRITER_NAME,
    orchestrator_identity,
    run_directory_name,
    spawn_concurrent,
    spawn_run,
)
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Result, is_ok

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _unwrap(SliceObservation.try_create(stream_id, _instant(ns), True), "observation")


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return (
        (_obs("eurusd"), _obs("gbpusd")),
        (_obs("eurusd", _NS + 1), _obs("gbpusd", _NS + 1)),
    )


def _config(tag: str) -> ResolvedRunConfig:
    stamp = _unwrap(fingerprint({"n": "orch-example", "tag": tag}), "stamp")
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd", "gbpusd")},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def identity_is_stdlib_process_per_run() -> None:
    identity = orchestrator_identity()
    assert identity["spawn_model"] == SPAWN_MODEL == "process-per-run"
    assert identity["process_management"] == PROCESS_MANAGEMENT == "stdlib.subprocess"
    assert identity["ray"] == RAY == "absent"
    assert identity["docker"] == DOCKER == "not-required"
    assert identity["daemon"] == DAEMON == "not-required"
    assert identity["one_writer_per_stream"] is True


def run_stays_pure() -> None:
    config = _config("pure")
    slices = _slices()
    first = _unwrap(run(slices=slices, config=config, handler=SilentSliceHandler()), "a")
    second = _unwrap(run(slices=slices, config=config, handler=SilentSliceHandler()), "b")
    assert first.fp1_identity() == second.fp1_identity()


def spawned_process_matches_pure_run(output_root: Path) -> None:
    config = _config("one")
    slices = _slices()
    in_process = _unwrap(run(slices=slices, config=config, handler=SilentSliceHandler()), "pure")
    isolated = _unwrap(
        spawn_run(config=config, slices=slices, output_root=output_root),
        "spawn",
    )
    named = _unwrap(run_directory_name(config.fingerprint), "dir")
    assert Path(isolated.output_dir).name == named
    assert ":" not in named
    assert isolated.pid != os.getpid()
    assert isolated.outcome_identity == in_process.fp1_identity()
    assert isolated.ct32_fingerprint == _unwrap(in_process.ct32_fingerprint(), "ct32")


def concurrent_runs_never_share_a_writer(output_root: Path) -> None:
    slices = _slices()
    first = _config("alpha")
    second = _config("beta")
    isolated = _unwrap(
        spawn_concurrent(
            ({"config": first, "slices": slices}, {"config": second, "slices": slices}),
            output_root=output_root,
        ),
        "batch",
    )
    assert isolated[0].pid != isolated[1].pid
    assert isolated[0].output_dir != isolated[1].output_dir
    writer_a = Path(isolated[0].output_dir) / WRITER_NAME
    writer_b = Path(isolated[1].output_dir) / WRITER_NAME
    assert writer_a.is_file()
    assert writer_b.is_file()
    assert writer_a.resolve() != writer_b.resolve()


def main() -> None:
    assert qmb.SPAWN_MODEL == SPAWN_MODEL
    assert qmb.spawn_run is spawn_run
    identity_is_stdlib_process_per_run()
    print("process-per-run via stdlib subprocess")
    run_stays_pure()
    print("run is pure")
    with tempfile.TemporaryDirectory(prefix="qmb_orch_", ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        spawned_process_matches_pure_run(root)
        print("isolated output directory named by the run id")
        concurrent_runs_never_share_a_writer(root)
        print("one-writer-per-stream")
    print("no Ray, no required Docker, no daemon")
    print("process-per-run ok")


if __name__ == "__main__":
    main()
