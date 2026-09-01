"""Three thin doors and no operator command line (TN-17, DEC-0211).

Doors: in-process Python API, localhost HTTP evidence channel, unix-socket
powers channel. There is no CLI door and no typed operator command parser —
``qmb`` remains the platform's single command-line surface.
"""

from __future__ import annotations

from typing import Final

from qmn.doors.api import API_DOOR, api_door_name
from qmn.doors.http import EVIDENCE_DOOR, POWERS_DOOR, evidence_door_name, powers_door_name

__all__ = [
    "API_DOOR",
    "DOORS_SURFACE",
    "EVIDENCE_DOOR",
    "HAS_OPERATOR_CLI_DOOR",
    "POWERS_DOOR",
    "SHIPPED_DOORS",
    "api_door_name",
    "evidence_door_name",
    "powers_door_name",
    "shipped_doors",
]

DOORS_SURFACE: Final[str] = "qmn.doors"
HAS_OPERATOR_CLI_DOOR: Final[bool] = False
SHIPPED_DOORS: Final[tuple[str, ...]] = (API_DOOR, EVIDENCE_DOOR, POWERS_DOOR)


def shipped_doors() -> tuple[str, ...]:
    """The closed three-door set; never a fourth CLI door."""
    return SHIPPED_DOORS
