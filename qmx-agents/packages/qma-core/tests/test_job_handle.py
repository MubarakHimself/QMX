"""Story 45.4 — JobHandle definition: id, owner, closed state (FR-Q51)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.jobs import (
    AWAITING_APPROVAL_GATE,
    AWAITING_APPROVAL_IS_HANDLE_STATE,
    JOB_HANDLE_ABORT_TRIGGERS,
    JOB_HANDLE_FORBIDDEN_STATES,
    JOB_HANDLE_OPERATIONS,
    JOB_HANDLE_UNKNOWN_RESOLVE_COMMAND,
    JOB_HANDLE_UNKNOWN_TRIGGERS,
    JobArtifact,
    JobHandle,
    is_abort_trigger,
    is_forbidden_job_handle_state,
    is_unknown_trigger,
    outcome_for_trigger,
    parse_job_artifact,
    parse_job_handle,
    wake_mailbox_for,
)
from qma.core.vocabulary.enums import (
    JOB_HANDLE_TERMINAL_STATES,
    ArtifactCompleteness,
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


def test_ad17_vocabulary_excludes_succeeded_and_awaiting_approval() -> None:
    assert {member.value for member in JobHandleState} == {
        "queued",
        "running",
        "done",
        "failed",
        "cancelled",
        "aborted",
        "unknown",
    }
    assert "succeeded" not in {member.value for member in JobHandleState}
    assert AWAITING_APPROVAL_GATE not in {member.value for member in JobHandleState}
    assert AWAITING_APPROVAL_GATE not in {member.value for member in TaskMissionState}
    assert AWAITING_APPROVAL_IS_HANDLE_STATE is False
    assert frozenset({"succeeded", "awaiting_approval"}) == JOB_HANDLE_FORBIDDEN_STATES
    for alias in JOB_HANDLE_FORBIDDEN_STATES:
        assert is_forbidden_job_handle_state(alias)
        refused = parse_job_handle(
            job_id="job:alias",
            owner=_owner(),
            state=alias,
            task_id="task:alias",
        )
        assert is_refusal(refused)
        assert refused.context["field"] == "state"
        assert refused.context["given"] == alias


def test_handle_records_logical_run_attempt_and_artifact_inventory() -> None:
    assert {member.value for member in ArtifactCompleteness} == {
        "complete",
        "partial",
        "missing",
        "expired",
    }
    owner = _owner()
    handle = JobHandle.try_create(
        job_id="job:inv-1",
        owner=owner,
        state="running",
        task_id="task:inv-1",
        logical_run_id="inv:run-1",
        attempt_id=2,
        artifacts=(
            {"fp1": "fp1:sha256:partial", "completeness": "partial"},
            JobArtifact(fp1="fp1:sha256:gone", completeness=ArtifactCompleteness.MISSING),
        ),
    )
    assert is_ok(handle)
    assert handle.value.logical_run_id == "inv:run-1"
    assert handle.value.attempt_id == 2
    assert handle.value.artifacts[0].completeness is ArtifactCompleteness.PARTIAL
    assert handle.value.artifacts[1].completeness is ArtifactCompleteness.MISSING
    payload = handle.value.to_payload()
    assert payload["logical_run_id"] == "inv:run-1"
    assert payload["attempt_id"] == 2
    assert payload["artifacts"] == [
        {"fp1": "fp1:sha256:partial", "completeness": "partial"},
        {"fp1": "fp1:sha256:gone", "completeness": "missing"},
    ]
    restored = JobHandle.from_payload(payload)
    assert is_ok(restored)
    assert restored.value.logical_run_id == "inv:run-1"
    assert restored.value.attempt_id == 2
    assert restored.value.artifacts[0].completeness is ArtifactCompleteness.PARTIAL
    expired = parse_job_artifact({"fp1": "fp1:sha256:old", "completeness": "expired"})
    assert is_ok(expired)
    assert expired.value.completeness is ArtifactCompleteness.EXPIRED
    invented = parse_job_artifact({"fp1": "fp1:x", "completeness": "stale"})
    assert is_refusal(invented)
    defaulted = JobHandle.try_create(
        job_id="job:default",
        owner=owner,
        state="queued",
        task_id="task:default",
    )
    assert is_ok(defaulted)
    assert defaulted.value.logical_run_id == "job:default"
    assert defaulted.value.attempt_id == 1
    assert defaulted.value.artifacts == ()


def test_unknown_handle_holds_environment_lease_and_is_not_terminal() -> None:
    handle = JobHandle.try_create(
        job_id="job:timeout",
        owner=_owner(),
        state="unknown",
        task_id="task:timeout",
        unknown_trigger="timeout",
        logical_run_id="inv:timeout",
    )
    assert is_ok(handle)
    assert handle.value.state is JobHandleState.UNKNOWN
    assert handle.value.is_terminal is False
    assert handle.value.holds_environment_lease is True
    assert handle.value.state is not JobHandleState.FAILED
    assert handle.value.state is not JobHandleState.ABORTED
    assert handle.value.to_payload()["holds_environment_lease"] is True
