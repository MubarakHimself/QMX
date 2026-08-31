"""Story 24.6 — UNKNOWN at the exact (VenueId, account) command-stream boundary."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Instant,
    Ok,
    RefusalCategory,
    Result,
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
from qmn.order import (
    OPERATOR_PRINCIPAL,
    UNDELIVERABLE_ALARM_CLASS,
    CommandStreamUnknownBoundary,
    HoldDisposition,
    ProtectionIntentExtent,
    ReadbackClarity,
    ResolvePath,
    UnknownStreamRegistry,
    decide_resolve_path,
    unknown_never_rejection,
)
from qmn.venue import (
    AdmissionDisposition,
    Command,
    CommandObservation,
    ConnectionManager,
    JournalEvent,
    OrderParameters,
    OrderType,
    Reconciliation,
    ReconciliationVerdict,
    ResolveResolution,
    StandingIntentDisposition,
    StreamBlockCause,
    SubmissionOutcome,
    SubmissionResult,
    TimeInForce,
    UnknownTrigger,
    venue_command_stream,
    venue_writer_id,
)

T = TypeVar("T")

_BOOT = "boot-epoch-unknown-24-6"
_SESSION = "session-epoch-24-6"
_MACHINE = "vps-fra-01"
_ADAPTER = "ctrader-adapter"
_WALL_NS = 1_725_200_000 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue(value: str = "conformance:unknown-24-6") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(account_id: str, venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create(account_id, venue or _venue(), AccountRole.DEMO))


def _instant(ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int = 2_000_000_000) -> Duration:
    return _ok(Duration.try_create(ns))


class _SecretStore:
    def __init__(self) -> None:
        self._values: dict[SecretRef, SecretValue] = {}

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        if ref not in self._values:
            return unpersistable("no such credential")
        return Ok(self._values[ref])

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue, /) -> Result[SecretRef]:
        self._values[ref] = new_value
        return Ok(ref)


class _ObsSink:
    def __init__(self) -> None:
        self.emitted: list[object] = []
        self.fail = False

    def emit(self, observation: object, /) -> SinkResult:
        if self.fail:
            return unpersistable("observation store unavailable")
        self.emitted.append(observation)
        return Ok(SinkAck())


class _JournalSink:
    def __init__(self) -> None:
        self.appended: list[object] = []
        self.fail = False

    def append(self, event: object, /) -> SinkResult:
        if self.fail:
            return unpersistable("journal store unavailable")
        self.appended.append(event)
        return Ok(SinkAck())


class _RecordSink:
    def __init__(self) -> None:
        self.written: list[object] = []
        self.fail = False

    def write(self, record: object, /) -> SinkResult:
        if self.fail:
            return unpersistable("record store unavailable")
        self.written.append(record)
        return Ok(SinkAck())


def _manager(
    venue: VenueId,
    account: Account,
    *,
    journal: _JournalSink | None = None,
    obs: _ObsSink | None = None,
) -> tuple[ConnectionManager, _JournalSink, _ObsSink]:
    writer = _ok(venue_writer_id(_MACHINE, _ADAPTER, venue, account, _BOOT))
    jnl = journal if journal is not None else _JournalSink()
    observations = obs if obs is not None else _ObsSink()
    cm = _ok(
        ConnectionManager.try_create(
            writer, _SecretStore(), observations, jnl, _RecordSink()
        )
    )
    return cm, jnl, observations


def _extent(capacity: int = 8) -> ProtectionIntentExtent:
    return _ok(ProtectionIntentExtent.try_create(capacity))


def _boundary(
    venue: VenueId | None = None,
    account: Account | None = None,
    *,
    journal: _JournalSink | None = None,
    extent: ProtectionIntentExtent | None = None,
) -> tuple[CommandStreamUnknownBoundary, ConnectionManager, _JournalSink, _ObsSink]:
    v = venue or _venue()
    a = account or _account("acct-a", v)
    cm, jnl, obs = _manager(v, a, journal=journal)
    boundary = _ok(
        CommandStreamUnknownBoundary.try_create(
            venue_id=v,
            account=a,
            connection_manager=cm,
            extent=extent or _extent(),
        )
    )
    return boundary, cm, jnl, obs


def _params() -> OrderParameters:
    from qmf.core import Instrument, PriceDelta, Quantity

    venue = _venue()
    instrument = _ok(Instrument.try_create(venue, "EURUSD"))
    qty = _ok(Quantity.try_create(100, "lot", 2))
    delta = _ok(PriceDelta.try_create(100, instrument, 5))
    return _ok(
        OrderParameters.try_create(
            OrderType.MARKET,
            TimeInForce.GOOD_TILL_CANCEL,
            qty,
            protective_stop_distance=delta,
        )
    )


def _place(venue: VenueId, account: Account, ordinal: int = 1) -> Command:
    return _ok(Command.place_order(venue, account, _SESSION, ordinal, _params()))


def _cancel(venue: VenueId, account: Account, ordinal: int = 2) -> Command:
    return _ok(Command.cancel_order(venue, account, _SESSION, ordinal, "ord-1"))


def _close(venue: VenueId, account: Account, ordinal: int = 3) -> Command:
    return _ok(
        Command.close_position(
            venue,
            account,
            _SESSION,
            ordinal,
            "instrument-within-binding",
            "pos-1",
        )
    )


def _unknown_result(
    command: Command,
    *,
    trigger: UnknownTrigger = UnknownTrigger.TIMEOUT,
) -> SubmissionResult:
    fp = _ok(command.fingerprint())
    obs = CommandObservation(
        command_fp1=fp,
        kind=command.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        receive_instant=_instant(),
        unknown_trigger=trigger,
        monotonic_elapsed=_duration(750_000_000),
        submission_deadline=_instant(_WALL_NS + 5_000_000_000),
        detail="lost transport certainty; UNKNOWN is a state",
    )
    return SubmissionResult(
        command_fp1=fp,
        kind=command.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        observation=obs,
        journal_event=JournalEvent.for_outcome(fp, command.kind, SubmissionOutcome.UNKNOWN),
    )


def test_unknown_is_state_never_rejection_for_all_triggers() -> None:
    venue = _venue()
    account = _account("acct-a", venue)
    boundary, _, _, _ = _boundary(venue, account)
    for trigger in (
        UnknownTrigger.TIMEOUT,
        UnknownTrigger.TRANSPORT_ERROR,
        UnknownTrigger.DISCONNECT,
    ):
        cmd = _place(venue, account, ordinal=10 + list(UnknownTrigger).index(trigger))
        unknown = _unknown_result(cmd, trigger=trigger)
        assert unknown_never_rejection(unknown.outcome)
        assert unknown.outcome is not SubmissionOutcome.REJECTED_BY_VENUE
        block = _ok(boundary.record_unknown(unknown))
        assert block.trigger is trigger
    assert boundary.stream_open is False
    assert boundary.sensing_continues is True


def test_qmx_f062_two_accounts_on_one_connection_are_independent() -> None:
    """QMX-F062: stream is strictly finer than a connection — A blocked, B open."""
    venue = _venue()
    acct_a = _account("acct-a", venue)
    acct_b = _account("acct-b", venue)
    # Shared secret store / observation sink simulates one logical connection.
    shared_obs = _ObsSink()
    shared_store = _SecretStore()
    writer_a = _ok(venue_writer_id(_MACHINE, _ADAPTER, venue, acct_a, _BOOT))
    writer_b = _ok(venue_writer_id(_MACHINE, _ADAPTER, venue, acct_b, _BOOT))
    cm_a = _ok(
        ConnectionManager.try_create(
            writer_a, shared_store, shared_obs, _JournalSink(), _RecordSink()
        )
    )
    cm_b = _ok(
        ConnectionManager.try_create(
            writer_b, shared_store, shared_obs, _JournalSink(), _RecordSink()
        )
    )
    boundary_a = _ok(
        CommandStreamUnknownBoundary.try_create(
            venue_id=venue, account=acct_a, connection_manager=cm_a, extent=_extent()
        )
    )
    boundary_b = _ok(
        CommandStreamUnknownBoundary.try_create(
            venue_id=venue, account=acct_b, connection_manager=cm_b, extent=_extent()
        )
    )
    registry = UnknownStreamRegistry()
    _ok(registry.register(boundary_a))
    _ok(registry.register(boundary_b))
    assert _ok(registry.is_independent(boundary_a, boundary_b)) is True
    assert boundary_a.stream != boundary_b.stream
    assert venue_command_stream(venue, acct_a) == boundary_a.stream

    _ok(boundary_a.record_unknown(_unknown_result(_place(venue, acct_a))))
    assert boundary_a.stream_open is False
    assert boundary_b.stream_open is True

    # Protection on A is held; place on A refused; B still admits.
    held = _ok(boundary_a.admit(_cancel(venue, acct_a), receive_instant=_instant()))
    assert isinstance(held, object)
    from qmn.order import HeldProtectionAct

    assert isinstance(held, HeldProtectionAct)
    assert held.disposition is HoldDisposition.HELD

    refused = _ok(boundary_a.admit(_place(venue, acct_a, ordinal=9), receive_instant=_instant()))
    from qmn.venue import AdmissionResult

    assert isinstance(refused, AdmissionResult)
    assert refused.disposition is AdmissionDisposition.REFUSED
    assert refused.block_cause is StreamBlockCause.OUTSTANDING_UNKNOWN
    assert refused.refusal is not None
    assert refused.refusal.category is RefusalCategory.TRANSIENT_VENUE_FAILURE

    open_b = _ok(boundary_b.admit(_place(venue, acct_b), receive_instant=_instant()))
    assert isinstance(open_b, AdmissionResult)
    assert open_b.disposition is AdmissionDisposition.ADMITTED
    assert boundary_b.sensing_continues is True
    assert is_ok(cm_a.emit_sensing_observation({"tick": "EURUSD"}))


def test_qmx_f062_two_bindings_on_one_account_share_the_block() -> None:
    """QMX-F062: stream is coarser than an account binding — both bindings blocked."""
    venue = _venue()
    account = _account("acct-shared", venue)
    boundary, _, _, _ = _boundary(venue, account)
    _ok(boundary.record_unknown(_unknown_result(_place(venue, account))))

    # Two logical bindings on the same account share one (VenueId, account) stream.
    binding_one_cmd = _cancel(venue, account, ordinal=2)
    binding_two_cmd = _close(venue, account, ordinal=3)
    assert venue_command_stream(venue, account) == boundary.stream
    held_one = _ok(boundary.admit(binding_one_cmd, receive_instant=_instant()))
    held_two = _ok(boundary.admit(binding_two_cmd, receive_instant=_instant(ns=_WALL_NS + 1)))
    from qmn.order import HeldProtectionAct

    assert isinstance(held_one, HeldProtectionAct)
    assert isinstance(held_two, HeldProtectionAct)
    place = _ok(boundary.admit(_place(venue, account, ordinal=4), receive_instant=_instant()))
    from qmn.venue import AdmissionResult

    assert isinstance(place, AdmissionResult)
    assert place.disposition is AdmissionDisposition.REFUSED


def test_standing_intent_held_not_refused_retried_or_dropped() -> None:
    venue = _venue()
    account = _account("acct-a", venue)
    boundary, _, jnl, _ = _boundary(venue, account)
    unknown_cmd = _place(venue, account)
    block = _ok(boundary.record_unknown(_unknown_result(unknown_cmd)))
    assert block.command_fp1 == _ok(unknown_cmd.fingerprint())

    held = _ok(boundary.admit(_cancel(venue, account), receive_instant=_instant()))
    from qmn.order import HeldProtectionAct

    assert isinstance(held, HeldProtectionAct)
    assert held.disposition is HoldDisposition.HELD
    assert held.intent is not None
    assert "never refused" in held.detail or "re-decided" in held.detail
    assert any("standing-protection-intent" in str(event) for event in jnl.appended)
    assert len(boundary.standing_intents) == 1

    # Re-decide while blocked: HOLD_OPEN even on reconciled.
    decision = _ok(
        boundary.redecide_standing_intent(
            held.intent,
            Reconciliation(verdict=ReconciliationVerdict.RECONCILED, detail="ok"),
        )
    )
    assert decision.disposition is StandingIntentDisposition.HOLD_OPEN
    assert decision.alarm is True

    # Clear only via explicit resolve, then re-decide dispatches (never a retry).
    _ok(
        boundary.resolve_by_operator_attestation(
            block.command_fp1,
            principal=OPERATOR_PRINCIPAL,
            receive_instant=_instant(_WALL_NS + 10),
            readback_detail={"orders": [], "fills": [], "positions": []},
        )
    )
    assert boundary.stream_open is True
    dispatched = _ok(
        boundary.redecide_standing_intent(
            held.intent,
            Reconciliation(verdict=ReconciliationVerdict.RECONCILED, detail="flat"),
        )
    )
    assert dispatched.disposition is StandingIntentDisposition.DISPATCH
    assert dispatched.alarm is False
    assert boundary.standing_intents == ()


def test_journal_failure_uses_reserved_extent_or_undeliverable() -> None:
    venue = _venue()
    account = _account("acct-a", venue)
    failing = _JournalSink()
    failing.fail = True
    extent = _extent(capacity=1)
    boundary, _, _, _ = _boundary(venue, account, journal=failing, extent=extent)
    _ok(boundary.record_unknown(_unknown_result(_place(venue, account))))

    held = _ok(boundary.admit(_cancel(venue, account), receive_instant=_instant()))
    from qmn.order import HeldProtectionAct

    assert isinstance(held, HeldProtectionAct)
    assert held.disposition is HoldDisposition.HELD
    assert held.journaled_to_extent is True
    assert extent.used == 1
    assert len(boundary.extent_held) == 1

    # Exhaust the extent — next hold is UNDELIVERABLE + alarm.
    undelivered = _ok(
        boundary.admit(_close(venue, account), receive_instant=_instant(_WALL_NS + 2))
    )
    assert isinstance(undelivered, HeldProtectionAct)
    assert undelivered.disposition is HoldDisposition.UNDELIVERABLE
    assert undelivered.undeliverable is not None
    assert undelivered.undeliverable.alarm_class == UNDELIVERABLE_ALARM_CLASS
    assert len(boundary.alarms) == 1
    assert boundary.alarms[0]["alarm_class"] == UNDELIVERABLE_ALARM_CLASS


def test_resolve_path_auto_only_on_unambiguous_reconciled_inside_lookback() -> None:
    reconciled = Reconciliation(
        verdict=ReconciliationVerdict.RECONCILED, detail="agree"
    )
    auto = _ok(
        decide_resolve_path(
            reconciled,
            clarity=ReadbackClarity.OBSERVED_ACCEPTED,
            covers_lookback=True,
        )
    )
    assert auto.path is ResolvePath.AUTO
    assert auto.auto_resolution is ResolveResolution.OBSERVED_ACCEPTED
    assert auto.may_auto_resolve is True

    absent = _ok(
        decide_resolve_path(
            reconciled,
            clarity=ReadbackClarity.OBSERVED_ABSENT,
            covers_lookback=True,
        )
    )
    assert absent.auto_resolution is ResolveResolution.OBSERVED_ABSENT

    for verdict in (
        ReconciliationVerdict.DRIFT,
        ReconciliationVerdict.UNKNOWN,
        ReconciliationVerdict.OUT_OF_LOOKBACK,
    ):
        decision = _ok(
            decide_resolve_path(
                Reconciliation(verdict=verdict, detail=verdict.value),
                clarity=ReadbackClarity.OBSERVED_ACCEPTED,
                covers_lookback=True,
            )
        )
        assert decision.path is ResolvePath.OPERATOR_ATTESTATION
        assert decision.may_auto_resolve is False
        assert "never auto-resolves" in decision.detail

    ambiguous = _ok(
        decide_resolve_path(
            reconciled,
            clarity=ReadbackClarity.AMBIGUOUS,
            covers_lookback=True,
        )
    )
    assert ambiguous.path is ResolvePath.OPERATOR_ATTESTATION

    out_of_window = _ok(
        decide_resolve_path(
            reconciled,
            clarity=ReadbackClarity.OBSERVED_ACCEPTED,
            covers_lookback=False,
        )
    )
    assert out_of_window.path is ResolvePath.OPERATOR_ATTESTATION


def test_auto_and_operator_resolve_enforce_two_path_precedence() -> None:
    venue = _venue()
    account = _account("acct-a", venue)
    boundary, _, _, obs = _boundary(venue, account)
    cmd = _place(venue, account)
    block = _ok(boundary.record_unknown(_unknown_result(cmd)))

    hold_decision = _ok(
        decide_resolve_path(
            Reconciliation(
                verdict=ReconciliationVerdict.DRIFT, detail="disagree"
            ),
            clarity=ReadbackClarity.OBSERVED_ACCEPTED,
            covers_lookback=True,
        )
    )
    refused_auto = _refusal(
        boundary.resolve_auto(
            block.command_fp1, hold_decision, receive_instant=_instant()
        )
    )
    assert refused_auto.category is RefusalCategory.POLICY_REJECTION
    assert boundary.stream_open is False

    # Machine / ops principal cannot attest.
    refused_ops = _refusal(
        boundary.resolve_by_operator_attestation(
            block.command_fp1,
            principal="ops",
            receive_instant=_instant(),
            readback_detail={"orders": []},
        )
    )
    assert refused_ops.category is RefusalCategory.POLICY_REJECTION

    auto_decision = _ok(
        decide_resolve_path(
            Reconciliation(
                verdict=ReconciliationVerdict.RECONCILED, detail="agree"
            ),
            clarity=ReadbackClarity.OBSERVED_ABSENT,
            covers_lookback=True,
        )
    )
    cleared = _ok(
        boundary.resolve_auto(
            block.command_fp1, auto_decision, receive_instant=_instant(_WALL_NS + 5)
        )
    )
    assert cleared.resolution is ResolveResolution.OBSERVED_ABSENT
    assert boundary.stream_open is True
    assert any(
        getattr(item, "resolution", None) is ResolveResolution.OBSERVED_ABSENT
        for item in obs.emitted
    )


def test_writer_stream_must_match_venue_account_pair() -> None:
    venue = _venue()
    acct_a = _account("acct-a", venue)
    acct_b = _account("acct-b", venue)
    cm, _, _ = _manager(venue, acct_b)
    refusal = _refusal(
        CommandStreamUnknownBoundary.try_create(
            venue_id=venue,
            account=acct_a,
            connection_manager=cm,
            extent=_extent(),
        )
    )
    assert refusal.context["field"] == "connection_manager"
    assert "QMX-F062" in str(refusal.context["reason"])
