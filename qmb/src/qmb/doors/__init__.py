"""Thin doors over the library (B-1).

Every capability exists once, in the library, as a pure function. Doors carry
only adaptation logic. The ``qmb`` CLI is the product face; the Python API
exposes the same surface in-process (never HTTP); the MCP door is scaffolded
and ships after CLI v1.
"""

from __future__ import annotations

from typing import Final

from qmb.doors.parity import (
    CAPABILITY_LIBRARY,
    CLI_ADAPTATION_COMMANDS,
    MCP_IN_DOOR_SET,
    SHIPPED_DOORS,
    capability_gaps,
    door_parity_identity,
    flatten_capabilities,
    required_library_names,
)

__all__ = [
    "CAPABILITY_LIBRARY",
    "CLI_ADAPTATION_COMMANDS",
    "CLI_PIN_KEY",
    "CLI_PROG",
    "MCP_IN_DOOR_SET",
    "MCP_SHIPPED",
    "SHIPPED_DOORS",
    "capability_gaps",
    "door_parity_identity",
    "flatten_capabilities",
    "required_library_names",
]

CLI_PROG: Final[str] = "qmb"
CLI_PIN_KEY: Final[str] = "qmb_cli_pin"
MCP_SHIPPED: Final[bool] = False
