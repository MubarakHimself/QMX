"""QML-owned conformance-gate contract (QL-8).

Format-versioned on QML's own AD-5 ladder — not CT-numbered (DEC-0178).
Package SemVer never enters identity (DEC-0180). The denial set is library-owned;
hosts inject read surfaces only and own process spawning.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "CONFORMANCE_CONTRACT_CLASS",
    "CONFORMANCE_FORMAT_VERSION",
    "CONFORMANCE_KNOWN_FORMAT_VERSIONS",
    "CONFORMANCE_LADDER",
    "DENIAL_SET",
    "LAYER2_CHECKS",
    "conformance_contract_identity",
]

CONFORMANCE_CONTRACT_CLASS: Final[str] = "qml-conformance-gate"
CONFORMANCE_FORMAT_VERSION: Final[int] = 1
CONFORMANCE_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset({CONFORMANCE_FORMAT_VERSION})
CONFORMANCE_LADDER: Final[str] = "qml-ad5"

# Capabilities a conformant bot may never exercise. Enforced by AST/import scan
# and capability starvation; named here so the denial set is library-owned.
DENIAL_SET: Final[frozenset[str]] = frozenset({"clock", "io", "network", "undeclared_randomness"})

LAYER2_CHECKS: Final[tuple[str, ...]] = (
    "static_ast_import_scan",
    "logic_loads_in_isolation",
    "no_book_present",
    "permitted_intent_kinds",
    "golden_slice_determinism",
    "state_bound_restore_equivalent",
)


def conformance_contract_identity() -> dict[str, object]:
    """Canonical identity of the conformance contract. No CT number, no package SemVer."""
    return {
        "class": CONFORMANCE_CONTRACT_CLASS,
        "contract_format_version": CONFORMANCE_FORMAT_VERSION,
        "ladder": CONFORMANCE_LADDER,
        "denial_set": sorted(DENIAL_SET),
        "layer2_checks": list(LAYER2_CHECKS),
    }
