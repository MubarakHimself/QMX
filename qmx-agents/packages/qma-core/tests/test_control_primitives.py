"""Story 43.3 — qma-core Graph Template / Loop / Skill definitions (FR-Q29)."""

from __future__ import annotations

import pytest
from qma.core.control import (
    DAEMON_EVALUATED_NODE_KINDS,
    DEFERRED_GRAPH_EXCLUSIONS,
    ControlPrimitive,
    Skill,
    emits_task,
    is_loop_kind,
    is_skill_distinct_from_loop,
)
from qma.core.vocabulary.enums import NodeKind


def test_three_control_primitives_are_distinct() -> None:
    assert set(ControlPrimitive) == {
        ControlPrimitive.GRAPH_TEMPLATE,
        ControlPrimitive.LOOP,
        ControlPrimitive.SKILL,
    }
    assert ControlPrimitive.SKILL is not ControlPrimitive.LOOP
    assert ControlPrimitive.GRAPH_TEMPLATE.value == "graph_template"


def test_skill_may_invoke_loop_but_is_never_a_loop() -> None:
    skill = Skill(
        qualified_id="analysis-backtest:review",
        version="1",
        summary="Review a backtest fold",
        loop_ref="hypothesis-test-learn",
    )
    assert skill.invokes_loop is True
    assert skill.is_loop is False
    assert is_skill_distinct_from_loop(skill)
    assert skill.to_payload()["grants_capability"] is False

    with pytest.raises(ValueError, match="fully-qualified"):
        Skill(qualified_id="bare", version="1", summary="x")

    with pytest.raises(ValueError, match="non-empty"):
        Skill(
            qualified_id="analysis-backtest:bad",
            version="1",
            summary="x",
            loop_ref="",
        )


def test_node_kind_emission_helpers() -> None:
    assert emits_task(NodeKind.TASK)
    assert emits_task(NodeKind.AGENT)
    assert emits_task(NodeKind.LOOP)
    assert is_loop_kind(NodeKind.LOOP)
    assert not emits_task(NodeKind.CONDITIONAL)
    assert NodeKind.HUMAN_GATE in DAEMON_EVALUATED_NODE_KINDS
    assert "GAP-0084" in DEFERRED_GRAPH_EXCLUSIONS
    assert "GAP-0086" in DEFERRED_GRAPH_EXCLUSIONS
