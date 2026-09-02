"""Per-desk MemoryProvider binding and deterministic admission (CT-43; FR-Q64).

QMA supplies no memory engine. Exactly one provider may bind a desk. Until a
provider is bound, ``recall`` returns ``NoMemoryProvider`` and ``propose`` stages
one RefinementProposal with exactly one ``memory`` edit. Once bound, admission
runs only through ``before_memory_write`` — never the staging path — and never
requires an operator principal. ``admission_confidence`` is gate-computed.
Provider-internal storage is not QMA evidence. GAP-0072 stays Deferred.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal

from qma.core.plugins.hooks import HookResult, HookSource, build_hook_result
from qma.core.ports.memory import (
    GAP_0072_EXTERNAL_MEMORY_BACKEND,
    MEMORY_PROVIDER_OPERATIONS,
    NO_PROMOTE_OPERATION,
    MemoryCandidate,
    MemoryProvider,
    compute_admission_confidence,
    parse_memory_candidate,
    refuse_external_memory_backend,
    refuse_memory_promote,
    stage_unbound_memory_edit,
)
from qma.core.refusals import NoMemoryProvider
from qma.core.vocabulary import (
    GovernedAct,
    GovernedActTarget,
    MemoryValidationState,
    VocabularyError,
    validate_governed_act,
)
from qma.core.vocabulary.enums import HookResultDecision, HookVerb
from qma.daemon.hooks.registry import HookRegistry, event_names_for_verb
from qma.daemon.staging.proposal import ProposalGate, RefinementProposal
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "GAP_0072_EXTERNAL_MEMORY_BACKEND",
    "MEMORY_PROVIDER_OPERATIONS",
    "NO_DATABASE_SERVER_SCOPE",
    "NO_PROMOTE_OPERATION",
    "AdmittingOutcome",
    "MemoryAdmissionGate",
    "MemoryProviderRegistry",
    "ProviderBinding",
    "RecallOutcome",
]


# Inherited no-database-server rule binds QMA's own stores only — never a
# provider's internal storage behind this port (DEC-0342, DEC-0317).
NO_DATABASE_SERVER_SCOPE: Final[str] = "qma_owned_stores_only"

_BLOCKING_BEFORE: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.BLOCK_STOP,
    }
)

RecallOutcome = MemoryCandidate | tuple[MemoryCandidate, ...]
AdmittingPath = Literal["bound_gate", "unbound_staging"]


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    """One desk → MemoryProvider binding (singleton cardinality)."""

    desk: str
    provider: MemoryProvider
    plugin_id: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "desk": self.desk,
                "plugin_id": self.plugin_id,
                "operations": sorted(MEMORY_PROVIDER_OPERATIONS),
                "promote": False,
                "reflect": False,
                "external_backend": False,
                "gap_0072": GAP_0072_EXTERNAL_MEMORY_BACKEND,
                "provider_storage_is_qma_evidence": False,
                "no_database_server_scope": NO_DATABASE_SERVER_SCOPE,
            }
        )


@dataclass(frozen=True, slots=True)
class AdmittingOutcome:
    """Result of propose / admit through the desk-scoped gate."""

    path: AdmittingPath
    candidate: MemoryCandidate | None = None
    proposal: RefinementProposal | None = None
    hook: HookResult | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {"path": self.path}
        if self.candidate is not None:
            payload["candidate"] = dict(
                self.candidate.to_payload(include_admission_confidence=True)
            )
        if self.proposal is not None:
            payload["proposal"] = dict(self.proposal.to_payload())
        if self.hook is not None:
            payload["hook_decision"] = self.hook.decision.value
        return MappingProxyType(payload)


class MemoryProviderRegistry:
    """In-memory singleton-per-desk registry for the MemoryProvider port.

    Empty by default — QMA ships no memory engine and no default binding
    (DEC-0342). A second binding for the same desk is a hard error.
    """

    def __init__(self) -> None:
        self._by_desk: dict[str, ProviderBinding] = {}

    def bind(
        self,
        desk: str,
        provider: MemoryProvider,
        *,
        plugin_id: str | None = None,
    ) -> Result[ProviderBinding]:
        """Bind exactly one MemoryProvider for ``desk``."""
        if not isinstance(desk, str) or desk.strip() == "":
            return invalid_input(
                "desk",
                "MemoryProvider is scoped per desk; desk is a non-empty string (CT-43; AD-1)",
                given=repr(desk),
            )
        key = desk.strip()
        if key in self._by_desk:
            existing = self._by_desk[key]
            return policy_rejection(
                "MemoryProvider",
                "exactly one MemoryProvider may bind a desk; a second binding "
                "is a hard error naming both plugin ids (CT-43; AD-1; FR-Q64)",
                desk=key,
                existing_plugin_id=existing.plugin_id,
                incoming_plugin_id=plugin_id,
            )
        binding = ProviderBinding(desk=key, provider=provider, plugin_id=plugin_id)
        self._by_desk[key] = binding
        return Ok(binding)

    def unbind(self, desk: str) -> None:
        self._by_desk.pop(desk.strip() if isinstance(desk, str) else desk, None)

    def get(self, desk: str) -> ProviderBinding | None:
        if not isinstance(desk, str):
            return None
        return self._by_desk.get(desk.strip())

    def is_bound(self, desk: str) -> bool:
        return self.get(desk) is not None

    def desks(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_desk))

    def refuse_external_backend(self, **extra: object) -> Result[None]:
        """Explicit Deferred GAP-0072 exclusion (FR-Q64)."""
        return refuse_external_memory_backend(**extra)

    def refuse_promote(self, **extra: object) -> Result[None]:
        """Memory has no promote operation (DEC-0345)."""
        return refuse_memory_promote(**extra)


@dataclass
class MemoryAdmissionGate:
    """Daemon admission gate over the per-desk MemoryProvider binding.

    Unbound path: ``recall`` → ``NoMemoryProvider``; ``propose`` → one staged
    RefinementProposal with exactly one ``memory`` edit.

    Bound path: ``propose`` / ``admit`` pass only through ``before_memory_write``;
    ``admission_confidence`` is computed here and never accepted from input.
    """

    registry: MemoryProviderRegistry = field(default_factory=MemoryProviderRegistry)
    staging: ProposalGate = field(default_factory=ProposalGate)
    hooks: HookRegistry | None = None

    def bind(
        self,
        desk: str,
        provider: MemoryProvider,
        *,
        plugin_id: str | None = None,
    ) -> Result[ProviderBinding]:
        return self.registry.bind(desk, provider, plugin_id=plugin_id)

    def recall(
        self,
        desk: object,
        *,
        scope: object,
        token_budget: object,
    ) -> Result[tuple[MemoryCandidate, ...]]:
        """Token-budgeted recall; unbound desks return ``NoMemoryProvider``."""
        if not isinstance(desk, str) or desk.strip() == "":
            return invalid_input(
                "desk",
                "recall names a desk (CT-43; FR-Q64)",
                given=repr(desk),
            )
        if not isinstance(scope, str) or scope.strip() == "":
            return invalid_input(
                "scope",
                "recall requires a non-empty scope (CT-43; FR-Q64)",
                given=repr(scope),
            )
        if isinstance(token_budget, bool) or not isinstance(token_budget, int) or token_budget < 0:
            return invalid_input(
                "token_budget",
                "recall is token-budgeted, not result-count-bounded (CT-43; FR-Q64; DEC-0317)",
                given=repr(token_budget),
            )
        binding = self.registry.get(desk)
        if binding is None:
            return NoMemoryProvider.of(desk=desk.strip())
        return binding.provider.recall(scope.strip(), token_budget)

    def propose(
        self,
        desk: object,
        candidate: object,
        *,
        summary: str | None = None,
        rationale: str | None = None,
        expected_outcome: str | None = None,
    ) -> Result[AdmittingOutcome]:
        """Propose a MemoryCandidate for the desk.

        Refuses proposer-supplied ``admission_confidence``. Unbound desks stage
        exactly one ``memory`` RefinementProposal edit. Bound desks route through
        ``before_memory_write`` only — never staging, never operator approval.
        """
        if not isinstance(desk, str) or desk.strip() == "":
            return invalid_input(
                "desk",
                "propose names a desk (CT-43; FR-Q64)",
                given=repr(desk),
            )
        parsed = parse_memory_candidate(candidate, for_propose=True)
        if is_refusal(parsed):
            return parsed
        body = parsed.value
        desk_key = desk.strip()
        binding = self.registry.get(desk_key)
        if binding is None:
            return self._stage_unbound(
                body, summary=summary, rationale=rationale, expected_outcome=expected_outcome
            )
        return self._admit_bound(binding, body, via="propose")

    def admit(
        self,
        desk: object,
        candidate: object,
    ) -> Result[AdmittingOutcome]:
        """Admit through the deterministic gate once a provider is bound.

        Verb is ``admit`` (GovernedAct.ADMIT), never ``promote``.
        """
        if not isinstance(desk, str) or desk.strip() == "":
            return invalid_input(
                "desk",
                "admit names a desk (CT-43; FR-Q64)",
                given=repr(desk),
            )
        try:
            validate_governed_act(GovernedAct.ADMIT, GovernedActTarget.MEMORY_CANDIDATE)
        except VocabularyError as exc:
            return policy_rejection("governed_act", str(exc))

        parsed = parse_memory_candidate(candidate, for_propose=True)
        if is_refusal(parsed):
            return parsed
        binding = self.registry.get(desk.strip())
        if binding is None:
            return NoMemoryProvider.of(desk=desk.strip())
        return self._admit_bound(binding, parsed.value, via="admit")

    def promote_refused(self, desk: object, memory_id: object = None) -> Result[None]:
        """Explicitly refuse any promote attempt on a memory candidate."""
        _ = desk, memory_id
        return refuse_memory_promote(desk=repr(desk), memory_id=repr(memory_id))

    def refuse_external_backend(self, **extra: object) -> Result[None]:
        return self.registry.refuse_external_backend(**extra)

    def provider_storage_is_qma_evidence(self) -> bool:
        """Provider-internal storage never holds or is read as QMA evidence."""
        return False

    def _stage_unbound(
        self,
        candidate: MemoryCandidate,
        *,
        summary: str | None,
        rationale: str | None,
        expected_outcome: str | None,
    ) -> Result[AdmittingOutcome]:
        edit = stage_unbound_memory_edit(candidate)
        accepted = self.staging.accept(
            summary=summary or f"stage memory candidate {candidate.id}",
            rationale=rationale
            or "no MemoryProvider bound; candidate stages as one memory edit (CT-43; FR-Q64)",
            edits=[dict(edit)],
            expected_outcome=expected_outcome
            or "candidate held in staging until a provider is bound",
            proposal_id=f"memory-stage-{candidate.id}",
        )
        if is_refusal(accepted):
            return accepted
        proposal = accepted.value
        if len(proposal.edits) != 1 or proposal.edits[0].kind.value != "memory":
            return policy_rejection(
                "edits",
                "unbound memory propose wraps exactly one memory edit (CT-43; FR-Q64)",
                edit_count=len(proposal.edits),
            )
        return Ok(
            AdmittingOutcome(
                path="unbound_staging",
                candidate=candidate,
                proposal=proposal,
            )
        )

    def _admit_bound(
        self,
        binding: ProviderBinding,
        candidate: MemoryCandidate,
        *,
        via: Literal["propose", "admit"],
    ) -> Result[AdmittingOutcome]:
        confidence = compute_admission_confidence(
            provenance=candidate.provenance,
            supporting_artifacts=candidate.supporting_artifacts,
            corroboration_count=candidate.corroboration_count
            if candidate.corroboration_count
            else len(candidate.supporting_artifacts),
            validation_history=candidate.validation_history or (candidate.validation_state.value,),
        )
        stamped = candidate.with_admission(
            confidence,
            state=MemoryValidationState.ADMITTED,
        )
        hook = self._before_memory_write(stamped, desk=binding.desk, via=via)
        if is_refusal(hook):
            return hook
        gate = hook.value
        if gate.decision in _BLOCKING_BEFORE:
            before, _after = event_names_for_verb(HookVerb.MEMORY_WRITE)
            return policy_rejection(
                before,
                f"{before} resolved to {gate.decision.value}; memory not admitted "
                "(CT-43; AD-10; FR-Q64)",
                given=gate.reason or gate.decision.value,
            )

        if via == "propose":
            proposed = binding.provider.propose(stamped)
            if is_refusal(proposed):
                return proposed
            admitted = binding.provider.admit(proposed.value)
        else:
            admitted = binding.provider.admit(stamped)
        if is_refusal(admitted):
            return admitted

        self._after_memory_write(admitted.value, desk=binding.desk, via=via)
        return Ok(
            AdmittingOutcome(
                path="bound_gate",
                candidate=admitted.value,
                hook=gate,
            )
        )

    def _before_memory_write(
        self,
        candidate: MemoryCandidate,
        *,
        desk: str,
        via: str,
    ) -> Result[HookResult]:
        if self.hooks is None:
            return Ok(build_hook_result(HookResultDecision.ALLOW, reason="no_hook_registry"))
        before, _after = event_names_for_verb(HookVerb.MEMORY_WRITE)
        payload = dict(candidate.to_payload())
        payload["desk"] = desk
        payload["via"] = via
        payload["operator_required"] = False
        result = self.hooks.dispatch(
            before,
            payload=payload,
            source=HookSource.MISSION,
        )
        if is_refusal(result):
            return result
        return Ok(result.value)

    def _after_memory_write(
        self,
        candidate: MemoryCandidate,
        *,
        desk: str,
        via: str,
    ) -> None:
        if self.hooks is None:
            return
        _before, after = event_names_for_verb(HookVerb.MEMORY_WRITE)
        payload = dict(candidate.to_payload())
        payload["desk"] = desk
        payload["via"] = via
        _ = self.hooks.dispatch(after, payload=payload, source=HookSource.MISSION)
