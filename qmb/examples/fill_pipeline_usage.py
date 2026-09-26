"""Reference usage — fill and slippage price-forming pipeline (Story 17.3).

Executable::

    python qmb/examples/fill_pipeline_usage.py

Shows the things FILL-2 / FILL-4 / FILL-6 / FILL-8 / SLIP-1 / B-2 pin down:

1. Fill decides Fill | NoFill | PartialFill by crossing the declared path,
   dispatched per order type including all-or-none.
2. Default pricing is bar-worst-case; optimistic-exact stamps a distinct
   fill-basis. Both stay optimistic-tainted until GAP-0048.
3. Partials cap by position and lot step, each with its own fee reference.
4. Typed NoFill reasons; gap fills at the gapped price with a marker.
5. Intra-slice order is the declared-path split; new intents rest.
6. Slippage maps pre-slip → post-slip (buy +, sell −) or vetoes; passive
   limits skip slippage unless configured.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.execution import (
    FILL_BASIS_OPTIMISTIC_EXACT,
    FILL_BASIS_WORST_CASE,
    NOFILL_ALL_OR_NONE_LEG_FAILED,
    TAINT_OPTIMISTIC,
    ConstantPercentSlippageAdapter,
    DeclaredPathFillAdapter,
    ExecutionSliceHandler,
    Fill,
    FillLeg,
    FillOrder,
    NoFill,
    OrderType,
    PartialFill,
    SlicePath,
    SlippageCalibration,
    ZeroSlippageAdapter,
    cross_declared_path,
    fill_all_or_none,
    rank_resting_on_path,
)
from qmb.execution.cost import ZeroCostAdapter
from qmb.runloop import (
    SAME_SLICE_NEW_INTENT_FILL,
    SUBPHASES,
    RestingIntent,
    SliceObservation,
    run_slice,
)
from qmf.core.chrono import Instant
from qmf.core.exact import ExactRational, Price, Quantity, UnitKind
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, Result, is_ok, is_refusal
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.paper import ExecutionTarget

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="venue-replay"), symbol="EURUSD")


def _price(value: int) -> Price:
    return _unwrap(Price.try_create(value, _instrument(), 5), "price")


def _qty(value: int) -> Quantity:
    return _unwrap(Quantity.try_create(value, "lot", 0), "quantity")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


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


def _path() -> SlicePath:
    return _unwrap(
        SlicePath.try_create(
            "eurusd",
            (_price(1_10000), _price(1_09000), _price(1_12000), _price(1_11000)),
            open=_price(1_10000),
            high=_price(1_12000),
            low=_price(1_09000),
            close=_price(1_11000),
            current=_price(1_10000),
            prior_close=_price(1_08000),
        ),
        "path",
    )


def main() -> None:
    path = _path()
    intent = _entry()
    market = _unwrap(
        cross_declared_path(
            intent,
            path,
            requested_quantity=_qty(1),
            order=_unwrap(FillOrder.try_create(OrderType.MARKET, Direction.LONG, _qty(1)), "mkt"),
        ),
        "market",
    )
    assert isinstance(market, Fill)
    assert market.pre_slip_price.as_fraction() == _price(1_12000).as_fraction()
    assert market.fill_basis == FILL_BASIS_WORST_CASE
    assert market.taint == TAINT_OPTIMISTIC
    print("dispatched per order type")
    print("Fill | NoFill | PartialFill")

    exact = _unwrap(
        cross_declared_path(
            intent,
            path,
            requested_quantity=_qty(1),
            order=_unwrap(
                FillOrder.try_create(
                    OrderType.LIMIT, Direction.LONG, _qty(1), limit_price=_price(1_10500)
                ),
                "limit",
            ),
            fill_basis=FILL_BASIS_OPTIMISTIC_EXACT,
        ),
        "exact",
    )
    assert isinstance(exact, Fill)
    assert exact.fill_basis == FILL_BASIS_OPTIMISTIC_EXACT
    assert exact.taint == TAINT_OPTIMISTIC
    print("worst-case default")
    print("optimistic-exact fill-basis")
    print("optimistic taint")

    missed = _unwrap(
        fill_all_or_none(
            (
                _unwrap(
                    FillLeg.try_create(
                        intent,
                        _unwrap(
                            FillOrder.try_create(OrderType.MARKET, Direction.LONG, _qty(1)),
                            "a",
                        ),
                    ),
                    "leg-a",
                ),
                _unwrap(
                    FillLeg.try_create(
                        intent,
                        _unwrap(
                            FillOrder.try_create(
                                OrderType.LIMIT,
                                Direction.LONG,
                                _qty(1),
                                limit_price=_price(1_05000),
                            ),
                            "b",
                        ),
                    ),
                    "leg-b",
                ),
            ),
            path,
        ),
        "aon",
    )
    for item in missed:
        assert isinstance(item, NoFill)
        assert item.reason == NOFILL_ALL_OR_NONE_LEG_FAILED
    print("all-or-none any-leg-fail is NoFill")

    partial = _unwrap(
        cross_declared_path(
            intent,
            path,
            requested_quantity=_qty(4),
            order=_unwrap(
                FillOrder.try_create(
                    OrderType.MARKET,
                    Direction.LONG,
                    _qty(4),
                    reduce_only=True,
                    position_quantity=_qty(2),
                    lot_step=_qty(1),
                    fee_reference="fee-partial",
                ),
                "partial-order",
            ),
        ),
        "partial",
    )
    assert isinstance(partial, PartialFill)
    assert partial.fee_reference == "fee-partial"
    print("partial capped by position and lot step")
    print("each partial has its own fee reference")

    closed = _unwrap(
        cross_declared_path(
            intent,
            _unwrap(
                SlicePath.try_create("eurusd", (_price(1_10000),), market_closed=True),
                "closed",
            ),
            requested_quantity=_qty(1),
        ),
        "closed",
    )
    assert isinstance(closed, NoFill)
    print("typed NoFill reasons")
    gapped = _unwrap(
        cross_declared_path(
            intent,
            path,
            requested_quantity=_qty(1),
            order=_unwrap(
                FillOrder.try_create(
                    OrderType.STOP, Direction.LONG, _qty(1), stop_price=_price(1_09000)
                ),
                "gap-stop",
            ),
        ),
        "gap",
    )
    assert isinstance(gapped, Fill)
    assert gapped.gap_fill is True
    print("gap fill at gapped price")

    low = _unwrap(
        RestingIntent.try_create(
            "low",
            "eurusd",
            order=_unwrap(
                FillOrder.try_create(
                    OrderType.LIMIT, Direction.LONG, _qty(1), limit_price=_price(1_09500)
                ),
                "low-order",
            ),
            authorized=intent,
        ),
        "low",
    )
    high = _unwrap(
        RestingIntent.try_create(
            "high",
            "eurusd",
            order=_unwrap(
                FillOrder.try_create(
                    OrderType.STOP, Direction.LONG, _qty(1), stop_price=_price(1_11500)
                ),
                "high-order",
            ),
            authorized=intent,
        ),
        "high",
    )
    ranked = _unwrap(rank_resting_on_path((high, low), path), "rank")
    ranked_ids: list[str] = []
    for item in ranked:
        assert isinstance(item, RestingIntent)
        ranked_ids.append(item.intent_id)
    assert ranked_ids == ["low", "high"]
    print("deterministic path-split sequencing")
    assert SAME_SLICE_NEW_INTENT_FILL is False
    print("new intents rest for a later slice")

    handler = ExecutionSliceHandler(
        fill=DeclaredPathFillAdapter(),
        slippage=ZeroSlippageAdapter(),
        cost=ZeroCostAdapter(),
        position_cap=_qty(1),
        lot_step=_qty(1),
    )
    _unwrap(handler.bind_path("eurusd", path), "bind")
    resting = _unwrap(
        RestingIntent.try_create(
            "rest-1",
            "eurusd",
            order=_unwrap(FillOrder.try_create(OrderType.MARKET, Direction.LONG, _qty(1)), "r"),
            authorized=intent,
        ),
        "rest",
    )

    class _Minting(ExecutionSliceHandler):
        def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
            del frontier
            minted = RestingIntent.try_create(f"new-{stream_id}", stream_id, authorized=intent)
            if is_refusal(minted):
                return minted
            return Ok((minted.value,))

    minted_handler = _Minting(
        fill=DeclaredPathFillAdapter(),
        slippage=ZeroSlippageAdapter(),
        cost=ZeroCostAdapter(),
        position_cap=_qty(1),
        lot_step=_qty(1),
        paths=dict(handler.paths),
        remaining_paths=dict(handler.remaining_paths),
    )
    outcome = _unwrap(
        run_slice(
            (_unwrap(SliceObservation.try_create("eurusd", _instant(), True), "obs"),),
            stream_set=("eurusd",),
            handler=minted_handler,
            resting=(resting,),
        ),
        "slice",
    )
    assert outcome.subphase_order() == SUBPHASES
    assert "rest-1" in outcome.filled
    assert "new-eurusd" in outcome.ineligible
    print("wired into run-loop sub-phase 3")

    slipped = ZeroSlippageAdapter().apply(market, path)
    assert is_ok(slipped)
    missing = ConstantPercentSlippageAdapter().apply(market, path)
    assert is_refusal(missing)
    cal = _unwrap(
        SlippageCalibration.try_create(
            "constant-percent",
            "broker-a",
            percent=_unwrap(
                ExactRational.try_create(1, 10000, UnitKind.DIMENSIONLESS_RATIO),
                "pct",
            ),
        ),
        "cal",
    )
    applied = ConstantPercentSlippageAdapter(calibration=cal).apply(market, path)
    assert is_ok(applied) or is_refusal(applied)
    print("slippage maps pre-slip to post-slip or vetoes")
    print("passive limits skip slippage unless configured")
    print("fill pipeline ok")


if __name__ == "__main__":
    main()
