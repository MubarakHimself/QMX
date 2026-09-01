"""Story 43.4 — mandatory daemon hook registry (FR-Q30; CT-41; AD-10)."""

from __future__ import annotations

from qma.core.plugins.hooks import HookEvent, HookResult, HookSource, build_hook_result
from qma.core.vocabulary.enums import HookControl, HookResultDecision, HookVerb
from qma.core.vocabulary.hooks import HOOK_CONTROLS, HOOK_EVENT_NAMES, HOOK_VERBS
from qma.daemon.hooks import (
    AGENT_REACHABLE_WRITE_VERBS,
    BYPASS_WRITE_PATHS,
    DAEMON_OWNED_HOOK_VERBS,
    PHASE_LESS_CONTROLS,
    HookRegistry,
    assert_no_bypass_write_path,
    event_names_for_verb,
)
from qmf.core import is_ok, is_refusal


def test_v1_registry_enumerates_all_twenty_three_verb_pairs_and_two_controls() -> None:
    registry = HookRegistry()
    assert registry.verbs == HOOK_VERBS
    assert len(registry.verbs) == 23
    assert set(registry.verbs) == {
        HookVerb.TOOL,
        HookVerb.TASK_CREATE,
        HookVerb.TASK_COMPLETE,
        HookVerb.LEDGER_APPEND,
        HookVerb.MEMORY_WRITE,
        HookVerb.SKILL_WRITE,
        HookVerb.ARTIFACT_REGISTER,
        HookVerb.EXPERIMENT_REGISTER,
        HookVerb.ENV_CREATE,
        HookVerb.ENV_REMOVE,
        HookVerb.SUBAGENT_SPAWN,
        HookVerb.MESSAGE_SEND,
        HookVerb.GRAPH_TRANSITION,
        HookVerb.SESSION_START,
        HookVerb.SESSION_END,
        HookVerb.MISSION_START,
        HookVerb.MISSION_COMPLETE,
        HookVerb.PLUGIN_ACTIVATE,
        HookVerb.PLUGIN_DEACTIVATE,
        HookVerb.ROUTINE_FIRE,
        HookVerb.HOOK_REGISTER,
        HookVerb.PROPOSAL_STAGE,
        HookVerb.PROPOSAL_APPLY,
    }
    assert registry.controls == (HookControl.AGENT_STOP, HookControl.REVIEW_REQUIRED)
    assert PHASE_LESS_CONTROLS == HOOK_CONTROLS
    assert registry.event_names == HOOK_EVENT_NAMES
    assert len(registry.event_names) == 23 * 2 + 2

    events = {entry.event for entry in registry.entries()}
    for verb in DAEMON_OWNED_HOOK_VERBS:
        before, after = event_names_for_verb(verb)
        assert before in events
        assert after in events
        assert registry.has_complete_pair(verb)
    assert events == {
        *(f"before_{v.value}" for v in HookVerb),
        *(f"after_{v.value}" for v in HookVerb),
        "agent_stop",
        "review_required",
    }
    phase_less = [entry for entry in registry.entries() if entry.control is not None]
    assert {entry.event for entry in phase_less} == {"agent_stop", "review_required"}


def test_evaluate_primitive_runs_before_then_after() -> None:
    registry = HookRegistry()
    order: list[str] = []

    def before_handler(event: HookEvent) -> HookResult:
        order.append(event.event)
        return build_hook_result(HookResultDecision.ALLOW, reason="gate_ok")

    def after_handler(event: HookEvent) -> HookResult:
        order.append(event.event)
        return build_hook_result(HookResultDecision.OBSERVE, reason="seen")

    assert is_ok(registry.register_handler("before_tool", before_handler, source=HookSource.PLUGIN))
    assert is_ok(registry.register_handler("after_tool", after_handler, source=HookSource.PLUGIN))

    def act() -> str:
        order.append("act")
        return "tool-result"

    outcome = registry.evaluate_primitive(HookVerb.TOOL, act=act, payload={"name": "search"})
    assert is_ok(outcome)
    invocation = outcome.value
    assert invocation.before_event == "before_tool"
    assert invocation.after_event == "after_tool"
    assert invocation.before_result.decision is HookResultDecision.ALLOW
    assert invocation.after_result.decision is HookResultDecision.OBSERVE
    assert invocation.value == "tool-result"
    assert order == ["before_tool", "act", "after_tool"]


def test_blocking_before_refuses_act_without_running_it() -> None:
    registry = HookRegistry()
    ran = {"act": False}

    def deny(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.DENY, reason="blocked")

    assert is_ok(registry.register_handler("before_memory_write", deny))

    def act() -> str:
        ran["act"] = True
        return "written"

    outcome = registry.evaluate_primitive(HookVerb.MEMORY_WRITE, act=act)
    assert is_refusal(outcome)
    assert ran["act"] is False


def test_agent_reachable_write_always_passes_before_hook() -> None:
    registry = HookRegistry()
    gated: list[str] = []

    def before_handler(event: HookEvent) -> HookResult:
        gated.append(event.event)
        return build_hook_result(HookResultDecision.ALLOW, reason="write_ok")

    for verb in sorted(AGENT_REACHABLE_WRITE_VERBS, key=lambda item: item.value):
        before, _after = event_names_for_verb(verb)
        assert is_ok(registry.register_handler(before, before_handler))

    for verb in sorted(AGENT_REACHABLE_WRITE_VERBS, key=lambda item: item.value):
        result = registry.agent_reachable_write(verb, act=lambda: {"ok": True})
        assert is_ok(result)
        assert result.value.agent_write is True
        assert result.value.before_event.startswith("before_")

    expected = [
        f"before_{v.value}" for v in sorted(AGENT_REACHABLE_WRITE_VERBS, key=lambda i: i.value)
    ]
    assert gated == expected
    assert_no_bypass_write_path()
    assert frozenset() == BYPASS_WRITE_PATHS


def test_agent_write_rejects_non_write_verb() -> None:
    registry = HookRegistry()
    outcome = registry.agent_reachable_write(HookVerb.TOOL, act=lambda: None)
    assert is_refusal(outcome)


def test_unknown_verb_and_event_refused() -> None:
    registry = HookRegistry()
    assert is_refusal(registry.resolve_verb("invented_write"))
    assert is_refusal(registry.resolve_event("before_invented"))
    assert is_refusal(registry.resolve_control("kill_switch"))
    assert is_refusal(registry.evaluate_primitive("invented_write", act=lambda: None))

    def observe(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.OBSERVE)

    assert is_refusal(registry.register_handler("before_invented", observe))
    # Incomplete / unowned pair surface: require_pair_or_refuse refuses unknown.
    assert is_refusal(registry.require_pair_or_refuse("not_a_primitive"))
    pair = registry.require_pair_or_refuse(HookVerb.LEDGER_APPEND)
    assert is_ok(pair)
    assert pair.value == ("before_ledger_append", "after_ledger_append")


def test_phase_less_controls_are_evaluable_and_exclusive() -> None:
    registry = HookRegistry()
    stop = registry.evaluate_control(HookControl.AGENT_STOP)
    review = registry.evaluate_control("review_required")
    assert is_ok(stop)
    assert is_ok(review)
    # Empty handlers resolve to observe on phase-less controls.
    assert stop.value.decision is HookResultDecision.OBSERVE
    assert review.value.decision is HookResultDecision.OBSERVE
    assert is_refusal(registry.evaluate_control("session_pause"))


def test_daemon_package_exports_hook_registry() -> None:
    import qma.daemon

    assert qma.daemon.HookRegistry is HookRegistry
    assert qma.daemon.AGENT_REACHABLE_WRITE_VERBS is AGENT_REACHABLE_WRITE_VERBS
    assert frozenset() == qma.daemon.BYPASS_WRITE_PATHS
