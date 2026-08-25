"""Pinned V1 execution adapters bound by adapter-id (B-6, Story 17.1).

Fill, slippage, and cost are SEPARATE adapters. Calibration *content* (spread
tables, slip parameters, commission rates, swap points) stays deferred to
GAP-0048 — these adapters invent no numbers. The ``zero`` slippage and cost
shapes are the named catalog entries from SLIP-2 / FEE-2, never a silent default.
The financing scheduler is bound from a schedule reference and refuses to apply
a swap until that artifact's content exists (FEE-4).
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core.exact import Money
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import unavailable
from qmb.execution.fidelity import FidelityIdentity, stamp_fidelity
from qmb.execution.ports import (
    COMPOSITION_VERSION,
    TAINT_OPTIMISTIC,
    AuthorizedIntent,
    CostedFill,
    CostPort,
    Fill,
    FillPort,
    NoFill,
    PartialFill,
    SlicePath,
    SlippagePort,
    require_authorized_intent,
)

__all__ = [
    "AMBIENT_DISCOVERY",
    "COST_ADAPTER_CATALOG",
    "COST_ADAPTER_ZERO",
    "FILL_ADAPTER_CATALOG",
    "FILL_ADAPTER_DECLARED_PATH",
    "FINANCING_ADAPTER_SCHEDULED",
    "SLIPPAGE_ADAPTER_CATALOG",
    "SLIPPAGE_ADAPTER_ZERO",
    "DeclaredPathFillAdapter",
    "FinancingScheduler",
    "ZeroCostAdapter",
    "ZeroSlippageAdapter",
]

AMBIENT_DISCOVERY: Final[bool] = False
FILL_ADAPTER_DECLARED_PATH: Final[str] = "declared-path"
SLIPPAGE_ADAPTER_ZERO: Final[str] = "zero"
COST_ADAPTER_ZERO: Final[str] = "zero"
FINANCING_ADAPTER_SCHEDULED: Final[str] = "scheduled"


@dataclass(frozen=True, slots=True)
class DeclaredPathFillAdapter:
    """Fill adapter: requested quantity at the first declared-path print.

    Honest declared-path crossing (order types, worst-case OHLC, gaps) is
    Story 17.3. This adapter is the bindable V1 identity for that seam.
    """

    adapter_id: str = FILL_ADAPTER_DECLARED_PATH
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + optimistic taint."""
        return stamp_fidelity(self.adapter_id, composition_version=self.composition_version)

    def decide(
        self,
        intent: AuthorizedIntent,
        path: SlicePath,
        *,
        requested_quantity: object,
    ) -> Result[Fill | NoFill | PartialFill]:
        """Fill the authorized intent; never a bot-sized order."""
        authorized = require_authorized_intent(intent)
        if is_refusal(authorized):
            return authorized
        if not path.prints:
            none = NoFill.try_create("empty-path")
            if is_refusal(none):
                return none
            return Ok(none.value)
        filled = Fill.try_create(requested_quantity, requested_quantity, path.prints[0])
        if is_refusal(filled):
            return filled
        return Ok(filled.value)


@dataclass(frozen=True, slots=True)
class ZeroSlippageAdapter:
    """Named ``zero`` slippage shape (SLIP-2). Post-slip equals pre-slip."""

    adapter_id: str = SLIPPAGE_ADAPTER_ZERO
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + optimistic taint."""
        return stamp_fidelity(
            f"slippage.{self.adapter_id}",
            composition_version=self.composition_version,
        )

    def apply(
        self,
        fill: Fill | PartialFill,
        path: SlicePath,
    ) -> Result[Fill | NoFill | PartialFill]:
        """Map pre-slip to post-slip with no invented offset; never resize."""
        del path
        if isinstance(fill, Fill):
            slipped = Fill.try_create(
                fill.quantity,
                fill.requested_quantity,
                fill.pre_slip_price,
                post_slip_price=fill.pre_slip_price,
            )
            if is_refusal(slipped):
                return slipped
            return Ok(slipped.value)
        slipped_partial = PartialFill.try_create(
            fill.quantity,
            fill.requested_quantity,
            fill.pre_slip_price,
            remaining_quantity=fill.remaining_quantity,
            post_slip_price=fill.pre_slip_price,
        )
        if is_refusal(slipped_partial):
            return slipped_partial
        return Ok(slipped_partial.value)


@dataclass(frozen=True, slots=True)
class ZeroCostAdapter:
    """Named ``zero`` commission shape (FEE-2). No invented rate; no silent default."""

    adapter_id: str = COST_ADAPTER_ZERO
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + optimistic taint."""
        return stamp_fidelity(
            f"cost.{self.adapter_id}",
            composition_version=self.composition_version,
        )

    def itemize(self, fill: Fill | PartialFill) -> Result[CostedFill]:
        """Itemize no commission lines — the named zero shape, not an absent model."""
        return CostedFill.try_create(fill, ())


@dataclass(frozen=True, slots=True)
class FinancingScheduler:
    """Scheduled position-level cash event, never an order fill (B-6, FEE-4).

    Bound from a financing-schedule reference. Calibration content (swap points,
    triple-swap weekday, sign convention) is deferred to GAP-0048; applying a
    swap without that artifact is a typed refusal, never a silent zero.
    """

    schedule_ref: str
    adapter_id: str = FINANCING_ADAPTER_SCHEDULED
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + schedule ref + optimistic taint."""
        return stamp_fidelity(
            f"financing.{self.adapter_id}",
            composition_version=self.composition_version,
            calibration_ref=self.schedule_ref,
        )

    def schedule(self, *, stream_id: str, direction: object) -> Result[Money]:
        """Refuse to invent swap content; never return a silent zero debit."""
        del stream_id, direction
        return unavailable(
            "financing_schedule",
            "swap/financing calibration content is deferred to GAP-0048; absence "
            "never silently zeros (B-6, FEE-4, SC-07)",
            schedule_ref=self.schedule_ref,
            gap="GAP-0048",
            financing_is_order_fill=False,
        )


FILL_ADAPTER_CATALOG: Final[MappingProxyType[str, type[FillPort]]] = MappingProxyType(
    {FILL_ADAPTER_DECLARED_PATH: DeclaredPathFillAdapter}
)
SLIPPAGE_ADAPTER_CATALOG: Final[MappingProxyType[str, type[SlippagePort]]] = MappingProxyType(
    {SLIPPAGE_ADAPTER_ZERO: ZeroSlippageAdapter}
)
COST_ADAPTER_CATALOG: Final[MappingProxyType[str, type[CostPort]]] = MappingProxyType(
    {COST_ADAPTER_ZERO: ZeroCostAdapter}
)
