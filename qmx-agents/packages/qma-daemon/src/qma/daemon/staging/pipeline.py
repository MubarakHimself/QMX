"""AD-22 admission pipeline: validate → verify → review → stage → apply (FR-Q66).

Deterministic validation (schema, immutable base, OCC), deterministic verification
(never an LLM judging itself), optional cross-model ReviewPolicy, staging via
``before_proposal_stage`` / ``after_proposal_stage``, and operator-only apply via
``before_proposal_apply`` / ``after_proposal_apply``. GAP-0074 evaluation gates
stay Deferred.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal

from qma.core.plugins.hooks import HookImplementationKind, HookSource
from qma.core.ports.handles import MONEY_PATH_FIELD_DIFF_SCHEMA, FieldLevelDiff
from qma.core.ports.model import DeploymentRecord, ReviewPolicy, select_reviewer
from qma.core.ports.refinement import (
    FINISHED_MISSION_TRAJECTORY_COUNT_KEY,
    GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES,
    PIPELINE_STAGES,
    STAGING_STORE_RECORD_TYPE,
    RefinementProposal,
    refuse_llm_self_judgment,
    refuse_self_improvement_evaluation_gates,
    validate_immutable_base,
    validate_optimistic_concurrency,
    validate_proposal_schema,
)
from qma.core.vocabulary.enums import HookResultDecision, HookVerb, ModelClass
from qma.daemon.hooks.registry import HookRegistry, event_names_for_verb
from qma.daemon.hooks.verifiers import DeterministicVerifier, run_deterministic_verifier
from qma.daemon.staging.proposal import (
    ProposalGate,
    accept_definition_store_proposal,
    apply_refinement_proposal,
)
from qma.wire.money_path_diff import validate_money_path_field_diff
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "FINISHED_MISSION_TRAJECTORY_COUNT_KEY",
    "GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES",
    "PIPELINE_STAGES",
    "STAGING_STORE_RECORD_TYPE",
    "AdmissionPipeline",
    "PipelineOutcome",
    "ProposalApprovalRequest",
]


_BLOCKING_BEFORE: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.BLOCK_STOP,
    }
)

VerifierKind = Literal["script", "test", "backtest_replay"]


@dataclass(frozen=True, slots=True)
class ProposalApprovalRequest:
    """Operator approval_request emitted before apply."""

    proposal_id: str
    money_path_relevant: bool
    schema: str | None
    payload: Mapping[str, object]

    def to_payload(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "kind": "approval_request",
            "proposal_id": self.proposal_id,
            "money_path_relevant": self.money_path_relevant,
            "payload": dict(self.payload),
        }
        if self.schema is not None:
            body["schema"] = self.schema
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class _StageInvocation:
    proposal: RefinementProposal
    before_event: str
    after_event: str


@dataclass(frozen=True, slots=True)
class PipelineOutcome:
    """Result of running the fixed AD-22 pipeline through staging or apply."""

    proposal: RefinementProposal
    stages_completed: tuple[str, ...]
    verifier_ref: str | None = None
    reviewer_deployment_id: str | None = None
    reviewer_family: str | None = None
    before_event: str | None = None
    after_event: str | None = None
    approval: ProposalApprovalRequest | None = None
    live: bool = False

    def to_payload(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "proposal_id": self.proposal.id,
            "state": self.proposal.state.value,
            "stages_completed": list(self.stages_completed),
            "live": self.live,
            "record_type": STAGING_STORE_RECORD_TYPE,
        }
        if self.verifier_ref is not None:
            body["verifier_ref"] = self.verifier_ref
        if self.reviewer_deployment_id is not None:
            body["reviewer_deployment_id"] = self.reviewer_deployment_id
        if self.reviewer_family is not None:
            body["reviewer_family"] = self.reviewer_family
        if self.before_event is not None:
            body["before_event"] = self.before_event
        if self.after_event is not None:
            body["after_event"] = self.after_event
        if self.approval is not None:
            body["approval"] = dict(self.approval.to_payload())
        return MappingProxyType(body)


@dataclass
class AdmissionPipeline:
    """Daemon-owned validate → verify → review → stage → apply gate (CT-50)."""

    staging: ProposalGate = field(default_factory=ProposalGate)
    hooks: HookRegistry | None = None
    evaluation_gates_armed: bool = False

    def refuse_evaluation_gates(self, **extra: object) -> TypedRefusal:
        """GAP-0074 stays Deferred — never arm trajectory evaluation gates."""
        return refuse_self_improvement_evaluation_gates(
            armed=self.evaluation_gates_armed,
            **extra,
        )

    def arm_evaluation_gates(self, *, finished_mission_count: object = None) -> Result[None]:
        """Explicitly refuse arming GAP-0074 gates in v1."""
        _ = finished_mission_count
        return self.refuse_evaluation_gates(attempted=True)

    def submit(
        self,
        *,
        summary: object,
        rationale: object,
        edits: Sequence[object],
        expected_outcome: object,
        verifier: DeterministicVerifier,
        proposal_id: str | None = None,
        author_family: str | None = None,
        catalog: Sequence[DeploymentRecord] = (),
        review_policy: ReviewPolicy | None = None,
        require_cross_model_review: bool = False,
        model_class: ModelClass | str = ModelClass.WORKHORSE_GENERAL,
        verifier_kind: VerifierKind = "script",
    ) -> Result[PipelineOutcome]:
        """Run validate → verify → optional review → stage (never live)."""
        accepted = accept_definition_store_proposal(
            summary=summary,
            rationale=rationale,
            edits=edits,
            expected_outcome=expected_outcome,
            proposal_id=proposal_id,
            author_family=author_family,
        )
        if is_refusal(accepted):
            return accepted
        proposal = accepted.value

        schema = validate_proposal_schema(proposal)
        if is_refusal(schema):
            return schema
        immutable = validate_immutable_base(schema.value)
        if is_refusal(immutable):
            return immutable
        occ = validate_optimistic_concurrency(
            immutable.value,
            current_references=self.staging.current_references(),
        )
        if is_refusal(occ):
            return occ
        validated = occ.value
        completed: list[str] = ["validate"]

        verified = self._verify(
            validated,
            verifier=verifier,
            verifier_kind=verifier_kind,
        )
        if is_refusal(verified):
            return verified
        verifier_ref, _evidence = verified.value
        completed.append("verify")

        reviewer: DeploymentRecord | None = None
        if require_cross_model_review or review_policy is not None or catalog:
            reviewed = self._optional_review(
                validated,
                author_family=author_family,
                catalog=catalog,
                review_policy=review_policy,
                model_class=model_class,
                require=require_cross_model_review or review_policy is not None,
            )
            if is_refusal(reviewed):
                return reviewed
            reviewer = reviewed.value
            if reviewer is not None:
                completed.append("review")

        staged = self._stage(validated)
        if is_refusal(staged):
            return staged
        completed.append("stage")
        invocation = staged.value
        return Ok(
            PipelineOutcome(
                proposal=invocation.proposal,
                stages_completed=tuple(completed),
                verifier_ref=verifier_ref,
                reviewer_deployment_id=(reviewer.deployment_id if reviewer is not None else None),
                reviewer_family=reviewer.model_family if reviewer is not None else None,
                before_event=invocation.before_event,
                after_event=invocation.after_event,
                live=False,
            )
        )

    def emit_approval_request(
        self,
        proposal_id: object,
        *,
        field_diff: Mapping[str, object] | None = None,
        money_path_relevant: bool = False,
    ) -> Result[ProposalApprovalRequest]:
        """Build an approval_request; money_path_relevant requires the named diff."""
        if not isinstance(proposal_id, str) or self.staging.get(proposal_id) is None:
            return policy_rejection(
                "proposal_id",
                "approval_request names a staged RefinementProposal id (CT-50)",
                proposal_id=repr(proposal_id),
            )
        if money_path_relevant:
            if field_diff is None:
                return policy_rejection(
                    "field_diff",
                    "a money_path_relevant candidate refuses approval_request "
                    "unless the payload carries the named qma-wire field-level "
                    "diff (CT-50; FR-Q66; AD-14)",
                )
            checked = validate_money_path_field_diff(field_diff)
            if is_refusal(checked):
                return checked
            diff: FieldLevelDiff = checked.value
            return Ok(
                ProposalApprovalRequest(
                    proposal_id=proposal_id,
                    money_path_relevant=True,
                    schema=MONEY_PATH_FIELD_DIFF_SCHEMA,
                    payload=diff.to_payload(),
                )
            )
        return Ok(
            ProposalApprovalRequest(
                proposal_id=proposal_id,
                money_path_relevant=False,
                schema=None,
                payload={"proposal_id": proposal_id},
            )
        )

    def apply(
        self,
        proposal_id: object,
        *,
        principal_class: object,
        field_diff: Mapping[str, object] | None = None,
        money_path_relevant: bool = False,
    ) -> Result[PipelineOutcome]:
        """Operator-only apply through ``before_proposal_apply`` / ``after_*``."""
        if self.evaluation_gates_armed:
            return self.refuse_evaluation_gates(during="apply")

        approval = self.emit_approval_request(
            proposal_id,
            field_diff=field_diff,
            money_path_relevant=money_path_relevant,
        )
        if is_refusal(approval):
            return approval

        if not isinstance(proposal_id, str):
            return policy_rejection(
                "proposal_apply",
                "apply names a staged RefinementProposal id (FR-Q66; AD-22)",
                proposal_id=repr(proposal_id),
            )
        staged = self.staging.get(proposal_id)
        if staged is None:
            return policy_rejection(
                "proposal_apply",
                "apply names a staged RefinementProposal id (FR-Q66; AD-22)",
                proposal_id=repr(proposal_id),
            )

        hooks = self.hooks or HookRegistry()
        before, after = event_names_for_verb(HookVerb.PROPOSAL_APPLY)
        payload: dict[str, object] = {
            "proposal_id": proposal_id,
            "principal_class": str(principal_class),
            "approval": dict(approval.value.to_payload()),
        }
        before_result = hooks.dispatch(before, payload=payload, source=HookSource.PLUGIN)
        if not is_ok(before_result):
            return before_result
        if before_result.value.decision in _BLOCKING_BEFORE:
            return policy_rejection(
                before,
                f"{before} resolved to {before_result.value.decision.value}; "
                "proposal not applied (CT-50; AD-10; FR-Q66)",
                given=before_result.value.reason or before_result.value.decision.value,
            )

        bodies = self.staging.definition_bodies()
        before_snapshots = {
            edit.target_id: dict(bodies[edit.target_id])
            for edit in staged.edits
            if edit.target_id in bodies
        }
        applied = apply_refinement_proposal(
            staged,
            principal_class=principal_class,
            before_snapshots=before_snapshots,
        )
        if is_refusal(applied):
            return applied
        recorded = self.staging.record_applied(applied.value)
        if is_refusal(recorded):
            return recorded
        result = recorded.value

        after_payload = dict(payload)
        after_payload["effect"] = dict(result.to_payload())
        after_result = hooks.dispatch(after, payload=after_payload, source=HookSource.PLUGIN)
        if not is_ok(after_result):
            return after_result

        return Ok(
            PipelineOutcome(
                proposal=result,
                stages_completed=("approve", "apply"),
                before_event=before,
                after_event=after,
                approval=approval.value,
                live=False,
            )
        )

    def promote_refused(self, proposal_id: object) -> Result[None]:
        return self.staging.promote_refused(proposal_id)

    def _verify(
        self,
        proposal: RefinementProposal,
        *,
        verifier: DeterministicVerifier,
        verifier_kind: VerifierKind,
    ) -> Result[tuple[str, Mapping[str, object]]]:
        kind = verifier.kind
        if kind not in {
            HookImplementationKind.CALLABLE,
            HookImplementationKind.SUBPROCESS,
        }:
            return refuse_llm_self_judgment(kind=repr(kind))
        if verifier_kind not in {"script", "test", "backtest_replay"}:
            return refuse_llm_self_judgment(verifier_kind=verifier_kind)

        evidence = run_deterministic_verifier(
            verifier,
            {
                "proposal_id": proposal.id,
                "summary": proposal.summary,
                "expected_outcome": proposal.expected_outcome,
                "edits": [dict(edit.to_payload()) for edit in proposal.edits],
                "verifier_kind": verifier_kind,
            },
        )
        if is_refusal(evidence):
            return evidence
        body = evidence.value
        if not bool(body.get("passed", False)):
            return policy_rejection(
                "verifier",
                "deterministic verifier refused the proposal (CT-50; FR-Q66)",
                evidence=dict(body),
                verifier_kind=verifier_kind,
            )
        ref = body.get("verifier_ref")
        if not isinstance(ref, str) or ref.strip() == "":
            ref = f"verifier:{proposal.id}:{verifier_kind}"
        return Ok((ref, body))

    def _optional_review(
        self,
        proposal: RefinementProposal,
        *,
        author_family: str | None,
        catalog: Sequence[DeploymentRecord],
        review_policy: ReviewPolicy | None,
        model_class: ModelClass | str,
        require: bool,
    ) -> Result[DeploymentRecord | None]:
        if not require and not catalog:
            return Ok(None)
        if author_family is not None and any(
            entry.model_family == author_family and entry.deployment_id == "self"
            for entry in catalog
        ):
            # Defensive: never select the proposing deployment as reviewer.
            pass
        policy = review_policy or ReviewPolicy(model_class=model_class)
        reviewer = select_reviewer(
            author_family if author_family is not None else proposal.author_family,
            catalog,
            model_class=policy.model_class,
        )
        if is_refusal(reviewer):
            if require:
                return reviewer
            return Ok(None)
        selected = reviewer.value
        family = selected.model_family
        author = author_family if author_family is not None else proposal.author_family
        if author is not None and family == author:
            return refuse_llm_self_judgment(
                author_family=author,
                reviewer_family=family,
            )
        return Ok(selected)

    def _stage(self, proposal: RefinementProposal) -> Result[_StageInvocation]:
        hooks = self.hooks or HookRegistry()
        before, after = event_names_for_verb(HookVerb.PROPOSAL_STAGE)
        payload: dict[str, object] = {
            "proposal": dict(proposal.to_payload()),
            "record_type": STAGING_STORE_RECORD_TYPE,
        }

        before_result = hooks.dispatch(before, payload=payload, source=HookSource.MISSION)
        if not is_ok(before_result):
            return before_result
        if before_result.value.decision in _BLOCKING_BEFORE:
            return policy_rejection(
                before,
                f"{before} resolved to {before_result.value.decision.value}; "
                "proposal not staged (CT-50; AD-10; FR-Q66)",
                given=before_result.value.reason or before_result.value.decision.value,
            )
        stored = self.staging.store(proposal)
        if is_refusal(stored):
            return stored
        effect = MappingProxyType({"proposal_id": stored.value.id, "live": False})
        after_payload = dict(payload)
        after_payload["effect"] = dict(effect)
        after_result = hooks.dispatch(after, payload=after_payload, source=HookSource.MISSION)
        if not is_ok(after_result):
            return after_result
        kept = self.staging.get(proposal.id)
        if kept is None:
            return invalid_input("proposal", "staging store lost the proposal")
        return Ok(
            _StageInvocation(
                proposal=kept,
                before_event=before,
                after_event=after,
            )
        )
