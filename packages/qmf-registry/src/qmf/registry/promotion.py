"""CT-06 promotion-occurrence card + CT-13 promotion event (COMP-QMF-REGISTRY).

The **only path to live money** (FR-009; ADR-0015; DEC-0116). Nothing crosses into the
live zone except through a human-signed promotion-occurrence card: a signed, immutable
record whose signature attests the exact words a human read. This module builds the
**record vocabulary and the refusal law** — the promotion gate's own workflow, UI, and
timing stay platform territory outside QMF.

Five laws this module pins down.

**The promotion-occurrence card is a reserved CT-06 kind (DEC-0116, DEC-0158).**
:class:`PromotionCard` mints the ``promotion-occurrence-card`` kind — one of the two
:data:`~qmf.registry.records.RESERVED_KIND_NAMES` the generic addable path may never
forge — through this dedicated path. The card carries a human-only ``signer`` (the
reviewer identity), a mandatory ``plain_words_summary`` **declared an identity field**,
the attested record's ``attested_fp1``, and — for an AD-32 risk admission — the
Book-definition (or BMS-definition) ``template_definition_fp1``, all folded into the
canonical CT-06 :class:`~qmf.registry.records.RegistrationRecord` body so they **are** the
card's ``fp1`` identity. The ``signed_at`` instant, the writer, and the per-writer
sequence are occurrence facts, excluded from identity exactly as
:class:`~qmf.core.OccurrenceRecord` excludes when/where/by-whom. V1 signing is the
operator's recorded approval; **no cryptographic dependency is taken now** (DEC-0116).

**The registry card is canonical; the journal carries only a pointer (DEC-0116).**
:class:`PromotionEvent` is the CT-13 ``promotion`` journal event, carrying **only** the
promotion card's ``fp1`` fingerprint plus a ``correlation_id`` — never a second promotion
schema. :func:`emit_promotion_event` hands it to the core-defined
:class:`~qmf.core.JournalSink` injected at the composition root (physical persistence
through ``qmf-data`` lands in Story 2.4), so emitting creates no import edge and the
journal never holds a second copy of the promotion fact.

**A signature attests the exact words read; a correction mints a new card under a fresh
human approval (FM-5).** The mandatory summary being an identity field means it cannot be
edited in place. Correcting it is :func:`correct_summary`: a **new** card is minted (a
different ``fp1``, because the summary is identity) and linked to the prior card with a
CT-07 ``supersedes`` edge — the signed record is never rewritten. The corrected card is
signed by the reviewer who read the **new** words, supplied as a required ``signer``
argument: a correction is a fresh human approval, never the prior card's signature
reused over words that human never read (H2; ADR-0015; DEC-0116).

**Because the attested template is an identity field, a signature can never attest a
superseded template (DEC-0158).** A card attesting an AD-32 admission carries the
Book-definition/BMS-definition fingerprint as ``template_definition_fp1``; a new template
version has a new fingerprint, so a card that attested the old template has a different
``fp1`` and can never silently stand for the new one.

**Only a human promotes into the live zone, only the current card, and only under the
in-force template (FM-4; AR-39; DEC-0041, DEC-0158).** :func:`authorize_live_promotion` is
the refusal law: a live-promotion request with no human-signed promotion-occurrence card
present does not occur — a typed refusal is returned. A present card authorizes only the
exact record its signature attests **and** only while it is the current head of the
supersedes chain: a card a later signed correction has superseded no longer speaks for the
crossing, so the gate consults the supersession state (the ``supersedes`` edges) the caller
must supply — a required argument with no default — and refuses a superseded card (FM-5).
When the card attests an AD-32
``template_definition_fp1``, the gate additionally **requires** the current in-force template
fingerprint and refuses on any mismatch — and refuses an absent argument outright, never
skipping the check — so a signature can never authorize a crossing under a superseded
template (DEC-0158).

Default-deny holds: this module imports **only** ``qmf.core`` and its own package
siblings ``qmf.registry.records`` (the canonical CT-06 record) and ``qmf.registry.lineage``
(the CT-07 supersedes edge) — never another roster package (DEC-0120). Every ``fp1``
fingerprint is computed in ``qmf-core`` and nowhere else. Every operation succeeds or
RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain failure is never raised across the
boundary. Stdlib plus qmf-core and package siblings only; frozen, immutable values
throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, cast

from qmf.core import (
    Fingerprint,
    Instant,
    JournalSink,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SinkResult,
    TypedRefusal,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.registry.lineage import EdgeType, LineageEdge
from qmf.registry.records import RegistrationRecord

__all__ = [
    "KIND_PROMOTION_OCCURRENCE_CARD",
    "PROMOTION_CARD_CONTRACT_FORMAT_VERSION",
    "PromotionAuthorization",
    "PromotionCard",
    "PromotionCorrection",
    "PromotionEvent",
    "authorize_live_promotion",
    "correct_summary",
    "emit_promotion_event",
]

# The reserved CT-06 kind this module mints. It is one of RESERVED_KIND_NAMES, so the
# generic KindRegistry/Registrar path refuses it — the promotion-occurrence card is
# reachable ONLY through this dedicated, human-signed path (DEC-0116, DEC-0158). The
# name is defined here and cross-checked against the reserved set by the contract test.
KIND_PROMOTION_OCCURRENCE_CARD: Final[str] = "promotion-occurrence-card"

# The per-kind contract format version for the promotion-occurrence card body (the
# CT-06 header's ``contract_format_version`` field, distinct from the record-envelope
# version). Its meaning never mutates — an incompatible body change mints the next
# version (DEC-0103; versioning-from-birth L15).
PROMOTION_CARD_CONTRACT_FORMAT_VERSION: Final[int] = 1

# The card body keys — every one an identity field (the body is folded into the CT-06
# record's fp1 identity). ``template_definition_fp1`` is present only for an AD-32
# risk-admission card; an absent value is an omitted key, never a null (DEC-0108).
_SIGNER_KEY: Final[str] = "signer"
_SUMMARY_KEY: Final[str] = "plain_words_summary"
_ATTESTED_FP1_KEY: Final[str] = "attested_fp1"
_TEMPLATE_FP1_KEY: Final[str] = "template_definition_fp1"


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a promotion construction returns.

    ``retryability`` is ``no`` — a blank signer, a missing summary, a non-``fp1``
    attested reference, or a bad journal wiring is a caller/wiring mistake, not a
    transient condition — and ``context`` always names the offending ``field`` and a
    human-legible ``reason`` (returned, never raised; CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal the live-promotion gate returns (FM-4).

    A live-promotion request with no human-signed promotion-occurrence card present — or
    a card attesting a different record — is a policy rejection: only a human promotes an
    artifact into the live zone (AR-39; DEC-0041). ``retryability`` is ``no``; the caller
    must obtain the human-signed card attesting THIS record before re-requesting.
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    A signer and a plain-words summary are opaque human text: the returned string is the
    caller's verbatim — never stripped, cased, or parsed — and the signature attests it
    exactly.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string,
    or ``None`` — parsing goes through qmf-core, never a local hash."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _resolve_correlation_id(value: object) -> Result[str | None]:
    """Resolve the optional ``correlation_id``: ``None`` or a non-blank string, else
    refuse.

    A linking annotation propagated across package boundaries and excluded from the
    journal event's ``fp1`` identity (CT-13; DEC-0112, DEC-0108); it is still validated
    as a clean token so it round-trips and propagates without ambiguity.
    """
    if value is None:
        return Ok(None)
    if isinstance(value, str) and value.strip() != "":
        return Ok(value)
    return _invalid(
        "correlation_id",
        "correlation_id, when present, is a non-blank linking annotation (or omitted); it "
        "is excluded from the promotion event's fp1 identity but propagated across "
        "boundaries (DEC-0112)",
        given=repr(value),
    )


# --- the human-signed promotion-occurrence card -----------------------------


@dataclass(frozen=True, slots=True)
class PromotionCard:
    """A human-signed promotion-occurrence card — the only path to live money (CT-06
    reserved kind; ADR-0015, DEC-0116, DEC-0158).

    ``signer`` is the human-only reviewer identity; ``plain_words_summary`` is the
    mandatory plain-words summary **declared an identity field**, so the signature attests
    the exact words read; ``attested_fp1`` is the ``fp1`` of the record the approval
    attests; ``template_definition_fp1`` is the Book-definition (or BMS-definition)
    fingerprint for an AD-32 risk admission, present only then. Those parts are folded into
    the canonical CT-06 :attr:`record` body, so they **are** the card's ``fp1`` identity.
    ``signed_at`` is the instant of the recorded approval occurrence — display-only,
    excluded from identity (the same occurrence/identity split :class:`~qmf.core.OccurrenceRecord`
    draws), as are the record's writer and per-writer sequence.

    :attr:`record` is the canonical registry artifact — the card IS a CT-06 record, and
    its :attr:`stable_id` is the card's ``fp1`` fingerprint. The card is frozen: a summary
    correction is a NEW card with a ``supersedes`` edge (:func:`correct_summary`), never an
    in-place edit.
    """

    signer: str
    plain_words_summary: str
    attested_fp1: Fingerprint
    template_definition_fp1: Fingerprint | None
    signed_at: Instant
    record: RegistrationRecord

    @classmethod
    def sign(
        cls,
        *,
        signer: object,
        plain_words_summary: object,
        attested_fp1: object,
        writer: object,
        sequence: object,
        signed_at: object,
        template_definition_fp1: object = None,
    ) -> Result[PromotionCard]:
        """Record a human's approval as a signed promotion-occurrence card, returning
        value-or-refusal (AC1; DEC-0116, DEC-0158).

        ``signer`` must be a non-blank human reviewer identity; ``plain_words_summary`` a
        mandatory non-blank string (an identity field); ``attested_fp1`` a
        :class:`~qmf.core.Fingerprint` (or ``fp1:sha256:<hex>`` string) — never a minted or
        mutable id; ``template_definition_fp1`` an optional Book-definition/BMS-definition
        fingerprint for an AD-32 risk admission. ``writer`` is a
        :class:`~qmf.core.WriterId`, ``sequence`` a non-negative integer, and ``signed_at``
        an :class:`~qmf.core.Instant`. The stable id is **derived** from the identity
        content by qmf-core and is never supplied; V1 signing takes no cryptographic
        dependency — the signer is the recorded reviewer identity (DEC-0116).
        """
        signer_token = _clean_str(signer)
        if signer_token is None:
            return _invalid(
                "signer",
                "a promotion-occurrence card carries a human-only signer (a non-blank "
                "reviewer identity); V1 signing is the operator's recorded approval, with "
                "no cryptographic dependency (DEC-0116)",
                given=repr(signer),
            )
        summary_token = _clean_str(plain_words_summary)
        if summary_token is None:
            return _invalid(
                "plain_words_summary",
                "the plain-words summary is mandatory and declared an identity field, so "
                "the signature attests the exact words read (DEC-0116)",
                given=repr(plain_words_summary),
            )
        attested = _coerce_fingerprint(attested_fp1)
        if attested is None:
            return _invalid(
                "attested_fp1",
                "a card attests a record by its fp1 fingerprint (fp1:sha256:<hex>); a "
                "minted or mutable id is never attested (DEC-0108)",
                given=repr(attested_fp1),
            )
        template: Fingerprint | None = None
        if template_definition_fp1 is not None:
            template = _coerce_fingerprint(template_definition_fp1)
            if template is None:
                return _invalid(
                    "template_definition_fp1",
                    "an AD-32 risk-admission card carries the Book-definition (or "
                    "BMS-definition) fingerprint as an identity field, so a signature can "
                    "never attest a superseded template (DEC-0158)",
                    given=repr(template_definition_fp1),
                )
        if not isinstance(signed_at, Instant):
            return _invalid(
                "signed_at",
                "signed-at is the Instant of the recorded approval occurrence "
                "(display-only, excluded from identity) (DEC-0106, DEC-0110)",
                given=repr(signed_at),
            )
        body: dict[str, object] = {
            _SIGNER_KEY: signer_token,
            _SUMMARY_KEY: summary_token,
            _ATTESTED_FP1_KEY: attested.value,
        }
        if template is not None:
            body[_TEMPLATE_FP1_KEY] = template.value
        # Build the canonical CT-06 record through the dedicated reserved-mint path: the
        # public RegistrationRecord.try_create and the generic KindRegistry/Registrar path
        # both refuse reserved kinds, so this is the ONLY path that mints a
        # promotion-occurrence card, and the record it produces is marked genuine so a
        # persist boundary can tell it from a forged look-alike (H2; DEC-0116, DEC-0158).
        # RegistrationRecord derives the stable id from the identity content and validates
        # writer/sequence.
        built = RegistrationRecord._mint_reserved(  # pyright: ignore[reportPrivateUsage]
            KIND_PROMOTION_OCCURRENCE_CARD,
            PROMOTION_CARD_CONTRACT_FORMAT_VERSION,
            (),
            body,
            writer,
            sequence,
            signed_at,
        )
        if is_refusal(built):
            return built
        record = built.value
        return Ok(
            cls(
                signer=signer_token,
                plain_words_summary=summary_token,
                attested_fp1=attested,
                template_definition_fp1=template,
                signed_at=signed_at,
                record=record,
            )
        )

    @property
    def stable_id(self) -> Fingerprint:
        """The card's ``fp1`` stable id — the canonical CT-06 record's derived id."""
        return self.record.stable_id

    @property
    def kind(self) -> str:
        """The reserved kind name (:data:`KIND_PROMOTION_OCCURRENCE_CARD`)."""
        return self.record.kind

    @property
    def writer(self) -> WriterId:
        """The occurrence writer (excluded from identity)."""
        return self.record.writer

    @property
    def sequence(self) -> int:
        """The per-writer occurrence sequence (excluded from identity)."""
        return self.record.sequence

    def attests(self, target: object) -> bool:
        """Whether this card's signature attests the record named by ``target``.

        ``target`` is a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>``
        string; anything malformed resolves to no match (``False``), never an exception.
        """
        resolved = _coerce_fingerprint(target)
        return resolved is not None and resolved == self.attested_fp1


# --- a summary correction: a new card + a supersedes edge (FM-5) ------------


@dataclass(frozen=True, slots=True)
class PromotionCorrection:
    """The result of correcting a signed card's plain-words summary (FM-5; CT-07).

    ``corrected_card`` is the NEW card (a different ``fp1``, because the summary is an
    identity field); ``supersedes_edge`` is the CT-07 ``supersedes`` edge linking the new
    card (``from_ref``) to the prior card (``to_ref``). The prior card is never edited in
    place — the signature attests the exact words read.
    """

    corrected_card: PromotionCard
    supersedes_edge: LineageEdge


def correct_summary(
    prior: object,
    corrected_summary: object,
    *,
    signer: object = None,
    writer: object,
    sequence: object,
    signed_at: object,
    edge_writer: object = None,
) -> Result[PromotionCorrection]:
    """Correct a signed card's plain-words summary, returning value-or-refusal (AC3; FM-5).

    Mints a NEW :class:`PromotionCard` carrying the ``corrected_summary`` — a different
    ``fp1`` because the summary is an identity field — under a **fresh human approval**, and
    builds the CT-07 ``supersedes`` edge linking the new card to the prior one. The signed
    record is never edited in place, because a signature attests the exact words read
    (DEC-0116).

    ``signer`` is the human reviewer who read the **corrected** words and is **required**:
    the new card is signed under this identity, never the prior card's signer — reusing the
    prior signature over words that human never read is exactly the forgery this refuses
    (H2; ADR-0015). ``attested_fp1`` and ``template_definition_fp1`` are carried over from
    the prior card (a correction is the same attestation with different words), but the
    ``signer`` and the ``signed_at`` instant are the fresh approval's, never inherited.
    ``writer`` signs the new card's record; ``edge_writer`` writes the supersedes edge
    (defaulting to ``writer``). A blank/absent ``signer`` is an ``invalid input`` refusal, as
    is a correction whose summary is unchanged (it would mint the identical card with nothing
    to supersede).
    """
    if not isinstance(prior, PromotionCard):
        return _invalid(
            "prior",
            "a correction supersedes a prior signed PromotionCard",
            given=repr(prior),
        )
    fresh_signer = _clean_str(signer)
    if fresh_signer is None:
        return _invalid(
            "signer",
            "a summary correction is a fresh human approval: the corrected card must be "
            "signed by the reviewer who read the NEW words (supplied as `signer`), never "
            "under the prior card's signature — that signature attests only the words it "
            "carried (FM-5; ADR-0015; DEC-0116)",
            given=repr(signer),
        )
    corrected = PromotionCard.sign(
        signer=fresh_signer,
        plain_words_summary=corrected_summary,
        attested_fp1=prior.attested_fp1,
        writer=writer,
        sequence=sequence,
        signed_at=signed_at,
        template_definition_fp1=prior.template_definition_fp1,
    )
    if is_refusal(corrected):
        return corrected
    new_card = corrected.value
    if new_card.stable_id == prior.stable_id:
        return _invalid(
            "plain_words_summary",
            "a correction changes the plain-words summary; an unchanged summary mints the "
            "identical card, with nothing to supersede (FM-5)",
            summary=new_card.plain_words_summary,
        )
    resolved_edge_writer = writer if edge_writer is None else edge_writer
    edge = LineageEdge.try_create(
        EdgeType.SUPERSEDES,
        new_card.stable_id,
        prior.stable_id,
        resolved_edge_writer,
    )
    if is_refusal(edge):
        return edge
    return Ok(PromotionCorrection(corrected_card=new_card, supersedes_edge=edge.value))


# --- the live-promotion gate (the refusal law, FM-4) ------------------------


@dataclass(frozen=True, slots=True)
class PromotionAuthorization:
    """An authorized live promotion (AC2; DEC-0041, DEC-0116).

    Returned only when a present human-signed :class:`PromotionCard` attests the exact
    record requested: ``card`` is that card and ``attested_fp1`` is the target's ``fp1``.
    QMF records the authorization vocabulary; the promotion gate's own workflow, UI, and
    timing remain platform territory outside QMF.
    """

    card: PromotionCard
    attested_fp1: Fingerprint


def _superseded_card_ids(value: object) -> frozenset[str] | None:
    """Resolve the supplied supersession state to a set of superseded card ``fp1`` strings.

    Accepts a collection of :class:`~qmf.core.Fingerprint`\\ s or valid ``fp1:sha256:<hex>``
    strings — the ``to_ref`` (superseded) endpoints of the ``supersedes`` chain — or a
    collection of :class:`~qmf.registry.LineageEdge`\\ s, from which the ``supersedes``
    edges' ``to_ref``\\ s are taken (any other edge type is ignored). A bare string/bytes is
    not a collection of references and resolves to ``None`` (an ``invalid input`` wiring
    refusal at the call site); an empty collection means nothing is superseded.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        return None
    resolved: set[str] = set()
    for item in cast("Iterable[object]", value):
        if isinstance(item, LineageEdge):
            if item.edge_type is EdgeType.SUPERSEDES:
                resolved.add(item.to_ref.value)
            continue
        fp = _coerce_fingerprint(item)
        if fp is None:
            return None
        resolved.add(fp.value)
    return frozenset(resolved)


def authorize_live_promotion(
    *,
    target_fp1: object,
    card: object,
    superseded: object,
    in_force_template_fp1: object = None,
) -> Result[PromotionAuthorization]:
    """The live-promotion refusal law: only a human-signed, current card authorizes the
    crossing (AC2; FM-4, FM-5; AR-39; DEC-0041, DEC-0158).

    ``target_fp1`` names the record being promoted into the live zone. With no
    human-signed promotion-occurrence card present (``card`` is ``None``), promotion does
    not occur — a ``policy rejection`` refusal is returned, because only a human promotes
    an artifact into the live zone. A present :class:`PromotionCard` authorizes only the
    exact record its signature attests; a card attesting a different record is refused. A
    non-card object is an ``invalid input`` wiring refusal.

    ``superseded`` is the supersession state the caller resolves from the CT-07
    ``supersedes`` chain and is a **required keyword argument with no default**: the caller
    must always answer it explicitly, because omitting it is exactly what would silently
    weaken the strongest invariant on the path to live money — only the current head of the
    supersedes chain authorizes. Pass a collection of superseded card fingerprints (the
    ``to_ref`` endpoints) or of :class:`~qmf.registry.LineageEdge`\\ s to read them from; pass
    an **empty collection** to state explicitly "I checked; nothing supersedes this card". A
    card whose ``fp1`` appears there has been superseded by a later signed correction and is
    **no longer the current head**, so it does not authorize the crossing — a ``policy
    rejection`` (only the current card speaks for live money; FM-5). Omitting the argument is
    a programmer error (a ``TypeError`` at call time; AR-13); passing ``None`` — or any other
    malformed value — is an ``invalid input`` wiring refusal, never a silent skip.

    ``in_force_template_fp1`` is the current in-force Book-definition/BMS-definition
    fingerprint. When the ``card`` carries an AD-32 ``template_definition_fp1``, this
    argument is **required** and the gate refuses unless it equals what the card attests: a
    signature can never attest a superseded template, so a card that attested an old template
    version does not authorize a crossing under a new one, and an **absent** in-force
    template is itself a refusal (never a silent skip; DEC-0158; AD-32). When the card
    carries no template, ``in_force_template_fp1`` is not consulted. The promotion gate's own
    workflow, UI, and timing are platform territory outside QMF — this is the record
    vocabulary and the refusal law only.
    """
    target = _coerce_fingerprint(target_fp1)
    if target is None:
        return _invalid(
            "target_fp1",
            "a live promotion names the target record by its fp1 fingerprint (fp1:sha256:<hex>)",
            given=repr(target_fp1),
        )
    if card is None:
        return _policy(
            "card",
            "no human-signed promotion-occurrence card is present; promotion does not "
            "occur — only a human promotes an artifact into the live zone (FM-4, AR-39, "
            "DEC-0041)",
            requested=target.value,
        )
    if not isinstance(card, PromotionCard):
        return _invalid(
            "card",
            "a live promotion is authorized by a signed PromotionCard; V1 signing is the "
            "operator's recorded approval (DEC-0116)",
            given=repr(card),
        )
    if card.attested_fp1 != target:
        return _policy(
            "card",
            "the promotion card attests a different record; a signature authorizes only "
            "the exact record it attests, so promotion does not occur (FM-4)",
            attested=card.attested_fp1.value,
            requested=target.value,
        )
    if superseded is None:
        return _invalid(
            "superseded",
            "the supersession state is required and must be supplied explicitly: pass the "
            "collection of superseded card fp1 fingerprints (or of LineageEdges to read the "
            "supersedes chain from), or an EMPTY collection to state 'I checked; nothing "
            "supersedes this card'. None is never a valid answer — accepting it would let a "
            "caller silently skip the only-the-current-head check (FM-5)",
            given=repr(superseded),
        )
    superseded_ids = _superseded_card_ids(superseded)
    if superseded_ids is None:
        return _invalid(
            "superseded",
            "the supersession state is a collection of superseded card fp1 fingerprints "
            "(or of LineageEdges to read the supersedes chain from); a bare string is not "
            "a collection of references",
            given=repr(superseded),
        )
    if card.stable_id.value in superseded_ids:
        return _policy(
            "card",
            "the promotion card has been superseded by a later signed correction; only "
            "the current head of the supersedes chain authorizes the live crossing, so "
            "promotion does not occur (FM-5, FM-4)",
            superseded_card=card.stable_id.value,
            requested=target.value,
        )
    if card.template_definition_fp1 is not None:
        if in_force_template_fp1 is None:
            return _policy(
                "in_force_template_fp1",
                "this card attests an AD-32 template (template_definition_fp1) but no "
                "in-force template fingerprint was supplied to compare it against; a "
                "signature can never attest a superseded template, so the crossing is "
                "refused until the current in-force template is supplied and matches — an "
                "absent argument is a refusal, never a skip (DEC-0158; AD-32)",
                attested_template=card.template_definition_fp1.value,
                requested=target.value,
            )
        in_force = _coerce_fingerprint(in_force_template_fp1)
        if in_force is None:
            return _invalid(
                "in_force_template_fp1",
                "the in-force template is named by an fp1 fingerprint (fp1:sha256:<hex>); a "
                "minted or mutable id is never a template reference (DEC-0108)",
                given=repr(in_force_template_fp1),
            )
        if card.template_definition_fp1 != in_force:
            return _policy(
                "card",
                "the promotion card attests a template that is not the in-force template; a "
                "signature attests only the exact template version its signer read, so a "
                "card that attested a superseded template does not authorize the crossing "
                "(DEC-0158; AD-32)",
                attested_template=card.template_definition_fp1.value,
                in_force_template=in_force.value,
                requested=target.value,
            )
    return Ok(PromotionAuthorization(card=card, attested_fp1=target))


# --- the CT-13 promotion journal event (only a pointer) ---------------------


@dataclass(frozen=True, slots=True)
class PromotionEvent:
    """The CT-13 ``promotion`` journal event — only the card's ``fp1`` plus a
    ``correlation_id`` (AC4; CT-13; DEC-0116).

    The registry card is canonical, so the journal carries **only a pointer**:
    ``promotion_card_fp1`` and an optional ``correlation_id`` — never a second promotion
    schema. This is the qmf-registry-side payload value handed to the core
    :class:`~qmf.core.JournalSink`; the composition root's wired sink maps it onto
    ``qmf-data``'s ``JournalEvent`` with ``event_type = promotion`` (Story 2.4), where
    ``correlation_id`` rides the event's own identity-excluded annotation and the payload
    carries only :meth:`journal_payload` — the card fingerprint.
    """

    promotion_card_fp1: Fingerprint
    correlation_id: str | None = None

    @classmethod
    def try_create(
        cls, promotion_card_fp1: object, *, correlation_id: object = None
    ) -> Result[PromotionEvent]:
        """Validate and build the promotion event, returning value-or-refusal (AC4).

        ``promotion_card_fp1`` must be a :class:`~qmf.core.Fingerprint` (or valid
        ``fp1:sha256:<hex>`` string) — the canonical card's id; ``correlation_id`` is an
        optional non-blank linking annotation excluded from journal-event identity. No
        other field is admitted — the journal never holds a second promotion schema
        (DEC-0116).
        """
        fp = _coerce_fingerprint(promotion_card_fp1)
        if fp is None:
            return _invalid(
                "promotion_card_fp1",
                "the promotion event carries the promotion card's fp1 fingerprint (the "
                "registry card is canonical); never a second promotion schema (DEC-0116)",
                given=repr(promotion_card_fp1),
            )
        correlation = _resolve_correlation_id(correlation_id)
        if is_refusal(correlation):
            return correlation
        return Ok(cls(promotion_card_fp1=fp, correlation_id=correlation.value))

    @classmethod
    def for_card(cls, card: object, *, correlation_id: object = None) -> Result[PromotionEvent]:
        """Build the promotion event for a signed :class:`PromotionCard`, returning
        value-or-refusal.

        The event references the card by its canonical :attr:`PromotionCard.stable_id`, so
        it can only ever be a pointer to the canonical card. A non-card argument is an
        ``invalid input`` refusal.
        """
        if not isinstance(card, PromotionCard):
            return _invalid(
                "card",
                "a promotion event is emitted for a signed PromotionCard",
                given=repr(card),
            )
        return cls.try_create(card.stable_id, correlation_id=correlation_id)

    def journal_payload(self) -> dict[str, object]:
        """The CT-13 promotion event payload — ONLY the card ``fp1`` (DEC-0116; CT-13).

        The ``correlation_id`` is deliberately absent: it rides the journal event's own
        identity-excluded top-level annotation, never the payload, so the payload is only
        the pointer to the canonical registry card.
        """
        return {"promotion_card_fp1": self.promotion_card_fp1.value}


def emit_promotion_event(
    sink: object, *, card: object, correlation_id: object = None
) -> SinkResult:
    """Emit the CT-13 promotion event through the injected core :class:`~qmf.core.JournalSink`
    (AC4; CT-13; DEC-0116, DEC-0138).

    Builds the :class:`PromotionEvent` for ``card`` (a pointer to the canonical registry
    card, plus an optional ``correlation_id``) and appends it through ``sink`` — a
    core-defined ``JournalSink`` injected at the composition root, so emitting creates no
    import edge (physical persistence through ``qmf-data`` lands in Story 2.4). Returns the
    sink's ``Result[SinkAck]``: a durable append is an :class:`~qmf.core.Ok`
    acknowledgment, and an unpersistable append is a ``storage failure`` refusal on which
    the caller **blocks its command stream** (block-on-unpersistable). A malformed card or
    a ``sink`` that is not a ``JournalSink`` is an ``invalid input`` refusal, and nothing
    is emitted.
    """
    event = PromotionEvent.for_card(card, correlation_id=correlation_id)
    if is_refusal(event):
        return event
    if not isinstance(sink, JournalSink):
        return _invalid(
            "sink",
            "a promotion event is emitted through a core JournalSink injected at the "
            "composition root (DEC-0138)",
            given=repr(sink),
        )
    # isinstance narrows to the unparametrized protocol; the injected sink accepts the
    # PromotionEvent payload this module produces (the composition root wires the concrete
    # sink), so name that payload type for the append call.
    typed_sink = cast("JournalSink[PromotionEvent]", sink)
    return typed_sink.append(event.value)
