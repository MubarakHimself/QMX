"""Story 43.9 — template-governed Agent-authored Mission hooks (FR-Q35; AD-11)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from qma.core.plugins.hooks import HookEvent, HookResult, HookSource, build_hook_result
from qma.core.vocabulary.enums import HookResultDecision
from qma.daemon.hooks import (
    AGENT_AUTHORED_FORBIDDEN_RESULT_FIELDS,
    AGENT_AUTHORED_WIRE_QUERY,
    HOOK_REGISTERED_JOURNAL_EVENT,
    HOOK_REGISTRATIONS_FOLD,
    AgentAuthoredHookRegistrar,
    HookRegistry,
    assert_agent_authored_hook_result,
    intersect_permissions_exact,
    validate_agent_authored_template,
)
from qma.wire import WireQuery, parse_wire_type, validate_family_payload
from qmf.core import is_ok, is_refusal


def _observe(_event: HookEvent) -> HookResult:
    return build_hook_result(HookResultDecision.OBSERVE, reason="mission_watch")


def _deny(_event: HookEvent) -> HookResult:
    return build_hook_result(HookResultDecision.DENY, reason="mission_block")


def _registrar() -> AgentAuthoredHookRegistrar:
    return AgentAuthoredHookRegistrar(registry=HookRegistry())


def _approve_basic(registrar: AgentAuthoredHookRegistrar, template_id: str = "tpl-observe") -> None:
    ok = registrar.approve_template(
        {
            "template_id": template_id,
            "event": "before_tool",
            "decisions": ["observe", "deny"],
            "permissions": ["tool.read"],
            "schema_version": "1",
        }
    )
    assert is_ok(ok)


def test_forbidden_result_fields_closed_at_five() -> None:
    assert frozenset(
        {
            "updated_input",
            "updated_output",
            "injected_context",
            "ledger_entry",
            "verifier_ref",
        }
    ) == AGENT_AUTHORED_FORBIDDEN_RESULT_FIELDS


def test_template_schema_validation_and_observe_or_deny_only() -> None:
    good = validate_agent_authored_template(
        {
            "template_id": "tpl-1",
            "event": "before_memory_write",
            "decisions": ["deny"],
            "permissions": ["memory.read"],
        }
    )
    assert is_ok(good)

    allow_illegal = validate_agent_authored_template(
        {
            "template_id": "tpl-bad",
            "event": "before_tool",
            "decisions": ["allow"],
            "permissions": [],
        }
    )
    assert is_refusal(allow_illegal)
    assert allow_illegal.context["field"] == "decisions"

    with_fields = validate_agent_authored_template(
        {
            "template_id": "tpl-fields",
            "event": "before_tool",
            "decisions": ["observe"],
            "fields": ["updated_input"],
        }
    )
    assert is_refusal(with_fields)
    assert with_fields.context["field"] == "fields"


def test_accepts_only_approved_mission_observe_or_deny_template() -> None:
    registrar = _registrar()
    _approve_basic(registrar)
    opened = registrar.open_mission("mission-a", permissions=["tool.read", "tool.list"])
    assert is_ok(opened)

    accepted = registrar.register(
        mission_id="mission-a",
        template_id="tpl-observe",
        handler=_observe,
        permissions=["tool.read"],
        correlation_id="corr-1",
    )
    assert is_ok(accepted)
    assert accepted.value.source is HookSource.MISSION
    assert accepted.value.durable is False
    assert accepted.value.correlation_id == "corr-1"

    untemplated = registrar.register(
        mission_id="mission-a",
        template_id=None,
        handler=_observe,
    )
    assert is_refusal(untemplated)
    assert untemplated.context["field"] == "template_id"

    unknown = registrar.register(
        mission_id="mission-a",
        template_id="missing-tpl",
        handler=_observe,
    )
    assert is_refusal(unknown)


def test_refuses_source_above_mission_and_outside_mission() -> None:
    registrar = _registrar()
    _approve_basic(registrar)
    assert is_ok(registrar.open_mission("mission-a", permissions=["tool.read"]))

    above = registrar.register(
        mission_id="mission-a",
        template_id="tpl-observe",
        handler=_observe,
        source=HookSource.DESK,
        permissions=["tool.read"],
    )
    assert is_refusal(above)
    assert above.context["field"] == "source"

    outside = registrar.register(
        mission_id="mission-missing",
        template_id="tpl-observe",
        handler=_observe,
        permissions=["tool.read"],
    )
    assert is_refusal(outside)
    assert outside.context["field"] == "mission_id"


def test_permissions_exact_intersection_refuses_silent_narrow() -> None:
    exact = intersect_permissions_exact(["a", "b"], ["a", "b", "c"])
    assert is_ok(exact)
    assert exact.value == frozenset({"a", "b"})

    narrow = intersect_permissions_exact(["a", "extra"], ["a", "b"])
    assert is_refusal(narrow)
    assert "extra" in cast(Sequence[object], narrow.context["given"])

    registrar = _registrar()
    _approve_basic(registrar)
    assert is_ok(registrar.open_mission("mission-a", permissions=["tool.read"]))

    refused = registrar.register(
        mission_id="mission-a",
        template_id="tpl-observe",
        handler=_observe,
        permissions=["tool.read", "tool.write"],
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "permissions"


def test_agent_authored_hook_result_only_decision_and_reason() -> None:
    ok = assert_agent_authored_hook_result(
        build_hook_result(HookResultDecision.DENY, reason="blocked")
    )
    assert is_ok(ok)

    # updated_input/output ride allow only at build time; construct HookResult
    # directly so the AD-11 field reject list is what we assert.
    cases: list[tuple[str, HookResult]] = [
        (
            "updated_input",
            HookResult(decision=HookResultDecision.DENY, reason="x", updated_input={"x": 1}),
        ),
        (
            "updated_output",
            HookResult(decision=HookResultDecision.DENY, reason="x", updated_output={"y": 2}),
        ),
        (
            "injected_context",
            build_hook_result(
                HookResultDecision.OBSERVE, reason="x", injected_context={"z": 3}
            ),
        ),
        (
            "ledger_entry",
            build_hook_result(
                HookResultDecision.OBSERVE, reason="x", ledger_entry={"kind": "note"}
            ),
        ),
        (
            "verifier_ref",
            build_hook_result(
                HookResultDecision.OBSERVE, reason="x", verifier_ref="fp1:sha256:ab"
            ),
        ),
    ]
    for field, result in cases:
        bad = assert_agent_authored_hook_result(result)
        assert is_refusal(bad), field
        assert field in cast(Sequence[object], bad.context["given"])


def test_registration_passes_before_hook_register_journals_and_folds() -> None:
    registrar = _registrar()
    _approve_basic(registrar)
    assert is_ok(registrar.open_mission("mission-a", permissions=["tool.read"]))

    registered = registrar.register(
        mission_id="mission-a",
        template_id="tpl-observe",
        handler=_deny,
        permissions=["tool.read"],
        correlation_id="corr-reg-1",
        registration_id="reg-1",
    )
    assert is_ok(registered)

    journal = registrar.journal_events
    assert any(
        row["event"] == HOOK_REGISTERED_JOURNAL_EVENT
        and row["correlation_id"] == "corr-reg-1"
        and row["registration_id"] == "reg-1"
        for row in journal
    )

    folded = registrar.folded_under_mission("mission-a")
    assert len(folded) == 1
    assert folded[0].registration_id == "reg-1"
    assert folded[0].fold == HOOK_REGISTRATIONS_FOLD


def test_named_wire_query_exposes_registration() -> None:
    assert AGENT_AUTHORED_WIRE_QUERY == "list_mission_hooks"
    assert parse_wire_type("list_mission_hooks") == WireQuery.LIST_MISSION_HOOKS.value
    assert is_ok(validate_family_payload("list_mission_hooks", {"mission_id": "mission-a"}))

    registrar = _registrar()
    _approve_basic(registrar)
    assert is_ok(registrar.open_mission("mission-a", permissions=["tool.read"]))
    assert is_ok(
        registrar.register(
            mission_id="mission-a",
            template_id="tpl-observe",
            handler=_observe,
            permissions=["tool.read"],
            correlation_id="corr-q",
            registration_id="reg-q",
        )
    )

    answered = registrar.answer_wire_query(
        WireQuery.LIST_MISSION_HOOKS,
        args={"mission_id": "mission-a"},
    )
    assert is_ok(answered)
    assert answered.value["query"] == "list_mission_hooks"
    assert answered.value["count"] == 1
    hooks = cast(Sequence[Mapping[str, object]], answered.value["hooks"])
    assert hooks[0]["registration_id"] == "reg-q"
    assert answered.value["fold"] == HOOK_REGISTRATIONS_FOLD


def test_mission_end_invokes_disposer_and_removes_hook() -> None:
    registrar = _registrar()
    _approve_basic(registrar)
    assert is_ok(registrar.open_mission("mission-a", permissions=["tool.read"]))
    assert is_ok(
        registrar.register(
            mission_id="mission-a",
            template_id="tpl-observe",
            handler=_observe,
            permissions=["tool.read"],
            correlation_id="corr-end",
            registration_id="reg-end",
        )
    )
    listed_before = registrar.list_mission_hooks("mission-a")
    assert is_ok(listed_before)
    assert listed_before.value["count"] == 1

    ended = registrar.end_mission("mission-a")
    assert is_ok(ended)
    assert ended.value["hooks_remaining"] == 0
    removed = cast(Sequence[object], ended.value["removed_registration_ids"])
    assert "reg-end" in removed
    listed_after = registrar.list_mission_hooks("mission-a")
    assert is_ok(listed_after)
    assert listed_after.value["count"] == 0
    assert registrar.folded_under_mission("mission-a") == ()

    # Handler is gone — dispatch yields empty-handler allow, not the agent observe.
    dispatched = registrar.registry.dispatch(
        "before_tool",
        source=HookSource.MISSION,
        scope_path=[
            {"kind": "desk", "id": "research"},
            {"kind": "quant", "id": "lead"},
            {"kind": "mission", "id": "mission-a"},
        ],
    )
    assert is_ok(dispatched)
    assert dispatched.value.reason == "empty_handler"


def test_refuses_durable_and_privilege_escalation() -> None:
    registrar = _registrar()
    _approve_basic(registrar)
    assert is_ok(registrar.open_mission("mission-a", permissions=["tool.read", "register_hook"]))

    durable = registrar.register(
        mission_id="mission-a",
        template_id="tpl-observe",
        handler=_observe,
        permissions=["tool.read"],
        durable=True,
    )
    assert is_refusal(durable)
    assert durable.context["field"] == "durable"

    escalate_flag = registrar.register(
        mission_id="mission-a",
        template_id="tpl-observe",
        handler=_observe,
        permissions=["tool.read"],
        escalate=True,
    )
    assert is_refusal(escalate_flag)
    assert escalate_flag.context["field"] == "privilege"

    escalate_perm = registrar.register(
        mission_id="mission-a",
        template_id="tpl-observe",
        handler=_observe,
        permissions=["register_hook"],
    )
    assert is_refusal(escalate_perm)
    assert escalate_perm.context["field"] == "privilege"
