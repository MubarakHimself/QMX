"""L1/L3 — the FR-048 / CT-33 Bot-mint gate (AR-64, DEC-0178/0176/0174).

Requirement (FR-048): the Bot kind (CT-33) registers ONLY after both QL-8 conformance
layers pass, else `policy rejection`; a registered Bot fp1 is over semantic content
only; a `strategy_family_id` cardinality != exactly one is `invalid input`.

Epic 2 owns this kind (per the lane brief's requirements binding). These tests assert
the requirement against the package's public surface. CT-33 is `wiring_status:
defined-unwired`; if qmf.registry ships NO bot-definition mint path at all, the ratified
surface is unrealized here and E2-L1-17..20 / E2-L3-09 stand as a COVERAGE-GAP finding
(not a pass, and not a manufactured-fixture pass either) — exactly as the plan's
untestable note #2 anticipated.
"""

from __future__ import annotations

import qmf.registry as registry
from qmf.registry import KindRegistry, RESERVED_KIND_NAMES

import helpers as h

# The names/tokens the FR-048/CT-33 bot-mint surface would expose if realized.
_BOT_MINT_TOKENS = (
    "bot", "conformance", "strategy_family", "footprint", "ql8", "ql_8", "ql-8",
)


def _public_bot_surface() -> list[str]:
    """Any public qmf.registry symbol that could be the CT-33 bot-mint gate."""
    names = getattr(registry, "__all__", None) or dir(registry)
    return [
        n for n in names
        if not n.startswith("_") and any(tok in n.lower() for tok in _BOT_MINT_TOKENS)
    ]


# The two permanently-red "surface exists" probes that lived here (E2-L1-17/18 and
# E2-L1-19/20) are DELETED by the 2026-08-27 fix round: their observation was
# accurate but filed against the wrong epic — epics.md assigns FR-048 to Epic 12,
# CT-33 is defined-unwired, and absence in qmf-registry is the ratified build
# order (superseded by FC-05 / OR-06: the unauthorized qml wiring was removed and
# the dated Bot-kind mint will be built at the QMB composition root under AD-25).
# A red test cannot prove a ratified absence; the wiring-absence pin lives in
# qa/tests/epic_12/test_l3_example_bot.py.
