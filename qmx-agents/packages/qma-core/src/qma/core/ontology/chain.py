"""Ontology chain and work vocabulary constants (AD-7; DEC-0306; FR-Q06)."""

from __future__ import annotations

from typing import Final

__all__ = [
    "ONTOLOGY_CHAIN",
    "ONTOLOGY_OBJECTS",
    "RUN_CONTAINER",
    "WORK_VOCABULARY",
    "is_ontology_object",
]


# Desk → Role → Quant → Agent → Subagent (DEC-0306).
ONTOLOGY_CHAIN: Final[tuple[str, ...]] = (
    "Desk",
    "Role",
    "Quant",
    "Agent",
    "Subagent",
)

ONTOLOGY_OBJECTS: Final[frozenset[str]] = frozenset(ONTOLOGY_CHAIN)

# Session is the run container; Worker is an addressable execution slot and is
# deliberately not an ontology object (DEC-0306).
RUN_CONTAINER: Final[str] = "Session"

# Goal (informal intent) → Mission (executable contract) → Task (DEC-0306).
WORK_VOCABULARY: Final[tuple[str, ...]] = ("Goal", "Mission", "Task")


def is_ontology_object(name: str) -> bool:
    """Return whether ``name`` is a link on the ontology chain.

    ``Session`` is the run container and ``Worker`` is an execution slot — neither
    is an ontology object.
    """
    return name in ONTOLOGY_OBJECTS
