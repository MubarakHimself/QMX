"""Contract test — the human-signed promotion occurrence (Story 2.3).

The Tier-1 contract test for the CT-06 promotion-card and CT-13 promotion-event boundary.
Each acceptance criterion is asserted against the real promotion types, with every ``fp1``
fingerprint computed by qmf-core:

* AC1 — a promotion-occurrence card is minted with a human-only signer, a signed immutable
  record, a mandatory plain-words summary declared an identity field, the attested record's
  fp1, reviewer identity, and instant; V1 signing is the operator's recorded approval, no
  cryptographic dependency.
* AC2 — a live-promotion request with no human-signed card present does not occur; a typed
  refusal is returned (FM-4) — only a human promotes into the live zone.
* AC3 — correcting the plain-words summary mints a NEW card linked to the prior via a CT-07
  supersedes edge; the signed record is never edited in place (FM-5).
* AC4 — the promotion journal event is the CT-13 promotion event carrying ONLY the card's
  fp1 fingerprint plus correlation_id; the registry card is canonical.
* AC5 — a card attesting an AD-32 risk admission carries the Book/BMS-definition fingerprint
  as an identity field, so a signature can never attest a superseded template.
* AC6 — the promotion module imports only qmf.core and its own package siblings.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Fingerprint,
    Instant,
    JournalSink,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SinkAck,
    SinkResult,
    TypedRefusal,
    WriterId,
    fingerprint,
    is_ok,
    is_unpersistable,
    unpersistable,
)
from qmf.registry import (
    RESERVED_KIND_NAMES,
    EdgeType,
    LineageEdge,
    PromotionAuthorization,
    PromotionCard,
    PromotionCorrection,
    PromotionEvent,
    RegistrationRecord,
    authorize_live_promotion,
    correct_summary,
    emit_promotion_event,
)
from qmf.registry import promotion as promotion_module
from qmf.registry.promotion import (
    KIND_PROMOTION_OCCURRENCE_CARD,
    PROMOTION_CARD_CONTRACT_FORMAT_VERSION,
)
from qmf.registry.records import is_genuine_reserved_record

_SIGNED_NS = 1_700_000_000_000_000_000

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _writer(machine: str = "node-a", stream: str = "promotion") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", stream, "boot-1"))


def _instant(ns: int = _SIGNED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _rec(tag: object) -> Fingerprint:
    return _ok(fingerprint({"rec": tag}))


def _card(**overrides: object) -> PromotionCard:
    args: dict[str, object] = {
        "signer": "operator:mubarak",
        "plain_words_summary": "Promote the EURUSD scalping bot to live.",
        "attested_fp1": _rec("bot"),
        "writer": _writer(),
        "sequence": 0,
        "signed_at": _instant(),
    }
    args.update(overrides)
    return _ok(PromotionCard.sign(**args))  # type: ignore[arg-type]


def _refused(result: object, field: str, category: RefusalCategory) -> TypedRefusal:
    assert isinstance(result, TypedRefusal), result
    assert result.category is category, result
    assert result.context["field"] == field, result
    return result


# --- AC1: the human-signed promotion-occurrence card ------------------------


def test_card_is_the_reserved_ct06_kind() -> None:
    # The card mints the reserved kind name honored by the generic path (which refuses it).
    assert KIND_PROMOTION_OCCURRENCE_CARD == "promotion-occurrence-card"
    assert KIND_PROMOTION_OCCURRENCE_CARD in RESERVED_KIND_NAMES
    card = _card()
    assert card.kind == KIND_PROMOTION_OCCURRENCE_CARD
    assert isinstance(card.record, RegistrationRecord)
    assert card.record.contract_format_version == PROMOTION_CARD_CONTRACT_FORMAT_VERSION


def test_card_carries_signer_summary_attested_and_instant() -> None:
    card = _card()
    assert card.signer == "operator:mubarak"
    assert card.plain_words_summary == "Promote the EURUSD scalping bot to live."
    assert card.attested_fp1 == _rec("bot")
    assert card.template_definition_fp1 is None
    assert card.signed_at == _instant()
    assert card.writer == _writer()
    assert card.sequence == 0


def test_stable_id_is_derived_from_the_card_identity() -> None:
    card = _card()
    assert card.stable_id.value.startswith("fp1:sha256:")
    # The card IS a canonical CT-06 record; its stable id equals the fingerprint of the
    # identity content (computed by qmf-core), never minted.
    assert card.stable_id == card.record.stable_id
    assert card.stable_id == _ok(fingerprint(card.record.fp1_identity()))


def test_summary_is_an_identity_field() -> None:
    base = _card()
    other = _card(plain_words_summary="Promote the EURUSD scalping bot to live now.")
    # The plain-words summary is an identity field: a different summary is a different card.
    assert other.stable_id != base.stable_id


def test_signer_and_attested_are_identity_fields() -> None:
    base = _card()
    other_signer = _card(signer="operator:someone-else")
    other_attested = _card(attested_fp1=_rec("different-bot"))
    assert other_signer.stable_id != base.stable_id
    assert other_attested.stable_id != base.stable_id


def test_signed_at_writer_and_sequence_are_excluded_from_identity() -> None:
    # Two recorded approvals of the exact same words for the same record, differing only in
    # occurrence facts, dedup to one identity (the same occurrence/identity split records use).
    a = _card(writer=_writer("node-a"), sequence=0, signed_at=_instant(_SIGNED_NS))
    b = _card(writer=_writer("node-b"), sequence=9, signed_at=_instant(_SIGNED_NS + 500))
    assert a.writer != b.writer
    assert a.sequence != b.sequence
    assert a.signed_at != b.signed_at
    assert a.stable_id == b.stable_id


def test_card_identity_body_carries_only_declared_identity_fields() -> None:
    body = _card().record.fp1_identity()["body"]
    assert body == {
        "signer": "operator:mubarak",
        "plain_words_summary": "Promote the EURUSD scalping bot to live.",
        "attested_fp1": _rec("bot").value,
    }


def test_attested_fp1_accepts_a_fingerprint_string() -> None:
    card = _card(attested_fp1=_rec("bot").value)
    assert card.attested_fp1 == _rec("bot")


def test_attests_matches_only_the_attested_record() -> None:
    card = _card(attested_fp1=_rec("bot"))
    assert card.attests(_rec("bot"))
    assert card.attests(_rec("bot").value)
    assert not card.attests(_rec("other"))
    assert not card.attests("not-a-fingerprint")


def test_sign_refuses_bad_signer_summary_attested_and_signed_at() -> None:
    _refused(
        PromotionCard.sign(
            signer="  ",
            plain_words_summary="s",
            attested_fp1=_rec("b"),
            writer=_writer(),
            sequence=0,
            signed_at=_instant(),
        ),
        "signer",
        RefusalCategory.INVALID_INPUT,
    )
    _refused(
        PromotionCard.sign(
            signer="op",
            plain_words_summary="   ",
            attested_fp1=_rec("b"),
            writer=_writer(),
            sequence=0,
            signed_at=_instant(),
        ),
        "plain_words_summary",
        RefusalCategory.INVALID_INPUT,
    )
    _refused(
        PromotionCard.sign(
            signer="op",
            plain_words_summary="s",
            attested_fp1="minted-id-42",
            writer=_writer(),
            sequence=0,
            signed_at=_instant(),
        ),
        "attested_fp1",
        RefusalCategory.INVALID_INPUT,
    )
    _refused(
        PromotionCard.sign(
            signer="op",
            plain_words_summary="s",
            attested_fp1=_rec("b"),
            writer=_writer(),
            sequence=0,
            signed_at=1_700_000_000,
        ),
        "signed_at",
        RefusalCategory.INVALID_INPUT,
    )


def test_sign_propagates_record_header_refusal() -> None:
    # A bad writer is validated by the delegated RegistrationRecord factory (FM-1 family).
    _refused(
        PromotionCard.sign(
            signer="op",
            plain_words_summary="s",
            attested_fp1=_rec("b"),
            writer="node-a",
            sequence=0,
            signed_at=_instant(),
        ),
        "writer",
        RefusalCategory.INVALID_INPUT,
    )
    _refused(
        PromotionCard.sign(
            signer="op",
            plain_words_summary="s",
            attested_fp1=_rec("b"),
            writer=_writer(),
            sequence=-1,
            signed_at=_instant(),
        ),
        "sequence",
        RefusalCategory.INVALID_INPUT,
    )


# --- AC2: the live-promotion refusal law (FM-4) -----------------------------


def test_no_card_present_refuses_promotion() -> None:
    target = _rec("bot")
    refusal = _refused(
        authorize_live_promotion(target_fp1=target, card=None),
        "card",
        RefusalCategory.POLICY_REJECTION,
    )
    # FM-4: promotion does not occur; only a human promotes into the live zone.
    assert refusal.context["requested"] == target.value
    assert refusal.retryability is Retryability.NO


def test_signed_card_authorizes_the_exact_attested_record() -> None:
    target = _rec("bot")
    card = _card(attested_fp1=target)
    authorized = _ok(authorize_live_promotion(target_fp1=target, card=card))
    assert isinstance(authorized, PromotionAuthorization)
    assert authorized.card is card
    assert authorized.attested_fp1 == target


def test_card_attesting_a_different_record_does_not_authorize() -> None:
    card = _card(attested_fp1=_rec("bot"))
    _refused(
        authorize_live_promotion(target_fp1=_rec("other-record"), card=card),
        "card",
        RefusalCategory.POLICY_REJECTION,
    )


def test_gate_refuses_bad_target_and_non_card() -> None:
    _refused(
        authorize_live_promotion(target_fp1="not-a-fingerprint", card=_card()),
        "target_fp1",
        RefusalCategory.INVALID_INPUT,
    )
    _refused(
        authorize_live_promotion(target_fp1=_rec("bot"), card="not-a-card"),
        "card",
        RefusalCategory.INVALID_INPUT,
    )


# --- AC3: a correction is a new card + a supersedes edge (FM-5) --------------


def test_correcting_the_summary_mints_a_new_card_and_supersedes_edge() -> None:
    prior = _card(plain_words_summary="Promote the EURUSD scalping bot to live.")
    correction = _ok(
        correct_summary(
            prior,
            "Promote the EUR/USD scalping bot to live.",
            signer="operator:mubarak",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
        )
    )
    assert isinstance(correction, PromotionCorrection)
    new_card = correction.corrected_card
    edge = correction.supersedes_edge
    # A NEW card (different id, because the summary is an identity field), re-signed by the
    # human who read the corrected words, same attested record; the prior card is untouched.
    assert new_card.stable_id != prior.stable_id
    assert new_card.signer == "operator:mubarak"
    assert new_card.attested_fp1 == prior.attested_fp1
    assert prior.plain_words_summary == "Promote the EURUSD scalping bot to live."
    # The supersedes edge links new -> prior (a correction, never an in-place edit).
    assert isinstance(edge, LineageEdge)
    assert edge.edge_type is EdgeType.SUPERSEDES
    assert edge.from_ref == new_card.stable_id
    assert edge.to_ref == prior.stable_id
    assert edge.writer == _writer()


def test_correction_preserves_the_template_fingerprint() -> None:
    prior = _card(attested_fp1=_rec("book"), template_definition_fp1=_rec("book-def-v1"))
    correction = _ok(
        correct_summary(
            prior,
            "Admit the scalping Book charter v1 to live (typo fixed).",
            signer="operator:mubarak",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
        )
    )
    assert correction.corrected_card.template_definition_fp1 == _rec("book-def-v1")


def test_correction_uses_a_distinct_edge_writer_when_given() -> None:
    prior = _card()
    correction = _ok(
        correct_summary(
            prior,
            "A corrected summary of the promotion.",
            signer="operator:mubarak",
            writer=_writer("node-a"),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
            edge_writer=_writer("node-b", stream="lineage"),
        )
    )
    assert correction.supersedes_edge.writer == _writer("node-b", stream="lineage")


def test_correction_refuses_non_card_prior() -> None:
    _refused(
        correct_summary("not-a-card", "x", writer=_writer(), sequence=1, signed_at=_instant()),
        "prior",
        RefusalCategory.INVALID_INPUT,
    )


def test_correction_refuses_an_unchanged_summary() -> None:
    prior = _card(plain_words_summary="Same words.")
    _refused(
        correct_summary(
            prior,
            "Same words.",
            signer="operator:mubarak",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
        ),
        "plain_words_summary",
        RefusalCategory.INVALID_INPUT,
    )


def test_correction_propagates_a_bad_corrected_summary() -> None:
    prior = _card()
    _refused(
        correct_summary(
            prior,
            "   ",
            signer="operator:mubarak",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(),
        ),
        "plain_words_summary",
        RefusalCategory.INVALID_INPUT,
    )


def test_correction_propagates_a_bad_edge_writer() -> None:
    prior = _card()
    _refused(
        correct_summary(
            prior,
            "A different corrected summary.",
            signer="operator:mubarak",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
            edge_writer="not-a-writer",
        ),
        "writer",
        RefusalCategory.INVALID_INPUT,
    )


# --- H2/H1: a correction is a FRESH human approval, never the prior signature -----------


def test_correction_requires_a_fresh_signer_and_never_reuses_the_prior_signature() -> None:
    # H2 (re-sign forgery): correct_summary must NOT mint new words under the prior card's
    # signature. A fresh human approval (signer) is required; without it the correction is
    # refused, so "NO risk cap" text can never be signed under the prior "0.5% risk cap"
    # reviewer's identity.
    prior = _card(
        signer="operator:mubarak",
        plain_words_summary="Promote strategy X to live with a 0.5% risk cap.",
    )
    # No fresh signer -> refused (the prior signature is never reused over unread words).
    no_signer = _refused(
        correct_summary(
            prior,
            "Promote strategy X to live with NO risk cap.",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
        ),
        "signer",
        RefusalCategory.INVALID_INPUT,
    )
    assert no_signer.retryability is Retryability.NO
    # A blank fresh signer is likewise refused.
    _refused(
        correct_summary(
            prior,
            "Promote strategy X to live with NO risk cap.",
            signer="   ",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
        ),
        "signer",
        RefusalCategory.INVALID_INPUT,
    )
    # With a fresh approval, the corrected card is signed by whoever read the NEW words —
    # never inherited from the prior card.
    correction = _ok(
        correct_summary(
            prior,
            "Promote strategy X to live with NO risk cap.",
            signer="reviewer:amina",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
        )
    )
    assert correction.corrected_card.signer == "reviewer:amina"
    assert correction.corrected_card.signer != prior.signer
    assert (
        correction.corrected_card.plain_words_summary
        == "Promote strategy X to live with NO risk cap."
    )


def test_genuine_card_record_is_recognized_and_forgery_is_not() -> None:
    # H2: the card minted through PromotionCard.sign carries the reserved-mint provenance, so
    # a persist boundary can tell it from a forged look-alike. The card's kind is reserved.
    card = _card()
    assert card.kind in RESERVED_KIND_NAMES
    assert is_genuine_reserved_record(card.record) is True
    # A record of the same reserved kind that did NOT come through the signing path is never
    # genuine (see test_ct09 for the persist-boundary refusal of such a look-alike).
    assert is_genuine_reserved_record(object()) is False


# --- H1: only the current head of the supersedes chain authorizes -----------------------


def test_superseded_card_does_not_authorize_only_the_current_head() -> None:
    # H1 (superseded-card forgery): the live gate consults the supersedes chain. A card a
    # later signed correction has superseded is no longer the current head and does not
    # authorize the crossing, even though it still attests the same record.
    target = _rec("strategy-x")
    prior = _card(
        signer="operator:mubarak",
        attested_fp1=target,
        plain_words_summary="Promote strategy X to live with a 0.5% risk cap.",
    )
    correction = _ok(
        correct_summary(
            prior,
            "Promote strategy X to live with a 0.5% risk cap (typo fixed).",
            signer="operator:mubarak",
            writer=_writer(),
            sequence=1,
            signed_at=_instant(_SIGNED_NS + 60),
        )
    )
    new_card = correction.corrected_card
    superseded = [correction.supersedes_edge]  # the CT-07 supersedes edge (to_ref = prior)
    # The current head authorizes.
    authorized = _ok(
        authorize_live_promotion(target_fp1=target, card=new_card, superseded=superseded)
    )
    assert isinstance(authorized, PromotionAuthorization)
    assert authorized.card is new_card
    # The superseded prior card does NOT authorize.
    refusal = _refused(
        authorize_live_promotion(target_fp1=target, card=prior, superseded=superseded),
        "card",
        RefusalCategory.POLICY_REJECTION,
    )
    assert refusal.context["superseded_card"] == prior.stable_id.value
    # The supersession state may also be given as a collection of superseded fingerprints.
    _refused(
        authorize_live_promotion(target_fp1=target, card=prior, superseded=[prior.stable_id]),
        "card",
        RefusalCategory.POLICY_REJECTION,
    )
    # With no supersession recorded (the default), the card still authorizes — the gate only
    # refuses a card the caller's supersedes state marks as superseded.
    assert is_ok(authorize_live_promotion(target_fp1=target, card=prior))
    # A malformed supersession state is a wiring refusal.
    _refused(
        authorize_live_promotion(target_fp1=target, card=new_card, superseded="not-a-collection"),
        "superseded",
        RefusalCategory.INVALID_INPUT,
    )


# --- AC5: an AD-32 risk-admission card binds the template fingerprint --------


def test_risk_admission_card_carries_the_template_fingerprint_as_identity() -> None:
    on_v1 = _card(attested_fp1=_rec("adm"), template_definition_fp1=_rec("book-def-v1"))
    on_v2 = _card(attested_fp1=_rec("adm"), template_definition_fp1=_rec("book-def-v2"))
    without = _card(attested_fp1=_rec("adm"))
    assert on_v1.template_definition_fp1 == _rec("book-def-v1")
    # A different template => a different card fp1, so a signature can never attest a
    # superseded template; a card with no template differs from one that binds a template.
    assert on_v1.stable_id != on_v2.stable_id
    assert on_v1.stable_id != without.stable_id
    # The template fingerprint is in the identity body (an identity field).
    assert on_v1.record.fp1_identity()["body"] == {
        "signer": on_v1.signer,
        "plain_words_summary": on_v1.plain_words_summary,
        "attested_fp1": on_v1.attested_fp1.value,
        "template_definition_fp1": _rec("book-def-v1").value,
    }


def test_sign_refuses_a_bad_template_fingerprint() -> None:
    _refused(
        PromotionCard.sign(
            signer="op",
            plain_words_summary="s",
            attested_fp1=_rec("b"),
            writer=_writer(),
            sequence=0,
            signed_at=_instant(),
            template_definition_fp1="minted-id",
        ),
        "template_definition_fp1",
        RefusalCategory.INVALID_INPUT,
    )


def test_template_fingerprint_accepts_a_string() -> None:
    card = _card(template_definition_fp1=_rec("book-def-v1").value)
    assert card.template_definition_fp1 == _rec("book-def-v1")


def test_live_gate_requires_and_matches_the_in_force_template() -> None:
    # M3: when the card attests an AD-32 template, the gate REQUIRES the in-force template
    # fingerprint and refuses on mismatch; an absent argument is a refusal, never a skip, so a
    # signature can never authorize a crossing under a superseded template (DEC-0158).
    target = _rec("admission")
    card = _card(attested_fp1=target, template_definition_fp1=_rec("book-def-v1"))
    # Absent in-force template => refusal (never a silent skip).
    _refused(
        authorize_live_promotion(target_fp1=target, card=card),
        "in_force_template_fp1",
        RefusalCategory.POLICY_REJECTION,
    )
    # A DIFFERENT (superseded) in-force template => refusal.
    mismatch = _refused(
        authorize_live_promotion(
            target_fp1=target, card=card, in_force_template_fp1=_rec("book-def-v2")
        ),
        "card",
        RefusalCategory.POLICY_REJECTION,
    )
    assert mismatch.context["attested_template"] == _rec("book-def-v1").value
    assert mismatch.context["in_force_template"] == _rec("book-def-v2").value
    # A malformed in-force template => wiring refusal.
    _refused(
        authorize_live_promotion(target_fp1=target, card=card, in_force_template_fp1="minted-id"),
        "in_force_template_fp1",
        RefusalCategory.INVALID_INPUT,
    )
    # The matching in-force template authorizes (and a string form is accepted).
    authorized = _ok(
        authorize_live_promotion(
            target_fp1=target, card=card, in_force_template_fp1=_rec("book-def-v1")
        )
    )
    assert isinstance(authorized, PromotionAuthorization)
    assert authorized.card is card
    assert is_ok(
        authorize_live_promotion(
            target_fp1=target, card=card, in_force_template_fp1=_rec("book-def-v1").value
        )
    )


def test_live_gate_ignores_the_in_force_template_when_the_card_carries_none() -> None:
    # M3: a card with no attested template does not consult the in-force template — an
    # ordinary (non-risk-admission) promotion authorizes without one.
    target = _rec("bot")
    card = _card(attested_fp1=target)
    assert card.template_definition_fp1 is None
    assert is_ok(authorize_live_promotion(target_fp1=target, card=card))
    # Supplying one for a template-less card is harmless (it is simply not consulted).
    assert is_ok(
        authorize_live_promotion(
            target_fp1=target, card=card, in_force_template_fp1=_rec("book-def-v1")
        )
    )


# --- AC4: the CT-13 promotion event carries only a pointer ------------------


def test_promotion_event_carries_only_the_card_fp1_and_correlation_id() -> None:
    card = _card()
    event = _ok(PromotionEvent.for_card(card, correlation_id="corr-1"))
    assert isinstance(event, PromotionEvent)
    assert event.promotion_card_fp1 == card.stable_id
    assert event.correlation_id == "corr-1"
    # The payload is ONLY the card fp1 — the registry card is canonical, never a second
    # promotion schema; correlation_id rides the event's own excluded annotation.
    assert event.journal_payload() == {"promotion_card_fp1": card.stable_id.value}


def test_promotion_event_correlation_id_is_optional() -> None:
    event = _ok(PromotionEvent.try_create(_rec("card")))
    assert event.correlation_id is None
    assert event.promotion_card_fp1 == _rec("card")


def test_promotion_event_refuses_bad_fp_and_correlation() -> None:
    _refused(
        PromotionEvent.try_create("minted-id"), "promotion_card_fp1", RefusalCategory.INVALID_INPUT
    )
    _refused(
        PromotionEvent.try_create(_rec("card"), correlation_id="   "),
        "correlation_id",
        RefusalCategory.INVALID_INPUT,
    )
    _refused(PromotionEvent.for_card("not-a-card"), "card", RefusalCategory.INVALID_INPUT)


def test_emit_promotion_event_appends_through_the_journal_sink() -> None:
    card = _card()
    sink = _RecordingSink()
    ack = emit_promotion_event(sink, card=card, correlation_id="corr-9")
    assert is_ok(ack)
    assert isinstance(ack.value, SinkAck)
    assert len(sink.appended) == 1
    assert sink.appended[0].promotion_card_fp1 == card.stable_id
    assert sink.appended[0].correlation_id == "corr-9"


def test_emit_blocks_on_unpersistable_storage_failure() -> None:
    # A storage-failure sink surfaces block-on-unpersistable: the refusal is returned, and
    # the caller blocks its command stream (Story 2.4 persists physically).
    card = _card()
    sink = _UnpersistableSink()
    result = emit_promotion_event(sink, card=card)
    assert is_unpersistable(result)


def test_emit_refuses_bad_card_and_non_sink() -> None:
    _refused(
        emit_promotion_event(_RecordingSink(), card="not-a-card"),
        "card",
        RefusalCategory.INVALID_INPUT,
    )
    _refused(
        emit_promotion_event(object(), card=_card()),
        "sink",
        RefusalCategory.INVALID_INPUT,
    )


class _RecordingSink:
    """A JournalSink test double that records appended promotion events."""

    def __init__(self) -> None:
        self.appended: list[PromotionEvent] = []

    def append(self, event: PromotionEvent, /) -> SinkResult:
        self.appended.append(event)
        return Ok(SinkAck())


class _UnpersistableSink:
    """A JournalSink test double whose append is never durable (block-on-unpersistable)."""

    def append(self, event: PromotionEvent, /) -> SinkResult:
        del event  # unused: this sink never persists, to exercise block-on-unpersistable
        return unpersistable("the journal room is unavailable", retryability=Retryability.NO)


def test_sinks_satisfy_the_journal_sink_protocol() -> None:
    assert isinstance(_RecordingSink(), JournalSink)
    assert isinstance(_UnpersistableSink(), JournalSink)


# --- AC6: default-deny import discipline ------------------------------------


def test_promotion_module_imports_only_core_and_package_siblings() -> None:
    source = Path(promotion_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    qmf_imports = {name for name in imported if name.startswith("qmf")}
    # It composes its own package siblings (records, lineage); the only cross-package qmf
    # import is qmf.core — never another roster package (default-deny; DEC-0120).
    external = {name for name in qmf_imports if not name.startswith("qmf.registry")}
    assert external == {"qmf.core"}, external
    assert qmf_imports <= {"qmf.core", "qmf.registry.records", "qmf.registry.lineage"}, qmf_imports
