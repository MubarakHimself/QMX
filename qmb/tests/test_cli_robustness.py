"""Story 33.1 — thin qmb robustness CLI group over the Epic 22 library."""

from __future__ import annotations

import json
from typing import TypeVar, cast

from click.testing import CliRunner
from qmb.doors import api, flatten_capabilities, required_library_names
from qmb.doors.cli import (
    invoke_robustness_candle_perturbation,
    invoke_robustness_rule_significance,
    invoke_robustness_trade_shuffle,
    invoke_robustness_walk_forward,
    main,
)
from qmb.doors.cli import tree as cli_tree
from qmb.doors.cli.tree import command_tree
from qmb.results.measures import ClosedTrade, TradeSide
from qmb.robustness import (
    BLOCK_LENGTH_KEY,
    ITERATIONS_KEY,
    PERTURBATION_SCENARIO_COUNT_KEY,
    PROCEDURE_MC_CANDLE_PERTURBATION,
    PROCEDURE_MC_TRADE_SHUFFLE,
    PROCEDURE_RULE_SIGNIFICANCE,
    PROCEDURE_WALK_FORWARD,
    RESAMPLING_SCHEME_KEY,
    ROBUSTNESS_PROCEDURES,
    SCENARIO_COUNT_KEY,
    WINDOW_COUNT_KEY,
    Candle,
    SignalBar,
    WalkForwardWindow,
    plan_walk_forward,
    run_candle_perturbation,
    run_significance_gate,
    run_trade_shuffle,
)
from qmf.core.chrono import Instant, Interval
from qmf.core.exact import Money, Price
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_DAY_NS = 86_400_000_000_000
_BASE_NS = 1_700_000_000_000_000_000
_INSTRUMENT = Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")
_RUNGS = (
    "walk-forward",
    "trade-shuffle",
    "candle-perturbation",
    "rule-significance",
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _money(minor: int) -> Money:
    return _ok(Money.try_create(minor, "USD", 2))


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _price(minor: int) -> Price:
    return _ok(Price.try_create(minor, _INSTRUMENT, 5))


def _trades() -> list[ClosedTrade]:
    pnls = (500, -300, 800, -1000, 200, -150, 400, -600)
    return [
        _ok(
            ClosedTrade.try_create(
                _money(pnl),
                _money(10),
                TradeSide.LONG if pnl >= 0 else TradeSide.SHORT,
                _instant((index + 1) * _DAY_NS),
            )
        )
        for index, pnl in enumerate(pnls)
    ]


def _window_interval() -> Interval:
    return _ok(Interval.try_create(_instant(0), _instant(9 * _DAY_NS)))


def _candles() -> list[Candle]:
    raw = (
        (100, 105, 98, 103),
        (103, 108, 101, 107),
        (107, 110, 104, 106),
        (106, 111, 105, 109),
        (109, 112, 107, 110),
        (110, 115, 108, 113),
        (113, 116, 111, 112),
        (112, 114, 109, 111),
    )
    return [
        _ok(Candle.try_create(_instant((index + 1) * _DAY_NS), open_, high, low, close))
        for index, (open_, high, low, close) in enumerate(raw)
    ]


def _signals() -> tuple[SignalBar, ...]:
    closes = (
        100_000,
        101_000,
        100_500,
        102_000,
        101_500,
        103_000,
        102_500,
        104_000,
        103_500,
        105_000,
        104_500,
        106_000,
    )
    fired = (True, False, True, False, True, False, True, False, True, False, True, False)
    return tuple(
        _ok(SignalBar.try_create(_instant(_BASE_NS + index * _DAY_NS), _price(close), flag))
        for index, (close, flag) in enumerate(zip(closes, fired, strict=True))
    )


def _windows() -> list[WalkForwardWindow]:
    out: list[WalkForwardWindow] = []
    for index in range(2):
        left = _ok(fingerprint({"n": f"in-{index}"}))
        right = _ok(fingerprint({"n": f"out-{index}"}))
        out.append(_ok(WalkForwardWindow.try_create(index, left, right)))
    return out


def test_command_tree_rungs_are_the_epic_22_procedures() -> None:
    tree = command_tree()
    assert tree["robustness"] == ROBUSTNESS_PROCEDURES
    assert ROBUSTNESS_PROCEDURES == (
        PROCEDURE_MC_TRADE_SHUFFLE,
        PROCEDURE_MC_CANDLE_PERTURBATION,
        PROCEDURE_RULE_SIGNIFICANCE,
        PROCEDURE_WALK_FORWARD,
    )
    catalog = set(flatten_capabilities())
    for procedure in ROBUSTNESS_PROCEDURES:
        assert f"robustness.{procedure}" in catalog


def test_cli_help_lists_the_robustness_rungs() -> None:
    runner = CliRunner()
    top = runner.invoke(main, ["--help"])
    assert top.exit_code == 0, top.output
    assert "robustness" in top.output
    helped = runner.invoke(main, ["robustness", "--help"])
    assert helped.exit_code == 0, helped.output
    lowered = helped.output.lower()
    for rung in _RUNGS:
        assert rung in lowered
    for procedure in ROBUSTNESS_PROCEDURES:
        assert procedure in helped.output
    assert "pass/fail" not in lowered
    assert "battery" not in lowered


def test_python_api_exposes_the_same_library_rungs() -> None:
    names = (
        "plan_walk_forward",
        "run_trade_shuffle",
        "run_candle_perturbation",
        "run_significance_gate",
    )
    required = required_library_names()
    for name in names:
        assert name in required
        assert getattr(api, name) is getattr(qmb, name)
        assert name in api.__all__
        assert name in qmb.__all__


def test_walk_forward_adapter_equals_the_library() -> None:
    windows = _windows()
    config = {
        WINDOW_COUNT_KEY: 2,
        "qmb_walk_forward_in_sample_span": 500,
        "qmb_walk_forward_out_of_sample_span": 100,
        "qmb_walk_forward_step": 100,
    }
    library = plan_walk_forward(windows, config=config)
    door = invoke_robustness_walk_forward(windows=windows, config=config)
    assert door == library
    assert is_ok(door)


def test_trade_shuffle_adapter_equals_the_library() -> None:
    kwargs = {
        "trades": _trades(),
        "starting_capital": _money(100_000),
        "period": _window_interval(),
        "base_seed": 42,
        "metrics": ["net_profit", "max_drawdown"],
        "config": {SCENARIO_COUNT_KEY: 40},
    }
    library = run_trade_shuffle(**kwargs)
    door = invoke_robustness_trade_shuffle(**kwargs)
    assert door == library
    assert is_ok(door)


def test_candle_perturbation_adapter_equals_the_library() -> None:
    kwargs = {
        "candles": _candles(),
        "base_seed": 42,
        "config": {BLOCK_LENGTH_KEY: 3, PERTURBATION_SCENARIO_COUNT_KEY: 20},
    }
    library = run_candle_perturbation(**kwargs)
    door = invoke_robustness_candle_perturbation(**kwargs)
    assert door == library
    assert is_ok(door)


def test_rule_significance_adapter_equals_the_library() -> None:
    kwargs = {
        "signals": _signals(),
        "base_seed": 7,
        "config": {
            RESAMPLING_SCHEME_KEY: "iid",
            ITERATIONS_KEY: 80,
        },
    }
    library = run_significance_gate(**kwargs)
    door = invoke_robustness_rule_significance(**kwargs)
    assert door == library
    assert is_ok(door)


def test_adapters_call_the_library_not_a_copy(monkeypatch) -> None:
    sentinel = object()
    calls: list[str] = []

    def _record(name: str) -> object:
        def recorder(*args: object, **kwargs: object) -> object:
            _ = (args, kwargs)
            calls.append(name)
            return Ok(sentinel)

        return recorder

    monkeypatch.setattr(cli_tree, "plan_walk_forward", _record("plan_walk_forward"))
    monkeypatch.setattr(cli_tree, "run_trade_shuffle", _record("run_trade_shuffle"))
    monkeypatch.setattr(cli_tree, "run_candle_perturbation", _record("run_candle_perturbation"))
    monkeypatch.setattr(cli_tree, "run_significance_gate", _record("run_significance_gate"))
    assert _ok(invoke_robustness_walk_forward(windows=("w",))) is sentinel
    assert (
        _ok(
            invoke_robustness_trade_shuffle(
                trades=1, starting_capital=1, period=1, base_seed=1, metrics=1
            )
        )
        is sentinel
    )
    assert _ok(invoke_robustness_candle_perturbation(candles=1, base_seed=1)) is sentinel
    assert _ok(invoke_robustness_rule_significance(signals=1, base_seed=1)) is sentinel
    assert calls == [
        "plan_walk_forward",
        "run_trade_shuffle",
        "run_candle_perturbation",
        "run_significance_gate",
    ]


def test_missing_prerequisites_are_typed_unavailable() -> None:
    walk = invoke_robustness_walk_forward()
    assert is_refusal(walk)
    assert walk.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert walk.context["command"] == f"robustness.{PROCEDURE_WALK_FORWARD}"
    shuffle = invoke_robustness_trade_shuffle()
    assert is_refusal(shuffle)
    assert shuffle.context["command"] == f"robustness.{PROCEDURE_MC_TRADE_SHUFFLE}"
    perturb = invoke_robustness_candle_perturbation()
    assert is_refusal(perturb)
    assert perturb.context["command"] == f"robustness.{PROCEDURE_MC_CANDLE_PERTURBATION}"
    gate = invoke_robustness_rule_significance()
    assert is_refusal(gate)
    assert gate.context["command"] == f"robustness.{PROCEDURE_RULE_SIGNIFICANCE}"


def test_click_robustness_commands_refuse_without_resources() -> None:
    runner = CliRunner()
    for procedure in ROBUSTNESS_PROCEDURES:
        clicked = runner.invoke(main, ["robustness", procedure])
        assert clicked.exit_code != 0, procedure
        assert clicked.stdout.strip() == ""
        payload = cast("dict[str, object]", json.loads(clicked.stderr))
        assert payload["category"] == RefusalCategory.UNAVAILABLE_DEPENDENCY.value
        assert "pass/fail" not in json.dumps(payload).lower()


def test_click_walk_forward_renders_library_identity() -> None:
    windows = _windows()
    config = {
        WINDOW_COUNT_KEY: 2,
        "qmb_walk_forward_in_sample_span": 500,
        "qmb_walk_forward_out_of_sample_span": 100,
        "qmb_walk_forward_step": 100,
    }
    planned = _ok(plan_walk_forward(windows, config=config))
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["robustness", PROCEDURE_WALK_FORWARD],
        obj={"windows": windows, "config": config},
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    rendered = json.loads(clicked.stdout)
    assert rendered["class"] == planned.fp1_identity()["class"]
    assert rendered["window_count"] == 2
    assert "pass/fail" not in clicked.stdout.lower()


def test_click_trade_shuffle_renders_library_identity() -> None:
    kwargs = {
        "trades": _trades(),
        "starting_capital": _money(100_000),
        "period": _window_interval(),
        "base_seed": 42,
        "metrics": ["net_profit"],
        "config": {SCENARIO_COUNT_KEY: 20},
    }
    shuffled = _ok(run_trade_shuffle(**kwargs))
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["robustness", PROCEDURE_MC_TRADE_SHUFFLE, "--base-seed", "42"],
        obj=kwargs,
    )
    assert clicked.exit_code == 0, clicked.output
    rendered = json.loads(clicked.stdout)
    assert rendered["procedure"] == PROCEDURE_MC_TRADE_SHUFFLE
    assert rendered["emits_verdict"] is False
    assert rendered["class"] == shuffled.fp1_identity()["class"]
