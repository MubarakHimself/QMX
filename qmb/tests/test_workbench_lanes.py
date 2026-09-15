"""Story 36.4 — three door-derived lanes and two honest workbench_lane labels."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.doors import api
from qmb.doors.cli.tree import invoke_backtest
from qmb.runloop import SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import PerformanceResult

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_STREAM = "eurusd"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(_STREAM, _instant(ns), True))


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs(),), (_obs(_NS + 1),))


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "workbench-lanes", "tag": tag}))
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={qmb.STREAM_SET_KEY: (_STREAM,)},
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
            machine="test-machine",
            worker_slot=slot,
            boot_epoch_id="boot-36-4",
        )
    )


def test_ungoverned_run_returns_values_and_writes_nothing(tmp_path: Path) -> None:
    identity = qmb.ungoverned_run_identity()
    assert identity["door"] == qmb.WORKBENCH_LANE_UNGOVERNED
    assert identity["writes_qmb_ledger"] is False
    assert identity["writes_ct32_registry_record"] is False
    assert identity["mints_experiment_spec"] is False
    assert identity["is_library_object"] is False
    assert identity["l33_graduation_is_this_spawn"] is False
    labels = _ok(qmb.door_derived_labels())
    assert labels.door == "ungoverned"
    assert labels.qmb_ledger_workbench_lane is None
    assert labels.experiment_ledger_workbench_lane is None
    assert labels.is_library_object is False

    config = _config(tag="ungoverned")
    outcome = _ok(run(slices=_slices(), config=config, handler=SilentSliceHandler()))
    assert outcome.writes_qmb_ledger is False
    assert outcome.writes_ct32_registry_record is False
    assert outcome.mints_experiment_spec is False
    assert outcome.is_library_object is False
    assert outcome.performance_result is not None
    assert isinstance(outcome.performance_result, PerformanceResult)
    cited = qmb.admit_library_object(outcome)
    assert is_refusal(cited)
    assert cited.context["is_library_object"] is False
    shaped = qmb.admit_library_object(outcome.performance_result)
    assert is_refusal(shaped)
    empty = tmp_path / "empty-ledger"
    empty.mkdir()
    lines = _ok(qmb.read_merge_view(empty, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION))
    assert lines == ()


def test_governed_orchestrator_stamps_workbench_lane_governed(tmp_path: Path) -> None:
    labels = _ok(qmb.door_derived_labels(orchestrator=True))
    assert labels.door == "governed"
    assert labels.qmb_ledger_workbench_lane == qmb.WORKBENCH_LANE_GOVERNED
    assert labels.experiment_ledger_workbench_lane is None
    assert labels.mints_experiment_spec is False
    assert labels.writes_qmb_ledger is True

    config = _config(tag="governed")
    sink = _sink(tmp_path)
    live = _ok(qmb.start_run(config=config, slices=_slices(), output_root=tmp_path))
    done = _ok(qmb.finish_run(live, config=config, ledger=sink, role=qmb.ROLE_CONFIRMATION))
    assert done.ct32_fingerprint is not None
    lines = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION))
    assert len(lines) == 1
    line = lines[0]
    assert line.workbench_lane == qmb.WORKBENCH_LANE_GOVERNED
    assert line.ct32_fingerprint == done.ct32_fingerprint
    assert "analysis_method" not in line.fp1_identity()
    assert "lane" not in line.fp1_identity()
    assert line.fp1_identity()["workbench_lane"] == "governed"


def test_qmb_ledger_refuses_coordinated_and_ungoverned_stamps() -> None:
    config = _config(tag="collapse")
    outcome = _ok(run(slices=_slices(), config=config, handler=SilentSliceHandler()))
    artifact = outcome.performance_result
    assert artifact is not None
    fp = _ok(artifact.fingerprint())
    coordinated = qmb.mint_completed_line(
        config,
        outcome_identity=outcome.fp1_identity(),
        ct32_fingerprint=fp,
        workbench_lane="coordinated",
    )
    assert is_refusal(coordinated)
    assert coordinated.category is RefusalCategory.POLICY_REJECTION
    ungoverned = qmb.mint_completed_line(
        config,
        outcome_identity=outcome.fp1_identity(),
        ct32_fingerprint=fp,
        workbench_lane="ungoverned",
    )
    assert is_refusal(ungoverned)


def test_caller_declared_lane_flags_are_refused(tmp_path: Path) -> None:
    run_flag = run(slices=_slices(), workbench_lane="governed")
    assert is_refusal(run_flag)
    assert run_flag.context["field"] == "workbench_lane"
    assert run_flag.context["spine_amendment"] is True
    method = run(slices=_slices(), analysis_method="rerun")
    assert is_refusal(method)
    spec = run(slices=_slices(), experiment_spec=True)
    assert is_refusal(spec)
    assert spec.context["mints_experiment_spec"] is False

    config = _config(tag="flag")
    sink = _sink(tmp_path)
    flagged = qmb.finish_run(
        object(),
        config=config,
        ledger=sink,
        workbench_lane="governed",
    )
    assert is_refusal(flagged)
    assert flagged.context["field"] == "workbench_lane"
    door = invoke_backtest(lane="governed")
    assert is_refusal(door)
    spec_door = invoke_backtest(experiment_spec=True)
    assert is_refusal(spec_door)
    derived = qmb.door_derived_labels(orchestrator=True, lane="governed")
    assert is_refusal(derived)


def test_l33_graduation_is_not_this_spawn() -> None:
    refused = qmb.graduate_ungoverned_via_spawn()
    assert is_refusal(refused)
    assert refused.context["is_this_spawn"] is False
    assert refused.context["is_workbench_lane"] is False
    assert qmb.L33_GRADUATION_IS_THIS_SPAWN is False
    registry = qmb.admit_library_object({"class": "performance-result"}, registry_record=True)
    assert is_ok(registry)
    assert registry.value.contract == "CT-32"


def test_api_reexports_workbench_door() -> None:
    assert api.door_derived_labels is qmb.door_derived_labels
    assert api.ungoverned_run_identity is qmb.ungoverned_run_identity
    assert api.graduate_ungoverned_via_spawn is qmb.graduate_ungoverned_via_spawn
    assert api.admit_library_object is qmb.admit_library_object
    assert qmb.ledger_identity()["workbench_lane"] == qmb.WORKBENCH_LANE_GOVERNED
    assert qmb.QMB_LEDGER_WORKBENCH_LANE == "governed"
