"""Deterministic Mission Compiler (AD-12; FR-Q27).

Turns a Goal plus an optional Graph Template into exactly one Mission record and
its initial Task Graph. Never an LLM. Empty ExecutionEnvironment registries do
not block compilation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Final, cast

from qma.core.ontology import ActorId, Goal, Quant
from qma.core.vocabulary.enums import (
    TASK_EMITTING_NODE_KINDS,
    NodeKind,
    TaskMissionState,
)
from qma.daemon.taskgraph.execution import validate_graph_template_topology
from qma.daemon.taskgraph.records import (
    MISSION_DIRECTOR_ROLE,
    RESERVED_APPROVAL_ROUTE_OPERATOR,
    GraphTemplate,
    MissionRecord,
    TaskGraph,
    TaskGraphNode,
    TaskLedger,
    TaskRecord,
    as_string_tuple,
)
from qmf.core import Ok, Result, is_ok
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CompileRequest",
    "CompileResult",
    "GraphTemplateCatalog",
    "MissionCompiler",
    "validate_approval_route",
]


_DECOMPOSITION_NODE_ID: Final[str] = "decomposition"


@dataclass(frozen=True, slots=True)
class CompileRequest:
    """Inputs to the deterministic Mission Compiler."""

    goal: Goal
    owner: Quant
    graph_template_ref: str | None = None
    intent: str | None = None
    scope: str = "mission"
    constraints: Sequence[str] = ()
    evidence_requirements: Sequence[str] = ()
    capabilities: Sequence[str] = ()
    success_criteria: Sequence[str] = ()
    outputs: Sequence[str] = ()
    verification: str = "deterministic_verifier"
    budget: Mapping[str, object] | None = None
    escalation: str = "quant_mailbox"
    termination_criteria: Sequence[str] = ()
    approval_route: str | None = None
    require_decomposition_reasoning: bool | None = None


@dataclass(frozen=True, slots=True)
class CompileResult:
    """Exactly one Mission and its initial Task Graph."""

    mission: MissionRecord
    task_graph: TaskGraph

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "mission": dict(self.mission.to_payload()),
                "task_graph": dict(self.task_graph.to_payload()),
            }
        )


class GraphTemplateCatalog:
    """In-memory definition-store stand-in for plugin-contributed templates.

    Registration validates topology (back-edges refused) and refuses any
    daemon-claimed template id. Stored templates are the authored, versioned,
    stateless artifacts — a run never mutates or interchanges them with a
    Task Graph (AD-13; FR-Q29).
    """

    def __init__(self) -> None:
        self._templates: dict[str, GraphTemplate] = {}

    def register(self, template: GraphTemplate) -> Result[str]:
        if template.qualified_id in self._templates:
            return invalid_input(
                "graph_template_ref",
                "duplicate graph_template registration refused",
                given=template.qualified_id,
            )
        validated = validate_graph_template_topology(template)
        if not is_ok(validated):
            return validated
        # Store the validated authored template; never a Task Graph projection.
        self._templates[template.qualified_id] = validated.value
        return Ok(template.qualified_id)

    def get(self, qualified_id: str) -> GraphTemplate | None:
        return self._templates.get(qualified_id)

    def __contains__(self, qualified_id: object) -> bool:
        return isinstance(qualified_id, str) and qualified_id in self._templates

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._templates))


def validate_approval_route(
    route: str | None,
    *,
    known_quant_actor_ids: frozenset[str] | set[str],
) -> Result[str | None]:
    """Accept reserved ``operator`` or an existing Quant ``ActorId`` only.

    A route naming a non-existent Quant is refused at compile time (FR-Q27).
    """
    if route is None:
        return Ok(None)
    if not route:
        return invalid_input(
            "approval_route",
            "approval_route must be the reserved operator value or an ActorId",
            given=repr(route),
        )
    if route == RESERVED_APPROVAL_ROUTE_OPERATOR:
        return Ok(route)
    parsed = ActorId.try_create(route)
    if not is_ok(parsed):
        return invalid_input(
            "approval_route",
            "approval_route must be the reserved operator value or a valid ActorId",
            given=route,
        )
    actor = parsed.value.value
    if actor not in known_quant_actor_ids:
        return policy_rejection(
            "approval_route",
            "approval_route naming a non-existent Quant is refused at Mission "
            "compile time (FR-Q27; AD-12)",
            route=actor,
        )
    return Ok(actor)


def _stable_token(*parts: str) -> str:
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _task_id(
    task_graph_id: str,
    node_id: str,
    *,
    iteration: int = 0,
    retry_index: int = 0,
) -> str:
    """Deterministic Task id from task-graph id, node id, iteration, retry_index."""
    return f"task:{task_graph_id}:{node_id}:{iteration}:{retry_index}"


def _parse_node_kind(raw: object) -> Result[NodeKind]:
    if isinstance(raw, NodeKind):
        return Ok(raw)
    if not isinstance(raw, str):
        return invalid_input("node.kind", "node kind must be a string", given=repr(raw))
    try:
        return Ok(NodeKind(raw))
    except ValueError:
        return invalid_input(
            "node.kind",
            "node kind must be one of the ten closed AD-13 values",
            given=raw,
        )


class MissionCompiler:
    """Deterministic daemon code — never an LLM (AD-12; FR-Q27)."""

    def __init__(
        self,
        *,
        templates: GraphTemplateCatalog | None = None,
        known_quant_actor_ids: frozenset[str] | set[str] | None = None,
    ) -> None:
        self._templates = templates if templates is not None else GraphTemplateCatalog()
        self._known_quants: set[str] = set(known_quant_actor_ids or ())

    @property
    def templates(self) -> GraphTemplateCatalog:
        return self._templates

    def remember_quant(self, actor_id: ActorId | str) -> None:
        token = actor_id.value if isinstance(actor_id, ActorId) else actor_id
        self._known_quants.add(token)

    def compile(self, request: CompileRequest) -> Result[CompileResult]:
        """Compile a Goal into exactly one Mission and its initial Task Graph."""
        owner = request.owner
        if owner.retired:
            return policy_rejection(
                "owner",
                "a retired Quant may not own a new Mission",
                owner=owner.actor_id.value,
            )
        self.remember_quant(owner.actor_id)

        route = validate_approval_route(
            request.approval_route,
            known_quant_actor_ids=self._known_quants,
        )
        if not is_ok(route):
            return route

        template: GraphTemplate | None = None
        if request.graph_template_ref is not None:
            template = self._templates.get(request.graph_template_ref)
            if template is None:
                return invalid_input(
                    "graph_template_ref",
                    "graph_template_ref must name a registered Graph Template "
                    "(AD-13); qma-daemon ships none of its own",
                    given=request.graph_template_ref,
                )

        needs_decomposition = request.require_decomposition_reasoning
        if needs_decomposition is None:
            needs_decomposition = template is None

        intent = request.intent if request.intent is not None else request.goal.text
        mission_token = _stable_token(owner.actor_id.value, request.goal.text, intent)
        mission_id = f"mission:{mission_token}"
        task_graph_id = f"taskgraph:{mission_token}"

        mission = MissionRecord(
            id=mission_id,
            owner=owner.actor_id,
            goal=request.goal,
            intent=intent,
            scope=request.scope,
            constraints=as_string_tuple(request.constraints),
            evidence_requirements=as_string_tuple(request.evidence_requirements),
            capabilities=as_string_tuple(request.capabilities),
            success_criteria=as_string_tuple(request.success_criteria),
            outputs=as_string_tuple(request.outputs),
            verification=request.verification,
            budget=dict(request.budget or {"units": "declared-per-mission"}),
            escalation=request.escalation,
            termination_criteria=as_string_tuple(request.termination_criteria),
            approval_route=route.value,
            state=TaskMissionState.PENDING,
            graph_template_ref=request.graph_template_ref,
            task_graph_id=task_graph_id,
        )

        # Desk is derived, never stored — verify derivation works at compile time.
        _ = mission.desk_for(owner)

        if needs_decomposition:
            graph = self._decomposition_graph(
                mission_id=mission_id,
                task_graph_id=task_graph_id,
                owner=owner.actor_id,
                intent=intent,
                goal_text=request.goal.text,
            )
        else:
            if template is None:
                return invalid_input(
                    "graph_template_ref",
                    "Graph Template expansion requires a resolved template",
                )
            built = self._expand_template(
                template=template,
                mission_id=mission_id,
                task_graph_id=task_graph_id,
                owner=owner.actor_id,
            )
            if not is_ok(built):
                return built
            graph = built.value

        return Ok(CompileResult(mission=mission, task_graph=graph))

    def _decomposition_graph(
        self,
        *,
        mission_id: str,
        task_graph_id: str,
        owner: ActorId,
        intent: str,
        goal_text: str,
    ) -> TaskGraph:
        """Emit a decomposition Task whose Agent acts as Mission Director."""
        node = TaskGraphNode(
            id=_DECOMPOSITION_NODE_ID,
            kind=NodeKind.AGENT,
            state=TaskMissionState.READY,
            config={"role": MISSION_DIRECTOR_ROLE},
        )
        task_id = _task_id(task_graph_id, _DECOMPOSITION_NODE_ID)
        task = TaskRecord(
            id=task_id,
            mission_id=mission_id,
            owner=owner,
            intent=f"decompose: {intent}",
            inputs={"goal": goal_text, "mission_id": mission_id},
            refs=(),
            acceptance_criteria=(
                "proposed_transitions_daemon_validated",
                "no_direct_terminal_authorship",
            ),
            state=TaskMissionState.READY,
            node_id=node.id,
            node_kind=node.kind,
            agent_role=MISSION_DIRECTOR_ROLE,
            ledger=TaskLedger(task_id=task_id),
        )
        return TaskGraph(
            id=task_graph_id,
            mission_id=mission_id,
            nodes=(node,),
            tasks=(task,),
            graph_template_ref=None,
            state=TaskMissionState.READY,
        )

    def _expand_template(
        self,
        *,
        template: GraphTemplate,
        mission_id: str,
        task_graph_id: str,
        owner: ActorId,
    ) -> Result[TaskGraph]:
        nodes: list[TaskGraphNode] = []
        tasks: list[TaskRecord] = []
        seen_ids: set[str] = set()

        for index, raw in enumerate(template.nodes):
            node_id_raw = raw.get("id", f"node-{index}")
            if not isinstance(node_id_raw, str) or not node_id_raw:
                return invalid_input("node.id", "graph template node id must be a string")
            if node_id_raw in seen_ids:
                return invalid_input(
                    "node.id",
                    "duplicate node id in Graph Template",
                    given=node_id_raw,
                )
            seen_ids.add(node_id_raw)
            kind = _parse_node_kind(raw.get("kind", NodeKind.TASK.value))
            if not is_ok(kind):
                return kind
            node_kind = kind.value
            config = {key: value for key, value in raw.items() if key not in {"id", "kind"}}
            node = TaskGraphNode(
                id=node_id_raw,
                kind=node_kind,
                state=TaskMissionState.PENDING,
                config=config,
            )
            nodes.append(node)
            if node_kind not in TASK_EMITTING_NODE_KINDS:
                continue
            # loop nodes mint Tasks at iteration time (AD-13); initial graph
            # materializes iteration 0 only when the template declares seed=true.
            if node_kind is NodeKind.LOOP and not bool(raw.get("seed", False)):
                continue
            task_id = _task_id(task_graph_id, node_id_raw)
            intent_raw = raw.get("intent", f"execute:{node_id_raw}")
            intent = intent_raw if isinstance(intent_raw, str) else f"execute:{node_id_raw}"
            ac_raw = raw.get("acceptance_criteria", ())
            if isinstance(ac_raw, Sequence) and not isinstance(ac_raw, (str, bytes)):
                acceptance = tuple(str(item) for item in cast("Sequence[object]", ac_raw))
            else:
                acceptance = ()
            refs_raw = raw.get("refs", ())
            if isinstance(refs_raw, Sequence) and not isinstance(refs_raw, (str, bytes)):
                refs = tuple(str(item) for item in cast("Sequence[object]", refs_raw))
            else:
                refs = ()
            inputs_raw = raw.get("inputs", {})
            inputs: dict[str, object] = (
                dict(cast("Mapping[str, object]", inputs_raw))
                if isinstance(inputs_raw, Mapping)
                else {}
            )
            worker_template = raw.get("worker_template")
            worker_ref = worker_template if isinstance(worker_template, str) else None
            agent_role = "pinned_agent" if node_kind is NodeKind.AGENT else None
            tasks.append(
                TaskRecord(
                    id=task_id,
                    mission_id=mission_id,
                    owner=owner,
                    intent=intent,
                    inputs=inputs,
                    refs=refs,
                    acceptance_criteria=acceptance,
                    state=TaskMissionState.READY if index == 0 else TaskMissionState.PENDING,
                    node_id=node_id_raw,
                    node_kind=node_kind,
                    agent_role=agent_role,
                    worker_template_ref=worker_ref,
                    ledger=TaskLedger(task_id=task_id),
                )
            )

        # Reject back-edges at compile/registration time (AD-13).
        forward: set[tuple[str, str]] = set()
        for edge in template.edges:
            src = edge.get("from")
            dst = edge.get("to")
            if not isinstance(src, str) or not isinstance(dst, str):
                return invalid_input("edge", "graph template edges require from/to strings")
            if (dst, src) in forward:
                return policy_rejection(
                    "graph_template",
                    "back-edges are rejected at Graph Template registration/compile "
                    "(AD-13; FR-Q29)",
                    from_node=src,
                    to_node=dst,
                )
            forward.add((src, dst))

        initial_state = (
            TaskMissionState.READY
            if any(t.state is TaskMissionState.READY for t in tasks)
            else TaskMissionState.PENDING
        )
        return Ok(
            TaskGraph(
                id=task_graph_id,
                mission_id=mission_id,
                nodes=tuple(nodes),
                tasks=tuple(tasks),
                graph_template_ref=template.qualified_id,
                state=initial_state,
            )
        )
