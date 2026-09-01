"""Ontology and work-vocabulary record types (AD-7; DEC-0306; FR-Q06).

Definitions only — no store, no daemon writes. Desk membership for a Quant is
the ``desk`` field on :class:`Quant`, never derived from ``ActorId`` text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from qma.core.ontology.actor_id import ActorId
from qma.core.ontology.desks import DeskSlug, OntologyError, RoleName

__all__ = [
    "PROFILE_FORBIDDEN_USES",
    "Agent",
    "Desk",
    "Goal",
    "Mission",
    "Profile",
    "Quant",
    "Role",
    "Session",
    "SlugTombstone",
    "Subagent",
    "Task",
    "Worker",
    "assert_profile_presentation_only",
    "retire_desk",
    "retire_quant",
]


PROFILE_FORBIDDEN_USES: Final[frozenset[str]] = frozenset(
    {
        "daemon_state",
        "identity_segment",
        "index",
        "filter",
        "permission_key",
        "routing_key",
    }
)


@dataclass(frozen=True, slots=True)
class Desk:
    """Organizational and workspace unit at the head of the ontology chain."""

    slug: DeskSlug
    display_name: str
    retired: bool = False


@dataclass(frozen=True, slots=True)
class Role:
    """Declarative, stateless behavioral contract (close to a system prompt).

    A per-Role permission policy is part of the Role contract and is the
    permission ceiling for Agents of this Role (FR-Q44; AD-24).
    """

    name: RoleName
    permission_policy: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "permission_policy", frozenset(self.permission_policy))


@dataclass(frozen=True, slots=True)
class Quant:
    """Persistent named organizational actor addressed by an opaque ``ActorId``.

    ``desk`` is the sole source of desk membership for consumers (FR-Q06).
    ``quant_slug`` is the store-side mint token used for collision / tombstone
    checks — never obtained by parsing ``actor_id``.
    """

    actor_id: ActorId
    desk: DeskSlug
    quant_slug: str
    role: RoleName
    name: str
    lead: bool = False
    retired: bool = False


@dataclass(frozen=True, slots=True)
class Agent:
    """Running reasoning or execution instance under a Session.

    ``effective_tool_ids`` and ``effective_permissions`` are the spawn-time
    snapshots — recorded verbatim and never recomputed for a running Agent
    (FR-Q43; AD-16).
    """

    id: str
    owner: ActorId
    session_id: str
    effective_tool_ids: frozenset[str] = frozenset()
    effective_permissions: frozenset[str] = frozenset()
    capabilities_frozen: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective_tool_ids", frozenset(self.effective_tool_ids))
        object.__setattr__(
            self,
            "effective_permissions",
            frozenset(self.effective_permissions),
        )
        object.__setattr__(self, "capabilities_frozen", True)


@dataclass(frozen=True, slots=True)
class Subagent:
    """Agent spawned by an Agent; capabilities no wider than its parent; a leaf."""

    id: str
    parent_agent_id: str
    owner: ActorId
    session_id: str
    effective_tool_ids: frozenset[str] = frozenset()
    effective_permissions: frozenset[str] = frozenset()
    capabilities_frozen: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective_tool_ids", frozenset(self.effective_tool_ids))
        object.__setattr__(
            self,
            "effective_permissions",
            frozenset(self.effective_permissions),
        )
        object.__setattr__(self, "capabilities_frozen", True)


@dataclass(frozen=True, slots=True)
class Session:
    """Run container for Agents and Subagents — not an ontology-chain link."""

    id: str
    owner: ActorId


@dataclass(frozen=True, slots=True)
class Worker:
    """Addressable execution slot — deliberately not an ontology object."""

    address: str


@dataclass(frozen=True, slots=True)
class Goal:
    """Informal intent supplied to the Mission Compiler."""

    text: str


@dataclass(frozen=True, slots=True)
class Mission:
    """Executable organizational contract owned by one Quant."""

    id: str
    owner: ActorId
    goal: Goal


@dataclass(frozen=True, slots=True)
class Task:
    """Work unit under a Mission."""

    id: str
    mission_id: str
    owner: ActorId


@dataclass(frozen=True, slots=True)
class Profile:
    """Presentation-only client configuration (DEC-0306).

    Never daemon state, never a ``scope_path`` segment, and never an index,
    filter, permission, or routing key.
    """

    display_name: str
    desk_slugs: tuple[DeskSlug, ...]


@dataclass(frozen=True, slots=True)
class SlugTombstone:
    """Permanent reservation of a retired desk or Quant slug (FR-Q06).

    The retired entity's ``ActorId`` remains stable; the tombstone prevents reuse.
    """

    slug: str
    slug_kind: Literal["desk_slug", "quant_slug"]
    actor_id: ActorId | None = None


def assert_profile_presentation_only(use: str) -> None:
    """Refuse any attempt to treat Profile as daemon/identity/routing state."""
    if use in PROFILE_FORBIDDEN_USES:
        raise OntologyError(
            f"Profile is presentation-only client configuration; "
            f"forbidden use {use!r} (never daemon state/identity/index/filter/"
            f"permission/routing)"
        )


def retire_desk(desk: Desk) -> tuple[Desk, SlugTombstone]:
    """Retire a Desk: slug stays reserved forever via tombstone."""
    if desk.retired:
        raise OntologyError(f"Desk {desk.slug.value!r} is already retired")
    retired = Desk(slug=desk.slug, display_name=desk.display_name, retired=True)
    tombstone = SlugTombstone(slug=desk.slug.value, slug_kind="desk_slug")
    return retired, tombstone


def retire_quant(quant: Quant) -> tuple[Quant, SlugTombstone]:
    """Retire a Quant: ``ActorId`` stays stable; tombstone reserves ``quant_slug``."""
    if quant.retired:
        raise OntologyError(f"Quant {quant.actor_id.value!r} is already retired")
    retired = Quant(
        actor_id=quant.actor_id,
        desk=quant.desk,
        quant_slug=quant.quant_slug,
        role=quant.role,
        name=quant.name,
        lead=quant.lead,
        retired=True,
    )
    tombstone = SlugTombstone(
        slug=quant.quant_slug,
        slug_kind="quant_slug",
        actor_id=quant.actor_id,
    )
    return retired, tombstone
