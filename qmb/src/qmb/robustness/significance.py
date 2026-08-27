"""The pre-build rule-significance gate — the signal-only edge test (Story 22.4).

The third ladder procedure (22.4) tests whether a bare entry rule has an edge
**before** a full strategy build commits compute. It is an advisory, evidence-based
pre-filter: it rejects noise-indistinguishable rules, and it never auto-merges and
never gates live money.

What the procedure is:

* a **signal-only pass over the B-2 event-slice loop with orders disabled** (AC1):
  :func:`run_significance_gate` runs the very same event-slice loop, the same pinned
  :data:`~qmb.runloop.loop.SUBPHASES` order, with trading locked exactly as in
  warm-up, so the strategy stays permanently flat and the raw entry signal is
  isolated from exit and position-management logic. Minting an entry, an exit, or a
  command during the pass is a typed ``policy rejection`` (:func:`refuse_signal_pass_act`);
* **look-ahead-safe log returns** (AC2; SC-06): the signal at bar ``t`` is scored
  against the NEXT bar's return — ``ln(close[t+1] / close[t])`` — the first return not
  knowable at signal time, so no forming-bar or future information enters the
  statistic. Close prices are exact :class:`~qmf.core.exact.Price` integers; they
  cross into the bounded return-space float carve-out only via the named AD-22
  conversion from Story 22.1 (:func:`~qmb.robustness.carveout.carve_return_statistic`),
  so no binary float is ever stored and identity is reproducible;
* a **detrended zero-edge null** (AC3): the returns are detrended by their in-sample
  mean AND the rule-return series is re-centred to zero before resampling
  (``H0: E[return] = 0``). The reported statistic is the empirical one-tailed p-value
  — the fraction of null resamples whose mean is at or above the observed mean —
  computed by the Story 22.1 distribution primitive;
* **configurable resampling and gate parameters** (AC4; SC-07): the resampling
  scheme is a UI-editable configurable — ``iid``, ``block``, or ``stationary`` — with
  a configurable block length, and the iteration count and minimum-observation floor
  are UI-editable configurables carrying no ratified value. The module ships no
  invented default for any of them; an unset required input is a typed refusal;
* **insufficient-data discipline** (AC5; AR-59; NFR-03): when the observation count
  falls below the configured minimum-observation floor the procedure returns a typed
  refusal rather than a fabricated p-value; where the floor is unset it emits a
  low-confidence warning label instead of a hard number. The result records seed
  provenance (base seed plus per-batch derivation), scheme and parameters, iteration
  count, and data-window UTC-ns bounds, and re-running reproduces the null
  distribution bit-for-bit;
* **advisory only** (AC6; SC-06; B-14; L20): the result world is replay or simulated,
  never live, and the claim class is robustness, never edge. The verdict is advisory
  to the operator — a build pipeline may consult it but it never auto-merges
  (:func:`refuse_gate_auto_merge`) and never gates live money
  (:func:`~qmb.robustness.contract.refuse_live_money_gate`) — and the pass/fail alpha
  thresholds stay deferred to GAP-0049.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.exact import ExactRational, Price, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import clean_token, invalid, policy
from qmb.results.charts import HistogramReadyArray
from qmb.robustness.carveout import carve_return_statistic
from qmb.robustness.contract import (
    CLAIM_CLASS_ROBUSTNESS,
    CLAIM_GATED_BEHIND,
    PROCEDURE_RULE_SIGNIFICANCE,
    require_configurable,
    require_positive_int,
)
from qmb.robustness.shuffle import RNG_FAMILY
from qmb.robustness.summary import (
    DIRECTION_HIGHER_IS_BETTER,
    DistributionSummary,
    summarize_distribution,
)
from qmb.runloop.loop import SUBPHASES, RestingIntent, SliceObservation, run

__all__ = [
    "ALPHA_THRESHOLDS_DEFERRED_TO",
    "GATE_AUTO_MERGES",
    "GATE_GATES_LIVE_MONEY",
    "GATE_IS_ADVISORY",
    "ITERATIONS_KEY",
    "LOW_CONFIDENCE_FLOOR_UNSET_LABEL",
    "MINIMUM_OBSERVATIONS_KEY",
    "NULL_DETRENDED_BY",
    "NULL_HYPOTHESIS",
    "RESAMPLING_SCHEMES",
    "RESAMPLING_SCHEME_KEY",
    "RESULT_WORLD_LIVE",
    "RETURN_ALIGNMENT",
    "RETURN_BASIS",
    "RULE_SIGNIFICANCE_PROCEDURE",
    "SCHEME_BLOCK",
    "SCHEME_IID",
    "SCHEME_STATIONARY",
    "SIGNAL_PASS_ORDERS_ENABLED",
    "SIGNAL_PASS_STRATEGY_STAYS_FLAT",
    "SIGNAL_PASS_TRADING_LOCKED",
    "SIGNIFICANCE_BLOCK_LENGTH_KEY",
    "SIGNIFICANCE_CANONICAL_PAYLOAD",
    "SIGNIFICANCE_CLAIM_CLASS",
    "SIGNIFICANCE_EMITS_IMAGE_PAYLOAD",
    "SIGNIFICANCE_EMITS_VERDICT",
    "SIGNIFICANCE_MAKES_EDGE_CLAIM",
    "SIGNIFICANCE_MODE",
    "SIGNIFICANCE_RESULT_CLASS",
    "SIGNIFICANCE_RESULT_FORMAT_VERSION",
    "SIGNIFICANCE_SEED_DERIVATION_RULE",
    "SIGNIFICANCE_WORLD",
    "NullDistribution",
    "SignalBar",
    "SignalOnlyHandler",
    "SignificanceProvenance",
    "SignificanceResult",
    "guard_signal_pass",
    "next_bar_log_returns",
    "refuse_gate_auto_merge",
    "refuse_live_result_world",
    "refuse_signal_pass_act",
    "run_signal_only_pass",
    "run_significance_gate",
    "significance_identity",
]

# The B-14 rung this module realizes and the signal-only edge-test mode it runs in.
RULE_SIGNIFICANCE_PROCEDURE: Final[str] = PROCEDURE_RULE_SIGNIFICANCE
SIGNIFICANCE_MODE: Final[str] = "signal-only-edge"

SIGNIFICANCE_RESULT_CLASS: Final[str] = "qmb-rule-significance-result"
SIGNIFICANCE_RESULT_FORMAT_VERSION: Final[int] = 1
_SIGNIFICANCE_PROVENANCE_CLASS: Final[str] = "qmb-rule-significance-provenance"
_NULL_DISTRIBUTION_CLASS: Final[str] = "qmb-rule-significance-null-distribution"
_SIGNAL_BAR_CLASS: Final[str] = "qmb-rule-significance-signal-bar"

# The signal-only pass runs the B-2 loop with orders disabled and trading locked
# exactly as in warm-up, so the strategy stays permanently flat (AC1).
SIGNAL_PASS_ORDERS_ENABLED: Final[bool] = False
SIGNAL_PASS_TRADING_LOCKED: Final[bool] = True
SIGNAL_PASS_STRATEGY_STAYS_FLAT: Final[bool] = True

# Look-ahead safety (AC2): the signal at bar t is aligned to the next bar's log
# return, the first return not knowable at signal time.
RETURN_ALIGNMENT: Final[str] = "signal-at-t-scored-on-next-bar-return"
RETURN_BASIS: Final[str] = "log-returns"
_RETURN_LABEL: Final[str] = "next_bar_log_return"

# The zero-edge null hypothesis (AC3): returns detrended by their in-sample mean and
# the rule-return series re-centred to zero before resampling.
NULL_HYPOTHESIS: Final[str] = "E[return]=0"
NULL_DETRENDED_BY: Final[str] = "in-sample-mean"

# The resampling scheme is a UI-editable configurable — iid, block, or stationary
# (AC4). The block length, iteration count, and minimum-observation floor are
# likewise UI-editable configurables with NO ratified value; none ships a default.
SCHEME_IID: Final[str] = "iid"
SCHEME_BLOCK: Final[str] = "block"
SCHEME_STATIONARY: Final[str] = "stationary"
RESAMPLING_SCHEMES: Final[tuple[str, ...]] = (SCHEME_IID, SCHEME_BLOCK, SCHEME_STATIONARY)
_BLOCK_SCHEMES: Final[frozenset[str]] = frozenset({SCHEME_BLOCK, SCHEME_STATIONARY})

RESAMPLING_SCHEME_KEY: Final[str] = "qmb_rule_significance_resampling_scheme"
SIGNIFICANCE_BLOCK_LENGTH_KEY: Final[str] = "qmb_rule_significance_block_length"
ITERATIONS_KEY: Final[str] = "qmb_rule_significance_iterations"
MINIMUM_OBSERVATIONS_KEY: Final[str] = "qmb_rule_significance_minimum_observations"

# The RNG family (shared with the other stochastic rungs) and this rung's per-batch
# seed-derivation rule (AR-59, AC5). A fresh generator is seeded per resample batch;
# there is no module-global RNG.
SIGNIFICANCE_SEED_DERIVATION_RULE: Final[str] = "base_seed + batch_index"

# When the minimum-observation floor is unset the result is labelled low-confidence
# rather than presented as a hard number (AC5).
LOW_CONFIDENCE_FLOOR_UNSET_LABEL: Final[str] = "minimum-observation-floor-unset"

# The result world is replay or simulated, never live; the claim class is robustness,
# never edge; and the gate is advisory — it never auto-merges and never gates live
# money (AC6). The pass/fail alpha thresholds stay deferred to GAP-0049.
SIGNIFICANCE_WORLD: Final[str] = World.REPLAY.value
RESULT_WORLD_LIVE: Final[str] = World.LIVE.value
SIGNIFICANCE_CLAIM_CLASS: Final[str] = CLAIM_CLASS_ROBUSTNESS
SIGNIFICANCE_MAKES_EDGE_CLAIM: Final[bool] = False
GATE_IS_ADVISORY: Final[bool] = True
GATE_AUTO_MERGES: Final[bool] = False
GATE_GATES_LIVE_MONEY: Final[bool] = False
ALPHA_THRESHOLDS_DEFERRED_TO: Final[str] = "GAP-0049"

# The null distribution is chart series as data, never images, and the gate emits no
# pass/fail verdict (AC6).
SIGNIFICANCE_CANONICAL_PAYLOAD: Final[str] = "series-data"
SIGNIFICANCE_EMITS_IMAGE_PAYLOAD: Final[bool] = False
SIGNIFICANCE_EMITS_VERDICT: Final[bool] = False


# --- one bar of the signal-only pass (AC1, AC2) ------------------------------


@dataclass(frozen=True, slots=True)
class SignalBar:
    """One bar of the signal-only pass: instant, close price, raw entry signal (AC1).

    ``close`` is an exact :class:`~qmf.core.exact.Price` integer (never a float);
    ``fired`` is whether the bare entry rule fired at this bar with orders disabled —
    the raw signal, isolated from any exit or position-management logic.
    """

    instant: Instant
    close: Price
    fired: bool

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Package SemVer never enters."""
        return {
            "class": _SIGNAL_BAR_CLASS,
            "close": self.close.fp1_identity(),
            "fired": self.fired,
            "instant_ns": self.instant.value_ns,
        }

    @classmethod
    def try_create(cls, instant: object, close: object, fired: object) -> Result[SignalBar]:
        """Validate one signal bar: an Instant, an exact positive Price, a bool signal."""
        if not isinstance(instant, Instant):
            return invalid(
                "instant",
                "a signal bar is timestamped with an Instant (int64 UTC-ns)",
                given=repr(type(instant).__name__),
            )
        if not isinstance(close, Price):
            return invalid(
                "close",
                "a signal-bar close is an exact Price integer, never a float; it crosses "
                "into the return-space carve-out only via the named AD-22 conversion (AC2)",
                given=repr(type(close).__name__),
            )
        if close.as_fraction() <= 0:
            return invalid(
                "close",
                "a close price is strictly positive so its log return is defined",
                given=str(close.as_fraction()),
            )
        if not isinstance(fired, bool):
            return invalid(
                "fired",
                "the raw entry signal is a bool: whether the bare entry rule fired at this bar",
                given=repr(fired),
            )
        return Ok(cls(instant=instant, close=close, fired=fired))


# --- the signal-only pass over the B-2 loop (AC1) ----------------------------


def refuse_signal_pass_act(action: object) -> TypedRefusal:
    """Minting an entry, an exit, or a command during the signal-only pass (AC1, B-2).

    The gate runs the event-slice loop with orders disabled and trading locked as in
    warm-up, so the strategy stays permanently flat and the raw entry signal is
    isolated from exit and position-management logic. Any attempt to mint an entry, an
    exit, or a command is a typed ``policy rejection`` — returned, never raised.
    """
    token = clean_token(action)
    named = token if token is not None else repr(action)
    return policy(
        "signal_pass",
        "minting an entry, an exit, or a command during the signal-only pass is a typed "
        "policy rejection; orders are disabled and the strategy stays permanently flat, "
        "isolating the raw entry signal from exit and position-management logic (B-2, AC1)",
        action=named,
        mode=SIGNIFICANCE_MODE,
        orders_enabled=SIGNAL_PASS_ORDERS_ENABLED,
    )


def guard_signal_pass(action: object) -> Result[None]:
    """Refuse ``action`` unconditionally during the signal-only pass (permanently flat)."""
    return refuse_signal_pass_act(action)


@dataclass(slots=True)
class SignalOnlyHandler:
    """A B-2 slice handler that records the raw entry signal and mints nothing (AC1).

    Orders are disabled: :meth:`mint_intents` evaluates the entry rule for the bar
    (recording whether it fired) but returns no intent, so the strategy stays
    permanently flat. Resting intents never fill. The handler holds no order or
    position state — the raw entry signal is isolated from exit and position logic.
    """

    fired_by_instant: Mapping[int, bool]
    recorded: dict[int, bool]

    def update_stream(
        self,
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def scheduled_position_event(self, stream_id: str, frontier: Instant) -> Result[None]:
        del stream_id, frontier
        return Ok(None)

    def execute_resting(
        self,
        intent: RestingIntent,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[bool]:
        del intent, observation, frontier
        return Ok(False)

    def update_closed_data(
        self,
        stream_id: str,
        observation: SliceObservation,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        del stream_id
        # Orders disabled: the entry rule is evaluated and its raw signal recorded,
        # but no intent is minted — the strategy stays permanently flat (AC1).
        self.recorded[frontier.value_ns] = bool(self.fired_by_instant.get(frontier.value_ns, False))
        return Ok(())


def run_signal_only_pass(
    signals: object,
    *,
    stream_id: str = "signal-pass",
) -> Result[tuple[SignalBar, ...]]:
    """Run the signal-only pass over the B-2 event-slice loop, orders disabled (AC1).

    One closed event slice per bar is driven through the very same loop, the same
    pinned :data:`~qmb.runloop.loop.SUBPHASES` order, with trading locked for the whole
    window exactly as in warm-up (the embargo covers every observation). The injected
    :class:`SignalOnlyHandler` mints nothing, so the strategy stays permanently flat
    and never fills. Returns the loop-confirmed signal bars in declaration order.
    """
    parsed = _coerce_signals(signals)
    if is_refusal(parsed):
        return parsed
    bars = parsed.value
    fired_by_instant = {bar.instant.value_ns: bar.fired for bar in bars}
    handler = SignalOnlyHandler(fired_by_instant=fired_by_instant, recorded={})
    slices: list[tuple[SliceObservation, ...]] = []
    for bar in bars:
        obs = SliceObservation.try_create(stream_id, bar.instant, True)
        if is_refusal(obs):
            return obs
        slices.append((obs.value,))
    outcome = run(
        slices=tuple(slices),
        stream_set=(stream_id,),
        handler=handler,
        embargo=len(bars),
    )
    if is_refusal(outcome):
        return outcome
    done = outcome.value
    if done.filled:
        return policy(
            "signal_pass",
            "the signal-only pass must stay permanently flat; a fill during the pass is a "
            "policy rejection (orders are disabled, B-2, AC1)",
            filled=list(done.filled),
        )
    if not all(step.is_warming_up for step in done.slices):
        return invalid(
            "signal_pass",
            "the signal-only pass locks trading for the whole window exactly as in warm-up; "
            "an unlocked slice would let the strategy act (AC1)",
        )
    return Ok(bars)


# --- look-ahead-safe next-bar log returns (AC2) ------------------------------


def next_bar_log_returns(signals: object) -> Result[tuple[Fraction, ...]]:
    """The look-ahead-safe next-bar log-return series over the signal bars (AC2).

    Return ``t`` is ``ln(close[t+1] / close[t])`` — the first return not knowable at
    bar ``t``'s signal time, so no forming-bar or future information enters it. Each
    return crosses the bounded return-space float carve-out via the named AD-22
    conversion (:func:`~qmb.robustness.carveout.carve_return_statistic`), so the stored
    value is an exact scaled rational and no binary float enters identity. The series
    is index-aligned to the signal bars ``0..n-2`` (the last bar has no next return).
    """
    parsed = _coerce_signals(signals)
    if is_refusal(parsed):
        return parsed
    bars = parsed.value
    if len(bars) < 2:
        return invalid(
            "signals",
            "a next-bar return needs at least two bars; a one-bar window has no return (AC2)",
            given=len(bars),
        )
    returns: list[Fraction] = []
    for index in range(len(bars) - 1):
        prev_close = bars[index].close.as_fraction()
        next_close = bars[index + 1].close.as_fraction()
        ratio = next_close / prev_close
        # The one float in the whole procedure: log() of an exact price ratio. It
        # re-enters an exact value only through the named AD-22 carve-out (AC2).
        carved = carve_return_statistic(_RETURN_LABEL, math.log(float(ratio)))
        if is_refusal(carved):
            return carved
        returns.append(carved.value.magnitude)
    return Ok(tuple(returns))


# --- the seed / scheme / data-window provenance (AC5) ------------------------


@dataclass(frozen=True, slots=True)
class SignificanceProvenance:
    """The seed, scheme, and data-window provenance the result records (AR-59, AC5).

    Carries the RNG family, base seed, per-batch seed-derivation rule, resampling
    scheme, block length (``None`` for the iid scheme), iteration count, the resolved
    minimum-observation floor (``None`` when unset), and the data-window UTC-ns bounds.
    """

    rng_family: str
    base_seed: int
    seed_derivation_rule: str
    resampling_scheme: str
    block_length: int | None
    iterations: int
    minimum_observations: int | None
    data_window_start_ns: int
    data_window_end_ns: int

    def fp1_identity(self) -> dict[str, object]:
        """Canonical provenance identity content."""
        content: dict[str, object] = {
            "base_seed": self.base_seed,
            "class": _SIGNIFICANCE_PROVENANCE_CLASS,
            "data_window_end_ns": self.data_window_end_ns,
            "data_window_start_ns": self.data_window_start_ns,
            "iterations": self.iterations,
            "resampling_scheme": self.resampling_scheme,
            "rng_family": self.rng_family,
            "seed_derivation_rule": self.seed_derivation_rule,
        }
        if self.block_length is not None:
            content["block_length"] = self.block_length
        if self.minimum_observations is not None:
            content["minimum_observations"] = self.minimum_observations
        return content


# --- the null distribution (AC3) ---------------------------------------------


@dataclass(frozen=True, slots=True)
class NullDistribution:
    """The zero-edge null resample means summarised against the observed mean (AC3).

    ``summary`` is the Story 22.1 distribution primitive over the null resample means
    against the observed mean, higher-is-better — its ``p_value`` is the empirical
    one-tailed fraction of null resamples at or above the observed mean. ``means`` is a
    histogram-ready array of the resample means (chart series as data, never an image,
    AD-10-excluded from identity). ``fingerprint`` is the ``fp1`` over the generation-
    order null means, so a re-run reproduces the null distribution bit-for-bit.
    """

    iterations: int
    observed_mean_num: int
    observed_mean_den: int
    summary: DistributionSummary
    means: HistogramReadyArray
    fingerprint: Fingerprint

    @property
    def observed_mean(self) -> Fraction:
        """The observed rule-return mean the null is described against."""
        return Fraction(self.observed_mean_num, self.observed_mean_den)

    @property
    def p_value(self) -> Fraction:
        """The empirical one-tailed p-value (fraction of null means at or above observed)."""
        return self.summary.p_value

    def chart_series(self) -> dict[str, object]:
        """The null distribution as machine-readable chart series (never an image)."""
        return self.means.as_data()

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The histogram array is display-only, excluded."""
        return {
            "canonical_payload": SIGNIFICANCE_CANONICAL_PAYLOAD,
            "class": _NULL_DISTRIBUTION_CLASS,
            "emits_image_payload": SIGNIFICANCE_EMITS_IMAGE_PAYLOAD,
            "emits_verdict": SIGNIFICANCE_EMITS_VERDICT,
            "iterations": self.iterations,
            "null_fingerprint": self.fingerprint.value,
            "observed_mean_den": self.observed_mean_den,
            "observed_mean_num": self.observed_mean_num,
            "summary": self.summary.fp1_identity(),
        }


# --- the result (AC1-AC6) ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class SignificanceResult:
    """The rule-significance gate result over a signal-only pass (AC1-AC6).

    ``provenance`` records the seed, scheme, parameters, and data-window bounds;
    ``null`` carries the zero-edge null distribution and the empirical p-value.
    ``low_confidence`` is ``True`` (with :attr:`low_confidence_label`) when the
    minimum-observation floor was unset. The whole object stays ``world = replay``,
    claims robustness (never edge), and is a pure deterministic function of its inputs
    — :meth:`fingerprint` reproduces bit-for-bit (AC5). It emits no pass/fail verdict
    and never auto-merges or gates live money (AC6).
    """

    procedure: str
    mode: str
    world: str
    claim_class: str
    base_seed: int
    observation_count: int
    provenance: SignificanceProvenance
    null: NullDistribution
    low_confidence: bool
    low_confidence_label: str | None

    @property
    def p_value(self) -> Fraction:
        """The empirical one-tailed p-value of the signal-only edge test (AC3)."""
        return self.null.p_value

    @property
    def observed_mean(self) -> Fraction:
        """The observed rule-return mean (excess over the in-sample market drift, AC3)."""
        return self.null.observed_mean

    @property
    def emits_verdict(self) -> bool:
        """Always ``False`` — the gate is advisory data, never a pass/fail verdict (AC6)."""
        return SIGNIFICANCE_EMITS_VERDICT

    @property
    def makes_edge_claim(self) -> bool:
        """Always ``False`` — the claim class is robustness, never edge (L20, AC6)."""
        return SIGNIFICANCE_MAKES_EDGE_CLAIM

    def rng_provenance(self) -> dict[str, object]:
        """The ``rng_provenance`` stamp the CT-32 label folds in (B-13, AR-59)."""
        return self.provenance.fp1_identity()

    def result_label(self) -> dict[str, object]:
        """The procedure identity plus seed that enter the result label (B-7, AC1)."""
        return {
            "base_seed": self.base_seed,
            "claim_class": self.claim_class,
            "class": SIGNIFICANCE_RESULT_CLASS,
            "gate_auto_merges": GATE_AUTO_MERGES,
            "gate_is_advisory": GATE_IS_ADVISORY,
            "makes_edge_claim": SIGNIFICANCE_MAKES_EDGE_CLAIM,
            "mode": self.mode,
            "procedure": self.procedure,
            "rng_family": self.provenance.rng_family,
            "world": self.world,
        }

    def chart_series(self) -> dict[str, object]:
        """The null distribution as chart series data (never an image, AC6)."""
        return self.null.chart_series()

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Deterministic and reproducible (AC5, NFR-03)."""
        content: dict[str, object] = {
            "alpha_thresholds_deferred_to": ALPHA_THRESHOLDS_DEFERRED_TO,
            "base_seed": self.base_seed,
            "canonical_payload": SIGNIFICANCE_CANONICAL_PAYLOAD,
            "claim_class": self.claim_class,
            "class": SIGNIFICANCE_RESULT_CLASS,
            "emits_verdict": SIGNIFICANCE_EMITS_VERDICT,
            "format_version": SIGNIFICANCE_RESULT_FORMAT_VERSION,
            "gate_auto_merges": GATE_AUTO_MERGES,
            "gate_gates_live_money": GATE_GATES_LIVE_MONEY,
            "gate_is_advisory": GATE_IS_ADVISORY,
            "low_confidence": self.low_confidence,
            "makes_edge_claim": SIGNIFICANCE_MAKES_EDGE_CLAIM,
            "mode": self.mode,
            "null": self.null.fp1_identity(),
            "observation_count": self.observation_count,
            "procedure": self.procedure,
            "provenance": self.provenance.fp1_identity(),
            "return_alignment": RETURN_ALIGNMENT,
            "return_basis": RETURN_BASIS,
            "world": self.world,
        }
        if self.low_confidence_label is not None:
            content["low_confidence_label"] = self.low_confidence_label
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. The same inputs reproduce it bit-for-bit (AC5)."""
        return fingerprint(self.fp1_identity())


def run_significance_gate(
    *,
    signals: object,
    base_seed: object,
    resampling_scheme: object = None,
    block_length: object = None,
    iterations: object = None,
    minimum_observations: object = None,
    config: object = None,
    band_probabilities: object = (),
    stream_id: str = "signal-pass",
) -> Result[SignificanceResult]:
    """Run the pre-build rule-significance gate over a signal-only pass (AC1-AC6).

    ``signals`` is the per-bar raw entry signal (:class:`SignalBar` values: instant,
    exact ``Price`` close, and whether the bare entry rule fired). The gate first
    performs a signal-only pass over the B-2 event-slice loop with orders disabled and
    trading locked as in warm-up (AC1), then scores each fired signal against the NEXT
    bar's log return (AC2), builds a detrended zero-edge null and reports the empirical
    one-tailed p-value (AC3). The resampling scheme (``iid`` / ``block`` /
    ``stationary``), block length, iteration count, and minimum-observation floor are
    UI-editable configurables resolved from ``config`` or passed explicitly — none has
    a ratified value (AC4). Below a configured floor the gate returns a typed refusal;
    with the floor unset the result is labelled low-confidence (AC5). The result stays
    ``world = replay``, claims robustness never edge, and is advisory — it never
    auto-merges and never gates live money (AC6).
    """
    passed = run_signal_only_pass(signals, stream_id=stream_id)
    if is_refusal(passed):
        return passed
    bars = passed.value
    base = _non_negative_int(base_seed, "base_seed")
    if is_refusal(base):
        return base
    scheme = _resolve_scheme(config, resampling_scheme)
    if is_refusal(scheme):
        return scheme
    resolved_block = _resolve_block_length(config, block_length, scheme.value)
    if is_refusal(resolved_block):
        return resolved_block
    resolved_iterations = _resolve_positive_int(config, iterations, ITERATIONS_KEY, "iterations")
    if is_refusal(resolved_iterations):
        return resolved_iterations
    floor = _resolve_minimum_observations(config, minimum_observations)
    if is_refusal(floor):
        return floor
    bands = _coerce_bands(band_probabilities)
    if is_refusal(bands):
        return bands
    returns = next_bar_log_returns(bars)
    if is_refusal(returns):
        return returns
    detrended = _detrend(returns.value)
    rule_returns = tuple(detrended[index] for index in range(len(bars) - 1) if bars[index].fired)
    observation_count = len(rule_returns)
    if observation_count == 0:
        return invalid(
            "signals",
            "the entry rule fired on no bar with a next-bar return; there is no rule-return "
            "series to score, so no p-value is fabricated (AC5)",
        )
    if floor.value is not None and observation_count < floor.value:
        return _refuse_insufficient_observations(observation_count, floor.value)
    observed_mean = _mean(rule_returns)
    pool = tuple(value - observed_mean for value in rule_returns)  # re-centred to zero (AC3)
    null_means = _null_resample_means(
        pool=pool,
        scheme=scheme.value,
        block_length=resolved_block.value,
        base_seed=base.value,
        iterations=resolved_iterations.value,
    )
    if is_refusal(null_means):
        return null_means
    null = _build_null(
        null_means=null_means.value,
        observed_mean=observed_mean,
        iterations=resolved_iterations.value,
        band_probabilities=bands.value,
    )
    if is_refusal(null):
        return null
    provenance = SignificanceProvenance(
        rng_family=RNG_FAMILY,
        base_seed=base.value,
        seed_derivation_rule=SIGNIFICANCE_SEED_DERIVATION_RULE,
        resampling_scheme=scheme.value,
        block_length=resolved_block.value,
        iterations=resolved_iterations.value,
        minimum_observations=floor.value,
        data_window_start_ns=bars[0].instant.value_ns,
        data_window_end_ns=bars[-1].instant.value_ns,
    )
    low_confidence = floor.value is None
    return Ok(
        SignificanceResult(
            procedure=RULE_SIGNIFICANCE_PROCEDURE,
            mode=SIGNIFICANCE_MODE,
            world=SIGNIFICANCE_WORLD,
            claim_class=SIGNIFICANCE_CLAIM_CLASS,
            base_seed=base.value,
            observation_count=observation_count,
            provenance=provenance,
            null=null.value,
            low_confidence=low_confidence,
            low_confidence_label=LOW_CONFIDENCE_FLOOR_UNSET_LABEL if low_confidence else None,
        )
    )


def refuse_gate_auto_merge(name: object) -> TypedRefusal:
    """Refuse auto-merging a build on the significance gate (SC-06, B-14, AC6).

    The gate is advisory: a build pipeline may consult its verdict, but it never
    auto-merges and never gates live money, and the pass/fail alpha thresholds stay
    deferred to GAP-0049. Any attempt to auto-merge is a ``policy rejection`` —
    returned, never raised.
    """
    token = clean_token(name)
    if token is None:
        return invalid(
            "pipeline",
            "a pipeline identity is required to refuse an auto-merge",
            given=repr(name),
        )
    return policy(
        "authority",
        "the rule-significance gate is advisory; a build pipeline may consult its verdict but "
        "it never auto-merges and never gates live money, and the pass/fail alpha thresholds "
        "stay deferred to GAP-0049 (SC-06, B-14)",
        pipeline=token,
        gate_is_advisory=GATE_IS_ADVISORY,
        gate_auto_merges=GATE_AUTO_MERGES,
        alpha_thresholds_deferred_to=ALPHA_THRESHOLDS_DEFERRED_TO,
    )


def refuse_live_result_world(world: object) -> TypedRefusal:
    """Refuse a live result world for the significance gate (SC-06, L20, AC6).

    The gate's result world is replay or simulated, never live: it produces robustness
    evidence, never an edge claim, and cannot be read as a live-money result. A live
    world is a typed ``policy rejection`` — returned, never raised.
    """
    token = clean_token(world)
    named = token if token is not None else repr(world)
    return policy(
        "world",
        "the rule-significance gate result world is replay or simulated, never live; the "
        "claim class is robustness, never edge (L20, SC-06)",
        world=named,
        legal=(World.REPLAY.value, World.SIMULATED.value),
        forbidden=RESULT_WORLD_LIVE,
    )


def significance_identity() -> dict[str, object]:
    """Identity-bearing rule-significance-gate fields. Package SemVer is omitted."""
    return {
        "alpha_thresholds_deferred_to": ALPHA_THRESHOLDS_DEFERRED_TO,
        "canonical_payload": SIGNIFICANCE_CANONICAL_PAYLOAD,
        "claim_class": SIGNIFICANCE_CLAIM_CLASS,
        "class": SIGNIFICANCE_RESULT_CLASS,
        "emits_image_payload": SIGNIFICANCE_EMITS_IMAGE_PAYLOAD,
        "emits_verdict": SIGNIFICANCE_EMITS_VERDICT,
        "format_version": SIGNIFICANCE_RESULT_FORMAT_VERSION,
        "gate_auto_merges": GATE_AUTO_MERGES,
        "gate_gates_live_money": GATE_GATES_LIVE_MONEY,
        "gate_is_advisory": GATE_IS_ADVISORY,
        "gated_behind": CLAIM_GATED_BEHIND,
        "iterations_key": ITERATIONS_KEY,
        "makes_edge_claim": SIGNIFICANCE_MAKES_EDGE_CLAIM,
        "minimum_observations_key": MINIMUM_OBSERVATIONS_KEY,
        "mode": SIGNIFICANCE_MODE,
        "null_detrended_by": NULL_DETRENDED_BY,
        "null_hypothesis": NULL_HYPOTHESIS,
        "procedure": RULE_SIGNIFICANCE_PROCEDURE,
        "resampling_scheme_key": RESAMPLING_SCHEME_KEY,
        "resampling_schemes": RESAMPLING_SCHEMES,
        "return_alignment": RETURN_ALIGNMENT,
        "return_basis": RETURN_BASIS,
        "rng_family": RNG_FAMILY,
        "seed_derivation_rule": SIGNIFICANCE_SEED_DERIVATION_RULE,
        "signal_pass_orders_enabled": SIGNAL_PASS_ORDERS_ENABLED,
        "signal_pass_strategy_stays_flat": SIGNAL_PASS_STRATEGY_STAYS_FLAT,
        "signal_pass_trading_locked": SIGNAL_PASS_TRADING_LOCKED,
        "subphases": SUBPHASES,
        "world": SIGNIFICANCE_WORLD,
    }


# --- the detrended zero-edge null and its resampling (AC3) -------------------


def _detrend(returns: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    """Detrend the returns by their in-sample mean (AC3): ``r - mean(r)``."""
    market_mean = _mean(returns)
    return tuple(value - market_mean for value in returns)


def _null_resample_means(
    *,
    pool: tuple[Fraction, ...],
    scheme: str,
    block_length: int | None,
    base_seed: int,
    iterations: int,
) -> Result[tuple[Fraction, ...]]:
    """Resample the re-centred rule-return pool ``iterations`` times, mean each (AC3, AC5).

    Batch ``i`` draws ``len(pool)`` values with a fresh ``random.Random(base_seed + i)``
    under the declared scheme (iid / moving-block / stationary) and takes their exact
    mean, so the null distribution reproduces bit-for-bit. Block-based schemes wrap the
    pool circularly and need a resolved block length.
    """
    size = len(pool)
    means: list[Fraction] = []
    for index in range(iterations):
        drawn = _resample_once(
            pool=pool,
            scheme=scheme,
            block_length=block_length,
            size=size,
            seed=base_seed + index,
        )
        if is_refusal(drawn):
            return drawn
        means.append(_mean(drawn.value))
    return Ok(tuple(means))


def _resample_once(
    *,
    pool: tuple[Fraction, ...],
    scheme: str,
    block_length: int | None,
    size: int,
    seed: int,
) -> Result[tuple[Fraction, ...]]:
    """Draw one ``size``-length resample of the pool under the declared scheme.

    The seeded generator selects only indices / block structure — the drawn values are
    always exact rationals from the pool, so no binary float enters the statistic.
    """
    # A fresh seeded MT19937 generator per batch, selecting resample indices only —
    # never a cryptographic use, and the drawn values stay exact rationals (AR-59, AC5).
    rng = random.Random(seed)  # noqa: S311
    if scheme == SCHEME_IID:
        return Ok(tuple(pool[rng.randrange(size)] for _ in range(size)))
    if block_length is None:
        return invalid(
            "block_length",
            "the block and stationary schemes need a resolved block length",
            scheme=scheme,
        )
    length = min(block_length, size)
    if scheme == SCHEME_BLOCK:
        drawn: list[Fraction] = []
        while len(drawn) < size:
            start = rng.randrange(size)
            drawn.extend(pool[(start + offset) % size] for offset in range(length))
        return Ok(tuple(drawn[:size]))
    # Stationary bootstrap: geometric block lengths with mean = block length, wrapping
    # the pool circularly (Politis-Romano). The restart probability drives only the
    # block boundaries, never a stored value.
    restart_probability = 1.0 / length
    drawn = []
    cursor = rng.randrange(size)
    while len(drawn) < size:
        drawn.append(pool[cursor])
        # A restart begins a fresh block at a new random index; otherwise the block
        # continues to the next index, wrapping the pool circularly (Politis-Romano).
        restart = rng.random() < restart_probability
        cursor = rng.randrange(size) if restart else (cursor + 1) % size
    return Ok(tuple(drawn[:size]))


def _build_null(
    *,
    null_means: tuple[Fraction, ...],
    observed_mean: Fraction,
    iterations: int,
    band_probabilities: tuple[Fraction, ...],
) -> Result[NullDistribution]:
    """Summarise the null resample means against the observed mean, higher-is-better (AC3)."""
    summary = summarize_distribution(
        null_means,
        observed_mean,
        DIRECTION_HIGHER_IS_BETTER,
        band_probabilities=band_probabilities,
    )
    if is_refusal(summary):
        return summary
    exact_means: list[ExactRational] = []
    for value in null_means:
        minted = ExactRational.try_create(
            value.numerator, value.denominator, UnitKind.DIMENSIONLESS_RATIO
        )
        if is_refusal(minted):
            return minted
        exact_means.append(minted.value)
    stamped = fingerprint(
        {
            "class": _NULL_DISTRIBUTION_CLASS,
            "means": [[value.numerator, value.denominator] for value in null_means],
        }
    )
    if is_refusal(stamped):
        return stamped
    means_array = HistogramReadyArray(
        name="rule_significance_null_distribution",
        unit_kind=UnitKind.DIMENSIONLESS_RATIO,
        values=tuple(exact_means),
    )
    return Ok(
        NullDistribution(
            iterations=iterations,
            observed_mean_num=observed_mean.numerator,
            observed_mean_den=observed_mean.denominator,
            summary=summary.value,
            means=means_array,
            fingerprint=stamped.value,
        )
    )


def _refuse_insufficient_observations(observation_count: int, floor: int) -> TypedRefusal:
    """Below the configured minimum-observation floor: a typed refusal, not a p-value (AC5)."""
    return invalid(
        "signals",
        "the rule-return observation count is below the configured minimum-observation floor; "
        "the gate returns a typed refusal rather than a fabricated p-value (AC5)",
        observation_count=observation_count,
        minimum_observations=floor,
    )


# --- exact-arithmetic helpers ------------------------------------------------


def _mean(values: tuple[Fraction, ...]) -> Fraction:
    """The exact mean of a non-empty sequence of exact rationals."""
    return sum(values, Fraction(0)) / len(values)


# --- configurable resolution (AC4) -------------------------------------------


def _resolve_scheme(config: object, explicit: object) -> Result[str]:
    """Resolve the resampling scheme configurable (iid / block / stationary, AC4).

    Preferred from the resolved run-config's ``qmb_rule_significance_resampling_scheme``
    key; an explicit argument is accepted for a direct call. Neither supplied is a typed
    refusal — the scheme has no ratified value and no baked default.
    """
    if config is not None:
        resolved = require_configurable(config, RESAMPLING_SCHEME_KEY)
        if is_refusal(resolved):
            return resolved
        raw: object = resolved.value
    elif explicit is not None:
        raw = explicit
    else:
        return invalid(
            "resampling_scheme",
            "the resampling scheme is a UI-editable configurable with no ratified value; supply "
            "it via the resolved run-config key or explicitly — iid, block, or stationary (SC-07)",
            resampling_scheme_key=RESAMPLING_SCHEME_KEY,
            allowed=RESAMPLING_SCHEMES,
        )
    token = clean_token(raw)
    if token is None or token not in RESAMPLING_SCHEMES:
        return invalid(
            "resampling_scheme",
            "the resampling scheme is one of iid, block, or stationary",
            given=repr(raw),
            allowed=RESAMPLING_SCHEMES,
        )
    return Ok(token)


def _resolve_block_length(config: object, explicit: object, scheme: str) -> Result[int | None]:
    """Resolve the block length: required for block/stationary, unused for iid (AC4)."""
    if scheme not in _BLOCK_SCHEMES:
        return Ok(None)
    resolved = _resolve_positive_int(
        config, explicit, SIGNIFICANCE_BLOCK_LENGTH_KEY, "block_length"
    )
    if is_refusal(resolved):
        return resolved
    return Ok(resolved.value)


def _resolve_positive_int(config: object, explicit: object, key: str, field: str) -> Result[int]:
    """Resolve a required positive-int configurable from the config key or an explicit arg.

    The input carries no ratified value (SC-07); unset it is a typed ``invalid input``
    refusal, never a silently-applied default.
    """
    if config is not None:
        return require_positive_int(config, key)
    if explicit is not None:
        return _positive_int(explicit, field)
    return invalid(
        field,
        "this input is a UI-editable configurable with no ratified value; supply it via the "
        "resolved run-config key or explicitly (SC-07)",
        configurable_key=key,
    )


def _resolve_minimum_observations(config: object, explicit: object) -> Result[int | None]:
    """Resolve the OPTIONAL minimum-observation floor (AC5).

    Unset (absent from the config and no explicit arg) is a legal low-confidence path —
    the floor is ``None`` and the result is labelled low-confidence rather than refused.
    A present value must be a positive integer; the module invents no default.
    """
    if config is not None:
        raw = _config_value(config, MINIMUM_OBSERVATIONS_KEY)
        if raw is not None:
            resolved = require_positive_int(config, MINIMUM_OBSERVATIONS_KEY)
            if is_refusal(resolved):
                return resolved
            return Ok(resolved.value)
    if explicit is not None:
        resolved = _positive_int(explicit, "minimum_observations")
        if is_refusal(resolved):
            return resolved
        return Ok(resolved.value)
    return Ok(None)


def _config_value(config: object, key: str) -> object:
    """Read one key from a resolved run-config (its ``keys`` mapping) or a plain mapping."""
    if isinstance(config, Mapping):
        return cast("Mapping[str, object]", config).get(key)
    keys = getattr(config, "keys", None)
    if isinstance(keys, Mapping):
        return cast("Mapping[str, object]", keys).get(key)
    return None


# --- coercion helpers --------------------------------------------------------


def _coerce_signals(value: object) -> Result[tuple[SignalBar, ...]]:
    if isinstance(value, SignalBar):
        items: Sequence[object] = (value,)
    elif isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "signals",
            "the rule-significance gate reads the signal-only pass's ordered signal bars",
            given=repr(type(value).__name__),
        )
    else:
        items = cast("Sequence[object]", value)
    out: list[SignalBar] = []
    previous_ns: int | None = None
    for index, item in enumerate(items):
        parsed = _signal_from(item, index)
        if is_refusal(parsed):
            return parsed
        bar = parsed.value
        if previous_ns is not None and bar.instant.value_ns <= previous_ns:
            return invalid(
                "signals",
                "signal bars are strictly increasing in Instant order (a real historical window)",
                index=index,
                instant_ns=bar.instant.value_ns,
                previous_ns=previous_ns,
            )
        previous_ns = bar.instant.value_ns
        out.append(bar)
    if not out:
        return invalid(
            "signals",
            "the signal-only pass reads a non-empty signal-bar series (AC1)",
        )
    return Ok(tuple(out))


def _signal_from(item: object, index: int) -> Result[SignalBar]:
    if isinstance(item, SignalBar):
        return Ok(item)
    if not isinstance(item, Mapping):
        return invalid(
            "signals",
            "every signal bar is a SignalBar or a mapping of instant, close, fired",
            index=index,
            given=repr(type(item).__name__),
        )
    body = cast("Mapping[str, object]", item)
    minted = SignalBar.try_create(body.get("instant"), body.get("close"), body.get("fired"))
    if is_refusal(minted):
        return invalid(
            "signals",
            "each signal bar is a valid instant / exact Price close / bool signal",
            index=index,
            cause=dict(minted.context),
        )
    return minted


def _coerce_bands(value: object) -> Result[tuple[Fraction, ...]]:
    """Coerce caller-supplied confidence-band probabilities (exact, no default alpha)."""
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "band_probabilities",
            "confidence-band probabilities are an ordered sequence; the gate invents no "
            "alpha level (SC-07)",
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


def _non_negative_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, "a non-negative exact integer is required", given=repr(value))
    return Ok(value)


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, "a positive exact integer is required", given=repr(value))
    return Ok(value)
