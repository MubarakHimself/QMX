"""Reference usage — MCP door scaffolded, not shipped (Story 16.6).

Executable::

    python qmb/examples/mcp_door_usage.py

Shows the things Story 16.6 / B-1 / SC-08 / AR-58 pin down:

1. ``qmb.doors.mcp`` is present as a sibling wrapper over the same library.
2. It is explicitly post-CLI-v1: ``is_shipped()`` is False.
3. Invocation RETURNS a typed ``unsupported capability`` refusal.
4. The door is never stacked over HTTP and is localhost-bound by default.
5. When a refusal is rendered later, ``error.data`` is the refusal union
   verbatim. CLI v1 does not wait on this door.
"""

from __future__ import annotations

import json

from qmb.doors import MCP_IN_DOOR_SET, SHIPPED_DOORS
from qmb.doors.cli.render import render_refusal
from qmb.doors.mcp import (
    BIND_HOST,
    error_data,
    is_shipped,
    main,
    mcp_door_identity,
    render_error,
)
from qmf.core.refusal import RefusalCategory, TypedRefusal, is_refusal


def unshipped_sibling() -> None:
    assert is_shipped() is False
    identity = mcp_door_identity()
    assert identity["wrapper"] == "sibling"
    assert identity["library"] == "qmb"
    assert identity["post_cli_v1"] is True
    assert identity["shipped"] is False
    assert identity["in_door_set"] is MCP_IN_DOOR_SET is False
    print("sibling wrapper over the same library; post-CLI-v1, not shipped")


def invocation_is_unsupported() -> None:
    refused = main()
    assert is_refusal(refused)
    assert isinstance(refused, TypedRefusal)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    print("invocation is typed unsupported-capability refusal")


def localhost_never_http() -> None:
    identity = mcp_door_identity()
    assert identity["stacked_over_http"] is False
    assert identity["localhost_bound"] is True
    assert BIND_HOST == "127.0.0.1"
    print("localhost-bound by default; never stacked over HTTP")


def error_data_is_the_union() -> None:
    refused = main()
    assert is_refusal(refused)
    payload = error_data(refused)
    assert payload == json.loads(render_refusal(refused))
    assert render_error(refused)["data"] == payload
    print("error.data carries the refusal union verbatim")


def cli_ships_first() -> None:
    assert SHIPPED_DOORS == ("cli", "api")
    assert is_shipped() is False
    print("CLI v1 ships first; MCP does not gate it")


if __name__ == "__main__":
    unshipped_sibling()
    invocation_is_unsupported()
    localhost_never_http()
    error_data_is_the_union()
    cli_ships_first()
    print("qmb MCP door scaffold ok")
