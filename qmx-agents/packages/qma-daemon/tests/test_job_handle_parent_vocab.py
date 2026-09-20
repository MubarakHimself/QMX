"""Story 57.3 — JobHandle keeps QMA AD-17 vocabulary exactly (SCN-0021 Branch C)."""

from __future__ import annotations

from qma.core.control import author_procedure
from qma.core.control.primitives import Skill
from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.operations import reconcile_external_egress
from qma.core.plugins import analysis_procedure_skill_payload
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.jobs import (
    AWAITING_APPROVAL_GATE,
    AWAITING_APPROVAL_IS_HANDLE_STATE,
    JOB_HANDLE_FORBIDDEN_STATES,
    JobHandle,
)
from qma.core.ports.tools import skill_compiles_to_mission, skill_grants_tool_or_capability
from qma.core.vocabulary.enums import (
    ArtifactCompleteness,
    ExecutionEnvironmentKind,
    JobHandleState,
    TaskMissionState,
)
from qma.daemon import CompileRequest, MissionCompiler, TaskGraphDispatcher
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.taskgraph import instantiate_procedure
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


def _service() -> tuple[JobHandleService, Quant, str, TaskGraphDispatcher]:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    compiled = compiler.compile(CompileRequest(goal=Goal(text="ad17 job"), owner=owner))
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
    service = JobHandleService(dispatcher=dispatcher, router=dispatcher.router)
    return service, owner, task.id, dispatcher


def test_handle_state_is_exactly_the_seven_ad17_members() -> None:
    assert {member.value for member in JobHandleState} == {
        "queued",
        "running",
        "done",
        "failed",
        "cancelled",
        "aborted",
        "unknown",
    }
    assert "succeeded" in JOB_HANDLE_FORBIDDEN_STATES
    assert AWAITING_APPROVAL_GATE in JOB_HANDLE_FORBIDDEN_STATES
    assert AWAITING_APPROVAL_IS_HANDLE_STATE is False
    service, owner, task_id, _dispatcher = _service()
    submitted = service.submit(
        owner=owner,
        task_id=task_id,
        logical_run_id="inv:ad17",
        attempt_id=1,
        artifacts=({"fp1": "fp1:sha256:a", "completeness": "complete"},),
    )
    assert is_ok(submitted)
    assert submitted.value.state is JobHandleState.QUEUED
    assert submitted.value.logical_run_id == "inv:ad17"
    assert submitted.value.attempt_id == 1
    assert submitted.value.artifacts[0].completeness is ArtifactCompleteness.COMPLETE
    for alias in ("succeeded", "awaiting_approval"):
        refused = JobHandle.try_create(
            job_id=submitted.value.job_id,
            owner=owner,
            state=alias,
            task_id=task_id,
        )
        assert is_refusal(refused)
        assert refused.context["field"] == "state"


def test_timeout_and_lost_supervisor_are_unknown_holding_lease() -> None:
    service, owner, task_id, dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id, logical_run_id="inv:to")
    assert is_ok(submitted)
    assert is_ok(service.start(submitted.value.job_id))
    timeout = service.observe_lost_certainty(submitted.value.job_id, trigger="timeout")
    assert is_ok(timeout)
    assert timeout.value.state is JobHandleState.UNKNOWN
    assert timeout.value.is_terminal is False
    assert timeout.value.holds_environment_lease is True
    assert timeout.value.state not in {
        JobHandleState.FAILED,
        JobHandleState.ABORTED,
        JobHandleState.CANCELLED,
        JobHandleState.DONE,
    }
    assert dispatcher.router.is_unknown(task_id)
    assert dispatcher.store.lease_for(task_id) is not None
    located = dispatcher.store.find_task(task_id)
    assert located is not None
    assert located[1].state is TaskMissionState.UNKNOWN
    lost = JobHandleService()
    other = lost.submit(owner=owner, task_id=f"{task_id}-lost")
    assert is_ok(other)
    assert is_ok(lost.start(other.value.job_id))
    supervisor = lost.observe_lost_certainty(other.value.job_id, trigger="lost_supervisor")
    assert is_ok(supervisor)
    assert supervisor.value.state is JobHandleState.UNKNOWN
    assert is_refusal(lost.abort(other.value.job_id, reason="timeout"))
    cancelled = JobHandleService()
    explicit = cancelled.submit(owner=owner, task_id=f"{task_id}-cancel")
    assert is_ok(explicit)
    stopped = cancelled.cancel(explicit.value.job_id)
    assert is_ok(stopped)
    assert stopped.value.state is JobHandleState.CANCELLED
    aborted = JobHandleService()
    env = aborted.submit(owner=owner, task_id=f"{task_id}-abort")
    assert is_ok(env)
    assert is_ok(aborted.start(env.value.job_id))
    killed = aborted.abort(env.value.job_id, reason="oom_kill")
    assert is_ok(killed)
    assert killed.value.state is JobHandleState.ABORTED
    assert killed.value.state is not JobHandleState.CANCELLED


def test_first_durable_terminal_wins_later_commands_are_noops() -> None:
    service, owner, task_id, dispatcher = _service()
    submitted = service.submit(owner=owner, task_id=task_id, logical_run_id="inv:race")
    assert is_ok(submitted)
    assert is_ok(service.start(submitted.value.job_id))
    cancelled = service.cancel(submitted.value.job_id)
    assert is_ok(cancelled)
    assert cancelled.value.state is JobHandleState.CANCELLED
    later_complete = service.complete(submitted.value.job_id, JobHandleState.DONE)
    assert is_ok(later_complete)
    assert later_complete.value.state is JobHandleState.CANCELLED
    assert later_complete.value.state is not JobHandleState.DONE
    assert later_complete.value.later_commands
    assert later_complete.value.later_commands[0]["noop"] is True
    assert later_complete.value.later_commands[0]["ignored_state"] == "done"
    assert later_complete.value.later_commands[0]["terminal_state"] == "cancelled"
    streamed = service.stream(submitted.value.job_id)
    assert is_ok(streamed)
    assert any(event.kind == "terminal_noop" for event in streamed.value)
    located = dispatcher.store.find_task(task_id)
    assert located is not None
    assert located[1].state is TaskMissionState.CANCELLED

    other, owner2, task_id2, dispatcher2 = _service()
    first = other.submit(owner=owner2, task_id=task_id2, logical_run_id="inv:race-2")
    assert is_ok(first)
    assert is_ok(other.start(first.value.job_id))
    done = other.complete(first.value.job_id, "done")
    assert is_ok(done)
    later_cancel = other.cancel(first.value.job_id)
    assert is_ok(later_cancel)
    assert later_cancel.value.state is JobHandleState.DONE
    assert later_cancel.value.later_commands[0]["command"] == "cancel"
    located2 = dispatcher2.store.find_task(task_id2)
    assert located2 is not None
    assert located2[1].state is TaskMissionState.DONE


def test_external_egress_without_receipt_stays_unknown() -> None:
    first = reconcile_external_egress(
        logical_invocation_id="inv:egress-57-3",
        reconcile_policy="query-then-decide",
        receipt=None,
        is_retry=False,
    )
    assert is_ok(first)
    assert first.value.handle_state is JobHandleState.UNKNOWN
    assert first.value.handle_state not in {
        JobHandleState.FAILED,
        JobHandleState.ABORTED,
        JobHandleState.DONE,
    }
    blind = reconcile_external_egress(
        logical_invocation_id="inv:egress-57-3",
        reconcile_policy="query-then-decide",
        receipt=None,
        is_retry=True,
    )
    assert is_refusal(blind)


def test_skills_remain_knowledge_and_never_compile_or_grant() -> None:
    assert skill_compiles_to_mission() is False
    assert skill_grants_tool_or_capability() is False
    skill = Skill(
        qualified_id="analysis-backtest:review",
        version="1",
        summary="Review a fold",
    )
    payload = skill.to_payload()
    assert payload["compiles_to_mission"] is False
    assert payload["grants_tools"] is False
    assert payload["grants_capability"] is False
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.ANALYSIS,
        quant_slug="notebook",
        role=RoleName.ANALYST,
        name="Quant notebook",
    )
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    authored = author_procedure(analysis_procedure_skill_payload())
    assert is_ok(authored)
    refused = instantiate_procedure(authored.value, owner=owner, compiler=compiler)
    assert is_refusal(refused)
    assert refused.context["field"] == "kind"
