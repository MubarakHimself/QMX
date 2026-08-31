"""Amend atomicity gate and tightening-act preservation (Story 24.7 / QMX-F063).

When CT-18 amend atomicity has not been measured for the account/order type,
dynamic protection is limited to the ratified single-sided breakeven ratchet
form or refused before origination per Book policy. The command path never
invents an amend sequence (cancel-then-place, multi-step, or dual-side
packaging).

A risk-non-increasing ``amend_protection`` that has already been originated is
never suppressed by ``registry:amend_min_improvement`` (origination policy
only). The act is journaled before dispatch; UNKNOWN holds it as a standing
intent for re-decision (Story 24.6 / AD-34 / DEC-0150).

``close_partial`` is refused as unsupported; fractional close is never emulated
by close-then-replace. The five CT-19 command kinds remain closed (CT-19; TN-6).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    Instant,
    JournalSink,
    Ok,
    PriceDelta,
    RefusalCategory,
    Result,
    Retryability,
    SinkResult,
    TypedRefusal,
    is_ok,
    is_refusal,
)

from qmn.venue import (
    Command,
    CommandKind,
    ProtectionAmendment,
    ProtectionSide,
)

__all__ = [
    "AMEND_JOURNAL_KIND",
    "CT19_CLOSED_KINDS",
    "AmendAtomicity",
    "AmendJournalRecord",
    "AmendSequencePlan",
    "BookDynamicProtectionPolicy",
    "DynamicProtectionOrigin",
    "admit_risk_non_increasing_amend_protection",
    "ct19_kinds_are_closed",
    "enforce_closed_ct19_vocabulary",
    "gate_amend_protection",
    "is_breakeven_ratchet_amendment",
    "is_single_sided_amendment",
    "journal_amend_before_dispatch",
    "refuse_close_partial",
    "refuse_close_then_replace",
    "refuse_invented_amend_sequence",
    "resolve_amend_atomicity",
]


AMEND_JOURNAL_KIND: Final[str] = "amend-protection-intent"
_CLOSE_PARTIAL_KIND: Final[str] = "close_partial"

CT19_CLOSED_KINDS: Final[frozenset[str]] = frozenset(
    {
        CommandKind.PLACE_ORDER.value,
        CommandKind.CANCEL_ORDER.value,
        CommandKind.CLOSE_POSITION.value,
        CommandKind.CLOSE_ALL.value,
        CommandKind.AMEND_PROTECTION.value,
    }
)


class AmendAtomicity(StrEnum):
    """Measured CT-18 amend-atomicity values plus the unmeasured state."""

    ATOMIC = "atomic"
    NON_ATOMIC = "non-atomic"
    UNDOCUMENTED = "undocumented"
    UNMEASURED = "unmeasured"


class BookDynamicProtectionPolicy(StrEnum):
    """Book policy when amend atomicity is not proven for dual-side amends."""

    SINGLE_SIDED_BREAKEVEN_RATCHET = "single-sided-breakeven-ratchet"
    REFUSE_BEFORE_ORIGINATION = "refuse-before-origination"


class DynamicProtectionOrigin(StrEnum):
    """Who authored the amend — dynamic Book ratchet vs already-originated act."""

    BREAKEVEN_RATCHET = "breakeven-ratchet"
    BOT_PROPOSAL = "bot-proposal"
    OPERATOR = "operator"
    BOOK_FORCE = "book-force"


@dataclass(frozen=True, slots=True)
class AmendSequencePlan:
    """An invented multi-step amend plan the command path must refuse."""

    steps: tuple[str, ...]
    detail: str = ""


@dataclass(frozen=True, slots=True)
class AmendJournalRecord:
    """Evidence that an ``amend_protection`` was journaled before dispatch."""

    kind: str
    command_fp1: str
    command_kind: str
    protection_side: str
    journaled_at_ns: int
    atomicity: str
    origin: str


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


def _unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


def resolve_amend_atomicity(measured: object) -> AmendAtomicity:
    """Resolve measured amend atomicity; absent/blank/unknown → UNMEASURED."""
    if measured is None:
        return AmendAtomicity.UNMEASURED
    if isinstance(measured, AmendAtomicity):
        return measured
    if isinstance(measured, str):
        token = measured.strip().lower()
        if token == "":
            return AmendAtomicity.UNMEASURED
        try:
            return AmendAtomicity(token)
        except ValueError:
            return AmendAtomicity.UNMEASURED
    if isinstance(measured, Mapping):
        payload = cast("Mapping[str, object]", measured)
        raw = payload.get("atomicity", payload.get("amend_atomicity"))
        return resolve_amend_atomicity(raw)
    # MeasuredFact-like: .measured mapping + optional .verdict attribute.
    measured_attr = getattr(measured, "measured", None)
    verdict = getattr(measured, "verdict", None)
    if measured_attr is not None:
        if verdict is not None and str(getattr(verdict, "value", verdict)).lower() != "verified":
            return AmendAtomicity.UNMEASURED
        return resolve_amend_atomicity(measured_attr)
    return AmendAtomicity.UNMEASURED


def _atomicity_unproven(atomicity: AmendAtomicity) -> bool:
    return atomicity is not AmendAtomicity.ATOMIC


def is_single_sided_amendment(amendment: object) -> bool:
    """V1 ``ProtectionAmendment`` is one side by construction."""
    return isinstance(amendment, ProtectionAmendment)


def is_breakeven_ratchet_amendment(
    amendment: object,
    *,
    breakeven_offset: object = None,
) -> Result[bool]:
    """True when a stop-side amendment lands at the declared breakeven offset."""
    if not isinstance(amendment, ProtectionAmendment):
        return _invalid(
            "protection_amendment",
            "breakeven ratchet check reads a typed ProtectionAmendment",
            given=type(amendment).__name__,
        )
    if amendment.protection_side is not ProtectionSide.STOP:
        return Ok(False)
    if breakeven_offset is None:
        offset_result = PriceDelta.try_create(
            0, amendment.new_distance.instrument, amendment.new_distance.scale
        )
        if is_refusal(offset_result):
            return offset_result
        offset = offset_result.value
    elif isinstance(breakeven_offset, PriceDelta):
        if breakeven_offset.instrument != amendment.new_distance.instrument:
            return _invalid(
                "breakeven_offset",
                "breakeven offset must name the amendment instrument",
            )
        offset = breakeven_offset
    else:
        return _invalid(
            "breakeven_offset",
            "breakeven offset is a PriceDelta or absent for a zero offset",
            given=repr(breakeven_offset),
        )
    return Ok(amendment.new_distance.as_fraction() == offset.as_fraction())


def refuse_invented_amend_sequence(plan: object) -> TypedRefusal:
    """Refuse any invented multi-step amend / cancel-replace sequence."""
    steps: tuple[str, ...]
    detail = "command path never invents an amend sequence"
    if isinstance(plan, AmendSequencePlan):
        steps = plan.steps
        if plan.detail:
            detail = plan.detail
    elif isinstance(plan, Sequence) and not isinstance(plan, (str, bytes)):
        steps = tuple(str(step) for step in cast("Sequence[object]", plan))
    else:
        steps = (repr(plan),)
    return _unsupported(
        "amend_sequence",
        detail,
        steps=list(steps),
        forbidden=("cancel-then-place", "dual-side-packaging", "multi-step-amend"),
    )


def refuse_close_partial(**extra: object) -> TypedRefusal:
    """``close_partial`` is not a V1 kind — unsupported capability refusal."""
    return _unsupported(
        "close_partial",
        "close_partial is not a V1 exit or command kind; a partial exit is an "
        "unsupported-capability refusal and is never emulated by close-then-replace",
        **extra,
    )


def refuse_close_then_replace(**extra: object) -> TypedRefusal:
    """Refuse fractional-close emulation via close-then-replace."""
    return _unsupported(
        "close_then_replace",
        "fractional close is never emulated by close-then-replace; that opens the "
        "unprotected window amend_protection forbids",
        **extra,
    )


def ct19_kinds_are_closed() -> bool:
    """True when CommandKind is exactly the five ratified CT-19 members."""
    return {kind.value for kind in CommandKind} == set(CT19_CLOSED_KINDS)


def enforce_closed_ct19_vocabulary(kind: object) -> Result[str]:
    """Admit only the five closed CT-19 kinds; refuse close_partial and others."""
    if not ct19_kinds_are_closed():
        return _policy(
            "command_kind",
            "CT-19 command vocabulary drifted; five kinds must remain closed",
            observed=sorted(kind.value for kind in CommandKind),
            required=sorted(CT19_CLOSED_KINDS),
        )
    if isinstance(kind, CommandKind):
        kind_token = kind.value
    elif isinstance(kind, str):
        kind_token = kind.strip().lower()
    else:
        return _invalid(
            "command_kind",
            "CT-19 vocabulary gate reads a CommandKind or kind token",
            given=repr(kind),
        )
    if kind_token == _CLOSE_PARTIAL_KIND:
        return refuse_close_partial()
    if kind_token not in CT19_CLOSED_KINDS:
        return _unsupported(
            "command_kind",
            "kind is outside the closed five-member CT-19 vocabulary",
            given=kind_token,
            allowed=sorted(CT19_CLOSED_KINDS),
        )
    return Ok(kind_token)


def admit_risk_non_increasing_amend_protection(
    command: object,
    *,
    amend_min_improvement: object = None,
) -> Result[Command]:
    """Admit an originated risk-non-increasing amend; never apply the threshold.

    ``registry:amend_min_improvement`` is Book origination policy only. The command
    path must not re-apply it as a suppression once the act has been originated.
    """
    del amend_min_improvement  # origination policy only — never a command-path gate
    if not isinstance(command, Command):
        return _invalid(
            "command",
            "amend admit reads a typed CT-19 Command",
            given=type(command).__name__,
        )
    if command.kind is not CommandKind.AMEND_PROTECTION:
        return _invalid(
            "command_kind",
            "amend_min_improvement non-suppression applies to amend_protection",
            given=command.kind.value,
        )
    if command.protection_amendment is None:
        return _invalid(
            "protection_amendment",
            "amend_protection carries a typed ProtectionAmendment",
        )
    return Ok(command)


def journal_amend_before_dispatch(
    command: object,
    *,
    journal: object,
    journaled_at: object,
    atomicity: object = AmendAtomicity.UNMEASURED,
    origin: object = DynamicProtectionOrigin.BOOK_FORCE,
) -> Result[AmendJournalRecord]:
    """Journal a risk-non-increasing amend_protection before wire dispatch."""
    admitted = admit_risk_non_increasing_amend_protection(command)
    if is_refusal(admitted):
        return admitted
    cmd = admitted.value
    amendment = cmd.protection_amendment
    if amendment is None:
        return _invalid(
            "protection_amendment",
            "amend_protection journals its typed ProtectionAmendment",
        )
    if not isinstance(journaled_at, Instant):
        return _invalid(
            "journaled_at",
            "amend journal stamp is a wall Instant",
            given=repr(journaled_at),
        )
    if not isinstance(journal, JournalSink):
        return _invalid(
            "journal",
            "amend_protection is journaled through a JournalSink before dispatch",
            given=type(journal).__name__,
        )
    sink = cast("JournalSink[Mapping[str, object]]", journal)
    fp = cmd.fingerprint()
    if is_refusal(fp):
        return fp
    resolved_atomicity = resolve_amend_atomicity(atomicity)
    if isinstance(origin, DynamicProtectionOrigin):
        origin_token = origin.value
    elif isinstance(origin, str) and origin.strip() != "":
        origin_token = origin.strip().lower()
    else:
        return _invalid(
            "origin",
            "amend journal records a DynamicProtectionOrigin or non-empty token",
            given=repr(origin),
        )
    record = AmendJournalRecord(
        kind=AMEND_JOURNAL_KIND,
        command_fp1=fp.value.value,
        command_kind=cmd.kind.value,
        protection_side=amendment.protection_side.value,
        journaled_at_ns=journaled_at.value_ns,
        atomicity=resolved_atomicity.value,
        origin=origin_token,
    )
    event: dict[str, object] = {
        "kind": record.kind,
        "command_fp1": record.command_fp1,
        "command_kind": record.command_kind,
        "protection_side": record.protection_side,
        "journaled_at_ns": record.journaled_at_ns,
        "atomicity": record.atomicity,
        "origin": record.origin,
        "phase": "before-dispatch",
    }
    appended: SinkResult = sink.append(event)
    if is_refusal(appended):
        return appended
    if not is_ok(appended):
        return cast("Result[AmendJournalRecord]", appended)
    return Ok(record)


def gate_amend_protection(
    command: object,
    *,
    atomicity: object,
    book_policy: object = BookDynamicProtectionPolicy.SINGLE_SIDED_BREAKEVEN_RATCHET,
    origin: object = DynamicProtectionOrigin.BOT_PROPOSAL,
    breakeven_offset: object = None,
    dual_side_requested: object = False,
    amend_sequence: object = None,
) -> Result[Command]:
    """Gate one ``amend_protection`` under measured amend atomicity (QMX-F063).

    Unmeasured / undocumented / non-atomic: dynamic protection is limited to the
    single-sided breakeven ratchet or refused before origination per Book policy.
    Dual-side and invented sequences always refuse unless atomicity is proven
    atomic — and even then the path never invents a multi-step amend sequence.
    """
    vocab = enforce_closed_ct19_vocabulary(
        command.kind if isinstance(command, Command) else command
    )
    if is_refusal(vocab):
        return vocab
    if not isinstance(command, Command):
        return _invalid(
            "command",
            "amend atomicity gate reads a typed CT-19 Command",
            given=type(command).__name__,
        )
    if command.kind is not CommandKind.AMEND_PROTECTION:
        return Ok(command)

    if amend_sequence is not None:
        return refuse_invented_amend_sequence(amend_sequence)
    if dual_side_requested is True:
        resolved = resolve_amend_atomicity(atomicity)
        if _atomicity_unproven(resolved):
            return _unsupported(
                "amend_atomicity",
                "dual-side protection amendment refuses until amend atomicity is "
                "measured atomic; single-sided amendment is the only legal V1 path",
                atomicity=resolved.value,
            )
        # Proven atomic still forbids inventing a sequence — no dual-side kind exists.
        return refuse_invented_amend_sequence(
            AmendSequencePlan(
                steps=("amend_stop", "amend_target"),
                detail=(
                    "even with atomic amend semantics the command path never invents "
                    "a dual-side amend sequence; ProtectionAmendment is single-sided"
                ),
            )
        )

    amendment = command.protection_amendment
    if amendment is None or not is_single_sided_amendment(amendment):
        return _invalid(
            "protection_amendment",
            "amend_protection carries a single-sided typed ProtectionAmendment",
        )

    resolved_atomicity = resolve_amend_atomicity(atomicity)
    if isinstance(book_policy, BookDynamicProtectionPolicy):
        policy = book_policy
    elif isinstance(book_policy, str):
        try:
            policy = BookDynamicProtectionPolicy(book_policy.strip().lower())
        except ValueError:
            return _invalid(
                "book_policy",
                "Book dynamic-protection policy is single-sided-breakeven-ratchet "
                "or refuse-before-origination",
                given=book_policy,
            )
    else:
        return _invalid(
            "book_policy",
            "Book dynamic-protection policy is a BookDynamicProtectionPolicy",
            given=repr(book_policy),
        )

    if isinstance(origin, DynamicProtectionOrigin):
        resolved_origin = origin
    elif isinstance(origin, str):
        try:
            resolved_origin = DynamicProtectionOrigin(origin.strip().lower())
        except ValueError:
            return _invalid(
                "origin",
                "amend origin is a DynamicProtectionOrigin token",
                given=origin,
            )
    else:
        return _invalid(
            "origin",
            "amend origin is a DynamicProtectionOrigin",
            given=repr(origin),
        )

    # Dynamic Book ratchet under unproven atomicity.
    if (
        resolved_origin is DynamicProtectionOrigin.BREAKEVEN_RATCHET
        and _atomicity_unproven(resolved_atomicity)
    ):
        if policy is BookDynamicProtectionPolicy.REFUSE_BEFORE_ORIGINATION:
            return _policy(
                "amend_atomicity",
                "Book policy refuses dynamic protection before origination while "
                "amend atomicity is unproven",
                atomicity=resolved_atomicity.value,
                book_policy=policy.value,
            )
        ratchet = is_breakeven_ratchet_amendment(
            amendment, breakeven_offset=breakeven_offset
        )
        if is_refusal(ratchet):
            return ratchet
        if not ratchet.value:
            return _policy(
                "dynamic_protection",
                "while amend atomicity is unproven, dynamic protection is limited "
                "to the ratified single-sided breakeven ratchet form",
                atomicity=resolved_atomicity.value,
                book_policy=policy.value,
                protection_side=amendment.protection_side.value,
            )

    return admit_risk_non_increasing_amend_protection(command)
