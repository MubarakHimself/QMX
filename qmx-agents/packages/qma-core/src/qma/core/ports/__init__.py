"""Seven runtime ports defined here and implemented by qma-daemon (AD-1; DEC-0300).

Exactly: MemoryProvider, ModelDeployment, ExecutionEnvironment, KnowledgeSource,
ToolAdapter, ComputeProvider, ContextCompiler. Each declares cardinality; every
singleton declares an explicit scope key.
"""

from __future__ import annotations

from qma.core.ports.cardinality import (
    CONTEXT_COMPILER_SCOPE_KEY,
    MULTI_CONTRIBUTION_POINTS,
    PORT_CONTRACT_BY_NAME,
    PORT_CONTRACTS,
    RETIRED_CONTRIBUTION_POINTS,
    Cardinality,
    PortContract,
    PortError,
    has_qma_wire_schema,
    qualified_contribution_id,
    require_singleton_scope_key,
    validate_contribution_point,
    validate_multi_contribution_key,
)
from qma.core.ports.compute import ComputeProvider
from qma.core.ports.context import ContextCompiler
from qma.core.ports.execution import ExecutionEnvironment
from qma.core.ports.knowledge import KnowledgeSource
from qma.core.ports.memory import MemoryProvider
from qma.core.ports.model import (
    DeploymentRecord,
    ModelDeployment,
    ReviewPolicy,
    select_reviewer,
)
from qma.core.ports.tools import ToolAdapter

RUNTIME_PORT_TYPES: tuple[type, ...] = (
    MemoryProvider,
    ModelDeployment,
    ExecutionEnvironment,
    KnowledgeSource,
    ToolAdapter,
    ComputeProvider,
    ContextCompiler,
)

__all__ = [
    "CONTEXT_COMPILER_SCOPE_KEY",
    "MULTI_CONTRIBUTION_POINTS",
    "PORT_CONTRACTS",
    "PORT_CONTRACT_BY_NAME",
    "RETIRED_CONTRIBUTION_POINTS",
    "RUNTIME_PORT_TYPES",
    "Cardinality",
    "ComputeProvider",
    "ContextCompiler",
    "DeploymentRecord",
    "ExecutionEnvironment",
    "KnowledgeSource",
    "MemoryProvider",
    "ModelDeployment",
    "PortContract",
    "PortError",
    "ReviewPolicy",
    "ToolAdapter",
    "has_qma_wire_schema",
    "qualified_contribution_id",
    "require_singleton_scope_key",
    "select_reviewer",
    "validate_contribution_point",
    "validate_multi_contribution_key",
]
