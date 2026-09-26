"""L27 reference usage: widget binds start; dispose does not cancel."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.operations import public_operation_descriptors
from qma.core.vocabulary.enums import CallerKind, JobHandleState
from qma.daemon.taskgraph import (
    FIFTH_COMPOSITION_MODE_MINTED,
    GAP_0081_CHROME_FILLED,
    NESTED_MISSION_CALLEE_OP_ID,
    PARENT_AD10_COMPOSITION_MODES,
    WIDGET_DISPOSE_CANCELS_MISSION,
    WIDGET_START_IMPLEMENTED,
    WIDGETS_OWN_INVOKE,
    GraphTemplate,
    NestedMissionHost,
)
from qma.wire import compute_input_hash
from qmf.core import is_ok, is_refusal


def main() -> None:
    assert WIDGET_START_IMPLEMENTED is True
    assert WIDGETS_OWN_INVOKE is False
    assert WIDGET_DISPOSE_CANCELS_MISSION is False
    assert GAP_0081_CHROME_FILLED is False
    assert FIFTH_COMPOSITION_MODE_MINTED is False
    assert len(PARENT_AD10_COMPOSITION_MODES) == 4
    assert "widget" not in PARENT_AD10_COMPOSITION_MODES

    descriptor = next(
        item
        for item in public_operation_descriptors()
        if item.op_id == NESTED_MISSION_CALLEE_OP_ID and item.version == 1
    )
    hashed = compute_input_hash({"procedure_id": "research-corpus:t"}, descriptor=descriptor)
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
    template = GraphTemplate(
        qualified_id="research-corpus:t",
        version="1.0.0",
        nodes=({"id": "work-t", "kind": "task", "intent": "do T work"},),
    )
    host = NestedMissionHost()
    binding = host.bind_widget_start("widget:start-t", template)
    assert is_ok(binding)
    assert binding.value.bound_verb == "start"
    assert binding.value.owns_invoke is False
    fifth = host.mint_composition_mode("widget")
    assert is_refusal(fifth)
    bare = host.execute_widget_contribution_point("widget")
    assert is_refusal(bare)
    started = host.press_widget(
        "widget:start-t",
        envelope={
            "logical_invocation_id": "inv:widget-1",
            "attempt_id": 1,
            "op_id": NESTED_MISSION_CALLEE_OP_ID,
            "op_version": 1,
            "contribution": {
                "qualified_id": "research-corpus:t",
                "package_version": "1.0.0",
            },
            "instance_id": "inst:1",
            "config_revision": 4,
            "grant_id": "grant:t",
            "effect_class": "place-run",
            "idempotency_key": "idem:widget-1",
            "reconcile_policy": "query-then-decide",
            "input_hash": hashed.value,
            "call_depth": 0,
            "caller_kind": "user",
        },
        owner=owner,
    )
    assert is_ok(started)
    assert started.value.envelope.caller_kind is CallerKind.USER
    assert started.value.envelope.instance_id == "inst:1"
    job_id = started.value.handle.job_id
    disposed = host.dispose_widget("widget:start-t")
    assert is_ok(disposed)
    live = host.handle_for(job_id)
    assert live is not None
    assert live.state is JobHandleState.RUNNING
    assert is_refusal(host.fill_gap_0081_chrome())


if __name__ == "__main__":
    main()
