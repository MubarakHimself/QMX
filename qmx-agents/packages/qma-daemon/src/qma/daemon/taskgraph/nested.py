"""Nested Mission invoke — one nested Mission / Task Graph / JobHandle.

Story 63.1 / FR-PG-29 / DEC-0455. A Graph Template node starts another
template at runtime as parent-AD-3 invoke of the callee's existing
``start | query-state | cancel | await``. Result is one nested Mission, one
Task Graph, one JobHandle. Occupancy and cancel follow that JobHandle.
Nested invoke does not union grants. Crash of A does not splice B's graph
into A.

Story 63.2 / FR-PG-30..32. Include-at-author writes a new versioned Graph
Template; it is not a runtime merge of live Task Graphs. Merging two live
Task Graphs is ``INVALID_INPUT`` (or the owner COMP illegal-topology
refusal). Envelope ``call_depth`` is checked against the host-registered
recursion ceiling; this story mints no number and does not reuse the
GAP-0108 retry-attempt ceiling row.

Story 63.3 / FR-PG-28. A widget binds ``start`` of template T. The press
is an enveloped invoke with ``caller_kind=user|agent`` and required
``instance_id``. Dispose does not cancel the Mission. A widget
contribution point without an envelope is refused. Parent AD-10 four
modes remain; GAP-0081 chrome is not filled.

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
from qma.core.vocabulary.enums import CallerKind, JobHandleState, LifecycleVerb
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.journal.variables import (
    HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY,
    HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY,
    HOST_RETRY_ATTEMPT_CEILING_KEY,
    HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
    GovernedVariableRegistry,
)
from qma.daemon.taskgraph.compiler import CompileRequest, GraphTemplateCatalog, MissionCompiler
from qma.daemon.taskgraph.execution import TOPOLOGY_REFUSAL_FAMILY
from qma.daemon.taskgraph.projection import TaskGraphStateService, empty_occupancy
from qma.daemon.taskgraph.records import (
    GraphTemplate,
    MissionRecord,
    TaskGraph,
    TaskGraphNode,
)
from qma.daemon.taskgraph.widget_start import (
    FIFTH_COMPOSITION_MODE_MINTED,
    GAP_0081_CHROME_FILLED,
    PARENT_AD10_COMPOSITION_MODES,
    WIDGET_DISPOSE_CANCELS_MISSION,
    WIDGET_START_CALLER_KINDS,
    WIDGET_START_IMPLEMENTED,
    WIDGET_START_VERB,
    WIDGETS_OWN_INVOKE,
    WidgetStartBinding,
    WidgetStartedMission,
    parse_widget_start_binding,
    refuse_fifth_composition_mode,
    refuse_gap_0081_widget_chrome,
    refuse_widget_contribution_without_envelope,
    refuse_widget_owned_invoke,
    widget_contribution_point_name,
)
from qma.wire.invocation_envelope import InvocationEnvelope, parse_invocation_envelope
from qmf.core import Ok, Result, is_refusal
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CALL_DEPTH_EXISTED_AT_INSPECT_SHA",
    "CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW",
    "FIFTH_COMPOSITION_MODE_MINTED",
    "GAP_0081_CHROME_FILLED",
    "GAP_0108_IS_RETRY_ATTEMPT_CEILING",
    "HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY",
    "HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY",
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
    "WIDGETS_OWN_INVOKE",
    "WIDGET_DISPOSE_CANCELS_MISSION",
    "WIDGET_START_CALLER_KINDS",
    "WIDGET_START_IMPLEMENTED",
    "WIDGET_START_VERB",
    "NestedMissionHost",
    "NestedMissionOccupancy",
    "ParentMissionRun",
    "WidgetStartBinding",
    "WidgetStartedMission",
    "bind_call_depth_ceiling_key",
    "claim_nested_connect_surface_absent_at_inspect_sha",
    "claim_nested_mission_occupancy_at_inspect_sha",
    "include_subgraph_at_author",
    "nested_callee_from_node",
    "parse_widget_start_binding",
    "refuse_fifth_composition_mode",
    "refuse_gap_0081_widget_chrome",
    "refuse_live_graph_splice",
    "refuse_live_task_graph_merge",
    "refuse_widget_contribution_without_envelope",
    "refuse_widget_owned_invoke",
]


NESTED_MISSION_INSPECT_SHA: Final[str] = "34c148b"
NESTED_MISSION_OCCUPANCY_EXISTED_AT_INSPECT_SHA: Final[bool] = False
CALL_DEPTH_EXISTED_AT_INSPECT_SHA: Final[bool] = True
PARENT_LOGICAL_INVOCATION_ID_EXISTED_AT_INSPECT_SHA: Final[bool] = True
LIFECYCLE_VERBS_EXISTED_AT_INSPECT_SHA: Final[bool] = True
SECOND_VERB_SET_MINTED: Final[bool] = False
INCLUDE_AT_AUTHOR_IMPLEMENTED: Final[bool] = True
RECURSION_CEILING_ROW_IMPLEMENTED: Final[bool] = True
CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW: Final[bool] = False
GAP_0108_IS_RETRY_ATTEMPT_CEILING: Final[bool] = True
_RETRY_CEILING_KEYS: Final[frozenset[str]] = frozenset(
    {
        HOST_RETRY_ATTEMPT_CEILING_KEY,
        HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
    }
)
_CALL_DEPTH_CEILING_KEYS: Final[frozenset[str]] = frozenset(
    {
        HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY,
        HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY,
    }
)
NESTED_MISSION_OCCUPANCY_FOLLOWS: Final[str] = "job_handle"
NESTED_MISSION_LIFECYCLE_VERBS: Final[frozenset[str]] = frozenset(
    member.value for member in LifecycleVerb
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


def refuse_live_task_graph_merge(
    *,
    left_graph_id: object | None = None,
    right_graph_id: object | None = None,
    left_found: bool = False,
    right_found: bool = False,
    instance_id: object | None = None,
    version: object | None = None,
    account: object | None = None,
    substitute_instance_id: object | None = None,
    substitute_version: object | None = None,
    substitute_account: object | None = None,
    other_live_graph_ids: Sequence[str] = (),
) -> TypedRefusal:
    """Merging two live Task Graphs is illegal topology (FR-PG-31)."""
    return invalid_input(
        "task_graph",
        "merging two live Task Graphs is refused; include-at-author is a new "
        "versioned Graph Template, not a runtime merge (DEC-0455; FR-PG-31; "
        "SCN-0025 Then 4)",
        code="INVALID_INPUT",
        family=TOPOLOGY_REFUSAL_FAMILY,
        merged=False,
        substituted=False,
        substituted_instance=False,
        substituted_version=False,
        substituted_account=False,
        left_graph_id=left_graph_id,
        right_graph_id=right_graph_id,
        left_found=left_found,
        right_found=right_found,
        instance_id=instance_id,
        version=version,
        account=account,
        substitute_instance_id=substitute_instance_id,
        substitute_version=substitute_version,
        substitute_account=substitute_account,
        other_live_graph_ids=list(other_live_graph_ids),
    )


def bind_call_depth_ceiling_key(key: object) -> Result[str]:
    """Bind the nested-mission call_depth ceiling; never the GAP-0108 retry row."""
    if not isinstance(key, str) or key.strip() == "":
        return invalid_input(
            "call_depth",
            "call_depth uses the host-registered nested-mission recursion ceiling",
            given=repr(key),
            call_depth_registry_key=HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY,
            gap_0108=False,
            reused_retry_row=CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW,
        )
    token = key.strip()
    if token in _RETRY_CEILING_KEYS:
        return invalid_input(
            "call_depth",
            "call_depth ceiling is not GAP-0108; do not reuse the retry-attempt "
            "ceiling registry row (FR-PG-32; AR-PG-10)",
            given=token,
            retry_registry_key=HOST_RETRY_ATTEMPT_CEILING_REGISTRY_KEY,
            call_depth_registry_key=HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY,
            gap_0108=False,
            reused_retry_row=False,
            code="INVALID_INPUT",
        )
    if token not in _CALL_DEPTH_CEILING_KEYS:
        return invalid_input(
            "call_depth",
            "call_depth uses the host-registered nested-mission recursion ceiling",
            given=token,
            call_depth_registry_key=HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY,
            gap_0108=False,
            reused_retry_row=CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW,
        )
    return Ok(HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY)


def _validate_call_depth_ceiling(value: object, *, source: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        shown: object = value if isinstance(value, (str, int, type(None))) else repr(value)
        return invalid_input(
            "call_depth",
            "host nested-mission call_depth ceiling is a host-registered "
            "registry row; this story mints no number (FR-PG-32; DEC-0455)",
            given=shown,
            registry_key=HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY,
            invented_default=False,
            source=source,
            gap_0108=False,
            code="INVALID_INPUT",
        )
    return Ok(value)


def _starts_identity(node: Mapping[str, object]) -> tuple[str, str] | None:
    raw = node.get("starts")
    if not isinstance(raw, Mapping):
        return None
    body = cast("Mapping[object, object]", raw)
    qualified = body.get("qualified_id")
    version = body.get("version")
    if not isinstance(qualified, str) or qualified.strip() == "":
        return None
    if not isinstance(version, str) or version.strip() == "":
        return None
    return (qualified.strip(), version.strip())


def include_subgraph_at_author(
    parent: object,
    included: object,
    *,
    new_version: object,
) -> Result[GraphTemplate]:
    """Compose B's subgraph into a new version of A. Never a live-graph merge."""
    if isinstance(parent, TaskGraph) or isinstance(included, TaskGraph):
        return invalid_input(
            "graph_template",
            "include-at-author composes Graph Templates, not a runtime merge of "
            "live Task Graphs (FR-PG-30; DEC-0455)",
            runtime_merge=False,
            code="INVALID_INPUT",
        )
    if not isinstance(parent, GraphTemplate):
        return invalid_input(
            "parent",
            "include-at-author names parent Graph Template A",
            given=type(parent).__name__,
        )
    if not isinstance(included, GraphTemplate):
        return invalid_input(
            "included",
            "include-at-author names included Graph Template B",
            given=type(included).__name__,
        )
    if not isinstance(new_version, str) or new_version.strip() == "":
        return invalid_input(
            "version",
            "include-at-author writes a new versioned Graph Template",
            given=repr(new_version),
        )
    version = new_version.strip()
    if version == parent.version:
        return invalid_input(
            "version",
            "include-at-author must write a new version, not overwrite the authored parent version",
            given=version,
            parent_version=parent.version,
        )
    if parent.qualified_id == included.qualified_id:
        return invalid_input(
            "graph_template_ref",
            "include-at-author includes another template's subgraph, not a self-merge",
            parent=parent.qualified_id,
            included=included.qualified_id,
        )
    included_id = (included.qualified_id, included.version)
    parent_nodes: list[dict[str, object]] = []
    for node in parent.nodes:
        body = dict(node)
        if _starts_identity(body) == included_id:
            continue
        parent_nodes.append(body)
    included_nodes = [dict(node) for node in included.nodes]
    seen: set[object] = {node.get("id") for node in parent_nodes}
    for node in included_nodes:
        node_id = node.get("id")
        if node_id in seen:
            return invalid_input(
                "node.id",
                "include-at-author does not silently rename colliding node ids",
                given=node_id,
                substituted=False,
                code="INVALID_INPUT",
            )
        seen.add(node_id)
    parent_ids = {node.get("id") for node in parent_nodes}
    included_ids = {node.get("id") for node in included_nodes}

    def _keep_edge(edge: Mapping[str, object], *, allow: set[object]) -> bool:
        return edge.get("from") in allow and edge.get("to") in allow

    edges = [dict(edge) for edge in parent.edges if _keep_edge(edge, allow=parent_ids)] + [
        dict(edge) for edge in included.edges if _keep_edge(edge, allow=included_ids)
    ]
    nodes = tuple(parent_nodes + included_nodes)
    if not nodes:
        return invalid_input(
            "nodes",
            "include-at-author produced an empty Graph Template",
        )
    try:
        authored = GraphTemplate(
            qualified_id=parent.qualified_id,
            version=version,
            nodes=nodes,
            edges=tuple(edges),
        )
    except ValueError as exc:
        return invalid_input("graph_template", str(exc))
    return Ok(authored)


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
    variables: GovernedVariableRegistry = field(
        default_factory=GovernedVariableRegistry.with_builtins
    )
    injected_call_depth_ceiling: int | None = None
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
    _widgets: dict[str, WidgetStartBinding] = field(
        default_factory=dict[str, WidgetStartBinding], init=False
    )
    _widget_jobs: dict[str, str] = field(default_factory=dict[str, str], init=False)
    _widget_starts: dict[str, WidgetStartedMission] = field(
        default_factory=dict[str, WidgetStartedMission], init=False
    )

    @property
    def templates(self) -> GraphTemplateCatalog:
        return self.compiler.templates

    @property
    def fifth_composition_mode_minted(self) -> bool:
        return FIFTH_COMPOSITION_MODE_MINTED

    @property
    def widgets_own_invoke(self) -> bool:
        return WIDGETS_OWN_INVOKE

    @property
    def widget_dispose_cancels_mission(self) -> bool:
        return WIDGET_DISPOSE_CANCELS_MISSION

    @property
    def gap_0081_chrome_filled(self) -> bool:
        return GAP_0081_CHROME_FILLED

    @property
    def widget_start_implemented(self) -> bool:
        return WIDGET_START_IMPLEMENTED

    @property
    def include_at_author_implemented(self) -> bool:
        return INCLUDE_AT_AUTHOR_IMPLEMENTED

    @property
    def recursion_ceiling_row_implemented(self) -> bool:
        return RECURSION_CEILING_ROW_IMPLEMENTED

    @property
    def call_depth_ceiling_key(self) -> str:
        return HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY

    def call_depth_ceiling(self) -> Result[int | None]:
        """Read the host-registered call_depth ceiling. Tests may inject a fixture."""
        if self.injected_call_depth_ceiling is not None:
            validated = _validate_call_depth_ceiling(
                self.injected_call_depth_ceiling, source="fixture"
            )
            if is_refusal(validated):
                return validated
            bound: int | None = validated.value
            return Ok(bound)
        raw = self.variables.get_value(HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY)
        if is_refusal(raw):
            return raw
        if raw.value is None:
            empty: int | None = None
            return Ok(empty)
        validated = _validate_call_depth_ceiling(raw.value, source="registry")
        if is_refusal(validated):
            return validated
        bound: int | None = validated.value
        return Ok(bound)

    def register_template(self, template: GraphTemplate) -> Result[str]:
        return self.templates.register(template)

    def include_at_author(
        self,
        parent: object,
        included: object,
        *,
        new_version: object,
    ) -> Result[GraphTemplate]:
        """Save include-of-B-into-A as a new versioned Graph Template."""
        parent_t = self._resolve_template(parent, field="parent")
        if is_refusal(parent_t):
            return parent_t
        included_t = self._resolve_template(included, field="included")
        if is_refusal(included_t):
            return included_t
        authored = include_subgraph_at_author(
            parent_t.value,
            included_t.value,
            new_version=new_version,
        )
        if is_refusal(authored):
            return authored
        stored = self.register_template(authored.value)
        if is_refusal(stored):
            return stored
        return Ok(authored.value)

    def merge_live_task_graphs(
        self,
        left_graph_id: object,
        right_graph_id: object,
        *,
        instance_id: object | None = None,
        version: object | None = None,
        account: object | None = None,
        substitute_instance_id: object | None = None,
        substitute_version: object | None = None,
        substitute_account: object | None = None,
    ) -> Result[TaskGraph]:
        """Always refuse. Partial failure does not substitute another identity."""
        left = self._live_graph(left_graph_id)
        right = self._live_graph(right_graph_id)
        known = {left_graph_id, right_graph_id}
        others = [graph_id for graph_id in self._live if graph_id not in known]
        return refuse_live_task_graph_merge(
            left_graph_id=left_graph_id if isinstance(left_graph_id, str) else repr(left_graph_id),
            right_graph_id=(
                right_graph_id if isinstance(right_graph_id, str) else repr(right_graph_id)
            ),
            left_found=left is not None,
            right_found=right is not None,
            instance_id=instance_id,
            version=version,
            account=account,
            substitute_instance_id=substitute_instance_id,
            substitute_version=substitute_version,
            substitute_account=substitute_account,
            other_live_graph_ids=others,
        )

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
                graph_template_version=template.version,
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
        started = self._widget_starts.get(job_id)
        if started is not None:
            live = self.jobs.handle_for(job_id)
            return live if live is not None else started.handle
        return self.jobs.handle_for(job_id)

    def widget_binding(self, widget_id: str) -> WidgetStartBinding | None:
        return self._widgets.get(widget_id)

    def widget_start_for(self, widget_id: str) -> WidgetStartedMission | None:
        job_id = self._widget_jobs.get(widget_id)
        if job_id is None:
            return None
        return self._widget_starts.get(job_id)

    def bind_widget_start(
        self,
        widget_id: object,
        template: object,
        *,
        verb: object = WIDGET_START_VERB,
        composition_mode: object | None = None,
        owns_invoke: object = False,
        is_contribution_point: object = False,
        gap_0081_chrome: object = False,
    ) -> Result[WidgetStartBinding]:
        """Bind a widget to ``start`` of Graph Template T. Host owns invoke."""
        resolved = self._resolve_widget_template(template)
        if is_refusal(resolved):
            return resolved
        binding = parse_widget_start_binding(
            widget_id,
            qualified_id=resolved.value.qualified_id,
            version=resolved.value.version,
            verb=verb,
            composition_mode=composition_mode,
            owns_invoke=owns_invoke,
            is_contribution_point=is_contribution_point,
            gap_0081_chrome=gap_0081_chrome,
        )
        if is_refusal(binding):
            return binding
        self._widgets[binding.value.widget_id] = binding.value
        return binding

    def press_widget(
        self,
        widget_id: object,
        *,
        envelope: object | None,
        owner: Quant,
        goal: str | None = None,
    ) -> Result[WidgetStartedMission]:
        """User/agent press. Envelope required. Widget does not own invoke."""
        if envelope is None:
            return refuse_widget_contribution_without_envelope(point="widget")
        if not isinstance(widget_id, str) or widget_id.strip() == "":
            return invalid_input(
                "widget_id",
                "widget id is a non-empty string",
                given=repr(widget_id),
            )
        token = widget_id.strip()
        binding = self._widgets.get(token)
        if binding is None:
            return invalid_input(
                "widget_id",
                "widget must be bound to start of template T before press",
                given=token,
                owns_invoke=WIDGETS_OWN_INVOKE,
            )
        parsed_env = parse_invocation_envelope(envelope)
        if is_refusal(parsed_env):
            return parsed_env
        env = parsed_env.value
        if env.instance_id.strip() == "":
            return invalid_input(
                "instance_id",
                "envelope instance_id remains required on widget start",
            )
        if env.caller_kind not in WIDGET_START_CALLER_KINDS:
            return invalid_input(
                "caller_kind",
                "widget start carries caller_kind=user or agent; nested "
                "workflow-to-workflow uses caller_kind=workflow",
                given=env.caller_kind.value,
                allowed=sorted(kind.value for kind in WIDGET_START_CALLER_KINDS),
            )
        if env.call_depth != 0:
            return invalid_input(
                "call_depth",
                "widget start is a top-level invoke_op, not a nested Mission",
                call_depth=env.call_depth,
                composition_mode=binding.composition_mode,
                fifth_composition_mode_minted=FIFTH_COMPOSITION_MODE_MINTED,
            )
        if env.contribution.qualified_id != binding.template_qualified_id:
            return invalid_input(
                "contribution.qualified_id",
                "envelope contribution is Graph Template T (qualified_id, version)",
                given=env.contribution.qualified_id,
                expected=binding.template_qualified_id,
            )
        if env.contribution.package_version != binding.template_version:
            return invalid_input(
                "contribution.package_version",
                "envelope contribution is Graph Template T (qualified_id, version)",
                given=env.contribution.package_version,
                expected=binding.template_version,
            )
        template = self.templates.get_versioned(
            binding.template_qualified_id, binding.template_version
        )
        if template is None:
            return invalid_input(
                "template",
                "widget binds start of a registered Graph Template T",
                qualified_id=binding.template_qualified_id,
                version=binding.template_version,
            )
        compiled = self.compile_parent(
            owner=owner,
            template=template,
            goal=goal if goal is not None else f"widget-start {template.qualified_id}",
        )
        if is_refusal(compiled):
            return compiled
        started = WidgetStartedMission(
            binding=binding,
            envelope=env,
            owner=owner,
            mission=compiled.value.mission,
            task_graph=compiled.value.task_graph,
            handle=compiled.value.handle,
        )
        self._widget_jobs[token] = started.handle.job_id
        self._widget_starts[started.handle.job_id] = started
        return Ok(started)

    def dispose_widget(
        self,
        widget_id: object,
        *,
        cancel: bool = False,
        job_id: object | None = None,
    ) -> Result[WidgetStartBinding]:
        """Dispose the widget. The Mission's JobHandle is not cancelled."""
        if cancel or WIDGET_DISPOSE_CANCELS_MISSION:
            return policy_rejection(
                "widget",
                "disposing the widget does not cancel the Mission (FR-PG-28; "
                "SCN-0025 Then 1; UX-DR-PG-02)",
                cancels=WIDGET_DISPOSE_CANCELS_MISSION,
                owns_invoke=WIDGETS_OWN_INVOKE,
            )
        if not isinstance(widget_id, str) or widget_id.strip() == "":
            return invalid_input(
                "widget_id",
                "widget id is a non-empty string",
                given=repr(widget_id),
            )
        token = widget_id.strip()
        binding = self._widgets.get(token)
        if binding is None:
            return invalid_input(
                "widget_id",
                "dispose names a bound widget",
                given=token,
            )
        resolved_job = job_id if job_id is not None else self._widget_jobs.get(token)
        if resolved_job is not None:
            if not isinstance(resolved_job, str) or resolved_job.strip() == "":
                return invalid_input(
                    "job_id",
                    "job_id is a non-empty string",
                    given=repr(resolved_job),
                )
            detached = self.jobs.on_client_detach(resolved_job.strip(), event="ui_client_detach")
            if is_refusal(detached):
                return detached
            if detached.value.state in {
                JobHandleState.CANCELLED,
                JobHandleState.ABORTED,
                JobHandleState.FAILED,
                JobHandleState.DONE,
            }:
                return policy_rejection(
                    "job_handle",
                    "disposing the widget must not cancel the Mission",
                    state=detached.value.state.value,
                    cancels=WIDGET_DISPOSE_CANCELS_MISSION,
                )
        self._widgets.pop(token, None)
        return Ok(binding)

    def execute_widget_contribution_point(
        self,
        point: object,
        *,
        envelope: object | None = None,
        widget_id: object | None = None,
        owner: Quant | None = None,
    ) -> Result[WidgetStartedMission]:
        """Widget contribution execute is refused; host press requires envelope."""
        token = widget_contribution_point_name(point)
        if envelope is None:
            return refuse_widget_contribution_without_envelope(
                point=token if token is not None else point
            )
        return refuse_widget_owned_invoke(
            given=token if token is not None else point,
            envelope_present=True,
            widget_id=widget_id,
            owner_present=owner is not None,
        )

    def mint_composition_mode(self, mode: object) -> Result[str]:
        """Parent AD-10 four modes remain. Widget is not a fifth."""
        if isinstance(mode, str) and mode in PARENT_AD10_COMPOSITION_MODES:
            return Ok(mode)
        return refuse_fifth_composition_mode(mode)

    def fill_gap_0081_chrome(self) -> Result[None]:
        """Widget start must not fill GAP-0081 chrome."""
        return refuse_gap_0081_widget_chrome()

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
        enforced = self._enforce_call_depth(env)
        if is_refusal(enforced):
            return enforced
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
                graph_template_version=version,
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

    def _live_graph(self, graph_id: object) -> TaskGraph | None:
        if not isinstance(graph_id, str) or graph_id.strip() == "":
            return None
        return self._live.get(graph_id.strip())

    def _enforce_call_depth(self, env: InvocationEnvelope) -> Result[None]:
        ceiling = self.call_depth_ceiling()
        if is_refusal(ceiling):
            return ceiling
        cap = ceiling.value
        if cap is None:
            return Ok(None)
        if env.call_depth > cap:
            return invalid_input(
                "call_depth",
                "envelope call_depth exceeds the host-registered recursion ceiling",
                call_depth=env.call_depth,
                ceiling=cap,
                registry_key=HOST_NESTED_MISSION_CALL_DEPTH_CEILING_REGISTRY_KEY,
                code="INVALID_INPUT",
                gap_0108=False,
                reused_retry_row=CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW,
            )
        return Ok(None)

    def _resolve_widget_template(self, value: object) -> Result[GraphTemplate]:
        if isinstance(value, TaskGraph):
            return invalid_input(
                "template",
                "widget binds start of a Graph Template, not a live Task Graph",
                runtime_merge=False,
                owns_invoke=WIDGETS_OWN_INVOKE,
            )
        if isinstance(value, GraphTemplate):
            found = self.templates.get_versioned(value.qualified_id, value.version)
            if found is None:
                stored = self.register_template(value)
                if is_refusal(stored):
                    return stored
                found = self.templates.get_versioned(value.qualified_id, value.version)
            if found is None:
                return invalid_input(
                    "template",
                    "widget binds start of a registered Graph Template T",
                    qualified_id=value.qualified_id,
                    version=value.version,
                )
            return Ok(found)
        if isinstance(value, Mapping):
            body = cast("Mapping[object, object]", value)
            qualified = body.get("qualified_id")
            version = body.get("version")
            if isinstance(qualified, str) and isinstance(version, str):
                found = self.templates.get_versioned(qualified.strip(), version.strip())
                if found is None:
                    return invalid_input(
                        "template",
                        "widget binds start of a registered Graph Template T "
                        "(qualified_id, version)",
                        qualified_id=qualified,
                        version=version,
                    )
                return Ok(found)
        return invalid_input(
            "template",
            "widget binds start of Graph Template T (qualified_id, version)",
            given="mapping" if isinstance(value, Mapping) else type(value).__name__,
        )

    def _resolve_template(self, value: object, *, field: str) -> Result[GraphTemplate]:
        if isinstance(value, TaskGraph):
            return invalid_input(
                field,
                "include-at-author composes Graph Templates, not live Task Graphs",
                runtime_merge=False,
                code="INVALID_INPUT",
            )
        if isinstance(value, GraphTemplate):
            found = self.templates.get_versioned(value.qualified_id, value.version)
            if found is None:
                stored = self.register_template(value)
                if is_refusal(stored):
                    return stored
                found = self.templates.get_versioned(value.qualified_id, value.version)
            if found is None:
                return invalid_input(
                    field,
                    "Graph Template failed to register",
                    qualified_id=value.qualified_id,
                    version=value.version,
                    substituted=False,
                )
            return Ok(found)
        if isinstance(value, Mapping):
            body = cast("Mapping[object, object]", value)
            qualified = body.get("qualified_id")
            version = body.get("version")
            if isinstance(qualified, str) and isinstance(version, str):
                found = self.templates.get_versioned(qualified.strip(), version.strip())
                if found is None:
                    return invalid_input(
                        field,
                        "include-at-author names a registered Graph Template "
                        "(qualified_id, version)",
                        qualified_id=qualified,
                        version=version,
                        substituted=False,
                    )
                return Ok(found)
        shown = "mapping" if isinstance(value, Mapping) else "value"
        return invalid_input(
            field,
            "include-at-author names Graph Template (qualified_id, version)",
            given=shown,
            substituted=False,
        )

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
