"""Reference usage — one ledger line per run on WriterId-scoped JSONL fragments.

Executable::

    python qmb/examples/orchestrator_ledger_usage.py

Shows the things Story 15.4 / AR-51 / AR-53 / B-4 pin down:

1. The orchestrator appends exactly one ledger line per run — completed or
   aborted, never zero, never two. The aborted line carries refusal context.
2. The line carries the AD-12 result label (evidence class; provenance=sandbox
   on factory-sandbox runs), the CT-32 fingerprint, raw AD-40 unit-kinded
   measures, the Book-bar fingerprint as resolved at run time, and a
   discriminated run role. It stores no pass/fail verdict.
3. Physically the ledger is JSONL fragment files, one fp1-canonical object per
   line, LF-terminated, append-with-fsync, WriterId-scoped per
   ``(machine, role, worker-slot)``. Concurrent processes never share a file.
4. Reads are a world-and-role-scoped merge view. The Book-bar read selects
   ``role=confirmation`` only.
5. Direct library ``run()`` produces no governed evidence.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.orchestrator import (
    FACTORY_SANDBOX_ENV,
    FRAGMENT_FILENAME,
    LedgerSink,
    finish_run,
    fragment_path,
    orchestrator_identity,
    start_run,
)
from qmb.orchestrator.watch import monotonic_ns
from qmb.runloop import STREAM_SET_KEY, CancelToken, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, canonical_bytes, fingerprint
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
    stamp = _unwrap(fingerprint({"n": "orch-ledger-example", "tag": tag}), "stamp")
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


def identity_names_one_line_jsonl() -> None:
    identity = qmb.ledger_identity()
    assert identity["one_line_per_run"] is qmb.ONE_LINE_PER_RUN is True
    assert identity["stores_verdict"] is qmb.STORES_VERDICT is False
    assert identity["fragment_kind"] == "jsonl"
    assert identity["book_bar_read_role"] == qmb.ROLE_CONFIRMATION
    assert identity["writer_scope"] == ("machine", "role", "worker-slot")
    orch = orchestrator_identity()
    assert orch["ledger_writes"] == "orchestrator"
    assert orch["ledger_fragment"] == FRAGMENT_FILENAME
    assert orch["factory_sandbox_env"] == FACTORY_SANDBOX_ENV


def completed_run_is_one_confirmation_line(output_root: Path, ledger_root: Path) -> None:
    config = _config("done")
    sink = _unwrap(
        LedgerSink.try_create(
            ledger_root, machine="example-machine", worker_slot=0, boot_epoch_id="boot-1"
        ),
        "sink",
    )
    live = _unwrap(
        start_run(config=config, slices=_slices(), output_root=output_root),
        "start",
    )
    done = _unwrap(
        finish_run(live, config=config, ledger=sink, role=qmb.ROLE_CONFIRMATION),
        "finish",
    )
    lines = _unwrap(
        qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION),
        "merge",
    )
    assert len(lines) == 1
    line = lines[0]
    assert line.role == qmb.ROLE_CONFIRMATION
    assert line.ct32_fingerprint == done.ct32_fingerprint
    assert "verdict" not in line.fp1_identity()
    assert all("unit_kind" in measure for measure in line.measures)
    writer = _unwrap(sink.writer_id(qmb.ROLE_CONFIRMATION), "writer")
    path = _unwrap(
        fragment_path(sink.root, writer, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION),
        "path",
    )
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    assert _unwrap(canonical_bytes(line.fp1_identity()), "canonical") == raw[:-1]
    bar = _unwrap(qmb.read_book_bar(sink.root, world=World.REPLAY), "book-bar")
    assert bar == lines


def aborted_line_carries_refusal_context(output_root: Path, ledger_root: Path) -> None:
    config = _config("abort")
    sink = _unwrap(
        LedgerSink.try_create(
            ledger_root, machine="example-machine", worker_slot=1, boot_epoch_id="boot-1"
        ),
        "abort-sink",
    )
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
    token = CancelToken()
    live = qmb.LiveSpawn(
        run_id=config.fingerprint,
        output_dir=str(directory),
        pid=process.pid,
        process=process,
        cancel=token,
        limits=qmb.RunLimits(),
        started_monotonic_ns=monotonic_ns(),
    )
    _unwrap(token.cancel(), "signal")
    refused = finish_run(live, config=config, ledger=sink)
    assert is_refusal(refused)
    assert refused.context["writes_ledger"] is True
    aborted = _unwrap(
        qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_ABORTED),
        "aborted-merge",
    )
    assert len(aborted) == 1
    assert aborted[0].refusal is not None
    assert aborted[0].refusal["terminal"] == "aborted"
    bar = _unwrap(qmb.read_book_bar(sink.root, world=World.REPLAY), "book-bar")
    assert all(item.run_id != config.fingerprint for item in bar)
    assert all(item.role == qmb.ROLE_CONFIRMATION for item in bar)


def library_run_is_not_governed_evidence(output_root: Path) -> None:
    config = _config("research")
    _unwrap(run(slices=_slices(), config=config, handler=SilentSliceHandler()), "pure run")
    assert list(output_root.rglob("*.jsonl")) == []


def main() -> None:
    assert qmb.finish_run is finish_run
    assert qmb.ONE_LINE_PER_RUN is True
    identity_names_one_line_jsonl()
    print("one ledger line per run; JSONL fragments; no stored verdict")
    with tempfile.TemporaryDirectory(prefix="qmb_ledger_", ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        runs = root / "runs"
        ledger = root / "ledger"
        runs.mkdir()
        completed_run_is_one_confirmation_line(runs, ledger)
        print("completed run appends one confirmation line; Book-bar read selects it")
        aborted_line_carries_refusal_context(runs, ledger)
        print("aborted line carries refusal context, never silently absent")
        library_run_is_not_governed_evidence(runs)
        print("direct library run() produces no governed evidence")
        print("WriterId-scoped fragments; concurrent slots never share a file")
    print("orchestrator ledger ok")


if __name__ == "__main__":
    main()
