"""Story 30.1 — fingerprinted ``regime_classifier_v1`` design before training.

Records the ruled model family, features, labels, all-session windows, leakage
controls, splits, imbalance treatment, hyperparameter bounds, evaluation,
acceptance/refusal criteria, compute estimate, retraining trigger, and failure
modes. Recovered Kronos/HMM/BOCPD/MS-GARCH candidates are evaluated and remain
unauthoritative. This module mints no trained weights, binds no producer, and
imports no training stack (FR-079; AR-89; DEC-0262; GAP-0051).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qmf.core import Fingerprint, Ok, Result, fingerprint, is_refusal

from qmn.mis._refuse import invalid, policy
from qmn.mis.catalog import (
    REGIME_CLASSIFIER_PRODUCER_ID,
    UNAUTHORITATIVE_CANDIDATES,
    refuse_unauthoritative_candidate,
)

__all__ = [
    "CHOSEN_MODEL_FAMILY",
    "DECLARED_TRADING_SESSIONS",
    "REGIME_CLASS_VOCABULARY",
    "REGIME_DESIGN_ARTIFACT_ID",
    "REGIME_DESIGN_FORMAT_VERSION",
    "REGIME_DESIGN_SURFACE",
    "CandidateFamilyEvaluation",
    "DataWindowContract",
    "EvaluationContract",
    "ExecutableRegimeContract",
    "FeatureContract",
    "HyperparameterBounds",
    "ImbalanceTreatment",
    "LabelContract",
    "LeakageControls",
    "ModelFamilyId",
    "RegimeClass",
    "RegimeClassifierDesign",
    "SplitStrategy",
    "TradingSession",
    "accepted_regime_classifier_design",
    "assert_design_unchanged",
    "evaluate_candidate_families",
    "executable_regime_contract",
    "refuse_design_authority_claim",
    "validate_regime_design_leakage",
]

REGIME_DESIGN_SURFACE: Final[str] = "qmn.mis.regime_design"
REGIME_DESIGN_FORMAT_VERSION: Final[int] = 1
REGIME_DESIGN_ARTIFACT_ID: Final[str] = "regime_classifier_v1_design"
CHOSEN_MODEL_FAMILY: Final[str] = "lightgbm-multiclass"


class ModelFamilyId(StrEnum):
    """Families evaluated for ``regime_classifier_v1``. Recovered names stay named."""

    LIGHTGBM_MULTICLASS = "lightgbm-multiclass"
    KRONOS = "kronos"
    HMM = "hmm"
    BOCPD = "bocpd"
    MS_GARCH = "ms-garch"
    ONLINE_RIVER = "online-river"


class RegimeClass(StrEnum):
    """Closed volatility/risk-state vocabulary — never a direction claim."""

    QUIET = "quiet"
    NORMAL = "normal"
    ELEVATED = "elevated"
    STRESSED = "stressed"


class TradingSession(StrEnum):
    """The three declared FX sessions that every corpus window must cover."""

    ASIA = "asia"
    LONDON = "london"
    NEW_YORK = "new_york"


class ImbalanceTreatment(StrEnum):
    """Ruled imbalance handling — no silent class invention."""

    CLASS_WEIGHT_BALANCED = "class-weight-balanced"
    EXCLUDE_INSUFFICIENT = "exclude-insufficient-evidence"


REGIME_CLASS_VOCABULARY: Final[tuple[str, ...]] = tuple(c.value for c in RegimeClass)
DECLARED_TRADING_SESSIONS: Final[tuple[str, ...]] = tuple(s.value for s in TradingSession)


@dataclass(frozen=True, slots=True)
class CandidateFamilyEvaluation:
    """One evaluated family. Evaluation alone never grants authority (DEC-0262)."""

    family_id: str
    selected: bool
    authority: str
    verdict: str
    rationale: str
    recovered_candidate: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-candidate-family-evaluation",
            "family_id": self.family_id,
            "selected": self.selected,
            "authority": self.authority,
            "verdict": self.verdict,
            "rationale": self.rationale,
            "recovered_candidate": self.recovered_candidate,
        }


@dataclass(frozen=True, slots=True)
class LeakageControls:
    """Hard leakage law for features, labels, and splits (L19/L20; NFR-19)."""

    as_of_only: bool
    no_future_bars: bool
    no_forming_bar: bool
    no_sealed_holdout_peek: bool
    no_post_event_revision: bool
    no_live_outcome_in_train: bool
    purge_bars: int
    embargo_bars: int
    synthetic_edge_forbidden: bool
    calendar_kinds_named_apart: tuple[str, ...]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-leakage-controls",
            "as_of_only": self.as_of_only,
            "no_future_bars": self.no_future_bars,
            "no_forming_bar": self.no_forming_bar,
            "no_sealed_holdout_peek": self.no_sealed_holdout_peek,
            "no_post_event_revision": self.no_post_event_revision,
            "no_live_outcome_in_train": self.no_live_outcome_in_train,
            "purge_bars": self.purge_bars,
            "embargo_bars": self.embargo_bars,
            "synthetic_edge_forbidden": self.synthetic_edge_forbidden,
            "calendar_kinds_named_apart": list(self.calendar_kinds_named_apart),
        }


@dataclass(frozen=True, slots=True)
class DataWindowContract:
    """All-session governed corpus windows cited by Story 30.2."""

    bar_interval: str
    lookback_calendar_days: int
    sessions: tuple[str, ...]
    instruments_scope: str
    source_law: str
    warm_up_bars: int

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-data-window-contract",
            "bar_interval": self.bar_interval,
            "lookback_calendar_days": self.lookback_calendar_days,
            "sessions": list(self.sessions),
            "instruments_scope": self.instruments_scope,
            "source_law": self.source_law,
            "warm_up_bars": self.warm_up_bars,
        }


@dataclass(frozen=True, slots=True)
class SplitStrategy:
    """Time-ordered non-overlapping train/validation/holdout with a no-peek seal."""

    ordering: str
    train_fraction_num: int
    train_fraction_den: int
    validation_fraction_num: int
    validation_fraction_den: int
    holdout_fraction_num: int
    holdout_fraction_den: int
    holdout_sealed: bool
    shuffle_forbidden: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-split-strategy",
            "ordering": self.ordering,
            "train_fraction": [self.train_fraction_num, self.train_fraction_den],
            "validation_fraction": [
                self.validation_fraction_num,
                self.validation_fraction_den,
            ],
            "holdout_fraction": [self.holdout_fraction_num, self.holdout_fraction_den],
            "holdout_sealed": self.holdout_sealed,
            "shuffle_forbidden": self.shuffle_forbidden,
        }


@dataclass(frozen=True, slots=True)
class LabelContract:
    """Deterministic as-of label generation cited by Story 30.3."""

    method: str
    class_vocabulary: tuple[str, ...]
    exclusion_class: str
    horizon_bars: int
    quantile_edges: tuple[str, ...]
    knowledge_time_law: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-label-contract",
            "method": self.method,
            "class_vocabulary": list(self.class_vocabulary),
            "exclusion_class": self.exclusion_class,
            "horizon_bars": self.horizon_bars,
            "quantile_edges": list(self.quantile_edges),
            "knowledge_time_law": self.knowledge_time_law,
        }


@dataclass(frozen=True, slots=True)
class FeatureContract:
    """Causal feature set and input timing / as-of law."""

    feature_ids: tuple[str, ...]
    input_timing: str
    as_of_law: str
    peer_mis_inputs: tuple[str, ...]
    forming_bar_policy: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-feature-contract",
            "feature_ids": list(self.feature_ids),
            "input_timing": self.input_timing,
            "as_of_law": self.as_of_law,
            "peer_mis_inputs": list(self.peer_mis_inputs),
            "forming_bar_policy": self.forming_bar_policy,
        }


@dataclass(frozen=True, slots=True)
class HyperparameterBounds:
    """Search bounds for the offline operator-run training script (Story 30.4)."""

    num_leaves_min: int
    num_leaves_max: int
    learning_rate_num_min: int
    learning_rate_den_min: int
    learning_rate_num_max: int
    learning_rate_den_max: int
    min_data_in_leaf_min: int
    min_data_in_leaf_max: int
    feature_fraction_num_min: int
    feature_fraction_den_min: int
    feature_fraction_num_max: int
    feature_fraction_den_max: int
    max_trials: int
    early_stopping_rounds: int

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-hyperparameter-bounds",
            "num_leaves": [self.num_leaves_min, self.num_leaves_max],
            "learning_rate": [
                [self.learning_rate_num_min, self.learning_rate_den_min],
                [self.learning_rate_num_max, self.learning_rate_den_max],
            ],
            "min_data_in_leaf": [self.min_data_in_leaf_min, self.min_data_in_leaf_max],
            "feature_fraction": [
                [self.feature_fraction_num_min, self.feature_fraction_den_min],
                [self.feature_fraction_num_max, self.feature_fraction_den_max],
            ],
            "max_trials": self.max_trials,
            "early_stopping_rounds": self.early_stopping_rounds,
        }


@dataclass(frozen=True, slots=True)
class EvaluationContract:
    """Measures and acceptance/refusal criteria cited by Stories 30.5 / 30.7."""

    measures: tuple[str, ...]
    per_session_required: bool
    per_class_required: bool
    calibration_check: str
    stability_check: str
    baseline_comparisons: tuple[str, ...]
    acceptance_macro_f1_num: int
    acceptance_macro_f1_den: int
    acceptance_min_per_class_recall_num: int
    acceptance_min_per_class_recall_den: int
    refuse_on_holdout_leak: bool
    refuse_profit_inference: bool
    refuse_live_authority_inference: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-contract",
            "measures": list(self.measures),
            "per_session_required": self.per_session_required,
            "per_class_required": self.per_class_required,
            "calibration_check": self.calibration_check,
            "stability_check": self.stability_check,
            "baseline_comparisons": list(self.baseline_comparisons),
            "acceptance_macro_f1": [
                self.acceptance_macro_f1_num,
                self.acceptance_macro_f1_den,
            ],
            "acceptance_min_per_class_recall": [
                self.acceptance_min_per_class_recall_num,
                self.acceptance_min_per_class_recall_den,
            ],
            "refuse_on_holdout_leak": self.refuse_on_holdout_leak,
            "refuse_profit_inference": self.refuse_profit_inference,
            "refuse_live_authority_inference": self.refuse_live_authority_inference,
        }


@dataclass(frozen=True, slots=True)
class RegimeClassifierDesign:
    """Decision-grade fingerprinted design artifact for ``regime_classifier_v1``."""

    artifact_id: str
    producer_id: str
    format_version: int
    chosen_family: str
    candidate_evaluations: tuple[CandidateFamilyEvaluation, ...]
    feature_contract: FeatureContract
    label_contract: LabelContract
    data_windows: DataWindowContract
    leakage: LeakageControls
    split_strategy: SplitStrategy
    imbalance_treatment: tuple[str, ...]
    hyperparameter_bounds: HyperparameterBounds
    evaluation: EvaluationContract
    compute_estimate: str
    retraining_trigger: str
    failure_modes: tuple[str, ...]
    training_location: str
    artifact_runtime: str
    grants_money_path_authority: bool
    grants_governed_binding: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-classifier-design",
            "artifact_id": self.artifact_id,
            "producer_id": self.producer_id,
            "format_version": self.format_version,
            "chosen_family": self.chosen_family,
            "candidate_evaluations": [row.fp1_identity() for row in self.candidate_evaluations],
            "feature_contract": self.feature_contract.fp1_identity(),
            "label_contract": self.label_contract.fp1_identity(),
            "data_windows": self.data_windows.fp1_identity(),
            "leakage": self.leakage.fp1_identity(),
            "split_strategy": self.split_strategy.fp1_identity(),
            "imbalance_treatment": list(self.imbalance_treatment),
            "hyperparameter_bounds": self.hyperparameter_bounds.fp1_identity(),
            "evaluation": self.evaluation.fp1_identity(),
            "compute_estimate": self.compute_estimate,
            "retraining_trigger": self.retraining_trigger,
            "failure_modes": list(self.failure_modes),
            "training_location": self.training_location,
            "artifact_runtime": self.artifact_runtime,
            "grants_money_path_authority": self.grants_money_path_authority,
            "grants_governed_binding": self.grants_governed_binding,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class ExecutableRegimeContract:
    """Executable data/training/evaluation contract cited by every later 30.x story."""

    design_artifact_id: str
    design_fp: Fingerprint
    chosen_family: str
    class_vocabulary: tuple[str, ...]
    exclusion_class: str
    sessions: tuple[str, ...]
    data_windows: DataWindowContract
    label_contract: LabelContract
    feature_contract: FeatureContract
    leakage: LeakageControls
    split_strategy: SplitStrategy
    imbalance_treatment: tuple[str, ...]
    hyperparameter_bounds: HyperparameterBounds
    evaluation: EvaluationContract
    training_location: str
    artifact_runtime: str
    silent_dimension_change_forbidden: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "executable-regime-contract",
            "design_artifact_id": self.design_artifact_id,
            "design_fp": self.design_fp.value,
            "chosen_family": self.chosen_family,
            "class_vocabulary": list(self.class_vocabulary),
            "exclusion_class": self.exclusion_class,
            "sessions": list(self.sessions),
            "data_windows": self.data_windows.fp1_identity(),
            "label_contract": self.label_contract.fp1_identity(),
            "feature_contract": self.feature_contract.fp1_identity(),
            "leakage": self.leakage.fp1_identity(),
            "split_strategy": self.split_strategy.fp1_identity(),
            "imbalance_treatment": list(self.imbalance_treatment),
            "hyperparameter_bounds": self.hyperparameter_bounds.fp1_identity(),
            "evaluation": self.evaluation.fp1_identity(),
            "training_location": self.training_location,
            "artifact_runtime": self.artifact_runtime,
            "silent_dimension_change_forbidden": self.silent_dimension_change_forbidden,
            "format_version": REGIME_DESIGN_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


def evaluate_candidate_families() -> tuple[CandidateFamilyEvaluation, ...]:
    """Evaluate candidate families. Recovered names keep ``authority=none``."""
    rows: list[CandidateFamilyEvaluation] = [
        CandidateFamilyEvaluation(
            family_id=ModelFamilyId.LIGHTGBM_MULTICLASS.value,
            selected=True,
            authority="design-only",
            verdict="chosen",
            rationale=(
                "Batch-fit / live-infer multiclass booster with a text model "
                "artifact, small CPU footprint, reproducible seed/window "
                "recording, and shadow-rollout-compatible immutable outputs; "
                "matches the offline operator-run script shape (DEC-0262)."
            ),
            recovered_candidate=False,
        ),
        CandidateFamilyEvaluation(
            family_id=ModelFamilyId.KRONOS.value,
            selected=False,
            authority="none",
            verdict="rejected-unauthoritative",
            rationale=(
                "Recovered pretrained foundation candidate; downloads and prior "
                "training grant no authority without fresh ratification (DEC-0262)."
            ),
            recovered_candidate=True,
        ),
        CandidateFamilyEvaluation(
            family_id=ModelFamilyId.HMM.value,
            selected=False,
            authority="none",
            verdict="rejected-unauthoritative",
            rationale=(
                "Recovered HMM candidate; public decode/predict_proba paths are "
                "smoothed and leak future bars unless a custom filtered recursion "
                "is owned; remains unauthoritative (DEC-0262)."
            ),
            recovered_candidate=True,
        ),
        CandidateFamilyEvaluation(
            family_id=ModelFamilyId.BOCPD.value,
            selected=False,
            authority="none",
            verdict="rejected-unauthoritative",
            rationale=(
                "Recovered online change-point candidate; packaging traps and no "
                "current authority until fresh ratification (DEC-0262)."
            ),
            recovered_candidate=True,
        ),
        CandidateFamilyEvaluation(
            family_id=ModelFamilyId.MS_GARCH.value,
            selected=False,
            authority="none",
            verdict="rejected-unauthoritative",
            rationale=(
                "Recovered MS-GARCH candidate is a volatility-forecast family, not "
                "the ruled multiclass risk-state classifier; no authority (DEC-0262)."
            ),
            recovered_candidate=True,
        ),
        CandidateFamilyEvaluation(
            family_id=ModelFamilyId.ONLINE_RIVER.value,
            selected=False,
            authority="none",
            verdict="rejected",
            rationale=(
                "Continuous online learning destroys reproducibility, rollback, "
                "and shadow comparison against an immutable artifact."
            ),
            recovered_candidate=False,
        ),
    ]
    return tuple(rows)


def accepted_regime_classifier_design() -> RegimeClassifierDesign:
    """The accepted Story 30.1 design. Fingerprint is stable; no training occurs."""
    evaluations = evaluate_candidate_families()
    features = FeatureContract(
        feature_ids=(
            "realized_range_pct_20",
            "realized_range_pct_60",
            "return_z_20",
            "return_z_60",
            "atr_ratio_20_60",
            "session_asia",
            "session_london",
            "session_new_york",
            "hour_of_session",
            "spread_state_elevated",
            "spread_state_extreme",
            "liquidity_stress",
            "sqs_hard_block",
            "gap_event",
            "feed_state_degraded",
        ),
        input_timing="sealed-bar-close-as-of",
        as_of_law="feature_row_t uses only observations with knowledge_time <= event_time_t",
        peer_mis_inputs=(
            "spread_state",
            "liquidity_stress_v1",
            "sqs",
            "gap_event",
            "feed_state",
        ),
        forming_bar_policy="refuse-forming-bar",
    )
    labels = LabelContract(
        method="forward-realized-range-quantile-buckets",
        class_vocabulary=REGIME_CLASS_VOCABULARY,
        exclusion_class="insufficient_evidence",
        horizon_bars=12,
        quantile_edges=("0.25", "0.50", "0.75"),
        knowledge_time_law=(
            "label at bar t uses only sealed bars through t+horizon after "
            "purge/embargo; ambiguous rows map to insufficient_evidence"
        ),
    )
    windows = DataWindowContract(
        bar_interval="M5",
        lookback_calendar_days=730,
        sessions=DECLARED_TRADING_SESSIONS,
        instruments_scope="fx-majors-declared-roster",
        source_law="governed-qmf-qmb-tools-only-no-provider-fetch-inside-training",
        warm_up_bars=120,
    )
    leakage = LeakageControls(
        as_of_only=True,
        no_future_bars=True,
        no_forming_bar=True,
        no_sealed_holdout_peek=True,
        no_post_event_revision=True,
        no_live_outcome_in_train=True,
        purge_bars=12,
        embargo_bars=12,
        synthetic_edge_forbidden=True,
        calendar_kinds_named_apart=(
            "market-hours-calendar",
            "day-boundary-calendar",
            "news-calendar",
        ),
    )
    splits = SplitStrategy(
        ordering="time-ordered-non-overlapping",
        train_fraction_num=6,
        train_fraction_den=10,
        validation_fraction_num=2,
        validation_fraction_den=10,
        holdout_fraction_num=2,
        holdout_fraction_den=10,
        holdout_sealed=True,
        shuffle_forbidden=True,
    )
    bounds = HyperparameterBounds(
        num_leaves_min=8,
        num_leaves_max=64,
        learning_rate_num_min=1,
        learning_rate_den_min=100,
        learning_rate_num_max=1,
        learning_rate_den_max=10,
        min_data_in_leaf_min=20,
        min_data_in_leaf_max=200,
        feature_fraction_num_min=6,
        feature_fraction_den_min=10,
        feature_fraction_num_max=1,
        feature_fraction_den_max=1,
        max_trials=40,
        early_stopping_rounds=50,
    )
    evaluation = EvaluationContract(
        measures=(
            "macro_f1",
            "per_class_recall",
            "per_class_precision",
            "per_session_macro_f1",
            "brier_multiclass",
            "transition_confusion",
            "calibration_reliability",
        ),
        per_session_required=True,
        per_class_required=True,
        calibration_check="reliability-diagram-per-class",
        stability_check="seed-rerun-agreement-or-typed-refusal",
        baseline_comparisons=(
            "majority-class",
            "session-conditional-majority",
            "rule-spread-state-proxy",
        ),
        acceptance_macro_f1_num=45,
        acceptance_macro_f1_den=100,
        acceptance_min_per_class_recall_num=30,
        acceptance_min_per_class_recall_den=100,
        refuse_on_holdout_leak=True,
        refuse_profit_inference=True,
        refuse_live_authority_inference=True,
    )
    return RegimeClassifierDesign(
        artifact_id=REGIME_DESIGN_ARTIFACT_ID,
        producer_id=REGIME_CLASSIFIER_PRODUCER_ID,
        format_version=REGIME_DESIGN_FORMAT_VERSION,
        chosen_family=CHOSEN_MODEL_FAMILY,
        candidate_evaluations=evaluations,
        feature_contract=features,
        label_contract=labels,
        data_windows=windows,
        leakage=leakage,
        split_strategy=splits,
        imbalance_treatment=(
            ImbalanceTreatment.CLASS_WEIGHT_BALANCED.value,
            ImbalanceTreatment.EXCLUDE_INSUFFICIENT.value,
        ),
        hyperparameter_bounds=bounds,
        evaluation=evaluation,
        compute_estimate="operator-laptop-cpu-a-few-hours",
        retraining_trigger=(
            "scheduled-calendar-quarter-or-material-distribution-shift-"
            "with-new-design-fp-if-any-dimension-changes"
        ),
        failure_modes=(
            "insufficient-session-coverage",
            "unsupported-class-balance",
            "holdout-seal-breach",
            "reproducibility-mismatch",
            "forming-bar-leak",
            "post-event-revision-leak",
            "synthetic-edge-attempt",
            "unauthoritative-candidate-smuggle",
            "partial-train-register-attempt",
        ),
        training_location="operator-machine-offline-script",
        artifact_runtime="lightgbm-text",
        grants_money_path_authority=False,
        grants_governed_binding=False,
    )


def executable_regime_contract(
    design: RegimeClassifierDesign | None = None,
) -> Result[ExecutableRegimeContract]:
    """Mint the executable contract later Story 30.x artifacts must cite."""
    artifact = design if design is not None else accepted_regime_classifier_design()
    leak = validate_regime_design_leakage(artifact)
    if is_refusal(leak):
        return leak
    authority = refuse_design_authority_claim(artifact)
    if is_refusal(authority):
        return authority
    design_fp = artifact.fingerprint()
    if is_refusal(design_fp):
        return design_fp
    return Ok(
        ExecutableRegimeContract(
            design_artifact_id=artifact.artifact_id,
            design_fp=design_fp.value,
            chosen_family=artifact.chosen_family,
            class_vocabulary=artifact.label_contract.class_vocabulary,
            exclusion_class=artifact.label_contract.exclusion_class,
            sessions=artifact.data_windows.sessions,
            data_windows=artifact.data_windows,
            label_contract=artifact.label_contract,
            feature_contract=artifact.feature_contract,
            leakage=artifact.leakage,
            split_strategy=artifact.split_strategy,
            imbalance_treatment=artifact.imbalance_treatment,
            hyperparameter_bounds=artifact.hyperparameter_bounds,
            evaluation=artifact.evaluation,
            training_location=artifact.training_location,
            artifact_runtime=artifact.artifact_runtime,
            silent_dimension_change_forbidden=True,
        )
    )


def validate_regime_design_leakage(
    design: object,
) -> Result[RegimeClassifierDesign]:
    """Prove the design's leakage and calendar laws before later stories cite it."""
    if not isinstance(design, RegimeClassifierDesign):
        return invalid(
            "design",
            "leakage validation takes a RegimeClassifierDesign",
            given=type(design).__name__,
        )
    leak = design.leakage
    required_flags = (
        ("as_of_only", leak.as_of_only),
        ("no_future_bars", leak.no_future_bars),
        ("no_forming_bar", leak.no_forming_bar),
        ("no_sealed_holdout_peek", leak.no_sealed_holdout_peek),
        ("no_post_event_revision", leak.no_post_event_revision),
        ("no_live_outcome_in_train", leak.no_live_outcome_in_train),
        ("synthetic_edge_forbidden", leak.synthetic_edge_forbidden),
    )
    for name, flag in required_flags:
        if flag is not True:
            return policy(
                name,
                "regime_classifier_v1 design must enforce the leakage law",
                given=flag,
            )
    if leak.purge_bars < design.label_contract.horizon_bars:
        return policy(
            "purge_bars",
            "purge must cover the forward label horizon",
            purge_bars=leak.purge_bars,
            horizon_bars=design.label_contract.horizon_bars,
        )
    if leak.embargo_bars < 1:
        return policy("embargo_bars", "embargo must be a positive bar count")
    calendars = set(leak.calendar_kinds_named_apart)
    required_calendars = {
        "market-hours-calendar",
        "day-boundary-calendar",
        "news-calendar",
    }
    if calendars != required_calendars:
        return policy(
            "calendar_kinds_named_apart",
            "market-hours, day-boundary, and news calendars remain named apart",
            given=sorted(calendars),
            required=sorted(required_calendars),
        )
    sessions = tuple(design.data_windows.sessions)
    if sessions != DECLARED_TRADING_SESSIONS:
        return policy(
            "sessions",
            "all three trading sessions must be declared exactly",
            given=list(sessions),
            required=list(DECLARED_TRADING_SESSIONS),
        )
    if design.split_strategy.shuffle_forbidden is not True:
        return policy(
            "shuffle_forbidden",
            "random shuffle of time-series splits is a leakage policy rejection",
        )
    if design.split_strategy.holdout_sealed is not True:
        return policy("holdout_sealed", "the holdout must be sealed no-peek")
    if design.feature_contract.forming_bar_policy != "refuse-forming-bar":
        return policy(
            "forming_bar_policy",
            "forming bars are refused at feature construction",
            given=design.feature_contract.forming_bar_policy,
        )
    if design.chosen_family != CHOSEN_MODEL_FAMILY:
        return policy(
            "chosen_family",
            "accepted design chooses lightgbm-multiclass",
            given=design.chosen_family,
        )
    selected = [row for row in design.candidate_evaluations if row.selected]
    if len(selected) != 1 or selected[0].family_id != CHOSEN_MODEL_FAMILY:
        return policy(
            "candidate_evaluations",
            "exactly one selected family and it must be lightgbm-multiclass",
        )
    for row in design.candidate_evaluations:
        if row.recovered_candidate and row.authority != "none":
            return policy(
                "authority",
                "recovered/pretrained candidates receive no authority merely by "
                "being evaluated (DEC-0262)",
                family_id=row.family_id,
                authority=row.authority,
            )
        if row.family_id in UNAUTHORITATIVE_CANDIDATES:
            refused = refuse_unauthoritative_candidate(row.family_id)
            if not is_refusal(refused):
                return policy(
                    "family_id",
                    "recovered candidate must still refuse through catalog policy",
                    family_id=row.family_id,
                )
            if row.selected:
                return policy(
                    "selected",
                    "unauthoritative recovered candidates cannot be selected",
                    family_id=row.family_id,
                )
    if design.grants_money_path_authority or design.grants_governed_binding:
        return policy(
            "authority",
            "the design artifact grants neither money-path nor governed binding",
        )
    vocab = tuple(design.label_contract.class_vocabulary)
    if vocab != REGIME_CLASS_VOCABULARY:
        return policy(
            "class_vocabulary",
            "closed regime class vocabulary is quiet|normal|elevated|stressed",
            given=list(vocab),
        )
    if design.label_contract.exclusion_class != "insufficient_evidence":
        return policy(
            "exclusion_class",
            "ambiguous rows use insufficient_evidence rather than an invented default",
            given=design.label_contract.exclusion_class,
        )
    return Ok(design)


def refuse_design_authority_claim(design: object) -> Result[None]:
    """Design acceptance is not training, registration, shadow, or live authority."""
    if not isinstance(design, RegimeClassifierDesign):
        return invalid(
            "design",
            "authority refusal takes a RegimeClassifierDesign",
            given=type(design).__name__,
        )
    if design.grants_money_path_authority or design.grants_governed_binding:
        return policy(
            "authority",
            "regime_classifier_v1 design grants no governed or money-path authority; "
            "Stories 30.4-30.8 own training, registration, shadow, and re-certification",
            producer_id=design.producer_id,
        )
    return Ok(None)


def assert_design_unchanged(
    cited_design_fp: object,
    *,
    design: RegimeClassifierDesign | None = None,
) -> Result[Fingerprint]:
    """Later stories refuse silent design-dimension changes (GAP-0051)."""
    artifact = design if design is not None else accepted_regime_classifier_design()
    validated = validate_regime_design_leakage(artifact)
    if is_refusal(validated):
        return validated
    current = artifact.fingerprint()
    if is_refusal(current):
        return current
    if isinstance(cited_design_fp, Fingerprint):
        cited_value = cited_design_fp.value
    else:
        parsed = Fingerprint.try_create(cited_design_fp)
        if is_refusal(parsed):
            return invalid(
                "cited_design_fp",
                "a cited design fingerprint is an fp1 Fingerprint",
                given=repr(cited_design_fp),
            )
        cited_value = parsed.value.value
    if cited_value != current.value.value:
        return policy(
            "design_fp",
            "no later story silently changes a regime_classifier_v1 design dimension; "
            "a design change requires a new fingerprinted artifact and governed process",
            cited=cited_value,
            current=current.value.value,
        )
    return Ok(current.value)
