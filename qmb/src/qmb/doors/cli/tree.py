"""Click-free CLI command tree: groups, prerequisites, and transport (B-1).

Every capability lives once in the library. This module sequences declared
library entry points — ``compile_run_config`` then ``qmb.orchestrator.spawn_run``
— and never computes a run-id or holds a cache (DEC-0159, DEC-0160).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid, policy, unavailable
from qmb.analysis import (
    ANALYSIS_PROJECT_MINTS_CT32,
    ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC,
    ANALYSIS_PROJECT_OCCUPANCY,
    ANALYSIS_RERUN_MINTS_CT32,
    ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC,
    ANALYSIS_RERUN_OCCUPANCY,
    COMPARE_RUNS_MINTS_CT32,
    COMPARE_RUNS_MINTS_EXPERIMENT_SPEC,
    COMPARE_RUNS_OCCUPANCY,
    CompareReadout,
    ProjectionView,
    RerunOutcome,
    compare_runs,
    project,
    rerun,
)
from qmb.config import (
    BMS_RECORD_KIND,
    BOOK_RECORD_KIND,
    ResolvedRunConfig,
    compile_run_config,
    run_config_identity,
)
from qmb.data import (
    DATA_COMMANDS,
    catalog,
    data_front_identity,
    gap_check,
    guard_data_door,
    has_generator_config,
    list_data,
    verify,
)
from qmb.data import download as run_download
from qmb.data import generate as run_generate
from qmb.doors import CLI_PIN_KEY, CLI_PROG
from qmb.ledger import ROLE_CONFIRMATION, LedgerLine
from qmb.optimize import CostEstimate, estimate_study_cost, parameter_space_from_bot
from qmb.orchestrator import (
    ON_FULL_ENQUEUE,
    GovernorBudgets,
    IsolatedRun,
    read_book_bar,
    read_merge_view,
    spawn_run,
)
from qmb.registryread import (
    LIBRARY_KINDS_OCCUPANCY,
    LIBRARY_MINTS_CT32,
    LIBRARY_MINTS_EXPERIMENT_SPEC,
    LibraryKindRoster,
    RegistryCompletion,
    RegistryReadPort,
    enumerate_library_kinds,
)
from qmb.registryread.candidates import (
    CANDIDATE_SET_MINTS_CT32,
    CANDIDATE_SET_MINTS_EXPERIMENT_SPEC,
    CANDIDATE_SET_OCCUPANCY,
    CandidateSet,
    SavedCandidateView,
    query_candidates,
    save_candidate_view,
)
from qmb.registryread.search import (
    LIBRARY_SEARCH_MINTS_CT32,
    LIBRARY_SEARCH_MINTS_EXPERIMENT_SPEC,
    LIBRARY_SEARCH_OCCUPANCY,
    LibrarySearch,
    search_library,
)
from qmb.robustness import (
    PROCEDURE_MC_CANDLE_PERTURBATION,
    PROCEDURE_MC_TRADE_SHUFFLE,
    PROCEDURE_RULE_SIGNIFICANCE,
    PROCEDURE_WALK_FORWARD,
    ROBUSTNESS_PROCEDURES,
    CandlePerturbationResult,
    SignificanceResult,
    TradeShuffleResult,
    WalkForwardPlan,
    plan_walk_forward,
    run_candle_perturbation,
    run_significance_gate,
    run_trade_shuffle,
)
from qmb.sweep import (
    RANK_DESCENDING,
    SweepBatchReport,
    SweepRanking,
    preflight_run_count,
    rank_sweep,
    run_sweep_batch,
)
from qmb.workbench import refuse_caller_declared_lane_fields

__all__ = [
    "ANALYSIS_COMMANDS",
    "ANALYSIS_NAMED_METHODS",
    "ANALYSIS_PROJECT_MINTS_CT32",
    "ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC",
    "ANALYSIS_PROJECT_OCCUPANCY",
    "ANALYSIS_RERUN_MINTS_CT32",
    "ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC",
    "ANALYSIS_RERUN_OCCUPANCY",
    "AUTOCOMPLETE",
    "AUTOCOMPLETE_PORT",
    "BMS_RECORD_KIND",
    "BOOK_RECORD_KIND",
    "BOT_RECORD_KIND",
    "COMMAND_GROUPS",
    "COMPARE_RUNS_MINTS_CT32",
    "COMPARE_RUNS_MINTS_EXPERIMENT_SPEC",
    "COMPARE_RUNS_OCCUPANCY",
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
    "analysis_command_occupancy",
    "cli_tree_identity",
    "command_prerequisites",
    "command_tree",
    "complete_registry",
    "data_command_occupancy",
    "invoke_analysis_project",
    "invoke_analysis_rerun",
    "invoke_backtest",
    "invoke_compare_runs",
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
    "require_prerequisites",
]

COMMAND_GROUPS: Final[tuple[str, ...]] = (
    "backtest",
    "data",
    "optimize",
    "sweep",
    "robustness",
    "ledger",
    "library",
    "analysis",
    "config",
)
LIBRARY_COMMANDS: Final[tuple[str, ...]] = ("kinds", "search", "candidates")
# Story 35.1 occupancy: analysis.project is a query. Story 35.3: rerun is a run.
# Story 35.5: compare is a readout query, not a named analysis method.
ANALYSIS_COMMANDS: Final[tuple[str, ...]] = ("project", "rerun", "compare")
ANALYSIS_NAMED_METHODS: Final[tuple[str, ...]] = ("project", "rerun")
COMPUTES_RUN_ID: Final[bool] = False
HOLDS_CACHE: Final[bool] = False
ORCHESTRATOR_ENTRY: Final[str] = "qmb.orchestrator.spawn_run"
AUTOCOMPLETE: Final[str] = "click.shell_complete"
AUTOCOMPLETE_PORT: Final[str] = "qmb.registryread"
BOT_RECORD_KIND: Final[str] = "bot-definition"
# Story 33.2 occupancy: batch is one governed qmb run wrapping combo children;
# rank is a query fold and consumes none.
SWEEP_COMMANDS: Final[tuple[str, ...]] = ("count", "batch", "rank")
SWEEP_BATCH_OCCUPANCY: Final[str] = "run"
SWEEP_RANK_OCCUPANCY: Final[str] = "query"
# Story 33.3 occupancy: download (and generate) that mutate rooms are one
# governed qmb run invocation. gap-check/verify/catalog/list are queries.
DATA_RUN_COMMANDS: Final[tuple[str, ...]] = ("download", "generate")
DATA_QUERY_COMMANDS: Final[tuple[str, ...]] = ("gap-check", "verify", "catalog", "list")
DATA_DOWNLOAD_OCCUPANCY: Final[str] = "run"
DATA_GENERATE_OCCUPANCY: Final[str] = "run"
DATA_QUERY_OCCUPANCY: Final[str] = "query"
DATA_MINTS_CT32: Final[bool] = False
DATA_MINTS_EXPERIMENT_SPEC: Final[bool] = False
_RANK_PERSIST_FIELDS: Final[tuple[str, ...]] = (
    "persist",
    "persist_candidates",
    "candidate_database",
    "database",
    "store",
    "databank",
)

_COMMAND_TREE: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "backtest": ("run",),
        "data": DATA_COMMANDS,
        "optimize": ("run", "space", "estimate"),
        "sweep": SWEEP_COMMANDS,
        # B-14 rungs are the Epic 22 procedure keys — no second robustness roster.
        "robustness": ROBUSTNESS_PROCEDURES,
        "ledger": ("merge", "bar"),
        "library": LIBRARY_COMMANDS,
        "analysis": ANALYSIS_COMMANDS,
        "config": ("compile", "show"),
    }
)

_BACKTEST_PREREQS: Final[tuple[str, ...]] = (
    "port",
    "book_fragment",
    "bms_fragment",
    "run_spec",
    "slices",
    "output_root",
)

_COMMAND_PREREQS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "backtest.run": _BACKTEST_PREREQS,
        "data.download": ("destination", "venue", "symbol", "start"),
        "data.verify": ("archive", "venue", "symbol", "start", "end"),
        "data.gap-check": ("archive", "venue", "symbol", "start", "end"),
        "data.list": (),
        "data.catalog": (),
        "data.generate": ("destination",),
        "optimize.run": ("declaration", *_BACKTEST_PREREQS),
        "optimize.space": ("declaration",),
        "optimize.estimate": ("budget",),
        "sweep.count": ("declaration",),
        "sweep.batch": (
            "admitted",
            "output_root",
            "ledger",
            "combo_slices",
            "projected_peak_memory",
        ),
        "sweep.rank": ("lines", "sweep_id", "objective", "world"),
        f"robustness.{PROCEDURE_WALK_FORWARD}": ("windows",),
        f"robustness.{PROCEDURE_MC_TRADE_SHUFFLE}": (
            "trades",
            "starting_capital",
            "period",
            "base_seed",
            "metrics",
        ),
        f"robustness.{PROCEDURE_MC_CANDLE_PERTURBATION}": ("candles", "base_seed"),
        f"robustness.{PROCEDURE_RULE_SIGNIFICANCE}": ("signals", "base_seed"),
        "ledger.merge": ("root", "world", "role"),
        "ledger.bar": ("root", "world"),
        "library.kinds": (),
        "library.search": ("kind",),
        "library.candidates": (),
        "analysis.project": ("source_ct32", "source_ct29", "predicate"),
        "analysis.rerun": ("source_ct32", "slices", "output_root", "ledger"),
        "analysis.compare": ("left", "right"),
        "config.compile": ("port", "book_fragment", "bms_fragment", "run_spec"),
        "config.show": (),
    }
)

_CompileFn = Callable[..., Result[ResolvedRunConfig]]
_OrchFn = Callable[..., Result[IsolatedRun]]


@dataclass(frozen=True, slots=True)
class BacktestSubmission:
    """Compiler artifact plus the orchestrator's isolated outcome.

    ``run_id`` is the resolved-config fingerprint the compiler already stamped.
    The door never mints a second identity.
    """

    config: ResolvedRunConfig
    isolated: IsolatedRun

    @property
    def run_id(self) -> Fingerprint:
        """Run-id root: the compiler's fingerprint, never a door-local recipe."""
        return self.config.fingerprint


def command_tree() -> dict[str, tuple[str, ...]]:
    """Platform command groups and their subcommands (B-1, AR-10)."""
    return dict(_COMMAND_TREE)


def cli_tree_identity() -> dict[str, object]:
    """Identity-bearing CLI-door fields. The click pin value is not restated."""
    return {
        "adaptation": ("parsing", "transport", "refusal-rendering", "autocomplete"),
        "autocomplete": AUTOCOMPLETE,
        "autocomplete_port": AUTOCOMPLETE_PORT,
        "computes_run_id": COMPUTES_RUN_ID,
        "groups": COMMAND_GROUPS,
        "holds_cache": HOLDS_CACHE,
        "orchestrator_entry": ORCHESTRATOR_ENTRY,
        "pin_key": CLI_PIN_KEY,
        "prog": CLI_PROG,
        "data_occupancy": {
            name: DATA_DOWNLOAD_OCCUPANCY if name in DATA_RUN_COMMANDS else DATA_QUERY_OCCUPANCY
            for name in DATA_COMMANDS
        },
        "data_mints_ct32": DATA_MINTS_CT32,
        "data_mints_experiment_spec": DATA_MINTS_EXPERIMENT_SPEC,
        "library_occupancy": LIBRARY_KINDS_OCCUPANCY,
        "library_mints_ct32": LIBRARY_MINTS_CT32,
        "library_mints_experiment_spec": LIBRARY_MINTS_EXPERIMENT_SPEC,
        "library_search_occupancy": LIBRARY_SEARCH_OCCUPANCY,
        "library_search_mints_ct32": LIBRARY_SEARCH_MINTS_CT32,
        "library_search_mints_experiment_spec": LIBRARY_SEARCH_MINTS_EXPERIMENT_SPEC,
        "library_candidates_occupancy": CANDIDATE_SET_OCCUPANCY,
        "library_candidates_mints_ct32": CANDIDATE_SET_MINTS_CT32,
        "library_candidates_mints_experiment_spec": CANDIDATE_SET_MINTS_EXPERIMENT_SPEC,
        "analysis_occupancy": {
            "project": ANALYSIS_PROJECT_OCCUPANCY,
            "rerun": ANALYSIS_RERUN_OCCUPANCY,
        },
        "analysis_mints_ct32": {
            "project": ANALYSIS_PROJECT_MINTS_CT32,
            "rerun": ANALYSIS_RERUN_MINTS_CT32,
        },
        "analysis_mints_experiment_spec": {
            "project": ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC,
            "rerun": ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC,
        },
    }


def complete_registry(
    port: object,
    incomplete: object = "",
    *,
    kind: object = None,
) -> tuple[RegistryCompletion, ...]:
    """Enumerate registry autocomplete through the one B-15 port.

    A missing or non-port ``port`` yields no candidates — never a door-side
    cache and never a live service query. The compiler's ``resolve`` on the
    same port is the other consumer; they cannot disagree (DEC-0165).
    """
    if not isinstance(port, RegistryReadPort):
        return ()
    return port.complete(incomplete, kind=kind)


def command_prerequisites(command: object) -> Result[tuple[str, ...]]:
    """Declared config/resource prerequisites for one tree command."""
    token = clean_token(command)
    if token is None:
        return invalid("command", "a CLI command name is a non-blank token")
    required = _COMMAND_PREREQS.get(token)
    if required is None:
        return invalid("command", "unknown CLI command", given=token, tree=COMMAND_GROUPS)
    return Ok(required)


def require_prerequisites(command: object, provided: object) -> Result[None]:
    """Return a typed refusal when declared command resources are absent (CT-04)."""
    required = command_prerequisites(command)
    if is_refusal(required):
        return required
    if not isinstance(provided, Mapping):
        return invalid(
            "provided",
            "command prerequisites are a key->value mapping",
            given=repr(type(provided).__name__),
        )
    body = cast("Mapping[str, object]", provided)
    missing = [name for name in required.value if not _present(body.get(name))]
    if missing:
        token = clean_token(command)
        return unavailable(
            "prerequisites",
            "command config or resource prerequisites are absent",
            command=token,
            missing=missing,
            required=list(required.value),
        )
    return Ok(None)


def invoke_library_kinds() -> Result[LibraryKindRoster]:
    """Enumerate the closed Library fp1 kind list (Story 34.1).

    Occupancy is a query: no CT-32, no ExperimentSpec successor, no new COMP.
    """
    checked = require_prerequisites("library.kinds", {})
    if is_refusal(checked):
        return checked
    return Ok(enumerate_library_kinds())


def invoke_library_search(
    *,
    kind: object = None,
    fp1: object = None,
    port: object = None,
    ledger_lines: object = None,
    world: object = None,
    role: object = None,
    experiment_refs: object = None,
    saved_views: object = None,
    lane: object = None,
    staging: object = None,
    qma_staging: object = None,
    refinement_proposals: object = None,
    store: object = None,
    sqlite: object = None,
    database: object = None,
    fourth_store: object = None,
    new_store: object = None,
    identity_store: object = None,
) -> Result[LibrarySearch]:
    """Thin wrapper over ``qmb.search_library`` (Story 34.2).

    Occupancy is a query: no CT-32, no ExperimentSpec successor, no door-side
    registry cache, no fourth store. Staging is not read.
    """
    checked = require_prerequisites("library.search", {"kind": kind})
    if is_refusal(checked):
        return checked
    return search_library(
        kind,
        fp1=fp1,
        port=port,
        ledger_lines=ledger_lines,
        world=world,
        role=role,
        experiment_refs=experiment_refs,
        saved_views=saved_views,
        lane=lane,
        staging=staging,
        qma_staging=qma_staging,
        refinement_proposals=refinement_proposals,
        store=store,
        sqlite=sqlite,
        database=database,
        fourth_store=fourth_store,
        new_store=new_store,
        identity_store=identity_store,
    )


def invoke_library_candidates(
    *,
    kind: object = None,
    fp1: object = None,
    zone: object = None,
    port: object = None,
    ledger_lines: object = None,
    world: object = None,
    role: object = None,
    experiment_refs: object = None,
    lane: object = None,
    sweep_id: object = None,
    objective: object = None,
    constraints: object = None,
    direction: object = None,
    home: object = None,
    run_dir: object = None,
    body: object = None,
    cite: object = None,
    staging: object = None,
    qma_staging: object = None,
    refinement_proposals: object = None,
    persist: object = None,
    persist_candidates: object = None,
    copied_rows: object = None,
    persist_copied_rows: object = None,
    candidate_database: object = None,
    database: object = None,
    store: object = None,
    sqlite: object = None,
    databank: object = None,
    mint_registry_kind: object = None,
    registry_kind: object = None,
) -> Result[CandidateSet | SavedCandidateView]:
    """Thin wrapper over ``qmb.query_candidates`` (Story 34.3).

    Occupancy is a query: no CT-32, no ExperimentSpec successor, no copied-row
    store, no qmf-registry kind. Staging is not read. ``sweep.rank`` is the
    rank fold when ranking fields are supplied. A saved-view ``home`` follows
    FR-W24; coordinated persistence is Epic 36.
    """
    checked = require_prerequisites("library.candidates", {})
    if is_refusal(checked):
        return checked
    found = query_candidates(
        kind=kind,
        fp1=fp1,
        zone=zone,
        port=port,
        ledger_lines=ledger_lines,
        world=world,
        role=role,
        experiment_refs=experiment_refs,
        lane=lane,
        sweep_id=sweep_id,
        objective=objective,
        constraints=constraints,
        direction=direction,
        staging=staging,
        qma_staging=qma_staging,
        refinement_proposals=refinement_proposals,
        persist=persist,
        persist_candidates=persist_candidates,
        copied_rows=copied_rows,
        persist_copied_rows=persist_copied_rows,
        candidate_database=candidate_database,
        database=database,
        store=store,
        sqlite=sqlite,
        databank=databank,
        mint_registry_kind=mint_registry_kind,
        registry_kind=registry_kind,
    )
    if is_refusal(found):
        return found
    if home is None:
        queried: CandidateSet | SavedCandidateView = found.value
        return Ok(queried)
    saved = save_candidate_view(
        found.value,
        home=home,
        body=body,
        run_dir=run_dir,
        cite=cite,
    )
    if is_refusal(saved):
        return saved
    persisted: CandidateSet | SavedCandidateView = saved.value
    return Ok(persisted)


def invoke_analysis_project(
    *,
    source_ct32: object = None,
    source_ct29: object = None,
    predicate: object = None,
    as_of: object = None,
    config: object = None,
    body: object = None,
    cite: object = None,
    hours: object = None,
    days: object = None,
    session: object = None,
    max_trades: object = None,
    include: object = None,
    exclude: object = None,
    trades: object = None,
    trade_list: object = None,
    copied_trades: object = None,
    occupancy: object = None,
    ledger: object = None,
    mint_ct32: object = None,
    experiment_spec: object = None,
    successor: object = None,
    sqlite: object = None,
    role: object = None,
    admission: object = None,
    claim_class: object = None,
    home: object = None,
    run_dir: object = None,
    size: object = None,
    r: object = None,
    book: object = None,
    bms: object = None,
    ports: object = None,
    execution_ports: object = None,
    starting_capital: object = None,
    spawn: object = None,
    orchestrator: object = None,
    spawn_run: object = None,
    portfolio: object = None,
    synthetic_portfolio: object = None,
    combine: object = None,
    combination: object = None,
    gating_live: object = None,
    confirmed: object = None,
) -> Result[ProjectionView]:
    """Thin wrapper over ``qmb.project`` (Story 35.1 / 35.2).

    Occupancy is a query: no CT-32, no ExperimentSpec successor, no ledger line.
    QMA must call this door (or the library) and must not reimplement the filter.
    Forbidden axes are path-dependent; ungoverned is a return value; governed
    writes the sidecar in the source run-dir.
    """
    folded_predicate = predicate
    if folded_predicate is None and any(
        item is not None for item in (hours, days, session, max_trades, include, exclude)
    ):
        folded_predicate = True
    if cite is None and body is None:
        checked = require_prerequisites(
            "analysis.project",
            {
                "source_ct32": source_ct32,
                "source_ct29": source_ct29,
                "predicate": folded_predicate,
            },
        )
        if is_refusal(checked):
            return checked
    return project(
        source_ct32=source_ct32,
        source_ct29=source_ct29,
        predicate=predicate,
        as_of=as_of,
        config=config,
        body=body,
        cite=cite,
        hours=hours,
        days=days,
        session=session,
        max_trades=max_trades,
        include=include,
        exclude=exclude,
        trades=trades,
        trade_list=trade_list,
        copied_trades=copied_trades,
        occupancy=occupancy,
        ledger=ledger,
        mint_ct32=mint_ct32,
        experiment_spec=experiment_spec,
        successor=successor,
        sqlite=sqlite,
        role=role,
        admission=admission,
        claim_class=claim_class,
        home=home,
        run_dir=run_dir,
        spawn=spawn,
        orchestrator=orchestrator,
        spawn_run=spawn_run,
        size=size,
        r=r,
        book=book,
        bms=bms,
        ports=ports,
        execution_ports=execution_ports,
        starting_capital=starting_capital,
        portfolio=portfolio,
        synthetic_portfolio=synthetic_portfolio,
        combine=combine,
        combination=combination,
        gating_live=gating_live,
        confirmed=confirmed,
    )


def invoke_analysis_rerun(
    *,
    source_ct32: object = None,
    config: object = None,
    port: object = None,
    book_fragment: object = None,
    bms_fragment: object = None,
    run_spec: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    starting_capital: object = None,
    fill_port: object = None,
    cost_port: object = None,
    financing_port: object = None,
    slices: object = None,
    output_root: object = None,
    ledger: object = None,
    occupancy: object = None,
    cpu_budget: object = None,
    memory_budget: object = None,
    projected_peak_memory: object = None,
    analysis_method: object = None,
    lane: object = None,
    workbench_lane: object = None,
    experiment_spec: object = None,
    sqlite: object = None,
    role: object = None,
    portfolio: object = None,
    synthetic_portfolio: object = None,
    combine: object = None,
    combination: object = None,
) -> Result[RerunOutcome]:
    """Thin wrapper over ``qmb.rerun`` (Story 35.3).

    Occupancy is a run: one governed spawn, one new CT-32, one ledger line with
    workbench_lane=governed citing that CT-32 by _ref. QMA must call this door
    (or the library) and must not reimplement the tunnel.
    """
    provided: dict[str, object] = {
        "source_ct32": source_ct32,
        "slices": slices,
        "output_root": output_root,
        "ledger": ledger,
    }
    if config is not None:
        provided["config"] = config
    else:
        provided["port"] = port
        provided["book_fragment"] = book_fragment
        provided["bms_fragment"] = bms_fragment
        provided["run_spec"] = run_spec
    checked = require_prerequisites("analysis.rerun", provided)
    if is_refusal(checked):
        return checked
    if config is None:
        layers = require_prerequisites(
            "config.compile",
            {
                "port": port,
                "book_fragment": book_fragment,
                "bms_fragment": bms_fragment,
                "run_spec": run_spec,
            },
        )
        if is_refusal(layers):
            return layers
    return rerun(
        source_ct32=source_ct32,
        config=config,
        port=port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec=run_spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
        starting_capital=starting_capital,
        fill_port=fill_port,
        cost_port=cost_port,
        financing_port=financing_port,
        slices=slices,
        output_root=output_root,
        ledger=ledger,
        occupancy=occupancy,
        cpu_budget=cpu_budget,
        memory_budget=memory_budget,
        projected_peak_memory=projected_peak_memory,
        analysis_method=analysis_method,
        lane=lane,
        workbench_lane=workbench_lane,
        experiment_spec=experiment_spec,
        sqlite=sqlite,
        role=role,
        portfolio=portfolio,
        synthetic_portfolio=synthetic_portfolio,
        combine=combine,
        combination=combination,
    )


def invoke_compare_runs(
    *,
    left: object = None,
    right: object = None,
    occupancy: object = None,
    ledger: object = None,
    mint_ct32: object = None,
    experiment_spec: object = None,
    successor: object = None,
    role: object = None,
    confirmation_label: object = None,
    analysis_method: object = None,
    lane: object = None,
    workbench_lane: object = None,
    gating_live: object = None,
    portfolio: object = None,
    synthetic_portfolio: object = None,
    combine: object = None,
    combination: object = None,
) -> Result[CompareReadout]:
    """Thin wrapper over ``qmb.compare_runs`` (Story 35.5).

    Occupancy is a query: no CT-32, no ledger line, no confirmation label.
    compare_runs is a readout, not a named analysis method.
    """
    checked = require_prerequisites(
        "analysis.compare",
        {
            "left": left,
            "right": right,
        },
    )
    if is_refusal(checked):
        return checked
    return compare_runs(
        left,
        right,
        occupancy=occupancy,
        ledger=ledger,
        mint_ct32=mint_ct32,
        experiment_spec=experiment_spec,
        successor=successor,
        role=role,
        confirmation_label=confirmation_label,
        analysis_method=analysis_method,
        lane=lane,
        workbench_lane=workbench_lane,
        gating_live=gating_live,
        portfolio=portfolio,
        synthetic_portfolio=synthetic_portfolio,
        combine=combine,
        combination=combination,
    )


def analysis_command_occupancy(command: object) -> Result[str]:
    """Classify an analysis command as occupancy ``run`` or query (FR-W11)."""
    token = clean_token(command)
    if token is None:
        return invalid("command", "an analysis command name is a non-blank token")
    name = token[9:] if token.startswith("analysis.") else token
    if name == "compare_runs":
        name = "compare"
    if name == "project":
        return Ok(ANALYSIS_PROJECT_OCCUPANCY)
    if name == "rerun":
        return Ok(ANALYSIS_RERUN_OCCUPANCY)
    if name == "compare":
        return Ok(COMPARE_RUNS_OCCUPANCY)
    return invalid(
        "command",
        "analysis occupancy classifies project (query), rerun (run), and compare (query readout)",
        given=token,
        legal=list(ANALYSIS_COMMANDS),
    )


def invoke_config_show() -> Result[Mapping[str, object]]:
    """Show the resolved-run-config identity schema (no I/O)."""
    checked = require_prerequisites("config.show", {})
    if is_refusal(checked):
        return checked
    return Ok(run_config_identity())


def invoke_config_compile(
    *,
    port: object = None,
    book_fragment: object = None,
    bms_fragment: object = None,
    run_spec: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    compiler: object = None,
) -> Result[ResolvedRunConfig]:
    """Compile one resolved run-config through the Epic 13 compiler (B-3)."""
    checked = require_prerequisites(
        "config.compile",
        {
            "port": port,
            "book_fragment": book_fragment,
            "bms_fragment": bms_fragment,
            "run_spec": run_spec,
        },
    )
    if is_refusal(checked):
        return checked
    compile_fn = _as_compiler(compiler)
    if is_refusal(compile_fn):
        return compile_fn
    return compile_fn.value(
        port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec=run_spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
    )


def invoke_backtest(
    *,
    port: object = None,
    book_fragment: object = None,
    bms_fragment: object = None,
    run_spec: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    slices: object = None,
    output_root: object = None,
    compiler: object = None,
    orchestrator: object = None,
    cancel: object = None,
    limits: object = None,
    probe: object = None,
    analysis_method: object = None,
    lane: object = None,
    workbench_lane: object = None,
    experiment_spec: object = None,
) -> Result[BacktestSubmission]:
    """Compile via ``compile_run_config`` and submit to ``spawn_run`` (B-1, B-3).

    The run-id root is the compiled artifact's fingerprint. This door does not
    call ``fp1`` and does not name a run directory of its own. Lane is
    door-derived ``governed``; caller-declared flags are refused (DEC-0270).
    """
    blocked = refuse_caller_declared_lane_fields(
        analysis_method=analysis_method,
        lane=lane,
        workbench_lane=workbench_lane,
    )
    if blocked is not None:
        return blocked
    if experiment_spec is not None:
        return policy(
            "experiment_spec",
            "a QMB orchestrator spawn not placed by CT-47 mints no ExperimentSpec "
            "unless a later act places the same work through CT-47 (FR-W05; DEC-0270)",
            mints_experiment_spec=False,
            workbench_lane="governed",
        )
    checked = require_prerequisites(
        "backtest.run",
        {
            "port": port,
            "book_fragment": book_fragment,
            "bms_fragment": bms_fragment,
            "run_spec": run_spec,
            "slices": slices,
            "output_root": output_root,
        },
    )
    if is_refusal(checked):
        return checked
    compiled = invoke_config_compile(
        port=port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec=run_spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
        compiler=compiler,
    )
    if is_refusal(compiled):
        return compiled
    orch = _as_orchestrator(orchestrator)
    if is_refusal(orch):
        return orch
    submitted = orch.value(
        config=compiled.value,
        slices=slices,
        output_root=output_root,
        cancel=cancel,
        limits=limits,
        probe=probe,
    )
    if is_refusal(submitted):
        return submitted
    return Ok(BacktestSubmission(config=compiled.value, isolated=submitted.value))


def invoke_optimize_space(*, declaration: object = None) -> Result[object]:
    """Read the CT-33-authoritative parameter-space schema (B-8)."""
    checked = require_prerequisites("optimize.space", {"declaration": declaration})
    if is_refusal(checked):
        return checked
    parsed = parameter_space_from_bot(declaration)
    if is_refusal(parsed):
        return parsed
    space: object = parsed.value
    return Ok(space)


def invoke_optimize_estimate(
    *,
    budget: object = None,
    param_count: object = None,
    declaration: object = None,
    per_trial_runtime: object = None,
    concurrency_cap: object = None,
    cpu_budget: object = None,
    memory_budget: object = None,
    projected_peak_memory: object = None,
) -> Result[CostEstimate]:
    """Estimate a Study's cost through the CLI door, spawning nothing (AC3, OPT-24).

    A thin wrapper over the one pure library function
    ``qmb.optimize.estimate_study_cost``: the projection lives once in the library
    and is never duplicated here. The parameter count may be given directly or
    derived from a CT-33 ``declaration``; the governor concurrency cap may be given
    directly or resolved from the ``cpu_budget``/``memory_budget`` (and optional
    ``projected_peak_memory``) governor budgets. No trial is spawned.
    """
    checked = require_prerequisites("optimize.estimate", {"budget": budget})
    if is_refusal(checked):
        return checked
    resolved_count = _resolve_param_count(param_count, declaration)
    if is_refusal(resolved_count):
        return resolved_count
    cap = _resolve_concurrency_cap(
        concurrency_cap, cpu_budget, memory_budget, projected_peak_memory
    )
    if is_refusal(cap):
        return cap
    return estimate_study_cost(
        budget,
        param_count=resolved_count.value,
        per_trial_runtime=per_trial_runtime,
        concurrency_cap=cap.value,
    )


def invoke_optimize_run(
    *,
    declaration: object = None,
    port: object = None,
    book_fragment: object = None,
    bms_fragment: object = None,
    run_spec: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    slices: object = None,
    output_root: object = None,
    compiler: object = None,
    orchestrator: object = None,
    cancel: object = None,
    limits: object = None,
    probe: object = None,
) -> Result[BacktestSubmission]:
    """One optimize trial is a first-class backtest run (B-8, B-3)."""
    checked = require_prerequisites(
        "optimize.run",
        {
            "declaration": declaration,
            "port": port,
            "book_fragment": book_fragment,
            "bms_fragment": bms_fragment,
            "run_spec": run_spec,
            "slices": slices,
            "output_root": output_root,
        },
    )
    if is_refusal(checked):
        return checked
    return invoke_backtest(
        port=port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec=run_spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
        slices=slices,
        output_root=output_root,
        compiler=compiler,
        orchestrator=orchestrator,
        cancel=cancel,
        limits=limits,
        probe=probe,
    )


def invoke_sweep_count(*, declaration: object = None) -> Result[int]:
    """Pre-flight run count for a declared sweep — a pure inspection (B-12, B-4).

    A thin wrapper over the one pure library function: the axes-to-count
    computation lives in ``qmb.sweep.preflight_run_count`` and is never duplicated
    here. ``declaration`` is a ``SweepDeclaration`` or the raw axis mapping.
    """
    checked = require_prerequisites("sweep.count", {"declaration": declaration})
    if is_refusal(checked):
        return checked
    return preflight_run_count(declaration)


def invoke_sweep_batch(
    *,
    admitted: object = None,
    output_root: object = None,
    ledger: object = None,
    combo_slices: object = None,
    projected_peak_memory: object = None,
    cpu_budget: object = None,
    memory_budget: object = None,
    budgets: object = None,
    on_full: object = None,
    cpu_cost: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    role: object = None,
    factory_sandbox: object = None,
) -> Result[SweepBatchReport]:
    """Thin wrapper over ``qmb.sweep.run_sweep_batch`` (Story 20.3, Story 33.2).

    The Cartesian expansion and per-combo isolation live once in Epic 20. This
    door parses and transports; it invents no second expander.

    Occupancy: a governed CLI invocation of this command is one qmb run unit
    wrapping the combo children. Process-per-run children inside that
    invocation are not additional QMA jobs. Each combo still writes exactly
    one ledger line. CT-47 ExperimentSpec placement is Epic 36 — this door
    does not mint it.
    """
    checked = require_prerequisites(
        "sweep.batch",
        {
            "admitted": admitted,
            "output_root": output_root,
            "ledger": ledger,
            "combo_slices": combo_slices,
            "projected_peak_memory": projected_peak_memory,
        },
    )
    if is_refusal(checked):
        return checked
    return run_sweep_batch(
        admitted,
        output_root=output_root,
        ledger=ledger,
        combo_slices=combo_slices,
        projected_peak_memory=projected_peak_memory,
        cpu_budget=cpu_budget,
        memory_budget=memory_budget,
        budgets=budgets,
        on_full=ON_FULL_ENQUEUE if on_full is None else on_full,
        cpu_cost=1 if cpu_cost is None else cpu_cost,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
        role=ROLE_CONFIRMATION if role is None else role,
        factory_sandbox=factory_sandbox,
    )


def invoke_sweep_rank(
    *,
    lines: object = None,
    sweep_id: object = None,
    objective: object = None,
    world: object = None,
    role: object = None,
    constraints: object = None,
    direction: object = None,
    persist: object = None,
    persist_candidates: object = None,
    candidate_database: object = None,
    database: object = None,
    store: object = None,
    databank: object = None,
) -> Result[SweepRanking]:
    """Thin wrapper over ``qmb.sweep.rank_sweep`` (Story 20.4, Story 33.2).

    Ranking is a read-time fold over the sweep's ledger lines. This door
    publishes the fold and never a copied-row artifact; it mints no CT-32 and
    no CT-47 successor.

    Occupancy: query — a governed CLI invocation consumes no ExecutionEnvironment
    occupancy.

    A request to persist a candidate database is a typed policy refusal: the
    operator is left with the fold, not a second store (FR-W20, DEC-0269).
    """
    requested = _requested_rank_persist(
        {
            "persist": persist,
            "persist_candidates": persist_candidates,
            "candidate_database": candidate_database,
            "database": database,
            "store": store,
            "databank": databank,
        }
    )
    if requested is not None:
        return policy(
            requested,
            "sweep.rank is a read-time fold over the sweep's ledger lines: it "
            "publishes no copied-row artifact and does not persist a candidate "
            "database — the operator is left with the fold, not a second store "
            "(FR-W20, DEC-0269)",
            occupancy=SWEEP_RANK_OCCUPANCY,
            mints_ct32=False,
            mints_experiment_spec=False,
        )
    checked = require_prerequisites(
        "sweep.rank",
        {
            "lines": lines,
            "sweep_id": sweep_id,
            "objective": objective,
            "world": world,
        },
    )
    if is_refusal(checked):
        return checked
    return rank_sweep(
        lines,
        sweep_id=sweep_id,
        objective=objective,
        world=world,
        role=ROLE_CONFIRMATION if role is None else role,
        constraints=() if constraints is None else constraints,
        direction=RANK_DESCENDING if direction is None else direction,
    )


def _requested_rank_persist(fields: Mapping[str, object]) -> str | None:
    """Return the persist-store field a caller asked rank to write, else None."""
    for name in _RANK_PERSIST_FIELDS:
        value = fields.get(name)
        if value is None or value is False:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return name
    return None


def invoke_robustness_walk_forward(
    *,
    windows: object = None,
    config: object = None,
    window_count: object = None,
    in_sample_span: object = None,
    out_of_sample_span: object = None,
    step: object = None,
) -> Result[WalkForwardPlan]:
    """Thin wrapper over ``qmb.robustness.plan_walk_forward`` (B-14).

    The walk-forward sequence lives once in the Epic 22 library. This door
    parses and transports; it invents no OOS pass battery (GAP-0048/GAP-0049).

    Occupancy: a governed CLI invocation of this command is one qmb run unit.
    Process-per-run children inside that invocation are not additional QMA
    jobs. CT-47 ExperimentSpec placement is Epic 36 — this door does not mint
    it.
    """
    checked = require_prerequisites(
        f"robustness.{PROCEDURE_WALK_FORWARD}",
        {"windows": windows},
    )
    if is_refusal(checked):
        return checked
    return plan_walk_forward(
        windows,
        config=config,
        window_count=window_count,
        in_sample_span=in_sample_span,
        out_of_sample_span=out_of_sample_span,
        step=step,
    )


def invoke_robustness_trade_shuffle(
    *,
    trades: object = None,
    starting_capital: object = None,
    period: object = None,
    base_seed: object = None,
    metrics: object = None,
    config: object = None,
    scenario_count: object = None,
    band_probabilities: object = (),
) -> Result[TradeShuffleResult]:
    """Thin wrapper over ``qmb.robustness.run_trade_shuffle`` (B-14).

    The Monte Carlo trade-shuffle lives once in the Epic 22 library. This door
    parses and transports; it invents no pass/fail battery (GAP-0048/GAP-0049).

    Occupancy: a governed CLI invocation of this command is one qmb run unit.
    Process-per-run children inside that invocation are not additional QMA
    jobs. CT-47 ExperimentSpec placement is Epic 36 — this door does not mint
    it.
    """
    checked = require_prerequisites(
        f"robustness.{PROCEDURE_MC_TRADE_SHUFFLE}",
        {
            "trades": trades,
            "starting_capital": starting_capital,
            "period": period,
            "base_seed": base_seed,
            "metrics": metrics,
        },
    )
    if is_refusal(checked):
        return checked
    return run_trade_shuffle(
        trades=trades,
        starting_capital=starting_capital,
        period=period,
        base_seed=base_seed,
        metrics=metrics,
        config=config,
        scenario_count=scenario_count,
        band_probabilities=band_probabilities,
    )


def invoke_robustness_candle_perturbation(
    *,
    candles: object = None,
    base_seed: object = None,
    block_length: object = None,
    scenario_count: object = None,
    config: object = None,
    seed_price: object = None,
    run_root: object = None,
    objective_identity: object = None,
    scenario_objectives: object = None,
    objective_direction: object = None,
    band_probabilities: object = (),
) -> Result[CandlePerturbationResult]:
    """Thin wrapper over ``qmb.robustness.run_candle_perturbation`` (B-14).

    The Monte Carlo candle-perturbation lives once in the Epic 22 library.
    This door parses and transports; it invents no pass/fail battery
    (GAP-0048/GAP-0049).

    Occupancy: a governed CLI invocation of this command is one qmb run unit.
    Process-per-run children inside that invocation are not additional QMA
    jobs. CT-47 ExperimentSpec placement is Epic 36 — this door does not mint
    it.
    """
    checked = require_prerequisites(
        f"robustness.{PROCEDURE_MC_CANDLE_PERTURBATION}",
        {"candles": candles, "base_seed": base_seed},
    )
    if is_refusal(checked):
        return checked
    return run_candle_perturbation(
        candles=candles,
        base_seed=base_seed,
        block_length=block_length,
        scenario_count=scenario_count,
        config=config,
        seed_price=seed_price,
        run_root=run_root,
        objective_identity=objective_identity,
        scenario_objectives=scenario_objectives,
        objective_direction=objective_direction,
        band_probabilities=band_probabilities,
    )


def invoke_robustness_rule_significance(
    *,
    signals: object = None,
    base_seed: object = None,
    resampling_scheme: object = None,
    block_length: object = None,
    iterations: object = None,
    minimum_observations: object = None,
    config: object = None,
    band_probabilities: object = (),
    stream_id: object = None,
) -> Result[SignificanceResult]:
    """Thin wrapper over ``qmb.robustness.run_significance_gate`` (B-14).

    The pre-build rule-significance gate lives once in the Epic 22 library.
    This door parses and transports; it invents no alpha battery
    (GAP-0048/GAP-0049).

    Occupancy: a governed CLI invocation of this command is one qmb run unit.
    Process-per-run children inside that invocation are not additional QMA
    jobs. CT-47 ExperimentSpec placement is Epic 36 — this door does not mint
    it.
    """
    checked = require_prerequisites(
        f"robustness.{PROCEDURE_RULE_SIGNIFICANCE}",
        {"signals": signals, "base_seed": base_seed},
    )
    if is_refusal(checked):
        return checked
    if isinstance(stream_id, str):
        return run_significance_gate(
            signals=signals,
            base_seed=base_seed,
            resampling_scheme=resampling_scheme,
            block_length=block_length,
            iterations=iterations,
            minimum_observations=minimum_observations,
            config=config,
            band_probabilities=band_probabilities,
            stream_id=stream_id,
        )
    return run_significance_gate(
        signals=signals,
        base_seed=base_seed,
        resampling_scheme=resampling_scheme,
        block_length=block_length,
        iterations=iterations,
        minimum_observations=minimum_observations,
        config=config,
        band_probabilities=band_probabilities,
    )


def data_command_occupancy(command: object) -> Result[str]:
    """Classify a data command as occupancy ``run`` or query (FR-W11).

    ``data.download`` that mutates rooms is one qmb run invocation. ``generate``
    likewise mutates rooms. ``data.gap-check|verify|catalog|list`` are queries:
    they consume no occupancy, mint no CT-32, and mint no ExperimentSpec
    successor.
    """
    token = clean_token(command)
    if token is None:
        return invalid("command", "a data command name is a non-blank token")
    name = token[5:] if token.startswith("data.") else token
    if name in DATA_RUN_COMMANDS:
        return Ok(DATA_DOWNLOAD_OCCUPANCY if name == "download" else DATA_GENERATE_OCCUPANCY)
    if name in DATA_QUERY_COMMANDS:
        return Ok(DATA_QUERY_OCCUPANCY)
    return invalid(
        "command",
        "data occupancy classifies download, generate, gap-check, verify, catalog, list",
        given=token,
        legal=list(DATA_COMMANDS),
    )


def invoke_data(command: object, provided: object = None) -> Result[Mapping[str, object]]:
    """Thin data-command front over the ratified qmf-data contracts (B-11).

    Occupancy: download/generate that mutate rooms are run invocations;
    gap-check/verify/catalog/list are queries (FR-W11). Vendor-style timezone
    clones, clone stores, CDN products, and Library-kind derived datasets are
    refused (FR-W30, FR-W31).
    """
    token = clean_token(command)
    if token is None or token not in DATA_COMMANDS:
        return invalid(
            "command",
            "data commands are download, verify, gap-check, list, catalog, generate",
            given=repr(command),
            legal=list(DATA_COMMANDS),
        )
    resources: Mapping[str, object]
    if provided is None:
        resources = {}
    elif isinstance(provided, Mapping):
        resources = cast("Mapping[str, object]", provided)
    else:
        return invalid(
            "provided",
            "command prerequisites are a key->value mapping",
            given=repr(type(provided).__name__),
        )
    guarded = guard_data_door(token, resources)
    if is_refusal(guarded):
        return guarded
    checked = require_prerequisites(f"data.{token}", resources)
    if is_refusal(checked):
        return checked
    if token == "download":  # noqa: S105 — command name, not a secret
        receipt = run_download(resources)
        if is_refusal(receipt):
            return receipt
        payload: dict[str, object] = dict(receipt.value.as_mapping())
        payload.update(data_front_identity())
        return Ok(_stamp_data_occupancy(payload, token))
    if token == "verify":  # noqa: S105 — command name, not a secret
        integrity = verify(resources)
        if is_refusal(integrity):
            return integrity
        verified: dict[str, object] = dict(integrity.value.as_mapping())
        verified.update(data_front_identity())
        return Ok(_stamp_data_occupancy(verified, token))
    if token == "gap-check":  # noqa: S105 — command name, not a secret
        checked_gaps = gap_check(resources)
        if is_refusal(checked_gaps):
            return checked_gaps
        gapped: dict[str, object] = dict(checked_gaps.value.as_mapping())
        gapped.update(data_front_identity())
        return Ok(_stamp_data_occupancy(gapped, token))
    if token == "list":  # noqa: S105 — command name, not a secret
        coverage = list_data(resources, command=token)
        if is_refusal(coverage):
            return coverage
        listed: dict[str, object] = dict(coverage.value.as_mapping())
        listed.update(data_front_identity())
        return Ok(_stamp_data_occupancy(listed, token))
    if token == "catalog":  # noqa: S105 — command name, not a secret
        coverage = catalog(resources)
        if is_refusal(coverage):
            return coverage
        aliased: dict[str, object] = dict(coverage.value.as_mapping())
        aliased.update(data_front_identity())
        return Ok(_stamp_data_occupancy(aliased, token))
    # generate — a resolved config runs the config-selected adapters; a bare
    # destination reports the generator front's capability surface (B-11).
    if has_generator_config(resources):
        generated = run_generate(resources)
        if is_refusal(generated):
            return generated
        produced: dict[str, object] = dict(generated.value.as_mapping())
        produced.update(data_front_identity())
        return Ok(_stamp_data_occupancy(produced, token))
    front: dict[str, object] = {"command": token}
    front.update(data_front_identity())
    return Ok(_stamp_data_occupancy(front, token))


def _stamp_data_occupancy(payload: dict[str, object], command: str) -> dict[str, object]:
    """Stamp occupancy classification onto a data-door payload (FR-W11)."""
    classified = data_command_occupancy(command)
    if is_refusal(classified):
        return payload
    payload["occupancy"] = classified.value
    payload["mints_ct32"] = DATA_MINTS_CT32
    payload["mints_experiment_spec"] = DATA_MINTS_EXPERIMENT_SPEC
    return payload


def invoke_ledger_merge(
    *,
    root: object = None,
    world: object = None,
    role: object = None,
) -> Result[tuple[LedgerLine, ...]]:
    """World-and-role-scoped ledger merge view (B-4)."""
    checked = require_prerequisites("ledger.merge", {"root": root, "world": world, "role": role})
    if is_refusal(checked):
        return checked
    return read_merge_view(root, world=world, role=role)


def invoke_ledger_bar(
    *,
    root: object = None,
    world: object = None,
) -> Result[tuple[LedgerLine, ...]]:
    """Book-bar read: confirmation lines only (B-4)."""
    checked = require_prerequisites("ledger.bar", {"root": root, "world": world})
    if is_refusal(checked):
        return checked
    return read_book_bar(root, world=world)


def _present(value: object) -> bool:
    if value is None:
        return False
    return not (isinstance(value, str) and value.strip() == "")


def _resolve_param_count(param_count: object, declaration: object) -> Result[object]:
    """Resolve the parameter count for a scale-with-#params estimate (AC3).

    An explicit ``param_count`` wins; otherwise it is derived from the CT-33
    ``declaration``'s parameter space (read once through the library). ``None`` is
    left for the pure estimator to require only when the budget scales with params.
    """
    if param_count is not None:
        return Ok(param_count)
    if declaration is None:
        result: object = None
        return Ok(result)
    space = parameter_space_from_bot(declaration)
    if is_refusal(space):
        return space
    derived: object = len(space.value)
    return Ok(derived)


def _resolve_concurrency_cap(
    concurrency_cap: object,
    cpu_budget: object,
    memory_budget: object,
    projected_peak_memory: object,
) -> Result[object]:
    """Resolve the governor concurrency cap the estimate divides by (AC3, B-5).

    An explicit ``concurrency_cap`` wins; otherwise it is the governor's
    ``min(cpu, memory)`` parallelism bound over the declared budgets. A bound of
    zero — no run fits the declared budget — is a typed refusal, never a silent
    divide.
    """
    if concurrency_cap is not None:
        return Ok(concurrency_cap)
    if cpu_budget is None and memory_budget is None:
        return invalid(
            "concurrency_cap",
            "an estimate divides by the governor concurrency cap; pass concurrency_cap "
            "directly, or the governor cpu/memory budgets to resolve min(cpu, memory)",
        )
    budgets = GovernorBudgets.try_create(cpu_budget, memory_budget)
    if is_refusal(budgets):
        return budgets
    peak = projected_peak_memory if projected_peak_memory is not None else 1
    bound = budgets.value.parallelism_bound(peak)
    if is_refusal(bound):
        return bound
    if bound.value < 1:
        return unavailable(
            "concurrency_cap",
            "the governor min(cpu, memory) parallelism bound is zero — no run fits the "
            "declared budget, so no wall can be projected (B-5, FM-6)",
            cpu_budget=cpu_budget,
            memory_budget=memory_budget,
        )
    cap: object = bound.value
    return Ok(cap)


def _as_compiler(compiler: object) -> Result[_CompileFn]:
    if compiler is None:
        return Ok(compile_run_config)
    if not callable(compiler):
        return invalid(
            "compiler",
            "a backtest compiles through qmb.config.compile_run_config",
            given=repr(type(compiler).__name__),
        )
    return Ok(cast("_CompileFn", compiler))


def _as_orchestrator(orchestrator: object) -> Result[_OrchFn]:
    if orchestrator is None:
        return Ok(spawn_run)
    if not callable(orchestrator):
        return invalid(
            "orchestrator",
            "a backtest submits to qmb.orchestrator.spawn_run",
            given=repr(type(orchestrator).__name__),
        )
    return Ok(cast("_OrchFn", orchestrator))
