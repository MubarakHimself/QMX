"""Epic 17 · Group C — fill & slippage price-forming pipeline (Story 17.3, R18-R23).

Independent, requirements-derived assertions (T-17.3-a..n; the R-011 branch locus).
Fill decides Fill|NoFill|PartialFill by crossing the declared path per order type;
default pricing is bar-worst-case with a labelled optimistic-exact mode; partials
are first-class; slippage maps pre->post (buy +, sell -) or vetoes an illegal print
(FILL-1..8, SLIP-1..3, SC-06). A failing test is a FINDING, never a licence to
soften the assertion or edit source.
"""

from __future__ import annotations

from _e17 import delta, entry, inst, ok, price, qty, ratio, refusal, slice_path

from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.door import Direction
from qmb.execution.fill import (
    FILL_BASIS_OPTIMISTIC_EXACT,
    FILL_BASIS_WORST_CASE,
    NOFILL_REASONS,
    FillLeg,
    FillOrder,
    OrderType,
    cross_declared_path,
    fill_all_or_none,
    rank_resting_on_path,
)
from qmb.execution.ports import (
    TAINT_OPTIMISTIC,
    Fill,
    NoFill,
    PartialFill,
    classify_fill_quantity,
)
from qmb.execution.slippage import (
    SLIPPAGE_MODELS,
    SlippageCalibration,
    derive_slippage_seed,
    slip_fill,
)

_OHLC = dict(open=100_000, high=102_000, low=98_000, close=101_000,
             prints=(100_000, 102_000, 98_000, 101_000), current=100_000, prior_close=100_000)


def _order(order_type, side=Direction.LONG, q=10, **kw):
    return ok(FillOrder.try_create(order_type, side, qty(q), **kw))


# --- T-17.3-a (L2) fill dispatches all eight order-type arms [R18] P0 ----------
def test_t173a_fill_dispatches_all_eight_order_types() -> None:
    path = slice_path(**_OHLC)
    e = entry()
    cases = {
        "market": _order(OrderType.MARKET),
        "limit": _order(OrderType.LIMIT, limit_price=price(101_000)),
        "stop": _order(OrderType.STOP, stop_price=price(101_000)),
        "stop-limit": _order(OrderType.STOP_LIMIT, stop_price=price(100_500),
                             limit_price=price(102_000)),
        "trailing-stop": _order(OrderType.TRAILING_STOP, side=Direction.SHORT,
                                trail_distance=delta(500)),
    }
    for name, order in cases.items():
        decided = ok(cross_declared_path(e, path, requested_quantity=order.quantity, order=order))
        assert isinstance(decided, (Fill, PartialFill)), f"{name} did not fill"
        assert decided.pre_slip_price is not None
    # market-on-open fills only on the session-open bar.
    moo = ok(cross_declared_path(e, slice_path(**_OHLC, session_open=True),
                                 requested_quantity=qty(10), order=_order(OrderType.MARKET_ON_OPEN)))
    assert isinstance(moo, Fill) and moo.pre_slip_price == price(100_000)
    # market-on-close fills only on the session-close bar.
    moc = ok(cross_declared_path(e, slice_path(**_OHLC, session_close=True),
                                 requested_quantity=qty(10), order=_order(OrderType.MARKET_ON_CLOSE)))
    assert isinstance(moc, Fill) and moc.pre_slip_price == price(101_000)
    # an all-or-none group whose legs cross returns a Fill per leg.
    legs = (ok(FillLeg.try_create(e, _order(OrderType.MARKET, q=5))),
            ok(FillLeg.try_create(e, _order(OrderType.LIMIT, q=5, limit_price=price(101_000)))))
    group = ok(fill_all_or_none(legs, path))
    assert all(isinstance(d, Fill) for d in group)


# --- T-17.3-b (L2) any AON leg failing -> NoFill for the whole group [R18] -----
def test_t173b_all_or_none_group_fails_whole() -> None:
    path = slice_path(**_OHLC)
    e = entry()
    good = ok(FillLeg.try_create(e, _order(OrderType.MARKET, q=5)))
    bad = ok(FillLeg.try_create(e, _order(OrderType.LIMIT, q=5, limit_price=price(90_000))))
    group = ok(fill_all_or_none((good, bad), path))
    # The crossing leg does NOT fill because a sibling leg failed.
    assert all(isinstance(d, NoFill) for d in group)
    assert all(d.reason == "all_or_none_leg_failed" for d in group)


# --- T-17.3-c (L1) worst-case pricing math is exact per order type [R19] P0 ----
def test_t173c_worst_case_price_math_is_exact() -> None:
    e = entry()
    # Buy limit: whole bar below limit -> worst = min(high, limit) = high (99000), not the limit.
    buy_path = slice_path(open=97_000, high=99_000, low=96_000, close=98_000,
                          prints=(97_000, 99_000, 96_000, 98_000))
    buy = ok(cross_declared_path(e, buy_path, requested_quantity=qty(10),
                                 order=_order(OrderType.LIMIT, limit_price=price(100_000)),
                                 fill_basis=FILL_BASIS_WORST_CASE))
    assert buy.pre_slip_price == price(99_000)  # min(high=99000, limit=100000)
    # Sell limit: whole bar above limit -> worst = max(low, limit) = low (101000).
    sell_path = slice_path(open=103_000, high=104_000, low=101_000, close=103_000,
                           prints=(103_000, 104_000, 101_000, 103_000))
    sell = ok(cross_declared_path(entry(direction=Direction.SHORT), sell_path,
                                  requested_quantity=qty(10),
                                  order=_order(OrderType.LIMIT, side=Direction.SHORT,
                                               limit_price=price(100_000)),
                                  fill_basis=FILL_BASIS_WORST_CASE))
    assert sell.pre_slip_price == price(101_000)  # max(low=101000, limit=100000)
    # Buy stop: worst = max(stop, current); with current above the stop the fill is current.
    stop_path = slice_path(open=100_000, high=102_000, low=99_000, close=101_000,
                           prints=(100_000, 102_000, 99_000, 101_000), current=101_000)
    stop = ok(cross_declared_path(e, stop_path, requested_quantity=qty(10),
                                  order=_order(OrderType.STOP, stop_price=price(100_000)),
                                  fill_basis=FILL_BASIS_WORST_CASE))
    assert stop.pre_slip_price == price(101_000)  # max(stop=100000, current=101000)


# --- T-17.3-d (L2) optimistic-exact fills at order price, distinct fill-basis [R19]
def test_t173d_optimistic_exact_mode_distinct_basis_still_tainted() -> None:
    e = entry()
    buy_path = slice_path(open=97_000, high=99_000, low=96_000, close=98_000,
                          prints=(97_000, 99_000, 96_000, 98_000))
    order = _order(OrderType.LIMIT, limit_price=price(100_000))
    worst = ok(cross_declared_path(e, buy_path, requested_quantity=qty(10), order=order,
                                   fill_basis=FILL_BASIS_WORST_CASE))
    exact = ok(cross_declared_path(e, buy_path, requested_quantity=qty(10), order=order,
                                   fill_basis=FILL_BASIS_OPTIMISTIC_EXACT))
    # Optimistic-exact fills at the exact order price (100000), worst-case at 99000.
    assert exact.pre_slip_price == price(100_000)
    assert worst.pre_slip_price == price(99_000)
    # Distinct fill-basis stamps; both remain optimistic-tainted until GAP-0048.
    assert exact.fill_basis == FILL_BASIS_OPTIMISTIC_EXACT
    assert worst.fill_basis == FILL_BASIS_WORST_CASE
    assert exact.taint == TAINT_OPTIMISTIC and worst.taint == TAINT_OPTIMISTIC


# --- T-17.3-e (L2) partial capped by position size + lot step, own fee ref [R20] P0
def test_t173e_partial_fill_capped_with_own_fee_reference() -> None:
    e = entry()
    path = slice_path(**_OHLC)
    # reduce_only market caps the fill to the open position size (4 of 10 requested).
    order = _order(OrderType.MARKET, q=10, reduce_only=True, position_quantity=qty(4),
                   intent_id="intent-42")
    decided = ok(cross_declared_path(e, path, requested_quantity=qty(10), order=order))
    assert isinstance(decided, PartialFill)
    assert decided.quantity.as_fraction() == 4  # capped to open position size
    assert decided.remaining_quantity.as_fraction() == 6
    # Each partial carries its own fee reference (FILL-8, B-6).
    assert decided.fee_reference == "intent-42"
    # Lot-step snap: 10 requested at a lot step of 3 fills 9 (floor to the step).
    snapped = ok(classify_fill_quantity(requested=qty(10), filled=qty(10), position_cap=qty(10),
                                        lot_step=qty(3), pre_slip_price=price(100_000)))
    assert isinstance(snapped, PartialFill) and snapped.quantity.as_fraction() == 9


# --- T-17.3-f (L1) lot-step rounding is exact-integer on the quantity path [R20]
def test_t173f_lot_step_rounding_is_exact_integer() -> None:
    from fractions import Fraction

    snapped = ok(classify_fill_quantity(requested=qty(10), filled=qty(10), position_cap=qty(10),
                                        lot_step=qty(3), pre_slip_price=price(100_000)))
    # The snapped quantity is an EXACT Fraction (9), never a binary float (9.0 +/- eps).
    assert isinstance(snapped.quantity.as_fraction(), Fraction)
    assert snapped.quantity.as_fraction() == Fraction(9)
    # A lot step that evenly divides the fill keeps it whole.
    whole = ok(classify_fill_quantity(requested=qty(10), filled=qty(10), position_cap=qty(10),
                                      lot_step=qty(5), pre_slip_price=price(100_000)))
    assert isinstance(whole, Fill) and whole.quantity.as_fraction() == Fraction(10)


# --- T-17.3-g (L2) stale/closed guards -> typed NoFill from the closed set [R21] P0
def test_t173g_nofill_reasons_are_from_the_closed_set() -> None:
    e = entry()
    # stale: a resting order whose bar end precedes submission.
    stale = ok(cross_declared_path(
        e, slice_path(**_OHLC, bar_end=1_700_000_000_000_000_000),
        requested_quantity=qty(10),
        order=_order(OrderType.MARKET, submitted_at=inst(1_700_000_000_000_000_001))))
    # market_closed.
    closed = ok(cross_declared_path(
        e, slice_path(prints=(100_000,), market_closed=True), requested_quantity=qty(10),
        order=_order(OrderType.MARKET)))
    # not_triggered.
    not_trig = ok(cross_declared_path(
        e, slice_path(**_OHLC), requested_quantity=qty(10),
        order=_order(OrderType.LIMIT, limit_price=price(90_000))))
    # insufficient_liquidity.
    dry = ok(cross_declared_path(
        e, slice_path(**_OHLC), requested_quantity=qty(10),
        order=_order(OrderType.MARKET, liquidity=qty(0))))
    for decision, reason in ((stale, "stale_data"), (closed, "market_closed"),
                             (not_trig, "not_triggered"), (dry, "insufficient_liquidity")):
        assert isinstance(decision, NoFill)
        assert decision.reason == reason
        assert decision.reason in NOFILL_REASONS


# --- T-17.3-h (L2) between-bar gap fills at the gapped price, not skipped [R21] --
def test_t173h_between_bar_gap_fills_with_marker() -> None:
    e = entry()
    # Prior close (101000) is above the buy limit (99800); the bar opens below it (99000)
    # -> a gap through the limit fills at the open with a gap_fill marker, not skipped.
    gap_path = slice_path(open=99_000, high=100_000, low=98_500, close=99_500,
                          prints=(99_000, 100_000, 98_500, 99_500), prior_close=101_000)
    decided = ok(cross_declared_path(e, gap_path, requested_quantity=qty(10),
                                     order=_order(OrderType.LIMIT, limit_price=price(99_800))))
    assert isinstance(decided, Fill)
    assert decided.gap_fill is True
    assert decided.pre_slip_price == price(99_000)  # the gapped (open) price


# --- T-17.3-i (L2) deterministic intra-slice sequencing, reproducible [R22] P0 --
def test_t173i_resting_orders_rank_deterministically() -> None:
    class RI:
        def __init__(self, iid, order):
            self.intent_id = iid
            self.order = order

    path = slice_path(open=100_000, high=102_000, low=98_000, close=101_000,
                      prints=(100_000, 101_000, 99_000, 98_000))
    # Order A (limit 101000) crosses earlier along the path than B (limit 99000).
    a = RI("A", _order(OrderType.LIMIT, q=5, limit_price=price(101_000), intent_id="A"))
    b = RI("B", _order(OrderType.LIMIT, q=5, limit_price=price(99_000), intent_id="B"))
    first = [x.intent_id for x in ok(rank_resting_on_path([b, a], path))]
    second = [x.intent_id for x in ok(rank_resting_on_path([b, a], path))]
    # Two runs produce the identical sequence (reproducible without tick data).
    assert first == second
    # A crosses before B along the declared path.
    assert first.index("A") < first.index("B")


# --- T-17.3-j (L2) the execution handler mints no new intent mid-slice [R22] ---
def test_t173j_execution_handler_mints_no_mid_slice_intent() -> None:
    # The cross-sub-phase "new intents rest for a later slice" is the Epic-14 loop's
    # guarantee (B-2 sub-phase 6); Epic 17's half is that the execution handler itself
    # mints NO fresh intent in a slice, so nothing it does makes one eligible this slice.
    from _e17 import RecordingCost, RecordingFill, RecordingSlippage
    from qmb.execution.handler import ExecutionSliceHandler

    handler = ExecutionSliceHandler(fill=RecordingFill(), slippage=RecordingSlippage(),
                                    cost=RecordingCost(),
                                    position_cap=qty(10), lot_step=qty(1))
    minted = ok(handler.mint_intents("eurusd", inst()))
    assert tuple(minted) == ()


# --- T-17.3-k (L2) slippage maps pre->post across all five models (buy +/sell -) [R23]
def test_t173k_slippage_maps_across_all_five_models() -> None:
    wide = slice_path(open=100_000, high=110_000, low=90_000, close=100_000,
                      prints=(90_000, 110_000))
    buy = ok(Fill.try_create(qty(10), qty(10), price(100_000), side=Direction.LONG))
    sell = ok(Fill.try_create(qty(10), qty(10), price(100_000), side=Direction.SHORT))
    calibrations = {
        "zero": None,
        "constant-percent": ok(SlippageCalibration.try_create("constant-percent", "b",
                                                              percent=ratio(1, 100))),
        "spread-crossing": ok(SlippageCalibration.try_create("spread-crossing", "b",
                                                            spread=delta(100),
                                                            spread_fraction=ratio(1, 2))),
        "gap-volatility": ok(SlippageCalibration.try_create("gap-volatility", "b",
                                                          range_fraction=ratio(1, 10))),
        "size-tiered": ok(SlippageCalibration.try_create("size-tiered", "b",
                                                       tiers=((qty(100), delta(200)),))),
    }
    assert set(calibrations) == set(SLIPPAGE_MODELS)
    for model, cal in calibrations.items():
        b = ok(slip_fill(buy, wide, model=model, calibration=cal, apply_to_passive_limits=False))
        s = ok(slip_fill(sell, wide, model=model, calibration=cal, apply_to_passive_limits=False))
        assert isinstance(b, Fill) and isinstance(s, Fill)
        if model == "zero":
            assert b.post_slip_price == price(100_000)  # zero shape: post == pre
            assert s.post_slip_price == price(100_000)
        else:
            # buy slips UP (+), sell slips DOWN (-).
            assert b.post_slip_price.as_fraction() > price(100_000).as_fraction()
            assert s.post_slip_price.as_fraction() < price(100_000).as_fraction()


# --- T-17.3-l (L2) slippage vetoes when the slipped print is illegal [R23] P0 --
def test_t173l_slippage_vetoes_illegal_print() -> None:
    # A narrow bar: the +offset pushes the buy print above the high and off the path.
    narrow = slice_path(open=100_000, high=100_000, low=99_900, close=100_000, prints=(100_000,))
    buy = ok(Fill.try_create(qty(10), qty(10), price(100_000), side=Direction.LONG))
    cal = ok(SlippageCalibration.try_create("constant-percent", "b", percent=ratio(1, 100)))
    vetoed = ok(slip_fill(buy, narrow, model="constant-percent", calibration=cal,
                          apply_to_passive_limits=False))
    assert isinstance(vetoed, NoFill) and vetoed.reason == "illegal-print"
    # Counter-case: a wide bar makes the same slipped print legal -> a Fill, not a veto.
    wide = slice_path(open=100_000, high=110_000, low=90_000, close=100_000, prints=(90_000, 110_000))
    assert isinstance(ok(slip_fill(buy, wide, model="constant-percent", calibration=cal,
                                   apply_to_passive_limits=False)), Fill)


# --- T-17.3-m (L2) passive limit fills skip slippage unless configured [R23] ---
def test_t173m_passive_limits_skip_slippage_unless_configured() -> None:
    wide = slice_path(open=100_000, high=110_000, low=90_000, close=100_000, prints=(90_000, 110_000))
    passive = ok(Fill.try_create(qty(10), qty(10), price(100_000), side=Direction.LONG, passive=True))
    cal = ok(SlippageCalibration.try_create("constant-percent", "b", percent=ratio(1, 100)))
    # Not applied to a passive limit by default: post == pre.
    skipped = ok(slip_fill(passive, wide, model="constant-percent", calibration=cal,
                           apply_to_passive_limits=False))
    assert skipped.post_slip_price == price(100_000)
    # Explicitly configured -> the offset IS applied.
    applied = ok(slip_fill(passive, wide, model="constant-percent", calibration=cal,
                           apply_to_passive_limits=True))
    assert applied.post_slip_price.as_fraction() > price(100_000).as_fraction()


# --- T-17.3-n (L3) stochastic term uses a per-run seed derived from run identity [R23]
def test_t173n_slippage_seed_is_deterministic_from_run_identity() -> None:
    from qmf.core.fingerprint import fingerprint

    run_a = ok(fingerprint({"run": "a"}))
    run_b = ok(fingerprint({"run": "b"}))
    # Replay of the same run reproduces the identical draw (SLIP-3, B-13).
    assert ok(derive_slippage_seed(run_a)) == ok(derive_slippage_seed(run_a))
    # A different run identity derives a different seed (identity-bound, not ambient).
    assert ok(derive_slippage_seed(run_a)) != ok(derive_slippage_seed(run_b))


# --- FC-30 (QMX-F030 / OR-11): slip_fill threads the per-run seed to the model boundary [R23,17.3-AC6]
def test_t173o_slip_fill_threads_seed_to_the_model_boundary() -> None:
    """OR-11 (Option A, binding): slip_fill must STOP discarding ``seed`` and thread
    the per-run seed to the slippage-model interface, so a FUTURE stochastic model is
    reproducible by construction (SLIP-3, NFR-03, B-13). The stochastic DRAW itself
    stays UNPROVEN-by-design — V1 ships no random model (see test_t173n) — so this
    proves only the PLUMBING: a test-owned recording model, driven through the REAL
    slip_fill path, receives the exact seed at the model boundary. It is an observer
    at a real seam, never a shim standing in for slip_fill.
    """
    from _e17 import RecordingSlippageModel

    wide = slice_path(open=100_000, high=110_000, low=90_000, close=100_000, prints=(90_000, 110_000))
    buy = ok(Fill.try_create(qty(10), qty(10), price(100_000), side=Direction.LONG))

    # A concrete per-run seed reaches the model boundary verbatim through real slip_fill.
    model = RecordingSlippageModel()
    out = ok(slip_fill(buy, wide, model=model, calibration=None,
                       apply_to_passive_limits=False, seed=1234567890))
    assert model.seen_seeds == [1234567890], "the per-run seed must reach the model boundary"
    # The pipeline still completes past the seam (offset applied, legal print, restamped).
    assert isinstance(out, Fill) and out.post_slip_price is not None

    # The wiring is unconditional: an absent seed is threaded through as None, never invented.
    none_model = RecordingSlippageModel()
    ok(slip_fill(buy, wide, model=none_model, calibration=None, apply_to_passive_limits=False))
    assert none_model.seen_seeds == [None]

    # No randomness was added: the deterministic string models ignore the seed entirely.
    cal = ok(SlippageCalibration.try_create("constant-percent", "b", percent=ratio(1, 100)))
    seeded = ok(slip_fill(buy, wide, model="constant-percent", calibration=cal,
                          apply_to_passive_limits=False, seed=999))
    unseeded = ok(slip_fill(buy, wide, model="constant-percent", calibration=cal,
                            apply_to_passive_limits=False, seed=None))
    assert seeded.post_slip_price == unseeded.post_slip_price  # seed changes no V1 draw


# --- FC-12 (QMX-F015): the run-loop SliceHandler binds and drives the COST port


def test_t171a_cost_port_bound_and_driven_by_the_slice_handler() -> None:
    """17.1-AC1 / 17.4-AC2 (FC-12): ExecutionSliceHandler — the SliceHandler the six
    sub-phases actually drive — binds the COST port and routes execute_resting through
    the composed fill -> slippage -> cost path, so the cost recorder sees the POST-SLIP
    fill and commission has a live producer on real runs. Counter-case: a handler with
    no cost seam (no CostPort field, no itemize call) — commission is never itemized on
    any run the loop drives.
    """
    from _e17 import RecordingCost, RecordingFill, RecordingSlippage
    from qmb.execution.handler import ExecutionSliceHandler
    from qmb.runloop import RestingIntent

    fill, slip, cost = RecordingFill(), RecordingSlippage(post=price(100_500)), RecordingCost()
    handler = ExecutionSliceHandler(
        fill=fill, slippage=slip, cost=cost, position_cap=qty(10), lot_step=qty(1),
    )
    ok(handler.bind_path("eurusd", slice_path(open=100_000, high=110_000, low=90_000,
                                              close=100_000, prints=(90_000, 110_000))))
    resting = ok(RestingIntent.try_create("r1", "eurusd", order=None, authorized=entry()))
    filled = ok(handler.execute_resting(resting, None, inst()))
    assert filled is True
    assert len(cost.calls) == 1, "the cost port must be driven by the handler's own path"
    assert cost.calls[0]["saw_post"] == price(100_500), "cost itemizes the POST-SLIP fill"
    assert handler.costed_fills, "the itemized CostedFill is retained as the commission producer"
    assert handler.costed_fills[0].fill.post_slip_price == price(100_500)
