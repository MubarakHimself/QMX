"""Story 43.2 — Closed Task/Mission state with evidence-bound terminal outcomes."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.vocabulary.enums import (
    TASK_MISSION_TERMINAL_STATES,
    ExecutionEnvironmentKind,
    JobHandleState,
    TaskMissionState,
    is_task_mission_terminal,
    map_job_handle_to_task_state,
)
from qma.daemon import CompileRequest, MissionCompiler, TaskGraphDispatcher
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.taskgraph import (
    JobHandleEvidence,
    MissionRecord,
    ProposedTransition,
    TaskRecord,
    compute_mission_state,
    validate_proposed_transition,
)
from qmf.core import is_ok, is_refusal


def _quant(*, slug: str = "alpha", desk: DeskSlug = DeskSlug.RESEARCH) -> Quant:
    minted = ActorId.mint(desk, slug)
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=desk,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
    )


class _EnvStub:
    """Structural ExecutionEnvironment stand-in for registry tests."""


def _compile_and_dispatch(
    *,
    with_environment: bool = True,
) -> tuple[TaskGraphDispatcher, MissionRecord, TaskRecord]:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="close outcomes lawfully"),
            owner=owner,
        )
    )
    assert is_ok(compiled)
    mission = compiled.value.mission
    graph = compiled.value.task_graph
    envs = ExecutionEnvironmentRegistry()
    if with_environment:
        assert is_ok(
            envs.register(
                ExecutionEnvironmentKind.DOCKER,
                _EnvStub(),
                provider_id="local-docker",
                declaration=ExecutionEnvironmentDeclaration.isolated(
                    ExecutionEnvironmentKind.DOCKER,
                    provider_ref="local-docker",
                ),
            )
        )
    dispatcher = TaskGraphDispatcher(environments=envs)
    dispatcher.materialize(graph, mission=mission)
    task = graph.tasks[0]
    decision = dispatcher.dispatch_task(
        task_id=task.id,
        holder_agent_id="agent:worker:1",
    )
    assert is_ok(decision)
    return dispatcher, mission, decision.value.task


def test_closed_vocabulary_exactly_eight_states_three_terminal() -> None:
    assert {s.value for s in TaskMissionState} == {
        "pending",
        "ready",
        "running",
        "blocked",
        "unknown",
        "done",
        "failed",
        "cancelled",
    }
    assert (
        frozenset(
            {
                TaskMissionState.DONE,
                TaskMissionState.FAILED,
                TaskMissionState.CANCELLED,
            }
        )
        == TASK_MISSION_TERMINAL_STATES
    )
    for state in TaskMissionState:
        assert is_task_mission_terminal(state) is (state in TASK_MISSION_TERMINAL_STATES)


def test_llm_proposal_cannot_author_terminal_even_after_dispatch() -> None:
    dispatcher, _mission, task = _compile_and_dispatch()
    agent_id = "agent:mission_director:x"
    for terminal in TASK_MISSION_TERMINAL_STATES:
        refused = validate_proposed_transition(
            ProposedTransition(
                target_kind="task",
                target_id=task.id,
                from_state=TaskMissionState.RUNNING,
                to_state=terminal,
                proposed_by_agent_id=agent_id,
            ),
            current_state=TaskMissionState.RUNNING,
        )
        assert is_refusal(refused)
        applied = dispatcher.apply_proposed_transition(
            ProposedTransition(
                target_kind="task",
                target_id=task.id,
                from_state=TaskMissionState.RUNNING,
                to_state=terminal,
                proposed_by_agent_id=agent_id,
            )
        )
        assert is_refusal(applied)
    # Task still running — no terminal authored.
    located = dispatcher.store.find_task(task.id)
    assert located is not None
    assert located[1].state is TaskMissionState.RUNNING


def test_dispatched_terminal_requires_job_handle_evidence() -> None:
    dispatcher, _mission, task = _compile_and_dispatch()
    # Cancel-without-handle path refuses for dispatched Tasks.
    refused = dispatcher.cancel_never_dispatched(task_id=task.id)
    assert is_refusal(refused)

    evidence = JobHandleEvidence(
        job_id="job-1",
        task_id=task.id,
        state=JobHandleState.DONE,
    )
    result = dispatcher.apply_job_handle_evidence(evidence)
    assert is_ok(result)
    assert result.value.task.state is TaskMissionState.DONE
    assert result.value.job_handle is not None
    assert result.value.dispatch_lease_retained is False
    assert result.value.environment_lease_retained is False
    assert dispatcher.store.lease_for(task.id) is None
    assert dispatcher.store.environment_lease_for(task.id) is None


def test_aborted_job_maps_to_failed_with_reason_never_cancelled() -> None:
    dispatcher, _mission, task = _compile_and_dispatch()
    evidence = JobHandleEvidence(
        job_id="job-abort",
        task_id=task.id,
        state=JobHandleState.ABORTED,
        abort_reason="oom_kill",
    )
    assert map_job_handle_to_task_state(JobHandleState.ABORTED) is TaskMissionState.FAILED
    result = dispatcher.apply_job_handle_evidence(evidence)
    assert is_ok(result)
    assert result.value.task.state is TaskMissionState.FAILED
    assert result.value.task.state is not TaskMissionState.CANCELLED
    assert result.value.task.ledger is not None
    assert any(e.get("kind") == "job_aborted" for e in result.value.task.ledger.entries)


def test_never_dispatched_task_cancels_without_job_handle() -> None:
    owner = _quant(slug="beta")
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    compiled = compiler.compile(CompileRequest(goal=Goal(text="cancel before start"), owner=owner))
    assert is_ok(compiled)
    dispatcher = TaskGraphDispatcher()
    dispatcher.materialize(compiled.value.task_graph, mission=compiled.value.mission)
    task = compiled.value.task_graph.tasks[0]
    assert task.state is TaskMissionState.READY
    assert dispatcher.store.was_dispatched(task.id) is False

    # Only cancelled is legal; done/failed refused.
    for illegal in (TaskMissionState.DONE, TaskMissionState.FAILED):
        from qma.daemon.taskgraph.state import validate_never_dispatched_cancel

        bad = validate_never_dispatched_cancel(
            current_state=task.state,
            to_state=illegal,
            was_dispatched=False,
        )
        assert is_refusal(bad)

    result = dispatcher.cancel_never_dispatched(task_id=task.id)
    assert is_ok(result)
    assert result.value.task.state is TaskMissionState.CANCELLED
    assert result.value.job_handle is None
    assert dispatcher.store.job_handle_for(task.id) is None


def test_unknown_job_handle_retains_leases_and_mission_is_unknown_not_failed() -> None:
    dispatcher, mission, task = _compile_and_dispatch(with_environment=True)
    assert dispatcher.store.lease_for(task.id) is not None
    assert dispatcher.store.environment_lease_for(task.id) is not None

    evidence = JobHandleEvidence(
        job_id="job-unk",
        task_id=task.id,
        state=JobHandleState.UNKNOWN,
    )
    result = dispatcher.apply_job_handle_evidence(evidence)
    assert is_ok(result)
    assert result.value.task.state is TaskMissionState.UNKNOWN
    assert result.value.dispatch_lease_retained is True
    assert result.value.environment_lease_retained is True
    assert dispatcher.store.lease_for(task.id) is not None
    assert dispatcher.store.environment_lease_for(task.id) is not None

    # Completion blocked: terminal proposal still refused; second terminal
    # evidence via apply without resolve path still works through resolve API.
    terminal_attempt = dispatcher.apply_proposed_transition(
        ProposedTransition(
            target_kind="task",
            target_id=task.id,
            from_state=TaskMissionState.UNKNOWN,
            to_state=TaskMissionState.FAILED,
            proposed_by_agent_id="agent:x",
        )
    )
    assert is_refusal(terminal_attempt)

    mission_state = dispatcher.mission_state_for(mission.id)
    assert is_ok(mission_state)
    assert mission_state.value is TaskMissionState.UNKNOWN
    assert mission_state.value is not TaskMissionState.FAILED
    stored_mission = dispatcher.store.mission(mission.id)
    assert stored_mission is not None
    assert stored_mission.state is TaskMissionState.UNKNOWN


def test_resolve_unknown_with_terminal_evidence_releases_leases() -> None:
    dispatcher, mission, task = _compile_and_dispatch()
    unknown = JobHandleEvidence(
        job_id="job-unk-2",
        task_id=task.id,
        state=JobHandleState.UNKNOWN,
    )
    assert is_ok(dispatcher.apply_job_handle_evidence(unknown))

    resolved = JobHandleEvidence(
        job_id="job-unk-2",
        task_id=task.id,
        state=JobHandleState.FAILED,
    )
    result = dispatcher.resolve_unknown_job_handle(resolved)
    assert is_ok(result)
    assert result.value.task.state is TaskMissionState.FAILED
    assert result.value.dispatch_lease_retained is False
    assert result.value.environment_lease_retained is False
    assert dispatcher.store.lease_for(task.id) is None

    mission_state = dispatcher.mission_state_for(mission.id)
    assert is_ok(mission_state)
    assert mission_state.value is TaskMissionState.FAILED


def test_mission_terminal_computed_from_tasks_not_job_handle() -> None:
    assert compute_mission_state(()) is TaskMissionState.PENDING
    assert (
        compute_mission_state((TaskMissionState.DONE, TaskMissionState.DONE))
        is TaskMissionState.DONE
    )
    assert (
        compute_mission_state((TaskMissionState.DONE, TaskMissionState.FAILED))
        is TaskMissionState.FAILED
    )
    assert (
        compute_mission_state((TaskMissionState.CANCELLED, TaskMissionState.CANCELLED))
        is TaskMissionState.CANCELLED
    )
    # unknown wins over failed — Mission never failed while unknown present.
    assert (
        compute_mission_state((TaskMissionState.FAILED, TaskMissionState.UNKNOWN))
        is TaskMissionState.UNKNOWN
    )
    assert (
        compute_mission_state((TaskMissionState.RUNNING, TaskMissionState.READY))
        is TaskMissionState.RUNNING
    )


def test_each_task_at_most_one_terminal_state() -> None:
    dispatcher, _mission, task = _compile_and_dispatch()
    first = dispatcher.apply_job_handle_evidence(
        JobHandleEvidence(
            job_id="job-once",
            task_id=task.id,
            state=JobHandleState.DONE,
        )
    )
    assert is_ok(first)
    second = dispatcher.apply_job_handle_evidence(
        JobHandleEvidence(
            job_id="job-once",
            task_id=task.id,
            state=JobHandleState.FAILED,
        )
    )
    assert is_refusal(second)
    located = dispatcher.store.find_task(task.id)
    assert located is not None
    assert located[1].state is TaskMissionState.DONE


def test_mismatched_proposed_terminal_refused_even_with_evidence() -> None:
    dispatcher, _mission, task = _compile_and_dispatch()
    refused = dispatcher.apply_job_handle_evidence(
        JobHandleEvidence(
            job_id="job-mis",
            task_id=task.id,
            state=JobHandleState.DONE,
        ),
        proposed_to_state=TaskMissionState.FAILED,
    )
    assert is_refusal(refused)
