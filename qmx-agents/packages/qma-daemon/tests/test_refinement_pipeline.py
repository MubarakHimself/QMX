"""Story 47.3 — stage and apply verified RefinementProposals (FR-Q66; CT-50)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import pytest
from qma.core.plugins.hooks import HookImplementationKind
from qma.core.ports.handles import MONEY_PATH_FIELD_DIFF_SCHEMA
from qma.core.ports.model import DeploymentRecord
from qma.core.ports.refinement import (
    GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES,
    PIPELINE_STAGES,
    STAGING_STORE_RECORD_TYPE,
    definition_reference,
)
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary import GovernedAct, GovernedActTarget, validate_governed_act
from qma.core.vocabulary.enums import ModelClass, RefinementEditKind
from qma.core.vocabulary.registry import VocabularyError
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.hooks.verifiers import DeterministicVerifier
from qma.daemon.staging import AdmissionPipeline, ProposalGate
from qmf.core import is_ok, is_refusal


def _pass_verifier(_payload: Mapping[str, object]) -> Mapping[str, object]:
    return {"passed": True, "verifier_ref": "test:script:1"}


def _fail_verifier(_payload: Mapping[str, object]) -> Mapping[str, object]:
    return {"passed": False, "reason": "tests_failed"}


def _worker_content() -> dict[str, object]:
    return {
        "role_ref": "analyst",
        "toolset_ref": "tools.readonly",
        "model_class": "WORKHORSE_GENERAL",
        "environment_ref": "env.local",
        "compute_requirement": {"cpus": 1},
        "permission_set": ["read"],
    }


def test_staging_store_accepts_only_refinement_proposal() -> None:
    gate = ProposalGate()
    assert gate.record_type == STAGING_STORE_RECORD_TYPE
    accepted = gate.accept(
        summary="narrow toolset",
        rationale="mission needs fewer tools",
        edits=[
            {
                "kind": "toolset",
                "operation": "create",
                "id": "research.readonly",
                "content": {"tools": ["market.read"]},
            }
        ],
        expected_outcome="toolset available",
        proposal_id="p-store",
    )
    assert is_ok(accepted)
    payload = accepted.value.to_payload()
    assert payload["type"] == STAGING_STORE_RECORD_TYPE
    assert payload["summary"]
    assert payload["rationale"]
    assert payload["expected_outcome"]
    assert accepted.value.edits[0].kind is RefinementEditKind.TOOLSET
    edits = cast("list[dict[str, object]]", payload["edits"])
    operations = {str(edit["operation"]) for edit in edits}
    kinds = {str(edit["kind"]) for edit in edits}
    assert operations <= {"create", "update", "delete"}
    assert kinds <= {
        "prompt",
        "memory",
        "skill",
        "toolset",
        "worker_template",
        "hook",
        "graph_template",
        "loop",
        "role",
    }


def test_pipeline_validate_verify_review_stage_never_live() -> None:
    hooks = HookRegistry()
    pipeline = AdmissionPipeline(hooks=hooks)
    catalog = (
        DeploymentRecord("author", ModelClass.WORKHORSE_GENERAL, "family-a"),
        DeploymentRecord("reviewer", ModelClass.REASONING_HIGH, "family-b"),
    )
    outcome = pipeline.submit(
        summary="add skill",
        rationale="document procedure",
        edits=[
            {
                "kind": "skill",
                "operation": "create",
                "id": "skill.review",
                "content": {"body": "checklist"},
            }
        ],
        expected_outcome="skill staged",
        proposal_id="p-stage",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_pass_verifier,
        ),
        author_family="family-a",
        catalog=catalog,
        require_cross_model_review=True,
        model_class=ModelClass.REASONING_HIGH,
    )
    assert is_ok(outcome)
    body = outcome.value
    assert body.live is False
    assert body.proposal.state.value == "staged"
    assert "validate" in body.stages_completed
    assert "verify" in body.stages_completed
    assert "review" in body.stages_completed
    assert "stage" in body.stages_completed
    assert body.before_event == "before_proposal_stage"
    assert body.after_event == "after_proposal_stage"
    assert body.reviewer_family == "family-b"
    assert body.reviewer_deployment_id == "reviewer"
    assert PIPELINE_STAGES[0] == "validate"


def test_verifier_failure_and_llm_self_judgment_refused() -> None:
    pipeline = AdmissionPipeline()
    failed = pipeline.submit(
        summary="bad",
        rationale="fail",
        edits=[
            {
                "kind": "hook",
                "operation": "create",
                "id": "hook.x",
                "content": {"phase": "before_tool"},
            }
        ],
        expected_outcome="blocked",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_fail_verifier,
        ),
    )
    assert is_refusal(failed)
    assert "verifier" in str(failed.context.get("field", "verifier"))

    with pytest.raises(VocabularyError):
        DeterministicVerifier(kind="prompt")


def test_operator_apply_records_snapshots_machine_refused() -> None:
    hooks = HookRegistry()
    pipeline = AdmissionPipeline(hooks=hooks)
    staged = pipeline.submit(
        summary="create loop",
        rationale="repeat",
        edits=[
            {
                "kind": "loop",
                "operation": "create",
                "id": "loop.daily",
                "content": {"cadence": "1d"},
            }
        ],
        expected_outcome="loop staged",
        proposal_id="p-apply",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_pass_verifier,
        ),
    )
    assert is_ok(staged)

    machine = pipeline.apply("p-apply", principal_class="machine")
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)

    applied = pipeline.apply("p-apply", principal_class="operator")
    assert is_ok(applied)
    assert applied.value.proposal.state.value == "applied"
    snapshots = applied.value.proposal.applied_snapshots
    assert snapshots is not None
    assert "loop.daily" in snapshots
    snap = cast("dict[str, object]", snapshots["loop.daily"])
    assert snap["before"] is None
    assert snap["after"] == {"cadence": "1d"}
    assert applied.value.before_event == "before_proposal_apply"
    assert applied.value.after_event == "after_proposal_apply"
    assert applied.value.live is False

    validate_governed_act(GovernedAct.APPLY, GovernedActTarget.REFINEMENT_PROPOSAL)
    with pytest.raises(VocabularyError):
        validate_governed_act(GovernedAct.PROMOTE, GovernedActTarget.REFINEMENT_PROPOSAL)
    promote = pipeline.promote_refused("p-apply")
    assert is_refusal(promote)


def test_role_base_worker_money_path_and_gap_0074() -> None:
    pipeline = AdmissionPipeline()
    role_base = pipeline.submit(
        summary="touch base",
        rationale="no",
        edits=[
            {
                "kind": "role",
                "operation": "update",
                "id": "researcher",
                "path": "role.base",
                "reference": "fp1:sha256:base",
                "content": {"toolset_ids": ["all"]},
            }
        ],
        expected_outcome="blocked",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_pass_verifier,
        ),
    )
    assert is_refusal(role_base)

    subagent = pipeline.submit(
        summary="spawn subagent",
        rationale="no",
        edits=[
            {
                "kind": "subagent",
                "operation": "create",
                "id": "child",
                "content": {},
            }
        ],
        expected_outcome="blocked",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_pass_verifier,
        ),
    )
    assert is_refusal(subagent)

    money = pipeline.submit(
        summary="money path",
        rationale="no",
        edits=[
            {
                "kind": "skill",
                "operation": "create",
                "id": "skill.risk",
                "content": {"money_path_relevant": True, "body": "x"},
            }
        ],
        expected_outcome="blocked",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_pass_verifier,
        ),
    )
    assert is_refusal(money)

    worker = pipeline.submit(
        summary="worker template",
        rationale="durable worker",
        edits=[
            {
                "kind": "worker_template",
                "operation": "create",
                "id": "wt.analysis",
                "content": _worker_content(),
            }
        ],
        expected_outcome="template staged",
        proposal_id="p-worker",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_pass_verifier,
        ),
    )
    assert is_ok(worker)
    assert worker.value.proposal.edits[0].kind is RefinementEditKind.WORKER_TEMPLATE

    missing_diff = pipeline.emit_approval_request(
        "p-worker",
        money_path_relevant=True,
    )
    assert is_refusal(missing_diff)

    with_diff = pipeline.emit_approval_request(
        "p-worker",
        money_path_relevant=True,
        field_diff={
            "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": "cand-1",
            "predecessor_ref": "pred-1",
            "fields": [{"path": "risk", "ancestor": 1, "proposed": 2}],
        },
    )
    assert is_ok(with_diff)
    assert with_diff.value.money_path_relevant is True
    assert with_diff.value.schema == MONEY_PATH_FIELD_DIFF_SCHEMA

    gates = pipeline.arm_evaluation_gates(finished_mission_count=50)
    assert is_refusal(gates)
    assert gates.context["gap"] == GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES
    assert gates.context.get("deferred") is True


def test_occ_conflict_on_stale_reference() -> None:
    pipeline = AdmissionPipeline()
    live = definition_reference({"body": "v1"})
    assert is_ok(live)
    pipeline.staging.seed_definition("skill.a", {"body": "v1"}, reference=live.value)

    stale = pipeline.submit(
        summary="stale update",
        rationale="occ",
        edits=[
            {
                "kind": "skill",
                "operation": "update",
                "id": "skill.a",
                "reference": "fp1:sha256:stale",
                "content": {"body": "v2"},
            }
        ],
        expected_outcome="blocked",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_pass_verifier,
        ),
    )
    assert is_refusal(stale)
    assert "optimistic_concurrency" in str(stale.context.get("field", ""))

    fresh = pipeline.submit(
        summary="fresh update",
        rationale="occ",
        edits=[
            {
                "kind": "skill",
                "operation": "update",
                "id": "skill.a",
                "reference": live.value,
                "content": {"body": "v2"},
            }
        ],
        expected_outcome="updated",
        proposal_id="p-occ",
        verifier=DeterministicVerifier(
            kind=HookImplementationKind.CALLABLE,
            run=_pass_verifier,
        ),
    )
    assert is_ok(fresh)
    applied = pipeline.apply("p-occ", principal_class="operator")
    assert is_ok(applied)
    snap = applied.value.proposal.applied_snapshots
    assert snap is not None
    skill_snap = cast("dict[str, object]", snap["skill.a"])
    assert skill_snap["before"] == {"body": "v1"}
    assert skill_snap["after"] == {"body": "v2"}
