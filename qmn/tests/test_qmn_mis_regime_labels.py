"""Story 30.3 - generate and audit classifier labels under the 30.1 contract."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core import CalendarIdentity, fingerprint, is_ok, is_refusal
from qmf.core.refusal import Result
from qmf.data import SegmentRole
from qmf.data.dukascopy import DUKASCOPY_SOURCE, PERSONAL_USE_LICENSE
from qmn.mis import (
    BAR_INTERVAL_M5_NS,
    DECLARED_TRADING_SESSIONS,
    EXCLUSION_CLASS,
    LABEL_GENERATOR_ID,
    REGIME_CLASS_VOCABULARY,
    REGIME_LABELS_ARTIFACT_ID,
    REGIME_LABELS_SURFACE,
    ExclusionReason,
    RawCorpusRow,
    SourceReceipt,
    accepted_regime_classifier_design,
    audit_regime_labels,
    build_acquisition_plan,
    clean_corpus,
    fit_label_quantile_edges,
    generate_regime_labels,
    materialize_corpus_splits,
    materialize_labeled_corpus,
    refuse_ad_hoc_label_tweak,
    refuse_label_training,
    refuse_sealed_holdout_outcome_peek,
    refuse_trained_regime_classifier,
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


def _receipt(
    *,
    row_count: int = 120,
    content_fp: str = "fp1:sha256:" + ("b" * 64),
) -> SourceReceipt:
    return SourceReceipt(
        source_id=DUKASCOPY_SOURCE,
        dataset_id="fx-majors-m5-bars",
        revision="rev-2024-labels",
        calendar_identity="forex-17NY:v3:2025a",
        license_tag=PERSONAL_USE_LICENSE,
        window_start_ns=_T0,
        window_end_ns=_T0 + row_count * BAR_INTERVAL_M5_NS,
        row_count=row_count,
        content_fp=content_fp,
    )


def _amplitude_for(index: int) -> int:
    """Deterministic amplitude schedule that spreads quartile buckets."""
    band = index % 40
    return 20 + band * band  # 20 .. 20+39^2


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
                close_scaled=_CLOSE,
                scale_digits=5,
                license_tag=PERSONAL_USE_LICENSE,
            )
        )
    return tuple(rows)


def _prepared_corpus(count: int = 120):
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
    return cleaned, splits


def test_label_edges_fit_on_train_only_and_are_fingerprinted() -> None:
    cleaned, splits = _prepared_corpus()
    edges = _ok(fit_label_quantile_edges(cleaned, splits))
    assert edges.method == LABEL_GENERATOR_ID
    assert edges.quantile_edges == ("0.25", "0.50", "0.75")
    assert len(edges.edge_values_ppb) == 3
    assert edges.edge_values_ppb == tuple(sorted(edges.edge_values_ppb))
    assert edges.train_sample_count >= 4
    fp = _ok(edges.fingerprint())
    assert fp.value.startswith("fp1:sha256:")
    assert is_refusal(
        fit_label_quantile_edges(cleaned, splits, inspect_sealed_holdout_outcomes=True)
    )


def test_generate_labels_map_vocabulary_and_exclusion() -> None:
    cleaned, splits = _prepared_corpus()
    rows = _ok(generate_regime_labels(cleaned, splits))
    assert len(rows) == len(cleaned.rows)
    labels = {row.class_label for row in rows}
    assert labels <= set(REGIME_CLASS_VOCABULARY) | {EXCLUSION_CLASS}
    assert EXCLUSION_CLASS in labels
    excluded = [row for row in rows if row.class_label == EXCLUSION_CLASS]
    assert excluded
    assert all(row.exclusion_reason is not None for row in excluded)
    assert any(
        row.exclusion_reason
        in {
            ExclusionReason.INSUFFICIENT_HORIZON.value,
            ExclusionReason.BOUNDARY_PURGE.value,
        }
        for row in excluded
    )
    labeled = [row for row in rows if row.class_label != EXCLUSION_CLASS]
    assert labeled
    sample = labeled[0]
    assert sample.generator_fp.startswith("fp1:sha256:")
    assert sample.config_fp.startswith("fp1:sha256:")
    assert sample.code_fp.startswith("fp1:sha256:")
    assert sample.data_fp.startswith("fp1:sha256:")
    assert sample.event_bound_ns == sample.event_time_ns
    assert sample.knowledge_bound_ns >= sample.event_time_ns
    assert sample.split_role in {
        SegmentRole.TRAIN.value,
        SegmentRole.VALIDATION.value,
        SegmentRole.SEALED_TEST.value,
    }


def test_ambiguous_rows_never_invent_default_class() -> None:
    cleaned, splits = _prepared_corpus(count=40)
    rows = _ok(generate_regime_labels(cleaned, splits))
    for row in rows:
        if row.forward_range_ppb is None or row.exclusion_reason is not None:
            assert row.class_label == EXCLUSION_CLASS
            assert row.exclusion_reason is not None


def test_audit_reports_balance_transitions_and_leakage_without_sealed_peek() -> None:
    cleaned, splits = _prepared_corpus()
    edges = _ok(fit_label_quantile_edges(cleaned, splits))
    rows = _ok(generate_regime_labels(cleaned, splits, edges=edges))
    audit = _ok(audit_regime_labels(rows, edges=edges))
    assert audit.total_rows == len(rows)
    assert audit.exclusion_count >= 1
    assert set(audit.class_counts) == set(REGIME_CLASS_VOCABULARY)
    assert set(audit.labeled_counts) >= set(REGIME_CLASS_VOCABULARY) | {EXCLUSION_CLASS}
    assert audit.transition_frequencies
    assert set(audit.session_distribution) == set(DECLARED_TRADING_SESSIONS)
    assert "EURUSD" in audit.instrument_distribution
    assert SegmentRole.TRAIN.value in audit.split_distribution
    assert audit.window_distribution
    assert audit.sealed_holdout_outcomes_inspected is False
    assert audit.leakage_checks["edges_fitted_on_train_only"] is True
    assert audit.leakage_checks["sealed_holdout_not_used_for_edges"] is True
    assert is_refusal(
        audit_regime_labels(rows, edges=edges, inspect_sealed_holdout_outcomes=True)
    )
    assert is_refusal(refuse_sealed_holdout_outcome_peek(action="peek"))


def test_materialize_labeled_corpus_with_lineage_no_training() -> None:
    cleaned, splits = _prepared_corpus()
    labeled = _ok(materialize_labeled_corpus(cleaned, splits))
    assert labeled.artifact_id == REGIME_LABELS_ARTIFACT_ID
    assert labeled.trains_model is False
    assert labeled.grants_money_path_authority is False
    assert labeled.design_fp == _ok(accepted_regime_classifier_design().fingerprint())
    assert labeled.cleaned_fp.value.startswith("fp1:sha256:")
    assert labeled.label_design_fp.value.startswith("fp1:sha256:")
    assert labeled.generator_fp.value.startswith("fp1:sha256:")
    assert labeled.audit.materially_unsupported is False
    assert labeled.audit.unsupported_classes == ()
    train_counts = labeled.audit.split_distribution[SegmentRole.TRAIN.value]
    for name in REGIME_CLASS_VOCABULARY:
        assert train_counts[name] > 0
    fp = _ok(labeled.fingerprint())
    assert fp.value.startswith("fp1:sha256:")
    again = _ok(materialize_labeled_corpus(cleaned, splits))
    assert _ok(again.fingerprint()) == fp
    assert REGIME_LABELS_SURFACE == "qmn.mis.regime_labels"
    assert is_refusal(refuse_label_training())
    assert is_refusal(materialize_labeled_corpus(cleaned, splits, train_model=True))
    assert is_refusal(
        materialize_labeled_corpus(cleaned, splits, allow_unsupported_classes=True)
    )
    assert is_refusal(refuse_ad_hoc_label_tweak(unsupported=("quiet",)))
    assert is_refusal(refuse_trained_regime_classifier("regime_classifier_v1"))


def test_forward_gap_maps_to_exclusion() -> None:
    plan = _ok(build_acquisition_plan())
    rows = list(_varying_rows(80))
    # Insert a time gap after row 20 by shifting subsequent event times.
    gap_shift = 3 * BAR_INTERVAL_M5_NS
    for index in range(21, len(rows)):
        event = rows[index].event_time_ns + gap_shift
        rows[index] = RawCorpusRow(
            row_id=rows[index].row_id,
            source_id=rows[index].source_id,
            instrument=rows[index].instrument,
            session=rows[index].session,
            event_time_ns=event,
            knowledge_time_ns=event,
            open_scaled=rows[index].open_scaled,
            high_scaled=rows[index].high_scaled,
            low_scaled=rows[index].low_scaled,
            close_scaled=rows[index].close_scaled,
            scale_digits=rows[index].scale_digits,
            license_tag=rows[index].license_tag,
        )
    cleaned = _ok(
        clean_corpus(tuple(rows), plan, source_receipts=(_receipt(row_count=80),))
    )
    splits = _ok(
        materialize_corpus_splits(
            cleaned,
            calendar_identity=_calendar(),
            holdout_months=_HOLDOUT_MONTHS,
        )
    )
    labeled_rows = _ok(generate_regime_labels(cleaned, splits))
    gap_excluded = [
        row
        for row in labeled_rows
        if row.exclusion_reason == ExclusionReason.FORWARD_GAP.value
    ]
    assert gap_excluded
    assert all(row.class_label == EXCLUSION_CLASS for row in gap_excluded)


def test_labels_module_stays_offline_and_training_free() -> None:
    text = (_MIS_SRC / "regime_labels.py").read_text(encoding="utf-8")
    forbidden = (
        "import urllib",
        "import requests",
        "import httpx",
        "import socket",
        "import lightgbm",
        "import sklearn",
        "def train(",
    )
    for needle in forbidden:
        assert needle not in text
    assert "mis.regime_labels.no_training" in text
    assert EXCLUSION_CLASS in text
    assert LABEL_GENERATOR_ID in text


def test_design_fingerprint_stable_across_label_citation() -> None:
    design_fp = _ok(accepted_regime_classifier_design().fingerprint())
    cleaned, splits = _prepared_corpus()
    labeled = _ok(materialize_labeled_corpus(cleaned, splits))
    assert labeled.design_fp == design_fp
    other = _ok(fingerprint({"class": "not-the-design", "n": 2}))
    assert design_fp.value != other.value
