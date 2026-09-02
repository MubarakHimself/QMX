"""Daemon implementation of the qma-core PluginContext protocol (CT-42; AD-1).

In-memory registration only for this story — no durable write and no process
start. Plugins import the protocol from ``qma-core``; this module implements it.
Each registration returns a disposer pushed onto the per-plugin exit stack.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from qma.core.barriers.money_path import (
    is_money_path_act_denied,
    match_money_path_act,
)
from qma.core.barriers.reachability import (
    forbidden_reach_token_in_contribution,
    is_forbidden_model_adapter,
    refuse_forbidden_model_adapter,
    validate_execution_environment_declaration,
)
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
from qma.core.ports.execution import ExecutionEnvironment, ExecutionEnvironmentDeclaration
from qma.core.ports.knowledge import KnowledgeSource
from qma.core.ports.memory import MemoryProvider
from qma.core.ports.model import DeploymentRecord, ModelDeployment
from qma.core.ports.tools import ToolAdapter
from qma.core.vocabulary.handles import is_handle_kind_contribution_point
from qma.daemon.plugins.exit_stack import PluginExitStack
from qmf.core import is_ok

__all__ = ["DaemonPluginContext", "PluginContextError"]


class PluginContextError(ValueError):
    """Raised when a daemon-side registration violates cardinality law."""


def _tool_act_tokens(tool: Mapping[str, object]) -> tuple[str, ...]:
    tokens: list[str] = []
    money = tool.get("money_path_act")
    if isinstance(money, str) and money:
        tokens.append(money)
    acts_raw = tool.get("acts", ())
    if isinstance(acts_raw, str) and acts_raw:
        tokens.append(acts_raw)
    elif isinstance(acts_raw, Sequence) and not isinstance(acts_raw, (str, bytes)):
        for item in cast(Sequence[object], acts_raw):
            if isinstance(item, str) and item:
                tokens.append(item)
    name = tool.get("name")
    if isinstance(name, str) and name:
        tokens.append(name)
    return tuple(tokens)


class DaemonPluginContext:
    """Concrete ``PluginContext`` held by the daemon loader for one plugin scope."""

    def __init__(
        self,
        plugin_id: str,
        *,
        exit_stack: PluginExitStack | None = None,
    ) -> None:
        if not plugin_id or ":" in plugin_id:
            raise PluginContextError(f"invalid plugin_id {plugin_id!r}")
        self._plugin_id = plugin_id
        self._exit_stack = exit_stack if exit_stack is not None else PluginExitStack(plugin_id)
        self._singletons: dict[tuple[str, str], object] = {}
        self._multis: dict[tuple[str, str], object] = {}
        self._credential_refs: dict[str, CredentialRef] = {}
        self._context_compiler: ContextCompiler | None = None

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def exit_stack(self) -> PluginExitStack:
        return self._exit_stack

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

    def _push(self, disposer: Disposer) -> Disposer:
        return self._exit_stack.push(disposer)

    def _dispose_singleton(self, port: str, scope_value: str) -> Disposer:
        key = (port, scope_value)

        def dispose() -> None:
            self._singletons.pop(key, None)

        return self._push(dispose)

    def _dispose_multi(self, point: str, qualified: str) -> Disposer:
        key = (point, qualified)

        def dispose() -> None:
            self._multis.pop(key, None)

        return self._push(dispose)

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
        if isinstance(environment, ExecutionEnvironmentDeclaration):
            checked = validate_execution_environment_declaration(environment)
            if not is_ok(checked):
                raise PluginContextError(
                    "reachability barrier refused ExecutionEnvironment "
                    f"{kind!r} for plugin {self._plugin_id!r}: {checked}"
                )
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

        return self._push(dispose)

    def register_tool(self, local_id: str, tool: Mapping[str, object]) -> Disposer:
        for act in _tool_act_tokens(tool):
            if is_money_path_act_denied(act):
                matched = match_money_path_act(act) or act
                raise PluginContextError(
                    "money-path act refused at plugin tool registration "
                    f"(plugin_id={self._plugin_id!r}, local_id={local_id!r}, "
                    f"matched_act={matched!r})"
                )
        reach = forbidden_reach_token_in_contribution(tool)
        if reach is not None:
            raise PluginContextError(
                "reachability barrier refused plugin tool registration "
                f"(plugin_id={self._plugin_id!r}, local_id={local_id!r}, "
                f"matched={reach!r})"
            )
        return self._bind_multi("tool", local_id, dict(tool))

    def register_tool_adapter(self, local_id: str, adapter: ToolAdapter) -> Disposer:
        metadata: Mapping[str, object] = {}
        raw_meta = getattr(adapter, "metadata", None)
        if isinstance(raw_meta, Mapping):
            metadata = cast(Mapping[str, object], raw_meta)
        for forbidden in ("desk", "role", "desk_and_role", "binding"):
            if forbidden in metadata:
                raise PluginContextError(
                    f"manifest for {self._plugin_id!r} declares operator-assigned field "
                    f"'tool_adapter_binding' ({forbidden})"
                )
        return self._bind_multi("tool_adapter", local_id, adapter)

    def register_hook(self, local_id: str, handler: HookHandler) -> Disposer:
        return self._bind_multi("hook", local_id, handler)

    def register_skill(self, local_id: str, skill: Mapping[str, object]) -> Disposer:
        return self._bind_multi("skill", local_id, dict(skill))

    def register_graph_template(self, local_id: str, template: Mapping[str, object]) -> Disposer:
        return self._bind_multi("graph_template", local_id, dict(template))

    def register_model_deployment(self, local_id: str, deployment: ModelDeployment) -> Disposer:
        family = getattr(deployment, "model_family", None)
        if family is not None:
            raise PluginContextError(
                f"manifest for {self._plugin_id!r} declares operator-assigned field 'model_family'"
            )
        adapter = getattr(deployment, "adapter", None)
        if isinstance(adapter, str) and is_forbidden_model_adapter(adapter):
            refused = refuse_forbidden_model_adapter(adapter)
            detail = (
                refused.context.get("reason", "openrouter_forbidden")
                if refused
                else ("openrouter_forbidden")
            )
            raise PluginContextError(
                f"OpenRouter is not a QMA path; refused model_deployment "
                f"{self._plugin_id!r}:{local_id} ({detail})"
            )
        if isinstance(deployment, DeploymentRecord) and deployment.model_family is not None:
            raise PluginContextError(
                f"manifest for {self._plugin_id!r} declares operator-assigned field 'model_family'"
            )
        return self._bind_multi("model_deployment", local_id, deployment)

    def register_toolset(self, local_id: str, toolset: Mapping[str, object]) -> Disposer:
        return self._bind_multi("toolset", local_id, dict(toolset))

    def register_worker_template(self, local_id: str, template: Mapping[str, object]) -> Disposer:
        reach = forbidden_reach_token_in_contribution(template)
        if reach is not None:
            raise PluginContextError(
                "reachability barrier refused worker_template "
                f"{self._plugin_id!r}:{local_id} (matched={reach!r})"
            )
        return self._bind_multi("worker_template", local_id, dict(template))

    def dispose_all(self) -> None:
        """LIFO dispose every registration in this plugin scope."""
        self._exit_stack.close()

    def snapshot(self) -> dict[str, Any]:
        """Test/inspection helper — no durable write."""
        return {
            "plugin_id": self._plugin_id,
            "singletons": dict(self._singletons),
            "multis": dict(self._multis),
            "credential_refs": dict(self._credential_refs),
            "context_compiler_bound": self._context_compiler is not None,
            "exit_stack_depth": self._exit_stack.depth,
            "exit_stack_closed": self._exit_stack.closed,
        }
