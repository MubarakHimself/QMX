"""Persist promotion and activation through closed CT-13 paths (Story 26.10).

An accepted promotion journals as the existing ``promotion`` type. The payload
is only the promotion-card ``fp1``; ``correlation_id`` rides the envelope as
the closed CT-13 annotation (DEC-0116; QMX-F046). Operator, artifact, config,
and binding detail stay on the referenced card and read-time projections.

Activation — requested, refused, or successful — journals as a CT-24 binding
transition mapped onto CT-13 ``risk transition``. It never uses ``promotion``
and never mints an eighth type (FTR-01/FTR-02; CT-24/25). Requested versus
enforced state and principal evidence are reconstructed from the referenced
transition record.

A journal-sink refusal blocks the state change. A log line is never journal
evidence (NFR-15/16).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import (
    Fingerprint,
    Instant,
    JournalSink,
    Ok,
    Result,
    SinkResult,
    fingerprint,
    is_ok,
    is_refusal,
)

from qmn.observability.logging import (
    LOGS_ARE_NOT_JOURNALS,
    LOGS_SATISFY_CT13_EVIDENCE,
    log_record_is_journal_evidence,
)
from qmn.promotion._refuse import clean_token, invalid, policy, unsupported
from qmn.promotion.lifecycle import (
    ActivationAcceptance,
    ActivationReadiness,
    PromotionLanding,
)
from qmn.seats.state import GovernedSeatState

__all__ = [
    "ACTIVATION_CT13_EVENT_TYPE",
    "ACTIVATION_PAYLOAD_KEYS",
    "ACTIVATION_TRIGGER",
    "CT13_SEVEN_EVENT_TYPES",
    "LOG_LINE_SUBSTITUTES_FOR_JOURNAL",
    "PROMOTION_EVENT_TYPE",
    "PROMOTION_PAYLOAD_KEYS",
    "ActivationBindingTransition",
    "ActivationJournalRow",
    "ActivationPhase",
    "ActivationReconstruction",
    "CommittedActivation",
    "PromotionJournalRow",
    "assert_closed_ct13_event_type",
    "commit_activation",
    "commit_promotion",
    "map_activation_ct13_event_type",
    "persist_activation",
    "persist_promotion",
    "promotion_journal_payload",
    "reconstruct_activation",
]

# AD-21 / CT-13 closed seven — never an eighth node-private type (FTR-01/FTR-02).
CT13_SEVEN_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "decision",
        "order",
        "fill",
        "risk transition",
        "promotion",
        "data quality",
        "control action",
    }
)

PROMOTION_EVENT_TYPE: Final[str] = "promotion"
ACTIVATION_CT13_EVENT_TYPE: Final[str] = "risk transition"
ACTIVATION_TRIGGER: Final[str] = "activation"
PROMOTION_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset({"promotion_card_fp1"})
ACTIVATION_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset({"transition_fp1"})
LOG_LINE_SUBSTITUTES_FOR_JOURNAL: Final[bool] = False
_ACTIVATION_FORMAT_VERSION: Final[int] = 1
_RowT = TypeVar("_RowT")

_WIDENED_PROMOTION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "operator",
        "operator_signature",
        "artifact",
        "artifact_key",
        "config",
        "binding",
        "binding_id",
        "seat_id",
        "principal",
    }
)


class ActivationPhase(StrEnum):
    """Closed activation recording phases — still one CT-24 transition kind."""

    REQUESTED = "requested"
    REFUSED = "refused"
    SUCCESSFUL = "successful"


def assert_closed_ct13_event_type(proposed: object) -> Result[str]:
    """Refuse any journal event type outside CT-13's closed seven (FTR-01/FTR-02)."""
    token = clean_token(proposed)
    if token is None:
        return invalid(
            "event_type",
            "a CT-13 journal event type is a non-blank token among the closed seven",
            given=repr(proposed),
            allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
        )
    if token not in CT13_SEVEN_EVENT_TYPES:
        return unsupported(
            "event_type",
            "promotion and activation persist through CT-13's existing seven; an "
            "eighth node-private journal type is refused (FTR-01/FTR-02)",
            ftr="FTR-01",
            given=token,
            allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
        )
    return Ok(token)


def map_activation_ct13_event_type(
    proposed: object = ACTIVATION_CT13_EVENT_TYPE,
) -> Result[str]:
    """Map activation onto CT-24's existing CT-13 ``risk transition`` row."""
    closed = assert_closed_ct13_event_type(proposed)
    if is_refusal(closed):
        return closed
    if closed.value != ACTIVATION_CT13_EVENT_TYPE:
        return policy(
            "event_type",
            "activation uses the CT-24 binding transition mapped onto CT-13 "
            "risk transition; it never uses the promotion event type",
            given=closed.value,
            mapped=ACTIVATION_CT13_EVENT_TYPE,
            ftr="FTR-01",
        )
    return closed


def promotion_journal_payload(card_fp1: object) -> Result[Mapping[str, object]]:
    """Closed promotion payload — only the card ``fp1`` (DEC-0116).

    Matches the registry ``PromotionEvent.journal_payload`` shape without
    importing ``qmf.registry`` (host owns that mint surface).
    """
    if not isinstance(card_fp1, Fingerprint):
        return invalid(
            "promotion_card_fp1",
            "the promotion event payload carries the promotion-card fp1",
            given=repr(card_fp1),
        )
    payload: dict[str, object] = {"promotion_card_fp1": card_fp1.value}
    extra = set(payload) - PROMOTION_PAYLOAD_KEYS
    if extra:
        return policy(
            "payload",
            "the promotion event payload carries only the promotion-card fp1; "
            "operator, artifact, config, and binding detail stay on the card",
            extra=sorted(extra),
            allowed=sorted(PROMOTION_PAYLOAD_KEYS),
        )
    return Ok(MappingProxyType(payload))


@dataclass(frozen=True, slots=True)
class PromotionJournalRow:
    """CT-13 ``promotion`` envelope: payload pointer plus ``correlation_id``."""

    event_type: str
    promotion_card_fp1: Fingerprint
    correlation_id: str | None
    payload: Mapping[str, object]

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "event_type": self.event_type,
            "payload": dict(self.payload),
        }
        if self.correlation_id is not None:
            body["correlation_id"] = self.correlation_id
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class ActivationBindingTransition:
    """CT-24 binding transition for an activation act (DEC-0205, DEC-0251).

    Requested versus enforced state and the operator principal live on this
    record. The CT-13 event is only a pointer at its ``fp1``.
    """

    phase: ActivationPhase
    seat_id: str
    binding_id: str
    requested_state: GovernedSeatState
    enforced_state: GovernedSeatState
    operator_signature: str
    transition_instant: Instant
    trigger_kind: str = ACTIVATION_TRIGGER
    effective_at: Instant | None = None
    refusing_check: str | None = None

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "class": "binding-transition-record",
            "trigger_kind": self.trigger_kind,
            "phase": self.phase.value,
            "seat_id": self.seat_id,
            "binding_id": self.binding_id,
            "requested_state": self.requested_state.value,
            "enforced_state": self.enforced_state.value,
            "operator_signature": self.operator_signature,
            "transition_instant": self.transition_instant.fp1_identity(),
            "format_version": _ACTIVATION_FORMAT_VERSION,
        }
        if self.effective_at is not None:
            content["effective_at"] = self.effective_at.fp1_identity()
        if self.refusing_check is not None:
            content["refusing_check"] = self.refusing_check
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(self.fp1_identity())

    @classmethod
    def try_create(
        cls,
        *,
        phase: object,
        seat_id: object,
        binding_id: object,
        requested_state: object,
        enforced_state: object,
        operator_signature: object,
        transition_instant: object,
        effective_at: object = None,
        refusing_check: object = None,
    ) -> Result[ActivationBindingTransition]:
        resolved_phase = _coerce_phase(phase)
        if is_refusal(resolved_phase):
            return resolved_phase
        sid = clean_token(seat_id)
        if sid is None:
            return invalid(
                "seat_id",
                "an activation transition names the admitted seat",
                given=repr(seat_id),
            )
        bid = clean_token(binding_id)
        if bid is None:
            return invalid(
                "binding_id",
                "an activation transition names the live binding",
                given=repr(binding_id),
            )
        requested = _coerce_seat_state(requested_state, "requested_state")
        if is_refusal(requested):
            return requested
        enforced = _coerce_seat_state(enforced_state, "enforced_state")
        if is_refusal(enforced):
            return enforced
        signature = clean_token(operator_signature)
        if signature is None:
            return invalid(
                "operator_signature",
                "activation principal evidence rides the CT-24 transition",
                given=repr(operator_signature),
            )
        if not isinstance(transition_instant, Instant):
            return invalid(
                "transition_instant",
                "a CT-24 activation transition is dated with an injected Instant",
                given=repr(type(transition_instant).__name__),
            )
        bound: Instant | None = None
        if effective_at is not None:
            if not isinstance(effective_at, Instant):
                return invalid(
                    "effective_at",
                    "activation effective-at is an Instant when present",
                    given=repr(type(effective_at).__name__),
                )
            bound = effective_at
        check: str | None = None
        if refusing_check is not None:
            check = clean_token(refusing_check)
            if check is None:
                return invalid(
                    "refusing_check",
                    "a refused activation cites a non-empty refusing check",
                    given=repr(refusing_check),
                )
        states = _validate_phase_states(
            resolved_phase.value,
            requested=requested.value,
            enforced=enforced.value,
        )
        if is_refusal(states):
            return states
        return Ok(
            cls(
                phase=resolved_phase.value,
                seat_id=sid,
                binding_id=bid,
                requested_state=requested.value,
                enforced_state=enforced.value,
                operator_signature=signature,
                transition_instant=transition_instant,
                effective_at=bound,
                refusing_check=check,
            )
        )


@dataclass(frozen=True, slots=True)
class ActivationJournalRow:
    """CT-13 ``risk transition`` envelope pointing at the CT-24 record."""

    event_type: str
    transition_fp1: Fingerprint
    correlation_id: str | None
    payload: Mapping[str, object]

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "event_type": self.event_type,
            "payload": dict(self.payload),
        }
        if self.correlation_id is not None:
            body["correlation_id"] = self.correlation_id
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class ActivationReconstruction:
    """Read-time view over a referenced CT-24 activation transition."""

    requested_state: GovernedSeatState
    enforced_state: GovernedSeatState
    principal: str
    phase: ActivationPhase
    transition_fp1: Fingerprint

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "enforced_state": self.enforced_state.value,
                "phase": self.phase.value,
                "principal": self.principal,
                "requested_state": self.requested_state.value,
                "transition_fp1": self.transition_fp1.value,
            }
        )


@dataclass(frozen=True, slots=True)
class CommittedActivation:
    """Activation outcome after the CT-24/CT-13 persist gate."""

    phase: ActivationPhase
    transition: ActivationBindingTransition
    event: ActivationJournalRow
    acceptance: ActivationAcceptance | None
    readiness: ActivationReadiness | None
    applied: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "applied": self.applied,
                "event_type": self.event.event_type,
                "phase": self.phase.value,
                "transition_fp1": self.event.transition_fp1.value,
            }
        )


def persist_promotion(
    *,
    journal: object,
    card_fp1: object,
    correlation_id: object = None,
) -> Result[PromotionJournalRow]:
    """Append the closed CT-13 promotion event through ``journal``."""
    mapped = assert_closed_ct13_event_type(PROMOTION_EVENT_TYPE)
    if is_refusal(mapped):
        return mapped
    payload = promotion_journal_payload(card_fp1)
    if is_refusal(payload):
        return payload
    widened = set(payload.value) & _WIDENED_PROMOTION_KEYS
    if widened or frozenset(payload.value) != PROMOTION_PAYLOAD_KEYS:
        return policy(
            "payload",
            "the promotion event payload carries only the promotion-card fp1; "
            "operator, artifact, config, and binding detail stay on the card",
            payload_keys=sorted(payload.value),
            allowed=sorted(PROMOTION_PAYLOAD_KEYS),
        )
    correlation = _optional_correlation(correlation_id)
    if is_refusal(correlation):
        return correlation
    sink = _require_journal_sink(journal)
    if is_refusal(sink):
        return sink
    card = cast("Fingerprint", card_fp1)
    row = PromotionJournalRow(
        event_type=mapped.value,
        promotion_card_fp1=card,
        correlation_id=correlation.value,
        payload=payload.value,
    )
    return _append_row(sink.value, row.as_mapping(), row)


def persist_activation(
    *,
    journal: object,
    transition: object,
    correlation_id: object = None,
    event_type: object = ACTIVATION_CT13_EVENT_TYPE,
) -> Result[ActivationJournalRow]:
    """Append activation as CT-24 mapped onto CT-13 ``risk transition``."""
    if not isinstance(transition, ActivationBindingTransition):
        return invalid(
            "transition",
            "activation journals a CT-24 ActivationBindingTransition",
            given=repr(type(transition).__name__),
        )
    mapped = map_activation_ct13_event_type(event_type)
    if is_refusal(mapped):
        return mapped
    fp = transition.fingerprint()
    if is_refusal(fp):
        return fp
    payload = MappingProxyType({"transition_fp1": fp.value.value})
    if frozenset(payload) != ACTIVATION_PAYLOAD_KEYS:
        return policy(
            "payload",
            "the activation journal payload is only the CT-24 transition fp1",
            payload_keys=sorted(payload),
            allowed=sorted(ACTIVATION_PAYLOAD_KEYS),
        )
    correlation = _optional_correlation(correlation_id)
    if is_refusal(correlation):
        return correlation
    sink = _require_journal_sink(journal)
    if is_refusal(sink):
        return sink
    row = ActivationJournalRow(
        event_type=mapped.value,
        transition_fp1=fp.value,
        correlation_id=correlation.value,
        payload=payload,
    )
    return _append_row(sink.value, row.as_mapping(), row)


def commit_promotion(
    landing: object,
    *,
    journal: object,
    correlation_id: object = None,
) -> Result[PromotionLanding]:
    """Persist the promotion event; sink refusal blocks the landing."""
    if not isinstance(landing, PromotionLanding):
        return invalid(
            "landing",
            "promotion persist commits a PromotionLanding",
            given=repr(type(landing).__name__),
        )
    persisted = persist_promotion(
        journal=journal,
        card_fp1=landing.card_fp1,
        correlation_id=correlation_id,
    )
    if is_refusal(persisted):
        return persisted
    del persisted
    return Ok(landing)


def commit_activation(
    *,
    journal: object,
    phase: object,
    correlation_id: object = None,
    acceptance: object = None,
    readiness: object = None,
    landing: object = None,
    operator_signature: object = None,
    transition_instant: object = None,
    refusing_check: object = None,
    event_type: object = ACTIVATION_CT13_EVENT_TYPE,
) -> Result[CommittedActivation]:
    """Persist the CT-24 activation transition before any state takes effect."""
    resolved_phase = _coerce_phase(phase)
    if is_refusal(resolved_phase):
        return resolved_phase
    built = _transition_for_phase(
        resolved_phase.value,
        acceptance=acceptance,
        readiness=readiness,
        landing=landing,
        operator_signature=operator_signature,
        transition_instant=transition_instant,
        refusing_check=refusing_check,
    )
    if is_refusal(built):
        return built
    persisted = persist_activation(
        journal=journal,
        transition=built.value,
        correlation_id=correlation_id,
        event_type=event_type,
    )
    if is_refusal(persisted):
        return persisted
    accepted = acceptance if isinstance(acceptance, ActivationAcceptance) else None
    ready = readiness if isinstance(readiness, ActivationReadiness) else None
    applied = resolved_phase.value is not ActivationPhase.REFUSED
    return Ok(
        CommittedActivation(
            phase=resolved_phase.value,
            transition=built.value,
            event=persisted.value,
            acceptance=accepted,
            readiness=ready,
            applied=applied,
        )
    )


def reconstruct_activation(
    event: object,
    transitions: object,
) -> Result[ActivationReconstruction]:
    """Rebuild requested/enforced/principal from the referenced CT-24 record."""
    if not isinstance(event, Mapping):
        return invalid(
            "event",
            "activation reconstruction reads the CT-13 journal mapping",
            given=repr(type(event).__name__),
        )
    row = cast("Mapping[str, object]", event)
    mapped = map_activation_ct13_event_type(row.get("event_type"))
    if is_refusal(mapped):
        return mapped
    payload = row.get("payload")
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "the activation journal payload is the CT-24 transition pointer",
            given=repr(payload),
        )
    payload_map = cast("Mapping[str, object]", payload)
    if frozenset(payload_map) != ACTIVATION_PAYLOAD_KEYS:
        return policy(
            "payload",
            "requested versus enforced state is reconstructed from the "
            "referenced CT-24 record, never by widening the journal payload",
            payload_keys=sorted(payload_map),
            allowed=sorted(ACTIVATION_PAYLOAD_KEYS),
        )
    pointer = payload_map.get("transition_fp1")
    token = clean_token(pointer)
    if token is None:
        return invalid(
            "transition_fp1",
            "the activation journal payload points at the CT-24 transition fp1",
            given=repr(pointer),
        )
    if not isinstance(transitions, Mapping):
        return invalid(
            "transitions",
            "reconstruction looks up CT-24 records by fingerprint",
            given=repr(type(transitions).__name__),
        )
    record = cast("Mapping[str, object]", transitions).get(token)
    if not isinstance(record, ActivationBindingTransition):
        return invalid(
            "transition_fp1",
            "the referenced CT-24 activation transition is not present",
            transition_fp1=token,
        )
    fp = record.fingerprint()
    if is_refusal(fp):
        return fp
    return Ok(
        ActivationReconstruction(
            requested_state=record.requested_state,
            enforced_state=record.enforced_state,
            principal=record.operator_signature,
            phase=record.phase,
            transition_fp1=fp.value,
        )
    )


def _transition_for_phase(
    phase: ActivationPhase,
    *,
    acceptance: object,
    readiness: object,
    landing: object,
    operator_signature: object,
    transition_instant: object,
    refusing_check: object,
) -> Result[ActivationBindingTransition]:
    if phase is ActivationPhase.SUCCESSFUL:
        if not isinstance(readiness, ActivationReadiness):
            return invalid(
                "readiness",
                "successful activation persist reads ActivationReadiness",
                given=repr(type(readiness).__name__),
            )
        if not readiness.may_mint_intent or not readiness.passed:
            return policy(
                "readiness",
                "successful activation persist requires a passed day-boundary revalidation",
                passed=readiness.passed,
                may_mint_intent=readiness.may_mint_intent,
            )
        acc = readiness.acceptance
        return ActivationBindingTransition.try_create(
            phase=phase,
            seat_id=acc.landing.seat_id,
            binding_id=acc.landing.binding_id,
            requested_state=GovernedSeatState.ACTIVE,
            enforced_state=GovernedSeatState.ACTIVE,
            operator_signature=acc.operator_signature,
            transition_instant=readiness.revalidated_at,
            effective_at=acc.schedule.effective_at,
        )
    if phase is ActivationPhase.REQUESTED:
        if not isinstance(acceptance, ActivationAcceptance):
            return invalid(
                "acceptance",
                "requested activation persist reads ActivationAcceptance",
                given=repr(type(acceptance).__name__),
            )
        return ActivationBindingTransition.try_create(
            phase=phase,
            seat_id=acceptance.landing.seat_id,
            binding_id=acceptance.landing.binding_id,
            requested_state=acceptance.requested_state,
            enforced_state=acceptance.enforced_state,
            operator_signature=acceptance.operator_signature,
            transition_instant=acceptance.schedule.signed_at,
            effective_at=acceptance.schedule.effective_at,
        )
    source = acceptance if isinstance(acceptance, ActivationAcceptance) else None
    land = landing if isinstance(landing, PromotionLanding) else None
    if source is not None:
        land = source.landing
        signature = source.operator_signature
        instant = source.schedule.signed_at
        effective = source.schedule.effective_at
    else:
        signature = operator_signature
        instant = transition_instant
        effective = None
    if not isinstance(land, PromotionLanding):
        return invalid(
            "landing",
            "a refused activation cites the admitted promotion landing",
            given=repr(type(landing).__name__),
        )
    if not isinstance(instant, Instant):
        return invalid(
            "transition_instant",
            "a refused activation is dated with an injected Instant",
            given=repr(type(instant).__name__),
        )
    return ActivationBindingTransition.try_create(
        phase=phase,
        seat_id=land.seat_id,
        binding_id=land.binding_id,
        requested_state=GovernedSeatState.ACTIVE,
        enforced_state=land.seat_state,
        operator_signature=signature,
        transition_instant=instant,
        effective_at=effective,
        refusing_check=refusing_check,
    )


def _coerce_phase(value: object) -> Result[ActivationPhase]:
    if isinstance(value, ActivationPhase):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "phase",
            "activation recording phase is requested, refused, or successful",
            given=repr(value),
            allowed=sorted(item.value for item in ActivationPhase),
        )
    try:
        return Ok(ActivationPhase(token))
    except ValueError:
        return invalid(
            "phase",
            "activation recording phase is requested, refused, or successful",
            given=token,
            allowed=sorted(item.value for item in ActivationPhase),
        )


def _coerce_seat_state(value: object, field: str) -> Result[GovernedSeatState]:
    if isinstance(value, GovernedSeatState):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            field,
            "activation requested and enforced states are governed seat states",
            given=repr(value),
        )
    try:
        return Ok(GovernedSeatState(token))
    except ValueError:
        return invalid(
            field,
            "activation requested and enforced states are governed seat states",
            given=token,
        )


def _validate_phase_states(
    phase: ActivationPhase,
    *,
    requested: GovernedSeatState,
    enforced: GovernedSeatState,
) -> Result[None]:
    if requested is not GovernedSeatState.ACTIVE:
        return policy(
            "requested_state",
            "activation requests ACTIVE; enforced state is reconstructed separately",
            requested_state=requested.value,
        )
    if phase is ActivationPhase.SUCCESSFUL:
        if enforced is not GovernedSeatState.ACTIVE:
            return policy(
                "enforced_state",
                "successful activation enforces ACTIVE only after the day-boundary",
                enforced_state=enforced.value,
            )
        return Ok(None)
    if enforced is GovernedSeatState.ACTIVE:
        return policy(
            "enforced_state",
            "requested or refused activation does not enforce ACTIVE",
            phase=phase.value,
            enforced_state=enforced.value,
        )
    return Ok(None)


def _optional_correlation(value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    token = clean_token(value)
    if token is None:
        return invalid(
            "correlation_id",
            "correlation_id, when present, is a non-blank linking annotation",
            given=repr(value),
        )
    return Ok(token)


def _require_journal_sink(journal: object) -> Result[JournalSink[Mapping[str, object]]]:
    if not isinstance(journal, JournalSink):
        return invalid(
            "journal",
            "promotion and activation persist through a JournalSink; a log line "
            "never substitutes for the missing journal record",
            given=repr(type(journal).__name__),
            logs_are_not_journals=LOGS_ARE_NOT_JOURNALS,
            logs_satisfy_ct13=LOGS_SATISFY_CT13_EVIDENCE,
            log_line_substitutes=LOG_LINE_SUBSTITUTES_FOR_JOURNAL,
            log_record_is_journal_evidence=log_record_is_journal_evidence(),
        )
    return Ok(cast("JournalSink[Mapping[str, object]]", journal))


def _append_row(
    sink: JournalSink[Mapping[str, object]],
    mapping: Mapping[str, object],
    row: _RowT,
) -> Result[_RowT]:
    appended: SinkResult = sink.append(mapping)
    if is_refusal(appended):
        return appended
    if not is_ok(appended):
        return cast("Result[_RowT]", appended)
    return Ok(row)
