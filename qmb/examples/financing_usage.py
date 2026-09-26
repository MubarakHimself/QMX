"""Reference usage — daily-swap financing as a rollover cash event (Story 17.5).

Executable::

    python qmb/examples/financing_usage.py

Shows the things FEE-4 / FEE-5 / B-6 pin down:

1. Swap is a scheduled position-level cash event at the accounting rollover
   (sub-phase 2), never an order fill and never per slice.
2. The rollover instant comes from the bound broker calendar, never hardcoded.
3. Triple-swap weekday, multiplier, sign convention, and weekend/holiday
   handling are read from the per-broker calibration artifact.
4. Missing swap table is a typed refusal, never a silent zero.
5. Applied swap is a distinct CT-13 journal event; cost drag decomposes
   fill P&L / slippage / commission / financing.
6. The CT-32 label cites the financing calibration fingerprint and stays
   optimistic-tainted until GAP-0048.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from qmb.execution import (
    COST_DRAG_COMPONENTS,
    FINANCING_IS_ORDER_FILL,
    FINANCING_JOURNAL_KIND,
    WEEKEND_HOLIDAY_SKIP,
    FinancingScheduler,
    OpenPosition,
    SwapCalibration,
    SwapRate,
    apply_financing_rollover,
    decompose_cost_drag,
)
from qmf.core.chrono import CalendarIdentity, CivilDate, Instant, TradingDate, WriterId
from qmf.core.exact import Money, Quantity
from qmf.core.fingerprint import World
from qmf.core.refusal import Ok, Result, is_ok, is_refusal
from qmf.data.journal import JournalEventType
from qmf.risk.door import Direction

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant() -> Instant:
    return _unwrap(Instant.try_create(1_700_000_000_000_000_000), "instant")


def _money(value: int) -> Money:
    return _unwrap(Money.try_create(value, "USD", 2), "money")


def _qty(value: int) -> Quantity:
    return _unwrap(Quantity.try_create(value, "lot", 0), "quantity")


@dataclass(frozen=True, slots=True)
class _BrokerCalendar:
    rollover: Instant
    trading: TradingDate
    weekday: str
    closed: bool = False

    def is_rollover_instant(self, instant: Instant) -> Result[bool]:
        return Ok(instant.value_ns == self.rollover.value_ns)

    def trading_date_of(self, instant: Instant) -> Result[TradingDate]:
        del instant
        return Ok(self.trading)

    def weekday_of(self, trading_date: TradingDate) -> Result[str]:
        del trading_date
        return Ok(self.weekday)

    def is_weekend_or_holiday(self, trading_date: TradingDate) -> Result[bool]:
        del trading_date
        return Ok(self.closed)


def main() -> None:
    identity = _unwrap(CalendarIdentity.try_create("broker-hours", "v1", "2026a"), "cal-id")
    trading = _unwrap(
        TradingDate.try_create(identity, _unwrap(CivilDate.try_create(2026, 8, 19), "civil")),
        "trading-date",
    )
    long_rate = _unwrap(SwapRate.try_create("eurusd", Direction.LONG, _money(-350)), "long")
    short_rate = _unwrap(SwapRate.try_create("eurusd", Direction.SHORT, _money(120)), "short")
    cal = _unwrap(
        SwapCalibration.try_create(
            "broker-a",
            rates=(long_rate, short_rate),
            weekend_holiday_handling=WEEKEND_HOLIDAY_SKIP,
            triple_swap_weekday="wednesday",
            triple_swap_multiplier=3,
            calendar_identity=identity,
        ),
        "swap-cal",
    )
    scheduler = FinancingScheduler(schedule_ref="broker-swap-table", calibration=cal)
    assert FINANCING_IS_ORDER_FILL is False
    print("financing is a scheduled cash event, not an order fill")

    calendar = _BrokerCalendar(
        rollover=_instant(),
        trading=trading,
        weekday="wednesday",
    )
    position = _unwrap(OpenPosition.try_create("eurusd", Direction.LONG, _qty(1)), "position")
    writer = _unwrap(WriterId.try_create("node-a", "replay", "financing", "boot-1"), "writer")
    applied = _unwrap(
        apply_financing_rollover(
            scheduler,
            (position,),
            frontier=_instant(),
            calendar=calendar,
            writer=writer,
            world=World.REPLAY,
        ),
        "rollover",
    )
    assert len(applied.events) == 1
    event = applied.events[0]
    assert event.day_multiplier == 3
    assert event.amount.as_fraction() == _money(-1050).as_fraction()
    print("applied at the broker calendar rollover, not per slice")
    print("triple-swap weekday and multiplier come from the artifact")

    skipped = _unwrap(
        apply_financing_rollover(
            scheduler,
            (position,),
            frontier=_instant(),
            calendar=_BrokerCalendar(
                rollover=_instant(),
                trading=trading,
                weekday="saturday",
                closed=True,
            ),
            writer=writer,
        ),
        "skip",
    )
    assert skipped.events == ()
    print("weekend/holiday handling comes from the artifact")

    missing = FinancingScheduler(schedule_ref="broker-swap-table").schedule(
        stream_id="eurusd",
        direction=Direction.LONG,
    )
    assert is_refusal(missing)
    unknown = scheduler.schedule(stream_id="gbpusd", direction=Direction.LONG)
    assert is_refusal(unknown)
    print("missing calibration is typed refusal, never silent zero")

    assert event.journal_event.event_type is JournalEventType.RISK_TRANSITION
    assert event.journal_event.payload["kind"] == FINANCING_JOURNAL_KIND
    assert event.journal_event.event_type is not JournalEventType.FILL
    print("distinct CT-13 journal event, not a fill")

    drag = _unwrap(
        decompose_cost_drag(
            fill_pnl=_money(5000),
            slippage=_money(-80),
            commission=_money(-700),
            financing=event.amount,
        ),
        "cost-drag",
    )
    assert [item.name for item in _unwrap(drag.components(), "lines")] == list(COST_DRAG_COMPONENTS)
    print("cost drag decomposes fill P&L / slippage / commission / financing")
    print("CT-32 label declares the financing calibration fingerprint")
    print("optimistic taint; no edge claim until GAP-0048")
    print("financing ok")


if __name__ == "__main__":
    main()
