"""Closed Task/Mission state law with JobHandle evidence (AD-12; FR-Q28).

Terminal authorship is daemon-only. An LLM may propose non-terminal progress;
terminal outcomes require terminal JobHandle evidence (except never-dispatched
cancel). Mission state is computed from Tasks, never from a JobHandle.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from qma.core.vocabulary.enums import (
    TASK_MISSION_TERMINAL_STATES,
    JobHandleState,
    TaskMissionState,
    is_job_handle_terminal,
    is_task_mission_terminal,
    map_job_handle_to_task_state,
)
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "JobHandleEvidence",
    "compute_mission_state",
    "task_state_from_job_handle",
    "validate_never_dispatched_cancel",
    "validate_terminal_evidence",
    "validate_unique_terminal",
]


@dataclass(frozen=True, slots=True)
class JobHandleEvidence:
    """Daemon-resolved JobHandle snapshot used as Task-state evidence (CT-46).

    Full Compute Router placement lands in Epic 45; this record is the evidence
    surface FR-Q28 binds to Task terminal outcomes.
    """

    job_id: str
    task_id: str
    state: JobHandleState
    abort_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.job_id:
            msg = "JobHandleEvidence.job_id is required"
            raise ValueError(msg)
        if not self.task_id:
            msg = "JobHandleEvidence.task_id is required"
            raise ValueError(msg)
        if self.state is JobHandleState.ABORTED and not self.abort_reason:
            msg = "aborted JobHandle evidence requires abort_reason (DEC-0316)"
            raise ValueError(msg)

    @property
    def is_terminal(self) -> bool:
        return is_job_handle_terminal(self.state)

    @property
    def mapped_task_state(self) -> TaskMissionState:
        return map_job_handle_to_task_state(self.state)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "job_id": self.job_id,
            "task_id": self.task_id,
            "state": self.state.value,
            "mapped_task_state": self.mapped_task_state.value,
            "is_terminal": self.is_terminal,
        }
        if self.abort_reason is not None:
            payload["abort_reason"] = self.abort_reason
        return MappingProxyType(payload)


def task_state_from_job_handle(evidence: JobHandleEvidence) -> TaskMissionState:
    """Apply the fixed total JobHandle→Task mapping (DEC-0316)."""
    return evidence.mapped_task_state


def validate_unique_terminal(
    *,
    current_state: TaskMissionState,
    to_state: TaskMissionState,
) -> Result[TaskMissionState]:
    """Each Task reaches at most one terminal state (FR-Q28; AD-12)."""
    if is_task_mission_terminal(current_state):
        return policy_rejection(
            "task_state",
            "each Task reaches at most one terminal state; further terminal "
            "transitions are refused (FR-Q28; AD-12)",
            current_state=current_state.value,
            to_state=to_state.value,
        )
    return Ok(to_state)


def validate_never_dispatched_cancel(
    *,
    current_state: TaskMissionState,
    to_state: TaskMissionState,
    was_dispatched: bool,
) -> Result[TaskMissionState]:
    """Never-dispatched Tasks may terminate only as cancelled, without JobHandle."""
    if was_dispatched:
        return policy_rejection(
            "task_state",
            "dispatched Task cancel requires terminal JobHandle evidence "
            "(FR-Q28; AD-12)",
            current_state=current_state.value,
            to_state=to_state.value,
        )
    if to_state is not TaskMissionState.CANCELLED:
        return policy_rejection(
            "task_state",
            "a never-dispatched Task may reach only cancelled as its terminal "
            "state (FR-Q28; AD-12)",
            current_state=current_state.value,
            to_state=to_state.value,
        )
    if current_state not in {
        TaskMissionState.PENDING,
        TaskMissionState.READY,
        TaskMissionState.BLOCKED,
    }:
        return policy_rejection(
            "task_state",
            "never-dispatched cancel is only legal from pending, ready, or blocked",
            current_state=current_state.value,
        )
    unique = validate_unique_terminal(current_state=current_state, to_state=to_state)
    if not is_ok(unique):
        return unique
    return Ok(TaskMissionState.CANCELLED)


def validate_terminal_evidence(
    *,
    current_state: TaskMissionState,
    evidence: JobHandleEvidence,
    was_dispatched: bool,
    proposed_to_state: TaskMissionState | None = None,
) -> Result[TaskMissionState]:
    """Accept a Task transition only when JobHandle evidence authorizes it.

    LLM proposals never author terminal outcomes: callers must supply evidence.
    ``unknown`` JobHandle maps only to Task ``unknown`` and is non-terminal.
    """
    if not was_dispatched:
        return policy_rejection(
            "job_handle",
            "JobHandle evidence applies only to dispatched Tasks; "
            "never-dispatched Tasks cancel without a JobHandle (FR-Q28)",
            task_id=evidence.task_id,
        )
    if evidence.task_id == "":
        return invalid_input("task_id", "JobHandle evidence requires task_id")

    unique = validate_unique_terminal(
        current_state=current_state,
        to_state=evidence.mapped_task_state,
    )
    if not is_ok(unique):
        return unique

    mapped = evidence.mapped_task_state
    if proposed_to_state is not None and proposed_to_state is not mapped:
        return policy_rejection(
            "proposed_transition",
            "proposed terminal state must equal the JobHandle→Task mapping; "
            "an LLM cannot author a different terminal outcome (FR-Q28; L35)",
            proposed=proposed_to_state.value,
            evidenced=mapped.value,
            job_state=evidence.state.value,
        )

    if evidence.state is JobHandleState.UNKNOWN:
        if mapped is not TaskMissionState.UNKNOWN:
            return policy_rejection(
                "job_handle",
                "JobHandle unknown may enter only Task unknown (FR-Q28; AD-12)",
                job_state=evidence.state.value,
                mapped=mapped.value,
            )
        return Ok(TaskMissionState.UNKNOWN)

    if not evidence.is_terminal:
        # queued/running → running (non-terminal progress from evidence)
        return Ok(mapped)

    if not is_task_mission_terminal(mapped):
        return policy_rejection(
            "job_handle",
            "terminal JobHandle must map to a terminal Task state",
            job_state=evidence.state.value,
            mapped=mapped.value,
        )
    return Ok(mapped)


def compute_mission_state(task_states: Sequence[TaskMissionState]) -> TaskMissionState:
    """Derive Mission state from its Tasks — never from a JobHandle (FR-Q28).

    A Mission containing any ``unknown`` Task is ``unknown``, never ``failed``.
    Terminal aggregation applies only when every Task is terminal.
    """
    if not task_states:
        return TaskMissionState.PENDING

    states = tuple(task_states)
    if any(s is TaskMissionState.UNKNOWN for s in states):
        return TaskMissionState.UNKNOWN

    if all(s in TASK_MISSION_TERMINAL_STATES for s in states):
        if any(s is TaskMissionState.FAILED for s in states):
            return TaskMissionState.FAILED
        if all(s is TaskMissionState.CANCELLED for s in states):
            return TaskMissionState.CANCELLED
        if any(s is TaskMissionState.DONE for s in states):
            return TaskMissionState.DONE
        return TaskMissionState.CANCELLED

    if any(s is TaskMissionState.RUNNING for s in states):
        return TaskMissionState.RUNNING
    if any(s is TaskMissionState.BLOCKED for s in states):
        return TaskMissionState.BLOCKED
    if any(s is TaskMissionState.READY for s in states):
        return TaskMissionState.READY
    return TaskMissionState.PENDING
