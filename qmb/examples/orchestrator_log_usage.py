"""Reference usage — per-run AD-14 operational logs streamed by the orchestrator.

Executable::

    python qmb/examples/orchestrator_log_usage.py

Shows the things Story 15.5 / B-4 / AR-35 / CT-11 pin down:

1. The orchestrator owns the injected log sink and streams the run's
   operational log into a per-run log file in the run's output directory.
2. Per-run logs are AD-14 operational logs only and are NEVER evidence —
   under CT-11 only the raw archive and the journal bear evidence.
3. Structured logs that cross package boundaries carry a ``correlation_id``
   excluded from fp1 identity.
4. A crashed run leaves a partial log in its own room and never corrupts a
   sibling or the ledger.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.orchestrator import (
    CORRELATION_ID_EXCLUDED_FROM_FP1,
    EVENT_RUN_ABORTED,
    EVENT_RUN_COMPLETED,
    EVENT_RUN_STARTED,
    EVENT_SPAWNED,
    EVIDENCE_BEARING_FORMATS,
    LOG_FILENAME,
    LOG_IS_EVIDENCE,
    abort_run,
    inject_run_log,
    mint_correlation_id,
    operational_log_identity,
    orchestrator_identity,
    propagate_correlation,
    read_run_log,
    spawn_run,
    start_run,
    structured_log_fp1_identity,
)
from qmb.orchestrator.watch import monotonic_ns
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
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
    stamp = _unwrap(fingerprint({"n": "orch-log-example", "tag": tag}), "stamp")
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


def identity_names_operational_only_logs() -> None:
    identity = orchestrator_identity()
    log_identity = operational_log_identity()
    assert identity["log_owner"] == "orchestrator"
    assert identity["log_filename"] == LOG_FILENAME == "run.log"
    assert identity["log_is_evidence"] is LOG_IS_EVIDENCE is False
    assert identity["correlation_id_excluded_from_fp1"] is (
        CORRELATION_ID_EXCLUDED_FROM_FP1 is True
    )
    assert (
        log_identity["evidence_bearing_formats"]
        == EVIDENCE_BEARING_FORMATS
        == (
            "raw archive",
            "journal",
        )
    )


def correlation_id_excluded_from_fp1() -> None:
    correlation = mint_correlation_id()
    payload = {"event": "journal-append-attempt", "package": "qmf-data"}
    bound = _unwrap(
        propagate_correlation(payload, correlation_id=correlation),
        "boundary",
    )
    assert bound["correlation_id"] == correlation
    identity = _unwrap(structured_log_fp1_identity(bound), "identity")
    assert "correlation_id" not in identity
    first = _unwrap(
        qmb.OperationalRecord.try_create(
            event="boundary",
            message="cross-package structured log",
            run_id="run-a",
            correlation_id="corr-a",
            timestamp="2026-01-01T00:00:00.000000000Z",
        ),
        "first",
    )
    second = _unwrap(
        qmb.OperationalRecord.try_create(
            event="boundary",
            message="cross-package structured log",
            run_id="run-a",
            correlation_id="corr-b",
            timestamp="2026-01-02T00:00:00.000000000Z",
        ),
        "second",
    )
    assert first.fp1_identity() == second.fp1_identity()
    assert "correlation_id" not in first.fp1_identity()


def orchestrator_streams_into_run_directory(output_root: Path) -> None:
    config = _config("stream")
    isolated = _unwrap(
        spawn_run(config=config, slices=_slices(), output_root=output_root),
        "spawn",
    )
    log_file = Path(isolated.output_dir) / LOG_FILENAME
    assert log_file.is_file()
    records = _unwrap(read_run_log(isolated.output_dir), "log")
    events = [item.event for item in records]
    assert EVENT_SPAWNED in events
    assert EVENT_RUN_STARTED in events
    assert EVENT_RUN_COMPLETED in events
    assert all(item.is_evidence is False for item in records)
    assert all(item.timestamp.endswith("Z") for item in records)


def crashed_run_stays_in_its_own_room(output_root: Path) -> None:
    victim_config = _config("victim")
    named = _unwrap(qmb.run_directory_name(victim_config.fingerprint), "dir")
    directory = output_root / named
    directory.mkdir()
    correlation = mint_correlation_id()
    path = _unwrap(
        inject_run_log(
            directory,
            run_id=victim_config.fingerprint,
            correlation_id=correlation,
        ),
        "inject",
    )
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    victim = qmb.LiveSpawn(
        run_id=victim_config.fingerprint,
        output_dir=str(directory),
        pid=process.pid,
        process=process,
        cancel=qmb.CancelToken(),
        limits=qmb.RunLimits(),
        started_monotonic_ns=monotonic_ns(),
        correlation_id=correlation,
        log_path=str(path),
    )
    sibling = _unwrap(
        start_run(config=_config("sibling"), slices=_slices(), output_root=output_root),
        "sibling",
    )
    aborted = abort_run(victim)
    assert is_refusal(aborted)
    assert aborted.context["operational_log_is_evidence"] is False
    done = _unwrap(qmb.collect_run(sibling), "sibling collect")
    victim_events = [item.event for item in _unwrap(read_run_log(victim.output_dir), "v")]
    sibling_events = [item.event for item in _unwrap(read_run_log(done.output_dir), "s")]
    assert EVENT_RUN_ABORTED in victim_events
    assert EVENT_RUN_ABORTED not in sibling_events
    assert EVENT_RUN_COMPLETED in sibling_events
    assert list(output_root.rglob("ledger.jsonl")) == []
    assert victim.output_dir != done.output_dir


def library_run_writes_no_log(output_root: Path) -> None:
    _unwrap(
        run(slices=_slices(), config=_config("research"), handler=SilentSliceHandler()),
        "pure run",
    )
    assert list(output_root.rglob(LOG_FILENAME)) == []


def main() -> None:
    assert qmb.LOG_IS_EVIDENCE is False
    identity_names_operational_only_logs()
    print("orchestrator owns the injected log sink")
    correlation_id_excluded_from_fp1()
    print("correlation_id excluded from fp1 identity")
    with tempfile.TemporaryDirectory(prefix="qmb_log_", ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        orchestrator_streams_into_run_directory(root)
        print("AD-14 operational logs only, never evidence")
        crashed_run_stays_in_its_own_room(root)
        print("crashed run leaves a partial log in its own room")
        research = root / "research"
        research.mkdir()
        library_run_writes_no_log(research)
        print("never corrupts sibling or the ledger")
    print("orchestrator log ok")


if __name__ == "__main__":
    main()
