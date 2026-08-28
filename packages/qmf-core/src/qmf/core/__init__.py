"""qmf.core — exact domain foundation.

Roster package of the QMF V1 uv workspace. It declares the package identity and
version and re-exports the public CT-* surface as it lands story by story: CT-04,
the typed refusal envelope; CT-03, the instrument/venue/account identity nouns;
CT-01, the exact money/price/quantity value vocabulary; CT-02, exact time,
calendars, and the injected Clock; CT-05, the single canonical serializer, the
fp1 fingerprint, the result label, and the worlds; and the protocol seams —
``SecretRef``/``SecretValue`` with the read-plus-atomic-replace ``SecretStore``
port, and the ``ObservationSink``/``JournalSink``/``RecordSink`` persistence sinks
whose refusals carry block-on-unpersistable semantics — all injected at the
composition root (CT-21; AR-37, AD-15, DEC-0136, DEC-0138). Nothing here reaches
across a sibling boundary — the default-deny dependency direction (L30) is
preserved by construction, and qmf-core takes zero outside dependencies (DEC-0104).

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
    fingerprint_bytes,
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
from qmf.core.secret import (
    SecretRef,
    SecretStore,
    SecretValue,
)
from qmf.core.sinks import (
    JournalSink,
    ObservationSink,
    RecordSink,
    SinkAck,
    SinkResult,
    is_unpersistable,
    unpersistable,
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
    "JournalSink",
    "Money",
    "MonotonicReading",
    "ObservationSink",
    "OccurrenceRecord",
    "Ok",
    "OrderingKey",
    "Price",
    "PriceDelta",
    "Quantity",
    "RecordSink",
    "RefusalCategory",
    "Result",
    "ResultLabel",
    "Retryability",
    "RoundingMode",
    "SecretRef",
    "SecretStore",
    "SecretValue",
    "SessionWindow",
    "SinkAck",
    "SinkResult",
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
    "fingerprint_bytes",
    "governed_namespace",
    "is_ok",
    "is_refusal",
    "is_unpersistable",
    "reconcile_write",
    "render_utc_iso8601",
    "unpersistable",
    "verify_tzdb_pin",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
