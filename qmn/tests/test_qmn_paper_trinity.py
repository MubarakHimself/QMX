"""Story 36.6 — node-paper remains COMP-QMN; no per-bot lane; QMA-paper absent."""

from __future__ import annotations

from qmf.core import AccountRole, World, is_ok, is_refusal
from qmn.paper import (
    FORBIDDEN_PER_BOT_PAPER_SURFACES,
    NODE_PAPER_ACCOUNT_ROLE,
    NODE_PAPER_NOUN,
    NODE_PAPER_OWNER,
    NODE_PAPER_WORLD,
    QMA_PAPER_EXISTS,
    RESEARCH_PAPER_NOUN,
    name_node_paper,
    refuse_per_bot_paper_lane,
)


def test_node_paper_is_demo_live_book_routing() -> None:
    named = name_node_paper()
    assert is_ok(named)
    assert named.value == NODE_PAPER_NOUN
    assert NODE_PAPER_OWNER == "COMP-QMN"
    assert NODE_PAPER_ACCOUNT_ROLE is AccountRole.DEMO
    assert NODE_PAPER_WORLD is World.LIVE
    assert QMA_PAPER_EXISTS is False


def test_research_paper_and_qma_paper_are_not_node_paper() -> None:
    research = name_node_paper(noun=RESEARCH_PAPER_NOUN)
    assert is_refusal(research)
    qma = name_node_paper(noun="qma-paper")
    assert is_refusal(qma)
    per_bot = refuse_per_bot_paper_lane("per-bot-paper-lane")
    assert is_refusal(per_bot)
    assert "per-bot-paper-lane" in FORBIDDEN_PER_BOT_PAPER_SURFACES
