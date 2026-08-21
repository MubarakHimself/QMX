"""qmf.core — exact domain foundation.

Roster package of the QMF V1 uv workspace. It declares the package identity and
version and re-exports the public CT-* surface as it lands story by story: CT-04,
the typed refusal envelope; CT-03, the instrument/venue/account identity nouns;
CT-01, the exact money/price/quantity value vocabulary; CT-02, exact time,
calendars, and the injected Clock; and CT-05, the single canonical serializer, the
fp1 fingerprint, the result label, and the worlds. Nothing here reaches across a
sibling boundary — the default-deny dependency direction (L30) is preserved by
construction, and qmf-core takes zero outside dependencies (DEC-0104).

``CONTRACT_FORMAT_VERSION`` re-exported here is CT-01's; each contract owns its own
format version, so CT-02's is reached as ``qmf.core.chrono.CONTRACT_FORMAT_VERSION``
and CT-05's as ``qmf.core.fingerprint.CONTRACT_FORMAT_VERSION``.
"""

from __future__ import annotations

from qmf.core.chrono import (
    CalendarIdentity,
    CivilDate,
    Clock,
    ClockKind,
    DataDrivenClock,
    DisplayTime,
    Duration,
    Instant,
    Interval,
    MonotonicReading,
    OrderingKey,
    SessionWindow,
    TemporalOrder,
    TradingDate,
    WriterId,
    WriterSequencer,
    compare_causal,
    render_utc_iso8601,
    verify_tzdb_pin,
)
from qmf.core.exact import (
    CONTRACT_FORMAT_VERSION,
    ExactRational,
    Money,
    Price,
    PriceDelta,
    Quantity,
    RoundingMode,
    UnitKind,
    ValueFactor,
)
from qmf.core.fingerprint import (
    LIVE_EVIDENCE_NAMESPACE,
    EvidenceClass,
    Fingerprint,
    GovernedEvidenceLedger,
    OccurrenceRecord,
    ResultLabel,
    World,
    WriteOutcome,
    WriteReceipt,
    canonical_bytes,
    fingerprint,
    governed_namespace,
    reconcile_write,
)
from qmf.core.identity import (
    Account,
    AccountRole,
    DatedRecord,
    Instrument,
    Venue,
    VenueId,
)
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "LIVE_EVIDENCE_NAMESPACE",
    "Account",
    "AccountRole",
    "CalendarIdentity",
    "CivilDate",
    "Clock",
    "ClockKind",
    "DataDrivenClock",
    "DatedRecord",
    "DisplayTime",
    "Duration",
    "EvidenceClass",
    "ExactRational",
    "Fingerprint",
    "GovernedEvidenceLedger",
    "Instant",
    "Instrument",
    "Interval",
    "Money",
    "MonotonicReading",
    "OccurrenceRecord",
    "Ok",
    "OrderingKey",
    "Price",
    "PriceDelta",
    "Quantity",
    "RefusalCategory",
    "Result",
    "ResultLabel",
    "Retryability",
    "RoundingMode",
    "SessionWindow",
    "TemporalOrder",
    "TradingDate",
    "TypedRefusal",
    "UnitKind",
    "ValueFactor",
    "Venue",
    "VenueId",
    "World",
    "WriteOutcome",
    "WriteReceipt",
    "WriterId",
    "WriterSequencer",
    "__version__",
    "canonical_bytes",
    "compare_causal",
    "fingerprint",
    "governed_namespace",
    "is_ok",
    "is_refusal",
    "reconcile_write",
    "render_utc_iso8601",
    "verify_tzdb_pin",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
