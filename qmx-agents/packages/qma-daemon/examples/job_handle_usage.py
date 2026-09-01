"""L27 reference usage: durable JobHandle state and Task mapping (Story 45.4)."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.jobs import JOB_HANDLE_OPERATIONS
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    JobHandleState,
    PrincipalClass,
    TaskMissionState,
)
from qma.daemon import CompileRequest, MissionCompiler, TaskGraphDispatcher
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qmf.core import is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    compiled = compiler.compile(CompileRequest(goal=Goal(text="run job"), owner=owner))
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
    task_id = compiled.value.task_graph.tasks[0].id
    assert is_ok(dispatcher.dispatch_task(task_id=task_id, holder_agent_id="agent:w1"))

    service = JobHandleService(dispatcher=dispatcher, router=router)
    assert service.operations == JOB_HANDLE_OPERATIONS
    submitted = service.submit(owner=owner, task_id=task_id)
    assert is_ok(submitted)
    assert submitted.value.state is JobHandleState.QUEUED
    assert is_ok(service.attach(submitted.value.job_id))
    assert is_ok(service.start(submitted.value.job_id))
    lost = service.observe_lost_certainty(submitted.value.job_id, trigger="timeout")
    assert is_ok(lost)
    assert lost.value.state is JobHandleState.UNKNOWN
    assert is_refusal(service.retry(submitted.value.job_id))
    machine = service.resolve_unknown(
        submitted.value.job_id,
        principal=PrincipalClass.MACHINE,
        recorded=True,
        to_state=JobHandleState.FAILED,
    )
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    resolved = service.resolve_unknown(
        submitted.value.job_id,
        principal=PrincipalClass.OPERATOR,
        recorded=True,
        to_state=JobHandleState.FAILED,
    )
    assert is_ok(resolved)
    located = dispatcher.store.find_task(task_id)
    assert located is not None
    assert located[1].state is TaskMissionState.FAILED
    snapshot = service.snapshot()
    restarted = JobHandleService()
    assert is_ok(restarted.recover_after_restart(snapshot))
    reattached = restarted.reattach(submitted.value.job_id, daemon_restarted=True)
    assert is_ok(reattached)
    assert reattached.value.state is JobHandleState.FAILED
    print("JobHandle minted, mapped by daemon, unknown held for operator resolution")


if __name__ == "__main__":
    main()
