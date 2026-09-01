"""Control primitives — Graph Template, Loop, Skill, and the AD-14 runtime contract.

Definitions only. Runtime Loop node state and Task minting live in
``qma-daemon``; Mission Template registry and graph-engine selection remain
Deferred (GAP-0084, GAP-0086). Dialogue / RLM runtimes implement the shared
loop-and-state contract in the daemon (FR-Q52).
"""

from __future__ import annotations

from qma.core.control.primitives import (
    DAEMON_EVALUATED_NODE_KINDS,
    DEFERRED_GRAPH_EXCLUSIONS,
    ControlPrimitive,
    Skill,
    emits_task,
    holds_dispatch_lease,
    is_loop_kind,
    is_skill_distinct_from_loop,
    node_carries_ledger,
)
from qma.core.control.runtime import (
    ANALYSIS_NOTEBOOK_TOOL_ID,
    BACKGROUND_SESSION_TYPES,
    CLIENT_SESSION_AXIS,
    DEFERRED_RUNTIME_EXCLUSIONS,
    DIALOGUE_RUNTIME_DESKS,
    DURABLE_SESSION_AXES,
    HOSTED_NOTEBOOK_SERVICES,
    LOOP_AND_STATE_CONTRACT,
    LOOP_AND_STATE_SURFACES,
    RLM_DEPTH_CAP_REGISTRY_KEY,
    RLM_HOST_TRANSPORT,
    RLM_KERNEL_INTERPRETER,
    RLM_KERNEL_PLACEMENT,
    RLM_RUNTIME_DESK,
    available_execution_models,
    durable_session_payload,
    is_analysis_desk,
    is_rlm_runtime_in_scope,
    mint_durable_session,
    parse_session_attachment,
    select_execution_model,
)

__all__ = [
    "ANALYSIS_NOTEBOOK_TOOL_ID",
    "BACKGROUND_SESSION_TYPES",
    "CLIENT_SESSION_AXIS",
    "DAEMON_EVALUATED_NODE_KINDS",
    "DEFERRED_GRAPH_EXCLUSIONS",
    "DEFERRED_RUNTIME_EXCLUSIONS",
    "DIALOGUE_RUNTIME_DESKS",
    "DURABLE_SESSION_AXES",
    "HOSTED_NOTEBOOK_SERVICES",
    "LOOP_AND_STATE_CONTRACT",
    "LOOP_AND_STATE_SURFACES",
    "RLM_DEPTH_CAP_REGISTRY_KEY",
    "RLM_HOST_TRANSPORT",
    "RLM_KERNEL_INTERPRETER",
    "RLM_KERNEL_PLACEMENT",
    "RLM_RUNTIME_DESK",
    "ControlPrimitive",
    "Skill",
    "available_execution_models",
    "durable_session_payload",
    "emits_task",
    "holds_dispatch_lease",
    "is_analysis_desk",
    "is_loop_kind",
    "is_rlm_runtime_in_scope",
    "is_skill_distinct_from_loop",
    "mint_durable_session",
    "node_carries_ledger",
    "parse_session_attachment",
    "select_execution_model",
]
