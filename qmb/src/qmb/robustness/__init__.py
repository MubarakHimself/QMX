"""Validation-ladder procedures as library functions (B-14).

Backtest, optimize, Monte Carlo, rule-significance, and walk-forward ship as
versioned procedures. They claim robustness or infra-stress, never edge
(DEC-0169).
"""

from __future__ import annotations

from typing import Final

__all__ = ["PROCEDURES", "ladder_identity"]

PROCEDURES: Final[tuple[str, ...]] = (
    "backtest",
    "optimize",
    "monte-carlo",
    "rule-significance",
    "walk-forward",
)


def ladder_identity() -> dict[str, object]:
    """Identity-bearing ladder fields. Package SemVer is omitted."""
    return {"procedures": PROCEDURES, "claim_class": "robustness-or-infra-stress"}
