"""Epic 17 · Group E — daily-swap financing at the rollover (Story 17.5, R29-R33).

Independent, requirements-derived assertions (T-17.5-a..f). Financing is a scheduled
position-level cash event at the per-broker AD-8 accounting rollover — never an order
fill, never per slice; triple-swap/weekend/sign are read from a versioned per-broker
artifact (never invented); an absent swap table refuses (never a silent zero); each
swap is a distinct CT-13 event and cost drag decomposes into four attributable lines
(FEE-4/FEE-5, AR-56, B-2, DEC-0135, SC-07). A failing test is a FINDING.
"""

from __future__ import annotations

from _e17 import FakeCalendar, inst, money, ok, qty, refusal, writer

from qmf.core.exact import Money
from qmf.core.fingerprint import Fingerprint, World
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.door import Direction
from qmb.execution.financing import (
    COST_DRAG_COMPONENTS,
    FINANCING_IS_ORDER_FILL,
    FINANCING_JOURNAL_KIND,
    FinancingScheduler,
    OpenPosition,
    SwapCalibration,
    SwapRate,
    apply_financing_rollover,
    charge_swap,
    decompose_cost_drag,
    financing_calibration_fingerprint,
    lookup_swap_rate,
    mint_financing_journal_event,
)
from qmb.execution.ports import TAINT_OPTIMISTIC


def _swaps(*, long_minor=-5, short_minor=3, handling="apply", triple_weekday=None,
           triple_mult=None, instr="eurusd"):
    rates = (
        ok(SwapRate.try_create(instr, Direction.LONG, money(long_minor))),
        ok(SwapRate.try_create(instr, Direction.SHORT, money(short_minor))),
    )
    return ok(SwapCalibration.try_create("broker-x", rates=rates,
                                         weekend_holiday_handling=handling,
                                         triple_swap_weekday=triple_weekday,
                                         triple_swap_multiplier=triple_mult))


def _scheduler(cal=None):
    return FinancingScheduler(schedule_ref="fx-broker", calibration=cal)


# --- T-17.5-a (L2) scheduled cash event at rollover, exact Money, per direction [R29] P0
def test_t175a_scheduled_cash_event_at_rollover_per_instrument_direction() -> None:
    cal = _swaps(long_minor=-5, short_minor=3)
    sched = _scheduler(cal)
    positions = (
        ok(OpenPosition.try_create("eurusd", Direction.LONG, qty(10))),
        ok(OpenPosition.try_create("eurusd", Direction.SHORT, qty(10))),
    )
    rollover = ok(apply_financing_rollover(sched, positions, frontier=inst(),
                                           calendar=FakeCalendar(is_rollover=True),
                                           writer=writer(), world=World.REPLAY))
    assert len(rollover.events) == 2
    by_dir = {e.position.direction: e.amount for e in rollover.events}
    # Exact-integer Money per instrument x direction; long and short differ (per direction).
    assert by_dir[Direction.LONG] == money(-50)   # -0.05 x 10
    assert by_dir[Direction.SHORT] == money(30)    # +0.03 x 10
    for e in rollover.events:
        assert isinstance(e.amount, Money)
    # It is a scheduled cash event, never an order fill.
    assert FINANCING_IS_ORDER_FILL is False
    # Applied at the rollover, not per slice: away from the rollover instant nothing charges.
    off = ok(apply_financing_rollover(sched, positions, frontier=inst(),
                                      calendar=FakeCalendar(is_rollover=False),
                                      writer=writer(), world=World.REPLAY))
    assert off.events == ()
    # The rollover instant comes from the calendar, never a hardcoded wall time.
    assert is_refusal(apply_financing_rollover(sched, positions, frontier=inst(),
                                               calendar=None, writer=writer(), world=World.REPLAY))


# --- T-17.5-b (L2) triple-swap / weekend / sign read from the artifact [R30] ---
def test_t175b_triple_swap_weekend_and_sign_from_artifact() -> None:
    # Triple-swap weekday is TUESDAY per the artifact (never a hardcoded Wednesday).
    cal = _swaps(long_minor=-5, triple_weekday="tuesday", triple_mult=3)
    pos = ok(OpenPosition.try_create("eurusd", Direction.LONG, qty(10)))
    monday = ok(charge_swap(pos, cal, weekday="monday", closed=False))
    tuesday = ok(charge_swap(pos, cal, weekday="tuesday", closed=False))
    wednesday = ok(charge_swap(pos, cal, weekday="wednesday", closed=False))
    assert monday.day_multiplier == 1 and monday.amount == money(-50)
    assert tuesday.day_multiplier == 3 and tuesday.amount == money(-150)  # 3x on tuesday
    assert wednesday.day_multiplier == 1  # NOT tripled on wednesday
    # Sign convention: carry may be a credit (short rate is positive).
    short_pos = ok(OpenPosition.try_create("eurusd", Direction.SHORT, qty(10)))
    credit = ok(charge_swap(short_pos, cal, weekday="monday", closed=False))
    assert credit.amount == money(30)  # a positive (credit) carry, preserved
    # Weekend handling read from the artifact: skip -> no charge; apply -> charged.
    skip_cal = _swaps(handling="skip")
    skipped = ok(charge_swap(pos, skip_cal, weekday="saturday", closed=True))
    assert skipped.skipped is True and skipped.amount is None
    applied = ok(charge_swap(pos, _swaps(handling="apply"), weekday="saturday", closed=True))
    assert applied.skipped is False and applied.amount is not None


# --- T-17.5-c (L3) no bound swap table -> CT-04 refusal, never a silent zero [R31] P0
def test_t175c_absent_swap_table_refuses_never_zero() -> None:
    # A scheduler bound with NO swap calibration refuses (never a silent zero).
    none = refusal(_scheduler(None).schedule(stream_id="eurusd", direction=Direction.LONG))
    assert none.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # A calibration with no cell for this instrument refuses at lookup (never zero).
    cal = _swaps(instr="eurusd")
    miss = refusal(lookup_swap_rate(cal, "gbpusd", Direction.LONG))
    assert miss.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # And the rollover itself refuses for an uncovered instrument.
    uncovered = ok(OpenPosition.try_create("gbpusd", Direction.LONG, qty(10)))
    at_rollover = refusal(apply_financing_rollover(_scheduler(cal), (uncovered,), frontier=inst(),
                                                   calendar=FakeCalendar(is_rollover=True),
                                                   writer=writer(), world=World.REPLAY))
    assert at_rollover.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # Counter-case: the covered instrument charges (proves refusal is content-driven).
    covered = ok(OpenPosition.try_create("eurusd", Direction.LONG, qty(10)))
    assert is_ok(apply_financing_rollover(_scheduler(cal), (covered,), frontier=inst(),
                                          calendar=FakeCalendar(is_rollover=True),
                                          writer=writer(), world=World.REPLAY))


# --- T-17.5-d (L3) swap is a distinct CT-13 event, separate from a fill [R32] P1
def test_t175d_swap_is_a_distinct_journal_event() -> None:
    pos = ok(OpenPosition.try_create("eurusd", Direction.LONG, qty(10)))
    event = ok(mint_financing_journal_event(position=pos, amount=money(-50), day_multiplier=1,
                                             instant=inst(), writer=writer(), world=World.REPLAY,
                                             sequence=0))
    # The swap event is a distinct journal event, NOT a fill or an order event.
    assert event.event_type.value not in ("fill", "order")
    # It is self-identifying as financing (a swap-rollover), not folded into a fill.
    assert event.payload["kind"] == FINANCING_JOURNAL_KIND
    assert event.payload["financing_is_order_fill"] is False
    # (See findings.csv E17-F02: CT-13's seven types name no financing/swap kind; the swap
    #  is mapped onto 'risk transition' — the exact event_type mapping is under-specified.)


# --- T-17.5-e (L2) cost drag decomposes into four attributable lines [R32] -----
def test_t175e_cost_drag_decomposes_into_four_lines() -> None:
    drag = ok(decompose_cost_drag(fill_pnl=money(100), slippage=money(-2), commission=money(-3),
                                  financing=money(-5)))
    components = ok(drag.components())
    names = [c.name for c in components]
    # Four separately attributable lines — financing is never folded into fill P&L.
    assert names == list(COST_DRAG_COMPONENTS)
    assert len(set(names)) == 4
    for c in components:
        assert isinstance(c.amount, Money)
    assert ok(drag.total()) == money(90)  # 100 - 2 - 3 - 5
    # Cost-drag lines share one currency; a mismatch is refused (no silent conversion).
    assert is_refusal(decompose_cost_drag(fill_pnl=money(100), slippage=money(-2, ),
                                          commission=ok(Money.try_create(-3, "EUR", 2)),
                                          financing=money(-5)))


# --- T-17.5-f (L3) financing calibration fingerprint in the label, still tainted [R33]
def test_t175f_financing_fingerprint_in_label_and_optimistic_taint() -> None:
    cal = _swaps()
    sched = _scheduler(cal)
    ident = ok(sched.fidelity())
    # The financing calibration fingerprint is declared in the fidelity label (B-10, B-13).
    assert ident.calibration_ref == cal.fingerprint.value
    assert ident.taint == TAINT_OPTIMISTIC
    # The citation coerces to the same fingerprint.
    assert ok(financing_calibration_fingerprint(cal)) == cal.fingerprint
    assert isinstance(cal.fingerprint, Fingerprint)
    # A different swap table declares a different fingerprint (falsifiable).
    other = _swaps(long_minor=-9)
    assert other.fingerprint.value != cal.fingerprint.value
    # The run remains optimistic-tainted, barred from edge/split-budget claims.
    from qmb.execution.ports import refuse_optimistic_edge_claim

    assert refuse_optimistic_edge_claim(taint=sched.taint).value is None
    assert is_refusal(refuse_optimistic_edge_claim(taint=sched.taint, claims_edge=True))
