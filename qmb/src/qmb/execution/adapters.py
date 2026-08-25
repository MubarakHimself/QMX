"""Pinned V1 execution adapters bound by adapter-id (B-6, Story 17.1).

Fill, slippage, and cost are SEPARATE adapters. Calibration *content* (spread
tables, slip parameters, commission rates, swap points) stays deferred to
GAP-0048 — these adapters invent no numbers. The ``zero`` slippage and cost
shapes are the named catalog entries from SLIP-2 / FEE-2, never a silent default.
The financing scheduler is bound from a schedule reference plus an optional
swap-table calibration (FEE-4).
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core.chrono import Duration
from qmf.core.refusal import Ok, Result, is_refusal

from qmb.execution.cost import (
    COST_ADAPTER_CATALOG,
    COST_ADAPTER_NOTIONAL_MINIMUM,
    COST_ADAPTER_PER_LOT,
    COST_ADAPTER_PERCENT_OF_NOTIONAL,
    COST_ADAPTER_ZERO,
    COST_CALIBRATION_KEY,
    COST_MODELS,
    CommissionCalibration,
    NotionalProportionalMinimumCostAdapter,
    PercentOfNotionalCostAdapter,
    PerLotCostAdapter,
    ZeroCostAdapter,
)
from qmb.execution.fidelity import FidelityIdentity, stamp_fidelity
from qmb.execution.fill import (
    FILL_BASES,
    FILL_BASIS_WORST_CASE,
    cross_declared_path,
)
from qmb.execution.financing import (
    FINANCING_ADAPTER_SCHEDULED,
    FINANCING_CALIBRATION_KEY,
    FinancingScheduler,
)
from qmb.execution.ports import (
    COMPOSITION_VERSION,
    TAINT_OPTIMISTIC,
    AuthorizedIntent,
    Fill,
    FillPort,
    NoFill,
    PartialFill,
    SlicePath,
    SlippagePort,
    require_authorized_intent,
)
from qmb.execution.slippage import (
    SLIPPAGE_ADAPTER_CONSTANT_PERCENT,
    SLIPPAGE_ADAPTER_GAP_VOLATILITY,
    SLIPPAGE_ADAPTER_SIZE_TIERED,
    SLIPPAGE_ADAPTER_SPREAD_CROSSING,
    SLIPPAGE_ADAPTER_ZERO,
    ConstantPercentSlippageAdapter,
    GapVolatilitySlippageAdapter,
    SizeTieredSlippageAdapter,
    SpreadCrossingSlippageAdapter,
    ZeroSlippageAdapter,
)

__all__ = [
    "AMBIENT_DISCOVERY",
    "COST_ADAPTER_CATALOG",
    "COST_ADAPTER_NOTIONAL_MINIMUM",
    "COST_ADAPTER_PERCENT_OF_NOTIONAL",
    "COST_ADAPTER_PER_LOT",
    "COST_ADAPTER_ZERO",
    "COST_CALIBRATION_KEY",
    "COST_MODELS",
    "FILL_ADAPTER_CATALOG",
    "FILL_ADAPTER_DECLARED_PATH",
    "FINANCING_ADAPTER_SCHEDULED",
    "FINANCING_CALIBRATION_KEY",
    "SLIPPAGE_ADAPTER_CATALOG",
    "SLIPPAGE_ADAPTER_CONSTANT_PERCENT",
    "SLIPPAGE_ADAPTER_GAP_VOLATILITY",
    "SLIPPAGE_ADAPTER_SIZE_TIERED",
    "SLIPPAGE_ADAPTER_SPREAD_CROSSING",
    "SLIPPAGE_ADAPTER_ZERO",
    "CommissionCalibration",
    "ConstantPercentSlippageAdapter",
    "DeclaredPathFillAdapter",
    "FinancingScheduler",
    "GapVolatilitySlippageAdapter",
    "NotionalProportionalMinimumCostAdapter",
    "PerLotCostAdapter",
    "PercentOfNotionalCostAdapter",
    "SizeTieredSlippageAdapter",
    "SpreadCrossingSlippageAdapter",
    "ZeroCostAdapter",
    "ZeroSlippageAdapter",
]

AMBIENT_DISCOVERY: Final[bool] = False
FILL_ADAPTER_DECLARED_PATH: Final[str] = "declared-path"


@dataclass(frozen=True, slots=True)
class DeclaredPathFillAdapter:
    """Fill adapter: declared-path crossing dispatched per order type (FILL-2).

    Default pricing is bar-worst-case. Optimistic-exact is a labeled fill-basis.
    Both stay ``optimistic``-tainted until GAP-0048.
    """

    adapter_id: str = FILL_ADAPTER_DECLARED_PATH
    composition_version: int = COMPOSITION_VERSION
    taint: str = TAINT_OPTIMISTIC
    fill_basis: str = FILL_BASIS_WORST_CASE
    stale_price_span: Duration | None = None

    def fidelity(self) -> Result[FidelityIdentity]:
        """Stamp adapter-id + composition-version + fill-basis + optimistic taint."""
        return stamp_fidelity(
            self.adapter_id,
            composition_version=self.composition_version,
            fill_basis=self.fill_basis,
        )

    def decide(
        self,
        intent: AuthorizedIntent,
        path: SlicePath,
        *,
        requested_quantity: object,
        order: object = None,
        fill_basis: object = None,
        stale_price_span: object = None,
    ) -> Result[Fill | NoFill | PartialFill]:
        """Fill the authorized intent by crossing the declared path."""
        authorized = require_authorized_intent(intent)
        if is_refusal(authorized):
            return authorized
        if not path.prints and path.open is None:
            none = NoFill.try_create("empty-path")
            if is_refusal(none):
                return none
            return Ok(none.value)
        basis = self.fill_basis if fill_basis is None else fill_basis
        span = self.stale_price_span if stale_price_span is None else stale_price_span
        if basis not in FILL_BASES:
            basis = self.fill_basis
        return cross_declared_path(
            authorized.value,
            path,
            requested_quantity=requested_quantity,
            order=order,
            fill_basis=basis,
            stale_price_span=span,
        )


FILL_ADAPTER_CATALOG: Final[MappingProxyType[str, type[FillPort]]] = MappingProxyType(
    {FILL_ADAPTER_DECLARED_PATH: DeclaredPathFillAdapter}
)
SLIPPAGE_ADAPTER_CATALOG: Final[MappingProxyType[str, type[SlippagePort]]] = MappingProxyType(
    {
        SLIPPAGE_ADAPTER_ZERO: ZeroSlippageAdapter,
        SLIPPAGE_ADAPTER_CONSTANT_PERCENT: ConstantPercentSlippageAdapter,
        SLIPPAGE_ADAPTER_SPREAD_CROSSING: SpreadCrossingSlippageAdapter,
        SLIPPAGE_ADAPTER_GAP_VOLATILITY: GapVolatilitySlippageAdapter,
        SLIPPAGE_ADAPTER_SIZE_TIERED: SizeTieredSlippageAdapter,
    }
)
