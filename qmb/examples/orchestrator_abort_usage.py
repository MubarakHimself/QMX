"""Reference usage — cancel tokens and per-run limits with typed aborted refusals.

Executable::

    python qmb/examples/orchestrator_abort_usage.py

Shows the things Story 15.3 / AR-51 / B-5 / FM-6 pin down:

1. Every submitted run carries a cancel token and declared per-run limits
   ``qmb_run_time_limit`` and ``qmb_run_memory_limit`` (no spine values).
2. Limit breach or cancel is a typed ``aborted`` refusal with context.
3. Aborting one process does not touch siblings.
4. An aborted run never writes a partial governed result — output stays in
   that run's directory.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.orchestrator import (
    ABORT_KILLS_SIBLINGS,
    ENFORCEMENT,
    abort_run,
    orchestrator_identity,
    start_run,
)
from qmb.orchestrator.watch import monotonic_ns
from qmb.runloop import (
    CAUSE_CANCEL,
    CAUSE_MEMORY_LIMIT,
    CAUSE_TIME_LIMIT,
    MEMORY_LIMIT_KEY,
    PARTIAL_GOVERNED_RESULT_ON_ABORT,
    STREAM_SET_KEY,
    TERMINAL_ABORTED,
    TIME_LIMIT_KEY,
    CancelToken,
    RunLimits,
    SliceObservation,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal

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
    return ((_obs("eurusd"),), (_obs("eurusd", _NS + 1),))


def _config(tag: str) -> ResolvedRunConfig:
    stamp = _unwrap(fingerprint({"n": "orch-abort-example", "tag": tag}), "stamp")
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _hanging(output_root: Path, tag: str, *, limits: RunLimits | None = None) -> qmb.LiveSpawn:
    config = _config(tag)
    named = _unwrap(qmb.run_directory_name(config.fingerprint), "dir")
    directory = output_root / named
    directory.mkdir()
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return qmb.LiveSpawn(
        run_id=config.fingerprint,
        output_dir=str(directory),
        pid=process.pid,
        process=process,
        cancel=CancelToken(),
        limits=limits if limits is not None else RunLimits(),
        started_monotonic_ns=monotonic_ns(),
    )


def identity_names_declared_per_run_limits() -> None:
    identity = orchestrator_identity()
    assert identity["time_limit_key"] == TIME_LIMIT_KEY == "qmb_run_time_limit"
    assert identity["memory_limit_key"] == MEMORY_LIMIT_KEY == "qmb_run_memory_limit"
    assert identity["abort_kills_siblings"] is ABORT_KILLS_SIBLINGS is False
    assert identity["enforcement"] == ENFORCEMENT
    assert identity["partial_governed_result_on_abort"] is PARTIAL_GOVERNED_RESULT_ON_ABORT is False
    assert identity["cancel_token"] is True


def submitted_run_carries_token_and_limits(output_root: Path) -> None:
    token = CancelToken()
    limits = _unwrap(RunLimits.try_create(time_limit=25, memory_limit_bytes=32), "limits")
    live = _unwrap(
        start_run(
            config=_config("carry"),
            slices=_slices(),
            output_root=output_root,
            cancel=token,
            limits=limits,
        ),
        "start",
    )
    try:
        assert live.cancel is token
        assert live.limits.time_limit is not None
        assert live.limits.time_limit.value_ns == 25
        assert live.limits.memory_limit_bytes == 32
        payload = (Path(live.output_dir) / qmb.PAYLOAD_NAME).read_text(encoding="utf-8")
        assert TIME_LIMIT_KEY in payload
        assert MEMORY_LIMIT_KEY in payload
    finally:
        abort_run(live)


def cancel_and_limit_breach_are_typed_aborted(output_root: Path) -> None:
    cancelled = _hanging(output_root, "cancel")
    _unwrap(cancelled.cancel.cancel(), "signal")
    refused = qmb.collect_run(cancelled)
    assert is_refusal(refused)
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["cause"] == CAUSE_CANCEL
    assert refused.context["killed_os_process"] is True

    timed = _hanging(
        output_root,
        "time",
        limits=_unwrap(RunLimits.try_create(time_limit=1), "time limit"),
    )
    timed_out = qmb.collect_run(timed)
    assert is_refusal(timed_out)
    assert timed_out.context["cause"] == CAUSE_TIME_LIMIT

    oom = _hanging(
        output_root,
        "mem",
        limits=_unwrap(RunLimits.try_create(memory_limit_bytes=1), "memory limit"),
    )
    memory = qmb.collect_run(oom)
    assert is_refusal(memory)
    assert memory.context["cause"] == CAUSE_MEMORY_LIMIT


def abort_one_leaves_the_sibling(output_root: Path) -> None:
    victim = _hanging(output_root, "victim")
    sibling = _unwrap(
        start_run(config=_config("sibling"), slices=_slices(), output_root=output_root),
        "sibling",
    )
    aborted = abort_run(victim)
    assert aborted.context["terminal"] == TERMINAL_ABORTED
    assert aborted.context["sibling_processes_touched"] is False
    assert aborted.context["partial_governed_result"] is False
    done = _unwrap(qmb.collect_run(sibling), "sibling collect")
    assert done.run_id != victim.run_id
    assert Path(victim.output_dir).is_dir()
    assert Path(done.output_dir).is_dir()
    assert victim.output_dir != done.output_dir


def main() -> None:
    assert qmb.abort_run is abort_run
    assert qmb.TIME_LIMIT_KEY == TIME_LIMIT_KEY
    identity_names_declared_per_run_limits()
    print("declared per-run limits qmb_run_time_limit and qmb_run_memory_limit")
    with tempfile.TemporaryDirectory(prefix="qmb_abort_", ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        submitted_run_carries_token_and_limits(root)
        print("every submitted run carries a cancel token and declared limits")
        cancel_and_limit_breach_are_typed_aborted(root)
        print("limit breach or cancel is typed aborted with context")
        abort_one_leaves_the_sibling(root)
        print("aborting one process does not touch siblings")
        print("no partial governed result; output stays in the run directory")
    print("orchestrator abort ok")


if __name__ == "__main__":
    main()
