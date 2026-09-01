"""Graph Template / Loop / Skill control primitives (AD-13; FR-Q29).

Three primitives stand and are never interchanged:

* **Graph Template** — authored, plugin-contributed, versioned, stateless.
* **Loop** — node kind whose ``stopping_condition``, ``budget`` and
  ``escalation`` are runtime-owned (daemon Task Graph node state).
* **Skill** — reusable procedure and knowledge with progressive disclosure;
  ``Skill != Loop``, though a Skill may invoke a Loop.

Only ``task``, ``agent`` and ``loop`` emit Tasks. Every other node kind is
daemon-evaluated node state carrying neither ``dispatch_lease`` nor a ledger.
There is no Mission Template registry in v1 (GAP-0084) and no graph-engine
selection (GAP-0086).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qma.core.vocabulary.enums import TASK_EMITTING_NODE_KINDS, NodeKind

__all__ = [
    "DAEMON_EVALUATED_NODE_KINDS",
    "DEFERRED_GRAPH_EXCLUSIONS",
    "ControlPrimitive",
    "Skill",
    "emits_task",
    "holds_dispatch_lease",
    "is_loop_kind",
    "is_skill_distinct_from_loop",
    "node_carries_ledger",
]


class ControlPrimitive(StrEnum):
    """The three AD-13 control primitives — never collapsed into one kind."""

    GRAPH_TEMPLATE = "graph_template"
    LOOP = "loop"
    SKILL = "skill"


DAEMON_EVALUATED_NODE_KINDS: Final[frozenset[NodeKind]] = frozenset(
    kind for kind in NodeKind if kind not in TASK_EMITTING_NODE_KINDS
)

# Explicit Deferred exclusions — never invent implementations here (FR-Q29).
DEFERRED_GRAPH_EXCLUSIONS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "GAP-0084": "Mission Template registry beside Graph Templates — deferred",
        "GAP-0086": "graph-engine implementation selection — deferred",
    }
)


@dataclass(frozen=True, slots=True)
class Skill:
    """Reusable procedure and knowledge with progressive disclosure (AD-13).

    Distinct from Loop: a Skill may *invoke* a Loop via ``loop_ref`` but is
    never itself a Loop and never grants a tool or capability by registration.
    Addressed ``<plugin_id>:<local_id>`` like other multi contributions.
    """

    qualified_id: str
    version: str
    summary: str
    body: str = ""
    loop_ref: str | None = None
    disclosures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if ":" not in self.qualified_id:
            msg = "skill id must be fully-qualified <plugin_id>:<local_id> (AD-13; FR-Q29)"
            raise ValueError(msg)
        if self.loop_ref is not None and not self.loop_ref:
            msg = "skill loop_ref, when set, must be a non-empty Loop Registry id"
            raise ValueError(msg)

    @property
    def invokes_loop(self) -> bool:
        return self.loop_ref is not None

    @property
    def is_loop(self) -> bool:
        """Skills are never Loops (AD-13; Skill != Loop)."""
        return False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "qualified_id": self.qualified_id,
                "version": self.version,
                "summary": self.summary,
                "body": self.body,
                "loop_ref": self.loop_ref,
                "disclosures": list(self.disclosures),
                "control_primitive": ControlPrimitive.SKILL.value,
                "is_loop": False,
                "invokes_loop": self.invokes_loop,
                "grants_capability": False,
            }
        )


def emits_task(kind: NodeKind) -> bool:
    """Only ``task``, ``agent`` and ``loop`` emit Tasks (AD-13)."""
    return kind in TASK_EMITTING_NODE_KINDS


def holds_dispatch_lease(kind: NodeKind) -> bool:
    """Daemon-evaluated kinds hold neither lease (AD-13)."""
    return emits_task(kind)


def node_carries_ledger(kind: NodeKind) -> bool:
    """Daemon-evaluated kinds carry no Task Ledger (AD-13)."""
    return emits_task(kind)


def is_loop_kind(kind: NodeKind) -> bool:
    return kind is NodeKind.LOOP


def is_skill_distinct_from_loop(skill: Skill) -> bool:
    """Executable guard: Skill never collapses into Loop."""
    return skill.is_loop is False and ControlPrimitive.SKILL.value == "skill"
