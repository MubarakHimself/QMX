"""Story 16.2 — CLI renders typed refusals as nonzero exit + stderr JSON."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import cast

from click.testing import CliRunner, Result
from qmb._refuse import policy
from qmb.config import ResolvedRunConfig
from qmb.doors.cli import invoke_backtest, invoke_data, main, render_refusal
from qmb.orchestrator import IsolatedRun
from qmb.runloop import STREAM_SET_KEY
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import (
    Result as CoreResult,
)

_QMB_ROOT = Path(__file__).resolve().parents[1]
_CLI_SRC = _QMB_ROOT / "src" / "qmb" / "doors" / "cli"
_REQUIRED_KEYS = ("category", "context", "retryability")


def _payload(result: Result) -> dict[str, object]:
    assert result.exit_code != 0
    assert result.stdout.strip() == ""
    body = json.loads(result.stderr)
    assert isinstance(body, dict)
    payload = cast("dict[str, object]", body)
    for key in _REQUIRED_KEYS:
        assert key in payload
    return payload


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = fingerprint({"n": "cli-refusal", "tag": tag})
    assert is_ok(stamp)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp.value,
        bms_fp1=stamp.value,
        bot_fp1=stamp.value,
        book_fragment_fp1=stamp.value,
        bms_fragment_fp1=stamp.value,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp.value,
        binding_fp1=stamp.value,
    )


def test_render_refusal_encodes_category_context_retryability() -> None:
    refusal = TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={"field": "prerequisites", "missing": ["port", "run_spec"]},
    )
    payload = json.loads(render_refusal(refusal))
    assert payload == {
        "category": "unavailable dependency",
        "context": {"field": "prerequisites", "missing": ["port", "run_spec"]},
        "retryability": "no",
    }
    assert "after_condition_descriptor" not in payload


def test_render_refusal_includes_after_condition_descriptor() -> None:
    refusal = TypedRefusal(
        category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
        retryability=Retryability.AFTER_CONDITION,
        context={"source": "probe"},
        after_condition_descriptor="retry after 2s",
    )
    payload = json.loads(render_refusal(refusal))
    assert payload["category"] == "transient venue failure"
    assert payload["retryability"] == "after-condition"
    assert payload["after_condition_descriptor"] == "retry after 2s"
    assert payload["context"] == {"source": "probe"}


def test_render_refusal_empty_context_is_object_never_null() -> None:
    refusal = TypedRefusal(RefusalCategory.POLICY_REJECTION, Retryability.NO)
    payload = json.loads(render_refusal(refusal))
    assert payload["context"] == {}
    assert payload["context"] is not None


def test_click_refusal_is_nonzero_stderr_json() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["backtest", "run"])
    payload = _payload(result)
    assert payload["category"] == RefusalCategory.UNAVAILABLE_DEPENDENCY.value
    assert payload["retryability"] == Retryability.NO.value
    context = cast("dict[str, object]", payload["context"])
    assert context["command"] == "backtest.run"
    assert context["missing"] == [
        "port",
        "book_fragment",
        "bms_fragment",
        "run_spec",
        "slices",
        "output_root",
    ]


def test_library_returns_refusal_door_renders_it() -> None:
    library = invoke_data("download", {})
    assert is_refusal(library)
    runner = CliRunner()
    rendered = runner.invoke(main, ["data", "download"])
    payload = _payload(rendered)
    assert payload["category"] == library.category.value
    assert payload["retryability"] == library.retryability.value
    context = cast("dict[str, object]", payload["context"])
    assert context["field"] == library.context["field"]
    assert context["command"] == library.context["command"]
    assert context["missing"] == list(cast("tuple[str, ...]", library.context["missing"]))


def test_click_success_exits_zero_without_stderr_json() -> None:
    runner = CliRunner()
    catalog = runner.invoke(main, ["data", "catalog"])
    assert catalog.exit_code == 0, catalog.output
    assert catalog.stderr.strip() == ""
    assert "download" in catalog.stdout
    shown = runner.invoke(main, ["config", "show"])
    assert shown.exit_code == 0, shown.output
    assert shown.stderr.strip() == ""
    versioned = runner.invoke(main, ["version"])
    assert versioned.exit_code == 0, versioned.output
    assert versioned.stderr.strip() == ""


def test_click_compiler_refusal_is_stderr_json_not_raised() -> None:
    def compiler(port: object, **kwargs: object) -> CoreResult[ResolvedRunConfig]:
        _ = (port, kwargs)
        return policy("governor", "budget exhausted")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["backtest", "run", "mean-reversion"],
        obj={
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "slices": (("s",),),
            "output_root": "out",
            "compiler": compiler,
        },
    )
    payload = _payload(result)
    assert payload["category"] == RefusalCategory.POLICY_REJECTION.value
    assert payload["retryability"] == "no"
    context = cast("dict[str, object]", payload["context"])
    assert context["field"] == "governor"
    assert isinstance(result.exception, SystemExit)
    assert result.exception.code == 1


def test_click_after_condition_refusal_carries_descriptor() -> None:
    def compiler(port: object, **kwargs: object) -> CoreResult[ResolvedRunConfig]:
        _ = (port, kwargs)
        return TypedRefusal(
            category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
            retryability=Retryability.AFTER_CONDITION,
            context={"field": "venue"},
            after_condition_descriptor="retry after 2s",
        )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["config", "compile"],
        obj={
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "run_spec": {"bot": "x"},
            "compiler": compiler,
        },
    )
    payload = _payload(result)
    assert payload["category"] == "transient venue failure"
    assert payload["retryability"] == "after-condition"
    assert payload["after_condition_descriptor"] == "retry after 2s"


def test_programmer_error_surfaces_as_exception_not_refusal_json() -> None:
    def compiler(port: object, **kwargs: object) -> CoreResult[ResolvedRunConfig]:
        _ = (port, kwargs)
        raise RuntimeError("programmer-error")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["backtest", "run", "mean-reversion"],
        obj={
            "port": 1,
            "book_fragment": 1,
            "bms_fragment": 1,
            "slices": (("s",),),
            "output_root": "out",
            "compiler": compiler,
        },
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert result.exception.args == ("programmer-error",)
    text = result.stderr.strip()
    if text:
        try:
            parsed: object = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            keys = set(cast("dict[str, object]", parsed))
            assert not set(_REQUIRED_KEYS) <= keys


def test_library_invoke_does_not_raise_typed_refusal() -> None:
    refused = invoke_backtest()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_cli_door_never_raises_typed_refusal() -> None:
    offenders: list[str] = []
    for path in sorted(_CLI_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            exc = node.exc
            name: str | None = None
            target = exc.func if isinstance(exc, ast.Call) else exc
            if isinstance(target, ast.Name):
                name = target.id
            elif isinstance(target, ast.Attribute):
                name = target.attr
            if name == "TypedRefusal":
                offenders.append(f"{path.name}: raise TypedRefusal")
    assert offenders == []


def test_refusal_render_module_is_click_free() -> None:
    source = (_CLI_SRC / "render.py").read_text(encoding="utf-8")
    assert "import click" not in source
    assert "from click" not in source
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert "click" not in imported
    assert "json" in imported


def test_click_success_backtest_still_exits_zero() -> None:
    config = _config(tag="ok-run")

    def compiler(port: object, **kwargs: object) -> CoreResult[ResolvedRunConfig]:
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
    ) -> CoreResult[object]:
        _ = (slices, cancel, limits, probe)
        assert isinstance(config, ResolvedRunConfig)
        return Ok(
            IsolatedRun(
                run_id=config.fingerprint,
                output_dir=str(output_root),
                pid=0,
                worker_pid=0,
                ct32_fingerprint=None,
                outcome_identity={},
            )
        )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["backtest", "run", "mean-reversion", "--output-root", "out"],
        obj={
            "port": "port",
            "book_fragment": "book",
            "bms_fragment": "bms",
            "slices": (("eurusd",),),
            "compiler": compiler,
            "orchestrator": orchestrator,
        },
    )
    assert result.exit_code == 0, result.output
    assert config.fingerprint.value in result.stdout
    assert result.stderr.strip() == ""
