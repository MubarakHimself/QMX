"""Story 31.6 — executable honest FX paper claim without live money."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

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
    Retryability,
    TypedRefusal,
    VenueId,
    World,
    fingerprint,
    is_ok,
)
from qmf.risk.binding import BmsInstanceId
from qmf.risk.paper import BookMode, ExecutionTarget, RoutingOutcome, SeatState
from qmf.venue.capabilities import ErrorMap
from qmf.venue.commands import (
    Command,
    CommandKind,
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
from qmf.venue.events import ReconciliationVerdict
from qmf.venue.proto import SPOTWARE_PROTO_PACKAGE, compile_descriptor_set
from qmn.config import SensingOnlyDecl
from qmn.observability.failures_gate import DESIGNED_TYPED_FAILURE_IDS
from qmn.paper import (
    CANONICAL_SOURCE_TOKEN,
    FX_PAPER_CLAIM_SURFACE,
    FX_PAPER_REQUIRED_ELEMENTS,
    GRANTS_LIVE_MONEY,
    ILLEGAL_PAPER_SKIPS,
    INVENTS_KSA_VALUES,
    LOCAL_MATCHING_ENGINE,
    NODE_PAPER_ACCOUNT_ROLE,
    NODE_PAPER_WORLD,
    PROFIT_IS_EVIDENCE,
    RUNS_SOAK_WEEK,
    SPOT_FX_INCLUDED,
    V1_VENUE_CLIENT_KINDS,
    VENDOR_DEMO_HOST,
    PairedDemoBinding,
    admit_live_sensing,
    build_paired_demo_target,
    encoded_kinds_from_client,
    evaluate_fx_paper_claim,
    live_client_implementation_for,
    readback_kinds_from_client,
    refuse_fourth_venue_client_kind,
    refuse_fx_paper_illegal_skip,
    refuse_fx_paper_invented_ksa,
    refuse_fx_paper_live_authority,
    refuse_fx_paper_local_matching,
    refuse_fx_paper_profit,
    refuse_fx_paper_soak_week,
    refuse_fx_paper_twins,
    refuse_non_ctrader_live_mapping,
    resolve_book_execution_target,
)
from qmn.paper.first_deployment import LiveSensingAdmission
from qmn.venue import (
    ConformanceDouble,
    LiveCTraderClient,
    VenueClientKind,
    declared_command_kinds,
    select_venue_client,
)
from qmn.venue.live import WireKind
from qmn.venue.verify import (
    VenueFactVerifier,
    conformance_measured_facts,
    ctrader_static_declaration,
)

T = TypeVar("T")

_BOOT = "boot-epoch-fx-paper-31-6"
_WALL_NS = 1_724_000_000 * 1_000_000_000
_SESSION = "session-epoch-fx-paper"
_PROTO_TAG = 91
_LOOKBACK_NS = 1_000_000_000
_COVERING_VENUE_MS = (_WALL_NS - 2 * _LOOKBACK_NS) // 1_000_000
_PACKAGE = "protooa"
_INT64 = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
_INT32 = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
_UINT32 = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
_BYTES = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
_STRING = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
_OPTIONAL = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
_WORKSPACE = Path(__file__).resolve().parents[2]
_MAX_SOURCE_BYTES = 1 << 20
_VENUE_TOKEN = "venue-ctrader-demo"

_DESIGNED_IDS = (
    "fx_paper.fourth_kind",
    "fx_paper.go_live",
    "fx_paper.illegal_skip",
    "fx_paper.invented_ksa",
    "fx_paper.live_binding",
    "fx_paper.live_command_stream",
    "fx_paper.live_execution_target",
    "fx_paper.live_sequencer",
    "fx_paper.local_matching",
    "fx_paper.missing_element",
    "fx_paper.non_ctrader_mapping",
    "fx_paper.profit",
    "fx_paper.promotion",
    "fx_paper.soak_week",
    "fx_paper.twins",
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: object) -> TypedRefusal:
    assert isinstance(result, TypedRefusal), result
    return result


def _venue() -> VenueId:
    return _ok(VenueId.try_create(_VENUE_TOKEN))


def _account(*, role: AccountRole = AccountRole.DEMO) -> Account:
    return _ok(Account.try_create("acct-demo-1", _venue(), role))


def _clock(*, frames: int = 48) -> DataDrivenClock:
    walls = tuple(_ok(Instant.try_create(_WALL_NS + i * 1_000_000)) for i in range(frames))
    monos = tuple(5_000_000_000 + i * 1_000_000 for i in range(frames))
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
            declared_lookback=_ok(Duration.try_create(_LOOKBACK_NS)),
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


def _verify(client: LiveCTraderClient) -> object:
    account = client.account
    assert account is not None
    decl = _ok(ctrader_static_declaration())
    verifier = _ok(VenueFactVerifier.try_create(decl, client.venue_id, account))
    received = _ok(Instant.try_create(_WALL_NS))
    bundle = _ok(conformance_measured_facts(received_at=received))
    outcome = _ok(verifier.verify(bundle, received_at=received))
    _ok(client.accept_verification(outcome))
    _ok(client.verify_capabilities())
    return decl


def _ready(client: LiveCTraderClient, *, role: AccountRole = AccountRole.DEMO) -> object:
    _ok(client.open_session(_account(role=role)))
    decl = _verify(client)
    _bind_encode(client)
    return decl


def _instrument() -> Instrument:
    return _ok(Instrument.try_create(_venue(), "EURUSD"))


def _qty() -> Quantity:
    return _ok(Quantity.try_create(100, "lot", 2))


def _delta(value: int = 80) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), 5))


def _price() -> Price:
    return _ok(Price.try_create(1_10000, _instrument(), 5))


def _commands(client: LiveCTraderClient) -> dict[CommandKind, Command]:
    venue = client.venue_id
    account = _account()
    amendment = _ok(
        ProtectionAmendment.try_create(
            ProtectionSide.STOP,
            _delta(80),
            _price(),
            original_risk_distance=_delta(100),
        )
    )
    params = _ok(
        OrderParameters.try_create(
            OrderType.MARKET,
            TimeInForce.GOOD_TILL_CANCEL,
            _qty(),
            protective_stop_distance=_delta(),
        )
    )
    return {
        CommandKind.PLACE_ORDER: _ok(Command.place_order(venue, account, _SESSION, 1, params)),
        CommandKind.CANCEL_ORDER: _ok(Command.cancel_order(venue, account, _SESSION, 2, "1001")),
        CommandKind.CLOSE_POSITION: _ok(
            Command.close_position(venue, account, _SESSION, 3, "instrument-within-binding", "2002")
        ),
        CommandKind.CLOSE_ALL: _ok(
            Command.close_all(venue, account, _SESSION, 4, "account", "acct-demo-1")
        ),
        CommandKind.AMEND_PROTECTION: _ok(
            Command.amend_protection(venue, account, _SESSION, 5, amendment, "2002")
        ),
    }


def _fp(seed: str):
    return _ok(fingerprint({"class": "fx-paper-test", "seed": seed}))


def _bms(account: str, seed: str) -> BmsInstanceId:
    return _ok(BmsInstanceId.derive(_fp(seed), account, _venue(), World.LIVE))


def _paired() -> PairedDemoBinding:
    return _ok(
        build_paired_demo_target(
            venue_id=_venue(),
            account_id="acct-demo-1",
            live_bms_instance_id=_bms("acct-live", "bms-live"),
            paired_bms_instance_id=_bms("acct-demo-1", "bms-demo"),
            live_binding_epoch=_fp("live-binding-fx-paper"),
        )
    )


def _submit_all(client: LiveCTraderClient) -> None:
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
        rows = [
            row
            for row in _ok(client.observations())
            if row.get("kind") == "encode-handoff" and row.get("command_kind") == kind.value
        ]
        assert rows
        assert rows[-1]["payload_type"] == payload_types[kind]


def _readbacks(client: LiveCTraderClient) -> None:
    _ok(
        client.receive(
            WireKind.POSITION_READBACK,
            {"volume": 100},
            native_id="pos-fx-paper",
            venue_time_raw=_COVERING_VENUE_MS,
        )
    )
    _ok(
        client.receive(
            WireKind.BALANCE_READBACK,
            {"cash": 50_000},
            native_id="bal-fx-paper",
            venue_time_raw=_COVERING_VENUE_MS,
        )
    )


def _honest_client() -> tuple[LiveCTraderClient, object]:
    client = _client()
    decl = _ready(client)
    _submit_all(client)
    _readbacks(client)
    return client, decl


def _claim_kwargs(
    client: LiveCTraderClient, decl: object, **overrides: object
) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "vendor_host": VENDOR_DEMO_HOST,
        "client": client,
        "paired": _paired(),
        "declared_kinds": _ok(declared_command_kinds(decl)),
        "encoded_kinds": _ok(encoded_kinds_from_client(client)),
        "readback_kinds": _ok(readback_kinds_from_client(client)),
        "reconcile_result": _ok(client.reconcile()),
        "paper_virtual_ledger": True,
    }
    kwargs.update(overrides)
    return kwargs


def _evaluate(client: LiveCTraderClient, decl: object, **overrides: object):
    return evaluate_fx_paper_claim(**_claim_kwargs(client, decl, **overrides))  # type: ignore[arg-type]


def _imported_modules(path: Path) -> set[str]:
    resolved = path.resolve()
    assert not path.is_symlink(), resolved
    assert resolved.is_file() and resolved.is_relative_to(_WORKSPACE), resolved
    size = resolved.stat().st_size
    assert size <= _MAX_SOURCE_BYTES, resolved
    tree = ast.parse(resolved.read_text(encoding="utf-8"), filename=str(resolved))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_surface_markers_define_honest_paper_without_soak_or_live_money() -> None:
    assert FX_PAPER_CLAIM_SURFACE == "qmn.paper.fx_claim"
    assert VENDOR_DEMO_HOST == "demo.ctraderapi.com"
    assert CANONICAL_SOURCE_TOKEN == "ctrader"
    assert V1_VENUE_CLIENT_KINDS == ("ctrader", "replay", "conformance")
    assert FX_PAPER_REQUIRED_ELEMENTS == (
        "vendor_demo_host",
        "account_role_demo",
        "world_live",
        "venue_client_kind_ctrader",
        "live_ctrader_client",
        "submit_encode",
        "position_balance_readback",
    )
    assert SPOT_FX_INCLUDED is True
    assert RUNS_SOAK_WEEK is False
    assert GRANTS_LIVE_MONEY is False
    assert PROFIT_IS_EVIDENCE is False
    assert INVENTS_KSA_VALUES is False
    assert LOCAL_MATCHING_ENGINE is False
    assert NODE_PAPER_ACCOUNT_ROLE is AccountRole.DEMO
    assert NODE_PAPER_WORLD is World.LIVE
    assert "live-capital-size" in ILLEGAL_PAPER_SKIPS
    assert "spot-fx-later" in ILLEGAL_PAPER_SKIPS


def test_full_claim_seals_on_demo_host_without_a_live_token() -> None:
    client, decl = _honest_client()
    assert client.kind is VenueClientKind.CTRADER
    assert type(client) is LiveCTraderClient
    assert client.world is World.LIVE
    assert client.account is not None
    assert client.account.role is AccountRole.DEMO
    assert client.open_api_host is None
    assert client.capabilities_verified is True
    claim = _ok(_evaluate(client, decl))
    assert claim.vendor_host == VENDOR_DEMO_HOST
    assert claim.account_role is AccountRole.DEMO
    assert claim.world is World.LIVE
    assert claim.venue_client_kind is VenueClientKind.CTRADER
    assert claim.client_type == "LiveCTraderClient"
    assert claim.declared_kinds == frozenset(kind.value for kind in CommandKind)
    assert claim.encoded_kinds == claim.declared_kinds
    assert claim.readback_kinds == frozenset(
        {WireKind.POSITION_READBACK.value, WireKind.BALANCE_READBACK.value}
    )
    assert claim.reconcile_verdict is ReconciliationVerdict.RECONCILED
    assert claim.paired_demo_account == "acct-demo-1"
    assert claim.own_bms is True
    assert claim.paper_virtual_ledger is True
    assert claim.bot_twin_minted is False
    assert claim.book_twin_minted is False
    assert claim.local_matching_engine is False
    assert claim.spot_fx_included is True
    assert claim.runs_soak_week is False
    assert claim.grants_live_money is False
    assert claim.profit_is_evidence is False
    assert claim.invents_ksa is False
    assert claim.canonical_source_token == "ctrader"
    assert claim.live_sensing_only is True
    again = _ok(_evaluate(client, decl))
    assert again.fingerprint == claim.fingerprint


def test_absence_of_any_required_element_fails_the_claim() -> None:
    client, decl = _honest_client()

    host = _refusal(_evaluate(client, decl, vendor_host="live.ctraderapi.com"))
    assert host.context["missing_element"] == "vendor_demo_host"
    assert host.context["failure_id"] == "fx_paper.missing_element"

    double_venue = _ok(VenueId.try_create("conformance:fx"))
    double = _ok(ConformanceDouble.try_create(World.LIVE, double_venue))
    swapped = _claim_kwargs(client, decl)
    swapped["client"] = double
    wrong_client = _refusal(evaluate_fx_paper_claim(**swapped))  # type: ignore[arg-type]
    assert wrong_client.context["missing_element"] == "live_ctrader_client"

    live_role = _client()
    live_decl = _ready(live_role, role=AccountRole.LIVE)
    role = _refusal(_evaluate(live_role, live_decl))
    assert role.context["missing_element"] == "account_role_demo"

    partial = _refusal(
        _evaluate(client, decl, encoded_kinds=frozenset({CommandKind.PLACE_ORDER.value}))
    )
    assert partial.context["missing_element"] == "submit_encode"
    missing_kinds = partial.context["missing_kinds"]
    assert isinstance(missing_kinds, list | tuple)
    assert "cancel_order" in missing_kinds

    no_bal = _refusal(
        _evaluate(client, decl, readback_kinds=frozenset({WireKind.POSITION_READBACK.value}))
    )
    assert no_bal.context["missing_element"] == "position_balance_readback"

    refused_reconcile = TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context={"field": "reconcile", "reason": "blocked"},
    )
    rec = _refusal(_evaluate(client, decl, reconcile_result=refused_reconcile))
    assert rec.context["missing_element"] == "position_balance_readback"


def test_book_paper_still_routes_to_one_paired_demo_without_twins() -> None:
    paired = _paired()
    assert paired.paper_target.role is AccountRole.DEMO
    assert paired.world is World.LIVE
    assert paired.bot_twin_minted is False
    assert paired.book_twin_minted is False
    assert paired.pairing.live_bms_instance_id != paired.pairing.paired_bms_instance_id
    live = _ok(ExecutionTarget.try_create(AccountRole.LIVE, _venue(), "acct-live"))
    resolution = _ok(
        resolve_book_execution_target(
            book_mode=BookMode.PAPER,
            seat_state=SeatState.ACTIVE,
            active_controls=(),
            live_target=live,
            paper_target=paired.paper_target,
        )
    )
    assert resolution.outcome is RoutingOutcome.ROUTED_PAPER
    assert resolution.execution_target is not None
    assert resolution.execution_target.account_id == "acct-demo-1"
    assert resolution.execution_target.role is AccountRole.DEMO

    twinned = PairedDemoBinding(
        live_binding_epoch=paired.live_binding_epoch,
        paper_target=paired.paper_target,
        pairing=paired.pairing,
        world=World.LIVE,
        bot_twin_minted=True,
        book_twin_minted=False,
    )
    client, decl = _honest_client()
    refused = _refusal(_evaluate(client, decl, paired=twinned))
    assert refused.context["failure_id"] == "fx_paper.twins"
    assert refuse_fx_paper_twins().context["failure_id"] == "fx_paper.twins"
    matching = _refusal(_evaluate(client, decl, local_matching_engine=True))
    assert matching.context["failure_id"] == "fx_paper.local_matching"
    assert refuse_fx_paper_local_matching().context["failure_id"] == "fx_paper.local_matching"
    ledger = _refusal(_evaluate(client, decl, paper_virtual_ledger=False))
    assert ledger.context["failure_id"] == "fx_paper.missing_element"


def test_live_role_roster_stays_sensing_only_until_live_binding() -> None:
    sensing = _ok(
        admit_live_sensing(
            credentials_present=True,
            live_sensing=SensingOnlyDecl(
                venue_id=_VENUE_TOKEN,
                environment="live",
                account_id="acct-live-sense",
                credential_reference="qmx/venue-live",
                opaque_metric_id="m-sense",
                venue_client_kind=VenueClientKind.CTRADER,
            ),
        )
    )
    assert sensing.sensing_open is True
    assert sensing.has_live_binding is False
    assert sensing.has_command_stream is False
    assert sensing.opens_sequencer is False
    assert sensing.resolves_execution_target is False
    client, decl = _honest_client()
    claim = _ok(_evaluate(client, decl, live_sensing=sensing))
    assert claim.live_sensing_only is True
    assert claim.grants_live_money is False

    for flag, failure_id in (
        ("request_live_binding", "fx_paper.live_binding"),
        ("request_command_stream", "fx_paper.live_command_stream"),
        ("request_sequencer", "fx_paper.live_sequencer"),
        ("request_execution_target", "fx_paper.live_execution_target"),
        ("request_promotion", "fx_paper.promotion"),
        ("request_go_live", "fx_paper.go_live"),
    ):
        refused = _refusal(_evaluate(client, decl, **{flag: True}))
        assert refused.context["failure_id"] == failure_id

    live_binding = LiveSensingAdmission(
        credentials_present=True,
        sensing_open=True,
        may_record=True,
        may_verify_capabilities=True,
        may_accumulate_baseline=True,
        has_live_binding=True,
    )
    bound = _refusal(_evaluate(client, decl, live_sensing=live_binding))
    assert bound.context["failure_id"] == "fx_paper.live_binding"
    assert refuse_fx_paper_live_authority("live-binding").context["failure_id"] == (
        "fx_paper.live_binding"
    )


def test_live_capital_and_spot_fx_later_are_not_legal_skips() -> None:
    client, decl = _honest_client()
    for skip in ("live-capital-size", "spot FX later", "spot_fx_later"):
        refused = _refusal(_evaluate(client, decl, skip=skip))
        assert refused.context["failure_id"] == "fx_paper.illegal_skip"
        assert refused.context["spot_fx_included"] is True
    claim = _ok(_evaluate(client, decl))
    assert claim.spot_fx_included is True
    assert refuse_fx_paper_illegal_skip("spot-fx-later").context["failure_id"] == (
        "fx_paper.illegal_skip"
    )


def test_fourth_kind_and_non_ctrader_kind_are_never_mapped_onto_live_client() -> None:
    fourth = refuse_fourth_venue_client_kind("mt5")
    assert fourth.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert fourth.context["failure_id"] == "fx_paper.fourth_kind"
    assert fourth.context["canonical_source_token"] == "ctrader"
    assert _refusal(live_client_implementation_for("mt5")).context["failure_id"] == (
        "fx_paper.fourth_kind"
    )
    mapped = refuse_non_ctrader_live_mapping(VenueClientKind.REPLAY)
    assert mapped.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert mapped.context["failure_id"] == "fx_paper.non_ctrader_mapping"
    impl = _ok(live_client_implementation_for(VenueClientKind.CTRADER))
    assert impl is LiveCTraderClient
    replay_impl = _refusal(live_client_implementation_for(VenueClientKind.REPLAY))
    assert replay_impl.context["failure_id"] == "fx_paper.non_ctrader_mapping"
    selected = _ok(select_venue_client(World.LIVE, _venue(), VenueClientKind.CTRADER))
    assert selected.kind is VenueClientKind.CTRADER
    unknown = _refusal(select_venue_client(World.LIVE, _venue(), "mt5"))
    assert unknown.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    client, decl = _honest_client()
    claim_fourth = _refusal(_evaluate(client, decl, proposed_kind="mt5"))
    assert claim_fourth.context["failure_id"] == "fx_paper.fourth_kind"
    claim_replay = _refusal(_evaluate(client, decl, proposed_kind=VenueClientKind.REPLAY))
    assert claim_replay.context["failure_id"] == "fx_paper.non_ctrader_mapping"


def test_soak_ksa_profit_are_refused_and_not_evidence() -> None:
    client, decl = _honest_client()
    soak = _refusal(_evaluate(client, decl, run_soak_week=True))
    assert soak.context["failure_id"] == "fx_paper.soak_week"
    ksa = _refusal(_evaluate(client, decl, invent_ksa=True))
    assert ksa.context["failure_id"] == "fx_paper.invented_ksa"
    profit = _refusal(_evaluate(client, decl, treat_profit_as_evidence=True))
    assert profit.context["failure_id"] == "fx_paper.profit"
    assert refuse_fx_paper_soak_week().context["runs_soak_week"] is False
    assert refuse_fx_paper_invented_ksa().context["invents_ksa"] is False
    assert refuse_fx_paper_profit().context["profit_is_evidence"] is False


def test_qmb_qml_and_qma_do_not_import_qmf_venue() -> None:
    roots = (
        _WORKSPACE / "qmb" / "src",
        _WORKSPACE / "qml" / "src",
        _WORKSPACE / "qmx-agents" / "packages" / "qma-core" / "src",
        _WORKSPACE / "qmx-agents" / "packages" / "qma-daemon" / "src",
        _WORKSPACE / "qmx-agents" / "packages" / "qma-wire" / "src",
        _WORKSPACE / "qmn" / "src" / "qmn",
    )
    violations: list[str] = []
    venue_hits = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(_WORKSPACE)
            under_qmn_venue = relative.parts[:4] == ("qmn", "src", "qmn", "venue")
            for imported in _imported_modules(path):
                is_venue = imported == "qmf.venue" or imported.startswith("qmf.venue.")
                if not is_venue:
                    continue
                if under_qmn_venue:
                    venue_hits += 1
                    continue
                violations.append(f"{relative}: {imported}")
    assert violations == []
    assert venue_hits > 0


def test_designed_failure_ids_are_registered() -> None:
    for failure_id in _DESIGNED_IDS:
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS
