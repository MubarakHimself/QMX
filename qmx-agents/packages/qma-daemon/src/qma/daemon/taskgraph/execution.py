"""Graph Template / Loop / Skill execution model (AD-13; FR-Q29).

Graph Templates stay authored and stateless. Loop runtime controls
(``stopping_condition``, ``budget``, ``escalation``, iteration) live on Task
Graph *node* state. Skill definitions stay in ``qma-core`` and never become
Loops. ``qma-daemon`` contributes no ``graph_template`` in v1. Mission Template
registry and graph-engine selection remain Deferred (GAP-0084 / GAP-0086).
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
from qma.core.vocabulary.enums import (
    GraphArtifactKind,
    NodeKind,
    TaskMissionState,
)
from qma.daemon.taskgraph.records import (
    GraphTemplate,
    TaskGraph,
    TaskGraphNode,
    TaskLedger,
    TaskRecord,
)
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DAEMON_CONTRIBUTED_GRAPH_TEMPLATES",
    "DEFERRED_GRAPH_EXCLUSIONS",
    "MISSION_TEMPLATE_REGISTRY",
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
) -> Result[GraphTemplate]:
    """Reject back-edges at registration; keep Graph Template ≠ Task Graph."""
    owned = validate_no_daemon_graph_template(template.qualified_id)
    if not is_ok(owned):
        return owned

    if template.artifact_kind is not GraphArtifactKind.GRAPH_TEMPLATE:
        return invalid_input(
            "artifact_kind",
            "Graph Template artifact_kind must be graph_template, never task_graph",
            given=template.artifact_kind.value,
        )

    node_ids = {str(n.get("id")) for n in template.nodes if isinstance(n.get("id"), str)}
    forward: set[tuple[str, str]] = set()
    for edge in template.edges:
        src = edge.get("from")
        dst = edge.get("to")
        if not isinstance(src, str) or not isinstance(dst, str):
            return invalid_input("edge", "graph template edges require from/to strings")
        if src not in node_ids or dst not in node_ids:
            return invalid_input(
                "edge",
                "graph template edge endpoints must name declared nodes",
                given=f"{src}->{dst}",
            )
        if (dst, src) in forward:
            return policy_rejection(
                "graph_template",
                "back-edges are rejected at Graph Template registration (AD-13; FR-Q29)",
                from_node=src,
                to_node=dst,
            )
        forward.add((src, dst))
    return Ok(template)


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
