"""Three thin doors and no operator command line (TN-17, DEC-0211).

Doors: in-process Python API, localhost HTTP evidence channel, unix-socket
powers channel under ``SO_PEERCRED``. There is no CLI door and no typed
operator command parser — ``qmb`` remains the platform's single command-line
surface.
"""

from __future__ import annotations

from typing import Final

from qmn.doors.api import API_DOOR, api_door_name
from qmn.doors.http import (
    AGENT_SIGNER_PREFIXES,
    CLOSED_POWERS,
    EVIDENCE_DOOR,
    OPERATOR_ONLY_POWERS,
    OPERATOR_PRINCIPAL,
    OPS_ALLOWED_POWERS,
    OPS_PRINCIPAL,
    POWERS_DOOR,
    POWERS_SOCKET_MODE,
    POWERS_SOCKET_OWNER,
    POWERS_SOCKET_PATH,
    POWERS_TRANSPORT_SURFACE,
    PRINCIPAL_SET,
    SERVICE_ACCOUNT_NAME,
    AuthenticatedPeer,
    DeclaredPrincipals,
    PeerCredential,
    PowersCallAuthorization,
    RecordingPowersJournal,
    authorize_powers_call,
    declare_principals,
    evaluate_unit_principals,
    evidence_door_name,
    is_human_signer,
    ops_power_allowed,
    powers_door_name,
    powers_transport_identity,
    read_peercred,
    resolve_peer_principal,
)

__all__ = [
    "AGENT_SIGNER_PREFIXES",
    "API_DOOR",
    "CLOSED_POWERS",
    "DOORS_SURFACE",
    "EVIDENCE_DOOR",
    "HAS_OPERATOR_CLI_DOOR",
    "OPERATOR_ONLY_POWERS",
    "OPERATOR_PRINCIPAL",
    "OPS_ALLOWED_POWERS",
    "OPS_PRINCIPAL",
    "POWERS_DOOR",
    "POWERS_SOCKET_MODE",
    "POWERS_SOCKET_OWNER",
    "POWERS_SOCKET_PATH",
    "POWERS_TRANSPORT_SURFACE",
    "PRINCIPAL_SET",
    "SERVICE_ACCOUNT_NAME",
    "SHIPPED_DOORS",
    "AuthenticatedPeer",
    "DeclaredPrincipals",
    "PeerCredential",
    "PowersCallAuthorization",
    "RecordingPowersJournal",
    "api_door_name",
    "authorize_powers_call",
    "declare_principals",
    "evaluate_unit_principals",
    "evidence_door_name",
    "is_human_signer",
    "ops_power_allowed",
    "powers_door_name",
    "powers_transport_identity",
    "read_peercred",
    "resolve_peer_principal",
    "shipped_doors",
]

DOORS_SURFACE: Final[str] = "qmn.doors"
HAS_OPERATOR_CLI_DOOR: Final[bool] = False
SHIPPED_DOORS: Final[tuple[str, ...]] = (API_DOOR, EVIDENCE_DOOR, POWERS_DOOR)


def shipped_doors() -> tuple[str, ...]:
    """The closed three-door set; never a fourth CLI door."""
    return SHIPPED_DOORS
