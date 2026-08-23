"""Story 10.7 — CT-29 exit records, close reasons, attribution, and the bench fold.

Verifies exactly one immutable exit record per virtual (Book) position close carrying
frozen R faces, fill references, realized_pnl, identity-bearing cost_components, a
single-sourced realized_r (derived display never a second division), the close-reason
taxonomy with mechanism and outcome as separate fields and kill_line_flat minted apart
from protection_forced_flat (AC1, AC2); whole-trade attribution crediting the opening
Bot with no apportionment and reports partitioned by close reason (AC3); the read-time
bench fold counting qualifying-loss exits (realized_r <= -q) over the binding epoch,
with scratches and breakevens excluded (AC4); recording-precedes-interpretation stale
evidence refusal (AC5); and the V1 move-to-breakeven ratchet risk-non-increasing against
frozen original_risk_distance with R staying frozen (AC6) (FR-032; CT-29; DEC-0155).
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
    CLOSE_REASON_EVIDENCE_MAPPING,
    CT29_CONTRACT_FORMAT_VERSION,
    QUALIFYING_LOSS_THRESHOLD_VARIABLE,
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
    check_recording_precedes_interpretation,
    classify_bench_disposition,
    fold_bench,
    mint_exit_record,
    partition_by_close_reason,
    realized_r_of,
)
from qmf.risk.r_faces import FULL_ORIGINAL_LOSS, RFaces

# --- builders ----------------------------------------------------------------


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _instant(value_ns: int = 1_700_000_000_000_000_000) -> Instant:
    result = Instant.try_create(value_ns)
    assert is_ok(result)
    return result.value


def _money(value: int, scale: int = 2) -> Money:
    result = Money.try_create(value, "USD", scale)
    assert is_ok(result)
    return result.value


def _delta(value: int) -> PriceDelta:
    result = PriceDelta.try_create(value, _instrument(), 5)
    assert is_ok(result)
    return result.value


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    result = ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE)
    assert is_ok(result)
    return result.value


def _label(*, role: AccountRole = AccountRole.LIVE) -> ExitResultLabel:
    result = ExitResultLabel.try_create(role, World.LIVE)
    assert is_ok(result)
    return result.value


def _cost(name: str, amount: int, source: str = "broker") -> CostComponent:
    result = CostComponent.try_create(name, _money(amount), source)
    assert is_ok(result)
    return result.value


def _mint(
    *,
    seed: str = "pos-1",
    bot: str = "bot-alpha",
    risk_amount: int = 10000,  # $100.00 at scale 2
    risk_distance: int = 50,
    realized_pnl: int = -10000,
    costs: tuple[CostComponent, ...] = (),
    close_reason: CloseReason = CloseReason.PROTECTIVE_STOP_FILL,
    mechanism: CloseReason | None = None,
    outcome: CloseOutcome = CloseOutcome.LOSS,
    authority: ClosingAuthority = ClosingAuthority.BOOK_POLICY,
    epoch: Fingerprint | None = None,
    recorded_at: Instant | None = None,
    arbitration: Fingerprint | None = None,
    venue_obs: Fingerprint | None = None,
) -> Result[ExitRecord]:
    binding_epoch = epoch if epoch is not None else _fp("epoch-1")
    mech = mechanism if mechanism is not None else close_reason
    arb = arbitration
    vobs = venue_obs
    if close_reason in VENUE_AUTHORED_CLOSE_REASONS or authority is ClosingAuthority.VENUE:
        authority = ClosingAuthority.VENUE
        vobs = vobs if vobs is not None else _fp(f"venue-obs-{seed}")
        arb = None
    else:
        arb = arb if arb is not None else _fp(f"arb-{seed}")
        vobs = None
    return mint_exit_record(
        virtual_position_ref=_fp(seed),
        opening_bot_id=bot,
        original_risk_distance=_delta(risk_distance),
        original_risk_amount=_money(risk_amount),
        fill_references=(_fp(f"fill-{seed}"),),
        realized_pnl=_money(realized_pnl),
        cost_components=costs,
        close_reason=close_reason,
        mechanism=mech,
        outcome=outcome,
        closing_authority=authority,
        close_reason_mapping_version=1,
        result_label=_label(),
        loss_predicate_format_version=1,
        binding_epoch=binding_epoch,
        recorded_at=recorded_at if recorded_at is not None else _instant(),
        arbitration_record_ref=arb,
        venue_observation_ref=vobs,
    )


# --- AC1: one immutable exit record per virtual close ------------------------


def test_mint_exit_record_carries_frozen_r_faces_and_derived_realized_r() -> None:
    costs = (_cost("commission", 200),)
    result = _mint(realized_pnl=-10000, costs=costs, outcome=CloseOutcome.LOSS)
    assert is_ok(result)
    record = result.value
    assert record.original_risk_distance == _delta(50)
    assert record.original_risk_amount == _money(10000)
    assert record.close_reason is CloseReason.PROTECTIVE_STOP_FILL
    assert record.result_label.account_role is AccountRole.LIVE
    # realized_r is derived, never a stored independent field
    assert (
        not hasattr(record, "__dataclass_fields__")
        or "realized_r" not in record.__dataclass_fields__
    )
    realized = record.realized_r()
    assert is_ok(realized)
    # net = -100.00 - 2.00 = -102.00; / 100.00 = -1.02
    assert realized.value.as_fraction() == Fraction(-102, 100)
    via_helper = realized_r_of(record)
    assert is_ok(via_helper)
    assert via_helper.value == realized.value


def test_stream_refuses_second_mint_for_same_virtual_position() -> None:
    stream = ExitRecordStream()
    first = _mint(seed="pos-same")
    assert is_ok(first)
    assert is_ok(stream.mint(first.value))
    second = _mint(seed="pos-same", realized_pnl=-5000)
    assert is_ok(second)
    refused = stream.mint(second.value)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_kill_line_flat_is_minted_apart_from_protection_forced_flat() -> None:
    assert CloseReason.KILL_LINE_FLAT is not CloseReason.PROTECTION_FORCED_FLAT
    assert CloseReason.KILL_LINE_FLAT.value == "kill_line_flat"
    assert CloseReason.PROTECTION_FORCED_FLAT.value == "protection_forced_flat"
    kill = _mint(
        seed="pos-kill",
        close_reason=CloseReason.KILL_LINE_FLAT,
        authority=ClosingAuthority.BOOK_POLICY,
    )
    assert is_ok(kill)
    assert kill.value.close_reason is CloseReason.KILL_LINE_FLAT
    forced = _mint(
        seed="pos-ks",
        close_reason=CloseReason.PROTECTION_FORCED_FLAT,
        authority=ClosingAuthority.PROTECTION_AUTHORITY,
    )
    assert is_ok(forced)
    assert forced.value.close_reason is CloseReason.PROTECTION_FORCED_FLAT


def test_mechanism_and_outcome_are_separate_fields() -> None:
    # Same mechanism, two outcomes — no rule over mechanism alone (SCN-0011).
    be = _mint(
        seed="pos-be",
        realized_pnl=-50,
        costs=(_cost("commission", 50),),
        close_reason=CloseReason.PROTECTIVE_STOP_FILL,
        mechanism=CloseReason.PROTECTIVE_STOP_FILL,
        outcome=CloseOutcome.BREAKEVEN,
        authority=ClosingAuthority.VENUE,
    )
    assert is_ok(be)
    assert be.value.mechanism is CloseReason.PROTECTIVE_STOP_FILL
    assert be.value.outcome is CloseOutcome.BREAKEVEN
    loss = _mint(
        seed="pos-full",
        realized_pnl=-10200,
        close_reason=CloseReason.PROTECTIVE_STOP_FILL,
        mechanism=CloseReason.PROTECTIVE_STOP_FILL,
        outcome=CloseOutcome.LOSS,
        authority=ClosingAuthority.VENUE,
    )
    assert is_ok(loss)
    assert loss.value.mechanism is be.value.mechanism
    assert loss.value.outcome is not be.value.outcome


def test_venue_authored_close_carries_observation_not_arbitration() -> None:
    ok = _mint(
        seed="pos-venue",
        close_reason=CloseReason.VENUE_LIQUIDATION,
        authority=ClosingAuthority.VENUE,
    )
    assert is_ok(ok)
    assert ok.value.venue_observation_ref is not None
    assert ok.value.arbitration_record_ref is None
    # Node authority with venue reason refuses.
    bad = mint_exit_record(
        virtual_position_ref=_fp("pos-bad"),
        opening_bot_id="bot-alpha",
        original_risk_distance=_delta(50),
        original_risk_amount=_money(10000),
        fill_references=(_fp("fill-bad"),),
        realized_pnl=_money(-10000),
        cost_components=(),
        close_reason=CloseReason.VENUE_LIQUIDATION,
        mechanism=CloseReason.VENUE_LIQUIDATION,
        outcome=CloseOutcome.LOSS,
        closing_authority=ClosingAuthority.BOOK_POLICY,
        close_reason_mapping_version=1,
        result_label=_label(),
        loss_predicate_format_version=1,
        binding_epoch=_fp("epoch-1"),
        recorded_at=_instant(),
        arbitration_record_ref=_fp("arb-bad"),
    )
    assert is_refusal(bad)


def test_close_reason_taxonomy_is_complete_and_evidence_mapping_is_recorded() -> None:
    expected = {
        "protective_stop_fill",
        "target_fill",
        "protection_amendment_fill",
        "bot_intent",
        "hold_time_force_flat",
        "boundary_flat",
        "window_forced_flat",
        "protection_forced_flat",
        "kill_line_flat",
        "venue_liquidation",
        "venue_initiated_close",
        "operator_close",
    }
    assert {member.value for member in CloseReason} == expected
    assert CLOSE_REASON_EVIDENCE_MAPPING["SL_HIT"] == "protective_stop_fill"
    assert CLOSE_REASON_EVIDENCE_MAPPING["KS_FORCED_CLOSE"] == "protection_forced_flat"
    assert CT29_CONTRACT_FORMAT_VERSION == 1
    assert QUALIFYING_LOSS_THRESHOLD_VARIABLE == "qualifying_loss_threshold"


# --- AC3: whole-trade attribution --------------------------------------------


def test_whole_trade_attribution_credits_opening_bot_regardless_of_closer() -> None:
    venue_close = _mint(
        seed="pos-attr-v",
        bot="bot-alpha",
        close_reason=CloseReason.PROTECTIVE_STOP_FILL,
        authority=ClosingAuthority.VENUE,
        realized_pnl=-10200,
    )
    assert is_ok(venue_close)
    book_close = _mint(
        seed="pos-attr-b",
        bot="bot-alpha",
        close_reason=CloseReason.HOLD_TIME_FORCE_FLAT,
        authority=ClosingAuthority.BOOK_POLICY,
        realized_pnl=-12000,
    )
    assert is_ok(book_close)
    a1 = attribute_whole_trade(venue_close.value)
    a2 = attribute_whole_trade(book_close.value)
    assert is_ok(a1) and is_ok(a2)
    assert a1.value.opening_bot_id == "bot-alpha"
    assert a2.value.opening_bot_id == "bot-alpha"
    assert a1.value.close_reason is CloseReason.PROTECTIVE_STOP_FILL
    assert a2.value.close_reason is CloseReason.HOLD_TIME_FORCE_FLAT
    partitioned = partition_by_close_reason((venue_close.value, book_close.value))
    assert is_ok(partitioned)
    assert "protective_stop_fill" in partitioned.value
    assert "hold_time_force_flat" in partitioned.value
    assert len(partitioned.value["protective_stop_fill"]) == 1


# --- AC4: bench fold (SCN-0011 numbers) --------------------------------------


def test_bench_fold_counts_qualifying_losses_ignores_breakeven_and_scratch() -> None:
    epoch = _fp("epoch-scn")
    q = _r(1)  # illustrative q=1R — never a spine constant
    threshold = 2  # illustrative bench_consecutive_loss_threshold
    # 1. breakeven (outcome stamped) — never counts under any q
    be = _mint(
        seed="scn-1",
        epoch=epoch,
        realized_pnl=-50,
        costs=(_cost("commission", 50),),
        close_reason=CloseReason.PROTECTIVE_STOP_FILL,
        outcome=CloseOutcome.BREAKEVEN,
        authority=ClosingAuthority.VENUE,
        recorded_at=_instant(1),
    )
    # 2. scratch -0.15R
    scratch = _mint(
        seed="scn-2",
        epoch=epoch,
        realized_pnl=-1500,  # -15.00 / 100.00 = -0.15
        close_reason=CloseReason.BOT_INTENT,
        outcome=CloseOutcome.LOSS,
        authority=ClosingAuthority.BOOK_POLICY,
        recorded_at=_instant(2),
    )
    # 3. qualifying -1.02R
    ql1 = _mint(
        seed="scn-3",
        epoch=epoch,
        realized_pnl=-10000,
        costs=(_cost("commission", 200),),
        close_reason=CloseReason.PROTECTIVE_STOP_FILL,
        outcome=CloseOutcome.LOSS,
        authority=ClosingAuthority.VENUE,
        recorded_at=_instant(3),
    )
    # 4. qualifying -1.2R hold-time force flat
    ql2 = _mint(
        seed="scn-4",
        epoch=epoch,
        realized_pnl=-12000,
        close_reason=CloseReason.HOLD_TIME_FORCE_FLAT,
        outcome=CloseOutcome.LOSS,
        authority=ClosingAuthority.BOOK_POLICY,
        recorded_at=_instant(4),
    )
    assert is_ok(be)
    assert is_ok(scratch)
    assert is_ok(ql1)
    assert is_ok(ql2)
    records = (be.value, scratch.value, ql1.value, ql2.value)

    be_disp = classify_bench_disposition(be.value, q=q)
    scratch_disp = classify_bench_disposition(scratch.value, q=q)
    ql1_disp = classify_bench_disposition(ql1.value, q=q)
    ql2_disp = classify_bench_disposition(ql2.value, q=q)
    assert is_ok(be_disp)
    assert is_ok(scratch_disp)
    assert is_ok(ql1_disp)
    assert is_ok(ql2_disp)
    assert be_disp.value is BenchDisposition.BREAKEVEN
    assert scratch_disp.value is BenchDisposition.SCRATCH_OR_PARTIAL_LOSS
    assert ql1_disp.value is BenchDisposition.QUALIFYING_LOSS_EXIT
    assert ql2_disp.value is BenchDisposition.QUALIFYING_LOSS_EXIT

    folded = fold_bench(records, binding_epoch=epoch, q=q, threshold=threshold)
    assert is_ok(folded)
    assert folded.value.qualifying_loss_count == 2
    assert folded.value.breakeven_count == 1
    assert folded.value.scratch_or_partial_count == 1
    assert folded.value.threshold_crossed is True


def test_bench_fold_is_bounded_by_binding_epoch() -> None:
    epoch_a = _fp("epoch-a")
    epoch_b = _fp("epoch-b")
    q = _r(1)
    in_a = _mint(
        seed="ep-a",
        epoch=epoch_a,
        realized_pnl=-10000,
        authority=ClosingAuthority.VENUE,
    )
    in_b = _mint(
        seed="ep-b",
        epoch=epoch_b,
        realized_pnl=-10000,
        authority=ClosingAuthority.VENUE,
    )
    assert is_ok(in_a)
    assert is_ok(in_b)
    folded = fold_bench((in_a.value, in_b.value), binding_epoch=epoch_a, q=q, threshold=1)
    assert is_ok(folded)
    assert folded.value.qualifying_loss_count == 1
    assert len(folded.value.considered) == 1


def test_breakeven_never_counts_under_any_q() -> None:
    be = _mint(
        seed="be-any-q",
        realized_pnl=0,
        outcome=CloseOutcome.BREAKEVEN,
        authority=ClosingAuthority.VENUE,
    )
    assert is_ok(be)
    tiny_q = _r(1, 1000)  # 0.001R
    tiny_disp = classify_bench_disposition(be.value, q=tiny_q)
    assert is_ok(tiny_disp)
    assert tiny_disp.value is BenchDisposition.BREAKEVEN
    huge_q = _r(100)
    huge_disp = classify_bench_disposition(be.value, q=huge_q)
    assert is_ok(huge_disp)
    assert huge_disp.value is BenchDisposition.BREAKEVEN


# --- AC5: recording precedes interpretation ----------------------------------


def test_later_intent_refuses_stale_evidence_until_persisted_and_journaled() -> None:
    stream = ExitRecordStream()
    minted = _mint(seed="stale-pos", authority=ClosingAuthority.VENUE)
    assert is_ok(minted)
    fp = stream.mint(minted.value)
    assert is_ok(fp)
    # Not yet persisted/journaled → stale evidence
    refused = stream.check_seat_may_mint_intent(
        closed_virtual_position_ref=minted.value.virtual_position_ref
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE
    assert is_ok(stream.mark_persisted(fp.value))
    still = stream.check_seat_may_mint_intent(
        closed_virtual_position_ref=minted.value.virtual_position_ref
    )
    assert is_refusal(still)
    assert still.category is RefusalCategory.STALE_EVIDENCE
    assert is_ok(stream.mark_journaled(fp.value))
    ok = stream.check_seat_may_mint_intent(
        closed_virtual_position_ref=minted.value.virtual_position_ref
    )
    assert is_ok(ok)


def test_missing_closing_exit_is_stale_evidence() -> None:
    refused = check_recording_precedes_interpretation(
        closing_exit_record=None,
        persisted=False,
        journaled=False,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE


# --- AC6: move-to-breakeven ratchet; R stays frozen --------------------------


def test_move_to_breakeven_ratchet_refuses_widen_and_non_breakeven_tighten() -> None:
    original = _delta(50)
    # Widen refuses (risk-increasing).
    widened = check_move_to_breakeven_ratchet(
        original_risk_distance=original,
        proposed_risk_distance=_delta(60),
    )
    assert is_refusal(widened)
    assert widened.category is RefusalCategory.POLICY_REJECTION
    # Arbitrary tighten that is not to breakeven refuses (V1 ratchet only).
    trailing = check_move_to_breakeven_ratchet(
        original_risk_distance=original,
        proposed_risk_distance=_delta(25),
    )
    assert is_refusal(trailing)
    assert trailing.category is RefusalCategory.POLICY_REJECTION
    # Move to breakeven (zero offset) is legal.
    be = check_move_to_breakeven_ratchet(
        original_risk_distance=original,
        proposed_risk_distance=_delta(0),
    )
    assert is_ok(be)


def test_r_faces_stay_frozen_after_breakeven_ratchet() -> None:
    minted = _mint(
        seed="frozen-r",
        risk_amount=10000,
        risk_distance=50,
        realized_pnl=-10000,
        authority=ClosingAuthority.VENUE,
    )
    assert is_ok(minted)
    record = minted.value
    faces = RFaces.try_create(record.original_risk_distance, record.original_risk_amount)
    assert is_ok(faces)
    # After a legal breakeven ratchet the exit record's frozen faces are unchanged.
    assert is_ok(
        check_move_to_breakeven_ratchet(
            original_risk_distance=record.original_risk_distance,
            proposed_risk_distance=_delta(0),
        )
    )
    assert record.original_risk_distance == _delta(50)
    assert record.original_risk_amount == _money(10000)
    full_loss = faces.value.r_multiple_of(_money(-10000))
    assert is_ok(full_loss)
    assert full_loss.value == FULL_ORIGINAL_LOSS


def test_null_close_reason_refuses() -> None:
    refused = mint_exit_record(
        virtual_position_ref=_fp("null-reason"),
        opening_bot_id="bot-alpha",
        original_risk_distance=_delta(50),
        original_risk_amount=_money(10000),
        fill_references=(_fp("fill-null"),),
        realized_pnl=_money(-10000),
        cost_components=(),
        close_reason=None,
        mechanism=CloseReason.BOT_INTENT,
        outcome=CloseOutcome.LOSS,
        closing_authority=ClosingAuthority.BOOK_POLICY,
        close_reason_mapping_version=1,
        result_label=_label(),
        loss_predicate_format_version=1,
        binding_epoch=_fp("epoch-1"),
        recorded_at=_instant(),
        arbitration_record_ref=_fp("arb-null"),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
