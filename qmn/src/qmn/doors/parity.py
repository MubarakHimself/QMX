"""Derived door-parity reconciler for the three QMN doors (TN-17 / DEC-0202).

Parity is scoped: every capability the HTTP evidence and unix-socket powers
doors expose must be the same library function the Python API exposes, with the
same refusals — not that all doors expose the same set. Surfaces are DERIVED
from each door (routes / dispatch / ``is``-identity re-exports), never from a
hand-maintained capability catalog.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Final

from qmn.doors.http.dispatch import powers_capability_surface
from qmn.doors.http.evidence import evidence_capability_surface
from qmn.doors.library import library_capability_names

__all__ = [
    "AGENT_MCP_IN_DOOR_SET",
    "CLI_IN_DOOR_SET",
    "SHIPPED_DOORS",
    "api_capability_surface",
    "capability_gaps",
    "door_parity_identity",
    "evidence_http_capability_surface",
    "powers_unix_capability_surface",
]

SHIPPED_DOORS: Final[tuple[str, ...]] = ("python_api", "evidence_http", "powers_unix")
CLI_IN_DOOR_SET: Final[bool] = False
AGENT_MCP_IN_DOOR_SET: Final[bool] = False


def evidence_http_capability_surface() -> frozenset[str]:
    return evidence_capability_surface()


def powers_unix_capability_surface() -> frozenset[str]:
    return powers_capability_surface()


def api_capability_surface() -> frozenset[str]:
    """API door surface: names re-exported ``is``-identical to ``qmn.doors.library``."""
    from qmn.doors import api  # noqa: PLC0415 — import-cycle with the door
    from qmn.doors import library as lib  # noqa: PLC0415

    out: set[str] = set()
    for name in library_capability_names():
        if getattr(api, name, None) is getattr(lib, name, object()):
            out.add(name)
    return frozenset(out)


def capability_gaps(
    *,
    api_names: Iterable[str] | None = None,
    evidence_names: Iterable[str] | None = None,
    powers_names: Iterable[str] | None = None,
) -> Mapping[str, object]:
    """Reconcile DERIVED door surfaces against the Python API (TN-17).

    ``missing_*_from_api`` lists every library name an unequal door adapts that
    the API does not re-export identity-equal. Empty tuples mean parity holds.
    """
    api_set = frozenset(api_names) if api_names is not None else api_capability_surface()
    evidence_set = (
        frozenset(evidence_names)
        if evidence_names is not None
        else evidence_http_capability_surface()
    )
    powers_set = (
        frozenset(powers_names) if powers_names is not None else powers_unix_capability_surface()
    )
    return MappingProxyType(
        {
            "missing_evidence_from_api": tuple(sorted(evidence_set - api_set)),
            "missing_powers_from_api": tuple(sorted(powers_set - api_set)),
            "api": tuple(sorted(api_set)),
            "evidence_http": tuple(sorted(evidence_set)),
            "powers_unix": tuple(sorted(powers_set)),
        }
    )


def door_parity_identity() -> Mapping[str, object]:
    """Identity-bearing door-parity fields. Package SemVer is omitted."""
    return MappingProxyType(
        {
            "adaptation": ("parsing", "transport", "refusal-rendering"),
            "derived_reconciliation": True,
            "shipped_doors": SHIPPED_DOORS,
            "cli_in_door_set": CLI_IN_DOOR_SET,
            "agent_mcp_in_door_set": AGENT_MCP_IN_DOOR_SET,
            "library_capabilities": tuple(sorted(library_capability_names())),
        }
    )
