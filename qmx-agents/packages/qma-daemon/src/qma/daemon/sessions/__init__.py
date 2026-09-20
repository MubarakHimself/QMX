"""Product-session journal projection (Workflows AD-8; Stories 55.1–55.2).

``product_session`` is not a QMA Session fold and not a tab. Occupancy stays
none until a live-adjacent story. Public calls are compared to
``product_session.context``. ``granted_ops`` are grant_ids resolved to
host GrantRecords; mismatch and revoke refuse before execution.
"""

from __future__ import annotations

from qma.daemon.sessions.grant_binding import (
    GRANT_ACCEPTED_TABLE,
    GRANT_RECORD_TABLE,
    GRANT_REVOCATION_TABLE,
    GRANT_SIXTH_STORE_MINTED,
    TOOL_REGISTRY_REWRITTEN,
    BoundSessionGrant,
    compare_envelope_to_grant,
)
from qma.daemon.sessions.product_session import (
    PRODUCT_SESSION_CONTEXT_FIELDS,
    PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA,
    PRODUCT_SESSION_FOLD_ID,
    PRODUCT_SESSION_ID_PREFIX,
    PRODUCT_SESSION_INSPECT_SHAS,
    PRODUCT_SESSION_LIVE_ADJACENT,
    PRODUCT_SESSION_NEW_CT_MINTED,
    PRODUCT_SESSION_OCCUPANCY,
    PRODUCT_SESSION_OWNER,
    PRODUCT_SESSION_SIXTH_COMP_MINTED,
    PRODUCT_SESSION_SIXTH_STORE_MINTED,
    PRODUCT_SESSION_STORE,
    PRODUCT_SESSION_STORE_CLASS,
    PRODUCT_SESSION_TABLE,
    PRODUCT_SESSION_WIRED_AT_INSPECT_SHA,
    QMA_SESSION_ID_PREFIX,
    SELECTED_REF_KINDS,
    BoundProductSessionCall,
    ProductSession,
    ProductSessionContext,
    ProductSessionProfile,
    ProductSessionService,
    SelectedRef,
    bind_public_call_to_context,
    claim_product_session_at_inspect_sha,
    parse_product_session_profile,
    refuse_tab_as_product_session,
)

__all__ = [
    "GRANT_ACCEPTED_TABLE",
    "GRANT_RECORD_TABLE",
    "GRANT_REVOCATION_TABLE",
    "GRANT_SIXTH_STORE_MINTED",
    "PRODUCT_SESSION_CONTEXT_FIELDS",
    "PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA",
    "PRODUCT_SESSION_FOLD_ID",
    "PRODUCT_SESSION_ID_PREFIX",
    "PRODUCT_SESSION_INSPECT_SHAS",
    "PRODUCT_SESSION_LIVE_ADJACENT",
    "PRODUCT_SESSION_NEW_CT_MINTED",
    "PRODUCT_SESSION_OCCUPANCY",
    "PRODUCT_SESSION_OWNER",
    "PRODUCT_SESSION_SIXTH_COMP_MINTED",
    "PRODUCT_SESSION_SIXTH_STORE_MINTED",
    "PRODUCT_SESSION_STORE",
    "PRODUCT_SESSION_STORE_CLASS",
    "PRODUCT_SESSION_TABLE",
    "PRODUCT_SESSION_WIRED_AT_INSPECT_SHA",
    "QMA_SESSION_ID_PREFIX",
    "SELECTED_REF_KINDS",
    "TOOL_REGISTRY_REWRITTEN",
    "BoundProductSessionCall",
    "BoundSessionGrant",
    "ProductSession",
    "ProductSessionContext",
    "ProductSessionProfile",
    "ProductSessionService",
    "SelectedRef",
    "bind_public_call_to_context",
    "claim_product_session_at_inspect_sha",
    "compare_envelope_to_grant",
    "parse_product_session_profile",
    "refuse_tab_as_product_session",
]
