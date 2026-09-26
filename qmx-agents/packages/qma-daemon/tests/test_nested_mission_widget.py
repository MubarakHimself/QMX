"""Story 63.3 — widget binds start; dispose does not cancel."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.operations import public_operation_descriptors
from qma.core.ports.extensibility import register_ui_widget_contribution
from qma.core.vocabulary.enums import CallerKind, JobHandleState, LifecycleVerb
from qma.daemon.taskgraph import (
    FIFTH_COMPOSITION_MODE_MINTED,
    GAP_0081_CHROME_FILLED,
    NESTED_MISSION_CALLEE_OP_ID,
    PARENT_AD10_COMPOSITION_MODES,
    WIDGET_DISPOSE_CANCELS_MISSION,
    WIDGET_START_CALLER_KINDS,
    WIDGET_START_IMPLEMENTED,
    WIDGET_START_VERB,
    WIDGETS_OWN_INVOKE,
    GraphTemplate,
    NestedMissionHost,
    WidgetStartBinding,
    WidgetStartedMission,
)
from qma.wire import compute_input_hash
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import Result

_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "nested_mission_widget_usage.py"
_INPUT = {"procedure_id": "research-corpus:t"}


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


def _template_t() -> GraphTemplate:
    return GraphTemplate(
        qualified_id="research-corpus:t",
        version="1.0.0",
        nodes=({"id": "work-t", "kind": "task", "intent": "do T work"},),
        edges=(),
    )


def _envelope(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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
        "input_hash": _hash(),
        "call_depth": 0,
        "caller_kind": "user",
    }
    payload.update(overrides)
    return payload


def _bound_host() -> tuple[NestedMissionHost, WidgetStartBinding]:
    host = NestedMissionHost()
    binding = _ok(host.bind_widget_start("widget:start-t", _template_t()))
    return host, binding


def test_widget_binds_start_not_a_fifth_composition_mode() -> None:
    assert WIDGET_START_IMPLEMENTED is True
    assert WIDGETS_OWN_INVOKE is False
    assert WIDGET_DISPOSE_CANCELS_MISSION is False
    assert GAP_0081_CHROME_FILLED is False
    assert FIFTH_COMPOSITION_MODE_MINTED is False
    assert WIDGET_START_VERB == "start" == LifecycleVerb.START.value
    assert len(PARENT_AD10_COMPOSITION_MODES) == 4
    assert "widget" not in PARENT_AD10_COMPOSITION_MODES
    assert frozenset({CallerKind.USER, CallerKind.AGENT}) == WIDGET_START_CALLER_KINDS
    host, binding = _bound_host()
    assert binding.bound_verb == "start"
    assert binding.owns_invoke is False
    assert binding.is_contribution_point is False
    assert binding.gap_0081_chrome is False
    assert binding.composition_mode in PARENT_AD10_COMPOSITION_MODES
    assert host.widgets_own_invoke is False
    assert host.fifth_composition_mode_minted is False
    assert host.gap_0081_chrome_filled is False
    fifth = host.mint_composition_mode("widget")
    assert is_refusal(fifth)
    assert fifth.context["fifth_composition_mode_minted"] is False
    for mode in PARENT_AD10_COMPOSITION_MODES:
        assert _ok(host.mint_composition_mode(mode)) == mode
    owned = host.bind_widget_start(
        "widget:owns",
        _template_t(),
        owns_invoke=True,
    )
    assert is_refusal(owned)
    assert owned.context["owns_invoke"] is False
    cancel_bind = host.bind_widget_start(
        "widget:cancel",
        _template_t(),
        verb="cancel",
    )
    assert is_refusal(cancel_bind)
    chrome = host.fill_gap_0081_chrome()
    assert is_refusal(chrome)
    assert chrome.context["gap_0081_chrome_filled"] is False
    ui = register_ui_widget_contribution(plugin_id="research-corpus", local_id="panel")
    assert is_refusal(ui)


def test_widget_press_is_enveloped_user_or_agent_start() -> None:
    host, binding = _bound_host()
    owner = _quant()
    started = _ok(host.press_widget("widget:start-t", envelope=_envelope(), owner=owner))
    assert isinstance(started, WidgetStartedMission)
    assert started.envelope.caller_kind is CallerKind.USER
    assert started.envelope.instance_id == "inst:1"
    assert started.binding.widget_id == binding.widget_id
    assert started.mission.id
    assert started.handle.state is JobHandleState.RUNNING
    assert {node.id for node in started.task_graph.nodes} == {"work-t"}
    agent = NestedMissionHost()
    _ok(agent.bind_widget_start("widget:start-t", _template_t()))
    agent_started = _ok(
        agent.press_widget(
            "widget:start-t",
            envelope=_envelope(caller_kind="agent", idempotency_key="idem:agent"),
            owner=owner,
        )
    )
    assert agent_started.envelope.caller_kind is CallerKind.AGENT
    assert agent_started.envelope.instance_id == "inst:1"


def test_widget_press_requires_envelope_and_instance_id() -> None:
    host, _binding = _bound_host()
    owner = _quant()
    missing = host.press_widget("widget:start-t", envelope=None, owner=owner)
    assert is_refusal(missing)
    assert missing.context["envelope_present"] is False
    assert missing.context["field"] == "invocation_envelope"
    blank = host.press_widget(
        "widget:start-t",
        envelope=_envelope(instance_id=""),
        owner=owner,
    )
    assert is_refusal(blank)
    widget_kind = host.press_widget(
        "widget:start-t",
        envelope=_envelope(caller_kind="widget"),
        owner=owner,
    )
    assert is_refusal(widget_kind)
    assert widget_kind.context["field"] == "caller_kind"
    nested_kind = host.press_widget(
        "widget:start-t",
        envelope=_envelope(
            caller_kind="workflow",
            call_depth=1,
            parent_logical_invocation_id="inv:parent",
            idempotency_key="idem:workflow",
        ),
        owner=owner,
    )
    assert is_refusal(nested_kind)
    assert nested_kind.context["field"] == "caller_kind"


def test_dispose_does_not_cancel_the_mission() -> None:
    host, _binding = _bound_host()
    started = _ok(host.press_widget("widget:start-t", envelope=_envelope(), owner=_quant()))
    job_id = started.handle.job_id
    disposed = _ok(host.dispose_widget("widget:start-t"))
    assert disposed.owns_invoke is False
    assert host.widget_binding("widget:start-t") is None
    live = host.handle_for(job_id)
    assert live is not None
    assert live.state is JobHandleState.RUNNING
    assert live.state is not JobHandleState.CANCELLED
    remembered = host.widget_start_for("widget:start-t")
    assert remembered is not None
    assert remembered.handle.job_id == job_id
    cancelled_dispose = host.dispose_widget("widget:start-t", cancel=True, job_id=job_id)
    assert is_refusal(cancelled_dispose)
    still = host.jobs.handle_for(job_id)
    assert still is not None
    assert still.state is JobHandleState.RUNNING
    cancelled = _ok(host.jobs.cancel(job_id))
    assert cancelled.state is JobHandleState.CANCELLED


def test_widget_contribution_without_envelope_is_refused() -> None:
    host, _binding = _bound_host()
    for point in ("widget", "ui_widget", "ui_view"):
        refused = host.execute_widget_contribution_point(point)
        assert is_refusal(refused)
        assert refused.context["envelope_present"] is False
        assert refused.context["owns_invoke"] is False
    with_envelope = host.execute_widget_contribution_point(
        "widget",
        envelope=_envelope(),
        widget_id="widget:start-t",
        owner=_quant(),
    )
    assert is_refusal(with_envelope)
    assert with_envelope.context["owns_invoke"] is False
    assert with_envelope.context["envelope_present"] is True


def test_nested_mission_widget_usage_example_runs() -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    assert namespace["WIDGETS_OWN_INVOKE"] is False
    assert namespace["WIDGET_DISPOSE_CANCELS_MISSION"] is False
    assert namespace["GAP_0081_CHROME_FILLED"] is False
