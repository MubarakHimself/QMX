"""FTR-04 parent disposition for the cTrader transport locus (DEC-0243).

Epic 24 carries both outcomes and moves only on a formal parent disposition:

* **Accepted** (DEC-0243 APPLIED): transport lands in
  ``qmf.venue.connection.ConnectionManager`` under the named exemption
  ``qmf.venue.connection``.
* **Refused**: the unchanged transport contract lands in ``qmn.venue.ctrader``.

This module records the disposition explicitly so the story never chooses
silently (AR-76; FTR-04).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal
from qmf.venue.connection import ASYNC_CONFORMANCE_EXEMPTION

__all__ = [
    "ASYNC_EXEMPTION_MODULE",
    "FTR04_DISPOSITION",
    "TRANSPORT_LOCUS",
    "ParentAsyncExemptionDisposition",
    "resolve_transport_locus",
]

# Exact exemption name the parent async-conformance test must exempt (DEC-0243).
ASYNC_EXEMPTION_MODULE: Final[str] = ASYNC_CONFORMANCE_EXEMPTION

# Primary locus when the parent accepts the exemption.
_CONNECTION_MANAGER_LOCUS: Final[str] = "qmf.venue.connection.ConnectionManager"
# Fallback locus when and only when the parent refuses the exemption.
_FALLBACK_LOCUS: Final[str] = "qmn.venue.ctrader"


class ParentAsyncExemptionDisposition(StrEnum):
    """Formal parent disposition of the ``qmf.venue.connection`` async exemption."""

    ACCEPTED = "accepted"
    REFUSED = "refused"


# DEC-0243 APPLIED the exemption as a declared exemption — formal parent disposition.
FTR04_DISPOSITION: Final[ParentAsyncExemptionDisposition] = ParentAsyncExemptionDisposition.ACCEPTED

TRANSPORT_LOCUS: Final[str] = (
    _CONNECTION_MANAGER_LOCUS
    if FTR04_DISPOSITION is ParentAsyncExemptionDisposition.ACCEPTED
    else _FALLBACK_LOCUS
)


def resolve_transport_locus(
    disposition: object = FTR04_DISPOSITION,
) -> Result[str]:
    """Resolve the cTrader transport locus from a formal parent disposition.

    Returns the ConnectionManager path when the exemption is accepted, or
    ``qmn.venue.ctrader`` when and only when it is refused. An unknown disposition
    is an ``invalid input`` refusal — never a silent default (FTR-04).
    """
    if isinstance(disposition, ParentAsyncExemptionDisposition):
        resolved = disposition
    elif isinstance(disposition, str):
        try:
            resolved = ParentAsyncExemptionDisposition(disposition)
        except ValueError:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "disposition",
                    "reason": "FTR-04 disposition is accepted | refused",
                    "given": disposition,
                    "allowed": [m.value for m in ParentAsyncExemptionDisposition],
                },
            )
    else:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "disposition",
                "reason": "FTR-04 disposition is accepted | refused",
                "given": repr(disposition),
            },
        )
    if resolved is ParentAsyncExemptionDisposition.ACCEPTED:
        if ASYNC_EXEMPTION_MODULE != "qmf.venue.connection":
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "exemption",
                    "reason": "accepted disposition requires exemption named exactly "
                    "qmf.venue.connection",
                    "given": ASYNC_EXEMPTION_MODULE,
                },
            )
        return Ok(_CONNECTION_MANAGER_LOCUS)
    return Ok(_FALLBACK_LOCUS)
