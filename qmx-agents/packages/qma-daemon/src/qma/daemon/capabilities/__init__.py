"""Spawn-time capability narrowing and hook-enforced permission policy.

FR-Q43 / FR-Q44 — AD-16, AD-22, AD-10, AD-24.
"""

from __future__ import annotations

from qma.core.ports.capabilities import (
    CAPABILITY_NARROWING_ORDER,
    EffectiveCapabilitySet,
    RoleBase,
    RoleOverlay,
    assert_skill_is_not_capability_grant,
    compute_effective_capabilities,
    validate_overlay_against_base,
    validate_proposed_grant_against_ceiling,
)
from qma.core.ports.permissions import (
    AGENT_PATH_ENFORCEMENT_EVENTS,
    PermissionMode,
    PermissionPolicy,
    assert_agent_path_enforcement_event,
    check_plugin_permissions_at_load,
    compute_effective_permissions,
    deny_binds_under_mode,
    is_agent_path_enforcement_event,
    narrow_permissions,
    resolve_enforcement_decision,
)
from qma.daemon.capabilities.enforcer import PermissionPolicyEnforcer
from qma.daemon.capabilities.spawn import (
    AgentCapabilityStore,
    SpawnRequest,
    spawn_agent,
)

__all__ = [
    "AGENT_PATH_ENFORCEMENT_EVENTS",
    "CAPABILITY_NARROWING_ORDER",
    "AgentCapabilityStore",
    "EffectiveCapabilitySet",
    "PermissionMode",
    "PermissionPolicy",
    "PermissionPolicyEnforcer",
    "RoleBase",
    "RoleOverlay",
    "SpawnRequest",
    "assert_agent_path_enforcement_event",
    "assert_skill_is_not_capability_grant",
    "check_plugin_permissions_at_load",
    "compute_effective_capabilities",
    "compute_effective_permissions",
    "deny_binds_under_mode",
    "is_agent_path_enforcement_event",
    "narrow_permissions",
    "resolve_enforcement_decision",
    "spawn_agent",
    "validate_overlay_against_base",
    "validate_proposed_grant_against_ceiling",
]
