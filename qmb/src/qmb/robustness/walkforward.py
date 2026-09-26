"""Walk-forward as an ordered sequence of split-manifest runs (Story 22.5).

The fourth B-14 ladder rung is **not a procedure that returns one number** — it is
the discipline that turns rolling in-sample / out-of-sample analysis into an ordered
sequence of **first-class split-manifest runs** plus a **read-time aggregation view**,
with no single merged run and no invented window / OOS-count thresholds.

What this module owns, and what it defers to the modules that already own it:

* **The window sequence (AC1).** A walk-forward is a sequence of split manifests: each
  :class:`WalkForwardWindow` pairs one in-sample and one out-of-sample CT-12 split
  manifest (each a knowledge-time / embargo-purge / calendar-in-band manifest), and
  materializes as two first-class :class:`WalkForwardRun` runs under B-3/B-4 — each with
  its own resolved run-config and its own ledger line. ``train``/``test`` are display
  aliases for the two manifests, never a substitute for their fingerprints (B-8,
  DEC-0169), and every read is split-governed at every boundary by qmf-data (AD-21).
* **The B-4 ledger roles and the OOS read-time fold (AC2).** An in-sample (train) run
  ledgers ``role = trial`` (or ``replicate``) with its objective measure and **never a
  bar verdict**. Because no verdict-bearing backtest ships while the GAP-0048 fidelity
  seam is open (SC-06), an out-of-sample window's bar outcome is a **read-time fold**
  (:func:`fold_oos_bar_outcome`) that returns ``not-yet-ruled`` until GAP-0048/0049 close.
* **SC-11 batch admission (AC3).** :func:`admit_walk_forward` resolves exactly one
  registry as-of at admission through the single B-15 registry-read port, freezes it for
  every window, and stamps it into the batch label; after admission every Book/BMS/bot
  fragment resolves by explicit fingerprint, never ``name@latest``.
* **The deferred configurables (AC4).** The window count, the in-sample and
  out-of-sample spans, and the step are UI-editable configurables carrying **no ratified
  value**; the module ships no invented default and no baked WF/OOS pass battery (SC-07).
* **The read-time aggregation view (AC5).** :func:`aggregate_walk_forward` is a read-time
  aggregation over the ledger's window runs — **never a merged run** — written into the
  CT-32 artifact as data. Its aggregated in-sample / out-of-sample metric distributions
  are the declared feeders for the deferred governance battery (the PBO / CSCV
  candidates), which itself ships no ratified thresholds (SC-07).
* **Reproducibility (AC6).** Each window's resolved run-config reproduces its CT-32
  fingerprint or returns a typed refusal (the CT-32 machinery already owns this), and
  each window's label carries its split-manifest fingerprints, ``registry_as_of``,
  ``world``, and evidence class (AR-59; B-10).

Like every B-14 rung the module is pure: it consumes resolved inputs, RETURNS its
descriptors / labels / views, and writes no log and no ledger line — the Epic 15
orchestrator owns every append. No module-global mutable state exists anywhere.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import EvidenceClass, Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal
from qmf.data.splits import SplitManifest

from qmb._refuse import clean_token, invalid, policy
from qmb.config import (
    ConfigFragment,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.ledger.line import ROLE_REPLICATE, ROLE_TRIAL
from qmb.registryread import RegistryReadPort
from qmb.results.charts import HistogramReadyArray
from qmb.results.ct32 import REGISTRY_AS_OF_KEY, SPLIT_FINGERPRINT_KEY
from qmb.results.measures import MEASURE_IDENTITIES
from qmb.robustness.contract import (
    PROCEDURE_WALK_FORWARD,
    THRESHOLDS_DEFERRED_TO,
    require_positive_int,
)

__all__ = [
    "AGGREGATION_CANONICAL_PAYLOAD",
    "AGGREGATION_EMITS_VERDICT",
    "AGGREGATION_IS_MERGED_RUN",
    "GOVERNANCE_BATTERY_CANDIDATES",
    "GOVERNANCE_BATTERY_DEFERRED_TO",
    "GOVERNANCE_BATTERY_HAS_RATIFIED_THRESHOLDS",
    "IN_SAMPLE_ALIAS",
    "IN_SAMPLE_RUN_ROLE",
    "IN_SAMPLE_SPAN_KEY",
    "METRIC_FOLD_DISTRIBUTION_CLASS",
    "OOS_BAR_OUTCOME_NOT_YET_RULED",
    "OOS_VERDICT_GATED_BEHIND",
    "OUT_OF_SAMPLE_ALIAS",
    "OUT_OF_SAMPLE_SPAN_KEY",
    "STEP_KEY",
    "VERDICT_BEARING_BACKTEST_SHIPS",
    "WALK_FORWARD_ADMISSION_FREEZES_AS_OF",
    "WALK_FORWARD_ADMISSION_HAS_SECOND_CACHE",
    "WALK_FORWARD_ADMISSION_SINGLE_AS_OF",
    "WALK_FORWARD_AGGREGATION_CLASS",
    "WALK_FORWARD_ALIASES_ARE_DISPLAY_ONLY",
    "WALK_FORWARD_CONFIGURABLES_HAVE_RATIFIED_VALUE",
    "WALK_FORWARD_CONFIGURABLE_KEYS",
    "WALK_FORWARD_DEFINITION_CLASS",
    "WALK_FORWARD_FORMAT_VERSION",
    "WALK_FORWARD_LABEL_CLASS",
    "WALK_FORWARD_MODE",
    "WALK_FORWARD_PLAN_CLASS",
    "WALK_FORWARD_PROCEDURE",
    "WALK_FORWARD_READS_ARE_SPLIT_GOVERNED",
    "WALK_FORWARD_RUN_CLASS",
    "WALK_FORWARD_SEGMENTS",
    "WALK_FORWARD_SHIPS_INVENTED_DEFAULT",
    "WALK_FORWARD_SHIPS_OOS_BATTERY",
    "WALK_FORWARD_WINDOW_CLASS",
    "WALK_FORWARD_WINDOW_LABEL_CLASS",
    "WINDOW_COUNT_KEY",
    "WINDOW_RUN_ROLES",
    "WINDOW_WRITES_BAR_VERDICT",
    "AdmittedWalkForward",
    "MetricFoldDistribution",
    "WalkForwardAggregation",
    "WalkForwardDefinition",
    "WalkForwardLabel",
    "WalkForwardPlan",
    "WalkForwardRun",
    "WalkForwardWindow",
    "WalkForwardWindowResult",
    "admit_walk_forward",
    "aggregate_walk_forward",
    "fold_oos_bar_outcome",
    "plan_walk_forward",
    "refuse_merged_walk_forward_run",
    "refuse_walk_forward_battery_threshold",
    "refuse_window_bar_verdict",
    "walk_forward_admission_identity",
    "walk_forward_identity",
]

# The B-14 rung this module realizes and the rolling-split-sequence mode it runs in.
WALK_FORWARD_PROCEDURE: Final[str] = PROCEDURE_WALK_FORWARD
WALK_FORWARD_MODE: Final[str] = "rolling-split-sequence"

WALK_FORWARD_FORMAT_VERSION: Final[int] = 1
WALK_FORWARD_WINDOW_CLASS: Final[str] = "qmb-walk-forward-window"
WALK_FORWARD_RUN_CLASS: Final[str] = "qmb-walk-forward-run"
WALK_FORWARD_PLAN_CLASS: Final[str] = "qmb-walk-forward-plan"
WALK_FORWARD_DEFINITION_CLASS: Final[str] = "qmb-walk-forward-definition"
WALK_FORWARD_LABEL_CLASS: Final[str] = "qmb-walk-forward-label"
WALK_FORWARD_WINDOW_LABEL_CLASS: Final[str] = "qmb-walk-forward-window-label"
WALK_FORWARD_AGGREGATION_CLASS: Final[str] = "qmb-walk-forward-aggregation"
METRIC_FOLD_DISTRIBUTION_CLASS: Final[str] = "qmb-walk-forward-metric-fold-distribution"

# ``train``/``test`` are DISPLAY aliases for the in-sample and out-of-sample split
# manifests; the aliases never substitute for the manifest fingerprints (B-8,
# DEC-0169). The literals match the CT-12 split display aliases (qmb.optimize.splits).
IN_SAMPLE_ALIAS: Final[str] = "train"
OUT_OF_SAMPLE_ALIAS: Final[str] = "test"
WALK_FORWARD_SEGMENTS: Final[tuple[str, ...]] = (IN_SAMPLE_ALIAS, OUT_OF_SAMPLE_ALIAS)
WALK_FORWARD_ALIASES_ARE_DISPLAY_ONLY: Final[bool] = True

# Every window boundary is a governed CT-12 split manifest — a knowledge-time /
# embargo-purge / calendar-in-band manifest — so every read is split-governed by
# qmf-data at every boundary; a raw date range is never a walk-forward boundary (AD-21).
WALK_FORWARD_READS_ARE_SPLIT_GOVERNED: Final[bool] = True

# B-4 ledger roles under the GAP-0048 seam (AC2). An in-sample (train) run ledgers
# role=trial (or replicate) with its objective measure and never a bar verdict.
IN_SAMPLE_RUN_ROLE: Final[str] = ROLE_TRIAL
WINDOW_RUN_ROLES: Final[tuple[str, ...]] = (ROLE_TRIAL, ROLE_REPLICATE)
WINDOW_WRITES_BAR_VERDICT: Final[bool] = False

# The OOS read-time fold (AC2, SC-06). No verdict-bearing backtest ships while the
# GAP-0048 fidelity seam is open, so an out-of-sample window's bar outcome is a
# read-time fold that returns ``not-yet-ruled`` until GAP-0048/0049 close. The token
# matches the B-4 ledger canonical-assignment fold vocabulary (never a stored verdict).
OOS_BAR_OUTCOME_NOT_YET_RULED: Final[str] = "not-yet-ruled"
OOS_VERDICT_GATED_BEHIND: Final[str] = "GAP-0048/GAP-0049"
VERDICT_BEARING_BACKTEST_SHIPS: Final[bool] = False

# The deferred pass-battery configurables (AC4, SC-07). The window count, the in-sample
# and out-of-sample spans, and the step are UI-editable configurables with NO ratified
# value; the module ships no invented default and no baked WF/OOS pass battery.
WINDOW_COUNT_KEY: Final[str] = "qmb_walk_forward_window_count"
IN_SAMPLE_SPAN_KEY: Final[str] = "qmb_walk_forward_in_sample_span"
OUT_OF_SAMPLE_SPAN_KEY: Final[str] = "qmb_walk_forward_out_of_sample_span"
STEP_KEY: Final[str] = "qmb_walk_forward_step"
WALK_FORWARD_CONFIGURABLE_KEYS: Final[tuple[str, ...]] = (
    WINDOW_COUNT_KEY,
    IN_SAMPLE_SPAN_KEY,
    OUT_OF_SAMPLE_SPAN_KEY,
    STEP_KEY,
)
WALK_FORWARD_CONFIGURABLES_HAVE_RATIFIED_VALUE: Final[bool] = False
WALK_FORWARD_SHIPS_INVENTED_DEFAULT: Final[bool] = False
WALK_FORWARD_SHIPS_OOS_BATTERY: Final[bool] = False

# SC-11 batch admission (AC3): admission resolves exactly one as-of and freezes it; the
# one port is the only cache there is (B-15; SC-11; DEC-0165).
WALK_FORWARD_ADMISSION_SINGLE_AS_OF: Final[bool] = True
WALK_FORWARD_ADMISSION_FREEZES_AS_OF: Final[bool] = True
WALK_FORWARD_ADMISSION_HAS_SECOND_CACHE: Final[bool] = False

# The read-time aggregation view (AC5). It is a read-time aggregation over the ledger's
# window runs — never a merged run — emitted as chart series data, never images, and
# emitting no verdict. Its aggregated distributions feed the deferred governance battery.
AGGREGATION_IS_MERGED_RUN: Final[bool] = False
AGGREGATION_CANONICAL_PAYLOAD: Final[str] = "series-data"
AGGREGATION_EMITS_VERDICT: Final[bool] = False
GOVERNANCE_BATTERY_CANDIDATES: Final[tuple[str, ...]] = ("pbo", "cscv")
GOVERNANCE_BATTERY_HAS_RATIFIED_THRESHOLDS: Final[bool] = False
GOVERNANCE_BATTERY_DEFERRED_TO: Final[str] = THRESHOLDS_DEFERRED_TO

_BOT_LAYER_KEY: Final[str] = "bot"
_DISPLAY_KEY: Final[str] = "display"
_Quantity = ExactRational | Money


def walk_forward_identity() -> dict[str, object]:
    """Identity-bearing walk-forward-procedure fields. Package SemVer is omitted."""
    return {
        "aggregation_canonical_payload": AGGREGATION_CANONICAL_PAYLOAD,
        "aggregation_emits_verdict": AGGREGATION_EMITS_VERDICT,
        "aggregation_is_merged_run": AGGREGATION_IS_MERGED_RUN,
        "configurable_keys": WALK_FORWARD_CONFIGURABLE_KEYS,
        "configurables_have_ratified_value": WALK_FORWARD_CONFIGURABLES_HAVE_RATIFIED_VALUE,
        "format_version": WALK_FORWARD_FORMAT_VERSION,
        "governance_battery_candidates": GOVERNANCE_BATTERY_CANDIDATES,
        "governance_battery_deferred_to": GOVERNANCE_BATTERY_DEFERRED_TO,
        "governance_battery_has_ratified_thresholds": GOVERNANCE_BATTERY_HAS_RATIFIED_THRESHOLDS,
        "in_sample_run_role": IN_SAMPLE_RUN_ROLE,
        "mode": WALK_FORWARD_MODE,
        "oos_bar_outcome_not_yet_ruled": OOS_BAR_OUTCOME_NOT_YET_RULED,
        "oos_verdict_gated_behind": OOS_VERDICT_GATED_BEHIND,
        "procedure": WALK_FORWARD_PROCEDURE,
        "reads_are_split_governed": WALK_FORWARD_READS_ARE_SPLIT_GOVERNED,
        "segments": WALK_FORWARD_SEGMENTS,
        "ships_invented_default": WALK_FORWARD_SHIPS_INVENTED_DEFAULT,
        "ships_oos_battery": WALK_FORWARD_SHIPS_OOS_BATTERY,
        "verdict_bearing_backtest_ships": VERDICT_BEARING_BACKTEST_SHIPS,
        "window_run_roles": WINDOW_RUN_ROLES,
        "window_writes_bar_verdict": WINDOW_WRITES_BAR_VERDICT,
    }


# --- the window's two first-class split-manifest runs (AC1, AC2) -------------


@dataclass(frozen=True, slots=True)
class WalkForwardRun:
    """One of a window's two first-class split-manifest runs (AC1, AC2).

    ``segment_alias`` is the display token (``train``/``test``) and is **never**
    substituted for the fingerprint in identity. ``split_fp1`` is the CT-12 manifest
    the run reads (identity-bearing). ``role`` is ``trial`` (or ``replicate``) — never
    ``confirmation`` and never a bar-verdict role — and ``contributes_to_objective`` is
    true only for the in-sample run: it computes the objective, while the out-of-sample
    run records its measures and its bar outcome is a read-time fold (AC2).
    """

    window_index: int
    segment_alias: str
    split_fp1: Fingerprint
    role: str
    contributes_to_objective: bool
    world: World = World.REPLAY
    evidence_class: str = EvidenceClass.PROVISIONAL.value

    @property
    def is_in_sample(self) -> bool:
        """True for the in-sample (train) run — the one that computes the objective."""
        return self.contributes_to_objective

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The fingerprint rides; the alias never does."""
        return {
            "class": WALK_FORWARD_RUN_CLASS,
            "contributes_to_objective": self.contributes_to_objective,
            "evidence_class": self.evidence_class,
            "format_version": WALK_FORWARD_FORMAT_VERSION,
            "role": self.role,
            "split_fp1": self.split_fp1.value,
            "window_index": self.window_index,
            "world": self.world.value,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint of one window run."""
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    """One walk-forward window: an in-sample / out-of-sample split-manifest pair (AC1).

    ``in_sample_split`` and ``out_of_sample_split`` are CT-12 split-manifest ``fp1``
    fingerprints — each a knowledge-time / embargo-purge / calendar-in-band manifest.
    The window materializes as two first-class :class:`WalkForwardRun` runs; ``train``/
    ``test`` are display aliases (:meth:`display_aliases`) and identity carries the
    fingerprints, never the aliases. ``world`` is always ``replay`` in V1.
    """

    window_index: int
    in_sample_split: Fingerprint
    out_of_sample_split: Fingerprint
    world: World = World.REPLAY
    evidence_class: str = EvidenceClass.PROVISIONAL.value

    @classmethod
    def try_create(
        cls,
        window_index: object,
        in_sample_split: object,
        out_of_sample_split: object,
        *,
        world: object = World.REPLAY,
        evidence_class: object = EvidenceClass.PROVISIONAL,
    ) -> Result[WalkForwardWindow]:
        """Admit one window's split-manifest pair (AC1, AC6).

        ``window_index`` is a non-negative exact integer. Each split is a CT-12
        :class:`~qmf.data.SplitManifest` (its ``fingerprint`` is taken and its world
        checked), a :class:`~qmf.core.Fingerprint`, or an ``fp1`` token. The two splits
        must be distinct manifests — naming one for both leaves no out-of-sample content
        — and ``world`` must be ``replay``; a simulated split is a policy rejection
        (B-7, SC-06).
        """
        index = _non_negative_int(window_index, "window_index")
        if is_refusal(index):
            return index
        resolved_world = _require_replay_world(world, "world")
        if is_refusal(resolved_world):
            return resolved_world
        evidence = _coerce_evidence_class(evidence_class)
        if is_refusal(evidence):
            return evidence
        in_sample = _coerce_split(in_sample_split, "in_sample_split")
        if is_refusal(in_sample):
            return in_sample
        out_of_sample = _coerce_split(out_of_sample_split, "out_of_sample_split")
        if is_refusal(out_of_sample):
            return out_of_sample
        if in_sample.value == out_of_sample.value:
            return invalid(
                "out_of_sample_split",
                "a window's in-sample and out-of-sample splits are distinct manifests; "
                "naming one fingerprint for both leaves no out-of-sample content (B-8, OPT-9)",
                given=in_sample.value.value,
            )
        return Ok(
            cls(
                window_index=index.value,
                in_sample_split=in_sample.value,
                out_of_sample_split=out_of_sample.value,
                world=resolved_world.value,
                evidence_class=evidence.value,
            )
        )

    def split_for(self, alias: object) -> Result[Fingerprint]:
        """Resolve a display alias to its split fingerprint (``train``/``test``)."""
        token = clean_token(alias)
        if token == IN_SAMPLE_ALIAS:
            return Ok(self.in_sample_split)
        if token == OUT_OF_SAMPLE_ALIAS:
            return Ok(self.out_of_sample_split)
        return invalid(
            "alias",
            "a window split alias is the display token train or test; it resolves to a "
            "manifest fingerprint and is never substituted for it (B-8)",
            given=repr(alias),
            allowed=list(WALK_FORWARD_SEGMENTS),
        )

    def alias_for(self, split: object) -> Result[str]:
        """The display alias of a split fingerprint. Display only, never identity."""
        resolved = _coerce_split(split, "split")
        if is_refusal(resolved):
            return resolved
        if resolved.value == self.in_sample_split:
            return Ok(IN_SAMPLE_ALIAS)
        if resolved.value == self.out_of_sample_split:
            return Ok(OUT_OF_SAMPLE_ALIAS)
        return invalid(
            "split",
            "the fingerprint is neither this window's in-sample nor its out-of-sample split",
            given=resolved.value.value,
        )

    def display_aliases(self) -> dict[str, str]:
        """The display-only alias map. Never part of :meth:`fp1_identity` (B-8)."""
        return {
            IN_SAMPLE_ALIAS: self.in_sample_split.value,
            OUT_OF_SAMPLE_ALIAS: self.out_of_sample_split.value,
        }

    @property
    def in_sample_run(self) -> WalkForwardRun:
        """The in-sample (train) run — role=trial, computes the objective (AC2)."""
        return WalkForwardRun(
            window_index=self.window_index,
            segment_alias=IN_SAMPLE_ALIAS,
            split_fp1=self.in_sample_split,
            role=IN_SAMPLE_RUN_ROLE,
            contributes_to_objective=True,
            world=self.world,
            evidence_class=self.evidence_class,
        )

    @property
    def out_of_sample_run(self) -> WalkForwardRun:
        """The out-of-sample (test) run — records measures; bar outcome is not-yet-ruled."""
        return WalkForwardRun(
            window_index=self.window_index,
            segment_alias=OUT_OF_SAMPLE_ALIAS,
            split_fp1=self.out_of_sample_split,
            role=IN_SAMPLE_RUN_ROLE,
            contributes_to_objective=False,
            world=self.world,
            evidence_class=self.evidence_class,
        )

    @property
    def runs(self) -> tuple[WalkForwardRun, WalkForwardRun]:
        """The window's two first-class runs, in-sample first (AC1)."""
        return (self.in_sample_run, self.out_of_sample_run)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Both split fingerprints ride; aliases never do."""
        return {
            "class": WALK_FORWARD_WINDOW_CLASS,
            "evidence_class": self.evidence_class,
            "format_version": WALK_FORWARD_FORMAT_VERSION,
            "in_sample_split_fp1": self.in_sample_split.value,
            "out_of_sample_split_fp1": self.out_of_sample_split.value,
            "window_index": self.window_index,
            "world": self.world.value,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same split pair reproduces it (NFR-03)."""
        return fingerprint(self.fp1_identity())


# --- the ordered window sequence + the deferred configurables (AC1, AC4) -----


@dataclass(frozen=True, slots=True)
class WalkForwardPlan:
    """An ordered sequence of walk-forward windows plus its deferred configurables (AC1, AC4).

    ``windows`` is the ordered, contiguous ``0..n-1`` window sequence. ``window_count``,
    ``in_sample_span``, ``out_of_sample_span``, and ``step`` are the UI-editable
    configurables the plan pins into identity — none carries a ratified value, and the
    window count equals the length of the sequence (never an invented default).
    """

    windows: tuple[WalkForwardWindow, ...]
    window_count: int
    in_sample_span: int
    out_of_sample_span: int
    step: int
    world: World = World.REPLAY

    @property
    def runs(self) -> tuple[WalkForwardRun, ...]:
        """Every window's two runs, in window then in-sample-first order (AC1)."""
        out: list[WalkForwardRun] = []
        for window in self.windows:
            out.extend(window.runs)
        return tuple(out)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. The ordered windows and the four configurables ride."""
        return {
            "class": WALK_FORWARD_PLAN_CLASS,
            "format_version": WALK_FORWARD_FORMAT_VERSION,
            "in_sample_span": self.in_sample_span,
            "out_of_sample_span": self.out_of_sample_span,
            "step": self.step,
            "window_count": self.window_count,
            "windows": [window.fp1_identity() for window in self.windows],
            "world": self.world.value,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same windows + configurables reproduce it (NFR-03)."""
        return fingerprint(self.fp1_identity())


def plan_walk_forward(
    windows: object,
    *,
    config: object = None,
    window_count: object = None,
    in_sample_span: object = None,
    out_of_sample_span: object = None,
    step: object = None,
) -> Result[WalkForwardPlan]:
    """Sequence the windows and pin the deferred configurables (AC1, AC4).

    ``windows`` is an ordered sequence of :class:`WalkForwardWindow` (contiguous window
    indices ``0..n-1``, all in the same ``replay`` world). The window count, in-sample
    and out-of-sample spans, and step are resolved from ``config`` (a resolved run-config
    or a key->value mapping) via the four UI-editable keys, or passed explicitly — none
    unset is a typed refusal, since the module ships no invented default (SC-07). The
    resolved window count must equal the number of windows; a mismatch is refused rather
    than silently truncated.
    """
    parsed = _coerce_windows(windows)
    if is_refusal(parsed):
        return parsed
    ordered = parsed.value
    resolved_count = _resolve_configurable(config, window_count, WINDOW_COUNT_KEY)
    if is_refusal(resolved_count):
        return resolved_count
    resolved_in = _resolve_configurable(config, in_sample_span, IN_SAMPLE_SPAN_KEY)
    if is_refusal(resolved_in):
        return resolved_in
    resolved_out = _resolve_configurable(config, out_of_sample_span, OUT_OF_SAMPLE_SPAN_KEY)
    if is_refusal(resolved_out):
        return resolved_out
    resolved_step = _resolve_configurable(config, step, STEP_KEY)
    if is_refusal(resolved_step):
        return resolved_step
    if resolved_count.value != len(ordered):
        return invalid(
            "window_count",
            "the resolved window count is a UI-editable configurable that must equal the "
            "number of windows in the sequence; a mismatch is refused, never truncated (AC4)",
            window_count=resolved_count.value,
            windows=len(ordered),
        )
    return Ok(
        WalkForwardPlan(
            windows=ordered,
            window_count=resolved_count.value,
            in_sample_span=resolved_in.value,
            out_of_sample_span=resolved_out.value,
            step=resolved_step.value,
            world=ordered[0].world,
        )
    )


# --- SC-11 batch admission over one frozen registry as-of (AC3, AC6) ---------


@dataclass(frozen=True, slots=True)
class WalkForwardDefinition:
    """A walk-forward plan over a bot/Book/BMS context, admitted as one batch (AC3).

    ``bot`` / ``book`` / ``bms`` are the context refs (a human alias before admission,
    or an explicit ``fp1``); ``plan`` is the ordered window sequence. Admission resolves
    the context once through the one registry-read port and freezes a single as-of for
    every window (B-15, SC-11).
    """

    bot: str
    book: str
    bms: str
    plan: WalkForwardPlan

    @classmethod
    def try_create(
        cls, *, bot: object, book: object, bms: object, plan: object
    ) -> Result[WalkForwardDefinition]:
        """Validate the context refs and the plan, value-or-refusal."""
        bot_token = _cite(bot, "bot")
        if is_refusal(bot_token):
            return bot_token
        book_token = _cite(book, "book")
        if is_refusal(book_token):
            return book_token
        bms_token = _cite(bms, "bms")
        if is_refusal(bms_token):
            return bms_token
        if not isinstance(plan, WalkForwardPlan):
            return invalid(
                "plan",
                "a walk-forward definition names a WalkForwardPlan (the ordered window sequence)",
                given=repr(type(plan).__name__),
            )
        return Ok(cls(bot=bot_token.value, book=book_token.value, bms=bms_token.value, plan=plan))

    def fp1_identity(self) -> dict[str, object]:
        """Canonical definition identity. The context cites and the plan ride."""
        return {
            "bms": self.bms,
            "book": self.book,
            "bot": self.bot,
            "class": WALK_FORWARD_DEFINITION_CLASS,
            "format_version": WALK_FORWARD_FORMAT_VERSION,
            "plan": self.plan.fp1_identity(),
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The definition's ``fp1`` — the walk-forward id (computed by qmf-core)."""
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class WalkForwardLabel:
    """The one label the whole batch shares: the frozen registry as-of plus context (AC3).

    ``walk_forward_id`` is the definition's ``fp1``. ``registry_as_of`` and
    ``set_fingerprint`` ARE the one frozen as-of resolved at admission; every window's
    label carries the identical pair. ``bot_fp1`` / ``book_fp1`` / ``bms_fp1`` are the
    context resolved once to explicit fingerprints so no two windows resolve different
    versions (B-15, SC-11).
    """

    walk_forward_id: Fingerprint
    registry_as_of: Instant
    set_fingerprint: Fingerprint
    bot_fp1: Fingerprint
    book_fp1: Fingerprint
    bms_fp1: Fingerprint

    def registry_as_of_stamp(self) -> dict[str, object]:
        """The frozen as-of stamp (instant nanoseconds + set fingerprint)."""
        return {"value_ns": self.registry_as_of.value_ns, "fingerprint": self.set_fingerprint.value}

    def fp1_identity(self) -> dict[str, object]:
        """Canonical walk-forward-label identity. Package SemVer is omitted."""
        return {
            "bms_fp1": self.bms_fp1.value,
            "book_fp1": self.book_fp1.value,
            "bot_fp1": self.bot_fp1.value,
            "class": WALK_FORWARD_LABEL_CLASS,
            "format_version": WALK_FORWARD_FORMAT_VERSION,
            "registry_as_of": self.registry_as_of.fp1_identity(),
            "set_fingerprint": self.set_fingerprint.value,
            "walk_forward_id": self.walk_forward_id.value,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The label's ``fp1``, computed only by the qmf-core seam."""
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class AdmittedWalkForward:
    """A walk-forward admitted as a batch over one frozen registry as-of (B-15, SC-11).

    ``port`` is the single library-owned registry-read port, frozen at admission: after
    admission it resolves by explicit fingerprint only, and a fresher as-of set arriving
    on the hub never reaches an in-flight or not-yet-started window. ``book_fragment`` and
    ``bms_fragment`` are the context resolved once — shared identically by every window —
    and ``windows`` are the ordered window pairs.
    """

    definition: WalkForwardDefinition
    port: RegistryReadPort
    label: WalkForwardLabel
    book_fragment: ConfigFragment
    bms_fragment: ConfigFragment
    windows: tuple[WalkForwardWindow, ...]

    @property
    def registry_as_of(self) -> Instant:
        """The one frozen as-of instant every window shares."""
        return self.label.registry_as_of

    @property
    def set_fingerprint(self) -> Fingerprint:
        """The one frozen as-of set fingerprint every window shares."""
        return self.label.set_fingerprint

    @property
    def window_count(self) -> int:
        """The batch size — the number of admitted windows."""
        return len(self.windows)

    @property
    def run_count(self) -> int:
        """The number of first-class runs — two per window (in-sample + out-of-sample)."""
        return 2 * len(self.windows)

    def registry_as_of_stamp(self) -> dict[str, object]:
        """The frozen as-of stamp that lands in every window's CT-32 label set."""
        return self.label.registry_as_of_stamp()

    def window_label(self, window: object) -> Result[dict[str, object]]:
        """The per-window label carrying BOTH split fingerprints and the frozen as-of (AC6).

        A window label stamps the one frozen as-of onto this window's identity plus the
        in-sample and out-of-sample split-manifest fingerprints, the world, and the
        evidence class. Every window's label carries the identical ``registry_as_of``
        pair the batch label carries (B-15).
        """
        resolved = self._require_window(window)
        if is_refusal(resolved):
            return resolved
        member = resolved.value
        label: dict[str, object] = {
            "bms_fp1": self.label.bms_fp1.value,
            "book_fp1": self.label.book_fp1.value,
            "bot_fp1": self.label.bot_fp1.value,
            "class": WALK_FORWARD_WINDOW_LABEL_CLASS,
            _DISPLAY_KEY: {"aliases": member.display_aliases()},
            "evidence_class": member.evidence_class,
            "format_version": WALK_FORWARD_FORMAT_VERSION,
            "in_sample_split_fp1": member.in_sample_split.value,
            "out_of_sample_split_fp1": member.out_of_sample_split.value,
            "registry_as_of": self.registry_as_of_stamp(),
            "walk_forward_id": self.label.walk_forward_id.value,
            "window_index": member.window_index,
            "world": member.world.value,
        }
        return Ok(label)

    def compile_run(
        self,
        run: object,
        *,
        invocation_flags: object = None,
        workspace_defaults: object = None,
        condition_presets: object = (),
    ) -> Result[ResolvedRunConfig]:
        """Compile one window run's resolved run-config against the frozen as-of (AC1, AC3, AC6).

        The bot is cited by its resolved ``fp1`` and the Book/BMS ride as the fragments
        materialized once at admission, so compilation resolves every fragment by explicit
        fingerprint against the frozen as-of set, never ``name@latest`` (B-3; B-13; B-15).
        The frozen ``registry_as_of`` and the run's split-manifest fingerprint are stamped
        into the resolved run-config so they appear verbatim in the window's CT-32 label
        set (AR-59); a caller may not declare either.
        """
        resolved = self._require_run(run)
        if is_refusal(resolved):
            return resolved
        member = resolved.value
        guarded = _refuse_caller_stamp(invocation_flags, "invocation_flags")
        if guarded is not None:
            return guarded
        guarded = _refuse_caller_stamp(workspace_defaults, "workspace_defaults")
        if guarded is not None:
            return guarded
        run_spec: dict[str, object] = {
            _BOT_LAYER_KEY: self.label.bot_fp1,
            REGISTRY_AS_OF_KEY: self.registry_as_of_stamp(),
            SPLIT_FINGERPRINT_KEY: member.split_fp1.value,
        }
        return compile_run_config(
            self.port,
            book_fragment=self.book_fragment,
            bms_fragment=self.bms_fragment,
            run_spec=run_spec,
            invocation_flags=invocation_flags,
            workspace_defaults=workspace_defaults,
            condition_presets=condition_presets,
        )

    def _require_window(self, window: object) -> Result[WalkForwardWindow]:
        if not isinstance(window, WalkForwardWindow):
            return invalid(
                "window",
                "a window label names a WalkForwardWindow of this batch",
                given=repr(type(window).__name__),
            )
        identity = window.fp1_identity()
        for member in self.windows:
            if member.fp1_identity() == identity:
                return Ok(member)
        return invalid(
            "window",
            "this WalkForwardWindow is not a window of this admitted walk-forward",
            given=repr(identity),
        )

    def _require_run(self, run: object) -> Result[WalkForwardRun]:
        if not isinstance(run, WalkForwardRun):
            return invalid(
                "run",
                "a window compile names a WalkForwardRun of this batch",
                given=repr(type(run).__name__),
            )
        identity = run.fp1_identity()
        for window in self.windows:
            for member in window.runs:
                if member.fp1_identity() == identity:
                    return Ok(member)
        return invalid(
            "run",
            "this WalkForwardRun is not a run of this admitted walk-forward",
            given=repr(identity),
        )


def admit_walk_forward(
    definition: object, port: object, writer: object
) -> Result[AdmittedWalkForward]:
    """Admit a walk-forward as a batch over exactly one frozen registry as-of (AC3, B-15, SC-11).

    Admission resolves the bot/Book/BMS context ONCE through the single library-owned
    registry-read port — the bot to its ``fp1`` and the Book/BMS to materialized config
    fragments — then freezes the port's as-of for every window and stamps it into the
    batch label. A context reference that a fresher as-of set shows superseded at
    admission time is an AD-11 stale-evidence refusal at the port's configured severity,
    returned never raised (AD-11; AR-55; FM-7). Pass the live (unfrozen) port so admission
    can detect stale evidence before it freezes.
    """
    parsed = _as_definition(definition)
    if is_refusal(parsed):
        return parsed
    spec = parsed.value
    if not isinstance(port, RegistryReadPort):
        return invalid(
            "port",
            "a walk-forward admits its batch through the one library-owned registry-read port",
            given=repr(type(port).__name__),
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "batch admission stamps a WriterId on each materialized fragment's "
            "CT-07 occurrence-of edge",
            given=repr(type(writer).__name__),
        )
    # Resolve the context against the LIVE port so a superseded reference is an AD-11
    # stale-evidence refusal here, before the as-of is frozen.
    bot = port.resolve(spec.bot)
    if is_refusal(bot):
        return bot
    book_fragment = materialize_book_fragment(port, spec.book, writer)
    if is_refusal(book_fragment):
        return book_fragment
    bms_fragment = materialize_bms_fragment(port, spec.bms, writer)
    if is_refusal(bms_fragment):
        return bms_fragment
    walk_forward_id = spec.fingerprint()
    if is_refusal(walk_forward_id):
        return walk_forward_id
    # Freeze the one as-of for every window; admit_batch flips the frozen flag only, so
    # the bound as-of — and its (instant + set fingerprint) — is the one just used.
    frozen = port.admit_batch()
    label = WalkForwardLabel(
        walk_forward_id=walk_forward_id.value,
        registry_as_of=frozen.bound.registry_as_of,
        set_fingerprint=frozen.bound.fingerprint,
        bot_fp1=bot.value.fingerprint,
        book_fp1=book_fragment.value.source_fp1,
        bms_fp1=bms_fragment.value.source_fp1,
    )
    return Ok(
        AdmittedWalkForward(
            definition=spec,
            port=frozen,
            label=label,
            book_fragment=book_fragment.value,
            bms_fragment=bms_fragment.value,
            windows=spec.plan.windows,
        )
    )


def walk_forward_admission_identity() -> dict[str, object]:
    """Identity-bearing batch-admission fields. Package SemVer is omitted."""
    return {
        "admission_freezes_as_of": WALK_FORWARD_ADMISSION_FREEZES_AS_OF,
        "admission_has_second_cache": WALK_FORWARD_ADMISSION_HAS_SECOND_CACHE,
        "admission_single_as_of": WALK_FORWARD_ADMISSION_SINGLE_AS_OF,
        "registry_as_of_key": REGISTRY_AS_OF_KEY,
        "split_fingerprint_key": SPLIT_FINGERPRINT_KEY,
        "walk_forward_label_class": WALK_FORWARD_LABEL_CLASS,
        "walk_forward_window_label_class": WALK_FORWARD_WINDOW_LABEL_CLASS,
    }


# --- the out-of-sample bar-outcome read-time fold (AC2) ----------------------


def fold_oos_bar_outcome(window: object = None) -> str:
    """The out-of-sample bar outcome is a read-time fold returning ``not-yet-ruled`` (AC2).

    No verdict-bearing backtest ships while the GAP-0048 fidelity seam is open (SC-06), so
    an out-of-sample window's bar outcome is never a stored pass/fail — it is derived at
    read time and returns ``not-yet-ruled`` until GAP-0048/0049 close, exactly as the B-4
    canonical-assignment fold does for a world/role miss. The optional ``window`` argument
    is accepted for read-site symmetry and does not change the fold while the seam is open.
    """
    del window
    return OOS_BAR_OUTCOME_NOT_YET_RULED


def refuse_window_bar_verdict(name: object) -> Result[None]:
    """Refuse reading a bar verdict out of a walk-forward window run (AC2, B-4).

    A window run — in-sample or out-of-sample — appends one ``role = trial`` (or
    ``replicate``) ledger line of raw measures; it never writes a Book-bar pass/fail. Any
    attempt to read a bar verdict out of it is a ``policy rejection`` (B-4). The
    out-of-sample bar outcome is a read-time fold that returns ``not-yet-ruled`` while
    GAP-0048/0049 stay open, never a stored verdict.
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
        "a walk-forward window run is a role=trial (or replicate) run appending one ledger "
        "line of raw measures; it never writes a Book-bar pass/fail verdict, and the OOS bar "
        "outcome is a read-time fold that returns not-yet-ruled until GAP-0048/0049 close (B-4)",
        verdict=token,
        window_run_roles=WINDOW_RUN_ROLES,
        writes_bar_verdict=WINDOW_WRITES_BAR_VERDICT,
        oos_bar_outcome=OOS_BAR_OUTCOME_NOT_YET_RULED,
        gated_behind=OOS_VERDICT_GATED_BEHIND,
    )


# --- the read-time aggregation view over the window runs (AC5) ---------------


@dataclass(frozen=True, slots=True)
class WalkForwardWindowResult:
    """One window's in-sample and out-of-sample metric values, read from its runs (AC5).

    ``in_sample`` and ``out_of_sample`` map each selected metric identity to its exact
    value — an :class:`~qmf.core.exact.ExactRational` or :class:`~qmf.core.exact.Money`,
    read from the window run's raw ledger measures. A raw binary float is refused; the
    money path stays exact (AD-7).
    """

    window_index: int
    in_sample: Mapping[str, _Quantity]
    out_of_sample: Mapping[str, _Quantity]

    @classmethod
    def try_create(
        cls, window_index: object, in_sample: object, out_of_sample: object
    ) -> Result[WalkForwardWindowResult]:
        """Validate one window's paired in-sample / out-of-sample metric values."""
        index = _non_negative_int(window_index, "window_index")
        if is_refusal(index):
            return index
        parsed_in = _coerce_metric_map(in_sample, "in_sample")
        if is_refusal(parsed_in):
            return parsed_in
        parsed_out = _coerce_metric_map(out_of_sample, "out_of_sample")
        if is_refusal(parsed_out):
            return parsed_out
        return Ok(
            cls(
                window_index=index.value,
                in_sample=parsed_in.value,
                out_of_sample=parsed_out.value,
            )
        )


@dataclass(frozen=True, slots=True)
class MetricFoldDistribution:
    """One metric's per-window in-sample and out-of-sample distributions, as data (AC5).

    ``in_sample_distribution`` and ``out_of_sample_distribution`` are histogram-ready
    arrays of the metric's per-window values (in window order) — chart series data, never
    images — and the paired ``(in_sample, out_of_sample)`` points are the PBO / CSCV
    feeders. No pass/fail verdict and no threshold is emitted (SC-07).
    """

    metric_identity: str
    unit_kind: str
    window_count: int
    in_sample_distribution: HistogramReadyArray
    out_of_sample_distribution: HistogramReadyArray

    @property
    def emits_verdict(self) -> bool:
        """Always ``False`` — the fold distribution is pure data (AC5)."""
        return AGGREGATION_EMITS_VERDICT

    def chart_series(self) -> dict[str, object]:
        """Both segment distributions as machine-readable chart series (never images)."""
        return {
            "in_sample": self.in_sample_distribution.as_data(),
            "metric_identity": self.metric_identity,
            "out_of_sample": self.out_of_sample_distribution.as_data(),
        }

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The exact per-window values ride (reproducible)."""
        return {
            "canonical_payload": AGGREGATION_CANONICAL_PAYLOAD,
            "class": METRIC_FOLD_DISTRIBUTION_CLASS,
            "emits_verdict": AGGREGATION_EMITS_VERDICT,
            "in_sample_distribution": self.in_sample_distribution.as_data(),
            "metric_identity": self.metric_identity,
            "out_of_sample_distribution": self.out_of_sample_distribution.as_data(),
            "unit_kind": self.unit_kind,
            "window_count": self.window_count,
        }


@dataclass(frozen=True, slots=True)
class WalkForwardAggregation:
    """A read-time aggregation over the ledger's window runs — never a merged run (AC5).

    ``metrics`` carries each selected metric's per-window in-sample / out-of-sample
    distributions. The whole object is a read-time VIEW: it aggregates the window runs'
    measures, mints no run, and emits no verdict. Its distributions are the declared
    feeders for the deferred governance battery (the PBO / CSCV candidates), which ships
    no ratified thresholds (SC-07). :meth:`ct32_data_payload` is the aggregation written
    into the CT-32 artifact as data (AD-10-excluded from the CT-32 fingerprint).
    """

    window_count: int
    metrics: tuple[MetricFoldDistribution, ...]

    @property
    def is_merged_run(self) -> bool:
        """Always ``False`` — the aggregation is a read-time view, never a merged run (AC5)."""
        return AGGREGATION_IS_MERGED_RUN

    @property
    def emits_verdict(self) -> bool:
        """Always ``False`` — the aggregation is pure data, never a verdict (AC5)."""
        return AGGREGATION_EMITS_VERDICT

    def metric_named(self, identity: str) -> MetricFoldDistribution | None:
        """The per-window fold distribution for ``identity``, or ``None`` if absent."""
        for metric in self.metrics:
            if metric.metric_identity == identity:
                return metric
        return None

    def ct32_data_payload(self) -> dict[str, object]:
        """The aggregation written into the CT-32 artifact as data (AC5).

        A read-time aggregation view, tagged as data and never a merged run. It carries
        each metric's in-sample / out-of-sample distributions as chart series, names the
        deferred governance-battery candidates it feeds, and emits no verdict.
        """
        return {
            "canonical_payload": AGGREGATION_CANONICAL_PAYLOAD,
            "class": WALK_FORWARD_AGGREGATION_CLASS,
            "emits_verdict": AGGREGATION_EMITS_VERDICT,
            "governance_battery_candidates": list(GOVERNANCE_BATTERY_CANDIDATES),
            "governance_battery_deferred_to": GOVERNANCE_BATTERY_DEFERRED_TO,
            "governance_battery_has_ratified_thresholds": (
                GOVERNANCE_BATTERY_HAS_RATIFIED_THRESHOLDS
            ),
            "is_merged_run": AGGREGATION_IS_MERGED_RUN,
            "metrics": [metric.chart_series() for metric in self.metrics],
            "window_count": self.window_count,
        }

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Deterministic and reproducible (AC6, NFR-03)."""
        return {
            "class": WALK_FORWARD_AGGREGATION_CLASS,
            "emits_verdict": AGGREGATION_EMITS_VERDICT,
            "format_version": WALK_FORWARD_FORMAT_VERSION,
            "governance_battery_candidates": GOVERNANCE_BATTERY_CANDIDATES,
            "is_merged_run": AGGREGATION_IS_MERGED_RUN,
            "metrics": [metric.fp1_identity() for metric in self.metrics],
            "window_count": self.window_count,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. The same window results reproduce it bit-for-bit (AC6)."""
        return fingerprint(self.fp1_identity())


def aggregate_walk_forward(
    window_results: object, metrics: object
) -> Result[WalkForwardAggregation]:
    """Aggregate the window runs at read time — never a merged run (AC5, B-12).

    ``window_results`` is the ordered sequence of :class:`WalkForwardWindowResult` read
    from the ledger's window runs; ``metrics`` selects the measure identities to
    aggregate. Per metric the per-window in-sample and out-of-sample values are collected
    (in window order) into histogram-ready distributions — the declared feeders for the
    deferred PBO / CSCV governance battery. No run is minted, no threshold is applied, and
    no verdict is emitted (SC-07). A metric missing from any window, or a metric whose
    unit-kind differs across windows, is a typed refusal rather than a silently-dropped
    fold.
    """
    parsed = _coerce_window_results(window_results)
    if is_refusal(parsed):
        return parsed
    ordered = parsed.value
    selected = _coerce_metrics(metrics)
    if is_refusal(selected):
        return selected
    if not ordered:
        return invalid(
            "window_results",
            "a walk-forward aggregation reads at least one window run's result (AC5)",
        )
    per_metric: list[MetricFoldDistribution] = []
    for metric in selected.value:
        built = _fold_metric(metric, ordered)
        if is_refusal(built):
            return built
        per_metric.append(built.value)
    return Ok(WalkForwardAggregation(window_count=len(ordered), metrics=tuple(per_metric)))


def refuse_merged_walk_forward_run(name: object = "merged-run") -> Result[None]:
    """Refuse minting a single merged walk-forward run (AC5, B-12).

    The walk-forward view is a read-time aggregation over the ledger's window runs; there
    is no single merged run, and folding the windows into one governed run is a ``policy
    rejection``.
    """
    run_name = clean_token(name) or "merged-run"
    return policy(
        "run",
        "a walk-forward view is a read-time aggregation over the ledger's window runs; it "
        "never merges the windows into one governed run (B-12, AC5)",
        given=run_name,
        is_merged_run=AGGREGATION_IS_MERGED_RUN,
    )


def refuse_walk_forward_battery_threshold(name: object) -> Result[None]:
    """Refuse applying a ratified WF / OOS / PBO / CSCV pass-battery threshold (AC4, AC5, SC-07).

    The window count, spans, step, and the PBO / CSCV governance battery are deferred
    pass-battery values with no ratified threshold. Applying one is a ``policy rejection``
    until the deferred sitting rules the battery and its thresholds.
    """
    token = clean_token(name)
    if token is None:
        return invalid(
            "threshold",
            "a battery-threshold name is required to refuse it",
            given=repr(name),
        )
    return policy(
        "threshold",
        "the walk-forward window count, spans, step, and the PBO / CSCV governance battery "
        "are deferred pass-battery values with no ratified threshold; applying one is refused "
        "until the deferred sitting rules it (SC-07)",
        threshold=token,
        governance_battery_candidates=list(GOVERNANCE_BATTERY_CANDIDATES),
        has_ratified_thresholds=GOVERNANCE_BATTERY_HAS_RATIFIED_THRESHOLDS,
        deferred_to=GOVERNANCE_BATTERY_DEFERRED_TO,
    )


# --- aggregation helpers -----------------------------------------------------


def _fold_metric(
    metric: str, window_results: tuple[WalkForwardWindowResult, ...]
) -> Result[MetricFoldDistribution]:
    """Collect one metric's per-window in-sample / out-of-sample values, in window order."""
    in_values: list[_Quantity] = []
    out_values: list[_Quantity] = []
    unit_kind: UnitKind | None = None
    for result in window_results:
        in_value = result.in_sample.get(metric)
        out_value = result.out_of_sample.get(metric)
        if in_value is None or out_value is None:
            return invalid(
                "metric",
                "every window must carry the selected metric in both its in-sample and "
                "out-of-sample result; a missing fold is refused, never dropped (AC5)",
                metric=metric,
                window_index=result.window_index,
            )
        for value in (in_value, out_value):
            kind = value.unit_kind
            if unit_kind is None:
                unit_kind = kind
            elif kind != unit_kind:
                return invalid(
                    "metric",
                    "a metric's unit-kind must be identical across every window fold; a "
                    "mixed unit-kind is refused (AD-40)",
                    metric=metric,
                    expected=unit_kind.value,
                    given=kind.value,
                    window_index=result.window_index,
                )
        in_values.append(in_value)
        out_values.append(out_value)
    resolved_kind = cast("UnitKind", unit_kind)
    return Ok(
        MetricFoldDistribution(
            metric_identity=metric,
            unit_kind=resolved_kind.value,
            window_count=len(window_results),
            in_sample_distribution=HistogramReadyArray(
                name=f"{metric}_in_sample_distribution",
                unit_kind=resolved_kind,
                values=tuple(in_values),
            ),
            out_of_sample_distribution=HistogramReadyArray(
                name=f"{metric}_out_of_sample_distribution",
                unit_kind=resolved_kind,
                values=tuple(out_values),
            ),
        )
    )


# --- coercion helpers --------------------------------------------------------


def _coerce_split(value: object, field: str) -> Result[Fingerprint]:
    """Resolve a split reference to its manifest fingerprint, checking world (AC1, AC6)."""
    if isinstance(value, SplitManifest):
        world = _require_replay_world(value.world, field)
        if is_refusal(world):
            return world
        return Ok(value.fingerprint)
    if isinstance(value, Fingerprint):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            field,
            "a walk-forward window boundary is a governed CT-12 split manifest, named by "
            "fingerprint (an fp1 token, a Fingerprint, or a SplitManifest) (B-8, AD-21)",
            given=repr(value),
        )
    return Fingerprint.try_create(token)


def _coerce_windows(value: object) -> Result[tuple[WalkForwardWindow, ...]]:
    """Coerce and order-check the window sequence (contiguous 0..n-1, one replay world)."""
    if isinstance(value, WalkForwardWindow):
        candidates: Sequence[object] = (value,)
    elif isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "windows",
            "a walk-forward is an ordered sequence of WalkForwardWindow (B-8, AC1)",
            given=repr(type(value).__name__),
        )
    else:
        candidates = cast("Sequence[object]", value)
    if not candidates:
        return invalid("windows", "a walk-forward sequence has at least one window (AC1)")
    out: list[WalkForwardWindow] = []
    world: World | None = None
    for index, item in enumerate(candidates):
        if not isinstance(item, WalkForwardWindow):
            return invalid(
                "windows",
                "each window is a WalkForwardWindow built by WalkForwardWindow.try_create",
                index=index,
                given=repr(type(item).__name__),
            )
        if item.window_index != index:
            return invalid(
                "windows",
                "walk-forward windows are contiguous in declaration order 0..n-1; a gap or "
                "out-of-order index is refused (AC1)",
                position=index,
                window_index=item.window_index,
            )
        if world is None:
            world = item.world
        elif item.world is not world:
            return invalid(
                "windows",
                "every window in one walk-forward shares the same world (replay in V1)",
                index=index,
                expected=world.value,
                given=item.world.value,
            )
        out.append(item)
    return Ok(tuple(out))


def _coerce_window_results(value: object) -> Result[tuple[WalkForwardWindowResult, ...]]:
    if isinstance(value, WalkForwardWindowResult):
        candidates: Sequence[object] = (value,)
    elif isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "window_results",
            "a walk-forward aggregation reads a sequence of WalkForwardWindowResult",
            given=repr(type(value).__name__),
        )
    else:
        candidates = cast("Sequence[object]", value)
    out: list[WalkForwardWindowResult] = []
    for index, item in enumerate(candidates):
        if not isinstance(item, WalkForwardWindowResult):
            return invalid(
                "window_results",
                "each window result is a WalkForwardWindowResult",
                index=index,
                given=repr(type(item).__name__),
            )
        out.append(item)
    return Ok(tuple(out))


def _coerce_metric_map(value: object, field: str) -> Result[Mapping[str, _Quantity]]:
    if not isinstance(value, Mapping):
        return invalid(
            field,
            "a window result maps each metric identity to its exact value (ExactRational or Money)",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[object, object]", value)
    out: dict[str, _Quantity] = {}
    for key, item in body.items():
        token = clean_token(key)
        if token is None or token not in MEASURE_IDENTITIES:
            return invalid(
                field,
                "each metric key is a measure_identity from the V1 core measure set",
                given=repr(key),
                allowed=list(MEASURE_IDENTITIES),
            )
        if not isinstance(item, (ExactRational, Money)):
            return invalid(
                field,
                "a metric value is an exact ExactRational or Money, never a binary float (AD-7)",
                metric=token,
                given=repr(type(item).__name__),
            )
        out[token] = item
    return Ok(out)


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
        return invalid("metrics", "at least one metric is selected to aggregate (AC5)")
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


def _resolve_configurable(config: object, explicit: object, key: str) -> Result[int]:
    """Resolve one UI-editable positive-integer configurable (AC4, SC-07).

    Preferred from ``config`` (a resolved run-config or key->value mapping) via ``key``;
    an explicit value is accepted for a direct call. Neither supplied is a typed refusal —
    there is no ratified value and no baked default.
    """
    if config is not None:
        return require_positive_int(config, key)
    if explicit is not None:
        return _positive_int(explicit, key)
    return invalid(
        key,
        "this walk-forward input is a UI-editable configurable with no ratified value; supply "
        "it via the resolved run-config or explicitly — the module ships no invented default "
        "and no baked WF/OOS battery (SC-07)",
        configurable=key,
        deferred_to=THRESHOLDS_DEFERRED_TO,
    )


def _as_definition(value: object) -> Result[WalkForwardDefinition]:
    if isinstance(value, WalkForwardDefinition):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "definition",
            "a walk-forward is a WalkForwardDefinition or a mapping naming bot/book/bms and a plan",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)
    return WalkForwardDefinition.try_create(
        bot=body.get("bot"),
        book=body.get("book"),
        bms=body.get("bms"),
        plan=body.get("plan"),
    )


def _cite(value: object, field: str) -> Result[str]:
    """Resolve a context ref to its cite token — an ``fp1`` string or a human alias."""
    if isinstance(value, Fingerprint):
        return Ok(value.value)
    token = clean_token(value)
    if token is None:
        return invalid(
            field,
            "a context ref cites a bot/Book/BMS by fp1 or a human alias",
            given=repr(value),
        )
    return Ok(token)


def _refuse_caller_stamp(layer: object, field: str) -> TypedRefusal | None:
    """Refuse a caller-declared ``registry_as_of`` or ``split_fingerprint`` (B-15, AR-59)."""
    if not isinstance(layer, Mapping):
        return None
    body = cast("Mapping[str, object]", layer)
    for key in (REGISTRY_AS_OF_KEY, SPLIT_FINGERPRINT_KEY):
        if key in body:
            return invalid(
                field,
                "registry_as_of and split_fingerprint are stamped by batch admission from the "
                "one frozen as-of and the window's split manifest; neither is caller-declared "
                "(B-15, AR-59)",
                key=key,
            )
    return None


def _require_replay_world(value: object, field: str) -> Result[World]:
    """World must be ``replay``; simulated or live is a policy rejection (B-7, SC-06)."""
    resolved = _coerce_world(value)
    if resolved is None:
        return invalid(
            field,
            "a walk-forward world is one of the closed set live | replay | simulated",
            given=repr(value),
        )
    if resolved is not World.REPLAY:
        return policy(
            field,
            "walk-forward windows run world=replay only in V1; a simulated or live window is "
            "a policy rejection (B-7, SC-06)",
            given=resolved.value,
            allowed=World.REPLAY.value,
        )
    return Ok(resolved)


def _coerce_world(value: object) -> World | None:
    if isinstance(value, World):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return World(token)
    except ValueError:
        return None


def _coerce_evidence_class(value: object) -> Result[str]:
    if isinstance(value, EvidenceClass):
        return Ok(value.value)
    token = clean_token(value)
    if token is not None:
        try:
            return Ok(EvidenceClass(token).value)
        except ValueError:
            pass
    return invalid(
        "evidence_class",
        "a window evidence class is one of the closed set confirmed | unconfirmed | provisional",
        given=repr(value),
        allowed=[member.value for member in EvidenceClass],
    )


def _non_negative_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, "a non-negative exact integer is required", given=repr(value))
    return Ok(value)


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, "a positive exact integer is required", given=repr(value))
    return Ok(value)
