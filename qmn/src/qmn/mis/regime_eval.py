"""Story 30.5 - evaluate a trained ``regime_classifier_v1`` candidate.

Evaluation is separated from the multi-hour training transaction. Measures,
uncertainty, per-session/per-class results, calibration/stability checks,
baseline comparisons, error analysis, and acceptance/refusal criteria follow
the Story 30.1 ``EvaluationContract`` exactly. No profit, live authority, or
post-hoc threshold is inferred. Re-running against the same artifacts agrees
or returns a typed reproducibility refusal. Evaluation never mutates the
trained artifact or the sealed holdout (FR-079; NFR-03/19; GAP-0051).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, cast

from qmb.orchestrator.paths import write_bytes_exclusive_no_follow
from qmf.core import Fingerprint, Ok, Result, TypedRefusal, fingerprint, is_refusal
from qmf.data import SegmentRole

from qmn.mis._refuse import clean_token, invalid, policy
from qmn.mis.regime_corpus import CleanedCorpus
from qmn.mis.regime_design import (
    DECLARED_TRADING_SESSIONS,
    REGIME_CLASS_VOCABULARY,
    EvaluationContract,
    ExecutableRegimeContract,
    RegimeClassifierDesign,
    accepted_regime_classifier_design,
    assert_design_unchanged,
    executable_regime_contract,
)
from qmn.mis.regime_labels import EXCLUSION_CLASS, LabeledCorpus
from qmn.mis.regime_train import (
    TRAINING_BACKEND_DETERMINISTIC,
    TRAINING_BACKEND_LIGHTGBM,
    TrainingArtifact,
    TrainingTerminalStatus,
    assert_registerable_training_artifact,
    build_labeled_feature_rows,
    resolve_dependency_lock,
)

__all__ = [
    "EVALUATION_BACKEND_DETERMINISTIC",
    "EVALUATION_BACKEND_LIGHTGBM",
    "REGIME_EVAL_ARTIFACT_ID",
    "REGIME_EVAL_FORMAT_VERSION",
    "REGIME_EVAL_SURFACE",
    "BaselineComparisonResult",
    "ClassMetricBundle",
    "EvaluationConfig",
    "EvaluationMatrix",
    "EvaluationReport",
    "EvaluationSplitScores",
    "EvaluationVerdict",
    "PredictionRow",
    "SessionMetricBundle",
    "assert_evaluation_reproducible",
    "build_evaluation_config",
    "build_evaluation_matrix",
    "main",
    "refuse_artifact_mutation",
    "refuse_holdout_mutation",
    "refuse_live_authority_inference",
    "refuse_post_hoc_threshold",
    "refuse_profit_inference",
    "refuse_reproducibility_mismatch",
    "run_offline_evaluation",
]

REGIME_EVAL_SURFACE: Final[str] = "qmn.mis.regime_eval"
REGIME_EVAL_ARTIFACT_ID: Final[str] = "regime_classifier_v1_evaluation_report"
REGIME_EVAL_FORMAT_VERSION: Final[int] = 1
EVALUATION_BACKEND_DETERMINISTIC: Final[str] = TRAINING_BACKEND_DETERMINISTIC
EVALUATION_BACKEND_LIGHTGBM: Final[str] = TRAINING_BACKEND_LIGHTGBM
_SPLIT_ROLE_HOLDOUT: Final[str] = SegmentRole.SEALED_TEST.value
_SURROGATE_MARKER: Final[str] = "qmx_deterministic_surrogate_lightgbm_text_v1"
_REPORT_FILENAME: Final[str] = "evaluation_report.json"
_CONFIG_FILENAME: Final[str] = "evaluation_config.json"
_PPB: Final[int] = 1_000_000_000

_EvalRow = tuple[str, tuple[float, ...], str, str]


class EvaluationVerdict(StrEnum):
    """Closed vocabulary for the evaluation acceptance decision."""

    ACCEPTED = "accepted"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class PredictionRow:
    """One scored row with class probabilities in ppb (exact integer shares)."""

    row_id: str
    session: str
    true_label: str
    predicted_label: str
    probability_ppb: Mapping[str, int]
    split_role: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-prediction-row",
            "row_id": self.row_id,
            "session": self.session,
            "true_label": self.true_label,
            "predicted_label": self.predicted_label,
            "probability_ppb": dict(sorted(self.probability_ppb.items())),
            "split_role": self.split_role,
        }


PredictFn = Callable[
    [Sequence[_EvalRow], Mapping[str, object]],
    Result[tuple[PredictionRow, ...]],
]


@dataclass(frozen=True, slots=True)
class ClassMetricBundle:
    """Per-class precision/recall with exact rational numerators/denominators."""

    class_label: str
    support: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision_num: int
    precision_den: int
    recall_num: int
    recall_den: int

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-class-metrics",
            "class_label": self.class_label,
            "support": self.support,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": [self.precision_num, self.precision_den],
            "recall": [self.recall_num, self.recall_den],
        }


@dataclass(frozen=True, slots=True)
class SessionMetricBundle:
    """Per-session macro-F1 with support."""

    session: str
    support: int
    macro_f1_num: int
    macro_f1_den: int

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-session-metrics",
            "session": self.session,
            "support": self.support,
            "macro_f1": [self.macro_f1_num, self.macro_f1_den],
        }


@dataclass(frozen=True, slots=True)
class BaselineComparisonResult:
    """One predeclared baseline comparison against the candidate."""

    baseline_id: str
    macro_f1_num: int
    macro_f1_den: int
    candidate_beats_baseline: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-baseline-comparison",
            "baseline_id": self.baseline_id,
            "macro_f1": [self.macro_f1_num, self.macro_f1_den],
            "candidate_beats_baseline": self.candidate_beats_baseline,
        }


@dataclass(frozen=True, slots=True)
class EvaluationSplitScores:
    """Measures for one split under the Story 30.1 evaluation contract."""

    split_role: str
    row_count: int
    excluded_from_scoring: int
    macro_f1_num: int
    macro_f1_den: int
    per_class: tuple[ClassMetricBundle, ...]
    per_session: tuple[SessionMetricBundle, ...]
    brier_ppb: int
    transition_confusion: Mapping[str, int]
    calibration_bins: Mapping[str, tuple[int, int]]
    error_pairs: Mapping[str, int]
    min_per_class_recall_num: int
    min_per_class_recall_den: int
    uncertainty_support: Mapping[str, int]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-split-scores",
            "split_role": self.split_role,
            "row_count": self.row_count,
            "excluded_from_scoring": self.excluded_from_scoring,
            "macro_f1": [self.macro_f1_num, self.macro_f1_den],
            "per_class": [row.fp1_identity() for row in self.per_class],
            "per_session": [row.fp1_identity() for row in self.per_session],
            "brier_ppb": self.brier_ppb,
            "transition_confusion": dict(sorted(self.transition_confusion.items())),
            "calibration_bins": {
                key: list(value) for key, value in sorted(self.calibration_bins.items())
            },
            "error_pairs": dict(sorted(self.error_pairs.items())),
            "min_per_class_recall": [
                self.min_per_class_recall_num,
                self.min_per_class_recall_den,
            ],
            "uncertainty_support": dict(sorted(self.uncertainty_support.items())),
        }


@dataclass(frozen=True, slots=True)
class EvaluationMatrix:
    """Read-only train/validation/holdout feature rows for evaluation."""

    feature_ids: tuple[str, ...]
    class_vocabulary: tuple[str, ...]
    train_rows: tuple[_EvalRow, ...]
    validation_rows: tuple[_EvalRow, ...]
    holdout_rows: tuple[_EvalRow, ...]
    excluded_count: int
    holdout_read_only: bool
    artifact_mutated: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-matrix",
            "feature_ids": list(self.feature_ids),
            "class_vocabulary": list(self.class_vocabulary),
            "train_row_count": len(self.train_rows),
            "validation_row_count": len(self.validation_rows),
            "holdout_row_count": len(self.holdout_rows),
            "train_row_ids": [row[0] for row in self.train_rows],
            "validation_row_ids": [row[0] for row in self.validation_rows],
            "holdout_row_ids": [row[0] for row in self.holdout_rows],
            "train_labels": [row[2] for row in self.train_rows],
            "validation_labels": [row[2] for row in self.validation_rows],
            "holdout_labels": [row[2] for row in self.holdout_rows],
            "feature_payload_fp": _matrix_payload_fp(
                self.train_rows, self.validation_rows, self.holdout_rows
            ),
            "excluded_count": self.excluded_count,
            "holdout_read_only": self.holdout_read_only,
            "artifact_mutated": self.artifact_mutated,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    """Fingerprinted offline evaluation command/config (no credentials)."""

    design_fp: Fingerprint
    contract_fp: Fingerprint
    training_artifact_fp: Fingerprint
    model_fp: Fingerprint
    labeled_fp: Fingerprint
    cleaned_fp: Fingerprint
    splits_fp: Fingerprint
    evaluation_contract: EvaluationContract
    backend: str
    output_dir: str
    command: tuple[str, ...]
    grants_money_path_authority: bool
    grants_governed_binding: bool
    allows_profit_inference: bool
    allows_live_authority_inference: bool
    allows_post_hoc_threshold: bool
    mutates_trained_artifact: bool
    mutates_sealed_holdout: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-config",
            "design_fp": self.design_fp.value,
            "contract_fp": self.contract_fp.value,
            "training_artifact_fp": self.training_artifact_fp.value,
            "model_fp": self.model_fp.value,
            "labeled_fp": self.labeled_fp.value,
            "cleaned_fp": self.cleaned_fp.value,
            "splits_fp": self.splits_fp.value,
            "evaluation_contract": self.evaluation_contract.fp1_identity(),
            "backend": self.backend,
            "output_dir": self.output_dir,
            "command": list(self.command),
            "grants_money_path_authority": self.grants_money_path_authority,
            "grants_governed_binding": self.grants_governed_binding,
            "allows_profit_inference": self.allows_profit_inference,
            "allows_live_authority_inference": self.allows_live_authority_inference,
            "allows_post_hoc_threshold": self.allows_post_hoc_threshold,
            "mutates_trained_artifact": self.mutates_trained_artifact,
            "mutates_sealed_holdout": self.mutates_sealed_holdout,
            "format_version": REGIME_EVAL_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Fingerprinted evaluation report citing Story 30.1 acceptance criteria."""

    artifact_id: str
    verdict: EvaluationVerdict
    cause: str
    config_fp: Fingerprint
    code_fp: Fingerprint
    dependency_lock_fp: str
    design_fp: Fingerprint
    model_fp: Fingerprint
    training_artifact_fp: Fingerprint
    matrix_fp: Fingerprint
    train_scores: EvaluationSplitScores
    validation_scores: EvaluationSplitScores
    holdout_scores: EvaluationSplitScores
    baseline_comparisons: tuple[BaselineComparisonResult, ...]
    calibration_check: str
    stability_check: str
    stability_agreed: bool
    acceptance_macro_f1_num: int
    acceptance_macro_f1_den: int
    acceptance_min_per_class_recall_num: int
    acceptance_min_per_class_recall_den: int
    output_locations: Mapping[str, str]
    trained_artifact_mutated: bool
    sealed_holdout_mutated: bool
    grants_money_path_authority: bool
    grants_governed_binding: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-evaluation-report",
            "artifact_id": self.artifact_id,
            "verdict": self.verdict.value,
            "cause": self.cause,
            "config_fp": self.config_fp.value,
            "code_fp": self.code_fp.value,
            "dependency_lock_fp": self.dependency_lock_fp,
            "design_fp": self.design_fp.value,
            "model_fp": self.model_fp.value,
            "training_artifact_fp": self.training_artifact_fp.value,
            "matrix_fp": self.matrix_fp.value,
            "train_scores": self.train_scores.fp1_identity(),
            "validation_scores": self.validation_scores.fp1_identity(),
            "holdout_scores": self.holdout_scores.fp1_identity(),
            "baseline_comparisons": [row.fp1_identity() for row in self.baseline_comparisons],
            "calibration_check": self.calibration_check,
            "stability_check": self.stability_check,
            "stability_agreed": self.stability_agreed,
            "acceptance_macro_f1": [
                self.acceptance_macro_f1_num,
                self.acceptance_macro_f1_den,
            ],
            "acceptance_min_per_class_recall": [
                self.acceptance_min_per_class_recall_num,
                self.acceptance_min_per_class_recall_den,
            ],
            "output_locations": dict(sorted(self.output_locations.items())),
            "trained_artifact_mutated": self.trained_artifact_mutated,
            "sealed_holdout_mutated": self.sealed_holdout_mutated,
            "grants_money_path_authority": self.grants_money_path_authority,
            "grants_governed_binding": self.grants_governed_binding,
            "format_version": REGIME_EVAL_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())

    def governed_fp1_identity(self) -> dict[str, object]:
        """Path-independent identity for reproducibility (NFR-03)."""
        body = self.fp1_identity()
        body.pop("output_locations", None)
        body.pop("config_fp", None)
        return body

    def governed_fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.governed_fp1_identity())

    def as_jsonable(self) -> dict[str, object]:
        return self.fp1_identity()


def refuse_profit_inference(*, claim: object) -> TypedRefusal:
    """Evaluation never infers profit or trading edge (Story 30.1 contract)."""
    return policy(
        "profit",
        "regime evaluation refuses profit, PnL, or trading-edge inference; "
        "measures stay classification/calibration only",
        failure_id="mis.regime_eval.profit_inference",
        given=repr(claim),
    )


def refuse_live_authority_inference(*, claim: object) -> TypedRefusal:
    """Evaluation acceptance is not live or governed authority (GAP-0051)."""
    return policy(
        "live_authority",
        "evaluation acceptance grants no live consumer, governed binding, or money-path authority",
        failure_id="mis.regime_eval.live_authority_inference",
        given=repr(claim),
    )


def refuse_post_hoc_threshold(*, claim: object) -> TypedRefusal:
    """Thresholds are sealed in Story 30.1; post-hoc changes are refused."""
    return policy(
        "threshold",
        "acceptance thresholds are predeclared in the Story 30.1 evaluation "
        "contract; post-hoc threshold changes are refused",
        failure_id="mis.regime_eval.post_hoc_threshold",
        given=repr(claim),
    )


def refuse_artifact_mutation(*, claim: object) -> TypedRefusal:
    """Evaluation never mutates the trained artifact (NFR-03)."""
    return policy(
        "trained_artifact",
        "evaluation is read-only over the trained candidate; mutation is refused",
        failure_id="mis.regime_eval.artifact_mutation",
        given=repr(claim),
    )


def refuse_holdout_mutation(*, claim: object) -> TypedRefusal:
    """Evaluation may score the sealed holdout but must not mutate it (NFR-19)."""
    return policy(
        "sealed_holdout",
        "evaluation scores the sealed holdout read-only and never mutates it",
        failure_id="mis.regime_eval.holdout_mutation",
        given=repr(claim),
    )


def refuse_reproducibility_mismatch(
    *,
    expected_fp: object,
    observed_fp: object,
) -> TypedRefusal:
    """Identical evaluation inputs must reproduce or refuse (NFR-03)."""
    return policy(
        "reproducibility",
        "rerun against the same artifacts must reproduce the evaluation report "
        "or return an explicit reproducibility refusal with the differing identity",
        failure_id="mis.regime_eval.reproducibility_mismatch",
        expected=repr(expected_fp),
        observed=repr(observed_fp),
    )


def build_evaluation_matrix(
    cleaned: object,
    labeled: object,
    *,
    peer_features: Mapping[str, Mapping[str, float]] | None = None,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    mutate_sealed_holdout: object = False,
) -> Result[EvaluationMatrix]:
    """Build train/validation/holdout feature rows for evaluation (read-only)."""
    if mutate_sealed_holdout is True:
        return refuse_holdout_mutation(claim="mutate_sealed_holdout=True")
    if mutate_sealed_holdout not in (False, None):
        return invalid(
            "mutate_sealed_holdout",
            "mutate_sealed_holdout is False for evaluation",
            given=repr(mutate_sealed_holdout),
        )
    built = build_labeled_feature_rows(
        cleaned,
        labeled,
        roles={
            SegmentRole.TRAIN.value,
            SegmentRole.VALIDATION.value,
            _SPLIT_ROLE_HOLDOUT,
        },
        peer_features=peer_features,
        design=design,
        contract=contract,
    )
    if is_refusal(built):
        return built
    feature_ids, vocabulary, buckets, excluded = built.value
    train_rows = buckets.get(SegmentRole.TRAIN.value, ())
    validation_rows = buckets.get(SegmentRole.VALIDATION.value, ())
    holdout_rows = buckets.get(_SPLIT_ROLE_HOLDOUT, ())
    if not train_rows:
        return policy(
            "train_rows",
            "evaluation requires at least one non-excluded train row",
            failure_id="mis.regime_eval.insufficient_train_rows",
        )
    if not validation_rows:
        return policy(
            "validation_rows",
            "evaluation requires at least one non-excluded validation row",
            failure_id="mis.regime_eval.insufficient_validation_rows",
        )
    if not holdout_rows:
        return policy(
            "holdout_rows",
            "final evaluation requires at least one non-excluded sealed-holdout row",
            failure_id="mis.regime_eval.insufficient_holdout_rows",
        )
    return Ok(
        EvaluationMatrix(
            feature_ids=feature_ids,
            class_vocabulary=vocabulary,
            train_rows=train_rows,
            validation_rows=validation_rows,
            holdout_rows=holdout_rows,
            excluded_count=excluded,
            holdout_read_only=True,
            artifact_mutated=False,
        )
    )


def build_evaluation_config(
    *,
    artifact: object,
    labeled: object,
    cleaned: object,
    output_dir: object,
    backend: object | None = None,
    command: object | None = None,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    allow_profit_inference: object = False,
    allow_live_authority_inference: object = False,
    allow_post_hoc_threshold: object = False,
    mutate_trained_artifact: object = False,
    mutate_sealed_holdout: object = False,
    acceptance_macro_f1_override: object | None = None,
    acceptance_min_per_class_recall_override: object | None = None,
) -> Result[EvaluationConfig]:
    """Mint the fingerprinted evaluation config from Story 30.1-30.4 inputs."""
    blocked = _refuse_eval_allowances(
        allow_profit_inference=allow_profit_inference,
        allow_live_authority_inference=allow_live_authority_inference,
        allow_post_hoc_threshold=allow_post_hoc_threshold,
        mutate_trained_artifact=mutate_trained_artifact,
        mutate_sealed_holdout=mutate_sealed_holdout,
        acceptance_macro_f1_override=acceptance_macro_f1_override,
        acceptance_min_per_class_recall_override=acceptance_min_per_class_recall_override,
    )
    if is_refusal(blocked):
        return blocked
    inputs = _require_eval_inputs(
        artifact=artifact, labeled=labeled, cleaned=cleaned, output_dir=output_dir
    )
    if is_refusal(inputs):
        return inputs
    artifact_obj, labeled_corpus, cleaned_corpus, out = inputs.value
    cited = _cite_eval_design(
        artifact_obj, labeled_corpus, cleaned_corpus, design=design, contract=contract
    )
    if is_refusal(cited):
        return cited
    resolved_contract, eval_contract = cited.value
    backend_token = _eval_backend_token(backend, artifact_obj.model_text)
    if is_refusal(backend_token):
        return backend_token
    fps = _eval_input_fingerprints(artifact_obj, labeled_corpus, cleaned_corpus, resolved_contract)
    if is_refusal(fps):
        return fps
    labeled_fp, cleaned_fp, artifact_fp, contract_fp = fps.value
    cmd = _eval_command_argv(out, command)
    if is_refusal(cmd):
        return cmd
    return Ok(
        EvaluationConfig(
            design_fp=resolved_contract.design_fp,
            contract_fp=contract_fp,
            training_artifact_fp=artifact_fp,
            model_fp=artifact_obj.model_fp,
            labeled_fp=labeled_fp,
            cleaned_fp=cleaned_fp,
            splits_fp=labeled_corpus.splits_fp,
            evaluation_contract=eval_contract,
            backend=backend_token.value,
            output_dir=out,
            command=cmd.value,
            grants_money_path_authority=False,
            grants_governed_binding=False,
            allows_profit_inference=False,
            allows_live_authority_inference=False,
            allows_post_hoc_threshold=False,
            mutates_trained_artifact=False,
            mutates_sealed_holdout=False,
        )
    )


def run_offline_evaluation(
    *,
    artifact: object,
    labeled: object,
    cleaned: object,
    output_dir: object,
    backend: object | None = None,
    command: object | None = None,
    peer_features: Mapping[str, Mapping[str, float]] | None = None,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    lock_path: object | None = None,
    predict_fn: PredictFn | None = None,
    prior_report_fp: object | None = None,
    allow_profit_inference: object = False,
    allow_live_authority_inference: object = False,
    allow_post_hoc_threshold: object = False,
    mutate_trained_artifact: object = False,
    mutate_sealed_holdout: object = False,
    acceptance_macro_f1_override: object | None = None,
    acceptance_min_per_class_recall_override: object | None = None,
) -> Result[EvaluationReport]:
    """Run the offline evaluation script against a completed training artifact.

    Separated from training: never mutates the model bytes or sealed holdout.
    LightGBM prediction is optional and lazy; tests use the deterministic
    surrogate path only (never under poe test).
    """
    model_before = artifact.model_text if isinstance(artifact, TrainingArtifact) else None
    opened = _open_eval_session(
        artifact=artifact,
        labeled=labeled,
        cleaned=cleaned,
        output_dir=output_dir,
        backend=backend,
        command=command,
        design=design,
        contract=contract,
        lock_path=lock_path,
        allow_profit_inference=allow_profit_inference,
        allow_live_authority_inference=allow_live_authority_inference,
        allow_post_hoc_threshold=allow_post_hoc_threshold,
        mutate_trained_artifact=mutate_trained_artifact,
        mutate_sealed_holdout=mutate_sealed_holdout,
        acceptance_macro_f1_override=acceptance_macro_f1_override,
        acceptance_min_per_class_recall_override=acceptance_min_per_class_recall_override,
        peer_features=peer_features,
        predict_fn=predict_fn,
    )
    if is_refusal(opened):
        return opened
    return _finish_offline_evaluation(
        opened.value, artifact=artifact, model_before=model_before, prior_report_fp=prior_report_fp
    )


def assert_evaluation_reproducible(
    report: object,
    prior_report_fp: object,
) -> Result[Fingerprint]:
    """Agree with a prior governed report fingerprint or return a typed refusal.

    Compares the path-independent governed identity (measures, thresholds,
    exclusions, verdict, code/dependency/model citations) so distinct output
    directories do not spuriously refuse reproduction (NFR-03).
    """
    if not isinstance(report, EvaluationReport):
        return invalid(
            "report",
            "reproducibility check takes an EvaluationReport",
            given=type(report).__name__,
        )
    current = report.governed_fingerprint()
    if is_refusal(current):
        return current
    if isinstance(prior_report_fp, Fingerprint):
        expected = prior_report_fp.value
    elif isinstance(prior_report_fp, str) and prior_report_fp.strip():
        expected = prior_report_fp
    else:
        return invalid(
            "prior_report_fp",
            "prior_report_fp is a Fingerprint or non-blank fp1 string",
            given=repr(prior_report_fp),
        )
    if current.value.value != expected:
        return refuse_reproducibility_mismatch(
            expected_fp=expected,
            observed_fp=current.value.value,
        )
    return Ok(current.value)


def main(argv: Sequence[str] | None = None) -> int:
    """Operator entry: ``python -m qmn.mis.regime_eval`` (never a node CLI)."""
    parser = argparse.ArgumentParser(
        prog="qmn.mis.regime_eval",
        description=(
            "Offline operator-machine regime_classifier_v1 evaluation script. "
            "Separated from training; no profit/live authority; no post-hoc "
            "thresholds; never mutates the trained artifact or sealed holdout."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--backend",
        choices=(EVALUATION_BACKEND_DETERMINISTIC, EVALUATION_BACKEND_LIGHTGBM),
        default=EVALUATION_BACKEND_DETERMINISTIC,
    )
    parser.add_argument(
        "--artifact-json",
        type=Path,
        help="Path to a prepared training-artifact JSON envelope (operator-prepared).",
    )
    parser.add_argument(
        "--labeled-json",
        type=Path,
        help="Path to a prepared labeled-corpus JSON envelope (operator-prepared).",
    )
    parser.add_argument(
        "--cleaned-json",
        type=Path,
        help="Path to a prepared cleaned-corpus JSON envelope (operator-prepared).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.artifact_json is None or args.labeled_json is None or args.cleaned_json is None:
        sys.stderr.write(
            "operator-prepared --artifact-json, --labeled-json, and --cleaned-json "
            "are required; this script never fetches providers or opens credentials\n"
        )
        return 2

    sys.stderr.write(
        "JSON envelope loading for operator-prepared evaluation inputs is staged "
        "through run_offline_evaluation with in-memory Story 30.2-30.4 artifacts; "
        "pass objects from Python rather than relying on an undeclared on-disk "
        "schema in Story 30.5. Refusing rather than inventing a loader.\n"
    )
    refusal = policy(
        "cli_loader",
        "Story 30.5 ships the offline evaluation script API; operator JSON "
        "envelope loading stays explicit via Python objects from Stories "
        "30.2-30.4 rather than an invented on-disk schema",
        failure_id="mis.regime_eval.cli_loader",
        artifact_json=str(args.artifact_json),
        labeled_json=str(args.labeled_json),
        cleaned_json=str(args.cleaned_json),
        backend=args.backend,
        output_dir=str(args.output_dir),
    )
    envelope = {
        "status": EvaluationVerdict.REFUSED.value,
        "cause": refusal.context.get("reason"),
        "failure_id": refusal.context.get("failure_id"),
        "command": list(sys.argv if argv is None else argv),
    }
    prepared = _ensure_contained_dir(args.output_dir, contain_within=args.output_dir)
    if not is_refusal(prepared):
        _write_json(
            args.output_dir / _REPORT_FILENAME,
            envelope,
            contain_within=args.output_dir,
            message="evaluation output directory is not writable",
        )
    return 1


# --- internals -----------------------------------------------------------------


def _refuse_eval_allowances(
    *,
    allow_profit_inference: object,
    allow_live_authority_inference: object,
    allow_post_hoc_threshold: object,
    mutate_trained_artifact: object,
    mutate_sealed_holdout: object,
    acceptance_macro_f1_override: object | None,
    acceptance_min_per_class_recall_override: object | None,
) -> Result[None]:
    if allow_profit_inference is True:
        return refuse_profit_inference(claim="allow_profit_inference=True")
    if allow_profit_inference not in (False, None):
        return invalid(
            "allow_profit_inference",
            "allow_profit_inference is False for regime evaluation",
            given=repr(allow_profit_inference),
        )
    if allow_live_authority_inference is True:
        return refuse_live_authority_inference(claim="allow_live_authority_inference=True")
    if allow_live_authority_inference not in (False, None):
        return invalid(
            "allow_live_authority_inference",
            "allow_live_authority_inference is False for regime evaluation",
            given=repr(allow_live_authority_inference),
        )
    thresholds = _refuse_eval_thresholds(
        allow_post_hoc_threshold=allow_post_hoc_threshold,
        acceptance_macro_f1_override=acceptance_macro_f1_override,
        acceptance_min_per_class_recall_override=acceptance_min_per_class_recall_override,
    )
    if is_refusal(thresholds):
        return thresholds
    if mutate_trained_artifact is True:
        return refuse_artifact_mutation(claim="mutate_trained_artifact=True")
    if mutate_trained_artifact not in (False, None):
        return invalid(
            "mutate_trained_artifact",
            "mutate_trained_artifact is False for evaluation",
            given=repr(mutate_trained_artifact),
        )
    if mutate_sealed_holdout is True:
        return refuse_holdout_mutation(claim="mutate_sealed_holdout=True")
    if mutate_sealed_holdout not in (False, None):
        return invalid(
            "mutate_sealed_holdout",
            "mutate_sealed_holdout is False for evaluation",
            given=repr(mutate_sealed_holdout),
        )
    return Ok(None)


def _refuse_eval_thresholds(
    *,
    allow_post_hoc_threshold: object,
    acceptance_macro_f1_override: object | None,
    acceptance_min_per_class_recall_override: object | None,
) -> Result[None]:
    if allow_post_hoc_threshold is True or acceptance_macro_f1_override is not None:
        return refuse_post_hoc_threshold(
            claim={
                "allow_post_hoc_threshold": allow_post_hoc_threshold,
                "acceptance_macro_f1_override": acceptance_macro_f1_override,
            }
        )
    if acceptance_min_per_class_recall_override is not None:
        return refuse_post_hoc_threshold(
            claim={
                "acceptance_min_per_class_recall_override": (
                    acceptance_min_per_class_recall_override
                )
            }
        )
    if allow_post_hoc_threshold not in (False, None):
        return invalid(
            "allow_post_hoc_threshold",
            "allow_post_hoc_threshold is False for regime evaluation",
            given=repr(allow_post_hoc_threshold),
        )
    return Ok(None)


def _require_eval_inputs(
    *,
    artifact: object,
    labeled: object,
    cleaned: object,
    output_dir: object,
) -> Result[tuple[TrainingArtifact, LabeledCorpus, CleanedCorpus, str]]:
    if not isinstance(artifact, TrainingArtifact):
        return invalid(
            "artifact",
            "evaluation takes a completed TrainingArtifact from Story 30.4",
            given=type(artifact).__name__,
        )
    registerable = assert_registerable_training_artifact(artifact)
    if is_refusal(registerable):
        return policy(
            "artifact",
            "evaluation requires a completed registerable training artifact",
            failure_id="mis.regime_eval.incomplete_training",
            status=artifact.record.status.value,
        )
    if artifact.record.status is not TrainingTerminalStatus.COMPLETED:
        return policy(
            "artifact",
            "evaluation requires a completed training terminal record",
            failure_id="mis.regime_eval.incomplete_training",
            status=artifact.record.status.value,
        )
    if not isinstance(labeled, LabeledCorpus):
        return invalid(
            "labeled",
            "evaluation takes a LabeledCorpus from Story 30.3",
            given=type(labeled).__name__,
        )
    if not isinstance(cleaned, CleanedCorpus):
        return invalid(
            "cleaned",
            "evaluation takes the CleanedCorpus cited by the labeled corpus",
            given=type(cleaned).__name__,
        )
    out = clean_token(output_dir)
    if out is None:
        return invalid("output_dir", "output_dir is a non-blank path string")
    return Ok((artifact, labeled, cleaned, out))


def _cite_eval_design(
    artifact: TrainingArtifact,
    labeled: LabeledCorpus,
    cleaned: CleanedCorpus,
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[tuple[ExecutableRegimeContract, EvaluationContract]]:
    resolved = _resolve_contract(design=design, contract=contract)
    if is_refusal(resolved):
        return resolved
    design_artifact, resolved_contract = resolved.value
    if labeled.design_fp.value != resolved_contract.design_fp.value:
        return policy(
            "design_fp",
            "labeled corpus must cite the accepted Story 30.1 design fingerprint",
            labeled=labeled.design_fp.value,
            design=resolved_contract.design_fp.value,
        )
    if cleaned.design_fp.value != resolved_contract.design_fp.value:
        return policy(
            "design_fp",
            "cleaned corpus must cite the accepted Story 30.1 design fingerprint",
            cleaned=cleaned.design_fp.value,
            design=resolved_contract.design_fp.value,
        )
    if artifact.design_fp.value != resolved_contract.design_fp.value:
        return policy(
            "design_fp",
            "training artifact must cite the accepted Story 30.1 design fingerprint",
            artifact=artifact.design_fp.value,
            design=resolved_contract.design_fp.value,
        )
    unchanged = assert_design_unchanged(labeled.design_fp, design=design_artifact)
    if is_refusal(unchanged):
        return unchanged
    eval_contract = resolved_contract.evaluation
    if eval_contract.refuse_profit_inference is not True:
        return refuse_profit_inference(claim="design.refuse_profit_inference=False")
    if eval_contract.refuse_live_authority_inference is not True:
        return refuse_live_authority_inference(claim="design.refuse_live_authority_inference=False")
    if eval_contract.refuse_on_holdout_leak is not True:
        return policy(
            "holdout_leak",
            "evaluation contract must refuse holdout leak",
            failure_id="mis.regime_eval.holdout_leak",
        )
    return Ok((resolved_contract, eval_contract))


def _eval_backend_token(backend: object | None, model_text: str) -> Result[str]:
    backend_token = EVALUATION_BACKEND_DETERMINISTIC if backend is None else clean_token(backend)
    if backend_token not in {
        EVALUATION_BACKEND_DETERMINISTIC,
        EVALUATION_BACKEND_LIGHTGBM,
    }:
        return invalid(
            "backend",
            "backend is deterministic-surrogate or lightgbm",
            given=repr(backend),
        )
    if backend_token == EVALUATION_BACKEND_LIGHTGBM and _model_is_surrogate(model_text):
        backend_token = EVALUATION_BACKEND_DETERMINISTIC
    return Ok(backend_token)


def _eval_input_fingerprints(
    artifact: TrainingArtifact,
    labeled: LabeledCorpus,
    cleaned: CleanedCorpus,
    resolved_contract: ExecutableRegimeContract,
) -> Result[tuple[Fingerprint, Fingerprint, Fingerprint, Fingerprint]]:
    labeled_fp = labeled.fingerprint()
    if is_refusal(labeled_fp):
        return labeled_fp
    cleaned_fp = cleaned.fingerprint()
    if is_refusal(cleaned_fp):
        return cleaned_fp
    if labeled.cleaned_fp.value != cleaned_fp.value.value:
        return policy(
            "cleaned_fp",
            "cleaned corpus fingerprint must match the labeled corpus citation",
            labeled=labeled.cleaned_fp.value,
            cleaned=cleaned_fp.value.value,
        )
    artifact_fp = fingerprint(
        {
            "class": "regime-training-artifact-cite",
            "artifact_id": artifact.artifact_id,
            "model_fp": artifact.model_fp.value,
            "config_fp": artifact.config_fp.value,
            "code_fp": artifact.code_fp.value,
            "matrix_fp": artifact.matrix_fp.value,
            "design_fp": artifact.design_fp.value,
            "registerable": artifact.registerable,
            "status": artifact.record.status.value,
        }
    )
    if is_refusal(artifact_fp):
        return artifact_fp
    contract_fp = resolved_contract.fingerprint()
    if is_refusal(contract_fp):
        return contract_fp
    return Ok((labeled_fp.value, cleaned_fp.value, artifact_fp.value, contract_fp.value))


def _eval_command_argv(out: str, command: object | None) -> Result[tuple[str, ...]]:
    if command is None:
        return Ok(("python", "-m", "qmn.mis.regime_eval", "--output-dir", out))
    if isinstance(command, Sequence) and not isinstance(command, (str, bytes)):
        tokens = tuple(str(item) for item in cast("Sequence[object]", command))
        if not tokens:
            return invalid("command", "command is a non-empty argv sequence")
        return Ok(tokens)
    return invalid("command", "command is an argv sequence", given=type(command).__name__)


@dataclass(frozen=True, slots=True)
class _EvalSession:
    config: EvaluationConfig
    config_fp: Fingerprint
    code_fp: Fingerprint
    lock_fp: str
    out_root: Path
    matrix: EvaluationMatrix
    matrix_fp: Fingerprint
    artifact: TrainingArtifact
    predict: PredictFn


def _open_eval_session(
    *,
    artifact: object,
    labeled: object,
    cleaned: object,
    output_dir: object,
    backend: object | None,
    command: object | None,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
    lock_path: object | None,
    allow_profit_inference: object,
    allow_live_authority_inference: object,
    allow_post_hoc_threshold: object,
    mutate_trained_artifact: object,
    mutate_sealed_holdout: object,
    acceptance_macro_f1_override: object | None,
    acceptance_min_per_class_recall_override: object | None,
    peer_features: Mapping[str, Mapping[str, float]] | None,
    predict_fn: PredictFn | None,
) -> Result[_EvalSession]:
    config = build_evaluation_config(
        artifact=artifact,
        labeled=labeled,
        cleaned=cleaned,
        output_dir=output_dir,
        backend=backend,
        command=command,
        design=design,
        contract=contract,
        allow_profit_inference=allow_profit_inference,
        allow_live_authority_inference=allow_live_authority_inference,
        allow_post_hoc_threshold=allow_post_hoc_threshold,
        mutate_trained_artifact=mutate_trained_artifact,
        mutate_sealed_holdout=mutate_sealed_holdout,
        acceptance_macro_f1_override=acceptance_macro_f1_override,
        acceptance_min_per_class_recall_override=acceptance_min_per_class_recall_override,
    )
    if is_refusal(config):
        return config
    prepared = _eval_session_fps(config.value, lock_path=lock_path)
    if is_refusal(prepared):
        return prepared
    config_fp, code_fp, lock_fp, out_root = prepared.value
    matrix = build_evaluation_matrix(
        cleaned,
        labeled,
        peer_features=peer_features,
        design=design,
        contract=contract,
        mutate_sealed_holdout=False,
    )
    if is_refusal(matrix):
        return matrix
    matrix_fp = matrix.value.fingerprint()
    if is_refusal(matrix_fp):
        return matrix_fp
    if not isinstance(artifact, TrainingArtifact):
        return invalid(
            "artifact",
            "evaluation takes a completed TrainingArtifact from Story 30.4",
            given=type(artifact).__name__,
        )
    selected: Result[PredictFn] = (
        Ok(predict_fn)
        if predict_fn is not None
        else _select_predictor(config.value.backend, artifact.model_text)
    )
    if is_refusal(selected):
        return selected
    return Ok(
        _EvalSession(
            config=config.value,
            config_fp=config_fp,
            code_fp=code_fp,
            lock_fp=lock_fp,
            out_root=out_root,
            matrix=matrix.value,
            matrix_fp=matrix_fp.value,
            artifact=artifact,
            predict=selected.value,
        )
    )


def _eval_session_fps(
    config: EvaluationConfig, *, lock_path: object | None
) -> Result[tuple[Fingerprint, Fingerprint, str, Path]]:
    code_fp = _evaluation_code_fp()
    if is_refusal(code_fp):
        return code_fp
    config_fp = config.fingerprint()
    if is_refusal(config_fp):
        return config_fp
    lock = resolve_dependency_lock(lock_path=lock_path)
    if is_refusal(lock):
        return lock
    out_root = Path(config.output_dir)
    prepared = _ensure_contained_dir(out_root, contain_within=out_root)
    if is_refusal(prepared):
        return prepared
    written = _write_json(
        out_root / _CONFIG_FILENAME,
        config.fp1_identity(),
        contain_within=out_root,
        message="evaluation output directory is not writable",
    )
    if is_refusal(written):
        return written
    return Ok((config_fp.value, code_fp.value, lock.value.lock_fp, out_root))


def _finish_offline_evaluation(
    session: _EvalSession,
    *,
    artifact: object,
    model_before: str | None,
    prior_report_fp: object | None,
) -> Result[EvaluationReport]:
    scored = _eval_split_scores(session)
    if is_refusal(scored):
        return scored
    train_scores, validation_scores, holdout_scores, baselines, stability_agreed = scored.value
    if (
        model_before is not None
        and isinstance(artifact, TrainingArtifact)
        and artifact.model_text != model_before
    ):
        return refuse_artifact_mutation(claim="model_text_changed")
    verdict, cause = _acceptance_verdict(holdout_scores, session.config.evaluation_contract)
    report = _mint_eval_report(
        session,
        train_scores=train_scores,
        validation_scores=validation_scores,
        holdout_scores=holdout_scores,
        baselines=baselines,
        stability_agreed=stability_agreed,
        verdict=verdict,
        cause=cause,
    )
    governed_fp = report.governed_fingerprint()
    if is_refusal(governed_fp):
        return governed_fp
    if prior_report_fp is not None:
        check = assert_evaluation_reproducible(report, prior_report_fp)
        if is_refusal(check):
            return check
    written_report = _write_json(
        session.out_root / _REPORT_FILENAME,
        report.as_jsonable(),
        contain_within=session.out_root,
        message="evaluation report could not be written",
    )
    if is_refusal(written_report):
        return written_report
    return Ok(report)


def _eval_split_scores(
    session: _EvalSession,
) -> Result[
    tuple[
        EvaluationSplitScores,
        EvaluationSplitScores,
        EvaluationSplitScores,
        tuple[BaselineComparisonResult, ...],
        bool,
    ]
]:
    preds = _eval_predictions(session)
    if is_refusal(preds):
        return preds
    train_preds, valid_preds, holdout_preds, stability_agreed = preds.value
    train_scores = _score_split(
        train_preds,
        split_role=SegmentRole.TRAIN.value,
        vocabulary=session.matrix.class_vocabulary,
        feature_ids=session.matrix.feature_ids,
    )
    validation_scores = _score_split(
        valid_preds,
        split_role=SegmentRole.VALIDATION.value,
        vocabulary=session.matrix.class_vocabulary,
        feature_ids=session.matrix.feature_ids,
    )
    holdout_scores = _score_split(
        holdout_preds,
        split_role=_SPLIT_ROLE_HOLDOUT,
        vocabulary=session.matrix.class_vocabulary,
        feature_ids=session.matrix.feature_ids,
    )
    if is_refusal(train_scores):
        return train_scores
    if is_refusal(validation_scores):
        return validation_scores
    if is_refusal(holdout_scores):
        return holdout_scores
    baselines = _baseline_comparisons(
        holdout_rows=session.matrix.holdout_rows,
        train_rows=session.matrix.train_rows,
        candidate_macro=(
            holdout_scores.value.macro_f1_num,
            holdout_scores.value.macro_f1_den,
        ),
        baseline_ids=session.config.evaluation_contract.baseline_comparisons,
        feature_ids=session.matrix.feature_ids,
        vocabulary=session.matrix.class_vocabulary,
    )
    if is_refusal(baselines):
        return baselines
    return Ok(
        (
            train_scores.value,
            validation_scores.value,
            holdout_scores.value,
            baselines.value,
            stability_agreed,
        )
    )


def _eval_predictions(
    session: _EvalSession,
) -> Result[
    tuple[tuple[PredictionRow, ...], tuple[PredictionRow, ...], tuple[PredictionRow, ...], bool]
]:
    context: dict[str, object] = {
        "model_text": session.artifact.model_text,
        "model_fp": session.artifact.model_fp.value,
        "feature_ids": list(session.matrix.feature_ids),
        "class_vocabulary": list(session.matrix.class_vocabulary),
        "train_rows": session.matrix.train_rows,
        "backend": session.config.backend,
    }
    train_preds = session.predict(
        session.matrix.train_rows, {**context, "split_role": SegmentRole.TRAIN.value}
    )
    if is_refusal(train_preds):
        return train_preds
    valid_preds = session.predict(
        session.matrix.validation_rows, {**context, "split_role": SegmentRole.VALIDATION.value}
    )
    if is_refusal(valid_preds):
        return valid_preds
    holdout_ctx = {**context, "split_role": _SPLIT_ROLE_HOLDOUT}
    holdout_preds = session.predict(session.matrix.holdout_rows, holdout_ctx)
    if is_refusal(holdout_preds):
        return holdout_preds
    holdout_again = session.predict(session.matrix.holdout_rows, holdout_ctx)
    if is_refusal(holdout_again):
        return holdout_again
    stability_agreed = _predictions_agree(holdout_preds.value, holdout_again.value)
    if not stability_agreed:
        return refuse_reproducibility_mismatch(
            expected_fp=_predictions_fp(holdout_preds.value),
            observed_fp=_predictions_fp(holdout_again.value),
        )
    return Ok((train_preds.value, valid_preds.value, holdout_preds.value, stability_agreed))


def _mint_eval_report(
    session: _EvalSession,
    *,
    train_scores: EvaluationSplitScores,
    validation_scores: EvaluationSplitScores,
    holdout_scores: EvaluationSplitScores,
    baselines: tuple[BaselineComparisonResult, ...],
    stability_agreed: bool,
    verdict: EvaluationVerdict,
    cause: str,
) -> EvaluationReport:
    eval_contract = session.config.evaluation_contract
    locations = {
        "output_dir": session.config.output_dir,
        "config": f"{session.config.output_dir}/{_CONFIG_FILENAME}",
        "report": f"{session.config.output_dir}/{_REPORT_FILENAME}",
    }
    return EvaluationReport(
        artifact_id=REGIME_EVAL_ARTIFACT_ID,
        verdict=verdict,
        cause=cause,
        config_fp=session.config_fp,
        code_fp=session.code_fp,
        dependency_lock_fp=session.lock_fp,
        design_fp=session.config.design_fp,
        model_fp=session.config.model_fp,
        training_artifact_fp=session.config.training_artifact_fp,
        matrix_fp=session.matrix_fp,
        train_scores=train_scores,
        validation_scores=validation_scores,
        holdout_scores=holdout_scores,
        baseline_comparisons=baselines,
        calibration_check=eval_contract.calibration_check,
        stability_check=eval_contract.stability_check,
        stability_agreed=stability_agreed,
        acceptance_macro_f1_num=eval_contract.acceptance_macro_f1_num,
        acceptance_macro_f1_den=eval_contract.acceptance_macro_f1_den,
        acceptance_min_per_class_recall_num=eval_contract.acceptance_min_per_class_recall_num,
        acceptance_min_per_class_recall_den=eval_contract.acceptance_min_per_class_recall_den,
        output_locations=locations,
        trained_artifact_mutated=False,
        sealed_holdout_mutated=False,
        grants_money_path_authority=False,
        grants_governed_binding=False,
    )


def _resolve_contract(
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[tuple[RegimeClassifierDesign, ExecutableRegimeContract]]:
    artifact = design if design is not None else accepted_regime_classifier_design()
    if contract is None:
        built = executable_regime_contract(artifact)
        if is_refusal(built):
            return built
        return Ok((artifact, built.value))
    current = artifact.fingerprint()
    if is_refusal(current):
        return current
    if contract.design_fp.value != current.value.value:
        return policy(
            "contract",
            "executable contract must cite the supplied design fingerprint",
            contract=contract.design_fp.value,
            design=current.value.value,
        )
    return Ok((artifact, contract))


def _evaluation_code_fp() -> Result[Fingerprint]:
    return fingerprint(
        {
            "class": "regime-evaluation-code",
            "surface": REGIME_EVAL_SURFACE,
            "artifact_id": REGIME_EVAL_ARTIFACT_ID,
            "format_version": REGIME_EVAL_FORMAT_VERSION,
        }
    )


def _matrix_payload_fp(
    train_rows: Sequence[_EvalRow],
    validation_rows: Sequence[_EvalRow],
    holdout_rows: Sequence[_EvalRow],
) -> str:
    parts: list[str] = []
    for role, rows in (
        ("train", train_rows),
        ("validation", validation_rows),
        ("holdout", holdout_rows),
    ):
        for row_id, features, label, session in rows:
            quantized = ",".join(f"{value:.12g}" for value in features)
            parts.append(f"{role}:{row_id}:{label}:{session}:{quantized}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"fp1:sha256:{digest}"


def _output_dir_refusal(
    path: Path,
    *,
    message: str,
    given: object | None = None,
    errno: object | None = None,
) -> TypedRefusal:
    extra: dict[str, object] = {
        "path": str(path),
        "failure_id": "mis.regime_eval.output_dir",
    }
    if given is not None:
        extra["given"] = given
    if errno is not None:
        extra["errno"] = errno
    return policy("output_dir", message, **extra)


def _contained_pair(path: Path, contain_within: Path) -> Result[tuple[Path, Path]]:
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(contain_within))
    except OSError as exc:
        return _output_dir_refusal(
            path,
            message="evaluation output directory is not writable",
            given=type(exc).__name__,
            errno=getattr(exc, "errno", None),
        )
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        return _output_dir_refusal(
            path,
            message="evaluation output directory is not writable",
            given="symlink-or-escape",
        )
    return Ok((resolved, root_real))


def _ensure_contained_dir(path: Path, *, contain_within: Path) -> Result[None]:
    contained = _contained_pair(path, contain_within)
    if is_refusal(contained):
        return contained
    try:
        path.mkdir(  # skylos: ignore[SKY-D215] contained, no-follow
            parents=True,
            exist_ok=True,
        )
    except OSError as exc:
        return _output_dir_refusal(
            path,
            message="evaluation output directory is not writable",
            given=type(exc).__name__,
            errno=getattr(exc, "errno", None),
        )
    return Ok(None)


def _unlink_contained_regular(
    path: Path,
    *,
    contain_within: Path,
    missing_ok: bool = False,
) -> Result[None]:
    contained = _contained_pair(path, contain_within)
    if is_refusal(contained):
        return contained
    if not path.exists() and not path.is_symlink():
        if missing_ok:
            return Ok(None)
        return _output_dir_refusal(
            path,
            message="evaluation output directory is not writable",
            given="missing",
        )
    if path.is_symlink() or not path.is_file():
        return _output_dir_refusal(
            path,
            message="evaluation output directory is not writable",
            given="symlink-or-non-regular",
        )
    try:
        os.unlink(path)  # skylos: ignore[SKY-D215] contained, no-follow
    except OSError as exc:
        return _output_dir_refusal(
            path,
            message="evaluation output directory is not writable",
            given=type(exc).__name__,
            errno=getattr(exc, "errno", None),
        )
    return Ok(None)


def _write_json(
    path: Path,
    payload: Mapping[str, object],
    *,
    contain_within: Path,
    message: str,
) -> Result[None]:
    data = (json.dumps(payload, sort_keys=True, indent=2, separators=(",", ": ")) + "\n").encode(
        "utf-8"
    )
    unlinked = _unlink_contained_regular(path, contain_within=contain_within, missing_ok=True)
    if is_refusal(unlinked):
        return unlinked
    written = write_bytes_exclusive_no_follow(
        path, data, contain_within=contain_within, field="output_dir"
    )
    if is_refusal(written):
        return _output_dir_refusal(path, message=message, given=written.context.get("reason"))
    return Ok(None)


def _model_is_surrogate(model_text: str) -> bool:
    return model_text.startswith(_SURROGATE_MARKER)


def _select_predictor(backend: str, model_text: str) -> Result[PredictFn]:
    if _model_is_surrogate(model_text) or backend == EVALUATION_BACKEND_DETERMINISTIC:
        return Ok(_deterministic_surrogate_predict)
    if backend == EVALUATION_BACKEND_LIGHTGBM:
        if importlib.util.find_spec("lightgbm") is None:
            return policy(
                "backend",
                "lightgbm backend requested but lightgbm is not installed on this "
                "operator machine; install locally or evaluate a "
                "deterministic-surrogate artifact",
                failure_id="mis.regime_eval.lightgbm_missing",
            )
        return Ok(_lightgbm_predict)
    return invalid("backend", "unknown evaluation backend", given=backend)


def _deterministic_surrogate_predict(
    rows: Sequence[_EvalRow],
    context: Mapping[str, object],
) -> Result[tuple[PredictionRow, ...]]:
    """Majority-class predictor matching the Story 30.4 surrogate ranking rule."""
    vocabulary = _vocab_from_context(context)
    train_obj = context.get("train_rows", ())
    train_rows: Sequence[_EvalRow]
    if isinstance(train_obj, Sequence) and not isinstance(train_obj, (str, bytes)):
        train_rows = cast("Sequence[_EvalRow]", train_obj)
    else:
        train_rows = ()
    majority = _majority_label([row[2] for row in train_rows], vocabulary)
    split_role = str(context.get("split_role", "unknown"))
    probs = {label: (_PPB if label == majority else 0) for label in vocabulary}
    # Soften residual mass onto remaining classes for calibration checks when
    # majority is empty (should not happen with non-empty train).
    if majority not in vocabulary:
        share = _PPB // max(1, len(vocabulary))
        probs = dict.fromkeys(vocabulary, share)
        remainder = _PPB - share * len(vocabulary)
        if vocabulary:
            probs[vocabulary[0]] += remainder
        majority = vocabulary[0] if vocabulary else EXCLUSION_CLASS
    out: list[PredictionRow] = []
    for row_id, _features, true_label, session in rows:
        out.append(
            PredictionRow(
                row_id=row_id,
                session=session,
                true_label=true_label,
                predicted_label=majority,
                probability_ppb=dict(probs),
                split_role=split_role,
            )
        )
    return Ok(tuple(out))


def _lightgbm_predict(
    rows: Sequence[_EvalRow],
    context: Mapping[str, object],
) -> Result[tuple[PredictionRow, ...]]:
    """Lazy LightGBM predict for operator-machine evaluation (never poe test)."""
    import lightgbm as lgb  # noqa: PLC0415  # pyright: ignore[reportMissingImports]

    lgb_api: Any = lgb
    model_text = context.get("model_text")
    if not isinstance(model_text, str) or not model_text.strip():
        return invalid("model_text", "lightgbm evaluation requires model_text")
    vocabulary = _vocab_from_context(context)
    booster = lgb_api.Booster(model_str=model_text)
    features = [list(row[1]) for row in rows]
    if not features:
        return Ok(())
    raw = cast("Sequence[Sequence[float]]", booster.predict(features))
    split_role = str(context.get("split_role", "unknown"))
    out: list[PredictionRow] = []
    for index, row in enumerate(rows):
        row_id, _feats, true_label, session = row
        scores = list(raw[index]) if index < len(raw) else [0.0] * len(vocabulary)
        if len(scores) < len(vocabulary):
            scores = scores + [0.0] * (len(vocabulary) - len(scores))
        probs = _float_scores_to_ppb(scores[: len(vocabulary)], vocabulary)
        predicted = max(vocabulary, key=lambda label: probs.get(label, 0))
        out.append(
            PredictionRow(
                row_id=row_id,
                session=session,
                true_label=true_label,
                predicted_label=predicted,
                probability_ppb=probs,
                split_role=split_role,
            )
        )
    return Ok(tuple(out))


def _vocab_from_context(context: Mapping[str, object]) -> tuple[str, ...]:
    vocab_obj = context.get("class_vocabulary", list(REGIME_CLASS_VOCABULARY))
    if isinstance(vocab_obj, Sequence) and not isinstance(vocab_obj, (str, bytes)):
        return tuple(str(item) for item in cast("Sequence[object]", vocab_obj))
    return REGIME_CLASS_VOCABULARY


def _majority_label(labels: Sequence[str], vocabulary: Sequence[str]) -> str:
    counts: dict[str, int] = dict.fromkeys(vocabulary, 0)
    for label in labels:
        if label in counts:
            counts[label] += 1
        else:
            counts[label] = counts.get(label, 0) + 1
    if not counts:
        return vocabulary[0] if vocabulary else EXCLUSION_CLASS
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def _session_majority(
    train_rows: Sequence[_EvalRow],
    session: str,
    vocabulary: Sequence[str],
) -> str:
    labels = [row[2] for row in train_rows if row[3] == session]
    if not labels:
        return _majority_label([row[2] for row in train_rows], vocabulary)
    return _majority_label(labels, vocabulary)


def _float_scores_to_ppb(
    scores: Sequence[float],
    vocabulary: Sequence[str],
) -> dict[str, int]:
    clipped = [max(0.0, float(score)) for score in scores]
    total = sum(clipped)
    if total <= 0.0:
        share = _PPB // max(1, len(vocabulary))
        probs = dict.fromkeys(vocabulary, share)
        remainder = _PPB - share * len(vocabulary)
        if vocabulary:
            probs[vocabulary[0]] += remainder
        return probs
    raw = [int((score * _PPB) // total) for score in clipped]
    while len(raw) < len(vocabulary):
        raw.append(0)
    raw = raw[: len(vocabulary)]
    drift = _PPB - sum(raw)
    if raw:
        raw[0] += drift
    return {label: raw[index] for index, label in enumerate(vocabulary)}


def _predictions_agree(
    left: Sequence[PredictionRow],
    right: Sequence[PredictionRow],
) -> bool:
    if len(left) != len(right):
        return False
    return all(a.fp1_identity() == b.fp1_identity() for a, b in zip(left, right, strict=True))


def _predictions_fp(rows: Sequence[PredictionRow]) -> str:
    payload = [row.fp1_identity() for row in rows]
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"fp1:sha256:{digest}"


def _score_split(
    predictions: Sequence[PredictionRow],
    *,
    split_role: str,
    vocabulary: Sequence[str],
    feature_ids: Sequence[str],
) -> Result[EvaluationSplitScores]:
    _ = feature_ids
    if not predictions:
        return policy(
            "predictions",
            "split scoring requires at least one prediction row",
            split_role=split_role,
            failure_id="mis.regime_eval.empty_predictions",
        )
    per_class = _per_class_metrics(predictions, vocabulary)
    macro_num, macro_den = _macro_f1(per_class)
    per_session = _per_session_metrics(predictions, vocabulary)
    brier = _brier_ppb(predictions, vocabulary)
    transitions = _transition_confusion(predictions)
    calibration = _calibration_bins(predictions, vocabulary)
    errors = _error_pairs(predictions)
    recalls = [(row.recall_num, row.recall_den) for row in per_class if row.support > 0]
    if recalls:
        min_recall = min(recalls, key=lambda pair: (pair[0] * 10_000) // max(1, pair[1]))
    else:
        min_recall = (0, 1)
    support = dict.fromkeys(vocabulary, 0)
    for row in predictions:
        support[row.true_label] = support.get(row.true_label, 0) + 1
    return Ok(
        EvaluationSplitScores(
            split_role=split_role,
            row_count=len(predictions),
            excluded_from_scoring=0,
            macro_f1_num=macro_num,
            macro_f1_den=macro_den,
            per_class=per_class,
            per_session=per_session,
            brier_ppb=brier,
            transition_confusion=transitions,
            calibration_bins=calibration,
            error_pairs=errors,
            min_per_class_recall_num=min_recall[0],
            min_per_class_recall_den=min_recall[1],
            uncertainty_support=support,
        )
    )


def _per_class_metrics(
    predictions: Sequence[PredictionRow],
    vocabulary: Sequence[str],
) -> tuple[ClassMetricBundle, ...]:
    rows: list[ClassMetricBundle] = []
    for label in vocabulary:
        tp = sum(
            1 for row in predictions if row.true_label == label and row.predicted_label == label
        )
        fp = sum(
            1 for row in predictions if row.true_label != label and row.predicted_label == label
        )
        fn = sum(
            1 for row in predictions if row.true_label == label and row.predicted_label != label
        )
        support = sum(1 for row in predictions if row.true_label == label)
        precision_den = tp + fp
        recall_den = tp + fn
        rows.append(
            ClassMetricBundle(
                class_label=label,
                support=support,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                precision_num=tp if precision_den else 0,
                precision_den=precision_den if precision_den else 1,
                recall_num=tp if recall_den else 0,
                recall_den=recall_den if recall_den else 1,
            )
        )
    return tuple(rows)


def _f1_from_pr(
    precision_num: int,
    precision_den: int,
    recall_num: int,
    recall_den: int,
) -> tuple[int, int]:
    # F1 = 2PR/(P+R). With P=a/b and R=c/d: 2ac / (ad + bc) when dens match via cross.
    if precision_num == 0 or recall_num == 0:
        return (0, 1)
    num = 2 * precision_num * recall_num
    den = precision_num * recall_den + recall_num * precision_den
    if den == 0:
        return (0, 1)
    return (num, den)


def _macro_f1(per_class: Sequence[ClassMetricBundle]) -> tuple[int, int]:
    supported = [row for row in per_class if row.support > 0]
    if not supported:
        return (0, 1)
    # Average of per-class F1 as exact rational sum/n.
    total_num = 0
    total_den = 1
    count = len(supported)
    for row in supported:
        f_num, f_den = _f1_from_pr(
            row.precision_num, row.precision_den, row.recall_num, row.recall_den
        )
        # total += f_num/f_den
        total_num = total_num * f_den + f_num * total_den
        total_den = total_den * f_den
    # mean = total / count
    return (total_num, total_den * count)


def _per_session_metrics(
    predictions: Sequence[PredictionRow],
    vocabulary: Sequence[str],
) -> tuple[SessionMetricBundle, ...]:
    sessions = tuple(
        session
        for session in DECLARED_TRADING_SESSIONS
        if any(row.session == session for row in predictions)
    ) or tuple(sorted({row.session for row in predictions}))
    bundles: list[SessionMetricBundle] = []
    for session in sessions:
        subset = [row for row in predictions if row.session == session]
        per_class = _per_class_metrics(subset, vocabulary)
        macro_num, macro_den = _macro_f1(per_class)
        bundles.append(
            SessionMetricBundle(
                session=session,
                support=len(subset),
                macro_f1_num=macro_num,
                macro_f1_den=macro_den,
            )
        )
    return tuple(bundles)


def _brier_ppb(
    predictions: Sequence[PredictionRow],
    vocabulary: Sequence[str],
) -> int:
    if not predictions:
        return 0
    # Multiclass Brier = mean_i sum_k (p_ik - y_ik)^2, reported in ppb.
    total = 0
    for row in predictions:
        for label in vocabulary:
            p = row.probability_ppb.get(label, 0)
            y = _PPB if row.true_label == label else 0
            diff = p - y
            total += (diff * diff) // _PPB
    return total // (len(predictions) * max(1, len(vocabulary)))


def _transition_confusion(predictions: Sequence[PredictionRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    ordered = sorted(predictions, key=lambda row: row.row_id)
    previous: str | None = None
    for row in ordered:
        if previous is not None:
            key = f"{previous}->{row.true_label}|pred:{row.predicted_label}"
            counts[key] = counts.get(key, 0) + 1
        previous = row.true_label
    return counts


def _calibration_bins(
    predictions: Sequence[PredictionRow],
    vocabulary: Sequence[str],
) -> dict[str, tuple[int, int]]:
    """Per-class reliability bins: (predicted_mass_ppb_sum, outcome_count*_PPB)."""
    bins: dict[str, tuple[int, int]] = {}
    for label in vocabulary:
        mass = 0
        outcomes = 0
        for row in predictions:
            mass += row.probability_ppb.get(label, 0)
            if row.true_label == label:
                outcomes += 1
        bins[label] = (mass, outcomes * _PPB)
    return bins


def _error_pairs(predictions: Sequence[PredictionRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in predictions:
        if row.true_label == row.predicted_label:
            continue
        key = f"{row.true_label}->{row.predicted_label}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _ratio_ge(num: int, den: int, thr_num: int, thr_den: int) -> bool:
    return num * thr_den >= thr_num * den


def _acceptance_verdict(
    holdout: EvaluationSplitScores,
    contract: EvaluationContract,
) -> tuple[EvaluationVerdict, str]:
    macro_ok = _ratio_ge(
        holdout.macro_f1_num,
        holdout.macro_f1_den,
        contract.acceptance_macro_f1_num,
        contract.acceptance_macro_f1_den,
    )
    recall_ok = _ratio_ge(
        holdout.min_per_class_recall_num,
        holdout.min_per_class_recall_den,
        contract.acceptance_min_per_class_recall_num,
        contract.acceptance_min_per_class_recall_den,
    )
    if macro_ok and recall_ok:
        return (
            EvaluationVerdict.ACCEPTED,
            "holdout-meets-predeclared-macro-f1-and-min-per-class-recall",
        )
    reasons: list[str] = []
    if not macro_ok:
        reasons.append("macro_f1_below_threshold")
    if not recall_ok:
        reasons.append("min_per_class_recall_below_threshold")
    return (EvaluationVerdict.REFUSED, "+".join(reasons))


def _baseline_comparisons(
    *,
    holdout_rows: Sequence[_EvalRow],
    train_rows: Sequence[_EvalRow],
    candidate_macro: tuple[int, int],
    baseline_ids: Sequence[str],
    feature_ids: Sequence[str],
    vocabulary: Sequence[str],
) -> Result[tuple[BaselineComparisonResult, ...]]:
    results: list[BaselineComparisonResult] = []
    for baseline_id in baseline_ids:
        preds = _baseline_predict(
            baseline_id=baseline_id,
            holdout_rows=holdout_rows,
            train_rows=train_rows,
            feature_ids=feature_ids,
            vocabulary=vocabulary,
        )
        if is_refusal(preds):
            return preds
        scores = _score_split(
            preds.value,
            split_role=_SPLIT_ROLE_HOLDOUT,
            vocabulary=vocabulary,
            feature_ids=feature_ids,
        )
        if is_refusal(scores):
            return scores
        beats = _ratio_ge(
            candidate_macro[0],
            candidate_macro[1],
            scores.value.macro_f1_num,
            scores.value.macro_f1_den,
        )
        results.append(
            BaselineComparisonResult(
                baseline_id=baseline_id,
                macro_f1_num=scores.value.macro_f1_num,
                macro_f1_den=scores.value.macro_f1_den,
                candidate_beats_baseline=beats,
            )
        )
    return Ok(tuple(results))


def _baseline_predict(
    *,
    baseline_id: str,
    holdout_rows: Sequence[_EvalRow],
    train_rows: Sequence[_EvalRow],
    feature_ids: Sequence[str],
    vocabulary: Sequence[str],
) -> Result[tuple[PredictionRow, ...]]:
    if baseline_id == "majority-class":
        majority = _majority_label([row[2] for row in train_rows], vocabulary)
        return Ok(
            tuple(
                PredictionRow(
                    row_id=row[0],
                    session=row[3],
                    true_label=row[2],
                    predicted_label=majority,
                    probability_ppb={
                        label: (_PPB if label == majority else 0) for label in vocabulary
                    },
                    split_role=_SPLIT_ROLE_HOLDOUT,
                )
                for row in holdout_rows
            )
        )
    if baseline_id == "session-conditional-majority":
        out: list[PredictionRow] = []
        for row in holdout_rows:
            label = _session_majority(train_rows, row[3], vocabulary)
            out.append(
                PredictionRow(
                    row_id=row[0],
                    session=row[3],
                    true_label=row[2],
                    predicted_label=label,
                    probability_ppb={name: (_PPB if name == label else 0) for name in vocabulary},
                    split_role=_SPLIT_ROLE_HOLDOUT,
                )
            )
        return Ok(tuple(out))
    if baseline_id == "rule-spread-state-proxy":
        try:
            elevated_idx = list(feature_ids).index("spread_state_elevated")
            extreme_idx = list(feature_ids).index("spread_state_extreme")
        except ValueError:
            elevated_idx = -1
            extreme_idx = -1
        out_rows: list[PredictionRow] = []
        for row in holdout_rows:
            features = row[1]
            if extreme_idx >= 0 and extreme_idx < len(features) and features[extreme_idx] > 0:
                label = "stressed"
            elif elevated_idx >= 0 and elevated_idx < len(features) and features[elevated_idx] > 0:
                label = "elevated"
            else:
                label = "normal"
            if label not in vocabulary:
                label = vocabulary[0]
            out_rows.append(
                PredictionRow(
                    row_id=row[0],
                    session=row[3],
                    true_label=row[2],
                    predicted_label=label,
                    probability_ppb={name: (_PPB if name == label else 0) for name in vocabulary},
                    split_role=_SPLIT_ROLE_HOLDOUT,
                )
            )
        return Ok(tuple(out_rows))
    return policy(
        "baseline_id",
        "unknown baseline comparison id relative to the Story 30.1 contract",
        baseline_id=baseline_id,
        failure_id="mis.regime_eval.unknown_baseline",
    )


if __name__ == "__main__":
    raise SystemExit(main())
