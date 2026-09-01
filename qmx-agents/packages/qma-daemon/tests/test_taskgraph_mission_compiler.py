"""Story 43.1 — Deterministic Task Graph, Mission, compiler, scheduler, dispatcher."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    GraphArtifactKind,
    NodeKind,
    TaskMissionState,
)
from qma.daemon import CompileRequest, MissionCompiler, TaskGraphDispatcher
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.taskgraph import (
    MISSION_DIRECTOR_ROLE,
    RESERVED_APPROVAL_ROUTE_OPERATOR,
    GraphTemplate,
    GraphTemplateCatalog,
    ProposedTransition,
    derive_mission_desk,
    validate_approval_route,
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


def test_compile_goal_creates_one_mission_and_task_graph() -> None:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    result = compiler.compile(
        CompileRequest(
            goal=Goal(text="survey corpus coverage"),
            owner=owner,
            intent="survey corpus coverage",
            scope="research/corpus",
            constraints=("read_only",),
            evidence_requirements=("citation",),
            capabilities=("knowledge.search",),
            success_criteria=("coverage_report",),
            outputs=("report_ref",),
            verification="deterministic_verifier",
            budget={"tokens": 10_000},
            escalation="quant_mailbox",
            termination_criteria=("budget_exhausted",),
            approval_route=RESERVED_APPROVAL_ROUTE_OPERATOR,
        )
    )
    assert is_ok(result), result
    compiled = result.value
    mission = compiled.mission
    graph = compiled.task_graph

    assert mission.owner == owner.actor_id
    assert mission.goal.text == "survey corpus coverage"
    assert mission.intent == "survey corpus coverage"
    assert mission.scope == "research/corpus"
    assert mission.constraints == ("read_only",)
    assert mission.evidence_requirements == ("citation",)
    assert mission.capabilities == ("knowledge.search",)
    assert mission.success_criteria == ("coverage_report",)
    assert mission.outputs == ("report_ref",)
    assert mission.verification == "deterministic_verifier"
    assert mission.budget["tokens"] == 10_000
    assert mission.escalation == "quant_mailbox"
    assert mission.termination_criteria == ("budget_exhausted",)
    assert mission.approval_route == RESERVED_APPROVAL_ROUTE_OPERATOR
    assert "desk" not in mission.to_payload()
    assert derive_mission_desk(mission, owner) is DeskSlug.RESEARCH
    assert mission.desk_for(owner) is DeskSlug.RESEARCH

    assert graph.mission_id == mission.id
    assert graph.artifact_kind is GraphArtifactKind.TASK_GRAPH
    assert mission.task_graph_id == graph.id
    assert len(graph.tasks) == 1

    # Same inputs compile to the same Mission / Task Graph ids.
    again = compiler.compile(
        CompileRequest(
            goal=Goal(text="survey corpus coverage"),
            owner=owner,
            intent="survey corpus coverage",
            approval_route=RESERVED_APPROVAL_ROUTE_OPERATOR,
        )
    )
    assert is_ok(again)
    assert again.value.mission.id == mission.id
    assert again.value.task_graph.id == graph.id


def test_approval_route_accepts_operator_or_existing_quant_only() -> None:
    owner = _quant(slug="alpha")
    peer = _quant(slug="beta")
    known = {owner.actor_id.value, peer.actor_id.value}

    ok_operator = validate_approval_route(
        RESERVED_APPROVAL_ROUTE_OPERATOR,
        known_quant_actor_ids=known,
    )
    assert is_ok(ok_operator)
    assert ok_operator.value == RESERVED_APPROVAL_ROUTE_OPERATOR

    ok_peer = validate_approval_route(peer.actor_id.value, known_quant_actor_ids=known)
    assert is_ok(ok_peer)
    assert ok_peer.value == peer.actor_id.value

    missing = ActorId.mint(DeskSlug.RESEARCH, "ghost")
    assert is_ok(missing)
    refused = validate_approval_route(missing.value.value, known_quant_actor_ids=known)
    assert is_refusal(refused)

    compiler = MissionCompiler(known_quant_actor_ids=known)
    compile_refused = compiler.compile(
        CompileRequest(
            goal=Goal(text="needs approval"),
            owner=owner,
            approval_route=missing.value.value,
        )
    )
    assert is_refusal(compile_refused)


def test_decomposition_emits_mission_director_task() -> None:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    result = compiler.compile(
        CompileRequest(
            goal=Goal(text="reason about decomposition"),
            owner=owner,
            require_decomposition_reasoning=True,
        )
    )
    assert is_ok(result)
    graph = result.value.task_graph
    assert len(graph.tasks) == 1
    task = graph.tasks[0]
    assert task.agent_role == MISSION_DIRECTOR_ROLE
    assert task.is_mission_director_task
    assert task.node_kind is NodeKind.AGENT
    assert task.state is TaskMissionState.READY
    assert "intent" in task.to_payload()
    assert "inputs" in task.to_payload()
    assert "refs" in task.to_payload()
    assert "acceptance_criteria" in task.to_payload()
    assert task.ledger is not None
    assert task.to_payload()["transcript_independent"] is True

    # Mission Director is not an ontology object; state only via proposed transitions.
    from qma.core.ontology import is_ontology_object

    assert is_ontology_object("MissionDirector") is False
    assert is_ontology_object("Agent") is True

    dispatcher = TaskGraphDispatcher()
    dispatcher.materialize(graph)
    agent_id = TaskGraphDispatcher.mission_director_agent_id(
        owner.actor_id, result.value.mission.id
    )
    terminal = validate_proposed_transition(
        ProposedTransition(
            target_kind="task",
            target_id=task.id,
            from_state=TaskMissionState.READY,
            to_state=TaskMissionState.DONE,
            proposed_by_agent_id=agent_id,
            rationale="director must not author terminal",
        ),
        current_state=TaskMissionState.READY,
    )
    assert is_refusal(terminal)

    nonterminal = dispatcher.apply_proposed_transition(
        ProposedTransition(
            target_kind="task",
            target_id=task.id,
            from_state=TaskMissionState.READY,
            to_state=TaskMissionState.BLOCKED,
            proposed_by_agent_id=agent_id,
            rationale="awaiting inputs",
        )
    )
    assert is_ok(nonterminal)
    assert nonterminal.value.state is TaskMissionState.BLOCKED


def test_task_is_transcript_independent_across_reassignment() -> None:
    owner = _quant()
    catalog = GraphTemplateCatalog()
    template = GraphTemplate(
        qualified_id="research-corpus:survey",
        version="1",
        nodes=(
            {
                "id": "survey",
                "kind": "task",
                "intent": "collect evidence",
                "inputs": {"topic": "coverage"},
                "refs": ["knowledge:corpus"],
                "acceptance_criteria": ["citations_present"],
            },
        ),
    )
    assert is_ok(catalog.register(template))
    compiler = MissionCompiler(
        templates=catalog,
        known_quant_actor_ids={owner.actor_id.value},
    )
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="collect evidence"),
            owner=owner,
            graph_template_ref="research-corpus:survey",
            require_decomposition_reasoning=False,
        )
    )
    assert is_ok(compiled)
    graph = compiled.value.task_graph
    task = graph.tasks[0]
    assert task.intent == "collect evidence"
    assert task.inputs["topic"] == "coverage"
    assert task.refs == ("knowledge:corpus",)
    assert task.acceptance_criteria == ("citations_present",)
    assert task.ledger is not None
    ledger_after = task.ledger.append(
        {"kind": "progress", "note": "first agent notes", "authored_by": "agent-a"}
    )
    from qma.daemon.taskgraph import TaskRecord

    task_with_ledger = TaskRecord(
        id=task.id,
        mission_id=task.mission_id,
        owner=task.owner,
        intent=task.intent,
        inputs=dict(task.inputs),
        refs=task.refs,
        acceptance_criteria=task.acceptance_criteria,
        state=task.state,
        node_id=task.node_id,
        node_kind=task.node_kind,
        agent_role=task.agent_role,
        worker_template_ref=task.worker_template_ref,
        iteration=task.iteration,
        retry_index=task.retry_index,
        attempt_of=task.attempt_of,
        ledger=ledger_after,
    )

    dispatcher = TaskGraphDispatcher()
    dispatcher.materialize(graph.replace_task(task_with_ledger))
    assert is_ok(dispatcher.dispatch_task(task_id=task.id, holder_agent_id="agent-a"))
    reassigned = dispatcher.reassign(task_id=task.id, new_holder_agent_id="agent-b")
    assert is_ok(reassigned)
    assert reassigned.value.holder_agent_id == "agent-b"
    stored = dispatcher.store.for_mission(compiled.value.mission.id)
    assert stored is not None
    held = stored.task_by_id(task.id)
    assert held is not None
    assert held.ledger is not None
    assert held.intent == "collect evidence"
    assert any(e.get("note") == "first agent notes" for e in held.ledger.entries)


def test_dispatcher_grants_dispatch_lease_and_evaluates_environment() -> None:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    compiled = compiler.compile(CompileRequest(goal=Goal(text="run work"), owner=owner))
    assert is_ok(compiled)
    mission = compiled.value.mission
    graph = compiled.value.task_graph

    empty_envs = ExecutionEnvironmentRegistry()
    assert empty_envs.is_empty()
    dispatcher = TaskGraphDispatcher(environments=empty_envs)
    dispatcher.materialize(graph)

    # Compilation already succeeded; empty env registry does not undo it.
    assert mission.id
    assert graph.id

    decision = dispatcher.dispatch_next(
        mission_id=mission.id,
        holder_agent_id="agent-worker-1",
        environment_kind=ExecutionEnvironmentKind.DOCKER,
    )
    assert is_ok(decision)
    payload = decision.value.to_payload()
    assert payload["dispatch_lease"]["lease"] == "dispatch_lease"
    assert payload["dispatch_lease"]["holder_agent_id"] == "agent-worker-1"
    assert payload["environment_available"] is False
    assert payload["environment_refusal"]["variant"] == "NoEnvironment"
    assert payload["synchronization"] == "task_graph"
    assert decision.value.task.state is TaskMissionState.RUNNING
    env_refusal = decision.value.environment_refusal
    assert env_refusal is not None
    assert NoEnvironment.matches(env_refusal)

    # Registered provider may issue the environment_lease.
    populated = ExecutionEnvironmentRegistry()
    assert is_ok(
        populated.register(ExecutionEnvironmentKind.DOCKER, _EnvStub(), provider_id="local-docker")
    )
    lease = populated.evaluate_environment_lease(
        task_id="task:probe",
        kind=ExecutionEnvironmentKind.DOCKER,
    )
    assert is_ok(lease)
    assert lease.value.kind == "docker"
    assert lease.value.provider_id == "local-docker"
    assert lease.value.task_id == "task:probe"

    owner2 = _quant(slug="gamma")
    compiled2 = compiler.compile(CompileRequest(goal=Goal(text="run with env"), owner=owner2))
    assert is_ok(compiled2)
    dispatcher2 = TaskGraphDispatcher(environments=populated)
    dispatcher2.materialize(compiled2.value.task_graph)
    decision2 = dispatcher2.dispatch_next(
        mission_id=compiled2.value.mission.id,
        holder_agent_id="agent-worker-2",
        environment_kind="docker",
    )
    assert is_ok(decision2)
    assert decision2.value.environment_available is True
    assert decision2.value.environment_lease is not None
    assert decision2.value.environment_lease.kind == "docker"
    assert decision2.value.environment_lease.provider_id == "local-docker"


def test_back_edge_in_template_refused_at_compile() -> None:
    owner = _quant()
    catalog = GraphTemplateCatalog()
    template = GraphTemplate(
        qualified_id="dev-factory:cycle",
        version="1",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "b", "kind": "task"},
        ),
        edges=(
            {"from": "a", "to": "b"},
            {"from": "b", "to": "a"},
        ),
    )
    assert is_ok(catalog.register(template))
    compiler = MissionCompiler(
        templates=catalog,
        known_quant_actor_ids={owner.actor_id.value},
    )
    refused = compiler.compile(
        CompileRequest(
            goal=Goal(text="cyclic"),
            owner=owner,
            graph_template_ref="dev-factory:cycle",
            require_decomposition_reasoning=False,
        )
    )
    assert is_refusal(refused)


def test_scaffold_exports_compiler_and_dispatcher() -> None:
    import qma.daemon.envs
    import qma.daemon.scheduler
    import qma.daemon.taskgraph

    assert qma.daemon.taskgraph.MissionCompiler.__name__ == "MissionCompiler"
    assert qma.daemon.envs.ExecutionEnvironmentRegistry.__name__ == ("ExecutionEnvironmentRegistry")
    assert "Routines" in (qma.daemon.scheduler.__doc__ or "")
