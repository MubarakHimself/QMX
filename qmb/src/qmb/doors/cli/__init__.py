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
from datetime import datetime, timezone
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
    DATA_DOWNLOAD_OCCUPANCY,
    DATA_GENERATE_OCCUPANCY,
    DATA_MINTS_CT32,
    DATA_MINTS_EXPERIMENT_SPEC,
    DATA_QUERY_COMMANDS,
    DATA_QUERY_OCCUPANCY,
    DATA_RUN_COMMANDS,
    HOLDS_CACHE,
    LIBRARY_COMMANDS,
    LIBRARY_KINDS_OCCUPANCY,
    LIBRARY_MINTS_CT32,
    LIBRARY_MINTS_EXPERIMENT_SPEC,
    ORCHESTRATOR_ENTRY,
    SWEEP_BATCH_OCCUPANCY,
    SWEEP_COMMANDS,
    SWEEP_RANK_OCCUPANCY,
    BacktestSubmission,
    cli_tree_identity,
    command_prerequisites,
    command_tree,
    complete_registry,
    data_command_occupancy,
    invoke_backtest,
    invoke_config_compile,
    invoke_config_show,
    invoke_data,
    invoke_ledger_bar,
    invoke_ledger_merge,
    invoke_library_candidates,
    invoke_library_kinds,
    invoke_library_search,
    invoke_optimize_estimate,
    invoke_optimize_run,
    invoke_optimize_space,
    invoke_robustness_candle_perturbation,
    invoke_robustness_rule_significance,
    invoke_robustness_trade_shuffle,
    invoke_robustness_walk_forward,
    invoke_sweep_batch,
    invoke_sweep_count,
    invoke_sweep_rank,
    require_prerequisites,
)
from qmb.optimize import CostEstimate
from qmb.registryread import LibraryKindRoster, RegistryReadPort
from qmb.registryread.candidates import CandidateSet, SavedCandidateView
from qmb.registryread.search import LibrarySearch
from qmb.robustness import (
    PROCEDURE_MC_CANDLE_PERTURBATION,
    PROCEDURE_MC_TRADE_SHUFFLE,
    PROCEDURE_RULE_SIGNIFICANCE,
    PROCEDURE_WALK_FORWARD,
    RESAMPLING_SCHEMES,
    CandlePerturbationResult,
    SignificanceResult,
    TradeShuffleResult,
    WalkForwardPlan,
)
from qmb.sweep import SweepBatchReport, SweepRanking

_T = TypeVar("_T")

__all__ = [
    "AUTOCOMPLETE",
    "AUTOCOMPLETE_PORT",
    "BMS_RECORD_KIND",
    "BOOK_RECORD_KIND",
    "BOT_RECORD_KIND",
    "COMMAND_GROUPS",
    "COMPUTES_RUN_ID",
    "DATA_DOWNLOAD_OCCUPANCY",
    "DATA_GENERATE_OCCUPANCY",
    "DATA_MINTS_CT32",
    "DATA_MINTS_EXPERIMENT_SPEC",
    "DATA_QUERY_COMMANDS",
    "DATA_QUERY_OCCUPANCY",
    "DATA_RUN_COMMANDS",
    "HOLDS_CACHE",
    "LIBRARY_COMMANDS",
    "LIBRARY_KINDS_OCCUPANCY",
    "LIBRARY_MINTS_CT32",
    "LIBRARY_MINTS_EXPERIMENT_SPEC",
    "ORCHESTRATOR_ENTRY",
    "SWEEP_BATCH_OCCUPANCY",
    "SWEEP_COMMANDS",
    "SWEEP_RANK_OCCUPANCY",
    "BacktestSubmission",
    "cli_tree_identity",
    "command_prerequisites",
    "command_tree",
    "complete_registry",
    "data_command_occupancy",
    "invoke_backtest",
    "invoke_config_compile",
    "invoke_config_show",
    "invoke_data",
    "invoke_ledger_bar",
    "invoke_ledger_merge",
    "invoke_library_candidates",
    "invoke_library_kinds",
    "invoke_library_search",
    "invoke_optimize_estimate",
    "invoke_optimize_run",
    "invoke_optimize_space",
    "invoke_robustness_candle_perturbation",
    "invoke_robustness_rule_significance",
    "invoke_robustness_trade_shuffle",
    "invoke_robustness_walk_forward",
    "invoke_sweep_batch",
    "invoke_sweep_count",
    "invoke_sweep_rank",
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
    """Thin fronts over qmf-data rooms: download is a run; queries listed below.

    gap-check|verify|catalog|list are queries. No clone store, CDN product, or
    second catalog. Occupancy: data.download that mutates rooms is one qmb run
    invocation. Queries consume no occupancy, mint no CT-32, and mint no
    ExperimentSpec successor. Quality surfaces are read models over CT-13
    data-quality events and gap_check reports, not analysis.project. Derived
    datasets are fingerprinted qmf-data artifacts with a CT-07 lineage edge,
    never Library kinds. Vendor-style timezone clones that auto-update the
    source under a running experiment are refused; data_ref cites frozen CT-12
    split fingerprints.
    """


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
@click.option(
    "--timezone-clone",
    is_flag=True,
    default=False,
    help="Refused: auto-updating timezone clones are not allowed.",
)
@click.option(
    "--auto-update",
    is_flag=True,
    default=False,
    help="Refused: source auto-update under a running experiment is not allowed.",
)
@click.option(
    "--csv-store",
    is_flag=True,
    default=False,
    help="Refused: CSV/file import is a CT-15 adapter extend, not a new store.",
)
@click.option(
    "--cdn",
    is_flag=True,
    default=False,
    help="Refused: no CDN product or second catalog.",
)
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
    timezone_clone: bool,
    auto_update: bool,
    csv_store: bool,
    cdn: bool,
) -> None:
    """Download-once into the immutable raw archive (occupancy: run; mutates rooms).

    Vendor-style timezone clones that auto-update the source under a running
    experiment are refused; ExperimentSpec data_ref and governed run-config
    cite frozen CT-12 split fingerprints.
    """
    symbol: str | tuple[str, ...] | None
    if len(symbols) == 0:
        symbol = None
    elif len(symbols) == 1:
        symbol = symbols[0]
    else:
        symbol = symbols
    # The CLI door IS the composition root: when --end is omitted, the real
    # clock is read HERE and injected under the library's `now` key, so the
    # library below never reads the ambient wall clock (FR-002, DEC-0106).
    injected_now = None if end is not None else datetime.now(timezone.utc)  # ambient-scan: allow
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
                now=injected_now,
                resolution=resolution,
                side=side,
                overwrite=overwrite,
                license_tag=license_tag,
                world=world,
                timezone_clone=timezone_clone,
                auto_update=auto_update,
                csv_store=csv_store,
                cdn=cdn,
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
    """Verify window integrity (query: no occupancy, no CT-32).

    Quality surfaces are read models over CT-13 data-quality events and this
    report.
    """
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


@data_group.command("gap-check")
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
    "--bar-step-ns",
    default=None,
    help="Explicit expected bar step (UTC-ns); required, never invented.",
)
@click.option(
    "--calendar-rule-set",
    default=None,
    help="CT-02 rule set (e.g. forex-17NY); FX venues default to qmf-calendar-forex.",
)
@click.option(
    "--always-open/--no-always-open",
    default=False,
    help="Use an always-open CT-02 calendar (24/7); never the silent default.",
)
@click.option("--world", default=None, help="World-scoped raw room (default: replay).")
@click.pass_context
def data_gap_check(
    ctx: click.Context,
    archive: str | None,
    venue: str | None,
    symbol: str | None,
    start: str | None,
    end: str | None,
    resolution: str | None,
    side: str | None,
    bar_step_ns: str | None,
    calendar_rule_set: str | None,
    always_open: bool,
    world: str | None,
) -> None:
    """Calendar-aware gap detection (query: no occupancy, no CT-32).

    Quality surfaces are read models over CT-13 data-quality events and
    gap_check reports — not analysis.project.
    """
    _transport(
        ctx,
        invoke_data(
            "gap-check",
            _payload(
                ctx,
                archive=archive,
                venue=venue,
                symbol=symbol,
                start=start,
                end=end,
                resolution=resolution,
                side=side,
                bar_step_ns=bar_step_ns,
                calendar_rule_set=calendar_rule_set,
                always_open=always_open,
                world=world,
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
    """List coverage over Parquet rooms (query: no occupancy, no CT-32).

    The catalog is a rebuildable view over qmf-data rooms, never a second store.
    """
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
    """Alias of ``data list`` (query: no occupancy, no CT-32).

    Same machine-readable coverage payload. Not a second catalog product.
    """
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
    """Store-persisted synthetic series (occupancy: run; mutates rooms).

    world=simulated; not governed evidence. Derived series are fingerprinted
    artifacts with a CT-07 lineage edge, not Library kinds.
    """
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


@optimize_group.command("estimate")
@click.option(
    "--per-trial-runtime-ns",
    default=None,
    type=int,
    help="Measured typical per-trial runtime (ns); omit while not yet measured.",
)
@click.option(
    "--concurrency-cap",
    default=None,
    type=int,
    help="Governor min(cpu, memory) parallelism bound; or pass cpu/memory budgets on obj.",
)
@click.pass_context
def optimize_estimate(
    ctx: click.Context,
    per_trial_runtime_ns: int | None,
    concurrency_cap: int | None,
) -> None:
    """Estimate a Study's cost before committing compute (pure; spawns nothing)."""
    payload = _payload(ctx)
    _transport(
        ctx,
        invoke_optimize_estimate(
            budget=payload.get("budget"),
            param_count=payload.get("param_count"),
            declaration=payload.get("declaration"),
            per_trial_runtime=(
                per_trial_runtime_ns
                if per_trial_runtime_ns is not None
                else payload.get("per_trial_runtime")
            ),
            concurrency_cap=(
                concurrency_cap if concurrency_cap is not None else payload.get("concurrency_cap")
            ),
            cpu_budget=payload.get("cpu_budget"),
            memory_budget=payload.get("memory_budget"),
            projected_peak_memory=payload.get("projected_peak_memory"),
        ),
    )


@main.group("sweep")
def sweep_group() -> None:
    """Permutation sweep: pre-flight count, batch run, and rank query (B-12)."""


@sweep_group.command("count")
@click.argument(
    "bot",
    required=False,
    default=None,
    shell_complete=_shell_complete_kind(BOT_RECORD_KIND),
)
@click.option(
    "--book",
    default=None,
    help="Human Book alias; the sweep cites its context.",
    shell_complete=_shell_complete_kind(BOOK_RECORD_KIND),
)
@click.option(
    "--bms",
    default=None,
    help="Human BMS alias; the sweep cites its context.",
    shell_complete=_shell_complete_kind(BMS_RECORD_KIND),
)
@click.option("--instrument", "instruments", multiple=True, help="Instrument axis; repeatable.")
@click.option(
    "--seconds",
    "seconds",
    multiple=True,
    type=int,
    help="Time-interval BarSpec axis in seconds; repeatable.",
)
@click.pass_context
def sweep_count(
    ctx: click.Context,
    bot: str | None,
    book: str | None,
    bms: str | None,
    instruments: tuple[str, ...],
    seconds: tuple[int, ...],
) -> None:
    """Pre-flight run count for a declared sweep (pure inspection; spawns nothing)."""
    payload = _payload(ctx)
    declaration = _sweep_declaration(
        payload,
        bot=bot,
        book=book,
        bms=bms,
        instruments=instruments,
        seconds=seconds,
    )
    _transport(ctx, invoke_sweep_count(declaration=declaration))


# Occupancy: a governed CLI sweep.batch invocation is one qmb run unit wrapping
# the combo children. Each combo still writes exactly one ledger line (Story 20.3).
# Process-per-run children inside that invocation are not additional QMA jobs.
# This door does not place CT-47 ExperimentSpec (Epic 36).


@sweep_group.command("batch")
@click.option("--output-root", default=None, help="Isolated batch output root.")
@click.option(
    "--projected-peak-memory",
    default=None,
    type=int,
    help="Governor projected-peak memory in bytes.",
)
@click.pass_context
def sweep_batch(
    ctx: click.Context,
    output_root: str | None,
    projected_peak_memory: int | None,
) -> None:
    """Run an admitted sweep batch via qmb.sweep.run_sweep_batch."""
    payload = _payload(ctx, output_root=output_root, projected_peak_memory=projected_peak_memory)
    _transport(
        ctx,
        invoke_sweep_batch(
            admitted=payload.get("admitted"),
            output_root=payload.get("output_root"),
            ledger=payload.get("ledger"),
            combo_slices=payload.get("combo_slices"),
            projected_peak_memory=payload.get("projected_peak_memory"),
            cpu_budget=payload.get("cpu_budget"),
            memory_budget=payload.get("memory_budget"),
            budgets=payload.get("budgets"),
            on_full=payload.get("on_full"),
            cpu_cost=payload.get("cpu_cost"),
            invocation_flags=payload.get("invocation_flags"),
            workspace_defaults=payload.get("workspace_defaults"),
            condition_presets=payload.get("condition_presets", ()),
            role=payload.get("role"),
            factory_sandbox=payload.get("factory_sandbox"),
        ),
    )


# Occupancy: sweep.rank is a query. It consumes no occupancy, mints no CT-32,
# and mints no ExperimentSpec successor. A persist/database request is refused.


@sweep_group.command("rank")
@click.option("--sweep-id", default=None, help="Sweep id the fold reads (one sweep).")
@click.option("--objective", default=None, help="Roster measure_identity to order by.")
@click.option("--world", default=None, help="World the fold reads; never mixed.")
@click.option("--role", default=None, help="Ledger role the fold reads; never mixed.")
@click.option("--direction", default=None, help="ascending or descending.")
@click.option(
    "--persist",
    is_flag=True,
    default=False,
    help="Refused: ranking is a fold, not a candidate database.",
)
@click.option(
    "--database",
    default=None,
    help="Refused: ranking does not persist a candidate database.",
)
@click.option(
    "--candidate-database",
    default=None,
    help="Refused: ranking does not persist a candidate database.",
)
@click.pass_context
def sweep_rank(
    ctx: click.Context,
    sweep_id: str | None,
    objective: str | None,
    world: str | None,
    role: str | None,
    direction: str | None,
    persist: bool,
    database: str | None,
    candidate_database: str | None,
) -> None:
    """Rank a completed sweep as a read-time fold via qmb.sweep.rank_sweep."""
    payload = _payload(
        ctx,
        sweep_id=sweep_id,
        objective=objective,
        world=world,
        role=role,
        direction=direction,
        persist=persist,
        database=database,
        candidate_database=candidate_database,
    )
    _transport(
        ctx,
        invoke_sweep_rank(
            lines=payload.get("lines"),
            sweep_id=payload.get("sweep_id"),
            objective=payload.get("objective"),
            world=payload.get("world"),
            role=payload.get("role"),
            constraints=payload.get("constraints"),
            direction=payload.get("direction"),
            persist=payload.get("persist"),
            persist_candidates=payload.get("persist_candidates"),
            candidate_database=payload.get("candidate_database"),
            database=payload.get("database"),
            store=payload.get("store"),
            databank=payload.get("databank"),
        ),
    )


@main.group("robustness")
def robustness_group() -> None:
    """B-14 robustness ladder over the Epic 22 library.

    Walk-forward, trade-shuffle MC, candle-perturbation MC, and the pre-build
    rule-significance gate. Each command adapts the existing library rung.
    """


# Occupancy: a governed CLI robustness invocation is one qmb run unit.
# Process-per-run children inside that invocation are not additional QMA jobs.
# This door does not place CT-47 ExperimentSpec (Epic 36).
# Command registration order matches ROBUSTNESS_PROCEDURES (the tree).


@robustness_group.command(PROCEDURE_MC_TRADE_SHUFFLE)
@click.option("--base-seed", default=None, type=int)
@click.option("--scenario-count", default=None, type=int)
@click.option("--metric", "metrics", multiple=True)
@click.pass_context
def robustness_trade_shuffle(
    ctx: click.Context,
    base_seed: int | None,
    scenario_count: int | None,
    metrics: tuple[str, ...],
) -> None:
    """Trade-shuffle Monte Carlo via qmb.robustness.run_trade_shuffle."""
    payload = _payload(ctx, base_seed=base_seed, scenario_count=scenario_count)
    if metrics:
        payload.setdefault("metrics", metrics)
    _transport(
        ctx,
        invoke_robustness_trade_shuffle(
            trades=payload.get("trades"),
            starting_capital=payload.get("starting_capital"),
            period=payload.get("period"),
            base_seed=payload.get("base_seed"),
            metrics=payload.get("metrics"),
            config=payload.get("config"),
            scenario_count=payload.get("scenario_count"),
            band_probabilities=payload.get("band_probabilities", ()),
        ),
    )


@robustness_group.command(PROCEDURE_MC_CANDLE_PERTURBATION)
@click.option("--base-seed", default=None, type=int)
@click.option("--block-length", default=None, type=int)
@click.option("--scenario-count", default=None, type=int)
@click.pass_context
def robustness_candle_perturbation(
    ctx: click.Context,
    base_seed: int | None,
    block_length: int | None,
    scenario_count: int | None,
) -> None:
    """Candle-perturbation Monte Carlo via qmb.robustness.run_candle_perturbation."""
    payload = _payload(
        ctx,
        base_seed=base_seed,
        block_length=block_length,
        scenario_count=scenario_count,
    )
    _transport(
        ctx,
        invoke_robustness_candle_perturbation(
            candles=payload.get("candles"),
            base_seed=payload.get("base_seed"),
            block_length=payload.get("block_length"),
            scenario_count=payload.get("scenario_count"),
            config=payload.get("config"),
            seed_price=payload.get("seed_price"),
            run_root=payload.get("run_root"),
            objective_identity=payload.get("objective_identity"),
            scenario_objectives=payload.get("scenario_objectives"),
            objective_direction=payload.get("objective_direction"),
            band_probabilities=payload.get("band_probabilities", ()),
        ),
    )


@robustness_group.command(PROCEDURE_RULE_SIGNIFICANCE)
@click.option("--base-seed", default=None, type=int)
@click.option(
    "--resampling-scheme",
    default=None,
    type=click.Choice(list(RESAMPLING_SCHEMES), case_sensitive=False),
)
@click.option("--block-length", default=None, type=int)
@click.option("--iterations", default=None, type=int)
@click.option("--minimum-observations", default=None, type=int)
@click.pass_context
def robustness_rule_significance(
    ctx: click.Context,
    base_seed: int | None,
    resampling_scheme: str | None,
    block_length: int | None,
    iterations: int | None,
    minimum_observations: int | None,
) -> None:
    """Pre-build rule-significance gate via qmb.robustness.run_significance_gate."""
    payload = _payload(
        ctx,
        base_seed=base_seed,
        resampling_scheme=resampling_scheme,
        block_length=block_length,
        iterations=iterations,
        minimum_observations=minimum_observations,
    )
    _transport(
        ctx,
        invoke_robustness_rule_significance(
            signals=payload.get("signals"),
            base_seed=payload.get("base_seed"),
            resampling_scheme=payload.get("resampling_scheme"),
            block_length=payload.get("block_length"),
            iterations=payload.get("iterations"),
            minimum_observations=payload.get("minimum_observations"),
            config=payload.get("config"),
            band_probabilities=payload.get("band_probabilities", ()),
            stream_id=payload.get("stream_id"),
        ),
    )


@robustness_group.command(PROCEDURE_WALK_FORWARD)
@click.option("--window-count", default=None, type=int)
@click.option("--in-sample-span", default=None, type=int)
@click.option("--out-of-sample-span", default=None, type=int)
@click.option("--step", default=None, type=int)
@click.pass_context
def robustness_walk_forward(
    ctx: click.Context,
    window_count: int | None,
    in_sample_span: int | None,
    out_of_sample_span: int | None,
    step: int | None,
) -> None:
    """Walk-forward window sequence via qmb.robustness.plan_walk_forward."""
    payload = _payload(
        ctx,
        window_count=window_count,
        in_sample_span=in_sample_span,
        out_of_sample_span=out_of_sample_span,
        step=step,
    )
    _transport(
        ctx,
        invoke_robustness_walk_forward(
            windows=payload.get("windows"),
            config=payload.get("config"),
            window_count=payload.get("window_count"),
            in_sample_span=payload.get("in_sample_span"),
            out_of_sample_span=payload.get("out_of_sample_span"),
            step=payload.get("step"),
        ),
    )


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


@main.group("library")
def library_group() -> None:
    """Projection over existing fp1 kinds. Query only; no new COMP."""


@library_group.command("kinds")
@click.pass_context
def library_kinds(ctx: click.Context) -> None:
    """Enumerate Library kinds (existing fp1 list; coordinated ExperimentSpec)."""
    _transport(ctx, invoke_library_kinds())


@library_group.command("search")
@click.option("--kind", default=None, help="Library kind or saved-view citation.")
@click.option("--fp1", default=None, help="Source kind fp1; never name@version.")
@click.option("--world", default=None, help="World the ledger merge view reads.")
@click.option("--role", default=None, help="Role the ledger merge view reads.")
@click.option("--lane", default=None, help="ungoverned, governed, or coordinated.")
@click.option(
    "--staging",
    is_flag=True,
    default=False,
    help="Refused: Library search does not read QMA staging.",
)
@click.option(
    "--store",
    default=None,
    help="Refused: Library search does not open a fourth store.",
)
@click.pass_context
def library_search(
    ctx: click.Context,
    kind: str | None,
    fp1: str | None,
    world: str | None,
    role: str | None,
    lane: str | None,
    staging: bool,
    store: str | None,
) -> None:
    """Search Library kinds over as-of, ledger merge, and Experiment Ledger refs."""
    payload = _payload(ctx, kind=kind, fp1=fp1, world=world, role=role, lane=lane, store=store)
    _transport(
        ctx,
        invoke_library_search(
            kind=payload.get("kind"),
            fp1=payload.get("fp1"),
            port=payload.get("port"),
            ledger_lines=payload.get("ledger_lines"),
            world=payload.get("world"),
            role=payload.get("role"),
            experiment_refs=payload.get("experiment_refs"),
            saved_views=payload.get("saved_views"),
            lane=payload.get("lane"),
            staging=staging if staging else payload.get("staging"),
            store=payload.get("store"),
            sqlite=payload.get("sqlite"),
            database=payload.get("database"),
            fourth_store=payload.get("fourth_store"),
        ),
    )


@library_group.command("candidates")
@click.option("--kind", default=None, help="Optional Library kind filter.")
@click.option("--fp1", default=None, help="Optional source kind fp1 filter.")
@click.option("--zone", default=None, help="Optional zone filter: dev or live.")
@click.option("--world", default=None, help="World the ledger merge view reads.")
@click.option("--role", default=None, help="Role the ledger merge view reads.")
@click.option("--lane", default=None, help="ungoverned, governed, or coordinated.")
@click.option("--sweep-id", default=None, help="Sweep id when ranking via sweep.rank.")
@click.option("--objective", default=None, help="Roster measure_identity for sweep.rank.")
@click.option("--direction", default=None, help="ascending or descending.")
@click.option("--home", default=None, help="ungoverned, governed, or coordinated.")
@click.option("--run-dir", default=None, help="Source run-dir for governed JSON sidecar.")
@click.option(
    "--cite",
    default=None,
    help="Refused without a body: a citation is not a saved view.",
)
@click.option(
    "--staging",
    is_flag=True,
    default=False,
    help="Refused: candidate-set query does not read QMA staging.",
)
@click.option(
    "--persist",
    is_flag=True,
    default=False,
    help="Refused: candidate set does not persist copied rows.",
)
@click.option(
    "--database",
    default=None,
    help="Refused: candidate set is not a sqlite table (DEC-0084 stays dead).",
)
@click.option(
    "--sqlite",
    is_flag=True,
    default=False,
    help="Refused: candidate set is not a sqlite table (DEC-0084 stays dead).",
)
@click.option(
    "--registry-kind",
    is_flag=True,
    default=False,
    help="Refused: candidates are not a new qmf-registry kind.",
)
@click.pass_context
def library_candidates(
    ctx: click.Context,
    kind: str | None,
    fp1: str | None,
    zone: str | None,
    world: str | None,
    role: str | None,
    lane: str | None,
    sweep_id: str | None,
    objective: str | None,
    direction: str | None,
    home: str | None,
    run_dir: str | None,
    cite: str | None,
    staging: bool,
    persist: bool,
    database: str | None,
    sqlite: bool,
    registry_kind: bool,
) -> None:
    """Retain / filter / rank candidates as a read-time view (Story 34.3)."""
    payload = _payload(
        ctx,
        kind=kind,
        fp1=fp1,
        zone=zone,
        world=world,
        role=role,
        lane=lane,
        sweep_id=sweep_id,
        objective=objective,
        direction=direction,
        home=home,
        run_dir=run_dir,
        cite=cite,
        database=database,
    )
    _transport(
        ctx,
        invoke_library_candidates(
            kind=payload.get("kind"),
            fp1=payload.get("fp1"),
            zone=payload.get("zone"),
            port=payload.get("port"),
            ledger_lines=payload.get("ledger_lines"),
            world=payload.get("world"),
            role=payload.get("role"),
            experiment_refs=payload.get("experiment_refs"),
            lane=payload.get("lane"),
            sweep_id=payload.get("sweep_id"),
            objective=payload.get("objective"),
            constraints=payload.get("constraints"),
            direction=payload.get("direction"),
            home=payload.get("home"),
            run_dir=payload.get("run_dir"),
            body=payload.get("body"),
            cite=payload.get("cite"),
            staging=staging if staging else payload.get("staging"),
            persist=persist if persist else payload.get("persist"),
            database=payload.get("database"),
            sqlite=sqlite if sqlite else payload.get("sqlite"),
            mint_registry_kind=(
                registry_kind if registry_kind else payload.get("mint_registry_kind")
            ),
            registry_kind=registry_kind if registry_kind else payload.get("registry_kind"),
        ),
    )


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


def _sweep_declaration(
    payload: Mapping[str, object],
    *,
    bot: str | None,
    book: str | None,
    bms: str | None,
    instruments: tuple[str, ...],
    seconds: tuple[int, ...],
) -> object:
    """Assemble the raw axis mapping the pure library function expands (B-12).

    A pre-assembled ``declaration`` on the invocation object wins; otherwise the
    door folds the parsed options into the axis mapping. The door computes no run
    count of its own — that lives once in ``qmb.sweep``.
    """
    existing = payload.get("declaration")
    if existing is not None:
        return existing
    timeframes = payload.get("timeframes")
    if timeframes is None and seconds:
        timeframes = [{"kind": "time-interval", "seconds": value} for value in seconds]
    return {
        "bot": bot if bot is not None else payload.get("bot"),
        "book": book if book is not None else payload.get("book"),
        "bms": bms if bms is not None else payload.get("bms"),
        "instruments": list(instruments) if instruments else payload.get("instruments"),
        "timeframes": timeframes,
        "parameters": payload.get("parameters"),
    }


def _transport(ctx: click.Context, result: Result[_T]) -> None:
    if is_refusal(result):
        click.echo(render_refusal(result), err=True)
        ctx.exit(1)
    if is_ok(result):
        click.echo(_format_ok(result.value))


def _format_ok(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        # Sweep pre-flight run count and other scalar library results.
        return str(value)
    if isinstance(value, BacktestSubmission):
        return value.run_id.value
    if isinstance(value, ResolvedRunConfig):
        return value.fingerprint.value
    if isinstance(value, CostEstimate):
        # A pre-flight estimate is machine-readable JSON; it spawns no trial.
        return json.dumps(_jsonable_payload(value.fp1_identity()), ensure_ascii=False)
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
    if isinstance(
        value,
        (
            CandlePerturbationResult,
            CandidateSet,
            LibraryKindRoster,
            LibrarySearch,
            SavedCandidateView,
            SignificanceResult,
            SweepBatchReport,
            SweepRanking,
            TradeShuffleResult,
            WalkForwardPlan,
        ),
    ):
        return json.dumps(_jsonable_payload(value.fp1_identity()), ensure_ascii=False)
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
