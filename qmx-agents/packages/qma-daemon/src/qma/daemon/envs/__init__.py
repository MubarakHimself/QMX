"""ExecutionEnvironment registry and lease evaluation (AD-14, AD-17; FR-Q27, FR-Q47, FR-Q48)."""

from __future__ import annotations

from qma.core.barriers.reachability import GAP_0070_DESKTOP_EXCLUSION
from qma.core.ports.execution import (
    ComputerUseProfile,
    EnvironmentMount,
    ExecutionEnvironmentDeclaration,
    WorkerImageManifest,
)
from qma.core.vocabulary.enums import EnvironmentLifecycle
from qma.daemon.envs.registry import EnvironmentLease, ExecutionEnvironmentRegistry

__all__ = [
    "GAP_0070_DESKTOP_EXCLUSION",
    "ComputerUseProfile",
    "EnvironmentLease",
    "EnvironmentLifecycle",
    "EnvironmentMount",
    "ExecutionEnvironmentDeclaration",
    "ExecutionEnvironmentRegistry",
    "WorkerImageManifest",
]
