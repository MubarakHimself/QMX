"""Story 30.6 — register model and training lineage as versioned artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core import CalendarIdentity, Instant, WriterId, fingerprint, is_ok, is_refusal
from qmf.core.refusal import RefusalCategory, Result
from qmf.data.dukascopy import DUKASCOPY_SOURCE, PERSONAL_USE_LICENSE
from qmf.registry import EdgeLog, EdgeType, KindRegistry, Registrar, WriteOutcome
from qmn.mis import (
    BAR_INTERVAL_M5_NS,
    DECLARED_TRADING_SESSIONS,
    DEFAULT_TRAINING_SEED,
    EVALUATION_BACKEND_DETERMINISTIC,
    FORBIDDEN_AUTHORITY_STATUSES,
    REGIME_CLASSIFIER_PRODUCER_ID,
    REGIME_MODEL_KIND,
    REGIME_REGISTER_ARTIFACT_ID,
    REGIME_REGISTER_SURFACE,
    TRAINING_BACKEND_DETERMINISTIC,
    CandidateKind,
    EvaluationReport,
    EvaluationVerdict,
    RawCorpusRow,
    RegistrationAuthorityStatus,
    SourceReceipt,
    TrainingArtifact,
    assert_registration_preserves_composition_fp,
    build_accepted_registration,
    build_acquisition_plan,
    build_non_authoritative_registration,
    clean_corpus,
    enter_passive_hub_as_sandbox,
    install_regime_model_kind,
    materialize_corpus_splits,
    materialize_labeled_corpus,
    mint_registration_version,
    refuse_composition_fp_mutation,
    refuse_governed_or_active_status,
    refuse_live_consumer_binding,
    refuse_pretrained_reputation,
    refuse_trained_regime_classifier,
    register_model_lineage,
    run_offline_evaluation,
    run_offline_training,
)
from qmn.promotion.hub import SANDBOX_PROVENANCE
from qmn.promotion.passive_hub import PassiveHubTree, publish_inbox_fragment

T = TypeVar("T")

_MIS_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "mis"
_T0 = 1_700_000_000_000_000_000
_HOLDOUT_MONTHS = 12
_CLOSE = 100_000
_CREATED_NS = 1_700_000_100_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"))


def _receipt(*, row_count: int = 120) -> SourceReceipt:
    return SourceReceipt(
        source_id=DUKASCOPY_SOURCE,
        dataset_id="fx-majors-m5-bars",
        revision="rev-2024-reg",
        calendar_identity="forex-17NY:v3:2025a",
        license_tag=PERSONAL_USE_LICENSE,
        window_start_ns=_T0,
        window_end_ns=_T0 + row_count * BAR_INTERVAL_M5_NS,
        row_count=row_count,
        content_fp="fp1:sha256:" + ("r" * 64),
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
    assert isinstance(artifact, TrainingArtifact)
    return cleaned, labeled, artifact


def _evaluated(tmp_path: Path):
    cleaned, labeled, artifact = _trained(tmp_path)
    report = _ok(
        run_offline_evaluation(
            artifact=artifact,
            labeled=labeled,
            cleaned=cleaned,
            output_dir=str(tmp_path / "eval"),
            backend=EVALUATION_BACKEND_DETERMINISTIC,
        )
    )
    return cleaned, labeled, artifact, report


def _accepted_report(report: EvaluationReport) -> EvaluationReport:
    """Registration tests need an accepted evaluation cite; evaluation itself is Story 30.5."""
    return EvaluationReport(
        artifact_id=report.artifact_id,
        verdict=EvaluationVerdict.ACCEPTED,
        cause="test-accepted-for-registration",
        config_fp=report.config_fp,
        code_fp=report.code_fp,
        dependency_lock_fp=report.dependency_lock_fp,
        design_fp=report.design_fp,
        model_fp=report.model_fp,
        training_artifact_fp=report.training_artifact_fp,
        matrix_fp=report.matrix_fp,
        train_scores=report.train_scores,
        validation_scores=report.validation_scores,
        holdout_scores=report.holdout_scores,
        baseline_comparisons=report.baseline_comparisons,
        calibration_check=report.calibration_check,
        stability_check=report.stability_check,
        stability_agreed=report.stability_agreed,
        acceptance_macro_f1_num=report.acceptance_macro_f1_num,
        acceptance_macro_f1_den=report.acceptance_macro_f1_den,
        acceptance_min_per_class_recall_num=report.acceptance_min_per_class_recall_num,
        acceptance_min_per_class_recall_den=report.acceptance_min_per_class_recall_den,
        output_locations=report.output_locations,
        trained_artifact_mutated=False,
        sealed_holdout_mutated=False,
        grants_money_path_authority=False,
        grants_governed_binding=False,
    )


def _writer() -> WriterId:
    return _ok(WriterId.try_create("op-machine", "mis-register", "regime-model", "boot-30-6"))


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _registry():
    kinds = KindRegistry()
    _ok(install_regime_model_kind(kinds))
    registrar = Registrar(kinds)
    writer = _writer()
    edges = EdgeLog(writer)
    return registrar, edges, writer


def test_accepted_registration_links_full_lineage(tmp_path: Path) -> None:
    cleaned, labeled, artifact, report = _evaluated(tmp_path)
    accepted = _accepted_report(report)
    cleaned_fp = _ok(cleaned.fingerprint())
    labeled_fp = _ok(labeled.fingerprint())
    registration = _ok(
        build_accepted_registration(
            artifact=artifact,
            evaluation=accepted,
            cleaned_fp=cleaned_fp,
            labeled_fp=labeled_fp,
            splits_fp=labeled.splits_fp,
        )
    )
    assert registration.artifact_id == REGIME_REGISTER_ARTIFACT_ID
    assert registration.status is RegistrationAuthorityStatus.CANDIDATE
    assert registration.candidate_kind is CandidateKind.QMX_TRAINED
    assert registration.model_fp == artifact.model_fp
    assert registration.evaluation_report_fp is not None
    assert registration.training_config_fp == artifact.config_fp
    assert registration.code_fp == artifact.code_fp
    assert registration.seed == artifact.record.seed
    assert registration.cleaned_fp == cleaned_fp
    assert registration.labeled_fp == labeled_fp
    assert registration.splits_fp == labeled.splits_fp
    assert registration.design_fp == accepted.design_fp
    assert registration.provenance == SANDBOX_PROVENANCE
    assert registration.grants_money_path_authority is False
    assert registration.grants_governed_binding is False
    assert registration.grants_live_consumer_binding is False
    assert registration.changes_composition_fp is False
    assert registration.feature_schema_fp.value.startswith("fp1:sha256:")
    assert registration.class_mapping_fp.value.startswith("fp1:sha256:")

    composition = _ok(fingerprint({"class": "composition_fp", "label": "node-epoch-a"}))
    registrar, edges, writer = _registry()
    bundle = _ok(
        register_model_lineage(
            registration,
            registrar=registrar,
            edge_log=edges,
            writer=writer,
            sequence=0,
            created_at=_instant(),
            composition_fp=composition,
            output_dir=str(tmp_path / "reg"),
        )
    )
    assert bundle.outcome is WriteOutcome.STORED
    assert bundle.record.kind == REGIME_MODEL_KIND
    assert bundle.composition_fp_before == composition
    assert bundle.composition_fp_after == composition
    assert is_ok(assert_registration_preserves_composition_fp(bundle, composition_fp=composition))
    targets = {edge.to_ref for edge in bundle.edges if edge.edge_type is EdgeType.OCCURRENCE_OF}
    assert registration.model_fp in targets
    assert registration.feature_schema_fp in targets
    assert registration.class_mapping_fp in targets
    assert registration.design_fp in targets
    assert registration.evaluation_report_fp in targets
    assert (tmp_path / "reg" / "registration_record.json").is_file()
    assert (tmp_path / "reg" / "lineage_edges.jsonl").is_file()
    # Still unbound on the governed producer catalog.
    assert is_refusal(refuse_trained_regime_classifier(REGIME_CLASSIFIER_PRODUCER_ID))
    assert REGIME_REGISTER_SURFACE == "qmn.mis.regime_register"


def test_changed_content_mints_new_version(tmp_path: Path) -> None:
    _cleaned, _labeled, artifact, report = _evaluated(tmp_path)
    accepted = _accepted_report(report)
    first_reg = _ok(build_accepted_registration(artifact=artifact, evaluation=accepted))
    registrar, edges, writer = _registry()
    composition = _ok(fingerprint({"class": "composition_fp", "label": "stable"}))
    first = _ok(
        register_model_lineage(
            first_reg,
            registrar=registrar,
            edge_log=edges,
            writer=writer,
            sequence=0,
            created_at=_instant(),
            composition_fp=composition,
        )
    )
    # Semantic config change: different seed cite via a second training run.
    _c2, _l2, artifact2 = _trained(tmp_path / "seed-b", seed=DEFAULT_TRAINING_SEED + 7)
    report2 = _ok(
        run_offline_evaluation(
            artifact=artifact2,
            labeled=_l2,
            cleaned=_c2,
            output_dir=str(tmp_path / "eval-b"),
            backend=EVALUATION_BACKEND_DETERMINISTIC,
        )
    )
    second_reg = _ok(
        build_accepted_registration(
            artifact=artifact2,
            evaluation=_accepted_report(report2),
        )
    )
    second = _ok(
        mint_registration_version(
            second_reg,
            registrar=registrar,
            edge_log=edges,
            writer=writer,
            sequence=1,
            created_at=_instant(_CREATED_NS + 1),
            prior_bundle=first,
            composition_fp=composition,
        )
    )
    assert second.registration_fp != first.registration_fp
    assert second.stable_id != first.stable_id
    assert any(
        edge.edge_type is EdgeType.BRANCHES_FROM and edge.to_ref == first.stable_id
        for edge in second.edges
    )
    # Identical content refuses a new version.
    refused = mint_registration_version(
        first_reg,
        registrar=registrar,
        edge_log=edges,
        writer=writer,
        sequence=2,
        created_at=_instant(_CREATED_NS + 2),
        prior_bundle=first,
        composition_fp=composition,
    )
    assert is_refusal(refused)
    assert refused.context["failure_id"] == "mis.regime_register.identical_version"


def test_incomplete_and_external_candidates_have_no_authority(tmp_path: Path) -> None:
    _cleaned, _labeled, artifact, report = _evaluated(tmp_path)
    # Refused evaluation may be recorded honestly without authority.
    assert report.verdict is EvaluationVerdict.REFUSED
    refused_reg = _ok(
        build_non_authoritative_registration(
            candidate_kind=CandidateKind.REJECTED_EVALUATION,
            artifact=artifact,
            evaluation=report,
        )
    )
    assert refused_reg.status is RegistrationAuthorityStatus.REFUSED_CANDIDATE
    assert refused_reg.grants_governed_binding is False
    assert refused_reg.grants_live_consumer_binding is False

    incomplete = _ok(
        build_non_authoritative_registration(
            candidate_kind=CandidateKind.INCOMPLETE_TRAINING,
            model_bytes=b"checkpoint-partial",
        )
    )
    assert incomplete.status is RegistrationAuthorityStatus.INCOMPLETE_CANDIDATE

    for family in ("kronos", "hmm", "bocpd", "ms-garch"):
        external = _ok(
            build_non_authoritative_registration(
                candidate_kind=CandidateKind.EXTERNAL,
                external_family=family,
            )
        )
        assert external.status is RegistrationAuthorityStatus.EXTERNAL_CANDIDATE
        assert external.external_family == family
        assert external.grants_money_path_authority is False

    assert is_refusal(refuse_pretrained_reputation(family="kronos"))
    assert is_refusal(
        build_non_authoritative_registration(
            candidate_kind=CandidateKind.EXTERNAL,
            external_family="kronos",
            claim_pretrained_authority=True,
        )
    )
    for status in FORBIDDEN_AUTHORITY_STATUSES:
        assert is_refusal(refuse_governed_or_active_status(status=status))
        assert is_refusal(
            build_accepted_registration(
                artifact=artifact,
                evaluation=_accepted_report(report),
                request_status=status,
            )
        )
    assert is_refusal(refuse_live_consumer_binding(claim="bind-producer"))
    assert is_refusal(refuse_composition_fp_mutation(claim="rewrite-composition"))
    assert is_refusal(
        build_accepted_registration(
            artifact=artifact,
            evaluation=_accepted_report(report),
            grant_governed_binding=True,
        )
    )
    assert is_refusal(
        build_accepted_registration(
            artifact=artifact,
            evaluation=_accepted_report(report),
            mutate_composition_fp=True,
        )
    )
    # Refused evaluation cannot use the accepted registration door.
    assert is_refusal(build_accepted_registration(artifact=artifact, evaluation=report))


def test_passive_hub_keeps_sandbox_and_preserves_composition_fp(tmp_path: Path) -> None:
    _cleaned, _labeled, artifact, report = _evaluated(tmp_path)
    registration = _ok(
        build_accepted_registration(
            artifact=artifact,
            evaluation=_accepted_report(report),
        )
    )
    composition = _ok(fingerprint({"class": "composition_fp", "label": "hub-epoch"}))
    registrar, edges, writer = _registry()
    bundle = _ok(
        register_model_lineage(
            registration,
            registrar=registrar,
            edge_log=edges,
            writer=writer,
            sequence=0,
            created_at=_instant(),
            composition_fp=composition,
        )
    )
    tree = PassiveHubTree(tmp_path / "hub")
    published = _ok(
        enter_passive_hub_as_sandbox(
            bundle,
            tree=tree,
            writer=writer,
            artifact_key="regime-candidate",
        )
    )
    assert published.provenance == SANDBOX_PROVENANCE
    assert published.write_only_inbox is True
    assert published.promotion_refused is True
    assert published.publish_refused is True
    assert published.composition_fp_unchanged is True
    # Operator publish still refuses sandbox provenance.
    refused_publish = publish_inbox_fragment(tree, writer=writer, artifact_key="regime-candidate")
    assert is_refusal(refused_publish)
    assert refused_publish.context["field"] == "provenance"
    assert is_ok(assert_registration_preserves_composition_fp(bundle, composition_fp=composition))


def test_registration_module_stays_offline_without_training_or_deploy() -> None:
    text = (_MIS_SRC / "regime_register.py").read_text(encoding="utf-8")
    forbidden = (
        "import urllib",
        "import requests",
        "import httpx",
        "import socket",
        "run_offline_training",
        "qmn.deploy",
        "qmn.replay",
        "qmn.data",
        "qmx_agents",
        "qmx-agents",
    )
    for needle in forbidden:
        assert needle not in text
    assert "mis.regime_register.governed_status" in text
    assert "mis.regime_register.composition_fp_mutation" in text
    assert "mis.regime_register.pretrained_reputation" in text
    assert "python -m qmn.mis.regime_register" in text or "qmn.mis.regime_register" in text
    assert is_refusal(refuse_trained_regime_classifier("regime_classifier_v1"))
    assert (
        refuse_governed_or_active_status(status="active").category
        == RefusalCategory.POLICY_REJECTION
    )
