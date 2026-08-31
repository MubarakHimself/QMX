"""Port cardinality, scope keys, and multi contribution-point law (AD-1; DEC-0300)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

__all__ = [
    "CONTEXT_COMPILER_SCOPE_KEY",
    "MULTI_CONTRIBUTION_POINTS",
    "PORT_CONTRACTS",
    "PORT_CONTRACT_BY_NAME",
    "RETIRED_CONTRIBUTION_POINTS",
    "Cardinality",
    "PortContract",
    "PortError",
    "has_qma_wire_schema",
    "qualified_contribution_id",
    "require_singleton_scope_key",
    "validate_contribution_point",
    "validate_multi_contribution_key",
]


class Cardinality(StrEnum):
    """Contribution cardinality declared on every port and contribution point."""

    SINGLETON = "singleton"
    MULTI = "multi"


class PortError(ValueError):
    """Raised when a port binding or contribution point violates AD-1 cardinality."""


@dataclass(frozen=True, slots=True)
class PortContract:
    """Declarative contract for one of the seven runtime ports."""

    name: str
    cardinality: Cardinality
    scope_key: str | None
    replaceable_default: bool = False

    def __post_init__(self) -> None:
        if self.cardinality is Cardinality.SINGLETON and not self.scope_key:
            raise PortError(f"singleton port {self.name!r} must declare an explicit scope key")
        if self.cardinality is Cardinality.MULTI and self.scope_key is not None:
            raise PortError(f"multi port {self.name!r} must not declare a singleton scope key")
        if self.replaceable_default and self.name != "ContextCompiler":
            raise PortError("only ContextCompiler may declare a replaceable default binding")


# Singleton scope keys (AD-1): MemoryProvider/desk, KnowledgeSource/source_id,
# ExecutionEnvironment/kind, ComputeProvider/kind, ContextCompiler/daemon.
CONTEXT_COMPILER_SCOPE_KEY: Final[str] = "daemon"

PORT_CONTRACTS: Final[tuple[PortContract, ...]] = (
    PortContract("MemoryProvider", Cardinality.SINGLETON, "desk"),
    PortContract("ModelDeployment", Cardinality.MULTI, None),
    PortContract("ExecutionEnvironment", Cardinality.SINGLETON, "kind"),
    PortContract("KnowledgeSource", Cardinality.SINGLETON, "source_id"),
    PortContract("ToolAdapter", Cardinality.MULTI, None),
    PortContract("ComputeProvider", Cardinality.SINGLETON, "kind"),
    PortContract(
        "ContextCompiler",
        Cardinality.SINGLETON,
        CONTEXT_COMPILER_SCOPE_KEY,
        replaceable_default=True,
    ),
)

PORT_CONTRACT_BY_NAME: Final[Mapping[str, PortContract]] = {
    contract.name: contract for contract in PORT_CONTRACTS
}

# Eight multi contribution points, each addressed <plugin_id>:<local_id>.
MULTI_CONTRIBUTION_POINTS: Final[frozenset[str]] = frozenset(
    {
        "tool",
        "tool_adapter",
        "hook",
        "skill",
        "graph_template",
        "model_deployment",
        "toolset",
        "worker_template",
    }
)

# Retired / undeclared points that must never register (DEC-0300; GAP-0081).
RETIRED_CONTRIBUTION_POINTS: Final[frozenset[str]] = frozenset(
    {"ui_view", "command", "mission_template"}
)

# The eight multi points are the closed set with a qma-wire schema obligation.
# A point outside this set has no schema and may not be registered.
_WIRE_SCHEMA_BACKED: Final[frozenset[str]] = MULTI_CONTRIBUTION_POINTS


def has_qma_wire_schema(contribution_point: str) -> bool:
    """Return True only for contribution points backed by a qma-wire schema."""
    return contribution_point in _WIRE_SCHEMA_BACKED


def require_singleton_scope_key(port_name: str, scope_key: str | None) -> str:
    """Validate and return the required scope key for a singleton port binding."""
    contract = PORT_CONTRACT_BY_NAME.get(port_name)
    if contract is None:
        raise PortError(f"unknown runtime port {port_name!r}")
    if contract.cardinality is not Cardinality.SINGLETON:
        raise PortError(f"{port_name} is a multi port and has no singleton scope key")
    expected = contract.scope_key
    if expected is None:
        raise PortError(f"singleton port {port_name!r} missing declared scope key")
    if scope_key is None or scope_key == "":
        raise PortError(f"singleton {port_name} rejected without explicit scope key {expected!r}")
    if scope_key != expected:
        raise PortError(f"singleton {port_name} requires scope key {expected!r}, got {scope_key!r}")
    return expected


def qualified_contribution_id(plugin_id: object, local_id: object) -> str:
    """Build the daemon-wide multi contribution key ``<plugin_id>:<local_id>``."""
    if not isinstance(plugin_id, str) or not plugin_id or ":" in plugin_id:
        raise PortError(f"plugin_id must be a non-empty string without ':'; got {plugin_id!r}")
    if not isinstance(local_id, str) or not local_id or ":" in local_id:
        raise PortError(f"local_id must be a non-empty string without ':'; got {local_id!r}")
    return f"{plugin_id}:{local_id}"


def validate_multi_contribution_key(qualified_id: object) -> tuple[str, str]:
    """Parse and accept only a fully-qualified ``<plugin_id>:<local_id>`` key."""
    if not isinstance(qualified_id, str) or qualified_id.count(":") != 1:
        raise PortError(
            f"multi contribution must be keyed <plugin_id>:<local_id>; got {qualified_id!r}"
        )
    plugin_id, local_id = qualified_id.split(":", 1)
    # Rebuild through the constructor so empty segments and embedded ':' fail.
    rebuilt = qualified_contribution_id(plugin_id, local_id)
    left, right = rebuilt.split(":", 1)
    return left, right


def validate_contribution_point(contribution_point: object) -> str:
    """Accept only a declared multi point that has a qma-wire schema.

    Rejects undeclared UI points (``ui_view``) and every retired or invented
    contribution point that lacks a qma-wire schema (DEC-0300).
    """
    if not isinstance(contribution_point, str) or not contribution_point:
        raise PortError(f"invalid contribution point {contribution_point!r}")
    if contribution_point in RETIRED_CONTRIBUTION_POINTS:
        raise PortError(
            f"contribution point {contribution_point!r} is undeclared or retired "
            f"and may not be registered"
        )
    if contribution_point not in MULTI_CONTRIBUTION_POINTS:
        raise PortError(
            f"contribution point {contribution_point!r} is not one of the eight "
            f"declared multi points"
        )
    if not has_qma_wire_schema(contribution_point):
        raise PortError(
            f"contribution point {contribution_point!r} has no qma-wire schema "
            f"and may not be registered"
        )
    return contribution_point
