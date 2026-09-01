"""Story 45.4 — JobHandle definition: id, owner, closed state (FR-Q51)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.jobs import (
    JOB_HANDLE_ABORT_TRIGGERS,
    JOB_HANDLE_OPERATIONS,
    JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND,
    JOB_HANDLE_UNKNOWN_TRIGGERS,
    JobHandle,
    is_abort_trigger,
    is_unknown_trigger,
    outcome_for_trigger,
    parse_job_handle,
    wake_mailbox_for,
)
from qma.core.vocabulary.enums import (
    JOB_HANDLE_TERMINAL_STATES,
    JobHandleState,
    TaskMissionState,
    map_job_handle_to_task_state,
)
from qmf.core import is_ok, is_refusal


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    return minted.value


def test_operations_are_the_seven_ct46_verbs() -> None:
    assert JOB_HANDLE_OPERATIONS == (
        "submit",
        "attach",
        "wait",
        "reattach",
        "wake",
        "cancel",
        "stream",
    )
    assert JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND == "unknown.resolve"


def test_minted_handle_carries_id_owner_and_closed_state() -> None:
    owner = _owner()
    handle = JobHandle.try_create(
        job_id="job:task-1",
        owner=owner,
        state="queued",
        task_id="task-1",
    )
    assert is_ok(handle)
    assert handle.value.job_id == "job:task-1"
    assert handle.value.owner == owner
    assert handle.value.state is JobHandleState.QUEUED
    assert handle.value.wake_mailbox == wake_mailbox_for(owner)
    payload = handle.value.to_payload()
    assert payload["owner"] == owner.value
    assert payload["state"] == "queued"
    assert payload["operations"] == list(JOB_HANDLE_OPERATIONS)
    assert payload["is_terminal"] is False


def test_invented_state_is_refused() -> None:
    refused = parse_job_handle(
        job_id="job:x",
        owner=_owner(),
        state="succeeded",
        task_id="task:x",
    )
    assert is_refusal(refused)
    missing_owner = JobHandle.try_create(
        job_id="job:x",
        owner="",
        state="queued",
        task_id="task:x",
    )
    assert is_refusal(missing_owner)


def test_unknown_triggers_never_classify_as_failed_or_aborted() -> None:
    assert {
        "timeout",
        "lost_supervisor",
        "unreachable_environment",
        "daemon_restart",
    } == JOB_HANDLE_UNKNOWN_TRIGGERS
    for trigger in JOB_HANDLE_UNKNOWN_TRIGGERS:
        assert is_unknown_trigger(trigger)
        classified = outcome_for_trigger(trigger)
        assert is_ok(classified)
        assert classified.value is JobHandleState.UNKNOWN
        aborted = JobHandle.try_create(
            job_id="job:unk",
            owner=_owner(),
            state="aborted",
            task_id="task:unk",
            abort_reason=trigger,
        )
        assert is_refusal(aborted)


def test_abort_triggers_are_known_non_completion() -> None:
    assert {
        "oom_kill",
        "container_stop",
        "image_failure",
        "mount_failure",
    } == JOB_HANDLE_ABORT_TRIGGERS
    for trigger in JOB_HANDLE_ABORT_TRIGGERS:
        assert is_abort_trigger(trigger)
        classified = outcome_for_trigger(trigger)
        assert is_ok(classified)
        assert classified.value is JobHandleState.ABORTED
        handle = JobHandle.try_create(
            job_id="job:abort",
            owner=_owner(),
            state="aborted",
            task_id="task:abort",
            abort_reason=trigger,
        )
        assert is_ok(handle)
        assert handle.value.is_terminal is True
        assert handle.value.mapped_task_state is TaskMissionState.FAILED
        assert handle.value.mapped_task_state is not TaskMissionState.CANCELLED


def test_mapping_definition_is_total_and_aborted_never_cancelled() -> None:
    expected = {
        JobHandleState.QUEUED: TaskMissionState.RUNNING,
        JobHandleState.RUNNING: TaskMissionState.RUNNING,
        JobHandleState.DONE: TaskMissionState.DONE,
        JobHandleState.FAILED: TaskMissionState.FAILED,
        JobHandleState.ABORTED: TaskMissionState.FAILED,
        JobHandleState.CANCELLED: TaskMissionState.CANCELLED,
        JobHandleState.UNKNOWN: TaskMissionState.UNKNOWN,
    }
    for state, mapped in expected.items():
        assert map_job_handle_to_task_state(state) is mapped
    assert (
        frozenset(
            {
                JobHandleState.DONE,
                JobHandleState.FAILED,
                JobHandleState.CANCELLED,
                JobHandleState.ABORTED,
            }
        )
        == JOB_HANDLE_TERMINAL_STATES
    )
    restored = JobHandle.from_payload(
        {
            "job_id": "job:done",
            "owner": _owner().value,
            "state": "done",
            "task_id": "task:done",
        }
    )
    assert is_ok(restored)
    assert restored.value.state is JobHandleState.DONE
