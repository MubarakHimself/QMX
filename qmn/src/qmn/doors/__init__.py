"""Three thin doors and no operator command line (TN-17, DEC-0211).

Doors: in-process Python API, localhost HTTP evidence channel, unix-socket
powers channel under ``SO_PEERCRED``. There is no CLI door and no typed
operator command parser — ``qmb`` remains the platform's single command-line
surface. Story 25.8 serves the three doors over one library with derived
parity tests.
"""

from __future__ import annotations

from typing import Final

from qmn.doors.api import API_DOOR, api_door_name
from qmn.doors.http import (
    AGENT_SIGNER_PREFIXES,
    CLOSED_POWERS,
    EVIDENCE_BIND_HOST,
    EVIDENCE_DOOR,
    OPERATOR_ONLY_POWERS,
    OPERATOR_PRINCIPAL,
    OPS_ALLOWED_POWERS,
    OPS_PRINCIPAL,
    POWERS_DISPATCH_SURFACE,
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
    handle_evidence_request,
    handle_powers_call,
    is_human_signer,
    ops_power_allowed,
    powers_door_name,
    powers_transport_identity,
    read_peercred,
    render_evidence_http,
    render_powers_response,
    resolve_peer_principal,
)
from qmn.doors.library import (
    EVIDENCE_CAPABILITIES,
    EVIDENCE_CHANNEL_BUDGET_UNIT,
    LIBRARY_SURFACE,
    DoorRuntime,
    PowersEnactment,
    enact_power,
    library_capability_names,
    read_config_explanation,
    read_failure_detail,
    read_health,
    read_metrics,
    read_projections,
    read_status,
)
from qmn.doors.parity import (
    AGENT_MCP_IN_DOOR_SET,
    CLI_IN_DOOR_SET,
    api_capability_surface,
    capability_gaps,
    door_parity_identity,
)
from qmn.doors.wire import (
    AUTHORITY_LIVE,
    AUTHORITY_REPLICATED,
    AUTHORITY_SOURCES,
    WIRE_FORMAT_VERSION,
    refusal_wire_shape,
    wire_identity,
)

__all__ = [
    "AGENT_MCP_IN_DOOR_SET",
    "AGENT_SIGNER_PREFIXES",
    "API_DOOR",
    "AUTHORITY_LIVE",
    "AUTHORITY_REPLICATED",
    "AUTHORITY_SOURCES",
    "CLI_IN_DOOR_SET",
    "CLOSED_POWERS",
    "DOORS_SURFACE",
    "EVIDENCE_BIND_HOST",
    "EVIDENCE_CAPABILITIES",
    "EVIDENCE_CHANNEL_BUDGET_UNIT",
    "EVIDENCE_DOOR",
    "HAS_OPERATOR_CLI_DOOR",
    "LIBRARY_SURFACE",
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
    "SHIPPED_DOORS",
    "WIRE_FORMAT_VERSION",
    "AuthenticatedPeer",
    "DeclaredPrincipals",
    "DoorRuntime",
    "PeerCredential",
    "PowersCallAuthorization",
    "PowersEnactment",
    "RecordingPowersJournal",
    "api_capability_surface",
    "api_door_name",
    "authorize_powers_call",
    "capability_gaps",
    "declare_principals",
    "door_parity_identity",
    "enact_power",
    "evaluate_unit_principals",
    "evidence_door_name",
    "handle_evidence_request",
    "handle_powers_call",
    "is_human_signer",
    "library_capability_names",
    "ops_power_allowed",
    "powers_door_name",
    "powers_transport_identity",
    "read_config_explanation",
    "read_failure_detail",
    "read_health",
    "read_metrics",
    "read_peercred",
    "read_projections",
    "read_status",
    "refusal_wire_shape",
    "render_evidence_http",
    "render_powers_response",
    "resolve_peer_principal",
    "shipped_doors",
    "wire_identity",
]

DOORS_SURFACE: Final[str] = "qmn.doors"
HAS_OPERATOR_CLI_DOOR: Final[bool] = False
SHIPPED_DOORS: Final[tuple[str, ...]] = (API_DOOR, EVIDENCE_DOOR, POWERS_DOOR)


def shipped_doors() -> tuple[str, ...]:
    """Return the closed three-door set; never a fourth CLI door."""
    return SHIPPED_DOORS
