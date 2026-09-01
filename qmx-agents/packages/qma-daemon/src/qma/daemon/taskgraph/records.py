"""Mission, Task, and Task Graph records (AD-12; FR-Q27).

Daemon-owned durable work state. A Mission has no global form and never stores
desk — desk is derived from the owning Quant. A Task is transcript-independent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant
from qma.core.vocabulary.enums import (
    GraphArtifactKind,
    NodeKind,
    TaskMissionState,
)

__all__ = [
    "MISSION_DIRECTOR_ROLE",
    "RESERVED_APPROVAL_ROUTE_OPERATOR",
    "DispatchLease",
    "GraphTemplate",
    "MissionRecord",
    "ProposedTransition",
    "TaskGraph",
    "TaskGraphNode",
    "TaskLedger",
    "TaskRecord",
    "as_string_tuple",
    "derive_mission_desk",
]


RESERVED_APPROVAL_ROUTE_OPERATOR: Final[str] = "operator"
MISSION_DIRECTOR_ROLE: Final[str] = "mission_director"


@dataclass(frozen=True, slots=True)
class GraphTemplate:
    """Authored, plugin-contributed, versioned, stateless topology (AD-13).

    Never interchanged with a Task Graph. Addressed ``<plugin_id>:<local_id>``.
    A run never mutates an instance; nodes/edges are frozen snapshots.
    """

    qualified_id: str
    version: str
    nodes: tuple[Mapping[str, object], ...] = ()
    edges: tuple[Mapping[str, object], ...] = ()
    artifact_kind: GraphArtifactKind = GraphArtifactKind.GRAPH_TEMPLATE

    def __post_init__(self) -> None:
        if ":" not in self.qualified_id:
            msg = "graph_template id must be fully-qualified <plugin_id>:<local_id> (AD-13; FR-Q29)"
            raise ValueError(msg)
        if self.artifact_kind is not GraphArtifactKind.GRAPH_TEMPLATE:
            msg = "Graph Template artifact_kind must be graph_template, never task_graph"
            raise ValueError(msg)
        # Freeze contribution maps so a run cannot mutate authored topology.
        frozen_nodes = tuple(MappingProxyType(dict(node)) for node in self.nodes)
        frozen_edges = tuple(MappingProxyType(dict(edge)) for edge in self.edges)
        object.__setattr__(self, "nodes", frozen_nodes)
        object.__setattr__(self, "edges", frozen_edges)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "qualified_id": self.qualified_id,
                "version": self.version,
                "artifact_kind": self.artifact_kind.value,
                "nodes": [dict(n) for n in self.nodes],
                "edges": [dict(e) for e in self.edges],
                "stateless": True,
                "runtime_state": None,
            }
        )


@dataclass(frozen=True, slots=True)
class TaskLedger:
    """Append-only Task-owned ledger, independent of any Agent transcript (CT-51)."""

    task_id: str
    entries: tuple[Mapping[str, object], ...] = ()

    def append(self, entry: Mapping[str, object]) -> TaskLedger:
        return TaskLedger(task_id=self.task_id, entries=(*self.entries, dict(entry)))

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "task_id": self.task_id,
                "entries": [dict(e) for e in self.entries],
            }
        )


@dataclass(frozen=True, slots=True)
class TaskRecord:
    """Transcript-independent work unit under a Mission (AD-12; FR-Q27)."""

    id: str
    mission_id: str
    owner: ActorId
    intent: str
    inputs: Mapping[str, object] = field(default_factory=dict[str, object])
    refs: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    state: TaskMissionState = TaskMissionState.PENDING
    node_id: str | None = None
    node_kind: NodeKind | None = None
    agent_role: str | None = None
    worker_template_ref: str | None = None
    iteration: int = 0
    retry_index: int = 0
    attempt_of: str | None = None
    ledger: TaskLedger | None = None

    def __post_init__(self) -> None:
        if self.ledger is None:
            object.__setattr__(self, "ledger", TaskLedger(task_id=self.id))
        elif self.ledger.task_id != self.id:
            msg = "TaskLedger.task_id must equal TaskRecord.id"
            raise ValueError(msg)

    @property
    def is_decomposition(self) -> bool:
        return self.agent_role == MISSION_DIRECTOR_ROLE

    @property
    def is_mission_director_task(self) -> bool:
        return self.is_decomposition

    def with_state(self, state: TaskMissionState) -> TaskRecord:
        return TaskRecord(
            id=self.id,
            mission_id=self.mission_id,
            owner=self.owner,
            intent=self.intent,
            inputs=dict(self.inputs),
            refs=self.refs,
            acceptance_criteria=self.acceptance_criteria,
            state=state,
            node_id=self.node_id,
            node_kind=self.node_kind,
            agent_role=self.agent_role,
            worker_template_ref=self.worker_template_ref,
            iteration=self.iteration,
            retry_index=self.retry_index,
            attempt_of=self.attempt_of,
            ledger=self.ledger,
        )

    def to_payload(self) -> Mapping[str, object]:
        ledger = self.ledger if self.ledger is not None else TaskLedger(task_id=self.id)
        return MappingProxyType(
            {
                "id": self.id,
                "mission_id": self.mission_id,
                "owner": self.owner.value,
                "intent": self.intent,
                "inputs": dict(self.inputs),
                "refs": list(self.refs),
                "acceptance_criteria": list(self.acceptance_criteria),
                "state": self.state.value,
                "node_id": self.node_id,
                "node_kind": self.node_kind.value if self.node_kind is not None else None,
                "agent_role": self.agent_role,
                "worker_template_ref": self.worker_template_ref,
                "iteration": self.iteration,
                "retry_index": self.retry_index,
                "attempt_of": self.attempt_of,
                "ledger": dict(ledger.to_payload()),
                "transcript_independent": True,
            }
        )


@dataclass(frozen=True, slots=True)
class MissionRecord:
    """Executable organizational contract owned by exactly one Quant (AD-12).

    Desk is derived from the owning Quant and is never stored on the record.
    """

    id: str
    owner: ActorId
    goal: Goal
    intent: str
    scope: str
    constraints: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    capabilities: tuple[str, ...]
    success_criteria: tuple[str, ...]
    outputs: tuple[str, ...]
    verification: str
    budget: Mapping[str, object]
    escalation: str
    termination_criteria: tuple[str, ...]
    approval_route: str | None = None
    state: TaskMissionState = TaskMissionState.PENDING
    graph_template_ref: str | None = None
    task_graph_id: str | None = None

    def desk_for(self, owner_quant: Quant) -> DeskSlug:
        """Derive desk from the owning Quant record — never from Mission fields."""
        if owner_quant.actor_id != self.owner:
            msg = "desk derivation requires the Mission's owning Quant record"
            raise ValueError(msg)
        return owner_quant.desk

    def with_state(self, state: TaskMissionState) -> MissionRecord:
        return MissionRecord(
            id=self.id,
            owner=self.owner,
            goal=self.goal,
            intent=self.intent,
            scope=self.scope,
            constraints=self.constraints,
            evidence_requirements=self.evidence_requirements,
            capabilities=self.capabilities,
            success_criteria=self.success_criteria,
            outputs=self.outputs,
            verification=self.verification,
            budget=dict(self.budget),
            escalation=self.escalation,
            termination_criteria=self.termination_criteria,
            approval_route=self.approval_route,
            state=state,
            graph_template_ref=self.graph_template_ref,
            task_graph_id=self.task_graph_id,
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "id": self.id,
                "owner": self.owner.value,
                "goal": self.goal.text,
                "intent": self.intent,
                "scope": self.scope,
                "constraints": list(self.constraints),
                "evidence_requirements": list(self.evidence_requirements),
                "capabilities": list(self.capabilities),
                "success_criteria": list(self.success_criteria),
                "outputs": list(self.outputs),
                "verification": self.verification,
                "budget": dict(self.budget),
                "escalation": self.escalation,
                "termination_criteria": list(self.termination_criteria),
                "approval_route": self.approval_route,
                "state": self.state.value,
                "graph_template_ref": self.graph_template_ref,
                "task_graph_id": self.task_graph_id,
                # desk is deliberately absent — derived from Quant (DEC-0311)
            }
        )


@dataclass(frozen=True, slots=True)
class TaskGraphNode:
    """Daemon-evaluated Task Graph node carrying node state (AD-13).

    Non-emitting kinds hold neither ``dispatch_lease`` nor a ledger.
    """

    id: str
    kind: NodeKind
    state: TaskMissionState = TaskMissionState.PENDING
    config: Mapping[str, object] = field(default_factory=dict[str, object])

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", MappingProxyType(dict(self.config)))

    @property
    def emits_task(self) -> bool:
        return self.kind in {NodeKind.TASK, NodeKind.AGENT, NodeKind.LOOP}

    @property
    def holds_dispatch_lease(self) -> bool:
        return self.emits_task

    @property
    def carries_ledger(self) -> bool:
        return self.emits_task

    @property
    def is_daemon_evaluated(self) -> bool:
        return not self.emits_task


@dataclass(frozen=True, slots=True)
class TaskGraph:
    """Deterministic persisted daemon work state — the only place work lives."""

    id: str
    mission_id: str
    nodes: tuple[TaskGraphNode, ...] = ()
    tasks: tuple[TaskRecord, ...] = ()
    artifact_kind: GraphArtifactKind = GraphArtifactKind.TASK_GRAPH
    graph_template_ref: str | None = None
    state: TaskMissionState = TaskMissionState.PENDING

    def __post_init__(self) -> None:
        if self.artifact_kind is not GraphArtifactKind.TASK_GRAPH:
            msg = "Task Graph artifact_kind must be task_graph, never graph_template"
            raise ValueError(msg)

    def task_by_id(self, task_id: str) -> TaskRecord | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def ready_tasks(self) -> tuple[TaskRecord, ...]:
        return tuple(t for t in self.tasks if t.state is TaskMissionState.READY)

    def replace_task(self, task: TaskRecord) -> TaskGraph:
        updated = tuple(task if existing.id == task.id else existing for existing in self.tasks)
        return TaskGraph(
            id=self.id,
            mission_id=self.mission_id,
            nodes=self.nodes,
            tasks=updated,
            artifact_kind=self.artifact_kind,
            graph_template_ref=self.graph_template_ref,
            state=self.state,
        )

    def append_task(self, task: TaskRecord) -> TaskGraph:
        """Attach a newly minted Task (e.g. a loop iteration) without mutation."""
        if self.task_by_id(task.id) is not None:
            msg = f"Task {task.id!r} already present on Task Graph {self.id!r}"
            raise ValueError(msg)
        return TaskGraph(
            id=self.id,
            mission_id=self.mission_id,
            nodes=self.nodes,
            tasks=(*self.tasks, task),
            artifact_kind=self.artifact_kind,
            graph_template_ref=self.graph_template_ref,
            state=(
                self.state if self.state is not TaskMissionState.PENDING else TaskMissionState.READY
            ),
        )

    def node_by_id(self, node_id: str) -> TaskGraphNode | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "id": self.id,
                "mission_id": self.mission_id,
                "artifact_kind": self.artifact_kind.value,
                "graph_template_ref": self.graph_template_ref,
                "state": self.state.value,
                "nodes": [
                    {
                        "id": n.id,
                        "kind": n.kind.value,
                        "state": n.state.value,
                        "config": dict(n.config),
                    }
                    for n in self.nodes
                ],
                "tasks": [dict(t.to_payload()) for t in self.tasks],
            }
        )


@dataclass(frozen=True, slots=True)
class DispatchLease:
    """Per-Task lease granting Task Ledger append rights (AD-9 / AD-12)."""

    task_id: str
    holder_agent_id: str
    mission_id: str
    owner: ActorId

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "lease": "dispatch_lease",
                "task_id": self.task_id,
                "holder_agent_id": self.holder_agent_id,
                "mission_id": self.mission_id,
                "owner": self.owner.value,
            }
        )


@dataclass(frozen=True, slots=True)
class ProposedTransition:
    """LLM/agent-proposed Task or Mission state change — never self-authoring.

    The daemon alone validates and applies. Mission Director reaches state only
    through these proposed transitions (FR-Q27; L35).
    """

    target_kind: Literal["task", "mission"]
    target_id: str
    from_state: TaskMissionState
    to_state: TaskMissionState
    proposed_by_agent_id: str
    rationale: str = ""


def derive_mission_desk(mission: MissionRecord, owner_quant: Quant) -> DeskSlug:
    """Public helper: Mission desk is always the owning Quant's desk."""
    return mission.desk_for(owner_quant)


def as_string_tuple(values: Sequence[str] | None) -> tuple[str, ...]:
    if not values:
        return ()
    return tuple(values)
