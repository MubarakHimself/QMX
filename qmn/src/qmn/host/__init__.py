"""Composition root surface (TN-2): compose → fingerprint → seal.

The host is the only impure shell that owns ambient time, broker sessions,
secrets, async at the venue edge and doors, and real money. Later stories fill
preflight, boot-attempt records, and WriterId allocation; this module only
publishes the ordered ceremony names and a sealed-composition marker so the
scaffold cannot be mistaken for a second authority or CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "BOOT_CEREMONY_STEPS",
    "COMPOSITION_ROOT_SURFACE",
    "SealedComposition",
    "ceremony_steps",
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
