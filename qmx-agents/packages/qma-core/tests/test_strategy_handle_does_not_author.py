"""Story 38.1 — StrategyHandle stays on the reference/register side of the line."""

from __future__ import annotations

from pathlib import Path

from qma.core.ports.experiments import GAP_0085_STRATEGY_MECHANISMS, parse_experiment_spec
from qma.core.ports.handles import StrategyCandidate
from qma.core.vocabulary.handles import QMA_OWNED_CANDIDATE_ORIGIN, STRATEGY_CANDIDATE_ZONE
from qmf.core import is_ok, is_refusal

CORE_SRC = Path(__file__).resolve().parents[1] / "src"


def _fp(tag: str) -> str:
    return f"fp1:sha256:{tag:0<64}"


def test_strategy_handle_requires_an_already_fingerprinted_payload() -> None:
    minted = StrategyCandidate.try_create(
        origin=QMA_OWNED_CANDIDATE_ORIGIN,
        zone=STRATEGY_CANDIDATE_ZONE,
        payload_fp1=_fp("already-minted-by-qml"),
        stable_id="cand-1",
        handle_id="h:StrategyHandle:1",
        money_path_relevant=False,
        lineage_predecessor=_fp("predecessor"),
    )
    assert is_ok(minted)
    assert minted.value.payload_fp1.startswith("fp1:")
    assembled = StrategyCandidate.try_create(
        origin=QMA_OWNED_CANDIDATE_ORIGIN,
        zone=STRATEGY_CANDIDATE_ZONE,
        payload_fp1={"kind": "bot-definition", "body": {"strategy_family_id": "trend"}},
        stable_id="cand-2",
        handle_id="h:StrategyHandle:1",
        money_path_relevant=False,
    )
    assert is_refusal(assembled)
    assert assembled.context["field"] == "payload_fp1"


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
