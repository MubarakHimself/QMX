"""ProtoOA encode of the five CT-19 command kinds (Story 31.3).

Encode symbols for ``place_order``, ``cancel_order``, ``close_position``,
``close_all``, and ``amend_protection`` live here — a sibling of
:class:`~qmf.venue.connection.ConnectionManager`, imported only by ``qmn.venue``.
They emit length-prefixed ProtoOA ``ProtoMessage`` frames for Open API port 5035
through the in-house :class:`~qmf.venue.proto.CompiledProto` (tag 91). Zero
Spotware SDK, CCXT, Hummingbot, or Twisted code runs.

Money, price, and volume cross only declared exact-integer scale boundaries
(AD-7): volumes as cents (scale 2), prices as the market-data wire scale
(scale 5). A binary float without a declared rounding rule is refused. A
compiled field typed ``double``/``float`` is the same refusal — this encoder
never writes a wire float.

An undeclared CT-18 capability (command kind, order type, close scope, close-all
primitive) is an ``unsupported capability`` refusal naming that capability.
Compound commands are not encoded here; ``qmn.venue.live`` keeps the FTR-02
block (GAP-0059).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from qmf.core import (
    Ok,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.venue.capabilities import CapabilityDeclaration, CapabilityFieldName
from qmf.venue.commands import Command, CommandKind, OrderType, ProtectionSide, TimeInForce
from qmf.venue.connection import encode_framed_payload
from qmf.venue.ctrader import MARKET_DATA_WIRE_SCALE_EXPONENT
from qmf.venue.proto import CompiledProto

__all__ = [
    "PRICE_WIRE_SCALE_EXPONENT",
    "PROTO_OA_AMEND_POSITION_SLTP_REQ",
    "PROTO_OA_CANCEL_ORDER_REQ",
    "PROTO_OA_CLOSE_POSITION_REQ",
    "PROTO_OA_NEW_ORDER_REQ",
    "VOLUME_WIRE_SCALE_EXPONENT",
    "EncodedCommand",
    "encode_amend_protection",
    "encode_cancel_order",
    "encode_close_all",
    "encode_close_position",
    "encode_command",
    "encode_place_order",
]

# Spotware ProtoOA payloadType integers (Open API 5035). Not registry values:
# they are the pinned protocol's discriminant, parallel to CTRADER_OPEN_API_PORT.
PROTO_OA_NEW_ORDER_REQ: Final[int] = 2106
PROTO_OA_CANCEL_ORDER_REQ: Final[int] = 2108
PROTO_OA_AMEND_POSITION_SLTP_REQ: Final[int] = 2110
PROTO_OA_CLOSE_POSITION_REQ: Final[int] = 2111

# Volumes are cents on the wire (DEC-0135). Prices use the market-data uint64
# 1/100000 scale so encode never writes a binary float (AD-7).
VOLUME_WIRE_SCALE_EXPONENT: Final[int] = 2
PRICE_WIRE_SCALE_EXPONENT: Final[int] = MARKET_DATA_WIRE_SCALE_EXPONENT

_FLOAT_WIRE_TYPES: Final[frozenset[int]] = frozenset(
    {FieldDescriptor.TYPE_DOUBLE, FieldDescriptor.TYPE_FLOAT}
)

_ORDER_TYPE_WIRE: Final[Mapping[OrderType, int]] = {
    OrderType.MARKET: 1,
    OrderType.LIMIT: 2,
    OrderType.STOP: 3,
    OrderType.STOP_LIMIT: 6,
}
_TIF_WIRE: Final[Mapping[TimeInForce, int]] = {
    TimeInForce.GOOD_TILL_DATE: 1,
    TimeInForce.GOOD_TILL_CANCEL: 2,
    TimeInForce.IMMEDIATE_OR_CANCEL: 3,
    TimeInForce.FILL_OR_KILL: 4,
}
_TRADE_SIDE_WIRE: Final[Mapping[str, int]] = {"buy": 1, "sell": 2}

_PLACE_ORDER_NAMES: Final[tuple[str, ...]] = (
    "protooa.ProtoOANewOrderReq",
    "ProtoOANewOrderReq",
)
_CANCEL_ORDER_NAMES: Final[tuple[str, ...]] = (
    "protooa.ProtoOACancelOrderReq",
    "ProtoOACancelOrderReq",
)
_CLOSE_POSITION_NAMES: Final[tuple[str, ...]] = (
    "protooa.ProtoOAClosePositionReq",
    "ProtoOAClosePositionReq",
)
_AMEND_NAMES: Final[tuple[str, ...]] = (
    "protooa.ProtoOAAmendPositionSLTPReq",
    "ProtoOAAmendPositionSLTPReq",
)
_ENVELOPE_NAMES: Final[tuple[str, ...]] = ("protooa.ProtoMessage", "ProtoMessage")


@dataclass(frozen=True, slots=True)
class EncodedCommand:
    """One well-formed ProtoOA encode of a CT-19 command (Story 31.3).

    ``payload`` is the inner ProtoOA request; ``envelope`` is the ``ProtoMessage``
    wrapping it; ``frame`` is the length-prefixed Open API 5035 wire image.
    """

    kind: CommandKind
    message_name: str
    payload_type: int
    payload: bytes
    envelope: bytes
    frame: bytes
    client_msg_id: str


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unsupported(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


def _float_refused(field_name: str, value: object) -> TypedRefusal:
    return _invalid(
        field_name,
        "a float crossing without a declared rounding rule is refused; "
        "money, price, and volume encode only at declared exact-integer scale "
        "boundaries (AD-7)",
        given=repr(value),
    )


# --- scalar helpers ---------------------------------------------------------


def _as_plain_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _require_int(field_name: str, value: object, *, minimum: int = 0) -> Result[int]:
    if isinstance(value, float):
        return _float_refused(field_name, value)
    parsed = _as_plain_int(value)
    if parsed is None or parsed < minimum:
        return _invalid(
            field_name,
            "a venue-native identifier is a non-negative exact integer",
            given=repr(value),
        )
    return Ok(parsed)


def _optional_int(field_name: str, value: object) -> Result[int | None]:
    if value is None:
        return Ok(None)
    parsed = _require_int(field_name, value)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value)


def _venue_native_id(value: object) -> int | None:
    if isinstance(value, float):
        return None
    parsed = _as_plain_int(value)
    if parsed is not None and parsed >= 0:
        return parsed
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _to_wire_scale(value: int, from_scale: int, to_scale: int, field_name: str) -> Result[int]:
    """Lossless rescale of an exact integer onto a declared wire scale."""
    if from_scale == to_scale:
        return Ok(value)
    if from_scale < to_scale:
        return Ok(value * (10 ** (to_scale - from_scale)))
    divisor = 10 ** (from_scale - to_scale)
    if value % divisor != 0:
        return _invalid(
            field_name,
            "the exact value is not representable at the declared integer wire scale",
            from_scale=from_scale,
            to_scale=to_scale,
        )
    return Ok(value // divisor)


def _quantity_wire(quantity: Quantity, field_name: str) -> Result[int]:
    return _to_wire_scale(quantity.value, quantity.scale, VOLUME_WIRE_SCALE_EXPONENT, field_name)


def _price_wire(price: Price, field_name: str) -> Result[int]:
    return _to_wire_scale(price.value, price.scale, PRICE_WIRE_SCALE_EXPONENT, field_name)


def _delta_wire(delta: PriceDelta, field_name: str) -> Result[int]:
    scaled = _to_wire_scale(delta.value, delta.scale, PRICE_WIRE_SCALE_EXPONENT, field_name)
    if is_refusal(scaled):
        return scaled
    return Ok(abs(scaled.value))


# --- compiled proto helpers -------------------------------------------------


def _require_compiled(compiled: object) -> Result[CompiledProto]:
    if not isinstance(compiled, CompiledProto):
        return _invalid(
            "compiled",
            "encode consumes an in-house CompiledProto; qmn.venue.live must not compile proto",
            given=type(compiled).__name__,
        )
    return Ok(compiled)


def _require_declaration(declaration: object) -> Result[CapabilityDeclaration]:
    if not isinstance(declaration, CapabilityDeclaration):
        return _invalid(
            "declaration",
            "encode reads CT-18 capabilities from a CapabilityDeclaration",
            given=type(declaration).__name__,
        )
    return Ok(declaration)


def _require_command(command: object, expected: CommandKind) -> Result[Command]:
    if not isinstance(command, Command):
        return _invalid("command", "encode requires a CT-19 Command", given=type(command).__name__)
    if command.kind is not expected:
        return _invalid(
            "command",
            "this encode symbol is typed per CT-19 kind",
            expected=expected.value,
            given=command.kind.value,
        )
    return Ok(command)


def _message_class(
    compiled: CompiledProto, names: tuple[str, ...]
) -> Result[tuple[str, type[Message]]]:
    for name in names:
        resolved = compiled.message_class(name)
        if is_ok(resolved):
            return Ok((name, resolved.value))
    return _unsupported(
        "full_name",
        "the pinned proto release declares no such ProtoOA message",
        requested=list(names),
        capability="venue_protocol_artifact",
    )


def _field_of(message: Message, name: str) -> object | None:
    return message.DESCRIPTOR.fields_by_name.get(name)


def _field_wire_type(field: object) -> int | None:
    raw = getattr(field, "type", None)
    return raw if isinstance(raw, int) and not isinstance(raw, bool) else None


def _set_int(
    message: Message, names: Sequence[str], value: int, *, required: bool = True
) -> Result[bool]:
    for name in names:
        field = _field_of(message, name)
        if field is None:
            continue
        if _field_wire_type(field) in _FLOAT_WIRE_TYPES:
            return _float_refused(name, value)
        setattr(message, name, value)
        return Ok(True)
    if required:
        return _unsupported(
            "field",
            "the compiled ProtoOA message has no matching integer field",
            requested=list(names),
            capability="venue_protocol_artifact",
        )
    return Ok(False)


def _set_str(
    message: Message, names: Sequence[str], value: str, *, required: bool = False
) -> Result[bool]:
    for name in names:
        field = _field_of(message, name)
        if field is None:
            continue
        if _field_wire_type(field) in _FLOAT_WIRE_TYPES:
            return _float_refused(name, value)
        setattr(message, name, value)
        return Ok(True)
    if required:
        return _unsupported(
            "field",
            "the compiled ProtoOA message has no matching string field",
            requested=list(names),
            capability="venue_protocol_artifact",
        )
    return Ok(False)


def _set_bytes(
    message: Message, names: Sequence[str], value: bytes, *, required: bool = True
) -> Result[bool]:
    for name in names:
        if _field_of(message, name) is None:
            continue
        setattr(message, name, value)
        return Ok(True)
    if required:
        return _unsupported(
            "field",
            "the compiled ProtoOA message has no matching bytes field",
            requested=list(names),
            capability="venue_protocol_artifact",
        )
    return Ok(False)


# --- CT-18 gates ------------------------------------------------------------


def _declared_kinds(declaration: CapabilityDeclaration) -> Result[frozenset[str]]:
    raw = declaration.static_value(CapabilityFieldName.ACKNOWLEDGEMENT_MODES)
    if is_refusal(raw):
        return raw
    value = raw.value
    if not isinstance(value, Mapping):
        return _invalid(
            "acknowledgement_modes",
            "acknowledgement_modes is a mapping of command kind to acknowledgement mode",
            given=type(value).__name__,
            capability="acknowledgement_modes",
        )
    kinds = frozenset(str(key) for key in cast("Mapping[object, object]", value))
    return Ok(kinds)


def _require_kind_declared(declaration: CapabilityDeclaration, kind: CommandKind) -> Result[bool]:
    kinds = _declared_kinds(declaration)
    if is_refusal(kinds):
        return kinds
    if kind.value not in kinds.value:
        return _unsupported(
            "acknowledgement_modes",
            "the CT-18 declaration does not name this command kind",
            requested=kind.value,
            declared=sorted(kinds.value),
            capability="acknowledgement_modes",
        )
    return Ok(True)


def _require_close_all_primitive(declaration: CapabilityDeclaration) -> Result[bool]:
    raw = declaration.static_value(CapabilityFieldName.PROTECTION_PRIMITIVES)
    if is_refusal(raw):
        return raw
    value = raw.value
    tokens: tuple[str, ...]
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "protection_primitives",
            "protection_primitives is a sequence of primitive tokens",
            given=type(value).__name__,
            capability="protection_primitives",
        )
    tokens = tuple(str(item) for item in cast("Sequence[object]", value))
    if "close_all" not in tokens:
        return _unsupported(
            "protection_primitives",
            "the CT-18 declaration does not name the close_all primitive",
            requested="close_all",
            declared=list(tokens),
            capability="protection_primitives",
        )
    return Ok(True)


def _client_msg_id(command: Command, supplied: object) -> Result[str]:
    if supplied is not None:
        if not isinstance(supplied, str) or supplied.strip() == "":
            return _invalid(
                "client_msg_id",
                "clientMsgId is a non-empty string when supplied",
                given=repr(supplied),
            )
        return Ok(supplied.strip())
    fp = command.fingerprint()
    if is_refusal(fp):  # pragma: no cover - a valid Command always fingerprints
        return fp
    return Ok(fp.value.value)


def _finish(
    *,
    command: Command,
    compiled: CompiledProto,
    inner_name: str,
    payload_type: int,
    payload: bytes,
    client_msg_id: str,
) -> Result[EncodedCommand]:
    envelope_cls = _message_class(compiled, _ENVELOPE_NAMES)
    if is_refusal(envelope_cls):
        return envelope_cls
    envelope_name, envelope_type = envelope_cls.value
    _ = envelope_name
    envelope = envelope_type()
    set_type = _set_int(envelope, ("payloadType", "payload_type"), payload_type)
    if is_refusal(set_type):
        return set_type
    set_payload = _set_bytes(envelope, ("payload",), payload)
    if is_refusal(set_payload):
        return set_payload
    set_id = _set_str(envelope, ("clientMsgId", "client_msg_id"), client_msg_id)
    if is_refusal(set_id):
        return set_id
    envelope_bytes = envelope.SerializeToString()
    framed = encode_framed_payload(envelope_bytes)
    if is_refusal(framed):
        return framed
    return Ok(
        EncodedCommand(
            kind=command.kind,
            message_name=inner_name,
            payload_type=payload_type,
            payload=payload,
            envelope=envelope_bytes,
            frame=framed.value,
            client_msg_id=client_msg_id,
        )
    )


# --- per-kind encoders ------------------------------------------------------


def encode_place_order(
    command: object,
    *,
    compiled: object,
    declaration: object,
    ctid_trader_account_id: object,
    symbol_id: object,
    trade_side: object,
    client_msg_id: object = None,
) -> Result[EncodedCommand]:
    """Encode a ``place_order`` Command as ProtoOANewOrderReq (payloadType 2106)."""
    resolved = _require_command(command, CommandKind.PLACE_ORDER)
    if is_refusal(resolved):
        return resolved
    proto = _require_compiled(compiled)
    if is_refusal(proto):
        return proto
    decl = _require_declaration(declaration)
    if is_refusal(decl):
        return decl
    kind_ok = _require_kind_declared(decl.value, CommandKind.PLACE_ORDER)
    if is_refusal(kind_ok):
        return kind_ok
    params = resolved.value.order_parameters
    if params is None:
        return _invalid("order_parameters", "place_order carries typed OrderParameters")
    admitted = decl.value.order_parameter(order_type=params.order_type)
    if is_refusal(admitted):
        return admitted
    subset = decl.value.static_value(CapabilityFieldName.ORDER_PARAMETER_SUBSET)
    if is_ok(subset):
        raw_subset: object = subset.value
        if isinstance(raw_subset, Mapping):
            body = cast("Mapping[str, object]", raw_subset)
            tif_tokens = body.get("time_in_force")
            has_tif = isinstance(tif_tokens, Sequence) and not isinstance(
                tif_tokens, (str, bytes)
            )
            if has_tif and tuple(cast("Sequence[object]", tif_tokens)):
                tif_ok = decl.value.order_parameter(time_in_force=params.time_in_force)
                if is_refusal(tif_ok):
                    return tif_ok
    ctid = _require_int("ctid_trader_account_id", ctid_trader_account_id, minimum=1)
    if is_refusal(ctid):
        return ctid
    symbol = _require_int("symbol_id", symbol_id, minimum=1)
    if is_refusal(symbol):
        return symbol
    if isinstance(trade_side, float):
        return _float_refused("trade_side", trade_side)
    side_token = trade_side.strip().lower() if isinstance(trade_side, str) else None
    side_wire = _TRADE_SIDE_WIRE.get(side_token or "")
    if side_wire is None:
        return _invalid(
            "trade_side",
            "place_order encodes ProtoOA tradeSide buy | sell",
            given=repr(trade_side),
        )
    type_wire = _ORDER_TYPE_WIRE.get(params.order_type)
    if type_wire is None:  # pragma: no cover - OrderType is closed
        return _unsupported(
            "order_type",
            "no ProtoOA orderType mapping for this order type",
            requested=params.order_type.value,
            capability="order_parameter_subset",
        )
    tif_wire = _TIF_WIRE.get(params.time_in_force)
    if tif_wire is None:
        return _unsupported(
            "time_in_force",
            "this time-in-force has no ProtoOA mapping",
            requested=params.time_in_force.value,
            capability="order_parameter_subset",
        )
    volume = _quantity_wire(params.quantity, "volume")
    if is_refusal(volume):
        return volume
    msg_id = _client_msg_id(resolved.value, client_msg_id)
    if is_refusal(msg_id):
        return msg_id
    inner = _message_class(proto.value, _PLACE_ORDER_NAMES)
    if is_refusal(inner):
        return inner
    name, cls = inner.value
    message = cls()
    writes: tuple[Result[bool], ...] = (
        _set_int(message, ("ctidTraderAccountId",), ctid.value),
        _set_int(message, ("symbolId",), symbol.value),
        _set_int(message, ("orderType",), type_wire),
        _set_int(message, ("tradeSide",), side_wire),
        _set_int(message, ("volume",), volume.value),
        _set_int(message, ("timeInForce",), tif_wire, required=False),
        _set_str(message, ("clientOrderId",), msg_id.value, required=False),
    )
    for write in writes:
        if is_refusal(write):
            return write
    if params.limit_price is not None:
        limit = _price_wire(params.limit_price, "limitPrice")
        if is_refusal(limit):
            return limit
        written = _set_int(message, ("limitPrice",), limit.value)
        if is_refusal(written):
            return written
    if params.stop_price is not None:
        stop = _price_wire(params.stop_price, "stopPrice")
        if is_refusal(stop):
            return stop
        written = _set_int(message, ("stopPrice",), stop.value)
        if is_refusal(written):
            return written
    if params.protective_stop_distance is not None:
        relative = _delta_wire(params.protective_stop_distance, "relativeStopLoss")
        if is_refusal(relative):
            return relative
        written = _set_int(message, ("relativeStopLoss",), relative.value, required=False)
        if is_refusal(written):
            return written
    return _finish(
        command=resolved.value,
        compiled=proto.value,
        inner_name=name,
        payload_type=PROTO_OA_NEW_ORDER_REQ,
        payload=message.SerializeToString(),
        client_msg_id=msg_id.value,
    )


def encode_cancel_order(
    command: object,
    *,
    compiled: object,
    declaration: object,
    ctid_trader_account_id: object,
    client_msg_id: object = None,
) -> Result[EncodedCommand]:
    """Encode a ``cancel_order`` Command as ProtoOACancelOrderReq (payloadType 2108)."""
    resolved = _require_command(command, CommandKind.CANCEL_ORDER)
    if is_refusal(resolved):
        return resolved
    proto = _require_compiled(compiled)
    if is_refusal(proto):
        return proto
    decl = _require_declaration(declaration)
    if is_refusal(decl):
        return decl
    kind_ok = _require_kind_declared(decl.value, CommandKind.CANCEL_ORDER)
    if is_refusal(kind_ok):
        return kind_ok
    ctid = _require_int("ctid_trader_account_id", ctid_trader_account_id, minimum=1)
    if is_refusal(ctid):
        return ctid
    if isinstance(resolved.value.subject_reference, float):
        return _float_refused("subject_reference", resolved.value.subject_reference)
    order_id = _venue_native_id(resolved.value.subject_reference)
    if order_id is None:
        return _invalid(
            "subject_reference",
            "cancel_order encodes a venue-native integer orderId",
            given=repr(resolved.value.subject_reference),
        )
    msg_id = _client_msg_id(resolved.value, client_msg_id)
    if is_refusal(msg_id):
        return msg_id
    inner = _message_class(proto.value, _CANCEL_ORDER_NAMES)
    if is_refusal(inner):
        return inner
    name, cls = inner.value
    message = cls()
    for write in (
        _set_int(message, ("ctidTraderAccountId",), ctid.value),
        _set_int(message, ("orderId",), order_id),
    ):
        if is_refusal(write):
            return write
    return _finish(
        command=resolved.value,
        compiled=proto.value,
        inner_name=name,
        payload_type=PROTO_OA_CANCEL_ORDER_REQ,
        payload=message.SerializeToString(),
        client_msg_id=msg_id.value,
    )


def encode_close_position(
    command: object,
    *,
    compiled: object,
    declaration: object,
    ctid_trader_account_id: object,
    volume: object = None,
    client_msg_id: object = None,
) -> Result[EncodedCommand]:
    """Encode a ``close_position`` Command as ProtoOAClosePositionReq (payloadType 2111)."""
    resolved = _require_command(command, CommandKind.CLOSE_POSITION)
    if is_refusal(resolved):
        return resolved
    proto = _require_compiled(compiled)
    if is_refusal(proto):
        return proto
    decl = _require_declaration(declaration)
    if is_refusal(decl):
        return decl
    kind_ok = _require_kind_declared(decl.value, CommandKind.CLOSE_POSITION)
    if is_refusal(kind_ok):
        return kind_ok
    if resolved.value.close_scope is None:
        return _invalid("close_scope", "close_position carries a typed close scope")
    scope = decl.value.close_scope(resolved.value.close_scope)
    if is_refusal(scope):
        return scope
    ctid = _require_int("ctid_trader_account_id", ctid_trader_account_id, minimum=1)
    if is_refusal(ctid):
        return ctid
    if isinstance(resolved.value.subject_reference, float):
        return _float_refused("subject_reference", resolved.value.subject_reference)
    position_id = _venue_native_id(resolved.value.subject_reference)
    if position_id is None:
        return _invalid(
            "subject_reference",
            "close_position encodes a venue-native integer positionId",
            given=repr(resolved.value.subject_reference),
        )
    if isinstance(volume, float):
        return _float_refused("volume", volume)
    wire_volume: int | None = None
    if volume is not None:
        if not isinstance(volume, Quantity):
            return _invalid(
                "volume",
                "close volume is an exact qmf-core Quantity; a binary float is refused",
                given=repr(volume),
            )
        scaled = _quantity_wire(volume, "volume")
        if is_refusal(scaled):
            return scaled
        wire_volume = scaled.value
    msg_id = _client_msg_id(resolved.value, client_msg_id)
    if is_refusal(msg_id):
        return msg_id
    inner = _message_class(proto.value, _CLOSE_POSITION_NAMES)
    if is_refusal(inner):
        return inner
    name, cls = inner.value
    message = cls()
    for write in (
        _set_int(message, ("ctidTraderAccountId",), ctid.value),
        _set_int(message, ("positionId",), position_id),
    ):
        if is_refusal(write):
            return write
    if wire_volume is not None:
        written = _set_int(message, ("volume",), wire_volume)
        if is_refusal(written):
            return written
    return _finish(
        command=resolved.value,
        compiled=proto.value,
        inner_name=name,
        payload_type=PROTO_OA_CLOSE_POSITION_REQ,
        payload=message.SerializeToString(),
        client_msg_id=msg_id.value,
    )


def encode_close_all(
    command: object,
    *,
    compiled: object,
    declaration: object,
    ctid_trader_account_id: object,
    symbol_id: object = None,
    client_msg_id: object = None,
) -> Result[EncodedCommand]:
    """Encode a ``close_all`` Command as a ProtoOA close-position envelope.

    Open API 5035 has no dedicated close-all payload type. The well-formed result is
    a ``ProtoOAClosePositionReq`` carrying the account (and optional symbol) after
    the CT-18 ``close_all`` primitive and close scope admit the command.
    """
    resolved = _require_command(command, CommandKind.CLOSE_ALL)
    if is_refusal(resolved):
        return resolved
    proto = _require_compiled(compiled)
    if is_refusal(proto):
        return proto
    decl = _require_declaration(declaration)
    if is_refusal(decl):
        return decl
    kind_ok = _require_kind_declared(decl.value, CommandKind.CLOSE_ALL)
    if is_refusal(kind_ok):
        return kind_ok
    primitive = _require_close_all_primitive(decl.value)
    if is_refusal(primitive):
        return primitive
    if resolved.value.close_scope is None:
        return _invalid("close_scope", "close_all carries a typed close scope")
    scope = decl.value.close_scope(resolved.value.close_scope)
    if is_refusal(scope):
        return scope
    ctid = _require_int("ctid_trader_account_id", ctid_trader_account_id, minimum=1)
    if is_refusal(ctid):
        return ctid
    symbol = _optional_int("symbol_id", symbol_id)
    if is_refusal(symbol):
        return symbol
    msg_id = _client_msg_id(resolved.value, client_msg_id)
    if is_refusal(msg_id):
        return msg_id
    inner = _message_class(proto.value, _CLOSE_POSITION_NAMES)
    if is_refusal(inner):
        return inner
    name, cls = inner.value
    message = cls()
    written = _set_int(message, ("ctidTraderAccountId",), ctid.value)
    if is_refusal(written):
        return written
    if symbol.value is not None:
        extra = _set_int(message, ("symbolId",), symbol.value, required=False)
        if is_refusal(extra):
            return extra
    return _finish(
        command=resolved.value,
        compiled=proto.value,
        inner_name=name,
        payload_type=PROTO_OA_CLOSE_POSITION_REQ,
        payload=message.SerializeToString(),
        client_msg_id=msg_id.value,
    )


def encode_amend_protection(
    command: object,
    *,
    compiled: object,
    declaration: object,
    ctid_trader_account_id: object,
    client_msg_id: object = None,
) -> Result[EncodedCommand]:
    """Encode ``amend_protection`` as ProtoOAAmendPositionSLTPReq (payloadType 2110)."""
    resolved = _require_command(command, CommandKind.AMEND_PROTECTION)
    if is_refusal(resolved):
        return resolved
    proto = _require_compiled(compiled)
    if is_refusal(proto):
        return proto
    decl = _require_declaration(declaration)
    if is_refusal(decl):
        return decl
    kind_ok = _require_kind_declared(decl.value, CommandKind.AMEND_PROTECTION)
    if is_refusal(kind_ok):
        return kind_ok
    amendment = resolved.value.protection_amendment
    if amendment is None:
        return _invalid(
            "protection_amendment", "amend_protection carries a typed ProtectionAmendment"
        )
    ctid = _require_int("ctid_trader_account_id", ctid_trader_account_id, minimum=1)
    if is_refusal(ctid):
        return ctid
    if isinstance(resolved.value.subject_reference, float):
        return _float_refused("subject_reference", resolved.value.subject_reference)
    position_id = _venue_native_id(resolved.value.subject_reference)
    if position_id is None:
        return _invalid(
            "subject_reference",
            "amend_protection encodes a venue-native integer positionId",
            given=repr(resolved.value.subject_reference),
        )
    level = amendment.reference_price.add(amendment.new_distance)
    if is_refusal(level):
        return level
    wire_level = _price_wire(level.value, "protection_level")
    if is_refusal(wire_level):
        return wire_level
    msg_id = _client_msg_id(resolved.value, client_msg_id)
    if is_refusal(msg_id):
        return msg_id
    inner = _message_class(proto.value, _AMEND_NAMES)
    if is_refusal(inner):
        return inner
    name, cls = inner.value
    message = cls()
    for write in (
        _set_int(message, ("ctidTraderAccountId",), ctid.value),
        _set_int(message, ("positionId",), position_id),
    ):
        if is_refusal(write):
            return write
    field = "stopLoss" if amendment.protection_side is ProtectionSide.STOP else "takeProfit"
    written = _set_int(message, (field,), wire_level.value)
    if is_refusal(written):
        return written
    return _finish(
        command=resolved.value,
        compiled=proto.value,
        inner_name=name,
        payload_type=PROTO_OA_AMEND_POSITION_SLTP_REQ,
        payload=message.SerializeToString(),
        client_msg_id=msg_id.value,
    )


def encode_command(
    command: object,
    *,
    compiled: object,
    declaration: object,
    ctid_trader_account_id: object,
    symbol_id: object = None,
    trade_side: object = None,
    volume: object = None,
    client_msg_id: object = None,
) -> Result[EncodedCommand]:
    """Dispatch a CT-19 Command onto the matching ProtoOA encode symbol."""
    if not isinstance(command, Command):
        return _invalid("command", "encode requires a CT-19 Command", given=type(command).__name__)
    if command.kind is CommandKind.PLACE_ORDER:
        return encode_place_order(
            command,
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=ctid_trader_account_id,
            symbol_id=symbol_id,
            trade_side=trade_side,
            client_msg_id=client_msg_id,
        )
    if command.kind is CommandKind.CANCEL_ORDER:
        return encode_cancel_order(
            command,
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=ctid_trader_account_id,
            client_msg_id=client_msg_id,
        )
    if command.kind is CommandKind.CLOSE_POSITION:
        return encode_close_position(
            command,
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=ctid_trader_account_id,
            volume=volume,
            client_msg_id=client_msg_id,
        )
    if command.kind is CommandKind.CLOSE_ALL:
        return encode_close_all(
            command,
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=ctid_trader_account_id,
            symbol_id=symbol_id,
            client_msg_id=client_msg_id,
        )
    return encode_amend_protection(
        command,
        compiled=compiled,
        declaration=declaration,
        ctid_trader_account_id=ctid_trader_account_id,
        client_msg_id=client_msg_id,
    )
