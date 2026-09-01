"""ModelClass -> Deployment -> Credential Broker (AD-15, AD-24).

Story 44.1: deterministic ModelClass routing and Deployment-family governance.
ReviewPolicy and catalog helpers remain core-defined (CT-45).
"""

from __future__ import annotations

from qma.core.ports.model import (
    MODEL_FAMILY_ASSIGN_COMMAND,
    DeploymentRecord,
    ModelCapabilities,
    ModelClassRequest,
    NeedsFlags,
    ReviewPolicy,
    RoutingDecision,
    assign_model_family,
    resolve_model_request,
    select_reviewer,
)
from qma.daemon.proxy.registry import DeploymentRegistry
from qma.daemon.proxy.router import ModelRouter

__all__ = [
    "MODEL_FAMILY_ASSIGN_COMMAND",
    "DeploymentRecord",
    "DeploymentRegistry",
    "ModelCapabilities",
    "ModelClassRequest",
    "ModelRouter",
    "NeedsFlags",
    "ReviewPolicy",
    "RoutingDecision",
    "assign_model_family",
    "resolve_model_request",
    "select_reviewer",
]
