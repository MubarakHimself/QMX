"""Story 15.5 — per-run AD-14 operational logs streamed by the orchestrator."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.doors import api
from qmb.orchestrator.watch import monotonic_ns
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_STAMP = "2026-01-01T00:00:00.000000000Z"
_LATER = "2026-01-02T00:00:00.000000000Z"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs("eurusd"),), (_obs("eurusd", _NS + 1),))


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "orch-log", "tag": tag}))
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


def _hanging_with_log(tmp_path: Path, *, tag: str) -> qmb.LiveSpawn:
    config = _config(tag=tag)
    named = _ok(qmb.run_directory_name(config.fingerprint))
    directory = tmp_path / named
    directory.mkdir()
    correlation = qmb.mint_correlation_id()
    path = _ok(
        qmb.inject_run_log(
            directory,
            run_id=config.fingerprint,
            correlation_id=correlation,
        )
    )
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
        cancel=qmb.CancelToken(),
        limits=qmb.RunLimits(),
        started_monotonic_ns=monotonic_ns(),
        correlation_id=correlation,
        log_path=str(path),
    )


def test_identity_names_operational_only_logs_and_excluded_correlation() -> None:
    identity = qmb.orchestrator_identity()
    log_identity = qmb.operational_log_identity()
    assert identity["log_owner"] == qmb.IMPURE_OWNER == "orchestrator"
    assert identity["log_filename"] == qmb.LOG_FILENAME == "run.log"
    assert identity["log_is_evidence"] is qmb.LOG_IS_EVIDENCE is False
    assert identity["log_kind"] == qmb.LOG_KIND == "ad-14-operational"
    assert identity["correlation_id_excluded_from_fp1"] is (
        qmb.CORRELATION_ID_EXCLUDED_FROM_FP1 is True
    )
    assert identity["timestamp_excluded_from_fp1"] is qmb.TIMESTAMP_EXCLUDED_FROM_FP1 is True
    assert identity["timestamp_encoding"] == qmb.TIMESTAMP_ENCODING == "UTC-ISO-8601-Z"
    assert (
        identity["evidence_bearing_formats"]
        == qmb.EVIDENCE_BEARING_FORMATS
        == (
            "raw archive",
            "journal",
        )
    )
    assert log_identity["log_is_evidence"] is False
    assert qmb.__version__ not in identity.values()
    assert api.LogSink is qmb.LogSink
    assert api.propagate_correlation is qmb.propagate_correlation
    assert api.read_run_log is qmb.read_run_log
    assert api.inject_run_log is qmb.inject_run_log


def test_correlation_id_is_excluded_from_fp1_identity() -> None:
    run_id = "fp1:sha256:" + "ab" * 32
    first = _ok(
        qmb.OperationalRecord.try_create(
            event="boundary",
            message="cross-package structured log",
            run_id=run_id,
            correlation_id="corr-a",
            timestamp=_STAMP,
            fields={"package": "qmf-data"},
        )
    )
    second = _ok(
        qmb.OperationalRecord.try_create(
            event="boundary",
            message="cross-package structured log",
            run_id=run_id,
            correlation_id="corr-b",
            timestamp=_LATER,
            fields={"package": "qmf-data"},
        )
    )
    assert "correlation_id" not in first.fp1_identity()
    assert "timestamp" not in first.fp1_identity()
    assert first.fp1_identity() == second.fp1_identity()
    stamped = fingerprint(first.fp1_identity())
    other = fingerprint(second.fp1_identity())
    assert is_ok(stamped) and is_ok(other)
    assert stamped.value.value == other.value.value
    assert first.correlation_id != second.correlation_id
    assert first.to_row()["correlation_id"] == "corr-a"
    assert first.is_evidence is False


def test_propagate_correlation_across_package_boundary() -> None:
    correlation = qmb.mint_correlation_id()
    payload = {"event": "journal-append-attempt", "package": "qmf-data"}
    bound = _ok(qmb.propagate_correlation(payload, correlation_id=correlation))
    assert bound["correlation_id"] == correlation
    assert bound["package"] == "qmf-data"
    identity = _ok(qmb.structured_log_fp1_identity(bound))
    assert "correlation_id" not in identity
    assert identity["package"] == "qmf-data"
    refused = qmb.propagate_correlation(payload, correlation_id="")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "correlation_id"


def test_log_sink_health_and_one_writer(tmp_path: Path) -> None:
    path = tmp_path / qmb.LOG_FILENAME
    correlation = qmb.mint_correlation_id()
    sink = _ok(
        qmb.LogSink.try_create(
            path,
            run_id="fp1:sha256:" + "cd" * 32,
            correlation_id=correlation,
        )
    )
    report = sink.health()
    assert report.owner == "orchestrator"
    assert report.is_evidence is False
    assert report.is_open is True
    assert report.records_emitted == 0
    assert report.correlation_id == correlation
    _ok(sink.emit("spawned", "injected"))
    assert sink.health().records_emitted == 1
    sink.close()
    assert sink.health().is_open is False
    again = qmb.LogSink.try_create(
        path,
        run_id="fp1:sha256:" + "cd" * 32,
        correlation_id=correlation,
    )
    assert is_refusal(again)
    assert again.category is RefusalCategory.POLICY_REJECTION


def test_orchestrator_streams_operational_log_into_run_directory(tmp_path: Path) -> None:
    config = _config(tag="stream")
    live = _ok(qmb.start_run(config=config, slices=_slices(), output_root=tmp_path))
    log_file = Path(live.output_dir) / qmb.LOG_FILENAME
    assert log_file.is_file()
    assert live.correlation_id is not None
    assert live.log_path == str(log_file)
    payload = json.loads((Path(live.output_dir) / qmb.PAYLOAD_NAME).read_text(encoding="utf-8"))
    assert payload["correlation_id"] == live.correlation_id
    assert payload["log_name"] == qmb.LOG_FILENAME
    done = _ok(qmb.collect_run(live))
    records = _ok(qmb.read_run_log(done.output_dir))
    events = [item.event for item in records]
    assert events[0] == qmb.EVENT_SPAWNED
    assert qmb.EVENT_RUN_STARTED in events
    assert qmb.EVENT_RUN_COMPLETED in events
    assert all(item.correlation_id == live.correlation_id for item in records)
    assert all(item.is_evidence is False for item in records)
    assert all(item.timestamp.endswith("Z") for item in records)
    raw = log_file.read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r" not in raw
    assert log_file.resolve().parent == Path(done.output_dir).resolve()


def test_pure_run_writes_no_operational_log(tmp_path: Path) -> None:
    config = _config(tag="pure")
    _ok(run(slices=_slices(), config=config, handler=SilentSliceHandler()))
    assert list(tmp_path.rglob(qmb.LOG_FILENAME)) == []
    source = (_SRC / "runloop" / "loop.py").read_text(encoding="utf-8")
    assert "writes no log and no ledger" in source
    tree = ast.parse((_SRC / "runloop" / "loop.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert "qmb.orchestrator.log" not in imported
    assert "qmb.orchestrator" not in imported


def test_two_runs_never_share_a_log_file_or_correlation_id(tmp_path: Path) -> None:
    first = _ok(qmb.spawn_run(config=_config(tag="alpha"), slices=_slices(), output_root=tmp_path))
    second = _ok(qmb.spawn_run(config=_config(tag="beta"), slices=_slices(), output_root=tmp_path))
    path_a = Path(first.output_dir) / qmb.LOG_FILENAME
    path_b = Path(second.output_dir) / qmb.LOG_FILENAME
    assert path_a != path_b
    assert not path_a.samefile(path_b)
    records_a = _ok(qmb.read_run_log(first.output_dir))
    records_b = _ok(qmb.read_run_log(second.output_dir))
    assert records_a[0].correlation_id != records_b[0].correlation_id
    assert records_a[0].run_id != records_b[0].run_id


def test_crashed_run_leaves_partial_log_without_touching_sibling_or_ledger(
    tmp_path: Path,
) -> None:
    victim = _hanging_with_log(tmp_path, tag="victim")
    sibling = _hanging_with_log(tmp_path, tag="sibling")
    aborted = qmb.abort_run(victim)
    assert is_refusal(aborted)
    assert aborted.context["terminal"] == "aborted"
    assert aborted.context["operational_log_is_evidence"] is False
    assert aborted.context["sibling_processes_touched"] is False
    assert victim.process.poll() is not None
    assert sibling.process.poll() is None
    victim_records = _ok(qmb.read_run_log(victim.output_dir))
    sibling_records = _ok(qmb.read_run_log(sibling.output_dir))
    victim_events = [item.event for item in victim_records]
    sibling_events = [item.event for item in sibling_records]
    assert qmb.EVENT_SPAWNED in victim_events
    assert qmb.EVENT_RUN_ABORTED in victim_events
    assert qmb.EVENT_SPAWNED in sibling_events
    assert qmb.EVENT_RUN_ABORTED not in sibling_events
    assert Path(victim.output_dir).resolve() != Path(sibling.output_dir).resolve()
    assert list(tmp_path.rglob("ledger.jsonl")) == []
    assert list(Path(victim.output_dir).glob("*.jsonl")) == []
    assert list(Path(sibling.output_dir).glob("*.jsonl")) == []
    qmb.abort_run(sibling)


def test_logs_are_never_ct11_evidence() -> None:
    assert qmb.LOG_IS_EVIDENCE is False
    assert "raw archive" in qmb.EVIDENCE_BEARING_FORMATS
    assert "journal" in qmb.EVIDENCE_BEARING_FORMATS
    assert qmb.LOG_KIND not in qmb.EVIDENCE_BEARING_FORMATS
    assert qmb.LOG_FILENAME not in qmb.EVIDENCE_BEARING_FORMATS
