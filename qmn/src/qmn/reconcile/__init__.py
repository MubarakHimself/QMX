"""Four-verdict reconciliation with two exact residuals (TN-10; Story 26.6).

Startup and cadence reconciliation compares recorded fills/commands/virtual
positions with venue position and balance read-backs. The result is exactly
``reconciled | drift | unknown | out-of-lookback``. Quantity and cash residuals
are reported separately in exact scaled integers; venue and virtual-ledger
equities are shown side by side and never differenced. Floating P&L is narrative
only. ``reconciliation_epsilon = 0``. Drift on ``role = live`` is an entries-only
stand-down cleared only by operator ``resume``; on ``role = demo`` the same
severity alarm continues the soak. Role — not world — selects the behavior.
Position/balance read-backs map onto CT-13's closed seven (FTR-01; DEC-0247) —
no eighth journal type (FR-060; DEC-0258; DEC-0195; TN-10/25).
"""

from __future__ import annotations

from typing import Final

from qmn.reconcile.engine import (
    FOUR_VERDICTS,
    LookbackStatus,
    ReadbackStatus,
    ReconciliationReport,
    ReconciliationTrigger,
    run_reconciliation,
)
from qmn.reconcile.journal import (
    CT13_SEVEN_EVENT_TYPES,
    READBACK_CT13_EVENT_TYPE,
    READBACK_OBSERVATION_KINDS,
    assert_no_eighth_journal_type,
    map_readback_journal_event_type,
)
from qmn.reconcile.residuals import (
    RECONCILIATION_EPSILON,
    CashComponentKind,
    CashResidual,
    EquityNarrative,
    ExplainedCashComponent,
    QuantityResidual,
    build_equity_narrative,
    compute_cash_residual,
    compute_quantity_residual,
    refuse_equity_difference,
    refuse_float_on_reconcile_path,
)
from qmn.reconcile.response import (
    DRIFT_ALARM_CLASS,
    OPERATOR_RESUME_CLEARANCE,
    DriftResponse,
    DriftResponseKind,
    apply_drift_response,
    clear_operator_review,
)
from qmn.venue import ReconciliationVerdict

__all__ = [
    "CT13_SEVEN_EVENT_TYPES",
    "DRIFT_ALARM_CLASS",
    "FOUR_VERDICTS",
    "OPERATOR_RESUME_CLEARANCE",
    "READBACK_CT13_EVENT_TYPE",
    "READBACK_OBSERVATION_KINDS",
    "RECONCILE_SURFACE",
    "RECONCILIATION_EPSILON",
    "CashComponentKind",
    "CashResidual",
    "DriftResponse",
    "DriftResponseKind",
    "EquityNarrative",
    "ExplainedCashComponent",
    "LookbackStatus",
    "QuantityResidual",
    "ReadbackStatus",
    "ReconciliationReport",
    "ReconciliationTrigger",
    "ReconciliationVerdict",
    "apply_drift_response",
    "assert_no_eighth_journal_type",
    "build_equity_narrative",
    "clear_operator_review",
    "compute_cash_residual",
    "compute_quantity_residual",
    "map_readback_journal_event_type",
    "refuse_equity_difference",
    "refuse_float_on_reconcile_path",
    "run_reconciliation",
]

RECONCILE_SURFACE: Final[str] = "qmn.reconcile"
