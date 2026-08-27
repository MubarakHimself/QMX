"""Epic 17 · Group F — property-based invariants (L6): T-17.2-P, T-17.3-P, T-17.F-taint, T-17.F-partial.

The evidence-honesty spine as properties over broad input spaces a hand case cannot
enumerate: spread absence refuses across arbitrary keys (R13/R14); a worst-case fill
never leaves the bar or beats the order price across arbitrary OHLC (R19); taint never
drops and fidelity is lowest-wins across arbitrary bound sets (R7/R9/R12/R33); and
per-partial pro-rated commission sums exactly to the whole-fill commission (R20/R25).
Run under: uv run --with hypothesis pytest qa/tests/epic_17/test_g_properties.py

A failing test is a FINDING, never a licence to soften the assertion or edit source.
"""

from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from _e17 import entry, instrument, money, ok, price, qty, slice_path

from qmf.core.exact import Money
from qmf.core.refusal import is_ok, is_refusal
from qmf.risk.door import Direction
from qmb.execution.cost import CommissionCalibration, charge_commission
from qmb.execution.fidelity import FidelityTaxonomy, compute_run_fidelity, stamp_fidelity
from qmb.execution.fill import (
    FILL_BASIS_WORST_CASE,
    FillOrder,
    OrderType,
    cross_declared_path,
)
from qmb.execution.ports import Fill, PartialFill, TAINT_OPTIMISTIC, classify_fill_quantity
from qmb.execution.spread import (
    SpreadCalibration,
    SpreadCell,
    SpreadFeed,
    hour_utc,
    resolve_spread,
)

_EUR = instrument("EURUSD")
_NS_PER_HOUR = 3_600_000_000_000
_DAY0 = (1_700_000_000_000_000_000 // (24 * _NS_PER_HOUR)) * (24 * _NS_PER_HOUR)


def _inst_at_hour(hour: int):
    from qmf.core.chrono import Instant

    return ok(Instant.try_create(_DAY0 + hour * _NS_PER_HOUR))


# --- T-17.2-P (L6) spread: cell-present quotes buy!=sell; cell-absent refuses [R13/R14] P0
@settings(max_examples=120, deadline=None)
@given(
    present_hour=st.integers(min_value=0, max_value=23),
    hour_gap=st.integers(min_value=1, max_value=23),
    session=st.sampled_from(["london", "newyork", "tokyo", "sydney"]),
    bid=st.integers(min_value=50_000, max_value=150_000),
    spread=st.integers(min_value=1, max_value=5_000),
)
def test_t172p_spread_present_quotes_absent_refuses(present_hour, hour_gap, session, bid, spread):
    absent_hour = (present_hour + hour_gap) % 24
    assume(absent_hour != present_hour)
    cell = ok(SpreadCell.try_create(_EUR, present_hour, session,
                                    price(bid, instr=_EUR), price(bid + spread, instr=_EUR)))
    cal = ok(SpreadCalibration.try_create("broker-x", (cell,)))
    feed = ok(SpreadFeed.try_create(_EUR))
    # Where a calibration entry exists: a non-negative spread and buy != sell.
    present = resolve_spread(feed, at=_inst_at_hour(present_hour), session=session, calibration=cal)
    assert is_ok(present)
    quote = present.value
    assert quote.bid.as_fraction() < quote.ask.as_fraction()  # buy != sell, spread > 0
    # Where no entry exists: a typed refusal, never a silent zero spread.
    absent = resolve_spread(feed, at=_inst_at_hour(absent_hour), session=session, calibration=cal)
    assert is_refusal(absent)


# --- T-17.3-P (L6) worst-case fill stays in the bar and on the order-price side [R19] P0
@settings(max_examples=150, deadline=None)
@given(
    a=st.integers(min_value=80_000, max_value=120_000),
    b=st.integers(min_value=80_000, max_value=120_000),
    limit=st.integers(min_value=80_000, max_value=120_000),
    buy=st.booleans(),
)
def test_t173p_worst_case_fill_in_bar_and_bounded_by_order_price(a, b, limit, buy):
    low, high = (a, b) if a <= b else (b, a)
    side = Direction.LONG if buy else Direction.SHORT
    path = slice_path(open=low, high=high, low=low, close=high,
                      prints=(low, high))
    order = ok(FillOrder.try_create(OrderType.LIMIT, side, qty(10), limit_price=price(limit)))
    if buy:
        assume(low <= limit)  # a buy limit crosses when the low reaches the limit
    else:
        assume(high >= limit)  # a sell limit crosses when the high reaches the limit
    decided = cross_declared_path(entry(direction=side), path, requested_quantity=qty(10),
                                  order=order, fill_basis=FILL_BASIS_WORST_CASE)
    assert is_ok(decided)
    fill = decided.value
    assert isinstance(fill, (Fill, PartialFill))
    # Compare in the raw scaled-integer space (all Prices share instrument + scale 5).
    f = fill.pre_slip_price.value
    # The worst-case fill is always inside the bar range.
    assert low <= f <= high
    # And never beats the order price: a buy fills at <= limit, a sell at >= limit.
    if buy:
        assert f <= limit
    else:
        assert f >= limit


# --- T-17.F-taint (L6) taint never drops; run fidelity is lowest-wins [R7/R9/R12/R33] P0
@settings(max_examples=120, deadline=None)
@given(ranks=st.lists(st.integers(min_value=-1000, max_value=1000), min_size=2, max_size=5,
                      unique=True))
def test_t17f_taint_never_drops_and_fidelity_is_lowest(ranks):
    ids = [ok(stamp_fidelity(f"adapter-{i}")) for i in range(len(ranks))]
    # Every stamped identity carries the optimistic taint — it cannot be anything else.
    assert all(ident.taint == TAINT_OPTIMISTIC for ident in ids)
    taxonomy = ok(FidelityTaxonomy.try_create({f"adapter-{i}": r for i, r in enumerate(ranks)}))
    run = ok(compute_run_fidelity(ids, taxonomy=taxonomy))
    # The composed run label keeps the optimistic taint AND names the LOWEST-rank adapter.
    assert run.taint == TAINT_OPTIMISTIC
    lowest_index = ranks.index(min(ranks))
    assert run.lowest_adapter_id == f"adapter-{lowest_index}"
    # No composition can raise a non-optimistic taint — a drop is refused at the stamp.
    assert is_refusal(stamp_fidelity("adapter-x", taint="live"))


# --- T-17.F-partial (L6) per-partial pro-rata sums to the whole-fill commission [R20/R25] P0
@settings(max_examples=150, deadline=None)
@given(
    partials=st.lists(st.integers(min_value=1, max_value=25), min_size=1, max_size=8),
    per_lot_minor=st.integers(min_value=1, max_value=10_000),
)
def test_t17f_partial_commission_sums_to_whole(partials, per_lot_minor):
    total = sum(partials)
    calibration = ok(CommissionCalibration.try_create("per-lot/per-1k-units", "broker-x",
                                                      per_lot=money(per_lot_minor), currency="USD"))

    def _charge(quantity):
        f = ok(Fill.try_create(qty(quantity), qty(quantity), price(100_000),
                               post_slip_price=price(100_000), side=Direction.LONG))
        return ok(charge_commission(f, model="per-lot/per-1k-units", calibration=calibration))

    running = ok(Money.try_create(0, "USD", 2))
    filled = 0
    for part in partials:
        running = ok(running.add(_charge(part)))
        filled += part
    # Sum of quantities never exceeds the order quantity (here the sum defines it).
    assert filled == total
    # Sum of pro-rated commissions equals the whole-fill commission, exactly (no float drift).
    assert running == _charge(total)
    # A reduce_only cap holds: the classified quantity never exceeds the open position size.
    cap = max(1, total // 2)
    classified = ok(classify_fill_quantity(requested=qty(total), filled=qty(total),
                                           position_cap=qty(cap), lot_step=qty(1),
                                           pre_slip_price=price(100_000)))
    assert classified.quantity.as_fraction() <= cap
