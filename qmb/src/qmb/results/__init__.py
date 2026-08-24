"""Canonical CT-32 result artifact, metrics, and chart-series home (B-10).

Every run emits one canonical machine-readable result artifact, and that
artifact IS a CT-32 performance-result. Package SemVer is display-only
provenance on the occurrence record, never identity (DEC-0163, DEC-0167).
"""

from __future__ import annotations

from typing import Final

from qmf.risk.performance import PerformanceResult

__all__ = ["RESULT_CONTRACT", "result_identity"]

RESULT_CONTRACT: Final[str] = "CT-32"


def result_identity() -> dict[str, object]:
    """Identity-bearing result-container fields. Package SemVer is omitted."""
    return {
        "contract": RESULT_CONTRACT,
        "container": f"{PerformanceResult.__module__}.{PerformanceResult.__qualname__}",
    }
