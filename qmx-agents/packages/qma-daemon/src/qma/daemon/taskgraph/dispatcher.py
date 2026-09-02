"""Deterministic Task Graph scheduler and dispatcher (AD-12; FR-Q27, FR-Q28).

Decides where, when, who, and dependencies; grants ``dispatch_lease``; places
work through the Compute Router which mints one ``environment_lease`` per
available slot. Applies closed Task/Mission state with JobHandle-evidenced
terminal outcomes. Parallel workers synchronize through the Task Graph, never
chat.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from qma.core.ontology import ActorId
from qma.core.ports.compute import ComputeRequirement
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import (
    TASK_MISSION_TERMINAL_STATES,
    ExecutionEnvironmentKind,
    JobHandleState,
    TaskMissionState,
    is_task_mission_terminal,
)
from qma.daemon.envs.registry import EnvironmentLease, ExecutionEnvironmentRegistry
from qma.daemon.envs.router import ComputeRouter, PlacementDecision, QueuedPlacement
from qma.daemon.taskgraph.records import (
    MISSION_DIRECTOR_ROLE,
    DispatchLease,
    MissionRecord,
    ProposedTransition,
    TaskGraph,
    TaskRecord,
)
from qma.daemon.taskgraph.state import (
    JobHandleEvidence,
    compute_mission_state,
    validate_never_dispatched_cancel,
    validate_terminal_evidence,
)
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

if TYPE_CHECKING:
    from qma.daemon.ledgers.task import TaskLedgerStore

__all__ = [
    "DispatchDecision",
    "TaskGraphDispatcher",
    "TaskGraphStore",
    "TaskTransitionResult",
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
    queued_placement: QueuedPlacement | None = None

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
        if self.queued_placement is not None:
            payload["queued_placement"] = dict(self.queued_placement.to_payload())
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class TaskTransitionResult:
    """Daemon-authored Task transition plus derived Mission state."""

    task: TaskRecord
    mission: MissionRecord | None
    task_graph: TaskGraph
    job_handle: JobHandleEvidence | None
    dispatch_lease_retained: bool
    environment_lease_retained: bool

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "task": dict(self.task.to_payload()),
            "task_graph_id": self.task_graph.id,
            "dispatch_lease_retained": self.dispatch_lease_retained,
            "environment_lease_retained": self.environment_lease_retained,
        }
        if self.mission is not None:
            payload["mission"] = dict(self.mission.to_payload())
        if self.job_handle is not None:
            payload["job_handle"] = dict(self.job_handle.to_payload())
        return MappingProxyType(payload)


@dataclass
class TaskGraphStore:
    """In-memory Task Graph projection keyed by mission / graph id (AD-12)."""

    _by_graph_id: dict[str, TaskGraph] = field(default_factory=dict[str, TaskGraph])
    _by_mission_id: dict[str, str] = field(default_factory=dict[str, str])
    _missions: dict[str, MissionRecord] = field(default_factory=dict[str, MissionRecord])
    _dispatch_leases: dict[str, DispatchLease] = field(default_factory=dict[str, DispatchLease])
    _environment_leases: dict[str, EnvironmentLease] = field(
        default_factory=dict[str, EnvironmentLease]
    )
    _job_handles: dict[str, JobHandleEvidence] = field(default_factory=dict[str, JobHandleEvidence])
    _dispatched: set[str] = field(default_factory=set[str])
    slot_router: ComputeRouter | None = None

    def materialize(self, graph: TaskGraph) -> TaskGraph:
        """Persist the compiled Task Graph projection for its Mission."""
        self._by_graph_id[graph.id] = graph
        self._by_mission_id[graph.mission_id] = graph.id
        return graph

    def put_mission(self, mission: MissionRecord) -> MissionRecord:
        self._missions[mission.id] = mission
        return mission

    def mission(self, mission_id: str) -> MissionRecord | None:
        return self._missions.get(mission_id)

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

    def environment_lease_for(self, task_id: str) -> EnvironmentLease | None:
        return self._environment_leases.get(task_id)

    def job_handle_for(self, task_id: str) -> JobHandleEvidence | None:
        return self._job_handles.get(task_id)

    def was_dispatched(self, task_id: str) -> bool:
        return task_id in self._dispatched

    def record_lease(self, lease: DispatchLease) -> None:
        self._dispatch_leases[lease.task_id] = lease
        self._dispatched.add(lease.task_id)

    def record_environment_lease(self, lease: EnvironmentLease) -> None:
        self._environment_leases[lease.task_id] = lease

    def record_job_handle(self, evidence: JobHandleEvidence) -> None:
        self._job_handles[evidence.task_id] = evidence

    def release_leases(self, task_id: str) -> None:
        self._dispatch_leases.pop(task_id, None)
        self._environment_leases.pop(task_id, None)
        self._release_router_slot(task_id)

    def release_environment_lease(self, task_id: str) -> bool:
        """Release ``environment_lease`` only; retain ``dispatch_lease`` (FR-Q33)."""
        released = self._environment_leases.pop(task_id, None) is not None
        self._release_router_slot(task_id)
        return released

    def _release_router_slot(self, task_id: str) -> None:
        if self.slot_router is None or self.slot_router.is_unknown(task_id):
            return
        promoted = self.slot_router.release(task_id)
        if is_ok(promoted) and promoted.value is not None and promoted.value.lease is not None:
            self.record_environment_lease(promoted.value.lease)

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

    An LLM may propose non-terminal progress but can never author a terminal
    outcome — terminal transitions require JobHandle evidence via the daemon's
    evidence-bound path (FR-Q28; L35).
    """
    if proposal.from_state is not current_state:
        return policy_rejection(
            "proposed_transition",
            "proposed from_state must match current daemon state",
            from_state=proposal.from_state.value,
            current_state=current_state.value,
        )
    if proposal.to_state in TASK_MISSION_TERMINAL_STATES:
        return policy_rejection(
            "proposed_transition",
            "an LLM or Mission Director may propose but never author a terminal "
            "outcome; terminal transitions require JobHandle evidence applied by "
            "the daemon (FR-Q28; L35)",
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
    if is_task_mission_terminal(current_state):
        return policy_rejection(
            "proposed_transition",
            "each Task reaches at most one terminal state; no further transitions "
            "are accepted after a terminal outcome (FR-Q28; AD-12)",
            current_state=current_state.value,
            to_state=proposal.to_state.value,
        )
    return Ok(proposal)


class TaskGraphDispatcher:
    """Deterministic scheduler/dispatcher over materialized Task Graph state."""

    def __init__(
        self,
        *,
        store: TaskGraphStore | None = None,
        environments: ExecutionEnvironmentRegistry | None = None,
        router: ComputeRouter | None = None,
        ledgers: TaskLedgerStore | None = None,
        default_environment_kind: ExecutionEnvironmentKind | str = ExecutionEnvironmentKind.DOCKER,
    ) -> None:
        self._store = store if store is not None else TaskGraphStore()
        self._environments = (
            environments if environments is not None else ExecutionEnvironmentRegistry()
        )
        self._router = (
            router if router is not None else ComputeRouter(environments=self._environments)
        )
        if self._store.slot_router is None:
            self._store.slot_router = self._router
        if ledgers is None:
            from qma.daemon.ledgers.task import (  # noqa: PLC0415
                TaskLedgerStore as _TaskLedgerStore,
            )

            self._ledgers = _TaskLedgerStore()
        else:
            self._ledgers = ledgers
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

    @property
    def router(self) -> ComputeRouter:
        return self._router

    @property
    def ledgers(self) -> TaskLedgerStore:
        return self._ledgers

    def materialize(
        self,
        graph: TaskGraph,
        *,
        mission: MissionRecord | None = None,
    ) -> TaskGraph:
        if mission is not None:
            self._store.put_mission(mission)
        return self._store.materialize(graph)

    def dispatch_next(
        self,
        *,
        mission_id: str,
        holder_agent_id: str,
        environment_kind: ExecutionEnvironmentKind | str | None = None,
        requirement: ComputeRequirement | None = None,
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
            requirement=requirement,
        )

    def dispatch_task(
        self,
        *,
        task_id: str,
        holder_agent_id: str,
        environment_kind: ExecutionEnvironmentKind | str | None = None,
        requirement: ComputeRequirement | None = None,
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

        if requirement is not None:
            env_result = self._router.place_requirement(
                task_id=task.id,
                requirement=requirement,
            )
            kind = requirement.kind
        else:
            kind = environment_kind if environment_kind is not None else self._default_kind
            env_result = self._router.place_job(task_id=task.id, kind=kind)
        env_lease: EnvironmentLease | None = None
        env_refusal: NoEnvironment | None = None
        queued: QueuedPlacement | None = None
        if is_ok(env_result):
            env_lease = env_result.value.lease
            queued = env_result.value.queued
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
        self._ledgers.open_for_task(task)
        granted = self._ledgers.grant(lease)
        if is_refusal(granted):
            return granted
        if env_lease is not None:
            self._store.record_environment_lease(env_lease)

        seeded = self._ledgers.get(task.id)
        running = task.with_state(TaskMissionState.RUNNING)
        if seeded is not None:
            running = running.with_ledger(seeded)
        updated_graph = graph.replace_task(running)
        self._store.put(updated_graph)
        self._refresh_mission(task.mission_id, updated_graph)

        return Ok(
            DispatchDecision(
                task=running,
                dispatch_lease=lease,
                environment_lease=env_lease,
                environment_refusal=env_refusal,
                task_graph=updated_graph,
                queued_placement=queued,
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
        graph, task = located
        if is_task_mission_terminal(task.state):
            return policy_rejection(
                "dispatcher",
                "terminal Tasks cannot be reassigned (FR-Q28)",
                task_id=task_id,
                state=task.state.value,
            )
        # Transcript independence: ledger travels with the Task record.
        if task.ledger is None:
            return invalid_input(
                "ledger",
                "Task Ledger must exist for reassignment (transcript-independent)",
                task_id=task_id,
            )
        previous = self._store.lease_for(task_id)
        lease = DispatchLease(
            task_id=task.id,
            holder_agent_id=new_holder_agent_id,
            mission_id=task.mission_id,
            owner=task.owner,
        )
        self._ledgers.open_for_task(task)
        recorded = self._ledgers.record_reassignment(
            task_id=task.id,
            new_lease=lease,
            previous_holder_agent_id=(previous.holder_agent_id if previous is not None else None),
        )
        if is_refusal(recorded):
            return recorded
        self._store.record_lease(lease)
        updated = task.with_ledger(recorded.value)
        self._store.put(graph.replace_task(updated))
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
        updated_graph = graph.replace_task(updated)
        self._store.put(updated_graph)
        self._refresh_mission(task.mission_id, updated_graph)
        return Ok(updated)

    def cancel_never_dispatched(
        self,
        *,
        task_id: str,
    ) -> Result[TaskTransitionResult]:
        """Daemon-written cancel for a Task that never received a JobHandle."""
        located = self._store.find_task(task_id)
        if located is None:
            return invalid_input("task_id", "unknown Task id", given=task_id)
        graph, task = located
        if self._store.was_dispatched(task_id):
            return policy_rejection(
                "task_state",
                "Task was dispatched; cancel requires terminal JobHandle evidence (FR-Q28; AD-12)",
                task_id=task_id,
            )
        if self._store.job_handle_for(task_id) is not None:
            return policy_rejection(
                "job_handle",
                "never-dispatched cancel must not create or use a JobHandle",
                task_id=task_id,
            )
        validated = validate_never_dispatched_cancel(
            current_state=task.state,
            to_state=TaskMissionState.CANCELLED,
            was_dispatched=False,
        )
        if not is_ok(validated):
            return validated
        updated = task.with_state(TaskMissionState.CANCELLED)
        updated_graph = graph.replace_task(updated)
        self._store.put(updated_graph)
        mission = self._refresh_mission(task.mission_id, updated_graph)
        return Ok(
            TaskTransitionResult(
                task=updated,
                mission=mission,
                task_graph=updated_graph,
                job_handle=None,
                dispatch_lease_retained=False,
                environment_lease_retained=False,
            )
        )

    def apply_job_handle_evidence(
        self,
        evidence: JobHandleEvidence,
        *,
        proposed_to_state: TaskMissionState | None = None,
    ) -> Result[TaskTransitionResult]:
        """Apply JobHandle evidence to Task state; daemon alone authors outcomes.

        ``unknown`` retains both leases and blocks completion until
        :meth:`resolve_unknown_job_handle`. Terminal evidence releases leases.
        """
        located = self._store.find_task(evidence.task_id)
        if located is None:
            return invalid_input("task_id", "unknown Task id", given=evidence.task_id)
        graph, task = located
        validated = validate_terminal_evidence(
            current_state=task.state,
            evidence=evidence,
            was_dispatched=self._store.was_dispatched(evidence.task_id),
            proposed_to_state=proposed_to_state,
        )
        if not is_ok(validated):
            return validated

        new_state = validated.value
        previous_handle = self._store.job_handle_for(task.id)
        self._store.record_job_handle(evidence)
        updated = task.with_state(new_state)
        # Record abort reason on the Task Ledger when aborted → failed.
        if (
            evidence.state is JobHandleState.ABORTED
            and evidence.abort_reason
            and updated.ledger is not None
        ):
            updated = TaskRecord(
                id=updated.id,
                mission_id=updated.mission_id,
                owner=updated.owner,
                intent=updated.intent,
                inputs=dict(updated.inputs),
                refs=updated.refs,
                acceptance_criteria=updated.acceptance_criteria,
                state=updated.state,
                node_id=updated.node_id,
                node_kind=updated.node_kind,
                agent_role=updated.agent_role,
                worker_template_ref=updated.worker_template_ref,
                iteration=updated.iteration,
                retry_index=updated.retry_index,
                attempt_of=updated.attempt_of,
                ledger=updated.ledger.append(
                    {
                        "kind": "job_aborted",
                        "abort_reason": evidence.abort_reason,
                        "job_id": evidence.job_id,
                    }
                ),
            )

        retain = evidence.state is JobHandleState.UNKNOWN
        was_unknown = (
            previous_handle is not None and previous_handle.state is JobHandleState.UNKNOWN
        )
        if retain:
            # unknown holds both leases until explicit recorded resolution.
            if self._store.lease_for(task.id) is None:
                return policy_rejection(
                    "dispatch_lease",
                    "JobHandle unknown requires an existing dispatch_lease to retain "
                    "(FR-Q28; AD-12)",
                    task_id=task.id,
                )
            if self._router.lease_for(task.id) is not None:
                held = self._router.hold_unknown(task.id)
                if is_refusal(held):
                    return held
            dispatch_retained = True
            env_retained = self._store.environment_lease_for(task.id) is not None
        elif was_unknown:
            if self._router.is_unknown(task.id):
                resolved_slot = self._router.resolve_unknown(task.id, recorded=True)
                if is_refusal(resolved_slot):
                    return resolved_slot
                self._record_promoted_lease(resolved_slot.value)
            self._store.release_leases(task.id)
            dispatch_retained = False
            env_retained = False
        elif is_task_mission_terminal(new_state):
            if self._router.lease_for(task.id) is not None:
                released_slot = self._router.release(task.id)
                if is_refusal(released_slot):
                    return released_slot
                self._record_promoted_lease(released_slot.value)
            self._store.release_leases(task.id)
            dispatch_retained = False
            env_retained = False
        else:
            dispatch_retained = self._store.lease_for(task.id) is not None
            env_retained = self._store.environment_lease_for(task.id) is not None

        updated_graph = graph.replace_task(updated)
        self._store.put(updated_graph)
        mission = self._refresh_mission(task.mission_id, updated_graph)
        return Ok(
            TaskTransitionResult(
                task=updated,
                mission=mission,
                task_graph=updated_graph,
                job_handle=evidence,
                dispatch_lease_retained=dispatch_retained,
                environment_lease_retained=env_retained,
            )
        )

    def resolve_unknown_job_handle(
        self,
        evidence: JobHandleEvidence,
    ) -> Result[TaskTransitionResult]:
        """Explicit recorded resolution of an ``unknown`` JobHandle (FR-Q28).

        Accepts only terminal JobHandle evidence; releases both retained leases.
        """
        located = self._store.find_task(evidence.task_id)
        if located is None:
            return invalid_input("task_id", "unknown Task id", given=evidence.task_id)
        _graph, task = located
        if task.state is not TaskMissionState.UNKNOWN:
            return policy_rejection(
                "task_state",
                "resolve_unknown_job_handle requires Task state unknown",
                task_id=task.id,
                state=task.state.value,
            )
        current = self._store.job_handle_for(task.id)
        if current is None or current.state is not JobHandleState.UNKNOWN:
            return policy_rejection(
                "job_handle",
                "resolve_unknown_job_handle requires recorded JobHandle unknown",
                task_id=task.id,
            )
        if not evidence.is_terminal:
            return policy_rejection(
                "job_handle",
                "explicit resolution of unknown requires terminal JobHandle evidence",
                job_state=evidence.state.value,
            )
        # Temporarily treat as non-terminal current for unique-terminal check:
        # unknown is non-terminal, so validate_terminal_evidence is correct.
        return self.apply_job_handle_evidence(evidence)

    def _record_promoted_lease(self, decision: PlacementDecision | None) -> None:
        if decision is None or decision.lease is None:
            return
        self._store.record_environment_lease(decision.lease)

    def mission_state_for(self, mission_id: str) -> Result[TaskMissionState]:
        """Compute Mission state from its Tasks (never from a JobHandle)."""
        graph = self._store.for_mission(mission_id)
        if graph is None:
            return invalid_input(
                "mission_id",
                "no Task Graph projection materialized for mission",
                given=mission_id,
            )
        return Ok(compute_mission_state(tuple(t.state for t in graph.tasks)))

    def _refresh_mission(
        self,
        mission_id: str,
        graph: TaskGraph,
    ) -> MissionRecord | None:
        mission = self._store.mission(mission_id)
        derived = compute_mission_state(tuple(t.state for t in graph.tasks))
        if mission is None:
            return None
        updated = mission.with_state(derived)
        self._store.put_mission(updated)
        return updated

    @staticmethod
    def mission_director_agent_id(owner: ActorId, mission_id: str) -> str:
        """Addressable Agent id for the Mission Director role — not ontology."""
        return f"agent:{MISSION_DIRECTOR_ROLE}:{owner.value}:{mission_id}"
