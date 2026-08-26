"""Story 21.5 — operator-terminated Study: clean stopped, one line per run (AC5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.orchestrator.watch import monotonic_ns
from qmb.runloop import STREAM_SET_KEY, CancelToken, SliceObservation
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_BOOT = "boot-1"
_MACHINE = "test-machine"


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
    stamp = _ok(fingerprint({"n": "study-stop", "tag": tag}))
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


def _sink(tmp_path: Path, *, slot: object = 0) -> qmb.LedgerSink:
    return _ok(
        qmb.LedgerSink.try_create(
            tmp_path / "ledger",
            machine=_MACHINE,
            worker_slot=slot,
            boot_epoch_id=_BOOT,
        )
    )


def _finished_run(config: ResolvedRunConfig, tmp_path: Path) -> qmb.LiveSpawn:
    """Start a run and wait for its process to finish so the stop collects it."""
    live = _ok(qmb.start_run(config=config, slices=_slices(), output_root=tmp_path))
    live.process.wait()
    return live


def _in_flight_run(config: ResolvedRunConfig, tmp_path: Path) -> qmb.LiveSpawn:
    """A long-running OS process the stop must abort into exactly one aborted line."""
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
        cancel=CancelToken(),
        limits=qmb.RunLimits(),
        started_monotonic_ns=monotonic_ns(),
    )


def test_stop_transitions_to_a_clean_stopped_state_with_one_line_per_run(tmp_path: Path) -> None:
    first = _config(tag="done-a")
    second = _config(tag="done-b")
    sink = _sink(tmp_path)
    live = [_finished_run(first, tmp_path), _finished_run(second, tmp_path)]
    outcome = _ok(qmb.stop_study(live, configs=[first, second], ledger=sink, role=qmb.ROLE_TRIAL))
    assert outcome.state == qmb.STUDY_STATE_STOPPED == "stopped"
    assert outcome.lines_appended == outcome.total_runs == 2
    assert set(outcome.completed) == {first.fingerprint, second.fingerprint}
    assert outcome.aborted == ()
    assert outcome.partial_preserved is True
    assert outcome.resumable is True

    # Exactly one ledger line per run — never zero, never two.
    lines = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_TRIAL))
    assert len(lines) == 2
    assert {line.run_id for line in lines} == {first.fingerprint, second.fingerprint}
    for line in lines:
        assert line.role == qmb.ROLE_TRIAL
        assert line.refusal is None
        assert line.ct32_fingerprint is not None


def test_stop_aborts_an_in_flight_run_into_exactly_one_aborted_line(tmp_path: Path) -> None:
    config = _config(tag="in-flight")
    sink = _sink(tmp_path)
    live = _in_flight_run(config, tmp_path)
    outcome = _ok(qmb.stop_study([live], configs={config.fingerprint.value: config}, ledger=sink))
    assert outcome.state == qmb.STUDY_STATE_STOPPED
    assert outcome.lines_appended == 1
    assert outcome.completed == ()
    assert outcome.aborted == (config.fingerprint,)

    aborted = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_ABORTED))
    assert len(aborted) == 1
    line = aborted[0]
    assert line.role == qmb.ROLE_ABORTED
    assert line.refusal is not None
    assert line.refusal["terminal"] == "aborted"
    # partial results of the ABORTED run are preserved in its own run room.
    assert Path(live.output_dir).is_dir()


def test_stop_mixes_completed_and_aborted_never_zero_never_two(tmp_path: Path) -> None:
    done = _config(tag="mix-done")
    flight = _config(tag="mix-flight")
    sink = _sink(tmp_path)
    live = [_finished_run(done, tmp_path), _in_flight_run(flight, tmp_path)]
    outcome = _ok(qmb.stop_study(live, configs=[done, flight], ledger=sink))
    assert outcome.completed == (done.fingerprint,)
    assert outcome.aborted == (flight.fingerprint,)
    assert outcome.lines_appended == 2

    trials = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_TRIAL))
    aborted = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_ABORTED))
    assert [line.run_id for line in trials] == [done.fingerprint]
    assert [line.run_id for line in aborted] == [flight.fingerprint]

    # Stopping again over the already-completed run does not append a second line.
    again = _ok(qmb.stop_study([live[0]], configs=[done], ledger=sink))
    assert again.lines_appended == 1
    still = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_TRIAL))
    assert len(still) == 1


def test_stop_refuses_when_a_spawned_runs_config_is_missing(tmp_path: Path) -> None:
    config = _config(tag="no-config")
    sink = _sink(tmp_path)
    live = _finished_run(config, tmp_path)
    refused = qmb.stop_study([live], configs=[], ledger=sink)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["run_id"] == config.fingerprint.value


def test_stop_outcome_identity_excludes_semver() -> None:
    outcome = qmb.StudyStopOutcome(
        state=qmb.STUDY_STATE_STOPPED,
        completed=(),
        aborted=(),
        lines_appended=0,
    )
    identity = outcome.fp1_identity()
    assert identity["class"] == qmb.STUDY_STOP_OUTCOME_CLASS
    assert identity["state"] == "stopped"
    assert qmb.__version__ not in identity.values()
    assert is_ok(fingerprint(identity))
