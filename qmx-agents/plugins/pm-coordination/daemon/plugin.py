"""pm-coordination daemon half — PluginContext registrations (FR-Q71)."""

from __future__ import annotations

from qma.core.plugins import (
    HookEvent,
    HookResult,
    PluginContext,
    graph_template_payload,
    skill_payload,
)
from qma.core.plugins.hooks import build_hook_result
from qma.core.vocabulary.enums import HookResultDecision

_PLUGIN_ID = "pm-coordination"


def _review(_event: HookEvent) -> HookResult:
    return build_hook_result(HookResultDecision.OBSERVE, reason="pm review")


def activate(ctx: PluginContext) -> None:
    ctx.register_tool(
        "status",
        {
            "name": "status",
            "acts": ("collect_status",),
            "kind": "plugin",
            "tags": ("coordination",),
        },
    )
    ctx.register_hook("review", _review)
    ctx.register_skill(
        "coordinate",
        skill_payload(
            _PLUGIN_ID,
            "coordinate",
            summary="Coordinate desk status without money-path authority",
        ),
    )
    ctx.register_graph_template(
        "standup",
        graph_template_payload(
            _PLUGIN_ID,
            "standup",
            nodes=(
                {"id": "collect", "kind": "task"},
                {"id": "summarize", "kind": "task"},
            ),
            edges=({"from": "collect", "to": "summarize"},),
        ),
    )
    ctx.register_worker_template(
        "coordinator",
        {
            "role_ref": "product_manager",
            "toolset_ref": f"{_PLUGIN_ID}:status",
            "model_class": "WORKHORSE_GENERAL",
            "environment_ref": "env:docker",
            "compute_requirement": {"cpus": 1},
            "permission_set": ["read"],
            "image": "qma-worker:isolated",
        },
    )
