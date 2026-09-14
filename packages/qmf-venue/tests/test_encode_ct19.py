"""Story 31.3 — ProtoOA encode of the five CT-19 kinds (no network)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

import tomllib
from google.protobuf import descriptor_pb2
from qmf.core import (
    Account,
    AccountRole,
    Instrument,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    is_ok,
)
from qmf.venue import (
    PROTO_OA_AMEND_POSITION_SLTP_REQ,
    PROTO_OA_CANCEL_ORDER_REQ,
    PROTO_OA_CLOSE_POSITION_REQ,
    PROTO_OA_NEW_ORDER_REQ,
    CapabilityDeclaration,
    CapabilityField,
    CapabilityFieldName,
    Command,
    CommandKind,
    EncodedCommand,
    ErrorMap,
    ErrorMapRow,
    OrderParameters,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    ProtoArtifact,
    SubmissionOutcomeClass,
    TimeInForce,
    compile_descriptor_set,
    decode_framed_payload,
    encode_amend_protection,
    encode_cancel_order,
    encode_close_all,
    encode_close_position,
    encode_command,
    encode_place_order,
)
from qmf.venue.proto import SPOTWARE_PROTO_PACKAGE, CompiledProto

T = TypeVar("T")

_SESSION_EPOCH = "session-epoch-encode"
_PROTO_TAG = 91
_DIGEST = "sha256:" + "a" * 64
_ROOT = Path(__file__).resolve().parents[3]
_VENUE_SRC = _ROOT / "packages" / "qmf-venue" / "src" / "qmf" / "venue"
_BANNED = ("twisted", "ctrader_open_api", "openapipy", "spotware", "ccxt", "hummingbot")
_PACKAGE = "protooa"
_INT64 = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
_INT32 = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
_UINT32 = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
_BYTES = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
_STRING = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
_DOUBLE = descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE
_OPTIONAL = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
_MAX_SOURCE_BYTES = 1 << 20


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: object) -> TypedRefusal:
    assert isinstance(result, TypedRefusal), result
    return result


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account(venue: VenueId | None = None) -> Account:
    anchor = venue if venue is not None else _venue()
    return _ok(Account.try_create("acct-001", anchor, AccountRole.DEMO))


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return _ok(Instrument.try_create(_venue(), symbol))


def _price(value: int = 1_10000, scale: int = 5) -> Price:
    return _ok(Price.try_create(value, _instrument(), scale))


def _delta(value: int = 100, scale: int = 5) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), scale))


def _qty(value: int = 100, scale: int = 2) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


def _add_field(message: object, name: str, number: int, typ: int) -> None:
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = _OPTIONAL
    field.type = typ


def _add_message(file_proto: object, name: str, fields: tuple[tuple[str, int, int], ...]) -> None:
    message = file_proto.message_type.add()
    message.name = name
    for field_name, number, typ in fields:
        _add_field(message, field_name, number, typ)


def _descriptor_set_bytes(*, limit_price_double: bool = False) -> bytes:
    file_set = descriptor_pb2.FileDescriptorSet()
    file_proto = file_set.file.add()
    file_proto.name = "protooa.proto"
    file_proto.package = _PACKAGE
    file_proto.syntax = "proto3"
    _add_message(
        file_proto,
        "ProtoMessage",
        (("payloadType", 1, _UINT32), ("payload", 2, _BYTES), ("clientMsgId", 3, _STRING)),
    )
    limit_type = _DOUBLE if limit_price_double else _INT64
    _add_message(
        file_proto,
        "ProtoOANewOrderReq",
        (
            ("ctidTraderAccountId", 1, _INT64),
            ("symbolId", 2, _INT64),
            ("orderType", 3, _INT32),
            ("tradeSide", 4, _INT32),
            ("volume", 5, _INT64),
            ("limitPrice", 6, limit_type),
            ("stopPrice", 7, _INT64),
            ("timeInForce", 8, _INT32),
            ("clientOrderId", 17, _STRING),
            ("relativeStopLoss", 18, _INT64),
        ),
    )
    _add_message(
        file_proto,
        "ProtoOACancelOrderReq",
        (("ctidTraderAccountId", 1, _INT64), ("orderId", 2, _INT64)),
    )
    _add_message(
        file_proto,
        "ProtoOAClosePositionReq",
        (
            ("ctidTraderAccountId", 1, _INT64),
            ("positionId", 2, _INT64),
            ("volume", 3, _INT64),
            ("symbolId", 4, _INT64),
        ),
    )
    _add_message(
        file_proto,
        "ProtoOAAmendPositionSLTPReq",
        (
            ("ctidTraderAccountId", 1, _INT64),
            ("positionId", 2, _INT64),
            ("stopLoss", 3, _INT64),
            ("takeProfit", 4, _INT64),
        ),
    )
    return file_set.SerializeToString()


def _compiled(*, limit_price_double: bool = False) -> CompiledProto:
    return _ok(
        compile_descriptor_set(
            _descriptor_set_bytes(limit_price_double=limit_price_double),
            package_name=SPOTWARE_PROTO_PACKAGE,
            release_tag=_PROTO_TAG,
        )
    )


def _static(name: CapabilityFieldName, value: object) -> CapabilityField:
    return _ok(CapabilityField.static(name, value))


def _measured(name: CapabilityFieldName) -> CapabilityField:
    return _ok(CapabilityField.measured(name))


def _roster(
    *,
    acknowledgement_modes: object | None = None,
    order_types: object | None = None,
    command_scopes: object | None = None,
    protection_primitives: object | None = None,
) -> list[CapabilityField]:
    modes = (
        acknowledgement_modes
        if acknowledgement_modes is not None
        else {
            "place_order": "explicit-event",
            "cancel_order": "explicit-event",
            "close_position": "explicit-event",
            "close_all": "explicit-event",
            "amend_protection": "explicit-event",
        }
    )
    types = order_types if order_types is not None else ["market", "limit", "stop", "stop-limit"]
    scopes = (
        command_scopes
        if command_scopes is not None
        else ["account", "account-binding", "instrument-within-binding"]
    )
    primitives = (
        protection_primitives
        if protection_primitives is not None
        else ["suspend-new", "drain", "close_all"]
    )
    return [
        _static(CapabilityFieldName.MARKET_DATA_KINDS, ["tick", "bar", "depth"]),
        _static(CapabilityFieldName.ORDER_PARAMETER_SUBSET, {"order_types": types}),
        _static(CapabilityFieldName.COMMAND_SCOPES, scopes),
        _static(CapabilityFieldName.ACKNOWLEDGEMENT_MODES, modes),
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
        _static(CapabilityFieldName.PROTECTION_PRIMITIVES, primitives),
        _measured(CapabilityFieldName.SETTLEMENT_CURRENCY),
        _measured(CapabilityFieldName.MARGIN_SURFACE),
        _measured(CapabilityFieldName.VALUE_FACTOR_METADATA),
        _static(CapabilityFieldName.RECONCILIATION_LOOKBACK, "do-not-default"),
        _measured(CapabilityFieldName.PROTECTION_CAPABILITIES),
        _static(CapabilityFieldName.COMMAND_ID_MAPPING, {"injective_total": True}),
        _static(CapabilityFieldName.FLOAT_TARGET_SCALES, {"execution_price": "declared-digits"}),
        _static(CapabilityFieldName.VERIFICATION_SUITE, ["spot-timestamp-unit"]),
    ]


def _declaration(**kwargs: object) -> CapabilityDeclaration:
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
        CapabilityDeclaration.try_create(
            "ctrader-adapter-1.0.0", artifact, error_map, _roster(**kwargs)
        )
    )


def _order_params(order_type: OrderType = OrderType.MARKET, **kwargs: object) -> OrderParameters:
    return _ok(
        OrderParameters.try_create(order_type, TimeInForce.GOOD_TILL_CANCEL, _qty(), **kwargs)
    )


def _place(params: OrderParameters | None = None) -> Command:
    return _ok(
        Command.place_order(_venue(), _account(), _SESSION_EPOCH, 1, params or _order_params())
    )


def _cancel(subject: str = "1001") -> Command:
    return _ok(Command.cancel_order(_venue(), _account(), _SESSION_EPOCH, 2, subject))


def _close_pos(scope: str = "instrument-within-binding", subject: str = "2002") -> Command:
    return _ok(Command.close_position(_venue(), _account(), _SESSION_EPOCH, 3, scope, subject))


def _close_all(scope: str = "account", subject: str = "acct-001") -> Command:
    return _ok(Command.close_all(_venue(), _account(), _SESSION_EPOCH, 4, scope, subject))


def _amend(subject: str = "2002") -> Command:
    amendment = _ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP, _delta(80), _price(), original_risk_distance=_delta(100)
        )
    )
    return _ok(
        Command.amend_protection(_venue(), _account(), _SESSION_EPOCH, 5, amendment, subject)
    )


def _inner(compiled: CompiledProto, encoded: EncodedCommand) -> object:
    envelope = _ok(compiled.decode("protooa.ProtoMessage", encoded.envelope))
    assert envelope.payloadType == encoded.payload_type  # type: ignore[attr-defined]
    assert envelope.payload == encoded.payload  # type: ignore[attr-defined]
    inner = _ok(compiled.decode(encoded.message_name, encoded.payload))
    framed = _ok(decode_framed_payload(encoded.frame))
    assert framed == encoded.envelope
    return inner


def _imported_modules(path: Path) -> set[str]:
    resolved = path.resolve()
    assert not path.is_symlink(), resolved
    assert resolved.is_file() and resolved.is_relative_to(_ROOT), resolved
    assert resolved.stat().st_size <= _MAX_SOURCE_BYTES, resolved
    tree = ast.parse(resolved.read_text(encoding="utf-8"), filename=str(resolved))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


# --- well-formed encode of each kind ----------------------------------------


def test_place_order_encodes_protooa_new_order_req() -> None:
    compiled = _compiled()
    encoded = _ok(
        encode_place_order(
            _place(),
            compiled=compiled,
            declaration=_declaration(),
            ctid_trader_account_id=123456,
            symbol_id=1,
            trade_side="buy",
        )
    )
    assert encoded.kind is CommandKind.PLACE_ORDER
    assert encoded.payload_type == PROTO_OA_NEW_ORDER_REQ
    inner = _inner(compiled, encoded)
    assert inner.ctidTraderAccountId == 123456  # type: ignore[attr-defined]
    assert inner.symbolId == 1  # type: ignore[attr-defined]
    assert inner.orderType == 1  # type: ignore[attr-defined]
    assert inner.tradeSide == 1  # type: ignore[attr-defined]
    assert inner.volume == 100  # type: ignore[attr-defined]


def test_cancel_order_encodes_protooa_cancel_order_req() -> None:
    compiled = _compiled()
    encoded = _ok(
        encode_cancel_order(
            _cancel(),
            compiled=compiled,
            declaration=_declaration(),
            ctid_trader_account_id=123456,
        )
    )
    assert encoded.payload_type == PROTO_OA_CANCEL_ORDER_REQ
    inner = _inner(compiled, encoded)
    assert inner.orderId == 1001  # type: ignore[attr-defined]


def test_close_position_encodes_protooa_close_position_req() -> None:
    compiled = _compiled()
    encoded = _ok(
        encode_close_position(
            _close_pos(),
            compiled=compiled,
            declaration=_declaration(),
            ctid_trader_account_id=123456,
            volume=_qty(250),
        )
    )
    assert encoded.payload_type == PROTO_OA_CLOSE_POSITION_REQ
    inner = _inner(compiled, encoded)
    assert inner.positionId == 2002  # type: ignore[attr-defined]
    assert inner.volume == 250  # type: ignore[attr-defined]


def test_close_all_encodes_protooa_close_envelope() -> None:
    compiled = _compiled()
    encoded = _ok(
        encode_close_all(
            _close_all(),
            compiled=compiled,
            declaration=_declaration(),
            ctid_trader_account_id=123456,
        )
    )
    assert encoded.kind is CommandKind.CLOSE_ALL
    assert encoded.payload_type == PROTO_OA_CLOSE_POSITION_REQ
    inner = _inner(compiled, encoded)
    assert inner.ctidTraderAccountId == 123456  # type: ignore[attr-defined]


def test_amend_protection_encodes_protooa_amend_sltp() -> None:
    compiled = _compiled()
    encoded = _ok(
        encode_amend_protection(
            _amend(),
            compiled=compiled,
            declaration=_declaration(),
            ctid_trader_account_id=123456,
        )
    )
    assert encoded.payload_type == PROTO_OA_AMEND_POSITION_SLTP_REQ
    inner = _inner(compiled, encoded)
    assert inner.positionId == 2002  # type: ignore[attr-defined]
    assert inner.stopLoss == 1_10080  # type: ignore[attr-defined]


def test_encode_command_dispatches_each_kind() -> None:
    compiled = _compiled()
    declaration = _declaration()
    kinds = (
        encode_command(
            _place(),
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=1,
            symbol_id=1,
            trade_side="sell",
        ),
        encode_command(
            _cancel(), compiled=compiled, declaration=declaration, ctid_trader_account_id=1
        ),
        encode_command(
            _close_pos(),
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=1,
            volume=_qty(),
        ),
        encode_command(
            _close_all(), compiled=compiled, declaration=declaration, ctid_trader_account_id=1
        ),
        encode_command(
            _amend(), compiled=compiled, declaration=declaration, ctid_trader_account_id=1
        ),
    )
    assert [_ok(item).kind for item in kinds] == [
        CommandKind.PLACE_ORDER,
        CommandKind.CANCEL_ORDER,
        CommandKind.CLOSE_POSITION,
        CommandKind.CLOSE_ALL,
        CommandKind.AMEND_PROTECTION,
    ]


# --- missing CT-18 capability -----------------------------------------------


def test_place_order_refuses_undeclared_order_type() -> None:
    refusal = _refusal(
        encode_place_order(
            _place(_order_params(OrderType.LIMIT, limit_price=_price())),
            compiled=_compiled(),
            declaration=_declaration(order_types=["market"]),
            ctid_trader_account_id=1,
            symbol_id=1,
            trade_side="buy",
        )
    )
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "order_type"


def test_kind_omitted_from_acknowledgement_modes_is_unsupported() -> None:
    declaration = _declaration(acknowledgement_modes={"place_order": "explicit-event"})
    compiled = _compiled()
    for command, encoder, kwargs in (
        (_cancel(), encode_cancel_order, {}),
        (_close_pos(), encode_close_position, {"volume": _qty()}),
        (_close_all(), encode_close_all, {}),
        (_amend(), encode_amend_protection, {}),
    ):
        refusal = _refusal(
            encoder(
                command,
                compiled=compiled,
                declaration=declaration,
                ctid_trader_account_id=1,
                **kwargs,
            )
        )
        assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
        assert refusal.context["capability"] == "acknowledgement_modes"
        assert refusal.context["field"] == "acknowledgement_modes"


def test_close_scope_not_declared_is_unsupported() -> None:
    refusal = _refusal(
        encode_close_position(
            _close_pos(scope="instrument-within-binding"),
            compiled=_compiled(),
            declaration=_declaration(command_scopes=["account"]),
            ctid_trader_account_id=1,
            volume=_qty(),
        )
    )
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "close_scope"


def test_close_all_missing_primitive_is_unsupported() -> None:
    refusal = _refusal(
        encode_close_all(
            _close_all(),
            compiled=_compiled(),
            declaration=_declaration(protection_primitives=["suspend-new", "drain"]),
            ctid_trader_account_id=1,
        )
    )
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["capability"] == "protection_primitives"


# --- AD-7 exact integer scales; float refused --------------------------------


def test_float_ctid_is_refused() -> None:
    refusal = _refusal(
        encode_place_order(
            _place(),
            compiled=_compiled(),
            declaration=_declaration(),
            ctid_trader_account_id=1.5,
            symbol_id=1,
            trade_side="buy",
        )
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert "float" in str(refusal.context["reason"])


def test_float_volume_is_refused() -> None:
    refusal = _refusal(
        encode_close_position(
            _close_pos(),
            compiled=_compiled(),
            declaration=_declaration(),
            ctid_trader_account_id=1,
            volume=1.25,
        )
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert "float" in str(refusal.context["reason"])


def test_double_limit_price_field_is_refused() -> None:
    refusal = _refusal(
        encode_place_order(
            _place(_order_params(OrderType.LIMIT, limit_price=_price())),
            compiled=_compiled(limit_price_double=True),
            declaration=_declaration(),
            ctid_trader_account_id=1,
            symbol_id=1,
            trade_side="buy",
        )
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert "float" in str(refusal.context["reason"])


# --- hygiene ----------------------------------------------------------------


def test_encode_module_bans_companion_sdks() -> None:
    violations: list[str] = []
    for path in sorted(_VENUE_SRC.rglob("*.py")):
        for imported in _imported_modules(path):
            low = imported.lower()
            root_name = low.split(".", 1)[0]
            if root_name in _BANNED or any(token in low for token in _BANNED):
                violations.append(f"{path.name}:{imported}")
    assert violations == []


def test_protobuf_runtime_remains_pinned_7_36_0() -> None:
    data = tomllib.loads(
        (_ROOT / "packages" / "qmf-venue" / "pyproject.toml").read_text(encoding="utf-8")
    )
    deps = list(data["project"]["dependencies"])
    assert "protobuf==7.36.0" in deps
    assert not any(item.startswith("protobuf==7.36.1") for item in deps)
