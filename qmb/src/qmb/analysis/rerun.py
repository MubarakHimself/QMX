"""Path-dependent analysis.rerun: a new QMB run whose artifact is a new CT-32.

``analysis.rerun`` is a COMP-QMB library function. Given a completed run and a
new resolved run-config (Book/BMS fragments, fill/cost/financing ports, and/or
``starting_capital``), it compiles through the B-3 tunnel and spawns one
governed orchestrator run. Canonical artifact is the new CT-32. Occupancy is
one ``qmb`` **run** invocation per ExecutionEnvironment — not a query.

A ``starting_capital`` override is an invocation flag: the binding is stamped
``seed_overridden`` and the B-4 fold is forced ``unrated`` (Story 13.5 / FM-12).
``analysis_method`` and ``lane`` are not CT-32 or B-4 fields. Metadata lives on
the QMB ledger line (``workbench_lane=governed``) citing the CT-32 by ``_ref``.
Coordinated Experiment Ledger persistence is Epic 36 (DEC-0273, FR-W25).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.risk.performance import PerformanceResult

from qmb._refuse import clean_token, invalid, policy, storage
from qmb.config.compiler import ResolvedRunConfig, compile_run_config
from qmb.config.replay import STARTING_CAPITAL_KEY
from qmb.execution.binder import COST_ADAPTER_KEY, FILL_ADAPTER_KEY, FINANCING_SCHEDULE_KEY
from qmb.ledger.line import (
    WORKBENCH_LANE_COORDINATED,
    WORKBENCH_LANE_GOVERNED,
    LedgerLine,
    ct32_ref,
    mint_completed_line,
)
from qmb.orchestrator.ledger import LedgerSink
from qmb.orchestrator.spawn import IsolatedRun, SpawnJob, spawn_governed
from qmb.results.ct32 import as_ct32_artifact

__all__ = [
    "ANALYSIS_RERUN_CLASS",
    "ANALYSIS_RERUN_MINTS_CT32",
    "ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC",
    "ANALYSIS_RERUN_OCCUPANCY",
    "METHOD_RERUN",
    "WORKBENCH_LANE_GOVERNED",
    "RerunOutcome",
    "analysis_rerun_identity",
    "rerun",
]

ANALYSIS_RERUN_CLASS: Final[str] = "qmb-analysis-rerun"
ANALYSIS_RERUN_OCCUPANCY: Final[str] = "run"
ANALYSIS_RERUN_MINTS_CT32: Final[bool] = True
ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC: Final[bool] = False
METHOD_RERUN: Final[str] = "rerun"
_OCCUPANCY_CPU: Final[int] = 1
_OCCUPANCY_MEMORY: Final[int] = 1
_OCCUPANCY_PEAK: Final[int] = 1
_LABEL_FIELDS: Final[tuple[str, ...]] = ("analysis_method", "lane", "workbench_lane")
_SPEC_FIELDS: Final[tuple[str, ...]] = (
    "experiment_spec",
    "mint_experiment_spec",
    "successor",
)
_SQLITE_FIELDS: Final[tuple[str, ...]] = ("daemon_sqlite", "database", "sqlite")
_QUERY_TOKENS: Final[frozenset[str]] = frozenset({"none", "query"})
_RUN_TOKENS: Final[frozenset[str]] = frozenset({"job", "run"})
_PORT_KEYS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "cost_port": COST_ADAPTER_KEY,
        "fill_port": FILL_ADAPTER_KEY,
        "financing_port": FINANCING_SCHEDULE_KEY,
    }
)


@dataclass(frozen=True, slots=True)
class RerunOutcome:
    """One governed path-dependent rerun. Canonical artifact is the new CT-32."""

    source_ct32: str
    config: ResolvedRunConfig
    isolated: IsolatedRun
    ledger_line: LedgerLine
    ct32_fingerprint: Fingerprint
    occupancy: str = ANALYSIS_RERUN_OCCUPANCY
    mints_ct32: bool = True
    mints_experiment_spec: bool = False
    workbench_lane: str = WORKBENCH_LANE_GOVERNED

    @property
    def method(self) -> str:
        """Always ``rerun`` — this is a new run, not a projection saved view."""
        return METHOD_RERUN

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing rerun outcome. Package SemVer is omitted."""
        return {
            "class": ANALYSIS_RERUN_CLASS,
            "command": "analysis.rerun",
            "ct32": ct32_ref(self.ct32_fingerprint),
            "method": METHOD_RERUN,
            "mints_ct32": True,
            "mints_experiment_spec": False,
            "occupancy": ANALYSIS_RERUN_OCCUPANCY,
            "run_id": self.config.fingerprint.value,
            "source_ct32": self.source_ct32,
            "workbench_lane": WORKBENCH_LANE_GOVERNED,
        }


def analysis_rerun_identity() -> dict[str, object]:
    """Identity-bearing analysis.rerun fields. Package SemVer is omitted."""
    return {
        "class": ANALYSIS_RERUN_CLASS,
        "command": "analysis.rerun",
        "method": METHOD_RERUN,
        "mints_ct32": ANALYSIS_RERUN_MINTS_CT32,
        "mints_experiment_spec": ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC,
        "occupancy": ANALYSIS_RERUN_OCCUPANCY,
        "spawns_orchestrator": True,
        "workbench_lane": WORKBENCH_LANE_GOVERNED,
    }


def rerun(
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
    successor: object = None,
    mint_experiment_spec: object = None,
    sqlite: object = None,
    database: object = None,
    daemon_sqlite: object = None,
    **extra: object,
) -> Result[RerunOutcome]:
    """Spawn a new governed QMB run through the tunnel. Canonical artifact: CT-32.

    Occupancy is a run. ``starting_capital`` as an override stamps
    ``seed_overridden`` and forces fold ``unrated``. Coordinated Experiment
    Ledger persistence is Epic 36.
    """
    blocked = _refuse_payload_flags(
        extra=extra,
        occupancy=occupancy,
        analysis_method=analysis_method,
        lane=lane,
        workbench_lane=workbench_lane,
        experiment_spec=experiment_spec,
        successor=successor,
        mint_experiment_spec=mint_experiment_spec,
        sqlite=sqlite,
        database=database,
        daemon_sqlite=daemon_sqlite,
    )
    if blocked is not None:
        return blocked
    source = _cite_source(source_ct32)
    if is_refusal(source):
        return source
    compiled = _resolve_config(
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
    )
    if is_refusal(compiled):
        return compiled
    if slices is None:
        return invalid(
            "slices",
            "analysis.rerun is a new QMB run and requires the event slices the "
            "tunnel feeds run()",
        )
    if output_root is None:
        return invalid(
            "output_root",
            "analysis.rerun spawns a governed process-per-run under an isolated output root",
        )
    root = _ensure_output_root(output_root)
    if is_refusal(root):
        return root
    sink = _as_ledger(ledger)
    if is_refusal(sink):
        return sink
    spawned = spawn_governed(
        SpawnJob(
            config=compiled.value,
            slices=slices,
            projected_peak_memory=_occupancy_int(projected_peak_memory, _OCCUPANCY_PEAK),
        ),
        output_root=root.value,
        cpu_budget=_occupancy_int(cpu_budget, _OCCUPANCY_CPU),
        memory_budget=_occupancy_int(memory_budget, _OCCUPANCY_MEMORY),
        projected_peak_memory=_occupancy_int(projected_peak_memory, _OCCUPANCY_PEAK),
    )
    if is_refusal(spawned):
        return spawned
    isolated = spawned.value[0]
    stamped = isolated.ct32_fingerprint
    if stamped is None:
        return policy(
            "ct32",
            "analysis.rerun's canonical artifact is a new CT-32; a spawn without "
            "a CT-32 fingerprint is not a completed rerun (FR-W25, DEC-0273)",
            occupancy=ANALYSIS_RERUN_OCCUPANCY,
            mints_ct32=True,
            run_id=compiled.value.fingerprint.value,
        )
    minted = mint_completed_line(
        compiled.value,
        outcome_identity=isolated.outcome_identity,
        ct32_fingerprint=stamped,
        workbench_lane=WORKBENCH_LANE_GOVERNED,
    )
    if is_refusal(minted):
        return minted
    appended = sink.value.append(minted.value)
    if is_refusal(appended):
        return appended
    return Ok(
        RerunOutcome(
            source_ct32=source.value.value,
            config=compiled.value,
            isolated=isolated,
            ledger_line=appended.value,
            ct32_fingerprint=stamped,
        )
    )


def _cite_source(source: object) -> Result[Fingerprint]:
    if source is None:
        return invalid(
            "source_ct32",
            "analysis.rerun cites one completed run's CT-32 as the path-dependent source",
        )
    if isinstance(source, IsolatedRun):
        if source.ct32_fingerprint is None:
            return invalid(
                "source_ct32",
                "analysis.rerun cites a completed run whose canonical artifact is a CT-32",
            )
        return Ok(source.ct32_fingerprint)
    if isinstance(source, RerunOutcome):
        return Ok(source.ct32_fingerprint)
    if isinstance(source, Fingerprint):
        return Ok(source)
    token = clean_token(source)
    if token is not None and token.startswith("fp1:"):
        parsed = Fingerprint.try_create(token)
        if is_ok(parsed):
            return Ok(parsed.value)
        return parsed
    if isinstance(source, PerformanceResult):
        return source.fingerprint()
    artifact = as_ct32_artifact(source)
    if is_refusal(artifact):
        return invalid(
            "source_ct32",
            "analysis.rerun cites one completed CT-32 (artifact, stored JSON, "
            "run directory, IsolatedRun, or fp1)",
            given=repr(type(source).__name__),
        )
    stamped = artifact.value.get("fingerprint")
    parsed = Fingerprint.try_create(stamped) if isinstance(stamped, str) else None
    if parsed is not None and is_ok(parsed):
        return Ok(parsed.value)
    from qmf.core.fingerprint import fingerprint  # noqa: PLC0415 — identity of stored body

    identity = {key: value for key, value in artifact.value.items() if key != "qmb_extensions"}
    return fingerprint(identity)


def _resolve_config(
    *,
    config: object,
    port: object,
    book_fragment: object,
    bms_fragment: object,
    run_spec: object,
    invocation_flags: object,
    workspace_defaults: object,
    condition_presets: object,
    starting_capital: object,
    fill_port: object,
    cost_port: object,
    financing_port: object,
) -> Result[ResolvedRunConfig]:
    overlays = (starting_capital, fill_port, cost_port, financing_port)
    if isinstance(config, ResolvedRunConfig):
        mixed = (*overlays, port, book_fragment, bms_fragment, run_spec)
        if any(item is not None for item in mixed):
            return invalid(
                "config",
                "a resolved run-config is the compiled tunnel artifact; path-dependent "
                "Book/BMS/port/starting_capital overlays compile from layers, not a patch",
            )
        return Ok(config)
    if config is not None:
        return invalid(
            "config",
            "analysis.rerun takes a resolved run-config or compiles one from "
            "Book/BMS fragments, execution ports, and starting_capital",
            given=repr(type(config).__name__),
        )
    if any(item is None for item in (port, book_fragment, bms_fragment, run_spec)):
        return invalid(
            "config",
            "analysis.rerun compiles a new resolved run-config from port, "
            "book_fragment, bms_fragment, and run_spec, or takes a compiled artifact",
        )
    spec = _overlay_run_spec(
        run_spec,
        fill_port=fill_port,
        cost_port=cost_port,
        financing_port=financing_port,
    )
    if is_refusal(spec):
        return spec
    flags = _overlay_invocation_flags(invocation_flags, starting_capital=starting_capital)
    if is_refusal(flags):
        return flags
    return compile_run_config(
        port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec=spec.value,
        invocation_flags=flags.value,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
    )


def _overlay_run_spec(
    run_spec: object,
    *,
    fill_port: object,
    cost_port: object,
    financing_port: object,
) -> Result[dict[str, object]]:
    if not isinstance(run_spec, Mapping):
        return invalid(
            "run_spec",
            "the run spec (bot layer) is a mapping the compiler overlays",
            given=repr(type(run_spec).__name__),
        )
    spec = {str(key): value for key, value in cast("Mapping[object, object]", run_spec).items()}
    ports = {
        "fill_port": fill_port,
        "cost_port": cost_port,
        "financing_port": financing_port,
    }
    for field, value in ports.items():
        if value is None:
            continue
        key = _PORT_KEYS[field]
        token = value if not isinstance(value, str) else clean_token(value)
        if token is None:
            return invalid(
                field,
                "fill/cost/financing ports are adapter-id tokens bound from the "
                "resolved run-config (B-6)",
                given=repr(value),
            )
        spec[key] = token
    return Ok(spec)


def _overlay_invocation_flags(
    invocation_flags: object,
    *,
    starting_capital: object,
) -> Result[Mapping[str, object] | None]:
    flags: dict[str, object] = {}
    if invocation_flags is not None:
        if not isinstance(invocation_flags, Mapping):
            return invalid(
                "invocation_flags",
                "invocation flags are a mapping; starting_capital here stamps "
                "seed_overridden and forces fold unrated (FM-12)",
                given=repr(type(invocation_flags).__name__),
            )
        raw_flags = cast("Mapping[object, object]", invocation_flags)
        flags.update({str(key): value for key, value in raw_flags.items()})
    if starting_capital is not None:
        flags[STARTING_CAPITAL_KEY] = starting_capital
    if not flags:
        empty: Mapping[str, object] | None = None
        return Ok(empty)
    return Ok(flags)


def _ensure_output_root(output_root: object) -> Result[Path]:
    if isinstance(output_root, Path):
        root = output_root
    else:
        token = clean_token(output_root)
        if token is None:
            return invalid(
                "output_root",
                "analysis.rerun spawns under an isolated output root path",
                given=repr(type(output_root).__name__),
            )
        root = Path(token)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return storage(
            "output_root",
            "analysis.rerun could not create the isolated output root",
            given=type(exc).__name__,
            path=str(root),
        )
    return Ok(root)


def _as_ledger(ledger: object) -> Result[LedgerSink]:
    if ledger is None:
        return invalid(
            "ledger",
            "analysis.rerun is a governed run: it appends one QMB ledger line "
            "with workbench_lane=governed citing the new CT-32 by _ref (FR-W25)",
            occupancy=ANALYSIS_RERUN_OCCUPANCY,
            workbench_lane=WORKBENCH_LANE_GOVERNED,
        )
    if not isinstance(ledger, LedgerSink):
        return invalid(
            "ledger",
            "governed analysis.rerun writes through a LedgerSink",
            given=repr(type(ledger).__name__),
        )
    return Ok(ledger)


def _occupancy_int(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _refuse_payload_flags(
    *,
    extra: Mapping[str, object],
    occupancy: object,
    analysis_method: object,
    lane: object,
    workbench_lane: object,
    experiment_spec: object,
    successor: object,
    mint_experiment_spec: object,
    sqlite: object,
    database: object,
    daemon_sqlite: object,
) -> TypedRefusal | None:
    labels = _requested_field(
        {
            "analysis_method": analysis_method,
            "lane": lane,
            "workbench_lane": workbench_lane,
        },
        _LABEL_FIELDS,
    )
    if labels is None:
        labels = next((key for key in extra if key in _LABEL_FIELDS), None)
    if labels is not None:
        return policy(
            labels,
            "analysis_method and lane are not CT-32 or B-4 fields and are not a "
            "payload flag; analysis.rerun stamps workbench_lane=governed on the "
            "QMB ledger line citing the CT-32 by _ref. Coordinated Experiment "
            "Ledger is Epic 36 (FR-W07, FR-W25, FR-W28, DEC-0270)",
            occupancy=ANALYSIS_RERUN_OCCUPANCY,
            mints_ct32=True,
            workbench_lane=WORKBENCH_LANE_GOVERNED,
            epic="36",
        )
    spec = _requested_field(
        {
            "experiment_spec": experiment_spec,
            "mint_experiment_spec": mint_experiment_spec,
            "successor": successor,
        },
        _SPEC_FIELDS,
    )
    if spec is not None:
        return policy(
            spec,
            "analysis.rerun mints no ExperimentSpec successor; the coordinated "
            "Experiment Ledger stamp is Epic 36 (FR-W25, DEC-0276)",
            occupancy=ANALYSIS_RERUN_OCCUPANCY,
            mints_ct32=True,
            mints_experiment_spec=False,
            epic="36",
        )
    sqlite_field = _requested_field(
        {"daemon_sqlite": daemon_sqlite, "database": database, "sqlite": sqlite},
        _SQLITE_FIELDS,
    )
    if sqlite_field is not None:
        return policy(
            sqlite_field,
            "analysis.rerun does not open daemon sqlite; coordinated Experiment "
            "Ledger persistence is Epic 36 (FR-W25, DEC-0273)",
            occupancy=ANALYSIS_RERUN_OCCUPANCY,
            opens_sqlite=False,
            epic="36",
            workbench_lane=WORKBENCH_LANE_GOVERNED,
            coordinated=WORKBENCH_LANE_COORDINATED,
        )
    if occupancy is None:
        return None
    token = clean_token(occupancy)
    folded = occupancy.casefold() if isinstance(occupancy, str) else token
    if isinstance(folded, str) and folded in _QUERY_TOKENS:
        return policy(
            "occupancy",
            "analysis.rerun consumes one qmb run invocation per ExecutionEnvironment; "
            "it is not a query (FR-W11, FR-W25)",
            occupancy=ANALYSIS_RERUN_OCCUPANCY,
            given=folded,
            mints_ct32=True,
        )
    if not (isinstance(folded, str) and folded in _RUN_TOKENS):
        return invalid(
            "occupancy",
            "analysis.rerun occupancy is run — one qmb run invocation, never a query",
            given=repr(occupancy),
            occupancy=ANALYSIS_RERUN_OCCUPANCY,
        )
    return None


def _requested_field(fields: Mapping[str, object], names: tuple[str, ...]) -> str | None:
    for name in names:
        if fields.get(name) not in (None, False):
            return name
    return None
