"""Story 38.2 — StrategyHandle references and registers; it never assembles CT-33 JSON."""

from __future__ import annotations

from pathlib import Path

from qma.core.content import content_address
from qma.core.ports.experiments import GAP_0085_STRATEGY_MECHANISMS, parse_experiment_spec
from qma.core.ports.handles import (
    STRATEGY_HANDLE_LINEAGE_EDGE_TYPE,
    StrategyCandidate,
    parse_registry_record_fp1,
    parse_strategy_record_reference,
    refuse_strategy_handle_assembly,
    unset_money_path_fills,
)
from qma.core.vocabulary.handles import QMA_OWNED_CANDIDATE_ORIGIN, STRATEGY_CANDIDATE_ZONE
from qmf.core import is_ok, is_refusal

CORE_SRC = Path(__file__).resolve().parents[1] / "src"


def _fp(tag: str) -> str:
    addressed = content_address({"qml_host_minted": tag})
    assert is_ok(addressed)
    return addressed.value.value


def test_strategy_handle_requires_an_already_fingerprinted_payload() -> None:
    minted = StrategyCandidate.try_create(
        origin=QMA_OWNED_CANDIDATE_ORIGIN,
        zone=STRATEGY_CANDIDATE_ZONE,
        payload_fp1=_fp("already-minted-by-qml"),
        stable_id="cand-1",
        handle_id="h:StrategyHandle:1",
        money_path_relevant=False,
        lineage_predecessor=_fp("predecessor"),
        record_fp1=_fp("already-minted-by-qml"),
    )
    assert is_ok(minted)
    assert minted.value.payload_fp1.startswith("fp1:")
    assert minted.value.record_fp1 == _fp("already-minted-by-qml")
    assembled = StrategyCandidate.try_create(
        origin=QMA_OWNED_CANDIDATE_ORIGIN,
        zone=STRATEGY_CANDIDATE_ZONE,
        payload_fp1={"kind": "bot-definition", "body": {"strategy_family_id": "trend"}},
        stable_id="cand-2",
        handle_id="h:StrategyHandle:1",
        money_path_relevant=False,
    )
    assert is_refusal(assembled)
    assert assembled.context["field"] in {"payload_fp1", "assembly"}


def test_qma_core_does_not_assemble_ct33_or_mint_gap_0085_nouns() -> None:
    forbidden = (
        "mint_bot_definition",
        "mint_confluence",
        "register_bot_definition",
        "author_new_structure",
    )
    hits: list[str] = []
    for path in CORE_SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                hits.append(f"{path}: {token}")
    assert hits == []
    assert "entry_mechanism" in GAP_0085_STRATEGY_MECHANISMS
    refused = parse_experiment_spec(
        data_ref="data:x",
        environment_ref="env:x",
        seed=1,
        model_and_harness_version={"model": "m", "harness": "h"},
        cost_assumptions={},
        resolved_config_ref=_fp("cfg"),
        extra={"EntryMechanism": {"kind": "breakout"}},
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "mechanisms"


def test_strategy_handle_references_a_fingerprinted_registry_record() -> None:
    record_fp1 = _fp("qml-bot")
    referenced = parse_strategy_record_reference(
        handle_id="h:StrategyHandle:ref",
        record_fp1=record_fp1,
    )
    assert is_ok(referenced)
    assert referenced.value.evidence_ref == record_fp1
    assert referenced.value.contents is None
    assembled = parse_registry_record_fp1(
        {"kind": "bot-definition", "strategy_family_id": "trend", "confluence_set": ["fp1:x"]}
    )
    assert is_refusal(assembled)
    assert assembled.context["field"] == "assembly"


def test_refuse_ct33_ct34_json_mechanism_nouns_and_random_condition() -> None:
    assert STRATEGY_HANDLE_LINEAGE_EDGE_TYPE == "branches-from"
    ct33 = refuse_strategy_handle_assembly(
        {
            "kind": "bot-definition",
            "strategy_family_id": "trend",
            "confluence_set": [_fp("confluence")],
            "parameter_space": [],
            "footprint": {},
            "permitted_exit_intents": [],
            "logic_reference": _fp("logic"),
        }
    )
    assert ct33 is not None
    assert is_refusal(ct33)
    assert ct33.context["field"] == "assembly"
    ct34 = refuse_strategy_handle_assembly(
        {"kind": "confluence", "legs": [{"role": "level", "producer_binding": _fp("zone")}]}
    )
    assert ct34 is not None
    assert is_refusal(ct34)
    assert ct34.context["field"] == "assembly"
    nouns = refuse_strategy_handle_assembly({"EntryMechanism": {"kind": "breakout"}})
    assert nouns is not None
    assert is_refusal(nouns)
    assert nouns.context["field"] == "mechanisms"
    slots = refuse_strategy_handle_assembly({"note": "v1", "RandomCondition": {"min": 1, "max": 5}})
    assert slots is not None
    assert is_refusal(slots)
    assert slots.context["field"] == "random_condition"
    notes = refuse_strategy_handle_assembly({"note": "v1", "window": "H1"})
    assert notes is None


def test_gap_0085_strategy_mechanisms_refusal_is_unchanged() -> None:
    assert "entry_mechanism" in GAP_0085_STRATEGY_MECHANISMS
    assert "exit_mechanism" in GAP_0085_STRATEGY_MECHANISMS
    assert "session_rule" in GAP_0085_STRATEGY_MECHANISMS
    named = parse_experiment_spec(
        data_ref="data:x",
        environment_ref="env:x",
        seed=1,
        model_and_harness_version={"model": "m", "harness": "h"},
        cost_assumptions={},
        resolved_config_ref=_fp("cfg"),
        mechanisms={"ExitMechanism": {}},
    )
    assert is_refusal(named)
    assert named.context["field"] == "mechanisms"


def test_money_path_field_level_diff_still_never_fills_unset_fields() -> None:
    ancestor = {"note": "old"}
    proposed = {"sizing": "1R", "note": "new"}
    assert unset_money_path_fills(ancestor, proposed) == ("sizing",)
    allowed = {"sizing": "2R"}
    prior = {"sizing": "1R"}
    assert unset_money_path_fills(prior, allowed) == ()
