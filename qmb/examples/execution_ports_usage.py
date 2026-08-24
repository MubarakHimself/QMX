"""Reference usage — CT-23 intents, execution ports, CT-29 exits (Story 14.5).

Executable::

    python qmb/examples/execution_ports_usage.py

Shows the things B-6 / AR-56 / CT-23 / CT-29 / SC-06 pin down:

1. Inbound execution is a CT-23 authorized intent, never a bot-sized order.
2. An AD-40 full-loss price is required before any open.
3. Fill, slippage, and cost are SEPARATE ``typing.Protocol`` seams (Epic 17
   implements adapters); fill decides ``Fill | NoFill | PartialFill``.
4. One CT-29 exit record per virtual close; bot-proposed exits are
   risk-monotonic.
5. Every fill carries an ``optimistic`` taint until GAP-0048.
6. Store-persisted synthetic data is ``world=simulated`` and a policy
   rejection for governed evidence.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    PROVENANCE_SYNTHETIC_TAINTED,
    mint_replay_binding,
)
from qmb.execution import (
    COMPOSITION_ORDER,
    PORT_ROLES,
    TAINT_OPTIMISTIC,
    CostedFill,
    CostPort,
    ExecutionPorts,
    Fill,
    FillPort,
    FinancingPort,
    NoFill,
    PartialFill,
    SlicePath,
    SlippagePort,
    admit_open,
    apply_execution_ports,
    evaluate_exit,
    execute_authorized,
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
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.risk.door import (
    Direction,
    EntryIntent,
    ExitIntent,
    ExitKind,
    ExitLogicRef,
    ReasonCode,
    StopMoveDirection,
    TightenProtectiveStop,
)
from qmf.risk.exit_record import CloseOutcome, CloseReason, ClosingAuthority, ExitResultLabel
from qmf.risk.paper import ExecutionTarget

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant() -> Instant:
    return _unwrap(Instant.try_create(_NS), "instant")


def _fp(seed: str):
    return _unwrap(fingerprint({"seed": seed}), seed)


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="venue-replay"), symbol="EURUSD")


def _price() -> Price:
    return _unwrap(Price.try_create(1_10000, _instrument(), 5), "price")


def _qty(value: int) -> Quantity:
    return _unwrap(Quantity.try_create(value, "lot", 0), "quantity")


def _decision(
    result: Result[Fill] | Result[NoFill] | Result[PartialFill],
) -> Result[Fill | NoFill | PartialFill]:
    if isinstance(result, TypedRefusal):
        return result
    value: Fill | NoFill | PartialFill = result.value
    return Ok(value)


def _costed(result: Result[CostedFill | NoFill], what: str) -> CostedFill:
    value = _unwrap(result, what)
    if not isinstance(value, CostedFill):
        raise AssertionError(f"expected {what} to be a costed fill, got {value}")
    return value


class _OffsetStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        del cited_evidence
        value = entry_price.value - 500 if direction is Direction.LONG else entry_price.value + 500
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class _FillRequested:
    def decide(
        self,
        intent: EntryIntent | ExitIntent,
        path: SlicePath,
        *,
        requested_quantity: Quantity,
    ) -> Result[Fill | NoFill | PartialFill]:
        del intent
        return _decision(Fill.try_create(requested_quantity, requested_quantity, path.prints[0]))


class _FillPartial:
    def decide(
        self,
        intent: EntryIntent | ExitIntent,
        path: SlicePath,
        *,
        requested_quantity: Quantity,
    ) -> Result[Fill | NoFill | PartialFill]:
        del intent
        half = _unwrap(
            Quantity.try_create(1, requested_quantity.unit, requested_quantity.scale),
            "half",
        )
        return _decision(PartialFill.try_create(half, requested_quantity, path.prints[0]))


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


class _ZeroCost:
    def itemize(self, fill: Fill | PartialFill) -> Result[CostedFill]:
        return CostedFill.try_create(fill, ())


class _SilentFinancing:
    def schedule(self, *, stream_id: str, direction: object) -> Result[Money]:
        del stream_id, direction
        return Ok(Money(value=0, currency="USD", scale=2))


def _ports(fill: object | None = None) -> ExecutionPorts:
    return _unwrap(
        ExecutionPorts.try_create(
            fill or _FillRequested(),
            _PassThroughSlip(),
            _ZeroCost(),
            _SilentFinancing(),
        ),
        "ports",
    )


def _binding():
    return _unwrap(
        mint_replay_binding(
            book_fp1=_fp("book"),
            bms_fp1=_fp("bms"),
            bot_fp1=_fp("bot"),
            starting_capital=Money(value=1_000_000, currency="USD", scale=2),
            seed_overridden=False,
            venue_id="venue-replay",
            account_id="acct-replay",
            clock=CLOCK_REPLAY,
            data_provenance=PROVENANCE_RECORDED,
            keys={},
        ),
        "binding",
    )


def _entry() -> EntryIntent:
    return _unwrap(
        EntryIntent.try_create(
            _instrument(),
            Direction.LONG,
            _unwrap(ReasonCode.try_create("breakout", "scalper-v1"), "reason"),
            _unwrap(
                ExecutionTarget.try_create("demo", VenueId(value="venue-replay"), "acct-replay"),
                "target",
            ),
        ),
        "entry",
    )


def pinned_separate_ports() -> None:
    """Fill, slippage, and cost are separate Protocol seams; financing is not a fill."""
    assert PORT_ROLES == ("fill", "slippage", "cost", "financing")
    assert COMPOSITION_ORDER == ("fill", "slippage", "cost")
    assert isinstance(_FillRequested(), FillPort)
    assert isinstance(_PassThroughSlip(), SlippagePort)
    assert isinstance(_ZeroCost(), CostPort)
    assert isinstance(_SilentFinancing(), FinancingPort)
    assert FillPort is not SlippagePort


def authorized_intent_never_bot_sized() -> None:
    """CT-23 intent or typed refusal; full-loss required before open."""
    intent = _entry()
    assert _unwrap(require_authorized_intent(intent), "authorized") is intent

    class _BotSized:
        size = 1.0

    refused = require_authorized_intent(_BotSized())
    assert is_refusal(refused)
    binding = _binding()
    admitted = _unwrap(
        admit_open(
            binding,
            intent=intent,
            entry_price=_price(),
            exit_logic_ref=_unwrap(
                ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}),
                "logic",
            ),
            module=_OffsetStopModule(),
            book_resolved_requested_r=_unwrap(
                ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE), "requested_r"
            ),
        ),
        "admitted",
    )
    assert admitted.declared_full_loss_price is not None
    assert is_refusal(require_full_loss_before_open(None))


def fill_decisions_and_optimistic_taint() -> None:
    """Fill | NoFill | PartialFill; every fill is optimistic-tainted."""
    path = _unwrap(SlicePath.try_create("eurusd", (_price(),)), "path")
    full = _costed(
        apply_execution_ports(
            _ports(),
            intent=_entry(),
            path=path,
            requested_quantity=_qty(2),
            position_cap=_qty(2),
            lot_step=_qty(1),
        ),
        "fill",
    )
    assert isinstance(full.fill, Fill)
    assert full.fill.taint == TAINT_OPTIMISTIC
    partial = _costed(
        apply_execution_ports(
            _ports(_FillPartial()),
            intent=_entry(),
            path=path,
            requested_quantity=_qty(2),
            position_cap=_qty(2),
            lot_step=_qty(1),
        ),
        "partial",
    )
    assert isinstance(partial.fill, PartialFill)
    assert is_refusal(refuse_optimistic_edge_claim(claims_edge=True))


def one_exit_and_risk_monotonic() -> None:
    """One CT-29 record per virtual close; bot-proposed exits are risk-reducing."""
    binding = _binding()
    closing = _unwrap(
        ExitIntent.try_create(
            ExitKind.CLOSE_FULL,
            _unwrap(ReasonCode.try_create("done", "scalper-v1"), "reason"),
            _fp("vp-1"),
        ),
        "exit",
    )
    evaluated = _unwrap(evaluate_exit(binding, closing), "evaluated")
    assert evaluated.kind is ExitKind.CLOSE_FULL
    widen = TightenProtectiveStop.try_create(
        StopMoveDirection.WIDEN,
        _unwrap(PriceDelta.try_create(10, _instrument(), 5), "bound"),
    )
    assert is_refusal(widen)
    position = _fp("pos-1")
    record = _unwrap(
        record_virtual_close(
            binding,
            virtual_position_ref=position,
            opening_bot_id="bot-alpha",
            original_risk_distance=_unwrap(PriceDelta.try_create(50, _instrument(), 5), "distance"),
            original_risk_amount=Money(value=10_000, currency="USD", scale=2),
            fill_references=(_fp("fill-1"),),
            realized_pnl=Money(value=-10_000, currency="USD", scale=2),
            cost_components=(),
            close_reason=CloseReason.BOT_INTENT,
            mechanism=CloseReason.BOT_INTENT,
            outcome=CloseOutcome.LOSS,
            closing_authority=ClosingAuthority.BOOK_POLICY,
            close_reason_mapping_version=1,
            result_label=_unwrap(ExitResultLabel.try_create("demo", World.REPLAY), "label"),
            loss_predicate_format_version=1,
            recorded_at=_instant(),
            arbitration_record_ref=_fp("arb-1"),
        ),
        "exit record",
    )
    assert record.binding_epoch == binding.fingerprint
    second = record_virtual_close(
        binding,
        closed_refs=(record,),
        virtual_position_ref=position,
        opening_bot_id="bot-alpha",
        original_risk_distance=_unwrap(PriceDelta.try_create(50, _instrument(), 5), "distance"),
        original_risk_amount=Money(value=10_000, currency="USD", scale=2),
        fill_references=(_fp("fill-1"),),
        realized_pnl=Money(value=-10_000, currency="USD", scale=2),
        cost_components=(),
        close_reason=CloseReason.BOT_INTENT,
        mechanism=CloseReason.BOT_INTENT,
        outcome=CloseOutcome.LOSS,
        closing_authority=ClosingAuthority.BOOK_POLICY,
        close_reason_mapping_version=1,
        result_label=_unwrap(ExitResultLabel.try_create("demo", World.REPLAY), "label"),
        loss_predicate_format_version=1,
        recorded_at=_instant(),
        arbitration_record_ref=_fp("arb-1"),
    )
    assert is_refusal(second)


def synthetic_store_is_policy_rejection() -> None:
    """Store-persisted synthetic data is world=simulated until GAP-0048."""
    refused = refuse_store_synthetic_governed_evidence(PROVENANCE_SYNTHETIC_TAINTED)
    assert is_refusal(refused)
    executed = execute_authorized(
        _binding(),
        intent=_entry(),
        ports=_ports(),
        path=_unwrap(SlicePath.try_create("eurusd", (_price(),)), "path"),
        requested_quantity=_qty(1),
        position_cap=_qty(1),
        lot_step=_qty(1),
        data_provenance=PROVENANCE_SYNTHETIC_TAINTED,
        entry_price=_price(),
        exit_logic_ref=_unwrap(
            ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}),
            "logic",
        ),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_unwrap(
            ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE), "requested_r"
        ),
    )
    assert is_refusal(executed)


def main() -> None:
    assert qmb.PORT_ROLES == PORT_ROLES
    assert qmb.COMPOSITION_ORDER == COMPOSITION_ORDER
    pinned_separate_ports()
    print("fill, slippage, and cost are separate Protocol seams")
    authorized_intent_never_bot_sized()
    print("CT-23 authorized intent; never a bot-sized order")
    print("full-loss price required before open")
    fill_decisions_and_optimistic_taint()
    print("partial fill is first-class")
    print("optimistic taint on every fill")
    one_exit_and_risk_monotonic()
    print("one CT-29 exit per virtual close")
    print("bot-proposed exits are risk-monotonic")
    synthetic_store_is_policy_rejection()
    print("store-persisted synthetic is world=simulated policy rejection")
    print("execution ports ok")


if __name__ == "__main__":
    main()
