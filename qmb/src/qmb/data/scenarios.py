"""Deterministic multi-scenario generation with the pinned RNG (Story 23.4).

A multi-scenario request fans a resolved generator config out into ``N`` scenarios
whose substreams are each derived deterministically from the master seed
(``base_seed + scenario_index``, :data:`~qmb.data.rng.SEED_DERIVATION_RULE`), so
scenario ``k`` is bit-reproducible in isolation and every scenario is tagged by its
index — original-vs-synthetic is unambiguous regardless of completion order (R5; spec
section 2B; AC3).

The Jesse anchor pattern is honored by construction (AC4/AC5):

* a **history-seeded** process (``block-bootstrap`` / ``gaussian-resample`` /
  ``gaussian-noise``) has a real anchor, so **scenario 0 is the untouched original real
  path** — the cited source bars placed on the generation grid, drawing no randomness —
  and scenarios ``>0`` are perturbations of that path, each through the QMX-owned pinned
  RNG seeded ``base_seed + scenario_index``;
* a **from-scratch** ``gbm`` process has no real source to anchor, so there is **no
  scenario-0 original anchor and no robustness percentile band or p-value is
  computable** — the fan-out records ``robustness_band_computable = False`` and its
  permittable claim classes are ``infra-stress`` / ``logic-smoke`` only (spec section 5
  Q7; R3). :func:`refuse_robustness_band_for_from_scratch` is the contract refusal for
  any caller that asks for a band on such a run.

Scenario fan-out runs **process-per-run under the orchestrator's ``min(cpu, memory)``
governor** with enqueue-when-full — never silent oversubscription (B-5; AR-50; Epic 15;
AC6): :func:`scenario_governed_requests` builds one governed request per scenario and
:func:`admit_scenario_fanout` drives them through a :class:`~qmb.orchestrator.governor.
ResourceGovernor`. A scenario whose generation refuses is **counted and reported as a
typed refusal** in the fan-out result, never silently dropped beyond the explicit
``filtered_count`` line (R7, R8; AC6).

This module holds no mutable state and reads nothing ambient; every operation is a pure
``Result``-returning function or a frozen value type.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import clean_token, invalid, policy
from qmb.data.claim_class import (
    generator_lineage,
    permittable_claim_classes,
)
from qmb.data.generate import (
    GENERATOR_WORLD,
    SYNTHETIC_ORIGIN,
    SyntheticBar,
    build_generation_grid,
    resolve_generator_config,
    resolve_source_series,
    run_generator_adapter,
)
from qmb.data.rng import (
    RNG_ALGORITHM,
    RNG_FAMILY,
    RNG_VERSION,
    SEED_DERIVATION_RULE,
    derive_substream_seed,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only; avoids the results/execution import cycle
    from qmb.data.gap_check import MarketHoursCalendar
    from qmb.orchestrator.governor import GovernedRequest

# The ``qmb.data`` package is imported before ``qmb.results`` / ``qmb.orchestrator`` /
# ``qmb.ledger`` in ``qmb.__init__``, and ``qmb.ledger.line`` / ``qmb.orchestrator``
# pull in ``qmb.results.ct32`` (execution + runloop) — so importing them at module load
# would form the results/execution import cycle. This front therefore imports the
# governor lazily (inside the fan-out functions), exactly as ``generate.py`` imports
# ``orchestrator.paths`` lazily, and mirrors the ratified ``role = replicate`` vocabulary
# constant locally (``qmb.ledger.line.ROLE_REPLICATE``, a stable ledger role token).
ROLE_REPLICATE: Final[str] = "replicate"

__all__ = [
    "FANOUT_CLASS",
    "FANOUT_RESULT_FORMAT_VERSION",
    "GOVERNOR_BOUND",
    "SCENARIO_CLASS",
    "SCENARIO_ZERO_IS_ORIGINAL_ANCHOR",
    "GeneratedScenario",
    "GovernorAdmissionPlan",
    "RngProvenance",
    "ScenarioFailure",
    "ScenarioFanout",
    "admit_scenario_fanout",
    "derive_scenario_seeds",
    "generate_scenarios",
    "refuse_robustness_band_for_from_scratch",
    "regenerate_scenario",
    "scenario_governed_requests",
    "scenarios_identity",
]

# --- the multi-scenario contract constants -----------------------------------

SCENARIO_CLASS: Final[str] = "qmb-generated-scenario"
FANOUT_CLASS: Final[str] = "qmb-scenario-fanout"
FANOUT_RESULT_FORMAT_VERSION: Final[int] = 1
_RNG_PROVENANCE_CLASS: Final[str] = "qmb-generator-rng-provenance"
_SCENARIO_FAILURE_CLASS: Final[str] = "qmb-scenario-failure"
_ADMISSION_PLAN_CLASS: Final[str] = "qmb-scenario-governor-admission"

# For a history-seeded process, scenario 0 is the untouched original real path; for a
# from-scratch gbm there is no scenario-0 anchor (AC4/AC5).
SCENARIO_ZERO_IS_ORIGINAL_ANCHOR: Final[bool] = True

# The governor admits on the more constraining of the two capacities (B-5).
GOVERNOR_BOUND: Final[str] = "min-cpu-memory"


# --- the pinned-RNG provenance record (R4/R5, AC2) ---------------------------


@dataclass(frozen=True, slots=True)
class RngProvenance:
    """The QMX-owned pinned-RNG provenance a fan-out records (R4/R5, AC2).

    Names the QMX-owned algorithm and its pinned version, the substream seed-derivation
    rule, and the master seed and scenario count. It asserts the generator never draws
    through a runtime stdlib Random (spec section 2A.3).
    """

    rng_algorithm: str
    rng_family: str
    rng_version: int
    seed_derivation_rule: str
    base_seed: int
    scenario_count: int

    @property
    def is_runtime_stdlib_random(self) -> bool:
        """Always ``False`` — the generator owns its RNG (AC2)."""
        return False

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Package SemVer never enters."""
        return {
            "base_seed": self.base_seed,
            "class": _RNG_PROVENANCE_CLASS,
            "is_runtime_stdlib_random": False,
            "rng_algorithm": self.rng_algorithm,
            "rng_family": self.rng_family,
            "rng_version": self.rng_version,
            "scenario_count": self.scenario_count,
            "seed_derivation_rule": self.seed_derivation_rule,
        }


# --- one generated scenario (AC3, AC4) ---------------------------------------


@dataclass(frozen=True, slots=True)
class GeneratedScenario:
    """One generated scenario: index, derived substream seed, run id, bars (AC3, AC4).

    ``role`` is always ``replicate`` — a scenario is a governed replicate run. The
    substream ``seed`` is ``base_seed + scenario_index`` and ``run_id`` is the
    deterministic ``fp1`` of the per-scenario config, so scenario ``k`` reproduces in
    isolation. ``is_original_anchor`` marks the untouched original real path (scenario 0
    of a history-seeded run). ``series_fingerprint`` is the ``fp1`` over the scenario's
    bars; the fan-out folds only that fingerprint into its identity.
    """

    scenario_index: int
    seed: int
    run_id: Fingerprint
    is_original_anchor: bool
    bars: tuple[SyntheticBar, ...]
    series_fingerprint: Fingerprint
    role: str = ROLE_REPLICATE

    def fp1_identity(self) -> dict[str, object]:
        """Canonical scenario identity — bars folded in only by their fingerprint."""
        return {
            "class": SCENARIO_CLASS,
            "is_original_anchor": self.is_original_anchor,
            "role": self.role,
            "run_id": self.run_id.value,
            "scenario_index": self.scenario_index,
            "seed": self.seed,
            "series_fingerprint": self.series_fingerprint.value,
        }

    def as_mapping(self) -> dict[str, object]:
        """Machine-readable scenario row (door transport)."""
        content = dict(self.fp1_identity())
        content["bar_count"] = len(self.bars)
        content["bars"] = tuple(bar.as_mapping() for bar in self.bars)
        return content


# --- a counted, typed scenario failure (AC6, R7/R8) --------------------------


@dataclass(frozen=True, slots=True)
class ScenarioFailure:
    """One scenario failure, counted and reported as a typed refusal (AC6, R7/R8).

    A scenario whose generation refuses is captured here — its index, substream seed,
    deterministic run id, the refusal category, and the offending field/reason — and
    counted in the fan-out's ``filtered_count``. It is never silently dropped: it still
    consumed a governor slot in the process-per-run fan-out, so its ``run_id`` is one of
    the fan-out's governed requests.
    """

    scenario_index: int
    seed: int
    run_id: Fingerprint
    category: str
    field: str
    reason: str

    def fp1_identity(self) -> dict[str, object]:
        """Canonical failure identity content."""
        return {
            "category": self.category,
            "class": _SCENARIO_FAILURE_CLASS,
            "field": self.field,
            "reason": self.reason,
            "run_id": self.run_id.value,
            "scenario_index": self.scenario_index,
            "seed": self.seed,
        }


# --- the scenario fan-out result (AC3-AC6) -----------------------------------


@dataclass(frozen=True, slots=True)
class ScenarioFanout:
    """The deterministic multi-scenario fan-out of one generator config (AC3-AC6).

    ``scenarios`` are the successfully generated scenarios (scenario 0 is the untouched
    original for a history-seeded run); ``failures`` are the counted, typed
    per-scenario refusals and ``filtered_count`` is their explicit count. ``world`` is
    ``simulated`` and ``permittable_claim_classes`` is the world/lineage-bounded set
    (``infra-stress`` / ``logic-smoke``). ``has_original_anchor`` and
    ``robustness_band_computable`` are ``True`` only for a history-seeded lineage; for a
    from-scratch gbm they are ``False`` and no robustness band or p-value may be computed
    (AC5). ``governed_requests`` are the process-per-run governor requests for the whole
    fan-out — one per scenario the governor spawns, including a scenario whose generation
    later refuses (its run id still consumed a slot). Identity is a pure function of the
    inputs — :meth:`fingerprint` reproduces bit-for-bit.
    """

    process: str
    lineage: str
    base_seed: int
    scenario_count: int
    world: str
    origin: str
    has_original_anchor: bool
    robustness_band_computable: bool
    permittable_claim_classes: tuple[str, ...]
    rng_provenance: RngProvenance
    scenarios: tuple[GeneratedScenario, ...]
    failures: tuple[ScenarioFailure, ...]
    filtered_count: int
    governed_requests: tuple[GovernedRequest, ...] = ()

    @property
    def produced_count(self) -> int:
        """The number of scenarios successfully generated."""
        return len(self.scenarios)

    def original_anchor(self) -> GeneratedScenario | None:
        """Scenario 0's untouched-original series, or ``None`` for a from-scratch run (AC4)."""
        if not self.has_original_anchor:
            return None
        for scenario in self.scenarios:
            if scenario.is_original_anchor:
                return scenario
        return None

    def scenario_at(self, scenario_index: int) -> GeneratedScenario | None:
        """The scenario tagged ``scenario_index``, or ``None`` if it failed / is absent."""
        for scenario in self.scenarios:
            if scenario.scenario_index == scenario_index:
                return scenario
        return None

    def robustness_band_refusal(self) -> TypedRefusal | None:
        """The from-scratch robustness-band refusal, or ``None`` when an anchor exists (AC5)."""
        if self.robustness_band_computable:
            return None
        return refuse_robustness_band_for_from_scratch(self.process)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Deterministic and reproducible (AC1, NFR-03)."""
        return {
            "base_seed": self.base_seed,
            "class": FANOUT_CLASS,
            "failures": [failure.fp1_identity() for failure in self.failures],
            "filtered_count": self.filtered_count,
            "format_version": FANOUT_RESULT_FORMAT_VERSION,
            "governor_bound": GOVERNOR_BOUND,
            "has_original_anchor": self.has_original_anchor,
            "lineage": self.lineage,
            "origin": self.origin,
            "permittable_claim_classes": list(self.permittable_claim_classes),
            "process": self.process,
            "rng_provenance": self.rng_provenance.fp1_identity(),
            "robustness_band_computable": self.robustness_band_computable,
            "scenario_count": self.scenario_count,
            "scenarios": [scenario.fp1_identity() for scenario in self.scenarios],
            "world": self.world,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. The same inputs reproduce it bit-for-bit (AC1, AC3)."""
        return fingerprint(self.fp1_identity())

    def as_mapping(self) -> dict[str, object]:
        """Machine-readable fan-out result (door transport)."""
        content = dict(self.fp1_identity())
        content["produced_count"] = self.produced_count
        content["scenarios"] = tuple(scenario.as_mapping() for scenario in self.scenarios)
        content["governed_requests"] = tuple(
            request.fp1_identity() for request in self.governed_requests
        )
        return content


# --- the governor admission plan (AC6) ---------------------------------------


@dataclass(frozen=True, slots=True)
class GovernorAdmissionPlan:
    """The min(cpu, memory) admission plan for a scenario fan-out (B-5, AR-50, AC6).

    ``parallelism_bound`` is ``min(cpu slots, memory slots)`` — the homogeneous
    concurrent-run cap; ``admitted`` are the run ids admitted immediately and ``queued``
    are those held by enqueue-on-full (never silently oversubscribed). A run that can
    never fit the declared total budget, or an ``on_full = refuse`` overflow, surfaces as
    a typed refusal from :func:`admit_scenario_fanout`, not in this plan.
    """

    bound: str
    parallelism_bound: int
    admitted: tuple[str, ...]
    queued: tuple[str, ...]
    on_full: str

    @property
    def silent_oversubscription(self) -> bool:
        """Always ``False`` — admission is bounded by min(cpu, memory) (B-5, FM-6)."""
        return False

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content."""
        return {
            "admitted": list(self.admitted),
            "bound": self.bound,
            "class": _ADMISSION_PLAN_CLASS,
            "on_full": self.on_full,
            "parallelism_bound": self.parallelism_bound,
            "queued": list(self.queued),
            "silent_oversubscription": False,
        }


# --- seed derivation (AC3) ---------------------------------------------------


def derive_scenario_seeds(base_seed: object, scenario_count: object) -> Result[tuple[int, ...]]:
    """The deterministic substream seeds of a fan-out: ``base + 0 .. base + N-1`` (AC3).

    Each scenario's substream seed is ``base_seed + scenario_index`` so scenario ``k``
    reproduces in isolation (SEED_DERIVATION_RULE). ``base_seed`` is a non-negative
    integer and ``scenario_count`` a strictly-positive integer; a malformed value is a
    typed ``invalid input`` refusal.
    """
    base = _non_negative_int(base_seed, "base_seed")
    if is_refusal(base):
        return base
    count = _positive_int(scenario_count, "scenario_count")
    if is_refusal(count):
        return count
    return Ok(tuple(derive_substream_seed(base.value, index) for index in range(count.value)))


# --- the multi-scenario generation entry point (AC3-AC6) ---------------------


def generate_scenarios(
    resources: object,
    *,
    calendar: MarketHoursCalendar | None = None,
    source_series: object = None,
    projected_peak_memory: object = None,
    cpu_cost: object = 1,
) -> Result[ScenarioFanout]:
    """Fan a generator config out into ``N`` deterministic scenarios (AC3-AC6).

    Resolves the config, builds the shared market-hours grid and (for a history-seeded
    process) the cited source bars, then generates ``scenario_count`` scenarios. Each
    scenario ``k`` draws from the QMX-owned pinned RNG seeded ``base_seed + k``; scenario
    0 of a history-seeded run is the untouched original real path (no draw), and
    scenarios ``>0`` are perturbations. A from-scratch gbm has no original anchor and no
    computable robustness band. A scenario whose generation refuses is counted and
    reported (typed) in ``failures`` / ``filtered_count``, never silently dropped. When
    ``projected_peak_memory`` is supplied, the per-scenario governor requests are built
    for the process-per-run fan-out. No output root is written; persistence is the
    orchestrator's job.
    """
    resolved = resolve_generator_config(resources)
    if is_refusal(resolved):
        return resolved
    config = resolved.value
    body: Mapping[str, object] = (
        cast("Mapping[str, object]", resources) if isinstance(resources, Mapping) else {}
    )

    lineage = generator_lineage(config.process)
    if is_refusal(lineage):
        return lineage

    seeds = derive_scenario_seeds(config.seed, config.scenario_count)
    if is_refusal(seeds):
        return seeds

    grid = build_generation_grid(config, calendar=calendar, resources=body)
    if is_refusal(grid):
        return grid

    source_loaded = resolve_source_series(config, source_series=source_series, resources=body)
    if is_refusal(source_loaded):
        return source_loaded
    source_bars = source_loaded.value

    has_anchor = config.is_history_seeded
    anchor_bars: tuple[SyntheticBar, ...] | None = None
    if has_anchor:
        built_anchor = _original_anchor_bars(source_bars, grid.value, config.scale)
        if is_refusal(built_anchor):
            return built_anchor
        anchor_bars = built_anchor.value

    # Phase 1 — the deterministic per-scenario run ids of the whole fan-out. Every
    # scenario (including one whose generation later refuses) is a process-per-run unit
    # the governor spawns, so its run id is one of the fan-out's governed requests.
    run_ids: list[Fingerprint] = []
    for seed in seeds.value:
        run_id = config.with_seed(seed).fingerprint()
        if is_refusal(run_id):
            return run_id
        run_ids.append(run_id.value)

    # Phase 2 — generate each scenario's bars; a refusal is a counted, typed failure.
    scenarios: list[GeneratedScenario] = []
    failures: list[ScenarioFailure] = []
    for index, seed in enumerate(seeds.value):
        is_anchor = has_anchor and index == 0
        if is_anchor and anchor_bars is not None:
            produced: Result[tuple[SyntheticBar, ...]] = Ok(anchor_bars)
        else:
            produced = run_generator_adapter(
                config.with_seed(seed), grid=grid.value, source_bars=source_bars
            )
        if is_refusal(produced):
            failures.append(_failure_of(index, seed, run_ids[index], produced))
            continue
        bars = produced.value
        series_fp = fingerprint(_scenario_series_identity(index, is_anchor, bars))
        if is_refusal(series_fp):
            return series_fp
        scenarios.append(
            GeneratedScenario(
                scenario_index=index,
                seed=seed,
                run_id=run_ids[index],
                is_original_anchor=is_anchor,
                bars=bars,
                series_fingerprint=series_fp.value,
            )
        )

    permittable = permittable_claim_classes(config.process, GENERATOR_WORLD)
    if is_refusal(permittable):
        return permittable

    governed_requests: tuple[GovernedRequest, ...] = ()
    if projected_peak_memory is not None:
        built_requests = _governed_requests_for_run_ids(
            run_ids, projected_peak_memory=projected_peak_memory, cpu_cost=cpu_cost
        )
        if is_refusal(built_requests):
            return built_requests
        governed_requests = built_requests.value

    rng_provenance = RngProvenance(
        rng_algorithm=RNG_ALGORITHM,
        rng_family=RNG_FAMILY,
        rng_version=RNG_VERSION,
        seed_derivation_rule=SEED_DERIVATION_RULE,
        base_seed=config.seed,
        scenario_count=config.scenario_count,
    )
    return Ok(
        ScenarioFanout(
            process=config.process,
            lineage=lineage.value,
            base_seed=config.seed,
            scenario_count=config.scenario_count,
            world=GENERATOR_WORLD,
            origin=SYNTHETIC_ORIGIN,
            has_original_anchor=has_anchor,
            robustness_band_computable=has_anchor,
            permittable_claim_classes=permittable.value,
            rng_provenance=rng_provenance,
            scenarios=tuple(scenarios),
            failures=tuple(failures),
            filtered_count=len(failures),
            governed_requests=governed_requests,
        )
    )


def regenerate_scenario(
    resources: object,
    scenario_index: object,
    *,
    calendar: MarketHoursCalendar | None = None,
    source_series: object = None,
) -> Result[GeneratedScenario]:
    """Regenerate a single scenario by index, proving it reproduces in isolation (AC3).

    Resolves the config, derives scenario ``k``'s substream seed ``base_seed + k``, and
    generates only that scenario — the untouched original for scenario 0 of a
    history-seeded run, else a perturbation through the pinned RNG. The scenario's bars
    and fingerprint are identical to the one produced inside the full fan-out, so a
    scenario is bit-reproducible in isolation, independent of completion order.
    """
    resolved = resolve_generator_config(resources)
    if is_refusal(resolved):
        return resolved
    config = resolved.value
    body: Mapping[str, object] = (
        cast("Mapping[str, object]", resources) if isinstance(resources, Mapping) else {}
    )
    index = _non_negative_int(scenario_index, "scenario_index")
    if is_refusal(index):
        return index
    if index.value >= config.scenario_count:
        return invalid(
            "scenario_index",
            "the scenario index is within the requested scenario count",
            scenario_index=index.value,
            scenario_count=config.scenario_count,
        )
    seed = derive_substream_seed(config.seed, index.value)
    is_anchor = config.is_history_seeded and index.value == 0
    scenario_config = config.with_seed(seed)
    run_id = scenario_config.fingerprint()
    if is_refusal(run_id):
        return run_id

    grid = build_generation_grid(config, calendar=calendar, resources=body)
    if is_refusal(grid):
        return grid
    source_loaded = resolve_source_series(config, source_series=source_series, resources=body)
    if is_refusal(source_loaded):
        return source_loaded
    source_bars = source_loaded.value

    if is_anchor:
        produced = _original_anchor_bars(source_bars, grid.value, config.scale)
    else:
        produced = run_generator_adapter(
            scenario_config, grid=grid.value, source_bars=source_bars
        )
    if is_refusal(produced):
        return produced
    bars = produced.value
    series_fp = fingerprint(_scenario_series_identity(index.value, is_anchor, bars))
    if is_refusal(series_fp):
        return series_fp
    return Ok(
        GeneratedScenario(
            scenario_index=index.value,
            seed=seed,
            run_id=run_id.value,
            is_original_anchor=is_anchor,
            bars=bars,
            series_fingerprint=series_fp.value,
        )
    )


# --- the governed process-per-run fan-out (B-5, AR-50, AC6) ------------------


def scenario_governed_requests(
    scenarios: object,
    *,
    projected_peak_memory: object,
    cpu_cost: object = 1,
) -> Result[tuple[GovernedRequest, ...]]:
    """Build one governor request per scenario for the process-per-run fan-out (AC6).

    Each :class:`GeneratedScenario` becomes one
    :class:`~qmb.orchestrator.governor.GovernedRequest` the orchestrator submits to its
    ``min(cpu, memory)`` resource governor: admitted when it fits, enqueued when full,
    never silently oversubscribed. Process fan-out belongs to the orchestrator — no Ray,
    no daemon, no required Docker — and each governed scenario ledgers exactly one
    ``role = replicate`` line.
    """
    parsed = _coerce_scenarios(scenarios)
    if is_refusal(parsed):
        return parsed
    return _governed_requests_for_run_ids(
        [scenario.run_id for scenario in parsed.value],
        projected_peak_memory=projected_peak_memory,
        cpu_cost=cpu_cost,
    )


def admit_scenario_fanout(
    requests: object,
    budgets: object,
    *,
    on_full: object = None,
) -> Result[GovernorAdmissionPlan]:
    """Drive a scenario fan-out through the min(cpu, memory) governor (B-5, AR-50, AC6).

    Submits each governed request to a fresh :class:`~qmb.orchestrator.governor.
    ResourceGovernor` bound by the declared ``budgets``: it admits up to
    ``min(cpu slots, memory slots)`` runs and enqueues the rest (enqueue-on-full, the
    default when ``on_full`` is unset), never silently oversubscribing. A run that can
    never fit the declared total budget, or an ``on_full = refuse`` overflow, is a typed
    refusal — returned, never swallowed. ``requests`` is a :class:`ScenarioFanout` (its
    ``governed_requests``) or a sequence of :class:`~qmb.orchestrator.governor.
    GovernedRequest`.
    """
    from qmb.orchestrator.governor import (  # noqa: PLC0415 — import-cycle with orchestrator
        DECISION_ADMITTED,
        ResourceGovernor,
    )

    parsed = _coerce_requests(requests)
    if is_refusal(parsed):
        return parsed
    request_list = parsed.value
    if not request_list:
        return invalid(
            "requests",
            "a scenario fan-out has at least one governed request to admit; build them with "
            "scenario_governed_requests (supply projected_peak_memory to generate_scenarios)",
        )
    governor = ResourceGovernor.try_create(budgets=budgets, on_full=on_full)
    if is_refusal(governor):
        return governor
    gov = governor.value
    head = request_list[0]
    bound = gov.budgets.parallelism_bound(head.projected_peak_memory, head.cpu_cost)
    if is_refusal(bound):
        return bound
    admitted: list[str] = []
    queued: list[str] = []
    for request in request_list:
        decision = gov.submit(request)
        if is_refusal(decision):
            return decision
        if decision.value.decision == DECISION_ADMITTED:
            admitted.append(request.run_id.value)
        else:
            queued.append(request.run_id.value)
    return Ok(
        GovernorAdmissionPlan(
            bound=GOVERNOR_BOUND,
            parallelism_bound=bound.value,
            admitted=tuple(admitted),
            queued=tuple(queued),
            on_full=gov.on_full,
        )
    )


def refuse_robustness_band_for_from_scratch(process: object) -> TypedRefusal:
    """Refuse a robustness band / p-value on a from-scratch scenario set (AC5, spec section 5 Q7).

    A from-scratch ``gbm`` fan-out has no scenario-0 original real path to anchor a
    p-value, so NO robustness percentile band or p-value may be computed — the run emits
    only ``infra-stress`` / ``logic-smoke`` verdicts. A caller that asks for a robustness
    band on such a run is a typed ``policy rejection`` — returned, never raised (R3, R8).
    """
    token = clean_token(process)
    named = token if token is not None else repr(process)
    return policy(
        "robustness_band",
        "a from-scratch generator run has no scenario-0 original anchor; no robustness "
        "percentile band or p-value may be computed — the run emits only infra-stress / "
        "logic-smoke verdicts (spec section 5 Q7, R3, AC5)",
        process=named,
        has_original_anchor=False,
        robustness_band_computable=False,
    )


# --- identity ----------------------------------------------------------------


def scenarios_identity() -> dict[str, object]:
    """Identity-bearing multi-scenario-contract fields. Package SemVer is omitted."""
    return {
        "fanout_class": FANOUT_CLASS,
        "fanout_result_format_version": FANOUT_RESULT_FORMAT_VERSION,
        "governor_bound": GOVERNOR_BOUND,
        "rng_algorithm": RNG_ALGORITHM,
        "rng_family": RNG_FAMILY,
        "rng_version": RNG_VERSION,
        "scenario_class": SCENARIO_CLASS,
        "scenario_run_role": ROLE_REPLICATE,
        "scenario_zero_is_original_anchor": SCENARIO_ZERO_IS_ORIGINAL_ANCHOR,
        "seed_derivation_rule": SEED_DERIVATION_RULE,
    }


# --- internals ---------------------------------------------------------------


def _original_anchor_bars(
    source_bars: tuple[SyntheticBar, ...] | None,
    grid: tuple[int, ...],
    scale: int,
) -> Result[tuple[SyntheticBar, ...]]:
    """Scenario 0's untouched original real path on the generation grid (AC4).

    Places the cited source bars' verbatim OHLC on the shared market-hours grid instants
    — the real prices, re-timestamped so the anchor is directly comparable to the
    perturbed scenarios. It draws no randomness. Too few real bars to cover the window is
    a typed ``invalid input``: there is no real path to anchor.
    """
    if source_bars is None or not source_bars:
        return invalid(
            "source_series",
            "a history-seeded scenario 0 is the untouched original real path; the cited "
            "source series was not resolved to bars",
        )
    if len(source_bars) < len(grid):
        return invalid(
            "source_series",
            "the untouched original anchor needs at least one real source bar per grid slot; "
            "the cited source series is shorter than the generation window (AC4)",
            source_bar_count=len(source_bars),
            grid_slots=len(grid),
        )
    anchor: list[SyntheticBar] = []
    for index, instant_ns in enumerate(grid):
        source = source_bars[index]
        built = SyntheticBar.try_create(
            instant_ns, source.open, source.high, source.low, source.close, scale
        )
        if is_refusal(built):
            return built
        anchor.append(built.value)
    return Ok(tuple(anchor))


def _scenario_series_identity(
    scenario_index: int, is_anchor: bool, bars: tuple[SyntheticBar, ...]
) -> dict[str, object]:
    """Canonical identity of one scenario's bar series (folded into the scenario fp1)."""
    return {
        "bars": [bar.fp1_identity() for bar in bars],
        "class": f"{SCENARIO_CLASS}-series",
        "is_original_anchor": is_anchor,
        "scenario_index": scenario_index,
    }


def _governed_requests_for_run_ids(
    run_ids: Sequence[Fingerprint],
    *,
    projected_peak_memory: object,
    cpu_cost: object = 1,
) -> Result[tuple[GovernedRequest, ...]]:
    """Build one governor request per run id — the canonical fan-out request builder."""
    from qmb.orchestrator.governor import (  # noqa: PLC0415 — import-cycle with orchestrator
        GovernedRequest,
    )

    requests: list[GovernedRequest] = []
    for run_id in run_ids:
        built = GovernedRequest.try_create(run_id, projected_peak_memory, cpu_cost)
        if is_refusal(built):
            return built
        requests.append(built.value)
    return Ok(tuple(requests))


def _failure_of(
    index: int, seed: int, run_id: Fingerprint, refusal: TypedRefusal
) -> ScenarioFailure:
    """Capture a per-scenario refusal as a counted, typed failure (AC6)."""
    field = clean_token(refusal.context.get("field")) or "scenario"
    reason = refusal.context.get("reason")
    return ScenarioFailure(
        scenario_index=index,
        seed=seed,
        run_id=run_id,
        category=refusal.category.value,
        field=field,
        reason=str(reason) if reason is not None else "",
    )


def _coerce_scenarios(value: object) -> Result[tuple[GeneratedScenario, ...]]:
    if isinstance(value, GeneratedScenario):
        return Ok((value,))
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "scenarios",
            "the fan-out reads a sequence of GeneratedScenario descriptors",
            given=repr(type(value).__name__),
        )
    out: list[GeneratedScenario] = []
    for idx, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, GeneratedScenario):
            return invalid(
                "scenarios",
                "each scenario is a GeneratedScenario built by generate_scenarios",
                index=idx,
                given=repr(type(item).__name__),
            )
        out.append(item)
    if not out:
        return invalid("scenarios", "a scenario fan-out has at least one scenario")
    return Ok(tuple(out))


def _coerce_requests(value: object) -> Result[tuple[GovernedRequest, ...]]:
    from qmb.orchestrator.governor import (  # noqa: PLC0415 — import-cycle with orchestrator
        GovernedRequest,
    )

    if isinstance(value, ScenarioFanout):
        return Ok(value.governed_requests)
    if isinstance(value, GovernedRequest):
        return Ok((value,))
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "requests",
            "admission reads a ScenarioFanout or a sequence of GovernedRequest values",
            given=repr(type(value).__name__),
        )
    out: list[GovernedRequest] = []
    for idx, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, GovernedRequest):
            return invalid(
                "requests",
                "each request is a GovernedRequest built by scenario_governed_requests",
                index=idx,
                given=repr(type(item).__name__),
            )
        out.append(item)
    return Ok(tuple(out))


def _non_negative_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, f"{field} is a non-negative exact integer", given=repr(value))
    return Ok(value)


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, f"{field} is a strictly positive exact integer", given=repr(value))
    return Ok(value)
