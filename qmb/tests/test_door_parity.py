"""Story 16.5 — tier-2 door-parity contract test (AR-58, B-1, AR-18)."""

from __future__ import annotations

import json
from typing import TypeVar, cast

import click
from click.testing import CliRunner, Result
from qmb.config import ResolvedRunConfig
from qmb.doors import (
    CAPABILITY_LIBRARY,
    CLI_ADAPTATION_COMMANDS,
    MCP_IN_DOOR_SET,
    MCP_SHIPPED,
    SHIPPED_DOORS,
    api,
    capability_gaps,
    door_parity_identity,
    flatten_capabilities,
    required_library_names,
)
from qmb.doors.cli import (
    COMMAND_GROUPS,
    ORCHESTRATOR_ENTRY,
    BacktestSubmission,
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
    render_refusal,
)
from qmb.doors.cli import (
    __all__ as CLI_ALL,
)
from qmb.orchestrator import IsolatedRun
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import (
    Result as CoreResult,
)

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_REQUIRED_REFUSAL_KEYS = ("category", "context", "retryability")
_CLI_INVOKERS: dict[str, str] = {
    "invoke_backtest": "backtest.run",
    "invoke_config_compile": "config.compile",
    "invoke_config_show": "config.show",
    "invoke_data": "data",
    "invoke_ledger_bar": "ledger.bar",
    "invoke_ledger_merge": "ledger.merge",
    "invoke_optimize_run": "optimize.run",
    "invoke_optimize_space": "optimize.space",
}


def _ok(result: CoreResult[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "door-parity", "tag": tag}))
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
    def compile_run_config(port: object, **kwargs: object) -> CoreResult[ResolvedRunConfig]:
        _ = (port, kwargs)
        return Ok(config)

    return compile_run_config


def _fake_orchestrator() -> object:
    def spawn_run(
        *,
        config: object,
        slices: object,
        output_root: object,
        cancel: object = None,
        limits: object = None,
        probe: object = None,
    ) -> CoreResult[IsolatedRun]:
        _ = (slices, cancel, limits, probe)
        assert isinstance(config, ResolvedRunConfig)
        return Ok(_isolated(config, output_root))

    return spawn_run


def _cli_commands() -> set[str]:
    tree = command_tree()
    return {f"{group}.{name}" for group, names in tree.items() for name in names}


def _click_commands() -> set[str]:
    leaves: set[str] = set()
    for name, command in main.commands.items():
        if name in CLI_ADAPTATION_COMMANDS:
            continue
        if isinstance(command, click.Group):
            for sub in command.commands:
                leaves.add(f"{name}.{sub}")
            continue
        leaves.add(name)
    return leaves


def _cli_payload(result: Result) -> dict[str, object]:
    assert result.exit_code != 0
    assert result.stdout.strip() == ""
    body = json.loads(result.stderr)
    assert isinstance(body, dict)
    payload = cast("dict[str, object]", body)
    for key in _REQUIRED_REFUSAL_KEYS:
        assert key in payload
    return payload


def test_shipped_doors_are_cli_and_api_not_mcp() -> None:
    assert SHIPPED_DOORS == ("cli", "api")
    assert MCP_SHIPPED is False
    assert MCP_IN_DOOR_SET is MCP_SHIPPED
    identity = door_parity_identity()
    assert identity["shipped_doors"] == SHIPPED_DOORS
    assert identity["mcp_in_door_set"] is MCP_IN_DOOR_SET
    assert qmb.__version__ not in identity.values()
    assert identity["capabilities"] == flatten_capabilities()


def test_cli_tree_and_click_match_the_capability_catalog() -> None:
    catalog = set(flatten_capabilities())
    cli = _cli_commands()
    clicked = _click_commands()
    assert cli == catalog
    assert clicked == catalog
    assert tuple(command_tree()) == COMMAND_GROUPS
    for group, names in command_tree().items():
        for name in names:
            assert f"{group}.{name}" in CAPABILITY_LIBRARY


def test_python_api_exposes_every_catalog_library_name_identity_equal() -> None:
    missing = [name for name in required_library_names() if not hasattr(api, name)]
    assert missing == []
    for name in required_library_names():
        assert getattr(api, name) is getattr(qmb, name), name
        assert name in api.__all__
        assert name in qmb.__all__
    assert api.compile_run_config is qmb.compile_run_config
    assert api.spawn_run is qmb.spawn_run
    assert api.run is qmb.run
    assert api.read_merge_view is qmb.read_merge_view
    assert api.read_book_bar is qmb.read_book_bar
    assert api.parameter_space_from_bot is qmb.parameter_space_from_bot
    assert api.run_config_identity is qmb.run_config_identity
    assert api.DATA_COMMANDS is qmb.DATA_COMMANDS
    assert api.data_front_identity is qmb.data_front_identity


def test_data_subcommands_are_the_library_data_commands() -> None:
    data_cmds = {
        name.split(".", 1)[1] for name in flatten_capabilities() if name.startswith("data.")
    }
    assert tuple(sorted(data_cmds)) == tuple(sorted(api.DATA_COMMANDS))
    assert command_tree()["data"] == api.DATA_COMMANDS
    assert "download" in api.DATA_COMMANDS
    assert "verify" in api.DATA_COMMANDS
    assert "gap-check" in api.DATA_COMMANDS
    assert "list" in api.DATA_COMMANDS
    assert "catalog" in api.DATA_COMMANDS
    assert "generate" in api.DATA_COMMANDS


def test_capability_on_one_door_missing_from_the_other_fails() -> None:
    aligned = capability_gaps(cli=_cli_commands(), api_names=api.__all__)
    assert aligned == {"extra_cli": (), "missing_api": (), "missing_cli": ()}
    extra = capability_gaps(cli={*_cli_commands(), "secret.only"}, api_names=api.__all__)
    assert extra["extra_cli"] == ("secret.only",)
    missing_cli = capability_gaps(cli=set(), api_names=api.__all__)
    assert set(missing_cli["missing_cli"]) == set(flatten_capabilities())
    missing_api = capability_gaps(cli=_cli_commands(), api_names=set())
    assert set(missing_api["missing_api"]) == set(required_library_names())


def test_cli_invokers_are_not_orphan_capabilities() -> None:
    invokers = [name for name in CLI_ALL if name.startswith("invoke_")]
    assert set(invokers) == set(_CLI_INVOKERS)
    catalog = set(flatten_capabilities())
    for invoker, target in _CLI_INVOKERS.items():
        if target == "data":
            assert any(name.startswith("data.") for name in catalog)
            continue
        assert target in catalog, invoker


def test_backtest_run_id_is_the_compiler_fingerprint_on_both_doors() -> None:
    config = _config(tag="backtest")
    compiler = _fake_compiler(config)
    orchestrator = _fake_orchestrator()
    submitted = _ok(
        invoke_backtest(
            port=1,
            book_fragment=1,
            bms_fragment=1,
            run_spec={"bot": "mean-reversion"},
            slices=(("eurusd",),),
            output_root="out",
            compiler=compiler,
            orchestrator=orchestrator,
        )
    )
    assert isinstance(submitted, BacktestSubmission)
    assert submitted.run_id == config.fingerprint
    assert api.spawn_run is qmb.spawn_run
    assert ORCHESTRATOR_ENTRY == "qmb.orchestrator.spawn_run"
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["backtest", "run", "mean-reversion", "--output-root", "out"],
        obj={
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "slices": (("eurusd",),),
            "compiler": compiler,
            "orchestrator": orchestrator,
        },
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    assert clicked.stdout.strip() == config.fingerprint.value


def test_config_show_and_data_catalog_payloads_match() -> None:
    identity = api.run_config_identity()
    shown = _ok(invoke_config_show())
    assert shown == identity
    assert shown["class"] == api.RUN_CONFIG_CLASS
    runner = CliRunner()
    click_show = runner.invoke(main, ["config", "show"])
    assert click_show.exit_code == 0, click_show.output
    assert click_show.stderr.strip() == ""
    assert click_show.stdout.strip() == api.RUN_CONFIG_CLASS
    catalog = _ok(invoke_data("catalog"))
    front = api.data_front_identity()
    catalog_view = cast("dict[str, object]", catalog["view"])
    assert catalog["commands"] == front["commands"] == api.DATA_COMMANDS
    assert catalog["command"] == "catalog"
    assert catalog["entries"] == ()
    assert catalog_view["engine"] == "duckdb"
    listed = _ok(invoke_data("list"))
    assert listed["command"] == "list"
    assert listed["entries"] == catalog["entries"]
    click_catalog = runner.invoke(main, ["data", "catalog"])
    assert click_catalog.exit_code == 0, click_catalog.output
    assert click_catalog.stderr.strip() == ""
    rendered = json.loads(click_catalog.stdout)
    assert rendered["command"] == "catalog"
    assert rendered["entries"] == []
    for name in api.DATA_COMMANDS:
        assert name in click_catalog.stdout


def test_config_compile_refusal_is_identical_then_rendered_per_transport() -> None:
    python_refusal = api.compile_run_config(
        1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
    )
    assert is_refusal(python_refusal)
    assert isinstance(python_refusal, TypedRefusal)
    sequenced = invoke_config_compile(
        port=1,
        book_fragment=1,
        bms_fragment=1,
        run_spec={"bot": "x"},
    )
    assert sequenced == python_refusal
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["config", "compile"],
        obj={
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "run_spec": {"bot": "x"},
        },
    )
    payload = _cli_payload(clicked)
    assert payload == json.loads(render_refusal(python_refusal))
    assert payload["category"] == python_refusal.category.value
    assert payload["retryability"] == python_refusal.retryability.value


def test_ledger_merge_and_bar_refusals_match_across_doors() -> None:
    python_merge = api.read_merge_view("missing-dir", world="replay", role=api.ROLE_CONFIRMATION)
    cli_merge = invoke_ledger_merge(root="missing-dir", world="replay", role=api.ROLE_CONFIRMATION)
    assert is_refusal(python_merge)
    assert cli_merge == python_merge
    python_bar = api.read_book_bar("missing-dir", world="replay")
    cli_bar = invoke_ledger_bar(root="missing-dir", world="replay")
    assert is_refusal(python_bar)
    assert cli_bar == python_bar
    runner = CliRunner()
    merge_click = runner.invoke(
        main,
        ["ledger", "merge", "--root", "missing-dir", "--world", "replay", "--role", "confirmation"],
    )
    assert _cli_payload(merge_click) == json.loads(render_refusal(python_merge))
    bar_click = runner.invoke(main, ["ledger", "bar", "--root", "missing-dir", "--world", "replay"])
    assert _cli_payload(bar_click) == json.loads(render_refusal(python_bar))


def test_optimize_space_refusal_matches_across_doors() -> None:
    declaration = {"not": "a-bot"}
    python_space = api.parameter_space_from_bot(declaration)
    cli_space = invoke_optimize_space(declaration=declaration)
    assert is_refusal(python_space)
    assert cli_space == python_space
    runner = CliRunner()
    clicked = runner.invoke(main, ["optimize", "space"], obj={"declaration": declaration})
    assert _cli_payload(clicked) == json.loads(render_refusal(python_space))


def test_optimize_run_reuses_backtest_semantics() -> None:
    config = _config(tag="optimize")
    submitted = _ok(
        invoke_optimize_run(
            declaration={"present": True},
            port=1,
            book_fragment=1,
            bms_fragment=1,
            run_spec={"bot": "x"},
            slices=(("s",),),
            output_root="out",
            compiler=_fake_compiler(config),
            orchestrator=_fake_orchestrator(),
        )
    )
    assert submitted.run_id == config.fingerprint
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["optimize", "run", "bot-a"],
        obj={
            "declaration": {"present": True},
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "slices": (("s",),),
            "output_root": "out",
            "compiler": _fake_compiler(config),
            "orchestrator": _fake_orchestrator(),
        },
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    assert config.fingerprint.value in clicked.stdout


def test_cli_refusal_is_nonzero_stderr_json_python_returns_union() -> None:
    runner = CliRunner()
    cases = (
        ["backtest", "run"],
        ["data", "download"],
        ["optimize", "space"],
        ["ledger", "merge"],
        ["config", "compile"],
    )
    for args in cases:
        clicked = runner.invoke(main, list(args))
        payload = _cli_payload(clicked)
        assert payload["category"] in {
            RefusalCategory.UNAVAILABLE_DEPENDENCY.value,
            RefusalCategory.INVALID_INPUT.value,
        }
    python_run = api.run(slices="not-slices")
    assert is_refusal(python_run)
    assert isinstance(python_run, TypedRefusal)
    assert python_run.category is RefusalCategory.INVALID_INPUT
    python_compile = api.compile_run_config(
        None,
        book_fragment=None,
        bms_fragment=None,
        run_spec=None,
    )
    assert is_refusal(python_compile)
    assert isinstance(python_compile, TypedRefusal)


def test_python_door_does_not_raise_typed_refusal() -> None:
    refused = api.compile_run_config(
        None,
        book_fragment=None,
        bms_fragment=None,
        run_spec=None,
    )
    assert is_refusal(refused)
    try:
        payload: object = api.identity_payload("nope")  # type: ignore[call-arg]
    except TypeError:
        return
    raise AssertionError(f"expected TypeError, got {payload!r}")


def test_epic_14_run_loop_semantics_are_on_the_api_door() -> None:
    config = _config(tag="epic-14")
    slices = ((_obs("eurusd"),),)
    first = _ok(api.run(slices=slices, config=config, handler=SilentSliceHandler()))
    second = _ok(api.run(slices=slices, config=config, handler=SilentSliceHandler()))
    left = _ok(first.ct32_fingerprint())
    right = _ok(second.ct32_fingerprint())
    assert left == right
    assert left.value.startswith("fp1:sha256:")
    reproduced = _ok(
        api.reproduce_run(
            run_id=config.fingerprint,
            config=config,
            expected_fingerprint=left,
            slices=slices,
            handler=SilentSliceHandler(),
        )
    )
    assert _ok(reproduced.fingerprint()) == left
    mismatch = api.require_reproduced_fingerprint(
        left,
        _ok(fingerprint({"n": "other"})),
        run_id=config.fingerprint,
    )
    assert is_refusal(mismatch)
    assert mismatch.category is RefusalCategory.POLICY_REJECTION
    assert api.reproduce_run is qmb.reproduce_run
    assert api.require_reproduced_fingerprint is qmb.require_reproduced_fingerprint
    assert api.RESULT_CONTRACT == qmb.RESULT_CONTRACT


def test_data_command_success_matches_library_front() -> None:
    generated = _ok(invoke_data("generate", {"destination": "synth"}))
    assert generated["command"] == "generate"
    incomplete = invoke_data("download", {"destination": "archive"})
    assert is_refusal(incomplete)
    incomplete_verify = invoke_data("verify", {"archive": "raw"})
    assert is_refusal(incomplete_verify)
    runner = CliRunner()
    clicked = runner.invoke(main, ["data", "generate", "--destination", "synth"])
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    assert "generate" in clicked.stdout
    refused = runner.invoke(main, ["data", "download", "--destination", "archive"])
    assert refused.exit_code != 0
    refused_verify = runner.invoke(main, ["data", "verify", "--archive", "raw"])
    assert refused_verify.exit_code != 0
