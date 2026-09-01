"""Required deterministic verifier gates (FR-Q34; CT-41; AD-10, AD-15).

``before_task_complete`` and ``review_required`` run a deterministic verifier
(callable or subprocess) — never an LLM judging itself — then ReviewPolicy.
Returned ``ledger_entry`` / ``verifier_ref`` remain subject to the phase law.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qma.core.content import content_address
from qma.core.plugins.hooks import (
    HookImplementationKind,
    HookResult,
    assert_hook_result_phase_law,
    build_hook_result,
    parse_hook_implementation_kind,
)
from qma.core.ports.model import DeploymentRecord, ReviewPolicy, select_reviewer
from qma.core.vocabulary.enums import HookControl, HookResultDecision, ModelClass
from qma.core.vocabulary.hooks import parse_hook_event_name
from qma.core.vocabulary.registry import VocabularyError
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "REQUIRED_VERIFIER_GATE_EVENTS",
    "CompletionGateOutcome",
    "DeterministicVerifier",
    "apply_worker_daemon_decision",
    "evaluate_required_verifier_gate",
    "is_required_verifier_gate",
    "run_deterministic_verifier",
]


REQUIRED_VERIFIER_GATE_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "before_task_complete",
        HookControl.REVIEW_REQUIRED.value,
    }
)

VerifierFn = Callable[[Mapping[str, object]], Mapping[str, object]]


@dataclass(frozen=True, slots=True)
class DeterministicVerifier:
    """Deterministic completion/review verifier — callable or subprocess only."""

    kind: HookImplementationKind | str
    run: VerifierFn | None = None
    command: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        kind = parse_hook_implementation_kind(self.kind)
        object.__setattr__(self, "kind", kind)
        if kind is HookImplementationKind.CALLABLE and self.run is None:
            msg = "callable verifier requires run= (FR-Q34; AD-10)"
            raise VocabularyError(msg)
        if kind is HookImplementationKind.SUBPROCESS and not self.command:
            msg = "subprocess verifier requires command= (FR-Q34; AD-10)"
            raise VocabularyError(msg)


@dataclass(frozen=True, slots=True)
class CompletionGateOutcome:
    """Result of a required verifier gate including ReviewPolicy selection."""

    event: str
    result: HookResult
    verifier_ref: str
    reviewer: DeploymentRecord | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "event": self.event,
            "decision": self.result.decision.value,
            "reason": self.result.reason,
            "verifier_ref": self.verifier_ref,
        }
        if self.result.ledger_entry is not None:
            payload["ledger_entry"] = dict(self.result.ledger_entry)
        if self.reviewer is not None:
            payload["reviewer_deployment_id"] = self.reviewer.deployment_id
            payload["reviewer_family"] = self.reviewer.model_family
        return MappingProxyType(payload)


def is_required_verifier_gate(event: str) -> bool:
    """True for ``before_task_complete`` and ``review_required``."""
    try:
        name = parse_hook_event_name(event)
    except VocabularyError:
        return False
    return name in REQUIRED_VERIFIER_GATE_EVENTS


def run_deterministic_verifier(
    verifier: DeterministicVerifier,
    payload: Mapping[str, object],
) -> Result[Mapping[str, object]]:
    """Execute a callable or subprocess verifier — never a prompt/agent handler."""
    try:
        kind = parse_hook_implementation_kind(verifier.kind)
    except VocabularyError as exc:
        return policy_rejection("verifier", str(exc), given=repr(verifier.kind))
    if kind is HookImplementationKind.CALLABLE:
        run = verifier.run
        if run is None:
            return invalid_input(
                "verifier",
                "callable verifier requires run= (FR-Q34; AD-10)",
                given=repr(verifier.kind),
            )
        raw: Mapping[str, object] = run(dict(payload))
        return Ok(MappingProxyType(dict(raw)))
    command = verifier.command
    if command is None:
        return invalid_input(
            "verifier",
            "subprocess verifier requires command= (FR-Q34; AD-10)",
            given=repr(verifier.kind),
        )
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return policy_rejection(
            "verifier",
            f"subprocess verifier failed: {exc} (FR-Q34; AD-10)",
            given=list(command),
        )
    passed = completed.returncode == 0
    return Ok(
        MappingProxyType(
            {
                "passed": passed,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
    )


def apply_worker_daemon_decision(decision: HookResult) -> HookResult:
    """Worker-side interception may only apply the daemon-supplied decision.

    The worker never invents or widens a decision; it relays the daemon result.
    """
    return build_hook_result(
        decision.decision,
        reason=decision.reason,
        updated_input=decision.updated_input,
        updated_output=decision.updated_output,
        injected_context=decision.injected_context,
        ledger_entry=decision.ledger_entry,
        verifier_ref=decision.verifier_ref,
    )


def evaluate_required_verifier_gate(
    event: str,
    *,
    verifier: DeterministicVerifier,
    payload: Mapping[str, object] | None = None,
    author_family: str | None,
    catalog: Sequence[DeploymentRecord],
    model_class: ModelClass | str = ModelClass.WORKHORSE_GENERAL,
    ledger_entry: Mapping[str, object] | None = None,
    review_policy: ReviewPolicy | None = None,
) -> Result[CompletionGateOutcome]:
    """Run the required deterministic verifier then ReviewPolicy (FR-Q34).

    Phase-law fields ``ledger_entry`` and ``verifier_ref`` are validated before
    the outcome is returned. Empty catalog or no eligible reviewer yields
    ``NoEligibleReviewer``.
    """
    try:
        name = parse_hook_event_name(event)
    except VocabularyError as exc:
        return invalid_input("event", str(exc), given=repr(event))
    if name not in REQUIRED_VERIFIER_GATE_EVENTS:
        return policy_rejection(
            "event",
            "required verifier gate is only before_task_complete or "
            "review_required (FR-Q34; AD-10)",
            given=name,
        )
    verified = run_deterministic_verifier(verifier, dict(payload or {}))
    if not is_ok(verified):
        return verified
    evidence = dict(verified.value)
    fp = content_address(
        {
            "event": name,
            "evidence": evidence,
            "author_family": author_family,
        }
    )
    if not is_ok(fp):
        return fp
    verifier_ref = fp.value.value
    passed = bool(evidence.get("passed", False))
    if not passed:
        denied = build_hook_result(
            HookResultDecision.DENY,
            reason="verifier_failed",
            verifier_ref=verifier_ref,
            ledger_entry=ledger_entry,
        )
        try:
            validated = assert_hook_result_phase_law(name, denied)
        except VocabularyError as exc:
            return policy_rejection("phase_law", str(exc), given=name)
        return Ok(
            CompletionGateOutcome(
                event=name,
                result=validated,
                verifier_ref=verifier_ref,
            )
        )
    policy = review_policy or ReviewPolicy(model_class=model_class)
    reviewer = select_reviewer(
        author_family,
        catalog,
        model_class=policy.model_class,
    )
    if is_refusal(reviewer):
        return reviewer
    if name == "before_task_complete":
        decision = HookResultDecision.ALLOW
    else:
        decision = HookResultDecision.OBSERVE
    result = build_hook_result(
        decision,
        reason="verifier_passed",
        verifier_ref=verifier_ref,
        ledger_entry=ledger_entry,
    )
    try:
        validated = assert_hook_result_phase_law(name, result)
    except VocabularyError as exc:
        return policy_rejection("phase_law", str(exc), given=name)
    return Ok(
        CompletionGateOutcome(
            event=name,
            result=validated,
            verifier_ref=verifier_ref,
            reviewer=reviewer.value,
        )
    )
