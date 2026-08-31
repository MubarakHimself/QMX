"""ToolAdapter port — multi contribution ``tool_adapter`` (AD-1, AD-16)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["ToolAdapter"]


@runtime_checkable
class ToolAdapter(Protocol):
    """Definitions-only ToolAdapter seam; keyed ``<plugin_id>:<local_id>``.

    Cardinality: multi (see ``PORT_CONTRACTS``).
    """
