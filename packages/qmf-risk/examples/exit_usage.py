"""Reference usage — CT-29 exit records, attribution, and the bench fold (COMP-QMF-RISK).

Executable::

    python packages/qmf-risk/examples/exit_usage.py

Mints four SCN-0011-shaped exit records for one binding epoch, derives single-sourced
``realized_r`` from frozen fields, credits whole-trade attribution to the opening Bot,
folds the qualifying-loss bench (breakeven and scratch excluded), enforces
10→recording-precedes-interpretation, and shows the V1 move-to-breakeven ratchet.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TypeVar

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

T = TypeVar("T")


def _unwrap(result: Result[T], message: str) -> T:
    if is_ok(result):
        return result.value
    raise RuntimeError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _fp(seed: str) -> Fingerprint:
    return _unwrap(fingerprint({"seed": seed}), f"fingerprint failed for {seed!r}")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant mint failed")


def _money(value: int) -> Money:
    return _unwrap(Money.try_create(value, "USD", 2), "money mint failed")


def _delta(value: int) -> PriceDelta:
    instrument = Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")
    return _unwrap(PriceDelta.try_create(value, instrument, 5), "price-delta mint failed")


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    return _unwrap(
        ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE),
        "r-multiple mint failed",
    )


def _label() -> ExitResultLabel:
    return _unwrap(
        ExitResultLabel.try_create(AccountRole.LIVE, World.LIVE),
        "result-label mint failed",
    )


def _cost(name: str, amount: int) -> CostComponent:
    return _unwrap(
        CostComponent.try_create(name, _money(amount), "broker"),
        "cost-component mint failed",
    )


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
        minted = _unwrap(
            _mint(
                seed=seed,
                epoch=epoch,
                realized_pnl=pnl,
                close_reason=reason,
                outcome=outcome,
                authority=authority,
                recorded_at=_instant(ns),
                costs=costs,
            ),
            f"exit mint failed for {seed}",
        )
        fp = _unwrap(stream.mint(minted), f"stream mint failed for {seed}")
        _unwrap(stream.mark_persisted(fp), "persist failed")
        _unwrap(stream.mark_journaled(fp), "journal failed")
        records.append(minted)

    ql1_r = _unwrap(records[2].realized_r(), "realized_r derivation failed")
    print(
        f"single-sourced realized_r for protective-stop full loss: "
        f"{ql1_r.as_fraction()} (expected -51/50)"
    )
    _require(ql1_r.as_fraction() == Fraction(-102, 100), "realized_r mismatch")

    attributed = _unwrap(attribute_whole_trade(records[3]), "attribution failed")
    print(
        f"whole-trade attribution credits opening bot={attributed.opening_bot_id} "
        f"close_reason={attributed.close_reason.value}"
    )
    partitioned = _unwrap(partition_by_close_reason(tuple(records)), "partition failed")
    print(
        "reports partition by close reason: "
        + ", ".join(f"{k}={len(v)}" for k, v in sorted(partitioned.items()))
    )

    dispositions: list[BenchDisposition] = []
    for raw in (classify_bench_disposition(r, q=q) for r in records):
        dispositions.append(_unwrap(raw, "disposition classify failed"))
    print("bench dispositions: " + ", ".join(d.value for d in dispositions))
    _require(
        dispositions[0] is BenchDisposition.BREAKEVEN
        and dispositions[1] is BenchDisposition.SCRATCH_OR_PARTIAL_LOSS
        and dispositions[2] is BenchDisposition.QUALIFYING_LOSS_EXIT
        and dispositions[3] is BenchDisposition.QUALIFYING_LOSS_EXIT,
        "unexpected dispositions",
    )

    folded = _unwrap(
        fold_bench(tuple(records), binding_epoch=epoch, q=q, threshold=threshold),
        "bench fold failed",
    )
    print(
        f"bench fold: qualifying_loss_count={folded.qualifying_loss_count} "
        f"threshold={threshold} crossed={folded.threshold_crossed}"
    )
    _require(folded.qualifying_loss_count == 2, "expected two qualifying losses")
    _require(folded.threshold_crossed is True, "expected threshold crossed")

    # Recording precedes interpretation: an unrecorded close refuses.
    pending = _unwrap(
        _mint(
            seed="pending",
            epoch=epoch,
            realized_pnl=-10000,
            close_reason=CloseReason.BOT_INTENT,
            outcome=CloseOutcome.LOSS,
            authority=ClosingAuthority.BOOK_POLICY,
            recorded_at=_instant(5),
        ),
        "pending mint failed",
    )
    _unwrap(stream.mint(pending), "pending stream mint failed")
    stale = stream.check_seat_may_mint_intent(
        closed_virtual_position_ref=pending.virtual_position_ref
    )
    if not is_refusal(stale):
        raise RuntimeError("expected refusal for unrecorded close")
    _require(stale.category is RefusalCategory.STALE_EVIDENCE, "expected stale")
    print(f"recording precedes interpretation: refused ({stale.category.value})")

    _unwrap(
        check_move_to_breakeven_ratchet(
            original_risk_distance=_delta(50),
            proposed_risk_distance=_delta(0),
        ),
        "breakeven ratchet should accept zero offset",
    )
    widen = check_move_to_breakeven_ratchet(
        original_risk_distance=_delta(50),
        proposed_risk_distance=_delta(60),
    )
    if not is_refusal(widen):
        raise RuntimeError("widen must refuse")
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
