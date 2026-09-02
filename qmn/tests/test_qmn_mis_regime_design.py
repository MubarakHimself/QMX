"""Story 30.1 — fingerprinted regime_classifier_v1 design before training."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TypeVar

from qmf.core import RefusalCategory, fingerprint, is_ok, is_refusal
from qmf.core.refusal import Result
from qmn.mis import (
    CHOSEN_MODEL_FAMILY,
    DECLARED_TRADING_SESSIONS,
    REGIME_CLASS_VOCABULARY,
    REGIME_CLASSIFIER_PRODUCER_ID,
    REGIME_DESIGN_ARTIFACT_ID,
    REGIME_DESIGN_SURFACE,
    UNAUTHORITATIVE_CANDIDATES,
    accepted_regime_classifier_design,
    assert_design_unchanged,
    evaluate_candidate_families,
    executable_regime_contract,
    refuse_design_authority_claim,
    refuse_trained_regime_classifier,
    refuse_unauthoritative_candidate,
    validate_regime_design_leakage,
    v1_mis_inventory,
)

T = TypeVar("T")

_MIS_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "mis"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def test_design_records_chosen_family_and_required_dimensions() -> None:
    design = accepted_regime_classifier_design()
    assert design.artifact_id == REGIME_DESIGN_ARTIFACT_ID
    assert design.producer_id == REGIME_CLASSIFIER_PRODUCER_ID
    assert design.chosen_family == CHOSEN_MODEL_FAMILY == "lightgbm-multiclass"
    assert design.feature_contract.feature_ids
    assert design.feature_contract.input_timing == "sealed-bar-close-as-of"
    assert design.label_contract.class_vocabulary == REGIME_CLASS_VOCABULARY
    assert design.label_contract.exclusion_class == "insufficient_evidence"
    assert design.data_windows.sessions == DECLARED_TRADING_SESSIONS
    assert set(DECLARED_TRADING_SESSIONS) == {"asia", "london", "new_york"}
    assert design.leakage.as_of_only is True
    assert design.split_strategy.shuffle_forbidden is True
    assert design.imbalance_treatment
    assert design.hyperparameter_bounds.max_trials > 0
    assert design.evaluation.per_session_required is True
    assert design.evaluation.refuse_profit_inference is True
    assert design.compute_estimate
    assert design.retraining_trigger
    assert design.failure_modes
    assert design.training_location == "operator-machine-offline-script"
    assert design.grants_money_path_authority is False
    assert design.grants_governed_binding is False
    assert REGIME_DESIGN_SURFACE == "qmn.mis.regime_design"


def test_candidate_evaluation_grants_no_authority_to_recovered_names() -> None:
    rows = evaluate_candidate_families()
    recovered = {row.family_id for row in rows if row.recovered_candidate}
    assert recovered == UNAUTHORITATIVE_CANDIDATES
    for row in rows:
        if row.recovered_candidate:
            assert row.selected is False
            assert row.authority == "none"
            assert is_refusal(refuse_unauthoritative_candidate(row.family_id))
    selected = [row for row in rows if row.selected]
    assert len(selected) == 1
    assert selected[0].family_id == CHOSEN_MODEL_FAMILY
    assert selected[0].recovered_candidate is False


def test_design_and_executable_contract_are_fingerprinted_and_stable() -> None:
    design = accepted_regime_classifier_design()
    fp = _ok(design.fingerprint())
    assert fp.value.startswith("fp1:sha256:")
    assert _ok(accepted_regime_classifier_design().fingerprint()) == fp
    contract = _ok(executable_regime_contract(design))
    assert contract.design_fp == fp
    assert contract.chosen_family == CHOSEN_MODEL_FAMILY
    assert contract.silent_dimension_change_forbidden is True
    contract_fp = _ok(contract.fingerprint())
    assert contract_fp.value.startswith("fp1:sha256:")
    assert _ok(assert_design_unchanged(fp)) == fp
    assert _ok(assert_design_unchanged(fp.value)) == fp


def test_leakage_and_calendar_laws_validate() -> None:
    design = accepted_regime_classifier_design()
    assert _ok(validate_regime_design_leakage(design)) is design
    broken = replace(
        design,
        leakage=replace(design.leakage, no_future_bars=False),
    )
    refused = validate_regime_design_leakage(broken)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    calendars_broken = replace(
        design,
        leakage=replace(
            design.leakage,
            calendar_kinds_named_apart=("market-hours-calendar", "news-calendar"),
        ),
    )
    assert is_refusal(validate_regime_design_leakage(calendars_broken))
    sessions_broken = replace(
        design,
        data_windows=replace(design.data_windows, sessions=("london",)),
    )
    assert is_refusal(validate_regime_design_leakage(sessions_broken))


def test_silent_design_change_and_authority_claims_refuse() -> None:
    design = accepted_regime_classifier_design()
    fp = _ok(design.fingerprint())
    other = _ok(fingerprint({"class": "not-the-design", "n": 1}))
    changed = assert_design_unchanged(other)
    assert is_refusal(changed)
    assert changed.category is RefusalCategory.POLICY_REJECTION
    assert _ok(refuse_design_authority_claim(design)) is None
    claimed = replace(design, grants_money_path_authority=True)
    assert is_refusal(refuse_design_authority_claim(claimed))
    assert is_refusal(validate_regime_design_leakage(claimed))
    # Design acceptance still does not train, register, or bind the producer.
    assert is_refusal(refuse_trained_regime_classifier(REGIME_CLASSIFIER_PRODUCER_ID))
    inventory = v1_mis_inventory()
    assert inventory["regime_classifier_bound"] is False
    assert inventory["trained_model_selected"] is False
    assert fp.value != other.value


def test_design_module_imports_no_training_stack() -> None:
    text = (_MIS_SRC / "regime_design.py").read_text(encoding="utf-8")
    forbidden = (
        "import lightgbm",
        "import sklearn",
        "import torch",
        "import hmmlearn",
        "import optuna",
        "import xgboost",
    )
    for needle in forbidden:
        assert needle not in text
    assert "def fit(" not in text
    assert "def train(" not in text
