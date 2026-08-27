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


def test_e2_l1_17_18_bot_kind_both_conformance_layers_gate_exists() -> None:
    """FR-048/AR-64: a Bot-kind registration path gated on both QL-8 conformance-layer
    verdicts must exist so a Bot mints ONLY when both pass (else policy rejection). No
    such public path exists in qmf.registry — the ratified surface is unrealized here."""
    surface = _public_bot_surface()
    # 'bot-definition' is not a reserved kind and there is no mint gate exposed.
    assert "bot-definition" not in {k for k in RESERVED_KIND_NAMES}
    assert surface, (
        "COVERAGE GAP (E2-L1-17/18): no FR-048/CT-33 bot-mint gate is exposed by "
        "qmf.registry (no both-conformance-layers mint path, no policy-rejection-on-fail). "
        "CT-33 is defined-unwired and unrealized in this package; the ratified surface "
        "cannot be exercised, not even with injected verdicts."
    )


def test_e2_l1_19_20_ct33_bot_definition_kind_and_cardinality_exist() -> None:
    """FR-048/CT-33/DEC-0176: a `bot-definition` kind whose `strategy_family_id`
    cardinality must be exactly one (else `invalid input`) must be registrable. No
    bot-definition contract or kind is present in qmf.registry's KindRegistry surface."""
    reg = KindRegistry()
    # A realized surface would register or resolve a 'bot-definition' kind; the generic
    # registry knows nothing of it, and no dedicated bot contract ships.
    resolved = reg.contract_for("bot-definition")
    from qmf.core import is_refusal
    assert is_refusal(resolved)  # unknown kind — confirms the kind is unrealized
    # The FR-048 cardinality gate (strategy_family_id == exactly one) has no code to run.
    assert False, (
        "COVERAGE GAP (E2-L1-19/20, E2-L3-09): CT-33 bot-definition is defined-unwired — "
        "no kind, no both-layers mint gate, no strategy_family_id cardinality rule, and no "
        "producer-binding transitive-union rule exists in qmf.registry to test. FR-048's "
        "registry surface is unrealized in Epic 2 (QML authors the declaration; the "
        "composition root mints under AD-25)."
    )
