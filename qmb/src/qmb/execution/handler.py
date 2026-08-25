"""Run-loop sub-phase 3 handler: fill then slippage against the declared path.

Resting intents present at slice start fill here. Intents minted in sub-phase 5
are not eligible against this slice's path — they rest. Intra-slice order is
the declared-path split (FILL-6). Optimistic taint is unchanged (SC-06).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from qmf.core.chrono import Instant
from qmf.core.exact import Quantity
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.door import EntryIntent, ExitIntent

from qmb._refuse import invalid
from qmb.execution.fill import (
    FILL_BASIS_WORST_CASE,
    FillOrder,
    cross_declared_path,
    rank_resting_on_path,
    split_path_at,
)
from qmb.execution.ports import (
    TAINT_OPTIMISTIC,
    Fill,
    FillPort,
    NoFill,
    PartialFill,
    SlicePath,
    SlippagePort,
)
from qmb.runloop.loop import RestingIntent, SliceObservation

__all__ = ["ExecutionSliceHandler"]


def _empty_paths() -> dict[str, SlicePath]:
    return {}


@dataclass(slots=True)
class ExecutionSliceHandler:
    """SliceHandler that runs fill → slippage in sub-phase 3 (B-2)."""

    fill: FillPort
    slippage: SlippagePort
    position_cap: Quantity
    lot_step: Quantity
    fill_basis: str = FILL_BASIS_WORST_CASE
    stale_price_span: object = None
    paths: dict[str, SlicePath] = field(default_factory=_empty_paths)
    remaining_paths: dict[str, SlicePath] = field(default_factory=_empty_paths)

    def update_stream(
        self,
        stream_id: str,
        observation: SliceObservation | None,
        frontier: Instant,
    ) -> Result[None]:
        del stream_id, observation, frontier
        return Ok(None)

    def scheduled_position_event(self, stream_id: str, frontier: Instant) -> Result[None]:
        del stream_id, frontier
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
        """Sub-phase 3: fill then slippage. ``True`` when the resting intent fills."""
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
        slipped = self.slippage.apply(decided.value, path)
        if is_refusal(slipped):
            return slipped
        if isinstance(slipped.value, NoFill):
            return Ok(False)
        filled = slipped.value
        if filled.taint != TAINT_OPTIMISTIC:
            return invalid(
                "taint",
                "until GAP-0048 every fill carries the optimistic taint (B-6, SC-06)",
                given=filled.taint,
                gap="GAP-0048",
            )
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
