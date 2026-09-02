"""dev-factory daemon half — PluginContext registrations (FR-Q71)."""

from __future__ import annotations

from qma.core.plugins import HookEvent, HookResult, PluginContext, skill_payload
from qma.core.plugins.hooks import build_hook_result
from qma.core.vocabulary.enums import HookResultDecision

_PLUGIN_ID = "dev-factory"


def _lint(_event: HookEvent) -> HookResult:
    return build_hook_result(HookResultDecision.OBSERVE, reason="dev-factory lint")


def activate(ctx: PluginContext) -> None:
    ctx.register_tool(
        "plan",
        {
            "name": "plan",
            "acts": ("plan_change",),
            "kind": "plugin",
            "tags": ("factory",),
        },
    )
    ctx.register_hook("lint", _lint)
    ctx.register_skill(
        "factory",
        skill_payload(
            _PLUGIN_ID,
            "factory",
            summary="Plan a factory change without touching the money path",
        ),
    )
    ctx.register_worker_template(
        "factory-worker",
        {
            "role_ref": "developer",
            "toolset_ref": f"{_PLUGIN_ID}:factory-tools",
            "model_class": "CODING_HIGH",
            "environment_ref": "env:docker",
            "compute_requirement": {"cpus": 1},
            "permission_set": ["read"],
            "image": "qma-worker:isolated",
        },
    )
    ctx.register_toolset(
        "factory-tools",
        {
            "toolset_id": f"{_PLUGIN_ID}:factory-tools",
            "version": "0.1.0",
            "tool_ids": [f"{_PLUGIN_ID}:plan"],
        },
    )
