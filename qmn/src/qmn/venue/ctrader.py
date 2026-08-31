"""Fallback cTrader transport locus for a refused parent async exemption (FTR-04).

When DEC-0243's named exemption ``qmf.venue.connection`` is **accepted** (the
standing parent disposition), the live asyncio TLS transport lives in
:class:`qmf.venue.connection.ConnectionManager` and this module refuses to host a
second transport. If and only if the parent formally **refuses** that exemption,
the unchanged transport contract lands here (DEC-0243, DEC-0196, AR-76).

Story 24.1 carries both outcomes explicitly; it never chooses silently.
"""

from __future__ import annotations

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal

from qmn.venue.disposition import (
    ASYNC_EXEMPTION_MODULE,
    FTR04_DISPOSITION,
    ParentAsyncExemptionDisposition,
    resolve_transport_locus,
)

__all__ = [
    "host_transport_allowed",
    "transport_contract_summary",
]


def host_transport_allowed(
    disposition: object = FTR04_DISPOSITION,
) -> Result[bool]:
    """Whether this fallback module may host the cTrader TLS transport.

    Returns ``Ok(True)`` only under a formal ``refused`` disposition. Under the
    standing ``accepted`` disposition the transport stays in
    ``qmf.venue.connection.ConnectionManager`` and hosting here is a typed
    ``policy rejection`` (FTR-04; DEC-0243).
    """
    locus = resolve_transport_locus(disposition)
    if not isinstance(locus, Ok):
        return locus
    if locus.value == "qmn.venue.ctrader":
        return Ok(True)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context={
            "field": "transport_locus",
            "reason": "parent accepted the qmf.venue.connection async exemption; "
            "transport stays in ConnectionManager and must not be duplicated here",
            "disposition": (
                disposition.value
                if isinstance(disposition, ParentAsyncExemptionDisposition)
                else repr(disposition)
            ),
            "exemption": ASYNC_EXEMPTION_MODULE,
            "active_locus": locus.value,
        },
    )


def transport_contract_summary() -> dict[str, object]:
    """The unchanged transport contract both loci honour (DEC-0196).

    Credential-free description only — no host dial, no secret, no network.
    """
    locus = resolve_transport_locus()
    standing = locus.value if isinstance(locus, Ok) else "unresolved"
    return {
        "tls_port": 5035,
        "proto_tag_registry": "venue_protocol_artifact",
        "proto_tag_pinned": 91,
        "protobuf_runtime": "protobuf==7.36.0",
        "framing": "length-prefixed-ProtoMessage",
        "banned": ("Spotware SDK", "Twisted", "second event loop", "second connection manager"),
        "exemption_name": ASYNC_EXEMPTION_MODULE,
        "standing_disposition": FTR04_DISPOSITION.value,
        "standing_locus": standing,
    }
