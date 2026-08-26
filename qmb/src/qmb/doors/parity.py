"""Door-parity catalog for the shipped CLI and Python API doors (B-1, AR-58).

Every product capability lives once in the library. The CLI tree and the
Python API door must name the same capabilities and call the same library
entry points. MCP is scaffolded and stays out of the door-set until it ships.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Final

__all__ = [
    "CAPABILITY_LIBRARY",
    "CLI_ADAPTATION_COMMANDS",
    "MCP_IN_DOOR_SET",
    "SHIPPED_DOORS",
    "capability_gaps",
    "door_parity_identity",
    "flatten_capabilities",
    "required_library_names",
]

SHIPPED_DOORS: Final[tuple[str, ...]] = ("cli", "api")
CLI_ADAPTATION_COMMANDS: Final[tuple[str, ...]] = ("version",)
MCP_IN_DOOR_SET: Final[bool] = False

# Product command -> library names that implement it. A command on the CLI
# tree missing from this catalog, or a catalog entry whose names are missing
# from the Python API door, is a door-parity failure (B-1).
CAPABILITY_LIBRARY: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "backtest.run": ("compile_run_config", "spawn_run", "run"),
        "data.download": ("DATA_COMMANDS", "data_front_identity"),
        "data.verify": ("DATA_COMMANDS", "data_front_identity", "verify"),
        "data.gap-check": ("DATA_COMMANDS", "data_front_identity", "gap_check"),
        "data.list": ("DATA_COMMANDS", "data_front_identity", "list_data"),
        "data.catalog": ("DATA_COMMANDS", "data_front_identity", "list_data", "catalog"),
        "data.generate": ("DATA_COMMANDS", "data_front_identity"),
        "optimize.run": ("compile_run_config", "spawn_run", "parameter_space_from_bot"),
        "optimize.space": ("parameter_space_from_bot",),
        "ledger.merge": ("read_merge_view",),
        "ledger.bar": ("read_book_bar",),
        "config.compile": ("compile_run_config",),
        "config.show": ("run_config_identity",),
    }
)


def flatten_capabilities() -> tuple[str, ...]:
    """Product capabilities in catalog order (CLI ``group.command`` names)."""
    return tuple(CAPABILITY_LIBRARY)


def required_library_names() -> frozenset[str]:
    """Library attributes every shipped door must expose for the catalog."""
    names: set[str] = set()
    for entrypoints in CAPABILITY_LIBRARY.values():
        names.update(entrypoints)
    return frozenset(names)


def capability_gaps(
    *,
    cli: Iterable[str],
    api_names: Iterable[str],
) -> dict[str, tuple[str, ...]]:
    """Symmetric drift between the CLI tree, this catalog, and the API door.

    ``missing_cli`` / ``extra_cli`` are catalog-vs-CLI. ``missing_api`` is a
    catalog library name absent from the Python API door. Any non-empty tuple
    is a parity failure: a capability on one door missing from the other.
    """
    catalog = frozenset(CAPABILITY_LIBRARY)
    cli_set = frozenset(cli)
    api_set = frozenset(api_names)
    return {
        "extra_cli": tuple(sorted(cli_set - catalog)),
        "missing_api": tuple(sorted(required_library_names() - api_set)),
        "missing_cli": tuple(sorted(catalog - cli_set)),
    }


def door_parity_identity() -> dict[str, object]:
    """Identity-bearing door-parity fields. Package SemVer is omitted."""
    return {
        "adaptation": ("parsing", "transport", "refusal-rendering", "autocomplete"),
        "capabilities": flatten_capabilities(),
        "mcp_in_door_set": MCP_IN_DOOR_SET,
        "shipped_doors": SHIPPED_DOORS,
    }
