"""MemoryProvider port — per-desk singleton (CT-43; AD-1, AD-18)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["MemoryProvider"]


@runtime_checkable
class MemoryProvider(Protocol):
    """Definitions-only MemoryProvider seam; daemon binds one provider per desk.

    Cardinality: singleton, scope key ``desk`` (see ``PORT_CONTRACTS``).
    """
