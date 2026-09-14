"""Story 31.4 — ready live submit hands a Command to the encode path."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

import pytest
from google.protobuf import descriptor_pb2
from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Duration,
    Instant,
    Instrument,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    VenueId,
    World,
    is_ok,
)
from qmf.venue.capabilities import ErrorMap
from qmf.venue.commands import (
    Command,
    CommandKind,
    CompoundCommand,
    OrderParameters,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    SubmissionOutcome,
    TimeInForce,
)
from qmf.venue.encode import (
    PROTO_OA_AMEND_POSITION_SLTP_REQ,
    PROTO_OA_CANCEL_ORDER_REQ,
    PROTO_OA_CLOSE_POSITION_REQ,
    PROTO_OA_NEW_ORDER_REQ,
)
from qmf.venue.proto import SPOTWARE_PROTO_PACKAGE, compile_descriptor_set
from qmn.venue import (
    ConformanceDouble,
    LiveCTraderClient,
    VenueClientKind,
    compare_port_contract_shapes,
    compound_command_acceptance_blocked,
    conformance_measured_facts,
    ctrader_static_declaration,
    run_port_contract_suite,
    submit_not_ready_refusal,
)
from qmn.venue.verify import VenueFactVerifier

T = TypeVar("T")

_BOOT = "boot-epoch-submit-31-4"
_WALL_NS = 1_724_000_000 * 1_000_000_000
_SESSION = "session-epoch-submit"
_PROTO_TAG = 91
_PACKAGE = "protooa"
_INT64 = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
_INT32 = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
_UINT32 = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
_BYTES = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
_STRING = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
_OPTIONAL = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: object):
    from qmf.core import TypedRefusal

    assert isinstance(result, TypedRefusal), result
    return result


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(
        Account.try_create("acct-001", venue if venue is not None else _venue(), AccountRole.DEMO)
    )


def _clock() -> DataDrivenClock:
    walls = tuple(_ok(Instant.try_create(_WALL_NS + i * 1_000_000)) for i in range(24))
    monos = tuple(5_000_000_000 + i * 1_000_000 for i in range(24))
    return DataDrivenClock(boot_epoch_id=_BOOT, wall_instants=walls, monotonic_ns=monos)


def compiled_protooa():
    file_set = descriptor_pb2.FileDescriptorSet()
    file_proto = file_set.file.add()
    file_proto.name = "protooa.proto"
    file_proto.package = _PACKAGE
    file_proto.syntax = "proto3"

    def add_message(
        name: str,
        fields: tuple[tuple[str, int, descriptor_pb2.FieldDescriptorProto.Type.ValueType], ...],
    ) -> None:
        message = file_proto.message_type.add()
        message.name = name
        for field_name, number, typ in fields:
            field = message.field.add()
            field.name = field_name
            field.number = number
            field.label = _OPTIONAL
            field.type = typ

    add_message(
        "ProtoMessage",
        (("payloadType", 1, _UINT32), ("payload", 2, _BYTES), ("clientMsgId", 3, _STRING)),
    )
    add_message(
        "ProtoOANewOrderReq",
        (
            ("ctidTraderAccountId", 1, _INT64),
            ("symbolId", 2, _INT64),
            ("orderType", 3, _INT32),
            ("tradeSide", 4, _INT32),
            ("volume", 5, _INT64),
            ("limitPrice", 6, _INT64),
            ("stopPrice", 7, _INT64),
            ("timeInForce", 8, _INT32),
            ("clientOrderId", 17, _STRING),
            ("relativeStopLoss", 18, _INT64),
        ),
    )
    add_message(
        "ProtoOACancelOrderReq",
        (("ctidTraderAccountId", 1, _INT64), ("orderId", 2, _INT64)),
    )
    add_message(
        "ProtoOAClosePositionReq",
        (
            ("ctidTraderAccountId", 1, _INT64),
            ("positionId", 2, _INT64),
            ("volume", 3, _INT64),
            ("symbolId", 4, _INT64),
        ),
    )
    add_message(
        "ProtoOAAmendPositionSLTPReq",
        (
            ("ctidTraderAccountId", 1, _INT64),
            ("positionId", 2, _INT64),
            ("stopLoss", 3, _INT64),
            ("takeProfit", 4, _INT64),
        ),
    )
    return _ok(
        compile_descriptor_set(
            file_set.SerializeToString(),
            package_name=SPOTWARE_PROTO_PACKAGE,
            release_tag=_PROTO_TAG,
        )
    )


def _client() -> LiveCTraderClient:
    return _ok(
        LiveCTraderClient.try_create(
            World.LIVE,
            _venue(),
            clock=_clock(),
            error_map=_ok(ErrorMap.try_create(1, ())),
            declared_lookback=_ok(Duration.try_create(1_000_000_000)),
        )
    )


def _bind_encode(client: LiveCTraderClient) -> None:
    _ok(
        client.bind_encode_context(
            compiled=compiled_protooa(),
            ctid_trader_account_id=42,
            symbol_id=1,
            trade_side="buy",
            volume=_ok(Quantity.try_create(100, "lot", 2)),
        )
    )


def _verify(
    client: LiveCTraderClient,
    *,
    acknowledgement_modes: dict[str, str] | None = None,
) -> None:
    account = client.account
    assert account is not None
    decl = _ok(ctrader_static_declaration(acknowledgement_modes=acknowledgement_modes))
    verifier = _ok(VenueFactVerifier.try_create(decl, client.venue_id, account))
    received = _ok(Instant.try_create(_WALL_NS))
    bundle = _ok(conformance_measured_facts(received_at=received))
    outcome = _ok(verifier.verify(bundle, received_at=received))
    _ok(client.accept_verification(outcome))
    _ok(client.verify_capabilities())


def _ready(
    client: LiveCTraderClient,
    *,
    acknowledgement_modes: dict[str, str] | None = None,
) -> None:
    _ok(client.open_session(_account(client.venue_id)))
    _verify(client, acknowledgement_modes=acknowledgement_modes)
    _bind_encode(client)


def _instrument(venue: VenueId) -> Instrument:
    return _ok(Instrument.try_create(venue, "EURUSD"))


def _qty() -> Quantity:
    return _ok(Quantity.try_create(100, "lot", 2))


def _delta(venue: VenueId, value: int = 80) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(venue), 5))


def _price(venue: VenueId) -> Price:
    return _ok(Price.try_create(1_10000, _instrument(venue), 5))


def _place(client: LiveCTraderClient, ordinal: int, *, with_stop: bool) -> Command:
    kwargs: dict[str, object] = {}
    if with_stop:
        kwargs["protective_stop_distance"] = _delta(client.venue_id)
    params = _ok(
        OrderParameters.try_create(OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, _qty(), **kwargs)
    )
    return _ok(
        Command.place_order(client.venue_id, _account(client.venue_id), _SESSION, ordinal, params)
    )


def _commands(client: LiveCTraderClient) -> dict[CommandKind, Command]:
    venue = client.venue_id
    account = _account(venue)
    amendment = _ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP,
            _delta(venue, 80),
            _price(venue),
            original_risk_distance=_delta(venue, 100),
        )
    )
    return {
        CommandKind.PLACE_ORDER: _place(client, 1, with_stop=True),
        CommandKind.CANCEL_ORDER: _ok(Command.cancel_order(venue, account, _SESSION, 2, "1001")),
        CommandKind.CLOSE_POSITION: _ok(
            Command.close_position(venue, account, _SESSION, 3, "instrument-within-binding", "2002")
        ),
        CommandKind.CLOSE_ALL: _ok(
            Command.close_all(venue, account, _SESSION, 4, "account", "acct-001")
        ),
        CommandKind.AMEND_PROTECTION: _ok(
            Command.amend_protection(venue, account, _SESSION, 5, amendment, "2002")
        ),
    }


def _encode_rows(client: LiveCTraderClient) -> list[Mapping[str, object]]:
    return [row for row in _ok(client.observations()) if row.get("kind") == "encode-handoff"]


def test_unreadiness_is_unavailable_and_does_not_encode_or_open_a_socket() -> None:
    client = _client()
    _bind_encode(client)
    command = _ok(
        Command.cancel_order(client.venue_id, _account(client.venue_id), _SESSION, 1, "1001")
    )
    expected = submit_not_ready_refusal()
    refused = _refusal(client.submit(command))
    assert refused.category is expected.category
    assert refused.retryability is expected.retryability
    assert refused.context["field"] == "readiness"
    assert refused.after_condition_descriptor == expected.after_condition_descriptor
    assert _encode_rows(client) == []
    assert client.commands_retried == 0

    _ok(client.open_session(_account(client.venue_id)))
    still = _refusal(client.submit(command))
    assert still.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert _encode_rows(client) == []


def test_compound_submit_keeps_ftr02_block() -> None:
    client = _client()
    _ready(client)
    parent = _ok(
        Command.cancel_order(client.venue_id, _account(client.venue_id), _SESSION, 1, "1001")
    )
    compound = _ok(CompoundCommand.fan_out(parent, (0, 1)))
    refused = _refusal(client.submit(compound))
    blocked = compound_command_acceptance_blocked()
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["ftr"] == "FTR-02"
    assert refused.context["reason"] == blocked.context["reason"]
    assert _encode_rows(client) == []


def test_omitted_kind_is_the_remaining_single_kind_unsupported_capability() -> None:
    client = _client()
    _ok(client.open_session(_account(client.venue_id)))
    _verify(client, acknowledgement_modes={"place_order": "explicit-event"})
    _bind_encode(client)
    cancel = _ok(
        Command.cancel_order(client.venue_id, _account(client.venue_id), _SESSION, 1, "1001")
    )
    refused = _refusal(client.submit(cancel))
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["capability"] == "acknowledgement_modes"
    assert refused.context["requested"] == CommandKind.CANCEL_ORDER.value
    assert "sensing" not in str(refused.context.get("reason", "")).lower()
    assert _encode_rows(client) == []


def test_unprotected_place_order_refused_before_encode() -> None:
    client = _client()
    _ready(client)
    bare = _place(client, 1, with_stop=False)
    refused = _refusal(client.submit(bare))
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["field"] in {"protective_stop_distance", "protective_stop_forms"}
    assert _encode_rows(client) == []


def test_supported_kinds_encode_handoff_without_inventing_accept_or_retry() -> None:
    client = _client()
    _ready(client)
    payload_types = {
        CommandKind.PLACE_ORDER: PROTO_OA_NEW_ORDER_REQ,
        CommandKind.CANCEL_ORDER: PROTO_OA_CANCEL_ORDER_REQ,
        CommandKind.CLOSE_POSITION: PROTO_OA_CLOSE_POSITION_REQ,
        CommandKind.CLOSE_ALL: PROTO_OA_CLOSE_POSITION_REQ,
        CommandKind.AMEND_PROTECTION: PROTO_OA_AMEND_POSITION_SLTP_REQ,
    }
    for kind, command in _commands(client).items():
        submitted = _ok(client.submit(command))
        assert submitted.outcome is SubmissionOutcome.UNKNOWN
        assert submitted.outcome is not SubmissionOutcome.REJECTED_BY_VENUE
        assert submitted.observation.unknown_trigger is None
        assert client.commands_retried == 0
        assert client.auto_retry_enabled is False
        again = _ok(client.submit(command))
        assert again.outcome is SubmissionOutcome.UNKNOWN
        assert client.commands_retried == 0
        rows = [row for row in _encode_rows(client) if row.get("command_kind") == kind.value]
        assert rows
        assert rows[-1]["encoded"] is True
        assert rows[-1]["auto_retry"] is False
        assert rows[-1]["socket_opened"] is False
        assert rows[-1]["payload_type"] == payload_types[kind]


def test_sensing_only_reason_is_gone() -> None:
    client = _client()
    _ready(client)
    command = _ok(
        Command.cancel_order(client.venue_id, _account(client.venue_id), _SESSION, 1, "1001")
    )
    submitted = _ok(client.submit(command))
    assert submitted.outcome is SubmissionOutcome.UNKNOWN
    reason_blob = str(_ok(client.observations()))
    assert "sensing/recording only" not in reason_blob
    assert "Story 24.3" not in reason_blob


def test_live_and_double_agree_on_refusal_versus_encode_handoff() -> None:
    live = _client()
    _ready(live)
    double_venue = _ok(VenueId.try_create("conformance:31-4"))
    double = _ok(ConformanceDouble.try_create(World.LIVE, double_venue))
    live_shape = dict(_ok(run_port_contract_suite(live)))
    double_shape = dict(_ok(run_port_contract_suite(double)))
    live_submit = live_shape["submit_shape"]
    double_submit = double_shape["submit_shape"]
    assert isinstance(live_submit, Mapping)
    assert isinstance(double_submit, Mapping)
    assert live_submit["form"] == "encode-handoff"
    assert double_submit["form"] == "encode-handoff"
    assert live_submit == double_submit
    live_kinds = cast("Mapping[str, object]", live_shape["kind_submit_shapes"])
    double_kinds = cast("Mapping[str, object]", double_shape["kind_submit_shapes"])
    assert set(live_kinds) == {member.value for member in CommandKind}
    assert dict(live_kinds) == dict(double_kinds)
    parity = _ok(
        compare_port_contract_shapes(
            {VenueClientKind.CONFORMANCE: double_shape, VenueClientKind.CTRADER: live_shape}
        )
    )
    assert parity["parity"] is True


@pytest.mark.live
def test_credentialed_live_submit_stays_separately_tagged() -> None:
    """Credentialed live submit is not a Story 31.4 credential-free gate."""
    pytest.skip("Spotware sandbox token not a Story 31.4 prerequisite")
