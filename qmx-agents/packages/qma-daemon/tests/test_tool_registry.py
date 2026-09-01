"""Story 44.3 — Unified Tool Registry, adapter governance, lowest-capable selection."""

from __future__ import annotations

import pytest
from qma.core.barriers.capability import CAPABILITY_LADDER, CapabilityRung
from qma.core.control.primitives import Skill
from qma.core.plugins.manifest import ManifestError, parse_plugin_manifest
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.tools import (
    TOOL_KINDS,
    ToolAdapterRecord,
    ToolKind,
    ToolRecord,
    ToolsetRecord,
    select_lowest_capable,
    skill_grants_tool_or_capability,
)
from qma.core.refusals import OperatorPrincipalRequired, ProhibitedMoneyPathTool
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, PrincipalClass
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.tools import GAP_0070_DESKTOP_EXCLUSION, ToolRegistry
from qmf.core import is_ok, is_refusal


class _EnvStub:
    """Minimal ExecutionEnvironment stand-in for desktop registration tests."""


def test_all_seven_kinds_enter_one_registry() -> None:
    registry = ToolRegistry()
    assert registry.supported_kinds == TOOL_KINDS
    assert {kind.value for kind in TOOL_KINDS} == {
        "native",
        "cli",
        "plugin",
        "mcp_adapter",
        "browser",
        "computer_use",
        "backtest",
    }
    for kind in ToolKind:
        tool_id = f"demo:{kind.value}"
        assert is_ok(
            registry.register(
                tool_id=tool_id,
                kind=kind,
                schema={"name": kind.value},
                acts=("read",),
                check_fn=(lambda: False) if kind is ToolKind.COMPUTER_USE else None,
            )
        )
        entry = registry.get(tool_id)
        assert entry is not None
        assert entry.kind is kind
    assert len(registry.catalog()) == 7


def test_check_fn_excludes_unrunnable_before_schema_reaches_model() -> None:
    registry = ToolRegistry()
    assert is_ok(
        registry.register(
            tool_id="research:search",
            kind=ToolKind.NATIVE,
            schema={"name": "search", "params": ["q"]},
            acts=("search",),
            check_fn=lambda: True,
        )
    )
    assert is_ok(
        registry.register(
            tool_id="research:broken",
            kind=ToolKind.CLI,
            schema={"name": "broken"},
            acts=("search",),
            check_fn=lambda: False,
        )
    )
    visible = registry.model_visible_schemas()
    ids = [row["tool_id"] for row in visible]
    assert "research:search" in ids
    assert "research:broken" not in ids
    # Unrunnable tool stays registered but never model-visible.
    assert registry.get("research:broken") is not None
    assert registry.is_available("research:broken") is False


def test_tool_adapter_binding_is_operator_only_and_absent_from_manifest() -> None:
    registry = ToolRegistry()
    adapter = ToolAdapterRecord(
        adapter_id="trading-readonly:mcp",
        advertised_tool_ids=("trading-readonly:positions",),
    )
    assert is_ok(registry.register_adapter(adapter))

    machine = registry.write_adapter_binding(
        "trading-readonly:mcp",
        desk="trading",
        role="analyst",
        principal=PrincipalClass.MACHINE,
    )
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    assert machine.context["command"] == "tool_adapter.write"

    operator = registry.write_adapter_binding(
        "trading-readonly:mcp",
        desk="trading",
        role="analyst",
        principal=PrincipalClass.OPERATOR,
    )
    assert is_ok(operator)
    binding = registry.get_binding("trading-readonly:mcp", "trading", "analyst")
    assert binding is not None
    assert binding.desk == "trading"
    assert binding.role == "analyst"

    with pytest.raises(ManifestError, match="tool_adapter_binding"):
        parse_plugin_manifest(
            {
                "id": "trading-readonly",
                "version": "0.1.0",
                "qma_api": "1.0.0",
                "desk": "trading",
                "entrypoint": "trading_readonly:activate",
                "tool_adapter_binding": {"desk": "trading", "role": "analyst"},
                "contributions": [],
            }
        )

    with pytest.raises(Exception, match="desk"):
        ToolAdapterRecord(
            adapter_id="trading-readonly:mcp2",
            metadata={"desk": "trading", "role": "analyst"},
        )


def test_role_grants_mission_narrows_subagent_leaf_blocks() -> None:
    registry = ToolRegistry()
    for tool_id, tags in (
        ("research:search", ()),
        ("research:spawn_delegation", ("delegation",)),
        ("research:memory_write", ("memory_write",)),
        ("research:summarize", ()),
    ):
        assert is_ok(
            registry.register(
                tool_id=tool_id,
                kind=ToolKind.PLUGIN,
                schema={"name": tool_id},
                acts=("read",),
                tags=tags,
            )
        )
    assert is_ok(
        registry.register_toolset(
            ToolsetRecord(
                toolset_id="research:default",
                version="1",
                tool_ids=(
                    "research:search",
                    "research:spawn_delegation",
                    "research:memory_write",
                    "research:summarize",
                ),
            )
        )
    )

    widened = registry.resolve_effective_tool_ids(
        role_toolset_id="research:default",
        mission_tool_ids=("research:search", "research:invented"),
    )
    assert is_refusal(widened)

    mission_ok = registry.resolve_effective_tool_ids(
        role_toolset_id="research:default",
        mission_tool_ids=("research:search", "research:spawn_delegation", "research:memory_write"),
    )
    assert is_ok(mission_ok)
    assert mission_ok.value == frozenset(
        {
            "research:search",
            "research:spawn_delegation",
            "research:memory_write",
        }
    )

    leaf = registry.resolve_effective_tool_ids(
        role_toolset_id="research:default",
        mission_tool_ids=("research:search", "research:spawn_delegation", "research:memory_write"),
        parent_tool_ids=mission_ok.value,
        is_subagent=True,
    )
    assert is_ok(leaf)
    assert leaf.value == frozenset({"research:search"})
    assert "research:spawn_delegation" not in leaf.value
    assert "research:memory_write" not in leaf.value


def test_lowest_capable_rung_wins_and_skill_grants_nothing() -> None:
    assert skill_grants_tool_or_capability() is False
    assert len(CAPABILITY_LADDER) == 6

    registry = ToolRegistry()
    assert is_ok(
        registry.register(
            tool_id="analysis:api_read",
            kind=ToolKind.NATIVE,
            acts=("fetch_bars",),
            schema={"name": "api_read"},
        )
    )
    assert is_ok(
        registry.register(
            tool_id="analysis:cli_read",
            kind=ToolKind.CLI,
            acts=("fetch_bars",),
            schema={"name": "cli_read"},
        )
    )
    assert is_ok(
        registry.register(
            tool_id="analysis:browser_read",
            kind=ToolKind.BROWSER,
            acts=("fetch_bars",),
            schema={"name": "browser_read"},
        )
    )
    selected = registry.select_for_act("fetch_bars")
    assert is_ok(selected)
    assert selected.value.tool_id == "analysis:api_read"
    assert selected.value.capability_rung is CapabilityRung.API_OR_STRUCTURED_TOOL

    candidates = [tool for tool in registry.catalog() if "fetch_bars" in tool.acts]
    assert select_lowest_capable(candidates) is selected.value

    assert is_ok(
        registry.register_toolset(
            ToolsetRecord(
                toolset_id="analysis:base",
                version="1",
                tool_ids=("analysis:api_read", "analysis:cli_read"),
            )
        )
    )
    skill = Skill(
        qualified_id="analysis:chart_notes",
        version="1",
        summary="knowledge only",
        body="how to read charts",
    )
    assert skill.to_payload()["grants_capability"] is False
    resolved = registry.resolve_effective_tool_ids(
        role_toolset_id="analysis:base",
        appended_skills=(skill,),
    )
    assert is_ok(resolved)
    assert resolved.value == frozenset({"analysis:api_read", "analysis:cli_read"})
    # Skill did not inject any extra tool id.
    assert "analysis:chart_notes" not in resolved.value


def test_computer_use_fails_check_fn_without_desktop_gap_0070_excluded() -> None:
    envs = ExecutionEnvironmentRegistry()
    registry = ToolRegistry(environments=envs)
    assert GAP_0070_DESKTOP_EXCLUSION["gap"] == "GAP-0070"
    assert GAP_0070_DESKTOP_EXCLUSION["status"] == "deferred"

    assert is_ok(
        registry.register(
            tool_id="computer:click",
            kind=ToolKind.COMPUTER_USE,
            schema={"name": "click"},
            acts=("click",),
        )
    )
    tool = registry.get("computer:click")
    assert tool is not None
    assert tool.requires_environment_kind == "desktop"
    assert tool.is_available() is False
    assert registry.model_visible_schemas() == ()
    assert registry.snapshot()["desktop_registered"] is False

    # Registering desktop makes the same tool available (still no VPS provisioned here).
    assert is_ok(
        envs.register(
            ExecutionEnvironmentKind.DESKTOP,
            _EnvStub(),
            declaration=ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DESKTOP,
                provider_ref="local-desktop",
            ),
        )
    )
    assert tool.is_available() is True
    visible = registry.model_visible_schemas()
    assert len(visible) == 1
    assert visible[0]["tool_id"] == "computer:click"


def test_trading_desk_refuses_execution_tool_ar_q18() -> None:
    registry = ToolRegistry()
    refused = registry.register(
        tool_id="trading-readonly:place_order",
        kind=ToolKind.PLUGIN,
        schema={"name": "place_order"},
        acts=("order",),
        money_path_act="order",
    )
    assert is_refusal(refused)
    assert ProhibitedMoneyPathTool.matches(refused)
    assert refused.context["tool_id"] == "trading-readonly:place_order"
    assert refused.context["matched_act"] == "order"
    # Read-only market data still registers.
    assert is_ok(
        registry.register(
            tool_id="trading-readonly:positions",
            kind=ToolKind.PLUGIN,
            schema={"name": "positions"},
            acts=("read_positions",),
        )
    )
    assert registry.is_available("trading-readonly:positions") is True


def test_record_rejects_non_qualified_ids() -> None:
    with pytest.raises(Exception, match="fully-qualified"):
        ToolRecord(
            tool_id="bare",
            kind=ToolKind.NATIVE,
            capability_rung=CapabilityRung.API_OR_STRUCTURED_TOOL,
        )
    with pytest.raises(Exception, match="fully-qualified"):
        ToolsetRecord(toolset_id="pack:set", version="1", tool_ids=("bare",))
