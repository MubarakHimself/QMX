"""Story 30.3 - generate and audit ``regime_classifier_v1`` classifier labels.

Deterministic forward-realized-range quantile buckets citing the accepted
Story 30.1 label contract and the Story 30.2 cleaned corpus / split manifests.
Ambiguous or insufficient-evidence rows map to the designed exclusion class.
Materially unsupported train classes refuse ad-hoc tweaks and return to the
governed design-change process. No model training and no money-path authority
(FR-079; NFR-03/08; CT-07/11; GAP-0051).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from types import MappingProxyType
from typing import Final, TypeAlias, cast

from qmf.core import (
    ExactRational,
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    UnitKind,
    fingerprint,
    is_refusal,
)
from qmf.data import SegmentRole

from qmn.mis._refuse import clean_token, invalid, policy
from qmn.mis.liquidity import exact_nearest_rank_quantile
from qmn.mis.regime_corpus import (
    BAR_INTERVAL_M5_NS,
    CleanedCorpus,
    CleanedCorpusRow,
    CorpusSplitBundle,
)
from qmn.mis.regime_design import (
    DECLARED_TRADING_SESSIONS,
    REGIME_CLASS_VOCABULARY,
    ExecutableRegimeContract,
    LabelContract,
    RegimeClass,
    RegimeClassifierDesign,
    assert_design_unchanged,
    executable_regime_contract,
)

__all__ = [
    "EXCLUSION_CLASS",
    "LABELS_FORMAT_VERSION",
    "LABEL_GENERATOR_ID",
    "REGIME_LABELS_ARTIFACT_ID",
    "REGIME_LABELS_SURFACE",
    "ExclusionReason",
    "LabelAuditReport",
    "LabelEdgeFit",
    "LabeledCorpus",
    "LabeledRow",
    "audit_regime_labels",
    "fit_label_quantile_edges",
    "generate_regime_labels",
    "materialize_labeled_corpus",
    "refuse_ad_hoc_label_tweak",
    "refuse_label_training",
    "refuse_sealed_holdout_outcome_peek",
]

REGIME_LABELS_SURFACE: Final[str] = "qmn.mis.regime_labels"
REGIME_LABELS_ARTIFACT_ID: Final[str] = "regime_classifier_v1_labeled_corpus"
LABELS_FORMAT_VERSION: Final[int] = 1
LABEL_GENERATOR_ID: Final[str] = "forward-realized-range-quantile-buckets"
EXCLUSION_CLASS: Final[str] = "insufficient_evidence"
_RANGE_PPB_SCALE: Final[int] = 1_000_000_000
_SPLIT_ROLE_HOLDOUT: Final[str] = SegmentRole.SEALED_TEST.value


class ExclusionReason(StrEnum):
    """Closed vocabulary for rows that map to the designed exclusion class."""

    INSUFFICIENT_HORIZON = "insufficient_horizon"
    FORWARD_GAP = "forward_gap"
    BOUNDARY_PURGE = "boundary_purge"
    ZERO_CLOSE = "zero_close"
    UNKNOWN_SPLIT = "unknown_split"


@dataclass(frozen=True, slots=True)
class LabelEdgeFit:
    """Train-only nearest-rank quantile edges for the closed class buckets."""

    edge_values_ppb: tuple[int, ...]
    quantile_edges: tuple[str, ...]
    train_sample_count: int
    method: str
    design_fp: Fingerprint
    cleaned_fp: Fingerprint

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-label-edge-fit",
            "edge_values_ppb": list(self.edge_values_ppb),
            "quantile_edges": list(self.quantile_edges),
            "train_sample_count": self.train_sample_count,
            "method": self.method,
            "design_fp": self.design_fp.value,
            "cleaned_fp": self.cleaned_fp.value,
            "format_version": LABELS_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class LabeledRow:
    """One deterministically labeled sealed-bar row with provenance stamps."""

    row_id: str
    instrument: str
    session: str
    event_time_ns: int
    knowledge_time_ns: int
    split_role: str
    class_label: str
    forward_range_ppb: int | None
    event_bound_ns: int
    knowledge_bound_ns: int
    generator_fp: str
    config_fp: str
    code_fp: str
    data_fp: str
    exclusion_reason: str | None = None

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "class": "regime-labeled-row",
            "row_id": self.row_id,
            "instrument": self.instrument,
            "session": self.session,
            "event_time_ns": self.event_time_ns,
            "knowledge_time_ns": self.knowledge_time_ns,
            "split_role": self.split_role,
            "class_label": self.class_label,
            "event_bound_ns": self.event_bound_ns,
            "knowledge_bound_ns": self.knowledge_bound_ns,
            "generator_fp": self.generator_fp,
            "config_fp": self.config_fp,
            "code_fp": self.code_fp,
            "data_fp": self.data_fp,
        }
        if self.forward_range_ppb is not None:
            content["forward_range_ppb"] = self.forward_range_ppb
        if self.exclusion_reason is not None:
            content["exclusion_reason"] = self.exclusion_reason
        return content


@dataclass(frozen=True, slots=True)
class LabelAuditReport:
    """Per-split label audit - distribution evidence, never sealed-outcome peeking."""

    total_rows: int
    class_counts: Mapping[str, int]
    exclusion_count: int
    labeled_counts: Mapping[str, int]
    balance_ratios: Mapping[str, tuple[int, int]]
    transition_frequencies: Mapping[str, int]
    gap_count: int
    missingness: Mapping[str, int]
    session_distribution: Mapping[str, Mapping[str, int]]
    instrument_distribution: Mapping[str, Mapping[str, int]]
    split_distribution: Mapping[str, Mapping[str, int]]
    window_distribution: Mapping[str, int]
    leakage_checks: Mapping[str, bool]
    unsupported_classes: tuple[str, ...]
    sealed_holdout_outcomes_inspected: bool
    materially_unsupported: bool
    design_change_required: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-label-audit-report",
            "total_rows": self.total_rows,
            "class_counts": dict(sorted(self.class_counts.items())),
            "exclusion_count": self.exclusion_count,
            "labeled_counts": dict(sorted(self.labeled_counts.items())),
            "balance_ratios": {
                key: list(value) for key, value in sorted(self.balance_ratios.items())
            },
            "transition_frequencies": dict(sorted(self.transition_frequencies.items())),
            "gap_count": self.gap_count,
            "missingness": dict(sorted(self.missingness.items())),
            "session_distribution": {
                key: dict(sorted(inner.items()))
                for key, inner in sorted(self.session_distribution.items())
            },
            "instrument_distribution": {
                key: dict(sorted(inner.items()))
                for key, inner in sorted(self.instrument_distribution.items())
            },
            "split_distribution": {
                key: dict(sorted(inner.items()))
                for key, inner in sorted(self.split_distribution.items())
            },
            "window_distribution": dict(sorted(self.window_distribution.items())),
            "leakage_checks": dict(sorted(self.leakage_checks.items())),
            "unsupported_classes": list(self.unsupported_classes),
            "sealed_holdout_outcomes_inspected": self.sealed_holdout_outcomes_inspected,
            "materially_unsupported": self.materially_unsupported,
            "design_change_required": self.design_change_required,
            "format_version": LABELS_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class LabeledCorpus:
    """Fingerprinted labeled derivative - research evidence only."""

    artifact_id: str
    design_fp: Fingerprint
    contract_fp: Fingerprint
    cleaned_fp: Fingerprint
    splits_fp: Fingerprint
    label_design_fp: Fingerprint
    edges_fp: Fingerprint
    generator_fp: Fingerprint
    config_fp: Fingerprint
    code_fp: Fingerprint
    data_fp: Fingerprint
    rows: tuple[LabeledRow, ...]
    edges: LabelEdgeFit
    audit: LabelAuditReport
    grants_money_path_authority: bool
    trains_model: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-labeled-corpus",
            "artifact_id": self.artifact_id,
            "design_fp": self.design_fp.value,
            "contract_fp": self.contract_fp.value,
            "cleaned_fp": self.cleaned_fp.value,
            "splits_fp": self.splits_fp.value,
            "label_design_fp": self.label_design_fp.value,
            "edges_fp": self.edges_fp.value,
            "generator_fp": self.generator_fp.value,
            "config_fp": self.config_fp.value,
            "code_fp": self.code_fp.value,
            "data_fp": self.data_fp.value,
            "row_count": len(self.rows),
            "row_fps": [row.fp1_identity() for row in self.rows],
            "audit": self.audit.fp1_identity(),
            "grants_money_path_authority": self.grants_money_path_authority,
            "trains_model": self.trains_model,
            "format_version": LABELS_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


def refuse_label_training(*, claim: object = "train") -> TypedRefusal:
    """Story 30.3 labels the corpus; it does not train a model."""
    return policy(
        "claim",
        "Story 30.3 generates and audits classifier labels; training is Story 30.4",
        failure_id="mis.regime_labels.no_training",
        given=repr(claim),
    )


def refuse_ad_hoc_label_tweak(*, unsupported: object) -> TypedRefusal:
    """Unsupported classes return to Story 30.1 - never an ad-hoc label remap."""
    return policy(
        "unsupported_classes",
        "materially unsupported classes return to Story 30.1's governed "
        "design-change process, not an ad hoc label tweak",
        failure_id="mis.regime_labels.ad_hoc_tweak",
        given=repr(unsupported),
    )


def refuse_sealed_holdout_outcome_peek(*, action: object) -> TypedRefusal:
    """Label audit must not inspect sealed evaluation outcomes beyond process."""
    return policy(
        "action",
        "label audit reports distribution and leakage checks per split without "
        "inspecting sealed evaluation outcomes beyond the declared process",
        failure_id="mis.regime_labels.sealed_holdout_peek",
        given=repr(action),
    )


def fit_label_quantile_edges(
    cleaned: object,
    splits: object,
    *,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    inspect_sealed_holdout_outcomes: object = False,
) -> Result[LabelEdgeFit]:
    """Fit nearest-rank quantile edges on train-eligible forward ranges only."""
    peek = _refuse_holdout_peek(
        inspect_sealed_holdout_outcomes,
        action="fit_on_sealed_holdout",
        reason="inspect_sealed_holdout_outcomes is False for label edge fitting",
    )
    if is_refusal(peek):
        return peek
    prepared = _prepare_edge_fit(cleaned, splits, design=design, contract=contract)
    if is_refusal(prepared):
        return prepared
    cleaned_corpus, split_bundle, resolved_contract, cleaned_fp = prepared.value
    samples = _collect_train_forward_ranges(cleaned_corpus, split_bundle, resolved_contract)
    if is_refusal(samples):
        return samples
    return _fit_edge_values(samples.value, resolved_contract, cleaned_fp)


def generate_regime_labels(
    cleaned: object,
    splits: object,
    *,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    edges: LabelEdgeFit | None = None,
    inspect_sealed_holdout_outcomes: object = False,
    train_model: object = False,
) -> Result[tuple[LabeledRow, ...]]:
    """Generate deterministic labels for every cleaned row under the label contract."""
    flags = _refuse_label_generation_flags(
        train_model=train_model,
        inspect_sealed_holdout_outcomes=inspect_sealed_holdout_outcomes,
    )
    if is_refusal(flags):
        return flags
    prepared = _prepare_label_generation(
        cleaned, splits, design=design, contract=contract, edges=edges
    )
    if is_refusal(prepared):
        return prepared
    return _label_cleaned_rows(*prepared.value)


def audit_regime_labels(
    rows: object,
    *,
    edges: object,
    inspect_sealed_holdout_outcomes: object = False,
) -> Result[LabelAuditReport]:
    """Audit counts, balance, transitions, gaps, missingness, and leakage checks."""
    admitted = _admitted_labeled_rows(
        rows,
        edges=edges,
        inspect_sealed_holdout_outcomes=inspect_sealed_holdout_outcomes,
    )
    if is_refusal(admitted):
        return admitted
    tallies = _tally_labeled_rows(admitted.value)
    if is_refusal(tallies):
        return tallies
    return Ok(_label_audit_from_tallies(admitted.value, tallies.value, edges))


def materialize_labeled_corpus(
    cleaned: object,
    splits: object,
    *,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    train_model: object = False,
    inspect_sealed_holdout_outcomes: object = False,
    allow_unsupported_classes: object = False,
) -> Result[LabeledCorpus]:
    """Persist the fingerprinted labeled derivative with lineage and audit."""
    flags = _refuse_materialize_label_flags(
        train_model=train_model,
        inspect_sealed_holdout_outcomes=inspect_sealed_holdout_outcomes,
        allow_unsupported_classes=allow_unsupported_classes,
    )
    if is_refusal(flags):
        return flags
    resolved = _resolve_inputs(cleaned, splits, design=design, contract=contract)
    if is_refusal(resolved):
        return resolved
    return _mint_labeled_corpus(*resolved.value, design=design)


@dataclass
class _LabelTallies:
    labeled_counts: dict[str, int]
    class_counts: dict[str, int]
    missingness: dict[str, int]
    session_distribution: dict[str, dict[str, int]]
    instrument_distribution: dict[str, dict[str, int]]
    split_distribution: dict[str, dict[str, int]]
    window_distribution: dict[str, int]
    transition_frequencies: dict[str, int]
    gap_count: int
    by_instrument: dict[str, list[LabeledRow]]


@dataclass(frozen=True, slots=True)
class _LabeledCorpusFps:
    contract_fp: Fingerprint
    splits_fp: Fingerprint
    edges_fp: Fingerprint
    label_design_fp: Fingerprint
    generator_fp: Fingerprint
    config_fp: Fingerprint
    code_fp: Fingerprint
    data_fp: Fingerprint


def _refuse_holdout_peek(flag: object, *, action: str, reason: str) -> Result[None]:
    if flag is True:
        return refuse_sealed_holdout_outcome_peek(action=action)
    if flag not in (False, None):
        return invalid("inspect_sealed_holdout_outcomes", reason, given=repr(flag))
    return Ok(None)


def _refuse_training_claim(train_model: object) -> Result[None]:
    if train_model is True:
        return refuse_label_training(claim="train_model=True")
    if train_model not in (False, None):
        return invalid(
            "train_model",
            "train_model is False; Story 30.3 does not train",
            given=repr(train_model),
        )
    return Ok(None)


def _refuse_label_generation_flags(
    *,
    train_model: object,
    inspect_sealed_holdout_outcomes: object,
) -> Result[None]:
    training = _refuse_training_claim(train_model)
    if is_refusal(training):
        return training
    return _refuse_holdout_peek(
        inspect_sealed_holdout_outcomes,
        action="generate_with_sealed_peek",
        reason="inspect_sealed_holdout_outcomes is False for label generation",
    )


def _refuse_materialize_label_flags(
    *,
    train_model: object,
    inspect_sealed_holdout_outcomes: object,
    allow_unsupported_classes: object,
) -> Result[None]:
    training = _refuse_training_claim(train_model)
    if is_refusal(training):
        return training
    if inspect_sealed_holdout_outcomes is True:
        return refuse_sealed_holdout_outcome_peek(action="materialize_sealed_peek")
    if allow_unsupported_classes is True:
        return refuse_ad_hoc_label_tweak(unsupported="allow_unsupported_classes=True")
    if allow_unsupported_classes not in (False, None):
        return invalid(
            "allow_unsupported_classes",
            "allow_unsupported_classes is False; unsupported classes need a design change",
            given=repr(allow_unsupported_classes),
        )
    return Ok(None)


def _prepare_edge_fit(
    cleaned: object,
    splits: object,
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[tuple[CleanedCorpus, CorpusSplitBundle, ExecutableRegimeContract, Fingerprint]]:
    resolved = _resolve_inputs(cleaned, splits, design=design, contract=contract)
    if is_refusal(resolved):
        return resolved
    cleaned_corpus, split_bundle, resolved_contract, cleaned_fp = resolved.value
    method_check = _require_label_method(resolved_contract.label_contract)
    if is_refusal(method_check):
        return method_check
    return Ok((cleaned_corpus, split_bundle, resolved_contract, cleaned_fp))


def _train_forward_range_sample(
    row: CleanedCorpusRow,
    index: int,
    rows: Sequence[CleanedCorpusRow],
    *,
    boundaries: tuple[int, int, int],
    train_end: int,
    purge_ns: int,
    horizon: int,
) -> int | None:
    if _role_for_time(row.event_time_ns, boundaries) != SegmentRole.TRAIN.value:
        return None
    if row.event_time_ns >= train_end - purge_ns:
        return None
    measured = _forward_range_ppb(rows, index, horizon)
    if is_refusal(measured):
        return None
    _reason, value = measured.value
    return value


def _collect_train_forward_ranges(
    cleaned: CleanedCorpus,
    splits: CorpusSplitBundle,
    contract: ExecutableRegimeContract,
) -> Result[list[int]]:
    boundaries = _split_boundaries_ns(splits)
    if is_refusal(boundaries):
        return boundaries
    train_end, _validation_end, _holdout_end = boundaries.value
    purge_ns = contract.leakage.purge_bars * BAR_INTERVAL_M5_NS
    horizon = contract.label_contract.horizon_bars
    samples: list[int] = []
    for rows in _group_rows(cleaned.rows).values():
        for index, row in enumerate(rows):
            sample = _train_forward_range_sample(
                row,
                index,
                rows,
                boundaries=boundaries.value,
                train_end=train_end,
                purge_ns=purge_ns,
                horizon=horizon,
            )
            if sample is not None:
                samples.append(sample)
    return Ok(samples)


def _nearest_rank_edges(
    samples: Sequence[int],
    quantile_edges: Sequence[str],
) -> Result[list[int]]:
    edge_values: list[int] = []
    for edge_token in quantile_edges:
        ratio = _edge_as_rational(edge_token)
        if is_refusal(ratio):
            return ratio
        point = exact_nearest_rank_quantile(samples, ratio.value)
        if is_refusal(point):
            return point
        edge_values.append(point.value)
    return Ok(edge_values)


def _fit_edge_values(
    samples: list[int],
    contract: ExecutableRegimeContract,
    cleaned_fp: Fingerprint,
) -> Result[LabelEdgeFit]:
    label_contract = contract.label_contract
    if len(samples) < len(label_contract.quantile_edges) + 1:
        return policy(
            "train_samples",
            "train-eligible forward ranges are insufficient to fit the ruled "
            "quantile edges; return to Story 30.1 rather than inventing edges",
            sample_count=len(samples),
            required_edges=len(label_contract.quantile_edges),
            failure_id="mis.regime_labels.ad_hoc_tweak",
        )
    edge_values = _nearest_rank_edges(samples, label_contract.quantile_edges)
    if is_refusal(edge_values):
        return edge_values
    if edge_values.value != sorted(edge_values.value):
        return policy(
            "quantile_edges",
            "fitted quantile edges must be non-decreasing; refuse rather than reorder",
            edges=edge_values.value,
            failure_id="mis.regime_labels.ad_hoc_tweak",
        )
    return Ok(
        LabelEdgeFit(
            edge_values_ppb=tuple(edge_values.value),
            quantile_edges=tuple(label_contract.quantile_edges),
            train_sample_count=len(samples),
            method=label_contract.method,
            design_fp=contract.design_fp,
            cleaned_fp=cleaned_fp,
        )
    )


def _require_generation_label_contract(label_contract: LabelContract) -> Result[None]:
    method_check = _require_label_method(label_contract)
    if is_refusal(method_check):
        return method_check
    if label_contract.exclusion_class != EXCLUSION_CLASS:
        return policy(
            "exclusion_class",
            "ambiguous rows use insufficient_evidence rather than an invented default",
            given=label_contract.exclusion_class,
            required=EXCLUSION_CLASS,
        )
    if tuple(label_contract.class_vocabulary) != REGIME_CLASS_VOCABULARY:
        return policy(
            "class_vocabulary",
            "labels map only to the closed regime class vocabulary",
            given=list(label_contract.class_vocabulary),
            required=list(REGIME_CLASS_VOCABULARY),
        )
    return Ok(None)


def _resolve_generation_edges(
    cleaned: CleanedCorpus,
    splits: CorpusSplitBundle,
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract,
    edges: LabelEdgeFit | None,
) -> Result[LabelEdgeFit]:
    if edges is not None:
        return Ok(edges)
    return fit_label_quantile_edges(cleaned, splits, design=design, contract=contract)


_LabelGenerationPrep: TypeAlias = tuple[
    CleanedCorpus,
    LabelContract,
    LabelEdgeFit,
    tuple[int, int, int],
    int,
    tuple[Fingerprint, Fingerprint, Fingerprint, Fingerprint],
]


def _prepare_label_generation(
    cleaned: object,
    splits: object,
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
    edges: LabelEdgeFit | None,
) -> Result[_LabelGenerationPrep]:
    resolved = _resolve_inputs(cleaned, splits, design=design, contract=contract)
    if is_refusal(resolved):
        return resolved
    cleaned_corpus, split_bundle, resolved_contract, cleaned_fp = resolved.value
    label_contract = resolved_contract.label_contract
    method_check = _require_generation_label_contract(label_contract)
    if is_refusal(method_check):
        return method_check
    resolved_edges = _resolve_generation_edges(
        cleaned_corpus,
        split_bundle,
        design=design,
        contract=resolved_contract,
        edges=edges,
    )
    if is_refusal(resolved_edges):
        return resolved_edges
    provenance = _provenance_fps(
        label_contract=label_contract,
        edges=resolved_edges.value,
        cleaned_fp=cleaned_fp,
        design_fp=resolved_contract.design_fp,
    )
    if is_refusal(provenance):
        return provenance
    boundaries = _split_boundaries_ns(split_bundle)
    if is_refusal(boundaries):
        return boundaries
    purge_ns = resolved_contract.leakage.purge_bars * BAR_INTERVAL_M5_NS
    return Ok(
        (
            cleaned_corpus,
            label_contract,
            resolved_edges.value,
            boundaries.value,
            purge_ns,
            provenance.value,
        )
    )


def _row_exclusion_and_range(
    row: CleanedCorpusRow,
    index: int,
    rows: Sequence[CleanedCorpusRow],
    *,
    horizon: int,
    purge_ns: int,
    boundaries: tuple[int, int, int],
) -> tuple[ExclusionReason | None, int | None, int]:
    knowledge_bound = row.knowledge_time_ns
    measured = _forward_range_ppb(rows, index, horizon)
    if is_refusal(measured):
        return ExclusionReason.INSUFFICIENT_HORIZON, None, knowledge_bound
    reason, value = measured.value
    if reason is not None:
        return reason, None, knowledge_bound
    knowledge_bound = rows[index + horizon].knowledge_time_ns
    next_boundary = _next_boundary_ns(row.event_time_ns, boundaries)
    if next_boundary is not None and row.event_time_ns >= next_boundary - purge_ns:
        return ExclusionReason.BOUNDARY_PURGE, value, knowledge_bound
    return None, value, knowledge_bound


def _class_and_split_role(
    role: str | None,
    exclusion: ExclusionReason | None,
    range_ppb: int | None,
    edges: Sequence[int],
) -> tuple[str, str, ExclusionReason | None]:
    if role is None:
        return EXCLUSION_CLASS, "unknown", ExclusionReason.UNKNOWN_SPLIT
    if exclusion is not None or range_ppb is None:
        if exclusion is None:
            exclusion = ExclusionReason.INSUFFICIENT_HORIZON
        return EXCLUSION_CLASS, role, exclusion
    return _bucket_class(range_ppb, edges), role, None


def _label_one_row(
    row: CleanedCorpusRow,
    index: int,
    rows: Sequence[CleanedCorpusRow],
    *,
    horizon: int,
    purge_ns: int,
    boundaries: tuple[int, int, int],
    edges: Sequence[int],
    generator_fp: Fingerprint,
    config_fp: Fingerprint,
    code_fp: Fingerprint,
    data_fp: Fingerprint,
) -> LabeledRow:
    role = _role_for_time(row.event_time_ns, boundaries)
    exclusion, range_ppb, knowledge_bound = _row_exclusion_and_range(
        row, index, rows, horizon=horizon, purge_ns=purge_ns, boundaries=boundaries
    )
    class_label, split_role, exclusion = _class_and_split_role(role, exclusion, range_ppb, edges)
    return LabeledRow(
        row_id=row.row_id,
        instrument=row.instrument,
        session=row.session,
        event_time_ns=row.event_time_ns,
        knowledge_time_ns=row.knowledge_time_ns,
        split_role=split_role,
        class_label=class_label,
        forward_range_ppb=range_ppb,
        event_bound_ns=row.event_time_ns,
        knowledge_bound_ns=knowledge_bound,
        generator_fp=generator_fp.value,
        config_fp=config_fp.value,
        code_fp=code_fp.value,
        data_fp=data_fp.value,
        exclusion_reason=exclusion.value if exclusion is not None else None,
    )


def _label_cleaned_rows(
    cleaned: CleanedCorpus,
    label_contract: LabelContract,
    edges: LabelEdgeFit,
    boundaries: tuple[int, int, int],
    purge_ns: int,
    provenance: tuple[Fingerprint, Fingerprint, Fingerprint, Fingerprint],
) -> Result[tuple[LabeledRow, ...]]:
    generator_fp, config_fp, code_fp, data_fp = provenance
    labeled: list[LabeledRow] = []
    for rows in _group_rows(cleaned.rows).values():
        for index, row in enumerate(rows):
            labeled.append(
                _label_one_row(
                    row,
                    index,
                    rows,
                    horizon=label_contract.horizon_bars,
                    purge_ns=purge_ns,
                    boundaries=boundaries,
                    edges=edges.edge_values_ppb,
                    generator_fp=generator_fp,
                    config_fp=config_fp,
                    code_fp=code_fp,
                    data_fp=data_fp,
                )
            )
    labeled.sort(key=lambda item: (item.instrument, item.event_time_ns, item.row_id))
    return Ok(tuple(labeled))


def _admitted_labeled_rows(
    rows: object,
    *,
    edges: object,
    inspect_sealed_holdout_outcomes: object,
) -> Result[list[LabeledRow]]:
    peek = _refuse_holdout_peek(
        inspect_sealed_holdout_outcomes,
        action="audit_sealed_outcomes",
        reason="inspect_sealed_holdout_outcomes is False for label audit",
    )
    if is_refusal(peek):
        return peek
    if not isinstance(edges, LabelEdgeFit):
        return invalid(
            "edges",
            "label audit cites the train-only LabelEdgeFit",
            given=type(edges).__name__,
        )
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return invalid(
            "rows",
            "label audit takes a sequence of LabeledRow values",
            given=type(rows).__name__,
        )
    admitted: list[LabeledRow] = []
    for index, raw in enumerate(cast("Sequence[object]", rows)):
        if not isinstance(raw, LabeledRow):
            return invalid(
                "rows",
                "each audited row is a LabeledRow",
                index=index,
                given=type(raw).__name__,
            )
        admitted.append(raw)
    return Ok(admitted)


def _empty_label_tallies() -> _LabelTallies:
    labeled_counts: dict[str, int] = dict.fromkeys(REGIME_CLASS_VOCABULARY, 0)
    labeled_counts[EXCLUSION_CLASS] = 0
    class_keys = (*REGIME_CLASS_VOCABULARY, EXCLUSION_CLASS)
    return _LabelTallies(
        labeled_counts=labeled_counts,
        class_counts=dict.fromkeys(REGIME_CLASS_VOCABULARY, 0),
        missingness={reason.value: 0 for reason in ExclusionReason},
        session_distribution={
            session: dict.fromkeys(class_keys, 0) for session in DECLARED_TRADING_SESSIONS
        },
        instrument_distribution={},
        split_distribution={},
        window_distribution={},
        transition_frequencies={},
        gap_count=0,
        by_instrument={},
    )


def _accumulate_exclusion(row: LabeledRow, tallies: _LabelTallies) -> None:
    if row.exclusion_reason is None:
        return
    if row.exclusion_reason not in tallies.missingness:
        tallies.missingness[row.exclusion_reason] = 0
    tallies.missingness[row.exclusion_reason] += 1
    if row.exclusion_reason == ExclusionReason.FORWARD_GAP.value:
        tallies.gap_count += 1


def _accumulate_labeled_row(row: LabeledRow, tallies: _LabelTallies) -> Result[None]:
    if row.class_label not in tallies.labeled_counts:
        return policy(
            "class_label",
            "audited labels must stay inside the closed vocabulary or exclusion class",
            given=row.class_label,
        )
    tallies.labeled_counts[row.class_label] += 1
    if row.class_label in tallies.class_counts:
        tallies.class_counts[row.class_label] += 1
    _accumulate_exclusion(row, tallies)
    if row.session in tallies.session_distribution:
        tallies.session_distribution[row.session][row.class_label] += 1
    class_keys = (*REGIME_CLASS_VOCABULARY, EXCLUSION_CLASS)
    tallies.instrument_distribution.setdefault(row.instrument, dict.fromkeys(class_keys, 0))
    tallies.instrument_distribution[row.instrument][row.class_label] += 1
    tallies.split_distribution.setdefault(row.split_role, dict.fromkeys(class_keys, 0))
    tallies.split_distribution[row.split_role][row.class_label] += 1
    window_key = f"{row.split_role}:{row.session}"
    tallies.window_distribution[window_key] = tallies.window_distribution.get(window_key, 0) + 1
    tallies.by_instrument.setdefault(row.instrument, []).append(row)
    return Ok(None)


def _count_transitions(by_instrument: Mapping[str, list[LabeledRow]]) -> dict[str, int]:
    transition_frequencies: dict[str, int] = {}
    for series in by_instrument.values():
        ordered = sorted(series, key=lambda item: item.event_time_ns)
        previous: str | None = None
        for row in ordered:
            if previous is not None:
                key = f"{previous}->{row.class_label}"
                transition_frequencies[key] = transition_frequencies.get(key, 0) + 1
            previous = row.class_label
    return transition_frequencies


def _tally_labeled_rows(admitted: Sequence[LabeledRow]) -> Result[_LabelTallies]:
    tallies = _empty_label_tallies()
    for row in admitted:
        accumulated = _accumulate_labeled_row(row, tallies)
        if is_refusal(accumulated):
            return accumulated
    tallies.transition_frequencies = _count_transitions(tallies.by_instrument)
    return Ok(tallies)


def _frozen_inner_maps(
    mapping: Mapping[str, Mapping[str, int]],
) -> Mapping[str, Mapping[str, int]]:
    return MappingProxyType(
        {
            key: MappingProxyType(dict(sorted(inner.items())))
            for key, inner in sorted(mapping.items())
        }
    )


def _label_leakage_checks(
    admitted: Sequence[LabeledRow],
    edges: LabelEdgeFit,
    labeled_counts: Mapping[str, int],
) -> dict[str, bool]:
    return {
        "edges_fitted_on_train_only": edges.train_sample_count > 0,
        "sealed_holdout_not_used_for_edges": True,
        "as_of_event_knowledge_bounds_present": all(
            row.event_bound_ns == row.event_time_ns and row.knowledge_bound_ns >= row.event_time_ns
            for row in admitted
        ),
        "closed_vocabulary_only": all(row.class_label in labeled_counts for row in admitted),
        "exclusion_class_is_insufficient_evidence": all(
            row.class_label != EXCLUSION_CLASS or row.exclusion_reason is not None
            for row in admitted
        ),
    }


def _label_audit_from_tallies(
    admitted: Sequence[LabeledRow],
    tallies: _LabelTallies,
    edges: object,
) -> LabelAuditReport:
    fitted = cast("LabelEdgeFit", edges)
    train_counts = tallies.split_distribution.get(SegmentRole.TRAIN.value, {})
    unsupported = tuple(name for name in REGIME_CLASS_VOCABULARY if train_counts.get(name, 0) <= 0)
    total_classed = sum(tallies.class_counts.values())
    denom = total_classed if total_classed > 0 else 1
    balance = {name: (count, denom) for name, count in tallies.class_counts.items()}
    leakage = _label_leakage_checks(admitted, fitted, tallies.labeled_counts)
    return LabelAuditReport(
        total_rows=len(admitted),
        class_counts=MappingProxyType(dict(sorted(tallies.class_counts.items()))),
        exclusion_count=tallies.labeled_counts[EXCLUSION_CLASS],
        labeled_counts=MappingProxyType(dict(sorted(tallies.labeled_counts.items()))),
        balance_ratios=MappingProxyType(dict(sorted(balance.items()))),
        transition_frequencies=MappingProxyType(
            dict(sorted(tallies.transition_frequencies.items()))
        ),
        gap_count=tallies.gap_count,
        missingness=MappingProxyType(dict(sorted(tallies.missingness.items()))),
        session_distribution=_frozen_inner_maps(tallies.session_distribution),
        instrument_distribution=_frozen_inner_maps(tallies.instrument_distribution),
        split_distribution=_frozen_inner_maps(tallies.split_distribution),
        window_distribution=MappingProxyType(dict(sorted(tallies.window_distribution.items()))),
        leakage_checks=MappingProxyType(dict(sorted(leakage.items()))),
        unsupported_classes=unsupported,
        sealed_holdout_outcomes_inspected=False,
        materially_unsupported=bool(unsupported),
        design_change_required=bool(unsupported),
    )


def _labeled_corpus_fps(
    cleaned_fp: Fingerprint,
    splits: CorpusSplitBundle,
    contract: ExecutableRegimeContract,
    edges: LabelEdgeFit,
) -> Result[_LabeledCorpusFps]:
    contract_fp = contract.fingerprint()
    if is_refusal(contract_fp):
        return contract_fp
    splits_fp = splits.fingerprint()
    if is_refusal(splits_fp):
        return splits_fp
    edges_fp = edges.fingerprint()
    if is_refusal(edges_fp):
        return edges_fp
    label_design = fingerprint(contract.label_contract.fp1_identity())
    if is_refusal(label_design):
        return label_design
    provenance = _provenance_fps(
        label_contract=contract.label_contract,
        edges=edges,
        cleaned_fp=cleaned_fp,
        design_fp=contract.design_fp,
    )
    if is_refusal(provenance):
        return provenance
    generator_fp, config_fp, code_fp, data_fp = provenance.value
    return Ok(
        _LabeledCorpusFps(
            contract_fp=contract_fp.value,
            splits_fp=splits_fp.value,
            edges_fp=edges_fp.value,
            label_design_fp=label_design.value,
            generator_fp=generator_fp,
            config_fp=config_fp,
            code_fp=code_fp,
            data_fp=data_fp,
        )
    )


def _labeled_corpus_result(
    contract: ExecutableRegimeContract,
    cleaned_fp: Fingerprint,
    fps: _LabeledCorpusFps,
    rows: tuple[LabeledRow, ...],
    edges: LabelEdgeFit,
    audit: LabelAuditReport,
) -> Result[LabeledCorpus]:
    return Ok(
        LabeledCorpus(
            artifact_id=REGIME_LABELS_ARTIFACT_ID,
            design_fp=contract.design_fp,
            contract_fp=fps.contract_fp,
            cleaned_fp=cleaned_fp,
            splits_fp=fps.splits_fp,
            label_design_fp=fps.label_design_fp,
            edges_fp=fps.edges_fp,
            generator_fp=fps.generator_fp,
            config_fp=fps.config_fp,
            code_fp=fps.code_fp,
            data_fp=fps.data_fp,
            rows=rows,
            edges=edges,
            audit=audit,
            grants_money_path_authority=False,
            trains_model=False,
        )
    )


def _mint_labeled_corpus(
    cleaned: CleanedCorpus,
    splits: CorpusSplitBundle,
    contract: ExecutableRegimeContract,
    cleaned_fp: Fingerprint,
    *,
    design: RegimeClassifierDesign | None,
) -> Result[LabeledCorpus]:
    edges = fit_label_quantile_edges(cleaned, splits, design=design, contract=contract)
    if is_refusal(edges):
        return edges
    rows = generate_regime_labels(
        cleaned, splits, design=design, contract=contract, edges=edges.value
    )
    if is_refusal(rows):
        return rows
    audit = audit_regime_labels(rows.value, edges=edges.value)
    if is_refusal(audit):
        return audit
    if audit.value.materially_unsupported:
        return refuse_ad_hoc_label_tweak(unsupported=audit.value.unsupported_classes)
    fps = _labeled_corpus_fps(cleaned_fp, splits, contract, edges.value)
    if is_refusal(fps):
        return fps
    return _labeled_corpus_result(
        contract, cleaned_fp, fps.value, rows.value, edges.value, audit.value
    )


def _resolve_inputs(
    cleaned: object,
    splits: object,
    *,
    design: RegimeClassifierDesign | None,
    contract: ExecutableRegimeContract | None,
) -> Result[tuple[CleanedCorpus, CorpusSplitBundle, ExecutableRegimeContract, Fingerprint]]:
    if not isinstance(cleaned, CleanedCorpus):
        return invalid(
            "cleaned",
            "label generation takes a CleanedCorpus from Story 30.2",
            given=type(cleaned).__name__,
        )
    if not isinstance(splits, CorpusSplitBundle):
        return invalid(
            "splits",
            "label generation takes a CorpusSplitBundle from Story 30.2",
            given=type(splits).__name__,
        )
    resolved_contract = contract
    if resolved_contract is None:
        minted = executable_regime_contract(design)
        if is_refusal(minted):
            return minted
        resolved_contract = minted.value
    unchanged = assert_design_unchanged(resolved_contract.design_fp, design=design)
    if is_refusal(unchanged):
        return unchanged
    if cleaned.design_fp.value != resolved_contract.design_fp.value:
        return policy(
            "design_fp",
            "cleaned corpus must cite the same design fingerprint as the executable contract",
            cleaned=cleaned.design_fp.value,
            contract=resolved_contract.design_fp.value,
        )
    cleaned_fp = cleaned.fingerprint()
    if is_refusal(cleaned_fp):
        return cleaned_fp
    return Ok((cleaned, splits, resolved_contract, cleaned_fp.value))


def _require_label_method(label_contract: LabelContract) -> Result[None]:
    if label_contract.method != LABEL_GENERATOR_ID:
        return policy(
            "method",
            "Story 30.3 implements only the ruled forward-realized-range-quantile-buckets method",
            given=label_contract.method,
            required=LABEL_GENERATOR_ID,
        )
    return Ok(None)


def _provenance_fps(
    *,
    label_contract: LabelContract,
    edges: LabelEdgeFit,
    cleaned_fp: Fingerprint,
    design_fp: Fingerprint,
) -> Result[tuple[Fingerprint, Fingerprint, Fingerprint, Fingerprint]]:
    config = fingerprint(label_contract.fp1_identity())
    if is_refusal(config):
        return config
    code = fingerprint(
        {
            "class": "regime-label-generator-code",
            "surface": REGIME_LABELS_SURFACE,
            "generator_id": LABEL_GENERATOR_ID,
            "format_version": LABELS_FORMAT_VERSION,
        }
    )
    if is_refusal(code):
        return code
    edges_fp = edges.fingerprint()
    if is_refusal(edges_fp):
        return edges_fp
    generator = fingerprint(
        {
            "class": "regime-label-generator",
            "generator_id": LABEL_GENERATOR_ID,
            "config_fp": config.value.value,
            "code_fp": code.value.value,
            "data_fp": cleaned_fp.value,
            "design_fp": design_fp.value,
            "edges_fp": edges_fp.value.value,
            "format_version": LABELS_FORMAT_VERSION,
        }
    )
    if is_refusal(generator):
        return generator
    return Ok((generator.value, config.value, code.value, cleaned_fp))


def _split_boundaries_ns(
    splits: CorpusSplitBundle,
) -> Result[tuple[int, int, int]]:
    segments = splits.combined_manifest.segments
    if len(segments) != 3:
        return policy(
            "segments",
            "labeled corpus expects train/validation/sealed-test combined manifests",
            count=len(segments),
        )
    values: list[int] = []
    for segment in segments:
        instant = segment.boundary.instant
        if instant is None:
            return invalid(
                "boundary",
                "regime label splits use instant-form boundaries",
                role=segment.role.value,
            )
        values.append(instant.value_ns)
    return Ok((values[0], values[1], values[2]))


def _role_for_time(
    event_time_ns: int,
    boundaries: tuple[int, int, int],
) -> str | None:
    train_end, validation_end, holdout_end = boundaries
    if event_time_ns < train_end:
        return SegmentRole.TRAIN.value
    if event_time_ns < validation_end:
        return SegmentRole.VALIDATION.value
    if event_time_ns < holdout_end:
        return _SPLIT_ROLE_HOLDOUT
    return None


def _next_boundary_ns(
    event_time_ns: int,
    boundaries: tuple[int, int, int],
) -> int | None:
    for boundary in boundaries:
        if event_time_ns < boundary:
            return boundary
    return None


def _group_rows(
    rows: Sequence[CleanedCorpusRow],
) -> dict[str, list[CleanedCorpusRow]]:
    grouped: dict[str, list[CleanedCorpusRow]] = {}
    for row in rows:
        grouped.setdefault(row.instrument, []).append(row)
    for instrument_rows in grouped.values():
        instrument_rows.sort(key=lambda item: item.event_time_ns)
    return grouped


def _forward_window(
    rows: Sequence[CleanedCorpusRow],
    index: int,
    horizon_bars: int,
) -> Result[tuple[ExclusionReason | None, Sequence[CleanedCorpusRow] | None]]:
    if horizon_bars < 1:
        return invalid(
            "horizon_bars",
            "label horizon is a positive sealed-bar count",
            given=horizon_bars,
        )
    end = index + horizon_bars
    if end >= len(rows):
        return Ok((ExclusionReason.INSUFFICIENT_HORIZON, None))
    if rows[index].close_scaled == 0:
        return Ok((ExclusionReason.ZERO_CLOSE, None))
    window = rows[index + 1 : end + 1]
    if len(window) != horizon_bars:
        return Ok((ExclusionReason.INSUFFICIENT_HORIZON, None))
    return Ok((None, window))


def _forward_window_gap(anchor: CleanedCorpusRow, window: Sequence[CleanedCorpusRow]) -> bool:
    prev_time = anchor.event_time_ns
    for bar in window:
        if bar.event_time_ns - prev_time != BAR_INTERVAL_M5_NS:
            return True
        prev_time = bar.event_time_ns
    return False


def _forward_range_ppb(
    rows: Sequence[CleanedCorpusRow],
    index: int,
    horizon_bars: int,
) -> Result[tuple[ExclusionReason | None, int | None]]:
    admitted = _forward_window(rows, index, horizon_bars)
    if is_refusal(admitted):
        return admitted
    reason, window = admitted.value
    if reason is not None or window is None:
        return Ok((reason, None))
    anchor = rows[index]
    if _forward_window_gap(anchor, window):
        return Ok((ExclusionReason.FORWARD_GAP, None))
    span = max(bar.high_scaled for bar in window) - min(bar.low_scaled for bar in window)
    if span < 0:
        return Ok((ExclusionReason.FORWARD_GAP, None))
    return Ok((None, (span * _RANGE_PPB_SCALE) // anchor.close_scaled))


def _edge_as_rational(token: object) -> Result[ExactRational]:
    text = clean_token(token)
    if text is None:
        return invalid(
            "quantile_edges",
            "quantile edge tokens are non-empty decimal strings from the label contract",
            given=repr(token),
        )
    try:
        frac = Fraction(text)
    except (ValueError, ZeroDivisionError):
        return invalid(
            "quantile_edges",
            "quantile edge token must parse as an exact rational",
            given=text,
        )
    if frac < 0 or frac > 1:
        return invalid(
            "quantile_edges",
            "quantile edges are ratios in [0, 1]",
            given=text,
        )
    return ExactRational.try_create(frac.numerator, frac.denominator, UnitKind.DIMENSIONLESS_RATIO)


def _bucket_class(range_ppb: int, edges: Sequence[int]) -> str:
    """Map a forward range onto quiet|normal|elevated|stressed via fitted edges."""
    # edges are (q25, q50, q75) for the four closed classes.
    if len(edges) != 3:
        # Defensive: contract validation already requires three edges.
        return RegimeClass.STRESSED.value if range_ppb > 0 else RegimeClass.QUIET.value
    if range_ppb <= edges[0]:
        return RegimeClass.QUIET.value
    if range_ppb <= edges[1]:
        return RegimeClass.NORMAL.value
    if range_ppb <= edges[2]:
        return RegimeClass.ELEVATED.value
    return RegimeClass.STRESSED.value
