"""Ledger line schema and world/role-scoped read views (B-4).

Exactly one ledger line per run, on a WriterId-scoped JSONL fragment. A
ledger line stores raw unit-kinded measures — never a stored pass/fail.
The bar verdict is a read-time fold (DEC-0161, DEC-0162).
"""

from __future__ import annotations

from typing import Final

from qmf.core.chrono import WriterId

__all__ = ["RUN_ROLES", "ledger_identity"]

RUN_ROLES: Final[tuple[str, ...]] = (
    "confirmation",
    "trial",
    "replicate",
    "aborted",
)


def ledger_identity() -> dict[str, object]:
    """Identity-bearing ledger fields. Package SemVer is omitted."""
    return {
        "run_roles": RUN_ROLES,
        "writer": f"{WriterId.__module__}.{WriterId.__qualname__}",
        "fragment_kind": "jsonl",
    }
