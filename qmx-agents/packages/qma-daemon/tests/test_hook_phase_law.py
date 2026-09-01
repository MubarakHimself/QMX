"""Story 43.5 — registration-time hook phase law and precedence (FR-Q31; CT-41)."""

from __future__ import annotations

import pytest
from qma.core.plugins.hooks import (
    HookEvent,
    HookResult,
    HookSource,
    assert_hook_result_phase_law,
    build_hook_result,
)
from qma.core.vocabulary.enums import HookResultDecision
from qma.core.vocabulary.hooks import (
    empty_result_decision_for_event,
    legal_decisions_for_event,
    legal_fields_for_event,
    most_restrictive_hook_result,
    validate_registration_phase_law,
)
from qma.core.vocabulary.registry import VocabularyError
from qma.daemon.hooks import (
    HookRegistry,
    default_empty_hook_result,
    resolve_parallel_hook_results,
)
from qmf.core import is_ok, is_refusal


def test_legal_decision_sets_per_phase() -> None:
    before = legal_decisions_for_event("before_memory_write")
    assert before == frozenset(
        {
            HookResultDecision.DENY,
            HookResultDecision.DEFER,
            HookResultDecision.ASK,
            HookResultDecision.ALLOW,
            HookResultDecision.OBSERVE,
        }
    )
    assert HookResultDecision.BLOCK_STOP not in before

    agent_stop = legal_decisions_for_event("agent_stop")
    assert agent_stop == frozenset(
        {HookResultDecision.BLOCK_STOP, HookResultDecision.OBSERVE}
    )
    assert HookResultDecision.DENY not in agent_stop
    assert HookResultDecision.ALLOW not in agent_stop

    review = legal_decisions_for_event("review_required")
    assert review == frozenset(
        {
            HookResultDecision.DENY,
            HookResultDecision.BLOCK_STOP,
            HookResultDecision.OBSERVE,
        }
    )
    assert HookResultDecision.ASK not in review
    assert HookResultDecision.DEFER not in review

    after_tool = legal_decisions_for_event("after_tool")
    assert after_tool == frozenset(
        {HookResultDecision.ALLOW, HookResultDecision.OBSERVE}
    )
    after_other = legal_decisions_for_event("after_memory_write")
    assert after_other == frozenset({HookResultDecision.OBSERVE})
    assert HookResultDecision.ALLOW not in after_other


def test_registration_refuses_illegal_decisions() -> None:
    registry = HookRegistry()

    def handler(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.OBSERVE)

    assert is_refusal(
        registry.register_handler(
            "before_tool",
            handler,
            decisions=(HookResultDecision.BLOCK_STOP,),
        )
    )
    assert is_refusal(
        registry.register_handler(
            "agent_stop",
            handler,
            decisions=(HookResultDecision.DENY,),
        )
    )
    assert is_refusal(
        registry.register_handler(
            "after_ledger_append",
            handler,
            decisions=(HookResultDecision.ALLOW,),
        )
    )
    assert is_refusal(
        registry.register_handler(
            "review_required",
            handler,
            decisions=(HookResultDecision.ASK, HookResultDecision.DEFER),
        )
    )
    assert is_ok(
        registry.register_handler(
            "before_tool",
            handler,
            decisions=(HookResultDecision.DENY, HookResultDecision.ALLOW),
        )
    )
    assert is_ok(
        registry.register_handler(
            "agent_stop",
            handler,
            decisions=(HookResultDecision.BLOCK_STOP, HookResultDecision.OBSERVE),
        )
    )


def test_registry_exposes_permitted_decision_sets() -> None:
    registry = HookRegistry()
    stop = registry.permitted_decisions("agent_stop")
    review = registry.permitted_decisions("review_required")
    after_tool = registry.permitted_decisions("after_tool")
    after_other = registry.permitted_decisions("after_session_end")
    before = registry.permitted_decisions("before_tool")
    assert is_ok(stop) and stop.value == legal_decisions_for_event("agent_stop")
    assert is_ok(review) and review.value == legal_decisions_for_event("review_required")
    assert is_ok(after_tool) and after_tool.value == legal_decisions_for_event("after_tool")
    assert is_ok(after_other) and after_other.value == frozenset({HookResultDecision.OBSERVE})
    assert is_ok(before) and HookResultDecision.ALLOW in before.value
    assert HookResultDecision.ALLOW not in after_other.value


def test_phase_gated_fields_refused_at_registration() -> None:
    registry = HookRegistry()

    def handler(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.ALLOW)

    assert is_refusal(
        registry.register_handler(
            "before_memory_write",
            handler,
            fields=("updated_input",),
        )
    )
    assert is_refusal(
        registry.register_handler(
            "after_tool",
            handler,
            decisions=(HookResultDecision.ALLOW,),
            fields=("updated_input",),
        )
    )
    assert is_refusal(
        registry.register_handler(
            "before_tool",
            handler,
            fields=("ledger_entry", "verifier_ref"),
        )
    )
    assert is_ok(
        registry.register_handler(
            "before_tool",
            handler,
            decisions=(HookResultDecision.ALLOW,),
            fields=("updated_input", "injected_context"),
        )
    )
    assert is_ok(
        registry.register_handler(
            "after_tool",
            handler,
            decisions=(HookResultDecision.ALLOW, HookResultDecision.OBSERVE),
            fields=("updated_output",),
        )
    )
    assert is_ok(
        registry.register_handler(
            "before_task_complete",
            handler,
            decisions=(HookResultDecision.ALLOW,),
            fields=("ledger_entry", "verifier_ref", "injected_context"),
        )
    )
    assert is_ok(
        registry.register_handler(
            "review_required",
            handler,
            decisions=(HookResultDecision.DENY, HookResultDecision.OBSERVE),
            fields=("ledger_entry", "verifier_ref"),
        )
    )
    assert legal_fields_for_event("before_tool") == frozenset(
        {"updated_input", "injected_context"}
    )
    assert legal_fields_for_event("after_session_end") == frozenset()


def test_injected_context_is_before_only_and_not_ledger() -> None:
    assert "injected_context" in legal_fields_for_event("before_skill_write")
    assert "injected_context" not in legal_fields_for_event("after_tool")
    assert "injected_context" not in legal_fields_for_event("review_required")
    with pytest.raises(VocabularyError, match="illegal"):
        validate_registration_phase_law("after_tool", fields=("injected_context",))
    result = build_hook_result(
        HookResultDecision.ALLOW,
        injected_context={"note": "to Context Compiler"},
    )
    assert assert_hook_result_phase_law("before_tool", result) is result
    with pytest.raises(VocabularyError):
        assert_hook_result_phase_law("after_memory_write", result)


def test_total_precedence_and_observe_nonparticipation() -> None:
    assert most_restrictive_hook_result(
        (
            HookResultDecision.OBSERVE,
            HookResultDecision.ALLOW,
            HookResultDecision.DENY,
            HookResultDecision.ASK,
        )
    ) is HookResultDecision.DENY
    assert most_restrictive_hook_result(
        (HookResultDecision.OBSERVE, HookResultDecision.ALLOW)
    ) is HookResultDecision.ALLOW
    assert most_restrictive_hook_result(
        (HookResultDecision.OBSERVE, HookResultDecision.OBSERVE)
    ) is HookResultDecision.OBSERVE
    assert most_restrictive_hook_result(
        (
            HookResultDecision.BLOCK_STOP,
            HookResultDecision.DENY,
            HookResultDecision.DEFER,
            HookResultDecision.ASK,
            HookResultDecision.ALLOW,
            HookResultDecision.OBSERVE,
        )
    ) is HookResultDecision.BLOCK_STOP

    observe = build_hook_result(HookResultDecision.OBSERVE, reason="seen")
    deny = build_hook_result(HookResultDecision.DENY, reason="blocked")
    allow = build_hook_result(HookResultDecision.ALLOW, reason="ok")
    winner = resolve_parallel_hook_results((observe, allow, deny))
    assert winner.decision is HookResultDecision.DENY
    assert winner.reason == "blocked"


def test_parallel_dispatch_uses_most_restrictive() -> None:
    registry = HookRegistry()

    def observe(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.OBSERVE, reason="watch")

    def ask(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.ASK, reason="need_human")

    def deny(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.DENY, reason="no")

    assert is_ok(registry.register_handler("before_tool", observe))
    assert is_ok(registry.register_handler("before_tool", ask))
    assert is_ok(registry.register_handler("before_tool", deny))
    outcome = registry.dispatch("before_tool", source=HookSource.PLUGIN)
    assert is_ok(outcome)
    assert outcome.value.decision is HookResultDecision.DENY
    assert outcome.value.reason == "no"


def test_empty_result_never_null_decision() -> None:
    assert empty_result_decision_for_event("before_tool") is HookResultDecision.ALLOW
    assert empty_result_decision_for_event("after_tool") is HookResultDecision.ALLOW
    assert empty_result_decision_for_event("agent_stop") is HookResultDecision.OBSERVE
    assert empty_result_decision_for_event("review_required") is HookResultDecision.OBSERVE
    assert empty_result_decision_for_event("after_mission_complete") is HookResultDecision.OBSERVE

    before = default_empty_hook_result("before_ledger_append")
    after_tool = default_empty_hook_result("after_tool")
    stop = default_empty_hook_result("agent_stop")
    review = default_empty_hook_result("review_required")
    after = default_empty_hook_result("after_plugin_activate")
    assert before.decision is HookResultDecision.ALLOW
    assert after_tool.decision is HookResultDecision.ALLOW
    assert stop.decision is HookResultDecision.OBSERVE
    assert review.decision is HookResultDecision.OBSERVE
    assert after.decision is HookResultDecision.OBSERVE
    assert before.decision is not None
    assert stop.decision is not None

    registry = HookRegistry()
    empty_before = registry.dispatch("before_task_create")
    empty_stop = registry.evaluate_control("agent_stop")
    assert is_ok(empty_before)
    assert is_ok(empty_stop)
    assert empty_before.value.decision is HookResultDecision.ALLOW
    assert empty_stop.value.decision is HookResultDecision.OBSERVE


def test_dispatch_refuses_phase_illegal_returned_result() -> None:
    registry = HookRegistry()

    def bad_after(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.DENY, reason="too_late")

    assert is_ok(registry.register_handler("after_tool", bad_after))
    outcome = registry.dispatch("after_tool")
    assert is_refusal(outcome)
