"""Story 8.5 tests — five typed command kinds under the four-outcome law (CT-19).

Fixture-driven throughout: commands are built on qmf-core value types, a representative
cTrader-platform capability declaration is assembled as *data* (parameterized on the
command-id mapping and the pinned error map), and fake sinks stand in for the injected
persistence seams. These pin every acceptance criterion — the exactly-five typed
vocabulary with no free-form payload and the partial-close unsupported-capability refusal;
the four-outcome law with denied-locally an outcome (never a refusal) and every outcome
minting an observation and a journal event; transport UNKNOWN as a state and the venue-error
table gate; command identity as the record fp1 with the durable command-id-binding,
idempotent re-presentation, and alarmed collision; the risk-non-increasing per-side
amend_protection constraint; and the compound meet (FR-023, CT-19, CT-20, AR-44, AR-48;
DEC-0137, DEC-0138, DEC-0140, DEC-0148).
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
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.venue import (
    FOUR_OUTCOME_LAW,
    BindingOutcome,
    Command,
    CommandIdBinding,
    CommandIdBindingRegistry,
    CommandKind,
    CommandOutcomeResolver,
    CompoundCommand,
    JournalEvent,
    OrderParameters,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    SubmissionOutcome,
    TimeInForce,
    UnknownTrigger,
    command_id_mapping_is_injective_total,
    derive_child_identity,
    is_success,
    journal_event_type,
    meet_outcomes,
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

_SESSION_EPOCH = "session-epoch-1"
_WALL_NS = 1_724_000_000 * 1_000_000_000
_DEADLINE_NS = _WALL_NS + 5_000_000_000
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


def _instrument(symbol: str = "EURUSD", venue: VenueId | None = None) -> Instrument:
    return _ok(Instrument.try_create(venue if venue is not None else _venue(), symbol))


def _instant(value_ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(value_ns))


def _duration(value_ns: int = 250_000_000) -> Duration:
    return _ok(Duration.try_create(value_ns))


def _price(value: int = 1_10000, scale: int = 5, symbol: str = "EURUSD") -> Price:
    return _ok(Price.try_create(value, _instrument(symbol), scale))


def _delta(value: int = 100, scale: int = 5, symbol: str = "EURUSD") -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(symbol), scale))


def _qty(value: int = 100, scale: int = 2) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


# --- command fixtures --------------------------------------------------------


def _order_params(order_type: OrderType = OrderType.MARKET, **kwargs: object) -> OrderParameters:
    return _ok(
        OrderParameters.try_create(order_type, TimeInForce.GOOD_TILL_CANCEL, _qty(), **kwargs)
    )


def _place_order(ordinal: int = 1, params: OrderParameters | None = None) -> Command:
    return _ok(
        Command.place_order(
            _venue(),
            _account(),
            _SESSION_EPOCH,
            ordinal,
            params if params is not None else _order_params(),
        )
    )


def _cancel_order(ordinal: int = 2, subject: str = "order-abc") -> Command:
    return _ok(Command.cancel_order(_venue(), _account(), _SESSION_EPOCH, ordinal, subject))


def _close_position(ordinal: int = 3) -> Command:
    return _ok(
        Command.close_position(
            _venue(), _account(), _SESSION_EPOCH, ordinal, "instrument-within-binding", "pos-xyz"
        )
    )


def _amend(ordinal: int = 4, amendment: ProtectionAmendment | None = None) -> Command:
    return _ok(
        Command.amend_protection(
            _venue(),
            _account(),
            _SESSION_EPOCH,
            ordinal,
            amendment if amendment is not None else _stop_amendment(),
            "pos-xyz",
        )
    )


def _stop_amendment(new_value: int = 80, original_value: int = 100) -> ProtectionAmendment:
    return _ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP,
            _delta(new_value),
            _price(),
            original_risk_distance=_delta(original_value),
        )
    )


# --- a representative cTrader-platform capability declaration ----------------


def _artifact() -> ProtoArtifact:
    return _ok(ProtoArtifact.try_create("openapi-proto-messages", _PROTO_TAG, _DIGEST))


def _static(name: CapabilityFieldName, value: object) -> CapabilityField:
    return _ok(CapabilityField.static(name, value))


def _measured(name: CapabilityFieldName) -> CapabilityField:
    return _ok(CapabilityField.measured(name))


def _roster(*, injective_total: bool = True) -> list[CapabilityField]:
    return [
        _static(CapabilityFieldName.MARKET_DATA_KINDS, ["tick", "bar", "depth"]),
        _static(
            CapabilityFieldName.ORDER_PARAMETER_SUBSET,
            {"order_types": ["market", "limit", "stop", "stop-limit"]},
        ),
        _static(
            CapabilityFieldName.COMMAND_SCOPES,
            ["account", "account-binding", "instrument-within-binding"],
        ),
        _static(CapabilityFieldName.ACKNOWLEDGEMENT_MODES, {"place_order": "explicit-event"}),
        _measured(CapabilityFieldName.POSITION_MODEL),
        _static(CapabilityFieldName.SESSION_TOPOLOGY, "two-connections-demo-live-separate-hosts"),
        _static(CapabilityFieldName.THROTTLE_SCOPE, "connection"),
        _static(CapabilityFieldName.RATE_LIMITS, {"non_historical_per_second": 50}),
        _static(CapabilityFieldName.SPAN_CAPS_AND_PAGING, {"historical_span_cap_ms": 604_800_000}),
        _static(CapabilityFieldName.TOKEN_LIFECYCLE_CLASS, {"access_token_days": 30}),
        _static(CapabilityFieldName.EQUITY_NATIVENESS, "derived"),
        _static(CapabilityFieldName.SERVER_CLOCK_AVAILABILITY, False),
        _static(CapabilityFieldName.INSTRUMENT_METADATA_SURFACE, "full-symbol-record-required"),
        _static(CapabilityFieldName.ATTRIBUTION_LABEL_SUPPORT, False),
        _static(CapabilityFieldName.PROTECTION_PRIMITIVES, ["suspend-new", "drain", "close_all"]),
        _measured(CapabilityFieldName.SETTLEMENT_CURRENCY),
        _measured(CapabilityFieldName.MARGIN_SURFACE),
        _measured(CapabilityFieldName.VALUE_FACTOR_METADATA),
        _static(CapabilityFieldName.RECONCILIATION_LOOKBACK, "do-not-default"),
        _measured(CapabilityFieldName.PROTECTION_CAPABILITIES),
        _static(CapabilityFieldName.COMMAND_ID_MAPPING, {"injective_total": injective_total}),
        _static(CapabilityFieldName.FLOAT_TARGET_SCALES, {"execution_price": "declared-digits"}),
        _static(CapabilityFieldName.VERIFICATION_SUITE, ["spot-timestamp-unit", "daily-boundary"]),
    ]


def _error_map() -> ErrorMap:
    rows = [
        _ok(
            ErrorMapRow.try_create(
                "ORDER_REJECTED",
                "place_order",
                RefusalCategory.POLICY_REJECTION,
                Retryability.NO,
                SubmissionOutcomeClass.REJECTED_BY_VENUE,
            )
        ),
        _ok(
            ErrorMapRow.try_create(
                "THROTTLED",
                "place_order",
                RefusalCategory.TRANSIENT_VENUE_FAILURE,
                Retryability.AFTER_CONDITION,
                SubmissionOutcomeClass.UNKNOWN,
                "rate window reopens",
            )
        ),
    ]
    return _ok(ErrorMap.try_create(1, rows))


def _declaration(*, injective_total: bool = True) -> CapabilityDeclaration:
    return _ok(
        CapabilityDeclaration.try_create(
            "ctrader-adapter-1.0.0",
            _artifact(),
            _error_map(),
            _roster(injective_total=injective_total),
        )
    )


def _resolver() -> CommandOutcomeResolver:
    return _ok(CommandOutcomeResolver.try_create(_declaration()))


# --- fake injected sinks -----------------------------------------------------


class _RecordingSink:
    """A RecordSink that durably stores every record and reports success."""

    def __init__(self) -> None:
        self.records: list[object] = []

    def write(self, record: object, /) -> SinkResult:
        self.records.append(record)
        return Ok(SinkAck())


class _FailingSink:
    """A RecordSink that always returns a storage-failure refusal."""

    def write(self, record: object, /) -> SinkResult:
        return unpersistable("the record store is offline")


# =====================================================================================
# AC1 — five typed command kinds, typed per kind, no free-form payload, partial close
# =====================================================================================


def test_command_vocabulary_is_exactly_five_kinds() -> None:
    assert {kind.value for kind in CommandKind} == {
        "place_order",
        "cancel_order",
        "close_position",
        "close_all",
        "amend_protection",
    }


def test_no_general_amend_order_kind_exists() -> None:
    # amend_protection is never widened into a general amend_order (DEC-0148).
    values = {kind.value for kind in CommandKind}
    assert "amend_order" not in values
    assert "amend_protection" in values


def test_place_order_is_typed_per_kind_with_no_cross_fields() -> None:
    command = _place_order()
    assert command.kind is CommandKind.PLACE_ORDER
    assert command.order_parameters is not None
    assert command.close_scope is None
    assert command.subject_reference is None
    assert command.protection_amendment is None


def test_place_order_refuses_free_form_payload() -> None:
    refusal = _refusal(
        Command.place_order(_venue(), _account(), _SESSION_EPOCH, 1, {"type": "market"})
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "order_parameters"


def test_cancel_order_names_its_subject() -> None:
    command = _cancel_order()
    assert command.kind is CommandKind.CANCEL_ORDER
    assert command.subject_reference == "order-abc"
    assert command.order_parameters is None


def test_cancel_order_requires_subject_reference() -> None:
    refusal = _refusal(Command.cancel_order(_venue(), _account(), _SESSION_EPOCH, 2, "  "))
    assert refusal.context["field"] == "subject_reference"


def test_close_position_carries_required_typed_scope() -> None:
    command = _close_position()
    assert command.kind is CommandKind.CLOSE_POSITION
    assert command.close_scope is not None
    assert command.close_scope.value == "instrument-within-binding"
    assert command.subject_reference == "pos-xyz"


def test_close_all_builds_over_scope() -> None:
    command = _ok(Command.close_all(_venue(), _account(), _SESSION_EPOCH, 5, "account", "acct-001"))
    assert command.kind is CommandKind.CLOSE_ALL
    assert command.close_scope is not None
    assert command.close_scope.value == "account"


def test_close_rejects_unknown_scope() -> None:
    refusal = _refusal(
        Command.close_position(_venue(), _account(), _SESSION_EPOCH, 3, "half-of-it", "pos-xyz")
    )
    assert refusal.context["field"] == "close_scope"


def test_close_requires_subject_reference() -> None:
    refusal = _refusal(Command.close_all(_venue(), _account(), _SESSION_EPOCH, 5, "account", ""))
    assert refusal.context["field"] == "subject_reference"


def test_partial_close_of_a_position_is_unsupported_capability() -> None:
    refusal = _refusal(
        Command.close_position(
            _venue(),
            _account(),
            _SESSION_EPOCH,
            3,
            "instrument-within-binding",
            "pos-xyz",
            partial_quantity=_qty(50),
        )
    )
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "partial_quantity"


def test_partial_close_all_is_unsupported_capability() -> None:
    refusal = _refusal(
        Command.close_all(
            _venue(),
            _account(),
            _SESSION_EPOCH,
            5,
            "account",
            "acct-001",
            partial_quantity=_qty(50),
        )
    )
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_order_parameters_reject_non_quantity() -> None:
    refusal = _refusal(
        OrderParameters.try_create(OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, 100)
    )
    assert refusal.context["field"] == "quantity"


def test_order_parameters_reject_non_positive_quantity() -> None:
    refusal = _refusal(
        OrderParameters.try_create(OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, _qty(0))
    )
    assert refusal.context["field"] == "quantity"


def test_order_parameters_reject_unknown_order_type_and_tif() -> None:
    assert (
        _refusal(OrderParameters.try_create("swap", TimeInForce.DAY, _qty())).context["field"]
        == "order_type"
    )
    assert (
        _refusal(OrderParameters.try_create(OrderType.MARKET, "forever", _qty())).context["field"]
        == "time_in_force"
    )


def test_market_order_forbids_prices() -> None:
    assert (
        _refusal(_price_order(OrderType.MARKET, limit_price=_price())).context["field"]
        == "limit_price"
    )
    assert (
        _refusal(_price_order(OrderType.MARKET, stop_price=_price())).context["field"]
        == "stop_price"
    )


def test_limit_order_requires_limit_price_only() -> None:
    assert is_ok(_price_order(OrderType.LIMIT, limit_price=_price()))
    assert _refusal(_price_order(OrderType.LIMIT)).context["field"] == "limit_price"
    assert (
        _refusal(_price_order(OrderType.LIMIT, limit_price=_price(), stop_price=_price())).context[
            "field"
        ]
        == "stop_price"
    )


def test_stop_order_requires_stop_price() -> None:
    assert is_ok(_price_order(OrderType.STOP, stop_price=_price()))
    assert _refusal(_price_order(OrderType.STOP)).context["field"] == "stop_price"


def test_stop_limit_order_requires_both_prices() -> None:
    assert is_ok(_price_order(OrderType.STOP_LIMIT, limit_price=_price(), stop_price=_price()))
    assert (
        _refusal(_price_order(OrderType.STOP_LIMIT, limit_price=_price())).context["field"]
        == "stop_price"
    )


def test_order_parameters_prices_must_share_instrument() -> None:
    refusal = _refusal(
        OrderParameters.try_create(
            OrderType.STOP_LIMIT,
            TimeInForce.DAY,
            _qty(),
            limit_price=_price(symbol="EURUSD"),
            stop_price=_ok(Price.try_create(1_10000, _instrument("GBPUSD"), 5)),
        )
    )
    assert refusal.context["field"] == "instrument"


def test_order_parameters_reject_non_delta_protective_stop() -> None:
    refusal = _refusal(
        OrderParameters.try_create(
            OrderType.MARKET, TimeInForce.DAY, _qty(), protective_stop_distance=_price()
        )
    )
    assert refusal.context["field"] == "protective_stop_distance"


def test_order_parameters_reject_non_price() -> None:
    refusal = _refusal(
        OrderParameters.try_create(OrderType.LIMIT, TimeInForce.DAY, _qty(), limit_price=110000)
    )
    assert refusal.context["field"] == "price"


def _price_order(order_type: OrderType, **kwargs: object) -> Result[OrderParameters]:
    return OrderParameters.try_create(order_type, TimeInForce.DAY, _qty(), **kwargs)


# =====================================================================================
# Shared stream-identity validation
# =====================================================================================


def test_command_refuses_account_not_belonging_to_venue() -> None:
    other = _ok(VenueId.try_create("venue-other"))
    foreign_account = _ok(Account.try_create("acct-001", other, AccountRole.DEMO))
    refusal = _refusal(
        Command.place_order(_venue(), foreign_account, _SESSION_EPOCH, 1, _order_params())
    )
    assert refusal.context["field"] == "account"


def test_command_refuses_blank_session_epoch() -> None:
    refusal = _refusal(Command.place_order(_venue(), _account(), "  ", 1, _order_params()))
    assert refusal.context["field"] == "session_epoch"


def test_command_refuses_bad_ordinal() -> None:
    assert (
        _refusal(
            Command.place_order(_venue(), _account(), _SESSION_EPOCH, -1, _order_params())
        ).context["field"]
        == "ordering_ordinal"
    )
    assert (
        _refusal(
            Command.place_order(_venue(), _account(), _SESSION_EPOCH, True, _order_params())
        ).context["field"]
        == "ordering_ordinal"
    )


def test_command_refuses_bad_venue_and_account() -> None:
    assert (
        _refusal(
            Command.place_order("venue", _account(), _SESSION_EPOCH, 1, _order_params())
        ).context["field"]
        == "venue_id"
    )
    assert (
        _refusal(Command.place_order(_venue(), "acct", _SESSION_EPOCH, 1, _order_params())).context[
            "field"
        ]
        == "account"
    )


def test_command_stream_property_names_the_pair() -> None:
    stream = _place_order().command_stream
    assert stream["venue_id"] == "venue-ctrader-demo"
    assert stream["account_id"] == "acct-001"


# =====================================================================================
# AC2 — the four-outcome law; denied-locally is an outcome; observation + journal
# =====================================================================================


def test_four_outcome_law_is_exactly_four() -> None:
    assert {outcome.value for outcome in FOUR_OUTCOME_LAW} == {
        "accepted-by-venue",
        "rejected-by-venue",
        "denied-locally",
        "UNKNOWN",
    }
    assert SubmissionOutcome.PARTIALLY_EXECUTED not in FOUR_OUTCOME_LAW


def test_accepted_resolves_and_mints_observation_and_journal() -> None:
    result = _ok(_resolver().accepted(_place_order(), receive_instant=_instant()))
    assert result.outcome is SubmissionOutcome.ACCEPTED_BY_VENUE
    assert result.outcome in FOUR_OUTCOME_LAW
    assert result.observation.outcome is SubmissionOutcome.ACCEPTED_BY_VENUE
    assert result.observation.receive_instant == _instant()
    assert result.journal_event.event_type == "command.place_order.accepted-by-venue"
    assert result.journal_event.command_fp1 == result.command_fp1
    assert is_success(result.outcome)


def test_denied_locally_is_an_outcome_never_a_refusal() -> None:
    result = _ok(
        _resolver().denied_locally(
            _place_order(), reason="kill line breached", receive_instant=_instant()
        )
    )
    assert result.outcome is SubmissionOutcome.DENIED_LOCALLY
    assert result.outcome in FOUR_OUTCOME_LAW
    assert result.observation.local_reason == "kill line breached"
    assert result.journal_event.event_type == "command.place_order.denied-locally"
    assert not is_success(result.outcome)


def test_denied_locally_requires_a_reason() -> None:
    refusal = _refusal(
        _resolver().denied_locally(_place_order(), reason="  ", receive_instant=_instant())
    )
    assert refusal.context["field"] == "reason"


def test_every_outcome_mints_one_observation_and_one_journal_event() -> None:
    resolver = _resolver()
    results = [
        _ok(resolver.accepted(_place_order(), receive_instant=_instant())),
        _ok(resolver.denied_locally(_place_order(), reason="blocked", receive_instant=_instant())),
        _ok(
            resolver.venue_error(
                _place_order(), venue_code="ORDER_REJECTED", receive_instant=_instant()
            )
        ),
        _ok(
            resolver.transport_unknown(
                _place_order(),
                trigger=UnknownTrigger.TIMEOUT,
                monotonic_elapsed=_duration(),
                receive_instant=_instant(),
                submission_deadline=_instant(_DEADLINE_NS),
            )
        ),
    ]
    for result in results:
        assert result.observation.command_fp1 == result.command_fp1
        assert result.journal_event.outcome is result.outcome
        assert result.journal_event.event_type == journal_event_type(result.kind, result.outcome)


def test_resolver_requires_a_declaration() -> None:
    assert _refusal(CommandOutcomeResolver.try_create(object())).context["field"] == "declaration"


def test_resolver_requires_a_command_and_receive_instant() -> None:
    assert (
        _refusal(_resolver().accepted(object(), receive_instant=_instant())).context["field"]
        == "command"
    )
    assert (
        _refusal(_resolver().accepted(_place_order(), receive_instant=object())).context["field"]
        == "receive_instant"
    )


def test_command_observation_is_occurrence_only_no_fp1_identity() -> None:
    result = _ok(_resolver().accepted(_place_order(), receive_instant=_instant()))
    assert not hasattr(result.observation, "fp1_identity")


# =====================================================================================
# AC3 — transport → UNKNOWN (a state); venue error → rejected only where declared
# =====================================================================================


def test_transport_unknown_is_a_state_with_full_observation() -> None:
    result = _ok(
        _resolver().transport_unknown(
            _place_order(),
            trigger=UnknownTrigger.DISCONNECT,
            monotonic_elapsed=_duration(),
            receive_instant=_instant(),
            submission_deadline=_instant(_DEADLINE_NS),
        )
    )
    assert result.outcome is SubmissionOutcome.UNKNOWN
    observation = result.observation
    assert observation.unknown_trigger is UnknownTrigger.DISCONNECT
    assert observation.monotonic_elapsed == _duration()
    assert observation.receive_instant == _instant()
    assert observation.submission_deadline == _instant(_DEADLINE_NS)


def test_all_three_transport_triggers_resolve_unknown() -> None:
    resolver = _resolver()
    for trigger in (
        UnknownTrigger.TIMEOUT,
        UnknownTrigger.TRANSPORT_ERROR,
        UnknownTrigger.DISCONNECT,
    ):
        result = _ok(
            resolver.transport_unknown(
                _place_order(),
                trigger=trigger,
                monotonic_elapsed=_duration(),
                receive_instant=_instant(),
                submission_deadline=_instant(_DEADLINE_NS),
            )
        )
        assert result.outcome is SubmissionOutcome.UNKNOWN


def test_a_timeout_is_never_read_as_a_rejection() -> None:
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
    assert result.outcome is not SubmissionOutcome.REJECTED_BY_VENUE


def test_transport_unknown_requires_deadline_trigger_and_elapsed() -> None:
    resolver = _resolver()
    bad_deadline = _refusal(
        resolver.transport_unknown(
            _place_order(),
            trigger=UnknownTrigger.TIMEOUT,
            monotonic_elapsed=_duration(),
            receive_instant=_instant(),
            submission_deadline=object(),
        )
    )
    assert bad_deadline.context["field"] == "submission_deadline"
    bad_trigger = _refusal(
        resolver.transport_unknown(
            _place_order(),
            trigger="gremlin",
            monotonic_elapsed=_duration(),
            receive_instant=_instant(),
            submission_deadline=_instant(_DEADLINE_NS),
        )
    )
    assert bad_trigger.context["field"] == "trigger"
    bad_elapsed = _refusal(
        resolver.transport_unknown(
            _place_order(),
            trigger=UnknownTrigger.TIMEOUT,
            monotonic_elapsed=object(),
            receive_instant=_instant(),
            submission_deadline=_instant(_DEADLINE_NS),
        )
    )
    assert bad_elapsed.context["field"] == "monotonic_elapsed"


def test_venue_error_rejects_only_where_the_table_declares_it() -> None:
    resolver = _resolver()
    rejected = _ok(
        resolver.venue_error(
            _place_order(), venue_code="ORDER_REJECTED", receive_instant=_instant()
        )
    )
    assert rejected.outcome is SubmissionOutcome.REJECTED_BY_VENUE
    assert rejected.observation.venue_code == "ORDER_REJECTED"


def test_venue_error_declared_unknown_class_resolves_unknown() -> None:
    result = _ok(
        _resolver().venue_error(_place_order(), venue_code="THROTTLED", receive_instant=_instant())
    )
    assert result.outcome is SubmissionOutcome.UNKNOWN


def test_unmapped_venue_error_is_unknown_fail_closed() -> None:
    result = _ok(
        _resolver().venue_error(_place_order(), venue_code="GHOST_CODE", receive_instant=_instant())
    )
    assert result.outcome is SubmissionOutcome.UNKNOWN


def test_venue_error_requires_a_code() -> None:
    refusal = _refusal(
        _resolver().venue_error(_place_order(), venue_code="  ", receive_instant=_instant())
    )
    assert refusal.context["field"] == "venue_code"


# =====================================================================================
# AC4 — command identity is the record fp1; command-id-binding; idempotency; collision
# =====================================================================================


def test_command_identity_is_its_fp1() -> None:
    fp = _ok(_place_order().fingerprint())
    assert isinstance(fp, Fingerprint)
    assert fp.value.startswith("fp1:sha256:")


def test_identical_commands_share_identity() -> None:
    assert _ok(_place_order(ordinal=7).fingerprint()) == _ok(_place_order(ordinal=7).fingerprint())


def test_differing_content_yields_different_identity() -> None:
    assert _ok(_place_order(ordinal=7).fingerprint()) != _ok(_cancel_order(ordinal=7).fingerprint())
    assert _ok(_place_order(ordinal=7).fingerprint()) != _ok(_place_order(ordinal=8).fingerprint())


def test_command_fp1_identity_omits_absent_kind_fields() -> None:
    content = _place_order().fp1_identity()
    assert content["command_kind"] == "place_order"
    assert "order_parameters" in content
    assert "close_scope" not in content
    assert "protection_amendment" not in content


def test_command_id_mapping_flag_is_read_from_declaration() -> None:
    assert _ok(command_id_mapping_is_injective_total(_declaration(injective_total=True))) is True
    assert _ok(command_id_mapping_is_injective_total(_declaration(injective_total=False))) is False


def test_command_id_mapping_flag_refuses_non_declaration() -> None:
    assert (
        _refusal(command_id_mapping_is_injective_total(object())).context["field"] == "declaration"
    )


def test_injective_total_mapping_needs_no_durable_binding() -> None:
    sink = _RecordingSink()
    registry = _ok(CommandIdBindingRegistry.try_create(sink))
    outcome = _ok(
        registry.bind_before_submission(
            _place_order(), venue_client_id="cid-1", injective_total=True
        )
    )
    assert outcome is BindingOutcome.MAPPING_INJECTIVE_TOTAL
    assert sink.records == []


def test_non_injective_mapping_persists_binding_before_submission() -> None:
    sink = _RecordingSink()
    registry = _ok(CommandIdBindingRegistry.try_create(sink))
    outcome = _ok(
        registry.bind_before_submission(
            _place_order(), venue_client_id="cid-1", injective_total=False
        )
    )
    assert outcome is BindingOutcome.BOUND
    assert len(sink.records) == 1
    record = sink.records[0]
    assert isinstance(record, CommandIdBinding)
    assert record.venue_client_id == "cid-1"


def test_re_presenting_the_same_command_is_idempotent() -> None:
    sink = _RecordingSink()
    registry = _ok(CommandIdBindingRegistry.try_create(sink))
    command = _place_order()
    first = _ok(
        registry.bind_before_submission(command, venue_client_id="cid-1", injective_total=False)
    )
    second = _ok(
        registry.bind_before_submission(command, venue_client_id="cid-1", injective_total=False)
    )
    assert first is BindingOutcome.BOUND
    assert second is BindingOutcome.IDEMPOTENT
    assert len(sink.records) == 1


def test_differing_content_under_reused_identity_is_refused_and_alarmed() -> None:
    sink = _RecordingSink()
    registry = _ok(CommandIdBindingRegistry.try_create(sink))
    _ok(
        registry.bind_before_submission(
            _place_order(ordinal=1), venue_client_id="cid-1", injective_total=False
        )
    )
    refusal = _refusal(
        registry.bind_before_submission(
            _place_order(ordinal=2), venue_client_id="cid-1", injective_total=False
        )
    )
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.context["alarm"] is True
    assert refusal.context["field"] == "command_id_binding"


def test_binding_storage_failure_is_surfaced_and_blocks_submission() -> None:
    registry = _ok(CommandIdBindingRegistry.try_create(_FailingSink()))
    refusal = _refusal(
        registry.bind_before_submission(
            _place_order(), venue_client_id="cid-1", injective_total=False
        )
    )
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    # The binding did not land, so nothing was recorded and the command is not submitted.
    assert registry.binding_for("cid-1") is None


def test_binding_registry_validates_inputs() -> None:
    assert _refusal(CommandIdBindingRegistry.try_create(object())).context["field"] == "record_sink"
    registry = _ok(CommandIdBindingRegistry.try_create(_RecordingSink()))
    assert (
        _refusal(
            registry.bind_before_submission(
                object(), venue_client_id="cid-1", injective_total=False
            )
        ).context["field"]
        == "command"
    )
    assert (
        _refusal(
            registry.bind_before_submission(
                _place_order(), venue_client_id="cid-1", injective_total="no"
            )
        ).context["field"]
        == "injective_total"
    )
    assert (
        _refusal(
            registry.bind_before_submission(
                _place_order(), venue_client_id="  ", injective_total=False
            )
        ).context["field"]
        == "venue_client_id"
    )


def test_binding_for_reads_recorded_binding() -> None:
    registry = _ok(CommandIdBindingRegistry.try_create(_RecordingSink()))
    _ok(
        registry.bind_before_submission(
            _place_order(), venue_client_id="cid-1", injective_total=False
        )
    )
    assert registry.binding_for("cid-1") is not None
    assert registry.binding_for("cid-2") is None
    assert registry.binding_for(object()) is None


def test_command_id_binding_fp1_identity() -> None:
    binding = CommandIdBinding(
        venue_client_id="cid-1",
        command_fp1=_ok(_place_order().fingerprint()),
        account_id="acct-001",
        session_epoch=_SESSION_EPOCH,
    )
    content = binding.fp1_identity()
    assert content["class"] == "command-id-binding"
    assert content["venue_client_id"] == "cid-1"


# =====================================================================================
# AC5 — amend_protection is risk-non-increasing per protection side
# =====================================================================================


def test_stop_side_risk_non_increasing_change_is_accepted() -> None:
    amendment = _ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP, _delta(80), _price(), original_risk_distance=_delta(100)
        )
    )
    assert amendment.protection_side is ProtectionSide.STOP
    assert amendment.original_risk_distance is not None


def test_stop_side_equal_distance_is_accepted() -> None:
    assert is_ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP, _delta(100), _price(), original_risk_distance=_delta(100)
        )
    )


def test_stop_side_risk_increasing_change_is_refused() -> None:
    refusal = _refusal(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP, _delta(120), _price(), original_risk_distance=_delta(100)
        )
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "new_distance"


def test_stop_side_requires_the_frozen_original_risk_distance() -> None:
    refusal = _refusal(ProtectionAmendment.try_create(ProtectionSide.STOP, _delta(80), _price()))
    assert refusal.context["field"] == "original_risk_distance"


def test_target_side_has_no_contract_risk_test() -> None:
    amendment = _ok(ProtectionAmendment.try_create(ProtectionSide.TARGET, _delta(500), _price()))
    assert amendment.protection_side is ProtectionSide.TARGET
    assert amendment.original_risk_distance is None


def test_target_side_refuses_a_stop_side_original_risk_distance() -> None:
    refusal = _refusal(
        ProtectionAmendment.try_create(
            ProtectionSide.TARGET, _delta(500), _price(), original_risk_distance=_delta(100)
        )
    )
    assert refusal.context["field"] == "original_risk_distance"


def test_amend_protection_validates_side_and_types() -> None:
    assert (
        _refusal(
            ProtectionAmendment.try_create(
                "trailing", _delta(80), _price(), original_risk_distance=_delta(100)
            )
        ).context["field"]
        == "protection_side"
    )
    assert (
        _refusal(
            ProtectionAmendment.try_create(
                ProtectionSide.STOP, 80, _price(), original_risk_distance=_delta(100)
            )
        ).context["field"]
        == "new_distance"
    )
    assert (
        _refusal(
            ProtectionAmendment.try_create(
                ProtectionSide.STOP, _delta(80), 110000, original_risk_distance=_delta(100)
            )
        ).context["field"]
        == "reference_price"
    )


def test_amend_protection_instrument_consistency() -> None:
    other = _ok(PriceDelta.try_create(80, _instrument("GBPUSD"), 5))
    assert (
        _refusal(
            ProtectionAmendment.try_create(
                ProtectionSide.STOP, other, _price(), original_risk_distance=_delta(100)
            )
        ).context["field"]
        == "instrument"
    )
    stop_mismatch = _refusal(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP,
            _delta(80),
            _price(),
            original_risk_distance=_ok(PriceDelta.try_create(100, _instrument("GBPUSD"), 5)),
        )
    )
    assert stop_mismatch.context["field"] == "original_risk_distance"


def test_amend_protection_command_requires_typed_amendment_and_subject() -> None:
    assert (
        _refusal(
            Command.amend_protection(
                _venue(), _account(), _SESSION_EPOCH, 4, {"stop": 1}, "pos-xyz"
            )
        ).context["field"]
        == "protection_amendment"
    )
    assert (
        _refusal(
            Command.amend_protection(
                _venue(), _account(), _SESSION_EPOCH, 4, _stop_amendment(), " "
            )
        ).context["field"]
        == "subject_reference"
    )


def test_amend_protection_command_carries_the_amendment() -> None:
    command = _amend()
    assert command.kind is CommandKind.AMEND_PROTECTION
    assert command.protection_amendment is not None
    assert command.subject_reference == "pos-xyz"
    assert "protection_amendment" in command.fp1_identity()


# =====================================================================================
# AC6 — compound command: parent outcome is the meet of its children
# =====================================================================================


def test_meet_all_accepted_is_accepted() -> None:
    outcome = _ok(
        meet_outcomes([SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.ACCEPTED_BY_VENUE])
    )
    assert outcome is SubmissionOutcome.ACCEPTED_BY_VENUE


def test_any_child_unknown_makes_the_parent_unknown() -> None:
    outcome = _ok(
        meet_outcomes(
            [
                SubmissionOutcome.ACCEPTED_BY_VENUE,
                SubmissionOutcome.REJECTED_BY_VENUE,
                SubmissionOutcome.UNKNOWN,
            ]
        )
    )
    assert outcome is SubmissionOutcome.UNKNOWN


def test_any_child_rejected_makes_the_parent_partially_executed() -> None:
    outcome = _ok(
        meet_outcomes([SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.REJECTED_BY_VENUE])
    )
    assert outcome is SubmissionOutcome.PARTIALLY_EXECUTED
    assert not is_success(outcome)


def test_a_denied_local_child_also_makes_the_parent_partially_executed() -> None:
    outcome = _ok(
        meet_outcomes([SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.DENIED_LOCALLY])
    )
    assert outcome is SubmissionOutcome.PARTIALLY_EXECUTED


def test_partially_executed_is_never_a_success() -> None:
    assert not is_success(SubmissionOutcome.PARTIALLY_EXECUTED)
    assert is_success(SubmissionOutcome.ACCEPTED_BY_VENUE)


def test_meet_refuses_empty_and_non_sequence_and_bad_child() -> None:
    assert _refusal(meet_outcomes([])).context["field"] == "child_outcomes"
    assert _refusal(meet_outcomes("accepted-by-venue")).context["field"] == "child_outcomes"
    assert (
        _refusal(meet_outcomes([SubmissionOutcome.ACCEPTED_BY_VENUE, "not-an-outcome"])).context[
            "field"
        ]
        == "child_outcomes"
    )


def test_meet_refuses_partially_executed_as_a_child() -> None:
    # A child is a single submission; partially-executed is a compound-parent outcome only.
    refusal = _refusal(
        meet_outcomes([SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.PARTIALLY_EXECUTED])
    )
    assert refusal.context["field"] == "child_outcomes"


def test_meet_accepts_string_child_tokens() -> None:
    assert (
        _ok(meet_outcomes(["accepted-by-venue", "accepted-by-venue"]))
        is SubmissionOutcome.ACCEPTED_BY_VENUE
    )


def test_compound_fan_out_derives_distinct_child_identities() -> None:
    compound = _ok(CompoundCommand.fan_out(_close_position(), [0, 1, 2]))
    assert len(compound.children) == 3
    identities = [child.identity.value for child in compound.children]
    assert len(set(identities)) == 3
    assert all(child.identity != compound.parent_fp1 for child in compound.children)


def test_compound_parent_outcome_is_the_meet() -> None:
    compound = _ok(CompoundCommand.fan_out(_close_position(), [0, 1]))
    accepted = _ok(
        compound.parent_outcome(
            [SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.ACCEPTED_BY_VENUE]
        )
    )
    assert accepted is SubmissionOutcome.ACCEPTED_BY_VENUE
    partial = _ok(
        compound.parent_outcome(
            [SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.REJECTED_BY_VENUE]
        )
    )
    assert partial is SubmissionOutcome.PARTIALLY_EXECUTED


def test_compound_fan_out_needs_at_least_two_distinct_ordinals() -> None:
    assert _refusal(CompoundCommand.fan_out(_close_position(), [0])).context["field"] == "ordinals"
    assert (
        _refusal(CompoundCommand.fan_out(_close_position(), [1, 1])).context["field"] == "ordinals"
    )


def test_compound_fan_out_validates_parent_and_ordinals() -> None:
    assert _refusal(CompoundCommand.fan_out(object(), [0, 1])).context["field"] == "parent"
    assert _refusal(CompoundCommand.fan_out(_close_position(), "01")).context["field"] == "ordinals"
    assert (
        _refusal(CompoundCommand.fan_out(_close_position(), [0, -1])).context["field"] == "ordinals"
    )


def test_parent_outcome_needs_one_outcome_per_child() -> None:
    compound = _ok(CompoundCommand.fan_out(_close_position(), [0, 1]))
    assert (
        _refusal(compound.parent_outcome([SubmissionOutcome.ACCEPTED_BY_VENUE])).context["field"]
        == "child_outcomes"
    )
    assert _refusal(compound.parent_outcome("x")).context["field"] == "child_outcomes"


def test_derive_child_identity_is_deterministic_and_distinct() -> None:
    parent_fp = _ok(_close_position().fingerprint())
    assert _ok(derive_child_identity(parent_fp, 0)) == _ok(derive_child_identity(parent_fp, 0))
    assert _ok(derive_child_identity(parent_fp, 0)) != _ok(derive_child_identity(parent_fp, 1))


def test_derive_child_identity_validates_inputs() -> None:
    assert _refusal(derive_child_identity("not-a-fp", 0)).context["field"] == "parent_fp1"
    parent_fp = _ok(_close_position().fingerprint())
    assert _refusal(derive_child_identity(parent_fp, -1)).context["field"] == "ordinal"


def test_journal_event_type_mapping() -> None:
    assert (
        journal_event_type(CommandKind.CLOSE_ALL, SubmissionOutcome.UNKNOWN)
        == "command.close_all.UNKNOWN"
    )


def test_journal_event_for_outcome_helper() -> None:
    fp = _ok(_place_order().fingerprint())
    event = JournalEvent.for_outcome(
        fp, CommandKind.CANCEL_ORDER, SubmissionOutcome.REJECTED_BY_VENUE
    )
    assert event.event_type == "command.cancel_order.rejected-by-venue"
    assert event.command_fp1 == fp
