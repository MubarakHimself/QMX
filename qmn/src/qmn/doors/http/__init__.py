"""Localhost HTTP evidence channel and AF_UNIX powers channel (TN-17).

Evidence is publish-never-act. Powers authenticate operator vs ops principals
at the transport under ``SO_PEERCRED`` (Story 25.7 / QMX-F045) and enact through
the shared door library (Story 25.8).
"""

from __future__ import annotations

from qmn.doors.http.dispatch import (
    POWERS_DISPATCH_SURFACE,
    handle_powers_call,
    powers_capability_surface,
    render_powers_response,
)
from qmn.doors.http.evidence import (
    EVIDENCE_BIND_HOST,
    EVIDENCE_DOOR,
    EVIDENCE_ROUTES,
    evidence_capability_surface,
    evidence_door_name,
    evidence_identity,
    handle_evidence_request,
    render_evidence_http,
)
from qmn.doors.http.powers import (
    AGENT_SIGNER_PREFIXES,
    CLOSED_POWERS,
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
    is_human_signer,
    ops_power_allowed,
    powers_transport_identity,
    read_peercred,
    resolve_peer_principal,
)

__all__ = [
    "AGENT_SIGNER_PREFIXES",
    "CLOSED_POWERS",
    "EVIDENCE_BIND_HOST",
    "EVIDENCE_DOOR",
    "EVIDENCE_ROUTES",
    "OPERATOR_ONLY_POWERS",
    "OPERATOR_PRINCIPAL",
    "OPS_ALLOWED_POWERS",
    "OPS_PRINCIPAL",
    "POWERS_DISPATCH_SURFACE",
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
    "evidence_capability_surface",
    "evidence_door_name",
    "evidence_identity",
    "handle_evidence_request",
    "handle_powers_call",
    "is_human_signer",
    "ops_power_allowed",
    "powers_capability_surface",
    "powers_door_name",
    "powers_transport_identity",
    "read_peercred",
    "render_evidence_http",
    "render_powers_response",
    "resolve_peer_principal",
]


def powers_door_name() -> str:
    return POWERS_DOOR
