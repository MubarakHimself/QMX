"""Story 43.3 — Graph Template, Loop, Skill, and node-kind execution model."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

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
from qma.core.operations import parse_operation_descriptor, public_operation_descriptors
from qma.core.vocabulary.enums import (
    TASK_EMITTING_NODE_KINDS,
    GraphArtifactKind,
    NodeKind,
    TaskMissionState,
)
from qma.daemon.taskgraph import (
    DAEMON_CONTRIBUTED_GRAPH_TEMPLATES,
    MISSION_TEMPLATE_REGISTRY,
    TOPOLOGY_REFUSAL_CODES,
    TOPOLOGY_REFUSAL_FAMILY,
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
from qmf.core import RefusalCategory, TypedRefusal, is_ok, is_refusal


def _edge(
    src: str,
    dst: str,
    *,
    mapping: str = "one",
    from_port: str = "data",
    to_port: str = "data",
    cartesian: bool | None = None,
    **extra: object,
) -> dict[str, object]:
    """Story 56.3 — edges declare mapping + port kinds (AD-5; FR-WF-42)."""
    payload: dict[str, object] = {
        "from": src,
        "to": dst,
        "mapping": mapping,
        "from_port": from_port,
        "to_port": to_port,
    }
    if cartesian is not None:
        payload["cartesian"] = cartesian
    payload.update(extra)
    return payload


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
        edges=(_edge("a", "b"), _edge("b", "a")),
    )
    refused = catalog.register(template)
    assert is_refusal(refused)
    assert "dev-factory:cycle" not in catalog

    direct = validate_graph_template_topology(template)
    assert is_refusal(direct)


def test_directed_triangle_cycle_refused_at_registration() -> None:
    """Story 56.1 / FR-WF-40 — A→B→C→A must refuse; reverse-edge-only is a hole."""
    template = GraphTemplate(
        qualified_id="dev-factory:triangle-cycle",
        version="1",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "b", "kind": "task"},
            {"id": "c", "kind": "task"},
        ),
        edges=(_edge("a", "b"), _edge("b", "c"), _edge("c", "a")),
    )
    direct = validate_graph_template_topology(template)
    assert is_refusal(direct)

    catalog = GraphTemplateCatalog()
    refused = catalog.register(template)
    assert is_refusal(refused)
    assert "dev-factory:triangle-cycle" not in catalog


def test_self_loop_refused_at_registration() -> None:
    template = GraphTemplate(
        qualified_id="dev-factory:self-loop",
        version="1",
        nodes=({"id": "a", "kind": "task"},),
        edges=(_edge("a", "a"),),
    )
    direct = validate_graph_template_topology(template)
    assert is_refusal(direct)
    catalog = GraphTemplateCatalog()
    assert is_refusal(catalog.register(template))
    assert "dev-factory:self-loop" not in catalog


def test_dag_template_keeps_compile_identity_qualified_id_version() -> None:
    """FR-WF-39 — compile identity is (qualified_id, version), not Artifact rail."""
    template = GraphTemplate(
        qualified_id="dev-factory:linear",
        version="3",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "b", "kind": "task"},
        ),
        edges=(_edge("a", "b"),),
    )
    validated = validate_graph_template_topology(template)
    assert is_ok(validated)
    assert validated.value.qualified_id == "dev-factory:linear"
    assert validated.value.version == "3"
    catalog = GraphTemplateCatalog()
    assert is_ok(catalog.register(template))
    stored = catalog.get("dev-factory:linear")
    assert stored is not None
    assert (stored.qualified_id, stored.version) == ("dev-factory:linear", "3")


def test_loop_node_state_is_not_a_template_cycle() -> None:
    """Runtime Loop controls stay on node state; template edges still must be a DAG."""
    # A valid DAG that includes a loop *node* registers; iteration is node state.
    template = GraphTemplate(
        qualified_id="dev-factory:with-loop-node",
        version="1",
        nodes=(
            {"id": "seed", "kind": "task"},
            {
                "id": "retry",
                "kind": "loop",
                "config": {"stopping_condition": "max_iterations", "budget": {"max": 3}},
            },
            {"id": "done", "kind": "task"},
        ),
        edges=(_edge("seed", "retry"), _edge("retry", "done")),
    )
    assert is_ok(validate_graph_template_topology(template))

    # A template that cycles through a loop node is still an illegal template cycle.
    cyclic = GraphTemplate(
        qualified_id="dev-factory:loop-as-cycle",
        version="1",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "loop", "kind": "loop"},
            {"id": "b", "kind": "task"},
        ),
        edges=(_edge("a", "loop"), _edge("loop", "b"), _edge("b", "a")),
    )
    assert is_refusal(validate_graph_template_topology(cyclic))


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
            _edge("check", "approve", from_port="control", to_port="control"),
            _edge("approve", "work", from_port="control", to_port="data"),
            _edge("work", "join", from_port="data", to_port="control"),
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


def _assert_topology_typed_refusal(
    refused: object,
    *,
    illegal_shape: str,
    code: str,
) -> TypedRefusal:
    """Story 56.2 — illegal topology is a typed refusal, never a crash."""
    assert isinstance(refused, TypedRefusal)
    assert refused.context["illegal_shape"] == illegal_shape
    assert refused.context["code"] == code
    shape = refused.context["error_refusal_shape"]
    assert isinstance(shape, Mapping)
    typed_shape = cast(Mapping[str, object], shape)
    assert typed_shape["family"] == TOPOLOGY_REFUSAL_FAMILY
    codes = typed_shape["codes"]
    assert isinstance(codes, tuple)
    assert set(cast("tuple[str, ...]", codes)) == set(TOPOLOGY_REFUSAL_CODES)
    assert code in TOPOLOGY_REFUSAL_CODES
    return refused


def _descriptor_payload(
    *,
    op_id: str,
    input_cardinality: str = "one",
    output_cardinality: str = "one",
    dependencies: list[str] | None = None,
) -> dict[str, object]:
    base = dict(public_operation_descriptors()[0].to_payload())
    base["op_id"] = op_id
    base["input_schema"] = f"{op_id}.v1"
    base["input_cardinality"] = input_cardinality
    base["output_cardinality"] = output_cardinality
    base["declared_operation_dependencies"] = list(dependencies or [])
    return base


def test_cycle_is_typed_invalid_input_refusal_not_crash() -> None:
    """Story 56.2 — cycle → INVALID_INPUT typed refusal, never an exception."""
    template = GraphTemplate(
        qualified_id="dev-factory:typed-cycle",
        version="1",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "b", "kind": "task"},
            {"id": "c", "kind": "task"},
        ),
        edges=(_edge("a", "b"), _edge("b", "c"), _edge("c", "a")),
    )
    refused = validate_graph_template_topology(template)
    assert is_refusal(refused)
    typed = _assert_topology_typed_refusal(
        refused, illegal_shape="cycle", code="INVALID_INPUT"
    )
    assert typed.category is RefusalCategory.INVALID_INPUT
    catalog = GraphTemplateCatalog()
    assert is_refusal(catalog.register(template))
    assert "dev-factory:typed-cycle" not in catalog


def test_missing_dependency_edge_endpoint_is_typed_refusal() -> None:
    """Story 56.2 — missing dependency (undeclared edge endpoint) → typed refusal."""
    template = GraphTemplate(
        qualified_id="dev-factory:missing-edge-dep",
        version="1",
        nodes=({"id": "a", "kind": "task"},),
        edges=(_edge("a", "ghost"),),
    )
    refused = validate_graph_template_topology(template)
    assert is_refusal(refused)
    typed = _assert_topology_typed_refusal(
        refused, illegal_shape="missing_dependency", code="INVALID_INPUT"
    )
    assert typed.category is RefusalCategory.INVALID_INPUT


def test_missing_dependency_depends_on_is_typed_refusal() -> None:
    """Story 56.2 — missing dependency via node depends_on → typed refusal."""
    template = GraphTemplate(
        qualified_id="dev-factory:missing-depends-on",
        version="1",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "b", "kind": "task", "depends_on": ["missing-node"]},
        ),
        edges=(_edge("a", "b"),),
    )
    refused = validate_graph_template_topology(template)
    assert is_refusal(refused)
    typed = _assert_topology_typed_refusal(
        refused, illegal_shape="missing_dependency", code="INVALID_INPUT"
    )
    assert typed.context["missing"] == "missing-node"


def test_missing_operation_dependency_is_typed_unavailable() -> None:
    """Story 56.2 — declared operation dependency absent from the graph."""
    producer = parse_operation_descriptor(
        _descriptor_payload(op_id="test.producer", output_cardinality="one")
    )
    consumer = parse_operation_descriptor(
        _descriptor_payload(
            op_id="test.consumer",
            dependencies=["test.producer"],
        )
    )
    assert is_ok(producer) and is_ok(consumer)
    catalog = {producer.value.op_id: producer.value, consumer.value.op_id: consumer.value}

    # Consumer alone — producer dependency missing from the template.
    template = GraphTemplate(
        qualified_id="dev-factory:missing-op-dep",
        version="1",
        nodes=({"id": "only", "kind": "task", "op_id": "test.consumer"},),
        edges=(),
    )
    refused = validate_graph_template_topology(template, descriptors=catalog)
    assert is_refusal(refused)
    typed = _assert_topology_typed_refusal(
        refused, illegal_shape="missing_dependency", code="UNAVAILABLE"
    )
    assert typed.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert typed.context["missing"] == "test.producer"

    # Satisfied when both ops appear on nodes.
    satisfied = GraphTemplate(
        qualified_id="dev-factory:satisfied-op-dep",
        version="1",
        nodes=(
            {"id": "p", "kind": "task", "op_id": "test.producer"},
            {"id": "c", "kind": "task", "op_id": "test.consumer"},
        ),
        edges=(_edge("p", "c"),),
    )
    assert is_ok(validate_graph_template_topology(satisfied, descriptors=catalog))


def test_unknown_op_id_is_typed_invalid_input_refusal() -> None:
    """Story 56.2 — unknown op_id → INVALID_INPUT typed refusal."""
    template = GraphTemplate(
        qualified_id="dev-factory:unknown-op",
        version="1",
        nodes=({"id": "a", "kind": "task", "op_id": "totally.unknown.op"},),
        edges=(),
    )
    refused = validate_graph_template_topology(template)
    assert is_refusal(refused)
    typed = _assert_topology_typed_refusal(
        refused, illegal_shape="unknown_op_id", code="INVALID_INPUT"
    )
    assert typed.category is RefusalCategory.INVALID_INPUT
    assert typed.context["op_id"] == "totally.unknown.op"
    assert is_refusal(GraphTemplateCatalog().register(template))


def test_cardinality_mismatch_many_to_one_is_typed_refusal() -> None:
    """Story 56.2 — many→one without reducing mapping → INVALID_INPUT."""
    many_out = parse_operation_descriptor(
        _descriptor_payload(op_id="test.many_out", output_cardinality="many")
    )
    one_in = parse_operation_descriptor(
        _descriptor_payload(op_id="test.one_in", input_cardinality="one")
    )
    assert is_ok(many_out) and is_ok(one_in)
    catalog = {
        many_out.value.op_id: many_out.value,
        one_in.value.op_id: one_in.value,
    }
    template = GraphTemplate(
        qualified_id="dev-factory:card-mismatch",
        version="1",
        nodes=(
            {"id": "src", "kind": "task", "op_id": "test.many_out"},
            {"id": "dst", "kind": "task", "op_id": "test.one_in"},
        ),
        # broadcast expands; it is not a reducing many→one mapping.
        edges=(_edge("src", "dst", mapping="broadcast"),),
    )
    refused = validate_graph_template_topology(template, descriptors=catalog)
    assert is_refusal(refused)
    typed = _assert_topology_typed_refusal(
        refused, illegal_shape="cardinality_mismatch", code="INVALID_INPUT"
    )
    assert typed.category is RefusalCategory.INVALID_INPUT
    assert typed.context["output_cardinality"] == "many"
    assert typed.context["input_cardinality"] == "one"

    # Explicit reducing mapping admits the edge.
    fixed = GraphTemplate(
        qualified_id="dev-factory:card-ok",
        version="1",
        nodes=(
            {"id": "src", "kind": "task", "op_id": "test.many_out"},
            {"id": "dst", "kind": "task", "op_id": "test.one_in"},
        ),
        edges=(_edge("src", "dst", mapping="zip"),),
    )
    assert is_ok(validate_graph_template_topology(fixed, descriptors=catalog))


def test_illegal_topology_public_boundary_never_raises() -> None:
    """Story 56.2 — public validate/register return refusals; never raise."""
    shapes: list[GraphTemplate] = [
        GraphTemplate(
            qualified_id="dev-factory:raise-cycle",
            version="1",
            nodes=({"id": "a", "kind": "task"}, {"id": "b", "kind": "task"}),
            edges=(_edge("a", "b"), _edge("b", "a")),
        ),
        GraphTemplate(
            qualified_id="dev-factory:raise-missing",
            version="1",
            nodes=({"id": "a", "kind": "task"},),
            edges=(_edge("a", "nope"),),
        ),
        GraphTemplate(
            qualified_id="dev-factory:raise-unknown-op",
            version="1",
            nodes=({"id": "a", "kind": "task", "op_id": "no.such.op"},),
        ),
    ]
    catalog = GraphTemplateCatalog()
    for template in shapes:
        direct = validate_graph_template_topology(template)
        assert is_refusal(direct)
        assert isinstance(direct, TypedRefusal)
        assert "code" in direct.context
        assert direct.context["code"] in TOPOLOGY_REFUSAL_CODES
        registered = catalog.register(template)
        assert is_refusal(registered)
        assert isinstance(registered, TypedRefusal)


def test_edge_mapping_required_no_silent_cartesian() -> None:
    """Story 56.3 / FR-WF-42 — mapping must be declared; silent Cartesian refuses."""
    missing = GraphTemplate(
        qualified_id="dev-factory:missing-mapping",
        version="1",
        nodes=({"id": "a", "kind": "task"}, {"id": "b", "kind": "task"}),
        edges=({"from": "a", "to": "b", "from_port": "data", "to_port": "data"},),
    )
    refused = validate_graph_template_topology(missing)
    assert is_refusal(refused)
    typed = _assert_topology_typed_refusal(
        refused, illegal_shape="silent_cartesian", code="INVALID_INPUT"
    )
    assert typed.category is RefusalCategory.INVALID_INPUT

    silent = GraphTemplate(
        qualified_id="dev-factory:silent-cartesian",
        version="1",
        nodes=({"id": "a", "kind": "task"}, {"id": "b", "kind": "task"}),
        edges=(
            {
                "from": "a",
                "to": "b",
                "mapping": "cartesian",
                "from_port": "data",
                "to_port": "data",
            },
        ),
    )
    refused_cartesian = validate_graph_template_topology(silent)
    assert is_refusal(refused_cartesian)
    _assert_topology_typed_refusal(
        refused_cartesian, illegal_shape="silent_cartesian", code="INVALID_INPUT"
    )

    explicit = GraphTemplate(
        qualified_id="dev-factory:explicit-cartesian",
        version="1",
        nodes=({"id": "a", "kind": "task"}, {"id": "b", "kind": "task"}),
        edges=(_edge("a", "b", mapping="cartesian", cartesian=True),),
    )
    assert is_ok(validate_graph_template_topology(explicit))


def test_edge_ports_declare_closed_kinds() -> None:
    """Story 56.3 — each port declares reference|data|event|control."""
    missing_ports = GraphTemplate(
        qualified_id="dev-factory:missing-ports",
        version="1",
        nodes=({"id": "a", "kind": "task"}, {"id": "b", "kind": "task"}),
        edges=({"from": "a", "to": "b", "mapping": "one"},),
    )
    refused = validate_graph_template_topology(missing_ports)
    assert is_refusal(refused)
    _assert_topology_typed_refusal(
        refused, illegal_shape="missing_port_kind", code="INVALID_INPUT"
    )

    bad_kind = GraphTemplate(
        qualified_id="dev-factory:bad-port-kind",
        version="1",
        nodes=({"id": "a", "kind": "task"}, {"id": "b", "kind": "task"}),
        edges=(_edge("a", "b", from_port="payload", to_port="data"),),
    )
    refused_kind = validate_graph_template_topology(bad_kind)
    assert is_refusal(refused_kind)
    _assert_topology_typed_refusal(
        refused_kind, illegal_shape="unknown_port_kind", code="INVALID_INPUT"
    )


def test_conditional_skip_is_node_kind_not_dropped_edges() -> None:
    """Story 56.3 — refuse drop_on_empty / conditional_skip edge keys."""
    template = GraphTemplate(
        qualified_id="dev-factory:drop-edge-skip",
        version="1",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "b", "kind": "task"},
            {"id": "gate", "kind": "conditional"},
        ),
        edges=(
            _edge("a", "gate", from_port="data", to_port="control", drop_on_empty=True),
            _edge("gate", "b", from_port="control", to_port="data"),
        ),
    )
    refused = validate_graph_template_topology(template)
    assert is_refusal(refused)
    typed = _assert_topology_typed_refusal(
        refused, illegal_shape="dropped_edge_skip", code="INVALID_INPUT"
    )
    forbidden = typed.context["forbidden_keys"]
    assert isinstance(forbidden, tuple)
    assert "drop_on_empty" in cast("tuple[str, ...]", forbidden)

    # Conditional as a node kind with declared mapping/ports is legal.
    legal = GraphTemplate(
        qualified_id="dev-factory:conditional-node",
        version="1",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "gate", "kind": "conditional"},
            {"id": "b", "kind": "task"},
        ),
        edges=(
            _edge("a", "gate", from_port="data", to_port="control"),
            _edge("gate", "b", from_port="control", to_port="data"),
        ),
    )
    assert is_ok(validate_graph_template_topology(legal))


def test_illegal_graph_register_keeps_previous_roster_no_occupancy() -> None:
    """Story 56.3 — refused register leaves prior roster; consumes no occupancy."""
    catalog = GraphTemplateCatalog()
    good = GraphTemplate(
        qualified_id="dev-factory:good-linear",
        version="1",
        nodes=({"id": "a", "kind": "task"}, {"id": "b", "kind": "task"}),
        edges=(_edge("a", "b"),),
    )
    assert is_ok(catalog.register(good))
    before = catalog.ids()

    illegal = GraphTemplate(
        qualified_id="dev-factory:illegal-cycle",
        version="1",
        nodes=(
            {"id": "a", "kind": "task"},
            {"id": "b", "kind": "task"},
            {"id": "c", "kind": "task"},
        ),
        edges=(_edge("a", "b"), _edge("b", "c"), _edge("c", "a")),
    )
    refused = catalog.register(illegal)
    assert is_refusal(refused)
    assert isinstance(refused, TypedRefusal)
    assert catalog.ids() == before
    assert "dev-factory:illegal-cycle" not in catalog
    # Topology registration is not a door run — no occupancy field is minted.
    assert "occupancy" not in refused.context
