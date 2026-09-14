"""Story 31.3 — live client translates Command onto qmf-venue encode symbols."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

import tomllib
from google.protobuf import descriptor_pb2
from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Instant,
    Instrument,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
)
from qmf.venue.capabilities import (
    CapabilityDeclaration,
    CapabilityField,
    CapabilityFieldName,
    ErrorMap,
    ErrorMapRow,
    SubmissionOutcomeClass,
)
from qmf.venue.commands import (
    Command,
    CommandKind,
    CompoundCommand,
    OrderParameters,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    TimeInForce,
)
from qmf.venue.encode import (
    PROTO_OA_AMEND_POSITION_SLTP_REQ,
    PROTO_OA_CANCEL_ORDER_REQ,
    PROTO_OA_CLOSE_POSITION_REQ,
    PROTO_OA_NEW_ORDER_REQ,
    EncodedCommand,
)
from qmf.venue.proto import (
    SPOTWARE_PROTO_PACKAGE,
    CompiledProto,
    ProtoArtifact,
    compile_descriptor_set,
)
from qmn.venue import LiveCTraderClient, compound_command_acceptance_blocked
from qmn.venue.live import LiveCTraderClient as LiveInModule

T = TypeVar("T")

_BOOT = "boot-epoch-encode-31-3"
_WALL_NS = 1_724_000_000 * 1_000_000_000
_SESSION = "session-epoch-encode"
_PROTO_TAG = 91
_DIGEST = "sha256:" + "a" * 64
_QMN_ROOT = Path(__file__).resolve().parents[1]
_WORKSPACE = _QMN_ROOT.parent
_LIVE_SRC = _QMN_ROOT / "src" / "qmn" / "venue" / "live.py"
_MAX_SOURCE_BYTES = 1 << 20
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


def _refusal(result: object) -> TypedRefusal:
    assert isinstance(result, TypedRefusal), result
    return result


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(
        Account.try_create("acct-001", venue if venue is not None else _venue(), AccountRole.DEMO)
    )


def _clock() -> DataDrivenClock:
    walls = tuple(_ok(Instant.try_create(_WALL_NS + i * 1_000_000)) for i in range(8))
    monos = tuple(5_000_000_000 + i * 1_000_000 for i in range(8))
    return DataDrivenClock(boot_epoch_id=_BOOT, wall_instants=walls, monotonic_ns=monos)


def _error_map() -> ErrorMap:
    return _ok(ErrorMap.try_create(1, ()))


def _client() -> LiveCTraderClient:
    return _ok(
        LiveCTraderClient.try_create(World.LIVE, _venue(), clock=_clock(), error_map=_error_map())
    )


def _add_field(
    message: descriptor_pb2.DescriptorProto,
    name: str,
    number: int,
    typ: descriptor_pb2.FieldDescriptorProto.Type.ValueType,
) -> None:
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = _OPTIONAL
    field.type = typ


def _add_message(
    file_proto: descriptor_pb2.FileDescriptorProto,
    name: str,
    fields: tuple[tuple[str, int, descriptor_pb2.FieldDescriptorProto.Type.ValueType], ...],
) -> None:
    message = file_proto.message_type.add()
    message.name = name
    for field_name, number, typ in fields:
        _add_field(message, field_name, number, typ)


def _compiled() -> CompiledProto:
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
    _add_message(
        file_proto,
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
    return _ok(
        compile_descriptor_set(
            file_set.SerializeToString(),
            package_name=SPOTWARE_PROTO_PACKAGE,
            release_tag=_PROTO_TAG,
        )
    )


def _static(name: CapabilityFieldName, value: object) -> CapabilityField:
    return _ok(CapabilityField.static(name, value))


def _measured(name: CapabilityFieldName) -> CapabilityField:
    return _ok(CapabilityField.measured(name))


def _declaration(*, acknowledgement_modes: object | None = None) -> CapabilityDeclaration:
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
    fields = [
        _static(CapabilityFieldName.MARKET_DATA_KINDS, ["tick", "bar", "depth"]),
        _static(
            CapabilityFieldName.ORDER_PARAMETER_SUBSET,
            {"order_types": ["market", "limit", "stop", "stop-limit"]},
        ),
        _static(
            CapabilityFieldName.COMMAND_SCOPES,
            ["account", "account-binding", "instrument-within-binding"],
        ),
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
        _static(CapabilityFieldName.PROTECTION_PRIMITIVES, ["suspend-new", "drain", "close_all"]),
        _measured(CapabilityFieldName.SETTLEMENT_CURRENCY),
        _measured(CapabilityFieldName.MARGIN_SURFACE),
        _measured(CapabilityFieldName.VALUE_FACTOR_METADATA),
        _static(CapabilityFieldName.RECONCILIATION_LOOKBACK, "do-not-default"),
        _measured(CapabilityFieldName.PROTECTION_CAPABILITIES),
        _static(CapabilityFieldName.COMMAND_ID_MAPPING, {"injective_total": True}),
        _static(CapabilityFieldName.FLOAT_TARGET_SCALES, {"execution_price": "declared-digits"}),
        _static(CapabilityFieldName.VERIFICATION_SUITE, ["spot-timestamp-unit"]),
    ]
    error_map = _ok(ErrorMap.try_create(1, [row]))
    return _ok(CapabilityDeclaration.try_create("qmn.venue/31.3", artifact, error_map, fields))


def _qty() -> Quantity:
    return _ok(Quantity.try_create(100, "lot", 2))


def _instrument() -> Instrument:
    return _ok(Instrument.try_create(_venue(), "EURUSD"))


def _price() -> Price:
    return _ok(Price.try_create(1_10000, _instrument(), 5))


def _delta(value: int = 80) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), 5))


def _params() -> OrderParameters:
    return _ok(OrderParameters.try_create(OrderType.MARKET, TimeInForce.GOOD_TILL_CANCEL, _qty()))


def _imported_modules(path: Path) -> set[str]:
    resolved = path.resolve()
    assert not path.is_symlink(), resolved
    assert resolved.is_file() and resolved.is_relative_to(_WORKSPACE), resolved
    assert resolved.stat().st_size <= _MAX_SOURCE_BYTES, resolved
    tree = ast.parse(resolved.read_text(encoding="utf-8"), filename=str(resolved))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_live_translates_each_kind_onto_encode_symbols() -> None:
    client = _client()
    compiled = _compiled()
    declaration = _declaration()
    venue = client.venue_id
    account = _account(venue)
    place = _ok(Command.place_order(venue, account, _SESSION, 1, _params()))
    cancel = _ok(Command.cancel_order(venue, account, _SESSION, 2, "1001"))
    close_pos = _ok(
        Command.close_position(venue, account, _SESSION, 3, "instrument-within-binding", "2002")
    )
    close_all = _ok(Command.close_all(venue, account, _SESSION, 4, "account", "acct-001"))
    amendment = _ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP, _delta(80), _price(), original_risk_distance=_delta(100)
        )
    )
    amend = _ok(Command.amend_protection(venue, account, _SESSION, 5, amendment, "2002"))

    encoded_place = _ok(
        client.encode_command(
            place,
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=42,
            symbol_id=1,
            trade_side="buy",
        )
    )
    encoded_cancel = _ok(
        client.encode_command(
            cancel, compiled=compiled, declaration=declaration, ctid_trader_account_id=42
        )
    )
    encoded_close = _ok(
        client.encode_command(
            close_pos,
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=42,
            volume=_qty(),
        )
    )
    encoded_all = _ok(
        client.encode_command(
            close_all, compiled=compiled, declaration=declaration, ctid_trader_account_id=42
        )
    )
    encoded_amend = _ok(
        client.encode_command(
            amend, compiled=compiled, declaration=declaration, ctid_trader_account_id=42
        )
    )
    assert isinstance(encoded_place, EncodedCommand)
    assert encoded_place.kind is CommandKind.PLACE_ORDER
    assert encoded_place.payload_type == PROTO_OA_NEW_ORDER_REQ
    assert encoded_cancel.payload_type == PROTO_OA_CANCEL_ORDER_REQ
    assert encoded_close.payload_type == PROTO_OA_CLOSE_POSITION_REQ
    assert encoded_all.payload_type == PROTO_OA_CLOSE_POSITION_REQ
    assert encoded_amend.payload_type == PROTO_OA_AMEND_POSITION_SLTP_REQ


def test_live_encode_compound_keeps_ftr02_block() -> None:
    client = _client()
    parent = _ok(
        Command.cancel_order(client.venue_id, _account(client.venue_id), _SESSION, 1, "1001")
    )
    compound = _ok(CompoundCommand.fan_out(parent, (0, 1)))
    refusal = _refusal(
        client.encode_command(
            compound,
            compiled=_compiled(),
            declaration=_declaration(),
            ctid_trader_account_id=1,
        )
    )
    blocked = compound_command_acceptance_blocked()
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["ftr"] == "FTR-02"
    assert refusal.context["field"] == blocked.context["field"]
    assert refusal.context["reason"] == blocked.context["reason"]


def test_live_encode_names_missing_ct18_capability() -> None:
    client = _client()
    command = _ok(
        Command.cancel_order(client.venue_id, _account(client.venue_id), _SESSION, 1, "1001")
    )
    refusal = _refusal(
        client.encode_command(
            command,
            compiled=_compiled(),
            declaration=_declaration(acknowledgement_modes={"place_order": "explicit-event"}),
            ctid_trader_account_id=1,
        )
    )
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["capability"] == "acknowledgement_modes"


def test_live_module_does_not_compile_or_import_proto() -> None:
    imports = _imported_modules(_LIVE_SRC)
    assert "qmf.venue.encode" in imports
    assert "qmf.venue.proto" not in imports
    assert not any(
        name == "google.protobuf" or name.startswith("google.protobuf.") for name in imports
    )
    source = _LIVE_SRC.read_text(encoding="utf-8")
    assert "compile_descriptor_set" not in source
    assert LiveInModule is LiveCTraderClient


def test_qmn_does_not_declare_protobuf() -> None:
    data = tomllib.loads((_QMN_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = list(data["project"]["dependencies"])
    assert not any(item.startswith("protobuf") for item in deps)
    venue = tomllib.loads(
        (_WORKSPACE / "packages" / "qmf-venue" / "pyproject.toml").read_text(encoding="utf-8")
    )
    venue_deps = list(venue["project"]["dependencies"])
    assert "protobuf==7.36.0" in venue_deps
    assert not any(item.startswith("protobuf==7.36.1") for item in venue_deps)
