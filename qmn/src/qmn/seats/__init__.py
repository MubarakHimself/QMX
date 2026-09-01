"""QL-7 seat-hosting surface (TN-19; Story 26.8).

Hosts governed bots behind the runtime protocol: declared as-of evidence only,
canonical assignment, callback deadline and memory ceiling. A containment
breach quarantines automatically; only operator ``seat_reinstate`` exits.
"""

from __future__ import annotations

from typing import Final

from qmn.seats.host import (
    FORBIDDEN_SEAT_SURFACE_KEYS,
    SEAT_CALLBACK_DEADLINE_REGISTRY_KEY,
    SEAT_MEMORY_CEILING_REGISTRY_KEY,
    GovernedSeat,
    GovernedSeatHandler,
    SeatContainment,
    construct_governed_seat,
    drive_governed_seat,
    refuse_invented_seat_bounds,
)
from qmn.seats.state import (
    OPERATOR_PRINCIPAL,
    OPERATOR_SEAT_REINSTATE,
    QUARANTINE_TRIGGERS,
    SEAT_STATE_WORDS,
    GovernedSeatState,
    QuarantineTrigger,
    SeatTransitionRecord,
    SeatTransitionStream,
    apply_operator_seat_reinstate,
    fold_seat_state,
    mint_quarantine_transition,
    mint_seat_reinstate,
)

__all__ = [
    "FORBIDDEN_SEAT_SURFACE_KEYS",
    "OPERATOR_PRINCIPAL",
    "OPERATOR_SEAT_REINSTATE",
    "QUARANTINE_TRIGGERS",
    "SEATS_SURFACE",
    "SEAT_CALLBACK_DEADLINE_REGISTRY_KEY",
    "SEAT_MEMORY_CEILING_REGISTRY_KEY",
    "SEAT_STATE_WORDS",
    "GovernedSeat",
    "GovernedSeatHandler",
    "GovernedSeatState",
    "QuarantineTrigger",
    "SeatContainment",
    "SeatTransitionRecord",
    "SeatTransitionStream",
    "apply_operator_seat_reinstate",
    "construct_governed_seat",
    "drive_governed_seat",
    "fold_seat_state",
    "mint_quarantine_transition",
    "mint_seat_reinstate",
    "refuse_invented_seat_bounds",
]

SEATS_SURFACE: Final[str] = "qmn.seats"
