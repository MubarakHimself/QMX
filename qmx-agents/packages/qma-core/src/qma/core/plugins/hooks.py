"""HookEvent and HookResult contribution types (CT-41; AD-10).

Defined in ``qma-core/plugins/`` so plugins import them from core, never daemon.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from qma.core.plugins.secret_schema import assert_no_secret_in_hook_payloads
from qma.core.vocabulary.enums import HookResultDecision
from qma.core.vocabulary.hooks import (
    assert_decision_legal_for_event,
    assert_fields_legal_for_event,
    parse_hook_event_name,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import is_refusal

__all__ = [
    "FORBIDDEN_HOOK_IMPLEMENTATION_KINDS",
    "HookEvent",
    "HookImplementationKind",
    "HookPhase",
    "HookResult",
    "HookSource",
    "assert_hook_result_phase_law",
    "build_hook_event",
    "build_hook_result",
    "parse_hook_implementation_kind",
]


# Prompt-type and agent-type handlers are refused — hooks are deterministic
# Python callables or subprocesses only (FR-Q34; P-2; AD-10).
FORBIDDEN_HOOK_IMPLEMENTATION_KINDS: Final[frozenset[str]] = frozenset(
    {
        "prompt",
        "agent",
        "prompt_type",
        "agent_type",
        "prompt-type",
        "agent-type",
    }
)


class HookPhase(StrEnum):
    """Phase declared by the event name, or phase-less for the two controls."""

    BEFORE = "before"
    AFTER = "after"
    PHASE_LESS = "phase_less"


class HookSource(StrEnum):
    """Source class that bounds events a hook may receive (AD-10)."""

    DESK = "desk"
    ROLE = "role"
    MISSION = "mission"
    PLUGIN = "plugin"


class HookImplementationKind(StrEnum):
    """Closed deterministic hook forms (FR-Q34; CT-41; AD-10).

    Only ``callable`` and ``subprocess`` are legal. Prompt-type and agent-type
    handlers are refused at registration.
    """

    CALLABLE = "callable"
    SUBPROCESS = "subprocess"


def parse_hook_implementation_kind(value: object) -> HookImplementationKind:
    """Accept only callable or subprocess; refuse prompt/agent handlers."""
    if isinstance(value, HookImplementationKind):
        return value
    if not isinstance(value, str):
        raise VocabularyError(
            f"{value!r} is not a HookImplementationKind; "
            "hooks must be deterministic callable or subprocess (FR-Q34; AD-10)"
        )
    normalized = value.strip().lower().replace("-", "_")
    if normalized in FORBIDDEN_HOOK_IMPLEMENTATION_KINDS or value.strip().lower() in (
        "prompt-type",
        "agent-type",
    ):
        raise VocabularyError(
            f"hook implementation {value!r} is forbidden; no prompt-type or "
            "agent-type handlers (FR-Q34; P-2; AD-10)"
        )
    try:
        return parse_closed(HookImplementationKind, normalized)
    except VocabularyError as exc:
        raise VocabularyError(
            f"{value!r} is not a deterministic hook form; legal kinds are "
            f"{{{', '.join(sorted(k.value for k in HookImplementationKind))}}} "
            "(FR-Q34; AD-10)"
        ) from exc


@dataclass(frozen=True, slots=True)
class HookEvent:
    """A daemon-owned hook invocation envelope.

    ``timeout_key`` cites a ``registry:hook.timeout_*`` key only — never a
    numeric timeout constant (FR-Q32; CT-41; DEC-0309).
    """

    event: str
    phase: HookPhase
    source: HookSource
    payload: Mapping[str, Any]
    matcher: str | None = None
    timeout_key: str | None = None


@dataclass(frozen=True, slots=True)
class HookResult:
    """Tagged-union HookResult; phase-gated fields are optional omitted keys."""

    decision: HookResultDecision
    reason: str = ""
    updated_input: Mapping[str, Any] | None = None
    updated_output: Mapping[str, Any] | None = None
    injected_context: Mapping[str, Any] | None = None
    ledger_entry: Mapping[str, Any] | None = None
    verifier_ref: str | None = None


def _phase_for_event(event: str) -> HookPhase:
    if event.startswith("before_"):
        return HookPhase.BEFORE
    if event.startswith("after_"):
        return HookPhase.AFTER
    return HookPhase.PHASE_LESS


def build_hook_event(
    event: str,
    *,
    source: HookSource | str,
    payload: Mapping[str, Any] | None = None,
    matcher: str | None = None,
    timeout_key: str | None = None,
) -> HookEvent:
    """Construct a HookEvent after validating the closed event name."""
    name = parse_hook_event_name(event)
    resolved_source = source if isinstance(source, HookSource) else parse_closed(HookSource, source)
    return HookEvent(
        event=name,
        phase=_phase_for_event(name),
        source=resolved_source,
        payload=dict(payload or {}),
        matcher=matcher,
        timeout_key=timeout_key,
    )


def build_hook_result(
    decision: HookResultDecision | str,
    *,
    reason: str = "",
    updated_input: Mapping[str, Any] | None = None,
    updated_output: Mapping[str, Any] | None = None,
    injected_context: Mapping[str, Any] | None = None,
    ledger_entry: Mapping[str, Any] | None = None,
    verifier_ref: str | None = None,
) -> HookResult:
    """Construct a HookResult after validating the closed decision vocabulary."""
    resolved = parse_closed(HookResultDecision, decision)
    if resolved is HookResultDecision.OBSERVE and (
        updated_input is not None or updated_output is not None
    ):
        raise VocabularyError("observe may not carry updated_input or updated_output (AD-10)")
    secret_check = assert_no_secret_in_hook_payloads(
        updated_input=updated_input,
        updated_output=updated_output,
        injected_context=injected_context,
    )
    if is_refusal(secret_check):
        raise VocabularyError(
            "resolved secrets are excluded from updated_input, updated_output, "
            "and injected_context (AD-24; FR-Q46)"
        )
    return HookResult(
        decision=resolved,
        reason=reason,
        updated_input=dict(updated_input) if updated_input is not None else None,
        updated_output=dict(updated_output) if updated_output is not None else None,
        injected_context=(dict(injected_context) if injected_context is not None else None),
        ledger_entry=dict(ledger_entry) if ledger_entry is not None else None,
        verifier_ref=verifier_ref,
    )


def assert_hook_result_phase_law(event: str, result: HookResult) -> HookResult:
    """Refuse a HookResult whose decision or fields violate the phase law.

    ``updated_input`` / ``updated_output`` may ride only an ``allow``.
    ``injected_context`` reaches the Context Compiler, never the ledger.
    """
    name = parse_hook_event_name(event)
    assert_decision_legal_for_event(name, result.decision)
    present: list[str] = []
    if result.updated_input is not None:
        present.append("updated_input")
    if result.updated_output is not None:
        present.append("updated_output")
    if result.injected_context is not None:
        present.append("injected_context")
    if result.ledger_entry is not None:
        present.append("ledger_entry")
    if result.verifier_ref is not None:
        present.append("verifier_ref")
    assert_fields_legal_for_event(name, present)
    if result.decision is not HookResultDecision.ALLOW and (
        result.updated_input is not None or result.updated_output is not None
    ):
        raise VocabularyError(
            "updated_input and updated_output ride allow only (FR-Q31; CT-41; AD-10)"
        )
    return result
