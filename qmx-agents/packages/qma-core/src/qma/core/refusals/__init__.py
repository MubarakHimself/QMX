"""QMA typed-refusal variants of the qmf-core base (CT-04; FR-Q05).

Public QMA boundaries RETURN these variants; they never raise a domain failure
across the package boundary. Each named variant is defined once in this package.
"""

from __future__ import annotations

from qma.core.refusals._base import QmaRefusal, variant_name
from qma.core.refusals.variants import (
    NAMED_REFUSAL_VARIANTS,
    CredentialOutOfScope,
    CursorScopeMismatch,
    NoEligibleDeployment,
    NoEligibleReviewer,
    NoEnvironment,
    NoMemoryProvider,
    NonLoopbackProxy,
    OperatorPrincipalRequired,
    ProhibitedMoneyPathTool,
    ProvenanceShapeMismatch,
    SlugUnavailable,
    StaleSnapshot,
    StoreVersionMismatch,
    UnauthenticatedProxy,
    UnknownHostRequest,
)

__all__ = [
    "NAMED_REFUSAL_VARIANTS",
    "CredentialOutOfScope",
    "CursorScopeMismatch",
    "NoEligibleDeployment",
    "NoEligibleReviewer",
    "NoEnvironment",
    "NoMemoryProvider",
    "NonLoopbackProxy",
    "OperatorPrincipalRequired",
    "ProhibitedMoneyPathTool",
    "ProvenanceShapeMismatch",
    "QmaRefusal",
    "SlugUnavailable",
    "StaleSnapshot",
    "StoreVersionMismatch",
    "UnauthenticatedProxy",
    "UnknownHostRequest",
    "variant_name",
]
