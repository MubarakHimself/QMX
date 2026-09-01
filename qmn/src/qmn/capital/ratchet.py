"""V1 breakeven ratchet: Book origination then command-path dispatch (TN-8/TN-24g).

Trigger / offset / ``amend_min_improvement`` originate a risk-non-increasing
proposal under Book exit_policy. Once originated, the command path dispatches
the single-sided ``amend_protection`` without reapplying the origination
threshold. No other dynamic-protection grammar exists in V1 (DEC-0209).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import ExactRational, Ok, Price, PriceDelta, Result, UnitKind, is_ok, is_refusal
from qmf.risk.exit_record import check_move_to_breakeven_ratchet

from qmn.capital._refuse import invalid, policy, unsupported
from qmn.order.amend import (
    BookDynamicProtectionPolicy,
    DynamicProtectionOrigin,
    admit_risk_non_increasing_amend_protection,
    gate_amend_protection,
    is_breakeven_ratchet_amendment,
)
from qmn.venue import Command, CommandKind, ProtectionAmendment, ProtectionSide

__all__ = [
    "AMEND_MIN_IMPROVEMENT_REGISTRY_KEY",
    "BREAKEVEN_RATCHET_OFFSET_REGISTRY_KEY",
    "BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY",
    "V1_DYNAMIC_PROTECTION_GRAMMAR",
    "BreakevenRatchetOrigin",
    "BreakevenRatchetProposal",
    "DynamicProtectionGrammar",
    "dispatch_originated_breakeven_ratchet",
    "originate_breakeven_ratchet",
    "refuse_non_breakeven_dynamic_grammar",
    "v1_dynamic_protection_is_breakeven_ratchet_only",
]


BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY: Final[str] = "breakeven_ratchet_trigger"
BREAKEVEN_RATCHET_OFFSET_REGISTRY_KEY: Final[str] = "breakeven_ratchet_offset"
AMEND_MIN_IMPROVEMENT_REGISTRY_KEY: Final[str] = "amend_min_improvement"
V1_DYNAMIC_PROTECTION_GRAMMAR: Final[str] = "single-sided-breakeven-ratchet"


class DynamicProtectionGrammar(StrEnum):
    """Closed V1 dynamic-protection grammar — ratchet only (TN-24g)."""

    SINGLE_SIDED_BREAKEVEN_RATCHET = "single-sided-breakeven-ratchet"


class BreakevenRatchetOrigin(StrEnum):
    """Whether Book policy originated a proposal this evaluation."""

    ORIGINATED = "originated"
    NOT_YET = "not-yet"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class BreakevenRatchetProposal:
    """Book-originated single-sided move-to-breakeven amendment."""

    origin: BreakevenRatchetOrigin
    amendment: ProtectionAmendment | None
    trigger_registry_key: str = BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY
    offset_registry_key: str = BREAKEVEN_RATCHET_OFFSET_REGISTRY_KEY
    min_improvement_registry_key: str = AMEND_MIN_IMPROVEMENT_REGISTRY_KEY
    grammar: DynamicProtectionGrammar = (
        DynamicProtectionGrammar.SINGLE_SIDED_BREAKEVEN_RATCHET
    )

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "grammar": self.grammar.value,
            "min_improvement_registry_key": self.min_improvement_registry_key,
            "offset_registry_key": self.offset_registry_key,
            "origin": self.origin.value,
            "trigger_registry_key": self.trigger_registry_key,
        }
        if self.amendment is not None:
            body["amendment"] = self.amendment.fp1_identity()
        return MappingProxyType(body)


def v1_dynamic_protection_is_breakeven_ratchet_only() -> bool:
    """True when the closed V1 grammar is exactly the breakeven ratchet."""
    return (
        frozenset(member.value for member in DynamicProtectionGrammar)
        == frozenset({V1_DYNAMIC_PROTECTION_GRAMMAR})
    )


def refuse_non_breakeven_dynamic_grammar(grammar: object) -> Result[None]:
    """Refuse any dynamic-protection grammar other than the V1 ratchet."""
    token = grammar.value if isinstance(grammar, DynamicProtectionGrammar) else grammar
    if isinstance(token, str) and token.strip().lower() == V1_DYNAMIC_PROTECTION_GRAMMAR:
        return Ok(None)
    return unsupported(
        "dynamic_protection_grammar",
        "V1 dynamic protection is the single-sided breakeven ratchet only; "
        "no other dynamic-protection grammar exists",
        given=repr(grammar),
        allowed=[V1_DYNAMIC_PROTECTION_GRAMMAR],
    )


def originate_breakeven_ratchet(
    *,
    original_risk_distance: object,
    current_stop_distance: object,
    favorable_excursion: object,
    reference_price: object,
    trigger: object,
    offset: object = None,
    amend_min_improvement: object = None,
) -> Result[BreakevenRatchetProposal]:
    """Book exit_policy origination of a move-to-breakeven proposal (TN-8).

    ``trigger``, ``offset``, and ``amend_min_improvement`` gate ORIGINATION only.
    A proposal that fails the risk-non-increasing / breakeven-landing checks
    refuses; conditions not yet met return ``origin=not-yet`` without an
    amendment. The command path must never re-apply these thresholds.
    """
    if not isinstance(original_risk_distance, PriceDelta):
        return invalid(
            "original_risk_distance",
            "ratchet origination reads the frozen original_risk_distance",
            given=repr(original_risk_distance),
        )
    if not isinstance(current_stop_distance, PriceDelta):
        return invalid(
            "current_stop_distance",
            "ratchet origination reads the current stop PriceDelta",
            given=repr(current_stop_distance),
        )
    if not isinstance(reference_price, Price):
        return invalid(
            "reference_price",
            "ratchet origination carries the declared reference Price",
            given=repr(reference_price),
        )
    if not isinstance(trigger, ExactRational) or trigger.unit_kind is not UnitKind.R_MULTIPLE:
        return invalid(
            BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY,
            "breakeven_ratchet_trigger is a positive r-multiple ExactRational — "
            "Book-declared, never a spine constant",
            given=repr(trigger),
        )
    if trigger.as_fraction() <= 0:
        return invalid(
            BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY,
            "breakeven_ratchet_trigger is a positive r-multiple",
            given=str(trigger.as_fraction()),
        )
    excursion = _coerce_excursion(favorable_excursion)
    if not isinstance(excursion, ExactRational):
        return excursion

    # Origination threshold: favorable excursion must reach the trigger.
    if excursion.as_fraction() < trigger.as_fraction():
        return Ok(
            BreakevenRatchetProposal(
                origin=BreakevenRatchetOrigin.NOT_YET,
                amendment=None,
            )
        )

    # Land at declared offset (default zero — stop at entry).
    if offset is None:
        offset_r = PriceDelta.try_create(
            0, original_risk_distance.instrument, original_risk_distance.scale
        )
        if is_refusal(offset_r):
            return offset_r
        resolved_offset = offset_r.value
    elif isinstance(offset, PriceDelta):
        resolved_offset = offset
    else:
        return invalid(
            BREAKEVEN_RATCHET_OFFSET_REGISTRY_KEY,
            "breakeven_ratchet_offset is a PriceDelta or absent for a zero offset",
            given=repr(offset),
        )

    # Minimum improvement is origination policy only — compare against current stop.
    if amend_min_improvement is not None:
        if (
            not isinstance(amend_min_improvement, ExactRational)
            or amend_min_improvement.unit_kind is not UnitKind.R_MULTIPLE
        ):
            return invalid(
                AMEND_MIN_IMPROVEMENT_REGISTRY_KEY,
                "amend_min_improvement is an r-multiple ExactRational at origination",
                given=repr(amend_min_improvement),
            )
        if amend_min_improvement.as_fraction() < 0:
            return invalid(
                AMEND_MIN_IMPROVEMENT_REGISTRY_KEY,
                "amend_min_improvement is a non-negative r-multiple",
                given=str(amend_min_improvement.as_fraction()),
            )
        improvement = current_stop_distance.as_fraction() - resolved_offset.as_fraction()
        # Improvement measured in original-risk R units.
        original = original_risk_distance.as_fraction()
        if original <= 0:
            return invalid(
                "original_risk_distance",
                "original_risk_distance must be positive to measure improvement",
                given=str(original),
            )
        improvement_r = improvement / original
        if improvement_r < amend_min_improvement.as_fraction():
            return Ok(
                BreakevenRatchetProposal(
                    origin=BreakevenRatchetOrigin.NOT_YET,
                    amendment=None,
                )
            )

    ratchet_ok = check_move_to_breakeven_ratchet(
        original_risk_distance=original_risk_distance,
        proposed_risk_distance=resolved_offset,
        breakeven_offset=resolved_offset,
    )
    if is_refusal(ratchet_ok):
        return ratchet_ok

    amendment_r = ProtectionAmendment.try_create(
        ProtectionSide.STOP,
        resolved_offset,
        reference_price,
        original_risk_distance=original_risk_distance,
    )
    if is_refusal(amendment_r):
        return amendment_r
    is_be = is_breakeven_ratchet_amendment(
        amendment_r.value, breakeven_offset=resolved_offset
    )
    if is_refusal(is_be):
        return is_be
    if not is_be.value:
        return policy(
            "amendment",
            "originated amendment must be the single-sided breakeven ratchet form",
        )
    return Ok(
        BreakevenRatchetProposal(
            origin=BreakevenRatchetOrigin.ORIGINATED,
            amendment=amendment_r.value,
        )
    )


def dispatch_originated_breakeven_ratchet(
    command: object,
    *,
    atomicity: object = None,
    amend_min_improvement: object = None,
    breakeven_offset: object = None,
) -> Result[Command]:
    """Dispatch an originated ratchet amend without reapplying origination thresholds.

    ``amend_min_improvement`` is accepted only to prove it is ignored on the
    command path — Book origination already applied it.
    """
    # Prove the threshold is never a command-path gate.
    del amend_min_improvement
    if not isinstance(command, Command):
        return invalid(
            "command",
            "ratchet dispatch reads a typed CT-19 Command",
            given=type(command).__name__,
        )
    if command.kind is not CommandKind.AMEND_PROTECTION:
        return invalid(
            "command",
            "breakeven ratchet dispatch is an amend_protection command",
            given=command.kind.value,
        )
    grammar = refuse_non_breakeven_dynamic_grammar(
        DynamicProtectionGrammar.SINGLE_SIDED_BREAKEVEN_RATCHET
    )
    if is_refusal(grammar):
        return grammar

    gated = gate_amend_protection(
        command,
        atomicity=atomicity,
        book_policy=BookDynamicProtectionPolicy.SINGLE_SIDED_BREAKEVEN_RATCHET,
        origin=DynamicProtectionOrigin.BREAKEVEN_RATCHET,
        breakeven_offset=breakeven_offset,
    )
    if is_refusal(gated):
        return gated
    # Admit without re-applying amend_min_improvement (origination policy only).
    admitted = admit_risk_non_increasing_amend_protection(
        gated.value, amend_min_improvement=None
    )
    if is_refusal(admitted):
        return admitted
    assert is_ok(admitted)
    return admitted


def _coerce_excursion(value: object) -> ExactRational | Result[BreakevenRatchetProposal]:
    if isinstance(value, ExactRational) and value.unit_kind is UnitKind.R_MULTIPLE:
        return value
    return invalid(
        "favorable_excursion",
        "favorable excursion is an r-multiple ExactRational measured against "
        "frozen original_risk_distance",
        given=repr(value),
    )
