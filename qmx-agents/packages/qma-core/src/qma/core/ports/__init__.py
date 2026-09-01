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
    MODEL_FAMILY_ASSIGN_COMMAND,
    DeploymentRecord,
    ModelCapabilities,
    ModelClassRequest,
    ModelDeployment,
    NeedsFlags,
    ReviewPolicy,
    RoutingDecision,
    assign_model_family,
    capabilities_for,
    eligible_pool,
    resolve_model_request,
    select_from_eligible,
    select_reviewer,
    unmet_constraint_for,
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
    "MODEL_FAMILY_ASSIGN_COMMAND",
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
    "ModelCapabilities",
    "ModelClassRequest",
    "ModelDeployment",
    "NeedsFlags",
    "PortContract",
    "PortError",
    "ReviewPolicy",
    "RoutingDecision",
    "ToolAdapter",
    "assign_model_family",
    "capabilities_for",
    "eligible_pool",
    "has_qma_wire_schema",
    "qualified_contribution_id",
    "require_singleton_scope_key",
    "resolve_model_request",
    "select_from_eligible",
    "select_reviewer",
    "unmet_constraint_for",
    "validate_contribution_point",
    "validate_multi_contribution_key",
]
