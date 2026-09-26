"""Story 30.6 — register ``regime_classifier_v1`` and training lineage as versioned artifacts.

A completed accepted training run registers the model artifact, preprocessing/
feature schema, class mapping, evaluation report, training config, code/
dependency identity, seed, data/split manifests, and design decision as
content-fingerprinted CT-06 records linked by append-only CT-07 lineage. A
changed byte or semantic config mints a new version. Rejected/incomplete
training and external candidates (Kronos/HMM/BOCPD/MS-GARCH) may be recorded
with honest provenance but cannot receive governed/ratified/active status or a
live consumer binding. Registry publication into the passive hub keeps sandbox
provenance visible; promotion still refuses until the separate human/
recertification path. Registering a candidate never changes node
``composition_fp`` (FR-079; CT-05/06/07; TN-19/20; DEC-0262; GAP-0051).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol, TypeIs

from qmf.core import (
    Fingerprint,
    Instant,
    Ok,
    Result,
    TypedRefusal,
    WriterId,
    fingerprint,
    fingerprint_bytes,
    is_refusal,
)

from qmn.mis._refuse import clean_token, invalid, policy
from qmn.mis.catalog import (
    REGIME_CLASSIFIER_PRODUCER_ID,
    UNAUTHORITATIVE_CANDIDATES,
    refuse_trained_regime_classifier,
    refuse_unauthoritative_candidate,
)
from qmn.mis.regime_design import (
    ExecutableRegimeContract,
    FeatureContract,
    LabelContract,
    RegimeClassifierDesign,
    accepted_regime_classifier_design,
    assert_design_unchanged,
    executable_regime_contract,
)
from qmn.mis.regime_eval import EvaluationReport, EvaluationVerdict
from qmn.mis.regime_train import (
    TrainingArtifact,
    TrainingTerminalStatus,
    assert_registerable_training_artifact,
)
from qmn.promotion.hub import SANDBOX_PROVENANCE, HubArtifact, refuse_sandbox_provenance
from qmn.promotion.passive_hub import HubFragment, PassiveHubTree, accept_inbox_fragment

__all__ = [
    "FORBIDDEN_AUTHORITY_STATUSES",
    "REGIME_MODEL_KIND",
    "REGIME_MODEL_KIND_FORMAT_VERSION",
    "REGIME_REGISTER_ARTIFACT_ID",
    "REGIME_REGISTER_FORMAT_VERSION",
    "REGIME_REGISTER_SURFACE",
    "REGISTRATION_LINEAGE_EDGE_TYPE",
    "CandidateKind",
    "RegimeModelRegistration",
    "RegistrationAuthorityStatus",
    "RegistrationLineageBundle",
    "SandboxHubPublication",
    "assert_registration_preserves_composition_fp",
    "build_accepted_registration",
    "build_non_authoritative_registration",
    "enter_passive_hub_as_sandbox",
    "install_regime_model_kind",
    "main",
    "mint_registration_version",
    "refuse_composition_fp_mutation",
    "refuse_governed_or_active_status",
    "refuse_live_consumer_binding",
    "refuse_pretrained_reputation",
    "regime_model_kind_contract",
    "register_model_lineage",
]

REGIME_REGISTER_SURFACE: Final[str] = "qmn.mis.regime_register"
REGIME_REGISTER_ARTIFACT_ID: Final[str] = "regime_classifier_v1_registration"
REGIME_REGISTER_FORMAT_VERSION: Final[int] = 1
REGIME_MODEL_KIND: Final[str] = "regime-model-candidate"
REGIME_MODEL_KIND_FORMAT_VERSION: Final[int] = 1
# CT-07 edge type tokens — string form so mis never imports qmf.registry (host owns that seam).
REGISTRATION_LINEAGE_EDGE_TYPE: Final[str] = "occurrence-of"
_BRANCHES_FROM_EDGE_TYPE: Final[str] = "branches-from"
FORBIDDEN_AUTHORITY_STATUSES: Final[frozenset[str]] = frozenset({"governed", "ratified", "active"})

_BODY_FIELD: Final[str] = "content"
_REGISTRATION_FILENAME: Final[str] = "registration_record.json"
_LINEAGE_FILENAME: Final[str] = "lineage_edges.jsonl"


@dataclass(frozen=True, slots=True)
class _RegimeModelKindContract:
    """Local KindContract for regime-model-candidate — no qmf.registry import."""

    name: str
    contract_format_version: int
    required_fields: frozenset[str]
    optional_fields: frozenset[str]

    def validate_body(self, body: Mapping[str, object]) -> Result[Mapping[str, object]]:
        keys = frozenset(body.keys())
        allowed = self.required_fields | self.optional_fields
        unknown = keys - allowed
        if unknown:
            return invalid(
                "body",
                "the body carries fields this kind's contract does not define; a kind "
                "field set is addable in a later version, never redefined (FM-1)",
                kind=self.name,
                unknown=sorted(unknown),
                allowed=sorted(allowed),
            )
        missing = self.required_fields - keys
        if missing:
            return invalid(
                "body",
                "the body is missing fields this kind's contract requires (FM-1)",
                kind=self.name,
                missing=sorted(missing),
            )
        return Ok(body)


class _RegistrationRecordLike(Protocol):
    """Structural CT-06 record — host owns the concrete type."""

    kind: object
    stable_id: Fingerprint


class _RegistrationReceiptLike(Protocol):
    """Structural CT-06 registration receipt."""

    record: _RegistrationRecordLike
    outcome: object


class _LineageEdgeLike(Protocol):
    """Structural CT-07 lineage edge — host owns the concrete type."""

    edge_type: object
    to_ref: Fingerprint

    def canonical_line(self) -> Result[bytes]: ...


class _EdgeAppendReceiptLike(Protocol):
    """Structural CT-07 edge-append receipt."""

    edge: _LineageEdgeLike


class _KindRegistryHost(Protocol):
    """Structural CT-06 KindRegistry — mis never imports qmf.registry."""

    def register(self, contract: object, /) -> Result[object]: ...

    def contract_for(self, kind: object, /) -> Result[object]: ...


class _RegistrarHost(Protocol):
    """Structural CT-06 Registrar — mis never imports qmf.registry."""

    def register(
        self,
        *,
        kind: object,
        body: object,
        writer: object,
        sequence: object,
        created_at: object,
        at_birth_parent_refs: object = (),
    ) -> Result[_RegistrationReceiptLike]: ...


class _EdgeLogHost(Protocol):
    """Structural CT-07 EdgeLog — mis never imports qmf.registry."""

    def append(
        self,
        *,
        edge_type: object,
        from_ref: object,
        to_ref: object,
        contract_format_version: object = ...,
    ) -> Result[_EdgeAppendReceiptLike]: ...

    def append_edge(self, edge: object, /) -> Result[_EdgeAppendReceiptLike]: ...


def _is_kind_registry(obj: object) -> TypeIs[_KindRegistryHost]:
    return callable(getattr(obj, "register", None)) and callable(
        getattr(obj, "contract_for", None)
    )


def _is_registrar(obj: object) -> TypeIs[_RegistrarHost]:
    return callable(getattr(obj, "register", None)) and not callable(
        getattr(obj, "contract_for", None)
    )


def _is_edge_log(obj: object) -> TypeIs[_EdgeLogHost]:
    return callable(getattr(obj, "append", None)) and callable(getattr(obj, "append_edge", None))


class RegistrationAuthorityStatus(StrEnum):
    """Closed authority vocabulary for Story 30.6 registrations.

    Only candidate / incomplete / external / refused statuses are legal.
    ``governed``, ``ratified``, and ``active`` are refused (DEC-0262).
    """

    CANDIDATE = "candidate"
    INCOMPLETE_CANDIDATE = "incomplete-candidate"
    EXTERNAL_CANDIDATE = "external-candidate"
    REFUSED_CANDIDATE = "refused-candidate"


class CandidateKind(StrEnum):
    """How the candidate entered the registration surface."""

    QMX_TRAINED = "qmx-trained"
    INCOMPLETE_TRAINING = "incomplete-training"
    REJECTED_EVALUATION = "rejected-evaluation"
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class RegimeModelRegistration:
    """Fingerprinted versioned registration citing full training provenance."""

    artifact_id: str
    producer_id: str
    status: RegistrationAuthorityStatus
    candidate_kind: CandidateKind
    model_fp: Fingerprint
    feature_schema_fp: Fingerprint
    class_mapping_fp: Fingerprint
    evaluation_report_fp: Fingerprint | None
    training_config_fp: Fingerprint | None
    code_fp: Fingerprint | None
    dependency_lock_fp: str | None
    seed: int | None
    cleaned_fp: Fingerprint | None
    labeled_fp: Fingerprint | None
    splits_fp: Fingerprint | None
    design_fp: Fingerprint
    contract_fp: Fingerprint
    training_artifact_fp: Fingerprint | None
    external_family: str | None
    provenance: str
    grants_money_path_authority: bool
    grants_governed_binding: bool
    grants_live_consumer_binding: bool
    changes_composition_fp: bool
    format_version: int

    def fp1_identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "class": "regime-model-registration",
            "artifact_id": self.artifact_id,
            "producer_id": self.producer_id,
            "status": self.status.value,
            "candidate_kind": self.candidate_kind.value,
            "model_fp": self.model_fp.value,
            "feature_schema_fp": self.feature_schema_fp.value,
            "class_mapping_fp": self.class_mapping_fp.value,
            "design_fp": self.design_fp.value,
            "contract_fp": self.contract_fp.value,
            "provenance": self.provenance,
            "grants_money_path_authority": self.grants_money_path_authority,
            "grants_governed_binding": self.grants_governed_binding,
            "grants_live_consumer_binding": self.grants_live_consumer_binding,
            "changes_composition_fp": self.changes_composition_fp,
            "format_version": self.format_version,
        }
        # Absent optional cites are omitted keys — fp1 refuses null (DEC-0108).
        if self.evaluation_report_fp is not None:
            body["evaluation_report_fp"] = self.evaluation_report_fp.value
        if self.training_config_fp is not None:
            body["training_config_fp"] = self.training_config_fp.value
        if self.code_fp is not None:
            body["code_fp"] = self.code_fp.value
        if self.dependency_lock_fp is not None:
            body["dependency_lock_fp"] = self.dependency_lock_fp
        if self.seed is not None:
            body["seed"] = self.seed
        if self.cleaned_fp is not None:
            body["cleaned_fp"] = self.cleaned_fp.value
        if self.labeled_fp is not None:
            body["labeled_fp"] = self.labeled_fp.value
        if self.splits_fp is not None:
            body["splits_fp"] = self.splits_fp.value
        if self.training_artifact_fp is not None:
            body["training_artifact_fp"] = self.training_artifact_fp.value
        if self.external_family is not None:
            body["external_family"] = self.external_family
        return body

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())

    def lineage_targets(self) -> tuple[Fingerprint, ...]:
        """Endpoints that receive append-only occurrence-of edges."""
        seen: set[str] = set()
        targets: list[Fingerprint] = []
        for ref in (
            self.model_fp,
            self.feature_schema_fp,
            self.class_mapping_fp,
            self.evaluation_report_fp,
            self.training_config_fp,
            self.code_fp,
            self.cleaned_fp,
            self.labeled_fp,
            self.splits_fp,
            self.design_fp,
            self.contract_fp,
            self.training_artifact_fp,
        ):
            if ref is None:
                continue
            if ref.digest in seen:
                continue
            seen.add(ref.digest)
            targets.append(ref)
        return tuple(targets)

    def as_jsonable(self) -> dict[str, object]:
        return self.fp1_identity()


@dataclass(frozen=True, slots=True)
class RegistrationLineageBundle:
    """CT-06 registration receipt plus append-only CT-07 lineage edges."""

    registration: RegimeModelRegistration
    registration_fp: Fingerprint
    record: _RegistrationRecordLike
    outcome: object
    edges: tuple[_LineageEdgeLike, ...]
    prior_registration_fp: Fingerprint | None
    composition_fp_before: Fingerprint | None
    composition_fp_after: Fingerprint | None

    @property
    def stable_id(self) -> Fingerprint:
        return self.record.stable_id

    def as_mapping(self) -> Mapping[str, object]:
        outcome_token = getattr(self.outcome, "value", self.outcome)
        return MappingProxyType(
            {
                "registration_fp": self.registration_fp.value,
                "stable_id": self.stable_id.value,
                "outcome": outcome_token,
                "edge_count": len(self.edges),
                "status": self.registration.status.value,
                "provenance": self.registration.provenance,
                "composition_fp_before": (
                    None if self.composition_fp_before is None else self.composition_fp_before.value
                ),
                "composition_fp_after": (
                    None if self.composition_fp_after is None else self.composition_fp_after.value
                ),
                "changes_composition_fp": self.registration.changes_composition_fp,
            }
        )


@dataclass(frozen=True, slots=True)
class SandboxHubPublication:
    """Passive-hub inbox accept that keeps sandbox provenance visible."""

    registration_fp: Fingerprint
    hub_artifact: HubArtifact
    provenance: str
    write_only_inbox: bool
    promotion_refused: bool
    publish_refused: bool
    composition_fp_unchanged: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "registration_fp": self.registration_fp.value,
                "artifact_key": self.hub_artifact.artifact_key,
                "fp1": self.hub_artifact.fp1.value,
                "provenance": self.provenance,
                "write_only_inbox": self.write_only_inbox,
                "promotion_refused": self.promotion_refused,
                "publish_refused": self.publish_refused,
                "composition_fp_unchanged": self.composition_fp_unchanged,
            }
        )


def refuse_governed_or_active_status(*, status: object) -> TypedRefusal:
    """Registration cannot mint governed/ratified/active authority (DEC-0262)."""
    return policy(
        "status",
        "Story 30.6 registration records candidates only; governed, ratified, "
        "and active status require the separate human/recertification path",
        failure_id="mis.regime_register.governed_status",
        given=repr(status),
        forbidden=sorted(FORBIDDEN_AUTHORITY_STATUSES),
    )


def refuse_live_consumer_binding(*, claim: object) -> TypedRefusal:
    """Registered candidates have no live consumer binding (TN-19/20)."""
    return policy(
        "live_consumer",
        "registering a regime candidate grants no live consumer, governed "
        "producer, or money-path binding",
        failure_id="mis.regime_register.live_consumer_binding",
        given=repr(claim),
    )


def refuse_composition_fp_mutation(*, claim: object) -> TypedRefusal:
    """Registering a candidate never changes node composition_fp (TN-19/20)."""
    return policy(
        "composition_fp",
        "registering a regime candidate never mutates node composition_fp; "
        "candidates belong on shadow_composition_fp only after Story 30.7",
        failure_id="mis.regime_register.composition_fp_mutation",
        given=repr(claim),
    )


def refuse_pretrained_reputation(*, family: object) -> TypedRefusal:
    """No pretrained reputation substitutes for QMX evidence (DEC-0262)."""
    return policy(
        "external_family",
        "external or recovered candidates may be recorded with honest provenance "
        "but pretrained reputation never substitutes for QMX evidence",
        failure_id="mis.regime_register.pretrained_reputation",
        given=repr(family),
        unauthoritative=sorted(UNAUTHORITATIVE_CANDIDATES),
    )


def regime_model_kind_contract() -> Result[_RegimeModelKindContract]:
    """CT-06 kind contract for the regime-model-candidate record."""
    return Ok(
        _RegimeModelKindContract(
            name=REGIME_MODEL_KIND,
            contract_format_version=REGIME_MODEL_KIND_FORMAT_VERSION,
            required_fields=frozenset({_BODY_FIELD}),
            optional_fields=frozenset(),
        )
    )


def install_regime_model_kind(registry: object) -> Result[_RegimeModelKindContract]:
    """Install the regime-model-candidate kind on a host KindRegistry."""
    if not _is_kind_registry(registry):
        return invalid(
            "registry",
            "regime-model-candidate installs on a CT-06 KindRegistry",
            given=type(registry).__name__,
        )
    contract = regime_model_kind_contract()
    if is_refusal(contract):
        return contract
    admitted = registry.register(contract.value)
    if is_refusal(admitted):
        return admitted
    return Ok(contract.value)


def _feature_schema_fp(feature_contract: FeatureContract) -> Result[Fingerprint]:
    return fingerprint(
        {
            "class": "regime-feature-schema",
            "feature_contract": feature_contract.fp1_identity(),
        }
    )


def _class_mapping_fp(label_contract: LabelContract) -> Result[Fingerprint]:
    return fingerprint(
        {
            "class": "regime-class-mapping",
            "class_vocabulary": list(label_contract.class_vocabulary),
            "exclusion_class": label_contract.exclusion_class,
            "label_contract": label_contract.fp1_identity(),
        }
    )


def _coerce_status(status: object) -> Result[RegistrationAuthorityStatus]:
    if isinstance(status, RegistrationAuthorityStatus):
        token = status.value
        resolved = status
    else:
        token = clean_token(status)
        if token is None:
            return invalid(
                "status",
                "registration status is a non-empty authority token",
                given=repr(status),
            )
        lowered = token.strip().lower()
        if lowered in FORBIDDEN_AUTHORITY_STATUSES:
            return refuse_governed_or_active_status(status=lowered)
        try:
            resolved = RegistrationAuthorityStatus(lowered)
        except ValueError:
            return invalid(
                "status",
                "unknown registration authority status",
                given=token,
                allowed=[item.value for item in RegistrationAuthorityStatus],
            )
    if resolved.value in FORBIDDEN_AUTHORITY_STATUSES:
        return refuse_governed_or_active_status(status=resolved.value)
    return Ok(resolved)


def _training_artifact_cite(artifact: TrainingArtifact) -> Result[Fingerprint]:
    return fingerprint(
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


def build_accepted_registration(
    *,
    artifact: object,
    evaluation: object,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    cleaned_fp: object | None = None,
    labeled_fp: object | None = None,
    splits_fp: object | None = None,
    request_status: object = RegistrationAuthorityStatus.CANDIDATE,
    grant_governed_binding: object = False,
    grant_live_consumer_binding: object = False,
    mutate_composition_fp: object = False,
) -> Result[RegimeModelRegistration]:
    """Build a fingerprinted registration for a completed accepted training run."""
    if grant_governed_binding is True:
        return refuse_live_consumer_binding(claim="grant_governed_binding=True")
    if grant_live_consumer_binding is True:
        return refuse_live_consumer_binding(claim="grant_live_consumer_binding=True")
    if mutate_composition_fp is True:
        return refuse_composition_fp_mutation(claim="mutate_composition_fp=True")
    if grant_governed_binding not in (False, None) or grant_live_consumer_binding not in (
        False,
        None,
    ):
        return invalid(
            "authority",
            "authority grant flags are False for Story 30.6 registration",
            given=repr((grant_governed_binding, grant_live_consumer_binding)),
        )
    if mutate_composition_fp not in (False, None):
        return invalid(
            "mutate_composition_fp",
            "mutate_composition_fp is False for Story 30.6 registration",
            given=repr(mutate_composition_fp),
        )

    status = _coerce_status(request_status)
    if is_refusal(status):
        return status
    if status.value is not RegistrationAuthorityStatus.CANDIDATE:
        return policy(
            "status",
            "an accepted QMX training registration uses candidate status only",
            failure_id="mis.regime_register.accepted_status",
            given=status.value.value,
        )

    if not isinstance(artifact, TrainingArtifact):
        return invalid(
            "artifact",
            "accepted registration takes a completed TrainingArtifact",
            given=type(artifact).__name__,
        )
    registerable = assert_registerable_training_artifact(artifact)
    if is_refusal(registerable):
        return registerable
    if not isinstance(evaluation, EvaluationReport):
        return invalid(
            "evaluation",
            "accepted registration takes an EvaluationReport",
            given=type(evaluation).__name__,
        )
    if evaluation.verdict is not EvaluationVerdict.ACCEPTED:
        return policy(
            "evaluation",
            "accepted registration requires an accepted evaluation verdict; "
            "refused evaluations register only as refused-candidate",
            failure_id="mis.regime_register.evaluation_not_accepted",
            given=evaluation.verdict.value,
        )
    if evaluation.model_fp != artifact.model_fp:
        return policy(
            "model_fp",
            "evaluation report must cite the same model fingerprint as the training artifact",
            failure_id="mis.regime_register.model_fp_mismatch",
            training=artifact.model_fp.value,
            evaluation=evaluation.model_fp.value,
        )

    resolved_design = design if design is not None else accepted_regime_classifier_design()
    design_fp = resolved_design.fingerprint()
    if is_refusal(design_fp):
        return design_fp
    unchanged = assert_design_unchanged(design_fp.value, design=resolved_design)
    if is_refusal(unchanged):
        return unchanged
    if isinstance(contract, ExecutableRegimeContract):
        resolved_contract = contract
    else:
        built = executable_regime_contract(resolved_design)
        if is_refusal(built):
            return built
        resolved_contract = built.value

    feature_fp = _feature_schema_fp(resolved_contract.feature_contract)
    if is_refusal(feature_fp):
        return feature_fp
    class_fp = _class_mapping_fp(resolved_contract.label_contract)
    if is_refusal(class_fp):
        return class_fp
    contract_fp = resolved_contract.fingerprint()
    if is_refusal(contract_fp):
        return contract_fp
    eval_fp = evaluation.governed_fingerprint()
    if is_refusal(eval_fp):
        return eval_fp
    training_cite = _training_artifact_cite(artifact)
    if is_refusal(training_cite):
        return training_cite

    cleaned_resolved = _optional_fp(cleaned_fp, "cleaned_fp")
    if is_refusal(cleaned_resolved):
        return cleaned_resolved
    labeled_resolved = _optional_fp(labeled_fp, "labeled_fp")
    if is_refusal(labeled_resolved):
        return labeled_resolved
    splits_resolved = _optional_fp(splits_fp, "splits_fp")
    if is_refusal(splits_resolved):
        return splits_resolved

    return Ok(
        RegimeModelRegistration(
            artifact_id=REGIME_REGISTER_ARTIFACT_ID,
            producer_id=REGIME_CLASSIFIER_PRODUCER_ID,
            status=RegistrationAuthorityStatus.CANDIDATE,
            candidate_kind=CandidateKind.QMX_TRAINED,
            model_fp=artifact.model_fp,
            feature_schema_fp=feature_fp.value,
            class_mapping_fp=class_fp.value,
            evaluation_report_fp=eval_fp.value,
            training_config_fp=artifact.config_fp,
            code_fp=artifact.code_fp,
            dependency_lock_fp=artifact.record.dependency_lock.lock_fp,
            seed=artifact.record.seed,
            cleaned_fp=cleaned_resolved.value,
            labeled_fp=labeled_resolved.value,
            splits_fp=splits_resolved.value,
            design_fp=design_fp.value,
            contract_fp=contract_fp.value,
            training_artifact_fp=training_cite.value,
            external_family=None,
            provenance=SANDBOX_PROVENANCE,
            grants_money_path_authority=False,
            grants_governed_binding=False,
            grants_live_consumer_binding=False,
            changes_composition_fp=False,
            format_version=REGIME_REGISTER_FORMAT_VERSION,
        )
    )


def build_non_authoritative_registration(
    *,
    candidate_kind: object,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    model_bytes: object | None = None,
    model_fp: object | None = None,
    evaluation: object | None = None,
    artifact: object | None = None,
    external_family: object | None = None,
    claim_pretrained_authority: object = False,
    request_status: object | None = None,
    grant_governed_binding: object = False,
    grant_live_consumer_binding: object = False,
    mutate_composition_fp: object = False,
) -> Result[RegimeModelRegistration]:
    """Record incomplete/rejected/external candidates with honest provenance only."""
    if grant_governed_binding is True or grant_live_consumer_binding is True:
        return refuse_live_consumer_binding(
            claim=f"grant flags ({grant_governed_binding!r}, {grant_live_consumer_binding!r})"
        )
    if mutate_composition_fp is True:
        return refuse_composition_fp_mutation(claim="mutate_composition_fp=True")
    if claim_pretrained_authority is True:
        return refuse_pretrained_reputation(family=external_family)

    kind_token = clean_token(candidate_kind)
    if kind_token is None and isinstance(candidate_kind, CandidateKind):
        kind = candidate_kind
    elif kind_token is None:
        return invalid(
            "candidate_kind",
            "non-authoritative registration names a candidate kind",
            given=repr(candidate_kind),
        )
    else:
        try:
            kind = CandidateKind(kind_token)
        except ValueError:
            return invalid(
                "candidate_kind",
                "unknown non-authoritative candidate kind",
                given=kind_token,
                allowed=[item.value for item in CandidateKind],
            )
    if kind is CandidateKind.QMX_TRAINED:
        return invalid(
            "candidate_kind",
            "QMX-trained accepted candidates use build_accepted_registration",
            given=kind.value,
        )

    resolved_design = design if design is not None else accepted_regime_classifier_design()
    resolved_contract: ExecutableRegimeContract
    if isinstance(contract, ExecutableRegimeContract):
        resolved_contract = contract
    else:
        built = executable_regime_contract(resolved_design)
        if is_refusal(built):
            return built
        resolved_contract = built.value

    feature_fp = _feature_schema_fp(resolved_contract.feature_contract)
    if is_refusal(feature_fp):
        return feature_fp
    class_fp = _class_mapping_fp(resolved_contract.label_contract)
    if is_refusal(class_fp):
        return class_fp
    design_fp = resolved_design.fingerprint()
    if is_refusal(design_fp):
        return design_fp
    contract_fp = resolved_contract.fingerprint()
    if is_refusal(contract_fp):
        return contract_fp

    family_token: str | None = None
    if kind is CandidateKind.EXTERNAL:
        family_token = clean_token(external_family)
        if family_token is None:
            return invalid(
                "external_family",
                "external candidates declare their family (kronos/hmm/bocpd/ms-garch)",
                given=repr(external_family),
            )
        unauth = refuse_unauthoritative_candidate(family_token)
        if is_refusal(unauth):
            # Expected — record with honest provenance, no authority.
            pass
        else:
            return policy(
                "external_family",
                "external registration is reserved for Kronos/HMM/BOCPD/MS-GARCH "
                "candidates that remain unauthoritative",
                failure_id="mis.regime_register.unknown_external_family",
                given=family_token,
                unauthoritative=sorted(UNAUTHORITATIVE_CANDIDATES),
            )
        default_status = RegistrationAuthorityStatus.EXTERNAL_CANDIDATE
    elif kind is CandidateKind.INCOMPLETE_TRAINING:
        default_status = RegistrationAuthorityStatus.INCOMPLETE_CANDIDATE
    else:
        default_status = RegistrationAuthorityStatus.REFUSED_CANDIDATE

    status = _coerce_status(default_status if request_status is None else request_status)
    if is_refusal(status):
        return status

    resolved_model_fp: Fingerprint
    training_cite: Fingerprint | None = None
    training_config: Fingerprint | None = None
    code_fp: Fingerprint | None = None
    dependency_lock: str | None = None
    seed: int | None = None
    eval_fp: Fingerprint | None = None

    if isinstance(artifact, TrainingArtifact):
        # Incomplete/aborted artifacts may be recorded but never as registerable authority.
        if (
            artifact.registerable
            and artifact.record.status is TrainingTerminalStatus.COMPLETED
            and kind is CandidateKind.INCOMPLETE_TRAINING
        ):
            return policy(
                "artifact",
                "a completed registerable training artifact is not an incomplete candidate",
                failure_id="mis.regime_register.completed_as_incomplete",
            )
        resolved_model_fp = artifact.model_fp
        training_config = artifact.config_fp
        code_fp = artifact.code_fp
        dependency_lock = artifact.record.dependency_lock.lock_fp
        seed = artifact.record.seed
        cite = _training_artifact_cite(artifact)
        if is_refusal(cite):
            return cite
        training_cite = cite.value
    elif model_fp is not None:
        coerced = _optional_fp(model_fp, "model_fp")
        if is_refusal(coerced):
            return coerced
        if coerced.value is None:
            return invalid("model_fp", "model_fp resolved to an absent fingerprint")
        resolved_model_fp = coerced.value
    elif model_bytes is not None:
        if not isinstance(model_bytes, (bytes, bytearray, str)):
            return invalid(
                "model_bytes",
                "model_bytes is bytes or text for an external/incomplete candidate",
                given=type(model_bytes).__name__,
            )
        payload = (
            model_bytes.encode("utf-8") if isinstance(model_bytes, str) else bytes(model_bytes)
        )
        resolved_model_fp = fingerprint_bytes(payload)
    else:
        # Content-address a declared external stub so provenance stays honest.
        stub = fingerprint(
            {
                "class": "regime-external-candidate-stub",
                "family": family_token,
                "candidate_kind": kind.value,
                "authority": False,
            }
        )
        if is_refusal(stub):
            return stub
        resolved_model_fp = stub.value

    if isinstance(evaluation, EvaluationReport):
        if (
            evaluation.verdict is EvaluationVerdict.ACCEPTED
            and kind is CandidateKind.REJECTED_EVALUATION
        ):
            return policy(
                "evaluation",
                "rejected-evaluation candidates require a refused evaluation verdict",
                failure_id="mis.regime_register.accepted_as_rejected",
                given=evaluation.verdict.value,
            )
        scored = evaluation.governed_fingerprint()
        if is_refusal(scored):
            return scored
        eval_fp = scored.value

    return Ok(
        RegimeModelRegistration(
            artifact_id=REGIME_REGISTER_ARTIFACT_ID,
            producer_id=REGIME_CLASSIFIER_PRODUCER_ID,
            status=status.value,
            candidate_kind=kind,
            model_fp=resolved_model_fp,
            feature_schema_fp=feature_fp.value,
            class_mapping_fp=class_fp.value,
            evaluation_report_fp=eval_fp,
            training_config_fp=training_config,
            code_fp=code_fp,
            dependency_lock_fp=dependency_lock,
            seed=seed,
            cleaned_fp=None,
            labeled_fp=None,
            splits_fp=None,
            design_fp=design_fp.value,
            contract_fp=contract_fp.value,
            training_artifact_fp=training_cite,
            external_family=family_token,
            provenance=SANDBOX_PROVENANCE,
            grants_money_path_authority=False,
            grants_governed_binding=False,
            grants_live_consumer_binding=False,
            changes_composition_fp=False,
            format_version=REGIME_REGISTER_FORMAT_VERSION,
        )
    )


def _optional_fp(value: object | None, field: str) -> Result[Fingerprint | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            field,
            f"{field} is an fp1 fingerprint",
            given=repr(value),
        )
    return Ok(parsed.value)


def register_model_lineage(
    registration: object,
    *,
    registrar: object,
    edge_log: object,
    writer: object,
    sequence: object,
    created_at: object,
    composition_fp: object | None = None,
    prior_registration_fp: object | None = None,
    output_dir: object | None = None,
) -> Result[RegistrationLineageBundle]:
    """Mint the CT-06 record and append-only CT-07 occurrence-of lineage edges."""
    if not isinstance(registration, RegimeModelRegistration):
        return invalid(
            "registration",
            "register_model_lineage takes a RegimeModelRegistration",
            given=type(registration).__name__,
        )
    if registration.status.value in FORBIDDEN_AUTHORITY_STATUSES:
        return refuse_governed_or_active_status(status=registration.status.value)
    if (
        registration.grants_money_path_authority
        or registration.grants_governed_binding
        or registration.grants_live_consumer_binding
    ):
        return refuse_live_consumer_binding(claim="registration authority flags")
    if registration.changes_composition_fp:
        return refuse_composition_fp_mutation(claim="registration.changes_composition_fp")
    if not _is_registrar(registrar):
        return invalid(
            "registrar",
            "registration stamps through a CT-06 Registrar",
            given=type(registrar).__name__,
        )
    if not _is_edge_log(edge_log):
        return invalid(
            "edge_log",
            "lineage appends through a CT-07 EdgeLog",
            given=type(edge_log).__name__,
        )
    if not isinstance(writer, WriterId):
        return invalid("writer", "registration carries a WriterId", given=type(writer).__name__)
    if not isinstance(created_at, Instant):
        return invalid(
            "created_at",
            "registration created_at is an Instant occurrence fact",
            given=type(created_at).__name__,
        )
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        return invalid(
            "sequence",
            "per-writer sequence is a non-negative int",
            given=repr(sequence),
        )

    composition_before = _optional_fp(composition_fp, "composition_fp")
    if is_refusal(composition_before):
        return composition_before
    prior = _optional_fp(prior_registration_fp, "prior_registration_fp")
    if is_refusal(prior):
        return prior

    reg_fp = registration.fingerprint()
    if is_refusal(reg_fp):
        return reg_fp

    body = {_BODY_FIELD: registration.fp1_identity()}
    parents: list[Fingerprint] = [registration.design_fp, registration.model_fp]
    receipt = registrar.register(
        kind=REGIME_MODEL_KIND,
        body=body,
        writer=writer,
        sequence=sequence,
        created_at=created_at,
        at_birth_parent_refs=tuple(parents),
    )
    if is_refusal(receipt):
        return receipt
    admitted = receipt.value

    edges: list[_LineageEdgeLike] = []
    for target in registration.lineage_targets():
        appended = edge_log.append(
            edge_type=REGISTRATION_LINEAGE_EDGE_TYPE,
            from_ref=admitted.record.stable_id,
            to_ref=target,
        )
        if is_refusal(appended):
            return appended
        edges.append(appended.value.edge)

    if prior.value is not None:
        # A changed byte/config mints a new version; link with branches-from.
        branched = edge_log.append(
            edge_type=_BRANCHES_FROM_EDGE_TYPE,
            from_ref=admitted.record.stable_id,
            to_ref=prior.value,
        )
        if is_refusal(branched):
            return branched
        edges.append(branched.value.edge)

    # Still unbound on the governed producer catalog — registration is not binding.
    still_unbound = refuse_trained_regime_classifier(REGIME_CLASSIFIER_PRODUCER_ID)
    if not is_refusal(still_unbound):
        return policy(
            "producer_id",
            "governed producer catalog must still refuse regime_classifier_v1 after registration",
            failure_id="mis.regime_register.governed_binding_leak",
        )

    bundle = RegistrationLineageBundle(
        registration=registration,
        registration_fp=reg_fp.value,
        record=admitted.record,
        outcome=admitted.outcome,
        edges=tuple(edges),
        prior_registration_fp=prior.value,
        composition_fp_before=composition_before.value,
        composition_fp_after=composition_before.value,
    )

    if output_dir is not None:
        written = _write_registration_outputs(bundle, output_dir=output_dir)
        if is_refusal(written):
            return written

    return Ok(bundle)


def mint_registration_version(
    registration: object,
    *,
    registrar: object,
    edge_log: object,
    writer: object,
    sequence: object,
    created_at: object,
    prior_bundle: object,
    composition_fp: object | None = None,
    output_dir: object | None = None,
) -> Result[RegistrationLineageBundle]:
    """Mint a new registration version when content changes; link via branches-from."""
    if not isinstance(prior_bundle, RegistrationLineageBundle):
        return invalid(
            "prior_bundle",
            "mint_registration_version cites a prior RegistrationLineageBundle",
            given=type(prior_bundle).__name__,
        )
    if not isinstance(registration, RegimeModelRegistration):
        return invalid(
            "registration",
            "mint_registration_version takes a RegimeModelRegistration",
            given=type(registration).__name__,
        )
    new_fp = registration.fingerprint()
    if is_refusal(new_fp):
        return new_fp
    if new_fp.value == prior_bundle.registration_fp:
        return policy(
            "registration_fp",
            "identical registration content deduplicates; a changed byte or "
            "semantic config is required to mint a new version",
            failure_id="mis.regime_register.identical_version",
            fingerprint=new_fp.value.value,
        )
    return register_model_lineage(
        registration,
        registrar=registrar,
        edge_log=edge_log,
        writer=writer,
        sequence=sequence,
        created_at=created_at,
        composition_fp=composition_fp,
        prior_registration_fp=prior_bundle.stable_id,
        output_dir=output_dir,
    )


def assert_registration_preserves_composition_fp(
    bundle: object,
    *,
    composition_fp: object,
) -> Result[None]:
    """Verify registration left node composition_fp unchanged."""
    if not isinstance(bundle, RegistrationLineageBundle):
        return invalid(
            "bundle",
            "composition_fp preservation checks a RegistrationLineageBundle",
            given=type(bundle).__name__,
        )
    expected = _optional_fp(composition_fp, "composition_fp")
    if is_refusal(expected):
        return expected
    if expected.value is None:
        return invalid("composition_fp", "composition_fp is required for the preservation check")
    if bundle.registration.changes_composition_fp:
        return refuse_composition_fp_mutation(claim="bundle.changes_composition_fp")
    if bundle.composition_fp_before != bundle.composition_fp_after:
        return refuse_composition_fp_mutation(
            claim=(f"before={bundle.composition_fp_before!r} after={bundle.composition_fp_after!r}")
        )
    if bundle.composition_fp_after != expected.value:
        return refuse_composition_fp_mutation(
            claim=f"observed={bundle.composition_fp_after!r} expected={expected.value!r}"
        )
    return Ok(None)


def enter_passive_hub_as_sandbox(
    bundle: object,
    *,
    tree: object,
    writer: object,
    artifact_key: object | None = None,
) -> Result[SandboxHubPublication]:
    """Accept the registration into the passive-hub inbox with sandbox provenance.

    Promotion publish/pull still refuse sandbox provenance until the separate
    human/recertification path (Story 30.8). Inbox write never changes
    ``composition_fp``.
    """
    if not isinstance(bundle, RegistrationLineageBundle):
        return invalid(
            "bundle",
            "passive-hub entry takes a RegistrationLineageBundle",
            given=type(bundle).__name__,
        )
    if not isinstance(tree, PassiveHubTree):
        return invalid(
            "tree",
            "passive-hub entry takes a PassiveHubTree",
            given=type(tree).__name__,
        )
    if not isinstance(writer, WriterId):
        return invalid("writer", "hub fragments are WriterId-scoped", given=type(writer).__name__)

    key_token = clean_token(artifact_key) or REGIME_REGISTER_ARTIFACT_ID
    payload = json.dumps(
        bundle.registration.as_jsonable(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload_fp = fingerprint_bytes(payload)
    hub_artifact = HubArtifact.try_create(
        artifact_key=key_token,
        fp1=payload_fp,
        provenance=SANDBOX_PROVENANCE,
    )
    if is_refusal(hub_artifact):
        return hub_artifact
    fragment = HubFragment.try_create(
        artifact_key=hub_artifact.value.artifact_key,
        fp1=hub_artifact.value.fp1,
        provenance=hub_artifact.value.provenance,
        writer=writer,
        payload=payload,
    )
    if is_refusal(fragment):
        return fragment
    accepted = accept_inbox_fragment(tree, fragment.value)
    if is_refusal(accepted):
        return accepted

    # Promotion rules still refuse sandbox provenance at publish and pull.
    publish_gate = refuse_sandbox_provenance(SANDBOX_PROVENANCE, crossing="publish")
    pull_gate = refuse_sandbox_provenance(SANDBOX_PROVENANCE, crossing="pull")
    if not is_refusal(publish_gate) or not is_refusal(pull_gate):
        return policy(
            "provenance",
            "sandbox provenance must remain refused at publish and pull after hub entry",
            failure_id="mis.regime_register.sandbox_gate_leak",
        )

    return Ok(
        SandboxHubPublication(
            registration_fp=bundle.registration_fp,
            hub_artifact=hub_artifact.value,
            provenance=SANDBOX_PROVENANCE,
            write_only_inbox=True,
            promotion_refused=True,
            publish_refused=True,
            composition_fp_unchanged=True,
        )
    )


def _write_registration_outputs(
    bundle: RegistrationLineageBundle,
    *,
    output_dir: object,
) -> Result[None]:
    token = clean_token(output_dir)
    if token is None and not isinstance(output_dir, Path):
        return invalid(
            "output_dir",
            "output_dir is a filesystem path string or Path",
            given=repr(output_dir),
        )
    path = output_dir if isinstance(output_dir, Path) else Path(token)  # type: ignore[arg-type]
    try:
        path.mkdir(parents=True, exist_ok=True)
        (path / _REGISTRATION_FILENAME).write_text(
            json.dumps(bundle.registration.as_jsonable(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        lines: list[bytes] = []
        for edge in bundle.edges:
            serialized = edge.canonical_line()
            if is_refusal(serialized):
                return serialized
            lines.append(serialized.value.rstrip(b"\n"))
        (path / _LINEAGE_FILENAME).write_bytes(b"\n".join(lines) + (b"\n" if lines else b""))
    except OSError as exc:
        return policy(
            "output_dir",
            "registration output directory is not writable",
            failure_id="mis.regime_register.output_dir",
            given=str(path),
            cause=str(exc),
        )
    return Ok(None)


def main(argv: Sequence[str] | None = None) -> int:
    """Operator entry placeholder — registration is an in-library API over prepared artifacts."""
    _ = argv
    print(
        "qmn.mis.regime_register is an in-library API: build_accepted_registration / "
        "register_model_lineage over prepared Story 30.4/30.5 artifacts; it never "
        "trains, never binds a live consumer, and never mutates composition_fp",
        flush=True,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
