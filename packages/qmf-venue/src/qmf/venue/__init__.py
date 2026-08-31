"""qmf.venue — the venue seam (edge module nothing imports).

Roster package of the QMF V1 uv workspace. It imports only ``qmf-core`` and nothing
imports it — the default-deny dependency direction (L30/DEC-0120) holds by
construction.

Story 8.1 lands the first work unit: the cTrader capability probe and the
per-(VenueId, account) venue-observation profile it records. The probe connects to a
demo venue through a throwaway :class:`~qmf.venue.probe.ProbeTransport` seam, runs the
first-connection verify-or-refuse suite (spot-timestamp unit, daily boundary, bar
basis, pip formula, money exponent), and returns its recorded profile plus a findings
note surfacing contradictions with upstream assumptions (FR-022, FR-026, SC-02,
AR-45/AR-46; DEC-0135, DEC-0138). The port contracts CT-18..CT-21 and the connection
manager land in later stories; the probe deliberately depends on none of them.

Story 8.2 adds the in-house proto compilation (:mod:`qmf.venue.proto`): the Spotware
``openapi-proto-messages`` release is compiled from its message definitions (data, not
code) through the ``protobuf`` runtime — a qmf-venue-only dependency — pinned at the
injected AD-6 integer release tag, so the adapter owns its own transport, zero Spotware
SDK code runs, and a tag change is a governed re-verification event (AR-43, FR-026,
DEC-0141). Importing ``google.protobuf`` here is the module's only third-party import;
a compiled proto message never leaks into ``qmf-core``.

Story 8.3 adds the connection manager, the secret lifecycle, and injected-sink wiring
(:mod:`qmf.venue.connection`): the :class:`~qmf.venue.connection.ConnectionManager` is
the sole owner of venue sessions and the single in-memory holder of secret *values*,
fed by a composition-root-injected :class:`~qmf.core.SecretStore` port (read + atomic
replace) and calling the injected core sink protocols synchronously. Credentials never
leave it and never render; rotation is store-before-discard; a ``storage failure`` from
any command-path sink blocks the command stream while the sensing pipe is unaffected;
and an :class:`~qmf.venue.connection.AccountBinding`'s secret reference is
occurrence/display-only and excluded from fp1 (CT-21, AR-37, AR-38, AR-47; DEC-0136,
DEC-0138).

Story 8.4 adds two-artifact capability discovery wired in a fixed order
(:mod:`qmf.venue.capabilities`): the static, adapter-version-scoped, credential-free
:class:`~qmf.venue.capabilities.CapabilityDeclaration` (carrying the venue protocol
artifact identity, a marking per roster field, the pinned :class:`~qmf.venue.capabilities.ErrorMap`,
and an identity-bearing fingerprint) plus the per-(VenueId, account) venue-observation
profile, orchestrated by :class:`~qmf.venue.capabilities.CapabilityDiscovery`. The
declaration is present at construction and the profile must exist before the first
command and before any evidence-bearing decode; a measured-at-connection capability
consumed before its profile exists is an unavailable-dependency refusal, a
measured-but-unverified one consumed in evidence-bearing work is a policy-rejection
refusal, and an undeclared capability or unsupported close scope is an
unsupported-capability refusal never widened; an unmapped venue error code takes the
fail-closed default — transient venue failure, retryable = no, outcome = UNKNOWN, plus an
alarm — and a verified daily boundary anchors a venue-scoped market-hours calendar for
venue-native BarSpec (FR-022, CT-18, AR-45, AR-46, SC-09; DEC-0135, DEC-0137, DEC-0138,
DEC-0141).

Story 8.5 adds the five typed command kinds under the four-outcome law
(:mod:`qmf.venue.commands`): :class:`~qmf.venue.commands.Command` carries exactly one of
``place_order``, ``cancel_order``, ``close_position``, ``close_all``, and
``amend_protection``, typed per kind on qmf-core nouns with no free-form payload (a
fractional or partial close is an unsupported-capability refusal); every well-formed
submission resolves through :class:`~qmf.venue.commands.CommandOutcomeResolver` to exactly
one of :class:`~qmf.venue.commands.SubmissionOutcome`'s four members — accepted-by-venue,
rejected-by-venue, denied-locally, or UNKNOWN — with denied-locally an outcome (never a
refusal) and UNKNOWN a state (never an error), each minting a
:class:`~qmf.venue.commands.CommandObservation` and a :class:`~qmf.venue.commands.JournalEvent`;
command identity is the record's fp1, and where the CT-18 client-id mapping is not
injective-and-total a durable :class:`~qmf.venue.commands.CommandIdBinding` persists through
the injected sink before submission with idempotent re-presentation and alarmed collision
(:class:`~qmf.venue.commands.CommandIdBindingRegistry`); ``amend_protection`` is
risk-non-increasing per protection side (:class:`~qmf.venue.commands.ProtectionAmendment`);
and a compound command's outcome is the meet of its children — any child UNKNOWN makes the
parent UNKNOWN, any non-success makes it partially-executed, never a success
(:class:`~qmf.venue.commands.CompoundCommand`, :func:`~qmf.venue.commands.meet_outcomes`)
(FR-023, CT-19, CT-20, AR-44, AR-48; DEC-0137, DEC-0138, DEC-0140, DEC-0148).

Story 8.6 adds record-before-interpret events and on-demand reconciliation
(:mod:`qmf.venue.events`): every inbound venue event is stored verbatim through
:class:`~qmf.venue.events.EventRecorder` — with the mandatory receive wall time and
boot-scoped monotonic stamp — and journaled before any state evaluation as one ordered
multi-room unit (raw archive, journal, registry room) with a named
:class:`~qmf.venue.events.TransactionBoundary`, a partial write being a storage-failure
refusal that blocks the command stream (the sensing pipe unaffected) and is journaled on
recovery; the order-state machine is a read-time fold over the observation stream
(:func:`~qmf.venue.events.fold_order_state`, :class:`~qmf.venue.events.OrderStateProjection`)
and never a stored field, command outcome and order state stay separate streams, and a
terminal state is decided only by fills and venue lifecycle events; an observation with no
legal transition is annotated with a typed
:class:`~qmf.venue.events.OutOfSequenceEdge` and forces its owning command to UNKNOWN
(adapters never synthesize an observation); reconciliation is an on-demand read-back over a
mandatory declared lookback (:class:`~qmf.venue.events.ReconciliationReadback`) whose
verdict is one of :class:`~qmf.venue.events.ReconciliationVerdict`'s four members —
reconciled, drift, unknown, or out-of-lookback (the fourth so "I cannot see that far back"
is never read as "the position closed") — gating the command pipe only; and a
close_position, close_all, or amend_protection whose subject is observed terminal at or
after the submit stamp resolves rejected-by-venue (superseded-by-terminal-subject) — a named
outcome, never UNKNOWN — while an absent or already-terminal subject resolves without
submission (:func:`~qmf.venue.events.resolve_subject_terminal`) (FR-024, CT-20, AR-47,
SCN-0005; DEC-0137, DEC-0138, DEC-0140, DEC-0148, DEC-0150, DEC-0158).

Story 8.7 adds the UNKNOWN command-stream block and its explicit resolution
(:mod:`qmf.venue.blocking`): while an ``UNKNOWN`` is outstanding on a ``(VenueId, account)``
stream the :class:`~qmf.venue.blocking.UnknownGate` refuses new commands
(:meth:`~qmf.venue.blocking.UnknownGate.admit`; ``transient venue failure``, after-condition
= resolution) and never clears its own block — a refused **risk-reducing** act
(``cancel_order``, ``close_position``, ``close_all``, ``amend_protection``) never evaporates
but is preserved as a :class:`~qmf.venue.blocking.StandingProtectionIntent` journaled before
dispatch and re-decided (explicitly not retried) against a ``reconciled`` verdict only, with
``drift``, ``unknown``, and ``out-of-lookback`` alarming and holding it open
(:meth:`~qmf.venue.blocking.UnknownGate.redecide_standing_intent`); the risk-reducing kinds
dispatch ahead of ``place_order`` on every shared throttle
(:func:`~qmf.venue.blocking.order_for_shared_throttle`) and ``suspend-new`` takes local
effect instantly with no venue round-trip
(:meth:`~qmf.venue.blocking.UnknownGate.suspend_new`); and the block clears only on an
explicit :meth:`~qmf.venue.blocking.UnknownGate.resolve_unknown` call carrying one of
``observed-accepted | observed-absent | operator-attested`` — the
:class:`~qmf.venue.blocking.ResolveResolution` set — itself recorded as an observation,
never on a reconciliation verdict alone (FR-023, CT-19, SCN-0005; DEC-0137, DEC-0148,
DEC-0150, DEC-0158).

Story 8.8 lands the cTrader adapter as adapter #1, honoring the ratified venue facts as
per-broker configuration (:mod:`qmf.venue.ctrader`). The cTrader-platform facts are standing
obligations named at their point of use (DEC-0135): inbound decode crosses the named
money-path boundary — per-field Unix-ms UTC timestamps with mandatory receive-time recording,
no server clock existing (:func:`~qmf.venue.ctrader.decode_timestamp`); the 1/100000
market-data wire scale as an exact scaled integer
(:func:`~qmf.venue.ctrader.decode_market_data_price`); execution prices as raw doubles
crossing AD-7's boundary to the instrument's declared digits under a declared rounding mode
(:func:`~qmf.venue.ctrader.decode_execution_price`); and a ``moneyDigits`` exponent on the
nine money-bearing messages (:data:`~qmf.venue.ctrader.MONEY_BEARING_MESSAGES`) whose absence
refuses that message's money decode (:func:`~qmf.venue.ctrader.decode_money`). The adapter
paces itself at 50/s non-historical + 5/s historical per connection
(:class:`~qmf.venue.ctrader.RatePacer`), adopts the 10-second heartbeat bound, and enforces
the one-week historical tick-span cap (:func:`~qmf.venue.ctrader.tick_span_within_cap`), with
demo and live separate hosts requiring two simultaneous connections
(:class:`~qmf.venue.ctrader.SessionTopology`). The ~30-day access token and never-expiring
refresh token with cTID re-authorization are the declared
:class:`~qmf.venue.ctrader.TokenLifecycle`; heartbeat, token refresh, reconnect, gap replay,
and verification monitors are declared schedulable duties
(:data:`~qmf.venue.ctrader.SESSION_DUTIES`) the application's scheduler drives; and session
recovery never resubmits a command (:class:`~qmf.venue.ctrader.SessionRecovery`). The demoted
17:00-New-York daily boundary and BID-derived trendbar basis are never hardcoded —
:class:`~qmf.venue.ctrader.CTraderBrokerConfiguration` reads each from the venue-observation
profile, verify-or-refuse — and which broker fronts the platform is deployment configuration,
so :class:`~qmf.venue.ctrader.CTraderAdapter` names no broker and stays venue-blind above the
port (FR-025, FR-026, AR-42, AR-46; DEC-0135, DEC-0139).
"""

from __future__ import annotations

from qmf.venue.blocking import (
    RISK_REDUCING_KINDS,
    AdmissionDisposition,
    AdmissionResult,
    ResolveObservation,
    ResolveResolution,
    StandingIntentDecision,
    StandingIntentDisposition,
    StandingIntentJournalEvent,
    StandingProtectionIntent,
    StreamBlockCause,
    UnknownBlock,
    UnknownGate,
    is_risk_reducing,
    order_for_shared_throttle,
    throttle_priority,
)
from qmf.venue.capabilities import (
    CapabilityDeclaration,
    CapabilityDiscovery,
    CapabilityField,
    CapabilityFieldName,
    CloseScope,
    ErrorMap,
    ErrorMapResolution,
    ErrorMapRow,
    FieldMarking,
    SubmissionOutcomeClass,
)
from qmf.venue.commands import (
    FOUR_OUTCOME_LAW,
    BindingOutcome,
    Command,
    CommandIdBinding,
    CommandIdBindingRegistry,
    CommandKind,
    CommandObservation,
    CommandOutcomeResolver,
    CompoundChild,
    CompoundCommand,
    JournalEvent,
    OrderParameters,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    SubmissionOutcome,
    SubmissionResult,
    TimeInForce,
    UnknownTrigger,
    command_id_mapping_is_injective_total,
    derive_child_identity,
    is_success,
    journal_event_type,
    meet_outcomes,
)
from qmf.venue.connection import (
    ASYNC_CONFORMANCE_EXEMPTION,
    CTRADER_OPEN_API_PORT,
    AccountBinding,
    BlockCause,
    CommandPipeStatus,
    ConnectionManager,
    HealthReport,
    PipeState,
    decode_framed_payload,
    encode_framed_payload,
    venue_command_stream,
    venue_writer_id,
)
from qmf.venue.ctrader import (
    ACCESS_TOKEN_LIFETIME_CLASS,
    HEARTBEAT_BOUND_SECONDS,
    HISTORICAL_RATE_LIMIT_PER_SECOND,
    HISTORICAL_TICK_SPAN_CAP_MS,
    INVALIDATION_ANCHOR,
    MARKET_DATA_WIRE_SCALE_EXPONENT,
    MONEY_BEARING_MESSAGES,
    NON_HISTORICAL_RATE_LIMIT_PER_SECOND,
    REFRESH_TOKEN_LIFETIME_CLASS,
    SESSION_DUTIES,
    ConnectionEndpoint,
    CTraderAdapter,
    CTraderBrokerConfiguration,
    DecodedExecutionPrice,
    DecodedTimestamp,
    InFlightResolution,
    RatePacer,
    RequestClass,
    SchedulableDuty,
    SessionDuty,
    SessionRecovery,
    SessionTopology,
    TimestampUnit,
    TokenLifecycle,
    VenueEnvironment,
    decode_execution_price,
    decode_market_data_price,
    decode_money,
    decode_timestamp,
    tick_span_within_cap,
)
from qmf.venue.events import (
    EventRecorder,
    InboundVenueEvent,
    MultiRoomWrite,
    MultiRoomWriteResult,
    ObservationJournalEvent,
    ObservationKind,
    OrderState,
    OrderStateProjection,
    OutOfSequenceEdge,
    PartialWriteRecovery,
    Reconciliation,
    ReconciliationReadback,
    ReconciliationVerdict,
    SubjectResolution,
    SubjectTerminalOutcome,
    TransactionBoundary,
    VenueNativeIdentity,
    WriteRoom,
    detect_out_of_sequence,
    fold_order_state,
    is_legal_transition,
    observation_journal_event_type,
    resolve_subject_terminal,
)
from qmf.venue.observation import (
    FIRST_CONNECTION_CHECKS,
    PROBE_V1_CHECKS,
    REQUIRED_CONNECTION_CHECKS,
    MeasuredFact,
    ProbeCheck,
    ProbeVerdict,
    VenueEvidenceClass,
    VenueObservationProfile,
)
from qmf.venue.probe import (
    AccountMoneyRecord,
    CapabilityProbe,
    Finding,
    FindingsNote,
    ProbeReport,
    ProbeTransport,
    SpotSample,
    SymbolMetadataRecord,
    Tick,
    TickHistorySample,
    Trendbar,
    TrendbarSample,
    UpstreamAssumption,
)
from qmf.venue.proto import (
    SPOTWARE_PROTO_PACKAGE,
    CompiledProto,
    ProtoArtifact,
    TagChangeAssessment,
    assess_tag_change,
    compile_descriptor_set,
    descriptor_set_digest,
)

__all__ = [
    "ACCESS_TOKEN_LIFETIME_CLASS",
    "ASYNC_CONFORMANCE_EXEMPTION",
    "CTRADER_OPEN_API_PORT",
    "FIRST_CONNECTION_CHECKS",
    "FOUR_OUTCOME_LAW",
    "HEARTBEAT_BOUND_SECONDS",
    "HISTORICAL_RATE_LIMIT_PER_SECOND",
    "HISTORICAL_TICK_SPAN_CAP_MS",
    "INVALIDATION_ANCHOR",
    "MARKET_DATA_WIRE_SCALE_EXPONENT",
    "MONEY_BEARING_MESSAGES",
    "NON_HISTORICAL_RATE_LIMIT_PER_SECOND",
    "PROBE_V1_CHECKS",
    "REFRESH_TOKEN_LIFETIME_CLASS",
    "REQUIRED_CONNECTION_CHECKS",
    "RISK_REDUCING_KINDS",
    "SESSION_DUTIES",
    "SPOTWARE_PROTO_PACKAGE",
    "AccountBinding",
    "AccountMoneyRecord",
    "AdmissionDisposition",
    "AdmissionResult",
    "BindingOutcome",
    "BlockCause",
    "CTraderAdapter",
    "CTraderBrokerConfiguration",
    "CapabilityDeclaration",
    "CapabilityDiscovery",
    "CapabilityField",
    "CapabilityFieldName",
    "CapabilityProbe",
    "CloseScope",
    "Command",
    "CommandIdBinding",
    "CommandIdBindingRegistry",
    "CommandKind",
    "CommandObservation",
    "CommandOutcomeResolver",
    "CommandPipeStatus",
    "CompiledProto",
    "CompoundChild",
    "CompoundCommand",
    "ConnectionEndpoint",
    "ConnectionManager",
    "DecodedExecutionPrice",
    "DecodedTimestamp",
    "ErrorMap",
    "ErrorMapResolution",
    "ErrorMapRow",
    "EventRecorder",
    "FieldMarking",
    "Finding",
    "FindingsNote",
    "HealthReport",
    "InFlightResolution",
    "InboundVenueEvent",
    "JournalEvent",
    "MeasuredFact",
    "MultiRoomWrite",
    "MultiRoomWriteResult",
    "ObservationJournalEvent",
    "ObservationKind",
    "OrderParameters",
    "OrderState",
    "OrderStateProjection",
    "OrderType",
    "OutOfSequenceEdge",
    "PartialWriteRecovery",
    "PipeState",
    "ProbeCheck",
    "ProbeReport",
    "ProbeTransport",
    "ProbeVerdict",
    "ProtectionAmendment",
    "ProtectionSide",
    "ProtoArtifact",
    "RatePacer",
    "Reconciliation",
    "ReconciliationReadback",
    "ReconciliationVerdict",
    "RequestClass",
    "ResolveObservation",
    "ResolveResolution",
    "SchedulableDuty",
    "SessionDuty",
    "SessionRecovery",
    "SessionTopology",
    "SpotSample",
    "StandingIntentDecision",
    "StandingIntentDisposition",
    "StandingIntentJournalEvent",
    "StandingProtectionIntent",
    "StreamBlockCause",
    "SubjectResolution",
    "SubjectTerminalOutcome",
    "SubmissionOutcome",
    "SubmissionOutcomeClass",
    "SubmissionResult",
    "SymbolMetadataRecord",
    "TagChangeAssessment",
    "Tick",
    "TickHistorySample",
    "TimeInForce",
    "TimestampUnit",
    "TokenLifecycle",
    "TransactionBoundary",
    "Trendbar",
    "TrendbarSample",
    "UnknownBlock",
    "UnknownGate",
    "UnknownTrigger",
    "UpstreamAssumption",
    "VenueEnvironment",
    "VenueEvidenceClass",
    "VenueNativeIdentity",
    "VenueObservationProfile",
    "WriteRoom",
    "__version__",
    "assess_tag_change",
    "command_id_mapping_is_injective_total",
    "compile_descriptor_set",
    "decode_execution_price",
    "decode_framed_payload",
    "decode_market_data_price",
    "decode_money",
    "decode_timestamp",
    "derive_child_identity",
    "descriptor_set_digest",
    "detect_out_of_sequence",
    "encode_framed_payload",
    "fold_order_state",
    "is_legal_transition",
    "is_risk_reducing",
    "is_success",
    "journal_event_type",
    "meet_outcomes",
    "observation_journal_event_type",
    "order_for_shared_throttle",
    "resolve_subject_terminal",
    "throttle_priority",
    "tick_span_within_cap",
    "venue_command_stream",
    "venue_writer_id",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
