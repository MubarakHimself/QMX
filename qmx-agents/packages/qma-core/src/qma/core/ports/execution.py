"""ExecutionEnvironment port — singleton per ``kind`` (CT-46; AD-1, AD-17)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["ExecutionEnvironment"]


@runtime_checkable
class ExecutionEnvironment(Protocol):
    """Definitions-only ExecutionEnvironment seam; one binding per environment kind.

    Cardinality: singleton, scope key ``kind`` (see ``PORT_CONTRACTS``).
    """
