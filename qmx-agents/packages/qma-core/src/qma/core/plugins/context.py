"""PluginContext protocol — cardinality-typed registration methods (CT-42; AD-1).

Implemented by ``qma-daemon``. Plugin authors import this protocol from
``qma-core`` and never from ``qma-daemon``. The context exposes credential
reference strings only — never a resolved secret value (DEC-0323).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol, runtime_checkable

from qma.core.plugins.credential import CredentialRef
from qma.core.plugins.hooks import HookEvent, HookResult
from qma.core.ports.compute import ComputeProvider
from qma.core.ports.context import ContextCompiler
from qma.core.ports.execution import ExecutionEnvironment
from qma.core.ports.knowledge import KnowledgeSource
from qma.core.ports.memory import MemoryProvider
from qma.core.ports.model import ModelDeployment
from qma.core.ports.tools import ToolAdapter

__all__ = [
    "Disposer",
    "HookHandler",
    "PluginContext",
]

Disposer = Callable[[], None]
HookHandler = Callable[[HookEvent], HookResult]


@runtime_checkable
class PluginContext(Protocol):
    """Scoped registration surface returned to a plugin at activation.

    Each registration method returns a disposer pushed onto the per-plugin async
    exit stack so unload closes contributions LIFO.
    """

    @property
    def plugin_id(self) -> str:
        """Fully-qualified plugin id owning this scoped context."""
        ...

    def credential_ref(self, name: str) -> CredentialRef:
        """Return a credential *reference* string — never a resolved secret."""
        ...

    # --- singleton ports -------------------------------------------------
    def register_memory_provider(self, desk: str, provider: MemoryProvider) -> Disposer:
        """Bind MemoryProvider for ``desk`` (singleton scope key ``desk``)."""
        ...

    def register_knowledge_source(self, source_id: str, source: KnowledgeSource) -> Disposer:
        """Bind KnowledgeSource for ``source_id``."""
        ...

    def register_execution_environment(
        self, kind: str, environment: ExecutionEnvironment
    ) -> Disposer:
        """Bind ExecutionEnvironment for ``kind``."""
        ...

    def register_compute_provider(self, kind: str, provider: ComputeProvider) -> Disposer:
        """Bind ComputeProvider for ``kind``."""
        ...

    def register_context_compiler(self, compiler: ContextCompiler) -> Disposer:
        """Replace the daemon's default ContextCompiler (per-daemon singleton)."""
        ...

    # --- multi contribution points ---------------------------------------
    def register_tool(self, local_id: str, tool: Mapping[str, object]) -> Disposer:
        """Register multi ``tool`` as ``<plugin_id>:<local_id>``."""
        ...

    def register_tool_adapter(self, local_id: str, adapter: ToolAdapter) -> Disposer:
        """Register multi ``tool_adapter`` as ``<plugin_id>:<local_id>``."""
        ...

    def register_hook(self, local_id: str, handler: HookHandler) -> Disposer:
        """Register multi ``hook`` as ``<plugin_id>:<local_id>``."""
        ...

    def register_skill(self, local_id: str, skill: Mapping[str, object]) -> Disposer:
        """Register multi ``skill`` as ``<plugin_id>:<local_id>``."""
        ...

    def register_graph_template(self, local_id: str, template: Mapping[str, object]) -> Disposer:
        """Register multi ``graph_template`` as ``<plugin_id>:<local_id>``."""
        ...

    def register_model_deployment(self, local_id: str, deployment: ModelDeployment) -> Disposer:
        """Register multi ``model_deployment`` as ``<plugin_id>:<local_id>``."""
        ...

    def register_toolset(self, local_id: str, toolset: Mapping[str, object]) -> Disposer:
        """Register multi ``toolset`` as ``<plugin_id>:<local_id>``."""
        ...

    def register_worker_template(self, local_id: str, template: Mapping[str, object]) -> Disposer:
        """Register multi ``worker_template`` as ``<plugin_id>:<local_id>``."""
        ...
