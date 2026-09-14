"""Story 35.2 — forbidden projection axes refuse; ungoverned and governed homes."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

import pytest
from click.testing import CliRunner
from qmb.analysis import (
    FORBIDDEN_PROJECTION_AXES,
    PROJECTION_HOMES,
    PROJECTION_SIDECAR_FILENAME,
    project,
)
from qmb.config import ResolvedRunConfig
from qmb.doors.cli import invoke_analysis_project, main
from qmb.results import ClosedTrade, TradeSide, mint_run_performance_result
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.exact import Money
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_NS = 1_700_000_000_000_000_000
_FORBIDDEN_CASES: tuple[tuple[str, object, str], ...] = (
    ("size", 2, "size"),
    ("r", 1, "R"),
    ("book", "fp1:book", "Book/BMS fragments"),
    ("bms", "fp1:bms", "Book/BMS fragments"),
    ("book_fragment", {"patch": True}, "Book/BMS fragments"),
    ("ports", "fill", "execution ports"),
    ("execution_ports", True, "execution ports"),
    ("starting_capital", 10_000, "starting_capital"),
    ("lot_size", 1, "size"),
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _at(*, hour: int = 10) -> Instant:
    stamp = datetime(2023, 11, 15, hour, 0, tzinfo=timezone.utc)
    return _instant(int(stamp.timestamp()) * 1_000_000_000)


def _money(value: int) -> Money:
    return _ok(Money.try_create(value, "USD", 2))


def _trade(*, hour: int) -> ClosedTrade:
    return _ok(ClosedTrade.try_create(_money(100), _money(0), TradeSide.LONG, _at(hour=hour)))


def _obs(ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create("eurusd", _instant(ns), True))


def _config(*, registry_as_of: Instant) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "analysis-project-homes", "as_of": registry_as_of.value_ns}))
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",), "registry_as_of": registry_as_of},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _result(*, registry_as_of: Instant, trades: tuple[ClosedTrade, ...]) -> object:
    config = _config(registry_as_of=registry_as_of)
    outcome = _ok(
        run(
            slices=((_obs(_NS),), (_obs(_NS + 1),)),
            config=config,
            handler=SilentSliceHandler(),
        )
    )
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


def _project_args(
    artifact: object, trades: tuple[ClosedTrade, ...], as_of: Instant
) -> dict[str, object]:
    return {
        "source_ct32": artifact,
        "source_ct29": trades,
        "predicate": {"max_trades": 1},
        "as_of": as_of,
    }


@pytest.mark.parametrize(("key", "value", "axis"), _FORBIDDEN_CASES)
def test_forbidden_predicate_axis_is_path_dependent_refusal(
    key: str,
    value: object,
    axis: str,
) -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    refused = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={key: value},
        as_of=as_of,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["axis"] == axis
    assert refused.context["path_dependent"] is True
    assert refused.context["mints_ct32"] is False
    assert refused.context["implements_rerun"] is False
    reason = str(refused.context["reason"])
    assert axis in reason
    assert "path-dependent" in reason
    assert "new CT-32" in reason


@pytest.mark.parametrize(("key", "value", "axis"), _FORBIDDEN_CASES)
def test_forbidden_extra_field_is_path_dependent_refusal(
    key: str,
    value: object,
    axis: str,
) -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    refused = project(**_project_args(artifact, trades, as_of), **{key: value})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["axis"] == axis
    assert refused.context["field"] == key
    assert refused.context["path_dependent"] is True
    assert "path-dependent" in str(refused.context["reason"])
    assert refused.context["implements_rerun"] is False


def test_mixed_permitted_and_forbidden_predicate_still_refuses() -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    refused = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"hours": {"start": 8, "end": 16}, "starting_capital": 1},
        as_of=as_of,
    )
    assert is_refusal(refused)
    assert refused.context["axis"] == "starting_capital"
    kind = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"kind": "size", "value": 2},
        as_of=as_of,
    )
    assert is_refusal(kind)
    assert kind.context["axis"] == "size"


def test_ungoverned_home_is_a_return_value_only(tmp_path: Path) -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    view = _ok(project(**_project_args(artifact, trades, as_of)))
    assert view.home == "ungoverned"
    assert view.durable is False
    assert view.is_library_object is False
    assert view.path is None
    assert view.opens_sqlite is False
    assert view.spawns_orchestrator is False
    assert view.appends_ledger is False
    assert view.mints_ct32 is False
    assert list(tmp_path.iterdir()) == []
    explicit = _ok(
        project(**_project_args(artifact, trades, as_of), home="ungoverned", run_dir=tmp_path)
    )
    assert explicit.durable is False
    assert explicit.path is None
    assert list(tmp_path.iterdir()) == []
    identity = qmb.analysis_project_identity()
    assert identity["homes"] == list(PROJECTION_HOMES)
    assert identity["forbidden_axes"] == list(FORBIDDEN_PROJECTION_AXES)
    assert identity["is_library_object"] is False
    assert identity["opens_sqlite"] is False
    assert identity["ungoverned_durable"] is False
    assert identity["sidecar_filename"] == PROJECTION_SIDECAR_FILENAME


def test_governed_home_writes_json_sidecar_in_source_run_dir(tmp_path: Path) -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    source = tmp_path / "source-run"
    source.mkdir()
    other = tmp_path / "new-run"
    view = _ok(
        project(
            **_project_args(artifact, trades, as_of),
            home="governed-without-qma",
            run_dir=source,
        )
    )
    sidecar = source / PROJECTION_SIDECAR_FILENAME
    assert view.home == "governed"
    assert view.durable is True
    assert view.is_library_object is False
    assert view.path == str(sidecar)
    assert view.mints_ct32 is False
    assert view.spawns_orchestrator is False
    assert view.appends_ledger is False
    assert view.opens_sqlite is False
    assert sidecar.is_file()
    assert not other.exists()
    assert [path.name for path in source.iterdir()] == [PROJECTION_SIDECAR_FILENAME]
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload == view.body()
    assert set(payload) == {"method", "source_ct32", "source_ct29", "predicate", "as_of"}
    assert payload["method"] == "projection"
    missing = project(**_project_args(artifact, trades, as_of), home="governed")
    assert is_refusal(missing)
    assert missing.context["field"] == "run_dir"
    assert missing.context["spawns_orchestrator"] is False


def test_coordinated_home_and_sqlite_are_epic_36(tmp_path: Path) -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    refused = project(
        **_project_args(artifact, trades, as_of),
        home="coordinated",
        run_dir=tmp_path,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["epic"] == "36"
    assert refused.context["opens_sqlite"] is False
    assert refused.context["mints_ct32"] is False
    assert refused.context["spawns_orchestrator"] is False
    assert list(tmp_path.iterdir()) == []
    sqlite = project(**_project_args(artifact, trades, as_of), sqlite=True)
    assert is_refusal(sqlite)
    assert sqlite.context["opens_sqlite"] is False
    spawned = project(**_project_args(artifact, trades, as_of), spawn_run=True)
    assert is_refusal(spawned)
    assert spawned.context["spawns_orchestrator"] is False
    assert spawned.context["implements_rerun"] is False


def test_door_and_cli_forward_homes_and_forbidden_axes(tmp_path: Path) -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    library = project(**_project_args(artifact, trades, as_of), home="ungoverned")
    door = invoke_analysis_project(
        **_project_args(artifact, trades, as_of),
        home="ungoverned",
    )
    assert is_ok(library) and is_ok(door)
    assert door.value.body() == library.value.body()
    assert door.value.home == "ungoverned"
    extra = invoke_analysis_project(
        **_project_args(artifact, trades, as_of),
        starting_capital=10_000,
    )
    assert is_refusal(extra)
    assert extra.context["axis"] == "starting_capital"
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["analysis", "project", "--home", "governed-without-qma", "--run-dir", str(tmp_path)],
        obj=_project_args(artifact, trades, as_of),
    )
    assert clicked.exit_code == 0, clicked.output
    payload = json.loads(clicked.stdout)
    assert payload["method"] == "projection"
    sidecar = tmp_path / PROJECTION_SIDECAR_FILENAME
    assert sidecar.is_file()
    assert json.loads(sidecar.read_text(encoding="utf-8")) == payload
    forbidden = runner.invoke(
        main,
        ["analysis", "project"],
        obj={**_project_args(artifact, trades, as_of), "size": 2},
    )
    assert forbidden.exit_code != 0
    assert "path-dependent" in forbidden.output


def test_module_does_not_open_sqlite_spawn_or_import_qma() -> None:
    source = (_SRC / "analysis" / "project.py").read_text(encoding="utf-8")
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
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "spawn_run" not in called
    assert "sqlite3" not in called
