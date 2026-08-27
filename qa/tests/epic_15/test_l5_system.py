"""L5 end-to-end with REAL OS processes: process-per-run isolation, one-writer-
per-stream across processes, and kill-one-not-siblings.

These behaviours cannot exist without a real OS process, so they live here and
nowhere lower (one behaviour, one level).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from _e15 import config, lines_for_role, make_ledger, ok, slices
from qmb.ledger import ROLE_ABORTED, ROLE_CONFIRMATION
from qmb.orchestrator import (
    SpawnJob,
    abort_run,
    finish_run,
    run_directory_name,
    spawn_concurrent,
    spawn_governed,
    spawn_run,
    start_run,
)
from qmb.orchestrator.watch import ABORT_KILLS_SIBLINGS
from qmf.core.refusal import is_ok, is_refusal


# -- T-15.1-a [R1] real stdlib spawn, isolated dir named by run id -----------
def test_real_spawn_separate_process_and_named_output_dir(tmp_path):
    """Submitting a run starts a SEPARATE OS process (worker pid != orchestrator
    pid) whose output directory exists and is named by the run id.

    Counter-case that FAILS: the run executing in-process (same pid), or an output
    directory not keyed by the run id.
    """
    out = tmp_path / "out"
    out.mkdir()
    cfg = config("real-a")
    isolated = ok(spawn_run(config=cfg, slices=slices(), output_root=out))
    assert isolated.worker_pid != os.getpid(), "the run executes in a separate OS process"
    assert isolated.worker_pid > 0
    run_dir = Path(isolated.output_dir)
    assert run_dir.is_dir(), "the isolated output directory exists"
    assert run_dir.name == ok(run_directory_name(cfg.fingerprint)), "the directory is named by the run id"


# -- T-15.1-e [R4] one-writer-per-stream across real concurrent processes -----
def test_concurrent_real_processes_never_share_a_writer(tmp_path):
    """Two runs executing as real concurrent processes never share an output
    directory or a per-run log file; each holds distinct paths and a distinct pid.

    Counter-case that FAILS: two runs sharing an output directory or a log file
    (a shared writer for a stream), or an identical worker pid.
    """
    out = tmp_path / "out"
    out.mkdir()
    jobs = [SpawnJob(config=config("real-p"), slices=slices()),
            SpawnJob(config=config("real-q"), slices=slices())]
    results = ok(spawn_concurrent(jobs, output_root=out))
    assert len(results) == 2
    dir_a, dir_b = Path(results[0].output_dir), Path(results[1].output_dir)
    assert dir_a != dir_b, "concurrent runs never share an output directory"
    assert results[0].worker_pid != results[1].worker_pid, "each run is its own process"
    log_a, log_b = dir_a / "run.log", dir_b / "run.log"
    assert log_a.is_file() and log_b.is_file(), "each run streams its own operational log"
    assert log_a != log_b, "no two live runs share a log writer"


# -- FC-04 [R13, R-010] partial spawn cleanup is never silently absent -------
@pytest.mark.parametrize("governed", [False, True], ids=["concurrent", "governed"])
def test_partial_spawn_failure_ledgers_each_reaped_run_once(tmp_path, governed):
    """When run k fails to start, every already-started run is reaped and gets
    exactly one aborted ledger line; the failed and never-attempted runs get none.

    Counter-case that FAILS: cleanup kills an already-started process without a
    durable line, or falsely ledgers a run for which no process was ever started.
    """
    out = tmp_path / "out"
    out.mkdir()
    led = tmp_path / "led"
    led.mkdir()
    started = config("partial-started")
    fails_to_start = config("partial-refused")
    never_started = config("partial-never-started")

    refused_name = ok(run_directory_name(fails_to_start.fingerprint))
    (out / refused_name).mkdir()
    jobs = (
        SpawnJob(config=started, slices=slices(), projected_peak_memory=1),
        SpawnJob(config=fails_to_start, slices=slices(), projected_peak_memory=1),
        SpawnJob(config=never_started, slices=slices(), projected_peak_memory=1),
    )
    if governed:
        result = spawn_governed(
            jobs,
            output_root=out,
            cpu_budget=3,
            memory_budget=3,
            ledger=make_ledger(led),
        )
    else:
        result = spawn_concurrent(jobs, output_root=out, ledger=make_ledger(led))

    assert is_refusal(result), "run k's start refusal is returned"
    aborted = lines_for_role(led, ROLE_ABORTED)
    assert [line.run_id for line in aborted] == [started.fingerprint]
    assert aborted[0].refusal is not None
    assert aborted[0].refusal.get("cause") == "reaped/abandoned"


# -- T-15.3-e [R11] kill-one-not-siblings -----------------------------------
def test_abort_kills_only_its_own_process_siblings_survive(tmp_path):
    """Aborting one run terminates only that PID; a sibling process is untouched
    and completes, and each surviving run ledgers exactly one line.

    Counter-case that FAILS: an abort that also kills the sibling, or a refusal
    claiming sibling processes were touched.
    """
    out = tmp_path / "out"
    out.mkdir()
    cfg_victim = config("victim")
    cfg_survivor = config("survivor")
    victim = ok(start_run(config=cfg_victim, slices=slices(), output_root=out))
    survivor = ok(start_run(config=cfg_survivor, slices=slices(), output_root=out))

    refusal = abort_run(victim, cause="cancel")
    assert refusal.context.get("sibling_processes_touched") == ABORT_KILLS_SIBLINGS is False
    assert refusal.context.get("killed_os_process") is True
    assert refusal.context.get("pid") == victim.pid

    # The sibling was not signalled: it completes and ledgers exactly one line.
    led = tmp_path / "led"
    led.mkdir()
    collected = finish_run(survivor, config=cfg_survivor, ledger=make_ledger(led), role=ROLE_CONFIRMATION)
    assert is_ok(collected), "the sibling process survived the abort and completed"
    assert collected.value.worker_pid != victim.pid
