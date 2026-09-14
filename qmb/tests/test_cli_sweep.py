"""Story 33.2 — thin qmb sweep batch (run) and rank (query) CLI over Epic 20."""

from __future__ import annotations

import ast
import inspect
import json
import textwrap
from collections.abc import Callable
from typing import TypeVar, cast

import pytest
from click.testing import CliRunner
from qmb.doors import MCP_IN_DOOR_SET, api, flatten_capabilities, required_library_names
from qmb.doors.cli import (
    SWEEP_BATCH_OCCUPANCY,
    SWEEP_COMMANDS,
    SWEEP_RANK_OCCUPANCY,
    invoke_sweep_batch,
    invoke_sweep_rank,
    main,
)
from qmb.doors.cli import tree as cli_tree
from qmb.doors.cli.tree import command_tree
from qmb.ledger import LedgerLine
from qmb.results import emit_measure
from qmb.sweep import (
    BATCH_ONE_LINE_PER_COMBO,
    RANKING_CLASS,
    SweepBatchReport,
    SweepRanking,
    rank_sweep,
)
from qmf.core.exact import Money
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_SWEEP_A = fingerprint({"class": "sweep", "id": "cli-sweep-a"})
_BAR = fingerprint({"class": "book-bar", "id": "cli-bar-1"})
_BAR_SPEC = {"kind": "time-interval", "seconds": 60}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(*parts: object) -> Fingerprint:
    return _ok(fingerprint({"parts": list(parts)}))


def _sweep_id() -> Fingerprint:
    return _ok(_SWEEP_A)


def _coordinates(sweep_id: Fingerprint, instrument: str, param: str) -> dict[str, object]:
    return {
        "bar_spec": _BAR_SPEC,
        "class": "qmb-sweep-coordinates",
        "format_version": 1,
        "instrument": instrument,
        "param_hash": _fp("param", param).value,
        "sweep_id": sweep_id.value,
    }


def _net_profit(minor: int) -> dict[str, object]:
    quantity = Money(value=minor, currency="USD", scale=2)
    return _ok(emit_measure("net_profit", quantity)).fp1_identity()


def _completed(run: str, *, sweep_id: Fingerprint, minor: int) -> LedgerLine:
    return LedgerLine(
        run_id=_fp("run", run),
        role="confirmation",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value, "run": run},
        book_bar_fp1=_ok(_BAR),
        measures=(_net_profit(minor),),
        ct32_fingerprint=_fp("ct32", run),
        sweep_coordinates=_coordinates(sweep_id, "EURUSD", run),
    )


def _lines() -> list[LedgerLine]:
    sweep_id = _sweep_id()
    return [
        _completed("c1", sweep_id=sweep_id, minor=3000),
        _completed("c2", sweep_id=sweep_id, minor=1000),
        _completed("c3", sweep_id=sweep_id, minor=2000),
    ]


def test_command_tree_exposes_batch_and_rank() -> None:
    tree = command_tree()
    assert tree["sweep"] == SWEEP_COMMANDS == ("count", "batch", "rank")
    catalog = set(flatten_capabilities())
    assert "sweep.batch" in catalog
    assert "sweep.rank" in catalog
    assert "sweep.count" in catalog


def test_cli_help_lists_batch_and_rank() -> None:
    runner = CliRunner()
    top = runner.invoke(main, ["--help"])
    assert top.exit_code == 0, top.output
    assert "sweep" in top.output
    helped = runner.invoke(main, ["sweep", "--help"])
    assert helped.exit_code == 0, helped.output
    for sub in SWEEP_COMMANDS:
        assert sub in helped.output
    rank_help = runner.invoke(main, ["sweep", "rank", "--help"])
    assert rank_help.exit_code == 0, rank_help.output
    lowered = rank_help.output.lower()
    assert "fold" in lowered
    assert "--persist" in lowered
    assert "candidate" in lowered
    assert "database" in lowered


def test_python_api_reexports_the_epic_20_library() -> None:
    names = ("run_sweep_batch", "rank_sweep", "preflight_run_count")
    required = required_library_names()
    for name in names:
        assert name in required
        assert getattr(api, name) is getattr(qmb, name)
        assert name in api.__all__
        assert name in qmb.__all__
    assert MCP_IN_DOOR_SET is False


def test_occupancy_batch_is_run_rank_is_query() -> None:
    assert SWEEP_BATCH_OCCUPANCY == "run"
    assert SWEEP_RANK_OCCUPANCY == "query"
    assert BATCH_ONE_LINE_PER_COMBO is True
    assert qmb.BATCH_ONE_LINE_PER_COMBO is True


def test_rank_adapter_equals_the_library() -> None:
    lines = _lines()
    sweep_id = _sweep_id()
    library = rank_sweep(lines, sweep_id=sweep_id, objective="net_profit", world=World.REPLAY)
    door = invoke_sweep_rank(
        lines=lines, sweep_id=sweep_id, objective="net_profit", world=World.REPLAY
    )
    assert door == library
    assert is_ok(door)
    ranking = _ok(door)
    assert isinstance(ranking, SweepRanking)
    assert ranking.adds_computation is False
    assert ranking.publishes_never_acts is True
    assert ranking.ranked_count == 3


def test_adapters_call_the_library_not_a_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    calls: list[str] = []

    def _record(name: str) -> object:
        def recorder(*args: object, **kwargs: object) -> object:
            _ = (args, kwargs)
            calls.append(name)
            return Ok(sentinel)

        return recorder

    monkeypatch.setattr(cli_tree, "run_sweep_batch", _record("run_sweep_batch"))
    monkeypatch.setattr(cli_tree, "rank_sweep", _record("rank_sweep"))
    assert (
        _ok(
            invoke_sweep_batch(
                admitted=1,
                output_root=1,
                ledger=1,
                combo_slices=1,
                projected_peak_memory=1,
            )
        )
        is sentinel
    )
    assert _ok(invoke_sweep_rank(lines=1, sweep_id=1, objective=1, world=1)) is sentinel
    assert calls == ["run_sweep_batch", "rank_sweep"]


def _called_names(fn: Callable[..., object]) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def test_batch_door_does_not_expand_axes() -> None:
    batch_calls = _called_names(invoke_sweep_batch)
    assert "run_sweep_batch" in batch_calls
    assert "expand_sweep" not in batch_calls
    rank_calls = _called_names(invoke_sweep_rank)
    assert "rank_sweep" in rank_calls
    assert "mint_run_performance_result" not in rank_calls
    assert "fingerprint" not in rank_calls


def test_missing_prerequisites_are_typed_unavailable() -> None:
    batch = invoke_sweep_batch()
    assert is_refusal(batch)
    assert batch.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert batch.context["command"] == "sweep.batch"
    rank = invoke_sweep_rank()
    assert is_refusal(rank)
    assert rank.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert rank.context["command"] == "sweep.rank"


def test_rank_refuses_persisting_a_candidate_database(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        raise AssertionError("rank_sweep must not run when persist is requested")

    monkeypatch.setattr(cli_tree, "rank_sweep", boom)
    refused_cases = (
        invoke_sweep_rank(
            lines=_lines(),
            sweep_id=_sweep_id(),
            objective="net_profit",
            world=World.REPLAY,
            persist=True,
        ),
        invoke_sweep_rank(
            lines=_lines(),
            sweep_id=_sweep_id(),
            objective="net_profit",
            world=World.REPLAY,
            database="candidates.sqlite",
        ),
        invoke_sweep_rank(
            lines=_lines(),
            sweep_id=_sweep_id(),
            objective="net_profit",
            world=World.REPLAY,
            candidate_database="db",
        ),
        invoke_sweep_rank(
            lines=_lines(),
            sweep_id=_sweep_id(),
            objective="net_profit",
            world=World.REPLAY,
            store="databank",
        ),
        invoke_sweep_rank(
            lines=_lines(),
            sweep_id=_sweep_id(),
            objective="net_profit",
            world=World.REPLAY,
            databank=True,
        ),
        invoke_sweep_rank(
            lines=_lines(),
            sweep_id=_sweep_id(),
            objective="net_profit",
            world=World.REPLAY,
            persist_candidates=True,
        ),
    )
    for refused in refused_cases:
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["occupancy"] == SWEEP_RANK_OCCUPANCY
        assert refused.context["mints_ct32"] is False
        assert refused.context["mints_experiment_spec"] is False
        reason = cast("str", refused.context["reason"])
        assert "fold" in reason
        assert "second store" in reason


def test_rank_persist_false_still_folds() -> None:
    lines = _lines()
    ranking = _ok(
        invoke_sweep_rank(
            lines=lines,
            sweep_id=_sweep_id(),
            objective="net_profit",
            world=World.REPLAY,
            persist=False,
        )
    )
    assert ranking.ranked_count == 3
    assert ranking.fp1_identity()["class"] == RANKING_CLASS


def test_click_sweep_commands_refuse_without_resources() -> None:
    runner = CliRunner()
    for sub in ("batch", "rank"):
        clicked = runner.invoke(main, ["sweep", sub])
        assert clicked.exit_code != 0, sub
        assert clicked.stdout.strip() == ""
        payload = cast("dict[str, object]", json.loads(clicked.stderr))
        assert payload["category"] == RefusalCategory.UNAVAILABLE_DEPENDENCY.value


def test_click_rank_renders_the_library_fold() -> None:
    lines = _lines()
    sweep_id = _sweep_id()
    ranked = _ok(rank_sweep(lines, sweep_id=sweep_id, objective="net_profit", world=World.REPLAY))
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["sweep", "rank", "--objective", "net_profit", "--world", "replay"],
        obj={"lines": lines, "sweep_id": sweep_id},
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    rendered = json.loads(clicked.stdout)
    assert rendered["class"] == ranked.fp1_identity()["class"] == RANKING_CLASS
    assert rendered["publishes_never_acts"] is True
    assert rendered["makes_pass_fail_verdict"] is False
    assert len(rendered["ranked"]) == 3


def test_click_rank_persist_is_refused() -> None:
    lines = _lines()
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["sweep", "rank", "--persist"],
        obj={
            "lines": lines,
            "sweep_id": _sweep_id(),
            "objective": "net_profit",
            "world": World.REPLAY,
        },
    )
    assert clicked.exit_code != 0
    assert clicked.stdout.strip() == ""
    payload = cast("dict[str, object]", json.loads(clicked.stderr))
    assert payload["category"] == RefusalCategory.POLICY_REJECTION.value
    context = cast("dict[str, object]", payload["context"])
    assert context["occupancy"] == "query"
    assert "second store" in cast("str", context["reason"])


def test_click_rank_database_option_is_refused() -> None:
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["sweep", "rank", "--database", "candidates.sqlite"],
        obj={
            "lines": _lines(),
            "sweep_id": _sweep_id(),
            "objective": "net_profit",
            "world": World.REPLAY,
        },
    )
    assert clicked.exit_code != 0
    payload = cast("dict[str, object]", json.loads(clicked.stderr))
    assert payload["category"] == RefusalCategory.POLICY_REJECTION.value


def test_click_batch_forwards_to_the_library(monkeypatch: pytest.MonkeyPatch) -> None:
    report = SweepBatchReport(sweep_id=_fp("batch"), outcomes=())

    def recorder(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        return Ok(report)

    monkeypatch.setattr(cli_tree, "run_sweep_batch", recorder)
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["sweep", "batch", "--output-root", "out", "--projected-peak-memory", "64"],
        obj={"admitted": 1, "ledger": 1, "combo_slices": 1},
    )
    assert clicked.exit_code == 0, clicked.output
    rendered = json.loads(clicked.stdout)
    assert rendered == report.fp1_identity()
