"""L1 — the both-layers registration gate decision (E12-L1-03, P0).

The single gate decision: a Bot mints only when BOTH layer verdicts pass; any
failing combination is ``policy rejection`` and there is NO partial/probationary
outcome. Verdicts are INJECTED (a real pass verdict, or a crafted typed refusal
standing in for a failed layer) so only the gate logic is under test.

R-009 / P0-Q1 / FR-048 / QL-8 / AR-64 / DEC-0178 / FM-4.
"""

from __future__ import annotations

import _world as w
from qmf.core.refusal import (
    RefusalCategory,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qml.conformance import evaluate_ticket, gate_registration, lint_declaration, run_layer2_suite


def _verdicts() -> tuple[object, object]:
    world = w.build_world()
    d = world["declaration"]
    l1 = lint_declaration(
        d,
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["catalog_producers"],
        logic_catalog=[world["logic"]],
    )
    l2 = run_layer2_suite(
        declaration=d,
        factory=world["factory"],
        source_tree=world["source"],
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(l1) and is_ok(l2), "fixture must produce two real passing verdicts"
    return l1.value, l2.value


def _failed_layer() -> TypedRefusal:
    """A typed refusal standing in for a failed conformance layer (injected)."""
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context={"field": "conformance", "reason": "injected failed layer"},
    )


def test_e12_l1_03_evaluate_ticket_truth_table() -> None:
    """Pure gate: only (pass, pass) mints a ticket; every other combo is policy rejection."""
    ok = evaluate_ticket(layer1_passed=True, layer2_passed=True)
    assert is_ok(ok) and ok.value.layer1_passed and ok.value.layer2_passed
    for a, b in ((True, False), (False, True), (False, False)):
        verdict = evaluate_ticket(layer1_passed=a, layer2_passed=b)
        assert is_refusal(verdict), f"({a},{b}) must not mint a ticket"
        assert verdict.category is RefusalCategory.POLICY_REJECTION


def test_e12_l1_03_gate_pass_pass_mints_candidate() -> None:
    """Both real verdicts pass -> a RegistrationCandidate ticket (both layers marked passed)."""
    l1v, l2v = _verdicts()
    candidate = gate_registration(layer1=l1v, layer2=l2v)
    assert is_ok(candidate)
    assert candidate.value.ticket.layer1_passed is True
    assert candidate.value.ticket.layer2_passed is True


def test_e12_l1_03_gate_any_failed_layer_is_policy_rejection() -> None:
    """pass/fail, fail/pass, fail/fail each refuse policy rejection — no partial state."""
    l1v, l2v = _verdicts()
    fail = _failed_layer()
    combos = {
        "pass/fail": (l1v, fail),
        "fail/pass": (fail, l2v),
        "fail/fail": (fail, fail),
    }
    for label, (layer1, layer2) in combos.items():
        result = gate_registration(layer1=layer1, layer2=layer2)
        assert is_refusal(result), f"{label} must be refused"
        assert result.category is RefusalCategory.POLICY_REJECTION, label
        # The refusal carries no "candidate"/"ticket" — there is no partial mint.
        assert "layer1_passed" not in result.context


def test_e12_l1_03_no_probationary_registration() -> None:
    """A probation/partial flag is refused policy rejection even with two passing verdicts."""
    l1v, l2v = _verdicts()
    for flag in ("probation", "partial", "probationary"):
        result = gate_registration(**{"layer1": l1v, "layer2": l2v, flag: True})
        assert is_refusal(result), f"{flag}=True must be refused"
        assert result.category is RefusalCategory.POLICY_REJECTION, flag
    # Falsifiable control: without the flag the same verdicts mint.
    assert is_ok(gate_registration(layer1=l1v, layer2=l2v))
