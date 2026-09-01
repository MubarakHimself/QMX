"""Agent spawn records the effective capability set once (FR-Q43; AD-16).

The daemon computes the ordered narrowing at spawn, stamps it verbatim on the
Agent record, and refuses any later recompute for that running Agent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.control.primitives import Skill
from qma.core.ontology.actor_id import ActorId
from qma.core.ontology.records import Agent, Subagent
from qma.core.ports.capabilities import (
    EffectiveCapabilitySet,
    RoleBase,
    RoleOverlay,
    compute_effective_capabilities,
)
from qma.core.ports.permissions import (
    PermissionPolicy,
    compute_effective_permissions,
)
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "AgentCapabilityStore",
    "SpawnRequest",
    "spawn_agent",
]


@dataclass(frozen=True, slots=True)
class SpawnRequest:
    """Inputs for one Agent (or Subagent) spawn-time capability computation."""

    agent_id: str
    owner: ActorId
    session_id: str
    role_base: RoleBase
    role_overlay: RoleOverlay | None = None
    role_policy: PermissionPolicy | None = None
    mission_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None
    mission_permissions: Sequence[str] | frozenset[str] | set[str] | None = None
    parent_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None
    parent_permissions: Sequence[str] | frozenset[str] | set[str] | None = None
    parent_agent_id: str | None = None
    is_subagent: bool = False
    base_toolset_tool_ids: Mapping[str, Sequence[str]] | None = None
    tool_tags: Mapping[str, Sequence[str]] | None = None
    graph_template_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None
    task_graph_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None
    appended_skills: Sequence[Skill] = ()


def _materialize_spawn(
    request: SpawnRequest,
) -> Result[tuple[Agent | Subagent, EffectiveCapabilitySet]]:
    """Compute the spawn-time set once and stamp it on the Agent record."""
    if not request.agent_id.strip():
        return invalid_input(
            "agent_id",
            "agent id must be a non-empty string (FR-Q43)",
            given=repr(request.agent_id),
        )
    if not request.session_id.strip():
        return invalid_input(
            "session_id",
            "session id must be a non-empty string (FR-Q43)",
            given=repr(request.session_id),
        )
    overlay = request.role_overlay
    if overlay is None and request.appended_skills:
        overlay = RoleOverlay(
            role=request.role_base.role,
            appended_skills=tuple(request.appended_skills),
        )
    elif overlay is not None and request.appended_skills:
        overlay = RoleOverlay(
            role=overlay.role,
            toolset_ids=overlay.toolset_ids,
            tool_ids=overlay.tool_ids,
            appended_skills=tuple(overlay.appended_skills) + tuple(request.appended_skills),
        )

    caps = compute_effective_capabilities(
        request.role_base,
        overlay=overlay,
        mission_tool_ids=request.mission_tool_ids,
        parent_tool_ids=request.parent_tool_ids,
        base_toolset_tool_ids=request.base_toolset_tool_ids,
        is_subagent=request.is_subagent,
        tool_tags=request.tool_tags,
        graph_template_tool_ids=request.graph_template_tool_ids,
        task_graph_tool_ids=request.task_graph_tool_ids,
    )
    if not is_ok(caps):
        return caps

    policy = request.role_policy or PermissionPolicy(
        role=request.role_base.role,
        permissions=frozenset(),
    )
    perms = compute_effective_permissions(
        policy,
        mission_permissions=request.mission_permissions,
        parent_permissions=request.parent_permissions,
        is_subagent=request.is_subagent,
    )
    if not is_ok(perms):
        return perms

    if request.is_subagent:
        parent_id = request.parent_agent_id
        if parent_id is None or not parent_id.strip():
            return invalid_input(
                "parent_agent_id",
                "Subagent spawn requires parent_agent_id (FR-Q43; AD-16)",
            )
        actor: Agent | Subagent = Subagent(
            id=request.agent_id,
            parent_agent_id=parent_id,
            owner=request.owner,
            session_id=request.session_id,
            effective_tool_ids=caps.value.tool_ids,
            effective_permissions=perms.value,
            capabilities_frozen=True,
        )
    else:
        actor = Agent(
            id=request.agent_id,
            owner=request.owner,
            session_id=request.session_id,
            effective_tool_ids=caps.value.tool_ids,
            effective_permissions=perms.value,
            capabilities_frozen=True,
        )
    return Ok((actor, caps.value))


def spawn_agent(request: SpawnRequest) -> Result[Agent | Subagent]:
    """Compute effective capabilities once and stamp them on the Agent record."""
    spawned = _materialize_spawn(request)
    if not is_ok(spawned):
        return spawned
    return Ok(spawned.value[0])


class AgentCapabilityStore:
    """In-memory Agent records carrying frozen spawn-time capability sets.

    A running Agent's effective set is never recomputed (FR-Q43; AD-16).
    """

    def __init__(self) -> None:
        self._agents: dict[str, Agent | Subagent] = {}
        self._snapshots: dict[str, EffectiveCapabilitySet] = {}

    def spawn(self, request: SpawnRequest) -> Result[Agent | Subagent]:
        """Spawn, record the verbatim set, and refuse duplicate agent ids."""
        if request.agent_id in self._agents:
            return invalid_input(
                "agent_id",
                "agent already spawned; effective capabilities are immutable "
                "for a running Agent (FR-Q43; AD-16)",
                given=request.agent_id,
            )
        spawned = _materialize_spawn(request)
        if not is_ok(spawned):
            return spawned
        agent, snapshot = spawned.value
        self._agents[agent.id] = agent
        self._snapshots[agent.id] = snapshot
        return Ok(agent)

    def get(self, agent_id: str) -> Agent | Subagent | None:
        return self._agents.get(agent_id)

    def recorded_capabilities(self, agent_id: str) -> EffectiveCapabilitySet | None:
        """Return the spawn-time snapshot — never a recomputed value."""
        return self._snapshots.get(agent_id)

    def recompute(
        self,
        agent_id: str,
        request: SpawnRequest,
    ) -> Result[EffectiveCapabilitySet]:
        """Refuse recomputation for a running Agent (FR-Q43; AD-16)."""
        existing = self._agents.get(agent_id)
        if existing is None:
            return invalid_input(
                "agent_id",
                "no running Agent with this id",
                given=agent_id,
            )
        if existing.capabilities_frozen:
            return policy_rejection(
                "effective_capabilities",
                "effective capability set is recorded at spawn and never "
                "recomputed for a running Agent (FR-Q43; AD-16)",
                given=agent_id,
            )
        # Unreachable while capabilities_frozen is always True on spawn.
        _ = request
        return policy_rejection(
            "effective_capabilities",
            "recompute is forbidden (FR-Q43; AD-16)",
            given=agent_id,
        )

    def snapshot(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "agent_count": len(self._agents),
                "agent_ids": tuple(sorted(self._agents)),
            }
        )
