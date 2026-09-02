"""Story 46.7 — continuation bound keys and verifier substitution law (FR-Q63)."""

from __future__ import annotations

from qma.core.ontology import (
    CONTINUATION_BOUND_KEYS,
    CONTINUATION_BUDGET_KEY,
    CONTINUATION_EDITABILITY,
    CONTINUATION_ESCALATION_TARGET_KEY,
    CONTINUATION_HOME,
    CONTINUATION_MAX_CONSECUTIVE_KEY,
    CONTINUATION_SCOPE,
    CONTINUATION_UNDECLARED_VALUE,
    ContinuationBounds,
    is_continuation_bound_key,
    parse_continuation_bounds,
    refuse_invented_continuation_task,
    refuse_model_authored_completion,
)
from qma.core.vocabulary.enums import VariableEditability, VariableScope
from qmf.core import is_ok, is_refusal


def test_bound_keys_are_the_three_registry_citations() -> None:
    assert CONTINUATION_MAX_CONSECUTIVE_KEY == "registry:continuation.max_consecutive"
    assert CONTINUATION_BUDGET_KEY == "registry:continuation.budget"
    assert CONTINUATION_ESCALATION_TARGET_KEY == "registry:continuation.escalation_target"
    assert CONTINUATION_BOUND_KEYS == (
        CONTINUATION_MAX_CONSECUTIVE_KEY,
        CONTINUATION_BUDGET_KEY,
        CONTINUATION_ESCALATION_TARGET_KEY,
    )
    assert CONTINUATION_HOME == "registry"
    assert CONTINUATION_SCOPE is VariableScope.GLOBAL
    assert CONTINUATION_EDITABILITY is VariableEditability.UI_EDITABLE
    assert is_continuation_bound_key("continuation.max_consecutive")
    assert is_continuation_bound_key(CONTINUATION_BUDGET_KEY)
    assert not is_continuation_bound_key("continuation.sticky_limit")
    assert not is_continuation_bound_key("rlm.fanout_cost_ceiling_usd")


def test_parse_bounds_from_registry_keys_only() -> None:
    parsed = parse_continuation_bounds(
        {
            CONTINUATION_MAX_CONSECUTIVE_KEY: 2,
            CONTINUATION_BUDGET_KEY: 3,
            CONTINUATION_ESCALATION_TARGET_KEY: "quant_mailbox",
        }
    )
    assert is_ok(parsed)
    bounds = parsed.value
    assert isinstance(bounds, ContinuationBounds)
    assert bounds.max_consecutive == 2
    assert bounds.budget == 3
    assert bounds.escalation_target == "quant_mailbox"
    assert bounds.source_keys == CONTINUATION_BOUND_KEYS
    assert bounds.max_consecutive_key == CONTINUATION_MAX_CONSECUTIVE_KEY
    payload = bounds.to_payload()
    assert payload["source_keys"] == list(CONTINUATION_BOUND_KEYS)
    assert bounds.exhausted(consecutive=2, budget_used=0) is True
    assert bounds.exhausted(consecutive=0, budget_used=3) is True
    assert bounds.exhausted(consecutive=1, budget_used=1) is False

    bare = parse_continuation_bounds(
        {
            "continuation.max_consecutive": 1,
            "continuation.budget": 1,
            "continuation.escalation_target": "quant_mailbox",
        }
    )
    assert is_ok(bare)


def test_parse_refuses_undeclared_and_invented_sources() -> None:
    extra = parse_continuation_bounds(
        {
            CONTINUATION_MAX_CONSECUTIVE_KEY: 1,
            CONTINUATION_BUDGET_KEY: 1,
            CONTINUATION_ESCALATION_TARGET_KEY: "quant_mailbox",
            "sticky_limit": 4,
        }
    )
    assert is_refusal(extra)
    assert extra.context["field"] == "continuation"
    undeclared = parse_continuation_bounds(
        {
            CONTINUATION_MAX_CONSECUTIVE_KEY: CONTINUATION_UNDECLARED_VALUE,
            CONTINUATION_BUDGET_KEY: 1,
            CONTINUATION_ESCALATION_TARGET_KEY: "quant_mailbox",
        }
    )
    assert is_refusal(undeclared)
    missing = parse_continuation_bounds({CONTINUATION_BUDGET_KEY: 1})
    assert is_refusal(missing)
    assert missing.context["field"] == "continuation"


def test_refuse_model_authored_completion_and_invented_task() -> None:
    substituted = refuse_model_authored_completion(source="llm")
    assert is_refusal(substituted)
    assert substituted.context["model_substituted"] is True
    assert substituted.context["complete"] is False
    invented = refuse_invented_continuation_task()
    assert is_refusal(invented)
    assert invented.context["invented_task"] is False
