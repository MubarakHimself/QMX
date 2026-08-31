"""Hook event name construction and HookResult precedence (CT-41; AD-10)."""

from __future__ import annotations

from typing import Final

from qma.core.vocabulary.enums import HookControl, HookResultDecision, HookVerb
from qma.core.vocabulary.registry import VocabularyError, parse_closed

__all__ = [
    "HOOK_CONTROLS",
    "HOOK_EVENT_NAMES",
    "HOOK_RESULT_PRECEDENCE",
    "HOOK_VERBS",
    "build_hook_event_names",
    "hook_result_rank",
    "most_restrictive_hook_result",
    "parse_hook_event_name",
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


def hook_result_rank(decision: HookResultDecision | str) -> int:
    """Rank under total precedence; lower is more restrictive."""
    resolved = parse_closed(HookResultDecision, decision)
    return HOOK_RESULT_PRECEDENCE.index(resolved)


def most_restrictive_hook_result(
    decisions: tuple[HookResultDecision | str, ...],
) -> HookResultDecision:
    """Resolve parallel hook decisions most-restrictive-wins."""
    if not decisions:
        raise VocabularyError("at least one HookResult decision is required")
    ranked = [parse_closed(HookResultDecision, item) for item in decisions]
    return min(ranked, key=hook_result_rank)
