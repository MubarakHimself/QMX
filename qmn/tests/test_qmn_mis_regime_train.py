"""Story 30.4 — operator-run offline training script (no hours-long fit)."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core import CalendarIdentity, RefusalCategory, fingerprint, is_ok, is_refusal
from qmf.core.refusal import Result
from qmf.data.dukascopy import DUKASCOPY_SOURCE, PERSONAL_USE_LICENSE
from qmn.mis import (
    BAR_INTERVAL_M5_NS,
    DECLARED_TRADING_SESSIONS,
    DEFAULT_TRAINING_SEED,
    REGIME_TRAIN_ARTIFACT_ID,
    REGIME_TRAIN_SURFACE,
    RNG_ALGORITHM,
    TRAINING_BACKEND_DETERMINISTIC,
    TRAINING_LOCATION,
    RawCorpusRow,
    SourceReceipt,
    TrainingArtifact,
    TrainingCheckpoint,
    TrainingRecord,
    TrainingTerminalStatus,
    accepted_regime_classifier_design,
    assert_registerable_training_artifact,
    build_acquisition_plan,
    build_training_config,
    build_training_matrix,
    capture_machine_environment,
    clean_corpus,
    materialize_corpus_splits,
    materialize_labeled_corpus,
    refuse_broker_or_node_credential,
    refuse_live_network_training,
    refuse_partial_model_registration,
    refuse_trained_regime_classifier,
    refuse_vps_or_cloud_training,
    resolve_dependency_lock,
    resume_offline_training,
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
        revision="rev-2024-train",
        calendar_identity="forex-17NY:v3:2025a",
        license_tag=PERSONAL_USE_LICENSE,
        window_start_ns=_T0,
        window_end_ns=_T0 + row_count * BAR_INTERVAL_M5_NS,
        row_count=row_count,
        content_fp="fp1:sha256:" + ("c" * 64),
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


def test_training_config_records_provenance_dimensions(tmp_path: Path) -> None:
    cleaned, labeled = _prepared()
    config = _ok(
        build_training_config(
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(tmp_path / "run"),
            seed=DEFAULT_TRAINING_SEED,
            backend=TRAINING_BACKEND_DETERMINISTIC,
            max_trials=3,
        )
    )
    assert config.rng_algorithm == RNG_ALGORITHM
    assert config.seed == DEFAULT_TRAINING_SEED
    assert config.sessions == DECLARED_TRADING_SESSIONS
    assert config.allow_live_network is False
    assert config.allow_vps_or_cloud is False
    assert config.allow_broker_or_node_credential is False
    assert config.grants_money_path_authority is False
    assert config.data_window_start_ns < config.train_end_ns <= config.validation_end_ns
    assert config.validation_end_ns <= config.holdout_end_ns
    fp = _ok(config.fingerprint())
    assert fp.value.startswith("fp1:sha256:")
    machine = capture_machine_environment()
    assert machine.os_name
    assert machine.python_version
    lock = _ok(resolve_dependency_lock())
    assert lock.lock_fp
    assert REGIME_TRAIN_SURFACE == "qmn.mis.regime_train"
    assert TRAINING_LOCATION == "operator-machine-offline-script"


def test_offline_training_completes_with_terminal_record(tmp_path: Path) -> None:
    cleaned, labeled = _prepared()
    out = tmp_path / "complete"
    result = _ok(
        run_offline_training(
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(out),
            seed=DEFAULT_TRAINING_SEED,
            backend=TRAINING_BACKEND_DETERMINISTIC,
            max_trials=3,
        )
    )
    assert isinstance(result, TrainingArtifact)
    assert result.artifact_id == REGIME_TRAIN_ARTIFACT_ID
    assert result.record.status is TrainingTerminalStatus.COMPLETED
    assert result.record.cause == "search-complete"
    assert result.registerable is True
    assert result.grants_money_path_authority is False
    assert result.grants_governed_binding is False
    assert result.record.rng_algorithm == RNG_ALGORITHM
    assert result.record.seed == DEFAULT_TRAINING_SEED
    assert result.record.dependency_lock.lock_fp
    assert result.record.machine.os_name
    assert result.record.start_time_utc
    assert result.record.end_time_utc
    assert result.record.output_locations["model"]
    assert (out / "training_record.json").is_file()
    assert (out / "training_config.json").is_file()
    assert (out / "model.txt").is_file()
    assert len(result.record.trials) == 3
    assert _ok(assert_registerable_training_artifact(result)) is None
    # Still unbound on the node — Story 30.6 owns registration.
    assert is_refusal(refuse_trained_regime_classifier("regime_classifier_v1"))


def test_identical_inputs_reproduce_model_fingerprint(tmp_path: Path) -> None:
    cleaned, labeled = _prepared()
    first = _ok(
        run_offline_training(
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(tmp_path / "a"),
            seed=11,
            backend=TRAINING_BACKEND_DETERMINISTIC,
            max_trials=2,
        )
    )
    second = _ok(
        run_offline_training(
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(tmp_path / "b"),
            seed=11,
            backend=TRAINING_BACKEND_DETERMINISTIC,
            max_trials=2,
        )
    )
    assert isinstance(first, TrainingArtifact)
    assert isinstance(second, TrainingArtifact)
    # Governed model/matrix reproduce; config_fp includes output_dir so it moves.
    assert first.model_fp == second.model_fp
    assert first.matrix_fp == second.matrix_fp
    assert first.record.seed == second.record.seed
    assert first.record.trials[0].hyperparameters.fp1_identity() == (
        second.record.trials[0].hyperparameters.fp1_identity()
    )


def test_abort_and_partial_outputs_cannot_register(tmp_path: Path) -> None:
    cleaned, labeled = _prepared()
    out = tmp_path / "abort"
    result = _ok(
        run_offline_training(
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(out),
            seed=7,
            backend=TRAINING_BACKEND_DETERMINISTIC,
            max_trials=4,
            abort_after_trials=1,
        )
    )
    assert isinstance(result, TrainingRecord)
    assert result.status is TrainingTerminalStatus.ABORTED
    assert result.registerable is False
    assert is_refusal(assert_registerable_training_artifact(result))
    assert is_refusal(refuse_partial_model_registration(status=result.status.value))
    assert (out / "checkpoint.json").is_file() or (out / "training_record.json").is_file()
    checkpoint_path = out / "checkpoint.json"
    if checkpoint_path.is_file():
        # Resume continues without treating the checkpoint as a model.
        resumed = _ok(
            resume_offline_training(
                labeled=labeled,
                cleaned=cleaned,
                output_dir=str(out),
                seed=7,
                backend=TRAINING_BACKEND_DETERMINISTIC,
                max_trials=4,
            )
        )
        assert isinstance(resumed, TrainingArtifact)
        assert resumed.record.status is TrainingTerminalStatus.COMPLETED
        assert len(resumed.record.trials) == 4


def test_policy_refusals_for_vps_network_credentials_and_holdout() -> None:
    cleaned, labeled = _prepared()
    assert is_refusal(refuse_vps_or_cloud_training(location="trading-vps"))
    assert is_refusal(refuse_live_network_training(claim="fetch"))
    assert is_refusal(refuse_broker_or_node_credential(claim="ctrader-token"))
    assert is_refusal(
        build_training_config(
            labeled=labeled,
            cleaned=cleaned,
            output_dir="out",
            allow_vps_or_cloud=True,
        )
    )
    assert is_refusal(
        build_training_config(
            labeled=labeled,
            cleaned=cleaned,
            output_dir="out",
            allow_live_network=True,
        )
    )
    assert is_refusal(
        build_training_config(
            labeled=labeled,
            cleaned=cleaned,
            output_dir="out",
            allow_broker_or_node_credential=True,
        )
    )
    refused = build_training_matrix(
        cleaned,
        labeled,
        inspect_sealed_holdout=True,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert is_refusal(assert_registerable_training_artifact(TrainingCheckpoint(
        config_fp=_ok(fingerprint({"c": 1})),
        code_fp=_ok(fingerprint({"code": 1})),
        matrix_fp=_ok(fingerprint({"m": 1})),
        completed_trials=(),
        next_trial_index=0,
        best_trial_index=None,
        best_validation_score_ppb=None,
        registerable=False,
        output_dir="out",
    )))


def test_matrix_keeps_sealed_holdout_unused() -> None:
    cleaned, labeled = _prepared()
    matrix = _ok(build_training_matrix(cleaned, labeled))
    assert matrix.sealed_holdout_unused is True
    assert matrix.sealed_holdout_count >= 1
    assert matrix.train_rows
    assert matrix.validation_rows
    holdout_ids = {
        row.row_id
        for row in labeled.rows
        if row.split_role == "sealed-test"
    }
    used_ids = {row[0] for row in matrix.train_rows} | {
        row[0] for row in matrix.validation_rows
    }
    assert holdout_ids.isdisjoint(used_ids)
    assert accepted_regime_classifier_design().training_location == TRAINING_LOCATION


def test_training_module_stays_offline_without_eager_lightgbm() -> None:
    text = (_MIS_SRC / "regime_train.py").read_text(encoding="utf-8")
    forbidden = (
        "import urllib",
        "import requests",
        "import httpx",
        "import socket",
    )
    for needle in forbidden:
        assert needle not in text
    # LightGBM is lazy/optional for operator machines; never eager at module import.
    assert "import lightgbm as lgb" in text
    assert "import lightgbm" in text
    assert text.find("import lightgbm") > text.find("def _select_fitter")
    assert "mis.regime_train.partial_register" in text
    assert "mis.regime_train.vps_or_cloud" in text
    assert "python -m qmn.mis.regime_train" in text
