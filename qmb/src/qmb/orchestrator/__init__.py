"""Impure composition root: process spawn, governor, sinks, WriterId (B-4/B-5).

The library's ``run()`` is a pure function: it writes no log and no ledger.
This module is the one impure owner of injected sinks, process-per-run
spawn, and the ``min(cpu, memory)`` governor. The library never holds
module-global mutable state (DEC-0161).
"""

from __future__ import annotations

from typing import Final

__all__ = ["IMPURE_OWNER", "SPAWN_MODEL", "orchestrator_identity"]

IMPURE_OWNER: Final[str] = "orchestrator"
SPAWN_MODEL: Final[str] = "process-per-run"


def orchestrator_identity() -> dict[str, object]:
    """Identity-bearing orchestrator fields. Package SemVer is omitted."""
    return {
        "impure_owner": IMPURE_OWNER,
        "spawn_model": SPAWN_MODEL,
        "governor": "min-cpu-memory",
    }
