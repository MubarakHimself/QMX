"""Thin ``qmb`` CLI door (B-1).

Adaptation only: parsing, transport, refusal rendering, and registry
enumeration for autocomplete through the B-15 port. The door holds no
cache and computes no run-id of its own (DEC-0159, DEC-0160, DEC-0165).
Autocomplete uses click's native ``shell_complete`` — no bespoke completion
machinery. Click is pinned by ``registry:qmb_cli_pin``; the pin value lives
in the registry and the distribution manifest, never restated here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar, cast

import click
from click.shell_completion import CompletionItem
from qmf.core.refusal import Result, is_ok, is_refusal

from qmb._display import __version__
from qmb.config import ResolvedRunConfig
from qmb.doors import CLI_PROG
from qmb.doors.cli.render import render_refusal
from qmb.doors.cli.tree import (
    AUTOCOMPLETE,
    AUTOCOMPLETE_PORT,
    BMS_RECORD_KIND,
    BOOK_RECORD_KIND,
    BOT_RECORD_KIND,
    COMMAND_GROUPS,
    COMPUTES_RUN_ID,
    HOLDS_CACHE,
    ORCHESTRATOR_ENTRY,
    BacktestSubmission,
    cli_tree_identity,
    command_prerequisites,
    command_tree,
    complete_registry,
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
from qmb.registryread import RegistryReadPort

_T = TypeVar("_T")

__all__ = [
    "AUTOCOMPLETE",
    "AUTOCOMPLETE_PORT",
    "BMS_RECORD_KIND",
    "BOOK_RECORD_KIND",
    "BOT_RECORD_KIND",
    "COMMAND_GROUPS",
    "COMPUTES_RUN_ID",
    "HOLDS_CACHE",
    "ORCHESTRATOR_ENTRY",
    "BacktestSubmission",
    "cli_tree_identity",
    "command_prerequisites",
    "command_tree",
    "complete_registry",
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


_ShellComplete = Callable[[click.Context, click.Parameter, str], list[CompletionItem[str]]]


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


def _port_from_obj(obj: object) -> object:
    """The injected B-15 port, or ``None`` — never a door-side cache."""
    if isinstance(obj, RegistryReadPort):
        return obj
    if isinstance(obj, Mapping):
        body = cast("Mapping[str, object]", obj)
        return body.get("port")
    return None


def _shell_complete_kind(kind: str) -> _ShellComplete:
    """Click-native ``shell_complete`` callback over the one registry-read port."""

    def _complete(
        ctx: click.Context,
        param: click.Parameter,
        incomplete: str,
        *,
        _kind: str = kind,
    ) -> list[CompletionItem[str]]:
        _ = param
        items = complete_registry(_port_from_obj(ctx.find_root().obj), incomplete, kind=_kind)
        return [CompletionItem(item.value, help=item.cite()) for item in items]

    return _complete


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
@click.argument(
    "bot",
    required=False,
    default=None,
    shell_complete=_shell_complete_kind(BOT_RECORD_KIND),
)
@click.option(
    "--book",
    default=None,
    help="Human Book alias; the artifact cites fp1.",
    shell_complete=_shell_complete_kind(BOOK_RECORD_KIND),
)
@click.option(
    "--bms",
    default=None,
    help="Human BMS alias; the artifact cites fp1.",
    shell_complete=_shell_complete_kind(BMS_RECORD_KIND),
)
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
    """Thin fronts over qmf-data contracts (download, verify, list, catalog, generate)."""


@data_group.command("download")
@click.option("--destination", default=None, help="World-scoped raw-archive root.")
@click.option("--venue", default=None, help="Venue token for the acquisition window.")
@click.option(
    "--symbol",
    "symbols",
    multiple=True,
    help="Symbol(s); repeat or pass comma-separated.",
)
@click.option("--start", default=None, help="Window start (int64 UTC-ns or ISO-8601).")
@click.option(
    "--end",
    default=None,
    help="Window end (int64 UTC-ns or ISO-8601); defaults to end of today UTC.",
)
@click.option("--resolution", default=None, help="Resolution (Dukascopy #1: tick).")
@click.option(
    "--side",
    default=None,
    type=click.Choice(["bid", "ask", "both"], case_sensitive=False),
    help="Quote side streams: bid, ask, or both.",
)
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Append a new CT-10 revision instead of idempotent r1 intake.",
)
@click.option("--license-tag", default=None, help="Per-window licence tag metadata.")
@click.option("--world", default=None, help="World-scoped raw room (default: replay).")
@click.pass_context
def data_download(
    ctx: click.Context,
    destination: str | None,
    venue: str | None,
    symbols: tuple[str, ...],
    start: str | None,
    end: str | None,
    resolution: str | None,
    side: str | None,
    overwrite: bool,
    license_tag: str | None,
    world: str | None,
) -> None:
    """Download-once into the immutable raw archive (B-11)."""
    symbol: str | tuple[str, ...] | None
    if len(symbols) == 0:
        symbol = None
    elif len(symbols) == 1:
        symbol = symbols[0]
    else:
        symbol = symbols
    _transport(
        ctx,
        invoke_data(
            "download",
            _payload(
                ctx,
                destination=destination,
                venue=venue,
                symbol=symbol,
                start=start,
                end=end,
                resolution=resolution,
                side=side,
                overwrite=overwrite,
                license_tag=license_tag,
                world=world,
            ),
        ),
    )


@data_group.command("verify")
@click.option("--archive", default=None, help="World-scoped raw-archive root.")
@click.option("--venue", default=None, help="Venue token for the window.")
@click.option("--symbol", default=None, help="Symbol token for the window.")
@click.option("--start", default=None, help="Window start (int64 UTC-ns or ISO-8601).")
@click.option("--end", default=None, help="Window end (int64 UTC-ns or ISO-8601).")
@click.option("--resolution", default=None, help="Resolution (default tick).")
@click.option(
    "--side",
    default=None,
    type=click.Choice(["bid", "ask", "both"], case_sensitive=False),
    help="Requested quote side streams: bid, ask, or both.",
)
@click.option(
    "--edge-tolerance-ns",
    default=None,
    help="Armed edge tolerance in UTC-ns; blank leaves the guard un-armed.",
)
@click.option(
    "--expected-step-ns",
    default=None,
    help="Optional interior-gap step (UTC-ns); blank does not invent a threshold.",
)
@click.option("--world", default=None, help="World-scoped raw room (default: replay).")
@click.option("--correlation-id", default=None, help="Propagated CT-13 linking annotation.")
@click.pass_context
def data_verify(
    ctx: click.Context,
    archive: str | None,
    venue: str | None,
    symbol: str | None,
    start: str | None,
    end: str | None,
    resolution: str | None,
    side: str | None,
    edge_tolerance_ns: str | None,
    expected_step_ns: str | None,
    world: str | None,
    correlation_id: str | None,
) -> None:
    """Verify an acquired window's integrity (Story 18.4)."""
    _transport(
        ctx,
        invoke_data(
            "verify",
            _payload(
                ctx,
                archive=archive,
                venue=venue,
                symbol=symbol,
                start=start,
                end=end,
                resolution=resolution,
                side=side,
                edge_tolerance_ns=edge_tolerance_ns,
                expected_step_ns=expected_step_ns,
                world=world,
                correlation_id=correlation_id,
            ),
        ),
    )


@data_group.command("list")
@click.option("--destination", default=None, help="World-scoped raw-archive root.")
@click.option("--venue", default=None, help="Venue token to query.")
@click.option("--symbol", default=None, help="Symbol token to query.")
@click.option("--resolution", default=None, help="Resolution (default tick).")
@click.option(
    "--side",
    default=None,
    type=click.Choice(["bid", "ask", "both"], case_sensitive=False),
    help="Quote side(s) to report; both emits bid and ask rows.",
)
@click.option("--start", default=None, help="Optional window start (int64 UTC-ns).")
@click.option("--end", default=None, help="Optional window end (int64 UTC-ns).")
@click.option("--world", default=None, help="World-scoped raw room (default: replay).")
@click.pass_context
def data_list(
    ctx: click.Context,
    destination: str | None,
    venue: str | None,
    symbol: str | None,
    resolution: str | None,
    side: str | None,
    start: str | None,
    end: str | None,
    world: str | None,
) -> None:
    """List coverage per (venue, symbol, resolution, side) over Parquet rooms."""
    _transport(
        ctx,
        invoke_data(
            "list",
            _payload(
                ctx,
                destination=destination,
                venue=venue,
                symbol=symbol,
                resolution=resolution,
                side=side,
                start=start,
                end=end,
                world=world,
            ),
        ),
    )


@data_group.command("catalog")
@click.option("--destination", default=None, help="World-scoped raw-archive root.")
@click.option("--venue", default=None, help="Venue token to query.")
@click.option("--symbol", default=None, help="Symbol token to query.")
@click.option("--resolution", default=None, help="Resolution (default tick).")
@click.option(
    "--side",
    default=None,
    type=click.Choice(["bid", "ask", "both"], case_sensitive=False),
    help="Quote side(s) to report; both emits bid and ask rows.",
)
@click.option("--start", default=None, help="Optional window start (int64 UTC-ns).")
@click.option("--end", default=None, help="Optional window end (int64 UTC-ns).")
@click.option("--world", default=None, help="World-scoped raw room (default: replay).")
@click.pass_context
def data_catalog(
    ctx: click.Context,
    destination: str | None,
    venue: str | None,
    symbol: str | None,
    resolution: str | None,
    side: str | None,
    start: str | None,
    end: str | None,
    world: str | None,
) -> None:
    """Alias of ``data list`` — same machine-readable coverage payload."""
    _transport(
        ctx,
        invoke_data(
            "catalog",
            _payload(
                ctx,
                destination=destination,
                venue=venue,
                symbol=symbol,
                resolution=resolution,
                side=side,
                start=start,
                end=end,
                world=world,
            ),
        ),
    )


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
@click.argument(
    "bot",
    required=False,
    default=None,
    shell_complete=_shell_complete_kind(BOT_RECORD_KIND),
)
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
        # Story 18.3/18.4: list/catalog/verify payloads are machine-readable JSON.
        if "entries" in mapping and mapping.get("command") in {"list", "catalog"}:
            return json.dumps(_jsonable_payload(mapping), ensure_ascii=False)
        if mapping.get("command") == "verify" and "verdict" in mapping:
            return json.dumps(_jsonable_payload(mapping), ensure_ascii=False)
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


def _jsonable_payload(value: object) -> object:
    """JSON-native mirror of a coverage / door payload."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (str, int)):
        return value
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {str(key): _jsonable_payload(item) for key, item in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast("Sequence[object]", value)
        return [_jsonable_payload(item) for item in sequence]
    return str(value)
