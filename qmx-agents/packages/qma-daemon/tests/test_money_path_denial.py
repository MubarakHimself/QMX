"""Story 44.5 — Tool Registry act-level money-path denial (FR-Q42)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest
from qma.core.barriers.capability import CapabilityRung
from qma.core.barriers.money_path import (
    MONEY_PATH_DENIAL_NOT_LIFTABLE_BY,
    MONEY_PATH_DENIED_ACTS,
    QMA_MINTED_MONEY_PATH_VALUES,
    QMA_MINTED_PROMOTION_COMMAND,
    MoneyPathDeniedAct,
)
from qma.core.barriers.parent_surfaces import ProhibitedRecordFamily
from qma.core.ports.permissions import PermissionMode, PermissionPolicy
from qma.core.ports.tools import ToolAdapterRecord, ToolKind, ToolRecord
from qma.core.refusals import ProhibitedMoneyPathTool
from qma.daemon.capabilities import PermissionPolicyEnforcer
from qma.daemon.hooks import HookRegistry
from qma.daemon.tools import DEV_ZONE, ToolRegistry
from qma.daemon.tools.parent_writes import MONEY_PATH_VALUE_FIELDS
from qmf.core import is_ok, is_refusal

DENIED_VERBS: tuple[str, ...] = tuple(act.value for act in MoneyPathDeniedAct)


def _tool(
    tool_id: str,
    *,
    kind: ToolKind = ToolKind.NATIVE,
    acts: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
    money_path_act: str | None = None,
) -> ToolRecord:
    return ToolRecord(
        tool_id=tool_id,
        kind=kind,
        capability_rung=CapabilityRung.API_OR_STRUCTURED_TOOL,
        schema={"name": tool_id.rsplit(":", 1)[-1]},
        acts=frozenset(acts),
        tags=frozenset(tags),
        money_path_act=money_path_act,
    )


@pytest.mark.parametrize("act", DENIED_VERBS)
def test_registry_refuses_enumerated_acts_before_check_fn(act: str) -> None:
    registry = ToolRegistry()
    calls: list[int] = []

    def check() -> bool:
        calls.append(1)
        return True

    refused = registry.register(
        tool_id=f"trading:{act}",
        kind=ToolKind.PLUGIN,
        schema={"name": act},
        acts=(act,),
        check_fn=check,
    )
    assert is_refusal(refused)
    assert ProhibitedMoneyPathTool.matches(refused)
    assert refused.context["tool_id"] == f"trading:{act}"
    assert refused.context["matched_act"] == act
    assert refused.context["plugin_id"] == "trading"
    assert calls == []
    assert registry.get(f"trading:{act}") is None


@pytest.mark.parametrize("kind", list(ToolKind))
def test_every_tool_kind_is_denied_including_paper_only(kind: ToolKind) -> None:
    registry = ToolRegistry()
    tool_id = f"trading:{kind.value}_paper_order"
    refused = registry.register(
        tool_id=tool_id,
        kind=kind,
        schema={"name": "paper_place_order"},
        acts=("submit_order",),
        tags=("paper_only", "paper"),
        check_fn=lambda: True,
    )
    assert is_refusal(refused)
    assert ProhibitedMoneyPathTool.matches(refused)
    assert refused.context["matched_act"] == "submit_order"
    assert registry.get(tool_id) is None


def test_paper_prefixed_family_act_is_still_denied() -> None:
    registry = ToolRegistry()
    refused = registry.register(
        tool_id="trading:paper_cancel",
        kind=ToolKind.CLI,
        acts=("paper_only_cancel_order",),
    )
    assert is_refusal(refused)
    assert refused.context["matched_act"] == "cancel_order"


def test_mcp_adapter_refuses_whole_server_on_one_denied_tool() -> None:
    registry = ToolRegistry()
    good = _tool("trading-readonly:positions", acts=("read_positions",), kind=ToolKind.MCP_ADAPTER)
    bad = _tool("trading-readonly:place_order", acts=("submit_order",), kind=ToolKind.MCP_ADAPTER)
    adapter = ToolAdapterRecord(
        adapter_id="trading-readonly:mcp-exec",
        advertised_tool_ids=("trading-readonly:positions", "trading-readonly:place_order"),
    )
    refused = registry.register_mcp_server(adapter, (good, bad))
    assert is_refusal(refused)
    assert ProhibitedMoneyPathTool.matches(refused)
    assert refused.context["tool_id"] == "trading-readonly:place_order"
    assert refused.context["matched_act"] == "submit_order"
    assert registry.get_adapter("trading-readonly:mcp-exec") is None
    # Partial bind must not occur: neither advertised tool nor the adapter is stored.
    assert registry.get("trading-readonly:place_order") is None
    assert registry.get("trading-readonly:positions") is None


def test_mcp_adapter_advertised_acts_refuse_the_server() -> None:
    registry = ToolRegistry()
    adapter = ToolAdapterRecord(
        adapter_id="trading-readonly:mcp-acts",
        advertised_tool_ids=("trading-readonly:hedge",),
        advertised_acts=("hedge_position",),
    )
    refused = registry.register_adapter(adapter)
    assert is_refusal(refused)
    assert ProhibitedMoneyPathTool.matches(refused)
    assert refused.context["matched_act"] == "hedge_position"
    assert registry.get_adapter("trading-readonly:mcp-acts") is None


def test_mcp_metadata_advertised_tools_refuse_the_server() -> None:
    registry = ToolRegistry()
    adapter = ToolAdapterRecord(
        adapter_id="trading-readonly:mcp-meta",
        metadata={
            "advertised_tools": [
                {"tool_id": "trading-readonly:size", "acts": ("mint_sizing_decision",)},
            ]
        },
    )
    refused = registry.register_adapter(adapter)
    assert is_refusal(refused)
    assert refused.context["matched_act"] == "mint_sizing_decision"
    assert registry.get_adapter("trading-readonly:mcp-meta") is None


def test_role_mission_hook_toolset_check_fn_cannot_lift_denial() -> None:
    registry = ToolRegistry()
    assert {
        "role",
        "mission",
        "hook",
        "toolset",
        "tool_adapter",
        "check_fn",
    } <= MONEY_PATH_DENIAL_NOT_LIFTABLE_BY
    for via in ("role", "mission", "hook", "toolset", "tool_adapter", "check_fn"):
        refused = registry.resolve_permission(
            "submit_order",
            tool_id="trading:place_order",
            plugin_id="trading-readonly",
            via=via,
            check_fn=lambda: True,
        )
        assert is_refusal(refused)
        assert ProhibitedMoneyPathTool.matches(refused)
        assert refused.context["via"] == via
        assert refused.context["matched_act"] == "submit_order"

    selected = registry.select_for_act("open_position")
    assert is_refusal(selected)
    assert ProhibitedMoneyPathTool.matches(selected)


def test_enforcer_refuses_money_path_act_without_dispatching_hooks() -> None:
    hooks = HookRegistry()
    enforcer = PermissionPolicyEnforcer(hooks, mode=PermissionMode.PERMISSIVE)
    enforcer.register_role_policy(
        PermissionPolicy(
            role="Trader",
            permissions=frozenset({"submit_order", "tool.read"}),
        )
    )
    refused = enforcer.enforce(
        "before_tool",
        role="Trader",
        required_permission="submit_order",
        payload={"act": "submit_order", "tool_id": "trading:place_order"},
    )
    assert is_refusal(refused)
    assert ProhibitedMoneyPathTool.matches(refused)
    assert refused.context["matched_act"] == "submit_order"


def test_read_and_calculate_surface_refuses_money_path_writes() -> None:
    registry = ToolRegistry()
    for family in ProhibitedRecordFamily:
        refused = registry.attempt_money_path_write(family)
        assert is_refusal(refused)
        assert refused.context["family"] == family.value
    zone = registry.attempt_zone_transition()
    assert is_refusal(zone)
    assert zone.context["field"] == "zone_transition"


def test_sole_permitted_write_is_dev_zone_candidate() -> None:
    registry = ToolRegistry()
    written = registry.write_dev_zone_candidate(
        {"note": "research candidate"},
        origin="qma",
        summary="content-addressed dev-zone candidate",
    )
    assert is_ok(written)
    assert written.value.zone == DEV_ZONE
    assert written.value.origin == "qma"
    assert written.value.payload_fp1.startswith("fp1:")
    assert written.value.stable_id.startswith("fp1:")

    live = registry.write_dev_zone_candidate({"note": "nope"}, zone="live")
    assert is_refusal(live)
    assert live.context["field"] == "zone_transition"

    minted = registry.write_dev_zone_candidate({"sizing": "1R"})
    assert is_refusal(minted)
    assert minted.context["field"] == "payload"
    fields = minted.context["fields"]
    assert isinstance(fields, (list, tuple))
    assert "sizing" in fields


def test_story_mints_no_promotion_command_or_money_path_value() -> None:
    registry = ToolRegistry()
    assert registry.minted_promotion_command is None
    assert QMA_MINTED_PROMOTION_COMMAND is None
    assert QMA_MINTED_MONEY_PATH_VALUES == ()
    assert frozenset(MoneyPathDeniedAct) == MONEY_PATH_DENIED_ACTS
    source = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "tools"
    text = (source / "parent_writes.py").read_text(encoding="utf-8")
    assert "authorize_live_promotion" not in text
    assert "PromotionCard" not in text
    assert "qmf.registry.promotion" not in text
    for field in MONEY_PATH_VALUE_FIELDS:
        assert isinstance(field, str)


def test_read_only_trading_tools_still_register() -> None:
    registry = ToolRegistry()
    assert is_ok(
        registry.register(
            tool_id="trading-readonly:positions",
            kind=ToolKind.PLUGIN,
            acts=("read_positions",),
        )
    )
    assert is_ok(
        registry.register(
            tool_id="trading-readonly:risk_calc",
            kind=ToolKind.NATIVE,
            acts=("risk_calculate",),
        )
    )
    assert registry.is_available("trading-readonly:positions") is True
    snapshot: Mapping[str, object] = registry.snapshot()
    assert snapshot["minted_promotion_command"] is None
    assert snapshot["permitted_parent_write"] == ["qmf-registry", "dev_zone_candidate_write"]
