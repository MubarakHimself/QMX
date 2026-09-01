"""QL-7 seat-hosting surface (TN-19; Stories 26.8 and 26.15).

Hosts governed bots behind the runtime protocol: declared as-of evidence only,
canonical assignment, callback deadline and memory ceiling. A containment
breach quarantines automatically; only operator ``seat_reinstate`` exits.

Story 26.15: the ungoverned Python-bot tunnel cannot occupy a node seat.
``propose_node_seat`` is the seating door; hosted intents cross Book / BMS /
protection / order and cannot construct CT-19.
"""

from __future__ import annotations

from typing import Final

from qmn.seats.admission import (
    ADMISSION_LAYER_NAMES,
    SEAT_ADMISSION_PROOFS,
    SEAT_ADMISSION_SURFACE,
    UNGOVERNED_EVIDENCE_KINDS,
    UNGOVERNED_TUNNEL_NAMES,
    AdmittedNodeSeat,
    SeatAdmissionProof,
    cite_governed_seat_occurrence,
    inject_seat_callback,
    propose_node_seat,
    refuse_composition_root_ungoverned_import,
    refuse_ungoverned_tunnel_seat,
    scan_production_src_for_ungoverned_tunnel,
    ungoverned_tunnel_names_in_tree,
)
from qmn.seats.dispatch import (
    INTENT_PATH_HOPS,
    BookPathContext,
    SeatDispatchReceipt,
    dispatch_hosted_intents,
    dispatch_seat_intents,
    refuse_bot_constructed_ct19,
)
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
    "ADMISSION_LAYER_NAMES",
    "FORBIDDEN_SEAT_SURFACE_KEYS",
    "INTENT_PATH_HOPS",
    "OPERATOR_PRINCIPAL",
    "OPERATOR_SEAT_REINSTATE",
    "QUARANTINE_TRIGGERS",
    "SEATS_SURFACE",
    "SEAT_ADMISSION_PROOFS",
    "SEAT_ADMISSION_SURFACE",
    "SEAT_CALLBACK_DEADLINE_REGISTRY_KEY",
    "SEAT_MEMORY_CEILING_REGISTRY_KEY",
    "SEAT_STATE_WORDS",
    "UNGOVERNED_EVIDENCE_KINDS",
    "UNGOVERNED_TUNNEL_NAMES",
    "AdmittedNodeSeat",
    "BookPathContext",
    "GovernedSeat",
    "GovernedSeatHandler",
    "GovernedSeatState",
    "QuarantineTrigger",
    "SeatAdmissionProof",
    "SeatContainment",
    "SeatDispatchReceipt",
    "SeatTransitionRecord",
    "SeatTransitionStream",
    "apply_operator_seat_reinstate",
    "cite_governed_seat_occurrence",
    "construct_governed_seat",
    "dispatch_hosted_intents",
    "dispatch_seat_intents",
    "drive_governed_seat",
    "fold_seat_state",
    "inject_seat_callback",
    "mint_quarantine_transition",
    "mint_seat_reinstate",
    "propose_node_seat",
    "refuse_bot_constructed_ct19",
    "refuse_composition_root_ungoverned_import",
    "refuse_invented_seat_bounds",
    "refuse_ungoverned_tunnel_seat",
    "scan_production_src_for_ungoverned_tunnel",
    "ungoverned_tunnel_names_in_tree",
]

SEATS_SURFACE: Final[str] = "qmn.seats"
