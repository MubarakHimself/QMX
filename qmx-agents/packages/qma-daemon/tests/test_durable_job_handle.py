"""Story 45.4 — durable JobHandle state and daemon Task-state mapping (FR-Q51)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.jobs import JOB_HANDLE_OPERATIONS, JobHandle
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    JobHandleState,
    PrincipalClass,
    TaskMissionState,
    map_job_handle_to_task_state,
)
from qma.daemon import CompileRequest, MissionCompiler, TaskGraphDispatcher
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qmf.core import is_ok, is_refusal


def _quant(*, slug: str = "alpha") -> Quant:
    minted = ActorId.mint(DeskSlug.RESEARCH, slug)
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
    )


def _bound_dispatcher() -> tuple[TaskGraphDispatcher, Quant, str]:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    compiled = compiler.compile(CompileRequest(goal=Goal(text="durable job"), owner=owner))
    assert is_ok(compiled)
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(
        envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    router = ComputeRouter(environments=envs)
    dispatcher = TaskGraphDispatcher(environments=envs, router=router)
    dispatcher.materialize(compiled.value.task_graph, mission=compiled.value.mission)
    task = compiled.value.task_graph.tasks[0]
    decision = dispatcher.dispatch_task(task_id=task.id, holder_agent_id="agent:w1")
    assert is_ok(decision)
    return dispatcher, owner, task.id


def _service() -> tuple[JobHandleService, Quant, str, TaskGraphDispatcher]:
    dispatcher, owner, task_id = _bound_dispatcher()
    service = JobHandleService(dispatcher=dispatcher, router=dispatcher.router)
    return service, owner, task_id, dispatcher


def test_submit_mints_queued_handle_with_owner_and_operations() -> None:
    service, owner, task_id, _dispatcher = _service()
    assert service.operations == JOB_HANDLE_OPERATIONS
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    handle = submitted.value
    assert handle.job_id == f"job:{task_id}"
    assert handle.owner == owner.actor_id
    assert handle.state is JobHandleState.QUEUED
    assert handle.wake_mailbox == f"mailbox:{owner.actor_id.value}"
    attached = service.attach(handle.job_id)
    assert is_ok(attached)
    assert attached.value.job_id == handle.job_id
    waited = service.wait(handle.job_id, observed_state=JobHandleState.QUEUED)
    assert is_ok(waited)
    wait_payload = waited.value.to_payload()
    assert wait_payload["source"] == "durable_store"
    assert wait_payload["sleep_is_truth"] is False
    assert waited.value.changed is False
    streamed = service.stream(handle.job_id)
    assert is_ok(streamed)
    assert all(event.surface == "telemetry" for event in streamed.value)
    assert all(event.to_payload()["ledger"] is False for event in streamed.value)


def test_daemon_applies_total_mapping_agents_cannot() -> None:
    service, owner, task_id, dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    started = service.start(submitted.value.job_id)
    assert is_ok(started)
    located = dispatcher.store.find_task(task_id)
    assert located is not None
    assert located[1].state is TaskMissionState.RUNNING
    # Core mapping is the definition; it does not mutate Task state by itself.
    assert map_job_handle_to_task_state(JobHandleState.FAILED) is TaskMissionState.FAILED
    located_after = dispatcher.store.find_task(task_id)
    assert located_after is not None
    assert located_after[1].state is TaskMissionState.RUNNING
    done = service.complete(submitted.value.job_id, JobHandleState.DONE)
    assert is_ok(done)
    located_done = dispatcher.store.find_task(task_id)
    assert located_done is not None
    assert located_done[1].state is TaskMissionState.DONE
    assert done.value.mapped_task_state is TaskMissionState.DONE


def test_aborted_is_known_non_completion_distinct_from_cancelled() -> None:
    service, owner, task_id, dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    assert is_ok(service.start(submitted.value.job_id))
    aborted = service.abort(submitted.value.job_id, reason="oom_kill")
    assert is_ok(aborted)
    assert aborted.value.state is JobHandleState.ABORTED
    assert aborted.value.state is not JobHandleState.CANCELLED
    assert aborted.value.is_terminal is True
    located = dispatcher.store.find_task(task_id)
    assert located is not None
    assert located[1].state is TaskMissionState.FAILED
    assert located[1].state is not TaskMissionState.CANCELLED
    assert located[1].ledger is not None
    assert any(entry.get("kind") == "job_aborted" for entry in located[1].ledger.entries)

    service2, owner2, task_id2, dispatcher2 = _service()
    other = service2.submit(owner=owner2, task_id=task_id2)
    assert is_ok(other)
    cancelled = service2.cancel(other.value.job_id)
    assert is_ok(cancelled)
    assert cancelled.value.state is JobHandleState.CANCELLED
    located2 = dispatcher2.store.find_task(task_id2)
    assert located2 is not None
    assert located2[1].state is TaskMissionState.CANCELLED


def test_timeout_and_lost_supervisor_are_unknown_never_failed() -> None:
    service, owner, task_id, dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    assert is_ok(service.start(submitted.value.job_id))
    timeout = service.observe_lost_certainty(submitted.value.job_id, trigger="timeout")
    assert is_ok(timeout)
    assert timeout.value.state is JobHandleState.UNKNOWN
    assert timeout.value.state is not JobHandleState.FAILED
    located = dispatcher.store.find_task(task_id)
    assert located is not None
    assert located[1].state is TaskMissionState.UNKNOWN
    assert dispatcher.store.lease_for(task_id) is not None
    assert dispatcher.router.is_unknown(task_id)

    refused_abort = service.abort(submitted.value.job_id, reason="timeout")
    assert is_refusal(refused_abort)
    assert is_refusal(service.retry(submitted.value.job_id))
    assert is_refusal(service.infer_failure(submitted.value.job_id))
    assert is_refusal(service.assume_outcome(submitted.value.job_id, "failed"))
    assert is_refusal(service.cancel(submitted.value.job_id))
    assert timeout.value.state is JobHandleState.UNKNOWN


def test_unknown_resolution_requires_operator_principal_recorded_action() -> None:
    service, owner, task_id, dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    assert is_ok(service.start(submitted.value.job_id))
    unknown = service.mark_unknown(submitted.value.job_id, trigger="lost_supervisor")
    assert is_ok(unknown)

    machine = service.resolve_unknown(
        submitted.value.job_id,
        principal=PrincipalClass.MACHINE,
        recorded=True,
        to_state=JobHandleState.FAILED,
    )
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    unrecorded = service.resolve_unknown(
        submitted.value.job_id,
        principal=PrincipalClass.OPERATOR,
        recorded=False,
        to_state=JobHandleState.FAILED,
    )
    assert is_refusal(unrecorded)
    located = dispatcher.store.find_task(task_id)
    assert located is not None
    assert located[1].state is TaskMissionState.UNKNOWN

    resolved = service.resolve_unknown(
        submitted.value.job_id,
        principal=PrincipalClass.OPERATOR,
        recorded=True,
        to_state=JobHandleState.FAILED,
        correlation_id="corr:op-1",
    )
    assert is_ok(resolved)
    assert resolved.value.state is JobHandleState.FAILED
    assert resolved.value.recorded_resolution is not None
    assert resolved.value.recorded_resolution["principal_class"] == "operator"
    located_done = dispatcher.store.find_task(task_id)
    assert located_done is not None
    assert located_done[1].state is TaskMissionState.FAILED
    assert dispatcher.store.lease_for(task_id) is None


def test_reattach_restores_durable_truth_and_restart_is_unknown() -> None:
    service, owner, task_id, _dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    started = service.start(submitted.value.job_id)
    assert is_ok(started)
    wake = service.wake(submitted.value.job_id)
    assert is_ok(wake)
    assert wake.value.mailbox == started.value.wake_mailbox
    assert wake.value.owner == owner.actor_id.value
    snapshot = service.snapshot()

    restored = JobHandleService()
    recovered = restored.recover_after_restart(snapshot)
    assert is_ok(recovered)
    handle = restored.handle_for(started.value.job_id)
    assert handle is not None
    assert handle.state is JobHandleState.UNKNOWN
    assert handle.unknown_trigger == "daemon_restart"
    reattached = restored.reattach(started.value.job_id, daemon_restarted=True)
    assert is_ok(reattached)
    assert reattached.value.state is JobHandleState.UNKNOWN

    terminal_service, owner2, task_id2, _dispatcher2 = _service()
    done_submit = terminal_service.submit(owner=owner2, task_id=task_id2)
    assert is_ok(done_submit)
    assert is_ok(terminal_service.start(done_submit.value.job_id))
    completed = terminal_service.complete(done_submit.value.job_id, "done")
    assert is_ok(completed)
    fresh = JobHandleService()
    assert is_ok(fresh.recover_after_restart(terminal_service.snapshot()))
    restored_done = fresh.reattach(done_submit.value.job_id, daemon_restarted=True)
    assert is_ok(restored_done)
    assert restored_done.value.state is JobHandleState.DONE


def test_unreachable_environment_reattach_is_unknown() -> None:
    service, owner, task_id, _dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    assert is_ok(service.start(submitted.value.job_id))
    lost = service.reattach(
        submitted.value.job_id,
        supervisor_reachable=False,
        environment_reachable=False,
    )
    assert is_ok(lost)
    assert lost.value.state is JobHandleState.UNKNOWN
    assert lost.value.unknown_trigger in {
        "lost_supervisor",
        "unreachable_environment",
    }


def test_mapping_covers_every_job_handle_state_via_daemon() -> None:
    pairs = (
        (JobHandleState.QUEUED, TaskMissionState.RUNNING),
        (JobHandleState.RUNNING, TaskMissionState.RUNNING),
        (JobHandleState.DONE, TaskMissionState.DONE),
        (JobHandleState.FAILED, TaskMissionState.FAILED),
        (JobHandleState.CANCELLED, TaskMissionState.CANCELLED),
        (JobHandleState.ABORTED, TaskMissionState.FAILED),
        (JobHandleState.UNKNOWN, TaskMissionState.UNKNOWN),
    )
    for job_state, task_state in pairs:
        service, owner, task_id, dispatcher = _service()
        submitted = service.submit(owner=owner, task_id=task_id)
        assert is_ok(submitted)
        if job_state is JobHandleState.QUEUED:
            result = submitted
        elif job_state is JobHandleState.RUNNING:
            result = service.start(submitted.value.job_id)
        elif job_state is JobHandleState.DONE:
            assert is_ok(service.start(submitted.value.job_id))
            result = service.complete(submitted.value.job_id, "done")
        elif job_state is JobHandleState.FAILED:
            assert is_ok(service.start(submitted.value.job_id))
            result = service.complete(submitted.value.job_id, "failed")
        elif job_state is JobHandleState.CANCELLED:
            result = service.cancel(submitted.value.job_id)
        elif job_state is JobHandleState.ABORTED:
            assert is_ok(service.start(submitted.value.job_id))
            result = service.abort(submitted.value.job_id, reason="oom_kill")
        else:
            assert is_ok(service.start(submitted.value.job_id))
            result = service.mark_unknown(submitted.value.job_id, trigger="timeout")
        assert is_ok(result)
        assert result.value.state is job_state
        assert result.value.mapped_task_state is task_state
        located = dispatcher.store.find_task(task_id)
        assert located is not None
        assert located[1].state is task_state


def test_evidence_path_is_not_an_agent_completion() -> None:
    service, owner, task_id, dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    # Fabricating a terminal JobHandle in core does not complete the Task.
    fabricated = JobHandle.try_create(
        job_id=submitted.value.job_id,
        owner=owner,
        state="done",
        task_id=task_id,
    )
    assert is_ok(fabricated)
    located = dispatcher.store.find_task(task_id)
    assert located is not None
    assert located[1].state is TaskMissionState.RUNNING
    evidence = dispatcher.store.job_handle_for(task_id)
    assert evidence is not None
    assert evidence.state is JobHandleState.QUEUED


def test_wake_emits_to_owner_mailbox_on_terminal() -> None:
    service, owner, task_id, _dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    assert is_ok(service.wake(submitted.value.job_id))
    assert is_ok(service.start(submitted.value.job_id))
    done = service.complete(submitted.value.job_id, "done")
    assert is_ok(done)
    streamed = service.stream(submitted.value.job_id)
    assert is_ok(streamed)
    kinds = [event.kind for event in streamed.value]
    assert "wake" in kinds
    assert "submit" in kinds


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "job_handle_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
