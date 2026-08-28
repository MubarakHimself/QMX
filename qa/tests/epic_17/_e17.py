"""Shared construction mechanics for the INDEPENDENT Epic 17 (qmb-execution-ports) audit.

Assertions live in the test modules and assert what the RATIFIED requirements
demand (epics.md Stories 17.1-17.5 ACs + the QMB B-6/B-7 spine + the FILL/SLIP/
FEE/SPREAD/LABEL source spec + CT-* contracts, per PLAN.md), never what the
source happens to do. This module supplies ONLY construction mechanics (building
Prices, Money, intents, calibration fixtures, stub adapters, a fake calendar) so
the requirement-level assertions can run. A failing test is a FINDING, never a
licence to soften an assertion or edit source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from qmf.core.chrono import Instant, TradingDate, WriterId
from qmf.core.exact import (
    ExactRational,
    Money,
    Price,
    PriceDelta,
    Quantity,
    UnitKind,
    ValueFactor,
)
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, Result, is_ok, is_refusal
from qmf.risk.door import (
    CitedEvidence,
    Direction,
    EntryIntent,
    EvidenceSlot,
    ExitIntent,
    ExitKind,
    ReasonCode,
)
from qmf.risk.paper import ExecutionTarget
from qmb.config.compiler import ResolvedRunConfig
from qmb.config.replay import mint_replay_binding
from qmb.execution.ports import (
    CostedFill,
    Fill,
    NoFill,
    PartialFill,
    SlicePath,
    restamp_filled,
)

T = TypeVar("T")

NS: int = 1_700_000_000_000_000_000
_VENUE = VenueId(value="sim-venue")
_INSTRUMENT = Instrument(venue=_VENUE, symbol="EURUSD")
_PRICE_SCALE = 5


def ok(result: Result[T]) -> T:
    """Unwrap an ``Ok`` or fail loudly with the refusal context."""
    assert is_ok(result), f"expected Ok, got refusal: {getattr(result, 'context', result)!r}"
    return result.value


def refusal(result: object) -> object:
    assert is_refusal(result), f"expected a TypedRefusal, got Ok: {result!r}"
    return result


def instrument(symbol: str = "EURUSD") -> Instrument:
    return Instrument(venue=_VENUE, symbol=symbol)


def price(value: int, *, instr: Instrument | None = None, scale: int = _PRICE_SCALE) -> Price:
    return ok(Price.try_create(value, instr if instr is not None else _INSTRUMENT, scale))


def delta(value: int, *, instr: Instrument | None = None, scale: int = _PRICE_SCALE) -> PriceDelta:
    return ok(PriceDelta.try_create(value, instr if instr is not None else _INSTRUMENT, scale))


def qty(value: int, *, unit: str = "lot", scale: int = 0) -> Quantity:
    return ok(Quantity.try_create(value, unit, scale))


def money(value: int, *, currency: str = "USD", scale: int = 2) -> Money:
    return ok(Money.try_create(value, currency, scale))


def ratio(numerator: int, denominator: int) -> ExactRational:
    return ok(ExactRational.try_create(numerator, denominator, UnitKind.DIMENSIONLESS_RATIO))


def value_factor(numerator: int = 1, denominator: int = 1, *, instr: Instrument | None = None,
                 currency: str = "USD") -> ValueFactor:
    return ok(
        ValueFactor.try_create(
            numerator, denominator, instr if instr is not None else _INSTRUMENT, currency
        )
    )


def inst(ns: int = NS) -> Instant:
    return ok(Instant.try_create(ns))


def writer() -> WriterId:
    return ok(WriterId.try_create("machine-1", "recorder", "stream-a", "boot-1"))


def trading_date() -> TradingDate:
    from qmf.core.chrono import CalendarIdentity, CivilDate

    cal = ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"))
    civil = ok(CivilDate.try_create(2026, 1, 2))
    return ok(TradingDate.try_create(cal, civil))


# --- CT-23 intents -----------------------------------------------------------


def reason() -> ReasonCode:
    return ok(ReasonCode.try_create("momentum-break", "scalper-v1"))


def target() -> ExecutionTarget:
    from qmf.core import AccountRole

    return ok(ExecutionTarget.try_create(AccountRole.LIVE, _VENUE, "acct-1"))


def cited() -> CitedEvidence:
    slot = ok(EvidenceSlot.try_create("sqs", "sqs-ref-1", inst()))
    return ok(CitedEvidence.try_create(sqs_reading=slot))


def entry(*, direction: Direction = Direction.LONG, instr: Instrument | None = None) -> EntryIntent:
    return ok(
        EntryIntent.try_create(
            instr if instr is not None else _INSTRUMENT,
            direction,
            reason(),
            target(),
            cited_evidence=cited(),
        )
    )


def exit_intent() -> ExitIntent:
    return ok(ExitIntent.try_create(ExitKind.CLOSE_FULL, reason(), ok(fingerprint({"vp": "vp-1"}))))


def r_multiple(num: int, den: int = 1) -> ExactRational:
    return ok(ExactRational.try_create(num, den, UnitKind.R_MULTIPLE))


def exit_logic_ref():
    from qmf.risk.door import ExitLogicRef

    return ok(ExitLogicRef.try_create("book.default.evidence_stop", None))


class OffsetStopModule:
    """A door-side ExitLogicModule fake that derives a fixed-offset full-loss price."""

    def __init__(self, offset: int = 500) -> None:
        self.offset = offset

    def derive_full_loss_price(self, *, entry_price, direction, cited_evidence):
        value = (
            entry_price.value - self.offset
            if direction is Direction.LONG
            else entry_price.value + self.offset
        )
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class NoStopModule:
    """A module that can derive NO full-loss price — AD-40 precondition fails."""

    def derive_full_loss_price(self, *, entry_price, direction, cited_evidence):
        from qmf.risk.door import refuse_no_full_loss_price

        return refuse_no_full_loss_price(module="none")


# --- resolved run-config -----------------------------------------------------


def config(*, clock: str = "replay", data_provenance: str = "recorded",
           world: World = World.REPLAY, with_binding: bool = False, **keys: object) -> ResolvedRunConfig:
    """A resolved, read-only run-config built via the frozen dataclass (B-3).

    Same ``keys`` => same fingerprint. When ``with_binding`` a real world=replay
    ReplayBinding is minted so ``execute`` can run the full CT-23 door path.
    """
    stamp = ok(fingerprint({"n": "e17-cfg", "keys": sorted(str(k) for k in keys),
                            "clock": clock, "prov": data_provenance}))
    binding = None
    if with_binding:
        binding = ok(
            mint_replay_binding(
                book_fp1=stamp,
                bms_fp1=stamp,
                bot_fp1=stamp,
                starting_capital=money(10_000_00),
                seed_overridden=False,
                venue_id=_VENUE,
                account_id="acct-1",
                clock=clock,
                data_provenance=data_provenance,
                keys={},
            )
        )
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=dict(keys),
        clock=clock,
        data_provenance=data_provenance,
        world=world,
        fingerprint=stamp,
        binding_fp1=binding.fingerprint if binding is not None else stamp,
        replay_binding=binding,
    )


def replay_binding():
    """A standalone world=replay binding for risk.py functions."""
    stamp = ok(fingerprint({"n": "e17-binding"}))
    return ok(
        mint_replay_binding(
            book_fp1=stamp,
            bms_fp1=stamp,
            bot_fp1=stamp,
            starting_capital=money(10_000_00),
            seed_overridden=False,
            venue_id=_VENUE,
            account_id="acct-1",
            clock="replay",
            data_provenance="recorded",
            keys={},
        )
    )


# --- slice path --------------------------------------------------------------


def slice_path(
    *,
    prints: tuple[int, ...] = (100_000,),
    open: int | None = None,
    high: int | None = None,
    low: int | None = None,
    close: int | None = None,
    current: int | None = None,
    prior_close: int | None = None,
    session_open: bool = False,
    session_close: bool = False,
    market_closed: bool = False,
    bid: int | None = None,
    ask: int | None = None,
    bar_start: int | None = None,
    bar_end: int | None = None,
    stream_id: str = "eurusd",
    instr: Instrument | None = None,
) -> SlicePath:
    instr = instr if instr is not None else _INSTRUMENT

    def _p(v: int | None) -> Price | None:
        return None if v is None else price(v, instr=instr)

    return ok(
        SlicePath.try_create(
            stream_id,
            tuple(price(v, instr=instr) for v in prints),
            open=_p(open),
            high=_p(high),
            low=_p(low),
            close=_p(close),
            current=_p(current),
            prior_close=_p(prior_close),
            session_open=session_open,
            session_close=session_close,
            market_closed=market_closed,
            bid=_p(bid),
            ask=_p(ask),
            bar_start=None if bar_start is None else inst(bar_start),
            bar_end=None if bar_end is None else inst(bar_end),
        )
    )


# --- stub adapters (test-owned observers) ------------------------------------


class RecordingFill:
    """A FillPort stub that records what it saw and returns a scripted decision."""

    def __init__(self, decision: object | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._decision = decision

    def decide(self, intent, path, *, requested_quantity, **rest):
        self.calls.append({"intent": intent, "path": path, "requested": requested_quantity})
        if self._decision is not None:
            return Ok(self._decision)
        built = Fill.try_create(requested_quantity, requested_quantity, price(100_000))
        return built


class RecordingSlippage:
    """A SlippagePort stub that records and maps pre->post without resizing."""

    def __init__(self, *, veto: bool = False, post: object | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._veto = veto
        self._post = post

    def apply(self, fill, path):
        self.calls.append({"fill": fill, "path": path, "saw_post": fill.post_slip_price})
        if self._veto:
            return NoFill.try_create("illegal-print")
        post = self._post if self._post is not None else fill.pre_slip_price
        return restamp_filled(fill, post_slip_price=post)


class RecordingSlippageModel:
    """A test-owned SlippageModel observer at slip_fill's per-model boundary (SLIP-3, OR-11).

    Records the per-run seed handed to it AT the model boundary when driven through
    the REAL slip_fill path, and returns a FIXED, deterministic offset. This is a
    plumbing probe, not a stochastic model — nothing here draws or is random. A
    future stochastic model would consume the seed here; this one only witnesses it.
    """

    def __init__(self, *, offset_value: int = 100) -> None:
        self.seen_seeds: list[int | None] = []
        self._offset_value = offset_value

    def offset(self, fill, path, calibration, *, seed):
        self.seen_seeds.append(seed)
        return Ok(delta(self._offset_value))


class RecordingCost:
    """A CostPort stub that records and itemizes an empty cost set (no resize)."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def quote(self, fill):
        return money(0)

    def itemize(self, fill):
        self.calls.append({"fill": fill, "saw_post": fill.post_slip_price})
        return CostedFill.try_create(fill, ())


class RecordingFinancing:
    """A FinancingPort stub (scheduled cash event, never an order fill)."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def schedule(self, *, stream_id, direction):
        self.calls.append({"stream_id": stream_id, "direction": direction})
        return money(0)


@dataclass
class ResizingCost:
    """A malicious cost port that RESIZES the fill — used to prove the guard."""

    def quote(self, fill):
        return money(0)

    def itemize(self, fill):
        smaller = ok(Quantity.try_create(1, fill.quantity.unit, fill.quantity.scale))
        resized = ok(Fill.try_create(smaller, smaller, fill.pre_slip_price,
                                     post_slip_price=fill.post_slip_price))
        return CostedFill.try_create(resized, ())


# --- fake rollover calendar --------------------------------------------------


class FakeCalendar:
    """A duck-typed RolloverCalendar answering fixed schedule facts (test-owned)."""

    def __init__(self, *, is_rollover: bool = True, weekday: str = "monday",
                 closed: bool = False) -> None:
        self._is_rollover = is_rollover
        self._weekday = weekday
        self._closed = closed
        self._td = trading_date()

    def is_rollover_instant(self, instant):
        return Ok(self._is_rollover)

    def trading_date_of(self, instant):
        return Ok(self._td)

    def weekday_of(self, td):
        return Ok(self._weekday)

    def is_weekend_or_holiday(self, td):
        return Ok(self._closed)


def is_ref(result) -> bool:
    return is_refusal(result)
