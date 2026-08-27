"""L1 — unit assertions for the human-signed promotion gate (FR-009, P0-5).

E2-L1-11  a live-promotion request with NO signed card does not promote (FM-4)  (P0-5)
E2-L1-12  a card missing its mandatory plain_words_summary is rejected           (P0-5)
E2-L1-13  only-a-human-promotes: the reserved promotion kind cannot be minted
          through the generic (agent-reachable) registration path (L17/AR-39)    (P0-5)
E2-L1-14  the plain_words_summary is identity-bearing => a different summary => a
          different card fp1
E2-L1-15  the attested template fp1 is an identity field => changing it mints a
          NEW card, and a card can never authorize under a superseded template
E2-L1-16  every registry public op returns value-or-refusal (CT-04), never raises
"""

from __future__ import annotations

from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.registry import (
    KIND_PROMOTION_OCCURRENCE_CARD,
    RESERVED_KIND_NAMES,
    KindRegistry,
    PromotionCard,
    RegistrationRecord,
    authorize_live_promotion,
    persistence_fingerprint,
)
from qmf.registry.lineage import LineageEdge

import helpers as h

_SEVEN = {c.value for c in RefusalCategory}


def _card(summary: str = "Promote strategy X to live with a 0.5% risk cap.",
          attested: object = None, template: object = None,
          signer: str = "operator:mubarak") -> PromotionCard:
    got = PromotionCard.sign(
        signer=signer,
        plain_words_summary=summary,
        attested_fp1=attested if attested is not None else h.fp("record-under-review").value,
        writer=h.writer(),
        sequence=0,
        signed_at=h.instant(),
        template_definition_fp1=template,
    )
    return h.unwrap(got, "sign card")


# --- E2-L1-11 (P0) : no card => no promotion ----------------------------------


def test_e2_l1_11_no_card_does_not_promote() -> None:
    target = h.fp("artifact").value
    out = authorize_live_promotion(target_fp1=target, card=None, superseded=[])
    assert is_refusal(out)
    assert out.category is RefusalCategory.POLICY_REJECTION  # status unchanged, no live cap


# --- E2-L1-12 (P0) : missing mandatory summary => rejected --------------------


def test_e2_l1_12_missing_summary_is_rejected() -> None:
    for blank in (None, "", "   "):
        out = PromotionCard.sign(
            signer="operator:mubarak", plain_words_summary=blank,
            attested_fp1=h.fp("r").value, writer=h.writer(), sequence=0, signed_at=h.instant(),
        )
        assert is_refusal(out), f"blank summary accepted: {blank!r}"
        assert out.context.get("field") == "plain_words_summary"


# --- E2-L1-13 (P0) : only a human promotes — the reserved kind is un-forgeable --
# The registry enforces L17 by making the promotion-occurrence card a RESERVED kind
# the generic (agent-reachable) registration surface can neither register nor mint.
# (Human-identity of the signer string is platform territory, DEC-0116; the registry
# gate is the reserved-kind wall exercised here.)


def test_e2_l1_13_reserved_kind_cannot_be_minted_via_generic_factory() -> None:
    assert KIND_PROMOTION_OCCURRENCE_CARD in RESERVED_KIND_NAMES
    out = RegistrationRecord.try_create(
        KIND_PROMOTION_OCCURRENCE_CARD, 1, [], {"signer": "agent:bot"},
        h.writer(), 0, h.instant(),
    )
    assert is_refusal(out)
    assert out.context.get("reserved") is True


def test_e2_l1_13_reserved_kind_cannot_be_registered_in_kind_registry() -> None:
    reg = KindRegistry()
    from qmf.registry import FieldSetKind
    contract = h.unwrap(
        FieldSetKind.try_create(KIND_PROMOTION_OCCURRENCE_CARD, 1, (), ("signer",)),
        "contract",
    )
    out = reg.register(contract)
    assert is_refusal(out)
    assert out.context.get("reserved") is True


# --- E2-L1-14 (P0) : the summary is identity-bearing --------------------------


def test_e2_l1_14_different_summary_is_a_different_card_fp1() -> None:
    attested = h.fp("same-record").value
    a = _card(summary="Promote X to live, 0.5% cap.", attested=attested)
    b = _card(summary="Promote X to live, 1.0% cap.", attested=attested)
    assert a.plain_words_summary != b.plain_words_summary
    assert a.stable_id != b.stable_id  # the signature attests the exact words read


# --- E2-L1-15 (P0) : attested template fp1 is an identity field ----------------


def test_e2_l1_15_changing_attested_template_mints_a_new_card() -> None:
    attested = h.fp("admission").value
    t1 = h.fp("book-def-v1").value
    t2 = h.fp("book-def-v2").value
    c1 = _card(attested=attested, template=t1)
    c2 = _card(attested=attested, template=t2)
    assert c1.stable_id != c2.stable_id  # a signature can never attest a superseded template


def test_e2_l1_15_superseded_template_does_not_authorize_crossing() -> None:
    attested = h.fp("admission").value
    old_template = h.fp("book-def-v1").value
    in_force = h.fp("book-def-v2").value
    card = _card(attested=attested, template=old_template)
    out = authorize_live_promotion(
        target_fp1=attested, card=card, superseded=[], in_force_template_fp1=in_force
    )
    assert is_refusal(out)
    assert out.category is RefusalCategory.POLICY_REJECTION


def test_e2_l1_15_absent_in_force_template_is_refused_never_skipped() -> None:
    attested = h.fp("admission").value
    card = _card(attested=attested, template=h.fp("book-def-v1").value)
    # A card that attests a template but no in-force template supplied => refuse, never skip.
    out = authorize_live_promotion(target_fp1=attested, card=card, superseded=[])
    assert is_refusal(out)
    assert out.category is RefusalCategory.POLICY_REJECTION


# --- E2-L1-16 (P1) : value-or-refusal across the whole public surface ----------


def test_e2_l1_16_public_ops_return_typed_refusals_never_raise() -> None:
    from qmf.registry import EdgeLog, EdgeType, RegistryPersistence

    # Each of these public entry points is driven with bad input; each must RETURN a
    # CT-04 TypedRefusal whose category is one of the seven, and must not raise.
    probes = [
        h.registrar().register(kind="unknown", body={"id": "x"}, writer=h.writer(),
                               sequence=0, created_at=h.instant()),
        LineageEdge.try_create("bad-type", h.fp("a"), h.fp("b"), h.writer()),
        EdgeLog(h.writer()).append(edge_type=EdgeType.SUPERSEDES, from_ref="nope", to_ref=h.fp("b")),
        PromotionCard.sign(signer="", plain_words_summary="s", attested_fp1=h.fp("r").value,
                           writer=h.writer(), sequence=0, signed_at=h.instant()),
        authorize_live_promotion(target_fp1=h.fp("t").value, card=None, superseded=[]),
        persistence_fingerprint({"not": "a record"}),
        RegistryPersistence.open(object(), "live"),
    ]
    for out in probes:
        assert is_refusal(out), f"expected a returned refusal, got {out!r}"
        assert out.category.value in _SEVEN
        assert out.context is not None
