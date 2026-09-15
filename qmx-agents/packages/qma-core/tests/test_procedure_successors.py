"""Story 37.3 — config-changing door steps mint ExperimentSpec successors."""

from __future__ import annotations

from qma.core.control import (
    PROCEDURE_BOT_SUPERSEDES_EDGE,
    PROCEDURE_IS_EXPERIMENT_SPEC,
    PROCEDURE_MINTS_CT07_EDGE,
    PROCEDURE_SUCCESSOR_CHANGE,
    PROCEDURE_SUCCESSOR_EDGE_TYPE,
    PROCEDURE_USES_BOT_SUPERSEDES,
    admit_procedure_successor_change,
    admit_procedure_successor_edge,
    author_procedure,
    procedure_ct07_edge_kinds,
    procedure_mints_ct07_edge,
    procedure_step_changes_resolved_config,
    procedure_step_resolved_config_ref,
    procedure_successor_edge_type,
    procedure_uses_bot_supersedes,
    refuse_procedure_as_experiment_spec,
    refuse_procedure_bot_supersedes,
    refuse_procedure_new_ct07_edge,
)
from qma.core.plugins import analysis_procedure_graph_payload
from qma.core.ports.experiments import (
    COORDINATED_CONTINUITY_KIND,
    CT07_V1_EDGE_TYPES,
    EXPERIMENT_CHANGE_CODE,
    EXPERIMENT_CHANGE_RESOLVED_CONFIG,
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    admit_coordinated_continuity,
)
from qmf.core import is_ok, is_refusal


def test_procedure_is_not_experiment_spec_and_continuity_is_spec_fp1() -> None:
    authored = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    payload = authored.value.to_payload()
    assert payload["is_experiment_spec"] is PROCEDURE_IS_EXPERIMENT_SPEC
    assert authored.value.is_experiment_spec is False
    as_spec = author_procedure(
        {
            "kind": "experiment_spec",
            "qualified_id": "analysis-backtest:procedure",
            "version": "1",
        }
    )
    assert is_refusal(as_spec)
    assert refuse_procedure_as_experiment_spec().context["continuity"] == (
        COORDINATED_CONTINUITY_KIND
    )
    continuity = admit_coordinated_continuity("experiment_spec")
    assert is_ok(continuity)
    assert continuity.value == COORDINATED_CONTINUITY_KIND
    assert is_refusal(admit_coordinated_continuity("procedure"))


def test_successor_edge_is_existing_branches_from_not_bot_supersedes() -> None:
    assert procedure_successor_edge_type() == EXPERIMENT_LINEAGE_EDGE_TYPE
    assert PROCEDURE_SUCCESSOR_EDGE_TYPE == "branches-from"
    assert PROCEDURE_SUCCESSOR_CHANGE == EXPERIMENT_CHANGE_RESOLVED_CONFIG
    assert procedure_uses_bot_supersedes() is False
    assert PROCEDURE_USES_BOT_SUPERSEDES is False
    assert PROCEDURE_BOT_SUPERSEDES_EDGE == "supersedes"
    assert procedure_mints_ct07_edge() is False
    assert PROCEDURE_MINTS_CT07_EDGE is False
    assert procedure_ct07_edge_kinds() == frozenset()
    admitted = admit_procedure_successor_edge()
    assert is_ok(admitted)
    assert admitted.value == "branches-from"
    named = admit_procedure_successor_edge("branches-from")
    assert is_ok(named)
    change = admit_procedure_successor_change()
    assert is_ok(change)
    assert change.value == EXPERIMENT_CHANGE_RESOLVED_CONFIG


def test_bot_supersedes_and_new_edge_kinds_are_refused() -> None:
    supersedes = admit_procedure_successor_edge("supersedes")
    assert is_refusal(supersedes)
    assert supersedes.context["uses_bot_supersedes"] is False
    bot = refuse_procedure_bot_supersedes(given="bot-supersedes")
    assert is_refusal(bot)
    assert bot.context["edge_type"] == "branches-from"
    minted = admit_procedure_successor_edge("experiment-predecessor")
    assert is_refusal(minted)
    assert minted.context["mints_ct07_edge"] is False
    assert "experiment-predecessor" not in CT07_V1_EDGE_TYPES
    assert refuse_procedure_new_ct07_edge(given="procedure-from").context["allowed"] == (
        "branches-from"
    )
    code = admit_procedure_successor_change(EXPERIMENT_CHANGE_CODE)
    assert is_refusal(code)
    assert code.context["change"] == EXPERIMENT_CHANGE_RESOLVED_CONFIG


def test_resolved_config_change_is_detected_from_step_inputs() -> None:
    previous = "fp1:sha256:" + ("a" * 64)
    nxt = "fp1:sha256:" + ("b" * 64)
    assert procedure_step_changes_resolved_config(
        resolved_config_ref=nxt,
        predecessor_resolved_config_ref=previous,
    )
    assert not procedure_step_changes_resolved_config(
        resolved_config_ref=previous,
        predecessor_resolved_config_ref=previous,
    )
    assert not procedure_step_changes_resolved_config(
        resolved_config_ref=None,
        predecessor_resolved_config_ref=previous,
    )
    from_step = procedure_step_resolved_config_ref({"resolved_config_ref": nxt})
    assert from_step == nxt
    from_extra = procedure_step_resolved_config_ref(
        "backtest.run",
        extra={"resolved_config_ref": nxt},
    )
    assert from_extra == nxt
    query_has_no_change = procedure_step_changes_resolved_config(
        resolved_config_ref=None,
        predecessor_resolved_config_ref=previous,
    )
    assert query_has_no_change is False
