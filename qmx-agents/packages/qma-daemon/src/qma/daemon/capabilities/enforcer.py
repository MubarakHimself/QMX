"""Hook-enforced permission policy for the agent path (FR-Q44; AD-10; AD-24).

``before_tool``, ``before_task_complete``, ``review_required``,
``before_ledger_append``, and ``before_memory_write`` are the single enforcement
points. A ``deny`` binds under every permissive mode.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from qma.core.barriers.money_path import (
    is_money_path_act_denied,
    refuse_money_path_permission,
)
from qma.core.plugins.hooks import HookResult, HookSource, build_hook_result
from qma.core.ports.permissions import (
    AGENT_PATH_ENFORCEMENT_EVENTS,
    PermissionMode,
    PermissionPolicy,
    assert_agent_path_enforcement_event,
    check_plugin_permissions_at_load,
    deny_binds_under_mode,
    resolve_enforcement_decision,
)
from qma.core.vocabulary.enums import HookResultDecision
from qma.daemon.hooks.registry import HookRegistry
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "PermissionPolicyEnforcer",
]


@dataclass
class PermissionPolicyEnforcer:
    """Enforce Role/Mission/plugin permissions through the closed hook set."""

    registry: HookRegistry
    role_policies: dict[str, PermissionPolicy] = field(default_factory=dict[str, PermissionPolicy])
    mode: PermissionMode = PermissionMode.STRICT

    def register_role_policy(self, policy: PermissionPolicy) -> None:
        """Attach a Role permission policy (ceiling for that Role)."""
        self.role_policies[policy.role] = policy

    def check_plugin_load(
        self,
        *,
        plugin_id: str,
        requested: Sequence[str],
        allowed: Sequence[str] | frozenset[str],
    ) -> Result[frozenset[str]]:
        """Plugin permissions are checked at load (FR-Q44; AD-21)."""
        return check_plugin_permissions_at_load(
            requested,
            allowed=allowed,
            plugin_id=plugin_id,
        )

    def enforce(
        self,
        event: str,
        *,
        role: str | None = None,
        required_permission: str | None = None,
        payload: Mapping[str, object] | None = None,
        source: HookSource | str = HookSource.PLUGIN,
        mode: PermissionMode | str | None = None,
        timed_out: bool = False,
        correlation_id: str | None = None,
    ) -> Result[HookResult]:
        """Run one agent-path act through its enforcement hook.

        Unknown events are refused — the five named hooks are the only
        enforcement points. A hook ``deny`` binds under every permissive mode.
        """
        gated = assert_agent_path_enforcement_event(event)
        if not is_ok(gated):
            return policy_rejection(
                "enforcement_event",
                (
                    "agent-path acts enforce only through "
                    f"{sorted(AGENT_PATH_ENFORCEMENT_EVENTS)!r} (FR-Q44; AD-24)"
                ),
                given=event,
            )

        if required_permission is not None and is_money_path_act_denied(required_permission):
            return refuse_money_path_permission(
                tool_id=f"permission:{required_permission}",
                act=required_permission,
                via="permission_policy",
            )
        if payload is not None:
            payload_act = payload.get("act")
            if isinstance(payload_act, str) and is_money_path_act_denied(payload_act):
                tool_raw = payload.get("tool_id", "permission:act")
                return refuse_money_path_permission(
                    tool_id=str(tool_raw),
                    act=payload_act,
                    via="hook",
                )

        resolved_mode = (
            self.mode
            if mode is None
            else (mode if isinstance(mode, PermissionMode) else PermissionMode(mode))
        )

        if role is not None and required_permission is not None:
            policy = self.role_policies.get(role)
            if policy is None:
                return invalid_input(
                    "role",
                    "no permission policy registered for role (FR-Q44; AD-24)",
                    given=role,
                )
            if required_permission not in policy.permissions:
                # Role-policy deny is a HookResult deny; it binds under every
                # permissive mode (FR-Q44; AD-10; AD-24).
                return Ok(
                    build_hook_result(
                        HookResultDecision.DENY,
                        reason="permission_policy_deny",
                    )
                )

        dispatched = self.registry.dispatch(
            event,
            payload=payload,
            source=source,
            timed_out=timed_out,
            correlation_id=correlation_id,
        )
        if not is_ok(dispatched):
            return dispatched

        decision = resolve_enforcement_decision(
            (dispatched.value.decision,),
            mode=resolved_mode,
        )
        if decision is dispatched.value.decision:
            return Ok(dispatched.value)
        return Ok(build_hook_result(decision, reason=dispatched.value.reason))

    def deny_binds(self, decision: HookResultDecision | str) -> bool:
        """Expose the deny-binds-under-any-mode invariant for callers/tests."""
        return deny_binds_under_mode(decision, self.mode)

    def snapshot(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "enforcement_events": tuple(sorted(AGENT_PATH_ENFORCEMENT_EVENTS)),
                "mode": self.mode.value,
                "roles": tuple(sorted(self.role_policies)),
            }
        )
