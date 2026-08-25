"""Reference usage — CLI refusal rendering (Story 16.2).

Executable::

    python qmb/examples/cli_refusal_usage.py

Shows the things Story 16.2 / AR-58 / CT-04 pin down:

1. A typed refusal is RETURNED by the library and rendered by the door —
   never raised, never swallowed.
2. The CLI exits nonzero and writes machine-readable stderr JSON carrying
   category, context, and retryability.
3. A successful command exits zero.
4. A programmer error surfaces as an exception, distinct from the refusal
   channel.
"""

from __future__ import annotations

import json
from typing import TypeVar, cast

from click.testing import CliRunner
from qmb.doors.cli import invoke_data, main, render_refusal
from qmf.core.refusal import Result, TypedRefusal, is_ok, is_refusal

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def library_returns_door_renders() -> None:
    refused = invoke_data("download", {})
    assert is_refusal(refused)
    encoded = json.loads(render_refusal(refused))
    assert encoded["category"] == "unavailable dependency"
    assert encoded["retryability"] == "no"
    assert encoded["context"]["missing"] == ["destination"]
    runner = CliRunner()
    invoked = runner.invoke(main, ["data", "download"])
    assert invoked.exit_code != 0
    assert invoked.stdout.strip() == ""
    payload = json.loads(invoked.stderr)
    assert payload == encoded
    print("library RETURNED the refusal; door rendered stderr JSON")
    print("nonzero exit + category/context/retryability")


def success_exits_zero() -> None:
    runner = CliRunner()
    catalog = runner.invoke(main, ["data", "catalog"])
    assert catalog.exit_code == 0, catalog.output
    assert catalog.stderr.strip() == ""
    commands = _unwrap(invoke_data("catalog"), "catalog")
    listed = cast("tuple[str, ...]", commands["commands"])
    for name in listed:
        assert name in catalog.stdout
    print("successful run exits zero")


def programmer_error_is_not_the_refusal_channel() -> None:
    def compiler(port: object, **kwargs: object) -> Result[object]:
        _ = (port, kwargs)
        raise RuntimeError("programmer-error")

    runner = CliRunner()
    invoked = runner.invoke(
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
    assert isinstance(invoked.exception, RuntimeError)
    assert invoked.exception.args == ("programmer-error",)
    text = invoked.stderr.strip()
    if text:
        try:
            parsed: object = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            keys = set(cast("dict[str, object]", parsed))
            assert not {"category", "context", "retryability"} <= keys
    print("programmer error surfaces as an exception, not stderr JSON")


def door_never_raises_typed_refusal() -> None:
    runner = CliRunner()
    invoked = runner.invoke(main, ["optimize", "space"])
    assert invoked.exit_code != 0
    assert not isinstance(invoked.exception, TypedRefusal)
    payload = json.loads(invoked.stderr)
    assert payload["category"] in {
        "unavailable dependency",
        "invalid input",
    }
    print("typed refusal was not raised")


def main_example() -> None:
    library_returns_door_renders()
    success_exits_zero()
    programmer_error_is_not_the_refusal_channel()
    door_never_raises_typed_refusal()
    print("qmb CLI refusal rendering ok")


if __name__ == "__main__":
    main_example()
