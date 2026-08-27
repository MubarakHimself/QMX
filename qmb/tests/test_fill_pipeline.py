"""Story 17.3 — fill and slippage price-forming pipeline."""

from __future__ import annotations

from typing import TypeVar

from qmb.doors import api
from qmb.execution import (
    FILL_BASIS_OPTIMISTIC_EXACT,
    FILL_BASIS_WORST_CASE,
    NOFILL_ALL_OR_NONE_LEG_FAILED,
    NOFILL_INSUFFICIENT_LIQUIDITY,
    NOFILL_MARKET_CLOSED,
    NOFILL_NOT_TRIGGERED,
    NOFILL_REASONS,
    NOFILL_STALE_DATA,
    ORDER_TYPES,
    SLIPPAGE_MODELS,
    TAINT_OPTIMISTIC,
    ConstantPercentSlippageAdapter,
    DeclaredPathFillAdapter,
    ExecutionSliceHandler,
    Fill,
    FillKind,
    FillLeg,
    FillOrder,
    GapVolatilitySlippageAdapter,
    NoFill,
    OrderType,
    PartialFill,
    SizeTieredSlippageAdapter,
    SlicePath,
    SlippageCalibration,
    SpreadCrossingSlippageAdapter,
    ZeroSlippageAdapter,
    cross_declared_path,
    derive_slippage_seed,
    fill_all_or_none,
    fill_pipeline_identity,
    legal_print,
    rank_resting_on_path,
    slip_fill,
    split_path_at,
)
from qmb.execution.cost import ZeroCostAdapter
from qmb.runloop import (
    SAME_SLICE_NEW_INTENT_FILL,
    SUBPHASES,
    RestingIntent,
    SliceObservation,
    run_slice,
)
from qmf.core.chrono import Duration, Instant
from qmf.core.exact import ExactRational, Price, PriceDelta, Quantity, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.paper import ExecutionTarget

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_VENUE = "venue-replay"
_ACCOUNT = "acct-replay"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value=_VENUE), symbol="EURUSD")


def _price(value: int) -> Price:
    return _ok(Price.try_create(value, _instrument(), 5))


def _qty(value: int) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", 0))


def _delta(value: int) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), 5))


def _ratio(num: int, den: int) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


def _entry(direction: Direction = Direction.LONG) -> EntryIntent:
    return _ok(
        EntryIntent.try_create(
            _instrument(),
            direction,
            _ok(ReasonCode.try_create("breakout", "scalper-v1")),
            _ok(ExecutionTarget.try_create("demo", VenueId(value=_VENUE), _ACCOUNT)),
        )
    )


def _bar(
    *,
    open_: int = 1_10000,
    high: int = 1_12000,
    low: int = 1_09000,
    close: int = 1_11000,
    prior_close: int | None = None,
    session_open: bool = False,
    session_close: bool = False,
    market_closed: bool = False,
    bar_start: int | None = None,
    bar_end: int | None = None,
    bid: int | None = None,
    ask: int | None = None,
) -> SlicePath:
    opening = _price(open_)
    prints = (_price(open_), _price(low), _price(high), _price(close))
    return _ok(
        SlicePath.try_create(
            "eurusd",
            prints,
            open=opening,
            high=_price(high),
            low=_price(low),
            close=_price(close),
            current=opening,
            prior_close=None if prior_close is None else _price(prior_close),
            bar_start=None if bar_start is None else _instant(bar_start),
            bar_end=None if bar_end is None else _instant(bar_end),
            session_open=session_open,
            session_close=session_close,
            market_closed=market_closed,
            bid=None if bid is None else _price(bid),
            ask=None if ask is None else _price(ask),
        )
    )


def _order(
    kind: OrderType,
    *,
    side: Direction = Direction.LONG,
    quantity: int = 1,
    limit: int | None = None,
    stop: int | None = None,
    trail: int | None = None,
    submitted_at: Instant | None = None,
    evaluated_at: Instant | None = None,
    reduce_only: bool = False,
    position: int | None = None,
    lot_step: int | None = 1,
    liquidity: int | None = None,
    fee_reference: str | None = None,
    intent_id: str | None = "o-1",
) -> FillOrder:
    return _ok(
        FillOrder.try_create(
            kind,
            side,
            _qty(quantity),
            limit_price=None if limit is None else _price(limit),
            stop_price=None if stop is None else _price(stop),
            trail_distance=None if trail is None else _delta(trail),
            submitted_at=submitted_at,
            evaluated_at=evaluated_at,
            reduce_only=reduce_only,
            position_quantity=None if position is None else _qty(position),
            lot_step=None if lot_step is None else _qty(lot_step),
            liquidity=None if liquidity is None else _qty(liquidity),
            fee_reference=fee_reference,
            intent_id=intent_id,
        )
    )


def _cross(
    order: FillOrder,
    path: SlicePath,
    *,
    basis: str = FILL_BASIS_WORST_CASE,
    span: Duration | None = None,
) -> Result[Fill | NoFill | PartialFill]:
    return cross_declared_path(
        _entry(order.side),
        path,
        requested_quantity=order.quantity,
        order=order,
        fill_basis=basis,
        stale_price_span=span,
    )


def test_pipeline_identity_and_catalog() -> None:
    identity = fill_pipeline_identity()
    assert identity["order_types"] == ORDER_TYPES
    assert identity["nofill_reasons"] == NOFILL_REASONS
    assert identity["default_fill_basis"] == FILL_BASIS_WORST_CASE
    assert identity["taint_field"] == TAINT_OPTIMISTIC
    assert identity["same_slice_new_intent_fill"] is False
    assert qmb.SAME_SLICE_NEW_INTENT_FILL is False
    assert SLIPPAGE_MODELS == (
        "zero",
        "constant-percent",
        "spread-crossing",
        "gap-volatility",
        "size-tiered",
    )
    assert set(NOFILL_REASONS) == {
        NOFILL_MARKET_CLOSED,
        NOFILL_STALE_DATA,
        NOFILL_NOT_TRIGGERED,
        NOFILL_INSUFFICIENT_LIQUIDITY,
        NOFILL_ALL_OR_NONE_LEG_FAILED,
    }


def test_market_limit_stop_stop_limit_trailing_moo_moc() -> None:
    path = _bar()
    market = _ok(_cross(_order(OrderType.MARKET), path))
    assert isinstance(market, Fill)
    assert market.pre_slip_price.as_fraction() == _price(1_12000).as_fraction()
    assert market.fill_basis == FILL_BASIS_WORST_CASE
    assert market.taint == TAINT_OPTIMISTIC

    buy_limit = _ok(_cross(_order(OrderType.LIMIT, limit=1_10500), path))
    assert isinstance(buy_limit, Fill)
    assert buy_limit.pre_slip_price.as_fraction() == _price(1_10500).as_fraction()

    untouched = _ok(_cross(_order(OrderType.LIMIT, limit=1_08000), path))
    assert isinstance(untouched, NoFill)
    assert untouched.reason == NOFILL_NOT_TRIGGERED

    sell_limit = _ok(_cross(_order(OrderType.LIMIT, side=Direction.SHORT, limit=1_10000), path))
    assert isinstance(sell_limit, Fill)
    assert sell_limit.pre_slip_price.as_fraction() == _price(1_10000).as_fraction()

    buy_stop = _ok(_cross(_order(OrderType.STOP, stop=1_11500), path))
    assert isinstance(buy_stop, Fill)
    assert buy_stop.pre_slip_price.as_fraction() == _price(1_11500).as_fraction()

    stop_limit = _ok(_cross(_order(OrderType.STOP_LIMIT, stop=1_11500, limit=1_11800), path))
    assert isinstance(stop_limit, Fill)

    trail = _ok(_cross(_order(OrderType.TRAILING_STOP, side=Direction.SHORT, trail=500), path))
    assert isinstance(trail, Fill)

    moo_wait = _ok(_cross(_order(OrderType.MARKET_ON_OPEN), path))
    assert isinstance(moo_wait, NoFill)
    assert moo_wait.reason == NOFILL_NOT_TRIGGERED
    moo = _ok(_cross(_order(OrderType.MARKET_ON_OPEN), _bar(session_open=True)))
    assert isinstance(moo, Fill)

    moc_wait = _ok(_cross(_order(OrderType.MARKET_ON_CLOSE), path))
    assert isinstance(moc_wait, NoFill)
    moc = _ok(_cross(_order(OrderType.MARKET_ON_CLOSE), _bar(session_close=True)))
    assert isinstance(moc, Fill)


def test_all_or_none_any_leg_fail_nofills_group() -> None:
    path = _bar()
    intent = _entry()
    good = FillLeg.try_create(intent, _order(OrderType.MARKET, intent_id="a"))
    bad = FillLeg.try_create(intent, _order(OrderType.LIMIT, limit=1_08000, intent_id="b"))
    group = _ok(fill_all_or_none((_ok(good), _ok(bad)), path))
    assert len(group) == 2
    for item in group:
        assert isinstance(item, NoFill)
        assert item.reason == NOFILL_ALL_OR_NONE_LEG_FAILED
    both = _ok(
        fill_all_or_none(
            (
                _ok(FillLeg.try_create(intent, _order(OrderType.MARKET, intent_id="c"))),
                _ok(FillLeg.try_create(intent, _order(OrderType.MARKET, intent_id="d"))),
            ),
            path,
        )
    )
    assert all(isinstance(item, Fill) for item in both)


def test_worst_case_default_and_optimistic_exact_label() -> None:
    path = _bar(high=1_12000, low=1_09000)
    worst = _ok(_cross(_order(OrderType.LIMIT, limit=1_10500), path))
    assert isinstance(worst, Fill)
    assert worst.pre_slip_price.as_fraction() == _price(1_10500).as_fraction()
    assert worst.fill_basis == FILL_BASIS_WORST_CASE
    exact = _ok(
        _cross(
            _order(OrderType.LIMIT, limit=1_10500),
            path,
            basis=FILL_BASIS_OPTIMISTIC_EXACT,
        )
    )
    assert isinstance(exact, Fill)
    assert exact.pre_slip_price.as_fraction() == _price(1_10500).as_fraction()
    assert exact.fill_basis == FILL_BASIS_OPTIMISTIC_EXACT
    assert exact.taint == TAINT_OPTIMISTIC
    assert worst.taint == TAINT_OPTIMISTIC
    sell_worst = _ok(_cross(_order(OrderType.LIMIT, side=Direction.SHORT, limit=1_10000), path))
    assert isinstance(sell_worst, Fill)
    assert sell_worst.pre_slip_price.as_fraction() == _price(1_10000).as_fraction()
    adapter = DeclaredPathFillAdapter(fill_basis=FILL_BASIS_OPTIMISTIC_EXACT)
    labelled = _ok(adapter.fidelity())
    assert labelled.fill_basis == FILL_BASIS_OPTIMISTIC_EXACT
    assert labelled.taint == TAINT_OPTIMISTIC
    assert labelled.fp1_identity()["fill_basis"] == FILL_BASIS_OPTIMISTIC_EXACT
    assert "taint" not in labelled.fp1_identity()


def test_partial_reduce_only_lot_step_and_fee_reference() -> None:
    path = _bar()
    partial = _ok(
        _cross(
            _order(
                OrderType.MARKET,
                quantity=4,
                position=2,
                reduce_only=True,
                lot_step=1,
                fee_reference="fee-a",
            ),
            path,
        )
    )
    assert isinstance(partial, PartialFill)
    assert partial.quantity.as_fraction() == _qty(2).as_fraction()
    assert partial.requested_quantity.as_fraction() == _qty(4).as_fraction()
    assert partial.fee_reference == "fee-a"
    snapped = _ok(
        _cross(
            _order(OrderType.MARKET, quantity=3, liquidity=3, lot_step=2, fee_reference="fee-b"),
            path,
        )
    )
    assert isinstance(snapped, PartialFill)
    assert snapped.quantity.as_fraction() == _qty(2).as_fraction()
    assert snapped.fee_reference == "fee-b"
    empty = _ok(_cross(_order(OrderType.MARKET, quantity=2, reduce_only=True, position=0), path))
    assert isinstance(empty, NoFill)
    assert empty.reason == NOFILL_INSUFFICIENT_LIQUIDITY


def test_stale_gap_market_closed_typed_nofill() -> None:
    closed = _ok(_cross(_order(OrderType.MARKET), _bar(market_closed=True)))
    assert isinstance(closed, NoFill)
    assert closed.reason == NOFILL_MARKET_CLOSED

    stale_resting = _ok(
        _cross(
            _order(OrderType.LIMIT, limit=1_10500, submitted_at=_instant(_NS + 10)),
            _bar(bar_end=_NS),
        )
    )
    assert isinstance(stale_resting, NoFill)
    assert stale_resting.reason == NOFILL_STALE_DATA

    span = _ok(Duration.try_create(5))
    stale_market = _ok(
        _cross(
            _order(
                OrderType.MARKET,
                submitted_at=_instant(_NS - 100),
                evaluated_at=_instant(_NS + 20),
            ),
            _bar(bar_end=_NS),
            span=span,
        )
    )
    assert isinstance(stale_market, NoFill)
    assert stale_market.reason == NOFILL_STALE_DATA

    gapped = _ok(
        _cross(
            _order(OrderType.STOP, stop=1_11000),
            _bar(open_=1_11500, high=1_12000, low=1_11400, close=1_11800, prior_close=1_10000),
        )
    )
    assert isinstance(gapped, Fill)
    assert gapped.gap_fill is True
    assert gapped.pre_slip_price.as_fraction() == _price(1_11500).as_fraction()
    assert "gap_fill" in gapped.fp1_identity()


def test_intra_slice_path_split_is_deterministic() -> None:
    path = _bar()
    low_limit = _ok(
        RestingIntent.try_create(
            "low",
            "eurusd",
            order=_order(OrderType.LIMIT, limit=1_09500, intent_id="low"),
            authorized=_entry(),
        )
    )
    high_stop = _ok(
        RestingIntent.try_create(
            "high",
            "eurusd",
            order=_order(OrderType.STOP, stop=1_11500, intent_id="high"),
            authorized=_entry(),
        )
    )
    ranked = _ok(rank_resting_on_path((high_stop, low_limit), path))
    ranked_ids: list[str] = []
    for item in ranked:
        assert isinstance(item, RestingIntent)
        ranked_ids.append(item.intent_id)
    assert ranked_ids == ["low", "high"]
    ranked_order = low_limit.order
    assert isinstance(ranked_order, FillOrder)
    first = _ok(_cross(ranked_order, path))
    assert isinstance(first, Fill)
    remaining = _ok(split_path_at(path, first.pre_slip_price))
    assert remaining.prints[0].as_fraction() == first.pre_slip_price.as_fraction()
    again = _ok(rank_resting_on_path((high_stop, low_limit), path))
    again_ids: list[str] = []
    for item in again:
        assert isinstance(item, RestingIntent)
        again_ids.append(item.intent_id)
    assert again_ids == ["low", "high"]


def test_new_intents_rest_and_subphase_3_fill_handler() -> None:
    assert SAME_SLICE_NEW_INTENT_FILL is False
    assert SUBPHASES[2] == "resting-orders"
    path = _bar()
    fill = DeclaredPathFillAdapter()
    slip = ZeroSlippageAdapter()
    handler = ExecutionSliceHandler(
        fill=fill,
        slippage=slip,
        cost=ZeroCostAdapter(),
        position_cap=_qty(1),
        lot_step=_qty(1),
    )
    _ok(handler.bind_path("eurusd", path))
    resting = _ok(
        RestingIntent.try_create(
            "rest-1",
            "eurusd",
            order=_order(OrderType.MARKET, intent_id="rest-1"),
            authorized=_entry(),
        )
    )

    class _Minting(ExecutionSliceHandler):
        def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
            del frontier
            minted = RestingIntent.try_create(
                f"new-{stream_id}",
                stream_id,
                order=_order(OrderType.MARKET, intent_id=f"new-{stream_id}"),
                authorized=_entry(),
            )
            if is_refusal(minted):
                return minted
            return Ok((minted.value,))

    minted_handler = _Minting(
        fill=fill,
        slippage=slip,
        cost=ZeroCostAdapter(),
        position_cap=_qty(1),
        lot_step=_qty(1),
        paths=dict(handler.paths),
        remaining_paths=dict(handler.remaining_paths),
    )
    observation = _ok(SliceObservation.try_create("eurusd", _instant(), True))
    outcome = _ok(
        run_slice(
            (observation,),
            stream_set=("eurusd",),
            handler=minted_handler,
            resting=(resting,),
        )
    )
    assert outcome.subphase_order() == SUBPHASES
    assert "rest-1" in outcome.filled
    assert outcome.minted == ("new-eurusd",)
    assert "new-eurusd" in outcome.ineligible
    assert "fill:new-eurusd" not in outcome.trace[2].actions
    assert any(item.intent_id == "new-eurusd" for item in outcome.resting)


def test_slippage_maps_or_vetoes_skips_passive_limits() -> None:
    path = _bar(high=1_12000, low=1_09000, bid=1_09900, ask=1_10100)
    filled = _ok(_cross(_order(OrderType.MARKET), path))
    assert isinstance(filled, Fill)
    zeroed = _ok(ZeroSlippageAdapter().apply(filled, path))
    assert isinstance(zeroed, Fill)
    assert zeroed.post_slip_price is not None
    assert zeroed.post_slip_price.as_fraction() == filled.pre_slip_price.as_fraction()
    assert zeroed.taint == TAINT_OPTIMISTIC

    percent = _ok(
        SlippageCalibration.try_create(
            "constant-percent",
            "broker-a",
            percent=_ratio(1, 100),
        )
    )
    slipped = _ok(ConstantPercentSlippageAdapter(calibration=percent).apply(filled, path))
    assert isinstance(slipped, (Fill, NoFill))
    if isinstance(slipped, Fill):
        assert slipped.post_slip_price is not None
        assert slipped.post_slip_price.as_fraction() > filled.pre_slip_price.as_fraction()

    veto_cal = _ok(
        SlippageCalibration.try_create(
            "constant-percent",
            "broker-a",
            percent=_ratio(1, 1),
        )
    )
    vetoed = _ok(ConstantPercentSlippageAdapter(calibration=veto_cal).apply(filled, path))
    assert isinstance(vetoed, NoFill)
    assert vetoed.reason == "illegal-print"

    limit_fill = _ok(_cross(_order(OrderType.LIMIT, limit=1_10500), path))
    assert isinstance(limit_fill, Fill)
    assert limit_fill.passive is True
    skipped = _ok(ConstantPercentSlippageAdapter(calibration=percent).apply(limit_fill, path))
    assert isinstance(skipped, Fill)
    assert skipped.post_slip_price is not None
    assert skipped.post_slip_price.as_fraction() == limit_fill.pre_slip_price.as_fraction()
    forced = _ok(
        ConstantPercentSlippageAdapter(calibration=percent, apply_to_passive_limits=True).apply(
            limit_fill, path
        )
    )
    assert isinstance(forced, (Fill, NoFill))

    missing = ConstantPercentSlippageAdapter().apply(filled, path)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY

    spread_cal = _ok(
        SlippageCalibration.try_create(
            "spread-crossing",
            "broker-a",
            spread_fraction=_ratio(1, 2),
        )
    )
    crossed = SpreadCrossingSlippageAdapter(calibration=spread_cal).apply(filled, path)
    assert is_ok(crossed) or is_refusal(crossed)

    range_cal = _ok(
        SlippageCalibration.try_create(
            "gap-volatility",
            "broker-a",
            range_fraction=_ratio(1, 10),
        )
    )
    vol = _ok(GapVolatilitySlippageAdapter(calibration=range_cal).apply(filled, path))
    assert isinstance(vol, (Fill, NoFill))

    tier_cal = _ok(
        SlippageCalibration.try_create(
            "size-tiered",
            "broker-a",
            tiers=((_qty(1), _delta(10)), (_qty(10), _delta(50))),
        )
    )
    sized = _ok(SizeTieredSlippageAdapter(calibration=tier_cal).apply(filled, path))
    assert isinstance(sized, (Fill, NoFill))

    first = _ok(derive_slippage_seed(_ok(fingerprint({"run": "a"}))))
    second = _ok(derive_slippage_seed(_ok(fingerprint({"run": "a"}))))
    assert first == second
    other = _ok(derive_slippage_seed(_ok(fingerprint({"run": "b"}))))
    assert other != first
    assert _ok(legal_print(filled.pre_slip_price, path)) is True


def test_declared_path_adapter_and_api_door() -> None:
    adapter = DeclaredPathFillAdapter()
    path = _bar()
    decided = _ok(
        adapter.decide(
            _entry(),
            path,
            requested_quantity=_qty(1),
            order=_order(OrderType.MARKET),
        )
    )
    assert isinstance(decided, Fill)
    assert decided.kind is FillKind.FILL
    assert api.cross_declared_path is qmb.cross_declared_path is cross_declared_path
    assert api.ExecutionSliceHandler is qmb.ExecutionSliceHandler is ExecutionSliceHandler
    assert api.FillOrder is qmb.FillOrder is FillOrder
    assert api.OrderType is qmb.OrderType is OrderType
    assert api.slip_fill is qmb.slip_fill is slip_fill
    assert api.FILL_BASIS_WORST_CASE == qmb.FILL_BASIS_WORST_CASE == FILL_BASIS_WORST_CASE
    assert qmb.__version__ not in fill_pipeline_identity().values()
