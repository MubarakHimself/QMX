"""MemoryProvider binding and deterministic admission gate (CT-43; FR-Q64)."""

from __future__ import annotations

from qma.daemon.memory.admission import (
    GAP_0072_EXTERNAL_MEMORY_BACKEND,
    MEMORY_PROVIDER_OPERATIONS,
    NO_DATABASE_SERVER_SCOPE,
    NO_PROMOTE_OPERATION,
    AdmittingOutcome,
    MemoryAdmissionGate,
    MemoryProviderRegistry,
    ProviderBinding,
    RecallOutcome,
)

__all__ = [
    "GAP_0072_EXTERNAL_MEMORY_BACKEND",
    "MEMORY_PROVIDER_OPERATIONS",
    "NO_DATABASE_SERVER_SCOPE",
    "NO_PROMOTE_OPERATION",
    "AdmittingOutcome",
    "MemoryAdmissionGate",
    "MemoryProviderRegistry",
    "ProviderBinding",
    "RecallOutcome",
]
