"""Story 26.7 — kill line, breakeven ratchet, and qualifying-loss bench."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Money,
    Price,
    PriceDelta,
    RefusalCategory,
    UnitKind,
    VenueId,
    World,
    fingerprint,
)
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.binding import BindingState
from qmf.risk.exit_record import (
    CloseOutcome,
    CloseReason,
    ClosingAuthority,
    CostComponent,
    ExitResultLabel,
    mint_exit_record,
)
from qmf.risk.paper import BookMode, ExecutionTarget, RoutingOutcome, SeatState
from qmn.capital import (
    AMEND_MIN_IMPROVEMENT_REGISTRY_KEY,
    BENCH_CONSECUTIVE_LOSS_THRESHOLD_REGISTRY_KEY,
    BENCH_DISPOSITIONS,
    BENCH_FOLD_FIXTURE,
    BREAKEVEN_RATCHET_OFFSET_REGISTRY_KEY,
    BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY,
    CAPITAL_SURFACE,
    KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY,
    LOSS_FLOOR_REGISTRY_KEY,
    OPERATOR_KILL_LINE_RESUME,
    QUALIFYING_LOSS_THRESHOLD_REGISTRY_KEY,
    V1_DYNAMIC_PROTECTION_GRAMMAR,
    BreakevenRatchetOrigin,
    DynamicProtectionGrammar,
    KillLineCadence,
    apply_bench_crossing,
    apply_kill_line_breach,
    dispatch_originated_breakeven_ratchet,
    evaluate_kill_line,
    evaluate_qualifying_loss_bench,
    marked_virtual_equity,
    originate_breakeven_ratchet,
    refuse_invented_kill_line_floor,
    refuse_non_breakeven_dynamic_grammar,
    refuse_stale_exit_before_intent,
    restore_kill_line_stand_down,
    v1_dynamic_protection_is_breakeven_ratchet_only,
)
from qmn.venue import Command, ProtectionAmendment, ProtectionSide

T = TypeVar("T")

_VENUE = VenueId(value="venue-ctrader")
_SESSION = "session-capital-26-7"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(seed: str) -> Fingerprint:
    return _ok(fingerprint({"seed": seed}))


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _money(value: int, scale: int = 2) -> Money:
    return _ok(Money.try_create(value, "USD", scale))


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE))


def _instrument() -> Instrument:
    return Instrument(venue=_VENUE, symbol="EURUSD")


def _delta(value: int, scale: int = 5) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), scale))


def _price(value: int = 1_10000, scale: int = 5) -> Price:
    return _ok(Price.try_create(value, _instrument(), scale))


def _account(account_id: str = "acct-live") -> Account:
    return _ok(Account.try_create(account_id, _VENUE, AccountRole.LIVE))


def _live_target(account: str = "acct-live") -> ExecutionTarget:
    return _ok(ExecutionTarget.try_create(AccountRole.LIVE, _VENUE, account))


def _demo_target(account: str = "acct-demo") -> ExecutionTarget:
    return _ok(ExecutionTarget.try_create(AccountRole.DEMO, _VENUE, account))


def _label() -> ExitResultLabel:
    return _ok(ExitResultLabel.try_create(AccountRole.LIVE, World.LIVE))


def _cost(name: str, amount: int) -> CostComponent:
    return _ok(CostComponent.try_create(name, _money(amount), "broker"))


def _mint_exit(
    *,
    seed: str,
    epoch: Fingerprint,
    realized_pnl: int,
    outcome: CloseOutcome = CloseOutcome.LOSS,
    close_reason: CloseReason = CloseReason.PROTECTIVE_STOP_FILL,
    authority: ClosingAuthority = ClosingAuthority.VENUE,
    costs: tuple[CostComponent, ...] = (),
    recorded_at: Instant | None = None,
    risk_amount: int = 10_000,
) -> object:
    arb = None
    vobs = _fp(f"venue-obs-{seed}")
    if authority is not ClosingAuthority.VENUE:
        arb = _fp(f"arb-{seed}")
        vobs = None
    return _ok(
        mint_exit_record(
            virtual_position_ref=_fp(seed),
            opening_bot_id="bot-alpha",
            original_risk_distance=_delta(50),
            original_risk_amount=_money(risk_amount),
            fill_references=(_fp(f"fill-{seed}"),),
            realized_pnl=_money(realized_pnl),
            cost_components=costs,
            close_reason=close_reason,
            mechanism=close_reason,
            outcome=outcome,
            closing_authority=authority,
            close_reason_mapping_version=1,
            result_label=_label(),
            loss_predicate_format_version=1,
            binding_epoch=epoch,
            recorded_at=recorded_at or _instant(),
            arbitration_record_ref=arb,
            venue_observation_ref=vobs,
        )
    )


# --- surface ------------------------------------------------------------------


def test_capital_surface_and_registry_keys() -> None:
    assert CAPITAL_SURFACE == "qmn.capital"
    assert BENCH_FOLD_FIXTURE == "qmn/bench-fold"
    assert KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY == "kill_line_capital_floor"
    assert LOSS_FLOOR_REGISTRY_KEY == "loss_floor"
    assert QUALIFYING_LOSS_THRESHOLD_REGISTRY_KEY == "qualifying_loss_threshold"
    assert BENCH_CONSECUTIVE_LOSS_THRESHOLD_REGISTRY_KEY == "bench_consecutive_loss_threshold"
    assert BREAKEVEN_RATCHET_TRIGGER_REGISTRY_KEY == "breakeven_ratchet_trigger"
    assert BREAKEVEN_RATCHET_OFFSET_REGISTRY_KEY == "breakeven_ratchet_offset"
    assert AMEND_MIN_IMPROVEMENT_REGISTRY_KEY == "amend_min_improvement"
    assert V1_DYNAMIC_PROTECTION_GRAMMAR == "single-sided-breakeven-ratchet"
    assert v1_dynamic_protection_is_breakeven_ratchet_only() is True
    assert BENCH_DISPOSITIONS == frozenset(
        {"qualifying_loss_exit", "scratch-or-partial-loss", "breakeven"}
    )


# --- AC1: kill line over marked equity ----------------------------------------


def test_marked_equity_is_realized_plus_unrealized() -> None:
    equity = _ok(
        marked_virtual_equity(
            realized_cash=_money(100_000_00),
            unrealized_marks=(_money(-25_000_00),),
        )
    )
    assert equity.as_fraction() == _money(75_000_00).as_fraction()


def test_ftr07_refuses_invented_kill_line_floor() -> None:
    refused = _refusal(refuse_invented_kill_line_floor())
    assert refused.category is RefusalCategory.POLICY_REJECTION
    blank = _refusal(
        evaluate_kill_line(
            binding_scope_ref="binding-a",
            equity=_money(50_000_00),
            kill_line_capital_floor=None,
            evaluated_at=_instant(),
        )
    )
    assert blank.category is RefusalCategory.POLICY_REJECTION
    assert blank.context["field"] == KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY


def test_kill_line_breach_flattens_one_binding_and_stands_down() -> None:
    floor = _money(80_000_00)  # Book-declared — never a spine constant
    equity = _ok(
        marked_virtual_equity(
            realized_cash=_money(90_000_00),
            unrealized_marks={"EURUSD": _money(-15_000_00)},
        )
    )
    evaluation = _ok(
        evaluate_kill_line(
            binding_scope_ref="binding-a",
            equity=equity,
            kill_line_capital_floor=floor,
            loss_floor=floor,
            evaluated_at=_instant(),
            cadence=KillLineCadence.HELD_INSTRUMENT_PRICE,
        )
    )
    assert evaluation.breached is True
    assert evaluation.floor_registry_key == KILL_LINE_CAPITAL_FLOOR_REGISTRY_KEY

    package = _ok(
        apply_kill_line_breach(
            evaluation,
            venue_id=_VENUE,
            account_id="acct-live",
            live_target=_live_target(),
            paper_target=_demo_target(),
            book_mode=BookMode.LIVE,
        )
    )
    assert package.close_reason is CloseReason.KILL_LINE_FLAT
    assert package.close_reason is not CloseReason.PROTECTION_FORCED_FLAT
    assert package.binding_state is BindingState.STOOD_DOWN
    assert package.book_mode is BookMode.LIVE
    assert package.other_bindings_unaffected is True
    assert package.routing.outcome is RoutingOutcome.ROUTED_PAPER
    assert package.evaluation.binding_scope_ref == "binding-a"


def test_kill_line_other_binding_unaffected_by_construction() -> None:
    floor = _money(50_000_00)
    a = _ok(
        evaluate_kill_line(
            binding_scope_ref="binding-a",
            equity=_money(40_000_00),
            kill_line_capital_floor=floor,
            evaluated_at=_instant(),
            cadence=KillLineCadence.FILL,
        )
    )
    b = _ok(
        evaluate_kill_line(
            binding_scope_ref="binding-b",
            equity=_money(90_000_00),
            kill_line_capital_floor=floor,
            evaluated_at=_instant(),
            cadence=KillLineCadence.FILL,
        )
    )
    assert a.breached is True
    assert b.breached is False
    package = _ok(
        apply_kill_line_breach(
            a,
            venue_id=_VENUE,
            account_id="acct-live",
            live_target=_live_target(),
            paper_target=_demo_target(),
        )
    )
    assert package.evaluation.binding_scope_ref == "binding-a"
    assert package.other_bindings_unaffected is True


def test_kill_line_restore_requires_operator_signature() -> None:
    refused = _refusal(
        restore_kill_line_stand_down(
            binding_scope_ref="binding-a",
            venue_id=_VENUE,
            account_id="acct-live",
            issued_at=_instant(),
            operator_signature=None,
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["clears_only_by"] == OPERATOR_KILL_LINE_RESUME

    restored = _ok(
        restore_kill_line_stand_down(
            binding_scope_ref="binding-a",
            venue_id=_VENUE,
            account_id="acct-live",
            issued_at=_instant(),
            operator_signature="op-sig-resume-1",
        )
    )
    assert restored.binding_state is BindingState.LIVE
    assert restored.cleared_by == OPERATOR_KILL_LINE_RESUME


def test_loss_floor_drift_from_kill_line_refuses() -> None:
    refused = _refusal(
        evaluate_kill_line(
            binding_scope_ref="binding-a",
            equity=_money(100_000_00),
            kill_line_capital_floor=_money(80_000_00),
            loss_floor=_money(75_000_00),
            evaluated_at=_instant(),
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION


# --- AC2: breakeven ratchet origination then dispatch -------------------------


def test_v1_dynamic_protection_grammar_is_ratchet_only() -> None:
    assert _ok(refuse_non_breakeven_dynamic_grammar(DynamicProtectionGrammar.SINGLE_SIDED_BREAKEVEN_RATCHET)) is None
    refused = _refusal(refuse_non_breakeven_dynamic_grammar("trailing-stop"))
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_originate_breakeven_ratchet_waits_for_trigger() -> None:
    proposal = _ok(
        originate_breakeven_ratchet(
            original_risk_distance=_delta(100),
            current_stop_distance=_delta(100),
            favorable_excursion=_r(5, 10),  # 0.5R
            reference_price=_price(),
            trigger=_r(1),  # Book-declared — not a spine constant
            offset=None,
            amend_min_improvement=_r(1, 10),
        )
    )
    assert proposal.origin is BreakevenRatchetOrigin.NOT_YET
    assert proposal.amendment is None


def test_originate_then_dispatch_without_reapplying_min_improvement() -> None:
    proposal = _ok(
        originate_breakeven_ratchet(
            original_risk_distance=_delta(100),
            current_stop_distance=_delta(100),
            favorable_excursion=_r(12, 10),  # 1.2R ≥ trigger
            reference_price=_price(),
            trigger=_r(1),
            offset=_delta(0),
            amend_min_improvement=_r(1, 10),
        )
    )
    assert proposal.origin is BreakevenRatchetOrigin.ORIGINATED
    assert proposal.amendment is not None

    command = _ok(
        Command.amend_protection(
            _VENUE,
            _account(),
            _SESSION,
            4,
            proposal.amendment,
            "position-1",
        )
    )
    # Command path must ignore amend_min_improvement even if a huge threshold is passed.
    admitted = _ok(
        dispatch_originated_breakeven_ratchet(
            command,
            atomicity="unmeasured",
            amend_min_improvement=_r(100),  # would block if re-applied
            breakeven_offset=_delta(0),
        )
    )
    assert admitted.kind.value == "amend_protection"
    assert isinstance(admitted.protection_amendment, ProtectionAmendment)
    assert admitted.protection_amendment.protection_side is ProtectionSide.STOP


# --- AC3: qualifying-loss bench (SCN-0011) ------------------------------------


def test_scn0011_bench_fold_breakevens_never_count() -> None:
    epoch = _fp("epoch-scn-0011")
    q = _r(1)  # illustrative family q — never a spine constant
    threshold = 2  # illustrative bench_consecutive_loss_threshold
    records = (
        _mint_exit(
            seed="be-1",
            epoch=epoch,
            realized_pnl=-50,
            outcome=CloseOutcome.BREAKEVEN,
            costs=(_cost("commission", 50),),
            recorded_at=_instant(1),
        ),
        _mint_exit(
            seed="scratch-1",
            epoch=epoch,
            realized_pnl=-1_500,  # -0.15R
            close_reason=CloseReason.BOT_INTENT,
            authority=ClosingAuthority.BOOK_POLICY,
            recorded_at=_instant(2),
        ),
        _mint_exit(
            seed="ql-1",
            epoch=epoch,
            realized_pnl=-10_000,
            costs=(_cost("commission", 200),),
            recorded_at=_instant(3),
        ),
        _mint_exit(
            seed="ql-2",
            epoch=epoch,
            realized_pnl=-12_000,
            close_reason=CloseReason.HOLD_TIME_FORCE_FLAT,
            authority=ClosingAuthority.BOOK_POLICY,
            recorded_at=_instant(4),
        ),
    )
    report = _ok(
        evaluate_qualifying_loss_bench(
            records,
            binding_epoch=epoch,
            q=q,
            threshold=threshold,
        )
    )
    assert report.qualifying_loss_count == 2
    assert report.breakeven_clustering_count == 1
    assert report.fold.scratch_or_partial_count == 1
    assert report.threshold_crossed is True
    assert report.dispositions_closed == BENCH_DISPOSITIONS

    effect = _ok(
        apply_bench_crossing(
            report,
            live_target=_live_target(),
            paper_target=_demo_target(),
            book_mode=BookMode.LIVE,
        )
    )
    assert effect.seat_state is SeatState.BENCHED
    assert effect.book_mode is BookMode.LIVE
    assert effect.routing.outcome is RoutingOutcome.ROUTED_PAPER


def test_breakeven_never_counts_under_any_q() -> None:
    epoch = _fp("epoch-be-any-q")
    be = _mint_exit(
        seed="be-only",
        epoch=epoch,
        realized_pnl=0,
        outcome=CloseOutcome.BREAKEVEN,
    )
    for q in (_r(1, 1000), _r(1), _r(100)):
        report = _ok(
            evaluate_qualifying_loss_bench(
                (be,),
                binding_epoch=epoch,
                q=q,
                threshold=1,
            )
        )
        assert report.qualifying_loss_count == 0
        assert report.breakeven_clustering_count == 1
        assert report.threshold_crossed is False


def test_bench_fold_bounded_by_binding_epoch() -> None:
    epoch_a = _fp("epoch-a")
    epoch_b = _fp("epoch-b")
    in_a = _mint_exit(seed="a", epoch=epoch_a, realized_pnl=-10_000)
    in_b = _mint_exit(seed="b", epoch=epoch_b, realized_pnl=-10_000)
    report = _ok(
        evaluate_qualifying_loss_bench(
            (in_a, in_b),
            binding_epoch=epoch_a,
            q=_r(1),
            threshold=1,
        )
    )
    assert report.qualifying_loss_count == 1
    assert len(report.fold.considered) == 1


def test_stale_exit_persistence_refuses_next_intent() -> None:
    epoch = _fp("epoch-stale")
    closing = _mint_exit(seed="closing", epoch=epoch, realized_pnl=-10_000)
    refused = _refusal(
        refuse_stale_exit_before_intent(
            closing_exit_record=closing,
            persisted=False,
            journaled=True,
        )
    )
    assert refused.category is RefusalCategory.STALE_EVIDENCE
    assert _ok(
        refuse_stale_exit_before_intent(
            closing_exit_record=closing,
            persisted=True,
            journaled=True,
        )
    ) is None
