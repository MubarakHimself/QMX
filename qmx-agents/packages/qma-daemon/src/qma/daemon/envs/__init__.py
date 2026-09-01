"""ExecutionEnvironment registry, Compute Router, and lease evaluation.

AD-14, AD-17; FR-Q27, FR-Q47, FR-Q48, FR-Q49, FR-Q50.
"""

from __future__ import annotations

from qma.core.barriers.reachability import GAP_0070_DESKTOP_EXCLUSION
from qma.core.ports.compute import (
    COMPUTE_REQUIREMENT_FIELDS,
    ComputeRequirement,
    GpuRequirement,
    environment_isolation,
    match_compute_requirement,
    parse_compute_requirement,
)
from qma.core.ports.execution import (
    ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT,
    ENVIRONMENT_MAX_IN_FLIGHT_KEY,
    PINNED_SINGLE_SLOT_KINDS,
    ComputerUseProfile,
    EnvironmentMount,
    ExecutionEnvironmentDeclaration,
    WorkerImageManifest,
)
from qma.core.vocabulary.enums import EnvironmentLifecycle
from qma.daemon.envs.registry import EnvironmentLease, ExecutionEnvironmentRegistry
from qma.daemon.envs.router import ComputeRouter, PlacementDecision, QueuedPlacement

__all__ = [
    "COMPUTE_REQUIREMENT_FIELDS",
    "ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT",
    "ENVIRONMENT_MAX_IN_FLIGHT_KEY",
    "GAP_0070_DESKTOP_EXCLUSION",
    "PINNED_SINGLE_SLOT_KINDS",
    "ComputeRequirement",
    "ComputeRouter",
    "ComputerUseProfile",
    "EnvironmentLease",
    "EnvironmentLifecycle",
    "EnvironmentMount",
    "ExecutionEnvironmentDeclaration",
    "ExecutionEnvironmentRegistry",
    "GpuRequirement",
    "PlacementDecision",
    "QueuedPlacement",
    "WorkerImageManifest",
    "environment_isolation",
    "match_compute_requirement",
    "parse_compute_requirement",
]
