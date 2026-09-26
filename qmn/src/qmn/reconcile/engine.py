"""Startup and cadence reconciliation — four verdicts, two residuals (Story 26.6).

Compares recorded fills/commands/virtual positions with venue position and
balance read-backs. Result is exactly ``reconciled | drift | unknown |
out-of-lookback``. Quantity and cash residuals are reported separately; equity
series are narrative-only. Drift disposition is applied by binding role
(FR-060; DEC-0258; DEC-0195; TN-10/25).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import AccountRole, Ok, Quantity, Result, is_refusal

from qmn.reconcile._refuse import clean_token, invalid
from qmn.reconcile.residuals import (
    RECONCILIATION_EPSILON,
    CashResidual,
    EquityNarrative,
    QuantityResidual,
    build_equity_narrative,
    compute_cash_residual,
    compute_quantity_residual,
)
from qmn.reconcile.response import DriftResponse, apply_drift_response
from qmn.venue import ReconciliationVerdict

__all__ = [
    "FOUR_VERDICTS",
    "LookbackStatus",
    "ReadbackStatus",
    "ReconciliationReport",
    "ReconciliationTrigger",
    "run_reconciliation",
]

FOUR_VERDICTS: Final[frozenset[str]] = frozenset(member.value for member in ReconciliationVerdict)


class ReconciliationTrigger(StrEnum):
    """When reconciliation runs (TN-10 cadence)."""

    STARTUP = "startup"
    SCHEDULED = "scheduled"
    AFTER_UNKNOWN = "after-unknown"
    RECONNECT = "reconnect"
    ACCOUNTING_ROLLOVER = "accounting-rollover"


class LookbackStatus(StrEnum):
    """Whether the read-back falls inside the declared lookback."""

    INSIDE = "inside"
    OUT_OF_LOOKBACK = "out-of-lookback"


class ReadbackStatus(StrEnum):
    """Read-back quality apart from lookback."""

    PRESENT = "present"
    ABSENT = "absent"
    AMBIGUOUS = "ambiguous"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """One startup or cadence reconciliation result (FR-060; DEC-0258)."""

    verdict: ReconciliationVerdict
    trigger: ReconciliationTrigger
    quantity_residuals: tuple[QuantityResidual, ...]
    cash_residual: CashResidual | None
    equity: EquityNarrative | None
    operator_review: bool
    drift_response: DriftResponse | None
    detail: str
    reconciliation_epsilon: int = RECONCILIATION_EPSILON

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "detail": self.detail,
            "operator_review": self.operator_review,
            "quantity_residuals": tuple(q.as_mapping() for q in self.quantity_residuals),
            "reconciliation_epsilon": self.reconciliation_epsilon,
            "trigger": self.trigger.value,
            "verdict": self.verdict.value,
            "verdict_vocabulary": sorted(FOUR_VERDICTS),
        }
        if self.cash_residual is not None:
            body["cash_residual"] = self.cash_residual.as_mapping()
        if self.equity is not None:
            body["equity"] = self.equity.as_mapping()
        if self.drift_response is not None:
            body["drift_response"] = self.drift_response.as_mapping()
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class _InstrumentQtyPair:
    instrument: str
    virtual: Quantity
    venue: Quantity


def run_reconciliation(
    *,
    trigger: object,
    role: object,
    lookback_status: object = LookbackStatus.INSIDE,
    readback_status: object = ReadbackStatus.PRESENT,
    quantity_pairs: object = (),
    venue_realized_balance: object | None = None,
    virtual_realized_cash: object | None = None,
    explained_cash_components: object = (),
    floating_pnl: object | None = None,
    venue_equity: object | None = None,
    venue_mark_instant: object | None = None,
    virtual_ledger_equity: object | None = None,
    virtual_mark_instant: object | None = None,
    world: object | None = None,
) -> Result[ReconciliationReport]:
    """Fold one reconciliation pass into a four-verdict report.

    Precedence: ``out-of-lookback`` and uncertain read-backs resolve before
    residual arithmetic. A non-zero quantity or cash residual is ``drift`` and
    sets ``operator_review``; floating P&L never participates in that test.
    """
    trig = _coerce_trigger(trigger)
    if trig is None:
        return invalid(
            "trigger",
            "reconciliation trigger is startup|scheduled|after-unknown|reconnect|"
            "accounting-rollover",
            given=repr(trigger),
        )
    lookback = _coerce_lookback(lookback_status)
    if lookback is None:
        return invalid(
            "lookback_status",
            "lookback status is inside|out-of-lookback",
            given=repr(lookback_status),
        )
    readback = _coerce_readback(readback_status)
    if readback is None:
        return invalid(
            "readback_status",
            "read-back status is present|absent|ambiguous|stale",
            given=repr(readback_status),
        )

    if lookback is LookbackStatus.OUT_OF_LOOKBACK:
        return Ok(
            ReconciliationReport(
                verdict=ReconciliationVerdict.OUT_OF_LOOKBACK,
                trigger=trig,
                quantity_residuals=(),
                cash_residual=None,
                equity=None,
                operator_review=False,
                drift_response=None,
                detail="read-back is out of the declared lookback; operator "
                "attestation required — never read as position-closed",
            )
        )

    if readback is not ReadbackStatus.PRESENT:
        return Ok(
            ReconciliationReport(
                verdict=ReconciliationVerdict.UNKNOWN,
                trigger=trig,
                quantity_residuals=(),
                cash_residual=None,
                equity=None,
                operator_review=False,
                drift_response=None,
                detail=f"venue read-back is {readback.value}; residual arithmetic "
                "does not run under uncertainty",
            )
        )

    pairs = _parse_quantity_pairs(quantity_pairs)
    if is_refusal(pairs):
        return pairs
    qty_residuals: list[QuantityResidual] = []
    for pair in pairs.value:
        computed = compute_quantity_residual(
            instrument=pair.instrument,
            virtual_quantity=pair.virtual,
            venue_quantity=pair.venue,
        )
        if is_refusal(computed):
            return computed
        qty_residuals.append(computed.value)

    cash: CashResidual | None = None
    if venue_realized_balance is not None or virtual_realized_cash is not None:
        if venue_realized_balance is None or virtual_realized_cash is None:
            return invalid(
                "cash",
                "cash residual requires both venue_realized_balance and "
                "virtual_realized_cash",
            )
        cash_r = compute_cash_residual(
            venue_realized_balance=venue_realized_balance,
            virtual_realized_cash=virtual_realized_cash,
            explained_components=explained_cash_components,
            floating_pnl=floating_pnl,
        )
        if is_refusal(cash_r):
            return cash_r
        cash = cash_r.value

    equity: EquityNarrative | None = None
    equity_fields = (
        venue_equity,
        venue_mark_instant,
        virtual_ledger_equity,
        virtual_mark_instant,
    )
    if any(f is not None for f in equity_fields):
        if any(f is None for f in equity_fields):
            return invalid(
                "equity",
                "equity narrative requires venue and virtual equities with mark "
                "instants side by side",
            )
        equity_r = build_equity_narrative(
            venue_equity=venue_equity,
            venue_mark_instant=venue_mark_instant,
            virtual_ledger_equity=virtual_ledger_equity,
            virtual_mark_instant=virtual_mark_instant,
            floating_pnl=floating_pnl,
        )
        if is_refusal(equity_r):
            return equity_r
        equity = equity_r.value

    qty_drift = any(not q.is_zero for q in qty_residuals)
    cash_drift = cash is not None and not cash.is_zero
    if qty_drift or cash_drift:
        drift = apply_drift_response(role=role, world=world)
        if is_refusal(drift):
            return drift
        return Ok(
            ReconciliationReport(
                verdict=ReconciliationVerdict.DRIFT,
                trigger=trig,
                quantity_residuals=tuple(qty_residuals),
                cash_residual=cash,
                equity=equity,
                operator_review=True,
                drift_response=drift.value,
                detail="non-zero quantity or cash residual at reconciliation_epsilon=0",
            )
        )

    # Prove role is a valid AccountRole even on the reconciled path (callers
    # pass it for the drift branch); world remains ignored.
    if _coerce_role(role) is None:
        return invalid(
            "role",
            "reconciliation carries the binding AccountRole even when reconciled",
            given=repr(role),
            allowed=[member.value for member in AccountRole],
        )

    return Ok(
        ReconciliationReport(
            verdict=ReconciliationVerdict.RECONCILED,
            trigger=trig,
            quantity_residuals=tuple(qty_residuals),
            cash_residual=cash,
            equity=equity,
            operator_review=False,
            drift_response=None,
            detail="quantity and cash residuals are zero at reconciliation_epsilon=0",
        )
    )


def _coerce_trigger(value: object) -> ReconciliationTrigger | None:
    if isinstance(value, ReconciliationTrigger):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return ReconciliationTrigger(token)
    except ValueError:
        return None


def _coerce_lookback(value: object) -> LookbackStatus | None:
    if isinstance(value, LookbackStatus):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return LookbackStatus(token)
    except ValueError:
        return None


def _coerce_readback(value: object) -> ReadbackStatus | None:
    if isinstance(value, ReadbackStatus):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return ReadbackStatus(token)
    except ValueError:
        return None


def _coerce_role(value: object) -> AccountRole | None:
    if isinstance(value, AccountRole):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return AccountRole(token)
    except ValueError:
        return None


def _parse_quantity_pairs(value: object) -> Result[tuple[_InstrumentQtyPair, ...]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "quantity_pairs",
            "quantity_pairs is a sequence of (instrument, virtual, venue) triples "
            "or QuantityResidual values",
            given=repr(type(value).__name__),
        )
    out: list[_InstrumentQtyPair] = []
    for raw_item in cast("Sequence[object]", value):
        if isinstance(raw_item, QuantityResidual):
            out.append(
                _InstrumentQtyPair(
                    instrument=raw_item.instrument,
                    virtual=raw_item.virtual_quantity,
                    venue=raw_item.venue_quantity,
                )
            )
            continue
        if not isinstance(raw_item, Sequence) or isinstance(raw_item, (str, bytes)):
            return invalid(
                "quantity_pairs",
                "each pair is a 3-tuple (instrument, virtual, venue) or "
                "QuantityResidual",
                given=repr(raw_item) if not isinstance(raw_item, Sequence) else "non-triple",
            )
        triple = tuple(cast("Sequence[object]", raw_item))
        if len(triple) != 3:
            return invalid(
                "quantity_pairs",
                "each tuple is (instrument, virtual_quantity, venue_quantity)",
                given=f"len={len(triple)}",
            )
        inst_token = clean_token(triple[0])
        if inst_token is None:
            return invalid(
                "instrument",
                "quantity pair names an instrument",
                given=repr(triple[0]),
            )
        virtual = triple[1]
        venue = triple[2]
        if not isinstance(virtual, Quantity) or not isinstance(venue, Quantity):
            return invalid(
                "quantity_pairs",
                "virtual and venue quantities are exact Quantity values",
                instrument=inst_token,
            )
        out.append(_InstrumentQtyPair(instrument=inst_token, virtual=virtual, venue=venue))
    return Ok(tuple(out))
