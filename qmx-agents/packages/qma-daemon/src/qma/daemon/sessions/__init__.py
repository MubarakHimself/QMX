"""Product-session journal projection (Workflows AD-8; Story 55.1).

``product_session`` is not a QMA Session fold and not a tab. Occupancy stays
none until a live-adjacent story. Public calls are compared to
``product_session.context``.
"""

from __future__ import annotations

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
    "BoundProductSessionCall",
    "ProductSession",
    "ProductSessionContext",
    "ProductSessionProfile",
    "ProductSessionService",
    "SelectedRef",
    "bind_public_call_to_context",
    "claim_product_session_at_inspect_sha",
    "parse_product_session_profile",
    "refuse_tab_as_product_session",
]
