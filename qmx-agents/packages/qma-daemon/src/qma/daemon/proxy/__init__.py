"""ModelClass -> Deployment -> Credential Broker (AD-15, AD-24).

Story 44.1: deterministic ModelClass routing and Deployment-family governance.
Story 44.2: OpenCodex local-proxy custody and Credential Broker egress.
ReviewPolicy and catalog helpers remain core-defined (CT-45).
"""

from __future__ import annotations

from qma.core.ports.model import (
    AUTH_MODE_NONE,
    LOCAL_PROXY_ADAPTERS,
    MODEL_FAMILY_ASSIGN_COMMAND,
    OPENCODEX_ADAPTER,
    PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY,
    DeploymentRecord,
    ModelCapabilities,
    ModelClassRequest,
    NeedsFlags,
    ReviewPolicy,
    RoutingDecision,
    assign_model_family,
    is_local_proxy_deployment,
    resolve_model_request,
    select_reviewer,
)
from qma.daemon.proxy.broker import (
    WINDOWS_CREDENTIAL_MANAGER_BACKEND,
    CredentialBackend,
    CredentialBroker,
    MemoryCredentialBackend,
    WindowsCredentialManagerBackend,
)
from qma.daemon.proxy.egress import (
    ADAPTER_LAYERS,
    AdapterLayerCaller,
    EgressFrame,
    EgressFrameError,
)
from qma.daemon.proxy.harness import (
    ModelHarnessResult,
    RoutingTelemetry,
    execute_quant_model_request,
)
from qma.daemon.proxy.local_proxy import (
    ALLOW_UNAUTHENTICATED_LOOPBACK_DEFAULT,
    LocalProxyStartupEvidence,
    record_local_proxy_startup_evidence,
    validate_local_proxy_registration,
)
from qma.daemon.proxy.opencodex import (
    OpenCodexCallResult,
    OpenCodexDeployment,
    build_opencodex_deployment_record,
)
from qma.daemon.proxy.registry import DeploymentRegistry
from qma.daemon.proxy.router import ModelRouter

__all__ = [
    "ADAPTER_LAYERS",
    "ALLOW_UNAUTHENTICATED_LOOPBACK_DEFAULT",
    "AUTH_MODE_NONE",
    "LOCAL_PROXY_ADAPTERS",
    "MODEL_FAMILY_ASSIGN_COMMAND",
    "OPENCODEX_ADAPTER",
    "PROXY_ALLOW_UNAUTHENTICATED_LOOPBACK_KEY",
    "WINDOWS_CREDENTIAL_MANAGER_BACKEND",
    "AdapterLayerCaller",
    "CredentialBackend",
    "CredentialBroker",
    "DeploymentRecord",
    "DeploymentRegistry",
    "EgressFrame",
    "EgressFrameError",
    "LocalProxyStartupEvidence",
    "MemoryCredentialBackend",
    "ModelCapabilities",
    "ModelClassRequest",
    "ModelHarnessResult",
    "ModelRouter",
    "NeedsFlags",
    "OpenCodexCallResult",
    "OpenCodexDeployment",
    "ReviewPolicy",
    "RoutingDecision",
    "RoutingTelemetry",
    "WindowsCredentialManagerBackend",
    "assign_model_family",
    "build_opencodex_deployment_record",
    "execute_quant_model_request",
    "is_local_proxy_deployment",
    "record_local_proxy_startup_evidence",
    "resolve_model_request",
    "select_reviewer",
    "validate_local_proxy_registration",
]
