"""Story 47.1 — MemoryProvider binding and deterministic admission (FR-Q64)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest
from qma.core.ports.memory import (
    GAP_0072_EXTERNAL_MEMORY_BACKEND,
    MEMORY_PROVIDER_OPERATIONS,
    MemoryCandidate,
    compute_admission_confidence,
)
from qma.core.refusals import NoMemoryProvider
from qma.core.vocabulary import GovernedAct, GovernedActTarget, validate_governed_act
from qma.core.vocabulary.enums import MemoryValidationState, RefinementEditKind
from qma.core.vocabulary.registry import VocabularyError
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.memory import MemoryAdmissionGate, MemoryProviderRegistry
from qma.daemon.plugins import DaemonPluginContext
from qmf.core import Ok, Result, is_ok, is_refusal


@dataclass
class _InMemoryProvider:
    """Test double — not a shipped QMA memory engine (GAP-0072 stays Deferred)."""

    store: dict[str, MemoryCandidate] = field(default_factory=dict[str, MemoryCandidate])

    def propose(self, candidate: MemoryCandidate) -> Result[MemoryCandidate]:
        return Ok(candidate)

    def admit(self, candidate: MemoryCandidate) -> Result[MemoryCandidate]:
        self.store[candidate.id] = candidate
        return Ok(candidate)

    def recall(self, scope: str, token_budget: int) -> Result[tuple[MemoryCandidate, ...]]:
        hits = tuple(c for c in self.store.values() if c.scope == scope)
        if token_budget == 0:
            return Ok(())
        # Token budget: each candidate costs 1 token in this stub.
        return Ok(hits[:token_budget])

    def get(self, memory_id: str) -> Result[MemoryCandidate]:
        return Ok(self.store[memory_id])

    def list(self, scope: str) -> Result[tuple[MemoryCandidate, ...]]:
        return Ok(tuple(c for c in self.store.values() if c.scope == scope))

    def history(self, memory_id: str) -> Result[tuple[MemoryCandidate, ...]]:
        current = self.store.get(memory_id)
        return Ok((current,) if current is not None else ())

    def supersede(self, memory_id: str, successor: MemoryCandidate) -> Result[MemoryCandidate]:
        if memory_id in self.store:
            old = self.store[memory_id]
            self.store[memory_id] = MemoryCandidate(
                id=old.id,
                provenance=old.provenance,
                supporting_artifacts=old.supporting_artifacts,
                scope=old.scope,
                proposer=old.proposer,
                occurrence_time=old.occurrence_time,
                validation_state=MemoryValidationState.SUPERSEDED,
                content=old.content,
                admission_confidence=old.admission_confidence,
                supersession=successor.id,
                corroboration_count=old.corroboration_count,
                validation_history=old.validation_history,
            )
        self.store[successor.id] = successor
        return Ok(successor)

    def invalidate(self, memory_id: str) -> Result[MemoryCandidate]:
        current = self.store[memory_id]
        updated = MemoryCandidate(
            id=current.id,
            provenance=current.provenance,
            supporting_artifacts=current.supporting_artifacts,
            scope=current.scope,
            proposer=current.proposer,
            occurrence_time=current.occurrence_time,
            validation_state=MemoryValidationState.INVALIDATED,
            content=current.content,
            admission_confidence=current.admission_confidence,
            supersession=current.supersession,
            corroboration_count=current.corroboration_count,
            validation_history=current.validation_history,
        )
        self.store[memory_id] = updated
        return Ok(updated)

    def expire(self, memory_id: str) -> Result[MemoryCandidate]:
        current = self.store[memory_id]
        updated = MemoryCandidate(
            id=current.id,
            provenance=current.provenance,
            supporting_artifacts=current.supporting_artifacts,
            scope=current.scope,
            proposer=current.proposer,
            occurrence_time=current.occurrence_time,
            validation_state=MemoryValidationState.EXPIRED,
            content=current.content,
            admission_confidence=current.admission_confidence,
            supersession=current.supersession,
            corroboration_count=current.corroboration_count,
            validation_history=current.validation_history,
        )
        self.store[memory_id] = updated
        return Ok(updated)

    def scopes(self) -> Result[tuple[str, ...]]:
        return Ok(tuple(sorted({c.scope for c in self.store.values()})))


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "mem-47-1",
        "provenance": {"source": "observation"},
        "supporting_artifacts": ["artifact://ev-1"],
        "scope": "research/mission-1",
        "proposer": "agent:research/quant/a1",
        "occurrence_time": 1_700_000_000_000_000_000,
        "content": {"statement": "range holds above 1.0800"},
    }
    body.update(overrides)
    return body


def test_exactly_one_provider_per_desk_and_no_default_engine() -> None:
    registry = MemoryProviderRegistry()
    assert registry.desks() == ()
    first = registry.bind("research", _InMemoryProvider(), plugin_id="research-corpus")
    assert is_ok(first)
    assert registry.is_bound("research")
    assert set(MEMORY_PROVIDER_OPERATIONS).issuperset({"propose", "admit", "recall", "scopes"})
    assert first.value.to_payload()["promote"] is False
    assert first.value.to_payload()["reflect"] is False
    assert first.value.to_payload()["provider_storage_is_qma_evidence"] is False

    duplicate = registry.bind("research", _InMemoryProvider(), plugin_id="other-plugin")
    assert is_refusal(duplicate)
    assert "exactly one" in str(duplicate.context.get("reason", ""))


def test_plugin_context_registers_desk_scoped_provider() -> None:
    ctx = DaemonPluginContext("research-corpus")
    dispose = ctx.register_memory_provider("research", _InMemoryProvider())
    snap = ctx.snapshot()
    assert ("MemoryProvider", "research") in snap["singletons"]
    dispose()
    assert ("MemoryProvider", "research") not in ctx.snapshot()["singletons"]


def test_unbound_recall_returns_no_memory_provider() -> None:
    gate = MemoryAdmissionGate()
    refused = gate.recall("research", scope="research/mission-1", token_budget=128)
    assert is_refusal(refused)
    assert NoMemoryProvider.matches(refused)


def test_unbound_propose_stages_one_memory_edit() -> None:
    gate = MemoryAdmissionGate()
    outcome = gate.propose("research", _payload())
    assert is_ok(outcome)
    assert outcome.value.path == "unbound_staging"
    assert outcome.value.proposal is not None
    assert len(outcome.value.proposal.edits) == 1
    assert outcome.value.proposal.edits[0].kind is RefinementEditKind.MEMORY
    assert outcome.value.candidate is not None
    assert outcome.value.candidate.admission_confidence is None


def test_propose_refuses_proposer_supplied_admission_confidence() -> None:
    gate = MemoryAdmissionGate()
    refused = gate.propose("research", _payload(admission_confidence=0.99))
    assert is_refusal(refused)
    assert refused.context["field"] == "admission_confidence"


def test_bound_admit_computes_confidence_through_before_memory_write() -> None:
    provider = _InMemoryProvider()
    hooks = HookRegistry()
    gate = MemoryAdmissionGate(hooks=hooks)
    assert is_ok(gate.bind("research", provider, plugin_id="research-corpus"))

    outcome = gate.propose("research", _payload())
    assert is_ok(outcome)
    assert outcome.value.path == "bound_gate"
    admitted = outcome.value.candidate
    assert admitted is not None
    assert admitted.validation_state is MemoryValidationState.ADMITTED
    assert admitted.admission_confidence is not None
    # Gate stamps after computing from pre-admit inputs; recompute from payload inputs.
    expected_from_input = compute_admission_confidence(
        provenance={"source": "observation"},
        supporting_artifacts=("artifact://ev-1",),
        corroboration_count=1,
        validation_history=("proposed",),
    )
    assert admitted.admission_confidence == expected_from_input
    assert admitted.id in provider.store

    recalled = gate.recall("research", scope="research/mission-1", token_budget=8)
    assert is_ok(recalled)
    assert len(recalled.value) == 1
    assert recalled.value[0].admission_confidence == admitted.admission_confidence

    # Bound path never creates a staging proposal.
    assert outcome.value.proposal is None


def test_admit_verb_never_promote() -> None:
    gate = MemoryAdmissionGate()
    provider = _InMemoryProvider()
    assert is_ok(gate.bind("research", provider))
    validate_governed_act(GovernedAct.ADMIT, GovernedActTarget.MEMORY_CANDIDATE)
    with pytest.raises(VocabularyError):
        validate_governed_act(GovernedAct.PROMOTE, GovernedActTarget.MEMORY_CANDIDATE)
    refused = gate.promote_refused("research", "mem-47-1")
    assert is_refusal(refused)
    assert refused.context["act"] == "promote"

    admitted = gate.admit("research", _payload(id="mem-admit"))
    assert is_ok(admitted)
    assert admitted.value.path == "bound_gate"
    assert admitted.value.candidate is not None
    assert admitted.value.candidate.validation_state is MemoryValidationState.ADMITTED


def test_gap_0072_excluded_and_provider_storage_not_qma_evidence() -> None:
    gate = MemoryAdmissionGate()
    deferred = gate.refuse_external_backend(requested="hindsight")
    assert is_refusal(deferred)
    assert deferred.context["gap"] == GAP_0072_EXTERNAL_MEMORY_BACKEND
    assert gate.provider_storage_is_qma_evidence() is False
    binding_payload: Mapping[str, object] = {
        "no_database_server_scope": "qma_owned_stores_only",
        "provider_storage_is_qma_evidence": False,
    }
    assert binding_payload["provider_storage_is_qma_evidence"] is False
