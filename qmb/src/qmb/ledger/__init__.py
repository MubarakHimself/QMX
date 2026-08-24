"""Ledger line schema and world/role-scoped read views (B-4).

Exactly one ledger line per run, on a WriterId-scoped JSONL fragment. A
ledger line stores raw unit-kinded measures — never a stored pass/fail.
The bar verdict is a read-time fold (DEC-0161, DEC-0162). Physical append
and merge I/O live in the orchestrator; this module is the schema.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from qmf.core.chrono import WriterId

from qmb.config.compiler import ASSIGNMENT_IS_CANONICAL_KEY, ResolvedRunConfig
from qmb.config.replay import FOLD_RATED, FOLD_UNRATED
from qmb.ledger.line import (
    BOOK_BAR_READ_ROLE,
    LEDGER_FORMAT_VERSION,
    LEDGER_FORMAT_VERSION_1,
    LEDGER_LINE_CLASS,
    ONE_LINE_PER_RUN,
    PROVENANCE_SANDBOX,
    ROLE_ABORTED,
    ROLE_CONFIRMATION,
    ROLE_REPLICATE,
    ROLE_TRIAL,
    RUN_ROLES,
    STORES_VERDICT,
    LedgerLine,
    book_bar_fingerprint,
    book_bar_lines,
    merge_ledger_lines,
    mint_aborted_line,
    mint_completed_line,
)

__all__ = [
    "BOOK_BAR_READ_ROLE",
    "CANONICAL_ASSIGNMENT_CANONICAL",
    "CANONICAL_ASSIGNMENT_MISS",
    "CANONICAL_ASSIGNMENT_NOT_YET_RULED",
    "FOLD_RATED",
    "FOLD_UNRATED",
    "LEDGER_FORMAT_VERSION",
    "LEDGER_FORMAT_VERSION_1",
    "LEDGER_LINE_CLASS",
    "ONE_LINE_PER_RUN",
    "PROVENANCE_SANDBOX",
    "ROLE_ABORTED",
    "ROLE_CONFIRMATION",
    "ROLE_REPLICATE",
    "ROLE_TRIAL",
    "RUN_ROLES",
    "STORES_VERDICT",
    "LedgerLine",
    "book_bar_fingerprint",
    "book_bar_lines",
    "fold_canonical_assignment",
    "ledger_identity",
    "merge_ledger_lines",
    "mint_aborted_line",
    "mint_completed_line",
]

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
        "book_bar_read_role": BOOK_BAR_READ_ROLE,
        "canonical_assignment_qualifier": (
            CANONICAL_ASSIGNMENT_CANONICAL,
            CANONICAL_ASSIGNMENT_MISS,
            CANONICAL_ASSIGNMENT_NOT_YET_RULED,
        ),
        "fold_ratings": (FOLD_RATED, FOLD_UNRATED),
        "format_version": LEDGER_FORMAT_VERSION,
        "fragment_kind": "jsonl",
        "line_class": LEDGER_LINE_CLASS,
        "one_line_per_run": ONE_LINE_PER_RUN,
        "run_roles": RUN_ROLES,
        "stores_verdict": STORES_VERDICT,
        "writer": f"{WriterId.__module__}.{WriterId.__qualname__}",
        "writer_scope": ("machine", "role", "worker-slot"),
    }
