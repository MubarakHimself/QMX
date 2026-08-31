"""Six-rung capability ladder declared as code (FR-Q09; DEC-0315).

Not a setting, plugin contribution, or UI-editable variable. The daemon applies
the ordered ladder at registration; the lowest capable rung wins.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

__all__ = [
    "CAPABILITY_LADDER",
    "CAPABILITY_LADDER_OWNER",
    "CapabilityError",
    "CapabilityRung",
    "assert_ladder_is_code_declared",
    "capability_rung_rank",
    "parse_capability_rung",
]


class CapabilityRung(StrEnum):
    """Ordered capability rungs (AD-16). Lowest capable wins."""

    API_OR_STRUCTURED_TOOL = "api_or_structured_tool"
    CLI = "cli"
    CONTAINERIZED_PROGRAM = "containerized_program"
    BROWSER_AUTOMATION = "browser_automation"
    VISUAL_BROWSER_OR_COMPUTER_USE = "visual_browser_or_computer_use"
    PERSISTENT_REMOTE_DESKTOP = "persistent_remote_desktop"


# Code-declared ordered ladder — never a settings key or contribution point.
CAPABILITY_LADDER: Final[tuple[CapabilityRung, ...]] = (
    CapabilityRung.API_OR_STRUCTURED_TOOL,
    CapabilityRung.CLI,
    CapabilityRung.CONTAINERIZED_PROGRAM,
    CapabilityRung.BROWSER_AUTOMATION,
    CapabilityRung.VISUAL_BROWSER_OR_COMPUTER_USE,
    CapabilityRung.PERSISTENT_REMOTE_DESKTOP,
)

CAPABILITY_LADDER_OWNER: Final[str] = "AD-16"


class CapabilityError(ValueError):
    """Raised when a capability-ladder constant is misused."""


def parse_capability_rung(value: CapabilityRung | str) -> CapabilityRung:
    """Parse a rung; invented values fail."""
    if isinstance(value, CapabilityRung):
        return value
    try:
        return CapabilityRung(value)
    except ValueError as exc:
        raise CapabilityError(f"{value!r} is not a capability-ladder rung") from exc


def capability_rung_rank(rung: CapabilityRung | str) -> int:
    """Return 0-based rank on the ladder (lower = more preferred)."""
    resolved = parse_capability_rung(rung)
    return CAPABILITY_LADDER.index(resolved)


def assert_ladder_is_code_declared() -> None:
    """Pin that the ladder is the six code-declared rungs, nothing else."""
    if len(CAPABILITY_LADDER) != 6:
        raise CapabilityError("capability ladder must declare exactly six rungs")
    if tuple(CapabilityRung) != CAPABILITY_LADDER:
        raise CapabilityError(
            "capability ladder must equal CapabilityRung members in declaration order"
        )
    if set(CAPABILITY_LADDER) != set(CapabilityRung):
        raise CapabilityError("capability ladder must cover every CapabilityRung member")
