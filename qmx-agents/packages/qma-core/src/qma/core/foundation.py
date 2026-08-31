"""qmf-core foundations QMA reuses — never re-derives (AD-3; DEC-0302; FR-Q04).

Money, time, ids, ``correlation_id``, ``fp1``, and the typed-refusal base are
imported from ``qmf-core``. This module re-exports them so QMA units have one
import surface and cannot mint a parallel base.
"""

from __future__ import annotations

from qmf.core.chrono import (
    CalendarIdentity,
    Clock,
    Duration,
    Instant,
    Interval,
    TradingDate,
    WriterId,
)
from qmf.core.exact import Money, Price, PriceDelta, Quantity
from qmf.core.fingerprint import (
    Fingerprint,
    canonical_bytes,
    fingerprint,
    fingerprint_bytes,
)
from qmf.core.identity import Account, Instrument, Venue, VenueId
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

# CT-13 linking annotation: qmf-core pins the field as an opaque string, not a
# distinct class. QMA must not mint a parallel CorrelationId value type.
type CorrelationId = str

__all__ = [
    "Account",
    "CalendarIdentity",
    "Clock",
    "CorrelationId",
    "Duration",
    "Fingerprint",
    "Instant",
    "Instrument",
    "Interval",
    "Money",
    "Ok",
    "Price",
    "PriceDelta",
    "Quantity",
    "RefusalCategory",
    "Result",
    "Retryability",
    "TradingDate",
    "TypedRefusal",
    "Venue",
    "VenueId",
    "WriterId",
    "canonical_bytes",
    "fingerprint",
    "fingerprint_bytes",
    "is_ok",
    "is_refusal",
]
