"""Story 63.1 — nested Mission invoke is start/query-state/cancel/await."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import cast

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.operations import public_operation_descriptors
from qma.core.refusals import NestedGrantUnionRefused
from qma.core.vocabulary.enums import CallerKind, JobHandleState, LifecycleVerb
from qma.daemon.taskgraph import (
    CALL_DEPTH_EXISTED_AT_INSPECT_SHA,
    FIFTH_COMPOSITION_MODE_MINTED,
    INCLUDE_AT_AUTHOR_IMPLEMENTED,
    LIFECYCLE_VERBS_EXISTED_AT_INSPECT_SHA,
    NESTED_MISSION_CALLEE_OP_ID,
    NESTED_MISSION_INSPECT_SHA,
    NESTED_MISSION_LIFECYCLE_VERBS,
    NESTED_MISSION_OCCUPANCY_EXISTED_AT_INSPECT_SHA,
    NESTED_MISSION_OCCUPANCY_FOLLOWS,
    PARENT_AD10_COMPOSITION_MODES,
    PARENT_LOGICAL_INVOCATION_ID_EXISTED_AT_INSPECT_SHA,
    RECURSION_CEILING_ROW_IMPLEMENTED,
    SECOND_VERB_SET_MINTED,
    GraphTemplate,
    NestedMissionHost,
    NestedMissionOccupancy,
    ParentMissionRun,
    claim_nested_connect_surface_absent_at_inspect_sha,
    claim_nested_mission_occupancy_at_inspect_sha,
)
from qma.wire import compute_input_hash
from qma.wire.invocation_envelope import INVOCATION_ENVELOPE_FIELDS_AT_INSPECT_SHA
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import Result

_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "nested_mission_usage.py"
_INPUT = {"procedure_id": "research-corpus:b"}


def _ok[T](result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _quant() -> Quant:
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )


def _descriptor():
    for item in public_operation_descriptors():
        if item.op_id == NESTED_MISSION_CALLEE_OP_ID and item.version == 1:
            return item
    raise AssertionError("qma.procedure.start v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _template_a() -> GraphTemplate:
    return GraphTemplate(
        qualified_id="research-corpus:a",
        version="1.0.0",
        nodes=(
            {
                "id": "start-b",
                "kind": "task",
                "intent": "start nested B",
                "starts": {"qualified_id": "research-corpus:b", "version": "1.0.0"},
            },
        ),
        edges=(),
    )


def _template_b() -> GraphTemplate:
    return GraphTemplate(
        qualified_id="research-corpus:b",
        version="1.0.0",
        nodes=({"id": "work-b", "kind": "task", "intent": "do B work"},),
        edges=(),
    )


def _envelope(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "logical_invocation_id": "inv:nested-1",
        "attempt_id": 1,
        "op_id": NESTED_MISSION_CALLEE_OP_ID,
        "op_version": 1,
        "contribution": {
            "qualified_id": "research-corpus:b",
            "package_version": "1.0.0",
        },
        "instance_id": "inst:1",
        "config_revision": 4,
        "grant_id": "grant:b",
        "effect_class": "place-run",
        "idempotency_key": "idem:nested-1",
        "reconcile_policy": "query-then-decide",
        "input_hash": _hash(),
        "call_depth": 1,
        "caller_kind": "workflow",
        "parent_logical_invocation_id": "inv:parent-a",
    }
    payload.update(overrides)
    return payload


def _world() -> tuple[NestedMissionHost, ParentMissionRun, NestedMissionOccupancy]:
    host = NestedMissionHost()
    _ok(host.register_template(_template_a()))
    _ok(host.register_template(_template_b()))
    parent = _ok(
        host.compile_parent(
            owner=_quant(),
            template=_template_a(),
            goal="run A then nested B",
        )
    )
    nested = _ok(
        host.invoke(
            "start",
            envelope=_envelope(),
            parent_graph_id=parent.task_graph.id,
            node_id="start-b",
            caller_grant_ids=("grant:a",),
            callee_grant_ids=("grant:b",),
        )
    )
    assert isinstance(nested, NestedMissionOccupancy)
    return host, parent, nested


def test_inspect_sha_honesty_occupancy_absent_connect_present() -> None:
    assert NESTED_MISSION_INSPECT_SHA == "34c148b"
    assert NESTED_MISSION_OCCUPANCY_EXISTED_AT_INSPECT_SHA is False
    assert CALL_DEPTH_EXISTED_AT_INSPECT_SHA is True
    assert PARENT_LOGICAL_INVOCATION_ID_EXISTED_AT_INSPECT_SHA is True
    assert LIFECYCLE_VERBS_EXISTED_AT_INSPECT_SHA is True
    assert "call_depth" in INVOCATION_ENVELOPE_FIELDS_AT_INSPECT_SHA
    assert "parent_logical_invocation_id" in INVOCATION_ENVELOPE_FIELDS_AT_INSPECT_SHA
    assert {
        "start",
        "query-state",
        "cancel",
        "await",
    } == NESTED_MISSION_LIFECYCLE_VERBS
    descriptor = _descriptor()
    assert {verb.value for verb in descriptor.lifecycle_verbs} == {
        "start",
        "query-state",
        "cancel",
        "await",
    }
    assert is_refusal(claim_nested_mission_occupancy_at_inspect_sha(True))
    assert _ok(claim_nested_mission_occupancy_at_inspect_sha(False)) is False
    assert is_refusal(claim_nested_connect_surface_absent_at_inspect_sha(True))
    assert _ok(claim_nested_connect_surface_absent_at_inspect_sha(False)) is False
    assert SECOND_VERB_SET_MINTED is False
    assert FIFTH_COMPOSITION_MODE_MINTED is False
    assert INCLUDE_AT_AUTHOR_IMPLEMENTED is False
    assert RECURSION_CEILING_ROW_IMPLEMENTED is False
    assert len(PARENT_AD10_COMPOSITION_MODES) == 4


def test_nested_start_is_one_mission_one_graph_one_job_handle() -> None:
    host, parent, nested = _world()
    assert nested.envelope.caller_kind is CallerKind.WORKFLOW
    assert nested.envelope.instance_id == "inst:1"
    assert nested.verb is LifecycleVerb.START
    assert nested.callee_qualified_id == "research-corpus:b"
    assert nested.callee_version == "1.0.0"
    assert nested.task_graph.id != parent.task_graph.id
    assert nested.mission.id != parent.mission.id
    assert nested.handle.job_id != parent.handle.job_id
    assert nested.handle.state is JobHandleState.RUNNING
    assert {node.id for node in nested.task_graph.nodes} == {"work-b"}
    assert {node.id for node in parent.task_graph.nodes} == {"start-b"}
    assert "work-b" not in {node.id for node in parent.task_graph.nodes}
    occupancy = dict(host.graphs.occupancy_for(nested.task_graph.id))
    slots = cast("dict[str, object]", occupancy["slots"])
    slot = cast("dict[str, object]", slots[nested.handle.job_id])
    assert slot["follows"] == NESTED_MISSION_OCCUPANCY_FOLLOWS == "job_handle"
    assert slot["spliced"] is False
    pointer = dict(host.graphs.occupancy_for(parent.task_graph.id))
    parent_slots = cast("dict[str, object]", pointer["slots"])
    start_slot = cast("dict[str, object]", parent_slots["start-b"])
    assert start_slot["nested_job_id"] == nested.handle.job_id
    assert start_slot["spliced"] is False


def test_lifecycle_verbs_are_existing_start_query_cancel_await() -> None:
    host, _parent, nested = _world()
    queried = _ok(
        host.invoke(
            "query-state",
            envelope=_envelope(idempotency_key="idem:query"),
            job_id=nested.handle.job_id,
        )
    )
    assert isinstance(queried, NestedMissionOccupancy)
    assert queried.handle.state is JobHandleState.RUNNING
    assert queried.handle.job_id == nested.handle.job_id
    waited = _ok(
        host.invoke(
            "await",
            envelope=_envelope(idempotency_key="idem:await"),
            job_id=nested.handle.job_id,
        )
    )
    assert isinstance(waited, NestedMissionOccupancy)
    assert waited.verb is LifecycleVerb.AWAIT
    assert waited.handle.job_id == nested.handle.job_id
    paused = host.invoke(
        "pause",
        envelope=_envelope(idempotency_key="idem:pause"),
        job_id=nested.handle.job_id,
    )
    assert is_refusal(paused)
    assert paused.context["second_verb_set_minted"] is False
    missing = host.invoke(
        "start",
        envelope=_envelope(instance_id="", idempotency_key="idem:missing"),
        parent_graph_id=nested.parent_graph_id,
        node_id="start-b",
    )
    assert is_refusal(missing)
    widget = host.invoke(
        "start",
        envelope=_envelope(caller_kind="user", idempotency_key="idem:user"),
        parent_graph_id=nested.parent_graph_id,
        node_id="start-b",
    )
    assert is_refusal(widget)
    assert widget.context["field"] == "caller_kind"


def test_occupancy_and_cancel_follow_the_nested_job_handle() -> None:
    host, parent, nested = _world()
    cancelled = _ok(
        host.invoke(
            "cancel",
            envelope=_envelope(idempotency_key="idem:cancel"),
            job_id=nested.handle.job_id,
        )
    )
    assert isinstance(cancelled, NestedMissionOccupancy)
    assert cancelled.handle.state is JobHandleState.CANCELLED
    live = host.handle_for(nested.handle.job_id)
    assert live is not None
    assert live.state is JobHandleState.CANCELLED
    parent_live = host.jobs.handle_for(parent.handle.job_id)
    assert parent_live is not None
    assert parent_live.state is JobHandleState.RUNNING
    occupancy = host.occupancy_for(nested.handle.job_id)
    assert occupancy is not None
    assert occupancy.handle.job_id == nested.handle.job_id


def test_nested_invoke_does_not_union_grants() -> None:
    host = NestedMissionHost()
    _ok(host.register_template(_template_a()))
    _ok(host.register_template(_template_b()))
    parent = _ok(
        host.compile_parent(
            owner=_quant(),
            template=_template_a(),
            goal="run A then nested B",
        )
    )
    nested = _ok(
        host.invoke(
            "start",
            envelope=_envelope(),
            parent_graph_id=parent.task_graph.id,
            node_id="start-b",
            caller_grant_ids=("grant:a",),
            callee_grant_ids=("grant:b",),
        )
    )
    assert isinstance(nested, NestedMissionOccupancy)
    assert nested.grant_ids == ("grant:b",)
    assert "grant:a" not in nested.grant_ids
    unioned = host.invoke(
        "start",
        envelope=_envelope(idempotency_key="idem:union"),
        parent_graph_id=parent.task_graph.id,
        node_id="start-b",
        caller_grant_ids=("grant:a",),
        callee_grant_ids=("grant:b",),
        union_grants=True,
    )
    assert is_refusal(unioned)
    assert isinstance(unioned, NestedGrantUnionRefused)
    leaked = host.invoke(
        "start",
        envelope=_envelope(idempotency_key="idem:leak", grant_id="grant:a"),
        parent_graph_id=parent.task_graph.id,
        node_id="start-b",
        caller_grant_ids=("grant:a",),
        callee_grant_ids=("grant:b",),
    )
    assert is_refusal(leaked)
    assert isinstance(leaked, NestedGrantUnionRefused)


def test_crash_of_a_does_not_splice_b_nodes_into_a() -> None:
    host, parent, nested = _world()
    parent_nodes = {node.id for node in parent.task_graph.nodes}
    child_nodes = {node.id for node in nested.task_graph.nodes}
    assert child_nodes.isdisjoint(parent_nodes)
    crashed = host.crash_parent(parent.task_graph.id)
    assert is_ok(crashed)
    assert host.is_live(parent.task_graph.id) is False
    assert host.is_live(nested.task_graph.id) is True
    child_handle = host.handle_for(nested.handle.job_id)
    assert child_handle is not None
    assert child_handle.state is JobHandleState.RUNNING
    recovered = _ok(host.recover_parent(parent.task_graph.id))
    assert {node.id for node in recovered.nodes} == parent_nodes
    assert "work-b" not in {node.id for node in recovered.nodes}
    child = _ok(host.graphs.get(nested.task_graph.id))
    assert {node.id for node in child.nodes} == child_nodes
    spliced = host.splice_child_into_parent(
        parent_graph_id=parent.task_graph.id,
        child_job_id=nested.handle.job_id,
    )
    assert is_refusal(spliced)
    assert spliced.context["spliced"] is False


def test_nested_mission_usage_example_runs() -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    assert namespace["NESTED_MISSION_OCCUPANCY_EXISTED_AT_INSPECT_SHA"] is False
    assert namespace["CALL_DEPTH_EXISTED_AT_INSPECT_SHA"] is True
