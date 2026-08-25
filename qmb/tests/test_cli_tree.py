"""Story 16.1 — thin click qmb CLI command tree, no domain logic in the door."""

from __future__ import annotations

import ast
from importlib.metadata import version
from pathlib import Path
from typing import TypeVar, cast

import click
import tomllib
from click.testing import CliRunner
from qmb.config import ResolvedRunConfig
from qmb.doors.cli import (
    COMMAND_GROUPS,
    COMPUTES_RUN_ID,
    HOLDS_CACHE,
    ORCHESTRATOR_ENTRY,
    BacktestSubmission,
    cli_tree_identity,
    command_prerequisites,
    command_tree,
    invoke_backtest,
    invoke_config_compile,
    invoke_config_show,
    invoke_data,
    invoke_ledger_bar,
    invoke_ledger_merge,
    invoke_optimize_run,
    invoke_optimize_space,
    main,
    require_prerequisites,
)
from qmb.orchestrator import IsolatedRun
from qmb.runloop import STREAM_SET_KEY
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_QMB_ROOT = Path(__file__).resolve().parents[1]
_CLI_SRC = _QMB_ROOT / "src" / "qmb" / "doors" / "cli"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "cli-tree", "tag": tag}))
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


def _isolated(config: ResolvedRunConfig, output_root: object) -> IsolatedRun:
    return IsolatedRun(
        run_id=config.fingerprint,
        output_dir=str(output_root),
        pid=0,
        worker_pid=0,
        ct32_fingerprint=None,
        outcome_identity={"submitted": True},
    )


def _fake_compiler(config: ResolvedRunConfig) -> object:
    from qmf.core.refusal import Ok

    def compile_run_config(port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        _ = (port, kwargs)
        return Ok(config)

    return compile_run_config


def _fake_orchestrator() -> object:
    from qmf.core.refusal import Ok

    def spawn_run(
        *,
        config: object,
        slices: object,
        output_root: object,
        cancel: object = None,
        limits: object = None,
        probe: object = None,
    ) -> Result[IsolatedRun]:
        _ = (slices, cancel, limits, probe)
        assert isinstance(config, ResolvedRunConfig)
        return Ok(_isolated(config, output_root))

    return spawn_run


def test_click_runtime_matches_pyproject_pin() -> None:
    data = tomllib.loads((_QMB_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = tuple(data["project"]["dependencies"])
    assert f"click=={version('click')}" in deps
    assert qmb.CLI_PIN_KEY == "qmb_cli_pin"


def test_command_tree_exposes_platform_groups() -> None:
    tree = command_tree()
    assert tuple(tree) == COMMAND_GROUPS
    assert COMMAND_GROUPS == ("backtest", "data", "optimize", "ledger", "config")
    assert tree["backtest"] == ("run",)
    assert tree["data"] == qmb.DATA_COMMANDS
    assert tree["optimize"] == ("run", "space")
    assert tree["ledger"] == ("merge", "bar")
    assert tree["config"] == ("compile", "show")
    identity = cli_tree_identity()
    assert identity["computes_run_id"] is COMPUTES_RUN_ID is False
    assert identity["holds_cache"] is HOLDS_CACHE is False
    assert identity["orchestrator_entry"] == ORCHESTRATOR_ENTRY
    assert identity["pin_key"] == qmb.CLI_PIN_KEY
    assert qmb.__version__ not in identity.values()


def test_click_groups_match_command_tree() -> None:
    runner = CliRunner()
    helped = runner.invoke(main, ["--help"])
    assert helped.exit_code == 0, helped.output
    for group in COMMAND_GROUPS:
        assert group in helped.output
        cmd = main.commands[group]
        assert isinstance(cmd, click.Group)
        assert tuple(cmd.commands) == command_tree()[group]
        nested = runner.invoke(main, [group, "--help"])
        assert nested.exit_code == 0, nested.output
        for sub in command_tree()[group]:
            assert sub in nested.output


def test_missing_prerequisites_are_typed_unavailable() -> None:
    refused = require_prerequisites("backtest.run", {})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["missing"] == (
        "port",
        "book_fragment",
        "bms_fragment",
        "run_spec",
        "slices",
        "output_root",
    )
    unknown = command_prerequisites("not-a-command")
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.INVALID_INPUT


def test_blank_and_non_mapping_prerequisites_refuse() -> None:
    blank = require_prerequisites("   ", {})
    assert is_refusal(blank)
    assert blank.category is RefusalCategory.INVALID_INPUT
    not_map = require_prerequisites("config.show", ["nope"])
    assert is_refusal(not_map)
    assert not_map.category is RefusalCategory.INVALID_INPUT
    empty_string = require_prerequisites("data.download", {"destination": "  "})
    assert is_refusal(empty_string)
    assert empty_string.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_invoke_backtest_refuses_when_resources_absent() -> None:
    refused = invoke_backtest()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["command"] == "backtest.run"


def test_invoke_backtest_compiles_then_submits_without_computing_run_id() -> None:
    from qmf.core.refusal import Ok

    config = _config(tag="submit")
    seen: list[str] = []

    def compiler(port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        seen.append("compile")
        assert port == "port"
        assert kwargs["book_fragment"] == "book"
        assert kwargs["bms_fragment"] == "bms"
        assert kwargs["run_spec"] == {"bot": "mean-reversion"}
        return Ok(config)

    def orchestrator(
        *,
        config: object,
        slices: object,
        output_root: object,
        cancel: object = None,
        limits: object = None,
        probe: object = None,
    ) -> Result[IsolatedRun]:
        seen.append("spawn")
        _ = (slices, cancel, limits, probe)
        assert config is config_arg
        return Ok(_isolated(cast("ResolvedRunConfig", config), output_root))

    config_arg = config
    submitted = _ok(
        invoke_backtest(
            port="port",
            book_fragment="book",
            bms_fragment="bms",
            run_spec={"bot": "mean-reversion"},
            slices=(("eurusd",),),
            output_root="out",
            compiler=compiler,
            orchestrator=orchestrator,
        )
    )
    assert isinstance(submitted, BacktestSubmission)
    assert seen == ["compile", "spawn"]
    assert submitted.run_id == config.fingerprint
    assert submitted.run_id is submitted.config.fingerprint
    assert submitted.isolated.output_dir == "out"


def test_door_run_id_is_compiler_fingerprint_not_orchestrator_token() -> None:
    from qmf.core.refusal import Ok

    config = _config(tag="door-id")
    other = _ok(fingerprint({"n": "other-id"}))

    def compiler(port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        _ = (port, kwargs)
        return Ok(config)

    def orchestrator(
        *,
        config: object,
        slices: object,
        output_root: object,
        cancel: object = None,
        limits: object = None,
        probe: object = None,
    ) -> Result[IsolatedRun]:
        _ = (slices, cancel, limits, probe)
        return Ok(
            IsolatedRun(
                run_id=other,
                output_dir=str(output_root),
                pid=0,
                worker_pid=0,
                ct32_fingerprint=None,
                outcome_identity={},
            )
        )

    submitted = _ok(
        invoke_backtest(
            port=1,
            book_fragment=1,
            bms_fragment=1,
            run_spec={"bot": "x"},
            slices=(("s",),),
            output_root="out",
            compiler=compiler,
            orchestrator=orchestrator,
        )
    )
    assert submitted.run_id == config.fingerprint
    assert submitted.run_id != other
    assert submitted.isolated.run_id == other


def test_invoke_backtest_propagates_compiler_and_orchestrator_refusals() -> None:
    from qmb._refuse import invalid, policy

    def compiler(port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        _ = (port, kwargs)
        return invalid("bot", "bot cite missing")

    refused = invoke_backtest(
        port=1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
        slices=(("s",),),
        output_root="out",
        compiler=compiler,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT

    def orch(
        *,
        config: object,
        slices: object,
        output_root: object,
        cancel: object = None,
        limits: object = None,
        probe: object = None,
    ) -> Result[IsolatedRun]:
        _ = (config, slices, output_root, cancel, limits, probe)
        return policy("governor", "budget exhausted")

    config = _config(tag="orch-refuse")

    def ok_compiler(port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        _ = (port, kwargs)
        from qmf.core.refusal import Ok

        return Ok(config)

    orch_refused = invoke_backtest(
        port=1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
        slices=(("s",),),
        output_root="out",
        compiler=ok_compiler,
        orchestrator=orch,
    )
    assert is_refusal(orch_refused)
    assert orch_refused.category is RefusalCategory.POLICY_REJECTION


def test_default_compiler_is_the_library_entry() -> None:
    refused = invoke_config_compile(
        port=1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_non_callable_compiler_and_orchestrator_refuse() -> None:
    refused = invoke_config_compile(
        port=1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
        compiler="not-callable",
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    orch_refused = invoke_backtest(
        port=1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
        slices=(("s",),),
        output_root="out",
        compiler=_fake_compiler(_config(tag="bad-orch")),
        orchestrator="not-callable",
    )
    assert is_refusal(orch_refused)
    assert orch_refused.category is RefusalCategory.INVALID_INPUT


def test_data_commands_refuse_absent_resources_and_catalog_is_free() -> None:
    missing = invoke_data("download", {})
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    unknown = invoke_data("wipe")
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.INVALID_INPUT
    not_map = invoke_data("download", "dest")
    assert is_refusal(not_map)
    catalog = _ok(invoke_data("catalog"))
    assert catalog["command"] == "catalog"
    assert catalog["commands"] == qmb.DATA_COMMANDS
    downloaded = _ok(invoke_data("download", {"destination": "archive"}))
    assert downloaded["command"] == "download"


def test_optimize_and_ledger_and_config_prerequisites() -> None:
    space = invoke_optimize_space()
    assert is_refusal(space)
    assert space.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    invalid_decl = invoke_optimize_space(declaration={"not": "a-bot"})
    assert is_refusal(invalid_decl)
    trial = invoke_optimize_run()
    assert is_refusal(trial)
    assert trial.context["command"] == "optimize.run"
    merge = invoke_ledger_merge()
    assert is_refusal(merge)
    bar = invoke_ledger_bar()
    assert is_refusal(bar)
    compiled = invoke_config_compile()
    assert is_refusal(compiled)
    shown = _ok(invoke_config_show())
    assert shown["class"] == qmb.RUN_CONFIG_CLASS


def test_optimize_run_reuses_backtest_submit() -> None:
    from qmf.core.refusal import Ok

    config = _config(tag="opt")

    def compiler(port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        _ = (port, kwargs)
        return Ok(config)

    submitted = _ok(
        invoke_optimize_run(
            declaration={"present": True},
            port=1,
            book_fragment=1,
            bms_fragment=1,
            run_spec={"bot": "x"},
            slices=(("s",),),
            output_root="out",
            compiler=compiler,
            orchestrator=_fake_orchestrator(),
        )
    )
    assert submitted.run_id == config.fingerprint


def test_click_backtest_run_compiles_and_submits() -> None:
    from qmf.core.refusal import Ok

    config = _config(tag="click-run")
    seen: list[str] = []

    def compiler(port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        seen.append("compile")
        _ = (port, kwargs)
        return Ok(config)

    def orchestrator(
        *,
        config: object,
        slices: object,
        output_root: object,
        cancel: object = None,
        limits: object = None,
        probe: object = None,
    ) -> Result[IsolatedRun]:
        seen.append("spawn")
        _ = (slices, cancel, limits, probe)
        assert isinstance(config, ResolvedRunConfig)
        return Ok(_isolated(config, output_root))

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["backtest", "run", "mean-reversion", "--book", "scalping", "--output-root", "out"],
        obj={
            "port": "port",
            "book_fragment": "book",
            "bms_fragment": "bms",
            "run_spec": {"bot": "mean-reversion"},
            "slices": (("eurusd",),),
            "compiler": compiler,
            "orchestrator": orchestrator,
        },
    )
    assert result.exit_code == 0, result.output
    assert config.fingerprint.value in result.output
    assert seen == ["compile", "spawn"]


def test_click_backtest_bot_token_defaults_to_run() -> None:
    from qmf.core.refusal import Ok

    config = _config(tag="alias-run")

    def compiler(port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        _ = port
        assert kwargs["run_spec"] == {"bot": "mean-reversion"}
        return Ok(config)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["backtest", "mean-reversion", "--book", "scalping", "--output-root", "out"],
        obj={
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "slices": (("s",),),
            "compiler": compiler,
            "orchestrator": _fake_orchestrator(),
        },
    )
    assert result.exit_code == 0, result.output
    assert config.fingerprint.value in result.output


def test_click_commands_return_typed_refusal_when_prereqs_absent() -> None:
    runner = CliRunner()
    cases = (
        ["backtest", "run"],
        ["data", "download"],
        ["data", "verify"],
        ["data", "generate"],
        ["optimize", "run"],
        ["optimize", "space"],
        ["ledger", "merge"],
        ["ledger", "bar"],
        ["config", "compile"],
    )
    for args in cases:
        result = runner.invoke(main, list(args))
        assert result.exit_code != 0, args
        text = result.output + (result.stderr or "")
        assert "unavailable dependency" in text or "invalid input" in text


def test_click_catalog_and_config_show_succeed_without_resources() -> None:
    runner = CliRunner()
    catalog = runner.invoke(main, ["data", "catalog"])
    assert catalog.exit_code == 0, catalog.output
    for name in qmb.DATA_COMMANDS:
        assert name in catalog.output
    shown = runner.invoke(main, ["config", "show"])
    assert shown.exit_code == 0, shown.output
    assert qmb.RUN_CONFIG_CLASS in shown.output


def test_click_data_download_and_optimize_and_ledger_with_injected_resources() -> None:
    runner = CliRunner()
    downloaded = runner.invoke(main, ["data", "download", "--destination", "room"])
    assert downloaded.exit_code == 0, downloaded.output
    assert "download" in downloaded.output
    compiled = runner.invoke(
        main,
        ["config", "compile"],
        obj={
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "run_spec": {"bot": "x"},
            "compiler": _fake_compiler(_config(tag="cfg")),
        },
    )
    assert compiled.exit_code == 0, compiled.output
    assert compiled.output.strip().startswith("fp1:")
    opt = runner.invoke(
        main,
        ["optimize", "run", "bot-a"],
        obj={
            "declaration": {"present": True},
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "slices": (("s",),),
            "output_root": "out",
            "compiler": _fake_compiler(_config(tag="opt-cli")),
            "orchestrator": _fake_orchestrator(),
        },
    )
    assert opt.exit_code == 0, opt.output
    merge = runner.invoke(
        main,
        ["ledger", "merge", "--root", "missing-dir", "--world", "replay", "--role", "confirmation"],
    )
    assert merge.exit_code != 0
    bar = runner.invoke(main, ["ledger", "bar", "--root", "missing-dir", "--world", "replay"])
    assert bar.exit_code != 0


def test_click_verify_generate_and_optimize_space_paths() -> None:
    runner = CliRunner()
    verified = runner.invoke(main, ["data", "verify", "--archive", "raw"])
    assert verified.exit_code == 0, verified.output
    generated = runner.invoke(main, ["data", "generate", "--destination", "synth"])
    assert generated.exit_code == 0, generated.output
    space = runner.invoke(main, ["optimize", "space"], obj={"declaration": {"not": "bot"}})
    assert space.exit_code != 0


def test_cli_door_never_calls_fp1() -> None:
    offenders: list[str] = []
    for path in sorted(_CLI_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "fingerprint":
                offenders.append(f"{path.name}: fingerprint()")
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "fingerprint"
                and isinstance(func.value, ast.Name)
                and func.value.id in {"fingerprint"}
            ):
                offenders.append(f"{path.name}: fingerprint.fingerprint()")
    assert offenders == []


def test_click_module_is_confined_to_cli_init() -> None:
    tree_source = (_CLI_SRC / "tree.py").read_text(encoding="utf-8")
    assert "import click" not in tree_source
    init_tree = ast.parse((_CLI_SRC / "__init__.py").read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(init_tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    assert "click" in names
    assert "qmf.venue" not in names
