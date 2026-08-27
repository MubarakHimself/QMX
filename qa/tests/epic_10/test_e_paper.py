"""Epic 10 independent audit — Cluster E (Story 10.5).

Paper as a dated binding-epoch change (CT-24), plus the SCN-0006 golden fixture.
Authored from Story 10.5 ACs, CT-24, and SCN-0006.

Planned IDs: E1-E8.
"""

from __future__ import annotations

from qmf.core import (
    AccountRole,
    Fingerprint,
    Instant,
    Money,
    RefusalCategory,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.binding import BookInstanceId
from qmf.risk.paper import (
    ActiveControl,
    BindingTransitionRecord,
    BindingTransitionStream,
    BookMode,
    ClearingCause,
    ExecutionTarget,
    ModeFoldResult,
    PaperEpochLog,
    PaperEpochRecord,
    PaperTargetLog,
    PaperTargetRecord,
    ReturnMechanism,
    RoutingOutcome,
    SeatState,
    TreasuryBoundaryKind,
    TriggerDisposition,
    TriggerKind,
    authorize_return_to_live,
    reject_paper_pnl_to_treasury,
    reset_paper_epoch,
    resolve_execution_target,
    validate_book_mode,
)

_VENUE = VenueId(value="venue-ctrader")


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result)
    return result.value


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _book_id(value: str = "book-inst-1") -> BookInstanceId:
    result = BookInstanceId.try_create(value)
    assert is_ok(result)
    return result.value


def _live_target(account: str = "acct-live") -> ExecutionTarget:
    result = ExecutionTarget.try_create(AccountRole.LIVE, _VENUE, account)
    assert is_ok(result)
    return result.value


def _paper_target(account: str = "acct-demo") -> ExecutionTarget:
    result = ExecutionTarget.try_create(AccountRole.PAPER_VALIDATION, _VENUE, account)
    assert is_ok(result)
    return result.value


def _trigger(disposition: TriggerDisposition = TriggerDisposition.ROUTES_TO_PAPER,
             name: str = "operator-paper-flip") -> TriggerKind:
    result = TriggerKind.try_create(name, disposition)
    assert is_ok(result)
    return result.value


def _control(disposition: TriggerDisposition, control_id: str = "c1") -> ActiveControl:
    result = ActiveControl.try_create(control_id, disposition)
    assert is_ok(result)
    return result.value


def _usd(minor: int = 500_000) -> Money:
    result = Money.try_create(minor, "USD", 2)
    assert is_ok(result)
    return result.value


def _live_transition(book: BookInstanceId, instant: Instant) -> BindingTransitionRecord:
    result = BindingTransitionRecord.try_create(
        book, _fp("binding-live"), BookMode.LIVE, instant,
        _trigger(TriggerDisposition.ROUTES_TO_PAPER, "first-live-entry"),
    )
    assert is_ok(result)
    return result.value


def _paper_transition(book: BookInstanceId, instant: Instant) -> BindingTransitionRecord:
    result = BindingTransitionRecord.try_create(
        book, _fp("binding-paper"), BookMode.PAPER, instant, _trigger(),
        paper_target_ref=_paper_target(), paper_epoch_ref=_fp("paper-epoch-1"),
    )
    assert is_ok(result)
    return result.value


# --- E1: modes are exactly LIVE|PAPER; a seat/binding word in the mode refuses -


def test_E1_book_modes_are_exactly_live_and_paper() -> None:
    assert {m.value for m in BookMode} == {"LIVE", "PAPER"}
    assert is_ok(validate_book_mode(BookMode.PAPER))
    for word in ("active", "benched", "live", "paper", "stood-down"):
        result = validate_book_mode(word)
        assert is_refusal(result), word
        assert result.category is RefusalCategory.INVALID_INPUT


# --- E2: the flip is a dated epoch change; current mode is a read-time fold ----


def test_E2_flip_is_dated_epoch_change_and_mode_is_a_fold() -> None:
    stream = BindingTransitionStream()
    book = _book_id()
    # An empty stream folds fail-closed to the most-restrictive PAPER (never a stored field).
    empty = stream.current_mode(book)
    assert isinstance(empty, ModeFoldResult)
    assert empty.mode is BookMode.PAPER
    assert empty.fail_closed is True
    assert is_ok(stream.mint(_live_transition(book, _instant(1_000))))
    assert stream.current_mode(book).mode is BookMode.LIVE
    # A later PAPER flip is a NEW dated transition minting a new epoch; the fold reports
    # PAPER without any field mutation, and it is the SAME book (not a new Book/twin).
    paper = _paper_transition(book, _instant(2_000))
    assert is_ok(stream.mint(paper))
    assert stream.current_mode(book).mode is BookMode.PAPER
    assert paper.book_instance_id == book


# --- E3: routing resolved once; PAPER selects the paired target, one submission -


def test_E3_paper_mode_selects_the_single_paired_target() -> None:
    live, paper = _live_target(), _paper_target()
    result = resolve_execution_target(
        book_mode=BookMode.PAPER, seat_state=SeatState.ACTIVE, active_controls=[],
        live_target=live, paper_target=paper,
    )
    assert is_ok(result)
    assert result.value.outcome is RoutingOutcome.ROUTED_PAPER
    # Exactly one target, the paired one — never also the live target (one submission).
    assert result.value.execution_target == paper
    assert result.value.execution_target != live


# --- E4: exactly one active paper target; none resolvable -> unavailable ------


def test_E4_one_active_paper_target_per_binding() -> None:
    log = PaperTargetLog()
    binding = _fp("binding-1")
    first = PaperTargetRecord.try_create(binding, _paper_target("demo-a"), _instant(1_000))
    assert is_ok(first)
    assert is_ok(log.mint(first.value))
    active = log.resolve_active_target(binding)
    assert is_ok(active)
    assert active.value.account_id == "demo-a"
    # A second target without a supersedes edge refuses (only one active at an instant).
    second = PaperTargetRecord.try_create(binding, _paper_target("demo-b"), _instant(2_000))
    assert is_ok(second)
    assert is_refusal(log.mint(second.value))
    # No resolvable target for a paper transition is an unavailable-dependency refusal.
    no_target = resolve_execution_target(
        book_mode=BookMode.PAPER, seat_state=SeatState.ACTIVE, active_controls=[],
        live_target=_live_target(), paper_target=None,
    )
    assert is_refusal(no_target)
    assert no_target.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# --- E5: trigger disposition routes-to-paper vs blocks-paper; recording != trade -


def test_E5_trigger_disposition_routes_or_blocks_recording_not_trading() -> None:
    # routes-to-paper (capital/authority) routes to paper.
    routed = resolve_execution_target(
        book_mode=BookMode.LIVE, seat_state=SeatState.ACTIVE,
        active_controls=[_control(TriggerDisposition.ROUTES_TO_PAPER, "kill-line-stand-down")],
        live_target=_live_target(), paper_target=_paper_target(),
    )
    assert is_ok(routed)
    assert routed.value.outcome is RoutingOutcome.ROUTED_PAPER
    # blocks-paper (market-risk) blocks even in PAPER mode -> recording only, not trading.
    blocked = resolve_execution_target(
        book_mode=BookMode.PAPER, seat_state=SeatState.ACTIVE,
        active_controls=[_control(TriggerDisposition.BLOCKS_PAPER, "news-window")],
        live_target=_live_target(), paper_target=_paper_target(),
    )
    assert is_ok(blocked)
    assert blocked.value.outcome is RoutingOutcome.BLOCKED
    assert blocked.value.execution_target is None
    assert blocked.value.is_recording_only() is True


# --- E6: paper balance frozen at flip; reset mints signed epoch; no boundary ---


def test_E6_paper_balance_frozen_reset_signed_no_money_boundary() -> None:
    log = PaperEpochLog()
    binding = _fp("binding-1")
    first = PaperEpochRecord.try_create(_book_id(), binding, _usd(), "operator-mubarak", _instant())
    assert is_ok(first)
    first_fp = log.mint(first.value)
    assert is_ok(first_fp)
    # A reset mints a NEW operator-signed paper_epoch_reset with a fresh balance + lineage;
    # the running balance is never mutated (both epochs remain in the append-only log).
    reset = reset_paper_epoch(
        book_instance_id=_book_id(), binding_ref=binding,
        prior_epoch_fingerprint=first_fp.value, fresh_balance=_usd(1_000_000),
        operator_signature="operator-mubarak", dated_at=_instant(2_000),
    )
    assert is_ok(reset)
    assert reset.value.boundary_kind is TreasuryBoundaryKind.PAPER_EPOCH_RESET
    assert is_ok(log.mint(reset.value))
    assert len(log.epochs()) == 2
    # A non-USD or non-positive starting balance is refused; paper P&L never crosses money.
    assert is_refusal(PaperEpochRecord.try_create(_book_id(), binding, Money(value=5, currency="EUR", scale=2), "op", _instant()))
    assert reject_paper_pnl_to_treasury(_usd(1_000)).category is RefusalCategory.POLICY_REJECTION


# --- E7: return to live asymmetry --------------------------------------------


def test_E7_return_to_live_asymmetry() -> None:
    # Clocked+mechanical: automatic CT-24 transition, no signature (refuses a signature).
    mechanical = authorize_return_to_live(clearing_cause=ClearingCause.CLOCKED_MECHANICAL)
    assert is_ok(mechanical)
    assert mechanical.value.mechanism is ReturnMechanism.CT24_TRANSITION
    assert mechanical.value.operator_signature is None
    assert is_refusal(authorize_return_to_live(
        clearing_cause=ClearingCause.CLOCKED_MECHANICAL, operator_signature="op"
    ))
    # Real money (first live entry) requires an operator signature.
    assert is_refusal(authorize_return_to_live(clearing_cause=ClearingCause.FIRST_LIVE_ENTRY))
    assert is_ok(authorize_return_to_live(
        clearing_cause=ClearingCause.FIRST_LIVE_ENTRY, operator_signature="operator-mubarak"
    ))
    # A control stand-down clears only by an operator CT-30 resume.
    resume = authorize_return_to_live(
        clearing_cause=ClearingCause.CONTROL_STAND_DOWN, operator_signature="operator-mubarak"
    )
    assert is_ok(resume)
    assert resume.value.mechanism is ReturnMechanism.CT30_RESUME
    # Paper performance NEVER authorizes a return.
    assert is_refusal(authorize_return_to_live(
        clearing_cause=ClearingCause.FIRST_LIVE_ENTRY, operator_signature="op",
        justified_by_paper_performance=True,
    ))


# --- E8 [L4]: SCN-0006 executable golden fixture end-to-end -------------------


def test_E8_scn0006_book_paper_transition_end_to_end() -> None:
    """SCN-0006: a Book flips live->paper->live as dated binding-epoch changes.

    The Book identity, its execution-target selection, and the money boundary all
    hold; the current mode is always a read-time fold over the CT-24 stream.
    """
    stream = BindingTransitionStream()
    book = _book_id("scn-0006-book")

    # 1. First live entry establishes LIVE.
    assert is_ok(stream.mint(_live_transition(book, _instant(1_000))))
    assert stream.current_mode(book).mode is BookMode.LIVE
    live_route = resolve_execution_target(
        book_mode=BookMode.LIVE, seat_state=SeatState.ACTIVE, active_controls=[],
        live_target=_live_target(), paper_target=_paper_target(),
    )
    assert is_ok(live_route)
    assert live_route.value.outcome is RoutingOutcome.ROUTED_LIVE

    # 2. A dated flip to PAPER mints a new epoch on the SAME book (no new Book/twin).
    paper = _paper_transition(book, _instant(2_000))
    assert is_ok(stream.mint(paper))
    fold_after_flip = stream.current_mode(book)
    assert fold_after_flip.mode is BookMode.PAPER
    assert fold_after_flip.fail_closed is False
    paper_route = resolve_execution_target(
        book_mode=BookMode.PAPER, seat_state=SeatState.ACTIVE, active_controls=[],
        live_target=_live_target(), paper_target=_paper_target(),
    )
    assert is_ok(paper_route)
    assert paper_route.value.execution_target.role is AccountRole.PAPER_VALIDATION

    # 3. Knowledge-time bound: as-of before the flip still folds to LIVE.
    assert stream.current_mode(book, as_of=_instant(1_500)).mode is BookMode.LIVE

    # 4. Return to live is a clocked-mechanical CT-24 transition (no resume, no signature).
    outcome = authorize_return_to_live(clearing_cause=ClearingCause.CLOCKED_MECHANICAL)
    assert is_ok(outcome)
    assert outcome.value.mechanism is ReturnMechanism.CT24_TRANSITION
    return_transition = BindingTransitionRecord.try_create(
        book, _fp("binding-live-2"), BookMode.LIVE, _instant(3_000),
        _trigger(TriggerDisposition.ROUTES_TO_PAPER, "day-boundary-clear"),
    )
    assert is_ok(return_transition)
    assert is_ok(stream.mint(return_transition.value))
    assert stream.current_mode(book).mode is BookMode.LIVE
