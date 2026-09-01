"""Closed-and-addable hook registry and HookResult (AD-10, AD-11; FR-Q30/FR-Q31)."""

from __future__ import annotations

from qma.daemon.hooks.registry import (
    AGENT_REACHABLE_WRITE_VERBS,
    BYPASS_WRITE_PATHS,
    DAEMON_OWNED_HOOK_VERBS,
    PHASE_LESS_CONTROLS,
    HookRegistry,
    HookRegistryEntry,
    PrimitiveInvocation,
    assert_no_bypass_write_path,
    default_empty_hook_result,
    event_names_for_verb,
    resolve_parallel_hook_results,
)

__all__ = [
    "AGENT_REACHABLE_WRITE_VERBS",
    "BYPASS_WRITE_PATHS",
    "DAEMON_OWNED_HOOK_VERBS",
    "PHASE_LESS_CONTROLS",
    "HookRegistry",
    "HookRegistryEntry",
    "PrimitiveInvocation",
    "assert_no_bypass_write_path",
    "default_empty_hook_result",
    "event_names_for_verb",
    "resolve_parallel_hook_results",
]
