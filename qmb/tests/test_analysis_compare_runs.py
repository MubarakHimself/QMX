"""Story 35.5 — compare_runs is readout; labels stay parent-shaped."""

from __future__ import annotations

import ast
import inspect
import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

import pytest
from click.testing import CliRunner
from qmb.analysis import compare_runs, project, rerun
from qmb.config import ResolvedRunConfig
from qmb.doors import api, flatten_capabilities, required_library_names
from qmb.doors.cli import (
    COMPARE_RUNS_OCCUPANCY,
    analysis_command_occupancy,
    command_tree,
    invoke_compare_runs,
    main,
)
from qmb.doors.cli import tree as cli_tree
from qmb.ledger.line import LedgerLine
from qmb.results import ClosedTrade, TradeSide, mint_run_performance_result
from qmb.results.ct32 import load_stored_ct32
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.exact import Money
from qmf.core.fingerprint import ResultLabel, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import PerformanceResult

import qmb

T = TypeVar("T")

_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_REPO = Path(__file__).resolve().parents[2]
_NS = 1_700_000_000_000_000_000
_BANNED_SHAPE_FIELDS = ("analysis_method", "lane")
_WORKBENCH_FIELDS = ("analysis_method", "lane", "workbench_lane")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _at(*, day: int = 15, hour: int = 10) -> Instant:
    stamp = datetime(2023, 11, day, hour, 0, tzinfo=timezone.utc)
    return _instant(int(stamp.timestamp()) * 1_000_000_000)


def _money(value: int) -> Money:
    return _ok(Money.try_create(value, "USD", 2))


def _trade(*, hour: int, pnl: int = 100) -> ClosedTrade:
    return _ok(ClosedTrade.try_create(_money(pnl), _money(0), TradeSide.LONG, _at(hour=hour)))


def _obs(stream_id: str = "eurusd", ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def _config(*, tag: str, registry_as_of: Instant | None = None) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "analysis-compare", "tag": tag}))
    keys: dict[str, object] = {STREAM_SET_KEY: ("eurusd",)}
    if registry_as_of is not None:
        keys["registry_as_of"] = registry_as_of
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=keys,
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs(),), (_obs(ns=_NS + 1),))


def _result(*, tag: str, trades: tuple[ClosedTrade, ...] = ()) -> PerformanceResult:
    config = _config(tag=tag, registry_as_of=_at(hour=0))
    outcome = _ok(run(slices=_slices(), config=config, handler=SilentSliceHandler()))
    return _ok(
        mint_run_performance_result(
            config,
            evidence_range=outcome.evidence_range,
            stream_order=outcome.stream_order,
            slice_count=2,
            filled_count=0,
            resting_count=0,
            data_points_processed=2,
            outcome_identity=outcome.fp1_identity(),
            trades=trades,
        )
    )


def _sink(tmp_path: Path, *, slot: object = 0) -> qmb.LedgerSink:
    return _ok(
        qmb.LedgerSink.try_create(
            tmp_path / "ledger",
            machine="test-machine",
            worker_slot=slot,
            boot_epoch_id="boot-1",
        )
    )


def test_compare_runs_identity_is_a_query_readout_not_a_method() -> None:
    identity = qmb.compare_runs_identity()
    assert identity["occupancy"] == COMPARE_RUNS_OCCUPANCY == "query"
    assert identity["mints_ct32"] is qmb.COMPARE_RUNS_MINTS_CT32 is False
    assert identity["mints_experiment_spec"] is qmb.COMPARE_RUNS_MINTS_EXPERIMENT_SPEC is False
    assert identity["is_analysis_method"] is qmb.COMPARE_RUNS_IS_ANALYSIS_METHOD is False
    assert identity["appends_ledger"] is False
    assert "confirmation_label" not in identity
    assert "analysis_method" not in identity
    assert "lane" not in identity
    assert identity["command"] == "compare_runs"
    assert qmb.__version__ not in identity.values()
    assert _ok(analysis_command_occupancy("compare")) == "query"
    assert _ok(analysis_command_occupancy("compare_runs")) == "query"
    assert _ok(analysis_command_occupancy("analysis.compare")) == "query"
    assert _ok(analysis_command_occupancy("project")) == "query"
    assert _ok(analysis_command_occupancy("rerun")) == "run"


def test_compare_runs_reads_cited_fields_and_mints_nothing(tmp_path: Path) -> None:
    left = _result(tag="left", trades=(_trade(hour=10),))
    right = _result(tag="right", trades=(_trade(hour=11),))
    ledger: list[object] = []
    readout = _ok(compare_runs(left, right))
    assert readout.occupancy == "query"
    assert readout.mints_ct32 is False
    assert readout.mints_experiment_spec is False
    assert readout.appends_ledger is False
    assert readout.confirmation_label is None
    assert readout.is_analysis_method is False
    assert readout.is_admission_evidence is False
    assert readout.b4_role is None
    assert readout.consumes_occupancy is False
    assert readout.same_world is True
    assert readout.source == "ct-32"
    assert readout.publish_only is True
    paths = {row.path for row in readout.differing}
    assert paths
    assert list(tmp_path.iterdir()) == []
    assert ledger == []
    same = _ok(compare_runs(left, left))
    assert same.differing == ()
    assert same.same_world is True
    assert is_refusal(compare_runs(left, right, occupancy="run"))
    assert is_refusal(compare_runs(left, right, mint_ct32=True))
    assert is_refusal(compare_runs(left, right, ledger=True))
    assert is_refusal(compare_runs(left, right, role="confirmation"))
    assert is_refusal(compare_runs(left, right, confirmation_label=True))
    assert is_refusal(compare_runs(left, right, analysis_method="compare"))
    assert is_refusal(compare_runs(left, right, lane="governed"))


def test_projection_has_no_b4_role_inherits_world_never_confirmed() -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(tag="proj", trades=trades)
    view = _ok(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
        )
    )
    assert view.b4_role is None
    assert view.claim_class == qmb.CLAIM_CLASS_PROJECTION == "projection"
    assert view.world == World.REPLAY.value == artifact.result_label.world.value
    assert view.confirmed is False
    assert view.is_admission_evidence is False
    assert "role" not in view.body()
    assert "world" not in view.body()
    assert is_refusal(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
            confirmed=True,
        )
    )
    assert is_refusal(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
            evidence_class="confirmed",
        )
    )
    gated = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"max_trades": 1},
        as_of=as_of,
        gating_live=True,
    )
    assert is_refusal(gated)
    assert gated.category is RefusalCategory.POLICY_REJECTION
    assert gated.context["law"] == "L20"
    assert gated.context["world"] == World.REPLAY.value
    assert is_refusal(compare_runs(artifact, artifact, gating_live=True))


def test_rerun_b4_role_is_the_role_of_that_run(tmp_path: Path) -> None:
    source = _result(tag="source")
    confirmation = _ok(
        rerun(
            source_ct32=source,
            config=_config(tag="confirm"),
            slices=_slices(),
            output_root=tmp_path / "confirm",
            ledger=_sink(tmp_path, slot=0),
        )
    )
    assert confirmation.b4_role == qmb.ROLE_CONFIRMATION
    assert confirmation.is_admission_evidence is True
    stored = _ok(load_stored_ct32(confirmation.isolated.output_dir))
    for field in _WORKBENCH_FIELDS:
        assert field not in stored
    trial = _ok(
        rerun(
            source_ct32=source,
            config=_config(tag="trial"),
            slices=_slices(),
            output_root=tmp_path / "trial",
            ledger=_sink(tmp_path, slot=1),
            role=qmb.ROLE_TRIAL,
        )
    )
    assert trial.b4_role == qmb.ROLE_TRIAL == "trial"
    assert trial.is_admission_evidence is False
    assert trial.ledger_line.role == "trial"
    trial_stored = _ok(load_stored_ct32(trial.isolated.output_dir))
    for field in _WORKBENCH_FIELDS:
        assert field not in trial_stored
    assert "role" not in trial_stored
    readout = _ok(compare_runs(source, _ok(load_stored_ct32(trial.isolated.output_dir))))
    assert readout.same_world is True
    assert readout.confirmation_label is None
    assert readout.b4_role is None


def test_ct32_and_b4_gain_no_workbench_fields() -> None:
    contract = (_REPO / "docs" / "contracts" / "ct-32-performance-result.yaml").read_text(
        encoding="utf-8"
    )
    assert "analysis_method" not in contract
    assert "workbench_lane" not in contract
    for field in _BANNED_SHAPE_FIELDS:
        assert field not in ResultLabel.__dataclass_fields__
        assert field not in PerformanceResult.__dataclass_fields__
        assert field not in LedgerLine.__dataclass_fields__
    assert "workbench_lane" not in ResultLabel.__dataclass_fields__
    assert "workbench_lane" not in PerformanceResult.__dataclass_fields__
    assert "analysis_method" not in qmb.ledger_identity()
    assert "analysis_method" not in qmb.result_identity()


def test_f07_synthetic_portfolio_is_refused_as_deferred(tmp_path: Path) -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(tag="f07", trades=trades)
    projected = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"max_trades": 1},
        as_of=as_of,
        portfolio=True,
    )
    assert is_refusal(projected)
    assert projected.category is RefusalCategory.POLICY_REJECTION
    assert projected.context["feature"] == qmb.F07_FEATURE == "F07"
    assert projected.context["deferred"] is True
    assert projected.context["implements_project"] is False
    assert projected.context["implements_rerun"] is False
    path_dependent = rerun(
        source_ct32=artifact,
        config=_config(tag="f07-rerun"),
        slices=_slices(),
        output_root=tmp_path / "f07",
        ledger=_sink(tmp_path),
        synthetic_portfolio=True,
    )
    assert is_refusal(path_dependent)
    assert path_dependent.context["feature"] == "F07"
    compared = compare_runs(artifact, artifact, combine=True)
    assert is_refusal(compared)
    assert compared.context["deferred"] is True
    assert "F07" in str(compared.context["reason"])


def test_python_api_and_cli_are_thin_doors() -> None:
    left = _result(tag="door-left")
    right = _result(tag="door-right")
    library = compare_runs(left, right)
    door = invoke_compare_runs(left=left, right=right)
    assert is_ok(library) and is_ok(door)
    assert door.value.fp1_identity() == library.value.fp1_identity()
    assert api.compare_runs is qmb.compare_runs
    assert api.compare_runs_identity is qmb.compare_runs_identity
    assert "compare_runs" in required_library_names()
    assert "analysis.compare" in flatten_capabilities()
    assert command_tree()["analysis"] == ("project", "rerun", "compare")
    tree = ast.parse(textwrap.dedent(inspect.getsource(invoke_compare_runs)))
    names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "compare_runs" in names
    runner = CliRunner()
    helped = runner.invoke(main, ["analysis", "--help"])
    assert helped.exit_code == 0, helped.output
    assert "compare" in helped.output
    compare_help = runner.invoke(main, ["analysis", "compare", "--help"])
    assert compare_help.exit_code == 0, compare_help.output
    assert "query" in compare_help.output.lower() or "readout" in compare_help.output.lower()
    clicked = runner.invoke(
        main,
        ["analysis", "compare"],
        obj={"left": left, "right": right},
    )
    assert clicked.exit_code == 0, clicked.output
    payload = json.loads(clicked.stdout)
    assert payload["occupancy"] == "query"
    assert payload["mints_ct32"] is False
    assert payload["is_analysis_method"] is False
    assert "confirmation_label" not in payload
    assert "analysis_method" not in payload
    assert "lane" not in payload
    occupied = runner.invoke(
        main,
        ["analysis", "compare", "--occupancy", "run"],
        obj={"left": left, "right": right},
    )
    assert occupied.exit_code != 0
    portfolio = runner.invoke(
        main,
        ["analysis", "compare", "--portfolio"],
        obj={"left": left, "right": right},
    )
    assert portfolio.exit_code != 0


def test_door_calls_the_library_not_a_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    calls: list[str] = []

    def _record(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        calls.append("compare_runs")
        from qmf.core.refusal import Ok

        return Ok(sentinel)

    monkeypatch.setattr(cli_tree, "compare_runs", _record)
    result = invoke_compare_runs(left=1, right=1)
    assert is_ok(result)
    assert result.value is sentinel
    assert calls == ["compare_runs"]


def test_module_does_not_open_sqlite_or_import_qma() -> None:
    source = (_SRC / "analysis" / "compare.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".", 1)[0])
    assert "qma" not in imported
    assert "sqlite3" not in imported
    assert "qmx-agents" not in source
