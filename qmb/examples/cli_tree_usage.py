"""Reference usage — thin click ``qmb`` command tree (Story 16.1).

Executable::

    python qmb/examples/cli_tree_usage.py

Shows the things Story 16.1 / B-1 / AR-10 pin down:

1. The command tree is the platform's single CLI surface: backtest, data,
   optimize, ledger, and config groups, built on the ``qmb_cli_pin`` click
   door. Capabilities live in the library; the door parses and transports.
2. Commands declare config/resource prerequisites and return a typed refusal
   when they are absent.
3. A backtest compiles through ``qmb.config.compile_run_config`` and submits
   to ``qmb.orchestrator.spawn_run``. The door does not compute a run-id —
   the compiler fingerprint is the run-id root.
"""

from __future__ import annotations

from typing import TypeVar

from click.testing import CliRunner
from qmb.config import ResolvedRunConfig
from qmb.doors.cli import (
    COMMAND_GROUPS,
    command_tree,
    invoke_backtest,
    require_prerequisites,
)
from qmb.doors.cli import (
    main as cli_main,
)
from qmb.orchestrator import IsolatedRun
from qmb.runloop import STREAM_SET_KEY
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def tree_is_the_platform_surface() -> None:
    tree = command_tree()
    assert tuple(tree) == COMMAND_GROUPS
    assert COMMAND_GROUPS == ("backtest", "data", "optimize", "sweep", "ledger", "config")
    runner = CliRunner()
    helped = runner.invoke(cli_main, ["--help"])
    assert helped.exit_code == 0, helped.output
    for group in COMMAND_GROUPS:
        assert group in helped.output
    catalog = runner.invoke(cli_main, ["data", "catalog"])
    assert catalog.exit_code == 0, catalog.output
    assert "download" in catalog.output
    print("command tree groups: " + ", ".join(COMMAND_GROUPS))


def missing_prerequisites_are_typed_refusals() -> None:
    refused = require_prerequisites("backtest.run", {})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    runner = CliRunner()
    invoked = runner.invoke(cli_main, ["backtest", "run"])
    assert invoked.exit_code != 0
    assert "unavailable dependency" in invoked.output + (invoked.stderr or "")
    print("absent resources return typed refusal: " + refused.category)


def backtest_compiles_then_submits_without_a_door_run_id() -> None:
    stamp = _unwrap(fingerprint({"n": "cli-tree-example"}), "stamp")
    config = ResolvedRunConfig(
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

    submitted = _unwrap(
        invoke_backtest(
            port="port",
            book_fragment="book",
            bms_fragment="bms",
            run_spec={"bot": "mean-reversion"},
            slices=(("eurusd",),),
            output_root="out",
            compiler=compiler,
            orchestrator=orchestrator,
        ),
        "backtest",
    )
    assert seen == ["compile", "spawn"]
    assert submitted.run_id == config.fingerprint
    print("compiled via compile_run_config; submitted to qmb.orchestrator")
    print("run-id is the compiler fingerprint; door computed none")


def main() -> None:
    tree_is_the_platform_surface()
    missing_prerequisites_are_typed_refusals()
    backtest_compiles_then_submits_without_a_door_run_id()
    print("qmb CLI command tree ok")


if __name__ == "__main__":
    main()
