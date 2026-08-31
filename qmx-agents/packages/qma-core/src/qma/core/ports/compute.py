"""ComputeProvider port — singleton per ``kind`` (AD-1, AD-17)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["ComputeProvider"]


@runtime_checkable
class ComputeProvider(Protocol):
    """Definitions-only ComputeProvider seam; one binding per compute kind.

    Cardinality: singleton, scope key ``kind`` (see ``PORT_CONTRACTS``).
    """
