"""RefinementProposal record and admission-gate vocabulary (CT-50; AD-22).

Definitions only. The staging store holds exactly this one record type. The
daemon owns validate → verify → review → stage → approve → apply. A proposal is
**applied**, never promoted. Self-improvement evaluation gates stay Deferred
GAP-0074; v1 ships invariants plus staging.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal, cast
from uuid import uuid4

from qma.core.content import content_address
from qma.core.vocabulary.enums import RefinementEditKind
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result, is_refusal
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "CLOSED_EDIT_KINDS",
    "EDIT_OPERATIONS",
    "FINISHED_MISSION_TRAJECTORY_COUNT_KEY",
    "GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES",
    "PIPELINE_STAGES",
    "ROLE_BASE_PATH",
    "ROLE_OVERLAY_PATH",
    "RUNTIME_INSTANCE_EDIT_KINDS",
    "STAGING_STORE_RECORD_TYPE",
    "WORKER_TEMPLATE_REQUIRED_FIELDS",
    "EditOperation",
    "ProposalEdit",
    "ProposalState",
    "RefinementProposal",
    "accept_refinement_proposal",
    "definition_reference",
    "parse_proposal_edit",
    "refuse_llm_self_judgment",
    "refuse_money_path_edit_target",
    "refuse_role_base_on_proposal_path",
    "refuse_runtime_instance_edit",
    "refuse_self_improvement_evaluation_gates",
    "refuse_subagent_edit_kind",
    "validate_immutable_base",
    "validate_optimistic_concurrency",
    "validate_proposal_schema",
    "validate_worker_template_shape",
]


GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES: Final[str] = "GAP-0074"

FINISHED_MISSION_TRAJECTORY_COUNT_KEY: Final[str] = (
    "registry:deferred.finished_mission_trajectory_count"
)

STAGING_STORE_RECORD_TYPE: Final[str] = "refinement-proposal"

ROLE_BASE_PATH: Final[str] = "role.base"
ROLE_OVERLAY_PATH: Final[str] = "role.overlay"

CLOSED_EDIT_KINDS: Final[frozenset[str]] = frozenset(member.value for member in RefinementEditKind)

EDIT_OPERATIONS: Final[frozenset[str]] = frozenset({"create", "update", "delete"})

PIPELINE_STAGES: Final[tuple[str, ...]] = (
    "validate",
    "verify",
    "review",
    "stage",
    "approve",
    "apply",
)

# Runtime-instanced objects are never edit kinds (CT-50; DEC-0321).
RUNTIME_INSTANCE_EDIT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "subagent",
        "agent",
        "session",
        "mission",
        "worker",
        "quant",
        "task",
        "task_graph",
    }
)

WORKER_TEMPLATE_REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "role_ref",
        "toolset_ref",
        "model_class",
        "environment_ref",
        "compute_requirement",
        "permission_set",
    }
)

EditOperation = Literal["create", "update", "delete"]


class ProposalState(StrEnum):
    """Staging lifecycle for one RefinementProposal."""

    STAGED = "staged"
    APPLIED = "applied"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class ProposalEdit:
    """One create/update/delete over a closed edit kind — never ``variable``."""

    kind: RefinementEditKind
    operation: EditOperation
    target_id: str
    content: Mapping[str, object] = field(default_factory=dict[str, object])
    reference: str | None = None
    path: str | None = None

    def __post_init__(self) -> None:
        if self.kind is RefinementEditKind.ROLE and self.path == ROLE_BASE_PATH:
            msg = (
                "role.base is immutable to the RefinementProposal pipeline; "
                "only role.overlay is proposal-editable (CT-50; AD-22)"
            )
            raise ValueError(msg)
        if self.kind is RefinementEditKind.ROLE and self.path is None:
            object.__setattr__(self, "path", ROLE_OVERLAY_PATH)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind.value,
            "operation": self.operation,
            "id": self.target_id,
            "content": dict(self.content),
        }
        if self.reference is not None:
            payload["reference"] = self.reference
        if self.path is not None:
            payload["path"] = self.path
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class RefinementProposal:
    """Single staging-store record type for definition-store agent edits."""

    id: str
    summary: str
    rationale: str
    edits: tuple[ProposalEdit, ...]
    expected_outcome: str
    state: ProposalState = ProposalState.STAGED
    applied_snapshots: Mapping[str, object] | None = None
    money_path_relevant: bool = False
    author_family: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        """JSON-native staging payload."""
        payload: dict[str, object] = {
            "type": STAGING_STORE_RECORD_TYPE,
            "id": self.id,
            "summary": self.summary,
            "rationale": self.rationale,
            "expected_outcome": self.expected_outcome,
            "state": self.state.value,
            "money_path_relevant": self.money_path_relevant,
            "edits": [dict(edit.to_payload()) for edit in self.edits],
        }
        if self.author_family is not None:
            payload["author_family"] = self.author_family
        if self.applied_snapshots is not None:
            payload["applied_snapshots"] = dict(self.applied_snapshots)
        return MappingProxyType(payload)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def refuse_self_improvement_evaluation_gates(**extra: object) -> TypedRefusal:
    """Trajectory-count evaluation gates stay Deferred GAP-0074 (CT-50)."""
    return _policy(
        "evaluation_gates",
        "self-improvement evaluation gates are Deferred GAP-0074; v1 ships "
        "invariants plus staging only and never arms the trajectory threshold "
        f"({FINISHED_MISSION_TRAJECTORY_COUNT_KEY}) (CT-50; FR-Q66; DEC-0321)",
        gap=GAP_0074_SELF_IMPROVEMENT_EVALUATION_GATES,
        deferred=True,
        threshold_key=FINISHED_MISSION_TRAJECTORY_COUNT_KEY,
        **extra,
    )


def refuse_llm_self_judgment(**extra: object) -> TypedRefusal:
    """An LLM never verifies or judges its own RefinementProposal."""
    return _policy(
        "verifier",
        "deterministic verification uses a verifier script, test or backtest "
        "replay; an LLM never judges its own proposal (CT-50; FR-Q66; AD-22)",
        llm_self_judgment=False,
        **extra,
    )


def refuse_role_base_on_proposal_path(**extra: object) -> TypedRefusal:
    """``role.base`` is operator-only via ``role.set_base``, never this pipeline."""
    return _policy(
        "role_base",
        "role.base is written only by an operator-principal role.set_base; "
        "the proposal pipeline accepts only role.overlay (CT-50; FR-Q66; AD-22)",
        path=ROLE_BASE_PATH,
        **extra,
    )


def refuse_subagent_edit_kind(**extra: object) -> TypedRefusal:
    """``subagent`` is never an edit kind; durable workers use ``worker_template``."""
    return _policy(
        "refinement_edit_kind",
        "subagent is not an edit kind; a spawned worker's durable definition is "
        "a worker_template (CT-50; FR-Q66; AD-22)",
        kind="subagent",
        **extra,
    )


def refuse_runtime_instance_edit(*, kind: object, **extra: object) -> TypedRefusal:
    """Runtime-instanced objects are not RefinementProposal edit targets."""
    return _policy(
        "refinement_edit_kind",
        "only definitions are edit targets; runtime instances are not edit "
        "kinds (CT-50; FR-Q66; AD-22)",
        kind=repr(kind),
        **extra,
    )


def refuse_money_path_edit_target(**extra: object) -> TypedRefusal:
    """No edit kind may name a money-path record (CT-50; AD-14, AD-22)."""
    return _policy(
        "money_path",
        "no RefinementProposal edit may name a money-path record; nothing in "
        "this pipeline reaches qmf-registry or a registry zone (CT-50; FR-Q66)",
        **extra,
    )


def parse_proposal_edit(raw: object) -> Result[ProposalEdit]:
    """Parse one edit mapping against the closed AD-22 kind/operation set."""
    if not isinstance(raw, Mapping):
        return _invalid(
            "edit",
            "a RefinementProposal edit is a mapping with kind, operation, and id (CT-50; FR-Q66)",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    kind_raw = body.get("kind")
    if isinstance(kind_raw, str) and kind_raw == "variable":
        return _policy(
            "refinement_edit_kind",
            "there is no variable edit kind; an agent, hook, Role or Mission may "
            "never set a registered variable through a RefinementProposal "
            "(FR-Q36; AD-26)",
            kind=kind_raw,
        )
    if isinstance(kind_raw, str) and kind_raw == "subagent":
        return refuse_subagent_edit_kind()
    if isinstance(kind_raw, str) and kind_raw in RUNTIME_INSTANCE_EDIT_KINDS:
        return refuse_runtime_instance_edit(kind=kind_raw)
    try:
        kind = parse_closed(RefinementEditKind, kind_raw)
    except VocabularyError as exc:
        return _policy(
            "refinement_edit_kind",
            "edit kind must be one of the nine closed AD-22 kinds; variable is "
            "not among them (CT-50; FR-Q66; AD-22)",
            kind=repr(kind_raw),
            detail=str(exc),
        )
    operation = body.get("operation")
    if operation not in EDIT_OPERATIONS:
        return _invalid(
            "operation",
            "edit operation is create | update | delete",
            given=repr(operation),
        )
    target_id = body.get("id")
    if not isinstance(target_id, str) or target_id.strip() == "":
        return _invalid(
            "id",
            "each edit names a non-empty target definition id",
            given=repr(target_id),
        )
    path = body.get("path")
    if kind is RefinementEditKind.ROLE:
        if path in {ROLE_BASE_PATH, "base"}:
            return refuse_role_base_on_proposal_path(given=repr(path))
        if path is not None and path not in {ROLE_OVERLAY_PATH, "overlay"}:
            return _policy(
                "role_path",
                "role edits target role.overlay only (CT-50; FR-Q66; AD-22)",
                given=repr(path),
            )
        path = ROLE_OVERLAY_PATH
    content = body.get("content", {})
    if not isinstance(content, Mapping):
        return _invalid(
            "content",
            "edit content is a mapping",
            given=repr(type(content).__name__),
        )
    content_map = cast("Mapping[str, object]", content)
    if content_map.get("money_path_relevant") is True:
        return refuse_money_path_edit_target(target_id=target_id)
    if any(key.startswith("money_path") for key in content_map):
        return refuse_money_path_edit_target(target_id=target_id)
    reference = body.get("reference")
    if reference is not None and not isinstance(reference, str):
        return _invalid(
            "reference",
            "edit reference is a string when present",
            given=repr(reference),
        )
    if operation in {"update", "delete"} and (
        not isinstance(reference, str) or reference.strip() == ""
    ):
        return _invalid(
            "reference",
            "update and delete edits carry a reference for immutable-base and "
            "optimistic-concurrency checks (CT-50; FR-Q66)",
            given=repr(reference),
        )
    path_s = path if isinstance(path, str) else None
    return Ok(
        ProposalEdit(
            kind=kind,
            operation=cast("EditOperation", operation),
            target_id=target_id.strip(),
            content=MappingProxyType(dict(content_map)),
            reference=reference.strip() if isinstance(reference, str) else None,
            path=path_s,
        )
    )


def accept_refinement_proposal(
    *,
    summary: object,
    rationale: object,
    edits: Sequence[object],
    expected_outcome: object,
    proposal_id: str | None = None,
    money_path_relevant: bool = False,
    author_family: str | None = None,
) -> Result[RefinementProposal]:
    """Build a RefinementProposal after schema-level field checks."""
    if money_path_relevant:
        return refuse_money_path_edit_target(
            detail="a RefinementProposal never carries money_path_relevant",
        )
    if not isinstance(summary, str) or summary.strip() == "":
        return _invalid("summary", "proposal summary is a non-empty string")
    if not isinstance(rationale, str) or rationale.strip() == "":
        return _invalid("rationale", "proposal rationale is a non-empty string")
    if not isinstance(expected_outcome, str) or expected_outcome.strip() == "":
        return _invalid(
            "expected_outcome",
            "proposal expected_outcome is a non-empty string",
        )
    if not edits:
        return _invalid(
            "edits",
            "a RefinementProposal carries one or more edits (CT-50; FR-Q66)",
        )
    parsed: list[ProposalEdit] = []
    for raw in edits:
        edit = parse_proposal_edit(raw)
        if is_refusal(edit):
            return edit
        parsed.append(edit.value)
    return Ok(
        RefinementProposal(
            id=proposal_id if proposal_id else str(uuid4()),
            summary=summary.strip(),
            rationale=rationale.strip(),
            edits=tuple(parsed),
            expected_outcome=expected_outcome.strip(),
            state=ProposalState.STAGED,
            money_path_relevant=False,
            author_family=author_family,
        )
    )


def validate_proposal_schema(proposal: RefinementProposal) -> Result[RefinementProposal]:
    """Deterministic schema validation for a constructed proposal."""
    if not proposal.edits:
        return _invalid("edits", "a RefinementProposal carries one or more edits")
    for edit in proposal.edits:
        if edit.kind.value not in CLOSED_EDIT_KINDS:
            return refuse_runtime_instance_edit(kind=edit.kind.value)
        if edit.kind is RefinementEditKind.ROLE and edit.path == ROLE_BASE_PATH:
            return refuse_role_base_on_proposal_path()
        if edit.kind is RefinementEditKind.WORKER_TEMPLATE and edit.operation != "delete":
            shaped = validate_worker_template_shape(edit.content)
            if is_refusal(shaped):
                return shaped
    return Ok(proposal)


def validate_worker_template_shape(content: Mapping[str, object]) -> Result[None]:
    """``worker_template`` carries the durable spawned-worker definition fields."""
    missing = sorted(WORKER_TEMPLATE_REQUIRED_FIELDS - frozenset(content))
    if missing:
        return _invalid(
            "worker_template",
            "worker_template content requires role_ref, toolset_ref, model_class, "
            "environment_ref, compute_requirement and permission_set (CT-50; AD-22)",
            missing=missing,
        )
    return Ok(None)


def validate_immutable_base(proposal: RefinementProposal) -> Result[RefinementProposal]:
    """Reject any edit whose path resolves into ``role.base``."""
    for edit in proposal.edits:
        if edit.path == ROLE_BASE_PATH:
            return refuse_role_base_on_proposal_path(target_id=edit.target_id)
        if edit.kind is RefinementEditKind.ROLE and edit.path not in {
            None,
            ROLE_OVERLAY_PATH,
        }:
            return refuse_role_base_on_proposal_path(
                target_id=edit.target_id,
                given=repr(edit.path),
            )
        if edit.kind is RefinementEditKind.PROMPT and edit.path == ROLE_BASE_PATH:
            return refuse_role_base_on_proposal_path(target_id=edit.target_id)
    return Ok(proposal)


def validate_optimistic_concurrency(
    proposal: RefinementProposal,
    *,
    current_references: Mapping[str, str],
) -> Result[RefinementProposal]:
    """OCC: update/delete ``reference`` must match the live definition base."""
    for edit in proposal.edits:
        if edit.operation == "create":
            if edit.target_id in current_references:
                return _policy(
                    "optimistic_concurrency",
                    "create refuses an id that already exists in the definition "
                    "store (CT-50; FR-Q66)",
                    target_id=edit.target_id,
                )
            continue
        live = current_references.get(edit.target_id)
        if live is None:
            return _policy(
                "optimistic_concurrency",
                "update/delete requires a live definition base (CT-50; FR-Q66)",
                target_id=edit.target_id,
                operation=edit.operation,
            )
        if edit.reference != live:
            return _policy(
                "optimistic_concurrency",
                "edit reference does not match the live definition base (CT-50; FR-Q66; AD-22)",
                target_id=edit.target_id,
                expected=live,
                given=edit.reference,
            )
    return Ok(proposal)


def definition_reference(content: Mapping[str, object]) -> Result[str]:
    """Content-address a definition body for OCC reference stamps."""
    addressed = content_address(dict(content))
    if is_refusal(addressed):
        return addressed
    return Ok(addressed.value.value)
