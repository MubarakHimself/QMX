"""Story 60.4 — one QuantMind/QMX Copilot identity; skills and hits are not grants."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from qma.core.control.primitives import Skill
from qma.core.ports.copilot import (
    APP_USE_MAY_APPLY,
    CONTEXT_TRANSFER_KINDS,
    CONTRIBUTION_HIT_IS_GRANT,
    COPILOT_PRODUCT_ALIASES,
    COPILOT_PRODUCT_IDENTITY,
    COPILOT_SEAT_PROFILES,
    ENGINE_RUN_ID_PREFIX,
    ENGINE_RUN_IS_THIRD_CHAT,
    GAP_0081_CHROME_FILLED,
    HOOKS_OVERRIDE_PRIVILEGE_GATE,
    IN_APP_PANEL_IS_CONTRACT,
    IN_APP_PANEL_IS_GAP_0081_CHROME,
    IN_APP_PANEL_IS_SECOND_COPILOT,
    INSTANCE_MAY_OMIT_PANEL,
    PACK_MAY_OMIT_COPILOT_PROFILE,
    PANEL_DISPOSE_CANCELS_JOB_HANDLE,
    PRODUCT_SESSION_ID_PREFIX,
    RECONNECT_REPLAYS_UNACKED_INTENT,
    SECOND_COPILOT_PRODUCT_MINTED,
    SKILLS_GRANT,
    intersect_tool_availability,
    parse_copilot_product_identity,
    privilege_gate_holds,
    refuse_context_transfer,
    refuse_engine_run_as_chat,
    refuse_panel_as_second_copilot,
    refuse_second_copilot_product,
    refuse_skill_as_grant,
)
from qma.core.vocabulary.enums import HookResultDecision
from qmf.core import is_ok, is_refusal


def test_one_copilot_product_identity_and_optional_panel_contract() -> None:
    assert COPILOT_PRODUCT_IDENTITY == "QuantMind/QMX Copilot"
    assert frozenset(
        {
            "QuantMind/QMX Copilot",
            "QuantMind Copilot",
            "QMX Copilot",
        }
    ) == COPILOT_PRODUCT_ALIASES
    assert frozenset({"authoring", "app-use"}) == COPILOT_SEAT_PROFILES
    assert PRODUCT_SESSION_ID_PREFIX == "psess:"
    assert ENGINE_RUN_ID_PREFIX == "sess:"
    assert SECOND_COPILOT_PRODUCT_MINTED is False
    assert ENGINE_RUN_IS_THIRD_CHAT is False
    assert IN_APP_PANEL_IS_CONTRACT is True
    assert IN_APP_PANEL_IS_GAP_0081_CHROME is False
    assert IN_APP_PANEL_IS_SECOND_COPILOT is False
    assert GAP_0081_CHROME_FILLED is False
    assert PACK_MAY_OMIT_COPILOT_PROFILE is True
    assert INSTANCE_MAY_OMIT_PANEL is True
    assert PANEL_DISPOSE_CANCELS_JOB_HANDLE is False
    assert RECONNECT_REPLAYS_UNACKED_INTENT is False
    assert APP_USE_MAY_APPLY is False
    assert SKILLS_GRANT is False
    assert CONTRIBUTION_HIT_IS_GRANT is False
    assert HOOKS_OVERRIDE_PRIVILEGE_GATE is False
    assert frozenset({"selected_refs", "change_request"}) == CONTEXT_TRANSFER_KINDS

    for alias in COPILOT_PRODUCT_ALIASES:
        parsed = parse_copilot_product_identity(alias)
        assert is_ok(parsed)
        assert parsed.value == COPILOT_PRODUCT_IDENTITY
    second = parse_copilot_product_identity("Desk Copilot")
    assert is_refusal(second)
    assert second.context["second_copilot"] is False
    minted = refuse_second_copilot_product()
    assert is_refusal(minted)
    assert minted.context["minted"] is False
    panel = refuse_panel_as_second_copilot(given="panel:app")
    assert is_refusal(panel)
    assert panel.context["is_contract"] is True
    assert panel.context["is_gap_0081_chrome"] is False
    assert panel.context["is_second_copilot"] is False
    engine = refuse_engine_run_as_chat(given="sess:run-1")
    assert is_refusal(engine)
    assert engine.context["third_chat"] is False
    assert engine.context["prefix"] == "sess:"
    transfer = refuse_context_transfer("transcript")
    assert is_refusal(transfer)
    assert list(cast("Sequence[object]", transfer.context["allowed"])) == [
        "change_request",
        "selected_refs",
    ]


def test_tool_availability_is_four_way_intersection_and_hooks_cannot_rescue() -> None:
    available = intersect_tool_availability(
        ["analysis-backtest:qmb", "research-corpus:inspect", "ghost:hit"],
        ["analysis-backtest:qmb", "research-corpus:inspect"],
        ["analysis-backtest:qmb", "ghost:hit"],
        ["analysis-backtest:qmb", "research-corpus:inspect"],
    )
    assert available == frozenset({"analysis-backtest:qmb"})
    missing = privilege_gate_holds(
        available=available,
        qualified_id="research-corpus:inspect",
        hook_decision=HookResultDecision.ALLOW,
    )
    assert is_refusal(missing)
    assert missing.context["hooks_override"] is False
    assert missing.context["skills_grant"] is False
    assert missing.context["hit_is_grant"] is False
    held = privilege_gate_holds(
        available=available,
        qualified_id="analysis-backtest:qmb",
        hook_decision=HookResultDecision.ALLOW,
    )
    assert is_ok(held)
    skill = Skill(
        qualified_id="research-corpus:inspect-skill",
        version="0.1.0",
        summary="describes inspect",
    )
    described = refuse_skill_as_grant(skill)
    assert is_ok(described)
    treated = refuse_skill_as_grant(skill, treat_as_grant=True)
    assert is_refusal(treated)
    assert treated.context["skills_grant"] is False
