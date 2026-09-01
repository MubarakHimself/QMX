"""Two exact residuals and the side-by-side equity narrative (TN-10; DEC-0195).

Quantity and cash residuals are compared separately at ``reconciliation_epsilon
= 0``. Floating P&L is named in the equity narrative and never enters either
residual. Venue equity and virtual-ledger equity are shown side by side and
never differenced. Foreign float cannot enter the arithmetic (DEC-0225).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Instant, Money, Ok, Quantity, Result, is_refusal

from qmn.reconcile._refuse import clean_token, invalid, policy

__all__ = [
    "RECONCILIATION_EPSILON",
    "CashComponentKind",
    "CashResidual",
    "EquityNarrative",
    "ExplainedCashComponent",
    "QuantityResidual",
    "build_equity_narrative",
    "compute_cash_residual",
    "compute_quantity_residual",
    "refuse_equity_difference",
    "refuse_float_on_reconcile_path",
]

# Statement about the exact scaled-integer domain — absorbs no representation error.
RECONCILIATION_EPSILON: Final[int] = 0


class CashComponentKind(StrEnum):
    """Named explained cash components that may enter the cash residual (TN-10).

    ``FLOATING_PNL`` is listed so callers can name it in the equity narrative; it
    is refused when offered as a residual component.
    """

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"
    FINANCING = "financing"
    COMMISSION = "commission"
    BOUNDARY_ACT = "boundary-act"
    FLOATING_PNL = "floating-pnl"


_RESIDUAL_CASH_KINDS: Final[frozenset[CashComponentKind]] = frozenset(
    {
        CashComponentKind.DEPOSIT,
        CashComponentKind.WITHDRAWAL,
        CashComponentKind.FEE,
        CashComponentKind.FINANCING,
        CashComponentKind.COMMISSION,
        CashComponentKind.BOUNDARY_ACT,
    }
)


@dataclass(frozen=True, slots=True)
class ExplainedCashComponent:
    """One named, evidenced cash component of the residual decomposition."""

    kind: CashComponentKind
    amount: Money
    evidence_ref: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "amount": self.amount.fp1_identity(),
                "evidence_ref": self.evidence_ref,
                "kind": self.kind.value,
            }
        )


@dataclass(frozen=True, slots=True)
class QuantityResidual:
    """Exact instrument-quantity residual (venue − virtual) at epsilon 0."""

    instrument: str
    virtual_quantity: Quantity
    venue_quantity: Quantity
    residual: Quantity

    @property
    def is_zero(self) -> bool:
        return self.residual.as_fraction() == 0

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "instrument": self.instrument,
                "is_zero": self.is_zero,
                "residual": self.residual.fp1_identity(),
                "venue_quantity": self.venue_quantity.fp1_identity(),
                "virtual_quantity": self.virtual_quantity.fp1_identity(),
            }
        )


@dataclass(frozen=True, slots=True)
class CashResidual:
    """Exact cash residual after named explained components (TN-10).

    ``floating_pnl`` is carried for the equity narrative only and never enters
    ``residual``. ``reconciliation_epsilon`` is always 0.
    """

    venue_realized_balance: Money
    virtual_realized_cash: Money
    explained_components: tuple[ExplainedCashComponent, ...]
    residual: Money
    floating_pnl: Money | None
    reconciliation_epsilon: int = RECONCILIATION_EPSILON

    @property
    def is_zero(self) -> bool:
        return self.residual.as_fraction() == 0

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "explained_components": tuple(c.as_mapping() for c in self.explained_components),
            "is_zero": self.is_zero,
            "reconciliation_epsilon": self.reconciliation_epsilon,
            "residual": self.residual.fp1_identity(),
            "venue_realized_balance": self.venue_realized_balance.fp1_identity(),
            "virtual_realized_cash": self.virtual_realized_cash.fp1_identity(),
        }
        if self.floating_pnl is not None:
            body["floating_pnl_narrative"] = self.floating_pnl.fp1_identity()
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class EquityNarrative:
    """Venue and virtual-ledger equity side by side — never differenced."""

    venue_equity: Money
    venue_mark_instant: Instant
    virtual_ledger_equity: Money
    virtual_mark_instant: Instant
    floating_pnl: Money | None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "differenced": False,
            "venue_equity": self.venue_equity.fp1_identity(),
            "venue_mark_instant": self.venue_mark_instant.fp1_identity(),
            "virtual_ledger_equity": self.virtual_ledger_equity.fp1_identity(),
            "virtual_mark_instant": self.virtual_mark_instant.fp1_identity(),
        }
        if self.floating_pnl is not None:
            body["floating_pnl"] = self.floating_pnl.fp1_identity()
        return MappingProxyType(body)


def refuse_float_on_reconcile_path(value: object) -> Result[None]:
    """Foreign float cannot enter reconcile arithmetic (DEC-0141, DEC-0225)."""
    if isinstance(value, float):
        return policy(
            "money",
            "foreign float cannot enter reconciliation arithmetic; decode at the "
            "venue-adapter boundary into exact scaled integers first",
            given=repr(value),
        )
    return Ok(None)


def compute_quantity_residual(
    *,
    instrument: object,
    virtual_quantity: object,
    venue_quantity: object,
) -> Result[QuantityResidual]:
    """Compute venue − virtual quantity residual in exact Quantity units."""
    inst = clean_token(instrument)
    if inst is None:
        return invalid(
            "instrument",
            "quantity residual names an instrument",
            given=repr(instrument),
        )
    if not isinstance(virtual_quantity, Quantity):
        float_check = refuse_float_on_reconcile_path(virtual_quantity)
        if is_refusal(float_check):
            return float_check
        return invalid(
            "virtual_quantity",
            "virtual quantity is an exact Quantity",
            given=repr(virtual_quantity),
        )
    if not isinstance(venue_quantity, Quantity):
        float_check = refuse_float_on_reconcile_path(venue_quantity)
        if is_refusal(float_check):
            return float_check
        return invalid(
            "venue_quantity",
            "venue quantity is an exact Quantity",
            given=repr(venue_quantity),
        )
    residual_r = venue_quantity.subtract(virtual_quantity)
    if is_refusal(residual_r):
        return residual_r
    return Ok(
        QuantityResidual(
            instrument=inst,
            virtual_quantity=virtual_quantity,
            venue_quantity=venue_quantity,
            residual=residual_r.value,
        )
    )


def compute_cash_residual(
    *,
    venue_realized_balance: object,
    virtual_realized_cash: object,
    explained_components: object = (),
    floating_pnl: object | None = None,
) -> Result[CashResidual]:
    """Decompose cash residual: venue − (virtual + named explained components).

    Floating P&L is accepted only as narrative input and never enters the sum.
    ``reconciliation_epsilon`` is fixed at 0.
    """
    for label, value in (
        ("venue_realized_balance", venue_realized_balance),
        ("virtual_realized_cash", virtual_realized_cash),
        ("floating_pnl", floating_pnl),
    ):
        if value is None and label == "floating_pnl":
            continue
        float_check = refuse_float_on_reconcile_path(value)
        if is_refusal(float_check):
            return float_check
        if label != "floating_pnl" and not isinstance(value, Money):
            return invalid(label, "cash residual inputs are exact Money", given=repr(value))

    venue_bal = cast("Money", venue_realized_balance)
    virtual_cash = cast("Money", virtual_realized_cash)

    if not isinstance(explained_components, Sequence) or isinstance(
        explained_components, (str, bytes)
    ):
        return invalid(
            "explained_components",
            "explained cash components are a sequence of ExplainedCashComponent",
            given=repr(type(explained_components).__name__),
        )

    resolved: list[ExplainedCashComponent] = []
    explained_sum = Money.try_create(0, venue_bal.currency, venue_bal.scale)
    if is_refusal(explained_sum):
        return explained_sum
    running = explained_sum.value

    for item in cast("Sequence[object]", explained_components):
        if not isinstance(item, ExplainedCashComponent):
            return invalid(
                "explained_components",
                "each item is an ExplainedCashComponent",
                given=repr(item),
            )
        if item.kind is CashComponentKind.FLOATING_PNL:
            return policy(
                "explained_components",
                "floating P&L is an equity-narrative component and never enters "
                "either residual",
                kind=item.kind.value,
            )
        if item.kind not in _RESIDUAL_CASH_KINDS:
            return invalid(
                "explained_components",
                "cash residual components are deposit|withdrawal|fee|financing|"
                "commission|boundary-act",
                kind=item.kind.value,
            )
        float_check = refuse_float_on_reconcile_path(item.amount)
        if is_refusal(float_check):
            return float_check
        evidence = clean_token(item.evidence_ref)
        if evidence is None:
            return invalid(
                "evidence_ref",
                "each explained cash component carries evidence",
                kind=item.kind.value,
            )
        added = running.add(item.amount)
        if is_refusal(added):
            return added
        running = added.value
        resolved.append(item)

    expected = virtual_cash.add(running)
    if is_refusal(expected):
        return expected
    residual_r = venue_bal.subtract(expected.value)
    if is_refusal(residual_r):
        return residual_r

    narrative_pnl: Money | None = None
    if floating_pnl is not None:
        if not isinstance(floating_pnl, Money):
            return invalid(
                "floating_pnl",
                "floating P&L narrative is exact Money when present",
                given=repr(floating_pnl),
            )
        narrative_pnl = floating_pnl

    return Ok(
        CashResidual(
            venue_realized_balance=venue_bal,
            virtual_realized_cash=virtual_cash,
            explained_components=tuple(resolved),
            residual=residual_r.value,
            floating_pnl=narrative_pnl,
            reconciliation_epsilon=RECONCILIATION_EPSILON,
        )
    )


def build_equity_narrative(
    *,
    venue_equity: object,
    venue_mark_instant: object,
    virtual_ledger_equity: object,
    virtual_mark_instant: object,
    floating_pnl: object | None = None,
) -> Result[EquityNarrative]:
    """Show venue and virtual equities side by side; never difference them."""
    for label, value in (
        ("venue_equity", venue_equity),
        ("virtual_ledger_equity", virtual_ledger_equity),
        ("floating_pnl", floating_pnl),
    ):
        if value is None and label == "floating_pnl":
            continue
        float_check = refuse_float_on_reconcile_path(value)
        if is_refusal(float_check):
            return float_check
        if label != "floating_pnl" and not isinstance(value, Money):
            return invalid(label, "equity narrative carries exact Money", given=repr(value))
    if not isinstance(venue_mark_instant, Instant):
        return invalid(
            "venue_mark_instant",
            "venue equity carries its mark Instant",
            given=repr(venue_mark_instant),
        )
    if not isinstance(virtual_mark_instant, Instant):
        return invalid(
            "virtual_mark_instant",
            "virtual-ledger equity carries its mark Instant",
            given=repr(virtual_mark_instant),
        )
    narrative_pnl: Money | None = None
    if floating_pnl is not None:
        if not isinstance(floating_pnl, Money):
            return invalid(
                "floating_pnl",
                "floating P&L narrative is exact Money when present",
                given=repr(floating_pnl),
            )
        narrative_pnl = floating_pnl
    return Ok(
        EquityNarrative(
            venue_equity=cast("Money", venue_equity),
            venue_mark_instant=venue_mark_instant,
            virtual_ledger_equity=cast("Money", virtual_ledger_equity),
            virtual_mark_instant=virtual_mark_instant,
            floating_pnl=narrative_pnl,
        )
    )


def refuse_equity_difference(
    venue_equity: object,
    virtual_ledger_equity: object,
) -> Result[None]:
    """Differencing the two equity series is a policy rejection (DEC-0195)."""
    return policy(
        "equity_difference",
        "venue equity and virtual-ledger equity are shown side by side and never "
        "differenced; differencing two marks under epsilon 0 would set "
        "operator_review permanently on any open position",
        venue=repr(venue_equity),
        virtual=repr(virtual_ledger_equity),
    )
