"""Binding/config epoch ``state_carry`` enforcement (CT-28; Story 26.4).

At every binding or config epoch transition, ``ledger | cycle | budget |
bench_counter | exposure`` each declare ``carry | reset``. Carry requires a
signed ``carries-ledger`` edge. ``continues-performance`` remains independent
and is never inferred from carries-ledger. Absence is an invalid-input refusal
(FR-077; DEC-0143, DEC-0158).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Ok, Result, is_refusal
from qmf.risk.binding import (
    STATE_CARRY_COUNTERS,
    StateCarry,
    StateCarryChoice,
)

from qmn.ledger._refuse import clean_token, invalid

__all__ = [
    "EPOCH_STATE_CARRY_COUNTERS",
    "EpochStateCarry",
    "require_epoch_state_carry",
    "validate_state_carry_declaration",
]

EPOCH_STATE_CARRY_COUNTERS: Final[tuple[str, ...]] = tuple(c.value for c in STATE_CARRY_COUNTERS)


@dataclass(frozen=True, slots=True)
class EpochStateCarry:
    """Validated per-counter carry|reset declaration for one epoch transition."""

    declaration: Mapping[str, StateCarryChoice]
    carries_ledger_signature: str | None
    continues_performance_signature: str | None

    def carried_counters(self) -> frozenset[str]:
        return frozenset(k for k, v in self.declaration.items() if v is StateCarryChoice.CARRY)

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "state_carry": {k: v.value for k, v in sorted(self.declaration.items())},
        }
        if self.carries_ledger_signature is not None:
            body["carries_ledger_signature"] = self.carries_ledger_signature
        if self.continues_performance_signature is not None:
            body["continues_performance_signature"] = self.continues_performance_signature
        return MappingProxyType(body)


def validate_state_carry_declaration(raw: object) -> Result[Mapping[str, StateCarryChoice]]:
    """Require a complete five-counter ``carry|reset`` map; absence refuses."""
    if raw is None:
        return invalid(
            "state_carry",
            "state_carry is mandatory at every binding/config epoch transition; "
            "absence is an invalid-input refusal",
        )
    if isinstance(raw, StateCarry):
        return Ok(
            MappingProxyType(
                {counter.value: raw.choice_for(counter) for counter in STATE_CARRY_COUNTERS}
            )
        )
    if not isinstance(raw, Mapping):
        return invalid(
            "state_carry",
            "state_carry is a mapping of the five counters to carry|reset",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    resolved: dict[str, StateCarryChoice] = {}
    for name in EPOCH_STATE_CARRY_COUNTERS:
        if name not in body:
            return invalid(
                "state_carry",
                "state_carry must declare every counter; absence is invalid input",
                missing=name,
                required=list(EPOCH_STATE_CARRY_COUNTERS),
            )
        choice = _coerce_choice(body[name])
        if choice is None:
            return invalid(
                "state_carry",
                "each state_carry counter is carry | reset",
                counter=name,
                given=repr(body[name]),
            )
        resolved[name] = choice
    extra = sorted(set(body) - set(EPOCH_STATE_CARRY_COUNTERS))
    if extra:
        return invalid(
            "state_carry",
            "unknown state_carry counters refused",
            unknown=extra,
        )
    return Ok(MappingProxyType(resolved))


def require_epoch_state_carry(
    *,
    state_carry: object,
    carries_ledger_signature: object = None,
    continues_performance_signature: object = None,
) -> Result[EpochStateCarry]:
    """Validate epoch state_carry and gate carry on a signed carries-ledger edge.

    ``continues-performance`` is independent — present or absent without
    implying or being implied by carries-ledger.
    """
    declaration = validate_state_carry_declaration(state_carry)
    if is_refusal(declaration):
        return declaration

    carries_sig: str | None
    if carries_ledger_signature is None:
        carries_sig = None
    else:
        carries_sig = clean_token(carries_ledger_signature)
        if carries_sig is None:
            return invalid(
                "carries_ledger_signature",
                "carries-ledger signature is a non-blank token when supplied",
                given=repr(carries_ledger_signature),
            )

    continues_sig: str | None
    if continues_performance_signature is None:
        continues_sig = None
    else:
        continues_sig = clean_token(continues_performance_signature)
        if continues_sig is None:
            return invalid(
                "continues_performance_signature",
                "continues-performance signature is a non-blank token when supplied",
                given=repr(continues_performance_signature),
            )

    any_carry = any(v is StateCarryChoice.CARRY for v in declaration.value.values())
    if any_carry and carries_sig is None:
        return invalid(
            "carries_ledger_signature",
            "state_carry carry requires a human-signed carries-ledger signature; "
            "continues-performance remains independent and never gates money carry",
        )

    return Ok(
        EpochStateCarry(
            declaration=declaration.value,
            carries_ledger_signature=carries_sig,
            continues_performance_signature=continues_sig,
        )
    )


def _coerce_choice(value: object) -> StateCarryChoice | None:
    if isinstance(value, StateCarryChoice):
        return value
    if isinstance(value, str):
        try:
            return StateCarryChoice(value)
        except ValueError:
            return None
    return None
