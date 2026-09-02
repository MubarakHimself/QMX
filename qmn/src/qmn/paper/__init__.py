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
from qmn.paper.first_deployment import (
    DECLARED_FAULT_INJECTION_POINTS,
    DEMO_SHAPE_MACHINERY,
    DEMO_SHAPE_NODE_TIMERS,
    DEMO_SHAPE_UNITS,
    FAULT_INJECTION_MODE,
    FIRST_DEPLOYMENT_BOOK_ROUTING,
    FIRST_DEPLOYMENT_SURFACE,
    LATE_LIVE_APPROVAL_DELAYS,
    LIVE_SENSING_ALLOWED,
    LIVE_SENSING_FORBIDDEN,
    OPENS_LIVE_CREDENTIALS,
    PRE_UNATTENDED_PROOFS,
    PROCURES_VPS,
    FirstDeploymentWindow,
    LiveSensingAdmission,
    PreUnattendedProof,
    admit_live_sensing,
    begin_unattended_interval,
    compose_first_deployment_window,
    record_pre_unattended_proofs,
    refuse_continuous_supervision,
    refuse_first_deployment_live_authority,
    refuse_late_approval_blocks_demo,
    refuse_open_live_credentials,
    refuse_procure_vps,
    require_first_deployment_book_routing,
    resolve_first_deployment_execution_target,
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
    "DECLARED_FAULT_INJECTION_POINTS",
    "DEMO_SHAPE_MACHINERY",
    "DEMO_SHAPE_NODE_TIMERS",
    "DEMO_SHAPE_UNITS",
    "FAULT_INJECTION_MODE",
    "FIRST_DEPLOYMENT_BOOK_ROUTING",
    "FIRST_DEPLOYMENT_SURFACE",
    "FORBIDDEN_PER_BOT_PAPER_SURFACES",
    "LATE_LIVE_APPROVAL_DELAYS",
    "LIVE_OUTAGE_ALARM_CLASS",
    "LIVE_SENSING_ALLOWED",
    "LIVE_SENSING_FORBIDDEN",
    "MARKET_RISK_BLOCK_KINDS",
    "NODE_PAPER_ACCOUNT_ROLE",
    "NODE_PAPER_WORLD",
    "OPENS_LIVE_CREDENTIALS",
    "OPERATOR_PAPER_FLIP_TRIGGER",
    "PAPER_OUTAGE_ALARM_CLASS",
    "PAPER_SURFACE",
    "POST_ACTIVATION_PAPER_ROUTE",
    "PRE_UNATTENDED_PROOFS",
    "PROCURES_VPS",
    "BotNodeJourney",
    "FirstDeploymentWindow",
    "LiveSensingAdmission",
    "MarketRiskBlockKind",
    "PairedDemoBinding",
    "PaperFlipPackage",
    "PaperOutageAlarm",
    "PreUnattendedProof",
    "ProtectiveDemotionKind",
    "active_control_for_demotion",
    "active_control_for_market_risk",
    "admit_live_sensing",
    "begin_unattended_interval",
    "build_paired_demo_target",
    "compose_first_deployment_window",
    "fold_book_mode",
    "inspect_bot_node_journey",
    "mint_operator_paper_flip",
    "raise_paper_outage_alarm",
    "record_pre_unattended_proofs",
    "refuse_continuous_supervision",
    "refuse_first_deployment_live_authority",
    "refuse_late_approval_blocks_demo",
    "refuse_open_live_credentials",
    "refuse_per_bot_paper_lane",
    "refuse_procure_vps",
    "require_demo_paper_target",
    "require_first_deployment_book_routing",
    "resolve_book_execution_target",
    "resolve_first_deployment_execution_target",
    "route_protective_demotion",
]

PAPER_SURFACE: Final[str] = "qmn.paper"
