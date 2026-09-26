"""L27 reference usage: nested Mission invoke is one JobHandle occupancy."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.operations import public_operation_descriptors
from qma.core.vocabulary.enums import JobHandleState, LifecycleVerb
from qma.daemon.journal.variables import (
    HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY,
    HOST_RETRY_ATTEMPT_CEILING_KEY,
)
from qma.daemon.taskgraph import (
    CALL_DEPTH_EXISTED_AT_INSPECT_SHA,
    CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW,
    FIFTH_COMPOSITION_MODE_MINTED,
    INCLUDE_AT_AUTHOR_IMPLEMENTED,
    LIFECYCLE_VERBS_EXISTED_AT_INSPECT_SHA,
    NESTED_MISSION_CALLEE_OP_ID,
    NESTED_MISSION_INSPECT_SHA,
    NESTED_MISSION_OCCUPANCY_EXISTED_AT_INSPECT_SHA,
    PARENT_LOGICAL_INVOCATION_ID_EXISTED_AT_INSPECT_SHA,
    RECURSION_CEILING_ROW_IMPLEMENTED,
    SECOND_VERB_SET_MINTED,
    GraphTemplate,
    NestedMissionHost,
    NestedMissionOccupancy,
    bind_call_depth_ceiling_key,
    claim_nested_connect_surface_absent_at_inspect_sha,
    claim_nested_mission_occupancy_at_inspect_sha,
)
from qma.wire import compute_input_hash
from qmf.core import is_ok, is_refusal


def main() -> None:
    assert NESTED_MISSION_OCCUPANCY_EXISTED_AT_INSPECT_SHA is False
    assert CALL_DEPTH_EXISTED_AT_INSPECT_SHA is True
    assert PARENT_LOGICAL_INVOCATION_ID_EXISTED_AT_INSPECT_SHA is True
    assert LIFECYCLE_VERBS_EXISTED_AT_INSPECT_SHA is True
    assert NESTED_MISSION_INSPECT_SHA == "34c148b"
    assert SECOND_VERB_SET_MINTED is False
    assert FIFTH_COMPOSITION_MODE_MINTED is False
    assert INCLUDE_AT_AUTHOR_IMPLEMENTED is True
    assert RECURSION_CEILING_ROW_IMPLEMENTED is True
    assert CALL_DEPTH_REUSES_RETRY_REGISTRY_ROW is False
    assert HOST_NESTED_MISSION_CALL_DEPTH_CEILING_KEY != HOST_RETRY_ATTEMPT_CEILING_KEY
    assert is_refusal(bind_call_depth_ceiling_key(HOST_RETRY_ATTEMPT_CEILING_KEY))
    assert is_refusal(claim_nested_mission_occupancy_at_inspect_sha(True))
    assert is_ok(claim_nested_mission_occupancy_at_inspect_sha(False))
    assert is_refusal(claim_nested_connect_surface_absent_at_inspect_sha(True))

    descriptor = next(
        item
        for item in public_operation_descriptors()
        if item.op_id == NESTED_MISSION_CALLEE_OP_ID and item.version == 1
    )
    hashed = compute_input_hash({"procedure_id": "research-corpus:b"}, descriptor=descriptor)
    assert is_ok(hashed)
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )
    host = NestedMissionHost()
    template_a = GraphTemplate(
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
    )
    template_b = GraphTemplate(
        qualified_id="research-corpus:b",
        version="1.0.0",
        nodes=({"id": "work-b", "kind": "task", "intent": "do B work"},),
    )
    assert is_ok(host.register_template(template_a))
    assert is_ok(host.register_template(template_b))
    parent = host.compile_parent(owner=owner, template=template_a, goal="run A then nested B")
    assert is_ok(parent)
    nested = host.invoke(
        LifecycleVerb.START,
        envelope={
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
            "input_hash": hashed.value,
            "call_depth": 1,
            "caller_kind": "workflow",
            "parent_logical_invocation_id": "inv:parent-a",
        },
        parent_graph_id=parent.value.task_graph.id,
        node_id="start-b",
        caller_grant_ids=("grant:a",),
        callee_grant_ids=("grant:b",),
    )
    assert is_ok(nested)
    occupancy = nested.value
    assert isinstance(occupancy, NestedMissionOccupancy)
    assert occupancy.handle.job_id != parent.value.handle.job_id
    assert occupancy.task_graph.id != parent.value.task_graph.id
    assert {node.id for node in occupancy.task_graph.nodes} == {"work-b"}
    assert is_ok(host.crash_parent(parent.value.task_graph.id))
    recovered = host.recover_parent(parent.value.task_graph.id)
    assert is_ok(recovered)
    assert "work-b" not in {node.id for node in recovered.value.nodes}
    spliced = host.splice_child_into_parent(
        parent_graph_id=parent.value.task_graph.id,
        child_job_id=occupancy.handle.job_id,
    )
    assert is_refusal(spliced)
    cancelled = host.invoke(
        "cancel",
        envelope={
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
            "idempotency_key": "idem:cancel",
            "reconcile_policy": "query-then-decide",
            "input_hash": hashed.value,
            "call_depth": 1,
            "caller_kind": "workflow",
            "parent_logical_invocation_id": "inv:parent-a",
        },
        job_id=occupancy.handle.job_id,
    )
    assert is_ok(cancelled)
    assert isinstance(cancelled.value, NestedMissionOccupancy)
    assert cancelled.value.handle.state is JobHandleState.CANCELLED
    included = host.include_at_author(template_a, template_b, new_version="1.1.0")
    assert is_ok(included)
    assert included.value.qualified_id == "research-corpus:a"
    assert included.value.version == "1.1.0"
    assert "work-b" in {node["id"] for node in included.value.nodes}
    original = host.templates.get_versioned("research-corpus:a", "1.0.0")
    assert original is not None
    assert {node["id"] for node in original.nodes} == {"start-b"}
    merged = host.merge_live_task_graphs(
        parent.value.task_graph.id,
        occupancy.task_graph.id,
        substitute_instance_id="inst:other",
        substitute_version="9.9.9",
        substitute_account="acct:other",
    )
    assert is_refusal(merged)
    assert merged.context["merged"] is False
    assert merged.context["substituted"] is False
    deep = NestedMissionHost(injected_call_depth_ceiling=1)
    assert is_ok(deep.register_template(template_a))
    assert is_ok(deep.register_template(template_b))
    deep_parent = deep.compile_parent(owner=owner, template=template_a, goal="run A then nested B")
    assert is_ok(deep_parent)
    over = deep.invoke(
        LifecycleVerb.START,
        envelope={
            "logical_invocation_id": "inv:nested-deep",
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
            "idempotency_key": "idem:deep",
            "reconcile_policy": "query-then-decide",
            "input_hash": hashed.value,
            "call_depth": 2,
            "caller_kind": "workflow",
            "parent_logical_invocation_id": "inv:parent-a",
        },
        parent_graph_id=deep_parent.value.task_graph.id,
        node_id="start-b",
        caller_grant_ids=("grant:a",),
        callee_grant_ids=("grant:b",),
    )
    assert is_refusal(over)
    assert over.context["field"] == "call_depth"


if __name__ == "__main__":
    main()
