"""Per-Role permission policy and agent-path enforcement points (AD-24; FR-Q44).

A per-Role permission policy is part of the Role contract and is the ceiling.
A Mission and a Subagent may only narrow it. Plugin permissions are checked at
load. Hooks ``before_tool``, ``before_task_complete``, ``review_required``,
``before_ledger_append``, and ``before_memory_write`` are the single enforcement
points under AD-10's total precedence; a ``deny`` binds under every permissive
mode.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qma.core.vocabulary.enums import HookControl, HookResultDecision
from qma.core.vocabulary.hooks import (
    HOOK_RESULT_PRECEDENCE,
    hook_result_rank,
    most_restrictive_hook_result,
)
from qmf.core import Ok, Result, is_ok
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "AGENT_PATH_ENFORCEMENT_EVENTS",
    "PermissionMode",
    "PermissionPolicy",
    "assert_agent_path_enforcement_event",
    "check_plugin_permissions_at_load",
    "compute_effective_permissions",
    "deny_binds_under_mode",
    "is_agent_path_enforcement_event",
    "narrow_permissions",
    "resolve_enforcement_decision",
]

# Single agent-path enforcement surface (FR-Q44; AD-10; AD-24).
AGENT_PATH_ENFORCEMENT_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "before_tool",
        "before_task_complete",
        HookControl.REVIEW_REQUIRED.value,
        "before_ledger_append",
        "before_memory_write",
    }
)


class PermissionMode(StrEnum):
    """Runtime permission modes — none may override a binding ``deny`` (FR-Q44)."""

    STRICT = "strict"
    PERMISSIVE = "permissive"


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    """Per-Role permission ceiling — part of the Role contract (AD-24; FR-Q44)."""

    role: str
    permissions: frozenset[str] = field(default_factory=frozenset[str])

    def __post_init__(self) -> None:
        if not self.role.strip():
            msg = "permission policy requires a non-empty role name (FR-Q44; AD-24)"
            raise ValueError(msg)
        cleaned = frozenset(item for item in self.permissions if item.strip())
        object.__setattr__(self, "permissions", cleaned)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "role": self.role,
                "permissions": tuple(sorted(self.permissions)),
            }
        )


def _policy_rejection(
    field: str,
    reason: str,
    *,
    given: object | None = None,
    extras: Sequence[str] | None = None,
) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    if given is not None:
        context["given"] = given
    if extras is not None:
        context["extras"] = list(extras)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def is_agent_path_enforcement_event(event: str) -> bool:
    """True when ``event`` is one of the five agent-path enforcement points."""
    return event in AGENT_PATH_ENFORCEMENT_EVENTS


def assert_agent_path_enforcement_event(event: str) -> Result[str]:
    """Refuse an agent-path act that bypasses the closed enforcement set."""
    if event in AGENT_PATH_ENFORCEMENT_EVENTS:
        return Ok(event)
    return _policy_rejection(
        "enforcement_event",
        (
            "agent-path acts enforce only through before_tool, before_task_complete, "
            "review_required, before_ledger_append, and before_memory_write "
            "(FR-Q44; AD-10; AD-24)"
        ),
        given=event,
    )


def narrow_permissions(
    proposed: Iterable[str] | None,
    *,
    ceiling: Iterable[str],
    field: str,
) -> Result[frozenset[str]]:
    """Mission / Subagent may only narrow a Role permission policy (FR-Q44)."""
    ceiling_set = frozenset(item for item in ceiling if str(item).strip())
    if proposed is None:
        return Ok(ceiling_set)
    asked = frozenset(item for item in proposed if str(item).strip())
    extras = asked - ceiling_set
    if extras:
        return _policy_rejection(
            field,
            (
                f"{field} may only narrow the Role permission policy; "
                "widening is refused (FR-Q44; AD-24)"
            ),
            extras=sorted(extras),
        )
    return Ok(asked)


def compute_effective_permissions(
    role_policy: PermissionPolicy,
    *,
    mission_permissions: Iterable[str] | None = None,
    parent_permissions: Iterable[str] | None = None,
    is_subagent: bool = False,
) -> Result[frozenset[str]]:
    """Role ceiling → Mission narrow → parent/Subagent narrow (FR-Q44)."""
    effective = role_policy.permissions

    if mission_permissions is not None:
        mission = narrow_permissions(
            mission_permissions,
            ceiling=effective,
            field="mission_permissions",
        )
        if not is_ok(mission):
            return mission
        effective = mission.value

    if parent_permissions is not None:
        # Parent/Subagent is a later ceiling: intersect so this stage only
        # removes. Parent extras never widen the child (FR-Q44; AD-24).
        parent = frozenset(item for item in parent_permissions if str(item).strip())
        effective = effective & parent
    elif is_subagent:
        # No parent grant supplied — keep the already-narrowed Role/Mission set.
        effective = frozenset(effective)

    return Ok(effective)


def check_plugin_permissions_at_load(
    requested: Sequence[str] | Iterable[str],
    *,
    allowed: Sequence[str] | Iterable[str] | frozenset[str],
    plugin_id: str,
) -> Result[frozenset[str]]:
    """Plugin permissions are checked at load — extras refuse the load (FR-Q44)."""
    allowed_set = frozenset(item for item in allowed if str(item).strip())
    asked = frozenset(item for item in requested if str(item).strip())
    extras = asked - allowed_set
    if extras:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "plugin.permissions",
                "reason": (
                    "plugin permissions outside the load allowlist are refused at "
                    "load (FR-Q44; AD-24; AD-21)"
                ),
                "plugin_id": plugin_id,
                "extras": sorted(extras),
            },
        )
    return Ok(asked)


def deny_binds_under_mode(
    decision: HookResultDecision | str,
    mode: PermissionMode | str = PermissionMode.PERMISSIVE,
) -> bool:
    """A ``deny`` binds under every permissive mode (FR-Q44; AD-10; AD-24).

    Returns True when the decision must block the act. Permissive mode never
    softens ``deny`` or ``block_stop``.
    """
    resolved = (
        decision if isinstance(decision, HookResultDecision) else HookResultDecision(decision)
    )
    _ = mode if isinstance(mode, PermissionMode) else PermissionMode(mode)  # validate mode
    return resolved in {HookResultDecision.DENY, HookResultDecision.BLOCK_STOP}


def resolve_enforcement_decision(
    decisions: Sequence[HookResultDecision | str],
    *,
    mode: PermissionMode | str = PermissionMode.STRICT,
) -> HookResultDecision:
    """Resolve parallel hook decisions; deny always binds under any mode."""
    if not decisions:
        msg = "enforcement requires at least one HookResult decision (FR-Q44)"
        raise ValueError(msg)
    winner = most_restrictive_hook_result(tuple(decisions))
    if deny_binds_under_mode(winner, mode):
        return winner
    # Pin precedence identity so a future mode cannot invent a softer ladder.
    if winner not in HOOK_RESULT_PRECEDENCE:
        msg = f"unknown HookResult decision {winner!r}"
        raise ValueError(msg)
    _ = hook_result_rank(winner)
    return winner
