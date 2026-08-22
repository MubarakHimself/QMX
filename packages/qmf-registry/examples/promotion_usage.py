"""Reference usage — the human-signed promotion occurrence (COMP-QMF-REGISTRY).

Executable::

    python packages/qmf-registry/examples/promotion_usage.py

Shows the six things Story 2.3 pins down:

1. A human-signed promotion-occurrence card: a human-only signer, a mandatory plain-words
   summary declared an identity field, the attested record's fp1, and a stable id DERIVED
   from the card's fp1 fingerprint. V1 signing is the operator's recorded approval — no
   cryptographic dependency.
2. The live-promotion refusal law: with no human-signed card present, promotion does not
   occur (a typed refusal, FM-4); a present card attesting the record authorizes it.
3. Correcting the plain-words summary mints a NEW card linked to the prior card with a
   CT-07 supersedes edge — the signed record is never edited in place.
4. A card attesting an AD-32 risk admission carries the Book-definition (or BMS-definition)
   fingerprint as an identity field, so a signature can never attest a superseded template
   (a different template derives a different card fp1).
5. The CT-13 promotion event carries ONLY the card's fp1 fingerprint plus correlation_id —
   never a second schema; it is emitted through the core JournalSink seam and the registry
   card stays canonical.
6. Every fp1 fingerprint is computed in qmf-core; this example uses qmf.registry, whose
   promotion module imports only qmf.core and its own package siblings.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Fingerprint,
    Instant,
    Ok,
    Result,
    SinkAck,
    SinkResult,
    TypedRefusal,
    WriterId,
    fingerprint,
    is_ok,
)
from qmf.registry import (
    EdgeType,
    PromotionCard,
    PromotionEvent,
    authorize_live_promotion,
    correct_summary,
    emit_promotion_event,
)

T = TypeVar("T")

_SIGNED_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _writer(machine: str) -> WriterId:
    return _unwrap(WriterId.try_create(machine, "authoring", "promotion", "boot-1"), "writer")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _rec(tag: str) -> Fingerprint:
    """A stand-in fp1 fingerprint for a registered record."""
    return _unwrap(fingerprint({"rec": tag}), f"record {tag}")


class _RecordingJournalSink:
    """A demo JournalSink that records what it is handed (the real sink is wired at the
    composition root and maps the event onto qmf-data's JournalEvent in Story 2.4)."""

    def __init__(self) -> None:
        self.appended: list[PromotionEvent] = []

    def append(self, event: PromotionEvent, /) -> SinkResult:
        self.appended.append(event)
        return Ok(SinkAck())


def signed_card_has_a_derived_id() -> PromotionCard:
    """A human-signed card whose stable id is derived from its fp1 identity."""
    card = _unwrap(
        PromotionCard.sign(
            signer="operator:mubarak",
            plain_words_summary="Promote the EURUSD scalping bot to live after paper review.",
            attested_fp1=_rec("bot-under-review"),
            writer=_writer("node-a"),
            sequence=0,
            signed_at=_instant(_SIGNED_NS),
        ),
        "signed card",
    )
    # The id is derived, not minted: the card IS a canonical CT-06 record whose stable id
    # equals the fingerprint of its identity content.
    assert card.stable_id == _unwrap(fingerprint(card.record.fp1_identity()), "derived id")
    assert card.stable_id.value.startswith("fp1:sha256:")
    assert card.kind == "promotion-occurrence-card"
    # The plain-words summary is an identity field; the signed-at instant is not.
    assert card.record.fp1_identity()["body"] == {
        "signer": "operator:mubarak",
        "plain_words_summary": "Promote the EURUSD scalping bot to live after paper review.",
        "attested_fp1": card.attested_fp1.value,
    }
    return card


def no_card_refuses_but_a_signed_card_authorizes() -> tuple[str, str]:
    """The refusal law: no card => promotion does not occur; a signed card authorizes."""
    target = _rec("bot-under-review")
    no_card = authorize_live_promotion(target_fp1=target, card=None)
    assert isinstance(no_card, TypedRefusal)  # FM-4: only a human promotes into live
    card = signed_card_has_a_derived_id()
    authorized = _unwrap(
        authorize_live_promotion(target_fp1=target, card=card), "authorized promotion"
    )
    assert authorized.card is card
    assert authorized.attested_fp1 == target
    # A card attesting a DIFFERENT record does not authorize this one.
    wrong = authorize_live_promotion(target_fp1=_rec("some-other-record"), card=card)
    assert isinstance(wrong, TypedRefusal)
    return no_card.category.value, wrong.category.value


def correcting_the_summary_mints_a_new_card() -> tuple[str, str]:
    """A typo fix mints a NEW card + a CT-07 supersedes edge; the prior card is untouched."""
    prior = signed_card_has_a_derived_id()
    correction = _unwrap(
        correct_summary(
            prior,
            "Promote the EUR/USD scalping bot to live after paper review.",
            writer=_writer("node-a"),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
        ),
        "summary correction",
    )
    new_card = correction.corrected_card
    edge = correction.supersedes_edge
    # The new card has a different id (the summary is an identity field); the prior card is
    # unchanged, and the supersedes edge links new -> prior.
    assert new_card.stable_id != prior.stable_id
    assert edge.edge_type is EdgeType.SUPERSEDES
    assert edge.from_ref == new_card.stable_id
    assert edge.to_ref == prior.stable_id
    assert prior.plain_words_summary.endswith("paper review.")
    return prior.stable_id.value, new_card.stable_id.value


def risk_admission_card_binds_the_template_fingerprint() -> bool:
    """A card attesting an AD-32 admission carries the Book/BMS-definition fp as identity."""
    common = {
        "signer": "operator:mubarak",
        "plain_words_summary": "Admit the scalping Book charter v1 to live.",
        "attested_fp1": _rec("book-admission"),
        "writer": _writer("node-a"),
        "sequence": 0,
        "signed_at": _instant(_SIGNED_NS),
    }
    on_v1 = _unwrap(
        PromotionCard.sign(template_definition_fp1=_rec("book-definition-v1"), **common),
        "card on template v1",
    )
    on_v2 = _unwrap(
        PromotionCard.sign(template_definition_fp1=_rec("book-definition-v2"), **common),
        "card on template v2",
    )
    # The template fingerprint is an identity field, so a signature over a superseded
    # template can never stand for the new one: different template => different card fp1.
    return on_v1.stable_id != on_v2.stable_id


def promotion_event_is_only_a_pointer() -> tuple[str, int]:
    """The CT-13 promotion event carries ONLY the card fp1 + correlation_id, canonical."""
    card = signed_card_has_a_derived_id()
    sink = _RecordingJournalSink()
    ack = emit_promotion_event(sink, card=card, correlation_id="corr-42")
    assert is_ok(ack)
    event = sink.appended[0]
    # Only a pointer to the canonical registry card: the payload carries just the fp1.
    assert event.promotion_card_fp1 == card.stable_id
    assert event.correlation_id == "corr-42"
    assert event.journal_payload() == {"promotion_card_fp1": card.stable_id.value}
    return event.promotion_card_fp1.value, len(sink.appended)


def main() -> None:
    card = signed_card_has_a_derived_id()
    print(f"signed card, derived id: {card.stable_id.value[:19]}...")

    no_card_category, wrong_category = no_card_refuses_but_a_signed_card_authorizes()
    print(f"no card present, promotion refused: {no_card_category}")
    print(f"card attesting another record refused: {wrong_category}")

    prior_id, new_id = correcting_the_summary_mints_a_new_card()
    print(f"summary correction mints a new card: {prior_id != new_id}")

    template_bound = risk_admission_card_binds_the_template_fingerprint()
    print(f"risk-admission card binds the template fingerprint: {template_bound}")

    event_fp1, appended = promotion_event_is_only_a_pointer()
    print(f"promotion event is only a pointer to the card: {event_fp1[:19]}...")
    print(f"promotion event emitted through the JournalSink: {appended}")


if __name__ == "__main__":
    main()
