"""Epic 10 independent audit — Cluster G (Story 10.7).

CT-29 exit records, close reasons, whole-trade attribution, the qualifying-loss
bench fold, recording-precedes-interpretation, and the move-to-breakeven ratchet.
Authored from Story 10.7 ACs, CT-29, and SCN-0011.

Planned IDs: G1-G8.
"""

from __future__ import annotations

from fractions import Fraction

from qmf.core import (
    AccountRole,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Money,
    PriceDelta,
    RefusalCategory,
    Result,
    UnitKind,
    VenueId,
    World,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.exit_record import (
    VENUE_AUTHORED_CLOSE_REASONS,
    BenchDisposition,
    CloseOutcome,
    CloseReason,
    ClosingAuthority,
    CostComponent,
    ExitRecord,
    ExitRecordStream,
    ExitResultLabel,
    attribute_whole_trade,
    check_move_to_breakeven_ratchet,
    classify_bench_disposition,
    fold_bench,
    mint_exit_record,
    partition_by_close_reason,
    realized_r_of,
)
from qmf.risk.r_faces import FULL_ORIGINAL_LOSS, RFaces


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result)
    return result.value


def _usd(minor: int, scale: int = 2) -> Money:
    result = Money.try_create(minor, "USD", scale)
    assert is_ok(result)
    return result.value


def _delta(value: int) -> PriceDelta:
    result = PriceDelta.try_create(value, _instrument(), 5)
    assert is_ok(result)
    return result.value


def _r(num: int, den: int = 1) -> ExactRational:
    result = ExactRational.try_create(num, den, UnitKind.R_MULTIPLE)
    assert is_ok(result)
    return result.value


def _label() -> ExitResultLabel:
    result = ExitResultLabel.try_create(AccountRole.LIVE, World.LIVE)
    assert is_ok(result)
    return result.value


def _cost(name: str, amount: int) -> CostComponent:
    result = CostComponent.try_create(name, _usd(amount), "broker")
    assert is_ok(result)
    return result.value


def _mint(
    *,
    seed: str = "pos-1",
    bot: str = "bot-alpha",
    risk_amount: int = 10000,
    risk_distance: int = 50,
    realized_pnl: int = -10000,
    costs: tuple[CostComponent, ...] = (),
    close_reason: CloseReason = CloseReason.PROTECTIVE_STOP_FILL,
    outcome: CloseOutcome = CloseOutcome.LOSS,
    authority: ClosingAuthority = ClosingAuthority.BOOK_POLICY,
    epoch: Fingerprint | None = None,
    recorded_at: Instant | None = None,
) -> Result[ExitRecord]:
    binding_epoch = epoch if epoch is not None else _fp("epoch-1")
    if close_reason in VENUE_AUTHORED_CLOSE_REASONS or authority is ClosingAuthority.VENUE:
        authority = ClosingAuthority.VENUE
        arb = None
        vobs = _fp(f"venue-obs-{seed}")
    else:
        arb = _fp(f"arb-{seed}")
        vobs = None
    return mint_exit_record(
        virtual_position_ref=_fp(seed), opening_bot_id=bot,
        original_risk_distance=_delta(risk_distance), original_risk_amount=_usd(risk_amount),
        fill_references=(_fp(f"fill-{seed}"),), realized_pnl=_usd(realized_pnl),
        cost_components=costs, close_reason=close_reason, mechanism=close_reason,
        outcome=outcome, closing_authority=authority, close_reason_mapping_version=1,
        result_label=_label(), loss_predicate_format_version=1, binding_epoch=binding_epoch,
        recorded_at=recorded_at if recorded_at is not None else _instant(),
        arbitration_record_ref=arb, venue_observation_ref=vobs,
    )


# --- G1: exactly one immutable exit record carrying the mandated fields -------


def test_G1_one_immutable_exit_record_with_mandated_fields() -> None:
    result = _mint(realized_pnl=-10000, costs=(_cost("commission", 200),))
    assert is_ok(result)
    record = result.value
    assert record.original_risk_distance == _delta(50)
    assert record.original_risk_amount == _usd(10000)
    assert record.close_reason is CloseReason.PROTECTIVE_STOP_FILL
    assert record.closing_authority is ClosingAuthority.BOOK_POLICY
    assert record.arbitration_record_ref is not None
    assert record.result_label.account_role is AccountRole.LIVE
    # Exactly one per virtual position: a second mint for the same position refuses.
    stream = ExitRecordStream()
    assert is_ok(stream.mint(record))
    dup = _mint(seed="pos-1", realized_pnl=-5000)
    assert is_ok(dup)
    refused = stream.mint(dup.value)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- G2: realized_r is a single-sourced derived display -----------------------


def test_G2_realized_r_is_derived_never_a_second_implementation() -> None:
    result = _mint(realized_pnl=-10000, costs=(_cost("commission", 200),))
    assert is_ok(result)
    record = result.value
    # realized_r is NOT a stored dataclass field; it is derived on demand.
    assert "realized_r" not in getattr(record, "__dataclass_fields__", {})
    # net = -100.00 - 2.00 = -102.00 ; /100.00 = -1.02
    derived = record.realized_r()
    assert is_ok(derived)
    assert derived.value.as_fraction() == Fraction(-102, 100)
    # The free-function helper is the same single source, not a second division.
    via_helper = realized_r_of(record)
    assert is_ok(via_helper)
    assert via_helper.value == derived.value


# --- G3: the close-reason taxonomy; mechanism/outcome separate; kills apart ----


def test_G3_close_reason_taxonomy_mechanism_outcome_and_kills_apart() -> None:
    expected = {
        "protective_stop_fill", "target_fill", "protection_amendment_fill", "bot_intent",
        "hold_time_force_flat", "boundary_flat", "window_forced_flat", "protection_forced_flat",
        "kill_line_flat", "venue_liquidation", "venue_initiated_close", "operator_close",
    }
    assert {m.value for m in CloseReason} == expected
    assert CloseReason.KILL_LINE_FLAT is not CloseReason.PROTECTION_FORCED_FLAT
    # mechanism and outcome are separate fields: same mechanism, two outcomes.
    be = _mint(seed="be", realized_pnl=-50, costs=(_cost("commission", 50),),
               close_reason=CloseReason.PROTECTIVE_STOP_FILL, outcome=CloseOutcome.BREAKEVEN,
               authority=ClosingAuthority.VENUE)
    loss = _mint(seed="loss", realized_pnl=-10200, close_reason=CloseReason.PROTECTIVE_STOP_FILL,
                 outcome=CloseOutcome.LOSS, authority=ClosingAuthority.VENUE)
    assert is_ok(be) and is_ok(loss)
    assert be.value.mechanism is loss.value.mechanism
    assert be.value.outcome is not loss.value.outcome


# --- G4: whole-trade attribution credits the opening bot ---------------------


def test_G4_whole_trade_attribution_credits_opening_bot() -> None:
    venue_close = _mint(seed="attr-v", bot="bot-alpha", close_reason=CloseReason.PROTECTIVE_STOP_FILL,
                        authority=ClosingAuthority.VENUE, realized_pnl=-10200)
    book_close = _mint(seed="attr-b", bot="bot-alpha", close_reason=CloseReason.HOLD_TIME_FORCE_FLAT,
                       authority=ClosingAuthority.BOOK_POLICY, realized_pnl=-12000)
    assert is_ok(venue_close) and is_ok(book_close)
    a1 = attribute_whole_trade(venue_close.value)
    a2 = attribute_whole_trade(book_close.value)
    assert is_ok(a1) and is_ok(a2)
    # Regardless of who closed (venue vs book), the opening bot is credited.
    assert a1.value.opening_bot_id == "bot-alpha"
    assert a2.value.opening_bot_id == "bot-alpha"
    partitioned = partition_by_close_reason((venue_close.value, book_close.value))
    assert is_ok(partitioned)
    assert "protective_stop_fill" in partitioned.value
    assert "hold_time_force_flat" in partitioned.value


# --- G5 [SCN-0011]: the qualifying-loss bench fold ---------------------------


def test_G5_bench_counts_qualifying_losses_only() -> None:
    epoch = _fp("epoch-scn")
    q = _r(1)  # illustrative q=1R, never a spine constant
    be = _mint(seed="s1", epoch=epoch, realized_pnl=-50, costs=(_cost("commission", 50),),
               close_reason=CloseReason.PROTECTIVE_STOP_FILL, outcome=CloseOutcome.BREAKEVEN,
               authority=ClosingAuthority.VENUE, recorded_at=_instant(1))
    scratch = _mint(seed="s2", epoch=epoch, realized_pnl=-1500, close_reason=CloseReason.BOT_INTENT,
                    outcome=CloseOutcome.LOSS, authority=ClosingAuthority.BOOK_POLICY, recorded_at=_instant(2))
    ql1 = _mint(seed="s3", epoch=epoch, realized_pnl=-10000, costs=(_cost("commission", 200),),
                close_reason=CloseReason.PROTECTIVE_STOP_FILL, outcome=CloseOutcome.LOSS,
                authority=ClosingAuthority.VENUE, recorded_at=_instant(3))
    ql2 = _mint(seed="s4", epoch=epoch, realized_pnl=-12000, close_reason=CloseReason.HOLD_TIME_FORCE_FLAT,
                outcome=CloseOutcome.LOSS, authority=ClosingAuthority.BOOK_POLICY, recorded_at=_instant(4))
    for r in (be, scratch, ql1, ql2):
        assert is_ok(r)
    # per-record disposition
    assert classify_bench_disposition(be.value, q=q).value is BenchDisposition.BREAKEVEN  # type: ignore[union-attr]
    assert classify_bench_disposition(scratch.value, q=q).value is BenchDisposition.SCRATCH_OR_PARTIAL_LOSS  # type: ignore[union-attr]
    assert classify_bench_disposition(ql1.value, q=q).value is BenchDisposition.QUALIFYING_LOSS_EXIT  # type: ignore[union-attr]
    # a breakeven never counts under ANY q
    assert classify_bench_disposition(be.value, q=_r(1, 1000)).value is BenchDisposition.BREAKEVEN  # type: ignore[union-attr]
    assert classify_bench_disposition(be.value, q=_r(100)).value is BenchDisposition.BREAKEVEN  # type: ignore[union-attr]
    folded = fold_bench((be.value, scratch.value, ql1.value, ql2.value), binding_epoch=epoch, q=q, threshold=2)
    assert is_ok(folded)
    assert folded.value.qualifying_loss_count == 2
    assert folded.value.breakeven_count == 1
    assert folded.value.scratch_or_partial_count == 1
    # bounded by the binding epoch: a record in another epoch is excluded.
    other = _mint(seed="other", epoch=_fp("epoch-b"), realized_pnl=-10000, authority=ClosingAuthority.VENUE)
    assert is_ok(other)
    bounded = fold_bench((ql1.value, other.value), binding_epoch=epoch, q=q, threshold=1)
    assert is_ok(bounded)
    assert bounded.value.qualifying_loss_count == 1


# --- G6 [L3]: recording precedes interpretation (stale evidence) --------------


def test_G6_recording_precedes_interpretation_stale_evidence() -> None:
    stream = ExitRecordStream()
    minted = _mint(seed="stale", authority=ClosingAuthority.VENUE)
    assert is_ok(minted)
    fp = stream.mint(minted.value)
    assert is_ok(fp)
    # Not yet persisted/journaled -> a later same-seat intent refuses stale evidence.
    refused = stream.check_seat_may_mint_intent(closed_virtual_position_ref=minted.value.virtual_position_ref)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE
    assert is_ok(stream.mark_persisted(fp.value))
    still = stream.check_seat_may_mint_intent(closed_virtual_position_ref=minted.value.virtual_position_ref)
    assert is_refusal(still)  # persisted but not journaled -> still stale
    assert is_ok(stream.mark_journaled(fp.value))
    ok = stream.check_seat_may_mint_intent(closed_virtual_position_ref=minted.value.virtual_position_ref)
    assert is_ok(ok)


# --- G7: the move-to-breakeven ratchet is risk-non-increasing; R stays frozen -


def test_G7_breakeven_ratchet_risk_non_increasing_r_frozen() -> None:
    original = _delta(50)
    # widen refuses; an arbitrary tighten (not to breakeven) refuses; move-to-breakeven ok.
    assert is_refusal(check_move_to_breakeven_ratchet(original_risk_distance=original, proposed_risk_distance=_delta(60)))
    assert is_refusal(check_move_to_breakeven_ratchet(original_risk_distance=original, proposed_risk_distance=_delta(25)))
    assert is_ok(check_move_to_breakeven_ratchet(original_risk_distance=original, proposed_risk_distance=_delta(0)))
    # R stays frozen: after a legal ratchet, -1R still means a full original loss.
    minted = _mint(seed="frozen", risk_amount=10000, risk_distance=50, realized_pnl=-10000, authority=ClosingAuthority.VENUE)
    assert is_ok(minted)
    faces = RFaces.try_create(minted.value.original_risk_distance, minted.value.original_risk_amount)
    assert is_ok(faces)
    full_loss = faces.value.r_multiple_of(_usd(-10000))
    assert is_ok(full_loss)
    assert full_loss.value == FULL_ORIGINAL_LOSS


# --- G8 [L4]: SCN-0011 executable golden fixture -----------------------------


def test_G8_scn0011_qualifying_loss_bench_end_to_end() -> None:
    """SCN-0011: four exits in one binding epoch; two qualifying losses cross a
    threshold of 2, and the whole-trade R credits the OPENING bot regardless of
    who closed. q and the threshold are illustrative, never spine constants."""
    epoch = _fp("scn0011-epoch")
    q = _r(1)
    threshold = 2
    # Four exits on the same (Book, Bot) opened by bot-alpha; some closed by the venue,
    # some by book policy.
    exits = [
        _mint(seed="e1", bot="bot-alpha", epoch=epoch, realized_pnl=-50,
              costs=(_cost("commission", 50),), close_reason=CloseReason.PROTECTIVE_STOP_FILL,
              outcome=CloseOutcome.BREAKEVEN, authority=ClosingAuthority.VENUE, recorded_at=_instant(1)),
        _mint(seed="e2", bot="bot-alpha", epoch=epoch, realized_pnl=-1500,
              close_reason=CloseReason.BOT_INTENT, outcome=CloseOutcome.LOSS,
              authority=ClosingAuthority.BOOK_POLICY, recorded_at=_instant(2)),
        _mint(seed="e3", bot="bot-alpha", epoch=epoch, realized_pnl=-10000,
              costs=(_cost("commission", 200),), close_reason=CloseReason.PROTECTIVE_STOP_FILL,
              outcome=CloseOutcome.LOSS, authority=ClosingAuthority.VENUE, recorded_at=_instant(3)),
        _mint(seed="e4", bot="bot-alpha", epoch=epoch, realized_pnl=-12000,
              close_reason=CloseReason.KILL_LINE_FLAT, outcome=CloseOutcome.LOSS,
              authority=ClosingAuthority.BOOK_POLICY, recorded_at=_instant(4)),
    ]
    records = []
    for r in exits:
        assert is_ok(r)
        records.append(r.value)
    # Whole-trade attribution credits the opening bot on every close, including the
    # kill_line_flat closed by book policy.
    for record in records:
        attributed = attribute_whole_trade(record)
        assert is_ok(attributed)
        assert attributed.value.opening_bot_id == "bot-alpha"
    # The read-time bench fold, bounded by the epoch, counts exactly the two qualifying
    # losses and crosses the threshold -> seat benched.
    folded = fold_bench(tuple(records), binding_epoch=epoch, q=q, threshold=threshold)
    assert is_ok(folded)
    assert folded.value.qualifying_loss_count == 2
    assert folded.value.breakeven_count == 1
    assert folded.value.scratch_or_partial_count == 1
    assert folded.value.threshold_crossed is True
