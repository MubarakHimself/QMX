"""Spawn-time effective capability narrowing (AD-16; FR-Q43).

``role.base`` is the ceiling. Ordered narrowing applies ``role.overlay``, then
Mission, then parent — every stage after ``role.base`` may only remove. An
overlay (or later scope) naming a tool or toolset outside the base is refused
at application, never silently dropped. An appended Skill is knowledge and
never a capability grant. The computed set is recorded verbatim on the Agent
record and never recomputed for a running Agent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from qma.core.control.primitives import Skill
from qma.core.ports.tools import (
    skill_grants_tool_or_capability,
    subagent_inherited_tool_ids,
)
from qmf.core import Ok, Result, is_ok
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "CAPABILITY_NARROWING_ORDER",
    "EffectiveCapabilitySet",
    "RoleBase",
    "RoleOverlay",
    "assert_skill_is_not_capability_grant",
    "compute_effective_capabilities",
    "validate_overlay_against_base",
    "validate_proposed_grant_against_ceiling",
]

# Ordered stages after role.base — each may remove only (FR-Q43; AD-16).
CAPABILITY_NARROWING_ORDER: Final[tuple[str, ...]] = (
    "role.base",
    "role.overlay",
    "mission",
    "parent",
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


@dataclass(frozen=True, slots=True)
class RoleBase:
    """Operator-authored capability ceiling for a Role (``role.base``; AD-16/AD-22).

    Written only by an operator-principal ``role.set_base`` command. Grants
    toolsets (and optionally explicit tool ids). This is the spawn-time ceiling.
    """

    role: str
    toolset_ids: tuple[str, ...] = ()
    tool_ids: frozenset[str] = field(default_factory=frozenset[str])

    def __post_init__(self) -> None:
        if not self.role.strip():
            msg = "role.base requires a non-empty role name (FR-Q43; AD-16)"
            raise ValueError(msg)
        object.__setattr__(self, "toolset_ids", tuple(dict.fromkeys(self.toolset_ids)))
        object.__setattr__(self, "tool_ids", frozenset(self.tool_ids))
        for tool_id in self.tool_ids:
            if ":" not in tool_id:
                msg = f"role.base tool ids must be fully-qualified; got {tool_id!r} (FR-Q43; AD-16)"
                raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class RoleOverlay:
    """Proposal-editable Role overlay — may only narrow grants (AD-22; FR-Q43).

    May append Skills (knowledge only) and narrow toolsets/tools. Naming a tool
    or toolset outside ``role.base`` is refused at application.
    """

    role: str
    toolset_ids: tuple[str, ...] | None = None
    tool_ids: frozenset[str] | None = None
    appended_skills: tuple[Skill, ...] = ()

    def __post_init__(self) -> None:
        if not self.role.strip():
            msg = "role.overlay requires a non-empty role name (FR-Q43; AD-22)"
            raise ValueError(msg)
        if self.toolset_ids is not None:
            object.__setattr__(
                self,
                "toolset_ids",
                tuple(dict.fromkeys(self.toolset_ids)),
            )
        if self.tool_ids is not None:
            object.__setattr__(self, "tool_ids", frozenset(self.tool_ids))
            for tool_id in self.tool_ids:
                if ":" not in tool_id:
                    msg = (
                        f"role.overlay tool ids must be fully-qualified; "
                        f"got {tool_id!r} (FR-Q43; AD-16)"
                    )
                    raise ValueError(msg)
        object.__setattr__(self, "appended_skills", tuple(self.appended_skills))


@dataclass(frozen=True, slots=True)
class EffectiveCapabilitySet:
    """Immutable-at-spawn capability snapshot recorded on the Agent (FR-Q43)."""

    tool_ids: frozenset[str]
    toolset_ids: tuple[str, ...] = ()
    stages_applied: tuple[str, ...] = CAPABILITY_NARROWING_ORDER
    frozen: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_ids", frozenset(self.tool_ids))
        object.__setattr__(self, "toolset_ids", tuple(self.toolset_ids))
        object.__setattr__(self, "stages_applied", tuple(self.stages_applied))
        object.__setattr__(self, "frozen", True)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "tool_ids": tuple(sorted(self.tool_ids)),
                "toolset_ids": list(self.toolset_ids),
                "stages_applied": list(self.stages_applied),
                "frozen": True,
            }
        )


def assert_skill_is_not_capability_grant(skill: Skill) -> Result[str]:
    """Refuse any attempt to treat a Skill as a tool or capability grant."""
    if skill_grants_tool_or_capability():
        return _policy_rejection(
            "skill",
            "Skill must not grant a tool or capability (FR-Q43; AD-16)",
            given=skill.qualified_id,
        )
    payload = skill.to_payload()
    if payload.get("grants_capability"):
        return _policy_rejection(
            "skill",
            "appended Skill supplies knowledge only and never a capability grant "
            "(FR-Q43; AD-16; AD-22)",
            given=skill.qualified_id,
        )
    return Ok(skill.qualified_id)


def validate_proposed_grant_against_ceiling(
    proposed_tool_ids: Sequence[str] | frozenset[str] | set[str] | None,
    *,
    ceiling: Sequence[str] | frozenset[str] | set[str],
    field: str,
) -> Result[frozenset[str]]:
    """Refuse a wider grant rather than silently dropping extras (FR-Q43)."""
    if proposed_tool_ids is None:
        return Ok(frozenset(ceiling))
    return _narrow_or_refuse(proposed_tool_ids, ceiling, field=field)


def _narrow_or_refuse(
    proposed: Sequence[str] | frozenset[str] | set[str],
    ceiling: Sequence[str] | frozenset[str] | set[str],
    *,
    field: str,
) -> Result[frozenset[str]]:
    granted = frozenset(ceiling)
    asked = frozenset(proposed)
    extras = asked - granted
    if extras:
        return _policy_rejection(
            field,
            (
                f"{field} may only remove capabilities under role.base; "
                "wider grants are refused, never silently dropped (FR-Q43; AD-16)"
            ),
            extras=sorted(extras),
        )
    return Ok(asked)


def validate_overlay_against_base(
    base: RoleBase,
    overlay: RoleOverlay,
    *,
    base_toolset_tool_ids: Mapping[str, Sequence[str]] | None = None,
) -> Result[frozenset[str]]:
    """Refuse overlay tool/toolset entries outside ``role.base`` (FR-Q43; AD-22)."""
    if overlay.role != base.role:
        return _policy_rejection(
            "role.overlay",
            "overlay role must match role.base (FR-Q43; AD-22)",
            given=overlay.role,
        )

    for skill in overlay.appended_skills:
        skill_ok = assert_skill_is_not_capability_grant(skill)
        if not is_ok(skill_ok):
            return skill_ok

    ceiling_tools = set(base.tool_ids)
    if base_toolset_tool_ids is not None:
        for toolset_id in base.toolset_ids:
            ceiling_tools.update(base_toolset_tool_ids.get(toolset_id, ()))

    if overlay.toolset_ids is not None:
        base_sets = frozenset(base.toolset_ids)
        extras = frozenset(overlay.toolset_ids) - base_sets
        if extras:
            return _policy_rejection(
                "role.overlay.toolset_ids",
                (
                    "overlay toolset outside role.base is refused at application, "
                    "never silently dropped (FR-Q43; AD-16; AD-22)"
                ),
                extras=sorted(extras),
            )

    if overlay.tool_ids is None:
        if overlay.toolset_ids is None or base_toolset_tool_ids is None:
            return Ok(frozenset(ceiling_tools))
        remaining = set(base.tool_ids)
        for toolset_id in overlay.toolset_ids:
            remaining.update(base_toolset_tool_ids.get(toolset_id, ()))
        return Ok(frozenset(remaining))
    return _narrow_or_refuse(
        overlay.tool_ids,
        ceiling_tools,
        field="role.overlay.tool_ids",
    )


def compute_effective_capabilities(
    base: RoleBase,
    *,
    overlay: RoleOverlay | None = None,
    mission_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None,
    parent_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None,
    base_toolset_tool_ids: Mapping[str, Sequence[str]] | None = None,
    is_subagent: bool = False,
    tool_tags: Mapping[str, Sequence[str]] | None = None,
    graph_template_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None,
    task_graph_tool_ids: Sequence[str] | frozenset[str] | set[str] | None = None,
) -> Result[EffectiveCapabilitySet]:
    """Compute the spawn-time effective set by ordered narrowing (FR-Q43).

    Stages: ``role.base`` (ceiling) → ``role.overlay`` → Mission → parent.
    Graph Template / Task Graph proposals that widen are refused like overlays.
    Skills never contribute tools. Result is frozen for the Agent record.
    """
    ceiling_tools: set[str] = set(base.tool_ids)
    if base_toolset_tool_ids is not None:
        for toolset_id in base.toolset_ids:
            ceiling_tools.update(base_toolset_tool_ids.get(toolset_id, ()))
    effective = frozenset(ceiling_tools)
    effective_toolsets: tuple[str, ...] = base.toolset_ids

    if overlay is not None:
        overlay_ok = validate_overlay_against_base(
            base,
            overlay,
            base_toolset_tool_ids=base_toolset_tool_ids,
        )
        if not is_ok(overlay_ok):
            return overlay_ok
        effective = overlay_ok.value
        if overlay.toolset_ids is not None:
            effective_toolsets = overlay.toolset_ids

    # Graph Template / Task Graph may only narrow — refuse widen attempts.
    for label, proposed in (
        ("graph_template", graph_template_tool_ids),
        ("task_graph", task_graph_tool_ids),
    ):
        if proposed is None:
            continue
        narrowed = _narrow_or_refuse(proposed, effective, field=label)
        if not is_ok(narrowed):
            return narrowed
        effective = narrowed.value

    if mission_tool_ids is not None:
        mission = _narrow_or_refuse(mission_tool_ids, effective, field="mission")
        if not is_ok(mission):
            return mission
        effective = mission.value

    if parent_tool_ids is not None:
        # Parent is a later ceiling, typically a superset. Intersect so this
        # stage only removes; parent extras never become a grant (FR-Q43).
        effective = effective & frozenset(parent_tool_ids)

    if is_subagent:
        effective = subagent_inherited_tool_ids(effective, tool_tags=tool_tags)

    return Ok(
        EffectiveCapabilitySet(
            tool_ids=effective,
            toolset_ids=effective_toolsets,
            stages_applied=CAPABILITY_NARROWING_ORDER,
            frozen=True,
        )
    )
