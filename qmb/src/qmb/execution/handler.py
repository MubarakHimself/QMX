"""Run-loop handler: sub-phase 2 financing plus sub-phase 3 fill/slippage.

Scheduled financing is a position-level cash event at the accounting rollover
(not an order fill). Resting intents present at slice start fill in sub-phase 3.
Intents minted in sub-phase 5 rest. Optimistic taint is unchanged (SC-06).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Quantity
from qmf.core.fingerprint import World
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.door import EntryIntent, ExitIntent

from qmb._refuse import invalid, unavailable
from qmb.execution.fill import (
    FILL_BASIS_WORST_CASE,
    FillOrder,
    cross_declared_path,
    rank_resting_on_path,
    split_path_at,
)
from qmb.execution.financing import (
    FINANCING_CONTENT_DEFERRED_TO,
    FinancingCashEvent,
    OpenPosition,
    apply_financing_rollover,
)
from qmb.execution.ports import (
    CostedFill,
    CostPort,
    Fill,
    FillPort,
    FinancingPort,
    NoFill,
    PartialFill,
    SlicePath,
    SlippagePort,
    slip_then_cost,
)
from qmb.runloop.loop import RestingIntent, SliceObservation

__all__ = ["ExecutionSliceHandler"]


def _empty_paths() -> dict[str, SlicePath]:
    return {}


def _empty_positions() -> list[OpenPosition]:
    return []


def _empty_events() -> list[FinancingCashEvent]:
    return []


def _empty_costed() -> list[CostedFill]:
    return []


@dataclass(slots=True)
class ExecutionSliceHandler:
    """SliceHandler: sub-phase 2 financing, then fill → slippage → cost in sub-phase 3.

    Sub-phase 3 runs the composed execution path (17.1-AC1): fill decides,
    slippage maps price, and the bound COST port itemizes commission on the
    post-slip fill — each itemized :class:`CostedFill` is retained on
    :attr:`costed_fills`, the producer for per-partial commission (17.4-AC2)
    and the cost-drag decomposition (17.5-AC4).
    """

    fill: FillPort
    slippage: SlippagePort
    cost: CostPort
    position_cap: Quantity
    lot_step: Quantity
    fill_basis: str = FILL_BASIS_WORST_CASE
    stale_price_span: object = None
    paths: dict[str, SlicePath] = field(default_factory=_empty_paths)
    remaining_paths: dict[str, SlicePath] = field(default_factory=_empty_paths)
    financing: FinancingPort | None = None
    rollover_calendar: object | None = None
    open_positions: list[OpenPosition] = field(default_factory=_empty_positions)
    financing_writer: WriterId | None = None
    financing_world: World = World.REPLAY
    financing_sequence: int = 0
    financing_events: list[FinancingCashEvent] = field(default_factory=_empty_events)
    costed_fills: list[CostedFill] = field(default_factory=_empty_costed)

    def update_stream(
        self,
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def scheduled_position_event(self, stream_id: str, frontier: Instant) -> Result[None]:
        """Sub-phase 2: apply swap at the calendar's accounting-rollover instant."""
        if self.financing is None:
            return Ok(None)
        if self.rollover_calendar is None:
            return unavailable(
                "calendar",
                "the accounting-rollover instant comes from the bound broker "
                "market-hours calendar, never a hardcoded wall time (AD-8, DEC-0135, FEE-4)",
                stream_id=stream_id,
                gap=FINANCING_CONTENT_DEFERRED_TO,
            )
        if self.financing_writer is None:
            return invalid(
                "writer",
                "a CT-13 financing event is written under an AD-8 WriterId",
                stream_id=stream_id,
            )
        applied = apply_financing_rollover(
            self.financing,
            tuple(self.open_positions),
            frontier=frontier,
            calendar=self.rollover_calendar,
            writer=self.financing_writer,
            world=self.financing_world,
            start_sequence=self.financing_sequence,
            stream_id=stream_id,
        )
        if is_refusal(applied):
            return applied
        self.financing_events.extend(applied.value.events)
        self.financing_sequence += len(applied.value.events)
        return Ok(None)

    def update_closed_data(
        self,
        stream_id: str,
        observation: SliceObservation,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        del stream_id, frontier
        return Ok(())

    def bind_path(self, stream_id: str, path: SlicePath) -> Result[None]:
        """Pin the declared path the slice's resting orders cross."""
        self.paths[stream_id] = path
        self.remaining_paths[stream_id] = path
        return Ok(None)

    def rank_resting(
        self,
        intents: Sequence[RestingIntent],
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[tuple[RestingIntent, ...]]:
        """Deterministic path-split order for this stream's resting cohort (FILL-6)."""
        del observation, frontier
        path = self.remaining_paths.get(stream_id, self.paths.get(stream_id))
        if path is None:
            return Ok(tuple(intents))
        ranked = rank_resting_on_path(intents, path)
        if is_refusal(ranked):
            return ranked
        return Ok(cast("tuple[RestingIntent, ...]", ranked.value))

    def execute_resting(
        self,
        intent: RestingIntent,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[bool]:
        """Sub-phase 3: the composed fill → slippage → cost path (17.1-AC1).

        ``True`` when the resting intent fills. The post-decision pipeline is the
        shared :func:`~qmb.execution.ports.slip_then_cost` tail, so slippage never
        resizes, the COST port itemizes the post-slip fill (never resizing), and
        the itemized :class:`CostedFill` is retained on :attr:`costed_fills`.
        """
        del observation, frontier
        path = self.remaining_paths.get(intent.stream_id, self.paths.get(intent.stream_id))
        if path is None:
            return Ok(False)
        authorized = intent.authorized
        if not isinstance(authorized, (EntryIntent, ExitIntent)):
            return Ok(False)
        order = intent.order if isinstance(intent.order, FillOrder) else None
        requested = order.quantity if order is not None else self.position_cap
        decided = self._decide(authorized, path, requested, order)
        if is_refusal(decided):
            return decided
        if isinstance(decided.value, NoFill):
            return Ok(False)
        costed = slip_then_cost(self.slippage, self.cost, decided.value, path)
        if is_refusal(costed):
            return costed
        if isinstance(costed.value, NoFill):
            return Ok(False)
        outcome = costed.value
        self.costed_fills.append(outcome)
        filled = outcome.fill
        price = filled.post_slip_price
        if price is None:
            price = filled.pre_slip_price
        split = split_path_at(path, price)
        if is_refusal(split):
            return split
        self.remaining_paths[intent.stream_id] = split.value
        return Ok(True)

    def _decide(
        self,
        authorized: EntryIntent | ExitIntent,
        path: SlicePath,
        requested: Quantity,
        order: FillOrder | None,
    ) -> Result[Fill | NoFill | PartialFill]:
        decide = cast(Any, self.fill.decide)
        try:
            return decide(
                authorized,
                path,
                requested_quantity=requested,
                order=order,
                fill_basis=self.fill_basis,
                stale_price_span=self.stale_price_span,
            )
        except TypeError:
            return cross_declared_path(
                authorized,
                path,
                requested_quantity=requested,
                order=order,
                fill_basis=self.fill_basis,
                stale_price_span=self.stale_price_span,
            )
