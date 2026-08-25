"""MCP door — scaffolded, not shipped until after CLI v1 (B-1, SC-08).

A sibling wrapper over the same library, never stacked over HTTP,
localhost-bound by default. This module is present so the structural-seed
tree is complete; it is not a product face, not in the V1 door-set, and
not registered as a console script. CLI v1 does not wait on it.
"""

from __future__ import annotations

from typing import Final

from qmf.core.refusal import Result

from qmb._refuse import unsupported
from qmb.doors import MCP_IN_DOOR_SET, MCP_SHIPPED
from qmb.doors.mcp.render import error_data, render_error

__all__ = [
    "BIND_HOST",
    "COMPUTES_RUN_ID",
    "HOLDS_CACHE",
    "LIBRARY",
    "LOCALHOST_BOUND",
    "POST_CLI_V1",
    "SHIPPED",
    "STACKED_OVER_HTTP",
    "TRANSPORT",
    "WRAPPER",
    "error_data",
    "is_shipped",
    "main",
    "mcp_door_identity",
    "render_error",
    "serve",
]

SHIPPED: Final[bool] = MCP_SHIPPED
POST_CLI_V1: Final[bool] = True
STACKED_OVER_HTTP: Final[bool] = False
LOCALHOST_BOUND: Final[bool] = True
BIND_HOST: Final[str] = "127.0.0.1"
LIBRARY: Final[str] = "qmb"
WRAPPER: Final[str] = "sibling"
TRANSPORT: Final[str] = "mcp"
HOLDS_CACHE: Final[bool] = False
COMPUTES_RUN_ID: Final[bool] = False


def is_shipped() -> bool:
    """False in V1: the MCP door ships after CLI v1."""
    return SHIPPED


def mcp_door_identity() -> dict[str, object]:
    """Identity-bearing MCP-door fields (B-1, SC-08, AR-58). SemVer excluded."""
    return {
        "bind_host": BIND_HOST,
        "computes_run_id": COMPUTES_RUN_ID,
        "holds_cache": HOLDS_CACHE,
        "in_door_set": MCP_IN_DOOR_SET,
        "library": LIBRARY,
        "localhost_bound": LOCALHOST_BOUND,
        "post_cli_v1": POST_CLI_V1,
        "shipped": SHIPPED,
        "stacked_over_http": STACKED_OVER_HTTP,
        "transport": TRANSPORT,
        "wrapper": WRAPPER,
    }


def serve() -> Result[None]:
    """Refuse to bind: this door is not a V1 product face."""
    return unsupported(
        "door",
        "the MCP door is scaffolded and ships after CLI v1; it is not stacked over HTTP",
    )


def main() -> Result[None]:
    """Refuse invocation: this door is not a V1 product face."""
    return serve()
