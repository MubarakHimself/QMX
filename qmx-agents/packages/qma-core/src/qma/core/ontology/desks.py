"""Fixed desk slugs, display names, and Role names (AD-7; DEC-0306; FR-Q06)."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

__all__ = [
    "DESK_DISPLAY_NAMES",
    "DESK_PREFIX_TOKENS",
    "DESK_SLUG_VALUES",
    "ROLE_DISPLAY_NAMES",
    "ROLE_SLUG_COLLISION_KEYS",
    "DeskSlug",
    "OntologyError",
    "RoleName",
    "assert_role_names_are_not_desk_names",
    "role_slug_collision_key",
]


class OntologyError(ValueError):
    """Raised when ontology static invariants are violated."""


class DeskSlug(StrEnum):
    """The five fixed ``desk_slug`` values (AD-7; DEC-0306)."""

    RESEARCH = "research"
    TRADING = "trading"
    DEV = "dev"
    ANALYSIS = "analysis"
    PM = "pm"


class RoleName(StrEnum):
    """The five Role display names — never used as Desk names (AD-7)."""

    RESEARCHER = "Researcher"
    TRADER = "Trader"
    DEVELOPER = "Developer"
    ANALYST = "Analyst"
    PRODUCT_MANAGER = "Product Manager"


DESK_SLUG_VALUES: Final[frozenset[str]] = frozenset(member.value for member in DeskSlug)

# Identical to the plugin prefix tokens research-*, trading-*, … (DEC-0306, DEC-0337).
DESK_PREFIX_TOKENS: Final[frozenset[str]] = DESK_SLUG_VALUES

DESK_DISPLAY_NAMES: Final[dict[DeskSlug, str]] = {
    DeskSlug.RESEARCH: "Research",
    DeskSlug.TRADING: "Trading",
    DeskSlug.DEV: "Development",
    DeskSlug.ANALYSIS: "Analysis",
    DeskSlug.PM: "PM",
}

ROLE_DISPLAY_NAMES: Final[frozenset[str]] = frozenset(member.value for member in RoleName)


def role_slug_collision_key(name: str) -> str:
    """Case-fold a Role name into the slug-collision key space."""
    folded = name.casefold().strip()
    return folded.replace(" ", "").replace("_", "").replace("-", "")


ROLE_SLUG_COLLISION_KEYS: Final[frozenset[str]] = frozenset(
    role_slug_collision_key(name) for name in ROLE_DISPLAY_NAMES
)


def assert_role_names_are_not_desk_names() -> None:
    """Static check: a Role name may never be used as a Desk name (FR-Q06)."""
    desk_names = frozenset(DESK_DISPLAY_NAMES.values())
    overlap = desk_names & ROLE_DISPLAY_NAMES
    if overlap:
        raise OntologyError(
            f"Role names must never name a Desk; overlapping names: {sorted(overlap)}"
        )
    desk_keys = frozenset(role_slug_collision_key(name) for name in desk_names)
    role_keys = ROLE_SLUG_COLLISION_KEYS
    key_overlap = desk_keys & role_keys
    if key_overlap:
        raise OntologyError(
            "Role names must never case-fold onto a Desk name; "
            f"overlapping keys: {sorted(key_overlap)}"
        )


# Run at import so a drift in the closed sets fails loudly in definitions.
assert_role_names_are_not_desk_names()
