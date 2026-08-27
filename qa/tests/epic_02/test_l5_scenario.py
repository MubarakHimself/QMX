"""L5 — the SCN-0007 acceptance chain: an agent cannot promote an artifact to live.

E2-L5-01 (P0):
  Given a research artifact (fp1 + lineage) and an agent reporting its checks passed,
  When the agent attempts to move it from research to live,
  Then the status does not change and no live capability is granted; only a human-signed
  promotion occurrence attesting the card's fp1 (plain-words summary + Book-definition
  fp as identity fields) can authorize the crossing; a summary typo-fix mints a NEW card
  with a `supersedes` edge; and passing any number of agent-run checks cannot substitute
  for human authorization.  (P0-5, FR-009, SCN-0007, L17)
"""

from __future__ import annotations

from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.registry import (
    KIND_PROMOTION_OCCURRENCE_CARD,
    EdgeType,
    PromotionCard,
    RegistrationRecord,
    authorize_live_promotion,
    correct_summary,
)

import helpers as h


def test_e2_l5_01_agent_cannot_promote_only_a_human_card_can(tmp_path) -> None:
    # Given: a research artifact with a proposed fp1 and lineage.
    artifact = h.record({"id": "strategy-x", "period": 20})
    target = artifact.stable_id
    book_def = h.fp("book-definition-v1").value

    # When: the agent reports "checks passed" and attempts to move research -> live.
    # An agent's run is not an operator ruling — there is no signed card, so the gate refuses.
    for _agent_checks_passed in range(5):  # any number of agent-run checks
        attempt = authorize_live_promotion(target_fp1=target, card=None, superseded=[])
        assert is_refusal(attempt)
        # Then: status does not change, no live capability granted.
        assert attempt.category is RefusalCategory.POLICY_REJECTION

    # An agent also cannot FORGE the promotion-occurrence card through the generic path.
    forged = RegistrationRecord.try_create(
        KIND_PROMOTION_OCCURRENCE_CARD, 1, [], {"signer": "agent:bot-7"},
        h.writer(role="agent"), 0, h.instant(),
    )
    assert is_refusal(forged)

    # Only a human-signed, current card attesting the record's fp1 authorizes the crossing.
    card = h.unwrap(
        PromotionCard.sign(
            signer="operator:mubarak",
            plain_words_summary="Promote strategy X to live with a 0.5% risk cap.",
            attested_fp1=target,
            writer=h.writer(),
            sequence=0,
            signed_at=h.instant(),
            template_definition_fp1=book_def,
        ),
        "sign",
    )
    authorized = authorize_live_promotion(
        target_fp1=target, card=card, superseded=[], in_force_template_fp1=book_def
    )
    assert is_ok(authorized)
    assert authorized.value.card.stable_id == card.stable_id

    # A summary typo-fix mints a NEW card (different fp1) linked by a `supersedes` edge —
    # the signed record is never edited in place.
    correction = h.unwrap(
        correct_summary(
            card,
            "Promote strategy X to live with a 0.50% risk cap.",  # typo fix
            signer="operator:mubarak",
            writer=h.writer(),
            sequence=1,
            signed_at=h.instant(1_700_000_000_000_000_001),
        ),
        "correct",
    )
    new_card = correction.corrected_card
    edge = correction.supersedes_edge
    assert new_card.stable_id != card.stable_id
    assert edge.edge_type is EdgeType.SUPERSEDES
    assert edge.from_ref == new_card.stable_id
    assert edge.to_ref == card.stable_id

    # Once superseded, the PRIOR card no longer speaks for the crossing (only the current head).
    stale = authorize_live_promotion(
        target_fp1=target, card=card, superseded=[card.stable_id],
        in_force_template_fp1=book_def,
    )
    assert is_refusal(stale)
    assert stale.category is RefusalCategory.POLICY_REJECTION

    # The corrected (current) card authorizes — it attests the same artifact fp1.
    fresh = authorize_live_promotion(
        target_fp1=target, card=new_card, superseded=[card.stable_id],
        in_force_template_fp1=book_def,
    )
    assert is_ok(fresh)
