"""Story 26.6 — four reconciliation verdicts and two exact residuals."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    AccountRole,
    Instant,
    Money,
    Quantity,
    RefusalCategory,
    World,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import Result
from qmn.reconcile import (
    CT13_SEVEN_EVENT_TYPES,
    DRIFT_ALARM_CLASS,
    FOUR_VERDICTS,
    OPERATOR_RESUME_CLEARANCE,
    READBACK_CT13_EVENT_TYPE,
    RECONCILE_SURFACE,
    RECONCILIATION_EPSILON,
    CashComponentKind,
    DriftResponseKind,
    ExplainedCashComponent,
    LookbackStatus,
    ReadbackStatus,
    ReconciliationTrigger,
    ReconciliationVerdict,
    apply_drift_response,
    assert_no_eighth_journal_type,
    build_equity_narrative,
    clear_operator_review,
    compute_cash_residual,
    compute_quantity_residual,
    map_readback_journal_event_type,
    refuse_equity_difference,
    refuse_float_on_reconcile_path,
    run_reconciliation,
)

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _money(value: int, *, scale: int = 2, currency: str = "USD") -> Money:
    return _ok(Money.try_create(value, currency, scale))


def _qty(value: int, *, scale: int = 2, unit: str = "lot") -> Quantity:
    return _ok(Quantity.try_create(value, unit, scale))


# --- surface -----------------------------------------------------------------


def test_reconcile_surface_and_closed_vocabulary() -> None:
    assert RECONCILE_SURFACE == "qmn.reconcile"
    assert RECONCILIATION_EPSILON == 0
    assert frozenset({"reconciled", "drift", "unknown", "out-of-lookback"}) == FOUR_VERDICTS
    assert {m.value for m in ReconciliationVerdict} == FOUR_VERDICTS
    assert DRIFT_ALARM_CLASS == "silent-degradation"
    assert READBACK_CT13_EVENT_TYPE in CT13_SEVEN_EVENT_TYPES
    assert len(CT13_SEVEN_EVENT_TYPES) == 7


# --- AC1: four verdicts + two residuals + side-by-side equity ---------------


def test_reconciled_when_both_residuals_zero() -> None:
    report = _ok(
        run_reconciliation(
            trigger=ReconciliationTrigger.STARTUP,
            role=AccountRole.LIVE,
            quantity_pairs=(("EURUSD", _qty(100), _qty(100)),),
            venue_realized_balance=_money(50_000_00),
            virtual_realized_cash=_money(50_000_00),
            venue_equity=_money(51_000_00),
            venue_mark_instant=_instant(1),
            virtual_ledger_equity=_money(50_900_00),
            virtual_mark_instant=_instant(2),
            floating_pnl=_money(900_00),
        )
    )
    assert report.verdict is ReconciliationVerdict.RECONCILED
    assert report.operator_review is False
    assert report.reconciliation_epsilon == 0
    assert report.quantity_residuals[0].is_zero
    assert report.cash_residual is not None and report.cash_residual.is_zero
    assert report.equity is not None
    assert report.equity.as_mapping()["differenced"] is False
    # Equities differ but are never differenced into a residual.
    assert report.equity.venue_equity != report.equity.virtual_ledger_equity


def test_drift_on_quantity_residual_reports_exact_integers() -> None:
    report = _ok(
        run_reconciliation(
            trigger="scheduled",
            role=AccountRole.LIVE,
            quantity_pairs=(("EURUSD", _qty(100), _qty(150)),),
            venue_realized_balance=_money(10_000_00),
            virtual_realized_cash=_money(10_000_00),
        )
    )
    assert report.verdict is ReconciliationVerdict.DRIFT
    assert report.operator_review is True
    residual = report.quantity_residuals[0]
    assert residual.residual == _qty(50)
    assert residual.virtual_quantity.value == 100
    assert residual.venue_quantity.value == 150
    assert report.cash_residual is not None and report.cash_residual.is_zero


def test_drift_on_cash_residual_separate_from_quantity() -> None:
    report = _ok(
        run_reconciliation(
            trigger=ReconciliationTrigger.RECONNECT,
            role=AccountRole.DEMO,
            quantity_pairs=(("GBPUSD", _qty(0), _qty(0)),),
            venue_realized_balance=_money(10_050_00),
            virtual_realized_cash=_money(10_000_00),
        )
    )
    assert report.verdict is ReconciliationVerdict.DRIFT
    assert report.quantity_residuals[0].is_zero
    assert report.cash_residual is not None
    assert report.cash_residual.residual == _money(50_00)


def test_unknown_and_out_of_lookback_skip_residual_arithmetic() -> None:
    unknown = _ok(
        run_reconciliation(
            trigger=ReconciliationTrigger.AFTER_UNKNOWN,
            role=AccountRole.LIVE,
            readback_status=ReadbackStatus.ABSENT,
            quantity_pairs=(("EURUSD", _qty(1), _qty(9)),),
        )
    )
    assert unknown.verdict is ReconciliationVerdict.UNKNOWN
    assert unknown.quantity_residuals == ()
    assert unknown.cash_residual is None

    stale = _ok(
        run_reconciliation(
            trigger="startup",
            role="live",
            readback_status="ambiguous",
        )
    )
    assert stale.verdict is ReconciliationVerdict.UNKNOWN

    ool = _ok(
        run_reconciliation(
            trigger=ReconciliationTrigger.STARTUP,
            role=AccountRole.LIVE,
            lookback_status=LookbackStatus.OUT_OF_LOOKBACK,
            quantity_pairs=(("EURUSD", _qty(1), _qty(9)),),
        )
    )
    assert ool.verdict is ReconciliationVerdict.OUT_OF_LOOKBACK
    assert "never read as position-closed" in ool.detail
    assert ool.quantity_residuals == ()


def test_equity_side_by_side_never_differenced() -> None:
    narrative = _ok(
        build_equity_narrative(
            venue_equity=_money(100_00),
            venue_mark_instant=_instant(10),
            virtual_ledger_equity=_money(99_00),
            virtual_mark_instant=_instant(11),
            floating_pnl=_money(5_00),
        )
    )
    assert narrative.as_mapping()["differenced"] is False
    refused = _refusal(refuse_equity_difference(_money(100_00), _money(99_00)))
    assert refused.category is RefusalCategory.POLICY_REJECTION


# --- AC2: cash decomposition, floating PnL, epsilon 0, no foreign float -----


def test_explained_cash_components_named_and_evidenced() -> None:
    components = (
        ExplainedCashComponent(
            kind=CashComponentKind.FEE,
            amount=_money(-25_00),
            evidence_ref="fee-obs-1",
        ),
        ExplainedCashComponent(
            kind=CashComponentKind.COMMISSION,
            amount=_money(-10_00),
            evidence_ref="comm-obs-1",
        ),
        ExplainedCashComponent(
            kind=CashComponentKind.BOUNDARY_ACT,
            amount=_money(100_00),
            evidence_ref="sweep-boundary-1",
        ),
        ExplainedCashComponent(
            kind=CashComponentKind.DEPOSIT,
            amount=_money(500_00),
            evidence_ref="deposit-1",
        ),
        ExplainedCashComponent(
            kind=CashComponentKind.WITHDRAWAL,
            amount=_money(-200_00),
            evidence_ref="wd-1",
        ),
        ExplainedCashComponent(
            kind=CashComponentKind.FINANCING,
            amount=_money(-5_00),
            evidence_ref="fin-1",
        ),
    )
    # venue 10_360 = virtual 10_000 + explained (+500 -200 -25 -10 +100 -5) = +360
    cash = _ok(
        compute_cash_residual(
            venue_realized_balance=_money(10_360_00),
            virtual_realized_cash=_money(10_000_00),
            explained_components=components,
            floating_pnl=_money(777_00),
        )
    )
    assert cash.is_zero
    assert cash.reconciliation_epsilon == 0
    assert cash.floating_pnl == _money(777_00)
    assert "floating_pnl_narrative" in cash.as_mapping()
    assert len(cash.explained_components) == 6
    kinds = {c.kind for c in cash.explained_components}
    assert CashComponentKind.FLOATING_PNL not in kinds


def test_floating_pnl_refused_as_residual_component() -> None:
    refused = _refusal(
        compute_cash_residual(
            venue_realized_balance=_money(100_00),
            virtual_realized_cash=_money(100_00),
            explained_components=(
                ExplainedCashComponent(
                    kind=CashComponentKind.FLOATING_PNL,
                    amount=_money(10_00),
                    evidence_ref="mark-1",
                ),
            ),
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert "never enters" in str(refused.context["reason"])


def test_foreign_float_refused_on_reconcile_path() -> None:
    float_refused = _refusal(refuse_float_on_reconcile_path(1.25))
    assert float_refused.category is RefusalCategory.POLICY_REJECTION
    qty_refused = _refusal(
        compute_quantity_residual(
            instrument="EURUSD",
            virtual_quantity=1.5,
            venue_quantity=_qty(1),
        )
    )
    assert qty_refused.category is RefusalCategory.POLICY_REJECTION
    cash_refused = _refusal(
        compute_cash_residual(
            venue_realized_balance=99.99,
            virtual_realized_cash=_money(100_00),
        )
    )
    assert cash_refused.category is RefusalCategory.POLICY_REJECTION


def test_reconciliation_epsilon_is_zero_and_absorbs_nothing() -> None:
    cash = _ok(
        compute_cash_residual(
            venue_realized_balance=_money(100_01),
            virtual_realized_cash=_money(100_00),
        )
    )
    assert cash.reconciliation_epsilon == 0
    assert cash.is_zero is False
    assert cash.residual == _money(1)


# --- AC3: drift response keyed by role, never world -------------------------


def test_live_drift_entries_only_stand_down_cleared_by_resume() -> None:
    report = _ok(
        run_reconciliation(
            trigger=ReconciliationTrigger.SCHEDULED,
            role=AccountRole.LIVE,
            world=World.LIVE,
            quantity_pairs=(("EURUSD", _qty(1), _qty(2)),),
            venue_realized_balance=_money(1_00),
            virtual_realized_cash=_money(1_00),
        )
    )
    assert report.verdict is ReconciliationVerdict.DRIFT
    assert report.drift_response is not None
    resp = report.drift_response
    assert resp.kind is DriftResponseKind.ENTRIES_ONLY_STAND_DOWN
    assert resp.entries_blocked is True
    assert resp.exits_and_protection_pass is True
    assert resp.continues_soak is False
    assert resp.clears_only_by == OPERATOR_RESUME_CLEARANCE
    assert resp.alarm_class == DRIFT_ALARM_CLASS
    assert resp.world_ignored is True

    blocked = _refusal(
        clear_operator_review(response=resp, clearance="restart", fresh_review=True)
    )
    assert blocked.category is RefusalCategory.POLICY_REJECTION

    cleared = _ok(
        clear_operator_review(
            response=resp,
            clearance=OPERATOR_RESUME_CLEARANCE,
            fresh_review=True,
        )
    )
    assert cleared.operator_review is False
    assert cleared.entries_blocked is False


def test_demo_drift_alarms_same_severity_and_continues_soak() -> None:
    # Same world=live as a paper/soak binding — role selects behavior.
    report = _ok(
        run_reconciliation(
            trigger=ReconciliationTrigger.STARTUP,
            role=AccountRole.DEMO,
            world=World.LIVE,
            quantity_pairs=(("EURUSD", _qty(1), _qty(3)),),
        )
    )
    assert report.verdict is ReconciliationVerdict.DRIFT
    assert report.drift_response is not None
    resp = report.drift_response
    assert resp.kind is DriftResponseKind.ALARM_AND_CONTINUE
    assert resp.alarm_class == DRIFT_ALARM_CLASS
    assert resp.continues_soak is True
    assert resp.entries_blocked is False
    assert resp.clears_only_by is None
    assert resp.world_ignored is True

    # Direct apply proves world never flips live vs demo.
    live = _ok(apply_drift_response(role="live", world="replay"))
    demo = _ok(apply_drift_response(role="demo", world="live"))
    assert live.kind is DriftResponseKind.ENTRIES_ONLY_STAND_DOWN
    assert demo.kind is DriftResponseKind.ALARM_AND_CONTINUE
    assert live.alarm_class == demo.alarm_class == DRIFT_ALARM_CLASS


# --- FTR-01: no eighth journal type -----------------------------------------


def test_ftr01_readbacks_map_onto_existing_seven() -> None:
    for kind in (
        "position-readback",
        "position-read-back",
        "balance-readback",
        "balance-read-back",
    ):
        mapped = _ok(map_readback_journal_event_type(kind))
        assert mapped == READBACK_CT13_EVENT_TYPE
        assert mapped in CT13_SEVEN_EVENT_TYPES

    eighth = _refusal(assert_no_eighth_journal_type("observation"))
    assert eighth.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert eighth.context["ftr"] == "FTR-01"
    assert "eighth" in str(eighth.context["reason"])

    invented = _refusal(assert_no_eighth_journal_type("reconciliation"))
    assert invented.context["ftr"] == "FTR-01"
    assert "observation" not in CT13_SEVEN_EVENT_TYPES
    assert "reconciliation" not in CT13_SEVEN_EVENT_TYPES
