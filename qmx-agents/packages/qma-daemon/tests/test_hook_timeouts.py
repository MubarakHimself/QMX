"""Story 43.6 — fail-closed hook timeouts that preserve evidence (FR-Q32; CT-41)."""

from __future__ import annotations

from collections.abc import Mapping

from qma.core.plugins.hooks import HookEvent, HookResult, HookSource, build_hook_result
from qma.core.vocabulary.enums import HookResultDecision
from qma.core.vocabulary.hooks import (
    BEFORE_LEDGER_APPEND_EVENT,
    HOOK_TIMEOUT_REASON,
    timeout_decision_for_event,
)
from qma.daemon.hooks import (
    HOOK_TIMEOUT_AFTER_KEY,
    HOOK_TIMEOUT_BEFORE_KEY,
    HOOK_TIMEOUT_CONTROL_KEY,
    HOOK_TIMEOUT_KEYS,
    HookRegistry,
    LedgerQuarantineStream,
    annotate_ledger_entry,
    evaluate_before_ledger_append,
    resolve_hook_timeout,
    timeout_registry_key_for_event,
)
from qmf.core import is_ok


def _well_formed_entry(*, agent_id: str = "agent-1") -> dict[str, object]:
    return {
        "id": "entry-1",
        "kind": "progress",
        "attempt_no": 0,
        "authored_by": {"agent": agent_id, "quant": "quant:desk.lead"},
        "recorded_at": "2026-09-01T00:00:00Z",
        "model_deployment_ref": "deploy:workhorse",
    }


def test_timeout_keys_are_registry_citations_only() -> None:
    assert HOOK_TIMEOUT_BEFORE_KEY == "registry:hook.timeout_before"
    assert HOOK_TIMEOUT_AFTER_KEY == "registry:hook.timeout_after"
    assert HOOK_TIMEOUT_CONTROL_KEY == "registry:hook.timeout_control"
    assert {
        HOOK_TIMEOUT_BEFORE_KEY,
        HOOK_TIMEOUT_AFTER_KEY,
        HOOK_TIMEOUT_CONTROL_KEY,
    } == HOOK_TIMEOUT_KEYS
    assert timeout_registry_key_for_event("before_tool") == HOOK_TIMEOUT_BEFORE_KEY
    assert timeout_registry_key_for_event("before_memory_write") == HOOK_TIMEOUT_BEFORE_KEY
    assert timeout_registry_key_for_event(BEFORE_LEDGER_APPEND_EVENT) == HOOK_TIMEOUT_BEFORE_KEY
    assert timeout_registry_key_for_event("after_tool") == HOOK_TIMEOUT_AFTER_KEY
    assert timeout_registry_key_for_event("after_ledger_append") == HOOK_TIMEOUT_AFTER_KEY
    assert timeout_registry_key_for_event("agent_stop") == HOOK_TIMEOUT_CONTROL_KEY
    assert timeout_registry_key_for_event("review_required") == HOOK_TIMEOUT_CONTROL_KEY
    # No numeric timeout constants invented anywhere in the key surface.
    for key in HOOK_TIMEOUT_KEYS:
        assert key.startswith("registry:hook.timeout_")
        assert not any(ch.isdigit() for ch in key)


def test_before_timeout_denies_with_telemetry_except_ledger_append() -> None:
    registry = HookRegistry()
    outcome = registry.resolve_timeout("before_tool", correlation_id="corr-1")
    assert is_ok(outcome)
    resolution = outcome.value
    assert resolution.decision is HookResultDecision.DENY
    assert resolution.result.reason == HOOK_TIMEOUT_REASON
    assert resolution.timeout_key == HOOK_TIMEOUT_BEFORE_KEY
    assert resolution.telemetry is not None
    assert resolution.telemetry.correlation_id == "corr-1"
    assert resolution.telemetry.reason == HOOK_TIMEOUT_REASON
    assert len(registry.timeout_telemetry.records) == 1

    memory = resolve_hook_timeout("before_memory_write", correlation_id="corr-2")
    assert memory.decision is HookResultDecision.DENY
    assert memory.timeout_key == HOOK_TIMEOUT_BEFORE_KEY
    assert memory.telemetry is not None

    dispatched = registry.dispatch(
        "before_skill_write",
        timed_out=True,
        correlation_id="corr-3",
    )
    assert is_ok(dispatched)
    assert dispatched.value.decision is HookResultDecision.DENY
    assert dispatched.value.reason == HOOK_TIMEOUT_REASON


def test_before_ledger_append_timeout_allows_and_annotates() -> None:
    registry = HookRegistry()
    entry = _well_formed_entry()
    gate = registry.evaluate_ledger_append(
        entry,
        dispatch_lease_holder="agent-1",
        timed_out=True,
        correlation_id="corr-ledger",
    )
    assert is_ok(gate)
    result = gate.value
    assert result.decision is HookResultDecision.ALLOW
    assert result.result.reason == HOOK_TIMEOUT_REASON
    assert result.disposition == "record"
    assert result.timeout_key == HOOK_TIMEOUT_BEFORE_KEY
    assert result.entry["hook_timeout"] is True
    assert HOOK_TIMEOUT_REASON in result.entry["annotations"]  # type: ignore[operator]
    # Timeout on before_ledger_append does not emit deny telemetry.
    assert result.telemetry is None
    assert registry.timeout_telemetry.records == ()
    assert timeout_decision_for_event(BEFORE_LEDGER_APPEND_EVENT) is HookResultDecision.ALLOW


def test_well_formed_lease_holder_cannot_be_denied() -> None:
    registry = HookRegistry()

    def deny(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.DENY, reason="policy_deny")

    assert is_ok(registry.register_handler(BEFORE_LEDGER_APPEND_EVENT, deny))
    entry = _well_formed_entry(agent_id="agent-holder")
    gate = registry.evaluate_ledger_append(
        entry,
        dispatch_lease_holder="agent-holder",
    )
    assert is_ok(gate)
    result = gate.value
    assert result.decision is HookResultDecision.ALLOW
    assert result.disposition == "record"
    assert result.quarantine is None
    # Precedence deny overridden — evidence preserved.
    direct = evaluate_before_ledger_append(
        entry,
        dispatch_lease_holder="agent-holder",
        attempted_result=build_hook_result(HookResultDecision.DENY, reason="precedence"),
    )
    assert direct.decision is HookResultDecision.ALLOW
    assert direct.disposition == "record"


def test_schema_invalid_or_outside_lease_quarantines_never_discards() -> None:
    registry = HookRegistry()
    invalid = {"id": "bad", "kind": "progress"}  # missing required fields
    bad_schema = registry.evaluate_ledger_append(
        invalid,
        dispatch_lease_holder="agent-1",
    )
    assert is_ok(bad_schema)
    assert bad_schema.value.decision is HookResultDecision.DENY
    assert bad_schema.value.disposition == "quarantine"
    assert bad_schema.value.quarantine is not None
    assert bad_schema.value.quarantine.denial_source == "schema"
    assert bad_schema.value.to_payload()["discarded"] is False

    outside = _well_formed_entry(agent_id="other-agent")
    refused = registry.evaluate_ledger_append(
        outside,
        dispatch_lease_holder="lease-holder",
    )
    assert is_ok(refused)
    assert refused.value.decision is HookResultDecision.DENY
    assert refused.value.disposition == "quarantine"
    assert refused.value.quarantine is not None
    assert refused.value.quarantine.denial_source == "lease"
    assert refused.value.quarantine.to_payload()["discarded"] is False

    assert len(registry.ledger_quarantine.records) == 2
    assert registry.ledger_quarantine.discarded_count == 0

    # Explicit deny of invalid entry still quarantines — never discards.
    stream = LedgerQuarantineStream()
    quarantined = evaluate_before_ledger_append(
        invalid,
        dispatch_lease_holder="agent-1",
        attempted_result=build_hook_result(HookResultDecision.DENY, reason="schema_invalid"),
        quarantine=stream,
    )
    assert quarantined.disposition == "quarantine"
    assert stream.discarded_count == 0
    assert len(stream.records) == 1


def test_agent_stop_and_after_timeout_observe_annotated() -> None:
    registry = HookRegistry()

    stop = registry.resolve_timeout("agent_stop")
    assert is_ok(stop)
    assert stop.value.decision is HookResultDecision.OBSERVE
    assert stop.value.result.reason == HOOK_TIMEOUT_REASON
    assert stop.value.timeout_key == HOOK_TIMEOUT_CONTROL_KEY
    assert stop.value.telemetry is None

    after = registry.dispatch("after_tool", timed_out=True)
    assert is_ok(after)
    assert after.value.decision is HookResultDecision.OBSERVE
    assert after.value.reason == HOOK_TIMEOUT_REASON

    after_other = resolve_hook_timeout("after_memory_write")
    assert after_other.decision is HookResultDecision.OBSERVE
    assert after_other.timeout_key == HOOK_TIMEOUT_AFTER_KEY
    assert after_other.result.reason == HOOK_TIMEOUT_REASON

    # review_required stays fail-closed deny on timeout (CT-41 per-control).
    review = registry.resolve_timeout("review_required", correlation_id="corr-review")
    assert is_ok(review)
    assert review.value.decision is HookResultDecision.DENY
    assert review.value.timeout_key == HOOK_TIMEOUT_CONTROL_KEY
    assert review.value.telemetry is not None
    assert len(registry.timeout_telemetry.records) == 1


def test_dispatch_attaches_registry_timeout_key_not_numeric() -> None:
    registry = HookRegistry()
    seen: list[HookEvent] = []

    def capture(event: HookEvent) -> HookResult:
        seen.append(event)
        return build_hook_result(HookResultDecision.ALLOW, reason="ok")

    assert is_ok(registry.register_handler("before_tool", capture))
    outcome = registry.dispatch("before_tool", source=HookSource.PLUGIN)
    assert is_ok(outcome)
    assert len(seen) == 1
    assert seen[0].timeout_key == HOOK_TIMEOUT_BEFORE_KEY
    assert not hasattr(seen[0], "timeout_ms") or getattr(seen[0], "timeout_ms", None) is None


def test_daemon_exempt_author_and_annotation_helper() -> None:
    entry: Mapping[str, object] = {
        "id": "reassign-1",
        "kind": "reassigned",
        "attempt_no": 1,
        "authored_by": "daemon",
        "recorded_at": "2026-09-01T00:00:00Z",
    }
    gate = evaluate_before_ledger_append(
        entry,
        dispatch_lease_holder=None,
        timed_out=True,
    )
    assert gate.decision is HookResultDecision.ALLOW
    assert gate.disposition == "record"
    annotated = annotate_ledger_entry(dict(entry), annotation=HOOK_TIMEOUT_REASON)
    assert annotated["hook_timeout"] is True
