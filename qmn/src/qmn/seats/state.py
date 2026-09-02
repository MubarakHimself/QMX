"""Governed seat-state vocabulary and CT-24-shaped transitions (TN-19).

Seat state is a read-time fold over AD-41 seat records and CT-24 transitions —
``admitted | active | benched | quarantined``. Quarantine is automatic on a
callback breach; the only exit is the operator-signed ``seat_reinstate`` power
(DEC-0204, DEC-0251).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import Fingerprint, Instant, Ok, Result, TypedRefusal, fingerprint, is_refusal

from qmn.seats._refuse import clean_token, invalid, policy

__all__ = [
    "OPERATOR_PRINCIPAL",
    "OPERATOR_SEAT_REINSTATE",
    "QUARANTINE_TRIGGERS",
    "SEAT_STATE_WORDS",
    "GovernedSeatState",
    "QuarantineTrigger",
    "SeatTransitionRecord",
    "SeatTransitionStream",
    "apply_operator_seat_reinstate",
    "fold_seat_state",
    "mint_quarantine_transition",
    "mint_seat_reinstate",
]

OPERATOR_SEAT_REINSTATE: Final[str] = "seat_reinstate"
OPERATOR_PRINCIPAL: Final[str] = "operator"

SEAT_TRANSITION_FORMAT_VERSION: Final[int] = 1


class GovernedSeatState(StrEnum):
    """Node seat state — broader than qmf-risk ``active | benched`` routing."""

    ADMITTED = "admitted"
    ACTIVE = "active"
    BENCHED = "benched"
    QUARANTINED = "quarantined"


SEAT_STATE_WORDS: Final[frozenset[str]] = frozenset(state.value for state in GovernedSeatState)


class QuarantineTrigger(StrEnum):
    """Typed causes that auto-enter ``quarantined`` (TN-19)."""

    DEADLINE_BREACH = "deadline-breach"
    MEMORY_CEILING_BREACH = "memory-ceiling-breach"
    CALLBACK_EXCEPTION = "callback-exception"
    NON_RETURNING_CALLBACK = "non-returning-callback"


QUARANTINE_TRIGGERS: Final[frozenset[str]] = frozenset(t.value for t in QuarantineTrigger)


@dataclass(frozen=True, slots=True)
class SeatTransitionRecord:
    """One dated seat-state transition — journaled CT-24 vocabulary (DEC-0251).

    Quarantine transitions carry no operator signature. ``seat_reinstate``
    always does. Restart, boot epoch, and config version never mint one.
    """

    seat_id: str
    binding_ref: str
    from_state: GovernedSeatState
    to_state: GovernedSeatState
    trigger: str
    transition_instant: Instant
    operator_signature: str | None = None
    breach_detail: str | None = None

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "class": "seat-transition-record",
            "seat_id": self.seat_id,
            "binding_ref": self.binding_ref,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "trigger": self.trigger,
            "transition_instant": self.transition_instant.fp1_identity(),
            "format_version": SEAT_TRANSITION_FORMAT_VERSION,
        }
        if self.operator_signature is not None:
            content["operator_signature"] = self.operator_signature
        if self.breach_detail is not None:
            content["breach_detail"] = self.breach_detail
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(self.fp1_identity())

    @classmethod
    def try_create(
        cls,
        *,
        seat_id: object,
        binding_ref: object,
        from_state: object,
        to_state: object,
        trigger: object,
        transition_instant: object,
        operator_signature: object = None,
        breach_detail: object = None,
    ) -> Result[SeatTransitionRecord]:
        sid = clean_token(seat_id)
        if sid is None:
            return invalid(
                "seat_id",
                "a seat transition names a non-empty seat id",
                given=repr(seat_id),
            )
        binding = clean_token(binding_ref)
        if binding is None:
            return invalid(
                "binding_ref",
                "a seat transition cites the Book binding the seat sits at",
                given=repr(binding_ref),
            )
        source = _coerce_state(from_state, "from_state")
        if not isinstance(source, GovernedSeatState):
            return source
        target = _coerce_state(to_state, "to_state")
        if not isinstance(target, GovernedSeatState):
            return target
        trig = clean_token(trigger)
        if trig is None:
            return invalid(
                "trigger",
                "a seat transition carries a non-empty trigger token",
                given=repr(trigger),
            )
        if not isinstance(transition_instant, Instant):
            return invalid(
                "transition_instant",
                "a seat transition is dated with an injected Instant",
                given=repr(transition_instant),
            )
        signature: str | None = None
        if operator_signature is not None:
            signature = clean_token(operator_signature)
            if signature is None:
                return invalid(
                    "operator_signature",
                    "an operator signature is a non-empty token when present",
                    given=repr(operator_signature),
                )
        detail: str | None = None
        if breach_detail is not None:
            detail = clean_token(breach_detail)
            if detail is None:
                return invalid(
                    "breach_detail",
                    "breach detail is a non-empty token when present",
                    given=repr(breach_detail),
                )
        if target is GovernedSeatState.QUARANTINED:
            if trig not in QUARANTINE_TRIGGERS:
                return invalid(
                    "trigger",
                    "quarantine is entered only by deadline-breach, "
                    "memory-ceiling-breach, callback-exception, or "
                    "non-returning-callback",
                    given=trig,
                    allowed=sorted(QUARANTINE_TRIGGERS),
                )
            if signature is not None:
                return invalid(
                    "operator_signature",
                    "automatic quarantine carries no operator signature",
                )
        if trig == OPERATOR_SEAT_REINSTATE:
            if source is not GovernedSeatState.QUARANTINED:
                return policy(
                    "from_state",
                    "seat_reinstate exits quarantined only",
                    given=source.value,
                )
            if target is GovernedSeatState.QUARANTINED:
                return policy(
                    "to_state",
                    "seat_reinstate leaves quarantined; it never re-enters it",
                )
            if signature is None:
                return policy(
                    "operator_signature",
                    "leaving quarantined requires the operator-signed "
                    "seat_reinstate power — never a restart or boot epoch",
                )
        return Ok(
            cls(
                seat_id=sid,
                binding_ref=binding,
                from_state=source,
                to_state=target,
                trigger=trig,
                transition_instant=transition_instant,
                operator_signature=signature,
                breach_detail=detail,
            )
        )


class SeatTransitionStream:
    """Append-only seat-transition log; current state is a read-time fold."""

    def __init__(self) -> None:
        self._by_seat: dict[str, list[SeatTransitionRecord]] = {}
        self._by_fingerprint: dict[str, SeatTransitionRecord] = {}

    def mint(self, record: object) -> Result[Fingerprint]:
        if not isinstance(record, SeatTransitionRecord):
            return invalid(
                "record",
                "the stream mints a SeatTransitionRecord",
                given=repr(record),
            )
        fp = record.fingerprint()
        if is_refusal(fp):
            return fp
        key = fp.value.value
        if key in self._by_fingerprint:
            return invalid(
                "record",
                "the seat-transition stream is append-only; equal fingerprint refused",
                fingerprint=key,
            )
        self._by_fingerprint[key] = record
        self._by_seat.setdefault(record.seat_id, []).append(record)
        return Ok(fp.value)

    def records_for(self, seat_id: object) -> tuple[SeatTransitionRecord, ...]:
        token = clean_token(seat_id)
        if token is None:
            return ()
        return tuple(self._by_seat.get(token, ()))


def fold_seat_state(
    stream: object,
    seat_id: object,
    *,
    initial: object = GovernedSeatState.ADMITTED,
) -> Result[GovernedSeatState]:
    """Fold current seat state from CT-24-shaped transitions — never a stored field."""
    if not isinstance(stream, SeatTransitionStream):
        return invalid(
            "stream",
            "seat state folds over a SeatTransitionStream",
            given=repr(stream),
        )
    start = _coerce_state(initial, "initial")
    if not isinstance(start, GovernedSeatState):
        return start
    current = start
    for record in stream.records_for(seat_id):
        current = record.to_state
    return Ok(current)


def mint_quarantine_transition(
    *,
    seat_id: object,
    binding_ref: object,
    from_state: object,
    trigger: object,
    transition_instant: object,
    breach_detail: object = None,
    stream: object = None,
) -> Result[SeatTransitionRecord]:
    """Automatic quarantine transition — no operator signature (TN-19)."""
    record = SeatTransitionRecord.try_create(
        seat_id=seat_id,
        binding_ref=binding_ref,
        from_state=from_state,
        to_state=GovernedSeatState.QUARANTINED,
        trigger=trigger,
        transition_instant=transition_instant,
        breach_detail=breach_detail,
    )
    if is_refusal(record):
        return record
    if stream is not None:
        if not isinstance(stream, SeatTransitionStream):
            return invalid(
                "stream",
                "quarantine journals onto a SeatTransitionStream",
                given=repr(stream),
            )
        minted = stream.mint(record.value)
        if is_refusal(minted):
            return minted
    return record


def mint_seat_reinstate(
    *,
    seat_id: object,
    binding_ref: object,
    transition_instant: object,
    operator_signature: object,
    to_state: object = GovernedSeatState.ADMITTED,
    stream: object = None,
    infer_from_restart: object = False,
    infer_from_boot_epoch: object = False,
    infer_from_config_version: object = False,
    infer_from_absence_of_breaches: object = False,
) -> Result[SeatTransitionRecord]:
    """Operator-signed exit from ``quarantined`` — the only exit (TN-17/TN-19).

    Lands ``admitted`` by default so reinstate never silently re-arms exposure;
    activation remains a separate act (TN-20). Restart / boot / config / silence
    never substitute for the signed power.
    """
    if infer_from_restart is not False:
        return policy(
            "infer_from_restart",
            "leaving quarantined is never inferred from a restart",
            given=repr(infer_from_restart),
        )
    if infer_from_boot_epoch is not False:
        return policy(
            "infer_from_boot_epoch",
            "leaving quarantined is never inferred from a new boot epoch",
            given=repr(infer_from_boot_epoch),
        )
    if infer_from_config_version is not False:
        return policy(
            "infer_from_config_version",
            "leaving quarantined is never inferred from a config version",
            given=repr(infer_from_config_version),
        )
    if infer_from_absence_of_breaches is not False:
        return policy(
            "infer_from_absence_of_breaches",
            "leaving quarantined is never inferred from the absence of further breaches",
            given=repr(infer_from_absence_of_breaches),
        )
    record = SeatTransitionRecord.try_create(
        seat_id=seat_id,
        binding_ref=binding_ref,
        from_state=GovernedSeatState.QUARANTINED,
        to_state=to_state,
        trigger=OPERATOR_SEAT_REINSTATE,
        transition_instant=transition_instant,
        operator_signature=operator_signature,
    )
    if is_refusal(record):
        return record
    if stream is not None:
        if not isinstance(stream, SeatTransitionStream):
            return invalid(
                "stream",
                "seat_reinstate journals onto a SeatTransitionStream",
                given=repr(stream),
            )
        minted = stream.mint(record.value)
        if is_refusal(minted):
            return minted
    return record


def apply_operator_seat_reinstate(
    *,
    principal: object,
    seat_id: object,
    binding_ref: object,
    transition_instant: object,
    operator_signature: object,
    to_state: object = GovernedSeatState.ADMITTED,
    stream: object = None,
    infer_from_restart: object = False,
    infer_from_boot_epoch: object = False,
    infer_from_config_version: object = False,
    infer_from_absence_of_breaches: object = False,
) -> Result[SeatTransitionRecord]:
    """Operator-principal ``seat_reinstate`` — the only exit from quarantine."""
    actor = clean_token(principal)
    if actor != OPERATOR_PRINCIPAL:
        return policy(
            "principal",
            "leaving quarantined is the operator-signed seat_reinstate power; "
            "ops, restart, and inferred silence cannot exit it",
            given=repr(principal),
            required=OPERATOR_PRINCIPAL,
        )
    return mint_seat_reinstate(
        seat_id=seat_id,
        binding_ref=binding_ref,
        transition_instant=transition_instant,
        operator_signature=operator_signature,
        to_state=to_state,
        stream=stream,
        infer_from_restart=infer_from_restart,
        infer_from_boot_epoch=infer_from_boot_epoch,
        infer_from_config_version=infer_from_config_version,
        infer_from_absence_of_breaches=infer_from_absence_of_breaches,
    )


def _coerce_state(value: object, field: str) -> GovernedSeatState | TypedRefusal:
    if isinstance(value, GovernedSeatState):
        return value
    if isinstance(value, str):
        try:
            return GovernedSeatState(value)
        except ValueError:
            pass
    return invalid(
        field,
        "a governed seat state is admitted | active | benched | quarantined",
        given=repr(value),
        allowed=sorted(SEAT_STATE_WORDS),
    )
