"""QL-7 seat-hosting surface (TN-19; Stories 26.8, 26.15, 26.16, and 26.19).

Hosts governed bots behind the runtime protocol: declared as-of evidence only,
canonical assignment, callback deadline and memory ceiling. A containment
breach quarantines automatically; only operator ``seat_reinstate`` exits.

Story 26.15: the ungoverned Python-bot tunnel cannot occupy a node seat.
``propose_node_seat`` is the seating door; hosted intents cross Book / BMS /
protection / order and cannot construct CT-19.

Story 26.16: V1 containment is stated honestly — cooperative deadline,
LimitProbe memory, exception quarantine, and slice-progress last-resort.
There is no hardened OS-level confinement; GAP-0054 stays deferred.

Story 26.19: concurrent seat callbacks are proved with host streams, doors,
and timers under injected bounds; isolation and backpressure are measured
without inventing latency budgets or claiming OS confinement.
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
from qmn.seats.containment_limit import (
    COMPENSATING_CONTROLS,
    CONTAINMENT_LIMIT_SURFACE,
    GAP_0054_ID,
    GAP_0054_STATUS,
    V1_HARDENED_OS_CONFINEMENT,
    ContainmentInjection,
    EnforcementClass,
    LimitHonestyRecord,
    SeatContainmentProof,
    V1ContainmentDocsReport,
    prove_v1_seat_containment,
    refuse_invented_os_hard_cap,
    scan_os_confinement_apis,
    v1_containment_documentation_report,
    v1_seat_containment_limits,
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
    "COMPENSATING_CONTROLS",
    "CONTAINMENT_LIMIT_SURFACE",
    "FORBIDDEN_SEAT_SURFACE_KEYS",
    "GAP_0054_ID",
    "GAP_0054_STATUS",
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
    "V1_HARDENED_OS_CONFINEMENT",
    "AdmittedNodeSeat",
    "BookPathContext",
    "ContainmentInjection",
    "EnforcementClass",
    "GovernedSeat",
    "GovernedSeatHandler",
    "GovernedSeatState",
    "LimitHonestyRecord",
    "QuarantineTrigger",
    "SeatAdmissionProof",
    "SeatContainment",
    "SeatContainmentProof",
    "SeatDispatchReceipt",
    "SeatTransitionRecord",
    "SeatTransitionStream",
    "V1ContainmentDocsReport",
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
    "prove_v1_seat_containment",
    "refuse_bot_constructed_ct19",
    "refuse_composition_root_ungoverned_import",
    "refuse_invented_os_hard_cap",
    "refuse_invented_seat_bounds",
    "refuse_ungoverned_tunnel_seat",
    "scan_os_confinement_apis",
    "scan_production_src_for_ungoverned_tunnel",
    "ungoverned_tunnel_names_in_tree",
    "v1_containment_documentation_report",
    "v1_seat_containment_limits",
]

SEATS_SURFACE: Final[str] = "qmn.seats"
