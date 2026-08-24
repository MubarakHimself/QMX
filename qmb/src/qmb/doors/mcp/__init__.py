"""MCP door — scaffolded, not shipped until after CLI v1 (B-1, SC-08).

A sibling wrapper over the same library, never stacked over HTTP. This
module is present so the structural-seed tree is complete; it is not a
product face and is not registered as a console script.
"""

from __future__ import annotations

from typing import Final

from qmf.core.refusal import Result

from qmb._refuse import unsupported
from qmb.doors import MCP_SHIPPED

__all__ = ["SHIPPED", "is_shipped", "main"]

SHIPPED: Final[bool] = MCP_SHIPPED


def is_shipped() -> bool:
    """False in V1: the MCP door ships after CLI v1."""
    return SHIPPED


def main() -> Result[None]:
    """Refuse invocation: this door is not a V1 product face."""
    return unsupported(
        "door",
        "the MCP door is scaffolded and ships after CLI v1; it is not stacked over HTTP",
    )
