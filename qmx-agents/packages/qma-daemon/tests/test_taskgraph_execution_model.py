"""Story 43.3 — Graph Template, Loop, Skill, and node-kind execution model."""

from __future__ import annotations

import pytest
from qma.core.control import (
    DAEMON_EVALUATED_NODE_KINDS,
    DEFERRED_GRAPH_EXCLUSIONS,
    ControlPrimitive,
    Skill,
    emits_task,
    holds_dispatch_lease,
    is_skill_distinct_from_loop,
    node_carries_ledger,
)
from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.vocabulary.enums import (
    TASK_EMITTING_NODE_KINDS,
    GraphArtifactKind,
    NodeKind,
    TaskMissionState,
)
from qma.daemon.taskgraph import (
    DAEMON_CONTRIBUTED_GRAPH_TEMPLATES,
    MISSION_TEMPLATE_REGISTRY,
    CompileRequest,
    GraphTemplate,
    GraphTemplateCatalog,
    LoopNodeState,
    MissionCompiler,
    TaskGraph,
    TaskGraphNode,
    assert_template_not_interchanged,
    deterministic_task_id,
    loop_state_from_node_config,
    mint_loop_iteration_task,
    validate_graph_template_topology,
    validate_no_daemon_graph_template,
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


def test_graph_template_is_authored_versioned_stateless() -> None:
    nodes = [{"id": "survey", "kind": "task", "intent": "collect"}]
    template = GraphTemplate(
        qualified_id="research-corpus:survey",
        version="1.0.0",
        nodes=tuple(nodes),
        edges=(),
    )
    assert template.artifact_kind is GraphArtifactKind.GRAPH_TEMPLATE
    assert template.to_payload()["stateless"] is True
    assert template.to_payload()["runtime_state"] is None

    # Mutating the contribution source must not mutate the authored template.
    nodes[0]["intent"] = "tampered"
    assert template.nodes[0]["intent"] == "collect"

    with pytest.raises(TypeError):
        template.nodes[0]["intent"] = "mutated"  # type: ignore[index]


def test_run_never_interchanges_template_with_task_graph() -> None:
    owner = _quant()
    catalog = GraphTemplateCatalog()
    template = GraphTemplate(
        qualified_id="research-corpus:pipeline",
        version="1",
        nodes=({"id": "step", "kind": "task", "intent": "run"},),
    )
    assert is_ok(catalog.register(template))
    compiler = MissionCompiler(
        templates=catalog,
        known_quant_actor_ids={owner.actor_id.value},
    )
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="run pipeline"),
            owner=owner,
            graph_template_ref="research-corpus:pipeline",
            require_decomposition_reasoning=False,
        )
    )
    assert is_ok(compiled)
    graph = compiled.value.task_graph
    assert graph.artifact_kind is GraphArtifactKind.TASK_GRAPH
    assert graph.graph_template_ref == template.qualified_id
    # Catalog still holds the original authored template — not the Task Graph.
    stored = catalog.get("research-corpus:pipeline")
    assert stored is not None
    assert stored.artifact_kind is GraphArtifactKind.GRAPH_TEMPLATE
    assert stored.qualified_id == template.qualified_id
    assert is_ok(assert_template_not_interchanged(stored, graph))


def test_skill_is_distinct_from_loop_and_may_invoke_one() -> None:
    skill = Skill(
        qualified_id="research-corpus:summarize",
        version="1",
        summary="Summarize evidence packs",
        body="Read citations then write a digest.",
        loop_ref="act-observe-verify",
        disclosures=("summary", "body"),
    )
    assert skill.is_loop is False
    assert skill.invokes_loop is True
    assert is_skill_distinct_from_loop(skill)
    payload = skill.to_payload()
    assert payload["control_primitive"] == ControlPrimitive.SKILL.value
    assert payload["grants_capability"] is False
    assert payload["is_loop"] is False

    plain = Skill(
        qualified_id="dev-factory:lint-notes",
        version="1",
        summary="Lint notes without a loop",
    )
    assert plain.invokes_loop is False
    assert plain.is_loop is False


def test_ten_node_kinds_only_three_emit_tasks() -> None:
    assert len(tuple(NodeKind)) == 10
    assert frozenset({NodeKind.TASK, NodeKind.AGENT, NodeKind.LOOP}) == TASK_EMITTING_NODE_KINDS
    assert (
        frozenset(
            {
                NodeKind.CONDITIONAL,
                NodeKind.PARALLEL_BRANCH,
                NodeKind.JOIN,
                NodeKind.APPROVAL_GATE,
                NodeKind.HUMAN_GATE,
                NodeKind.DETERMINISTIC_SCRIPT,
                NodeKind.ARTIFACT_DEPENDENCY,
            }
        )
        == DAEMON_EVALUATED_NODE_KINDS
    )
    for kind in NodeKind:
        node = TaskGraphNode(id=kind.value, kind=kind)
        assert node.emits_task is emits_task(kind)
        assert node.holds_dispatch_lease is holds_dispatch_lease(kind)
        assert node.carries_ledger is node_carries_ledger(kind)
        if kind in TASK_EMITTING_NODE_KINDS:
            assert node.is_daemon_evaluated is False
        else:
            assert node.is_daemon_evaluated is True
            assert node.holds_dispatch_lease is False
            assert node.carries_ledger is False


def test_loop_runtime_controls_are_node_state_not_task_fields() -> None:
    owner = _quant()
    node = TaskGraphNode(
        id="observe",
        kind=NodeKind.LOOP,
        config={
            "stopping_condition": "max_iterations>=3",
            "budget": {"tokens": 1_000},
            "escalation": "quant_mailbox",
        },
    )
    state = loop_state_from_node_config(node)
    assert is_ok(state)
    loop = state.value
    assert loop.stopping_condition == "max_iterations>=3"
    assert loop.budget["tokens"] == 1_000
    assert loop.escalation == "quant_mailbox"
    assert loop.iteration == 0
    assert loop.control_primitive is ControlPrimitive.LOOP

    graph = TaskGraph(
        id="taskgraph:demo",
        mission_id="mission:demo",
        nodes=(node,),
        tasks=(),
        graph_template_ref="research-corpus:observe",
    )
    minted = mint_loop_iteration_task(
        graph=graph,
        node=node,
        loop_state=loop,
        owner=owner.actor_id,
        intent="observe once",
    )
    assert is_ok(minted)
    task, advanced = minted.value
    assert task.id == deterministic_task_id(graph.id, node.id, iteration=0, retry_index=0)
    assert task.node_kind is NodeKind.LOOP
    assert task.state is TaskMissionState.READY
    # Authoritative iteration advanced on node state.
    assert advanced.iteration == 1
    assert advanced.stopping_condition == loop.stopping_condition
    assert "stopping_condition" not in task.to_payload()
    assert "budget" not in task.to_payload()
    assert "escalation" not in task.to_payload()
    # Task may carry mint-time provenance indices, but controls stay on the node.
    assert task.iteration == 0
    assert advanced.to_payload()["runtime_owned"] is True

    graph2 = graph.append_task(task)
    duplicate = mint_loop_iteration_task(
        graph=graph2,
        node=node,
        loop_state=loop,  # same iteration again
        owner=owner.actor_id,
    )
    assert is_refusal(duplicate)

    next_mint = mint_loop_iteration_task(
        graph=graph2,
        node=node,
        loop_state=advanced,
        owner=owner.actor_id,
    )
    assert is_ok(next_mint)
    task2, advanced2 = next_mint.value
    assert task2.id == deterministic_task_id(graph.id, node.id, iteration=1, retry_index=0)
    assert advanced2.iteration == 2


def test_stopped_loop_emits_no_further_tasks() -> None:
    owner = _quant()
    node = TaskGraphNode(id="loop", kind=NodeKind.LOOP)
    loop = LoopNodeState(
        node_id="loop",
        stopping_condition="done",
        budget={},
        escalation="quant_mailbox",
        iteration=2,
    ).mark_stopped(reason="stopping_condition_met")
    graph = TaskGraph(id="taskgraph:x", mission_id="mission:x", nodes=(node,))
    refused = mint_loop_iteration_task(
        graph=graph,
        node=node,
        loop_state=loop,
        owner=owner.actor_id,
    )
    assert is_refusal(refused)


def test_back_edge_refused_at_registration() -> None:
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
    refused = catalog.register(template)
    assert is_refusal(refused)
    assert "dev-factory:cycle" not in catalog

    direct = validate_graph_template_topology(template)
    assert is_refusal(direct)


def test_daemon_contributes_no_graph_template_and_gaps_deferred() -> None:
    assert DAEMON_CONTRIBUTED_GRAPH_TEMPLATES == ()
    assert MISSION_TEMPLATE_REGISTRY is None
    assert "GAP-0084" in DEFERRED_GRAPH_EXCLUSIONS
    assert "GAP-0086" in DEFERRED_GRAPH_EXCLUSIONS

    for banned in ("qma-daemon:builtin", "daemon:cycle", "qma:observe"):
        assert is_refusal(validate_no_daemon_graph_template(banned))

    catalog = GraphTemplateCatalog()
    refused = catalog.register(
        GraphTemplate(
            qualified_id="qma-daemon:act-observe-verify",
            version="1",
            nodes=({"id": "a", "kind": "task"},),
        )
    )
    assert is_refusal(refused)


def test_non_emitting_kinds_materialize_without_tasks() -> None:
    owner = _quant()
    catalog = GraphTemplateCatalog()
    template = GraphTemplate(
        qualified_id="pm-coordination:gate",
        version="1",
        nodes=(
            {"id": "check", "kind": "conditional"},
            {"id": "approve", "kind": "approval_gate"},
            {"id": "join", "kind": "join"},
            {"id": "work", "kind": "task", "intent": "do work", "seed": True},
        ),
        edges=(
            {"from": "check", "to": "approve"},
            {"from": "approve", "to": "work"},
            {"from": "work", "to": "join"},
        ),
    )
    assert is_ok(catalog.register(template))
    compiler = MissionCompiler(
        templates=catalog,
        known_quant_actor_ids={owner.actor_id.value},
    )
    compiled = compiler.compile(
        CompileRequest(
            goal=Goal(text="gated work"),
            owner=owner,
            graph_template_ref="pm-coordination:gate",
            require_decomposition_reasoning=False,
        )
    )
    assert is_ok(compiled)
    graph = compiled.value.task_graph
    kinds = {n.id: n.kind for n in graph.nodes}
    assert kinds["check"] is NodeKind.CONDITIONAL
    assert kinds["approve"] is NodeKind.APPROVAL_GATE
    assert kinds["join"] is NodeKind.JOIN
    assert all(not n.holds_dispatch_lease for n in graph.nodes if not n.emits_task)
    assert all(not n.carries_ledger for n in graph.nodes if not n.emits_task)
    assert len(graph.tasks) == 1
    assert graph.tasks[0].node_kind is NodeKind.TASK
