"""Hook event name construction, phase law, and HookResult precedence (CT-41; AD-10)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from qma.core.vocabulary.enums import HookControl, HookResultDecision, HookVerb
from qma.core.vocabulary.registry import VocabularyError, parse_closed

__all__ = [
    "HOOK_CONTROLS",
    "HOOK_EVENT_NAMES",
    "HOOK_RESULT_FIELDS",
    "HOOK_RESULT_PRECEDENCE",
    "HOOK_VERBS",
    "assert_decision_legal_for_event",
    "assert_fields_legal_for_event",
    "build_hook_event_names",
    "empty_result_decision_for_event",
    "hook_result_rank",
    "legal_decisions_for_event",
    "legal_fields_for_event",
    "most_restrictive_hook_result",
    "parse_hook_event_name",
    "validate_registration_phase_law",
]

HOOK_VERBS: Final[tuple[HookVerb, ...]] = tuple(HookVerb)
HOOK_CONTROLS: Final[tuple[HookControl, ...]] = tuple(HookControl)

# Total precedence: block_stop > deny > defer > ask > allow > observe (DEC-0309).
# Lower index is more restrictive; parallel hooks resolve most-restrictive-wins.
HOOK_RESULT_PRECEDENCE: Final[tuple[HookResultDecision, ...]] = (
    HookResultDecision.BLOCK_STOP,
    HookResultDecision.DENY,
    HookResultDecision.DEFER,
    HookResultDecision.ASK,
    HookResultDecision.ALLOW,
    HookResultDecision.OBSERVE,
)

# Phase-gated HookResult fields (decision/reason are always legal).
HOOK_RESULT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "updated_input",
        "updated_output",
        "injected_context",
        "ledger_entry",
        "verifier_ref",
    }
)

_BEFORE_DECISIONS: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.ALLOW,
        HookResultDecision.OBSERVE,
    }
)
_AGENT_STOP_DECISIONS: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.BLOCK_STOP,
        HookResultDecision.OBSERVE,
    }
)
_REVIEW_REQUIRED_DECISIONS: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.BLOCK_STOP,
        HookResultDecision.OBSERVE,
    }
)
_AFTER_TOOL_DECISIONS: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.ALLOW,
        HookResultDecision.OBSERVE,
    }
)
_AFTER_ONLY_OBSERVE: Final[frozenset[HookResultDecision]] = frozenset(
    {HookResultDecision.OBSERVE}
)


def build_hook_event_names() -> frozenset[str]:
    """All legal HookEvent names: before_/after_ per verb plus two controls."""
    events: set[str] = set()
    for verb in HOOK_VERBS:
        events.add(f"before_{verb.value}")
        events.add(f"after_{verb.value}")
    for control in HOOK_CONTROLS:
        events.add(control.value)
    return frozenset(events)


HOOK_EVENT_NAMES: Final[frozenset[str]] = build_hook_event_names()


def parse_hook_event_name(value: object) -> str:
    """Accept only a registered before_/after_ verb event or phase-less control."""
    if not isinstance(value, str):
        raise VocabularyError(f"{value!r} is not a HookEvent name")
    if value in HOOK_EVENT_NAMES:
        return value
    raise VocabularyError(f"{value!r} is not a registered HookEvent name")


def legal_decisions_for_event(event: str) -> frozenset[HookResultDecision]:
    """Closed legal decision set for one HookEvent under the phase law (FR-Q31)."""
    name = parse_hook_event_name(event)
    if name == HookControl.AGENT_STOP.value:
        return _AGENT_STOP_DECISIONS
    if name == HookControl.REVIEW_REQUIRED.value:
        return _REVIEW_REQUIRED_DECISIONS
    if name.startswith("before_"):
        return _BEFORE_DECISIONS
    if name == "after_tool":
        return _AFTER_TOOL_DECISIONS
    if name.startswith("after_"):
        return _AFTER_ONLY_OBSERVE
    raise VocabularyError(f"{name!r} has no phase-law decision set")


def legal_fields_for_event(event: str) -> frozenset[str]:
    """Phase-gated HookResult fields legal for one event (FR-Q31; CT-41)."""
    name = parse_hook_event_name(event)
    if name == "before_tool":
        return frozenset({"updated_input", "injected_context"})
    if name == "after_tool":
        return frozenset({"updated_output"})
    if name == "before_task_complete":
        return frozenset({"injected_context", "ledger_entry", "verifier_ref"})
    if name == HookControl.REVIEW_REQUIRED.value:
        return frozenset({"ledger_entry", "verifier_ref"})
    if name.startswith("before_"):
        return frozenset({"injected_context"})
    return frozenset()


def empty_result_decision_for_event(event: str) -> HookResultDecision:
    """Resolution when a hook returns no result — never a null decision (FR-Q31)."""
    name = parse_hook_event_name(event)
    if name.startswith("before_") or name == "after_tool":
        return HookResultDecision.ALLOW
    return HookResultDecision.OBSERVE


def assert_decision_legal_for_event(
    event: str,
    decision: HookResultDecision | str,
) -> HookResultDecision:
    """Refuse a decision illegal for the event's phase (registration-time)."""
    name = parse_hook_event_name(event)
    resolved = parse_closed(HookResultDecision, decision)
    legal = legal_decisions_for_event(name)
    if resolved not in legal:
        allowed = ", ".join(sorted(item.value for item in legal))
        raise VocabularyError(
            f"decision {resolved.value!r} is illegal for event {name!r}; "
            f"legal decisions are {{{allowed}}} (FR-Q31; CT-41; AD-10)"
        )
    return resolved


def assert_fields_legal_for_event(
    event: str,
    fields: Iterable[str],
) -> frozenset[str]:
    """Refuse phase-gated fields illegal for the event (registration-time)."""
    name = parse_hook_event_name(event)
    declared = frozenset(fields)
    unknown = declared - HOOK_RESULT_FIELDS
    if unknown:
        raise VocabularyError(
            f"unknown HookResult field(s) {sorted(unknown)!r}; "
            f"phase-gated fields are {sorted(HOOK_RESULT_FIELDS)!r} (FR-Q31; CT-41)"
        )
    legal = legal_fields_for_event(name)
    illegal = declared - legal
    if illegal:
        raise VocabularyError(
            f"field(s) {sorted(illegal)!r} are illegal for event {name!r}; "
            f"legal fields are {sorted(legal)!r} (FR-Q31; CT-41; AD-10)"
        )
    return declared


def validate_registration_phase_law(
    event: str,
    *,
    decisions: Iterable[HookResultDecision | str] | None = None,
    fields: Iterable[str] | None = None,
) -> tuple[frozenset[HookResultDecision], frozenset[str]]:
    """Validate declared decisions and fields at registration (FR-Q31).

    Omitted ``decisions`` defaults to the full legal set for the event.
    Omitted ``fields`` defaults to no phase-gated fields.
    """
    name = parse_hook_event_name(event)
    if decisions is None:
        resolved_decisions = legal_decisions_for_event(name)
    else:
        resolved_decisions = frozenset(
            assert_decision_legal_for_event(name, item) for item in decisions
        )
        if not resolved_decisions:
            raise VocabularyError(
                f"hook registration for {name!r} must declare at least one "
                "legal decision (FR-Q31; AD-10)"
            )
    resolved_fields: frozenset[str] = (
        frozenset() if fields is None else assert_fields_legal_for_event(name, fields)
    )
    return resolved_decisions, resolved_fields


def hook_result_rank(decision: HookResultDecision | str) -> int:
    """Rank under total precedence; lower is more restrictive."""
    resolved = parse_closed(HookResultDecision, decision)
    return HOOK_RESULT_PRECEDENCE.index(resolved)


def most_restrictive_hook_result(
    decisions: tuple[HookResultDecision | str, ...],
) -> HookResultDecision:
    """Resolve parallel hook decisions most-restrictive-wins.

    ``observe`` never participates when any non-observe decision is present.
    An empty decision set is illegal — a missing result is resolved by
    ``empty_result_decision_for_event``, never as a null decision.
    """
    if not decisions:
        raise VocabularyError(
            "at least one HookResult decision is required; missing results "
            "resolve via empty_result_decision_for_event, never null (FR-Q31)"
        )
    ranked = [parse_closed(HookResultDecision, item) for item in decisions]
    participating = [item for item in ranked if item is not HookResultDecision.OBSERVE]
    if participating:
        return min(participating, key=hook_result_rank)
    return HookResultDecision.OBSERVE
