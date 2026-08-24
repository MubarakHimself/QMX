"""Ledger line schema and world/role-scoped read views (B-4).

Exactly one ledger line per run, on a WriterId-scoped JSONL fragment. A
ledger line stores raw unit-kinded measures — never a stored pass/fail.
The bar verdict is a read-time fold (DEC-0161, DEC-0162).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from qmf.core.chrono import WriterId

from qmb.config.compiler import ASSIGNMENT_IS_CANONICAL_KEY, ResolvedRunConfig
from qmb.config.replay import FOLD_RATED, FOLD_UNRATED

__all__ = [
    "CANONICAL_ASSIGNMENT_CANONICAL",
    "CANONICAL_ASSIGNMENT_MISS",
    "CANONICAL_ASSIGNMENT_NOT_YET_RULED",
    "FOLD_RATED",
    "FOLD_UNRATED",
    "RUN_ROLES",
    "fold_canonical_assignment",
    "ledger_identity",
]

RUN_ROLES: Final[tuple[str, ...]] = (
    "confirmation",
    "trial",
    "replicate",
    "aborted",
)

CANONICAL_ASSIGNMENT_CANONICAL: Final[str] = "canonical"
CANONICAL_ASSIGNMENT_MISS: Final[str] = "miss"
CANONICAL_ASSIGNMENT_NOT_YET_RULED: Final[str] = "not-yet-ruled"


def fold_canonical_assignment(config: object) -> str:
    """B-4 qualifier over the B-3 ``assignment_is_canonical`` stamp (DEC-0183).

    A run whose resolved values differ from the cited CT-33 canonical assignment
    satisfies no admission-bar requirement that declares canonical-assignment
    evidence, exactly as a world/role miss yields ``not-yet-ruled``. Ungoverned
    cites carry no stamp.
    """
    stamp: object
    if isinstance(config, ResolvedRunConfig):
        stamp = config.assignment_is_canonical
    elif isinstance(config, Mapping):
        mapping = cast("Mapping[str, object]", config)
        stamp = mapping.get(ASSIGNMENT_IS_CANONICAL_KEY)
        keys = mapping.get("keys")
        if stamp is None and isinstance(keys, Mapping):
            nested = cast("Mapping[str, object]", keys)
            stamp = nested.get(ASSIGNMENT_IS_CANONICAL_KEY)
    else:
        stamp = None
    if stamp is True:
        return CANONICAL_ASSIGNMENT_CANONICAL
    if stamp is False:
        return CANONICAL_ASSIGNMENT_MISS
    return CANONICAL_ASSIGNMENT_NOT_YET_RULED


def ledger_identity() -> dict[str, object]:
    """Identity-bearing ledger fields. Package SemVer is omitted."""
    return {
        "fold_ratings": (FOLD_RATED, FOLD_UNRATED),
        "fragment_kind": "jsonl",
        "run_roles": RUN_ROLES,
        "writer": f"{WriterId.__module__}.{WriterId.__qualname__}",
        "canonical_assignment_qualifier": (
            CANONICAL_ASSIGNMENT_CANONICAL,
            CANONICAL_ASSIGNMENT_MISS,
            CANONICAL_ASSIGNMENT_NOT_YET_RULED,
        ),
    }
