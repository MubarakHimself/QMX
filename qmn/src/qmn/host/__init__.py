"""Composition root surface (TN-2): compose → fingerprint → seal.

The host is the only impure shell that owns ambient time, broker sessions,
secrets, async at the venue edge and doors, and real money. Story 25.3 mints
identity-bearing Compose records through the qmf-registry Registrar exactly
once per fingerprint; later stories fill preflight, boot-attempt records, and
WriterId allocation. Child modules and doors never restamp and never hold a
registry cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from qmn.host.registry_mint import (
    COMPOSE_KIND_FORMAT_VERSION,
    COMPOSE_RECORD_KINDS,
    DOOR_LOCAL_REGISTRY_CACHE,
    HAS_ALTERNATE_IDENTITY_FUNCTION,
    IDENTITY_FORBIDDEN_OCCURRENCE_KEYS,
    REGISTRY_MINT_SURFACE,
    ComposeOccurrenceEvidence,
    CompositionRootRegistry,
    compose_kind_contract,
    install_compose_kinds,
    mint_compose_record,
)

__all__ = [
    "BOOT_CEREMONY_STEPS",
    "COMPOSE_KIND_FORMAT_VERSION",
    "COMPOSE_RECORD_KINDS",
    "COMPOSITION_ROOT_SURFACE",
    "DOOR_LOCAL_REGISTRY_CACHE",
    "HAS_ALTERNATE_IDENTITY_FUNCTION",
    "IDENTITY_FORBIDDEN_OCCURRENCE_KEYS",
    "REGISTRY_MINT_SURFACE",
    "ComposeOccurrenceEvidence",
    "CompositionRootRegistry",
    "SealedComposition",
    "ceremony_steps",
    "compose_kind_contract",
    "install_compose_kinds",
    "mint_compose_record",
]

COMPOSITION_ROOT_SURFACE: Final[str] = "qmn.host"
BOOT_CEREMONY_STEPS: Final[tuple[str, ...]] = (
    "preflight",
    "compose",
    "fingerprint",
    "seal",
)


@dataclass(frozen=True, slots=True)
class SealedComposition:
    """Marker for one sealed boot-epoch composition.

    Identity later binds ``composition_fp``; the scaffold carries only the
    ceremony step labels so no operational value is invented here.
    """

    surface: str = COMPOSITION_ROOT_SURFACE
    sealed: bool = True

    def steps(self) -> tuple[str, ...]:
        return BOOT_CEREMONY_STEPS


def ceremony_steps() -> tuple[str, ...]:
    """Ordered compose → fingerprint → seal ceremony (plus preflight gate)."""
    return BOOT_CEREMONY_STEPS
