"""Story 8.7 tests — UNKNOWN blocks the command stream until explicit reconciliation.

Fixture-driven throughout: commands are built on qmf-core value types, the injected sinks
are canned in-memory fakes that contact no host and no filesystem, and a real
:class:`~qmf.venue.connection.ConnectionManager` (the WriterId holder) wires them, so every
persistence crosses an injected seam. These pin every acceptance criterion of Story 8.7
(FR-023, CT-19, SCN-0005; DEC-0137, DEC-0148, DEC-0150, DEC-0158):

* an UNKNOWN submission is minted as an explicit observation carrying its trigger, the
  monotonic elapsed measurement, the wall receive instant, and the injected submission
  deadline in force (mandatory existence, never QMF's value), and the block boundary
  requires those fields;
* while an UNKNOWN is outstanding the whole (VenueId, account) stream refuses new commands
  (transient venue failure, after-condition = resolution); the gate never clears its own
  block, retries, assumes an outcome, flattens, or invents a terminal state;
* a refused risk-reducing act never evaporates — it stands as a standing protection intent
  journaled before dispatch and re-decided (never retried) against a reconciled verdict
  only, while drift/unknown/out-of-lookback alarm and hold it open;
* the risk-reducing kinds dispatch ahead of place_order on every shared throttle, and
  suspend-new takes local effect instantly with no venue round-trip;
* resolve_unknown(command identity, resolution) carries one of observed-accepted |
  observed-absent | operator-attested, is itself recorded as an observation, and clears the
  block on that resolution — never on a reconciliation verdict alone.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Fingerprint,
    Instant,
    Instrument,
    Ok,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretValue,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.venue import (
    RISK_REDUCING_KINDS,
    AdmissionDisposition,
    Command,
    CommandKind,
    CommandObservation,
    CommandOutcomeResolver,
    CommandPipeStatus,
    ConnectionManager,
    JournalEvent,
    OrderParameters,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    Reconciliation,
    ReconciliationVerdict,
    ResolveObservation,
    ResolveResolution,
    StandingIntentDisposition,
    StandingProtectionIntent,
    StreamBlockCause,
    SubmissionOutcome,
    SubmissionResult,
    TimeInForce,
    UnknownBlock,
    UnknownGate,
    UnknownTrigger,
    is_risk_reducing,
    order_for_shared_throttle,
    throttle_priority,
    venue_writer_id,
)
from qmf.venue.capabilities import (
    CapabilityDeclaration,
    CapabilityField,
    CapabilityFieldName,
    ErrorMap,
    ErrorMapRow,
    ProtoArtifact,
    SubmissionOutcomeClass,
)

T = TypeVar("T")

_MACHINE = "vps-fra-01"
_ADAPTER_ROLE = "ctrader-adapter"
_BOOT = "boot-epoch-A"
_SESSION_EPOCH = "session-epoch-1"
_WALL_NS = 1_724_000_000 * 1_000_000_000
_DEADLINE_NS = _WALL_NS + 5_000_000_000
_ELAPSED_NS = 250_000_000
_PROTO_TAG = 91
_DIGEST = "sha256:" + "a" * 64


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


# --- qmf-core value fixtures -------------------------------------------------


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account(venue: VenueId | None = None) -> Account:
    anchor = venue if venue is not None else _venue()
    return _ok(Account.try_create("acct-001", anchor, AccountRole.DEMO))


def _other_account() -> Account:
    return _ok(Account.try_create("acct-999", _venue(), AccountRole.DEMO))


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return _ok(Instrument.try_create(_venue(), symbol))


def _instant(value_ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(value_ns))


def _duration(value_ns: int = _ELAPSED_NS) -> Duration:
    return _ok(Duration.try_create(value_ns))


def _price(value: int = 1_10000, scale: int = 5) -> Price:
    return _ok(Price.try_create(value, _instrument(), scale))


def _delta(value: int = 100, scale: int = 5) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), scale))


def _qty(value: int = 100, scale: int = 2) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


# --- command fixtures --------------------------------------------------------


def _order_params(order_type: OrderType = OrderType.MARKET) -> OrderParameters:
    return _ok(OrderParameters.try_create(order_type, TimeInForce.GOOD_TILL_CANCEL, _qty()))


def _place_order(ordinal: int = 1, account: Account | None = None) -> Command:
    return _ok(
        Command.place_order(
            _venue(),
            account if account is not None else _account(),
            _SESSION_EPOCH,
            ordinal,
            _order_params(),
        )
    )


def _cancel_order(ordinal: int = 2, subject: str = "order-abc") -> Command:
    return _ok(Command.cancel_order(_venue(), _account(), _SESSION_EPOCH, ordinal, subject))


def _close_position(ordinal: int = 3, subject: str = "pos-xyz") -> Command:
    return _ok(
        Command.close_position(
            _venue(), _account(), _SESSION_EPOCH, ordinal, "instrument-within-binding", subject
        )
    )


def _close_all(ordinal: int = 4, subject: str = "acct") -> Command:
    return _ok(Command.close_all(_venue(), _account(), _SESSION_EPOCH, ordinal, "account", subject))


def _stop_amendment() -> ProtectionAmendment:
    return _ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP, _delta(80), _price(), original_risk_distance=_delta(100)
        )
    )


def _amend(ordinal: int = 5, subject: str = "pos-xyz") -> Command:
    return _ok(
        Command.amend_protection(
            _venue(), _account(), _SESSION_EPOCH, ordinal, _stop_amendment(), subject
        )
    )


def _risk_reducing_command(kind: CommandKind, ordinal: int) -> Command:
    if kind is CommandKind.CANCEL_ORDER:
        return _cancel_order(ordinal)
    if kind is CommandKind.CLOSE_POSITION:
        return _close_position(ordinal)
    if kind is CommandKind.CLOSE_ALL:
        return _close_all(ordinal)
    return _amend(ordinal)


# --- canned injected seams ---------------------------------------------------


class FakeSecretStore:
    def __init__(self) -> None:
        self._values: dict[SecretRef, SecretValue] = {}

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:  # pragma: no cover - unused here
        if ref not in self._values:
            return unpersistable("no such credential")
        return Ok(self._values[ref])

    def atomic_replace(  # pragma: no cover - unused here
        self, ref: SecretRef, new_value: SecretValue, /
    ) -> Result[SecretRef]:
        self._values[ref] = new_value
        return Ok(ref)


class FakeObservationSink:
    def __init__(self) -> None:
        self.emitted: list[object] = []
        self.fail: bool = False

    def emit(self, observation: object, /) -> SinkResult:
        if self.fail:
            return unpersistable("observation store unavailable")
        self.emitted.append(observation)
        return Ok(SinkAck())


class FakeJournalSink:
    def __init__(self) -> None:
        self.appended: list[object] = []
        self.fail: bool = False

    def append(self, event: object, /) -> SinkResult:
        if self.fail:
            return unpersistable("journal store unavailable")
        self.appended.append(event)
        return Ok(SinkAck())


class FakeRecordSink:
    def __init__(self) -> None:
        self.written: list[object] = []
        self.fail: bool = False

    def write(self, record: object, /) -> SinkResult:  # pragma: no cover - unused here
        if self.fail:
            return unpersistable("registry store unavailable")
        self.written.append(record)
        return Ok(SinkAck())


class _Sinks:
    def __init__(self) -> None:
        self.store = FakeSecretStore()
        self.obs = FakeObservationSink()
        self.journal = FakeJournalSink()
        self.record = FakeRecordSink()


def _writer() -> object:
    return _ok(venue_writer_id(_MACHINE, _ADAPTER_ROLE, _venue(), _account(), _BOOT))


def _manager(sinks: _Sinks) -> ConnectionManager:
    return _ok(
        ConnectionManager.try_create(_writer(), sinks.store, sinks.obs, sinks.journal, sinks.record)
    )


def _gate(sinks: _Sinks | None = None) -> tuple[UnknownGate, _Sinks]:
    kit = sinks if sinks is not None else _Sinks()
    return _ok(UnknownGate.try_create(_manager(kit))), kit


# --- UNKNOWN submission-result fixtures --------------------------------------


def _observation(
    command: Command,
    *,
    trigger: UnknownTrigger | None = UnknownTrigger.TIMEOUT,
    elapsed: Duration | None = None,
    deadline: Instant | None = None,
) -> tuple[Fingerprint, CommandObservation]:
    fp = _ok(command.fingerprint())
    obs = CommandObservation(
        command_fp1=fp,
        kind=command.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        receive_instant=_instant(),
        unknown_trigger=trigger,
        monotonic_elapsed=elapsed if elapsed is not None else _duration(),
        submission_deadline=deadline if deadline is not None else _instant(_DEADLINE_NS),
        detail="lost transport certainty before a final outcome; UNKNOWN is a state",
    )
    return fp, obs


def _unknown_result(command: Command, **kwargs: object) -> SubmissionResult:
    fp, obs = _observation(command, **kwargs)  # type: ignore[arg-type]
    return SubmissionResult(
        command_fp1=fp,
        kind=command.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        observation=obs,
        journal_event=JournalEvent.for_outcome(fp, command.kind, SubmissionOutcome.UNKNOWN),
    )


# --- a representative cTrader-platform capability declaration ----------------


def _roster() -> list[CapabilityField]:
    def static(name: CapabilityFieldName, value: object) -> CapabilityField:
        return _ok(CapabilityField.static(name, value))

    def measured(name: CapabilityFieldName) -> CapabilityField:
        return _ok(CapabilityField.measured(name))

    return [
        static(CapabilityFieldName.MARKET_DATA_KINDS, ["tick"]),
        static(CapabilityFieldName.ORDER_PARAMETER_SUBSET, {"order_types": ["market"]}),
        static(CapabilityFieldName.COMMAND_SCOPES, ["account", "instrument-within-binding"]),
        static(CapabilityFieldName.ACKNOWLEDGEMENT_MODES, {"place_order": "explicit-event"}),
        measured(CapabilityFieldName.POSITION_MODEL),
        static(CapabilityFieldName.SESSION_TOPOLOGY, "two-connections"),
        static(CapabilityFieldName.THROTTLE_SCOPE, "connection"),
        static(CapabilityFieldName.RATE_LIMITS, {"non_historical_per_second": 50}),
        static(CapabilityFieldName.SPAN_CAPS_AND_PAGING, {"historical_span_cap_ms": 604_800_000}),
        static(CapabilityFieldName.TOKEN_LIFECYCLE_CLASS, {"access_token_days": 30}),
        static(CapabilityFieldName.EQUITY_NATIVENESS, "derived"),
        static(CapabilityFieldName.SERVER_CLOCK_AVAILABILITY, False),
        static(CapabilityFieldName.INSTRUMENT_METADATA_SURFACE, "full-symbol-record-required"),
        static(CapabilityFieldName.ATTRIBUTION_LABEL_SUPPORT, False),
        static(CapabilityFieldName.PROTECTION_PRIMITIVES, ["suspend-new", "drain", "close_all"]),
        measured(CapabilityFieldName.SETTLEMENT_CURRENCY),
        measured(CapabilityFieldName.MARGIN_SURFACE),
        measured(CapabilityFieldName.VALUE_FACTOR_METADATA),
        static(CapabilityFieldName.RECONCILIATION_LOOKBACK, "do-not-default"),
        measured(CapabilityFieldName.PROTECTION_CAPABILITIES),
        static(CapabilityFieldName.COMMAND_ID_MAPPING, {"injective_total": True}),
        static(CapabilityFieldName.FLOAT_TARGET_SCALES, {"execution_price": "declared-digits"}),
        static(CapabilityFieldName.VERIFICATION_SUITE, ["spot-timestamp-unit"]),
    ]


def _declaration() -> CapabilityDeclaration:
    artifact = _ok(ProtoArtifact.try_create("openapi-proto-messages", _PROTO_TAG, _DIGEST))
    row = _ok(
        ErrorMapRow.try_create(
            "ORDER_REJECTED",
            "place_order",
            RefusalCategory.POLICY_REJECTION,
            Retryability.NO,
            SubmissionOutcomeClass.REJECTED_BY_VENUE,
        )
    )
    error_map = _ok(ErrorMap.try_create(1, [row]))
    return _ok(
        CapabilityDeclaration.try_create("ctrader-adapter-1.0.0", artifact, error_map, _roster())
    )


def _resolver() -> CommandOutcomeResolver:
    return _ok(CommandOutcomeResolver.try_create(_declaration()))


def _reconciliation(verdict: ReconciliationVerdict) -> Reconciliation:
    return Reconciliation(verdict=verdict, detail=f"verdict={verdict.value}")


# =====================================================================================
# AC1 — an UNKNOWN is an explicit observation carrying its mandatory fields
# =====================================================================================


def test_transport_unknown_mints_observation_with_mandatory_fields() -> None:
    result = _ok(
        _resolver().transport_unknown(
            _place_order(),
            trigger=UnknownTrigger.TIMEOUT,
            monotonic_elapsed=_duration(),
            receive_instant=_instant(),
            submission_deadline=_instant(_DEADLINE_NS),
        )
    )
    assert result.outcome is SubmissionOutcome.UNKNOWN
    obs = result.observation
    assert obs.unknown_trigger is UnknownTrigger.TIMEOUT
    assert obs.monotonic_elapsed == _duration()
    assert obs.receive_instant == _instant()
    assert obs.submission_deadline == _instant(_DEADLINE_NS)


def test_transport_unknown_requires_the_injected_deadline() -> None:
    # The deadline's existence is mandatory though its value is never QMF's (do-not-default):
    # a missing deadline is refused, never defaulted.
    refusal = _refusal(
        _resolver().transport_unknown(
            _place_order(),
            trigger=UnknownTrigger.DISCONNECT,
            monotonic_elapsed=_duration(),
            receive_instant=_instant(),
            submission_deadline=None,
        )
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "submission_deadline"


def test_record_unknown_carries_the_mandatory_fields_onto_the_block() -> None:
    gate, _ = _gate()
    block = _ok(
        gate.record_unknown(_unknown_result(_place_order(), trigger=UnknownTrigger.DISCONNECT))
    )
    assert isinstance(block, UnknownBlock)
    assert block.trigger is UnknownTrigger.DISCONNECT
    assert block.monotonic_elapsed == _duration()
    assert block.receive_instant == _instant()
    assert block.submission_deadline == _instant(_DEADLINE_NS)
    assert block.after_condition == "resolution"


def test_record_unknown_refuses_a_non_unknown_result() -> None:
    gate, _ = _gate()
    command = _place_order()
    fp = _ok(command.fingerprint())
    accepted = SubmissionResult(
        command_fp1=fp,
        kind=command.kind,
        outcome=SubmissionOutcome.ACCEPTED_BY_VENUE,
        observation=CommandObservation(
            command_fp1=fp,
            kind=command.kind,
            outcome=SubmissionOutcome.ACCEPTED_BY_VENUE,
            receive_instant=_instant(),
        ),
        journal_event=JournalEvent.for_outcome(
            fp, command.kind, SubmissionOutcome.ACCEPTED_BY_VENUE
        ),
    )
    refusal = _refusal(gate.record_unknown(accepted))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert gate.stream_open is True


def test_record_unknown_refuses_a_non_submission_result() -> None:
    gate, _ = _gate()
    assert _refusal(gate.record_unknown("not-a-result")).category is RefusalCategory.INVALID_INPUT


def _unknown_result_with_observation(command: Command, obs: CommandObservation) -> SubmissionResult:
    fp = _ok(command.fingerprint())
    return SubmissionResult(
        command_fp1=fp,
        kind=command.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        observation=obs,
        journal_event=JournalEvent.for_outcome(fp, command.kind, SubmissionOutcome.UNKNOWN),
    )


def test_record_unknown_refuses_a_result_missing_a_mandatory_field() -> None:
    gate, _ = _gate()
    # a missing trigger.
    no_trigger = _unknown_result(_place_order(), trigger=None)
    assert _refusal(gate.record_unknown(no_trigger)).context["field"] == "submission_result"
    # a missing monotonic elapsed measurement.
    command = _cancel_order(9)
    fp = _ok(command.fingerprint())
    missing_elapsed = _unknown_result_with_observation(
        command,
        CommandObservation(
            command_fp1=fp,
            kind=command.kind,
            outcome=SubmissionOutcome.UNKNOWN,
            receive_instant=_instant(),
            unknown_trigger=UnknownTrigger.TIMEOUT,
            monotonic_elapsed=None,
            submission_deadline=_instant(_DEADLINE_NS),
        ),
    )
    assert _refusal(gate.record_unknown(missing_elapsed)).category is RefusalCategory.INVALID_INPUT
    # a missing submission deadline (its existence is mandatory, though its value is never QMF's).
    missing_deadline = _unknown_result_with_observation(
        command,
        CommandObservation(
            command_fp1=fp,
            kind=command.kind,
            outcome=SubmissionOutcome.UNKNOWN,
            receive_instant=_instant(),
            unknown_trigger=UnknownTrigger.TIMEOUT,
            monotonic_elapsed=_duration(),
            submission_deadline=None,
        ),
    )
    assert _refusal(gate.record_unknown(missing_deadline)).category is RefusalCategory.INVALID_INPUT


def test_record_unknown_is_idempotent_for_the_same_command() -> None:
    gate, _ = _gate()
    result = _unknown_result(_place_order())
    first = _ok(gate.record_unknown(result))
    second = _ok(gate.record_unknown(result))
    assert first is second
    assert gate.outstanding_count == 1


# =====================================================================================
# AC2 — an outstanding UNKNOWN blocks new commands on the stream
# =====================================================================================


def test_outstanding_unknown_refuses_a_new_command() -> None:
    gate, _ = _gate()
    _ok(gate.record_unknown(_unknown_result(_place_order())))
    assert gate.stream_open is False
    result = _ok(gate.admit(_place_order(7), receive_instant=_instant()))
    assert result.disposition is AdmissionDisposition.REFUSED
    assert result.block_cause is StreamBlockCause.OUTSTANDING_UNKNOWN
    assert result.standing_intent is None
    assert result.refusal is not None
    assert result.refusal.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert result.refusal.retryability is Retryability.AFTER_CONDITION
    assert result.refusal.after_condition_descriptor == "resolution"


def test_require_stream_open_surfaces_the_block_refusal() -> None:
    gate, _ = _gate()
    assert _ok(gate.require_stream_open()) is True
    _ok(gate.record_unknown(_unknown_result(_place_order())))
    refusal = _refusal(gate.require_stream_open())
    assert refusal.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert refusal.after_condition_descriptor == "resolution"


def test_admit_is_open_when_no_unknown_and_not_suspended() -> None:
    gate, _ = _gate()
    result = _ok(gate.admit(_place_order(), receive_instant=_instant()))
    assert result.admitted is True
    assert result.disposition is AdmissionDisposition.ADMITTED
    assert result.block_cause is None
    assert result.refusal is None


def test_admit_refuses_a_command_on_a_different_stream() -> None:
    gate, _ = _gate()
    foreign = _place_order(account=_other_account())
    refusal = _refusal(gate.admit(foreign, receive_instant=_instant()))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "command"


def test_admit_validates_its_arguments() -> None:
    gate, _ = _gate()
    assert _refusal(gate.admit("not-a-command", receive_instant=_instant())).context["field"] == (
        "command"
    )
    assert _refusal(gate.admit(_place_order(), receive_instant="nope")).context["field"] == (
        "receive_instant"
    )


# =====================================================================================
# AC3 — a refused protection act is preserved as a standing intent
# =====================================================================================


def test_each_risk_reducing_kind_is_held_as_a_standing_intent() -> None:
    for ordinal, kind in enumerate(sorted(RISK_REDUCING_KINDS, key=lambda k: k.value), start=20):
        gate, kit = _gate()
        _ok(gate.record_unknown(_unknown_result(_place_order())))
        command = _risk_reducing_command(kind, ordinal)
        result = _ok(gate.admit(command, receive_instant=_instant()))
        assert result.disposition is AdmissionDisposition.HELD_AS_STANDING_INTENT
        assert result.block_cause is StreamBlockCause.OUTSTANDING_UNKNOWN
        assert result.refusal is not None  # the act is still refused now
        intent = result.standing_intent
        assert isinstance(intent, StandingProtectionIntent)
        assert intent.kind is kind
        assert gate.standing_intents == (intent,)
        # journaled before dispatch: the held journal event landed on the injected sink.
        assert kit.journal.appended == [intent.journal_event]
        assert intent.journal_event.event_type.startswith("command.standing-protection-intent.held")


def test_a_held_intent_survives_the_journal_only_when_the_write_lands() -> None:
    gate, kit = _gate()
    _ok(gate.record_unknown(_unknown_result(_place_order())))
    kit.journal.fail = True
    refusal = _refusal(gate.admit(_close_position(), receive_instant=_instant()))
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    # the intent is not preserved until it is journaled (fail-closed).
    assert gate.standing_intents == ()


def test_standing_intent_dispatches_only_against_a_reconciled_verdict() -> None:
    gate, _ = _gate()
    _ok(gate.record_unknown(_unknown_result(_place_order())))
    held = _ok(gate.admit(_close_position(), receive_instant=_instant()))
    intent = held.standing_intent
    assert intent is not None
    # while the block still stands, the intent holds open — it never dispatches against a
    # blocked stream, even on a reconciled verdict.
    still_blocked = _ok(
        gate.redecide_standing_intent(intent, _reconciliation(ReconciliationVerdict.RECONCILED))
    )
    assert still_blocked.disposition is StandingIntentDisposition.HOLD_OPEN
    assert still_blocked.alarm is True
    # clear the block by an explicit resolution, then re-decide against reconciled → dispatch.
    _ok(
        gate.resolve_unknown(
            intent_block_fp(gate), ResolveResolution.OBSERVED_ABSENT, receive_instant=_instant()
        )
    )
    decision = _ok(
        gate.redecide_standing_intent(intent, _reconciliation(ReconciliationVerdict.RECONCILED))
    )
    assert decision.disposition is StandingIntentDisposition.DISPATCH
    assert decision.dispatches is True
    assert decision.alarm is False
    # re-decided to dispatch → dropped from the standing set (a fresh act, never a retry).
    assert gate.standing_intents == ()


def intent_block_fp(gate: UnknownGate) -> Fingerprint:
    """The fp1 of the single outstanding UNKNOWN block on the gate (test helper)."""
    outstanding = gate.outstanding
    assert len(outstanding) == 1
    return outstanding[0].command_fp1


def test_standing_intent_holds_open_and_alarms_on_non_reconciled_verdicts() -> None:
    for verdict in (
        ReconciliationVerdict.DRIFT,
        ReconciliationVerdict.UNKNOWN,
        ReconciliationVerdict.OUT_OF_LOOKBACK,
    ):
        gate, _ = _gate()
        _ok(gate.record_unknown(_unknown_result(_place_order())))
        held = _ok(gate.admit(_amend(), receive_instant=_instant()))
        intent = held.standing_intent
        assert intent is not None
        _ok(
            gate.resolve_unknown(
                intent_block_fp(gate),
                ResolveResolution.OPERATOR_ATTESTED,
                receive_instant=_instant(),
            )
        )
        decision = _ok(gate.redecide_standing_intent(intent, _reconciliation(verdict)))
        assert decision.disposition is StandingIntentDisposition.HOLD_OPEN
        assert decision.alarm is True
        assert decision.verdict is verdict
        # holds open → the intent stays standing (never opens against state it cannot see).
        assert gate.standing_intents == (intent,)


def test_redecide_validates_its_arguments() -> None:
    gate, _ = _gate()
    _ok(gate.record_unknown(_unknown_result(_place_order())))
    held = _ok(gate.admit(_close_all(), receive_instant=_instant()))
    intent = held.standing_intent
    assert intent is not None
    assert (
        _refusal(
            gate.redecide_standing_intent("nope", _reconciliation(ReconciliationVerdict.RECONCILED))
        ).context["field"]
        == "intent"
    )
    assert _refusal(gate.redecide_standing_intent(intent, "nope")).context["field"] == (
        "reconciliation"
    )


def test_redecide_refuses_an_intent_not_held_here() -> None:
    gate, _ = _gate()
    other_gate, _ = _gate()
    _ok(other_gate.record_unknown(_unknown_result(_place_order())))
    held = _ok(other_gate.admit(_close_position(), receive_instant=_instant()))
    intent = held.standing_intent
    assert intent is not None
    # a fresh gate holds no intents, so re-deciding a foreign intent is refused.
    refusal = _refusal(
        gate.redecide_standing_intent(intent, _reconciliation(ReconciliationVerdict.RECONCILED))
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "intent"


# =====================================================================================
# AC4 — throttle ordering and the local, instant suspend-new
# =====================================================================================


def test_risk_reducing_kinds_dispatch_ahead_of_place_order_on_a_shared_throttle() -> None:
    pending = [_place_order(1), _cancel_order(2), _place_order(3), _close_all(4)]
    ordered = _ok(order_for_shared_throttle(pending))
    assert [command.ordering_ordinal for command in ordered] == [2, 4, 1, 3]


def test_shared_throttle_ordering_edges() -> None:
    assert _ok(order_for_shared_throttle([])) == ()
    assert _refusal(order_for_shared_throttle("nope")).context["field"] == "commands"
    assert _refusal(order_for_shared_throttle([_place_order(), "x"])).context["field"] == "commands"


def test_is_risk_reducing_and_throttle_priority_classify_every_kind() -> None:
    assert is_risk_reducing(CommandKind.CANCEL_ORDER) is True
    assert is_risk_reducing(CommandKind.CLOSE_POSITION) is True
    assert is_risk_reducing(CommandKind.CLOSE_ALL) is True
    assert is_risk_reducing(CommandKind.AMEND_PROTECTION) is True
    assert is_risk_reducing(CommandKind.PLACE_ORDER) is False
    assert is_risk_reducing("place_order") is False
    assert throttle_priority(CommandKind.CANCEL_ORDER) == 0
    assert throttle_priority(CommandKind.PLACE_ORDER) == 1
    assert throttle_priority("not-a-kind") == 1


def test_suspend_new_takes_local_effect_instantly_with_no_venue_round_trip() -> None:
    gate, kit = _gate()
    assert gate.is_new_suspended is False
    assert _ok(gate.suspend_new()) is True
    assert gate.is_new_suspended is True
    # local, instant: no venue call, no sink write.
    assert kit.obs.emitted == []
    assert kit.journal.appended == []
    assert kit.record.written == []
    # a new place_order is refused while suspend-new is in effect...
    refused = _ok(gate.admit(_place_order(), receive_instant=_instant()))
    assert refused.disposition is AdmissionDisposition.REFUSED
    assert refused.block_cause is StreamBlockCause.SUSPEND_NEW
    assert refused.refusal is not None
    assert refused.refusal.after_condition_descriptor == "suspend-new lifted"
    # ...but a risk-reducing command still dispatches.
    admitted = _ok(gate.admit(_close_position(), receive_instant=_instant()))
    assert admitted.admitted is True
    # resume lifts it locally.
    assert _ok(gate.resume_new()) is True
    assert gate.is_new_suspended is False
    assert _ok(gate.admit(_place_order(), receive_instant=_instant())).admitted is True


# =====================================================================================
# AC5 — resolve_unknown is explicit, recorded, and the only thing that clears the block
# =====================================================================================


def test_resolve_unknown_records_an_observation_and_clears_the_block() -> None:
    for resolution in ResolveResolution:
        gate, kit = _gate()
        block = _ok(gate.record_unknown(_unknown_result(_place_order())))
        observation = _ok(
            gate.resolve_unknown(block.command_fp1, resolution, receive_instant=_instant())
        )
        assert isinstance(observation, ResolveObservation)
        assert observation.resolution is resolution
        assert observation.command_fp1 == block.command_fp1
        # the resolve call is itself recorded as an observation on the injected sink.
        assert kit.obs.emitted == [observation]
        # the block clears on that resolution.
        assert gate.stream_open is True
        assert gate.outstanding_count == 0


def test_resolve_unknown_accepts_the_string_forms_of_the_resolution() -> None:
    gate, _ = _gate()
    block = _ok(gate.record_unknown(_unknown_result(_place_order())))
    observation = _ok(
        gate.resolve_unknown(block.command_fp1, "observed-accepted", receive_instant=_instant())
    )
    assert observation.resolution is ResolveResolution.OBSERVED_ACCEPTED


def test_resolve_unknown_validates_its_arguments() -> None:
    gate, _ = _gate()
    block = _ok(gate.record_unknown(_unknown_result(_place_order())))
    assert (
        _refusal(
            gate.resolve_unknown(
                "not-a-fp", ResolveResolution.OBSERVED_ABSENT, receive_instant=_instant()
            )
        ).context["field"]
        == "command_fp1"
    )
    assert (
        _refusal(
            gate.resolve_unknown(block.command_fp1, "bogus", receive_instant=_instant())
        ).context["field"]
        == "resolution"
    )
    # a non-string, non-enum resolution is refused too (never coerced).
    assert (
        _refusal(gate.resolve_unknown(block.command_fp1, 123, receive_instant=_instant())).context[
            "field"
        ]
        == "resolution"
    )
    assert (
        _refusal(
            gate.resolve_unknown(
                block.command_fp1, ResolveResolution.OBSERVED_ABSENT, receive_instant="x"
            )
        ).context["field"]
        == "receive_instant"
    )


def test_resolve_unknown_refuses_an_unrecognized_identity() -> None:
    gate, _ = _gate()
    _ok(gate.record_unknown(_unknown_result(_place_order())))
    stranger = _ok(_cancel_order(88).fingerprint())
    refusal = _refusal(
        gate.resolve_unknown(
            stranger, ResolveResolution.OBSERVED_ABSENT, receive_instant=_instant()
        )
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "command_fp1"
    # the block was not cleared by a failed resolve.
    assert gate.stream_open is False


def test_resolve_unknown_keeps_the_block_when_recording_fails() -> None:
    gate, kit = _gate()
    block = _ok(gate.record_unknown(_unknown_result(_place_order())))
    kit.obs.fail = True
    refusal = _refusal(
        gate.resolve_unknown(
            block.command_fp1, ResolveResolution.OBSERVED_ACCEPTED, receive_instant=_instant()
        )
    )
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    # fail-closed: the resolution must be recorded before the block clears.
    assert gate.stream_open is False
    assert gate.outstanding_count == 1


def test_multiple_outstanding_unknowns_each_clear_independently() -> None:
    gate, _ = _gate()
    first = _ok(gate.record_unknown(_unknown_result(_place_order(1))))
    second = _ok(gate.record_unknown(_unknown_result(_cancel_order(2))))
    assert gate.outstanding_count == 2
    _ok(
        gate.resolve_unknown(
            first.command_fp1, ResolveResolution.OBSERVED_ABSENT, receive_instant=_instant()
        )
    )
    # one still outstanding → the stream stays blocked.
    assert gate.stream_open is False
    _ok(
        gate.resolve_unknown(
            second.command_fp1, ResolveResolution.OBSERVED_ABSENT, receive_instant=_instant()
        )
    )
    assert gate.stream_open is True


# =====================================================================================
# construction and wiring
# =====================================================================================


def test_try_create_requires_a_connection_manager() -> None:
    refusal = _refusal(UnknownGate.try_create("not-a-manager"))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "connection_manager"


def test_gate_reports_its_stream_and_repr() -> None:
    gate, kit = _gate()
    # the stream token is the deterministic (VenueId, account) join the WriterId carries.
    assert gate.stream == "venue-ctrader-demo::acct-001"
    assert "UnknownGate(" in repr(gate)
    # the connection manager's own command pipe is a separate gate, unaffected here.
    assert _manager(kit).health().command_pipe is CommandPipeStatus.OPEN
