"""Thin doors over the library (B-1).

Every capability exists once, in the library, as a pure function. Doors carry
only adaptation logic. The ``qmb`` CLI is the product face; the Python API
exposes the same surface; the MCP door is scaffolded and ships after CLI v1.
"""

from __future__ import annotations

from typing import Final

__all__ = ["CLI_PIN_KEY", "CLI_PROG", "MCP_SHIPPED"]

CLI_PROG: Final[str] = "qmb"
CLI_PIN_KEY: Final[str] = "qmb_cli_pin"
MCP_SHIPPED: Final[bool] = False
