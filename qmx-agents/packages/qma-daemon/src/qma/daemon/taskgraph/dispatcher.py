"""Deterministic Task Graph scheduler and dispatcher (AD-12; FR-Q27).

Decides where, when, who, and dependencies; grants ``dispatch_lease``; evaluates
``environment_lease`` through the core ExecutionEnvironment port registry.
Parallel workers synchronize through the Task Graph, never chat.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from qma.core.ontology import ActorId
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, TaskMissionState
from qma.daemon.envs.registry import EnvironmentLease, ExecutionEnvironmentRegistry
from qma.daemon.taskgraph.records import (
    MISSION_DIRECTOR_ROLE,
    DispatchLease,
    ProposedTransition,
    TaskGraph,
    TaskRecord,
)
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DispatchDecision",
    "TaskGraphDispatcher",
    "TaskGraphStore",
    "validate_proposed_transition",
]


@dataclass(frozen=True, slots=True)
class DispatchDecision:
    """Result of scheduling one ready Task."""

    task: TaskRecord
    dispatch_lease: DispatchLease
    environment_lease: EnvironmentLease | None
    environment_refusal: NoEnvironment | None
    task_graph: TaskGraph

    @property
    def environment_available(self) -> bool:
        return self.environment_lease is not None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "task_id": self.task.id,
            "dispatch_lease": dict(self.dispatch_lease.to_payload()),
            "environment_available": self.environment_available,
            "synchronization": "task_graph",
        }
        if self.environment_lease is not None:
            payload["environment_lease"] = dict(self.environment_lease.to_payload())
        if self.environment_refusal is not None:
            payload["environment_refusal"] = {
                "variant": "NoEnvironment",
                "kind": self.environment_refusal.context.get("kind"),
            }
        return MappingProxyType(payload)


@dataclass
class TaskGraphStore:
    """In-memory Task Graph projection keyed by mission / graph id (AD-12)."""

    _by_graph_id: dict[str, TaskGraph] = field(default_factory=dict[str, TaskGraph])
    _by_mission_id: dict[str, str] = field(default_factory=dict[str, str])
    _dispatch_leases: dict[str, DispatchLease] = field(
        default_factory=dict[str, DispatchLease]
    )

    def materialize(self, graph: TaskGraph) -> TaskGraph:
        """Persist the compiled Task Graph projection for its Mission."""
        self._by_graph_id[graph.id] = graph
        self._by_mission_id[graph.mission_id] = graph.id
        return graph

    def get(self, graph_id: str) -> TaskGraph | None:
        return self._by_graph_id.get(graph_id)

    def for_mission(self, mission_id: str) -> TaskGraph | None:
        graph_id = self._by_mission_id.get(mission_id)
        if graph_id is None:
            return None
        return self._by_graph_id.get(graph_id)

    def put(self, graph: TaskGraph) -> None:
        self._by_graph_id[graph.id] = graph
        self._by_mission_id[graph.mission_id] = graph.id

    def lease_for(self, task_id: str) -> DispatchLease | None:
        return self._dispatch_leases.get(task_id)

    def record_lease(self, lease: DispatchLease) -> None:
        self._dispatch_leases[lease.task_id] = lease

    def find_task(self, task_id: str) -> tuple[TaskGraph, TaskRecord] | None:
        for graph in self._by_graph_id.values():
            task = graph.task_by_id(task_id)
            if task is not None:
                return graph, task
        return None


def validate_proposed_transition(
    proposal: ProposedTransition,
    *,
    current_state: TaskMissionState,
) -> Result[ProposedTransition]:
    """Daemon-side gate: Mission Director / agents propose; daemon validates.

    Terminal-outcome authorship remains refused here at the proposal layer for
    Story 43.1; Story 43.2 binds JobHandle evidence. Non-terminal proposals that
    match the current state are accepted for recording.
    """
    if proposal.from_state is not current_state:
        return policy_rejection(
            "proposed_transition",
            "proposed from_state must match current daemon state",
            from_state=proposal.from_state.value,
            current_state=current_state.value,
        )
    terminal = {
        TaskMissionState.DONE,
        TaskMissionState.FAILED,
        TaskMissionState.CANCELLED,
    }
    if proposal.to_state in terminal:
        return policy_rejection(
            "proposed_transition",
            "an LLM or Mission Director may propose but never author a terminal "
            "outcome; the daemon alone applies terminal transitions (FR-Q27; L35)",
            to_state=proposal.to_state.value,
            proposed_by=proposal.proposed_by_agent_id,
        )
    try:
        TaskMissionState(proposal.to_state.value)
    except ValueError:
        return invalid_input(
            "to_state",
            "Task/Mission state must be one of the eight closed values",
            given=repr(proposal.to_state),
        )
    return Ok(proposal)


class TaskGraphDispatcher:
    """Deterministic scheduler/dispatcher over materialized Task Graph state."""

    def __init__(
        self,
        *,
        store: TaskGraphStore | None = None,
        environments: ExecutionEnvironmentRegistry | None = None,
        default_environment_kind: ExecutionEnvironmentKind | str = ExecutionEnvironmentKind.DOCKER,
    ) -> None:
        self._store = store if store is not None else TaskGraphStore()
        self._environments = (
            environments if environments is not None else ExecutionEnvironmentRegistry()
        )
        self._default_kind = (
            default_environment_kind.value
            if isinstance(default_environment_kind, ExecutionEnvironmentKind)
            else default_environment_kind
        )

    @property
    def store(self) -> TaskGraphStore:
        return self._store

    @property
    def environments(self) -> ExecutionEnvironmentRegistry:
        return self._environments

    def materialize(self, graph: TaskGraph) -> TaskGraph:
        return self._store.materialize(graph)

    def dispatch_next(
        self,
        *,
        mission_id: str,
        holder_agent_id: str,
        environment_kind: ExecutionEnvironmentKind | str | None = None,
    ) -> Result[DispatchDecision]:
        """Select the next ready Task, grant ``dispatch_lease``, evaluate env lease."""
        graph = self._store.for_mission(mission_id)
        if graph is None:
            return invalid_input(
                "mission_id",
                "no Task Graph projection materialized for mission",
                given=mission_id,
            )
        ready = graph.ready_tasks()
        if not ready:
            return policy_rejection(
                "dispatcher",
                "no ready Task in the Mission Task Graph",
                mission_id=mission_id,
            )
        task = ready[0]
        return self.dispatch_task(
            task_id=task.id,
            holder_agent_id=holder_agent_id,
            environment_kind=environment_kind,
        )

    def dispatch_task(
        self,
        *,
        task_id: str,
        holder_agent_id: str,
        environment_kind: ExecutionEnvironmentKind | str | None = None,
    ) -> Result[DispatchDecision]:
        located = self._store.find_task(task_id)
        if located is None:
            return invalid_input("task_id", "unknown Task id", given=task_id)
        graph, task = located
        if task.state is not TaskMissionState.READY:
            return policy_rejection(
                "dispatcher",
                "only ready Tasks may be dispatched",
                task_id=task_id,
                state=task.state.value,
            )
        if not holder_agent_id:
            return invalid_input(
                "holder_agent_id",
                "dispatch_lease requires a holder agent id",
            )

        kind = environment_kind if environment_kind is not None else self._default_kind
        env_result = self._environments.evaluate_environment_lease(
            task_id=task.id,
            kind=kind,
        )
        env_lease: EnvironmentLease | None = None
        env_refusal: NoEnvironment | None = None
        if is_ok(env_result):
            env_lease = env_result.value
        elif is_refusal(env_result) and NoEnvironment.matches(env_result):
            env_refusal = (
                env_result
                if isinstance(env_result, NoEnvironment)
                else NoEnvironment.of(kind=str(kind))
            )
        else:
            return env_result

        lease = DispatchLease(
            task_id=task.id,
            holder_agent_id=holder_agent_id,
            mission_id=task.mission_id,
            owner=task.owner,
        )
        self._store.record_lease(lease)

        running = task.with_state(TaskMissionState.RUNNING)
        updated_graph = graph.replace_task(running)
        self._store.put(updated_graph)

        return Ok(
            DispatchDecision(
                task=running,
                dispatch_lease=lease,
                environment_lease=env_lease,
                environment_refusal=env_refusal,
                task_graph=updated_graph,
            )
        )

    def reassign(
        self,
        *,
        task_id: str,
        new_holder_agent_id: str,
    ) -> Result[DispatchLease]:
        """Change ``dispatch_lease`` holder; Task Ledger stays with the Task."""
        located = self._store.find_task(task_id)
        if located is None:
            return invalid_input("task_id", "unknown Task id", given=task_id)
        _graph, task = located
        # Transcript independence: ledger travels with the Task record.
        if task.ledger is None:
            return invalid_input(
                "ledger",
                "Task Ledger must exist for reassignment (transcript-independent)",
                task_id=task_id,
            )
        lease = DispatchLease(
            task_id=task.id,
            holder_agent_id=new_holder_agent_id,
            mission_id=task.mission_id,
            owner=task.owner,
        )
        self._store.record_lease(lease)
        return Ok(lease)

    def apply_proposed_transition(
        self,
        proposal: ProposedTransition,
    ) -> Result[TaskRecord]:
        """Validate a Mission Director / agent proposal against daemon state."""
        located = self._store.find_task(proposal.target_id)
        if proposal.target_kind != "task" or located is None:
            return invalid_input(
                "target_id",
                "proposed transition target Task not found in Task Graph",
                given=proposal.target_id,
            )
        graph, task = located
        validated = validate_proposed_transition(proposal, current_state=task.state)
        if not is_ok(validated):
            return validated
        updated = task.with_state(proposal.to_state)
        self._store.put(graph.replace_task(updated))
        return Ok(updated)

    @staticmethod
    def mission_director_agent_id(owner: ActorId, mission_id: str) -> str:
        """Addressable Agent id for the Mission Director role — not ontology."""
        return f"agent:{MISSION_DIRECTOR_ROLE}:{owner.value}:{mission_id}"
