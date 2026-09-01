"""AD-22 definition-store change boundary (FR-Q26; DEC-0307, DEC-0321, DEC-0345).

An Agent may enter a definition-store change only as a RefinementProposal. A
proposal is later **applied** through the governed staging path and is never
**promoted**. The sole direct Agent exception is a Mission-scoped,
template-validated observe-or-deny hook registered through ``before_hook_register``
and disposed with its Mission.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal, cast
from uuid import uuid4

from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary import (
    GovernedAct,
    GovernedActTarget,
    PrincipalClass,
    RefinementEditKind,
    VocabularyError,
    parse_closed,
    validate_governed_act,
)
from qma.wire.principals import authorize_wire_command
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "AGENT_DIRECT_DEFINITION_EXCEPTION",
    "EditOperation",
    "ProposalEdit",
    "ProposalGate",
    "ProposalState",
    "RefinementProposal",
    "accept_definition_store_proposal",
    "apply_refinement_proposal",
    "register_mission_scoped_hook_exception",
]


AGENT_DIRECT_DEFINITION_EXCEPTION: Final[str] = "before_hook_register"

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
        if self.kind is RefinementEditKind.ROLE and self.path == "role.base":
            msg = (
                "role.base is immutable to the RefinementProposal pipeline; "
                "only role.overlay is proposal-editable (FR-Q26; AD-22)"
            )
            raise ValueError(msg)


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

    def to_payload(self) -> Mapping[str, object]:
        """JSON-native staging payload."""
        payload: dict[str, object] = {
            "id": self.id,
            "summary": self.summary,
            "rationale": self.rationale,
            "expected_outcome": self.expected_outcome,
            "state": self.state.value,
            "edits": [
                {
                    "kind": edit.kind.value,
                    "operation": edit.operation,
                    "id": edit.target_id,
                    "content": dict(edit.content),
                    **({"reference": edit.reference} if edit.reference is not None else {}),
                    **({"path": edit.path} if edit.path is not None else {}),
                }
                for edit in self.edits
            ],
        }
        if self.applied_snapshots is not None:
            payload["applied_snapshots"] = dict(self.applied_snapshots)
        return MappingProxyType(payload)


def _parse_edit(raw: object) -> Result[ProposalEdit]:
    if not isinstance(raw, Mapping):
        return invalid_input(
            "edit",
            "a RefinementProposal edit is a mapping with kind, operation, and id (FR-Q26; AD-22)",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    kind_raw = body.get("kind")
    if isinstance(kind_raw, str) and kind_raw == "variable":
        return policy_rejection(
            "refinement_edit_kind",
            "there is no variable edit kind; an agent, hook, Role or Mission may "
            "never set a registered variable through a RefinementProposal "
            "(FR-Q36; AD-26)",
            kind=kind_raw,
        )
    try:
        kind = parse_closed(RefinementEditKind, kind_raw)
    except VocabularyError as exc:
        return policy_rejection(
            "refinement_edit_kind",
            "edit kind must be one of the nine closed AD-22 kinds; variable is "
            "not among them (FR-Q26, FR-Q36; AD-22, AD-26)",
            kind=repr(kind_raw),
            detail=str(exc),
        )
    operation = body.get("operation")
    if operation not in {"create", "update", "delete"}:
        return invalid_input(
            "operation",
            "edit operation is create | update | delete",
            given=repr(operation),
        )
    target_id = body.get("id")
    if not isinstance(target_id, str) or target_id.strip() == "":
        return invalid_input(
            "id",
            "each edit names a non-empty target definition id",
            given=repr(target_id),
        )
    path = body.get("path")
    if kind is RefinementEditKind.ROLE and path == "role.base":
        return policy_rejection(
            "role_base",
            "role.base is written only by an operator-principal role.set_base; "
            "the proposal pipeline accepts only role.overlay (FR-Q26; AD-22)",
        )
    content = body.get("content", {})
    if not isinstance(content, Mapping):
        return invalid_input(
            "content",
            "edit content is a mapping",
            given=repr(type(content).__name__),
        )
    reference = body.get("reference")
    if reference is not None and not isinstance(reference, str):
        return invalid_input(
            "reference",
            "edit reference is a string when present",
            given=repr(reference),
        )
    path_s = path if isinstance(path, str) else None
    content_map = cast("Mapping[str, object]", content)
    return Ok(
        ProposalEdit(
            kind=kind,
            operation=cast("EditOperation", operation),
            target_id=target_id,
            content=MappingProxyType(dict(content_map)),
            reference=reference if isinstance(reference, str) else None,
            path=path_s,
        )
    )


def accept_definition_store_proposal(
    *,
    summary: object,
    rationale: object,
    edits: Sequence[object],
    expected_outcome: object,
    proposal_id: str | None = None,
) -> Result[RefinementProposal]:
    """Accept an Agent definition-store change only as a RefinementProposal.

    Any other entry shape — including a bare promote act — is refused.
    """
    if not isinstance(summary, str) or summary.strip() == "":
        return invalid_input("summary", "proposal summary is a non-empty string")
    if not isinstance(rationale, str) or rationale.strip() == "":
        return invalid_input("rationale", "proposal rationale is a non-empty string")
    if not isinstance(expected_outcome, str) or expected_outcome.strip() == "":
        return invalid_input(
            "expected_outcome",
            "proposal expected_outcome is a non-empty string",
        )
    if not edits:
        return invalid_input(
            "edits",
            "a RefinementProposal carries one or more edits (FR-Q26; AD-22)",
        )
    parsed: list[ProposalEdit] = []
    for raw in edits:
        edit = _parse_edit(raw)
        if is_refusal(edit):
            return edit
        parsed.append(edit.value)
    return Ok(
        RefinementProposal(
            id=proposal_id if proposal_id else str(uuid4()),
            summary=summary,
            rationale=rationale,
            edits=tuple(parsed),
            expected_outcome=expected_outcome,
            state=ProposalState.STAGED,
        )
    )


def apply_refinement_proposal(
    proposal: RefinementProposal,
    *,
    principal_class: object,
) -> Result[RefinementProposal]:
    """Apply a staged proposal through the governed path — never promote.

    v1 application requires an ``operator`` principal (AD-24 at
    ``before_proposal_apply``).
    """
    if proposal.state is not ProposalState.STAGED:
        return policy_rejection(
            "proposal_apply",
            "only a staged RefinementProposal may be applied (FR-Q26; AD-22)",
            state=proposal.state.value,
        )
    try:
        validate_governed_act(GovernedAct.APPLY, GovernedActTarget.REFINEMENT_PROPOSAL)
    except VocabularyError as exc:
        return policy_rejection("governed_act", str(exc))

    authorized = authorize_wire_command("admission.approve", principal_class)
    if is_refusal(authorized):
        return authorized
    if authorized.value.principal_class is not PrincipalClass.OPERATOR:
        return OperatorPrincipalRequired.of(
            command="before_proposal_apply",
            principal_class=str(principal_class),
        )

    snapshots = {
        edit.target_id: {
            "kind": edit.kind.value,
            "operation": edit.operation,
            "before": None,
            "after": dict(edit.content),
        }
        for edit in proposal.edits
    }
    return Ok(
        RefinementProposal(
            id=proposal.id,
            summary=proposal.summary,
            rationale=proposal.rationale,
            edits=proposal.edits,
            expected_outcome=proposal.expected_outcome,
            state=ProposalState.APPLIED,
            applied_snapshots=MappingProxyType(snapshots),
        )
    )


def register_mission_scoped_hook_exception(
    *,
    mission_id: object,
    template_id: object,
    observe_or_deny_only: bool,
    via_hook: object = AGENT_DIRECT_DEFINITION_EXCEPTION,
) -> Result[Mapping[str, object]]:
    """Sole direct Agent definition-store exception (FR-Q26; AD-8, AD-11).

    A Mission-scoped, template-validated observe-or-deny hook registered through
    ``before_hook_register``, disposed with its Mission, never becoming durable
    except through AD-22.
    """
    if via_hook != AGENT_DIRECT_DEFINITION_EXCEPTION:
        return policy_rejection(
            "definition_store_exception",
            "the sole direct Agent exception is registration through "
            f"{AGENT_DIRECT_DEFINITION_EXCEPTION} (FR-Q26; AD-8, AD-11)",
            via_hook=repr(via_hook),
        )
    if not isinstance(mission_id, str) or mission_id.strip() == "":
        return invalid_input(
            "mission_id",
            "mission-scoped hook registration names a Mission id",
            given=repr(mission_id),
        )
    if not isinstance(template_id, str) or template_id.strip() == "":
        return invalid_input(
            "template_id",
            "agent-authored hooks require an approved template id",
            given=repr(template_id),
        )
    if not observe_or_deny_only:
        return policy_rejection(
            "mission_hook",
            "an Agent-authored Mission hook is observe-or-deny only; "
            "updated_input/output, injected_context, ledger_entry and "
            "verifier_ref are refused (FR-Q26; AD-11)",
        )
    return Ok(
        MappingProxyType(
            {
                "exception": AGENT_DIRECT_DEFINITION_EXCEPTION,
                "mission_id": mission_id,
                "template_id": template_id,
                "observe_or_deny_only": True,
                "disposed_with": "mission",
                "durable_only_via": "refinement_proposal",
            }
        )
    )


@dataclass
class ProposalGate:
    """In-memory staging gate for RefinementProposal accept / apply."""

    _staged: dict[str, RefinementProposal] = field(
        default_factory=dict[str, RefinementProposal]
    )

    def accept(
        self,
        *,
        summary: object,
        rationale: object,
        edits: Sequence[object],
        expected_outcome: object,
        proposal_id: str | None = None,
    ) -> Result[RefinementProposal]:
        """Stage a definition-store change as a RefinementProposal."""
        accepted = accept_definition_store_proposal(
            summary=summary,
            rationale=rationale,
            edits=edits,
            expected_outcome=expected_outcome,
            proposal_id=proposal_id,
        )
        if is_refusal(accepted):
            return accepted
        self._staged[accepted.value.id] = accepted.value
        return accepted

    def apply(
        self,
        proposal_id: object,
        *,
        principal_class: object,
    ) -> Result[RefinementProposal]:
        """Apply a staged proposal; refuse promote and non-operator principals."""
        if not isinstance(proposal_id, str) or proposal_id not in self._staged:
            return policy_rejection(
                "proposal_apply",
                "apply names a staged RefinementProposal id (FR-Q26; AD-22)",
                proposal_id=repr(proposal_id),
            )
        applied = apply_refinement_proposal(
            self._staged[proposal_id],
            principal_class=principal_class,
        )
        if is_refusal(applied):
            return applied
        self._staged[proposal_id] = applied.value
        return applied

    def promote_refused(self, proposal_id: object) -> Result[None]:
        """Explicitly refuse any promote attempt on a refinement proposal."""
        return policy_rejection(
            "governed_act",
            "a RefinementProposal is applied through the staging path and is "
            "never promoted; promote is reserved for a human live-zone act "
            "outside QMA (FR-Q26; AD-22, DEC-0345)",
            proposal_id=repr(proposal_id),
            act=GovernedAct.PROMOTE.value,
        )
