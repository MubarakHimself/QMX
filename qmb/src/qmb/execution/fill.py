"""Declared-path fill crossing (FILL-2..FILL-8, Story 17.3).

The fill port decides ``Fill | NoFill | PartialFill`` and a pre-slip price by
crossing the slice's declared path, dispatched per order type. Default pricing
is bar-worst-case; optimistic-exact is a labeled mode. Both stay
``optimistic``-tainted until GAP-0048. All-or-none: any leg fail → NoFill for
the whole group.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core.chrono import Duration, Instant
from qmf.core.exact import Price, PriceDelta, Quantity
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.door import Direction, EntryIntent

from qmb._refuse import clean_token, invalid
from qmb.execution.ports import (
    FILL_BASES,
    FILL_BASIS_OPTIMISTIC_EXACT,
    FILL_BASIS_WORST_CASE,
    TAINT_OPTIMISTIC,
    AuthorizedIntent,
    Fill,
    FillDecision,
    NoFill,
    PartialFill,
    SlicePath,
    classify_fill_quantity,
    require_authorized_intent,
)

__all__ = [
    "FILL_BASES",
    "FILL_BASIS_KEY",
    "FILL_BASIS_OPTIMISTIC_EXACT",
    "FILL_BASIS_WORST_CASE",
    "NOFILL_ALL_OR_NONE_LEG_FAILED",
    "NOFILL_INSUFFICIENT_LIQUIDITY",
    "NOFILL_MARKET_CLOSED",
    "NOFILL_NOT_TRIGGERED",
    "NOFILL_REASONS",
    "NOFILL_STALE_DATA",
    "ORDER_TYPES",
    "STALE_PRICE_SPAN_KEY",
    "FillLeg",
    "FillOrder",
    "OrderType",
    "cross_declared_path",
    "default_fill_order",
    "fill_all_or_none",
    "fill_pipeline_identity",
    "path_ohlc",
    "rank_resting_on_path",
    "split_path_at",
]

FILL_BASIS_KEY: Final[str] = "fill_basis"
STALE_PRICE_SPAN_KEY: Final[str] = "stale_price_span"
NOFILL_MARKET_CLOSED: Final[str] = "market_closed"
NOFILL_STALE_DATA: Final[str] = "stale_data"
NOFILL_NOT_TRIGGERED: Final[str] = "not_triggered"
NOFILL_INSUFFICIENT_LIQUIDITY: Final[str] = "insufficient_liquidity"
NOFILL_ALL_OR_NONE_LEG_FAILED: Final[str] = "all_or_none_leg_failed"
NOFILL_REASONS: Final[tuple[str, ...]] = (
    NOFILL_MARKET_CLOSED,
    NOFILL_STALE_DATA,
    NOFILL_NOT_TRIGGERED,
    NOFILL_INSUFFICIENT_LIQUIDITY,
    NOFILL_ALL_OR_NONE_LEG_FAILED,
)


class OrderType(StrEnum):
    """Order types the fill port dispatches (FILL-2)."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop-limit"
    TRAILING_STOP = "trailing-stop"
    MARKET_ON_OPEN = "market-on-open"
    MARKET_ON_CLOSE = "market-on-close"
    ALL_OR_NONE = "all-or-none"


ORDER_TYPES: Final[tuple[str, ...]] = tuple(member.value for member in OrderType)

_PASSIVE_LIMITS: Final[frozenset[OrderType]] = frozenset({OrderType.LIMIT, OrderType.STOP_LIMIT})


def fill_pipeline_identity() -> dict[str, object]:
    """Identity-bearing fill-pipeline fields. Package SemVer is omitted."""
    return {
        "default_fill_basis": FILL_BASIS_WORST_CASE,
        "fill_bases": FILL_BASES,
        "nofill_reasons": NOFILL_REASONS,
        "order_types": ORDER_TYPES,
        "same_slice_new_intent_fill": False,
        "taint_field": TAINT_OPTIMISTIC,
    }


@dataclass(frozen=True, slots=True)
class FillOrder:
    """Resting order ticket the fill port dispatches against a slice path."""

    order_type: OrderType
    side: Direction
    quantity: Quantity
    limit_price: Price | None = None
    stop_price: Price | None = None
    trail_distance: PriceDelta | None = None
    trail_extreme: Price | None = None
    submitted_at: Instant | None = None
    evaluated_at: Instant | None = None
    group_id: str | None = None
    reduce_only: bool = False
    position_quantity: Quantity | None = None
    lot_step: Quantity | None = None
    liquidity: Quantity | None = None
    fee_reference: str | None = None
    intent_id: str | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content: dict[str, object] = {
            "class": "fill-order",
            "order_type": self.order_type.value,
            "quantity": self.quantity.fp1_identity(),
            "reduce_only": self.reduce_only,
            "side": self.side.value,
        }
        if self.limit_price is not None:
            content["limit_price"] = self.limit_price.fp1_identity()
        if self.stop_price is not None:
            content["stop_price"] = self.stop_price.fp1_identity()
        if self.trail_distance is not None:
            content["trail_distance"] = self.trail_distance.fp1_identity()
        if self.trail_extreme is not None:
            content["trail_extreme"] = self.trail_extreme.fp1_identity()
        if self.submitted_at is not None:
            content["submitted_at_ns"] = self.submitted_at.value_ns
        if self.group_id is not None:
            content["group_id"] = self.group_id
        if self.position_quantity is not None:
            content["position_quantity"] = self.position_quantity.fp1_identity()
        if self.lot_step is not None:
            content["lot_step"] = self.lot_step.fp1_identity()
        if self.liquidity is not None:
            content["liquidity"] = self.liquidity.fp1_identity()
        if self.fee_reference is not None:
            content["fee_reference"] = self.fee_reference
        if self.intent_id is not None:
            content["intent_id"] = self.intent_id
        return content

    @classmethod
    def try_create(
        cls,
        order_type: object,
        side: object,
        quantity: object,
        *,
        limit_price: object = None,
        stop_price: object = None,
        trail_distance: object = None,
        trail_extreme: object = None,
        submitted_at: object = None,
        evaluated_at: object = None,
        group_id: object = None,
        reduce_only: object = False,
        position_quantity: object = None,
        lot_step: object = None,
        liquidity: object = None,
        fee_reference: object = None,
        intent_id: object = None,
    ) -> Result[FillOrder]:
        """Validate a resting fill ticket."""
        typed = _coerce_order_type(order_type)
        if is_refusal(typed):
            return typed
        if not isinstance(side, Direction):
            return invalid(
                "side",
                "fill side is Direction.LONG (buy) or Direction.SHORT (sell)",
                given=repr(type(side).__name__),
            )
        qty = _require_qty(quantity, "quantity")
        if is_refusal(qty):
            return qty
        if qty.value.as_fraction() <= 0:
            return invalid(
                "quantity",
                "an order quantity is a positive exact count",
                given=str(qty.value.as_fraction()),
            )
        limit = _optional_price(limit_price, "limit_price")
        if is_refusal(limit):
            return limit
        stop = _optional_price(stop_price, "stop_price")
        if is_refusal(stop):
            return stop
        trail = _optional_delta(trail_distance, "trail_distance")
        if is_refusal(trail):
            return trail
        extreme = _optional_price(trail_extreme, "trail_extreme")
        if is_refusal(extreme):
            return extreme
        submitted = _optional_instant(submitted_at, "submitted_at")
        if is_refusal(submitted):
            return submitted
        evaluated = _optional_instant(evaluated_at, "evaluated_at")
        if is_refusal(evaluated):
            return evaluated
        if not isinstance(reduce_only, bool):
            return invalid(
                "reduce_only",
                "reduce_only is a bool; a reduce-only fill caps at open position size",
                given=repr(type(reduce_only).__name__),
            )
        group = _optional_token(group_id, "group_id")
        if is_refusal(group):
            return group
        position = _optional_qty(position_quantity, "position_quantity")
        if is_refusal(position):
            return position
        step = _optional_qty(lot_step, "lot_step")
        if is_refusal(step):
            return step
        depth = _optional_qty(liquidity, "liquidity")
        if is_refusal(depth):
            return depth
        fee = _optional_token(fee_reference, "fee_reference")
        if is_refusal(fee):
            return fee
        iid = _optional_token(intent_id, "intent_id")
        if is_refusal(iid):
            return iid
        needed_limit = typed.value in {OrderType.LIMIT, OrderType.STOP_LIMIT}
        needed_stop = typed.value in {
            OrderType.STOP,
            OrderType.STOP_LIMIT,
        }
        if needed_limit and limit.value is None:
            return invalid(
                "limit_price",
                "limit and stop-limit orders name an exact limit price",
                order_type=typed.value.value,
            )
        if needed_stop and stop.value is None:
            return invalid(
                "stop_price",
                "stop and stop-limit orders name an exact stop price",
                order_type=typed.value.value,
            )
        if typed.value is OrderType.TRAILING_STOP and trail.value is None:
            return invalid(
                "trail_distance",
                "a trailing-stop names an exact PriceDelta trail distance",
            )
        if trail.value is not None and trail.value.as_fraction() <= 0:
            return invalid(
                "trail_distance",
                "a trail distance is a positive exact PriceDelta",
                given=str(trail.value.as_fraction()),
            )
        return Ok(
            cls(
                order_type=typed.value,
                side=side,
                quantity=qty.value,
                limit_price=limit.value,
                stop_price=stop.value,
                trail_distance=trail.value,
                trail_extreme=extreme.value,
                submitted_at=submitted.value,
                evaluated_at=evaluated.value,
                group_id=group.value,
                reduce_only=reduce_only,
                position_quantity=position.value,
                lot_step=step.value,
                liquidity=depth.value,
                fee_reference=fee.value,
                intent_id=iid.value,
            )
        )


@dataclass(frozen=True, slots=True)
class FillLeg:
    """One all-or-none group member (FILL-2)."""

    intent: AuthorizedIntent
    order: FillOrder
    requested_quantity: Quantity

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "class": "fill-leg",
            "order": self.order.fp1_identity(),
            "requested_quantity": self.requested_quantity.fp1_identity(),
        }

    @classmethod
    def try_create(
        cls,
        intent: object,
        order: object,
        requested_quantity: object = None,
    ) -> Result[FillLeg]:
        """Validate one AON leg."""
        authorized = require_authorized_intent(intent)
        if is_refusal(authorized):
            return authorized
        if not isinstance(order, FillOrder):
            return invalid(
                "order",
                "an all-or-none leg carries a FillOrder ticket",
                given=repr(type(order).__name__),
            )
        qty = order.quantity if requested_quantity is None else requested_quantity
        parsed = _require_qty(qty, "requested_quantity")
        if is_refusal(parsed):
            return parsed
        return Ok(cls(intent=authorized.value, order=order, requested_quantity=parsed.value))


def default_fill_order(intent: object, requested_quantity: object) -> Result[FillOrder]:
    """Market ticket from a CT-23 intent when the caller omitted a FillOrder."""
    authorized = require_authorized_intent(intent)
    if is_refusal(authorized):
        return authorized
    if isinstance(authorized.value, EntryIntent):
        side = authorized.value.direction
    else:
        side = Direction.SHORT
    return FillOrder.try_create(OrderType.MARKET, side, requested_quantity)


def path_ohlc(path: object) -> Result[tuple[Price, Price, Price, Price]]:
    """Open/high/low/close from declared levels, else from the print path."""
    if not isinstance(path, SlicePath):
        return invalid(
            "path",
            "OHLC is read from a declared SlicePath",
            given=repr(type(path).__name__),
        )
    opening, high, low, closing = path.open, path.high, path.low, path.close
    if opening is not None and high is not None and low is not None and closing is not None:
        return Ok((opening, high, low, closing))
    if not path.prints:
        return invalid(
            "prints",
            "a slice path needs prints or declared OHLC for crossing",
        )
    opening = path.open if path.open is not None else path.prints[0]
    closing = path.close if path.close is not None else path.prints[-1]
    high = path.high if path.high is not None else _extreme(path.prints, high=True)
    low = path.low if path.low is not None else _extreme(path.prints, high=False)
    return Ok((opening, high, low, closing))


def cross_declared_path(
    intent: object,
    path: object,
    *,
    requested_quantity: object,
    order: object = None,
    fill_basis: object = FILL_BASIS_WORST_CASE,
    stale_price_span: object = None,
) -> Result[Fill | NoFill | PartialFill]:
    """Decide Fill/NoFill/PartialFill by crossing the declared path (FILL-2)."""
    authorized = require_authorized_intent(intent)
    if is_refusal(authorized):
        return authorized
    if not isinstance(path, SlicePath):
        return invalid(
            "path",
            "the fill port crosses a declared SlicePath inside the slice",
            given=repr(type(path).__name__),
        )
    ticket = _require_order(order, authorized.value, requested_quantity)
    if is_refusal(ticket):
        return ticket
    basis = _require_basis(fill_basis)
    if is_refusal(basis):
        return basis
    if path.market_closed:
        return _nofill_value(NOFILL_MARKET_CLOSED)
    stale = _stale_guard(ticket.value, path, stale_price_span)
    if is_refusal(stale):
        return stale
    if stale.value:
        return _nofill_value(NOFILL_STALE_DATA)
    if ticket.value.order_type is OrderType.ALL_OR_NONE:
        return _nofill_value(NOFILL_ALL_OR_NONE_LEG_FAILED)
    ohlc = path_ohlc(path)
    if is_refusal(ohlc):
        return ohlc
    opening, high, low, closing = ohlc.value
    current = path.current if path.current is not None else opening
    priced = _dispatch(
        ticket.value,
        path=path,
        opening=opening,
        high=high,
        low=low,
        closing=closing,
        current=current,
        fill_basis=basis.value,
    )
    if is_refusal(priced):
        return priced
    if isinstance(priced.value, NoFill):
        return _as_fill(priced.value)
    pre_slip, gap = priced.value
    return _emit(
        ticket.value,
        requested_quantity=ticket.value.quantity,
        pre_slip=pre_slip,
        fill_basis=basis.value,
        gap_fill=gap,
    )


def fill_all_or_none(
    legs: object,
    path: object,
    *,
    fill_basis: object = FILL_BASIS_WORST_CASE,
    stale_price_span: object = None,
) -> Result[tuple[FillDecision, ...]]:
    """Any failing AON leg returns NoFill for the whole group (FILL-2)."""
    parsed = _as_legs(legs)
    if is_refusal(parsed):
        return parsed
    if not parsed.value:
        return invalid("legs", "an all-or-none group names one or more legs")
    decisions: list[FillDecision] = []
    failed = False
    for leg in parsed.value:
        decided = cross_declared_path(
            leg.intent,
            path,
            requested_quantity=leg.requested_quantity,
            order=leg.order,
            fill_basis=fill_basis,
            stale_price_span=stale_price_span,
        )
        if is_refusal(decided):
            return decided
        decisions.append(decided.value)
        if not isinstance(decided.value, Fill):
            failed = True
    if not failed:
        return Ok(tuple(decisions))
    none = _nofill(NOFILL_ALL_OR_NONE_LEG_FAILED)
    if is_refusal(none):
        return none
    return Ok(tuple(none.value for _ in decisions))


def rank_resting_on_path(intents: object, path: object) -> Result[tuple[object, ...]]:
    """Deterministic intra-slice order by first-cross along the declared path (FILL-6)."""
    if isinstance(intents, (str, bytes)) or not isinstance(intents, Sequence):
        return invalid(
            "intents",
            "intra-slice sequencing ranks a sequence of resting intents",
            given=repr(type(intents).__name__),
        )
    if not isinstance(path, SlicePath):
        return invalid(
            "path",
            "sequencing splits a declared SlicePath",
            given=repr(type(path).__name__),
        )
    scored: list[tuple[int, object, object]] = []
    for index, raw in enumerate(cast("Sequence[object]", intents)):
        order = getattr(raw, "order", None)
        if not isinstance(order, FillOrder):
            scored.append((10_000 + index, None, raw))
            continue
        first = _first_cross_index(order, path)
        scored.append((first, getattr(raw, "intent_id", str(index)), raw))
    scored.sort(key=lambda item: (item[0], str(item[1])))
    return Ok(tuple(item[2] for item in scored))


def split_path_at(path: object, price: object) -> Result[SlicePath]:
    """Remaining path starts at the fill price (Jesse split_candle, FILL-6)."""
    if not isinstance(path, SlicePath):
        return invalid(
            "path",
            "path splitting consumes a declared SlicePath",
            given=repr(type(path).__name__),
        )
    if not isinstance(price, Price):
        return invalid(
            "price",
            "the split is an exact fill Price",
            given=repr(type(price).__name__),
        )
    remaining: list[Price] = [price]
    passed = False
    for print_ in path.prints:
        if passed:
            remaining.append(print_)
            continue
        if _same(print_, price) or _between_last(remaining[-1], print_, price):
            passed = True
            if not _same(print_, price):
                remaining.append(print_)
    if len(remaining) == 1 and path.prints:
        remaining.extend(path.prints)
    return SlicePath.try_create(
        path.stream_id,
        tuple(remaining),
        open=price,
        high=path.high,
        low=path.low,
        close=path.close,
        current=price,
        prior_close=path.prior_close,
        bar_start=path.bar_start,
        bar_end=path.bar_end,
        session_open=False,
        session_close=path.session_close,
        market_closed=path.market_closed,
        bid=path.bid,
        ask=path.ask,
    )


def _dispatch(
    order: FillOrder,
    *,
    path: SlicePath,
    opening: Price,
    high: Price,
    low: Price,
    closing: Price,
    current: Price,
    fill_basis: str,
) -> Result[tuple[Price, bool] | NoFill]:
    kind = order.order_type
    if kind is OrderType.MARKET:
        return _market(order, path, opening, high, low, closing, current, fill_basis)
    if kind is OrderType.LIMIT:
        return _limit(order, path, opening, high, low, fill_basis)
    if kind is OrderType.STOP:
        return _stop(order, path, opening, high, low, current, fill_basis)
    if kind is OrderType.STOP_LIMIT:
        return _stop_limit(order, path, opening, high, low, fill_basis)
    if kind is OrderType.TRAILING_STOP:
        return _trailing_stop(order, path, opening, high, low, current, fill_basis)
    if kind is OrderType.MARKET_ON_OPEN:
        if not path.session_open:
            return _priced_none(NOFILL_NOT_TRIGGERED)
        gapped = _gap_through_market(order, path, opening)
        if gapped is not None:
            return _priced_hit(gapped, True)
        return _priced_hit(opening, False)
    if kind is OrderType.MARKET_ON_CLOSE:
        if not path.session_close:
            return _priced_none(NOFILL_NOT_TRIGGERED)
        return _priced_hit(closing, False)
    return invalid("order_type", "unknown order type", given=kind.value)


def _market(
    order: FillOrder,
    path: SlicePath,
    opening: Price,
    high: Price,
    low: Price,
    closing: Price,
    current: Price,
    fill_basis: str,
) -> Result[tuple[Price, bool] | NoFill]:
    del path, opening, closing
    if fill_basis == FILL_BASIS_OPTIMISTIC_EXACT:
        return _priced_hit(current, False)
    worst = high if _is_buy(order) else low
    return _priced_hit(worst, False)


def _limit(
    order: FillOrder,
    path: SlicePath,
    opening: Price,
    high: Price,
    low: Price,
    fill_basis: str,
) -> Result[tuple[Price, bool] | NoFill]:
    limit = order.limit_price
    if limit is None:
        return invalid("limit_price", "a limit order names an exact limit price")
    gapped = _gap_through_limit(order, path, opening, limit)
    if gapped is not None:
        return _priced_hit(gapped, True)
    if not _limit_crossed(order, high, low, limit):
        return _priced_none(NOFILL_NOT_TRIGGERED)
    if fill_basis == FILL_BASIS_OPTIMISTIC_EXACT:
        return _priced_hit(limit, False)
    if _is_buy(order):
        return _priced_hit(_min_price(high, limit), False)
    return _priced_hit(_max_price(low, limit), False)


def _stop(
    order: FillOrder,
    path: SlicePath,
    opening: Price,
    high: Price,
    low: Price,
    current: Price,
    fill_basis: str,
) -> Result[tuple[Price, bool] | NoFill]:
    stop = order.stop_price
    if stop is None:
        return invalid("stop_price", "a stop order names an exact stop price")
    gapped = _gap_through_stop(order, path, opening, stop)
    if gapped is not None:
        return _priced_hit(gapped, True)
    if not _stop_triggered(order, high, low, stop):
        return _priced_none(NOFILL_NOT_TRIGGERED)
    if fill_basis == FILL_BASIS_OPTIMISTIC_EXACT:
        return _priced_hit(stop, False)
    if _is_buy(order):
        return _priced_hit(_max_price(stop, current), False)
    return _priced_hit(_min_price(stop, current), False)


def _stop_limit(
    order: FillOrder,
    path: SlicePath,
    opening: Price,
    high: Price,
    low: Price,
    fill_basis: str,
) -> Result[tuple[Price, bool] | NoFill]:
    stop = order.stop_price
    limit = order.limit_price
    if stop is None or limit is None:
        return invalid(
            "stop_price",
            "a stop-limit names both an exact stop and an exact limit",
        )
    if (
        not _stop_triggered(order, high, low, stop)
        and _gap_through_stop(order, path, opening, stop) is None
    ):
        return _priced_none(NOFILL_NOT_TRIGGERED)
    return _limit(order, path, opening, high, low, fill_basis)


def _trailing_stop(
    order: FillOrder,
    path: SlicePath,
    opening: Price,
    high: Price,
    low: Price,
    current: Price,
    fill_basis: str,
) -> Result[tuple[Price, bool] | NoFill]:
    trail = order.trail_distance
    if trail is None:
        return invalid("trail_distance", "a trailing-stop names a trail distance")
    if _is_buy(order):
        extreme = low if order.trail_extreme is None else _min_price(low, order.trail_extreme)
        stop = extreme.add(trail)
    else:
        extreme = high if order.trail_extreme is None else _max_price(high, order.trail_extreme)
        negated = PriceDelta.try_create(-abs(trail.value), trail.instrument, trail.scale)
        if is_refusal(negated):
            return negated
        stop = extreme.add(negated.value)
    if is_refusal(stop):
        return stop
    synthetic = FillOrder.try_create(
        OrderType.STOP,
        order.side,
        order.quantity,
        stop_price=stop.value,
        submitted_at=order.submitted_at,
        evaluated_at=order.evaluated_at,
        reduce_only=order.reduce_only,
        position_quantity=order.position_quantity,
        lot_step=order.lot_step,
        liquidity=order.liquidity,
        fee_reference=order.fee_reference,
        intent_id=order.intent_id,
    )
    if is_refusal(synthetic):
        return synthetic
    return _stop(synthetic.value, path, opening, high, low, current, fill_basis)


def _emit(
    order: FillOrder,
    *,
    requested_quantity: Quantity,
    pre_slip: Price,
    fill_basis: str,
    gap_fill: bool,
) -> Result[Fill | NoFill | PartialFill]:
    fillable = requested_quantity
    if order.liquidity is not None:
        if order.liquidity.as_fraction() <= 0:
            return _nofill_value(NOFILL_INSUFFICIENT_LIQUIDITY)
        if order.liquidity.as_fraction() < fillable.as_fraction():
            fillable = order.liquidity
    if order.reduce_only:
        position = order.position_quantity
        if position is None or position.as_fraction() <= 0:
            return _nofill_value(NOFILL_INSUFFICIENT_LIQUIDITY)
        if position.as_fraction() < fillable.as_fraction():
            fillable = position
    cap = fillable
    if order.position_quantity is not None and order.position_quantity.as_fraction() > 0:
        if order.reduce_only:
            cap = order.position_quantity
        elif order.position_quantity.as_fraction() < requested_quantity.as_fraction():
            cap = min_qty(order.position_quantity, fillable)
        else:
            cap = fillable
    if order.lot_step is not None:
        step_qty = order.lot_step
    else:
        built = _unit_step(requested_quantity)
        if is_refusal(built):
            return built
        step_qty = built.value
    fee = order.fee_reference
    if fee is None and fillable.as_fraction() < requested_quantity.as_fraction():
        fee = order.intent_id
    classified = classify_fill_quantity(
        requested=requested_quantity,
        filled=fillable,
        position_cap=cap if cap.as_fraction() > 0 else requested_quantity,
        lot_step=step_qty,
        pre_slip_price=pre_slip,
        fill_basis=fill_basis,
        gap_fill=gap_fill,
        fee_reference=fee,
        order_type=order.order_type.value,
        side=order.side,
        passive=order.order_type in _PASSIVE_LIMITS,
    )
    if is_refusal(classified):
        return classified
    if isinstance(classified.value, NoFill) and classified.value.reason == "lot-step-snap-to-zero":
        return _nofill_value(NOFILL_INSUFFICIENT_LIQUIDITY)
    return classified


def _stale_guard(
    order: FillOrder,
    path: SlicePath,
    stale_price_span: object,
) -> Result[bool]:
    if (
        path.bar_end is not None
        and order.submitted_at is not None
        and path.bar_end.value_ns < order.submitted_at.value_ns
    ):
        return Ok(True)
    if order.order_type not in {
        OrderType.MARKET,
        OrderType.MARKET_ON_OPEN,
        OrderType.MARKET_ON_CLOSE,
    }:
        return Ok(False)
    if stale_price_span is None or path.bar_end is None:
        return Ok(False)
    if not isinstance(stale_price_span, Duration):
        return invalid(
            "stale_price_span",
            "stale_price_span is a Duration; market fills beyond it are NoFill stale_data",
            given=repr(type(stale_price_span).__name__),
        )
    evaluated = order.evaluated_at
    if evaluated is None:
        return Ok(False)
    age = evaluated.difference(path.bar_end)
    if is_refusal(age):
        return age
    return Ok(age.value.value_ns > stale_price_span.value_ns)


def _limit_crossed(order: FillOrder, high: Price, low: Price, limit: Price) -> bool:
    if _is_buy(order):
        return _leq(low, limit)
    return _geq(high, limit)


def _stop_triggered(order: FillOrder, high: Price, low: Price, stop: Price) -> bool:
    if _is_buy(order):
        return _geq(high, stop)
    return _leq(low, stop)


def _gap_through_market(order: FillOrder, path: SlicePath, opening: Price) -> Price | None:
    del order
    if path.prior_close is None:
        return None
    if not _same(path.prior_close, opening):
        return opening
    return None


def _gap_through_limit(
    order: FillOrder,
    path: SlicePath,
    opening: Price,
    limit: Price,
) -> Price | None:
    prior = path.prior_close
    if prior is None:
        return None
    if _is_buy(order) and _gt(prior, limit) and _leq(opening, limit):
        return opening
    if not _is_buy(order) and _lt(prior, limit) and _geq(opening, limit):
        return opening
    return None


def _gap_through_stop(
    order: FillOrder,
    path: SlicePath,
    opening: Price,
    stop: Price,
) -> Price | None:
    prior = path.prior_close
    if prior is None:
        return None
    if _is_buy(order) and _lt(prior, stop) and _geq(opening, stop):
        return opening
    if not _is_buy(order) and _gt(prior, stop) and _leq(opening, stop):
        return opening
    return None


def _first_cross_index(order: FillOrder, path: SlicePath) -> int:
    if not path.prints:
        ohlc = path_ohlc(path)
        if is_refusal(ohlc):
            return 10_000
        return 0
    running: list[Price] = []
    for index, print_ in enumerate(path.prints):
        running.append(print_)
        high = _extreme(tuple(running), high=True)
        low = _extreme(tuple(running), high=False)
        if order.order_type is OrderType.LIMIT and order.limit_price is not None:
            if _limit_crossed(order, high, low, order.limit_price):
                return index
        elif order.order_type in {OrderType.STOP, OrderType.STOP_LIMIT, OrderType.TRAILING_STOP}:
            stop = order.stop_price
            if stop is not None and _stop_triggered(order, high, low, stop):
                return index
        else:
            return 0
    return 10_000


def _is_buy(order: FillOrder) -> bool:
    return order.side is Direction.LONG


def _as_fill(value: Fill | NoFill | PartialFill) -> Result[Fill | NoFill | PartialFill]:
    return Ok(value)


def _nofill_value(reason: str) -> Result[Fill | NoFill | PartialFill]:
    none = NoFill.try_create(reason)
    if is_refusal(none):
        return none
    return _as_fill(none.value)


def _nofill(reason: str) -> Result[NoFill]:
    none = NoFill.try_create(reason)
    if is_refusal(none):
        return none
    return Ok(none.value)


def _priced_none(reason: str) -> Result[tuple[Price, bool] | NoFill]:
    none = NoFill.try_create(reason)
    if is_refusal(none):
        return none
    outcome: tuple[Price, bool] | NoFill = none.value
    return Ok(outcome)


def _priced_hit(price: Price, gap: bool) -> Result[tuple[Price, bool] | NoFill]:
    outcome: tuple[Price, bool] | NoFill = (price, gap)
    return Ok(outcome)


def _require_basis(value: object) -> Result[str]:
    if value is None:
        return Ok(FILL_BASIS_WORST_CASE)
    token = value if isinstance(value, str) else clean_token(value)
    if token not in {FILL_BASIS_WORST_CASE, FILL_BASIS_OPTIMISTIC_EXACT}:
        return invalid(
            "fill_basis",
            "fill basis is worst-case or optimistic-exact (FILL-4)",
            given=repr(value),
            allowed=list(FILL_BASES),
        )
    return Ok(token)


def _require_order(
    order: object,
    intent: AuthorizedIntent,
    requested_quantity: object,
) -> Result[FillOrder]:
    if order is None:
        return default_fill_order(intent, requested_quantity)
    if isinstance(order, FillOrder):
        return Ok(order)
    return invalid(
        "order",
        "the fill port dispatches a FillOrder ticket per order type (FILL-2)",
        given=repr(type(order).__name__),
    )


def _coerce_order_type(value: object) -> Result[OrderType]:
    if isinstance(value, OrderType):
        return Ok(value)
    token = clean_token(value)
    for member in OrderType:
        if member.value == token:
            return Ok(member)
    return invalid(
        "order_type",
        "order type is market, limit, stop, stop-limit, trailing-stop, "
        "market-on-open, market-on-close, or all-or-none (FILL-2)",
        given=repr(value),
        allowed=list(ORDER_TYPES),
    )


def _as_legs(value: object) -> Result[tuple[FillLeg, ...]]:
    if isinstance(value, FillLeg):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "legs",
            "an all-or-none group is a sequence of FillLeg values",
            given=repr(type(value).__name__),
        )
    parsed: list[FillLeg] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        if isinstance(raw, FillLeg):
            parsed.append(raw)
            continue
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            items = cast("Sequence[object]", raw)
            if len(items) < 2:
                return invalid(
                    "legs",
                    "each AON leg is a FillLeg",
                    index=index,
                )
            extra = items[2] if len(items) > 2 else None
            created = FillLeg.try_create(items[0], items[1], extra)
            if is_refusal(created):
                return created
            parsed.append(created.value)
            continue
        return invalid(
            "legs",
            "each AON leg is a FillLeg",
            index=index,
            given=repr(type(raw).__name__),
        )
    return Ok(tuple(parsed))


def _require_qty(value: object, field: str) -> Result[Quantity]:
    if isinstance(value, Quantity):
        return Ok(value)
    return invalid(
        field,
        "a fill quantity is an exact Quantity, never a binary float",
        given=repr(type(value).__name__),
    )


def _optional_qty(value: object, field: str) -> Result[Quantity | None]:
    if value is None:
        return Ok(None)
    parsed = _require_qty(value, field)
    if is_refusal(parsed):
        return parsed
    optional: Quantity | None = parsed.value
    return Ok(optional)


def _optional_price(value: object, field: str) -> Result[Price | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Price):
        return Ok(value)
    return invalid(
        field,
        "a fill price is an exact Price, never a binary float",
        given=repr(type(value).__name__),
    )


def _optional_delta(value: object, field: str) -> Result[PriceDelta | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, PriceDelta):
        return Ok(value)
    return invalid(
        field,
        "a trail distance is an exact PriceDelta",
        given=repr(type(value).__name__),
    )


def _optional_instant(value: object, field: str) -> Result[Instant | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Instant):
        return Ok(value)
    return invalid(
        field,
        "order timestamps are Instants in UTC nanoseconds",
        given=repr(type(value).__name__),
    )


def _optional_token(value: object, field: str) -> Result[str | None]:
    if value is None:
        return Ok(None)
    token = clean_token(value)
    if token is None:
        return invalid(
            field,
            "a non-empty token is required when this field is set",
            given=repr(value),
        )
    return Ok(token)


def _unit_step(quantity: Quantity) -> Result[Quantity]:
    return Quantity.try_create(1, quantity.unit, quantity.scale)


def min_qty(left: Quantity, right: Quantity) -> Quantity:
    """The smaller of two same-unit quantities (already validated together)."""
    if left.as_fraction() <= right.as_fraction():
        return left
    return right


def _extreme(prints: tuple[Price, ...], *, high: bool) -> Price:
    winner = prints[0]
    for item in prints[1:]:
        if (high and _gt(item, winner)) or (not high and _lt(item, winner)):
            winner = item
    return winner


def _min_price(left: Price, right: Price) -> Price:
    return left if _leq(left, right) else right


def _max_price(left: Price, right: Price) -> Price:
    return left if _geq(left, right) else right


def _same(left: Price, right: Price) -> bool:
    return left.as_fraction() == right.as_fraction()


def _lt(left: Price, right: Price) -> bool:
    return left.as_fraction() < right.as_fraction()


def _leq(left: Price, right: Price) -> bool:
    return left.as_fraction() <= right.as_fraction()


def _gt(left: Price, right: Price) -> bool:
    return left.as_fraction() > right.as_fraction()


def _geq(left: Price, right: Price) -> bool:
    return left.as_fraction() >= right.as_fraction()


def _between_last(previous: Price, nxt: Price, target: Price) -> bool:
    lo = previous.as_fraction()
    hi = nxt.as_fraction()
    mid = target.as_fraction()
    return (lo <= mid <= hi) or (hi <= mid <= lo)
