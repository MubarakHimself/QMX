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
from qmb.registryread import RegistryCompletion, RegistryReadPort
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
    "config",
)
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
) -> Result[BacktestSubmission]:
    """Compile via ``compile_run_config`` and submit to ``spawn_run`` (B-1, B-3).

    The run-id root is the compiled artifact's fingerprint. This door does not
    call ``fp1`` and does not name a run directory of its own.
    """
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
