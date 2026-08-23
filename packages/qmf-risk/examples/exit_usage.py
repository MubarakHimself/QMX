"""Reference usage — CT-29 exit records, attribution, and the bench fold (COMP-QMF-RISK).

Executable::

    python packages/qmf-risk/examples/exit_usage.py

Mints four SCN-0011-shaped exit records for one binding epoch, derives single-sourced
``realized_r`` from frozen fields, credits whole-trade attribution to the opening Bot,
folds the qualifying-loss bench (breakeven and scratch excluded), enforces
recording-precedes-interpretation, and shows the V1 move-to-breakeven ratchet.
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
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result), f"fingerprint failed for {seed!r}"
    return result.value


def _instant(ns: int) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result), "instant mint failed"
    return result.value


def _money(value: int) -> Money:
    result = Money.try_create(value, "USD", 2)
    assert is_ok(result), "money mint failed"
    return result.value


def _delta(value: int) -> PriceDelta:
    instrument = Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")
    result = PriceDelta.try_create(value, instrument, 5)
    assert is_ok(result), "price-delta mint failed"
    return result.value


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    result = ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE)
    assert is_ok(result), "r-multiple mint failed"
    return result.value


def _label() -> ExitResultLabel:
    result = ExitResultLabel.try_create(AccountRole.LIVE, World.LIVE)
    assert is_ok(result), "result-label mint failed"
    return result.value


def _cost(name: str, amount: int) -> CostComponent:
    result = CostComponent.try_create(name, _money(amount), "broker")
    assert is_ok(result), "cost-component mint failed"
    return result.value


def _mint(
    *,
    seed: str,
    epoch: Fingerprint,
    realized_pnl: int,
    close_reason: CloseReason,
    outcome: CloseOutcome,
    authority: ClosingAuthority,
    recorded_at: Instant,
    costs: tuple[CostComponent, ...] = (),
) -> Result[ExitRecord]:
    arb = None if authority is ClosingAuthority.VENUE else _fp(f"arb-{seed}")
    vobs = _fp(f"venue-{seed}") if authority is ClosingAuthority.VENUE else None
    return mint_exit_record(
        virtual_position_ref=_fp(seed),
        opening_bot_id="bot-alpha",
        original_risk_distance=_delta(50),
        original_risk_amount=_money(10000),
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
        recorded_at=recorded_at,
        arbitration_record_ref=arb,
        venue_observation_ref=vobs,
    )


def main() -> None:
    epoch = _fp("epoch-demo")
    q = _r(1)
    threshold = 2

    specs = (
        (
            "be",
            -50,
            CloseReason.PROTECTIVE_STOP_FILL,
            CloseOutcome.BREAKEVEN,
            ClosingAuthority.VENUE,
            (_cost("commission", 50),),
            1,
        ),
        (
            "scratch",
            -1500,
            CloseReason.BOT_INTENT,
            CloseOutcome.LOSS,
            ClosingAuthority.BOOK_POLICY,
            (),
            2,
        ),
        (
            "ql1",
            -10000,
            CloseReason.PROTECTIVE_STOP_FILL,
            CloseOutcome.LOSS,
            ClosingAuthority.VENUE,
            (_cost("commission", 200),),
            3,
        ),
        (
            "ql2",
            -12000,
            CloseReason.HOLD_TIME_FORCE_FLAT,
            CloseOutcome.LOSS,
            ClosingAuthority.BOOK_POLICY,
            (),
            4,
        ),
    )
    stream = ExitRecordStream()
    records: list[ExitRecord] = []
    for seed, pnl, reason, outcome, authority, costs, ns in specs:
        minted = _mint(
            seed=seed,
            epoch=epoch,
            realized_pnl=pnl,
            close_reason=reason,
            outcome=outcome,
            authority=authority,
            recorded_at=_instant(ns),
            costs=costs,
        )
        assert is_ok(minted), f"exit mint failed for {seed}"
        fp = stream.mint(minted.value)
        assert is_ok(fp), f"stream mint failed for {seed}"
        assert is_ok(stream.mark_persisted(fp.value)), "persist failed"
        assert is_ok(stream.mark_journaled(fp.value)), "journal failed"
        records.append(minted.value)

    ql1_r = records[2].realized_r()
    assert is_ok(ql1_r), "realized_r derivation failed"
    print(
        f"single-sourced realized_r for protective-stop full loss: "
        f"{ql1_r.value.as_fraction()} (expected -51/50)"
    )
    _require(ql1_r.value.as_fraction() == Fraction(-102, 100), "realized_r mismatch")

    attributed = attribute_whole_trade(records[3])
    assert is_ok(attributed), "attribution failed"
    print(
        f"whole-trade attribution credits opening bot={attributed.value.opening_bot_id} "
        f"close_reason={attributed.value.close_reason.value}"
    )
    partitioned = partition_by_close_reason(tuple(records))
    assert is_ok(partitioned), "partition failed"
    print(
        "reports partition by close reason: "
        + ", ".join(f"{k}={len(v)}" for k, v in sorted(partitioned.value.items()))
    )

    dispositions: list[BenchDisposition] = []
    for raw in (classify_bench_disposition(r, q=q) for r in records):
        assert is_ok(raw), "disposition classify failed"
        dispositions.append(raw.value)
    print("bench dispositions: " + ", ".join(d.value for d in dispositions))
    _require(
        dispositions[0] is BenchDisposition.BREAKEVEN
        and dispositions[1] is BenchDisposition.SCRATCH_OR_PARTIAL_LOSS
        and dispositions[2] is BenchDisposition.QUALIFYING_LOSS_EXIT
        and dispositions[3] is BenchDisposition.QUALIFYING_LOSS_EXIT,
        "unexpected dispositions",
    )

    folded = fold_bench(tuple(records), binding_epoch=epoch, q=q, threshold=threshold)
    assert is_ok(folded), "bench fold failed"
    print(
        f"bench fold: qualifying_loss_count={folded.value.qualifying_loss_count} "
        f"threshold={threshold} crossed={folded.value.threshold_crossed}"
    )
    _require(folded.value.qualifying_loss_count == 2, "expected two qualifying losses")
    _require(folded.value.threshold_crossed is True, "expected threshold crossed")

    # Recording precedes interpretation: an unrecorded close refuses.
    pending = _mint(
        seed="pending",
        epoch=epoch,
        realized_pnl=-10000,
        close_reason=CloseReason.BOT_INTENT,
        outcome=CloseOutcome.LOSS,
        authority=ClosingAuthority.BOOK_POLICY,
        recorded_at=_instant(5),
    )
    assert is_ok(pending), "pending mint failed"
    pending_fp = stream.mint(pending.value)
    assert is_ok(pending_fp), "pending stream mint failed"
    stale = stream.check_seat_may_mint_intent(
        closed_virtual_position_ref=pending.value.virtual_position_ref
    )
    assert is_refusal(stale)
    _require(stale.category is RefusalCategory.STALE_EVIDENCE, "expected stale")
    print(f"recording precedes interpretation: refused ({stale.category.value})")

    ratchet = check_move_to_breakeven_ratchet(
        original_risk_distance=_delta(50),
        proposed_risk_distance=_delta(0),
    )
    assert is_ok(ratchet), "breakeven ratchet should accept zero offset"
    widen = check_move_to_breakeven_ratchet(
        original_risk_distance=_delta(50),
        proposed_risk_distance=_delta(60),
    )
    assert is_refusal(widen), "widen must refuse"
    print(
        f"move-to-breakeven ratchet: zero-offset ok; widen refused "
        f"({widen.category.value}); R stays frozen so -1R keeps meaning a full original loss"
    )
    print(
        "kill_line_flat and protection_forced_flat are distinct taxonomy members: "
        f"{CloseReason.KILL_LINE_FLAT.value} / {CloseReason.PROTECTION_FORCED_FLAT.value}"
    )


if __name__ == "__main__":
    main()
