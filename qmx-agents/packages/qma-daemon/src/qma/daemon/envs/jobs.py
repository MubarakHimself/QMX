"""Durable JobHandle operations and daemon-only Task mapping (CT-46; FR-Q51).

``submit`` queues and returns immediately. ``JobHandle.attach`` is a live view
that does not change identity. ``wait`` signals; the durable store is truth.
``JobHandle.reattach`` restores that store after detach or restart. ``wake``
targets the owning Quant mailbox stored at submit. ``cancel`` is explicit.
``stream`` is harness telemetry, never a ledger. Mapping onto Task state is
applied here through the dispatcher alone (DEC-0316).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from qma.core.ontology import ActorId, Quant
from qma.core.ports.compute import ComputeRequirement
from qma.core.ports.jobs import (
    JOB_HANDLE_OPERATIONS,
    JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND,
    JobHandle,
    is_abort_trigger,
    is_unknown_trigger,
    outcome_for_trigger,
    wake_mailbox_for,
)
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary.enums import (
    JOB_HANDLE_TERMINAL_STATES,
    ExecutionEnvironmentKind,
    JobHandleState,
    MessageKind,
    PrincipalClass,
    is_job_handle_terminal,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.envs.router import ComputeRouter
from qma.daemon.taskgraph.dispatcher import TaskGraphDispatcher, TaskTransitionResult
from qma.daemon.taskgraph.state import JobHandleEvidence
from qma.wire.principals import authorize_wire_command
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "JOB_HANDLE_OPERATIONS",
    "JobHandleService",
    "JobHandleStore",
    "JobStreamEvent",
    "JobWaitResult",
    "JobWake",
]


_FROM_QUEUED: frozenset[JobHandleState] = frozenset(
    {
        JobHandleState.RUNNING,
        JobHandleState.CANCELLED,
        JobHandleState.ABORTED,
        JobHandleState.UNKNOWN,
    }
)
_FROM_RUNNING: frozenset[JobHandleState] = frozenset(
    {
        JobHandleState.DONE,
        JobHandleState.FAILED,
        JobHandleState.CANCELLED,
        JobHandleState.ABORTED,
        JobHandleState.UNKNOWN,
    }
)


def _parse_state(state: JobHandleState | str) -> Result[JobHandleState]:
    if isinstance(state, JobHandleState):
        return Ok(state)
    try:
        return Ok(parse_closed(JobHandleState, state))
    except VocabularyError as exc:
        return invalid_input("state", str(exc), given=repr(state))


def _parse_principal(principal: PrincipalClass | str) -> Result[PrincipalClass]:
    if isinstance(principal, PrincipalClass):
        return Ok(principal)
    try:
        return Ok(parse_closed(PrincipalClass, principal))
    except VocabularyError as exc:
        return invalid_input("principal_class", str(exc), given=repr(principal))


def _parse_owner(owner: ActorId | Quant | str) -> Result[ActorId]:
    if isinstance(owner, ActorId):
        return Ok(owner)
    if isinstance(owner, Quant):
        return Ok(owner.actor_id)
    return ActorId.try_create(owner)


@dataclass(frozen=True, slots=True)
class JobStreamEvent:
    """Operational log line. Telemetry surface — never a Task Ledger entry."""

    job_id: str
    kind: str
    body: Mapping[str, object]
    surface: str = "telemetry"

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "job_id": self.job_id,
                "kind": self.kind,
                "body": dict(self.body),
                "surface": self.surface,
                "ledger": False,
            }
        )


@dataclass(frozen=True, slots=True)
class JobWaitResult:
    """Wait is a change signal. Durable JobHandle state is the source of truth."""

    handle: JobHandle
    observed_state: JobHandleState | None
    changed: bool

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "job_id": self.handle.job_id,
                "state": self.handle.state.value,
                "observed_state": (
                    None if self.observed_state is None else self.observed_state.value
                ),
                "changed": self.changed,
                "source": "durable_store",
                "sleep_is_truth": False,
            }
        )


@dataclass(frozen=True, slots=True)
class JobWake:
    """Wake delivery targeting the owning Quant mailbox stored at submit."""

    job_id: str
    owner: str
    mailbox: str
    message_kind: str
    armed: bool
    emitted: bool

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "job_id": self.job_id,
                "owner": self.owner,
                "mailbox": self.mailbox,
                "message_kind": self.message_kind,
                "armed": self.armed,
                "emitted": self.emitted,
            }
        )


@dataclass
class JobHandleStore:
    """Durable JobHandle records keyed by job id. Survives client detach."""

    _by_id: dict[str, JobHandle] = field(default_factory=dict[str, JobHandle])
    _by_task: dict[str, str] = field(default_factory=dict[str, str])

    def get(self, job_id: str) -> JobHandle | None:
        return self._by_id.get(job_id)

    def for_task(self, task_id: str) -> JobHandle | None:
        job_id = self._by_task.get(task_id)
        if job_id is None:
            return None
        return self._by_id.get(job_id)

    def put(self, handle: JobHandle) -> JobHandle:
        self._by_id[handle.job_id] = handle
        self._by_task[handle.task_id] = handle.job_id
        return handle

    def discard(self, job_id: str) -> None:
        handle = self._by_id.pop(job_id, None)
        if handle is not None:
            self._by_task.pop(handle.task_id, None)

    def all(self) -> tuple[JobHandle, ...]:
        return tuple(self._by_id.values())

    def snapshot(self) -> tuple[Mapping[str, object], ...]:
        return tuple(handle.to_payload() for handle in self._by_id.values())

    def restore(self, records: Sequence[Mapping[str, object]]) -> Result[int]:
        count = 0
        for payload in records:
            handle = JobHandle.from_payload(payload)
            if is_refusal(handle):
                return handle
            self.put(handle.value)
            count += 1
        return Ok(count)


class JobHandleService:
    """Daemon-owned JobHandle lifecycle. Agents never author Task outcomes."""

    def __init__(
        self,
        *,
        router: ComputeRouter | None = None,
        dispatcher: TaskGraphDispatcher | None = None,
        store: JobHandleStore | None = None,
    ) -> None:
        self._router = router if router is not None else ComputeRouter()
        self._dispatcher = dispatcher
        self._store = store if store is not None else JobHandleStore()
        self._streams: dict[str, list[JobStreamEvent]] = {}
        self._wakes: dict[str, JobWake] = {}
        if dispatcher is not None and dispatcher.router is not self._router:
            self._router = dispatcher.router

    @property
    def store(self) -> JobHandleStore:
        return self._store

    @property
    def router(self) -> ComputeRouter:
        return self._router

    @property
    def dispatcher(self) -> TaskGraphDispatcher | None:
        return self._dispatcher

    @property
    def operations(self) -> tuple[str, ...]:
        return JOB_HANDLE_OPERATIONS

    def handle_for(self, job_id: str) -> JobHandle | None:
        return self._store.get(job_id)

    def handle_for_task(self, task_id: str) -> JobHandle | None:
        return self._store.for_task(task_id)

    def snapshot(self) -> tuple[Mapping[str, object], ...]:
        return self._store.snapshot()

    def submit(
        self,
        *,
        owner: ActorId | Quant | str,
        task_id: str,
        job_id: str | None = None,
        kind: ExecutionEnvironmentKind | str | None = None,
        requirement: ComputeRequirement | None = None,
        correlation_id: str = "",
    ) -> Result[JobHandle]:
        """Queue work and return immediately with a durable JobHandle."""
        if not task_id:
            return invalid_input("task_id", "submit requires a task_id")
        parsed_owner = _parse_owner(owner)
        if is_refusal(parsed_owner):
            return parsed_owner
        existing = self._store.for_task(task_id)
        if isinstance(job_id, str) and job_id.strip():
            durable_id = job_id.strip()
        else:
            durable_id = f"job:{task_id}"
        if existing is not None:
            if existing.job_id != durable_id:
                return policy_rejection(
                    "job_id",
                    "a Task already has a JobHandle; submit does not mint a second id",
                    task_id=task_id,
                    existing=existing.job_id,
                    given=durable_id,
                )
            return Ok(existing)
        if requirement is not None:
            placed = self._router.place_requirement(task_id=task_id, requirement=requirement)
            if is_refusal(placed):
                return placed
        elif kind is not None:
            placed = self._router.place_job(task_id=task_id, kind=kind)
            if is_refusal(placed):
                return placed
        minted = JobHandle.try_create(
            job_id=durable_id,
            owner=parsed_owner.value,
            state=JobHandleState.QUEUED,
            task_id=task_id,
            wake_mailbox=wake_mailbox_for(parsed_owner.value),
            correlation_id=correlation_id,
        )
        if is_refusal(minted):
            return minted
        committed = self._commit(minted.value, event="submit")
        if is_ok(committed):
            self._wakes[durable_id] = JobWake(
                job_id=durable_id,
                owner=parsed_owner.value.value,
                mailbox=committed.value.wake_mailbox,
                message_kind=MessageKind.NOTIFY.value,
                armed=False,
                emitted=False,
            )
        return committed

    def attach(self, job_id: str) -> Result[JobHandle]:
        """Live view of durable state. Identity (job_id) does not change."""
        handle = self._store.get(job_id)
        if handle is None:
            return invalid_input(
                "job_id",
                "JobHandle.attach requires a minted job id",
                given=job_id,
            )
        return Ok(handle)

    def wait(
        self,
        job_id: str,
        *,
        observed_state: JobHandleState | str | None = None,
    ) -> Result[JobWaitResult]:
        """Block-until-change signal. Re-read the durable handle for truth."""
        handle = self._store.get(job_id)
        if handle is None:
            return invalid_input("job_id", "wait requires a minted job id", given=job_id)
        previous: JobHandleState | None = None
        if observed_state is not None:
            parsed = _parse_state(observed_state)
            if is_refusal(parsed):
                return parsed
            previous = parsed.value
        return Ok(
            JobWaitResult(
                handle=handle,
                observed_state=previous,
                changed=previous is None or previous is not handle.state,
            )
        )

    def reattach(
        self,
        job_id: str,
        *,
        supervisor_reachable: bool = True,
        environment_reachable: bool = True,
        daemon_restarted: bool = False,
    ) -> Result[JobHandle]:
        """Restore durable truth. Unreachable/restarted in-flight work is unknown."""
        handle = self._store.get(job_id)
        if handle is None:
            return invalid_input(
                "job_id",
                "JobHandle.reattach requires durable state; missing truth is not invented",
                given=job_id,
            )
        if handle.is_terminal or handle.state is JobHandleState.UNKNOWN:
            return Ok(handle)
        lost = daemon_restarted or not supervisor_reachable or not environment_reachable
        if not lost:
            return Ok(handle)
        trigger = (
            "daemon_restart"
            if daemon_restarted
            else ("unreachable_environment" if not environment_reachable else "lost_supervisor")
        )
        return self.mark_unknown(job_id, trigger=trigger)

    def recover_after_restart(
        self,
        records: Sequence[Mapping[str, object]] | None = None,
        *,
        supervisor_reachable: bool = False,
        environment_reachable: bool = False,
    ) -> Result[tuple[JobHandle, ...]]:
        """Reload durable records and mark unresolved in-flight jobs unknown."""
        if records is not None:
            restored = self._store.restore(records)
            if is_refusal(restored):
                return restored
        recovered: list[JobHandle] = []
        for handle in self._store.all():
            result = self.reattach(
                handle.job_id,
                supervisor_reachable=supervisor_reachable,
                environment_reachable=environment_reachable,
                daemon_restarted=True,
            )
            if is_refusal(result):
                return result
            recovered.append(result.value)
        return Ok(tuple(recovered))

    def wake(self, job_id: str) -> Result[JobWake]:
        """Arm async wakeup to the owning Quant mailbox stored at submit."""
        handle = self._store.get(job_id)
        if handle is None:
            return invalid_input("job_id", "wake requires a minted job id", given=job_id)
        record = self._wakes.get(job_id)
        if record is None:
            record = JobWake(
                job_id=job_id,
                owner=handle.owner.value,
                mailbox=handle.wake_mailbox,
                message_kind=MessageKind.NOTIFY.value,
                armed=True,
                emitted=False,
            )
        else:
            record = JobWake(
                job_id=record.job_id,
                owner=record.owner,
                mailbox=record.mailbox,
                message_kind=record.message_kind,
                armed=True,
                emitted=record.emitted,
            )
        self._wakes[job_id] = record
        updated = handle.with_state(handle.state, wake_armed=True)
        self._store.put(updated)
        if updated.is_terminal:
            return Ok(self._emit_wake(updated))
        return Ok(record)

    def cancel(self, job_id: str) -> Result[JobHandle]:
        """Explicit cancel. Distinct from aborted (environment/supervisor kill)."""
        handle = self._store.get(job_id)
        if handle is None:
            return invalid_input("job_id", "cancel requires a minted job id", given=job_id)
        if handle.state is JobHandleState.UNKNOWN:
            return policy_rejection(
                "job_handle",
                "an unknown JobHandle is resolved only by an operator-principal "
                "recorded action, never by cancel (CT-46; FR-Q51)",
                job_id=job_id,
            )
        return self._transition(handle, JobHandleState.CANCELLED, event="cancel")

    def stream(self, job_id: str) -> Result[tuple[JobStreamEvent, ...]]:
        """Operational logs. Harness telemetry — not the Task Ledger."""
        if self._store.get(job_id) is None and job_id not in self._streams:
            return invalid_input("job_id", "stream requires a minted job id", given=job_id)
        return Ok(tuple(self._streams.get(job_id, ())))

    def start(self, job_id: str) -> Result[JobHandle]:
        """queued → running once the environment begins the work."""
        handle = self._require(job_id)
        if is_refusal(handle):
            return handle
        return self._transition(handle.value, JobHandleState.RUNNING, event="start")

    def complete(self, job_id: str, state: JobHandleState | str) -> Result[JobHandle]:
        """Known application outcome: done or failed. Never a timeout."""
        parsed = _parse_state(state)
        if is_refusal(parsed):
            return parsed
        if parsed.value not in {JobHandleState.DONE, JobHandleState.FAILED}:
            return policy_rejection(
                "state",
                "complete accepts only done or failed; aborted, cancelled, and "
                "unknown have dedicated paths (CT-46; FR-Q51)",
                given=parsed.value.value,
            )
        handle = self._require(job_id)
        if is_refusal(handle):
            return handle
        return self._transition(handle.value, parsed.value, event="complete")

    def abort(self, job_id: str, *, reason: str) -> Result[JobHandle]:
        """Known non-completion by environment or supervisor — not cancel."""
        if is_unknown_trigger(reason):
            return policy_rejection(
                "abort_reason",
                "timeout, lost supervisor, unreachable environment, or daemon "
                "restart resolves to unknown, never aborted (CT-46; FR-Q51)",
                trigger=reason,
                job_id=job_id,
            )
        if not is_abort_trigger(reason) and not reason.strip():
            return invalid_input("abort_reason", "aborted requires a recorded reason")
        handle = self._require(job_id)
        if is_refusal(handle):
            return handle
        return self._transition(
            handle.value,
            JobHandleState.ABORTED,
            event="abort",
            abort_reason=reason,
        )

    def mark_unknown(self, job_id: str, *, trigger: str) -> Result[JobHandle]:
        """Unresolved outcome. Never failed, aborted, or retried."""
        classified = outcome_for_trigger(trigger)
        if is_refusal(classified):
            return classified
        if classified.value is not JobHandleState.UNKNOWN:
            return policy_rejection(
                "trigger",
                "known abort triggers use abort(); unknown-certainty uses mark_unknown",
                trigger=trigger,
            )
        handle = self._require(job_id)
        if is_refusal(handle):
            return handle
        if handle.value.state is JobHandleState.UNKNOWN:
            return Ok(handle.value)
        return self._transition(
            handle.value,
            JobHandleState.UNKNOWN,
            event="unknown",
            unknown_trigger=trigger,
        )

    def observe_lost_certainty(self, job_id: str, *, trigger: str) -> Result[JobHandle]:
        """Timeout / lost supervisor / unreachable env / restart → unknown."""
        return self.mark_unknown(job_id, trigger=trigger)

    def retry(self, job_id: str) -> Result[JobHandle]:
        """Retry must not invent a terminal outcome or free an unknown slot."""
        return self._refuse_unknown_shortcut(job_id, action="retry")

    def infer_failure(self, job_id: str) -> Result[JobHandle]:
        """Inferred failure is not a resolution of unknown."""
        return self._refuse_unknown_shortcut(job_id, action="infer_failure")

    def assume_outcome(self, job_id: str, outcome: str) -> Result[JobHandle]:
        """Assumed terminal state is not a resolution of unknown."""
        return self._refuse_unknown_shortcut(job_id, action="assume_outcome", outcome=outcome)

    def resolve_unknown(
        self,
        job_id: str,
        *,
        principal: PrincipalClass | str,
        recorded: bool,
        to_state: JobHandleState | str,
        abort_reason: str | None = None,
        correlation_id: str = "",
    ) -> Result[JobHandle]:
        """Operator-principal recorded action is the only unknown exit (AD-24)."""
        authorized = authorize_wire_command(JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND, principal)
        if is_refusal(authorized):
            return authorized
        parsed_principal = _parse_principal(principal)
        if is_refusal(parsed_principal):
            return parsed_principal
        if parsed_principal.value is not PrincipalClass.OPERATOR:
            return OperatorPrincipalRequired.of(
                command=JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND,
                principal_class=parsed_principal.value.value,
            )
        if not recorded:
            return policy_rejection(
                "job_handle",
                "an unknown JobHandle is resolved only by an operator-principal "
                "recorded action, never by a machine principal, retry, or "
                "inferred failure (CT-46; FR-Q51)",
                job_id=job_id,
                recorded=False,
            )
        parsed = _parse_state(to_state)
        if is_refusal(parsed):
            return parsed
        if parsed.value not in JOB_HANDLE_TERMINAL_STATES:
            return policy_rejection(
                "state",
                "explicit resolution of unknown requires a terminal JobHandle state",
                given=parsed.value.value,
            )
        handle = self._require(job_id)
        if is_refusal(handle):
            return handle
        if handle.value.state is not JobHandleState.UNKNOWN:
            return policy_rejection(
                "job_handle",
                "resolve_unknown requires JobHandle state unknown",
                job_id=job_id,
                state=handle.value.state.value,
            )
        if parsed.value is JobHandleState.ABORTED and not abort_reason:
            return invalid_input(
                "abort_reason",
                "resolving unknown to aborted requires a recorded abort reason",
            )
        resolution = {
            "command": JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND,
            "principal_class": PrincipalClass.OPERATOR.value,
            "recorded": True,
            "to_state": parsed.value.value,
            "correlation_id": correlation_id,
        }
        return self._transition(
            handle.value,
            parsed.value,
            event="unknown.resolve",
            abort_reason=abort_reason,
            unknown_trigger="",
            recorded_resolution=resolution,
            resolving_unknown=True,
        )

    def apply_to_task(self, job_id: str) -> Result[TaskTransitionResult]:
        """Daemon-only mapping onto the owning Task. Agents have no equivalent."""
        if self._dispatcher is None:
            return policy_rejection(
                "job_handle",
                "JobHandle→Task mapping is applied by the daemon dispatcher alone",
                job_id=job_id,
            )
        handle = self._require(job_id)
        if is_refusal(handle):
            return handle
        return self._apply_mapping(handle.value)

    def _require(self, job_id: str) -> Result[JobHandle]:
        handle = self._store.get(job_id)
        if handle is None:
            return invalid_input("job_id", "unknown JobHandle id", given=job_id)
        return Ok(handle)

    def _legal_transition(self, current: JobHandleState, nxt: JobHandleState) -> bool:
        if current is JobHandleState.QUEUED:
            return nxt in _FROM_QUEUED
        if current is JobHandleState.RUNNING:
            return nxt in _FROM_RUNNING
        return False

    def _transition(
        self,
        handle: JobHandle,
        nxt: JobHandleState,
        *,
        event: str,
        abort_reason: str | None = None,
        unknown_trigger: str | None = None,
        recorded_resolution: Mapping[str, object] | None = None,
        resolving_unknown: bool = False,
    ) -> Result[JobHandle]:
        if handle.state is nxt and not resolving_unknown:
            return Ok(handle)
        if handle.is_terminal:
            return policy_rejection(
                "job_handle",
                "terminal JobHandle states are done, failed, cancelled, and aborted; "
                "further transitions are refused (CT-46; FR-Q51)",
                job_id=handle.job_id,
                current_state=handle.state.value,
                to_state=nxt.value,
            )
        if handle.state is JobHandleState.UNKNOWN and not resolving_unknown:
            return policy_rejection(
                "job_handle",
                "an unknown JobHandle is resolved only by an operator-principal "
                "recorded action (CT-46; FR-Q51)",
                job_id=handle.job_id,
                to_state=nxt.value,
            )
        if not resolving_unknown and not self._legal_transition(handle.state, nxt):
            return policy_rejection(
                "job_handle",
                "illegal JobHandle transition (CT-46; FR-Q51)",
                job_id=handle.job_id,
                current_state=handle.state.value,
                to_state=nxt.value,
            )
        minted = JobHandle.try_create(
            job_id=handle.job_id,
            owner=handle.owner,
            state=nxt,
            task_id=handle.task_id,
            wake_mailbox=handle.wake_mailbox,
            abort_reason=(abort_reason if nxt is JobHandleState.ABORTED else None),
            unknown_trigger=(unknown_trigger if nxt is JobHandleState.UNKNOWN else None),
            correlation_id=handle.correlation_id,
            wake_armed=handle.wake_armed,
            recorded_resolution=recorded_resolution,
        )
        if is_refusal(minted):
            return minted
        return self._commit(minted.value, event=event, previous=handle)

    def _commit(
        self,
        handle: JobHandle,
        *,
        event: str,
        previous: JobHandle | None = None,
    ) -> Result[JobHandle]:
        self._store.put(handle)
        self._append_stream(
            handle.job_id,
            event,
            {
                "state": handle.state.value,
                "mapped_task_state": handle.mapped_task_state.value,
            },
        )
        if self._dispatcher is not None and self._dispatcher.store.was_dispatched(handle.task_id):
            mapped = self._apply_mapping(handle)
            if is_refusal(mapped):
                if previous is not None:
                    self._store.put(previous)
                else:
                    self._store.discard(handle.job_id)
                return mapped
        elif handle.state is JobHandleState.UNKNOWN:
            if self._router.lease_for(handle.task_id) is not None:
                held = self._router.hold_unknown(handle.task_id)
                if is_refusal(held):
                    if previous is not None:
                        self._store.put(previous)
                    else:
                        self._store.discard(handle.job_id)
                    return held
        elif (
            previous is not None
            and previous.state is JobHandleState.UNKNOWN
            and is_job_handle_terminal(handle.state)
            and self._router.is_unknown(handle.task_id)
        ):
            resolved = self._router.resolve_unknown(handle.task_id, recorded=True)
            if is_refusal(resolved):
                self._store.put(previous)
                return resolved
        if handle.is_terminal and handle.wake_armed:
            self._emit_wake(handle)
        return Ok(handle)

    def _apply_mapping(self, handle: JobHandle) -> Result[TaskTransitionResult]:
        """Daemon-only: JobHandle state → Task state through the dispatcher."""
        dispatcher = self._dispatcher
        if dispatcher is None:
            return policy_rejection(
                "job_handle",
                "JobHandle→Task mapping is applied by the daemon alone (DEC-0316)",
                job_id=handle.job_id,
            )
        evidence = JobHandleEvidence(
            job_id=handle.job_id,
            task_id=handle.task_id,
            state=handle.state,
            abort_reason=handle.abort_reason,
        )
        located = dispatcher.store.find_task(handle.task_id)
        if located is None:
            return policy_rejection(
                "task_id",
                "JobHandle→Task mapping requires a materialized Task",
                task_id=handle.task_id,
            )
        current = dispatcher.store.job_handle_for(handle.task_id)
        if current is not None and current.state is JobHandleState.UNKNOWN and handle.is_terminal:
            return dispatcher.resolve_unknown_job_handle(evidence)
        return dispatcher.apply_job_handle_evidence(evidence)

    def _append_stream(self, job_id: str, kind: str, body: Mapping[str, object]) -> None:
        self._streams.setdefault(job_id, []).append(
            JobStreamEvent(job_id=job_id, kind=kind, body=MappingProxyType(dict(body)))
        )

    def _emit_wake(self, handle: JobHandle) -> JobWake:
        record = JobWake(
            job_id=handle.job_id,
            owner=handle.owner.value,
            mailbox=handle.wake_mailbox,
            message_kind=MessageKind.NOTIFY.value,
            armed=True,
            emitted=True,
        )
        self._wakes[handle.job_id] = record
        self._append_stream(
            handle.job_id,
            "wake",
            {"mailbox": handle.wake_mailbox, "owner": handle.owner.value},
        )
        return record

    def _refuse_unknown_shortcut(
        self,
        job_id: str,
        *,
        action: str,
        outcome: str | None = None,
    ) -> Result[JobHandle]:
        handle = self._store.get(job_id)
        extra: dict[str, object] = {"job_id": job_id, "action": action}
        if handle is not None:
            extra["state"] = handle.state.value
        if outcome is not None:
            extra["outcome"] = outcome
        occupying = handle is not None and handle.state is JobHandleState.UNKNOWN
        extra["occupying"] = occupying
        if occupying and self._router.is_unknown(handle.task_id if handle is not None else ""):
            extra["environment_lease_held"] = True
        return policy_rejection(
            "job_handle",
            "an unknown JobHandle is resolved only by an operator-principal "
            "recorded action; retry, assumed outcome, or inferred failure does "
            "not mint a terminal state (CT-46; FR-Q51)",
            **extra,
        )
