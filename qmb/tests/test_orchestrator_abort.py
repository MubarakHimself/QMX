"""Story 15.3 — cancel tokens, per-run limits, typed aborted refusals (AR-51, B-5)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.doors import api
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
    SilentSliceHandler,
    SliceObservation,
    run,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs("eurusd"),), (_obs("eurusd", _NS + 1),))


def _config(*, tag: str, **keys: object) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "orch-abort", "tag": tag}))
    payload: dict[str, object] = {STREAM_SET_KEY: ("eurusd",)}
    payload.update(keys)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=payload,
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _hanging_live(
    tmp_path: Path,
    config: ResolvedRunConfig,
    *,
    cancel: CancelToken | None = None,
    limits: RunLimits | None = None,
) -> qmb.LiveSpawn:
    named = _ok(qmb.run_directory_name(config.fingerprint))
    directory = tmp_path / named
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
        cancel=cancel if cancel is not None else CancelToken(),
        limits=limits if limits is not None else RunLimits(),
        started_monotonic_ns=monotonic_ns(),
    )


def test_submitted_run_carries_cancel_token_and_declared_limit_keys(tmp_path: Path) -> None:
    identity = qmb.orchestrator_identity()
    assert identity["time_limit_key"] == TIME_LIMIT_KEY == "qmb_run_time_limit"
    assert identity["memory_limit_key"] == MEMORY_LIMIT_KEY == "qmb_run_memory_limit"
    assert identity["abort_kills_siblings"] is qmb.ABORT_KILLS_SIBLINGS is False
    assert identity["enforcement"] == qmb.ENFORCEMENT == "orchestrator-os-process"
    assert identity["partial_governed_result_on_abort"] is PARTIAL_GOVERNED_RESULT_ON_ABORT is False
    assert identity["cancel_token"] is True
    assert qmb.__version__ not in identity.values()
    assert api.abort_run is qmb.abort_run
    assert api.ProcessLimitProbe is qmb.ProcessLimitProbe

    limits = _ok(RunLimits.try_create(time_limit=50, memory_limit_bytes=64))
    token = CancelToken()
    config = _config(tag="carry", **{TIME_LIMIT_KEY: 50, MEMORY_LIMIT_KEY: 64})
    live = _ok(
        qmb.start_run(
            config=config,
            slices=_slices(),
            output_root=tmp_path,
            cancel=token,
            limits=limits,
        )
    )
    try:
        assert live.cancel is token
        assert live.limits.time_limit is not None
        assert live.limits.time_limit.value_ns == 50
        assert live.limits.memory_limit_bytes == 64
        payload = json.loads((Path(live.output_dir) / qmb.PAYLOAD_NAME).read_text(encoding="utf-8"))
        assert payload["limits"]["time_limit_key"] == TIME_LIMIT_KEY
        assert payload["limits"]["memory_limit_key"] == MEMORY_LIMIT_KEY
        assert payload["limits"]["time_limit_ns"] == 50
        assert payload["limits"]["memory_limit_bytes"] == 64
    finally:
        qmb.abort_run(live)


def test_cancel_kills_the_os_process_with_typed_aborted(tmp_path: Path) -> None:
    config = _config(tag="cancel")
    token = CancelToken()
    live = _hanging_live(tmp_path, config, cancel=token)
    _ok(token.cancel())
    refused = qmb.collect_run(live)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["cause"] == CAUSE_CANCEL
    assert refused.context["killed_os_process"] is True
    assert refused.context["sibling_processes_touched"] is False
    assert refused.context["partial_governed_result"] is False
    assert refused.context["run_id"] == config.fingerprint.value
    assert live.process.poll() is not None
    assert not (Path(live.output_dir) / qmb.RESULT_NAME).is_file()
    assert Path(live.output_dir).is_dir()


def test_time_limit_breach_is_typed_aborted_not_a_silent_kill(tmp_path: Path) -> None:
    config = _config(tag="time")
    limits = _ok(RunLimits.try_create(time_limit=1))
    live = _hanging_live(tmp_path, config, limits=limits)
    refused = qmb.collect_run(live)
    assert is_refusal(refused)
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["cause"] == CAUSE_TIME_LIMIT
    assert refused.context["time_limit_key"] == TIME_LIMIT_KEY
    assert refused.context["killed_os_process"] is True
    assert live.process.poll() is not None


def test_memory_limit_breach_is_typed_aborted(tmp_path: Path) -> None:
    config = _config(tag="mem")
    limits = _ok(RunLimits.try_create(memory_limit_bytes=1))
    live = _hanging_live(tmp_path, config, limits=limits)
    refused = qmb.collect_run(live)
    assert is_refusal(refused)
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["cause"] == CAUSE_MEMORY_LIMIT
    assert refused.context["memory_limit_key"] == MEMORY_LIMIT_KEY
    assert live.process.poll() is not None


def test_aborting_one_process_does_not_touch_siblings(tmp_path: Path) -> None:
    first = _config(tag="sib-a")
    second = _config(tag="sib-b")
    token_a = CancelToken()
    live_a = _hanging_live(tmp_path, first, cancel=token_a)
    live_b = _ok(qmb.start_run(config=second, slices=_slices(), output_root=tmp_path))
    try:
        pid_b = live_b.pid
        aborted = qmb.abort_run(live_a, cause=CAUSE_CANCEL)
        assert aborted.context["terminal"] == TERMINAL_ABORTED
        assert aborted.context["pid"] == live_a.pid
        assert live_a.process.poll() is not None
        assert live_b.process.poll() is None or Path(live_b.output_dir).exists()
        done_b = _ok(qmb.collect_run(live_b))
        assert done_b.pid == pid_b
        assert done_b.run_id == second.fingerprint
        in_b = _ok(run(slices=_slices(), config=second, handler=SilentSliceHandler()))
        assert done_b.outcome_identity == in_b.fp1_identity()
        assert live_a.output_dir != live_b.output_dir
        assert Path(live_a.output_dir).is_dir()
        assert Path(live_b.output_dir).is_dir()
        assert live_a.process.poll() is not None
    finally:
        if live_a.process.poll() is None:
            qmb.abort_run(live_a)
        if live_b.process.poll() is None:
            qmb.abort_run(live_b)


def test_aborted_run_never_returns_a_governed_isolated_run(tmp_path: Path) -> None:
    config = _config(tag="no-partial")
    live = _hanging_live(tmp_path, config)
    refused = qmb.abort_run(live)
    assert is_refusal(refused)
    assert refused.context["partial_governed_result"] is False
    assert refused.context["writes_ledger"] is False
    assert "outcome" not in refused.context
    assert "ct32_fingerprint" not in refused.context
    assert not (Path(live.output_dir) / qmb.RESULT_NAME).is_file()
    assert Path(live.output_dir).is_dir()


def test_spawn_concurrent_abort_does_not_reap_the_sibling(tmp_path: Path) -> None:
    tiny = _ok(RunLimits.try_create(time_limit=1))
    hanging = _config(tag="batch-hang")
    sibling = _config(tag="batch-ok")
    live_hang = _hanging_live(tmp_path, hanging, limits=tiny)
    live_ok = _ok(qmb.start_run(config=sibling, slices=_slices(), output_root=tmp_path))
    try:
        refused = qmb.collect_run(live_hang)
        assert is_refusal(refused)
        assert refused.context["cause"] == CAUSE_TIME_LIMIT
        done = _ok(qmb.collect_run(live_ok))
        assert done.run_id == sibling.fingerprint
        envelope = json.loads((Path(done.output_dir) / qmb.RESULT_NAME).read_text(encoding="utf-8"))
        assert envelope["ok"] is True
        assert live_hang.process.poll() is not None
        assert Path(live_hang.output_dir).is_dir()
    finally:
        if live_hang.process.poll() is None:
            qmb.abort_run(live_hang)
        if live_ok.process.poll() is None:
            qmb.abort_run(live_ok)


def test_pre_cancelled_token_refuses_before_spawn(tmp_path: Path) -> None:
    token = CancelToken()
    _ok(token.cancel())
    refused = qmb.start_run(
        config=_config(tag="pre-cancel"),
        slices=_slices(),
        output_root=tmp_path,
        cancel=token,
    )
    assert is_refusal(refused)
    assert refused.context["terminal"] == TERMINAL_ABORTED
    assert refused.context["killed_os_process"] is False
    assert list(tmp_path.iterdir()) == []


def test_unknown_cancel_and_mismatched_limits_are_invalid(tmp_path: Path) -> None:
    refused = qmb.start_run(
        config=_config(tag="bad-cancel"),
        slices=_slices(),
        output_root=tmp_path,
        cancel=object(),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "cancel"
    config = _config(tag="mismatch", **{TIME_LIMIT_KEY: 80})
    mismatch = qmb.start_run(
        config=config,
        slices=_slices(),
        output_root=tmp_path,
        limits=_ok(RunLimits.try_create(time_limit=1)),
    )
    assert is_refusal(mismatch)
    assert mismatch.context["field"] == "limits"
    assert list(tmp_path.iterdir()) == []


def test_process_limit_probe_reads_this_process() -> None:
    probe = qmb.ProcessLimitProbe.for_current_process()
    elapsed = _ok(probe.elapsed())
    assert elapsed.value_ns >= 0
    memory = _ok(probe.memory_bytes())
    assert memory > 0
