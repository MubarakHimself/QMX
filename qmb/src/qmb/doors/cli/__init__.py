"""Thin ``qmb`` CLI door (B-1).

Adaptation only: parsing, transport, and refusal rendering. The door holds no
cache and computes no run-id of its own (DEC-0159, DEC-0160). Click is pinned
by ``registry:qmb_cli_pin``; the pin value lives in the registry and the
distribution manifest, never restated here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeVar, cast

import click
from qmf.core.refusal import Result, is_ok, is_refusal

from qmb._display import __version__
from qmb.config import ResolvedRunConfig
from qmb.doors import CLI_PROG
from qmb.doors.cli.render import render_refusal
from qmb.doors.cli.tree import (
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
    require_prerequisites,
)

_T = TypeVar("_T")

__all__ = [
    "COMMAND_GROUPS",
    "COMPUTES_RUN_ID",
    "HOLDS_CACHE",
    "ORCHESTRATOR_ENTRY",
    "BacktestSubmission",
    "cli_tree_identity",
    "command_prerequisites",
    "command_tree",
    "invoke_backtest",
    "invoke_config_compile",
    "invoke_config_show",
    "invoke_data",
    "invoke_ledger_bar",
    "invoke_ledger_merge",
    "invoke_optimize_run",
    "invoke_optimize_space",
    "main",
    "render_refusal",
    "require_prerequisites",
]


class _TunnelGroup(click.Group):
    """``qmb backtest <bot>`` is the ``run`` subcommand (SCN-0012)."""

    def resolve_command(
        self,
        ctx: click.Context,
        args: list[str],
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args.insert(0, "run")
        return super().resolve_command(ctx, args)


@click.group(name=CLI_PROG)
@click.version_option(version=__version__, prog_name=CLI_PROG)
@click.pass_context
def main(ctx: click.Context) -> None:
    """QMX experimentation/backtesting library and CLI (COMP-QMB)."""
    ctx.ensure_object(dict)


@main.command("version")
def show_version() -> None:
    """Print display-only SemVer provenance. Never identity."""
    click.echo(__version__)


@main.group("backtest", cls=_TunnelGroup)
def backtest_group() -> None:
    """Compile one run-config and submit it to the orchestrator."""


@backtest_group.command("run")
@click.argument("bot", required=False, default=None)
@click.option("--book", default=None, help="Human Book alias; the artifact cites fp1.")
@click.option("--bms", default=None, help="Human BMS alias; the artifact cites fp1.")
@click.option("--output-root", default=None, help="Isolated run output root.")
@click.pass_context
def backtest_run(
    ctx: click.Context,
    bot: str | None,
    book: str | None,
    bms: str | None,
    output_root: str | None,
) -> None:
    """Compile via qmb.config.compile_run_config and submit to qmb.orchestrator."""
    payload = _payload(ctx, output_root=output_root)
    _apply_run_spec(payload, bot=bot)
    _transport(
        ctx,
        invoke_backtest(
            port=payload.get("port"),
            book_fragment=payload.get("book_fragment"),
            bms_fragment=payload.get("bms_fragment"),
            run_spec=payload.get("run_spec"),
            invocation_flags=payload.get("invocation_flags"),
            workspace_defaults=payload.get("workspace_defaults"),
            condition_presets=payload.get("condition_presets", ()),
            slices=payload.get("slices"),
            output_root=payload.get("output_root"),
            compiler=payload.get("compiler"),
            orchestrator=payload.get("orchestrator"),
            cancel=payload.get("cancel"),
            limits=payload.get("limits"),
            probe=payload.get("probe"),
        ),
    )
    _ = (book, bms)


@main.group("data")
def data_group() -> None:
    """Thin fronts over qmf-data contracts (download, verify, catalog, generate)."""


@data_group.command("download")
@click.option("--destination", default=None)
@click.pass_context
def data_download(ctx: click.Context, destination: str | None) -> None:
    """Download-once into the immutable raw archive (B-11)."""
    _transport(ctx, invoke_data("download", _payload(ctx, destination=destination)))


@data_group.command("verify")
@click.option("--archive", default=None)
@click.pass_context
def data_verify(ctx: click.Context, archive: str | None) -> None:
    """Verify an ingested window's provenance and license tag."""
    _transport(ctx, invoke_data("verify", _payload(ctx, archive=archive)))


@data_group.command("catalog")
@click.pass_context
def data_catalog(ctx: click.Context) -> None:
    """Catalog the thin data-command fronts."""
    _transport(ctx, invoke_data("catalog", _payload(ctx)))


@data_group.command("generate")
@click.option("--destination", default=None)
@click.pass_context
def data_generate(ctx: click.Context, destination: str | None) -> None:
    """Store-persisted synthetic series (world=simulated; not governed evidence)."""
    _transport(ctx, invoke_data("generate", _payload(ctx, destination=destination)))


@main.group("optimize")
def optimize_group() -> None:
    """Declared parameter spaces and generation-stepped trials (B-8)."""


@optimize_group.command("run")
@click.argument("bot", required=False, default=None)
@click.option("--output-root", default=None)
@click.pass_context
def optimize_run(ctx: click.Context, bot: str | None, output_root: str | None) -> None:
    """Submit one trial run through the same compiler and orchestrator."""
    payload = _payload(ctx, output_root=output_root)
    _apply_run_spec(payload, bot=bot)
    _transport(
        ctx,
        invoke_optimize_run(
            declaration=payload.get("declaration"),
            port=payload.get("port"),
            book_fragment=payload.get("book_fragment"),
            bms_fragment=payload.get("bms_fragment"),
            run_spec=payload.get("run_spec"),
            invocation_flags=payload.get("invocation_flags"),
            workspace_defaults=payload.get("workspace_defaults"),
            condition_presets=payload.get("condition_presets", ()),
            slices=payload.get("slices"),
            output_root=payload.get("output_root"),
            compiler=payload.get("compiler"),
            orchestrator=payload.get("orchestrator"),
            cancel=payload.get("cancel"),
            limits=payload.get("limits"),
            probe=payload.get("probe"),
        ),
    )


@optimize_group.command("space")
@click.pass_context
def optimize_space(ctx: click.Context) -> None:
    """Read the CT-33-authoritative parameter-space schema."""
    payload = _payload(ctx)
    _transport(ctx, invoke_optimize_space(declaration=payload.get("declaration")))


@main.group("ledger")
def ledger_group() -> None:
    """WriterId-scoped ledger merge views; never a stored pass/fail (B-4)."""


@ledger_group.command("merge")
@click.option("--root", default=None)
@click.option("--world", default=None)
@click.option("--role", default=None)
@click.pass_context
def ledger_merge(
    ctx: click.Context,
    root: str | None,
    world: str | None,
    role: str | None,
) -> None:
    """Merge WriterId fragments in one world-and-role namespace."""
    payload = _payload(ctx, root=root, world=world, role=role)
    _transport(
        ctx,
        invoke_ledger_merge(
            root=payload.get("root"),
            world=payload.get("world"),
            role=payload.get("role"),
        ),
    )


@ledger_group.command("bar")
@click.option("--root", default=None)
@click.option("--world", default=None)
@click.pass_context
def ledger_bar(ctx: click.Context, root: str | None, world: str | None) -> None:
    """Book-bar read: confirmation lines only."""
    payload = _payload(ctx, root=root, world=world)
    _transport(ctx, invoke_ledger_bar(root=payload.get("root"), world=payload.get("world")))


@main.group("config")
def config_group() -> None:
    """The B-3 config compiler: one resolved, fingerprinted run-config."""


@config_group.command("compile")
@click.pass_context
def config_compile(ctx: click.Context) -> None:
    """Compile one resolved run-config. The fingerprint is the run-id root."""
    payload = _payload(ctx)
    _transport(
        ctx,
        invoke_config_compile(
            port=payload.get("port"),
            book_fragment=payload.get("book_fragment"),
            bms_fragment=payload.get("bms_fragment"),
            run_spec=payload.get("run_spec"),
            invocation_flags=payload.get("invocation_flags"),
            workspace_defaults=payload.get("workspace_defaults"),
            condition_presets=payload.get("condition_presets", ()),
            compiler=payload.get("compiler"),
        ),
    )


@config_group.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show the resolved-run-config identity schema."""
    _ = ctx
    _transport(ctx, invoke_config_show())


def _payload(ctx: click.Context, **parsed: object) -> dict[str, object]:
    raw = ctx.obj
    payload: dict[str, object] = {}
    if isinstance(raw, Mapping):
        for key, item in cast("Mapping[object, object]", raw).items():
            payload[str(key)] = item
    for key, value in parsed.items():
        if value is not None and key not in payload:
            payload[key] = value
    return payload


def _apply_run_spec(payload: dict[str, object], *, bot: str | None) -> None:
    if "run_spec" in payload or not bot:
        return
    payload["run_spec"] = {"bot": bot}


def _transport(ctx: click.Context, result: Result[_T]) -> None:
    if is_refusal(result):
        click.echo(render_refusal(result), err=True)
        ctx.exit(1)
    if is_ok(result):
        click.echo(_format_ok(result.value))


def _format_ok(value: object) -> str:
    if isinstance(value, BacktestSubmission):
        return value.run_id.value
    if isinstance(value, ResolvedRunConfig):
        return value.fingerprint.value
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        commands = mapping.get("commands")
        if isinstance(commands, Sequence) and not isinstance(commands, (str, bytes)):
            items = cast("Sequence[object]", commands)
            return " ".join(str(item) for item in items)
        class_token = mapping.get("class")
        if isinstance(class_token, str):
            return class_token
        command = mapping.get("command")
        if isinstance(command, str):
            return command
    if isinstance(value, tuple):
        return str(len(cast("tuple[object, ...]", value)))
    return "ok"
