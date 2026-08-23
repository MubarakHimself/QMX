"""Story 8.6 tests — record-before-interpret events and on-demand reconciliation (CT-20).

Fixture-driven throughout: inbound observations are built on qmf-core value types, the
three injected sinks are canned in-memory fakes that contact no host and no filesystem,
and a real :class:`~qmf.venue.connection.ConnectionManager` (the WriterId holder) wires
them, so every persistence crosses an injected seam. These pin every acceptance criterion
(FR-024, CT-20, AR-47, SCN-0005; DEC-0137, DEC-0138, DEC-0140, DEC-0148, DEC-0158):

* every inbound event is stored verbatim — with the mandatory receive wall time and
  boot-scoped monotonic stamp — and journaled before any state evaluation, and a fill's
  price, quantity, venue instant, and receive instant are mandatory identity fields;
* order state is a read-time fold over the observation stream, never a stored field;
  command outcome and order state are separate streams, and a terminal state is decided
  only by fills and venue lifecycle events, never from a command outcome or absence alone;
* an observation with no legal transition is annotated with a typed out-of-sequence edge
  and forces its owning command to UNKNOWN, and no observation is ever synthesized;
* a multi-room write completes as one ordered unit with a named transaction boundary, and
  a partial write is a storage-failure refusal that blocks the command stream (the sensing
  pipe unaffected) and is journaled on recovery;
* reconciliation is an on-demand read-back over a mandatory declared lookback whose verdict
  is one of reconciled | drift | unknown | out-of-lookback, gating the command pipe only;
* a close/amend whose subject is observed terminal at or after the submit stamp resolves
  rejected-by-venue (superseded-by-terminal-subject), never UNKNOWN, and an absent or
  already-terminal subject resolves without submission.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Instant,
    Instrument,
    MonotonicReading,
    Ok,
    Price,
    Quantity,
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
from qmf.venue import (
    Command,
    CommandKind,
    ConnectionManager,
    EventRecorder,
    InboundVenueEvent,
    MultiRoomWrite,
    MultiRoomWriteResult,
    ObservationJournalEvent,
    ObservationKind,
    OrderParameters,
    OrderState,
    OrderType,
    OutOfSequenceEdge,
    PartialWriteRecovery,
    Reconciliation,
    ReconciliationReadback,
    ReconciliationVerdict,
    SubjectResolution,
    SubmissionOutcome,
    TimeInForce,
    TransactionBoundary,
    VenueNativeIdentity,
    WriteRoom,
    detect_out_of_sequence,
    fold_order_state,
    is_legal_transition,
    observation_journal_event_type,
    resolve_subject_terminal,
    venue_writer_id,
)

T = TypeVar("T")

_MACHINE = "vps-fra-01"
_ADAPTER_ROLE = "ctrader-adapter"
_BOOT = "boot-epoch-A"
_SESSION_EPOCH = "session-epoch-1"
_CRED_REF_ID = "venue-demo-cred-ref-0001"
_WALL_NS = 1_724_000_000 * 1_000_000_000
_LOOKBACK_NS = 7 * 24 * 60 * 60 * 1_000_000_000  # a one-week span, per the ratified span cap


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


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return _ok(Instrument.try_create(_venue(), symbol))


def _instant(value_ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(value_ns))


def _monotonic(value_ns: int = 5_000_000_000) -> MonotonicReading:
    return _ok(MonotonicReading.try_create(value_ns, _BOOT))


def _price(value: int = 1_10000, scale: int = 5) -> Price:
    return _ok(Price.try_create(value, _instrument(), scale))


def _qty(value: int = 100, scale: int = 2) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


def _identity(native_id: str = "fill-0001", revision: int = 0) -> VenueNativeIdentity:
    return _ok(VenueNativeIdentity.try_create("ctrader", native_id, revision))


# --- observation fixtures ----------------------------------------------------


def _event(
    kind: ObservationKind = ObservationKind.SUBMISSION_ACKNOWLEDGEMENT,
    *,
    native_id: str = "obs-0001",
    revision: int = 0,
    subject: str | None = None,
    venue_instant: Instant | None = None,
    fill_price: Price | None = None,
    fill_quantity: Quantity | None = None,
    receive_ns: int = _WALL_NS,
) -> InboundVenueEvent:
    return _ok(
        InboundVenueEvent.try_create(
            kind,
            _identity(native_id, revision),
            _instant(receive_ns),
            _monotonic(),
            _SESSION_EPOCH,
            {"wire": "verbatim-payload", "seq": revision},
            fill_price=fill_price,
            fill_quantity=fill_quantity,
            venue_instant=venue_instant,
            subject_native_id=subject,
        )
    )


def _fill(
    *,
    native_id: str = "fill-0001",
    quantity: Quantity | None = None,
    subject: str | None = None,
    venue_ns: int = _WALL_NS,
) -> InboundVenueEvent:
    return _ok(
        InboundVenueEvent.try_create(
            ObservationKind.FILL,
            _identity(native_id),
            _instant(),
            _monotonic(),
            _SESSION_EPOCH,
            {"wire": "fill"},
            fill_price=_price(),
            fill_quantity=quantity if quantity is not None else _qty(),
            venue_instant=_instant(venue_ns),
            subject_native_id=subject,
        )
    )


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

    def write(self, record: object, /) -> SinkResult:
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


def _recorder(sinks: _Sinks | None = None) -> tuple[EventRecorder, _Sinks]:
    kit = sinks if sinks is not None else _Sinks()
    return _ok(EventRecorder.try_create(_manager(kit))), kit


# --- command fixtures --------------------------------------------------------


def _close_position(subject: str = "pos-xyz", ordinal: int = 3) -> Command:
    return _ok(
        Command.close_position(
            _venue(), _account(), _SESSION_EPOCH, ordinal, "instrument-within-binding", subject
        )
    )


def _place_order(ordinal: int = 1) -> Command:
    params = _ok(OrderParameters.try_create(OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, _qty()))
    return _ok(Command.place_order(_venue(), _account(), _SESSION_EPOCH, ordinal, params))


# =====================================================================================
# AC1 — recording precedes interpretation; mandatory stamps; fill identity fields
# =====================================================================================


def test_inbound_event_stores_raw_payload_and_mandatory_stamps() -> None:
    event = _event()
    assert event.raw_payload["wire"] == "verbatim-payload"
    assert isinstance(event.receive_wall_time, Instant)
    assert isinstance(event.monotonic_stamp, MonotonicReading)
    assert event.session_epoch == _SESSION_EPOCH


def test_receive_wall_time_is_mandatory() -> None:
    refusal = _refusal(
        InboundVenueEvent.try_create(
            ObservationKind.FILL,
            _identity(),
            None,
            _monotonic(),
            _SESSION_EPOCH,
            {"wire": "x"},
        )
    )
    assert refusal.context["field"] == "receive_wall_time"


def test_monotonic_stamp_is_mandatory() -> None:
    refusal = _refusal(
        InboundVenueEvent.try_create(
            ObservationKind.SUBMISSION_ACKNOWLEDGEMENT,
            _identity(),
            _instant(),
            None,
            _SESSION_EPOCH,
            {"wire": "x"},
        )
    )
    assert refusal.context["field"] == "monotonic_stamp"


def test_raw_payload_is_never_absent() -> None:
    refusal = _refusal(
        InboundVenueEvent.try_create(
            ObservationKind.SUBMISSION_ACKNOWLEDGEMENT,
            _identity(),
            _instant(),
            _monotonic(),
            _SESSION_EPOCH,
            None,
        )
    )
    assert refusal.context["field"] == "raw_payload"


def test_fill_requires_price_quantity_and_venue_instant() -> None:
    for missing in ("fill_price", "fill_quantity", "venue_instant"):
        kwargs: dict[str, object] = {
            "fill_price": _price(),
            "fill_quantity": _qty(),
            "venue_instant": _instant(),
        }
        kwargs[missing] = None
        refusal = _refusal(
            InboundVenueEvent.try_create(
                ObservationKind.FILL,
                _identity(),
                _instant(),
                _monotonic(),
                _SESSION_EPOCH,
                {"wire": "fill"},
                **kwargs,
            )
        )
        assert refusal.context["field"] == missing


def test_fill_quantity_must_be_strictly_positive() -> None:
    refusal = _refusal(
        InboundVenueEvent.try_create(
            ObservationKind.FILL,
            _identity(),
            _instant(),
            _monotonic(),
            _SESSION_EPOCH,
            {"wire": "fill"},
            fill_price=_price(),
            fill_quantity=_ok(Quantity.try_create(0, "lot", 2)),
            venue_instant=_instant(),
        )
    )
    assert refusal.context["field"] == "fill_quantity"


def test_non_fill_cannot_carry_fill_price_or_quantity() -> None:
    price_refusal = _refusal(
        InboundVenueEvent.try_create(
            ObservationKind.CANCEL_ACKNOWLEDGEMENT,
            _identity(),
            _instant(),
            _monotonic(),
            _SESSION_EPOCH,
            {"wire": "cancel"},
            fill_price=_price(),
        )
    )
    assert price_refusal.context["field"] == "fill_price"
    qty_refusal = _refusal(
        InboundVenueEvent.try_create(
            ObservationKind.EXPIRY,
            _identity(),
            _instant(),
            _monotonic(),
            _SESSION_EPOCH,
            {"wire": "expiry"},
            fill_quantity=_qty(),
        )
    )
    assert qty_refusal.context["field"] == "fill_quantity"


def test_fill_identity_fields_enter_fingerprint_but_receive_stamp_does_not() -> None:
    # Two fills identical but for their receive wall time fingerprint the SAME — the receive
    # stamp is on the exclusion list — while a different fill price moves the fingerprint.
    base = _fill()
    later = _ok(
        InboundVenueEvent.try_create(
            ObservationKind.FILL,
            _identity(),
            _instant(_WALL_NS + 999),
            _monotonic(9_999_999),
            "a-different-session-epoch",
            {"wire": "fill"},
            fill_price=_price(),
            fill_quantity=_qty(),
            venue_instant=_instant(),
        )
    )
    assert _ok(base.fingerprint()).value == _ok(later.fingerprint()).value
    repriced = _ok(
        InboundVenueEvent.try_create(
            ObservationKind.FILL,
            _identity(),
            _instant(),
            _monotonic(),
            _SESSION_EPOCH,
            {"wire": "fill"},
            fill_price=_price(1_20000),
            fill_quantity=_qty(),
            venue_instant=_instant(),
        )
    )
    assert _ok(base.fingerprint()).value != _ok(repriced.fingerprint()).value


def test_redelivery_deduplicates_on_venue_native_identity() -> None:
    # A redelivered event with a different receive stamp keeps one identity (gap-replay dedup).
    first = _event(native_id="obs-9", revision=2, receive_ns=_WALL_NS)
    redelivered = _event(native_id="obs-9", revision=2, receive_ns=_WALL_NS + 1_000)
    assert _ok(first.fingerprint()).value == _ok(redelivered.fingerprint()).value


def test_recording_precedes_interpretation_raw_and_journal_land_first() -> None:
    recorder, sinks = _recorder()
    result = _ok(
        recorder.record(
            _fill(), registry_record={"record": "fill"}, boundary=TransactionBoundary.ATOMIC
        )
    )
    assert result.committed is True
    assert result.completed_rooms == (
        WriteRoom.RAW_ARCHIVE,
        WriteRoom.JOURNAL,
        WriteRoom.REGISTRY_ROOM,
    )
    # The verbatim observation reached the raw archive; a journal event and a record followed.
    assert sinks.obs.emitted == [_fill()] or isinstance(sinks.obs.emitted[0], InboundVenueEvent)
    assert isinstance(sinks.journal.appended[0], ObservationJournalEvent)
    assert sinks.record.written == [{"record": "fill"}]


def test_venue_native_identity_requires_its_parts() -> None:
    assert _refusal(VenueNativeIdentity.try_create("", "id", 0)).context["field"] == "source"
    assert (
        _refusal(VenueNativeIdentity.try_create("ctrader", "  ", 0)).context["field"]
        == "source_native_id"
    )
    assert (
        _refusal(VenueNativeIdentity.try_create("ctrader", "id", -1)).context["field"] == "revision"
    )
    assert (
        _refusal(VenueNativeIdentity.try_create("ctrader", "id", True)).context["field"]
        == "revision"
    )


def test_inbound_event_validates_kind_and_tokens() -> None:
    assert (
        _refusal(
            InboundVenueEvent.try_create(
                "not-a-kind", _identity(), _instant(), _monotonic(), _SESSION_EPOCH, {"w": 1}
            )
        ).context["field"]
        == "observation_kind"
    )
    assert (
        _refusal(
            InboundVenueEvent.try_create(
                ObservationKind.FILL,
                "not-identity",
                _instant(),
                _monotonic(),
                _SESSION_EPOCH,
                {},
            )
        ).context["field"]
        == "venue_native_identity"
    )
    assert (
        _refusal(
            InboundVenueEvent.try_create(
                ObservationKind.EXPIRY, _identity(), _instant(), _monotonic(), "   ", {"w": 1}
            )
        ).context["field"]
        == "session_epoch"
    )
    assert (
        _refusal(
            InboundVenueEvent.try_create(
                ObservationKind.EXPIRY,
                _identity(),
                _instant(),
                _monotonic(),
                _SESSION_EPOCH,
                {"w": 1},
                subject_native_id="   ",
            )
        ).context["field"]
        == "subject_native_id"
    )
    assert (
        _refusal(
            InboundVenueEvent.try_create(
                ObservationKind.EXPIRY,
                _identity(),
                _instant(),
                _monotonic(),
                _SESSION_EPOCH,
                {"w": 1},
                venue_instant="not-an-instant",
            )
        ).context["field"]
        == "venue_instant"
    )


def test_out_of_sequence_is_not_a_raw_inbound_kind() -> None:
    # An adapter never synthesizes a venue observation: out-of-sequence is a derived
    # annotation, never a raw kind at construction.
    refusal = _refusal(
        InboundVenueEvent.try_create(
            ObservationKind.OUT_OF_SEQUENCE,
            _identity(),
            _instant(),
            _monotonic(),
            _SESSION_EPOCH,
            {"w": 1},
        )
    )
    assert refusal.context["field"] == "observation_kind"


# =====================================================================================
# AC2 — order state is a read-time fold; separate streams; terminal only from lifecycle
# =====================================================================================


def test_order_state_is_never_a_stored_field() -> None:
    # The verbatim observation carries no order-state slot; state is a read-time fold only.
    event = _event()
    assert not hasattr(event, "order_state")
    assert "order_state" not in event.fp1_identity()


def test_fold_projects_prefix_from_command_outcome() -> None:
    assert _ok(fold_order_state(None, [])).state is OrderState.CLIENT_SUBMITTED
    assert (
        _ok(fold_order_state(SubmissionOutcome.ACCEPTED_BY_VENUE, [])).state
        is OrderState.VENUE_ACCEPTED
    )
    assert (
        _ok(fold_order_state(SubmissionOutcome.REJECTED_BY_VENUE, [])).state
        is OrderState.VENUE_REJECTED
    )
    assert _ok(fold_order_state(SubmissionOutcome.UNKNOWN, [])).state is OrderState.UNKNOWN


def test_prefix_states_are_never_terminal() -> None:
    # accepted/rejected/UNKNOWN are command-outcome projections, never an order terminal.
    for outcome in (
        SubmissionOutcome.ACCEPTED_BY_VENUE,
        SubmissionOutcome.REJECTED_BY_VENUE,
        SubmissionOutcome.UNKNOWN,
    ):
        assert _ok(fold_order_state(outcome, [])).terminal is False


def test_denied_locally_and_partially_executed_have_no_order_fold() -> None:
    assert (
        _refusal(fold_order_state(SubmissionOutcome.DENIED_LOCALLY, [])).context["field"]
        == "command_outcome"
    )
    assert (
        _refusal(fold_order_state(SubmissionOutcome.PARTIALLY_EXECUTED, [])).context["field"]
        == "command_outcome"
    )


def test_fill_folds_to_partially_filled_then_filled() -> None:
    # The natural stream: client-submitted, an acknowledgement (venue-accepted), then fills.
    ack = _event(ObservationKind.SUBMISSION_ACKNOWLEDGEMENT, native_id="ack")
    half = _fill(native_id="f1", quantity=_qty(60))
    rest = _fill(native_id="f2", quantity=_qty(40))
    partial = _ok(fold_order_state(None, [ack, half], ordered_quantity=_qty(100)))
    assert partial.state is OrderState.PARTIALLY_FILLED
    assert partial.terminal is False
    assert partial.cumulative_fill == _qty(60).as_fraction()
    full = _ok(fold_order_state(None, [ack, half, rest], ordered_quantity=_qty(100)))
    assert full.state is OrderState.FILLED
    assert full.terminal is True


def test_full_fill_is_never_inferred_without_ordered_quantity() -> None:
    # Absent the ordered quantity, a fill can only be read as partially-filled — a terminal
    # state is never inferred from absence alone.
    fill = _fill(quantity=_qty(100))
    projection = _ok(fold_order_state(SubmissionOutcome.ACCEPTED_BY_VENUE, [fill]))
    assert projection.state is OrderState.PARTIALLY_FILLED
    assert projection.terminal is False


def test_terminal_state_decided_only_by_lifecycle_events() -> None:
    cancel = _event(ObservationKind.CANCEL_ACKNOWLEDGEMENT, native_id="c")
    cancelled = _ok(fold_order_state(SubmissionOutcome.ACCEPTED_BY_VENUE, [cancel]))
    assert cancelled.state is OrderState.CANCELLED
    assert cancelled.terminal is True
    expiry = _event(ObservationKind.EXPIRY, native_id="e")
    assert (
        _ok(fold_order_state(SubmissionOutcome.ACCEPTED_BY_VENUE, [expiry])).state
        is OrderState.EXPIRED
    )
    close = _event(ObservationKind.CLOSE_BY_VENUE, native_id="cbv")
    assert (
        _ok(fold_order_state(SubmissionOutcome.ACCEPTED_BY_VENUE, [close])).state
        is OrderState.CLOSED_BY_VENUE
    )


def test_command_outcome_and_order_state_are_separate_streams() -> None:
    # The fold reads the two streams as separate inputs; the observation carries no command
    # outcome, and a submission acknowledgement never decides an order's terminal state.
    ack = _event(ObservationKind.SUBMISSION_ACKNOWLEDGEMENT)
    assert not hasattr(ack, "outcome")
    projection = _ok(fold_order_state(None, [ack]))
    assert projection.state is OrderState.VENUE_ACCEPTED
    assert projection.terminal is False


def test_fold_validates_its_inputs() -> None:
    assert _refusal(fold_order_state(None, "not-a-sequence")).context["field"] == "observations"
    assert _refusal(fold_order_state(None, [object()])).context["field"] == "observations"
    assert (
        _refusal(fold_order_state(None, [], ordered_quantity="not-a-qty")).context["field"]
        == "ordered_quantity"
    )
    assert _refusal(fold_order_state("not-an-outcome", [])).context["field"] == "command_outcome"


# =====================================================================================
# AC3 — out-of-sequence edge forces UNKNOWN; adapters never synthesize an observation
# =====================================================================================


def test_is_legal_transition_table() -> None:
    assert is_legal_transition(
        OrderState.CLIENT_SUBMITTED, ObservationKind.SUBMISSION_ACKNOWLEDGEMENT
    )
    assert is_legal_transition(OrderState.VENUE_ACCEPTED, ObservationKind.FILL)
    assert not is_legal_transition(OrderState.FILLED, ObservationKind.FILL)
    assert not is_legal_transition(OrderState.CANCELLED, ObservationKind.FILL)
    # An out-of-sequence kind is never legal, and a non-enum argument is a safe False.
    assert not is_legal_transition(OrderState.VENUE_ACCEPTED, ObservationKind.OUT_OF_SEQUENCE)
    assert not is_legal_transition("nonsense", ObservationKind.FILL)
    assert not is_legal_transition(OrderState.VENUE_ACCEPTED, "nonsense")


def test_detect_out_of_sequence_returns_edge_for_illegal_transition() -> None:
    fill = _fill()
    # A fill from a terminal state (cancelled) has no legal transition.
    edge = _ok(detect_out_of_sequence(OrderState.CANCELLED, fill))
    assert isinstance(edge, OutOfSequenceEdge)
    assert edge.attempted_kind is ObservationKind.FILL
    assert edge.prior_state is OrderState.CANCELLED
    # A legal transition returns no edge.
    assert _ok(detect_out_of_sequence(OrderState.VENUE_ACCEPTED, fill)) is None


def test_detect_out_of_sequence_validates_inputs() -> None:
    assert _refusal(detect_out_of_sequence("nonsense", _fill())).context["field"] == "prior_state"
    assert (
        _refusal(detect_out_of_sequence(OrderState.VENUE_ACCEPTED, object())).context["field"]
        == "event"
    )


def test_annotated_observation_forces_owning_command_to_unknown() -> None:
    ack = _event(ObservationKind.SUBMISSION_ACKNOWLEDGEMENT, native_id="ack")
    stray_fill = _fill(native_id="stray")
    # client-submitted -> ack (venue-accepted) -> cancel (cancelled) -> a fill after a cancel
    # is illegal; the fold detects it and forces UNKNOWN.
    cancel = _event(ObservationKind.CANCEL_ACKNOWLEDGEMENT, native_id="c")
    projection = _ok(fold_order_state(None, [ack, cancel, stray_fill]))
    assert projection.state is OrderState.UNKNOWN
    assert projection.out_of_sequence is True
    assert projection.terminal is False


def test_pre_annotated_out_of_sequence_event_forces_unknown() -> None:
    edge = _ok(
        OutOfSequenceEdge.try_create(
            ObservationKind.FILL, OrderState.CANCELLED, "no legal transition"
        )
    )
    annotated = _ok(_fill().with_out_of_sequence(edge))
    assert annotated.out_of_sequence is edge
    assert annotated.effective_journal_kind is ObservationKind.OUT_OF_SEQUENCE
    projection = _ok(fold_order_state(SubmissionOutcome.ACCEPTED_BY_VENUE, [annotated]))
    assert projection.state is OrderState.UNKNOWN
    assert projection.out_of_sequence is True


def test_with_out_of_sequence_requires_a_typed_edge() -> None:
    assert _refusal(_fill().with_out_of_sequence("not-an-edge")).context["field"] == "edge"


def test_out_of_sequence_edge_validates_its_parts() -> None:
    assert (
        _refusal(OutOfSequenceEdge.try_create("nope", OrderState.VENUE_ACCEPTED, "r")).context[
            "field"
        ]
        == "attempted_kind"
    )
    assert (
        _refusal(OutOfSequenceEdge.try_create(ObservationKind.FILL, "nope", "r")).context["field"]
        == "prior_state"
    )
    assert (
        _refusal(
            OutOfSequenceEdge.try_create(ObservationKind.FILL, OrderState.VENUE_ACCEPTED, "  ")
        ).context["field"]
        == "reason"
    )


def test_annotated_observation_journals_under_out_of_sequence_type() -> None:
    edge = _ok(
        OutOfSequenceEdge.try_create(ObservationKind.FILL, OrderState.CANCELLED, "no transition")
    )
    annotated = _ok(_fill().with_out_of_sequence(edge))
    journal_event = ObservationJournalEvent.for_event(annotated)
    assert journal_event.observation_kind is ObservationKind.OUT_OF_SEQUENCE
    assert journal_event.event_type == "observation.out-of-sequence"


# =====================================================================================
# AC4 — multi-room write as one ordered unit; partial write blocks + journals on recovery
# =====================================================================================


def test_multi_room_write_commits_all_three_rooms_in_order() -> None:
    recorder, sinks = _recorder()
    result = _ok(
        recorder.record(
            _event(), registry_record={"r": 1}, boundary=TransactionBoundary.ORDERED_WITH_RECOVERY
        )
    )
    assert isinstance(result, MultiRoomWriteResult)
    assert result.committed is True
    assert result.failed_room is None
    assert len(sinks.obs.emitted) == 1
    assert len(sinks.journal.appended) == 1
    assert len(sinks.record.written) == 1


def test_partial_write_at_journal_is_storage_failure_and_blocks_command_stream() -> None:
    sinks = _Sinks()
    sinks.journal.fail = True
    recorder, _ = _recorder(sinks)
    refusal = _refusal(
        recorder.record(_event(), registry_record={"r": 1}, boundary=TransactionBoundary.ATOMIC)
    )
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    assert refusal.context["completed_rooms"] == (WriteRoom.RAW_ARCHIVE.value,)
    assert refusal.context["failed_room"] == WriteRoom.JOURNAL.value
    # The command stream is blocked; the sensing pipe is unaffected.
    assert recorder.command_pipe_open is False
    assert recorder.sensing_pipe_open is True
    # The raw archive landed but the registry room was never attempted (ordered unit).
    assert len(sinks.obs.emitted) == 1
    assert len(sinks.record.written) == 0


def test_partial_write_at_raw_archive_blocks_before_any_room_completes() -> None:
    sinks = _Sinks()
    sinks.obs.fail = True
    recorder, _ = _recorder(sinks)
    refusal = _refusal(
        recorder.record(_event(), registry_record={"r": 1}, boundary=TransactionBoundary.ATOMIC)
    )
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    assert refusal.context["completed_rooms"] == ()
    assert refusal.context["failed_room"] == WriteRoom.RAW_ARCHIVE.value
    assert recorder.command_pipe_open is False


def test_partial_write_at_registry_room_records_failed_room() -> None:
    sinks = _Sinks()
    sinks.record.fail = True
    recorder, _ = _recorder(sinks)
    refusal = _refusal(
        recorder.record(_event(), registry_record={"r": 1}, boundary=TransactionBoundary.ATOMIC)
    )
    assert refusal.context["failed_room"] == WriteRoom.REGISTRY_ROOM.value
    assert refusal.context["completed_rooms"] == (
        WriteRoom.RAW_ARCHIVE.value,
        WriteRoom.JOURNAL.value,
    )


def test_partial_write_is_journaled_on_recovery() -> None:
    sinks = _Sinks()
    sinks.journal.fail = True
    recorder, _ = _recorder(sinks)
    _refusal(
        recorder.record(_event(), registry_record={"r": 1}, boundary=TransactionBoundary.ATOMIC)
    )
    pending = recorder.pending_recovery
    assert isinstance(pending, PartialWriteRecovery)
    assert pending.failed_room is WriteRoom.JOURNAL
    # The store returns; recovery journals the partial write, clearing the block and pending.
    sinks.journal.fail = False
    ack = _ok(recorder.recover())
    assert isinstance(ack, SinkAck)
    assert recorder.pending_recovery is None
    assert recorder.command_pipe_open is True
    # The recovery journal event names the affected observation identity.
    recovery_event = sinks.journal.appended[-1]
    assert isinstance(recovery_event, ObservationJournalEvent)
    assert recovery_event.event_type == "observation.partial-write-recovery"


def test_recover_with_no_pending_partial_is_refused() -> None:
    recorder, _ = _recorder()
    assert _refusal(recorder.recover()).context["field"] == "recovery"


def test_recover_surfaces_a_still_failing_store_and_keeps_pending() -> None:
    sinks = _Sinks()
    sinks.journal.fail = True
    recorder, _ = _recorder(sinks)
    _refusal(
        recorder.record(_event(), registry_record={"r": 1}, boundary=TransactionBoundary.ATOMIC)
    )
    # The journal is still down; recovery surfaces the failure and stays pending.
    refusal = _refusal(recorder.recover())
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    assert recorder.pending_recovery is not None


def test_multi_room_write_validates_its_inputs() -> None:
    assert (
        _refusal(
            MultiRoomWrite.for_event("not-an-event", registry_record={}, boundary="atomic")
        ).context["field"]
        == "event"
    )
    assert (
        _refusal(
            MultiRoomWrite.for_event(_event(), registry_record={}, boundary="not-a-boundary")
        ).context["field"]
        == "boundary"
    )
    assert (
        _refusal(
            MultiRoomWrite.for_event(_event(), registry_record=None, boundary="atomic")
        ).context["field"]
        == "registry_record"
    )
    recorder, _ = _recorder()
    assert _refusal(recorder.record_multi_room("not-a-write")).context["field"] == "write"


def test_recorder_try_create_requires_a_connection_manager() -> None:
    assert (
        _refusal(EventRecorder.try_create("not-a-manager")).context["field"] == "connection_manager"
    )


def test_recorder_exposes_the_connection_manager() -> None:
    recorder, _ = _recorder()
    assert isinstance(recorder.connection_manager, ConnectionManager)


def test_observation_journal_event_type_maps_each_kind() -> None:
    assert observation_journal_event_type(ObservationKind.FILL) == "observation.fill"
    assert (
        observation_journal_event_type("submission-acknowledgement")
        == "observation.submission-acknowledgement"
    )


# =====================================================================================
# AC5 — reconciliation read-back over a mandatory lookback; four verdicts; command-pipe only
# =====================================================================================


def _readback(
    *, earliest_ns: int, evidence: dict[str, object] | None = None
) -> ReconciliationReadback:
    return _ok(
        ReconciliationReadback.try_create(
            _instant(_WALL_NS),
            _ok(Duration.try_create(_LOOKBACK_NS)),
            _instant(earliest_ns),
            evidence if evidence is not None else {"orders": [], "positions": [], "balance": "0"},
        )
    )


def test_reconciliation_lookback_is_mandatory_do_not_default() -> None:
    refusal = _refusal(
        ReconciliationReadback.try_create(_instant(), None, _instant(), {"orders": []})
    )
    assert refusal.context["field"] == "declared_lookback"


def test_reconciliation_lookback_must_be_positive() -> None:
    refusal = _refusal(
        ReconciliationReadback.try_create(
            _instant(), _ok(Duration.try_create(0)), _instant(), {"orders": []}
        )
    )
    assert refusal.context["field"] == "declared_lookback"


def test_reconciliation_verdict_reconciled_when_state_agrees() -> None:
    readback = _readback(earliest_ns=_WALL_NS - _LOOKBACK_NS - 1)
    verdict = _ok(readback.verdict({"pos": "flat"}, {"pos": "flat"}))
    assert verdict.verdict is ReconciliationVerdict.RECONCILED
    assert verdict.standing_intent_may_dispatch is True
    assert verdict.holds_intent_open is False


def test_reconciliation_verdict_drift_when_state_disagrees() -> None:
    readback = _readback(earliest_ns=_WALL_NS - _LOOKBACK_NS - 1)
    verdict = _ok(readback.verdict({"pos": "long"}, {"pos": "flat"}))
    assert verdict.verdict is ReconciliationVerdict.DRIFT
    assert verdict.standing_intent_may_dispatch is False
    assert verdict.holds_intent_open is True


def test_reconciliation_verdict_unknown_when_venue_state_unreadable() -> None:
    readback = _readback(earliest_ns=_WALL_NS - _LOOKBACK_NS - 1)
    verdict = _ok(readback.verdict({"pos": "long"}, None))
    assert verdict.verdict is ReconciliationVerdict.UNKNOWN
    assert verdict.holds_intent_open is True


def test_out_of_lookback_is_never_read_as_position_closed() -> None:
    # The read-back cannot see the whole declared lookback: earliest_visible is AFTER the
    # required window start, so the verdict is out-of-lookback, distinct from reconciled.
    readback = _readback(earliest_ns=_WALL_NS - 1)
    verdict = _ok(readback.verdict({"pos": "long"}, {"pos": "flat"}))
    assert verdict.verdict is ReconciliationVerdict.OUT_OF_LOOKBACK
    assert verdict.is_out_of_lookback is True
    # It never dispatches a standing protection intent and holds it open.
    assert verdict.standing_intent_may_dispatch is False
    assert verdict.holds_intent_open is True
    assert readback.covers_declared_lookback is False


def test_reconciliation_gates_command_pipe_only_never_sensing() -> None:
    for verdict_value in (
        ReconciliationVerdict.RECONCILED,
        ReconciliationVerdict.DRIFT,
        ReconciliationVerdict.UNKNOWN,
        ReconciliationVerdict.OUT_OF_LOOKBACK,
    ):
        assert Reconciliation(verdict=verdict_value, detail="x").gates_sensing_pipe is False


def test_reconciliation_verdict_vocabulary_is_exactly_four() -> None:
    assert {v.value for v in ReconciliationVerdict} == {
        "reconciled",
        "drift",
        "unknown",
        "out-of-lookback",
    }


def test_reconciliation_readback_validates_instants_and_evidence() -> None:
    lookback = _ok(Duration.try_create(_LOOKBACK_NS))
    assert (
        _refusal(
            ReconciliationReadback.try_create("nope", lookback, _instant(), {"o": []})
        ).context["field"]
        == "reference_instant"
    )
    assert (
        _refusal(
            ReconciliationReadback.try_create(_instant(), lookback, "nope", {"o": []})
        ).context["field"]
        == "earliest_visible"
    )
    assert (
        _refusal(
            ReconciliationReadback.try_create(_instant(), lookback, _instant(), "not-a-mapping")
        ).context["field"]
        == "readback_evidence"
    )


# =====================================================================================
# AC6 — subject-terminal resolution: superseded (named) vs resolve-without-submission
# =====================================================================================


def test_subject_terminal_at_or_after_submit_supersedes_with_named_outcome() -> None:
    command = _close_position(subject="pos-xyz")
    submit_stamp = _instant(_WALL_NS)
    # The protective stop filled on the subject at the submit stamp — subject terminal.
    stop_fill = _fill(native_id="stop", subject="pos-xyz", venue_ns=_WALL_NS)
    resolution = _ok(
        resolve_subject_terminal(
            command,
            observations=[stop_fill],
            submit_stamp=submit_stamp,
            subject_present_at_submission=True,
        )
    )
    assert resolution.resolution is SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT
    assert resolution.outcome is SubmissionOutcome.REJECTED_BY_VENUE
    # A named outcome, never UNKNOWN.
    assert resolution.outcome is not SubmissionOutcome.UNKNOWN
    assert resolution.resolving_observation is stop_fill


def test_subject_absent_at_submission_resolves_without_submission() -> None:
    command = _close_position(subject="pos-gone")
    resolution = _ok(
        resolve_subject_terminal(
            command,
            observations=[],
            submit_stamp=_instant(_WALL_NS),
            subject_present_at_submission=False,
        )
    )
    assert resolution.resolution is SubjectResolution.RESOLVE_WITHOUT_SUBMISSION
    assert resolution.outcome is None


def test_subject_already_terminal_before_submission_resolves_without_submission() -> None:
    command = _close_position(subject="pos-xyz")
    prior_close = _fill(native_id="prior", subject="pos-xyz", venue_ns=_WALL_NS - 10)
    resolution = _ok(
        resolve_subject_terminal(
            command,
            observations=[prior_close],
            submit_stamp=_instant(_WALL_NS),
            subject_present_at_submission=True,
        )
    )
    assert resolution.resolution is SubjectResolution.RESOLVE_WITHOUT_SUBMISSION
    assert resolution.resolving_observation is prior_close


def test_live_subject_with_no_terminal_observation_proceeds() -> None:
    command = _close_position(subject="pos-live")
    unrelated = _fill(native_id="other", subject="pos-other", venue_ns=_WALL_NS + 5)
    resolution = _ok(
        resolve_subject_terminal(
            command,
            observations=[unrelated],
            submit_stamp=_instant(_WALL_NS),
            subject_present_at_submission=True,
        )
    )
    assert resolution.resolution is SubjectResolution.PROCEED
    assert resolution.outcome is None
    assert resolution.resolving_observation is None


def test_subject_terminal_resolution_applies_to_the_three_subject_commands() -> None:
    stop_fill = _fill(native_id="stop", subject="pos-xyz", venue_ns=_WALL_NS)
    close_all = _ok(
        Command.close_all(_venue(), _account(), _SESSION_EPOCH, 5, "account", "pos-xyz")
    )
    resolution = _ok(
        resolve_subject_terminal(
            close_all,
            observations=[stop_fill],
            submit_stamp=_instant(_WALL_NS),
            subject_present_at_submission=True,
        )
    )
    assert resolution.resolution is SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT


def test_subject_terminal_resolution_rejects_non_subject_commands() -> None:
    refusal = _refusal(
        resolve_subject_terminal(
            _place_order(),
            observations=[],
            submit_stamp=_instant(_WALL_NS),
            subject_present_at_submission=True,
        )
    )
    assert refusal.context["field"] == "command"
    assert refusal.context["kind"] == CommandKind.PLACE_ORDER.value


def test_subject_terminal_resolution_validates_inputs() -> None:
    command = _close_position()
    assert (
        _refusal(
            resolve_subject_terminal(
                "not-a-command",
                observations=[],
                submit_stamp=_instant(),
                subject_present_at_submission=True,
            )
        ).context["field"]
        == "command"
    )
    assert (
        _refusal(
            resolve_subject_terminal(
                command,
                observations=[],
                submit_stamp="nope",
                subject_present_at_submission=True,
            )
        ).context["field"]
        == "submit_stamp"
    )
    assert (
        _refusal(
            resolve_subject_terminal(
                command,
                observations=[],
                submit_stamp=_instant(),
                subject_present_at_submission="nope",
            )
        ).context["field"]
        == "subject_present_at_submission"
    )
    assert (
        _refusal(
            resolve_subject_terminal(
                command,
                observations="not-a-sequence",
                submit_stamp=_instant(),
                subject_present_at_submission=True,
            )
        ).context["field"]
        == "observations"
    )


def test_non_terminal_observation_on_subject_does_not_supersede() -> None:
    command = _close_position(subject="pos-xyz")
    # A submission acknowledgement on the subject is not a terminal observation.
    ack = _event(
        ObservationKind.SUBMISSION_ACKNOWLEDGEMENT,
        native_id="ack",
        subject="pos-xyz",
        venue_instant=_instant(_WALL_NS + 5),
    )
    resolution = _ok(
        resolve_subject_terminal(
            command,
            observations=[ack],
            submit_stamp=_instant(_WALL_NS),
            subject_present_at_submission=True,
        )
    )
    assert resolution.resolution is SubjectResolution.PROCEED
