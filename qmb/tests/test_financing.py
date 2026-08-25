"""Story 17.5 — daily-swap financing as a scheduled rollover cash event."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED
from qmb.doors import api
from qmb.execution import (
    COST_ADAPTER_KEY,
    COST_ADAPTER_ZERO,
    COST_COMPONENT_FINANCING,
    COST_DRAG_COMMISSION,
    COST_DRAG_COMPONENTS,
    COST_DRAG_FILL_PNL,
    COST_DRAG_FINANCING,
    COST_DRAG_SLIPPAGE,
    FILL_ADAPTER_DECLARED_PATH,
    FILL_ADAPTER_KEY,
    FINANCING_ADAPTER_SCHEDULED,
    FINANCING_CALIBRATION_KEY,
    FINANCING_CONTENT_DEFERRED_TO,
    FINANCING_IS_ORDER_FILL,
    FINANCING_JOURNAL_EVENT_TYPE,
    FINANCING_JOURNAL_KIND,
    FINANCING_JOURNAL_SUBTYPE,
    FINANCING_SCHEDULE_KEY,
    SLIPPAGE_ADAPTER_KEY,
    SLIPPAGE_ADAPTER_ZERO,
    TAINT_OPTIMISTIC,
    WEEKDAYS,
    WEEKEND_HOLIDAY_APPLY,
    WEEKEND_HOLIDAY_SKIP,
    DeclaredPathFillAdapter,
    ExecutionSliceHandler,
    FinancingScheduler,
    OpenPosition,
    SwapCalibration,
    SwapRate,
    ZeroSlippageAdapter,
    apply_financing_rollover,
    bind_execution_ports,
    decompose_cost_drag,
    financing_identity,
    fingerprint_financing,
    refuse_optimistic_edge_claim,
)
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run, run_slice
from qmf.core.chrono import CalendarIdentity, CivilDate, Instant, TradingDate, WriterId
from qmf.core.exact import Money, Quantity
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal
from qmf.data.journal import JournalEventType
from qmf.risk.door import Direction

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_VENUE = "venue-replay"
_ACCOUNT = "acct-replay"
_SCHEDULE = "broker-swap-table"
_SEED = Money(value=1_000_000, currency="USD", scale=2)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(seed: str):
    return _ok(fingerprint({"seed": seed}))


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _money(value: int, currency: str = "USD", scale: int = 2) -> Money:
    return _ok(Money.try_create(value, currency, scale))


def _qty(value: int) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", 0))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "replay", "financing", "boot-1"))


def _trading_date(*, year: int = 2026, month: int = 8, day: int = 19) -> TradingDate:
    identity = _ok(CalendarIdentity.try_create("broker-hours", "v1", "2026a"))
    civil = _ok(CivilDate.try_create(year, month, day))
    return _ok(TradingDate.try_create(identity, civil))


def _rate(
    stream_id: str = "eurusd",
    direction: Direction = Direction.LONG,
    amount: int = -350,
) -> SwapRate:
    return _ok(SwapRate.try_create(stream_id, direction, _money(amount)))


def _cal(
    *rates: SwapRate,
    weekday: str | None = "wednesday",
    multiplier: int | None = 3,
    handling: str = WEEKEND_HOLIDAY_SKIP,
) -> SwapCalibration:
    return _ok(
        SwapCalibration.try_create(
            "broker-a",
            rates=rates or (_rate(), _rate(direction=Direction.SHORT, amount=120)),
            weekend_holiday_handling=handling,
            triple_swap_weekday=weekday,
            triple_swap_multiplier=multiplier,
            calendar_identity=_ok(CalendarIdentity.try_create("broker-hours", "v1", "2026a")),
        )
    )


def _position(
    stream_id: str = "eurusd",
    direction: Direction = Direction.LONG,
    quantity: int = 2,
) -> OpenPosition:
    return _ok(OpenPosition.try_create(stream_id, direction, _qty(quantity)))


@dataclass(frozen=True, slots=True)
class _Calendar:
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


def _calendar(
    *,
    rollover: Instant | None = None,
    weekday: str = "wednesday",
    closed: bool = False,
    day: int = 19,
) -> _Calendar:
    at = _instant() if rollover is None else rollover
    return _Calendar(
        rollover=at,
        trading=_trading_date(day=day),
        weekday=weekday,
        closed=closed,
    )


def _scheduler(calibration: SwapCalibration | None = None) -> FinancingScheduler:
    return FinancingScheduler(schedule_ref=_SCHEDULE, calibration=calibration)


def _resolved(keys: dict[str, object] | None = None) -> qmb.ResolvedRunConfig:
    payload: dict[str, object] = {
        COST_ADAPTER_KEY: COST_ADAPTER_ZERO,
        FILL_ADAPTER_KEY: FILL_ADAPTER_DECLARED_PATH,
        FINANCING_SCHEDULE_KEY: _SCHEDULE,
        SLIPPAGE_ADAPTER_KEY: SLIPPAGE_ADAPTER_ZERO,
        STREAM_SET_KEY: ("eurusd",),
    }
    if keys:
        payload.update(keys)
    stamp = _fp("run")
    return qmb.ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=payload,
        clock=CLOCK_REPLAY,
        data_provenance=PROVENANCE_RECORDED,
        world=World.REPLAY,
        fingerprint=stamp,
    )


def test_financing_identity_catalog_and_api_door() -> None:
    identity = financing_identity()
    assert identity["financing_is_order_fill"] is FINANCING_IS_ORDER_FILL is False
    assert identity["applied_per_slice"] is False
    assert identity["applied_at"] == "accounting-rollover"
    assert identity["subphase"] == "scheduled-position-events"
    assert identity["silent_zero_on_missing_table"] is False
    assert identity["content_deferred_to"] == FINANCING_CONTENT_DEFERRED_TO == "GAP-0048"
    assert identity["component_name"] == COST_COMPONENT_FINANCING
    assert identity["cost_drag"] == list(COST_DRAG_COMPONENTS)
    assert COST_DRAG_COMPONENTS == (
        COST_DRAG_FILL_PNL,
        COST_DRAG_SLIPPAGE,
        COST_DRAG_COMMISSION,
        COST_DRAG_FINANCING,
    )
    assert identity["journal_event_type"] == FINANCING_JOURNAL_EVENT_TYPE == "risk transition"
    assert identity["journal_kind"] == FINANCING_JOURNAL_KIND
    assert identity["journal_subtype"] == FINANCING_JOURNAL_SUBTYPE
    assert identity["weekdays"] == list(WEEKDAYS)
    assert "version" not in identity
    assert qmb.__version__ not in identity.values()
    stamped = fingerprint_financing()
    assert is_ok(stamped)
    assert stamped.value.value.startswith("fp1:sha256:")
    assert api.financing_identity() == qmb.financing_identity() == identity
    assert api.SwapCalibration is qmb.SwapCalibration is SwapCalibration
    assert api.apply_financing_rollover is qmb.apply_financing_rollover is apply_financing_rollover
    assert api.FINANCING_CALIBRATION_KEY == FINANCING_CALIBRATION_KEY
    assert qmb.FINANCING_CALIBRATION_KEY == FINANCING_CALIBRATION_KEY
    assert api.FinancingScheduler is qmb.FinancingScheduler is FinancingScheduler


def test_scheduled_cash_event_at_rollover_not_fill_not_per_slice() -> None:
    cal = _cal()
    scheduler = _scheduler(cal)
    unit = _ok(scheduler.schedule(stream_id="eurusd", direction=Direction.LONG))
    assert isinstance(unit, Money)
    assert unit.as_fraction() == _money(-350).as_fraction()
    credit = _ok(scheduler.schedule(stream_id="eurusd", direction=Direction.SHORT))
    assert credit.as_fraction() == _money(120).as_fraction()
    calendar = _calendar(weekday="thursday")
    applied = _ok(
        scheduler.apply_at_rollover(
            (_position(),),
            frontier=_instant(),
            calendar=calendar,
            writer=_writer(),
        )
    )
    assert FINANCING_IS_ORDER_FILL is False
    assert len(applied.events) == 1
    event = applied.events[0]
    assert event.amount.as_fraction() == _money(-700).as_fraction()
    assert event.day_multiplier == 1
    assert event.taint == TAINT_OPTIMISTIC
    assert event.journal_event.event_type is JournalEventType.RISK_TRANSITION
    later = _ok(
        scheduler.apply_at_rollover(
            (_position(),),
            frontier=_instant(_NS + 1),
            calendar=calendar,
            writer=_writer(),
        )
    )
    assert later.events == ()
    assert later.skipped == ()


def test_triple_swap_and_weekend_holiday_come_from_artifact() -> None:
    cal = _cal(weekday="wednesday", multiplier=3, handling=WEEKEND_HOLIDAY_SKIP)
    scheduler = _scheduler(cal)
    triple = _ok(
        scheduler.apply_at_rollover(
            (_position(quantity=1),),
            frontier=_instant(),
            calendar=_calendar(weekday="wednesday"),
            writer=_writer(),
        )
    )
    assert len(triple.events) == 1
    assert triple.events[0].day_multiplier == 3
    assert triple.events[0].amount.as_fraction() == _money(-1050).as_fraction()
    skipped = _ok(
        scheduler.apply_at_rollover(
            (_position(quantity=1),),
            frontier=_instant(),
            calendar=_calendar(weekday="saturday", closed=True, day=22),
            writer=_writer(),
        )
    )
    assert skipped.events == ()
    assert skipped.skipped == (_position(quantity=1),)
    holiday_apply = _scheduler(
        _cal(weekday="wednesday", multiplier=3, handling=WEEKEND_HOLIDAY_APPLY)
    )
    charged = _ok(
        holiday_apply.apply_at_rollover(
            (_position(quantity=1),),
            frontier=_instant(),
            calendar=_calendar(weekday="wednesday", closed=True),
            writer=_writer(),
        )
    )
    assert len(charged.events) == 1
    assert charged.events[0].day_multiplier == 3
    invented = SwapCalibration.try_create(
        "broker-a",
        rates=(_rate(),),
        weekend_holiday_handling=WEEKEND_HOLIDAY_SKIP,
        triple_swap_weekday="wednesday",
    )
    assert is_refusal(invented)
    assert invented.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    hardcoded = SwapCalibration.try_create(
        "broker-a",
        rates=(_rate(),),
        weekend_holiday_handling=WEEKEND_HOLIDAY_SKIP,
        triple_swap_multiplier=3,
    )
    assert is_refusal(hardcoded)
    assert hardcoded.category is RefusalCategory.INVALID_INPUT


def test_missing_swap_table_is_typed_refusal_never_silent_zero() -> None:
    missing = _scheduler().schedule(stream_id="eurusd", direction=Direction.LONG)
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert missing.context["field"] == "financing_schedule"
    assert missing.context["gap"] == FINANCING_CONTENT_DEFERRED_TO
    assert missing.context["financing_is_order_fill"] is False
    empty = _cal()
    unknown = _scheduler(empty).schedule(stream_id="gbpusd", direction=Direction.LONG)
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert unknown.context["field"] == "swap_table"
    applied = apply_financing_rollover(
        _scheduler(empty),
        (_position(stream_id="gbpusd"),),
        frontier=_instant(),
        calendar=_calendar(),
        writer=_writer(),
    )
    assert is_refusal(applied)
    assert applied.context["field"] == "swap_table"
    bound = _ok(bind_execution_ports(_resolved()))
    silent = bound.ports.financing.schedule(stream_id="eurusd", direction=Direction.LONG)
    assert is_refusal(silent)
    assert silent.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_distinct_journal_event_and_cost_drag_decomposition() -> None:
    cal = _cal()
    applied = _ok(
        _scheduler(cal).apply_at_rollover(
            (_position(), _position(direction=Direction.SHORT, quantity=1)),
            frontier=_instant(),
            calendar=_calendar(weekday="thursday"),
            writer=_writer(),
        )
    )
    assert len(applied.events) == 2
    long_event, short_event = applied.events
    assert long_event.journal_event.event_type is JournalEventType.RISK_TRANSITION
    assert long_event.journal_event.payload["kind"] == FINANCING_JOURNAL_KIND
    assert long_event.journal_event.payload["subtype"] == FINANCING_JOURNAL_SUBTYPE
    assert long_event.journal_event.payload["financing_is_order_fill"] is False
    assert long_event.journal_event.event_type is not JournalEventType.FILL
    assert long_event.component.name == COST_COMPONENT_FINANCING
    assert short_event.amount.as_fraction() == _money(120).as_fraction()
    drag = _ok(
        decompose_cost_drag(
            fill_pnl=_money(5000),
            slippage=_money(-80),
            commission=_money(-700),
            financing=long_event.amount,
        )
    )
    assert drag.fill_pnl.as_fraction() == _money(5000).as_fraction()
    assert drag.slippage.as_fraction() == _money(-80).as_fraction()
    assert drag.commission.as_fraction() == _money(-700).as_fraction()
    assert drag.financing.as_fraction() == long_event.amount.as_fraction()
    lines = _ok(drag.components())
    assert [item.name for item in lines] == list(COST_DRAG_COMPONENTS)
    total = _ok(drag.total())
    assert total.as_fraction() == _money(5000 - 80 - 700 - 700).as_fraction()
    assert long_event.position.quantity.as_fraction() == _qty(2).as_fraction()


def test_ct32_label_declares_financing_fingerprint_and_stays_optimistic() -> None:
    cal = _cal()
    stamp = _fp("fin-ct32")
    with_cal = qmb.ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",), FINANCING_CALIBRATION_KEY: cal.fingerprint},
        clock=CLOCK_REPLAY,
        data_provenance=PROVENANCE_RECORDED,
        world=World.REPLAY,
        fingerprint=stamp,
    )
    without = qmb.ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock=CLOCK_REPLAY,
        data_provenance=PROVENANCE_RECORDED,
        world=World.REPLAY,
        fingerprint=stamp,
    )
    observation = _ok(SliceObservation.try_create("eurusd", _instant(), True))
    labelled = _ok(run(slices=((observation,),), config=with_cal, handler=SilentSliceHandler()))
    baseline = _ok(run(slices=((observation,),), config=without, handler=SilentSliceHandler()))
    assert labelled.performance_result is not None
    assert baseline.performance_result is not None
    inputs = labelled.performance_result.result_label.input_fingerprints
    assert cal.fingerprint in inputs
    assert cal.fingerprint not in baseline.performance_result.result_label.input_fingerprints
    assert _ok(labelled.ct32_fingerprint()).value != _ok(baseline.ct32_fingerprint()).value
    bound = _ok(bind_execution_ports(_resolved({FINANCING_CALIBRATION_KEY: cal})))
    assert isinstance(bound.ports.financing, FinancingScheduler)
    assert bound.ports.financing.taint == TAINT_OPTIMISTIC
    fidelity = bound.fidelity.bound[3]
    assert fidelity.adapter_id == f"financing.{FINANCING_ADAPTER_SCHEDULED}"
    assert fidelity.calibration_ref == cal.fingerprint.value
    assert fidelity.taint == TAINT_OPTIMISTIC
    edge = refuse_optimistic_edge_claim(taint=bound.fidelity.taint, claims_edge=True)
    assert is_refusal(edge)
    assert edge.category is RefusalCategory.POLICY_REJECTION
    budget = refuse_optimistic_edge_claim(taint=bound.fidelity.taint, spends_split_budget=True)
    assert is_refusal(budget)


def test_subphase_2_handler_applies_only_at_calendar_rollover() -> None:
    cal = _cal()
    scheduler = _scheduler(cal)
    calendar = _calendar(weekday="thursday")
    fill = DeclaredPathFillAdapter()
    slip = ZeroSlippageAdapter()
    handler = ExecutionSliceHandler(
        fill=fill,
        slippage=slip,
        position_cap=_qty(1),
        lot_step=_qty(1),
        financing=scheduler,
        rollover_calendar=calendar,
        open_positions=[_position(quantity=1)],
        financing_writer=_writer(),
    )
    observation = _ok(SliceObservation.try_create("eurusd", _instant(_NS + 5), True))
    quiet = _ok(
        run_slice(
            (observation,),
            stream_set=("eurusd",),
            handler=handler,
        )
    )
    assert quiet.subphase_order()[1] == "scheduled-position-events"
    assert handler.financing_events == []
    rollover_obs = _ok(SliceObservation.try_create("eurusd", _instant(), True))
    fired = _ok(
        run_slice(
            (rollover_obs,),
            stream_set=("eurusd",),
            handler=handler,
        )
    )
    assert fired.subphase_order()[1] == "scheduled-position-events"
    assert len(handler.financing_events) == 1
    assert handler.financing_events[0].amount.as_fraction() == _money(-350).as_fraction()
    missing_cal = ExecutionSliceHandler(
        fill=fill,
        slippage=slip,
        position_cap=_qty(1),
        lot_step=_qty(1),
        financing=scheduler,
        open_positions=[_position()],
        financing_writer=_writer(),
    )
    refused = missing_cal.scheduled_position_event("eurusd", _instant())
    assert is_refusal(refused)
    assert refused.context["field"] == "calendar"
