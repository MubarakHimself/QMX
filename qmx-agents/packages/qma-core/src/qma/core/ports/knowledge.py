"""KnowledgeSource port — singleton per ``source_id`` (CT-44; AD-1, AD-19)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["KnowledgeSource"]


@runtime_checkable
class KnowledgeSource(Protocol):
    """Definitions-only KnowledgeSource seam; one adapter per source_id.

    Cardinality: singleton, scope key ``source_id`` (see ``PORT_CONTRACTS``).
    """
