"""trading-readonly daemon half — read-only desk contributions (FR-Q71).

No order, position, protection, sizing, binding, mode, control, zone-transition,
or promotion act is registered. Paper is an account role, not a sandbox.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.plugins import PluginContext, skill_payload

_PLUGIN_ID = "trading-readonly"
_ADAPTER_META: Mapping[str, object] = MappingProxyType({"kind": "mcp_readonly", "writes": False})


@dataclass(frozen=True, slots=True)
class ReadOnlyMarketAdapter:
    """MCP adapter contribution with no desk-and-role binding (AD-16)."""

    adapter_id: str = f"{_PLUGIN_ID}:readonly-mcp"
    metadata: Mapping[str, object] = _ADAPTER_META


def activate(ctx: PluginContext) -> None:
    ctx.register_tool(
        "positions",
        {
            "name": "positions",
            "acts": ("read_positions",),
            "kind": "mcp_adapter",
            "tags": ("read_only", "recorded_evidence"),
        },
    )
    ctx.register_tool(
        "market-data",
        {
            "name": "market-data",
            "acts": ("read_market_data",),
            "kind": "mcp_adapter",
            "tags": ("read_only", "recorded_evidence"),
        },
    )
    ctx.register_tool_adapter("readonly-mcp", ReadOnlyMarketAdapter())
    ctx.register_skill(
        "tape-read",
        skill_payload(
            _PLUGIN_ID,
            "tape-read",
            summary="Read recorded positions and market data; never write the money path",
        ),
    )
    ctx.register_toolset(
        "readonly-tools",
        {
            "toolset_id": f"{_PLUGIN_ID}:readonly-tools",
            "version": "0.1.0",
            "tool_ids": [
                f"{_PLUGIN_ID}:positions",
                f"{_PLUGIN_ID}:market-data",
            ],
        },
    )
