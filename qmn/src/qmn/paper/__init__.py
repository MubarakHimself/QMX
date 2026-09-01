"""Book-level paper mode and protective demotions (TN-9; Story 26.5).

Paper is one explicit Book routing state plus protective demotion — never a
per-bot warm-up, probation, ramp, or paper lane. An operator-signed CT-24
transition routes a Book to exactly one paired demo account (role ``demo``,
``world = live``) with its own BMS, paper epoch, and virtual-ledger binding.
Capital/authority demotions route to that target; market-risk windows and KSA
block paper and live alike; a silent paper outage raises the live alarm class
(FR-058; DEC-0149, DEC-0194, DEC-0261; SCN-0006).
"""

from __future__ import annotations

from typing import Final

from qmn.paper.demotion import (
    CAPITAL_AUTHORITY_DEMOTION_KINDS,
    LIVE_OUTAGE_ALARM_CLASS,
    MARKET_RISK_BLOCK_KINDS,
    PAPER_OUTAGE_ALARM_CLASS,
    MarketRiskBlockKind,
    PaperOutageAlarm,
    ProtectiveDemotionKind,
    active_control_for_demotion,
    active_control_for_market_risk,
    raise_paper_outage_alarm,
    route_protective_demotion,
)
from qmn.paper.lane import (
    FORBIDDEN_PER_BOT_PAPER_SURFACES,
    POST_ACTIVATION_PAPER_ROUTE,
    BotNodeJourney,
    inspect_bot_node_journey,
    refuse_per_bot_paper_lane,
)
from qmn.paper.routing import (
    NODE_PAPER_ACCOUNT_ROLE,
    NODE_PAPER_WORLD,
    PairedDemoBinding,
    build_paired_demo_target,
    require_demo_paper_target,
    resolve_book_execution_target,
)
from qmn.paper.transition import (
    OPERATOR_PAPER_FLIP_TRIGGER,
    PaperFlipPackage,
    fold_book_mode,
    mint_operator_paper_flip,
)

__all__ = [
    "CAPITAL_AUTHORITY_DEMOTION_KINDS",
    "FORBIDDEN_PER_BOT_PAPER_SURFACES",
    "LIVE_OUTAGE_ALARM_CLASS",
    "MARKET_RISK_BLOCK_KINDS",
    "NODE_PAPER_ACCOUNT_ROLE",
    "NODE_PAPER_WORLD",
    "OPERATOR_PAPER_FLIP_TRIGGER",
    "PAPER_OUTAGE_ALARM_CLASS",
    "PAPER_SURFACE",
    "POST_ACTIVATION_PAPER_ROUTE",
    "BotNodeJourney",
    "MarketRiskBlockKind",
    "PairedDemoBinding",
    "PaperFlipPackage",
    "PaperOutageAlarm",
    "ProtectiveDemotionKind",
    "active_control_for_demotion",
    "active_control_for_market_risk",
    "build_paired_demo_target",
    "fold_book_mode",
    "inspect_bot_node_journey",
    "mint_operator_paper_flip",
    "raise_paper_outage_alarm",
    "refuse_per_bot_paper_lane",
    "require_demo_paper_target",
    "resolve_book_execution_target",
    "route_protective_demotion",
]

PAPER_SURFACE: Final[str] = "qmn.paper"
