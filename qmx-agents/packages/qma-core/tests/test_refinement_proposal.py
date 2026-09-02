"""Story 47.3 — CT-50 RefinementProposal definitions (FR-Q66)."""

from __future__ import annotations

from typing import cast

from qma.core.ports.refinement import (
    CLOSED_EDIT_KINDS,
    GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES,
    PIPELINE_STAGES,
    ROLE_BASE_PATH,
    ROLE_OVERLAY_PATH,
    STAGING_STORE_RECORD_TYPE,
    WORKER_TEMPLATE_REQUIRED_FIELDS,
    accept_refinement_proposal,
    definition_reference,
    parse_proposal_edit,
    refuse_llm_self_judgment,
    refuse_self_improvement_evaluation_gates,
    validate_immutable_base,
    validate_optimistic_concurrency,
    validate_proposal_schema,
)
from qma.core.vocabulary.enums import RefinementEditKind
from qmf.core import is_ok, is_refusal


def test_closed_edit_kinds_and_pipeline_stages() -> None:
    assert {kind.value for kind in RefinementEditKind} == CLOSED_EDIT_KINDS
    assert "variable" not in CLOSED_EDIT_KINDS
    assert "subagent" not in CLOSED_EDIT_KINDS
    assert PIPELINE_STAGES == (
        "validate",
        "verify",
        "review",
        "stage",
        "approve",
        "apply",
    )
    assert STAGING_STORE_RECORD_TYPE == "refinement-proposal"
    assert ROLE_BASE_PATH == "role.base"
    assert ROLE_OVERLAY_PATH == "role.overlay"


def test_accept_proposal_and_role_overlay_default() -> None:
    accepted = accept_refinement_proposal(
        summary="narrow role",
        rationale="fewer tools",
        edits=[
            {
                "kind": "role",
                "operation": "update",
                "id": "researcher",
                "reference": "fp1:sha256:abc",
                "content": {"toolset_ids": ["readonly"]},
            }
        ],
        expected_outcome="overlay narrowed",
    )
    assert is_ok(accepted)
    assert accepted.value.edits[0].path == ROLE_OVERLAY_PATH
    assert accepted.value.to_payload()["type"] == STAGING_STORE_RECORD_TYPE


def test_role_base_and_subagent_refused() -> None:
    base = parse_proposal_edit(
        {
            "kind": "role",
            "operation": "update",
            "id": "researcher",
            "path": "role.base",
            "reference": "fp1:sha256:abc",
            "content": {},
        }
    )
    assert is_refusal(base)
    assert "role.base" in str(base.context.get("reason", ""))

    sub = parse_proposal_edit(
        {
            "kind": "subagent",
            "operation": "create",
            "id": "child",
            "content": {},
        }
    )
    assert is_refusal(sub)
    assert "worker_template" in str(sub.context.get("reason", ""))


def test_worker_template_shape_and_occ() -> None:
    incomplete = accept_refinement_proposal(
        summary="worker",
        rationale="spawn",
        edits=[
            {
                "kind": "worker_template",
                "operation": "create",
                "id": "wt.analysis",
                "content": {"role_ref": "analyst"},
            }
        ],
        expected_outcome="template",
    )
    assert is_ok(incomplete)
    schema = validate_proposal_schema(incomplete.value)
    assert is_refusal(schema)
    missing = cast("list[str]", schema.context["missing"])
    assert sorted(missing) == sorted(WORKER_TEMPLATE_REQUIRED_FIELDS - {"role_ref"})

    content = {
        "role_ref": "analyst",
        "toolset_ref": "tools.readonly",
        "model_class": "WORKHORSE_GENERAL",
        "environment_ref": "env.local",
        "compute_requirement": {"cpus": 1},
        "permission_set": ["read"],
    }
    ok = accept_refinement_proposal(
        summary="worker",
        rationale="spawn",
        edits=[
            {
                "kind": "worker_template",
                "operation": "create",
                "id": "wt.analysis",
                "content": content,
            }
        ],
        expected_outcome="template",
    )
    assert is_ok(ok)
    assert is_ok(validate_proposal_schema(ok.value))

    live_ref = definition_reference({"body": "v1"})
    assert is_ok(live_ref)
    update = accept_refinement_proposal(
        summary="skill",
        rationale="bump",
        edits=[
            {
                "kind": "skill",
                "operation": "update",
                "id": "skill.a",
                "reference": "stale",
                "content": {"body": "v2"},
            }
        ],
        expected_outcome="updated",
    )
    assert is_ok(update)
    conflict = validate_optimistic_concurrency(
        update.value,
        current_references={"skill.a": live_ref.value},
    )
    assert is_refusal(conflict)

    matched = accept_refinement_proposal(
        summary="skill",
        rationale="bump",
        edits=[
            {
                "kind": "skill",
                "operation": "update",
                "id": "skill.a",
                "reference": live_ref.value,
                "content": {"body": "v2"},
            }
        ],
        expected_outcome="updated",
    )
    assert is_ok(matched)
    assert is_ok(
        validate_optimistic_concurrency(
            matched.value,
            current_references={"skill.a": live_ref.value},
        )
    )


def test_gap_0074_and_llm_self_judgment_stay_refused() -> None:
    gates = refuse_self_improvement_evaluation_gates()
    assert gates.context["gap"] == GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES
    assert gates.context.get("deferred") is True

    llm = refuse_llm_self_judgment(kind="prompt")
    assert llm.context.get("llm_self_judgment") is False

    immutable = accept_refinement_proposal(
        summary="prompt into base",
        rationale="no",
        edits=[
            {
                "kind": "prompt",
                "operation": "update",
                "id": "role.researcher",
                "path": "role.base",
                "reference": "fp1:sha256:x",
                "content": {"text": "system"},
            }
        ],
        expected_outcome="blocked",
    )
    assert is_ok(immutable)
    refused = validate_immutable_base(immutable.value)
    assert is_refusal(refused)
