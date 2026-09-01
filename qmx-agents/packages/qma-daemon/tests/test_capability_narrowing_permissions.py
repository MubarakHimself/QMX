"""Story 44.4 — spawn-time capability narrowing and hook-enforced permissions.

FR-Q43 / FR-Q44; AD-16, AD-22, AD-10, AD-24.
"""

from __future__ import annotations

from qma.core.control.primitives import Skill
from qma.core.ontology import ActorId, Agent, DeskSlug, Role, RoleName
from qma.core.plugins.hooks import HookEvent, HookResult, HookSource, build_hook_result
from qma.core.ports.capabilities import (
    CAPABILITY_NARROWING_ORDER,
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
    resolve_enforcement_decision,
)
from qma.core.vocabulary.enums import HookResultDecision
from qma.daemon.capabilities import (
    AgentCapabilityStore,
    PermissionPolicyEnforcer,
    SpawnRequest,
    spawn_agent,
)
from qma.daemon.hooks import HookRegistry
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, "cap-agent")
    assert is_ok(minted)
    return minted.value


def _base_tools() -> RoleBase:
    return RoleBase(
        role="Researcher",
        toolset_ids=("research:default",),
        tool_ids=frozenset(
            {
                "research:search",
                "research:summarize",
                "research:spawn_delegation",
                "research:memory_write",
            }
        ),
    )


def test_narrowing_order_is_base_overlay_mission_parent() -> None:
    assert CAPABILITY_NARROWING_ORDER == (
        "role.base",
        "role.overlay",
        "mission",
        "parent",
    )


def test_ordered_narrowing_role_base_ceiling_then_overlay_mission_parent() -> None:
    base = _base_tools()
    overlay = RoleOverlay(
        role="Researcher",
        tool_ids=frozenset({"research:search", "research:summarize", "research:memory_write"}),
    )
    result = compute_effective_capabilities(
        base,
        overlay=overlay,
        mission_tool_ids=("research:search", "research:summarize"),
        parent_tool_ids=("research:search",),
    )
    assert is_ok(result)
    assert result.value.tool_ids == frozenset({"research:search"})
    assert result.value.frozen is True
    assert result.value.stages_applied == CAPABILITY_NARROWING_ORDER


def test_overlay_outside_base_is_refused_not_silently_dropped() -> None:
    base = _base_tools()
    overlay = RoleOverlay(
        role="Researcher",
        tool_ids=frozenset({"research:search", "research:invented"}),
    )
    refused = validate_overlay_against_base(base, overlay)
    assert is_refusal(refused)
    assert refused.context["field"] == "role.overlay.tool_ids"
    assert refused.context["extras"] == ("research:invented",)

    also = compute_effective_capabilities(base, overlay=overlay)
    assert is_refusal(also)


def test_overlay_toolset_outside_base_refused() -> None:
    base = _base_tools()
    overlay = RoleOverlay(
        role="Researcher",
        toolset_ids=("research:default", "research:extra"),
    )
    refused = validate_overlay_against_base(base, overlay)
    assert is_refusal(refused)
    assert refused.context["field"] == "role.overlay.toolset_ids"


def test_mission_graph_template_task_graph_cannot_widen() -> None:
    base = _base_tools()
    mission = compute_effective_capabilities(
        base,
        mission_tool_ids=("research:search", "research:invented"),
    )
    assert is_refusal(mission)

    graph = compute_effective_capabilities(
        base,
        graph_template_tool_ids=("research:search", "research:extra"),
    )
    assert is_refusal(graph)

    task_graph = compute_effective_capabilities(
        base,
        task_graph_tool_ids=frozenset({"research:unknown"}),
    )
    assert is_refusal(task_graph)


def test_skill_never_grants_capability() -> None:
    base = _base_tools()
    skill = Skill(
        qualified_id="research:note-taking",
        version="1",
        summary="knowledge only",
        body="how to take notes",
    )
    assert skill.to_payload()["grants_capability"] is False

    overlay = RoleOverlay(
        role="Researcher",
        tool_ids=frozenset({"research:search"}),
        appended_skills=(skill,),
    )
    result = compute_effective_capabilities(base, overlay=overlay)
    assert is_ok(result)
    assert result.value.tool_ids == frozenset({"research:search"})
    assert "research:note-taking" not in result.value.tool_ids


def test_spawn_records_verbatim_set_and_refuses_recompute() -> None:
    store = AgentCapabilityStore()
    base = _base_tools()
    request = SpawnRequest(
        agent_id="agent-1",
        owner=_owner(),
        session_id="session-1",
        role_base=base,
        role_overlay=RoleOverlay(
            role="Researcher",
            tool_ids=frozenset({"research:search", "research:summarize"}),
        ),
        role_policy=PermissionPolicy(
            role="Researcher",
            permissions=frozenset({"tool.read", "tool.list", "memory.read"}),
        ),
        mission_tool_ids=("research:search",),
        mission_permissions=("tool.read",),
    )
    spawned = store.spawn(request)
    assert is_ok(spawned)
    agent = spawned.value
    assert agent.effective_tool_ids == frozenset({"research:search"})
    assert agent.effective_permissions == frozenset({"tool.read"})
    assert agent.capabilities_frozen is True

    recorded = store.recorded_capabilities("agent-1")
    assert recorded is not None
    assert recorded.tool_ids == frozenset({"research:search"})
    assert recorded.frozen is True

    # Same id refused; recompute refused for running Agent.
    dup = store.spawn(request)
    assert is_refusal(dup)

    wider = SpawnRequest(
        agent_id="agent-1",
        owner=_owner(),
        session_id="session-1",
        role_base=base,
        mission_tool_ids=(
            "research:search",
            "research:summarize",
            "research:memory_write",
        ),
    )
    recomputed = store.recompute("agent-1", wider)
    assert is_refusal(recomputed)
    assert "never recomputed" in str(recomputed.context["reason"])
    recorded_agent = store.get("agent-1")
    assert recorded_agent is not None
    assert recorded_agent.effective_tool_ids == frozenset({"research:search"})
    snapshot = store.recorded_capabilities("agent-1")
    assert snapshot is not None
    assert snapshot.stages_applied == CAPABILITY_NARROWING_ORDER


def test_subagent_never_wider_than_parent_and_leaf_blocks() -> None:
    store = AgentCapabilityStore()
    base = _base_tools()
    parent_req = SpawnRequest(
        agent_id="parent-1",
        owner=_owner(),
        session_id="session-1",
        role_base=base,
        mission_tool_ids=(
            "research:search",
            "research:spawn_delegation",
            "research:memory_write",
        ),
    )
    parent = store.spawn(parent_req)
    assert is_ok(parent)

    child = store.spawn(
        SpawnRequest(
            agent_id="child-1",
            owner=_owner(),
            session_id="session-1",
            role_base=base,
            parent_agent_id="parent-1",
            is_subagent=True,
            parent_tool_ids=parent.value.effective_tool_ids,
            tool_tags={
                "research:spawn_delegation": ("delegation",),
                "research:memory_write": ("memory_write",),
            },
        )
    )
    assert is_ok(child)
    assert child.value.effective_tool_ids == frozenset({"research:search"})
    assert "research:spawn_delegation" not in child.value.effective_tool_ids
    assert "research:memory_write" not in child.value.effective_tool_ids


def test_permission_policy_mission_and_subagent_only_narrow() -> None:
    policy = PermissionPolicy(
        role="Researcher",
        permissions=frozenset({"tool.read", "tool.list", "memory.read"}),
    )
    ok = compute_effective_permissions(
        policy,
        mission_permissions=("tool.read", "memory.read"),
    )
    assert is_ok(ok)
    assert ok.value == frozenset({"tool.read", "memory.read"})

    widened = compute_effective_permissions(
        policy,
        mission_permissions=("tool.read", "tool.write"),
    )
    assert is_refusal(widened)

    parent_narrow = compute_effective_permissions(
        policy,
        mission_permissions=("tool.read", "memory.read"),
        parent_permissions=("tool.read",),
        is_subagent=True,
    )
    assert is_ok(parent_narrow)
    assert parent_narrow.value == frozenset({"tool.read"})

    parent_ceiling = compute_effective_permissions(
        policy,
        parent_permissions=("tool.read",),
        is_subagent=True,
    )
    assert is_ok(parent_ceiling)
    assert parent_ceiling.value == frozenset({"tool.read"})

    parent_cannot_widen = compute_effective_permissions(
        policy,
        parent_permissions=("tool.read", "tool.list", "memory.read", "tool.write"),
        is_subagent=True,
    )
    assert is_ok(parent_cannot_widen)
    assert parent_cannot_widen.value == policy.permissions
    assert "tool.write" not in parent_cannot_widen.value


def test_plugin_permissions_checked_at_load() -> None:
    allowed = frozenset({"tool.read", "hook.register"})
    ok = check_plugin_permissions_at_load(
        ("tool.read",),
        allowed=allowed,
        plugin_id="research-corpus",
    )
    assert is_ok(ok)

    refused = check_plugin_permissions_at_load(
        ("tool.read", "secret.exfiltrate"),
        allowed=allowed,
        plugin_id="research-corpus",
    )
    assert is_refusal(refused)
    assert refused.context["plugin_id"] == "research-corpus"
    assert refused.context["extras"] == ("secret.exfiltrate",)


def test_agent_path_enforcement_events_are_exactly_five() -> None:
    assert (
        frozenset(
            {
                "before_tool",
                "before_task_complete",
                "review_required",
                "before_ledger_append",
                "before_memory_write",
            }
        )
        == AGENT_PATH_ENFORCEMENT_EVENTS
    )
    assert is_ok(assert_agent_path_enforcement_event("before_tool"))
    assert is_refusal(assert_agent_path_enforcement_event("after_tool"))
    assert is_refusal(assert_agent_path_enforcement_event("before_message_send"))


def test_deny_binds_under_every_permissive_mode() -> None:
    assert deny_binds_under_mode(HookResultDecision.DENY, PermissionMode.PERMISSIVE)
    assert deny_binds_under_mode(HookResultDecision.DENY, PermissionMode.STRICT)
    assert deny_binds_under_mode(HookResultDecision.BLOCK_STOP, PermissionMode.PERMISSIVE)
    assert not deny_binds_under_mode(HookResultDecision.ALLOW, PermissionMode.PERMISSIVE)

    winner = resolve_enforcement_decision(
        (HookResultDecision.ALLOW, HookResultDecision.DENY),
        mode=PermissionMode.PERMISSIVE,
    )
    assert winner is HookResultDecision.DENY


def test_enforcer_routes_through_hooks_and_role_ceiling() -> None:
    registry = HookRegistry()
    enforcer = PermissionPolicyEnforcer(
        registry,
        mode=PermissionMode.PERMISSIVE,
    )
    enforcer.register_role_policy(
        PermissionPolicy(
            role="Researcher",
            permissions=frozenset({"tool.read"}),
        )
    )

    # Missing permission → deny binds under permissive mode.
    denied = enforcer.enforce(
        "before_tool",
        role="Researcher",
        required_permission="tool.write",
    )
    assert is_ok(denied)
    assert denied.value.decision is HookResultDecision.DENY
    assert enforcer.deny_binds(denied.value.decision)

    # Bypass event refused.
    bypass = enforcer.enforce("after_tool")
    assert is_refusal(bypass)

    # Registered hook deny still binds under permissive mode.
    def deny_handler(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.DENY, reason="policy")

    assert is_ok(
        registry.register_handler(
            "before_memory_write",
            deny_handler,
            source=HookSource.PLUGIN,
        )
    )
    memory = enforcer.enforce("before_memory_write", mode=PermissionMode.PERMISSIVE)
    assert is_ok(memory)
    assert memory.value.decision is HookResultDecision.DENY

    load = enforcer.check_plugin_load(
        plugin_id="research-corpus",
        requested=("tool.read", "admin.escalate"),
        allowed=("tool.read",),
    )
    assert is_refusal(load)

    missing_role = enforcer.enforce(
        "before_tool",
        role="Trader",
        required_permission="tool.read",
    )
    assert is_refusal(missing_role)


def test_parent_cannot_widen_capability_set() -> None:
    base = _base_tools()
    result = compute_effective_capabilities(
        base,
        parent_tool_ids=(*base.tool_ids, "research:invented"),
    )
    assert is_ok(result)
    assert "research:invented" not in result.value.tool_ids
    assert result.value.tool_ids == base.tool_ids


def test_overlay_toolset_narrows_remaining_tools() -> None:
    base = RoleBase(
        role="Researcher",
        toolset_ids=("research:default", "research:extra"),
        tool_ids=frozenset(),
    )
    overlay = RoleOverlay(role="Researcher", toolset_ids=("research:default",))
    result = compute_effective_capabilities(
        base,
        overlay=overlay,
        base_toolset_tool_ids={
            "research:default": ("research:search",),
            "research:extra": ("research:summarize",),
        },
    )
    assert is_ok(result)
    assert result.value.tool_ids == frozenset({"research:search"})
    assert result.value.toolset_ids == ("research:default",)


def test_overlay_role_mismatch_and_proposed_grant_refused() -> None:
    base = _base_tools()
    mismatched = RoleOverlay(role="Trader", tool_ids=frozenset({"research:search"}))
    refused = validate_overlay_against_base(base, mismatched)
    assert is_refusal(refused)

    extra = validate_proposed_grant_against_ceiling(
        ("research:search", "research:invented"),
        ceiling=base.tool_ids,
        field="mission",
    )
    assert is_refusal(extra)
    unchanged = validate_proposed_grant_against_ceiling(
        None,
        ceiling=base.tool_ids,
        field="mission",
    )
    assert is_ok(unchanged)
    assert unchanged.value == base.tool_ids


def test_skill_assert_and_role_permission_policy_contract() -> None:
    skill = Skill(
        qualified_id="research:note-taking",
        version="1",
        summary="knowledge only",
        body="notes",
    )
    asserted = assert_skill_is_not_capability_grant(skill)
    assert is_ok(asserted)

    role = Role(
        name=RoleName.RESEARCHER,
        permission_policy=frozenset({"tool.read", "memory.read"}),
    )
    assert role.permission_policy == frozenset({"tool.read", "memory.read"})

    agent = Agent(
        id="frozen-1",
        owner=_owner(),
        session_id="session-1",
        effective_tool_ids=frozenset({"research:search"}),
        capabilities_frozen=False,
    )
    assert agent.capabilities_frozen is True


def test_spawn_refuses_subagent_without_parent_and_unknown_recompute() -> None:
    store = AgentCapabilityStore()
    missing = spawn_agent(
        SpawnRequest(
            agent_id="child-x",
            owner=_owner(),
            session_id="session-1",
            role_base=_base_tools(),
            is_subagent=True,
        )
    )
    assert is_refusal(missing)

    empty = spawn_agent(
        SpawnRequest(
            agent_id="  ",
            owner=_owner(),
            session_id="session-1",
            role_base=_base_tools(),
        )
    )
    assert is_refusal(empty)

    unknown = store.recompute(
        "missing",
        SpawnRequest(
            agent_id="missing",
            owner=_owner(),
            session_id="session-1",
            role_base=_base_tools(),
        ),
    )
    assert is_refusal(unknown)
