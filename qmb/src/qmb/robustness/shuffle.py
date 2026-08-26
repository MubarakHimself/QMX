"""Monte Carlo trade-shuffle — the sequence-risk B-14 rung (Story 22.2).

The first ladder procedure (22.2) re-orders a completed ``world = replay``
backtest's **realised trades** N times and re-derives the equity path and metrics,
so the operator can quantify how much the *ordering* of trades drove the outcome
(sequence risk) rather than the entry logic itself.

What the procedure is:

* a **pure library function** (:func:`run_trade_shuffle`) under the B-14 contract —
  it consumes the run's CT-29 realised-trade stream plus the virtual-ledger seed and
  the data-window bounds, RETURNS its result, and writes no log and no ledger line
  (the Epic 15 orchestrator owns every append). It is **procedure-ephemeral**: it
  never mints or persists a synthetic market series, so the run stays
  ``world = replay`` and its provenance is ``procedure-ephemeral`` (B-7; AC1);
* **exact-integer money math** (AD-7): each scenario keeps the multiset of realised
  P&Ls but permutes which P&L lands at which close instant of the same timeline, then
  re-accumulates the equity path as exact scaled integers. Path-dependent metrics
  (max drawdown, its recovery, losing streak, and the drawdown-derived ratios) move;
  order-invariant ones (net profit, win rate) do not (AC1);
* **per-scenario reproducibility** (AR-59; NFR-03): scenario ``s`` is shuffled by a
  fresh :class:`random.Random` seeded ``base_seed + s`` — no module-global RNG, no
  per-process hash randomization — and the result records the RNG family, base seed,
  seed-derivation rule, scenario count, and data-window UTC-ns bounds. Re-running the
  same inputs reproduces the result fingerprint bit-for-bit (AC2);
* a **direction-aware summary** built on the Story 22.1 distribution primitive
  (:func:`~qmb.robustness.summary.summarize_distribution`): per selected metric it
  carries percentile ranks, confidence bands, and the direction-aware empirical
  percentile rank of the original result (lower-is-better for drawdown), as chart
  **series data, never images** — and it emits no pass/fail verdict, the thresholds
  and the MC-1000 battery staying deferred (SC-07; AC3, AC4).

Fan-out (AC5): the scenario count is a UI-editable configurable with no ratified
value — the MC-1000 baseline is a deferred battery candidate, NOT a baked default —
and when scenarios fan out, the fan-out is the orchestrator's process-per-run
governor bounded by ``min(cpu, memory)`` with enqueue-when-full (no Ray, no daemon,
no required Docker; AR-50). Each governed scenario is cancellable via its cancel
token, and the orchestrator appends exactly one ledger line per scenario with
``role = replicate`` and never a bar verdict (B-4; AR-51). This module builds the
deterministic scenario descriptors and their governor requests; the orchestrator
owns the admission and the append.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core.chrono import Instant, Interval
from qmf.core.exact import ExactRational, Money
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.performance import PerformanceMeasure, UndefinedMeasure

from qmb._refuse import clean_token, invalid, policy
from qmb.config.compiler import PROVENANCE_PROCEDURE_EPHEMERAL
from qmb.ledger.line import ROLE_REPLICATE
from qmb.orchestrator.governor import ON_FULL_ENQUEUE, GovernedRequest
from qmb.results.charts import HistogramReadyArray
from qmb.results.measures import (
    MEASURE_IDENTITIES,
    ClosedTrade,
    assemble_v1_measure_set,
)
from qmb.robustness.contract import (
    PROCEDURE_MC_TRADE_SHUFFLE,
    THRESHOLDS_DEFERRED_TO,
    require_positive_int,
)
from qmb.robustness.summary import (
    DIRECTION_HIGHER_IS_BETTER,
    DIRECTION_LOWER_IS_BETTER,
    DistributionSummary,
    summarize_distribution,
)

__all__ = [
    "EXCLUDED_METRIC_ALL_SCENARIOS_UNDEFINED",
    "EXCLUDED_METRIC_OBSERVED_UNDEFINED",
    "FANOUT_DAEMON",
    "FANOUT_DOCKER",
    "FANOUT_GOVERNOR_BOUND",
    "FANOUT_ON_FULL",
    "FANOUT_RAY",
    "MC_1000_BASELINE",
    "MC_1000_IS_BAKED_DEFAULT",
    "METRIC_LOWER_IS_BETTER",
    "METRIC_SCENARIO_DISTRIBUTION_CLASS",
    "ONE_LEDGER_LINE_PER_SCENARIO",
    "RNG_FAMILY",
    "SCENARIO_COUNT_KEY",
    "SCENARIO_IS_CANCELLABLE",
    "SCENARIO_RUN_ROLE",
    "SCENARIO_WRITES_BAR_VERDICT",
    "SEED_DERIVATION_RULE",
    "SHUFFLE_CANONICAL_PAYLOAD",
    "SHUFFLE_EMITS_IMAGE_PAYLOAD",
    "SHUFFLE_EMITS_VERDICT",
    "SHUFFLE_MINTS_SYNTHETIC_SERIES",
    "SHUFFLE_MODE",
    "SHUFFLE_PERSISTS_SYNTHETIC_SERIES",
    "SHUFFLE_PROVENANCE_CLASS",
    "SHUFFLE_PROVENANCE_KIND",
    "SHUFFLE_RESULT_CLASS",
    "SHUFFLE_RESULT_FORMAT_VERSION",
    "SHUFFLE_SCENARIO_CLASS",
    "SHUFFLE_VERDICT_DEFERRED_TO",
    "TRADE_SHUFFLE_PROCEDURE",
    "ExcludedMetric",
    "MetricScenarioDistribution",
    "ShuffleProvenance",
    "ShuffleScenario",
    "TradeShuffleResult",
    "governed_scenario_requests",
    "metric_direction",
    "refuse_scenario_bar_verdict",
    "run_trade_shuffle",
    "scenario_seed",
    "shuffle_identity",
    "shuffle_scenarios",
]

# The B-14 rung this module realizes and the sequence-risk mode it runs in.
TRADE_SHUFFLE_PROCEDURE: Final[str] = PROCEDURE_MC_TRADE_SHUFFLE
SHUFFLE_MODE: Final[str] = "sequence-risk"

SHUFFLE_RESULT_CLASS: Final[str] = "qmb-trade-shuffle-result"
SHUFFLE_RESULT_FORMAT_VERSION: Final[int] = 1
SHUFFLE_PROVENANCE_CLASS: Final[str] = "qmb-trade-shuffle-provenance"
METRIC_SCENARIO_DISTRIBUTION_CLASS: Final[str] = "qmb-trade-shuffle-metric-distribution"
SHUFFLE_SCENARIO_CLASS: Final[str] = "qmb-trade-shuffle-scenario"
_EXCLUDED_METRIC_CLASS: Final[str] = "qmb-trade-shuffle-excluded-metric"

# The RNG family and its per-scenario seed-derivation rule (AR-59, AC2). A fresh
# Mersenne-Twister generator is seeded deterministically per scenario; there is no
# module-global RNG and no reliance on Python's hash randomization.
RNG_FAMILY: Final[str] = "python-stdlib-random-mt19937"
SEED_DERIVATION_RULE: Final[str] = "base_seed + scenario_index"

# The scenario count is a UI-editable configurable with NO ratified value (SC-07,
# AC4). The MC-1000 baseline is a deferred battery candidate, never baked as default.
SCENARIO_COUNT_KEY: Final[str] = "qmb_mc_trade_shuffle_scenarios"
MC_1000_BASELINE: Final[int] = 1000
MC_1000_IS_BAKED_DEFAULT: Final[bool] = False

# Procedure-ephemeral discipline (B-7, AC1): the shuffle re-accumulates realised
# trades and never mints or persists a synthetic market series, so the run stays
# world=replay and its provenance is procedure-ephemeral.
SHUFFLE_MINTS_SYNTHETIC_SERIES: Final[bool] = False
SHUFFLE_PERSISTS_SYNTHETIC_SERIES: Final[bool] = False
SHUFFLE_PROVENANCE_KIND: Final[str] = PROVENANCE_PROCEDURE_EPHEMERAL

# The summary is chart series as data, never images, and emits no verdict (AC3).
SHUFFLE_CANONICAL_PAYLOAD: Final[str] = "series-data"
SHUFFLE_EMITS_IMAGE_PAYLOAD: Final[bool] = False
SHUFFLE_EMITS_VERDICT: Final[bool] = False
SHUFFLE_VERDICT_DEFERRED_TO: Final[str] = THRESHOLDS_DEFERRED_TO

# The B-5 fan-out contract (AR-50, AR-51, AC5): scenarios fan out under the
# orchestrator's process-per-run governor bounded by min(cpu, memory) with
# enqueue-when-full — no Ray, no daemon, no required Docker — each governed scenario
# is cancellable, and the orchestrator appends exactly one role=replicate ledger line
# per scenario and never a bar verdict.
SCENARIO_RUN_ROLE: Final[str] = ROLE_REPLICATE
FANOUT_GOVERNOR_BOUND: Final[str] = "min-cpu-memory"
FANOUT_ON_FULL: Final[str] = ON_FULL_ENQUEUE
FANOUT_RAY: Final[str] = "absent"
FANOUT_DAEMON: Final[str] = "not-required"
FANOUT_DOCKER: Final[str] = "not-required"
SCENARIO_IS_CANCELLABLE: Final[bool] = True
ONE_LEDGER_LINE_PER_SCENARIO: Final[bool] = True
SCENARIO_WRITES_BAR_VERDICT: Final[bool] = False

# Metrics whose favourable pole is the LOW side: max drawdown (AC3), its recovery
# duration, and the longest losing streak are all path-dependent and lower-is-better.
# Every other selectable measure_identity is higher-is-better.
METRIC_LOWER_IS_BETTER: Final[frozenset[str]] = frozenset(
    {"max_drawdown", "max_drawdown_recovery", "losing_streak"}
)

# Reasons a selected metric is set aside rather than summarised (never coerced to a
# zero magnitude, AD-11): its original-result value is undefined, or every scenario's
# value came back undefined.
EXCLUDED_METRIC_OBSERVED_UNDEFINED: Final[str] = "observed-undefined"
EXCLUDED_METRIC_ALL_SCENARIOS_UNDEFINED: Final[str] = "all-scenarios-undefined"

_MeasureSlot = PerformanceMeasure | UndefinedMeasure
_Quantity = ExactRational | Money


def metric_direction(identity: object) -> str:
    """The favourable direction of one measure identity (AC3).

    ``max_drawdown``, ``max_drawdown_recovery``, and ``losing_streak`` are
    lower-is-better; every other measure identity is higher-is-better. The direction
    steers the summary's one-tailed p-value and the direction-aware percentile rank.
    """
    token = clean_token(identity)
    if token is not None and token in METRIC_LOWER_IS_BETTER:
        return DIRECTION_LOWER_IS_BETTER
    return DIRECTION_HIGHER_IS_BETTER


def scenario_seed(base_seed: object, scenario_index: object) -> Result[int]:
    """Derive scenario ``s``'s seed as ``base_seed + scenario_index`` (AR-59, AC2).

    Both inputs are non-negative exact integers; the derivation is the plain sum, so
    two runs of the same base seed and scenario index shuffle identically.
    """
    base = _non_negative_int(base_seed, "base_seed")
    if is_refusal(base):
        return base
    index = _non_negative_int(scenario_index, "scenario_index")
    if is_refusal(index):
        return index
    return Ok(base.value + index.value)


# --- scenario descriptors and the governed fan-out (AC5) ---------------------


@dataclass(frozen=True, slots=True)
class ShuffleScenario:
    """One Monte Carlo scenario: its index, derived seed, and replicate run id (AC2, AC5).

    ``role`` is always ``replicate`` — a scenario is a governed replicate run, never a
    confirmation or a bar-verdict run. ``run_id`` is the deterministic fingerprint the
    governor admits and the orchestrator ledgers exactly once.
    """

    scenario_index: int
    seed: int
    run_id: Fingerprint
    role: str = ROLE_REPLICATE

    def fp1_identity(self) -> dict[str, object]:
        """Canonical scenario identity content. Package SemVer is omitted."""
        return {
            "class": SHUFFLE_SCENARIO_CLASS,
            "role": self.role,
            "run_id": self.run_id.value,
            "scenario_index": self.scenario_index,
            "seed": self.seed,
        }


def shuffle_scenarios(
    base_seed: object,
    scenario_count: object,
    *,
    run_root: object = None,
) -> Result[tuple[ShuffleScenario, ...]]:
    """Build the deterministic scenario descriptors of one trade-shuffle run (AC2, AC5).

    ``scenario_count`` scenarios are numbered ``0..count-1``; scenario ``s`` carries
    seed ``base_seed + s`` and a run id fingerprinted from the procedure, base seed,
    scenario index, and the optional ``run_root`` (the parent run's id) so replicate
    ids never collide across parent runs. Each descriptor is ``role = replicate``.
    """
    base = _non_negative_int(base_seed, "base_seed")
    if is_refusal(base):
        return base
    count = _positive_int(scenario_count, "scenario_count")
    if is_refusal(count):
        return count
    root = _optional_run_root(run_root)
    if is_refusal(root):
        return root
    scenarios: list[ShuffleScenario] = []
    for index in range(count.value):
        seed = base.value + index
        stamped = fingerprint(
            {
                "base_seed": base.value,
                "class": SHUFFLE_SCENARIO_CLASS,
                "procedure": TRADE_SHUFFLE_PROCEDURE,
                "role": ROLE_REPLICATE,
                "run_root": root.value,
                "scenario_index": index,
                "seed": seed,
            }
        )
        if is_refusal(stamped):
            return stamped
        scenarios.append(ShuffleScenario(scenario_index=index, seed=seed, run_id=stamped.value))
    return Ok(tuple(scenarios))


def governed_scenario_requests(
    scenarios: object,
    *,
    projected_peak_memory: object,
    cpu_cost: object = 1,
) -> Result[tuple[GovernedRequest, ...]]:
    """Build the governor requests for a scenario fan-out (B-5, AR-50, AC5).

    Each :class:`ShuffleScenario` becomes one :class:`~qmb.orchestrator.governor.GovernedRequest`
    the orchestrator submits to its ``min(cpu, memory)`` resource governor: admitted
    when it fits, enqueued when full (enqueue-on-full), never silently oversubscribed.
    Process fan-out belongs to the orchestrator — no Ray, no daemon, no required
    Docker — and each governed scenario ledgers exactly one ``role = replicate`` line.
    """
    parsed = _coerce_scenarios(scenarios)
    if is_refusal(parsed):
        return parsed
    requests: list[GovernedRequest] = []
    for scenario in parsed.value:
        built = GovernedRequest.try_create(scenario.run_id, projected_peak_memory, cpu_cost)
        if is_refusal(built):
            return built
        requests.append(built.value)
    return Ok(tuple(requests))


def refuse_scenario_bar_verdict(name: object) -> Result[None]:
    """Refuse reading a bar verdict out of a replicate scenario line (AR-51, AC5).

    A governed scenario appends exactly one ``role = replicate`` ledger line carrying
    raw measures — never a Book-bar pass/fail. Any attempt to read a bar verdict out
    of it is a ``policy rejection`` (B-4, AR-51).
    """
    token = clean_token(name)
    if token is None:
        return invalid(
            "verdict",
            "a verdict name is required to refuse it",
            given=repr(name),
        )
    return policy(
        "verdict",
        "a trade-shuffle scenario is a role=replicate run appending one ledger line of "
        "raw measures; it never writes a Book-bar pass/fail verdict (B-4, AR-51)",
        verdict=token,
        role=SCENARIO_RUN_ROLE,
        writes_bar_verdict=SCENARIO_WRITES_BAR_VERDICT,
    )


# --- the RNG / data-window provenance record (AC2) ---------------------------


@dataclass(frozen=True, slots=True)
class ShuffleProvenance:
    """The RNG and data-window provenance every trade-shuffle result records (AR-59, AC2).

    Carries the RNG family, the base seed, the seed-derivation rule, the scenario
    count, and the data-window UTC-ns bounds. This is the ``rng_provenance`` the CT-32
    label folds in for a stochastic run (B-13).
    """

    rng_family: str
    base_seed: int
    seed_derivation_rule: str
    scenario_count: int
    data_window_start_ns: int
    data_window_end_ns: int

    def fp1_identity(self) -> dict[str, object]:
        """Canonical provenance identity content."""
        return {
            "base_seed": self.base_seed,
            "class": SHUFFLE_PROVENANCE_CLASS,
            "data_window_end_ns": self.data_window_end_ns,
            "data_window_start_ns": self.data_window_start_ns,
            "rng_family": self.rng_family,
            "scenario_count": self.scenario_count,
            "seed_derivation_rule": self.seed_derivation_rule,
        }


# --- per-metric scenario distribution (AC3) ----------------------------------


@dataclass(frozen=True, slots=True)
class MetricScenarioDistribution:
    """One selected metric summarised across the scenarios, as data (AC3).

    ``summary`` is the Story 22.1 distribution primitive — percentile ranks,
    confidence bands, and a direction-aware one-tailed p-value — over the scenario
    magnitudes against the original result. ``observed_favorable_rank`` is the
    direction-aware empirical percentile rank of the original result (its favourable
    fraction: how many scenarios it beats, low-side for drawdown). ``distribution`` is
    a histogram-ready array of scenario values — chart series as data, never an image,
    AD-10-excluded from identity. No pass/fail verdict is emitted.
    """

    metric_identity: str
    direction: str
    unit_kind: str
    scenario_count: int
    excluded_scenario_count: int
    summary: DistributionSummary
    observed_favorable_rank_num: int
    observed_favorable_rank_den: int
    distribution: HistogramReadyArray

    @property
    def observed_favorable_rank(self) -> Fraction:
        """The direction-aware empirical percentile rank of the original result (0..1)."""
        return Fraction(self.observed_favorable_rank_num, self.observed_favorable_rank_den)

    @property
    def emits_verdict(self) -> bool:
        """Always ``False`` — the metric distribution is pure data (AC3)."""
        return SHUFFLE_EMITS_VERDICT

    def chart_series(self) -> dict[str, object]:
        """The scenario distribution as machine-readable chart series (never an image)."""
        return self.distribution.as_data()

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The histogram array is display-only, excluded."""
        return {
            "canonical_payload": SHUFFLE_CANONICAL_PAYLOAD,
            "class": METRIC_SCENARIO_DISTRIBUTION_CLASS,
            "direction": self.direction,
            "emits_image_payload": SHUFFLE_EMITS_IMAGE_PAYLOAD,
            "emits_verdict": SHUFFLE_EMITS_VERDICT,
            "excluded_scenario_count": self.excluded_scenario_count,
            "metric_identity": self.metric_identity,
            "observed_favorable_rank_den": self.observed_favorable_rank_den,
            "observed_favorable_rank_num": self.observed_favorable_rank_num,
            "scenario_count": self.scenario_count,
            "summary": self.summary.fp1_identity(),
            "unit_kind": self.unit_kind,
        }


@dataclass(frozen=True, slots=True)
class ExcludedMetric:
    """A selected metric set aside rather than summarised, never coerced to zero (AD-11)."""

    metric_identity: str
    reason: str

    def fp1_identity(self) -> dict[str, object]:
        """Canonical excluded-metric identity content."""
        return {
            "class": _EXCLUDED_METRIC_CLASS,
            "metric_identity": self.metric_identity,
            "reason": self.reason,
        }


# --- the result (AC1, AC2, AC3) ----------------------------------------------


@dataclass(frozen=True, slots=True)
class TradeShuffleResult:
    """The Monte Carlo trade-shuffle result of one completed replay run (AC1, AC2, AC3).

    ``provenance`` records the RNG family, base seed, seed rule, scenario count, and
    data-window bounds; ``metrics`` carries each selected metric summarised across the
    scenarios; ``excluded_metrics`` names any metric set aside. The whole object is
    procedure-ephemeral (it minted no synthetic series), stays ``world = replay``, and
    is a pure deterministic function of its inputs — :meth:`fingerprint` reproduces
    bit-for-bit (AC2). It makes no edge claim and emits no verdict.
    """

    procedure: str
    mode: str
    world: str
    base_seed: int
    provenance: ShuffleProvenance
    metrics: tuple[MetricScenarioDistribution, ...]
    excluded_metrics: tuple[ExcludedMetric, ...]

    @property
    def emits_verdict(self) -> bool:
        """Always ``False`` — the result is pure data, never a verdict (AC3)."""
        return SHUFFLE_EMITS_VERDICT

    @property
    def mints_synthetic_series(self) -> bool:
        """Always ``False`` — the procedure is ephemeral, minting no market series (AC1)."""
        return SHUFFLE_MINTS_SYNTHETIC_SERIES

    def metric_named(self, identity: str) -> MetricScenarioDistribution | None:
        """The summarised distribution for ``identity``, or ``None`` if excluded."""
        for metric in self.metrics:
            if metric.metric_identity == identity:
                return metric
        return None

    def rng_provenance(self) -> dict[str, object]:
        """The ``rng_provenance`` stamp the CT-32 label folds in (B-13, AR-59)."""
        return self.provenance.fp1_identity()

    def result_label(self) -> dict[str, object]:
        """The procedure identity plus seed that enter the result label (B-7, AC1)."""
        return {
            "base_seed": self.base_seed,
            "class": SHUFFLE_RESULT_CLASS,
            "mints_synthetic_series": SHUFFLE_MINTS_SYNTHETIC_SERIES,
            "mode": self.mode,
            "procedure": self.procedure,
            "provenance_kind": SHUFFLE_PROVENANCE_KIND,
            "rng_family": self.provenance.rng_family,
            "world": self.world,
        }

    def chart_series(self) -> tuple[dict[str, object], ...]:
        """Every metric's scenario distribution as chart series data (never images, AC3)."""
        return tuple(metric.chart_series() for metric in self.metrics)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Deterministic and reproducible (AC2, NFR-03)."""
        return {
            "base_seed": self.base_seed,
            "canonical_payload": SHUFFLE_CANONICAL_PAYLOAD,
            "class": SHUFFLE_RESULT_CLASS,
            "emits_image_payload": SHUFFLE_EMITS_IMAGE_PAYLOAD,
            "emits_verdict": SHUFFLE_EMITS_VERDICT,
            "excluded_metrics": [item.fp1_identity() for item in self.excluded_metrics],
            "format_version": SHUFFLE_RESULT_FORMAT_VERSION,
            "metrics": [item.fp1_identity() for item in self.metrics],
            "mints_synthetic_series": SHUFFLE_MINTS_SYNTHETIC_SERIES,
            "mode": self.mode,
            "procedure": self.procedure,
            "provenance": self.provenance.fp1_identity(),
            "world": self.world,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. The same inputs reproduce it bit-for-bit (AC2)."""
        return fingerprint(self.fp1_identity())


def run_trade_shuffle(
    *,
    trades: object,
    starting_capital: object,
    period: object,
    base_seed: object,
    metrics: object,
    config: object = None,
    scenario_count: object = None,
    band_probabilities: object = (),
) -> Result[TradeShuffleResult]:
    """Run the Monte Carlo trade-shuffle over a completed replay run (AC1-AC4).

    ``trades`` is the run's CT-29 realised-trade stream (its :class:`ClosedTrade`
    values); ``starting_capital`` is the virtual-ledger seed; ``period`` is the
    data-window Interval. The scenario count is the operator-supplied UI-editable
    configurable resolved from ``config`` (its ``qmb_mc_trade_shuffle_scenarios`` key)
    or passed explicitly — there is no ratified value and the MC-1000 baseline is not
    baked. Each scenario permutes the realised P&Ls over the same close timeline with
    a ``base_seed + scenario_index`` seeded generator, re-accumulates the equity path
    in exact integer money, and the selected metrics are summarised across scenarios
    against the original result with the Story 22.1 primitive. No synthetic market
    series is minted; the run stays ``world = replay`` (B-7). No verdict is emitted.
    """
    resolved_count = _resolve_scenario_count(config, scenario_count)
    if is_refusal(resolved_count):
        return resolved_count
    base = _non_negative_int(base_seed, "base_seed")
    if is_refusal(base):
        return base
    if not isinstance(starting_capital, Money):
        return invalid(
            "starting_capital",
            "the virtual-ledger seed is exact Money, never a float (AD-7, B-3)",
            given=repr(type(starting_capital).__name__),
        )
    if not isinstance(period, Interval):
        return invalid(
            "period",
            "the data window is an AD-8 Interval; its UTC-ns bounds enter the result",
            given=repr(type(period).__name__),
        )
    selected = _coerce_metrics(metrics)
    if is_refusal(selected):
        return selected
    parsed_trades = _coerce_trades(trades)
    if is_refusal(parsed_trades):
        return parsed_trades
    realised = parsed_trades.value
    if not realised:
        return invalid(
            "trades",
            "trade-shuffle re-orders a completed run's realised trades; an empty trade "
            "record has no sequence to shuffle (AC1)",
        )
    bands = _coerce_bands(band_probabilities)
    if is_refusal(bands):
        return bands
    timeline = tuple(sorted((trade.closed_at for trade in realised), key=lambda i: i.value_ns))
    atoms = tuple((trade.realized_pnl, trade.fees, trade.side) for trade in realised)
    observed = assemble_v1_measure_set(
        starting_capital=starting_capital, period=period, trades=realised
    )
    if is_refusal(observed):
        return observed
    observed_slots = _slots_by_identity(observed.value)
    scenario_values = _accumulate_scenarios(
        atoms=atoms,
        timeline=timeline,
        starting_capital=starting_capital,
        period=period,
        base_seed=base.value,
        scenario_count=resolved_count.value,
        metrics=selected.value,
    )
    if is_refusal(scenario_values):
        return scenario_values
    per_metric: list[MetricScenarioDistribution] = []
    excluded: list[ExcludedMetric] = []
    for metric in selected.value:
        summarised = _summarise_metric(
            metric=metric,
            observed_slot=observed_slots.get(metric),
            scenario_quantities=scenario_values.value[metric],
            scenario_count=resolved_count.value,
            band_probabilities=bands.value,
        )
        if is_refusal(summarised):
            return summarised
        built, excluded_metric = summarised.value
        if built is not None:
            per_metric.append(built)
        if excluded_metric is not None:
            excluded.append(excluded_metric)
    provenance = ShuffleProvenance(
        rng_family=RNG_FAMILY,
        base_seed=base.value,
        seed_derivation_rule=SEED_DERIVATION_RULE,
        scenario_count=resolved_count.value,
        data_window_start_ns=period.start.value_ns,
        data_window_end_ns=period.end.value_ns,
    )
    return Ok(
        TradeShuffleResult(
            procedure=TRADE_SHUFFLE_PROCEDURE,
            mode=SHUFFLE_MODE,
            world=World.REPLAY.value,
            base_seed=base.value,
            provenance=provenance,
            metrics=tuple(per_metric),
            excluded_metrics=tuple(excluded),
        )
    )


def shuffle_identity() -> dict[str, object]:
    """Identity-bearing trade-shuffle-procedure fields. Package SemVer is omitted."""
    return {
        "canonical_payload": SHUFFLE_CANONICAL_PAYLOAD,
        "class": SHUFFLE_RESULT_CLASS,
        "emits_image_payload": SHUFFLE_EMITS_IMAGE_PAYLOAD,
        "emits_verdict": SHUFFLE_EMITS_VERDICT,
        "fanout_bound": FANOUT_GOVERNOR_BOUND,
        "fanout_daemon": FANOUT_DAEMON,
        "fanout_docker": FANOUT_DOCKER,
        "fanout_on_full": FANOUT_ON_FULL,
        "fanout_ray": FANOUT_RAY,
        "format_version": SHUFFLE_RESULT_FORMAT_VERSION,
        "mc_1000_is_baked_default": MC_1000_IS_BAKED_DEFAULT,
        "mints_synthetic_series": SHUFFLE_MINTS_SYNTHETIC_SERIES,
        "mode": SHUFFLE_MODE,
        "procedure": TRADE_SHUFFLE_PROCEDURE,
        "provenance_kind": SHUFFLE_PROVENANCE_KIND,
        "rng_family": RNG_FAMILY,
        "scenario_count_key": SCENARIO_COUNT_KEY,
        "scenario_run_role": SCENARIO_RUN_ROLE,
        "scenario_writes_bar_verdict": SCENARIO_WRITES_BAR_VERDICT,
        "seed_derivation_rule": SEED_DERIVATION_RULE,
        "verdict_deferred_to": SHUFFLE_VERDICT_DEFERRED_TO,
    }


# --- scenario accumulation (exact integer money) -----------------------------


def _accumulate_scenarios(
    *,
    atoms: tuple[tuple[Money, Money, object], ...],
    timeline: tuple[Instant, ...],
    starting_capital: Money,
    period: Interval,
    base_seed: int,
    scenario_count: int,
    metrics: tuple[str, ...],
) -> Result[dict[str, list[_Quantity]]]:
    """Re-order the realised P&Ls N times and collect each selected metric per scenario.

    Scenario ``s`` shuffles the atom-to-timeline assignment with a fresh
    ``random.Random(base_seed + s)`` and re-accumulates the equity path (exact integer
    money) by assembling the V1 measure set over the shuffled trades — Python's stable
    sort preserves the shuffled slot order for tied close instants. An undefined metric
    in a scenario is set aside (counted), never coerced to a zero magnitude (AD-11).
    """
    collected: dict[str, list[_Quantity]] = {metric: [] for metric in metrics}
    count = len(atoms)
    for index in range(scenario_count):
        order = list(range(count))
        # A seeded MT19937 generator, one fresh instance per scenario, for a
        # reproducible sequence-risk shuffle — never a cryptographic use (AR-59, AC2).
        random.Random(base_seed + index).shuffle(order)  # noqa: S311
        shuffled: list[ClosedTrade] = []
        for slot, source in enumerate(order):
            realized_pnl, fees, side = atoms[source]
            built = ClosedTrade.try_create(realized_pnl, fees, side, timeline[slot])
            if is_refusal(built):
                return built
            shuffled.append(built.value)
        measures = assemble_v1_measure_set(
            starting_capital=starting_capital, period=period, trades=tuple(shuffled)
        )
        if is_refusal(measures):
            return measures
        slots = _slots_by_identity(measures.value)
        for metric in metrics:
            slot_value = slots.get(metric)
            if isinstance(slot_value, PerformanceMeasure):
                collected[metric].append(slot_value.quantity)
    return Ok(collected)


def _summarise_metric(
    *,
    metric: str,
    observed_slot: _MeasureSlot | None,
    scenario_quantities: list[_Quantity],
    scenario_count: int,
    band_probabilities: tuple[Fraction, ...],
) -> Result[tuple[MetricScenarioDistribution | None, ExcludedMetric | None]]:
    """Summarise one metric across the scenarios against the original result (AC3)."""
    if not isinstance(observed_slot, PerformanceMeasure):
        return Ok((None, ExcludedMetric(metric, EXCLUDED_METRIC_OBSERVED_UNDEFINED)))
    if not scenario_quantities:
        return Ok((None, ExcludedMetric(metric, EXCLUDED_METRIC_ALL_SCENARIOS_UNDEFINED)))
    direction = metric_direction(metric)
    observed = observed_slot.quantity
    summary = summarize_distribution(
        scenario_quantities,
        observed,
        direction,
        band_probabilities=band_probabilities,
    )
    if is_refusal(summary):
        return summary
    favorable = _favorable_rank(summary.value.percentile_rank, direction)
    distribution = HistogramReadyArray(
        name=f"{metric}_scenario_distribution",
        unit_kind=observed.unit_kind,
        values=tuple(scenario_quantities),
    )
    built = MetricScenarioDistribution(
        metric_identity=metric,
        direction=direction,
        unit_kind=observed.unit_kind.value,
        scenario_count=scenario_count,
        excluded_scenario_count=scenario_count - len(scenario_quantities),
        summary=summary.value,
        observed_favorable_rank_num=favorable.numerator,
        observed_favorable_rank_den=favorable.denominator,
        distribution=distribution,
    )
    return Ok((built, None))


def _favorable_rank(percentile_rank: Fraction, direction: str) -> Fraction:
    """The direction-aware empirical percentile rank of the original result (AC3).

    ``percentile_rank`` is the fraction of the distribution below the observed value.
    Higher-is-better favours a high rank as-is; lower-is-better favours the low side,
    so the favourable fraction is its complement.
    """
    if direction == DIRECTION_LOWER_IS_BETTER:
        return Fraction(1) - percentile_rank
    return percentile_rank


def _slots_by_identity(measures: tuple[_MeasureSlot, ...]) -> dict[str, _MeasureSlot]:
    return {slot.measure_identity: slot for slot in measures}


# --- coercion helpers --------------------------------------------------------


def _resolve_scenario_count(config: object, scenario_count: object) -> Result[int]:
    """Resolve the operator-supplied scenario count (AC4).

    Preferred from the resolved run-config's ``qmb_mc_trade_shuffle_scenarios`` key;
    an explicit ``scenario_count`` is accepted for a direct call. Neither supplied is
    a typed refusal — there is no ratified value and no baked MC-1000 default.
    """
    if config is not None:
        return require_positive_int(config, SCENARIO_COUNT_KEY)
    if scenario_count is not None:
        return _positive_int(scenario_count, SCENARIO_COUNT_KEY)
    return invalid(
        "scenario_count",
        "the scenario count is a UI-editable configurable with no ratified value; supply "
        "it via the resolved run-config's qmb_mc_trade_shuffle_scenarios key or explicitly — "
        "the MC-1000 baseline is a deferred battery candidate, never a baked default (SC-07)",
        scenario_count_key=SCENARIO_COUNT_KEY,
        mc_1000_is_baked_default=MC_1000_IS_BAKED_DEFAULT,
    )


def _coerce_metrics(value: object) -> Result[tuple[str, ...]]:
    if isinstance(value, str):
        candidates: Sequence[object] = (value,)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        candidates = cast("Sequence[object]", value)
    else:
        return invalid(
            "metrics",
            "the selected metrics are a measure_identity or a sequence of them",
            given=repr(type(value).__name__),
        )
    if not candidates:
        return invalid(
            "metrics",
            "at least one metric is selected to summarise across the scenarios (AC3)",
        )
    out: list[str] = []
    for index, item in enumerate(candidates):
        token = clean_token(item)
        if token is None or token not in MEASURE_IDENTITIES:
            return invalid(
                "metrics",
                "each selected metric is a measure_identity from the V1 core measure set",
                index=index,
                given=repr(item),
                allowed=list(MEASURE_IDENTITIES),
            )
        if token not in out:
            out.append(token)
    return Ok(tuple(out))


def _coerce_trades(value: object) -> Result[tuple[ClosedTrade, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, ClosedTrade):
        return Ok((value,))
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "trades",
            "the realised-trade record is the run's CT-29 stream of ClosedTrade values",
            given=repr(type(value).__name__),
        )
    out: list[ClosedTrade] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if isinstance(item, ClosedTrade):
            out.append(item)
            continue
        if not isinstance(item, Mapping):
            return invalid(
                "trades",
                "every realised trade is a ClosedTrade or a mapping of realized_pnl, "
                "fees, side, closed_at",
                index=index,
                given=repr(type(item).__name__),
            )
        body = cast("Mapping[str, object]", item)
        minted = ClosedTrade.try_create(
            body.get("realized_pnl"),
            body.get("fees"),
            body.get("side"),
            body.get("closed_at"),
        )
        if is_refusal(minted):
            return minted
        out.append(minted.value)
    return Ok(tuple(out))


def _coerce_bands(value: object) -> Result[tuple[Fraction, ...]]:
    """Coerce caller-supplied confidence-band probabilities (exact, no default alpha)."""
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "band_probabilities",
            "confidence-band probabilities are an ordered sequence; the summary invents "
            "no alpha level (SC-07)",
            given=repr(type(value).__name__),
        )
    out: list[Fraction] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if isinstance(item, (bool, float)):
            return invalid(
                "band_probabilities",
                "a confidence-band probability is an exact number, never a boolean or a "
                "binary float (AD-7)",
                index=index,
                given=repr(item),
            )
        if isinstance(item, Fraction):
            out.append(item)
        elif isinstance(item, int):
            out.append(Fraction(item))
        elif isinstance(item, ExactRational):
            out.append(item.as_fraction())
        else:
            return invalid(
                "band_probabilities",
                "a confidence-band probability is an int, Fraction, or ExactRational",
                index=index,
                given=repr(type(item).__name__),
            )
    return Ok(tuple(out))


def _coerce_scenarios(value: object) -> Result[tuple[ShuffleScenario, ...]]:
    if isinstance(value, ShuffleScenario):
        return Ok((value,))
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "scenarios",
            "the fan-out reads a sequence of ShuffleScenario descriptors",
            given=repr(type(value).__name__),
        )
    out: list[ShuffleScenario] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, ShuffleScenario):
            return invalid(
                "scenarios",
                "each scenario is a ShuffleScenario built by shuffle_scenarios",
                index=index,
                given=repr(type(item).__name__),
            )
        out.append(item)
    if not out:
        return invalid("scenarios", "a scenario fan-out has at least one scenario")
    return Ok(tuple(out))


def _optional_run_root(value: object) -> Result[str]:
    if value is None:
        return Ok("")
    if isinstance(value, Fingerprint):
        return Ok(value.value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "run_root",
            "the parent run root is a Fingerprint or its fp1 token",
            given=repr(value),
        )
    return Ok(token)


def _non_negative_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, "a non-negative exact integer is required", given=repr(value))
    return Ok(value)


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, "a positive exact integer is required", given=repr(value))
    return Ok(value)
