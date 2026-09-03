"""Story 30.5 — evaluate trained regime candidate against ruled design."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core import CalendarIdentity, RefusalCategory, is_ok, is_refusal
from qmf.core.refusal import Result
from qmf.data.dukascopy import DUKASCOPY_SOURCE, PERSONAL_USE_LICENSE
from qmn.mis import (
    BAR_INTERVAL_M5_NS,
    DECLARED_TRADING_SESSIONS,
    DEFAULT_TRAINING_SEED,
    EVALUATION_BACKEND_DETERMINISTIC,
    REGIME_EVAL_ARTIFACT_ID,
    REGIME_EVAL_SURFACE,
    TRAINING_BACKEND_DETERMINISTIC,
    EvaluationReport,
    EvaluationVerdict,
    RawCorpusRow,
    SourceReceipt,
    accepted_regime_classifier_design,
    assert_evaluation_reproducible,
    build_acquisition_plan,
    build_evaluation_config,
    build_evaluation_matrix,
    clean_corpus,
    materialize_corpus_splits,
    materialize_labeled_corpus,
    refuse_artifact_mutation,
    refuse_holdout_mutation,
    refuse_live_authority_inference,
    refuse_post_hoc_threshold,
    refuse_profit_inference,
    refuse_trained_regime_classifier,
    run_offline_evaluation,
    run_offline_training,
)

T = TypeVar("T")

_MIS_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "mis"
_T0 = 1_700_000_000_000_000_000
_HOLDOUT_MONTHS = 12
_CLOSE = 100_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"))


def _receipt(*, row_count: int = 120) -> SourceReceipt:
    return SourceReceipt(
        source_id=DUKASCOPY_SOURCE,
        dataset_id="fx-majors-m5-bars",
        revision="rev-2024-eval",
        calendar_identity="forex-17NY:v3:2025a",
        license_tag=PERSONAL_USE_LICENSE,
        window_start_ns=_T0,
        window_end_ns=_T0 + row_count * BAR_INTERVAL_M5_NS,
        row_count=row_count,
        content_fp="fp1:sha256:" + ("e" * 64),
    )


def _amplitude_for(index: int) -> int:
    band = index % 40
    return 20 + band * band


def _varying_rows(count: int = 120) -> tuple[RawCorpusRow, ...]:
    rows: list[RawCorpusRow] = []
    sessions = DECLARED_TRADING_SESSIONS
    for index in range(count):
        amplitude = _amplitude_for(index)
        session = sessions[index % len(sessions)]
        rows.append(
            RawCorpusRow(
                row_id=f"r{index}",
                source_id=DUKASCOPY_SOURCE,
                instrument="EURUSD",
                session=session,
                event_time_ns=_T0 + index * BAR_INTERVAL_M5_NS,
                knowledge_time_ns=_T0 + index * BAR_INTERVAL_M5_NS,
                open_scaled=_CLOSE,
                high_scaled=_CLOSE + amplitude,
                low_scaled=_CLOSE - amplitude,
                close_scaled=_CLOSE + (amplitude // 5),
                scale_digits=5,
                license_tag=PERSONAL_USE_LICENSE,
            )
        )
    return tuple(rows)


def _prepared(count: int = 120):
    plan = _ok(build_acquisition_plan())
    cleaned = _ok(
        clean_corpus(
            _varying_rows(count),
            plan,
            source_receipts=(_receipt(row_count=count),),
        )
    )
    splits = _ok(
        materialize_corpus_splits(
            cleaned,
            calendar_identity=_calendar(),
            holdout_months=_HOLDOUT_MONTHS,
        )
    )
    labeled = _ok(materialize_labeled_corpus(cleaned, splits))
    return cleaned, labeled


def _trained(tmp_path: Path, *, seed: int = DEFAULT_TRAINING_SEED):
    cleaned, labeled = _prepared()
    artifact = _ok(
        run_offline_training(
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(tmp_path / "train"),
            seed=seed,
            backend=TRAINING_BACKEND_DETERMINISTIC,
            max_trials=2,
        )
    )
    return cleaned, labeled, artifact


def test_evaluation_follows_story_30_1_contract(tmp_path: Path) -> None:
    cleaned, labeled, artifact = _trained(tmp_path)
    design = accepted_regime_classifier_design()
    report = _ok(
        run_offline_evaluation(
            artifact=artifact,
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(tmp_path / "eval"),
            backend=EVALUATION_BACKEND_DETERMINISTIC,
        )
    )
    assert isinstance(report, EvaluationReport)
    assert report.artifact_id == REGIME_EVAL_ARTIFACT_ID
    assert report.verdict in {EvaluationVerdict.ACCEPTED, EvaluationVerdict.REFUSED}
    assert report.grants_money_path_authority is False
    assert report.grants_governed_binding is False
    assert report.trained_artifact_mutated is False
    assert report.sealed_holdout_mutated is False
    assert report.stability_agreed is True
    assert report.calibration_check == design.evaluation.calibration_check
    assert report.stability_check == design.evaluation.stability_check
    assert report.acceptance_macro_f1_num == design.evaluation.acceptance_macro_f1_num
    assert report.acceptance_macro_f1_den == design.evaluation.acceptance_macro_f1_den
    assert (
        report.acceptance_min_per_class_recall_num
        == design.evaluation.acceptance_min_per_class_recall_num
    )
    assert report.holdout_scores.row_count >= 1
    assert report.train_scores.per_class
    assert report.validation_scores.per_session
    assert {row.baseline_id for row in report.baseline_comparisons} == set(
        design.evaluation.baseline_comparisons
    )
    assert (tmp_path / "eval" / "evaluation_report.json").is_file()
    assert (tmp_path / "eval" / "evaluation_config.json").is_file()
    assert REGIME_EVAL_SURFACE == "qmn.mis.regime_eval"
    # Still unbound — evaluation is not registration or live authority.
    assert is_refusal(refuse_trained_regime_classifier("regime_classifier_v1"))


def test_identical_inputs_reproduce_evaluation_report(tmp_path: Path) -> None:
    cleaned, labeled, artifact = _trained(tmp_path, seed=19)
    first = _ok(
        run_offline_evaluation(
            artifact=artifact,
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(tmp_path / "eval-a"),
            backend=EVALUATION_BACKEND_DETERMINISTIC,
        )
    )
    second = _ok(
        run_offline_evaluation(
            artifact=artifact,
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(tmp_path / "eval-b"),
            backend=EVALUATION_BACKEND_DETERMINISTIC,
            prior_report_fp=_ok(first.governed_fingerprint()),
        )
    )
    # Governed scores/model citations reproduce; config_fp includes output_dir.
    assert first.model_fp == second.model_fp
    assert first.matrix_fp == second.matrix_fp
    assert first.holdout_scores.fp1_identity() == second.holdout_scores.fp1_identity()
    assert first.verdict == second.verdict
    assert _ok(assert_evaluation_reproducible(second, _ok(first.governed_fingerprint())))


def test_policy_refusals_for_profit_live_threshold_and_mutation() -> None:
    cleaned, labeled = _prepared()
    assert is_refusal(refuse_profit_inference(claim="pnl"))
    assert is_refusal(refuse_live_authority_inference(claim="bind-producer"))
    assert is_refusal(refuse_post_hoc_threshold(claim="raise-macro-f1"))
    assert is_refusal(refuse_artifact_mutation(claim="rewrite-model"))
    assert is_refusal(refuse_holdout_mutation(claim="rewrite-holdout"))
    assert is_refusal(
        build_evaluation_config(
            artifact=object(),
            labeled=labeled,
            cleaned=cleaned,
            output_dir="out",
            allow_profit_inference=True,
        )
    )
    # incomplete training object
    refused = build_evaluation_config(
        artifact=object(),
        labeled=labeled,
        cleaned=cleaned,
        output_dir="out",
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert is_refusal(
        build_evaluation_matrix(cleaned, labeled, mutate_sealed_holdout=True)
    )
    assert is_refusal(
        build_evaluation_config(
            artifact=object(),
            labeled=labeled,
            cleaned=cleaned,
            output_dir="out",
            acceptance_macro_f1_override=(99, 100),
        )
    )


def test_evaluation_matrix_includes_holdout_read_only() -> None:
    cleaned, labeled = _prepared()
    matrix = _ok(build_evaluation_matrix(cleaned, labeled))
    assert matrix.holdout_read_only is True
    assert matrix.artifact_mutated is False
    assert matrix.holdout_rows
    assert matrix.train_rows
    assert matrix.validation_rows
    holdout_ids = {row[0] for row in matrix.holdout_rows}
    train_ids = {row[0] for row in matrix.train_rows}
    assert holdout_ids.isdisjoint(train_ids)


def test_evaluation_module_stays_offline_without_eager_lightgbm() -> None:
    text = (_MIS_SRC / "regime_eval.py").read_text(encoding="utf-8")
    forbidden = (
        "import urllib",
        "import requests",
        "import httpx",
        "import socket",
    )
    for needle in forbidden:
        assert needle not in text
    # LightGBM is lazy/optional; never eager at module import — poe tests must
    # never execute a real model fit/predict under the LightGBM backend.
    assert "import lightgbm as lgb" in text
    assert text.find("import lightgbm as lgb") > text.find("def _lightgbm_predict")
    assert "mis.regime_eval.profit_inference" in text
    assert "mis.regime_eval.post_hoc_threshold" in text
    assert "python -m qmn.mis.regime_eval" in text
    assert "run_offline_training" not in text
