"""Story 30.2 — fetch and clean the governed all-session training corpus."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core import CalendarIdentity, RefusalCategory, fingerprint, is_ok, is_refusal
from qmf.core.refusal import Result
from qmf.data import SegmentRole
from qmf.data.dukascopy import DUKASCOPY_SOURCE, PERSONAL_USE_LICENSE
from qmn.mis import (
    ACQUISITION_CONTEXT,
    BAR_INTERVAL_M5_NS,
    DECLARED_TRADING_SESSIONS,
    REGIME_CORPUS_ARTIFACT_ID,
    REGIME_CORPUS_SURFACE,
    TRAINING_RUN_CONTEXT,
    QualityIssueCode,
    RawCorpusRow,
    SourceReceipt,
    accepted_regime_classifier_design,
    acquire_offline_corpus,
    build_acquisition_plan,
    clean_corpus,
    declared_governed_sources,
    executable_regime_contract,
    materialize_corpus_splits,
    materialize_training_corpus,
    refuse_corpus_training,
    refuse_live_network_corpus,
    refuse_provider_fetch_in_training,
    refuse_silent_repair,
    refuse_trained_regime_classifier,
)

T = TypeVar("T")

_MIS_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "mis"
_T0 = 1_700_000_000_000_000_000
_HOLDOUT_MONTHS = 12


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"))


def _receipt(
    *,
    source_id: str = DUKASCOPY_SOURCE,
    dataset_id: str = "fx-majors-m5-bars",
    revision: str = "rev-2024-01",
    calendar_identity: str = "forex-17NY:v3:2025a",
    license_tag: str = PERSONAL_USE_LICENSE,
    window_start_ns: int = _T0,
    window_end_ns: int = _T0 + 100 * BAR_INTERVAL_M5_NS,
    row_count: int = 30,
    content_fp: str = "fp1:sha256:" + ("a" * 64),
) -> SourceReceipt:
    return SourceReceipt(
        source_id=source_id,
        dataset_id=dataset_id,
        revision=revision,
        calendar_identity=calendar_identity,
        license_tag=license_tag,
        window_start_ns=window_start_ns,
        window_end_ns=window_end_ns,
        row_count=row_count,
        content_fp=content_fp,
    )


def _row(
    *,
    row_id: str,
    session: str,
    event_time_ns: int,
    instrument: str = "EURUSD",
    source_id: str = DUKASCOPY_SOURCE,
    scale_digits: int = 5,
    is_correction: bool = False,
    correction_of: str | None = None,
    open_scaled: int = 100_000,
    high_scaled: int = 100_100,
    low_scaled: int = 99_900,
    close_scaled: int = 100_050,
    license_tag: str = PERSONAL_USE_LICENSE,
) -> RawCorpusRow:
    return RawCorpusRow(
        row_id=row_id,
        source_id=source_id,
        instrument=instrument,
        session=session,
        event_time_ns=event_time_ns,
        knowledge_time_ns=event_time_ns,
        open_scaled=open_scaled,
        high_scaled=high_scaled,
        low_scaled=low_scaled,
        close_scaled=close_scaled,
        scale_digits=scale_digits,
        license_tag=license_tag,
        is_correction=is_correction,
        correction_of=correction_of,
    )


def _all_session_rows(count_per_session: int = 4) -> tuple[RawCorpusRow, ...]:
    rows: list[RawCorpusRow] = []
    index = 0
    for session in DECLARED_TRADING_SESSIONS:
        for _ in range(count_per_session):
            rows.append(
                _row(
                    row_id=f"r{index}",
                    session=session,
                    event_time_ns=_T0 + index * BAR_INTERVAL_M5_NS,
                )
            )
            index += 1
    return tuple(rows)


def test_acquisition_plan_cites_design_and_governed_sources() -> None:
    design = accepted_regime_classifier_design()
    contract = _ok(executable_regime_contract(design))
    plan = _ok(build_acquisition_plan(design=design, contract=contract))
    assert plan.design_fp == contract.design_fp
    assert plan.design_artifact_id == design.artifact_id
    assert plan.sessions == DECLARED_TRADING_SESSIONS
    assert plan.provider_fetch_in_training_forbidden is True
    assert plan.live_network_forbidden is True
    assert plan.acquisition_context == ACQUISITION_CONTEXT
    sources = declared_governed_sources()
    assert plan.sources == sources
    assert any(row.source_id == DUKASCOPY_SOURCE for row in sources)
    assert {row.calendar_kind for row in sources} >= {
        "market-hours-calendar",
        "day-boundary-calendar",
        "news-calendar",
    }
    fp = _ok(plan.fingerprint())
    assert fp.value.startswith("fp1:sha256:")
    assert REGIME_CORPUS_SURFACE == "qmn.mis.regime_corpus"


def test_provider_fetch_in_training_and_live_network_refuse() -> None:
    plan = _ok(build_acquisition_plan())
    refused = acquire_offline_corpus(
        plan,
        (_receipt(),),
        context=TRAINING_RUN_CONTEXT,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert is_refusal(refuse_provider_fetch_in_training(context=TRAINING_RUN_CONTEXT))
    live = acquire_offline_corpus(
        plan,
        (_receipt(),),
        allow_live_network=True,
    )
    assert is_refusal(live)
    assert is_refusal(refuse_live_network_corpus(target="https://example.invalid"))


def test_offline_acquisition_records_source_identities() -> None:
    plan = _ok(build_acquisition_plan())
    receipts = _ok(acquire_offline_corpus(plan, (_receipt(),)))
    assert len(receipts) == 1
    assert receipts[0].source_id == DUKASCOPY_SOURCE
    assert receipts[0].license_tag == PERSONAL_USE_LICENSE
    assert receipts[0].revision == "rev-2024-01"
    foreign = acquire_offline_corpus(
        plan,
        (_receipt(source_id="unknown-vendor", dataset_id="x"),),
    )
    assert is_refusal(foreign)


def test_cleaning_reports_refusals_and_preserves_raw_evidence() -> None:
    plan = _ok(build_acquisition_plan())
    good = list(_all_session_rows())
    bad_scale = _row(
        row_id="bad-scale",
        session="asia",
        event_time_ns=_T0 + 100 * BAR_INTERVAL_M5_NS,
        scale_digits=9,
    )
    duplicate = _row(
        row_id="dup",
        session="asia",
        event_time_ns=good[0].event_time_ns,
    )
    correction = _row(
        row_id="corr",
        session="london",
        event_time_ns=_T0 + 101 * BAR_INTERVAL_M5_NS,
        is_correction=True,
        correction_of="r0",
    )
    out_of_order = _row(
        row_id="ooo",
        session="new_york",
        event_time_ns=good[0].event_time_ns - BAR_INTERVAL_M5_NS,
    )
    cleaned = _ok(
        clean_corpus(
            (*good, bad_scale, duplicate, correction, out_of_order),
            plan,
            source_receipts=(_receipt(),),
        )
    )
    assert cleaned.quality.raw_evidence_preserved is True
    assert cleaned.quality.silent_repair_forbidden is True
    assert cleaned.quality.refused_count >= 4
    assert cleaned.quality.refusal_counts[QualityIssueCode.BAD_SCALE.value] >= 1
    assert cleaned.quality.refusal_counts[QualityIssueCode.DUPLICATE.value] >= 1
    assert cleaned.quality.refusal_counts[QualityIssueCode.CORRECTION.value] >= 1
    assert cleaned.quality.refusal_counts[QualityIssueCode.OUT_OF_ORDER.value] >= 1
    assert set(cleaned.sessions) == set(DECLARED_TRADING_SESSIONS)
    assert len(cleaned.raw_row_ids) == len(good) + 4
    assert is_refusal(refuse_silent_repair(action="fill-gap"))
    assert is_refusal(clean_corpus(good, plan, silent_repair=True))
    fp = _ok(cleaned.fingerprint())
    assert fp.value.startswith("fp1:sha256:")


def test_split_manifests_are_fingerprinted_time_ordered_and_sealed() -> None:
    plan = _ok(build_acquisition_plan())
    cleaned = _ok(clean_corpus(_all_session_rows(5), plan, source_receipts=(_receipt(),)))
    splits = _ok(
        materialize_corpus_splits(
            cleaned,
            calendar_identity=_calendar(),
            holdout_months=_HOLDOUT_MONTHS,
        )
    )
    assert splits.dataset_immutable is True
    assert splits.trains_model is False
    assert splits.split_strategy.holdout_sealed is True
    assert splits.split_strategy.shuffle_forbidden is True
    assert splits.combined_manifest.segments[0].role is SegmentRole.TRAIN
    assert splits.combined_manifest.segments[1].role is SegmentRole.VALIDATION
    assert splits.combined_manifest.segments[2].role is SegmentRole.SEALED_TEST
    assert splits.train_manifest.split_id.startswith("fp1:sha256:")
    assert splits.validation_manifest.split_id.startswith("fp1:sha256:")
    assert splits.holdout_manifest.split_id.startswith("fp1:sha256:")
    assert splits.as_of_set_fp.value.startswith("fp1:sha256:")
    ids = {
        splits.train_manifest.split_id,
        splits.validation_manifest.split_id,
        splits.holdout_manifest.split_id,
    }
    assert len(ids) == 3
    # No-peek: a position at/after the seal boundary is sealed.
    sealed = _ok(splits.holdout_seal.is_sealed(splits.combined_manifest.seal_boundary))
    assert sealed is True
    again = _ok(
        materialize_corpus_splits(
            cleaned,
            calendar_identity=_calendar(),
            holdout_months=_HOLDOUT_MONTHS,
        )
    )
    assert _ok(again.fingerprint()) == _ok(splits.fingerprint())


def test_materialize_training_corpus_end_to_end_without_training() -> None:
    corpus = _ok(
        materialize_training_corpus(
            raw_rows=_all_session_rows(5),
            receipts=(_receipt(),),
            calendar_identity=_calendar(),
            holdout_months=_HOLDOUT_MONTHS,
        )
    )
    assert corpus.artifact_id == REGIME_CORPUS_ARTIFACT_ID
    assert corpus.trains_model is False
    assert corpus.grants_money_path_authority is False
    assert corpus.cleaned.quality.admitted_count >= 3
    assert corpus.splits.dataset_immutable is True
    fp = _ok(corpus.fingerprint())
    assert fp.value.startswith("fp1:sha256:")
    assert is_refusal(refuse_corpus_training())
    assert is_refusal(
        materialize_training_corpus(
            raw_rows=_all_session_rows(),
            receipts=(_receipt(),),
            calendar_identity=_calendar(),
            holdout_months=_HOLDOUT_MONTHS,
            train_model=True,
        )
    )
    # Still unbound — Story 30.2 does not select trained weights.
    assert is_refusal(refuse_trained_regime_classifier("regime_classifier_v1"))


def test_corpus_module_is_offline_only() -> None:
    text = (_MIS_SRC / "regime_corpus.py").read_text(encoding="utf-8")
    forbidden = (
        "import urllib",
        "import requests",
        "import httpx",
        "import socket",
        "import lightgbm",
        "import sklearn",
        "def train(",
        "def fit(",
    )
    for needle in forbidden:
        assert needle not in text
    assert "TRAINING_RUN_CONTEXT" in text
    assert "no provider fetch" in text.lower() or "provider_fetch_in_training" in text


def test_design_fingerprint_stable_across_corpus_citation() -> None:
    design_fp = _ok(accepted_regime_classifier_design().fingerprint())
    plan = _ok(build_acquisition_plan())
    assert plan.design_fp == design_fp
    other = _ok(fingerprint({"class": "not-the-design", "n": 1}))
    assert design_fp.value != other.value
