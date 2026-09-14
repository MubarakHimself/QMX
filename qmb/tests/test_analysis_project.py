"""Story 35.1 — analysis.project returns the canonical saved-view JSON."""

from __future__ import annotations

import ast
import inspect
import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar, cast

import pytest
from click.testing import CliRunner
from qmb.analysis import apply_projection_predicate, cite_projection, project
from qmb.config import ResolvedRunConfig
from qmb.doors import api, flatten_capabilities, required_library_names
from qmb.doors.cli import (
    ANALYSIS_PROJECT_OCCUPANCY,
    command_tree,
    invoke_analysis_project,
    main,
)
from qmb.doors.cli import tree as cli_tree
from qmb.results import ClosedTrade, TradeSide, mint_run_performance_result
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.exact import Money
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import PerformanceResult

import qmb

T = TypeVar("T")

_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_NS = 1_700_000_000_000_000_000


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


def _trade(*, hour: int, pnl: int = 100, day: int = 15) -> ClosedTrade:
    return _ok(
        ClosedTrade.try_create(_money(pnl), _money(0), TradeSide.LONG, _at(day=day, hour=hour))
    )


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def _config(*, registry_as_of: Instant) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "analysis-project-cfg", "as_of": registry_as_of.value_ns}))
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


def _result(
    *,
    registry_as_of: Instant,
    trades: tuple[ClosedTrade, ...] = (),
) -> PerformanceResult:
    config = _config(registry_as_of=registry_as_of)
    outcome = _ok(
        run(
            slices=((_obs("eurusd", _NS),), (_obs("eurusd", _NS + 1),)),
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


def test_project_returns_canonical_json_and_fp1_of_that_json() -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10), _trade(hour=18))
    artifact = _result(registry_as_of=as_of, trades=trades)
    view = _ok(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"hours": {"start": 8, "end": 16}},
            as_of=as_of,
        )
    )
    body = view.body()
    assert set(body) == {"method", "source_ct32", "source_ct29", "predicate", "as_of"}
    assert body["method"] == qmb.METHOD_PROJECTION == "projection"
    assert body["source_ct32"] == _ok(artifact.fingerprint()).value
    assert body["source_ct29"] == artifact.trade_event_references[0]
    assert body["predicate"] == {"hours": {"end": 16, "start": 8}}
    assert body["as_of"] == as_of.fp1_identity()
    assert "trades" not in body
    assert "trade_list" not in body
    stamped = _ok(fingerprint(body))
    assert view.fingerprint == stamped
    assert view.fp1_identity() == body
    assert view.matched_count == 1
    identity = qmb.analysis_project_identity()
    assert identity["occupancy"] == ANALYSIS_PROJECT_OCCUPANCY == "query"
    assert identity["mints_ct32"] is False
    assert identity["mints_experiment_spec"] is False
    assert identity["claim_class"] == qmb.CLAIM_CLASS_PROJECTION
    assert identity["is_admission_evidence"] is False
    assert view.b4_role is None
    assert qmb.__version__ not in identity.values()


def test_as_of_is_source_registry_as_of_never_query_time() -> None:
    as_of = _at(hour=0)
    later = _at(hour=12)
    artifact = _result(registry_as_of=as_of, trades=(_trade(hour=10),))
    ok = _ok(
        project(
            source_ct32=artifact,
            source_ct29=(_trade(hour=10),),
            predicate={"max_trades": 1},
            as_of=as_of,
        )
    )
    assert ok.as_of["value_ns"] == as_of.value_ns
    refused = project(
        source_ct32=artifact,
        source_ct29=(_trade(hour=10),),
        predicate={"max_trades": 1},
        as_of=later,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert "query time" in str(refused.context["reason"])
    missing = project(
        source_ct32=artifact,
        source_ct29=(_trade(hour=10),),
        predicate={"max_trades": 1},
    )
    # Config Instant is recoverable from the PerformanceResult only via as_of/config.
    assert is_refusal(missing)
    via_config = _ok(
        project(
            source_ct32=artifact,
            source_ct29=(_trade(hour=10),),
            predicate={"max_trades": 1},
            config=_config(registry_as_of=as_of),
        )
    )
    assert via_config.as_of == as_of.fp1_identity()


def test_permitted_predicates_filter_the_ct29_stream() -> None:
    as_of = _at(hour=0)
    keep = _trade(hour=10, day=15)
    drop_hour = _trade(hour=18, day=15)
    drop_day = _trade(hour=10, day=16)
    trades = (keep, drop_hour, drop_day)
    artifact = _result(registry_as_of=as_of, trades=trades)
    hours = _ok(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"hours": {"start": 8, "end": 16}},
            as_of=as_of,
        )
    )
    assert hours.matched_count == 2
    days = _ok(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"days": ["wednesday"]},
            as_of=as_of,
        )
    )
    assert days.matched_count == 2
    session = _ok(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"session": {"start": 8, "end": 16, "name": "london"}},
            as_of=as_of,
        )
    )
    assert session.matched_count == 2
    predicate = cast("dict[str, object]", session.body()["predicate"])
    window = cast("dict[str, object]", predicate["session"])
    assert window["name"] == "london"
    capped = _ok(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
        )
    )
    assert capped.matched_count == 1
    cited_rows = (
        {"cite": "keep-1", "closed_at": _at(hour=10)},
        {"cite": "drop-1", "closed_at": _at(hour=10)},
    )
    included = _ok(
        project(
            source_ct32=artifact,
            source_ct29=cited_rows,
            predicate={"include": ["keep-1"]},
            as_of=as_of,
        )
    )
    assert included.matched_count == 1
    excluded = _ok(
        project(
            source_ct32=artifact,
            source_ct29=cited_rows,
            predicate={"exclude": ["keep-1"]},
            as_of=as_of,
        )
    )
    assert excluded.matched_count == 1
    filtered = _ok(apply_projection_predicate(cited_rows, {"include": ["keep-1"]}))
    assert len(filtered) == 1


def test_no_ct32_ledger_spec_or_occupancy_and_claim_class_is_projection(
    tmp_path: Path,
) -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    ledger: list[object] = []
    view = _ok(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 3},
            as_of=as_of,
        )
    )
    assert view.occupancy == "query"
    assert view.mints_ct32 is False
    assert view.mints_experiment_spec is False
    assert view.claim_class == "projection"
    assert view.is_admission_evidence is False
    assert view.b4_role is None
    assert list(tmp_path.iterdir()) == []
    assert ledger == []
    assert is_refusal(project(source_ct32=artifact, occupancy="run"))
    assert is_refusal(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
            mint_ct32=True,
        )
    )
    assert is_refusal(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
            ledger=True,
        )
    )
    assert is_refusal(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
            experiment_spec=True,
        )
    )
    assert is_refusal(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
            role="confirmation",
        )
    )
    assert is_refusal(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
            admission=True,
        )
    )
    assert is_refusal(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"starting_capital": 10_000},
            as_of=as_of,
        )
    )


def test_citation_without_json_body_and_copied_trade_list_are_refused() -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    view = _ok(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
        )
    )
    restored = _ok(cite_projection(body=view.body()))
    assert restored.fingerprint == view.fingerprint
    cited = cite_projection(cite=view.fingerprint.value)
    assert is_refusal(cited)
    assert cited.category is RefusalCategory.POLICY_REJECTION
    assert "without that JSON body" in str(cited.context["reason"])
    empty = cite_projection(body={})
    assert is_refusal(empty)
    copied = cite_projection(body={**view.body(), "trades": [{"pnl": 1}]})
    assert is_refusal(copied)
    assert "copied trade list" in str(copied.context["reason"])
    listed = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"max_trades": 1},
        as_of=as_of,
        trades=True,
    )
    assert is_refusal(listed)
    via_project = project(cite=view.fingerprint.value)
    assert is_refusal(via_project)


def test_python_api_and_cli_are_thin_doors() -> None:
    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(registry_as_of=as_of, trades=trades)
    library = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"max_trades": 1},
        as_of=as_of,
    )
    door = invoke_analysis_project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"max_trades": 1},
        as_of=as_of,
    )
    assert is_ok(library) and is_ok(door)
    assert door.value.body() == library.value.body()
    assert api.project is qmb.project
    assert api.cite_projection is qmb.cite_projection
    assert api.apply_projection_predicate is qmb.apply_projection_predicate
    assert "project" in required_library_names()
    assert "analysis.project" in flatten_capabilities()
    assert command_tree()["analysis"] == ("project", "rerun", "compare")
    tree = ast.parse(textwrap.dedent(inspect.getsource(invoke_analysis_project)))
    names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "project" in names
    runner = CliRunner()
    helped = runner.invoke(main, ["analysis", "--help"])
    assert helped.exit_code == 0, helped.output
    assert "project" in helped.output
    assert "query" in helped.output.lower()
    project_help = runner.invoke(main, ["analysis", "project", "--help"])
    assert project_help.exit_code == 0, project_help.output
    assert "--hours" in project_help.output
    assert "--max-trades" in project_help.output
    clicked = runner.invoke(
        main,
        ["analysis", "project", "--hours", "8-16"],
        obj={
            "source_ct32": artifact,
            "source_ct29": trades,
            "as_of": as_of,
        },
    )
    assert clicked.exit_code == 0, clicked.output
    payload = json.loads(clicked.stdout)
    assert payload["method"] == "projection"
    assert payload["as_of"]["value_ns"] == as_of.value_ns
    cite_only = runner.invoke(main, ["analysis", "project", "--cite", "fp1:missing"])
    assert cite_only.exit_code != 0
    copied = runner.invoke(
        main,
        ["analysis", "project", "--trades"],
        obj={"source_ct32": artifact, "source_ct29": trades, "as_of": as_of, "predicate": True},
    )
    assert copied.exit_code != 0


def test_door_calls_the_library_not_a_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    calls: list[str] = []

    def _record(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        calls.append("project")
        from qmf.core.refusal import Ok

        return Ok(sentinel)

    monkeypatch.setattr(cli_tree, "project", _record)
    result = invoke_analysis_project(
        source_ct32=1,
        source_ct29=1,
        predicate=1,
    )
    assert is_ok(result)
    assert result.value is sentinel
    assert calls == ["project"]


def test_module_does_not_open_sqlite_or_import_qma() -> None:
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
    assert "datetime.now" not in source
