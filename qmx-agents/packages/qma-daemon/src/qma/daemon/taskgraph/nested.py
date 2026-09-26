"""Nested Mission invoke — one nested Mission / Task Graph / JobHandle.

Story 63.1 / FR-PG-29 / DEC-0455. A Graph Template node starts another
template at runtime as parent-AD-3 invoke of the callee's existing
``start | query-state | cancel | await``. Result is one nested Mission, one
Task Graph, one JobHandle. Occupancy and cancel follow that JobHandle.
Nested invoke does not union grants. Crash of A does not splice B's graph
into A. Include-at-author and the recursion-ceiling row are not this story.

Nested Mission occupancy was absent at inspect SHA ``34c148b``. Envelope
``call_depth`` / ``parent_logical_invocation_id`` and AD-3 lifecycle verbs
already existed there as CONNECT fixtures (DEC-0465; NFR-PG-04).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qma.core.ontology import Goal, Quant
from qma.core.operations import public_operation_descriptors
from qma.core.operations.descriptor import OperationDescriptor
from qma.core.ports.jobs import JobHandle
from qma.core.ports.permissions import nested_invocation_grants
from qma.core.vocabulary.enums import CallerKind, LifecycleVerb
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.taskgraph.compiler import CompileRequest, GraphTemplateCatalog, MissionCompiler
from qma.daemon.taskgraph.projection import TaskGraphStateService, empty_occupancy
from qma.daemon.taskgraph.records import (
    GraphTemplate,
    MissionRecord,
    TaskGraph,
    TaskGraphNode,
)
from qma.wire.invocation_envelope import InvocationEnvelope, parse_invocation_envelope
from qmf.core import Ok, Result, is_refusal
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CALL_DEPTH_EXISTED_AT_INSPECT_SHA",
    "FIFTH_COMPOSITION_MODE_MINTED",
    "INCLUDE_AT_AUTHOR_IMPLEMENTED",
    "LIFECYCLE_VERBS_EXISTED_AT_INSPECT_SHA",
    "NESTED_MISSION_CALLEE_OP_ID",
    "NESTED_MISSION_INSPECT_SHA",
    "NESTED_MISSION_LIFECYCLE_VERBS",
    "NESTED_MISSION_OCCUPANCY_EXISTED_AT_INSPECT_SHA",
    "NESTED_MISSION_OCCUPANCY_FOLLOWS",
    "PARENT_AD10_COMPOSITION_MODES",
    "PARENT_LOGICAL_INVOCATION_ID_EXISTED_AT_INSPECT_SHA",
    "RECURSION_CEILING_ROW_IMPLEMENTED",
    "SECOND_VERB_SET_MINTED",
    "NestedMissionHost",
    "NestedMissionOccupancy",
    "ParentMissionRun",
    "claim_nested_connect_surface_absent_at_inspect_sha",
    "claim_nested_mission_occupancy_at_inspect_sha",
    "nested_callee_from_node",
    "refuse_live_graph_splice",
]


NESTED_MISSION_INSPECT_SHA: Final[str] = "34c148b"
NESTED_MISSION_OCCUPANCY_EXISTED_AT_INSPECT_SHA: Final[bool] = False
CALL_DEPTH_EXISTED_AT_INSPECT_SHA: Final[bool] = True
PARENT_LOGICAL_INVOCATION_ID_EXISTED_AT_INSPECT_SHA: Final[bool] = True
LIFECYCLE_VERBS_EXISTED_AT_INSPECT_SHA: Final[bool] = True
SECOND_VERB_SET_MINTED: Final[bool] = False
FIFTH_COMPOSITION_MODE_MINTED: Final[bool] = False
INCLUDE_AT_AUTHOR_IMPLEMENTED: Final[bool] = False
RECURSION_CEILING_ROW_IMPLEMENTED: Final[bool] = False
NESTED_MISSION_OCCUPANCY_FOLLOWS: Final[str] = "job_handle"
NESTED_MISSION_LIFECYCLE_VERBS: Final[frozenset[str]] = frozenset(
    member.value for member in LifecycleVerb
)
PARENT_AD10_COMPOSITION_MODES: Final[tuple[str, ...]] = (
    "consume_artifact",
    "invoke_op",
    "graph_template_coordinate",
    "composite_instance_graph",
)
_NESTED_CALLEE_OP_ID: Final[str] = "qma.procedure.start"


def claim_nested_mission_occupancy_at_inspect_sha(existed: object) -> Result[bool]:
    """Claiming nested Mission occupancy existed at inspect SHA ``34c148b`` fails."""
    if existed is True or existed == "true":
        return policy_rejection(
            "nested_mission_occupancy",
            "nested Mission invoke as first-class occupancy was absent at inspect "
            "SHA 34c148b; call_depth, parent_logical_invocation_id, and AD-3 "
            "lifecycle verbs existed as CONNECT fixtures (DEC-0465; NFR-PG-04; "
            "SCN-0025 Branch D)",
            existed_at_inspect_sha=False,
            inspect_sha=NESTED_MISSION_INSPECT_SHA,
            call_depth_existed_at_inspect_sha=True,
            parent_logical_invocation_id_existed_at_inspect_sha=True,
            lifecycle_verbs_existed_at_inspect_sha=True,
        )
    if existed is not False:
        return invalid_input(
            "existed_at_inspect_sha",
            "inspect-SHA claim is a boolean",
            given=repr(existed),
        )
    return Ok(False)


def claim_nested_connect_surface_absent_at_inspect_sha(absent: object) -> Result[bool]:
    """Claiming call_depth / parent id / lifecycle verbs were absent fails."""
    if absent is True or absent == "true":
        return policy_rejection(
            "call_depth",
            "call_depth, parent_logical_invocation_id, and lifecycle verbs "
            "existed at inspect SHA 34c148b as CONNECT fixtures; nested Mission "
            "occupancy did not (DEC-0465; NFR-PG-04; AR-PG-09)",
            existed_at_inspect_sha=True,
            nested_mission_occupancy_existed_at_inspect_sha=False,
            inspect_sha=NESTED_MISSION_INSPECT_SHA,
            lifecycle_verbs=sorted(NESTED_MISSION_LIFECYCLE_VERBS),
        )
    if absent is not False:
        return invalid_input(
            "absent_at_inspect_sha",
            "inspect-SHA claim is a boolean",
            given=repr(absent),
        )
    return Ok(False)


def refuse_live_graph_splice(
    *,
    parent: TaskGraph,
    child: TaskGraph,
) -> TypedRefusal:
    """Crash of A must not copy B's nodes into A (SCN-0025 Branch A)."""
    return invalid_input(
        "task_graph",
        "crash of the parent does not splice the child's Task Graph into the "
        "parent; A does not copy B's nodes (DEC-0455; SCN-0025 Branch A)",
        parent_graph_id=parent.id,
        child_graph_id=child.id,
        spliced=False,
        parent_node_ids=[node.id for node in parent.nodes],
        child_node_ids=[node.id for node in child.nodes],
    )


def nested_callee_from_node(node: TaskGraphNode) -> Result[tuple[str, str]]:
    """Read callee Graph Template identity from a parent node's ``starts``."""
    raw = node.config.get("starts")
    if not isinstance(raw, Mapping):
        return invalid_input(
            "starts",
            "a Graph Template node starts another as (qualified_id, version)",
            node_id=node.id,
            given=repr(raw),
        )
    body = cast("Mapping[object, object]", raw)
    qualified = body.get("qualified_id")
    version = body.get("version")
    if not isinstance(qualified, str) or qualified.strip() == "":
        return invalid_input(
            "starts.qualified_id",
            "callee identity is Graph Template (qualified_id, version)",
            node_id=node.id,
        )
    if not isinstance(version, str) or version.strip() == "":
        return invalid_input(
            "starts.version",
            "callee identity is Graph Template (qualified_id, version)",
            node_id=node.id,
        )
    return Ok((qualified.strip(), version.strip()))


def _parse_verb(value: object) -> Result[LifecycleVerb]:
    try:
        return Ok(parse_closed(LifecycleVerb, value))
    except VocabularyError as exc:
        return invalid_input(
            "lifecycle_verbs",
            "nested Mission invoke uses existing start|query-state|cancel|await; "
            "do not mint a second verb set (FR-PG-29; AR-PG-09)",
            given=repr(value),
            allowed=sorted(NESTED_MISSION_LIFECYCLE_VERBS),
            second_verb_set_minted=SECOND_VERB_SET_MINTED,
            detail=str(exc),
        )


def _descriptor_for(op_id: str, version: int) -> Result[OperationDescriptor]:
    for item in public_operation_descriptors():
        if item.op_id == op_id and item.version == version:
            return Ok(item)
    return invalid_input(
        "op_id",
        "parent-AD-3 invoke requires a published OperationDescriptor",
        op_id=op_id,
        op_version=version,
    )


def _as_grant_ids(value: object, *, field: str) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return invalid_input(field, f"{field} entries are non-empty grant ids")
        return Ok((token,))
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return invalid_input(field, f"{field} is a sequence of grant ids", given=repr(value))
    items: list[str] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, str) or item.strip() == "":
            return invalid_input(
                field, f"{field} entries are non-empty grant ids", given=repr(item)
            )
        items.append(item.strip())
    return Ok(tuple(items))


@dataclass(frozen=True, slots=True)
class ParentMissionRun:
    """Compiled parent Mission A with its own Task Graph and JobHandle."""

    owner: Quant
    mission: MissionRecord
    task_graph: TaskGraph
    handle: JobHandle

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "graph_id": self.task_graph.id,
                "job_id": self.handle.job_id,
                "mission_id": self.mission.id,
                "owner": self.owner.actor_id.value,
                "template": self.mission.graph_template_ref,
            }
        )


@dataclass(frozen=True, slots=True)
class NestedMissionOccupancy:
    """First-class nested Mission occupancy keyed by the callee JobHandle."""

    verb: LifecycleVerb
    envelope: InvocationEnvelope
    parent_graph_id: str
    parent_mission_id: str
    parent_node_id: str
    callee_qualified_id: str
    callee_version: str
    mission: MissionRecord
    task_graph: TaskGraph
    handle: JobHandle
    grant_ids: tuple[str, ...]

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "callee": {
                    "qualified_id": self.callee_qualified_id,
                    "version": self.callee_version,
                },
                "caller_kind": self.envelope.caller_kind.value,
                "follows": NESTED_MISSION_OCCUPANCY_FOLLOWS,
                "grant_ids": list(self.grant_ids),
                "graph_id": self.task_graph.id,
                "grants_unioned": False,
                "instance_id": self.envelope.instance_id,
                "job_id": self.handle.job_id,
                "mission_id": self.mission.id,
                "parent_graph_id": self.parent_graph_id,
                "parent_mission_id": self.parent_mission_id,
                "parent_node_id": self.parent_node_id,
                "spliced": False,
                "verb": self.verb.value,
            }
        )


@dataclass
class NestedMissionHost:
    """Runtime nested Mission invoke. One compile → one Mission → one JobHandle."""

    compiler: MissionCompiler = field(default_factory=MissionCompiler)
    jobs: JobHandleService = field(default_factory=JobHandleService)
    graphs: TaskGraphStateService = field(default_factory=TaskGraphStateService)
    _parents: dict[str, ParentMissionRun] = field(
        default_factory=dict[str, ParentMissionRun], init=False
    )
    _live: dict[str, TaskGraph] = field(default_factory=dict[str, TaskGraph], init=False)
    _by_job: dict[str, NestedMissionOccupancy] = field(
        default_factory=dict[str, NestedMissionOccupancy], init=False
    )
    _by_parent_node: dict[tuple[str, str], str] = field(
        default_factory=dict[tuple[str, str], str], init=False
    )

    @property
    def templates(self) -> GraphTemplateCatalog:
        return self.compiler.templates

    @property
    def fifth_composition_mode_minted(self) -> bool:
        return FIFTH_COMPOSITION_MODE_MINTED

    @property
    def include_at_author_implemented(self) -> bool:
        return INCLUDE_AT_AUTHOR_IMPLEMENTED

    @property
    def recursion_ceiling_row_implemented(self) -> bool:
        return RECURSION_CEILING_ROW_IMPLEMENTED

    def register_template(self, template: GraphTemplate) -> Result[str]:
        return self.templates.register(template)

    def compile_parent(
        self,
        *,
        owner: Quant,
        template: GraphTemplate,
        goal: str,
        intent: str | None = None,
    ) -> Result[ParentMissionRun]:
        """Compile Graph Template A. Does not inline callee B's nodes."""
        registered = self.templates.get_versioned(template.qualified_id, template.version)
        if registered is None:
            stored = self.register_template(template)
            if is_refusal(stored):
                return stored
        compiled = self.compiler.compile(
            CompileRequest(
                goal=Goal(text=goal),
                owner=owner,
                graph_template_ref=template.qualified_id,
                intent=intent if intent is not None else goal,
            )
        )
        if is_refusal(compiled):
            return compiled
        graph = compiled.value.task_graph
        persisted = self.graphs.persist(graph)
        if is_refusal(persisted):
            return persisted
        ready = graph.ready_tasks()
        if not ready:
            return invalid_input(
                "task_graph",
                "parent Graph Template A must emit a Task so occupancy can follow a JobHandle",
                graph_id=graph.id,
            )
        submitted = self.jobs.submit(
            owner=owner.actor_id,
            task_id=ready[0].id,
            job_id=f"job:{graph.id}",
            logical_run_id=graph.id,
        )
        if is_refusal(submitted):
            return submitted
        started = self.jobs.start(submitted.value.job_id)
        if is_refusal(started):
            return started
        run = ParentMissionRun(
            owner=owner,
            mission=compiled.value.mission,
            task_graph=graph,
            handle=started.value,
        )
        self._parents[graph.id] = run
        self._live[graph.id] = graph
        return Ok(run)

    def is_live(self, graph_id: str) -> bool:
        return graph_id in self._live

    def occupancy_for(self, job_id: str) -> NestedMissionOccupancy | None:
        return self._by_job.get(job_id)

    def handle_for(self, job_id: str) -> JobHandle | None:
        nested = self._by_job.get(job_id)
        if nested is not None:
            live = self.jobs.handle_for(job_id)
            return live if live is not None else nested.handle
        return self.jobs.handle_for(job_id)

    def invoke(
        self,
        verb: object,
        *,
        envelope: object,
        parent_graph_id: object | None = None,
        node_id: object | None = None,
        job_id: object | None = None,
        caller_grant_ids: object = (),
        callee_grant_ids: object | None = None,
        union_grants: bool = False,
    ) -> Result[NestedMissionOccupancy]:
        """Parent-AD-3 invoke of B: start | query-state | cancel | await."""
        parsed_verb = _parse_verb(verb)
        if is_refusal(parsed_verb):
            return parsed_verb
        parsed_env = parse_invocation_envelope(envelope)
        if is_refusal(parsed_env):
            return parsed_env
        env = parsed_env.value
        if env.instance_id.strip() == "":
            return invalid_input(
                "instance_id",
                "envelope instance_id remains required on nested Mission invoke",
            )
        if env.caller_kind is not CallerKind.WORKFLOW:
            return invalid_input(
                "caller_kind",
                "nested Mission invoke carries caller_kind=workflow",
                given=env.caller_kind.value,
                allowed=["workflow"],
            )
        if env.parent_logical_invocation_id is None or env.call_depth < 1:
            return invalid_input(
                "call_depth",
                "nested public calls carry parent_logical_invocation_id and call_depth",
                call_depth=env.call_depth,
            )
        descriptor = _descriptor_for(env.op_id, env.op_version)
        if is_refusal(descriptor):
            return descriptor
        if parsed_verb.value not in descriptor.value.lifecycle_verbs:
            return invalid_input(
                "lifecycle_verbs",
                "do not mint a second verb set; use the callee descriptor's "
                "existing start|query-state|cancel|await (FR-PG-29)",
                verb=parsed_verb.value.value,
                op_id=env.op_id,
                allowed=[item.value for item in descriptor.value.lifecycle_verbs],
                second_verb_set_minted=SECOND_VERB_SET_MINTED,
            )
        if parsed_verb.value is LifecycleVerb.START:
            return self._start(
                envelope=env,
                parent_graph_id=parent_graph_id,
                node_id=node_id,
                caller_grant_ids=caller_grant_ids,
                callee_grant_ids=callee_grant_ids,
                union_grants=union_grants,
            )
        resolved = self._resolve(job_id=job_id, parent_graph_id=parent_graph_id, node_id=node_id)
        if is_refusal(resolved):
            return resolved
        occupancy = resolved.value
        if parsed_verb.value is LifecycleVerb.QUERY_STATE:
            live = self.jobs.handle_for(occupancy.handle.job_id)
            handle = live if live is not None else occupancy.handle
            return Ok(
                NestedMissionOccupancy(
                    verb=LifecycleVerb.QUERY_STATE,
                    envelope=env,
                    parent_graph_id=occupancy.parent_graph_id,
                    parent_mission_id=occupancy.parent_mission_id,
                    parent_node_id=occupancy.parent_node_id,
                    callee_qualified_id=occupancy.callee_qualified_id,
                    callee_version=occupancy.callee_version,
                    mission=occupancy.mission,
                    task_graph=occupancy.task_graph,
                    handle=handle,
                    grant_ids=occupancy.grant_ids,
                )
            )
        if parsed_verb.value is LifecycleVerb.CANCEL:
            cancelled = self.jobs.cancel(occupancy.handle.job_id)
            if is_refusal(cancelled):
                return cancelled
            updated = NestedMissionOccupancy(
                verb=LifecycleVerb.CANCEL,
                envelope=env,
                parent_graph_id=occupancy.parent_graph_id,
                parent_mission_id=occupancy.parent_mission_id,
                parent_node_id=occupancy.parent_node_id,
                callee_qualified_id=occupancy.callee_qualified_id,
                callee_version=occupancy.callee_version,
                mission=occupancy.mission,
                task_graph=occupancy.task_graph,
                handle=cancelled.value,
                grant_ids=occupancy.grant_ids,
            )
            self._by_job[cancelled.value.job_id] = updated
            return Ok(updated)
        waited = self.jobs.wait(occupancy.handle.job_id)
        if is_refusal(waited):
            return waited
        return Ok(
            NestedMissionOccupancy(
                verb=LifecycleVerb.AWAIT,
                envelope=env,
                parent_graph_id=occupancy.parent_graph_id,
                parent_mission_id=occupancy.parent_mission_id,
                parent_node_id=occupancy.parent_node_id,
                callee_qualified_id=occupancy.callee_qualified_id,
                callee_version=occupancy.callee_version,
                mission=occupancy.mission,
                task_graph=occupancy.task_graph,
                handle=waited.value.handle,
                grant_ids=occupancy.grant_ids,
            )
        )

    def crash_parent(self, parent_graph_id: str) -> Result[None]:
        """A crashes while B runs. B's graph is not dropped or spliced."""
        if parent_graph_id not in self._live and parent_graph_id not in self._parents:
            return invalid_input(
                "parent_graph_id",
                "crash recovery requires a live parent Mission A",
                given=parent_graph_id,
            )
        self._live.pop(parent_graph_id, None)
        return Ok(None)

    def recover_parent(self, parent_graph_id: str) -> Result[TaskGraph]:
        """Restore A from durable occupancy. B's nodes stay off A's graph."""
        loaded = self.graphs.get(parent_graph_id)
        if is_refusal(loaded):
            return loaded
        parent = loaded.value
        original = self._parents.get(parent_graph_id)
        if original is not None:
            original_ids = {node.id for node in original.task_graph.nodes}
            leaked = [node.id for node in parent.nodes if node.id not in original_ids]
            if leaked:
                child = next(
                    (
                        occupancy.task_graph
                        for occupancy in self._by_job.values()
                        if occupancy.parent_graph_id == parent_graph_id
                    ),
                    None,
                )
                if child is not None:
                    return refuse_live_graph_splice(parent=parent, child=child)
                return invalid_input(
                    "task_graph",
                    "recovered parent A must not carry nodes that were not on A",
                    leaked=leaked,
                    spliced=False,
                )
        for occupancy in self._by_job.values():
            if occupancy.parent_graph_id != parent_graph_id:
                continue
            if occupancy.task_graph.id == parent.id:
                return refuse_live_graph_splice(parent=parent, child=occupancy.task_graph)
        self._live[parent.id] = parent
        return Ok(parent)

    def splice_child_into_parent(
        self,
        *,
        parent_graph_id: str,
        child_job_id: str,
    ) -> Result[TaskGraph]:
        """Forbidden crash-recovery path: copy B's nodes into A."""
        parent = self.graphs.get(parent_graph_id)
        if is_refusal(parent):
            return parent
        occupancy = self._by_job.get(child_job_id)
        if occupancy is None:
            return invalid_input(
                "job_id",
                "nested Mission occupancy follows the callee JobHandle",
                given=child_job_id,
            )
        return refuse_live_graph_splice(parent=parent.value, child=occupancy.task_graph)

    def _start(
        self,
        *,
        envelope: InvocationEnvelope,
        parent_graph_id: object | None,
        node_id: object | None,
        caller_grant_ids: object,
        callee_grant_ids: object | None,
        union_grants: bool,
    ) -> Result[NestedMissionOccupancy]:
        if not isinstance(parent_graph_id, str) or parent_graph_id.strip() == "":
            return invalid_input(
                "parent_graph_id",
                "nested start names parent Graph Template A's live Task Graph",
                given=repr(parent_graph_id),
            )
        parent = self._parents.get(parent_graph_id.strip())
        if parent is None:
            return invalid_input(
                "parent_graph_id",
                "parent Mission A is not a live nested-Mission occupancy",
                given=parent_graph_id,
            )
        node = self._parent_node(parent.task_graph, node_id)
        if is_refusal(node):
            return node
        callee_id = nested_callee_from_node(node.value)
        if is_refusal(callee_id):
            return callee_id
        qualified_id, version = callee_id.value
        if envelope.contribution.qualified_id != qualified_id:
            return invalid_input(
                "contribution.qualified_id",
                "envelope contribution is the callee Graph Template (qualified_id, version)",
                given=envelope.contribution.qualified_id,
                expected=qualified_id,
            )
        if envelope.contribution.package_version != version:
            return invalid_input(
                "contribution.package_version",
                "envelope contribution is the callee Graph Template (qualified_id, version)",
                given=envelope.contribution.package_version,
                expected=version,
            )
        template = self.templates.get_versioned(qualified_id, version)
        if template is None:
            return invalid_input(
                "starts",
                "callee Graph Template (qualified_id, version) must be registered",
                qualified_id=qualified_id,
                version=version,
            )
        caller = _as_grant_ids(caller_grant_ids, field="caller_grant_ids")
        if is_refusal(caller):
            return caller
        if callee_grant_ids is None:
            callee = (envelope.grant_id,)
        else:
            parsed_callee = _as_grant_ids(callee_grant_ids, field="callee_grant_ids")
            if is_refusal(parsed_callee):
                return parsed_callee
            callee = parsed_callee.value
        proposed: tuple[str, ...] | None = None
        if envelope.grant_id not in callee:
            proposed = (*callee, envelope.grant_id)
        granted = nested_invocation_grants(
            caller.value,
            callee,
            union=union_grants,
            proposed=proposed,
        )
        if is_refusal(granted):
            return granted
        compiled = self.compiler.compile(
            CompileRequest(
                goal=Goal(text=f"nested {qualified_id}@{version}"),
                owner=parent.owner,
                graph_template_ref=qualified_id,
                intent=(f"nested:{parent.mission.id}:{node.value.id}:{qualified_id}:{version}"),
            )
        )
        if is_refusal(compiled):
            return compiled
        child_graph = compiled.value.task_graph
        if child_graph.id == parent.task_graph.id:
            return refuse_live_graph_splice(parent=parent.task_graph, child=child_graph)
        ready = child_graph.ready_tasks()
        if not ready:
            return invalid_input(
                "task_graph",
                "callee Graph Template B must emit a Task so occupancy can follow a JobHandle",
                graph_id=child_graph.id,
            )
        submitted = self.jobs.submit(
            owner=parent.owner.actor_id,
            task_id=ready[0].id,
            job_id=f"job:{child_graph.id}",
            logical_run_id=child_graph.id,
            correlation_id=envelope.logical_invocation_id,
        )
        if is_refusal(submitted):
            return submitted
        started = self.jobs.start(submitted.value.job_id)
        if is_refusal(started):
            return started
        occupancy = NestedMissionOccupancy(
            verb=LifecycleVerb.START,
            envelope=envelope,
            parent_graph_id=parent.task_graph.id,
            parent_mission_id=parent.mission.id,
            parent_node_id=node.value.id,
            callee_qualified_id=qualified_id,
            callee_version=version,
            mission=compiled.value.mission,
            task_graph=child_graph,
            handle=started.value,
            grant_ids=tuple(sorted(granted.value)),
        )
        child_occupancy = dict(empty_occupancy())
        child_slots: dict[str, object] = {
            started.value.job_id: {
                "follows": NESTED_MISSION_OCCUPANCY_FOLLOWS,
                "graph_id": child_graph.id,
                "job_id": started.value.job_id,
                "kind": "nested_mission",
                "mission_id": occupancy.mission.id,
                "parent_graph_id": parent.task_graph.id,
                "spliced": False,
            }
        }
        child_occupancy["slots"] = child_slots
        persisted_child = self.graphs.persist(child_graph, occupancy=child_occupancy)
        if is_refusal(persisted_child):
            return persisted_child
        parent_occupancy = dict(self.graphs.occupancy_for(parent.task_graph.id))
        parent_slots_raw = parent_occupancy.get("slots", {})
        parent_slots: dict[str, object] = {}
        if isinstance(parent_slots_raw, Mapping):
            parent_slots = dict(cast("Mapping[str, object]", parent_slots_raw))
        parent_slots[node.value.id] = {
            "follows": NESTED_MISSION_OCCUPANCY_FOLLOWS,
            "kind": "nested_mission_pointer",
            "nested_graph_id": child_graph.id,
            "nested_job_id": started.value.job_id,
            "nested_mission_id": occupancy.mission.id,
            "spliced": False,
        }
        parent_occupancy["slots"] = parent_slots
        persisted_parent = self.graphs.persist(parent.task_graph, occupancy=parent_occupancy)
        if is_refusal(persisted_parent):
            return persisted_parent
        self._live[child_graph.id] = child_graph
        self._by_job[started.value.job_id] = occupancy
        self._by_parent_node[(parent.task_graph.id, node.value.id)] = started.value.job_id
        return Ok(occupancy)

    def _parent_node(
        self,
        graph: TaskGraph,
        node_id: object | None,
    ) -> Result[TaskGraphNode]:
        if node_id is None:
            matches = [node for node in graph.nodes if "starts" in node.config]
            if len(matches) != 1:
                return invalid_input(
                    "node_id",
                    "nested start names the parent node that starts callee B",
                    matches=[node.id for node in matches],
                )
            return Ok(matches[0])
        if not isinstance(node_id, str) or node_id.strip() == "":
            return invalid_input(
                "node_id",
                "parent node id is a non-empty string",
                given=repr(node_id),
            )
        found = graph.node_by_id(node_id.strip())
        if found is None:
            return invalid_input(
                "node_id",
                "parent node is not on Graph Template A's Task Graph",
                given=node_id,
                graph_id=graph.id,
            )
        return Ok(found)

    def _resolve(
        self,
        *,
        job_id: object | None,
        parent_graph_id: object | None,
        node_id: object | None,
    ) -> Result[NestedMissionOccupancy]:
        if isinstance(job_id, str) and job_id.strip():
            occupancy = self._by_job.get(job_id.strip())
            if occupancy is None:
                return invalid_input(
                    "job_id",
                    "occupancy and cancel follow the nested Mission JobHandle",
                    given=job_id,
                )
            return Ok(occupancy)
        if isinstance(parent_graph_id, str) and isinstance(node_id, str):
            nested_job = self._by_parent_node.get((parent_graph_id, node_id))
            if nested_job is None:
                return invalid_input(
                    "node_id",
                    "parent node has no nested Mission JobHandle",
                    parent_graph_id=parent_graph_id,
                    node_id=node_id,
                )
            occupancy = self._by_job.get(nested_job)
            if occupancy is None:
                return invalid_input(
                    "job_id",
                    "occupancy and cancel follow the nested Mission JobHandle",
                    given=nested_job,
                )
            return Ok(occupancy)
        return invalid_input(
            "job_id",
            "query-state|cancel|await follow the nested Mission JobHandle",
            given=repr(job_id),
        )


# Published callee op used when tests do not override envelope.op_id.
NESTED_MISSION_CALLEE_OP_ID: Final[str] = _NESTED_CALLEE_OP_ID
