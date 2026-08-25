"""Story 14.5 — CT-23 intent consumption, execution port seams, CT-29 exits."""

from __future__ import annotations

from typing import Protocol, TypeVar, get_args

from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_PROCEDURE_EPHEMERAL,
    PROVENANCE_RECORDED,
    PROVENANCE_SYNTHETIC_TAINTED,
    mint_replay_binding,
)
from qmb.doors import api
from qmb.execution import (
    CLAIMS_EDGE,
    COMPOSITION_ORDER,
    FILL_DECISIONS,
    FINANCING_IS_ORDER_FILL,
    GAP_0048_OPEN,
    PORT_ROLES,
    SPENDS_SPLIT_BUDGET,
    TAINT_IS_IDENTITY,
    TAINT_OPTIMISTIC,
    AuthorizedIntent,
    CostedFill,
    CostPort,
    ExecutionPorts,
    Fill,
    FillDecision,
    FillKind,
    FillPort,
    FinancingPort,
    NoFill,
    PartialFill,
    SlicePath,
    SlippagePort,
    admit_open,
    apply_execution_ports,
    classify_fill_quantity,
    derive_world_from_provenance,
    evaluate_exit,
    execute_authorized,
    fingerprint_ports,
    ports_identity,
    record_virtual_close,
    refuse_optimistic_edge_claim,
    refuse_store_synthetic_governed_evidence,
    require_authorized_intent,
    require_full_loss_before_open,
)
from qmf.core.chrono import Instant
from qmf.core.exact import ExactRational, Money, Price, PriceDelta, Quantity, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, RefusalCategory, Result, TypedRefusal, is_ok, is_refusal
from qmf.risk.door import (
    Direction,
    EntryIntent,
    ExitIntent,
    ExitKind,
    ExitLogicRef,
    ReasonCode,
    StopMoveDirection,
    TightenProtectiveStop,
    refuse_no_full_loss_price,
)
from qmf.risk.exit_record import CloseOutcome, CloseReason, ClosingAuthority, ExitResultLabel
from qmf.risk.paper import ExecutionTarget

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_VENUE = "venue-replay"
_ACCOUNT = "acct-replay"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _costed(result: Result[CostedFill | NoFill]) -> CostedFill:
    value = _ok(result)
    assert isinstance(value, CostedFill)
    return value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _fp(seed: str):
    return _ok(fingerprint({"seed": seed}))


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value=_VENUE), symbol="EURUSD")


def _price(value: int = 1_10000) -> Price:
    return _ok(Price.try_create(value, _instrument(), 5))


def _qty(value: int) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", 0))


def _path(price: Price | None = None) -> SlicePath:
    return _ok(SlicePath.try_create("eurusd", (price or _price(),)))


def _binding():
    return _ok(
        mint_replay_binding(
            book_fp1=_fp("book"),
            bms_fp1=_fp("bms"),
            bot_fp1=_fp("bot"),
            starting_capital=Money(value=1_000_000, currency="USD", scale=2),
            seed_overridden=False,
            venue_id=_VENUE,
            account_id=_ACCOUNT,
            clock=CLOCK_REPLAY,
            data_provenance=PROVENANCE_RECORDED,
            keys={},
        )
    )


def _entry() -> EntryIntent:
    return _ok(
        EntryIntent.try_create(
            _instrument(),
            Direction.LONG,
            _ok(ReasonCode.try_create("breakout", "scalper-v1")),
            _ok(ExecutionTarget.try_create("demo", VenueId(value=_VENUE), _ACCOUNT)),
        )
    )


def _exit() -> ExitIntent:
    return _ok(
        ExitIntent.try_create(
            ExitKind.CLOSE_FULL,
            _ok(ReasonCode.try_create("done", "scalper-v1")),
            _fp("vp-1"),
        )
    )


def _logic() -> ExitLogicRef:
    return _ok(ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}))


def _requested_r():
    return _ok(ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE))


class _OffsetStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        del cited_evidence
        value = entry_price.value - 500 if direction is Direction.LONG else entry_price.value + 500
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class _NoStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        del entry_price, direction, cited_evidence
        return refuse_no_full_loss_price(module="no-stop")


class _BotSizedOrder:
    size = 1.0


def _decision(
    result: Result[Fill] | Result[NoFill] | Result[PartialFill],
) -> Result[Fill | NoFill | PartialFill]:
    if isinstance(result, TypedRefusal):
        return result
    value: Fill | NoFill | PartialFill = result.value
    return Ok(value)


class _FillRequested:
    def decide(
        self,
        intent: EntryIntent | ExitIntent,
        path: SlicePath,
        *,
        requested_quantity: Quantity,
    ) -> Result[Fill | NoFill | PartialFill]:
        del intent
        price = path.prints[0] if path.prints else _price()
        return _decision(Fill.try_create(requested_quantity, requested_quantity, price))


class _FillPartial:
    def decide(
        self,
        intent: EntryIntent | ExitIntent,
        path: SlicePath,
        *,
        requested_quantity: Quantity,
    ) -> Result[Fill | NoFill | PartialFill]:
        del intent
        price = path.prints[0] if path.prints else _price()
        half = _ok(Quantity.try_create(1, requested_quantity.unit, requested_quantity.scale))
        return _decision(PartialFill.try_create(half, requested_quantity, price))


class _FillNone:
    def decide(
        self,
        intent: EntryIntent | ExitIntent,
        path: SlicePath,
        *,
        requested_quantity: Quantity,
    ) -> Result[Fill | NoFill | PartialFill]:
        del intent, path, requested_quantity
        return _decision(NoFill.try_create("no-cross"))


class _PassThroughSlip:
    def apply(
        self, fill: Fill | PartialFill, path: SlicePath
    ) -> Result[Fill | NoFill | PartialFill]:
        del path
        if isinstance(fill, Fill):
            return _decision(
                Fill.try_create(
                    fill.quantity,
                    fill.requested_quantity,
                    fill.pre_slip_price,
                    post_slip_price=fill.pre_slip_price,
                )
            )
        return _decision(
            PartialFill.try_create(
                fill.quantity,
                fill.requested_quantity,
                fill.pre_slip_price,
                remaining_quantity=fill.remaining_quantity,
                post_slip_price=fill.pre_slip_price,
            )
        )


class _VetoSlip:
    def apply(
        self, fill: Fill | PartialFill, path: SlicePath
    ) -> Result[Fill | NoFill | PartialFill]:
        del fill, path
        return _decision(NoFill.try_create("illegal-print"))


class _ResizeSlip:
    def apply(
        self, fill: Fill | PartialFill, path: SlicePath
    ) -> Result[Fill | NoFill | PartialFill]:
        del path
        smaller = _ok(Quantity.try_create(1, fill.quantity.unit, fill.quantity.scale))
        return _decision(
            PartialFill.try_create(
                smaller,
                fill.requested_quantity,
                fill.pre_slip_price,
                post_slip_price=fill.pre_slip_price,
            )
        )


class _ZeroCost:
    def quote(self, fill: Fill | PartialFill) -> Result[Money]:
        del fill
        return Ok(Money(value=0, currency="USD", scale=2))

    def itemize(self, fill: Fill | PartialFill) -> Result[CostedFill]:
        return CostedFill.try_create(fill, ())


class _SilentFinancing:
    def __init__(self) -> None:
        self.calls = 0

    def schedule(self, *, stream_id: str, direction: object) -> Result[Money]:
        del stream_id, direction
        self.calls += 1
        return Ok(Money(value=0, currency="USD", scale=2))


def _ports(
    fill: object | None = None,
    slippage: object | None = None,
    cost: object | None = None,
    financing: object | None = None,
) -> ExecutionPorts:
    return _ok(
        ExecutionPorts.try_create(
            fill or _FillRequested(),
            slippage or _PassThroughSlip(),
            cost or _ZeroCost(),
            financing or _SilentFinancing(),
        )
    )


def test_ports_are_separate_typing_protocols() -> None:
    assert PORT_ROLES == ("fill", "slippage", "cost", "financing")
    assert COMPOSITION_ORDER == ("fill", "slippage", "cost")
    assert FILL_DECISIONS == ("fill", "no-fill", "partial-fill")
    assert FINANCING_IS_ORDER_FILL is False
    assert issubclass(FillPort, Protocol)
    assert issubclass(SlippagePort, Protocol)
    assert issubclass(CostPort, Protocol)
    assert issubclass(FinancingPort, Protocol)
    assert FillPort is not SlippagePort
    assert FillPort is not CostPort
    assert SlippagePort is not CostPort
    assert isinstance(_FillRequested(), FillPort)
    assert not isinstance(_FillRequested(), SlippagePort)
    assert not isinstance(_PassThroughSlip(), FillPort)
    identity = ports_identity()
    assert identity["composition_order"] == COMPOSITION_ORDER
    assert identity["fill_decisions"] == FILL_DECISIONS
    assert identity["taint_field"] == TAINT_OPTIMISTIC
    assert identity["taint_is_identity"] is False
    assert identity["claims_edge"] is False
    assert identity["spends_split_budget"] is False
    assert identity["gap_0048_open"] is True
    assert identity["adapter_binding"] == "resolved-run-config"
    assert identity["financing_is_order_fill"] is False


def test_changing_composition_order_is_identity_bearing() -> None:
    canonical = _ok(fingerprint_ports())
    assert _ok(fingerprint_ports()).value == canonical.value
    permuted = dict(ports_identity())
    permuted["composition_order"] = tuple(reversed(COMPOSITION_ORDER))
    assert _ok(fingerprint(permuted)).value != canonical.value


def test_authorized_intent_is_ct23_never_a_bot_sized_order() -> None:
    assert set(get_args(AuthorizedIntent)) == {EntryIntent, ExitIntent}
    assert set(get_args(FillDecision)) == {Fill, NoFill, PartialFill}
    entry = _entry()
    assert _ok(require_authorized_intent(entry)) is entry
    closing = _exit()
    assert _ok(require_authorized_intent(closing)) is closing
    refused = require_authorized_intent(_BotSizedOrder())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "intent"
    apply_refused = apply_execution_ports(
        _ports(),
        intent=_BotSizedOrder(),
        path=_path(),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
    )
    assert is_refusal(apply_refused)
    assert apply_refused.category is RefusalCategory.INVALID_INPUT


def test_full_loss_price_required_before_open() -> None:
    binding = _binding()
    intent = _entry()
    entry = _price()
    logic = _logic()
    requested = _requested_r()
    admitted = _ok(
        admit_open(
            binding,
            intent=intent,
            entry_price=entry,
            exit_logic_ref=logic,
            module=_OffsetStopModule(),
            book_resolved_requested_r=requested,
        )
    )
    assert admitted.declared_full_loss_price is not None
    none_price = require_full_loss_before_open(None)
    assert is_refusal(none_price)
    missing = execute_authorized(
        binding,
        intent=intent,
        ports=_ports(),
        path=_path(entry),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
        data_provenance=PROVENANCE_RECORDED,
        entry_price=entry,
        exit_logic_ref=logic,
        module=_NoStopModule(),
        book_resolved_requested_r=requested,
    )
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT


def test_fill_nofill_partialfill_are_first_class() -> None:
    path = _path()
    filled = _costed(
        apply_execution_ports(
            _ports(),
            intent=_entry(),
            path=path,
            requested_quantity=_qty(2),
            position_cap=_qty(2),
            lot_step=_qty(1),
        )
    )
    assert isinstance(filled.fill, Fill)
    assert filled.fill.kind is FillKind.FILL
    assert filled.fill.taint == TAINT_OPTIMISTIC
    assert filled.taint == TAINT_OPTIMISTIC
    assert "taint" not in filled.fill.fp1_identity()

    partial = _costed(
        apply_execution_ports(
            _ports(_FillPartial()),
            intent=_entry(),
            path=path,
            requested_quantity=_qty(2),
            position_cap=_qty(2),
            lot_step=_qty(1),
        )
    )
    assert isinstance(partial.fill, PartialFill)
    assert partial.fill.kind is FillKind.PARTIAL_FILL
    assert partial.fill.quantity.as_fraction() == _qty(1).as_fraction()
    assert partial.fill.remaining_quantity.as_fraction() == _qty(1).as_fraction()
    assert partial.fill.taint == TAINT_OPTIMISTIC

    none = _ok(
        apply_execution_ports(
            _ports(_FillNone()),
            intent=_entry(),
            path=path,
            requested_quantity=_qty(2),
            position_cap=_qty(2),
            lot_step=_qty(1),
        )
    )
    assert isinstance(none, NoFill)
    assert none.kind is FillKind.NO_FILL
    assert none.reason == "no-cross"


def test_classify_caps_by_position_and_lot_step() -> None:
    price = _price()
    full = _ok(
        classify_fill_quantity(
            requested=_qty(2),
            filled=_qty(2),
            position_cap=_qty(2),
            lot_step=_qty(1),
            pre_slip_price=price,
        )
    )
    assert isinstance(full, Fill)
    capped = _ok(
        classify_fill_quantity(
            requested=_qty(4),
            filled=_qty(4),
            position_cap=_qty(2),
            lot_step=_qty(1),
            pre_slip_price=price,
        )
    )
    assert isinstance(capped, PartialFill)
    assert capped.quantity.as_fraction() == _qty(2).as_fraction()
    snapped = _ok(
        classify_fill_quantity(
            requested=_qty(3),
            filled=_qty(3),
            position_cap=_qty(3),
            lot_step=_qty(2),
            pre_slip_price=price,
        )
    )
    assert isinstance(snapped, PartialFill)
    assert snapped.quantity.as_fraction() == _qty(2).as_fraction()
    zeroed = _ok(
        classify_fill_quantity(
            requested=_qty(3),
            filled=_qty(1),
            position_cap=_qty(3),
            lot_step=_qty(2),
            pre_slip_price=price,
        )
    )
    assert isinstance(zeroed, NoFill)


def test_slippage_may_veto_and_must_not_resize() -> None:
    path = _path()
    vetoed = _ok(
        apply_execution_ports(
            _ports(slippage=_VetoSlip()),
            intent=_exit(),
            path=path,
            requested_quantity=_qty(1),
            position_cap=_qty(1),
            lot_step=_qty(1),
        )
    )
    assert isinstance(vetoed, NoFill)
    assert vetoed.reason == "illegal-print"
    resized = apply_execution_ports(
        _ports(_FillRequested(), _ResizeSlip()),
        intent=_exit(),
        path=path,
        requested_quantity=_qty(2),
        position_cap=_qty(2),
        lot_step=_qty(1),
    )
    assert is_refusal(resized)
    assert resized.category is RefusalCategory.INVALID_INPUT
    assert resized.context["field"] == "quantity"


def test_financing_is_not_invoked_on_the_fill_composition() -> None:
    financing = _SilentFinancing()
    _ok(
        apply_execution_ports(
            _ports(financing=financing),
            intent=_entry(),
            path=_path(),
            requested_quantity=_qty(1),
            position_cap=_qty(1),
            lot_step=_qty(1),
        )
    )
    assert financing.calls == 0
    assert qmb.FINANCING_IS_ORDER_FILL is False


class _AllRoles:
    def decide(
        self,
        intent: EntryIntent | ExitIntent,
        path: SlicePath,
        *,
        requested_quantity: Quantity,
    ) -> Result[Fill | NoFill | PartialFill]:
        del intent
        price = path.prints[0] if path.prints else _price()
        return _decision(Fill.try_create(requested_quantity, requested_quantity, price))

    def apply(
        self, fill: Fill | PartialFill, path: SlicePath
    ) -> Result[Fill | NoFill | PartialFill]:
        return _PassThroughSlip().apply(fill, path)

    def quote(self, fill: Fill | PartialFill) -> Result[Money]:
        del fill
        return Ok(Money(value=0, currency="USD", scale=2))

    def itemize(self, fill: Fill | PartialFill) -> Result[CostedFill]:
        return CostedFill.try_create(fill, ())

    def schedule(self, *, stream_id: str, direction: object) -> Result[Money]:
        del stream_id, direction
        return Ok(Money(value=0, currency="USD", scale=2))


def test_separate_port_objects_are_required() -> None:
    shared = _AllRoles()
    refused = ExecutionPorts.try_create(shared, shared, shared, shared)
    assert is_refusal(refused)
    assert refused.context["field"] == "ports"


def test_all_fills_carry_optimistic_taint_until_gap_0048() -> None:
    assert GAP_0048_OPEN is True
    assert TAINT_IS_IDENTITY is False
    assert CLAIMS_EDGE is False
    assert SPENDS_SPLIT_BUDGET is False
    price = _price()
    fill = _ok(Fill.try_create(_qty(1), _qty(1), price))
    assert fill.taint == TAINT_OPTIMISTIC
    assert "taint" not in fill.fp1_identity()
    tainted = Fill.try_create(_qty(1), _qty(1), price, taint="calibrated")
    assert is_refusal(tainted)
    assert tainted.category is RefusalCategory.POLICY_REJECTION
    edge = refuse_optimistic_edge_claim(claims_edge=True)
    assert is_refusal(edge)
    assert edge.category is RefusalCategory.POLICY_REJECTION
    budget = refuse_optimistic_edge_claim(spends_split_budget=True)
    assert is_refusal(budget)
    assert _ok(refuse_optimistic_edge_claim()) is None
    executed = _costed(
        apply_execution_ports(
            _ports(),
            intent=_entry(),
            path=_path(price),
            requested_quantity=_qty(1),
            position_cap=_qty(1),
            lot_step=_qty(1),
        )
    )
    assert executed.fill.taint == TAINT_OPTIMISTIC
    assert executed.taint == TAINT_OPTIMISTIC


def test_store_synthetic_is_world_simulated_policy_rejection() -> None:
    derived = _ok(derive_world_from_provenance(PROVENANCE_SYNTHETIC_TAINTED))
    assert derived is World.SIMULATED
    assert _ok(derive_world_from_provenance(PROVENANCE_RECORDED)) is World.REPLAY
    assert _ok(derive_world_from_provenance(PROVENANCE_PROCEDURE_EPHEMERAL)) is World.REPLAY
    refused = refuse_store_synthetic_governed_evidence(PROVENANCE_SYNTHETIC_TAINTED)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "world"
    assert refused.context["world"] == World.SIMULATED.value
    assert _ok(refuse_store_synthetic_governed_evidence(PROVENANCE_RECORDED)) is World.REPLAY
    simulated = refuse_store_synthetic_governed_evidence(World.SIMULATED)
    assert is_refusal(simulated)
    executed = execute_authorized(
        _binding(),
        intent=_entry(),
        ports=_ports(),
        path=_path(),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
        data_provenance=PROVENANCE_SYNTHETIC_TAINTED,
        entry_price=_price(),
        exit_logic_ref=_logic(),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_requested_r(),
    )
    assert is_refusal(executed)
    assert executed.category is RefusalCategory.POLICY_REJECTION


def test_execute_authorized_runs_ct23_then_ports() -> None:
    outcome = _costed(
        execute_authorized(
            _binding(),
            intent=_entry(),
            ports=_ports(),
            path=_path(),
            requested_quantity=_qty(1),
            position_cap=_qty(1),
            lot_step=_qty(1),
            data_provenance=PROVENANCE_RECORDED,
            entry_price=_price(),
            exit_logic_ref=_logic(),
            module=_OffsetStopModule(),
            book_resolved_requested_r=_requested_r(),
        )
    )
    assert isinstance(outcome, CostedFill)
    assert outcome.fill.kind is FillKind.FILL
    closed = _ok(
        execute_authorized(
            _binding(),
            intent=_exit(),
            ports=_ports(),
            path=_path(),
            requested_quantity=_qty(1),
            position_cap=_qty(1),
            lot_step=_qty(1),
            data_provenance=PROVENANCE_RECORDED,
        )
    )
    assert isinstance(closed, CostedFill)


def test_bot_proposed_exits_are_risk_monotonic() -> None:
    binding = _binding()
    closing = _ok(evaluate_exit(binding, _exit()))
    assert closing.kind is ExitKind.CLOSE_FULL
    bound = _ok(PriceDelta.try_create(10, _instrument(), 5))
    widen = TightenProtectiveStop.try_create(StopMoveDirection.WIDEN, bound)
    assert is_refusal(widen)
    assert widen.category is RefusalCategory.POLICY_REJECTION
    partial = ExitIntent.try_create(
        "close_partial",
        _ok(ReasonCode.try_create("scratch", "scalper-v1")),
        _fp("vp-2"),
    )
    assert is_refusal(partial)
    assert partial.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_one_ct29_exit_per_virtual_close() -> None:
    binding = _binding()
    instrument = _instrument()
    position = _fp("pos-1")
    label = _ok(ExitResultLabel.try_create("demo", World.REPLAY))
    kwargs = {
        "virtual_position_ref": position,
        "opening_bot_id": "bot-alpha",
        "original_risk_distance": _ok(PriceDelta.try_create(50, instrument, 5)),
        "original_risk_amount": Money(value=10_000, currency="USD", scale=2),
        "fill_references": (_fp("fill-1"),),
        "realized_pnl": Money(value=-10_000, currency="USD", scale=2),
        "cost_components": (),
        "close_reason": CloseReason.BOT_INTENT,
        "mechanism": CloseReason.BOT_INTENT,
        "outcome": CloseOutcome.LOSS,
        "closing_authority": ClosingAuthority.BOOK_POLICY,
        "close_reason_mapping_version": 1,
        "result_label": label,
        "loss_predicate_format_version": 1,
        "recorded_at": _instant(),
        "arbitration_record_ref": _fp("arb-1"),
    }
    first = _ok(record_virtual_close(binding, **kwargs))
    assert first.binding_epoch == binding.fingerprint
    assert first.result_label.world is World.REPLAY
    second = record_virtual_close(binding, closed_refs=(first,), **kwargs)
    assert is_refusal(second)
    assert second.category is RefusalCategory.POLICY_REJECTION
    assert second.context["field"] == "virtual_position_ref"
    other = _ok(
        record_virtual_close(
            binding,
            closed_refs=(first,),
            virtual_position_ref=_fp("pos-2"),
            opening_bot_id="bot-alpha",
            original_risk_distance=_ok(PriceDelta.try_create(50, instrument, 5)),
            original_risk_amount=Money(value=10_000, currency="USD", scale=2),
            fill_references=(_fp("fill-2"),),
            realized_pnl=Money(value=-10_000, currency="USD", scale=2),
            cost_components=(),
            close_reason=CloseReason.BOT_INTENT,
            mechanism=CloseReason.BOT_INTENT,
            outcome=CloseOutcome.LOSS,
            closing_authority=ClosingAuthority.BOOK_POLICY,
            close_reason_mapping_version=1,
            result_label=label,
            loss_predicate_format_version=1,
            recorded_at=_instant(),
            arbitration_record_ref=_fp("arb-2"),
        )
    )
    assert other.virtual_position_ref != first.virtual_position_ref


def test_api_door_matches_execution_port_surface() -> None:
    assert api.PORT_ROLES is qmb.PORT_ROLES is PORT_ROLES
    assert api.COMPOSITION_ORDER is qmb.COMPOSITION_ORDER
    assert api.FillPort is qmb.FillPort is FillPort
    assert api.SlippagePort is qmb.SlippagePort is SlippagePort
    assert api.CostPort is qmb.CostPort is CostPort
    assert api.FinancingPort is qmb.FinancingPort is FinancingPort
    assert api.execute_authorized is qmb.execute_authorized is execute_authorized
    assert api.record_virtual_close is qmb.record_virtual_close
    assert api.refuse_store_synthetic_governed_evidence is (
        qmb.refuse_store_synthetic_governed_evidence
    )
    assert api.TAINT_OPTIMISTIC == qmb.TAINT_OPTIMISTIC == TAINT_OPTIMISTIC
