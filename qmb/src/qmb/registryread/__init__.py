"""Single library-owned registry-read port over immutable as-of sets (B-15).

Registry state reaches a machine as an immutable, fingerprinted as-of set of
records and fragments. Doors enumerate through this port; the compiler
resolves through it. No door-side or second cache exists (DEC-0165).
"""

from __future__ import annotations

from typing import Final

from qmf.registry import KindRegistry

__all__ = ["STATE_KIND", "port_home", "read_port_identity"]

STATE_KIND: Final[str] = "as-of set"


def port_home() -> str:
    """The registry types this port reads; one port, no second cache."""
    return f"{KindRegistry.__module__}.{KindRegistry.__qualname__}"


def read_port_identity() -> dict[str, object]:
    """Identity-bearing registry-read fields. Package SemVer is omitted."""
    return {
        "state_kind": STATE_KIND,
        "port": "library-owned",
        "reads": port_home(),
    }
