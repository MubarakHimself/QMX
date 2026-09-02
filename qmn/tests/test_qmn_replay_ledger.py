"""Story 27.8 — exactly one terminal ledger record for every replay job."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import TypeVar

import pytest
from qmb.orchestrator.watch import ProcessLimitProbe
from qmb.runloop.observe import CancelToken, RunLimits
from qmf.core import (
    Account,
    AccountRole,
    Duration,
    RefusalCategory,
    Result,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmn.config import compile_node_config
from qmn.data import CommittedHotPrefix, SealedArchive
from qmn.mis.signal_snapshot import ProducerReadiness
from qmn.replay import (
    NEVER_REWRITE,
    ONE_TERMINAL_PER_JOB,
    REPLAY_TERMINAL_CLASS,
    TERMINAL_ABORT,
    TERMINAL_BOUND,
    TERMINAL_CANCEL,
    TERMINAL_COMPLETE,
    TERMINAL_REFUSE,
    TERMINAL_STATUSES,
    TERMINAL_TEARDOWN,
    TRANSACTION_BOUNDARY,
    RecordedDay,
    RecordedSignalSnapshot,
    ReplayImportPort,
    ReplayJobSpec,
    ReplayLedgerSink,
    ReplayLiveJob,
    ReplayTerminalRecord,
    allocate_replay_writer,
    encode_recorded_day,
    finish_replay_job,
    mint_data_fingerprint,
    mint_run_fingerprint,
    recover_replay_terminal,
    run_replay_job,
    spawn_replay_job,
    start_replay_job,
    teardown_replay_job,
)

T = TypeVar("T")

_START = 1_725_300_000 * 1_000_000_000
_END = _START + 60_000_000_000
_STREAM = "eurusd"
_BOOT = "replay-boot-27-8"
_MACHINE = "replay-host"
_DEPLOY = Path(__file__).resolve().parents[1] / "deploy"


def _load_safe_io() -> ModuleType:
    path = _DEPLOY / "safe_io.py"
    spec = importlib.util.spec_from_file_location("qmn_deploy_safe_io_replay_ledger", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_SAFE_IO = _load_safe_io()


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account() -> Account:
    return _ok(Account.try_create("acct-replay-1", _venue(), AccountRole.DEMO))


def _config_fp() -> str:
    return _ok(compile_node_config()).fingerprint.value


def _day(*, composition_fp: str) -> RecordedDay:
    snapshot = RecordedSignalSnapshot(
        frontier_ns=_START,
        environment="demo",
        feed_state="live",
        sqs_readiness=ProducerReadiness.OK,
        sqs_hard_block=False,
        snapshot_fp1="fp1:sha256:" + ("ab" * 32),
        labeler_version="sqs-v1",
    )
    observation = {
        "kind": "spot",
        "observation_id": "obs-1",
        "stream_id": _STREAM,
        "receive_wall_time_ns": _START,
        "closed": True,
        "payload": {"bid": 1},
    }
    decision = {
        "kind": "decision",
        "frontier_ns": _START,
        "stream_id": _STREAM,
        "sqs_readiness": ProducerReadiness.OK.value,
        "entry_refused": False,
    }
    control = {
        "kind": "interpretation-cursor-commit",
        "observation_id": "obs-1",
        "receive_wall_time_ns": _START,
        "event_type": "control action",
    }
    return RecordedDay(
        source_world=World.LIVE,
        venue_id=_venue(),
        account=_account(),
        stream_id=_STREAM,
        composition_fp=composition_fp,
        start_ns=_START,
        end_ns=_END,
        observations=(observation,),
        snapshots=(snapshot,),
        decisions=(decision,),
        controls=(control,),
        commands=(),
    )


def _seal(tmp_path: Path, day: RecordedDay) -> SealedArchive:
    archive = SealedArchive(tmp_path / "evidence")
    prefix = _ok(
        CommittedHotPrefix.try_create(
            world=World.LIVE,
            room_role="journal",
            prefix_id="recorded-day-1",
            start=day.start_ns,
            end=day.end_ns,
            payload=encode_recorded_day(day),
            committed=True,
        )
    )
    receipt = _ok(archive.sync(prefix))
    assert receipt.verified is True
    return archive


def _spec(tmp_path: Path, day: RecordedDay) -> ReplayJobSpec:
    port = ReplayImportPort(_seal(tmp_path, day))
    return _ok(
        ReplayJobSpec.try_create(
            import_port=port,
            source_world=World.LIVE,
            room_role="journal",
            prefix_id="recorded-day-1",
            start_ns=day.start_ns,
            end_ns=day.end_ns,
            composition_fp=day.composition_fp,
            machine=_MACHINE,
            boot_epoch_id=_BOOT,
        )
    )


def _sink(tmp_path: Path) -> ReplayLedgerSink:
    return _ok(
        ReplayLedgerSink.try_create(
            tmp_path / "replay-ledger",
            machine=_MACHINE,
            worker_slot="slot-0",
            boot_epoch_id=_BOOT,
        )
    )


def _lines(sink: ReplayLedgerSink) -> tuple[ReplayTerminalRecord, ...]:
    return _ok(sink.scan())


def test_one_terminal_per_job_contract() -> None:
    assert ONE_TERMINAL_PER_JOB is True
    assert NEVER_REWRITE is True
    assert TRANSACTION_BOUNDARY == "ordered-with-recovery"
    assert TERMINAL_STATUSES == (
        TERMINAL_COMPLETE,
        TERMINAL_REFUSE,
        TERMINAL_ABORT,
        TERMINAL_CANCEL,
        TERMINAL_BOUND,
        TERMINAL_TEARDOWN,
    )
    assert REPLAY_TERMINAL_CLASS == "qmn-replay-terminal-line"


def test_completed_job_appends_exactly_one_terminal_line(tmp_path: Path) -> None:
    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    sink = _sink(tmp_path)
    output = tmp_path / "run" / "diff.json"
    record = _ok(
        run_replay_job(
            spec,
            evidence_root=tmp_path / "evidence",
            output_path=output,
            ledger=sink,
        )
    )
    assert record.status == TERMINAL_COMPLETE
    assert record.world is World.REPLAY
    assert record.composition_fp == fp
    assert record.config_fp == fp
    assert record.interval == {"start_ns": _START, "end_ns": _END}
    assert record.refusal is None
    assert record.start_ns >= 0
    assert record.end_ns >= record.start_ns
    assert "output_path" in record.output_refs
    assert "output_fp1" in record.output_refs
    assert record.run_fp.value.startswith("fp1:sha256:")
    assert record.data_fp.value.startswith("fp1:sha256:")
    lines = _lines(sink)
    assert len(lines) == 1
    assert lines[0].fp1_identity() == record.fp1_identity()
    again = _ok(
        run_replay_job(
            spec,
            evidence_root=tmp_path / "evidence",
            output_path=output,
            ledger=sink,
        )
    )
    assert again.fp1_identity() == record.fp1_identity()
    assert len(_lines(sink)) == 1


def test_spawn_replay_job_still_writes_diff_and_one_terminal(tmp_path: Path) -> None:
    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    sink = _sink(tmp_path)
    output = tmp_path / "out" / "diff.json"
    receipt = _ok(
        spawn_replay_job(
            spec,
            evidence_root=tmp_path / "evidence",
            output_path=output,
            ledger=sink,
        )
    )
    assert receipt.pid != os.getpid()
    assert receipt.terminal_status == TERMINAL_COMPLETE
    body = json.loads(output.read_text(encoding="utf-8"))
    assert body["world"] == "replay"
    assert body["clean"] is True
    assert len(_lines(sink)) == 1


def test_refused_admitted_job_ledgers_one_refuse_line(tmp_path: Path) -> None:
    fp = _config_fp()
    port = ReplayImportPort(SealedArchive(tmp_path / "empty-evidence"))
    spec = _ok(
        ReplayJobSpec.try_create(
            import_port=port,
            source_world=World.LIVE,
            room_role="journal",
            prefix_id="recorded-day-1",
            start_ns=_START,
            end_ns=_END,
            composition_fp=fp,
            machine=_MACHINE,
            boot_epoch_id=_BOOT,
        )
    )
    sink = _sink(tmp_path)
    record = _ok(
        run_replay_job(
            spec,
            evidence_root=tmp_path / "empty-evidence",
            output_path=tmp_path / "run" / "diff.json",
            ledger=sink,
        )
    )
    assert record.status == TERMINAL_REFUSE
    assert record.refusal is not None
    assert record.failure is not None
    assert len(_lines(sink)) == 1


def test_admission_refusal_before_spawn_writes_zero_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    sink = _sink(tmp_path)
    monkeypatch.setenv("QMN_NODE_PROCESS", "1")
    refused = _refusal(
        start_replay_job(
            spec,
            evidence_root=tmp_path / "evidence",
            output_path=tmp_path / "run" / "diff.json",
        )
    )
    assert refused.context.get("failure_id") == "replay.in_node_process"
    assert _lines(sink) == ()


def _hanging_job(
    tmp_path: Path,
    spec: ReplayJobSpec,
    *,
    cancel: CancelToken | None = None,
    limits: RunLimits | None = None,
) -> ReplayLiveJob:
    run_dir = tmp_path / "hang"
    run_dir.mkdir(parents=True, exist_ok=True)
    output = run_dir / "diff.json"
    run_fp = _ok(mint_run_fingerprint(spec, output_dir=run_dir))
    writer = _ok(
        allocate_replay_writer(
            machine=spec.machine,
            role="replay-ledger",
            stream="replay:ledger:slot-0",
            boot_epoch_id=spec.boot_epoch_id,
        )
    )
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    token = cancel if cancel is not None else CancelToken()
    bound = limits if limits is not None else RunLimits()
    probe = ProcessLimitProbe(process.pid, 0)
    data_fp = _ok(mint_data_fingerprint(spec))
    _SAFE_IO.write_text_exclusive_no_follow(
        run_dir / "writer.json",
        json.dumps(
            {
                "run_fp": run_fp.value,
                "config_fp": spec.composition_fp,
                "data_fp": data_fp.value,
                "composition_fp": spec.composition_fp,
                "interval": {"start_ns": spec.start_ns, "end_ns": spec.end_ns},
                "start_ns": 1,
                "pid": process.pid,
                "output_path": str(output),
            },
            sort_keys=True,
        )
        + "\n",
        contain_within=run_dir,
    )
    return ReplayLiveJob(
        spec=spec,
        run_fp=run_fp,
        config_fp=spec.composition_fp,
        data_fp=data_fp,
        composition_fp=spec.composition_fp,
        run_dir=run_dir,
        output_path=output,
        evidence_root=tmp_path / "evidence",
        pid=process.pid,
        process=process,
        start_ns=1,
        writer=writer,
        cancel=token,
        limits=bound,
        probe=probe,
    )


def test_cancel_bound_teardown_and_abort_each_ledger_one_line(tmp_path: Path) -> None:
    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))

    sink_cancel = _ok(
        ReplayLedgerSink.try_create(
            tmp_path / "ledger-cancel",
            machine=_MACHINE,
            worker_slot="slot-c",
            boot_epoch_id=_BOOT,
        )
    )
    live_cancel = _hanging_job(tmp_path / "c", spec)
    _ok(live_cancel.cancel.cancel())
    cancelled = _ok(finish_replay_job(live_cancel, ledger=sink_cancel))
    assert cancelled.status == TERMINAL_CANCEL
    assert len(_lines(sink_cancel)) == 1

    sink_bound = _ok(
        ReplayLedgerSink.try_create(
            tmp_path / "ledger-bound",
            machine=_MACHINE,
            worker_slot="slot-b",
            boot_epoch_id=_BOOT,
        )
    )
    live_bound = _hanging_job(
        tmp_path / "b",
        spec,
        limits=_ok(RunLimits.try_create(time_limit=_ok(Duration.try_create(1)))),
    )
    bounded = _ok(finish_replay_job(live_bound, ledger=sink_bound))
    assert bounded.status == TERMINAL_BOUND
    assert len(_lines(sink_bound)) == 1

    sink_tear = _ok(
        ReplayLedgerSink.try_create(
            tmp_path / "ledger-tear",
            machine=_MACHINE,
            worker_slot="slot-t",
            boot_epoch_id=_BOOT,
        )
    )
    live_tear = _hanging_job(tmp_path / "t", spec)
    torn = _ok(teardown_replay_job(live_tear, ledger=sink_tear))
    assert torn.status == TERMINAL_TEARDOWN
    assert len(_lines(sink_tear)) == 1

    sink_abort = _ok(
        ReplayLedgerSink.try_create(
            tmp_path / "ledger-abort",
            machine=_MACHINE,
            worker_slot="slot-a",
            boot_epoch_id=_BOOT,
        )
    )
    live_abort = _hanging_job(tmp_path / "a", spec)
    live_abort.process.kill()
    live_abort.process.wait(timeout=5)
    aborted = _ok(finish_replay_job(live_abort, ledger=sink_abort))
    assert aborted.status == TERMINAL_ABORT
    assert aborted.failure is not None
    assert len(_lines(sink_abort)) == 1


def test_second_differing_line_is_refused_never_rewritten(tmp_path: Path) -> None:
    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    sink = _sink(tmp_path)
    output = tmp_path / "run" / "diff.json"
    first = _ok(
        run_replay_job(
            spec,
            evidence_root=tmp_path / "evidence",
            output_path=output,
            ledger=sink,
        )
    )
    tampered = ReplayTerminalRecord(
        run_fp=first.run_fp,
        config_fp=first.config_fp,
        data_fp=first.data_fp,
        composition_fp=first.composition_fp,
        interval=dict(first.interval),
        status=TERMINAL_ABORT,
        start_ns=first.start_ns,
        end_ns=first.end_ns,
        output_refs=dict(first.output_refs),
        failure={"status": TERMINAL_ABORT},
    )
    collision = _refusal(sink.append(tampered))
    assert collision.category is RefusalCategory.POLICY_REJECTION
    assert collision.context["failure_id"] in {"replay.ledger.rewrite", "replay.ledger.collision"}
    still = _lines(sink)
    assert len(still) == 1
    assert still[0].fp1_identity() == first.fp1_identity()
    assert still[0].status == TERMINAL_COMPLETE


def test_crash_recovery_appends_missing_terminal_from_output(tmp_path: Path) -> None:
    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    sink = _sink(tmp_path)
    output = tmp_path / "run" / "diff.json"
    live = _ok(
        start_replay_job(
            spec,
            evidence_root=tmp_path / "evidence",
            output_path=output,
        )
    )
    live.process.wait(timeout=60)
    assert output.is_file()
    assert _ok(sink.line_for(live.run_fp)) is None
    recovered = _ok(recover_replay_terminal(run_dir=live.run_dir, ledger=sink))
    assert recovered.status == TERMINAL_COMPLETE
    assert recovered.run_fp == live.run_fp
    assert len(_lines(sink)) == 1
    again = _ok(recover_replay_terminal(run_dir=live.run_dir, ledger=sink))
    assert again.fp1_identity() == recovered.fp1_identity()
    assert len(_lines(sink)) == 1


def test_crash_recovery_aborts_when_output_missing(tmp_path: Path) -> None:
    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    sink = _sink(tmp_path)
    live = _hanging_job(tmp_path, spec)
    live.process.kill()
    live.process.wait(timeout=5)
    recovered = _ok(recover_replay_terminal(run_dir=live.run_dir, ledger=sink))
    assert recovered.status == TERMINAL_ABORT
    assert len(_lines(sink)) == 1


def test_storage_failure_requires_review(tmp_path: Path) -> None:
    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    sink = _sink(tmp_path)
    path = _ok(sink.fragment_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()
    live = _hanging_job(tmp_path / "store", spec)
    live.process.kill()
    live.process.wait(timeout=5)
    refused = _refusal(finish_replay_job(live, ledger=sink))
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert refused.context.get("requiring_review") is True
    assert refused.context.get("failure_id") == "replay.ledger.storage"
    scanned = sink.scan()
    assert is_refusal(scanned)
    assert scanned.context.get("requiring_review") is True


def test_fragment_is_fp1_canonical_jsonl(tmp_path: Path) -> None:
    from qmf.core import canonical_bytes

    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    sink = _sink(tmp_path)
    record = _ok(
        run_replay_job(
            spec,
            evidence_root=tmp_path / "evidence",
            output_path=tmp_path / "run" / "diff.json",
            ledger=sink,
        )
    )
    path = _ok(sink.fragment_path())
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r" not in raw
    expected = _ok(canonical_bytes(dict(record.as_mapping())))
    assert raw[:-1] == expected
    assert "start_ns" not in record.fp1_identity()
    assert "end_ns" not in record.fp1_identity()
    assert record.as_mapping()["start_ns"] == record.start_ns


def test_direct_run_recorded_day_writes_no_terminal_line(tmp_path: Path) -> None:
    from qmn.replay import run_recorded_day

    fp = _config_fp()
    spec = _spec(tmp_path, _day(composition_fp=fp))
    _ok(run_recorded_day(spec))
    assert list(tmp_path.rglob("ledger.jsonl")) == []
