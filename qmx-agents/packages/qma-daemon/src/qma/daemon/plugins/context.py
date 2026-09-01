"""Daemon implementation of the qma-core PluginContext protocol (CT-42; AD-1).

In-memory registration only for this story — no durable write and no process
start. Plugins import the protocol from ``qma-core``; this module implements it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from qma.core.plugins.context import Disposer, HookHandler
from qma.core.plugins.credential import CredentialRef, parse_credential_ref
from qma.core.ports.cardinality import (
    HANDLE_KIND_CONTRIBUTION_POINTS,
    qualified_contribution_id,
    require_singleton_scope_key,
    validate_contribution_point,
)
from qma.core.ports.compute import ComputeProvider
from qma.core.ports.context import ContextCompiler
from qma.core.ports.execution import ExecutionEnvironment
from qma.core.ports.knowledge import KnowledgeSource
from qma.core.ports.memory import MemoryProvider
from qma.core.ports.model import ModelDeployment
from qma.core.ports.tools import ToolAdapter
from qma.core.vocabulary.handles import is_handle_kind_contribution_point

__all__ = ["DaemonPluginContext", "PluginContextError"]


class PluginContextError(ValueError):
    """Raised when a daemon-side registration violates cardinality law."""


class DaemonPluginContext:
    """Concrete ``PluginContext`` held by the daemon loader for one plugin scope."""

    def __init__(self, plugin_id: str) -> None:
        if not plugin_id or ":" in plugin_id:
            raise PluginContextError(f"invalid plugin_id {plugin_id!r}")
        self._plugin_id = plugin_id
        self._singletons: dict[tuple[str, str], object] = {}
        self._multis: dict[tuple[str, str], object] = {}
        self._credential_refs: dict[str, CredentialRef] = {}
        self._disposers: list[Disposer] = []
        self._context_compiler: ContextCompiler | None = None

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    def declare_credential_ref(self, name: str, ref: str) -> CredentialRef:
        """Record a credential reference string available to this plugin scope."""
        parsed = parse_credential_ref(ref)
        self._credential_refs[name] = parsed
        return parsed

    def credential_ref(self, name: str) -> CredentialRef:
        try:
            return self._credential_refs[name]
        except KeyError as exc:
            raise PluginContextError(
                f"no credential_ref named {name!r} in plugin {self._plugin_id!r}"
            ) from exc

    def _dispose_singleton(self, port: str, scope_value: str) -> Disposer:
        key = (port, scope_value)

        def dispose() -> None:
            self._singletons.pop(key, None)

        self._disposers.append(dispose)
        return dispose

    def _dispose_multi(self, point: str, qualified: str) -> Disposer:
        key = (point, qualified)

        def dispose() -> None:
            self._multis.pop(key, None)

        self._disposers.append(dispose)
        return dispose

    def _bind_singleton(
        self, port: str, scope_key: str | None, scope_value: str, value: object
    ) -> Disposer:
        require_singleton_scope_key(port, scope_key)
        if not scope_value:
            raise PluginContextError(f"singleton {port} requires a non-empty {scope_key} value")
        key = (port, scope_value)
        if key in self._singletons:
            raise PluginContextError(
                f"duplicate singleton binding for {port} key {scope_value!r} "
                f"in plugin {self._plugin_id!r}"
            )
        self._singletons[key] = value
        return self._dispose_singleton(port, scope_value)

    def register_handle_kind(self, kind: str) -> Disposer:
        """Trap: plugins never extend the closed handle-kind vocabulary."""
        raise PluginContextError(
            "handle kinds are a closed qma-core vocabulary; plugins may not "
            f"extend them with {kind!r} (AD-14; DEC-0313; FR-Q53)"
        )

    def _bind_multi(self, point: str, local_id: str, value: object) -> Disposer:
        if point in HANDLE_KIND_CONTRIBUTION_POINTS or is_handle_kind_contribution_point(point):
            raise PluginContextError(
                "handle kinds are a closed qma-core vocabulary; plugins may not "
                f"extend them with {point!r} (AD-14; DEC-0313; FR-Q53)"
            )
        validate_contribution_point(point)
        qualified = qualified_contribution_id(self._plugin_id, local_id)
        key = (point, qualified)
        if key in self._multis:
            raise PluginContextError(
                f"duplicate multi contribution {qualified!r} for point {point!r}"
            )
        self._multis[key] = value
        return self._dispose_multi(point, qualified)

    def register_memory_provider(self, desk: str, provider: MemoryProvider) -> Disposer:
        return self._bind_singleton("MemoryProvider", "desk", desk, provider)

    def register_knowledge_source(self, source_id: str, source: KnowledgeSource) -> Disposer:
        return self._bind_singleton("KnowledgeSource", "source_id", source_id, source)

    def register_execution_environment(
        self, kind: str, environment: ExecutionEnvironment
    ) -> Disposer:
        return self._bind_singleton("ExecutionEnvironment", "kind", kind, environment)

    def register_compute_provider(self, kind: str, provider: ComputeProvider) -> Disposer:
        return self._bind_singleton("ComputeProvider", "kind", kind, provider)

    def register_context_compiler(self, compiler: ContextCompiler) -> Disposer:
        require_singleton_scope_key("ContextCompiler", "daemon")
        if self._context_compiler is not None:
            raise PluginContextError(f"ContextCompiler already bound by plugin {self._plugin_id!r}")
        self._context_compiler = compiler
        self._singletons[("ContextCompiler", "daemon")] = compiler

        def dispose() -> None:
            self._context_compiler = None
            self._singletons.pop(("ContextCompiler", "daemon"), None)

        self._disposers.append(dispose)
        return dispose

    def register_tool(self, local_id: str, tool: Mapping[str, object]) -> Disposer:
        return self._bind_multi("tool", local_id, dict(tool))

    def register_tool_adapter(self, local_id: str, adapter: ToolAdapter) -> Disposer:
        return self._bind_multi("tool_adapter", local_id, adapter)

    def register_hook(self, local_id: str, handler: HookHandler) -> Disposer:
        return self._bind_multi("hook", local_id, handler)

    def register_skill(self, local_id: str, skill: Mapping[str, object]) -> Disposer:
        return self._bind_multi("skill", local_id, dict(skill))

    def register_graph_template(self, local_id: str, template: Mapping[str, object]) -> Disposer:
        return self._bind_multi("graph_template", local_id, dict(template))

    def register_model_deployment(self, local_id: str, deployment: ModelDeployment) -> Disposer:
        return self._bind_multi("model_deployment", local_id, deployment)

    def register_toolset(self, local_id: str, toolset: Mapping[str, object]) -> Disposer:
        return self._bind_multi("toolset", local_id, dict(toolset))

    def register_worker_template(self, local_id: str, template: Mapping[str, object]) -> Disposer:
        return self._bind_multi("worker_template", local_id, dict(template))

    def dispose_all(self) -> None:
        """LIFO dispose every registration in this plugin scope."""
        while self._disposers:
            disposer = self._disposers.pop()
            disposer()

    def snapshot(self) -> dict[str, Any]:
        """Test/inspection helper — no durable write."""
        return {
            "plugin_id": self._plugin_id,
            "singletons": dict(self._singletons),
            "multis": dict(self._multis),
            "credential_refs": dict(self._credential_refs),
            "context_compiler_bound": self._context_compiler is not None,
        }
