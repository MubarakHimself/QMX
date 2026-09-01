"""Tool Registry, capability ladder, money-path deny-list (AD-16; FR-Q41).

Registration validators import the code-declared ladder and deny-list from
``qma.core.barriers`` (FR-Q09; DEC-0315). The runtime registry lives here.
"""

from __future__ import annotations

from qma.core.barriers import (
    CAPABILITY_LADDER,
    MONEY_PATH_DENIED_ACTS,
    MONEY_PATH_DENY_LIST,
    CapabilityRung,
    MoneyPathAct,
    MoneyPathDeniedAct,
    assert_deny_list_not_widenable,
    assert_ladder_is_code_declared,
    is_money_path_act_denied,
    match_money_path_act,
    refuse_money_path_registration,
)
from qma.core.ports.tools import (
    LEAF_BLOCKED_TOOL_TAGS,
    TOOL_ADAPTER_WRITE_COMMAND,
    TOOL_KIND_DEFAULT_RUNG,
    TOOL_KINDS,
    ToolAdapterBinding,
    ToolAdapterRecord,
    ToolKind,
    ToolRecord,
    ToolsetRecord,
    default_rung_for_kind,
    narrow_toolset_ids,
    select_lowest_capable,
    skill_grants_tool_or_capability,
    subagent_inherited_tool_ids,
    write_tool_adapter_binding,
)
from qma.daemon.tools.parent_writes import (
    CANDIDATE_KIND,
    DEV_ZONE,
    DevZoneCandidate,
    ParentSurfaceGate,
)
from qma.daemon.tools.registry import GAP_0070_DESKTOP_EXCLUSION, ToolRegistry

__all__ = [
    "CANDIDATE_KIND",
    "CAPABILITY_LADDER",
    "DEV_ZONE",
    "GAP_0070_DESKTOP_EXCLUSION",
    "LEAF_BLOCKED_TOOL_TAGS",
    "MONEY_PATH_DENIED_ACTS",
    "MONEY_PATH_DENY_LIST",
    "TOOL_ADAPTER_WRITE_COMMAND",
    "TOOL_KINDS",
    "TOOL_KIND_DEFAULT_RUNG",
    "CapabilityRung",
    "DevZoneCandidate",
    "MoneyPathAct",
    "MoneyPathDeniedAct",
    "ParentSurfaceGate",
    "ToolAdapterBinding",
    "ToolAdapterRecord",
    "ToolKind",
    "ToolRecord",
    "ToolRegistry",
    "ToolsetRecord",
    "assert_deny_list_not_widenable",
    "assert_ladder_is_code_declared",
    "default_rung_for_kind",
    "is_money_path_act_denied",
    "match_money_path_act",
    "narrow_toolset_ids",
    "refuse_money_path_registration",
    "select_lowest_capable",
    "skill_grants_tool_or_capability",
    "subagent_inherited_tool_ids",
    "write_tool_adapter_binding",
]
