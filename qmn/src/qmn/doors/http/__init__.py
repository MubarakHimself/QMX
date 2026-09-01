"""Localhost HTTP evidence channel and AF_UNIX powers channel (TN-17).

Evidence is publish-never-act. Powers authenticate operator vs ops principals
at the transport; this scaffold only names the doors.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "EVIDENCE_DOOR",
    "POWERS_DOOR",
    "evidence_door_name",
    "powers_door_name",
]

EVIDENCE_DOOR: Final[str] = "evidence_http"
POWERS_DOOR: Final[str] = "powers_unix"


def evidence_door_name() -> str:
    return EVIDENCE_DOOR


def powers_door_name() -> str:
    return POWERS_DOOR
