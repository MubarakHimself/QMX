"""AD-22 definition-store change boundary (FR-Q26 / FR-Q66; DEC-0321, DEC-0345).

An Agent may enter a definition-store change only as a RefinementProposal. A
proposal is later **applied** through the governed staging path and is never
**promoted**. The sole direct Agent exception is a Mission-scoped,
template-validated observe-or-deny hook registered through ``before_hook_register``
and disposed with its Mission.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.ports.refinement import (
    CLOSED_EDIT_KINDS,
    EditOperation,
    ProposalEdit,
    ProposalState,
    RefinementProposal,
    accept_refinement_proposal,
    definition_reference,
    parse_proposal_edit,
)
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary import (
    GovernedAct,
    GovernedActTarget,
    PrincipalClass,
    VocabularyError,
    validate_governed_act,
)
from qma.wire.principals import authorize_wire_command
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "AGENT_DIRECT_DEFINITION_EXCEPTION",
    "CLOSED_EDIT_KINDS",
    "EditOperation",
    "ProposalEdit",
    "ProposalGate",
    "ProposalState",
    "RefinementProposal",
    "accept_definition_store_proposal",
    "apply_refinement_proposal",
    "parse_proposal_edit",
    "register_mission_scoped_hook_exception",
]


AGENT_DIRECT_DEFINITION_EXCEPTION: Final[str] = "before_hook_register"


def accept_definition_store_proposal(
    *,
    summary: object,
    rationale: object,
    edits: Sequence[object],
    expected_outcome: object,
    proposal_id: str | None = None,
    author_family: str | None = None,
) -> Result[RefinementProposal]:
    """Accept an Agent definition-store change only as a RefinementProposal.

    Any other entry shape — including a bare promote act — is refused.
    """
    return accept_refinement_proposal(
        summary=summary,
        rationale=rationale,
        edits=edits,
        expected_outcome=expected_outcome,
        proposal_id=proposal_id,
        author_family=author_family,
    )


def apply_refinement_proposal(
    proposal: RefinementProposal,
    *,
    principal_class: object,
    before_snapshots: Mapping[str, Mapping[str, object]] | None = None,
) -> Result[RefinementProposal]:
    """Apply a staged proposal through the governed path — never promote.

    v1 application requires an ``operator`` principal (AD-24 at
    ``before_proposal_apply``).
    """
    if proposal.state is not ProposalState.STAGED:
        return policy_rejection(
            "proposal_apply",
            "only a staged RefinementProposal may be applied (FR-Q66; AD-22)",
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

    prior = before_snapshots or {}
    snapshots = {
        edit.target_id: {
            "kind": edit.kind.value,
            "operation": edit.operation,
            "before": dict(prior[edit.target_id]) if edit.target_id in prior else None,
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
            money_path_relevant=proposal.money_path_relevant,
            author_family=proposal.author_family,
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
    """In-memory staging gate for RefinementProposal accept / apply.

    The staging store accepts exactly one record type: ``RefinementProposal``.
    """

    _staged: dict[str, RefinementProposal] = field(default_factory=dict[str, RefinementProposal])
    _definitions: dict[str, Mapping[str, object]] = field(
        default_factory=dict[str, Mapping[str, object]]
    )
    _definition_refs: dict[str, str] = field(default_factory=dict[str, str])

    @property
    def record_type(self) -> str:
        return "refinement-proposal"

    def current_references(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self._definition_refs))

    def definition_bodies(self) -> Mapping[str, Mapping[str, object]]:
        return MappingProxyType({key: dict(value) for key, value in self._definitions.items()})

    def seed_definition(
        self,
        target_id: str,
        content: Mapping[str, object],
        *,
        reference: str,
    ) -> None:
        """Install a live definition base for OCC checks (tests / bootstrap)."""
        self._definitions[target_id] = MappingProxyType(dict(content))
        self._definition_refs[target_id] = reference

    def get(self, proposal_id: str) -> RefinementProposal | None:
        return self._staged.get(proposal_id)

    def accept(
        self,
        *,
        summary: object,
        rationale: object,
        edits: Sequence[object],
        expected_outcome: object,
        proposal_id: str | None = None,
        author_family: str | None = None,
    ) -> Result[RefinementProposal]:
        """Stage a definition-store change as a RefinementProposal."""
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
        self._staged[accepted.value.id] = accepted.value
        return accepted

    def store(self, proposal: RefinementProposal) -> Result[RefinementProposal]:
        """Persist a validated proposal; refuse non-staged shapes."""
        if proposal.state is not ProposalState.STAGED:
            return policy_rejection(
                "staging_store",
                "only a staged candidate may enter the staging store; a staged "
                "candidate is never live (CT-50; FR-Q66)",
                state=proposal.state.value,
            )
        self._staged[proposal.id] = proposal
        return Ok(proposal)

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
                "apply names a staged RefinementProposal id (FR-Q66; AD-22)",
                proposal_id=repr(proposal_id),
            )
        staged = self._staged[proposal_id]
        before = {
            edit.target_id: dict(self._definitions[edit.target_id])
            for edit in staged.edits
            if edit.target_id in self._definitions
        }
        applied = apply_refinement_proposal(
            staged,
            principal_class=principal_class,
            before_snapshots=before,
        )
        if is_refusal(applied):
            return applied
        return self.record_applied(applied.value)

    def record_applied(self, proposal: RefinementProposal) -> Result[RefinementProposal]:
        """Persist an already-authorized applied proposal and materialize edits."""
        if proposal.state is not ProposalState.APPLIED:
            return policy_rejection(
                "proposal_apply",
                "record_applied requires an applied RefinementProposal (FR-Q66)",
                state=proposal.state.value,
            )
        if proposal.applied_snapshots is None:
            return policy_rejection(
                "applied_snapshots",
                "applied_snapshots are mandatory once a proposal is applied (CT-50)",
            )
        self._staged[proposal.id] = proposal
        self._materialize_applied(proposal)
        return Ok(proposal)

    def _materialize_applied(self, proposal: RefinementProposal) -> None:
        for edit in proposal.edits:
            if edit.operation == "delete":
                self._definitions.pop(edit.target_id, None)
                self._definition_refs.pop(edit.target_id, None)
                continue
            self._definitions[edit.target_id] = MappingProxyType(dict(edit.content))
            addressed = definition_reference(edit.content)
            if not is_refusal(addressed):
                self._definition_refs[edit.target_id] = addressed.value

    def promote_refused(self, proposal_id: object) -> Result[None]:
        """Explicitly refuse any promote attempt on a refinement proposal."""
        return policy_rejection(
            "governed_act",
            "a RefinementProposal is applied through the staging path and is "
            "never promoted; promote is reserved for a human live-zone act "
            "outside QMA (FR-Q66; AD-22, DEC-0345)",
            proposal_id=repr(proposal_id),
            act=GovernedAct.PROMOTE.value,
        )
