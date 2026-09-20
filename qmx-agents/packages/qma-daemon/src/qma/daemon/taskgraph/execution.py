"""Graph Template / Loop / Skill execution model (AD-13; FR-Q29).

Graph Templates stay authored and stateless. Loop runtime controls
(``stopping_condition``, ``budget``, ``escalation``, iteration) live on Task
Graph *node* state. Skill definitions stay in ``qma-core`` and never become
Loops. ``qma-daemon`` contributes no ``graph_template`` in v1. Mission Template
registry and graph-engine selection remain Deferred (GAP-0084 / GAP-0086).

Illegal topology shapes (cycle, missing dependency, unknown ``op_id``,
cardinality mismatch) return CT-04 typed refusals with the same closed
``error_refusal_shape`` codes as other public calls — never an untyped
exception at the public boundary (Story 56.2; AD-6; FR-WF-40).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qma.core.control import (
    DEFERRED_GRAPH_EXCLUSIONS,
    ControlPrimitive,
    Skill,
    emits_task,
    holds_dispatch_lease,
    node_carries_ledger,
)
from qma.core.ontology import ActorId
from qma.core.operations import public_operation_descriptors
from qma.core.operations.descriptor import (
    ERROR_REFUSAL_FAMILY,
    REQUIRED_REFUSAL_CODES,
    OperationDescriptor,
)
from qma.core.vocabulary.enums import (
    GraphArtifactKind,
    NodeKind,
    OperationCardinality,
    TaskMissionState,
)
from qma.daemon.taskgraph.records import (
    GraphTemplate,
    TaskGraph,
    TaskGraphNode,
    TaskLedger,
    TaskRecord,
)
from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DAEMON_CONTRIBUTED_GRAPH_TEMPLATES",
    "DEFERRED_GRAPH_EXCLUSIONS",
    "MISSION_TEMPLATE_REGISTRY",
    "REDUCING_EDGE_MAPPINGS",
    "TOPOLOGY_REFUSAL_CODES",
    "TOPOLOGY_REFUSAL_FAMILY",
    "ControlPrimitive",
    "LoopNodeState",
    "Skill",
    "assert_template_not_interchanged",
    "deterministic_task_id",
    "emits_task",
    "holds_dispatch_lease",
    "loop_state_from_node_config",
    "mint_loop_iteration_task",
    "node_carries_ledger",
    "validate_graph_template_topology",
    "validate_no_daemon_graph_template",
]


# qma-daemon ships no graph_template in v1 (AD-13; DEC-0312).
DAEMON_CONTRIBUTED_GRAPH_TEMPLATES: Final[tuple[GraphTemplate, ...]] = ()

# Mission Template registry is Deferred (GAP-0084) — deliberately absent.
MISSION_TEMPLATE_REGISTRY: Final[None] = None

# Same closed codes as OperationDescriptor.error_refusal_shape (AD-3; FR-WF-16).
TOPOLOGY_REFUSAL_FAMILY: Final[str] = ERROR_REFUSAL_FAMILY
TOPOLOGY_REFUSAL_CODES: Final[frozenset[str]] = REQUIRED_REFUSAL_CODES

# Edge mappings that may legally reduce many→one (AD-5; Story 56.3 declares the set).
REDUCING_EDGE_MAPPINGS: Final[frozenset[str]] = frozenset(
    {"one", "zip", "keyed-join", "cartesian"}
)
_EXPANDING_EDGE_MAPPINGS: Final[frozenset[str]] = frozenset({"broadcast", "cartesian"})


def _topology_refusal(
    field: str,
    reason: str,
    *,
    code: str,
    category: RefusalCategory = RefusalCategory.INVALID_INPUT,
    **extra: object,
) -> TypedRefusal:
    """Typed refusal carrying a closed error_refusal_shape code (Story 56.2)."""
    resolved_code = code if code in TOPOLOGY_REFUSAL_CODES else "INVALID_INPUT"
    context: dict[str, object] = {
        "field": field,
        "reason": reason,
        "code": resolved_code,
        "error_refusal_shape": {
            "family": TOPOLOGY_REFUSAL_FAMILY,
            "codes": sorted(TOPOLOGY_REFUSAL_CODES),
        },
    }
    context.update(extra)
    return TypedRefusal(
        category=category,
        retryability=Retryability.NO,
        context=context,
    )


def _index_descriptors(
    descriptors: Mapping[str, OperationDescriptor]
    | Sequence[OperationDescriptor]
    | None,
    *,
    default_public: bool,
) -> dict[str, OperationDescriptor]:
    if descriptors is None:
        if not default_public:
            return {}
        return {item.op_id: item for item in public_operation_descriptors()}
    if isinstance(descriptors, Mapping):
        return dict(descriptors)
    indexed: dict[str, OperationDescriptor] = {}
    for item in descriptors:
        indexed[item.op_id] = item
    return indexed


@dataclass(frozen=True, slots=True)
class LoopNodeState:
    """Runtime-owned Loop controls on a Task Graph node (AD-13).

    ``stopping_condition``, ``budget``, ``escalation`` and ``iteration`` are
    node state and never Task fields. A loop emits exactly one Task per
    iteration at mint time.
    """

    node_id: str
    stopping_condition: str
    budget: Mapping[str, object] = field(default_factory=dict[str, object])
    escalation: str = "quant_mailbox"
    iteration: int = 0
    stopped: bool = False
    last_evaluation: str | None = None

    def __post_init__(self) -> None:
        if not self.node_id:
            msg = "LoopNodeState.node_id is required"
            raise ValueError(msg)
        if self.iteration < 0:
            msg = "LoopNodeState.iteration must be >= 0"
            raise ValueError(msg)
        object.__setattr__(self, "budget", MappingProxyType(dict(self.budget)))

    @property
    def control_primitive(self) -> ControlPrimitive:
        return ControlPrimitive.LOOP

    def with_iteration(
        self,
        iteration: int,
        *,
        last_evaluation: str | None = None,
    ) -> LoopNodeState:
        evaluation = last_evaluation if last_evaluation is not None else self.last_evaluation
        return LoopNodeState(
            node_id=self.node_id,
            stopping_condition=self.stopping_condition,
            budget=dict(self.budget),
            escalation=self.escalation,
            iteration=iteration,
            stopped=self.stopped,
            last_evaluation=evaluation,
        )

    def mark_stopped(self, *, reason: str) -> LoopNodeState:
        return LoopNodeState(
            node_id=self.node_id,
            stopping_condition=self.stopping_condition,
            budget=dict(self.budget),
            escalation=self.escalation,
            iteration=self.iteration,
            stopped=True,
            last_evaluation=reason,
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "node_id": self.node_id,
                "stopping_condition": self.stopping_condition,
                "budget": dict(self.budget),
                "escalation": self.escalation,
                "iteration": self.iteration,
                "stopped": self.stopped,
                "last_evaluation": self.last_evaluation,
                "control_primitive": ControlPrimitive.LOOP.value,
                # Explicit: these controls are node state, never Task fields.
                "runtime_owned": True,
            }
        )


def deterministic_task_id(
    task_graph_id: str,
    node_id: str,
    *,
    iteration: int = 0,
    retry_index: int = 0,
) -> str:
    """Task id from task-graph id, node id, iteration, retry_index (AD-13)."""
    return f"task:{task_graph_id}:{node_id}:{iteration}:{retry_index}"


def validate_no_daemon_graph_template(qualified_id: str) -> Result[str]:
    """Refuse any template that claims the daemon as its contributing plugin."""
    plugin_id, _, _local = qualified_id.partition(":")
    if plugin_id in {"qma-daemon", "daemon", "qma"}:
        return policy_rejection(
            "graph_template",
            "qma-daemon contributes no graph_template in v1; every named cycle "
            "arrives as a plugin-contributed Graph Template (AD-13; FR-Q29)",
            given=qualified_id,
        )
    if any(t.qualified_id == qualified_id for t in DAEMON_CONTRIBUTED_GRAPH_TEMPLATES):
        return policy_rejection(
            "graph_template",
            "qma-daemon contributes no graph_template in v1",
            given=qualified_id,
        )
    return Ok(qualified_id)


def validate_graph_template_topology(
    template: GraphTemplate,
    *,
    descriptors: Mapping[str, OperationDescriptor]
    | Sequence[OperationDescriptor]
    | None = None,
) -> Result[GraphTemplate]:
    """Refuse illegal topology shapes as typed CT-04 refusals (AD-6; Story 56.2).

    Public boundary returns value-or-refusal — never an untyped exception.
    Illegal shapes covered:

    * **cycle** / self-loop — ``INVALID_INPUT``
    * **missing dependency** — edge endpoint or ``depends_on`` / declared
      operation dependency absent — ``INVALID_INPUT`` / ``UNAVAILABLE``
    * **unknown op_id** — node cites an op not in the descriptor catalog —
      ``INVALID_INPUT``
    * **cardinality mismatch** — predecessor ``output_cardinality`` cannot
      feed successor ``input_cardinality`` under the edge mapping —
      ``INVALID_INPUT``

    Pairwise reverse-edge checks are insufficient — ``A→B→C→A`` must refuse.
    Runtime Loops remain node state and never excuse a template cycle.
    """
    owned = validate_no_daemon_graph_template(template.qualified_id)
    if not is_ok(owned):
        return owned

    if template.artifact_kind is not GraphArtifactKind.GRAPH_TEMPLATE:
        return _topology_refusal(
            "artifact_kind",
            "Graph Template artifact_kind must be graph_template, never task_graph",
            code="INVALID_INPUT",
            given=template.artifact_kind.value,
        )

    node_ids: set[str] = set()
    node_by_id: dict[str, Mapping[str, object]] = {}
    cites_op = any(node.get("op_id") is not None for node in template.nodes)
    catalog = _index_descriptors(descriptors, default_public=cites_op)

    for node in template.nodes:
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            return _topology_refusal(
                "node.id",
                "graph template nodes require a non-empty string id",
                code="INVALID_INPUT",
            )
        if node_id in node_ids:
            return _topology_refusal(
                "node.id",
                "duplicate node id in Graph Template",
                code="INVALID_INPUT",
                given=node_id,
            )
        node_ids.add(node_id)
        node_by_id[node_id] = node

    op_by_node: dict[str, str] = {}
    for node_id, node in node_by_id.items():
        op_raw = node.get("op_id")
        if op_raw is None:
            continue
        if not isinstance(op_raw, str) or not op_raw:
            return _topology_refusal(
                "node.op_id",
                "node op_id must be a non-empty string when present",
                code="INVALID_INPUT",
                node_id=node_id,
            )
        if op_raw not in catalog:
            return _topology_refusal(
                "node.op_id",
                "unknown op_id — not present in the operation descriptor catalog",
                code="INVALID_INPUT",
                illegal_shape="unknown_op_id",
                node_id=node_id,
                op_id=op_raw,
            )
        op_by_node[node_id] = op_raw

    # Missing operation dependencies (declared on the descriptor, or node-local).
    for node_id, op_id in op_by_node.items():
        descriptor = catalog.get(op_id)
        if descriptor is None:
            continue
        graph_ops = set(op_by_node.values())
        for dep in descriptor.declared_operation_dependencies:
            if dep not in graph_ops:
                return _topology_refusal(
                    "declared_operation_dependencies",
                    "missing operation dependency — required op_id is not "
                    "present on any node in this Graph Template",
                    code="UNAVAILABLE",
                    category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                    illegal_shape="missing_dependency",
                    node_id=node_id,
                    op_id=op_id,
                    missing=dep,
                )

    for node_id, node in node_by_id.items():
        depends_raw = node.get("depends_on")
        if depends_raw is None:
            continue
        if isinstance(depends_raw, str):
            deps: tuple[object, ...] = (depends_raw,)
        elif isinstance(depends_raw, Sequence) and not isinstance(depends_raw, (str, bytes)):
            deps = tuple(cast("Sequence[object]", depends_raw))
        else:
            return _topology_refusal(
                "node.depends_on",
                "depends_on must be a string or sequence of node ids",
                code="INVALID_INPUT",
                node_id=node_id,
            )
        for dep in deps:
            if not isinstance(dep, str) or not dep:
                return _topology_refusal(
                    "node.depends_on",
                    "depends_on entries must be non-empty strings",
                    code="INVALID_INPUT",
                    node_id=node_id,
                )
            if dep not in node_ids:
                return _topology_refusal(
                    "node.depends_on",
                    "missing dependency — depends_on names an undeclared node",
                    code="INVALID_INPUT",
                    illegal_shape="missing_dependency",
                    node_id=node_id,
                    missing=dep,
                )

    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in template.edges:
        src = edge.get("from")
        dst = edge.get("to")
        if not isinstance(src, str) or not isinstance(dst, str):
            return _topology_refusal(
                "edge",
                "graph template edges require from/to strings",
                code="INVALID_INPUT",
            )
        if src not in node_ids or dst not in node_ids:
            return _topology_refusal(
                "edge",
                "missing dependency — edge endpoints must name declared nodes",
                code="INVALID_INPUT",
                illegal_shape="missing_dependency",
                given=f"{src}->{dst}",
            )
        if src == dst:
            return _topology_refusal(
                "graph_template",
                "self-loops are refused at Graph Template registration "
                "(AD-6; FR-WF-40)",
                code="INVALID_INPUT",
                illegal_shape="cycle",
                from_node=src,
                to_node=dst,
            )

        mapping_raw = edge.get("mapping")
        mapping = mapping_raw if isinstance(mapping_raw, str) else None
        src_op = op_by_node.get(src)
        dst_op = op_by_node.get(dst)
        if src_op is not None and dst_op is not None and catalog:
            src_desc = catalog.get(src_op)
            dst_desc = catalog.get(dst_op)
            if src_desc is not None and dst_desc is not None:
                refused = _refuse_cardinality_mismatch(
                    src_desc,
                    dst_desc,
                    mapping=mapping,
                    from_node=src,
                    to_node=dst,
                )
                if refused is not None:
                    return refused

        adjacency[src].append(dst)

    # DFS cycle detection — same temporary/permanent marks as
    # topological_plugin_order (AD-6: pairwise reverse-edge is insufficient).
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node_id: str) -> TypedRefusal | None:
        if node_id in permanent:
            return None
        if node_id in temporary:
            return _topology_refusal(
                "graph_template",
                "directed cycles are refused at Graph Template registration "
                "(AD-6; FR-WF-40); pairwise reverse-edge checks are insufficient",
                code="INVALID_INPUT",
                illegal_shape="cycle",
                node_id=node_id,
            )
        temporary.add(node_id)
        for successor in adjacency[node_id]:
            refused = visit(successor)
            if refused is not None:
                return refused
        temporary.remove(node_id)
        permanent.add(node_id)
        return None

    for node_id in node_ids:
        cycle = visit(node_id)
        if cycle is not None:
            return cycle
    return Ok(template)


def _refuse_cardinality_mismatch(
    src: OperationDescriptor,
    dst: OperationDescriptor,
    *,
    mapping: str | None,
    from_node: str,
    to_node: str,
) -> TypedRefusal | None:
    """Refuse many→one without a reducing mapping, or one→many without expand."""
    out_c = src.output_cardinality
    in_c = dst.input_cardinality
    if (
        out_c is OperationCardinality.MANY
        and in_c is OperationCardinality.ONE
        and (mapping is None or mapping not in REDUCING_EDGE_MAPPINGS)
    ):
        return _topology_refusal(
            "edge.mapping",
            "cardinality mismatch — many output cannot feed one input "
            "without an explicit reducing mapping "
            "(one|zip|keyed-join|cartesian)",
            code="INVALID_INPUT",
            illegal_shape="cardinality_mismatch",
            from_node=from_node,
            to_node=to_node,
            output_cardinality=out_c.value,
            input_cardinality=in_c.value,
            mapping=mapping,
        )
    if (
        out_c is OperationCardinality.ONE
        and in_c is OperationCardinality.MANY
        and (mapping is None or mapping not in _EXPANDING_EDGE_MAPPINGS)
    ):
        return _topology_refusal(
            "edge.mapping",
            "cardinality mismatch — one output cannot feed many input "
            "without an explicit expanding mapping (broadcast|cartesian)",
            code="INVALID_INPUT",
            illegal_shape="cardinality_mismatch",
            from_node=from_node,
            to_node=to_node,
            output_cardinality=out_c.value,
            input_cardinality=in_c.value,
            mapping=mapping,
        )
    return None


def assert_template_not_interchanged(
    template: GraphTemplate,
    task_graph: TaskGraph,
) -> Result[None]:
    """A run never swaps a Graph Template for the persisted Task Graph."""
    if template.artifact_kind is GraphArtifactKind.TASK_GRAPH:
        return policy_rejection(
            "graph_template",
            "Graph Template must not be interchanged with Task Graph (AD-13)",
        )
    if task_graph.artifact_kind is GraphArtifactKind.GRAPH_TEMPLATE:
        return policy_rejection(
            "task_graph",
            "Task Graph must not be interchanged with Graph Template (AD-13)",
        )
    if task_graph.graph_template_ref not in {None, template.qualified_id}:
        return policy_rejection(
            "task_graph",
            "Task Graph graph_template_ref must cite the authored template id "
            "or be absent; a run never mutates or replaces the template",
            template=template.qualified_id,
            graph_ref=task_graph.graph_template_ref,
        )
    return Ok(None)


def mint_loop_iteration_task(
    *,
    graph: TaskGraph,
    node: TaskGraphNode,
    loop_state: LoopNodeState,
    owner: ActorId,
    intent: str | None = None,
    inputs: Mapping[str, object] | None = None,
    refs: Sequence[str] = (),
    acceptance_criteria: Sequence[str] = (),
    retry_index: int = 0,
) -> Result[tuple[TaskRecord, LoopNodeState]]:
    """Emit exactly one Task for the next Loop iteration (AD-13).

    Iteration count / stopping_condition / budget / escalation remain on
    ``LoopNodeState`` (node state). The minted Task id embeds graph id, node
    id, iteration and ``retry_index`` but does not own those controls.
    """
    if node.kind is not NodeKind.LOOP:
        return invalid_input(
            "node.kind",
            "only a loop node may mint a loop-iteration Task",
            given=node.kind.value,
        )
    if node.id != loop_state.node_id:
        return invalid_input(
            "node_id",
            "LoopNodeState.node_id must match the Task Graph node id",
            given=loop_state.node_id,
        )
    if loop_state.stopped:
        return policy_rejection(
            "loop",
            "stopped loop emits no further Tasks",
            node_id=node.id,
            last_evaluation=loop_state.last_evaluation or "",
        )
    if not emits_task(node.kind):
        return policy_rejection(
            "node.kind",
            "daemon-evaluated node kinds emit no Tasks",
            given=node.kind.value,
        )

    iteration = loop_state.iteration
    task_id = deterministic_task_id(
        graph.id,
        node.id,
        iteration=iteration,
        retry_index=retry_index,
    )
    # Refuse a duplicate mint for the same iteration/retry.
    if graph.task_by_id(task_id) is not None:
        return policy_rejection(
            "loop",
            "a loop node emits exactly one Task per iteration; duplicate mint "
            "refused (AD-13; FR-Q29)",
            task_id=task_id,
            iteration=iteration,
        )

    work_intent = intent if intent is not None else f"loop:{node.id}:iter:{iteration}"
    input_payload: dict[str, object] = dict(inputs or {})
    # Node-state controls stay off the Task body; only a provenance pointer.
    input_payload.setdefault("loop_node_id", node.id)

    task = TaskRecord(
        id=task_id,
        mission_id=graph.mission_id,
        owner=owner,
        intent=work_intent,
        inputs=input_payload,
        refs=tuple(refs),
        acceptance_criteria=tuple(acceptance_criteria),
        state=TaskMissionState.READY,
        node_id=node.id,
        node_kind=NodeKind.LOOP,
        iteration=iteration,
        retry_index=retry_index,
        ledger=TaskLedger(task_id=task_id),
    )
    # Advance node-owned iteration after a successful mint.
    advanced = loop_state.with_iteration(
        iteration + 1,
        last_evaluation=f"minted:{task_id}",
    )
    return Ok((task, advanced))


def loop_state_from_node_config(node: TaskGraphNode) -> Result[LoopNodeState]:
    """Materialize runtime Loop controls from authored node config defaults."""
    if node.kind is not NodeKind.LOOP:
        return invalid_input(
            "node.kind",
            "LoopNodeState requires a loop node",
            given=node.kind.value,
        )
    config = node.config
    stopping = config.get("stopping_condition", "max_iterations")
    if not isinstance(stopping, str) or not stopping:
        return invalid_input(
            "stopping_condition",
            "loop stopping_condition must be a non-empty string",
        )
    budget_raw = config.get("budget", {})
    budget: dict[str, object]
    if isinstance(budget_raw, Mapping):
        budget = dict(cast("Mapping[str, object]", budget_raw))
    else:
        return invalid_input("budget", "loop budget must be a mapping")
    escalation_raw = config.get("escalation", "quant_mailbox")
    escalation = escalation_raw if isinstance(escalation_raw, str) else "quant_mailbox"
    return Ok(
        LoopNodeState(
            node_id=node.id,
            stopping_condition=stopping,
            budget=budget,
            escalation=escalation,
            iteration=0,
        )
    )
