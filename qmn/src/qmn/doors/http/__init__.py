"""Localhost HTTP evidence channel and AF_UNIX powers channel (TN-17).

Evidence is publish-never-act. Powers authenticate operator vs ops principals
at the transport under ``SO_PEERCRED`` (Story 25.7 / QMX-F045).
"""

from __future__ import annotations

from typing import Final

from qmn.doors.http.powers import (
    AGENT_SIGNER_PREFIXES,
    CLOSED_POWERS,
    OPERATOR_ONLY_POWERS,
    OPERATOR_PRINCIPAL,
    OPS_ALLOWED_POWERS,
    OPS_PRINCIPAL,
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
    is_human_signer,
    ops_power_allowed,
    powers_transport_identity,
    read_peercred,
    resolve_peer_principal,
)

__all__ = [
    "AGENT_SIGNER_PREFIXES",
    "CLOSED_POWERS",
    "EVIDENCE_DOOR",
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
    "AuthenticatedPeer",
    "DeclaredPrincipals",
    "PeerCredential",
    "PowersCallAuthorization",
    "RecordingPowersJournal",
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
]

EVIDENCE_DOOR: Final[str] = "evidence_http"
POWERS_DOOR: Final[str] = "powers_unix"


def evidence_door_name() -> str:
    return EVIDENCE_DOOR


def powers_door_name() -> str:
    return POWERS_DOOR
