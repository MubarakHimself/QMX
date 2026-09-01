"""ToolAdapter port and Tool Registry definitions (AD-1, AD-16; FR-Q41).

One registry spans every tool kind. MCP is an adapter inside the registry —
``tool_adapter`` contributions carry no desk-and-role binding; that binding is
written only by an ``operator``-principal ``tool_adapter.write`` command.
Definitions only: the daemon owns the runtime registry.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, runtime_checkable

from qma.core.barriers.capability import (
    CAPABILITY_LADDER,
    CapabilityRung,
    capability_rung_rank,
    parse_capability_rung,
)
from qma.core.refusals.variants import OperatorPrincipalRequired
from qma.core.vocabulary.enums import PrincipalClass
from qma.core.vocabulary.registry import VocabularyError
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "LEAF_BLOCKED_TOOL_TAGS",
    "TOOL_ADAPTER_WRITE_COMMAND",
    "TOOL_KINDS",
    "TOOL_KIND_DEFAULT_RUNG",
    "AvailabilityCheck",
    "ToolAdapter",
    "ToolAdapterBinding",
    "ToolAdapterRecord",
    "ToolKind",
    "ToolRecord",
    "ToolsetRecord",
    "default_rung_for_kind",
    "is_leaf_blocked_tool",
    "narrow_toolset_ids",
    "parse_tool_kind",
    "select_lowest_capable",
    "skill_grants_tool_or_capability",
    "subagent_inherited_tool_ids",
    "write_tool_adapter_binding",
]

TOOL_ADAPTER_WRITE_COMMAND: Final[str] = "tool_adapter.write"

# Subagent leaf may not hold delegation or memory-write tools (AD-16; FR-Q41).
LEAF_BLOCKED_TOOL_TAGS: Final[frozenset[str]] = frozenset(
    {
        "delegation",
        "memory_write",
    }
)

AvailabilityCheck = Callable[[], bool]


class ToolKind(StrEnum):
    """Closed tool kinds that all enter the one Tool Registry (AD-16; FR-Q41)."""

    NATIVE = "native"
    CLI = "cli"
    PLUGIN = "plugin"
    MCP_ADAPTER = "mcp_adapter"
    BROWSER = "browser"
    COMPUTER_USE = "computer_use"
    BACKTEST = "backtest"


TOOL_KINDS: Final[tuple[ToolKind, ...]] = tuple(ToolKind)

TOOL_KIND_DEFAULT_RUNG: Final[Mapping[ToolKind, CapabilityRung]] = MappingProxyType(
    {
        ToolKind.NATIVE: CapabilityRung.API_OR_STRUCTURED_TOOL,
        ToolKind.CLI: CapabilityRung.CLI,
        ToolKind.PLUGIN: CapabilityRung.API_OR_STRUCTURED_TOOL,
        ToolKind.MCP_ADAPTER: CapabilityRung.API_OR_STRUCTURED_TOOL,
        ToolKind.BROWSER: CapabilityRung.BROWSER_AUTOMATION,
        ToolKind.COMPUTER_USE: CapabilityRung.VISUAL_BROWSER_OR_COMPUTER_USE,
        ToolKind.BACKTEST: CapabilityRung.CONTAINERIZED_PROGRAM,
    }
)


@runtime_checkable
class ToolAdapter(Protocol):
    """Definitions-only ToolAdapter seam; keyed ``<plugin_id>:<local_id>``.

    Cardinality: multi (see ``PORT_CONTRACTS``). Desk-and-role binding is never
    part of the contribution — operator ``tool_adapter.write`` owns that.
    """


def parse_tool_kind(value: ToolKind | str) -> ToolKind:
    """Parse a closed ToolKind; invented values fail."""
    if isinstance(value, ToolKind):
        return value
    try:
        return ToolKind(value)
    except ValueError as exc:
        raise VocabularyError(f"{value!r} is not a ToolKind (AD-16; FR-Q41)") from exc


def default_rung_for_kind(kind: ToolKind | str) -> CapabilityRung:
    """Return the default capability rung for a tool kind."""
    return TOOL_KIND_DEFAULT_RUNG[parse_tool_kind(kind)]


def skill_grants_tool_or_capability() -> bool:
    """An appended Skill is knowledge only — never a tool or capability grant."""
    return False


def is_leaf_blocked_tool(
    tool_id: str,
    *,
    tags: Sequence[str] | frozenset[str] | set[str] = (),
) -> bool:
    """True when a Subagent leaf must not inherit this tool."""
    lowered = {tag.lower() for tag in tags}
    if lowered & LEAF_BLOCKED_TOOL_TAGS:
        return True
    token = tool_id.rsplit(":", 1)[-1].lower()
    return token in LEAF_BLOCKED_TOOL_TAGS or any(
        blocked in token for blocked in LEAF_BLOCKED_TOOL_TAGS
    )


@dataclass(frozen=True, slots=True)
class ToolRecord:
    """One Tool Registry entry — every kind uses this shape (AD-16; FR-Q41).

    ``check_fn`` is the availability preflight: an unrunnable tool is excluded
    before its schema reaches a model. Computer-use entries fail that check
    until a ``desktop`` ExecutionEnvironment is registered (GAP-0070 deferred).
    """

    tool_id: str
    kind: ToolKind
    capability_rung: CapabilityRung
    schema: Mapping[str, object] = field(default_factory=dict[str, object])
    check_fn: AvailabilityCheck | None = None
    acts: frozenset[str] = field(default_factory=frozenset[str])
    tags: frozenset[str] = field(default_factory=frozenset[str])
    plugin_id: str | None = None
    requires_environment_kind: str | None = None
    money_path_act: str | None = None

    def __post_init__(self) -> None:
        if ":" not in self.tool_id:
            msg = "tool_id must be fully-qualified <plugin_id>:<local_id> (AD-16; FR-Q41)"
            raise VocabularyError(msg)
        if self.plugin_id is None:
            object.__setattr__(self, "plugin_id", self.tool_id.split(":", 1)[0])
        if self.kind is ToolKind.COMPUTER_USE and self.requires_environment_kind is None:
            object.__setattr__(self, "requires_environment_kind", "desktop")
        # Freeze schema mapping.
        object.__setattr__(self, "schema", MappingProxyType(dict(self.schema)))
        object.__setattr__(self, "acts", frozenset(self.acts))
        object.__setattr__(self, "tags", frozenset(self.tags))

    def is_available(self) -> bool:
        """Run ``check_fn``; missing check means available."""
        if self.check_fn is None:
            return True
        return bool(self.check_fn())


@dataclass(frozen=True, slots=True)
class ToolAdapterRecord:
    """Plugin-contributed MCP/adapter contribution without desk-role binding."""

    adapter_id: str
    advertised_tool_ids: tuple[str, ...] = ()
    advertised_acts: tuple[str, ...] = ()
    plugin_id: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict[str, object])

    def __post_init__(self) -> None:
        if ":" not in self.adapter_id:
            msg = "adapter_id must be fully-qualified <plugin_id>:<local_id> (AD-16; FR-Q41)"
            raise VocabularyError(msg)
        if self.plugin_id is None:
            object.__setattr__(self, "plugin_id", self.adapter_id.split(":", 1)[0])
        object.__setattr__(
            self,
            "advertised_tool_ids",
            tuple(self.advertised_tool_ids),
        )
        object.__setattr__(self, "advertised_acts", tuple(self.advertised_acts))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        # Binding fields must never ride the contribution (AD-16).
        for forbidden in ("desk", "role", "desk_and_role", "binding"):
            if forbidden in self.metadata:
                msg = (
                    f"tool_adapter contribution may not declare {forbidden!r}; "
                    f"binding is written only via {TOOL_ADAPTER_WRITE_COMMAND} "
                    "(AD-16; FR-Q41)"
                )
                raise VocabularyError(msg)


@dataclass(frozen=True, slots=True)
class ToolAdapterBinding:
    """Operator-written desk-and-role binding for a ``tool_adapter`` (AD-16)."""

    adapter_id: str
    desk: str
    role: str

    def __post_init__(self) -> None:
        if not self.adapter_id or ":" not in self.adapter_id:
            msg = "adapter_id must be fully-qualified (AD-16)"
            raise VocabularyError(msg)
        if not self.desk.strip():
            msg = "desk must be a non-empty string (AD-16)"
            raise VocabularyError(msg)
        if not self.role.strip():
            msg = "role must be a non-empty string (AD-16)"
            raise VocabularyError(msg)

    @property
    def binding_key(self) -> str:
        return f"{self.adapter_id}@{self.desk}/{self.role}"


@dataclass(frozen=True, slots=True)
class ToolsetRecord:
    """Versioned definition-store record of fully-qualified tool ids (AD-16)."""

    toolset_id: str
    version: str
    tool_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if ":" not in self.toolset_id:
            msg = "toolset_id must be fully-qualified <plugin_id>:<local_id> (AD-16; FR-Q41)"
            raise VocabularyError(msg)
        if not self.version.strip():
            msg = "toolset version must be a non-empty string (AD-16)"
            raise VocabularyError(msg)
        for tool_id in self.tool_ids:
            if ":" not in tool_id:
                msg = (
                    f"toolset lists fully-qualified tool ids only; got {tool_id!r} (AD-16; FR-Q41)"
                )
                raise VocabularyError(msg)
        object.__setattr__(self, "tool_ids", tuple(dict.fromkeys(self.tool_ids)))

    def as_frozenset(self) -> frozenset[str]:
        return frozenset(self.tool_ids)


def write_tool_adapter_binding(
    adapter: ToolAdapterRecord,
    *,
    desk: str,
    role: str,
    principal: PrincipalClass | str,
) -> Result[ToolAdapterBinding]:
    """Operator-only desk-and-role binding write (``tool_adapter.write``)."""
    command = TOOL_ADAPTER_WRITE_COMMAND
    if isinstance(principal, PrincipalClass):
        resolved = principal
    else:
        try:
            resolved = PrincipalClass(principal)
        except ValueError:
            return OperatorPrincipalRequired.of(
                command=command,
                principal_class=str(principal),
            )
    if resolved is not PrincipalClass.OPERATOR:
        return OperatorPrincipalRequired.of(
            command=command,
            principal_class=resolved.value,
        )
    try:
        binding = ToolAdapterBinding(
            adapter_id=adapter.adapter_id,
            desk=desk,
            role=role,
        )
    except VocabularyError as exc:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "tool_adapter_binding",
                "reason": str(exc),
                "command": command,
            },
        )
    return Ok(binding)


def narrow_toolset_ids(
    role_grant: Sequence[str] | frozenset[str] | set[str],
    mission_subset: Sequence[str] | frozenset[str] | set[str] | None = None,
) -> Result[frozenset[str]]:
    """Mission may only narrow a Role-granted toolset — never widen it."""
    granted = frozenset(role_grant)
    for tool_id in granted:
        if ":" not in tool_id:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "tool_id",
                    "reason": "tool ids must be fully-qualified <plugin_id>:<local_id>",
                    "given": tool_id,
                },
            )
    if mission_subset is None:
        return Ok(granted)
    proposed = frozenset(mission_subset)
    extras = proposed - granted
    if extras:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "mission_toolset",
                "reason": "Mission may only narrow a Role-granted toolset (AD-16; FR-Q41)",
                "extras": sorted(extras),
            },
        )
    return Ok(proposed)


def subagent_inherited_tool_ids(
    parent_tool_ids: Sequence[str] | frozenset[str] | set[str],
    *,
    tool_tags: Mapping[str, Sequence[str]] | None = None,
) -> frozenset[str]:
    """Subagent inherits no more than its parent; leaf blocks delegation/memory-write."""
    tags_by_id = tool_tags or {}
    inherited: list[str] = []
    for tool_id in parent_tool_ids:
        tags = tags_by_id.get(tool_id, ())
        if is_leaf_blocked_tool(tool_id, tags=tags):
            continue
        inherited.append(tool_id)
    return frozenset(inherited)


def select_lowest_capable(
    candidates: Sequence[ToolRecord],
) -> ToolRecord | None:
    """Six-rung ladder: lowest capable rung wins (AD-16; P-10; FR-Q41)."""
    if not candidates:
        return None
    # Pin ladder identity so selection cannot drift from the code-declared rungs.
    if len(CAPABILITY_LADDER) != 6:
        msg = "capability ladder must declare exactly six rungs"
        raise VocabularyError(msg)
    ranked = sorted(
        candidates,
        key=lambda tool: (
            capability_rung_rank(parse_capability_rung(tool.capability_rung)),
            tool.tool_id,
        ),
    )
    return ranked[0]
