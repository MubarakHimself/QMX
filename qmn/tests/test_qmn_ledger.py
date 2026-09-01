"""Story 26.4 — exact virtual positions and the per-binding ledger (TN-25)."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Fingerprint,
    Instant,
    Instrument,
    Money,
    PriceDelta,
    Quantity,
    RefusalCategory,
    VenueId,
    fingerprint,
)
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.binding import StateCarry, StateCarryChoice, StateCarryCounter
from qmf.risk.r_faces import RFaces
from qmn.ledger import (
    ADMISSION_PLAN_EDGE,
    EPOCH_STATE_CARRY_COUNTERS,
    EXECUTION_QUALITY_SHORT_FILL,
    LEDGER_SURFACE,
    POSITION_KIND_VENUE,
    POSITION_KIND_VIRTUAL,
    TREASURY_BOUNDARY_KINDS,
    AttributedFill,
    AttributionDeclaration,
    BindingVirtualLedger,
    PositionKind,
    PositionModelKind,
    TreasuryBoundaryActKind,
    TreasuryBoundaryJournal,
    VenuePositionFold,
    VirtualPositionStatus,
    apply_treasury_boundary,
    fold_venue_observation,
    guard_no_scale_in,
    journal_missed_rollover_correction,
    mint_treasury_boundary_act,
    mint_virtual_position,
    prove_attribution_partition,
    rebase_partial_entry,
    reconcile_virtual_to_venue_quantity,
    refuse_boundary_rebase_of_r,
    refuse_float_money,
    refuse_paper_pnl_to_treasury,
    refuse_top_up_short_fill,
    require_epoch_state_carry,
    seed_binding_ledger,
    validate_state_carry_declaration,
)

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(seed: str) -> Fingerprint:
    return _ok(fingerprint({"seed": seed}))


def _instant(ns: int = 1_000_000_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _money(value: int, scale: int = 2) -> Money:
    return _ok(Money.try_create(value, "USD", scale))


def _qty(value: int, scale: int = 0) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


def _instrument() -> Instrument:
    return Instrument(venue=_ok(VenueId.try_create("ctrader")), symbol="EURUSD")


def _faces(amount: int = 10_000, distance: int = 50) -> RFaces:
    delta = _ok(PriceDelta.try_create(distance, _instrument(), 5))
    return _ok(RFaces.try_create(delta, _money(amount)))


def _seed_ledger(epoch: Fingerprint | None = None, seed: int = 100_000) -> BindingVirtualLedger:
    return _ok(
        seed_binding_ledger(
            binding_epoch=epoch or _fp("binding-epoch-1"),
            seed=_money(seed),
            recorded_at=_instant(),
            money_scale=2,
        )
    )


# --- surface ------------------------------------------------------------------


def test_ledger_surface_name() -> None:
    assert LEDGER_SURFACE == "qmn.ledger"
    assert PositionKind.VIRTUAL.value == POSITION_KIND_VIRTUAL
    assert PositionKind.VENUE.value == POSITION_KIND_VENUE
    assert set(EPOCH_STATE_CARRY_COUNTERS) == {
        "ledger",
        "cycle",
        "budget",
        "bench_counter",
        "exposure",
    }
    assert {k.value for k in TREASURY_BOUNDARY_KINDS} == {
        "sweep",
        "refund",
        "re_seed",
        "paper_epoch_reset",
        "accounting_rollover",
    }


# --- AC1: fold fill into binding ledger + virtual position; no-scale-in -------


def test_fold_fill_appends_binding_ledger_and_virtual_position() -> None:
    ledger = _seed_ledger()
    faces = _faces()
    admission = _fp("admission-1")
    command = _fp("command-1")
    fill = AttributedFill(
        command_identity=command,
        venue_native_id="deal-1",
        instrument="EURUSD",
        quantity=_qty(1),
        realized_cash=None,
        recorded_at=_instant(2),
    )
    folded = _ok(
        ledger.fold_fill(
            fill=fill,
            bot_id="bot-a",
            admission_identity=admission,
            faces=faces,
            admitted_quantity=_qty(1),
        )
    )
    assert folded.created is True
    assert folded.position.position_kind is PositionKind.VIRTUAL
    assert folded.position.admission_identity == admission
    assert folded.position.faces == faces
    assert folded.position.admission_faces == faces
    assert folded.position.status is VirtualPositionStatus.OPEN
    assert folded.record.command_identity == command
    assert folded.record.money_scale == 2
    assert ledger.has_open_virtual("EURUSD")
    assert len(ledger.records) == 2  # seed + fill


def test_no_scale_in_refuses_second_entry_on_open_virtual() -> None:
    ledger = _seed_ledger()
    faces = _faces()
    first = AttributedFill(
        command_identity=_fp("cmd-1"),
        venue_native_id="deal-1",
        instrument="EURUSD",
        quantity=_qty(1),
        realized_cash=None,
        recorded_at=_instant(2),
    )
    _ok(
        ledger.fold_fill(
            fill=first,
            bot_id="bot-a",
            admission_identity=_fp("adm-1"),
            faces=faces,
            admitted_quantity=_qty(1),
        )
    )
    blocked = _refusal(ledger.refuse_entry_if_open("EURUSD"))
    assert blocked.category is RefusalCategory.POLICY_REJECTION

    second = AttributedFill(
        command_identity=_fp("cmd-2"),
        venue_native_id="deal-2",
        instrument="EURUSD",
        quantity=_qty(1),
        realized_cash=None,
        recorded_at=_instant(3),
    )
    refused = _refusal(
        ledger.fold_fill(
            fill=second,
            bot_id="bot-a",
            admission_identity=_fp("adm-2"),
            faces=faces,
            admitted_quantity=_qty(1),
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert is_ok(guard_no_scale_in(has_open_virtual_position=False))
    assert _refusal(guard_no_scale_in(has_open_virtual_position=True)).category is (
        RefusalCategory.POLICY_REJECTION
    )


def test_venue_position_fold_is_separate_from_virtual() -> None:
    fold = VenuePositionFold()
    venue = _ok(
        fold_venue_observation(
            fold,
            account_id="acct-1",
            instrument="EURUSD",
            quantity=_qty(2),
            position_model="netting",
            observed_at=_instant(),
        )
    )
    assert venue.position_kind is PositionKind.VENUE
    assert fold.get("acct-1", "EURUSD") is venue
    # Virtual ledger never stores venue positions.
    ledger = _seed_ledger()
    assert ledger.position_for("EURUSD") is None


def test_refuse_float_on_money_path() -> None:
    refused = _refusal(refuse_float_money(1.5))
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert is_ok(refuse_float_money(_money(100)))
    seed_refused = _refusal(
        seed_binding_ledger(
            binding_epoch=_fp("e"),
            seed=12.34,  # type: ignore[arg-type]
            recorded_at=_instant(),
        )
    )
    assert seed_refused.category is RefusalCategory.INVALID_INPUT


# --- AC2: partial ENTRY re-base exactly once ---------------------------------


def test_partial_entry_rebases_amount_once_keeps_admission_plan() -> None:
    faces = _faces(amount=10_000)  # 100.00 USD at scale 2
    position = _ok(
        mint_virtual_position(
            binding_epoch=_fp("epoch"),
            instrument="EURUSD",
            bot_id="bot-a",
            admission_identity=_fp("adm"),
            command_identity=_fp("cmd"),
            faces=faces,
            admitted_quantity=_qty(2),
            filled_quantity=_qty(1),
            status=VirtualPositionStatus.PENDING_ENTRY,
        )
    )
    updated, outcome = _ok(
        rebase_partial_entry(position, filled_quantity=_qty(1), terminal=True)
    )
    assert updated.rebased is True
    assert updated.admission_faces == faces
    assert updated.admission_plan_edge == ADMISSION_PLAN_EDGE
    assert outcome.admission_plan_edge == ADMISSION_PLAN_EDGE
    # 10000 * 1/2 = 5000 exactly at scale 2
    assert updated.faces.original_risk_amount == _money(5_000)
    assert updated.faces.original_risk_distance == faces.original_risk_distance
    assert outcome.execution_quality.kind == EXECUTION_QUALITY_SHORT_FILL
    assert outcome.execution_quality.shortfall == _qty(1)
    assert "admission_faces" in outcome.lineage_content

    second = _refusal(rebase_partial_entry(updated, filled_quantity=_qty(1), terminal=True))
    assert second.category is RefusalCategory.POLICY_REJECTION

    top_up = _refusal(refuse_top_up_short_fill(attempt_top_up=True))
    assert top_up.category is RefusalCategory.POLICY_REJECTION
    assert is_ok(refuse_top_up_short_fill(attempt_top_up=False))


def test_fold_fill_rebases_on_entry_terminal_partial() -> None:
    ledger = _seed_ledger()
    faces = _faces(amount=10_000)
    fill = AttributedFill(
        command_identity=_fp("cmd"),
        venue_native_id="deal",
        instrument="EURUSD",
        quantity=_qty(1),
        realized_cash=None,
        recorded_at=_instant(2),
    )
    folded = _ok(
        ledger.fold_fill(
            fill=fill,
            bot_id="bot-a",
            admission_identity=_fp("adm"),
            faces=faces,
            admitted_quantity=_qty(2),
            entry_terminal=True,
        )
    )
    assert folded.position.rebased is True
    assert folded.position.faces.original_risk_amount == _money(5_000)
    assert folded.position.admission_faces.original_risk_amount == _money(10_000)


def test_full_fill_and_non_terminal_refuse_rebase() -> None:
    faces = _faces()
    position = _ok(
        mint_virtual_position(
            binding_epoch=_fp("epoch"),
            instrument="EURUSD",
            bot_id="bot-a",
            admission_identity=_fp("adm"),
            command_identity=_fp("cmd"),
            faces=faces,
            admitted_quantity=_qty(1),
            filled_quantity=_qty(1),
        )
    )
    assert _refusal(
        rebase_partial_entry(position, filled_quantity=_qty(1), terminal=True)
    ).category is RefusalCategory.INVALID_INPUT
    assert _refusal(
        rebase_partial_entry(position, filled_quantity=_qty(1), terminal=False)
    ).category is RefusalCategory.INVALID_INPUT


# --- AC3: netting attribution partition + virtual/venue quantity reconcile ---


def test_netting_attribution_partition_exhaustive_disjoint() -> None:
    missing = _refusal(
        prove_attribution_partition(
            account_key="v::a",
            position_model=PositionModelKind.NETTING,
            declarations=(
                AttributionDeclaration(
                    binding_id="b1",
                    instruments=frozenset({"EURUSD"}),
                    attribution_instruments=None,
                ),
            ),
        )
    )
    assert missing.category is RefusalCategory.POLICY_REJECTION

    overlap = _refusal(
        prove_attribution_partition(
            account_key="v::a",
            position_model="netting",
            declarations=(
                AttributionDeclaration(
                    binding_id="b1",
                    instruments=frozenset({"EURUSD", "GBPUSD"}),
                    attribution_instruments=frozenset({"EURUSD"}),
                    shared_flatten_signature="sig",
                ),
                AttributionDeclaration(
                    binding_id="b2",
                    instruments=frozenset({"EURUSD", "USDJPY"}),
                    attribution_instruments=frozenset({"EURUSD"}),
                    shared_flatten_signature="sig",
                ),
            ),
        )
    )
    assert overlap.category is RefusalCategory.INVALID_INPUT
    assert "disjoint" in str(overlap.context["reason"])

    gap = _refusal(
        prove_attribution_partition(
            account_key="v::a",
            position_model="netting",
            declarations=(
                AttributionDeclaration(
                    binding_id="b1",
                    instruments=frozenset({"EURUSD", "GBPUSD"}),
                    attribution_instruments=frozenset({"EURUSD"}),
                ),
            ),
        )
    )
    assert gap.category is RefusalCategory.INVALID_INPUT
    assert "exhaustive" in str(gap.context["reason"])

    no_sig = _refusal(
        prove_attribution_partition(
            account_key="v::a",
            position_model="netting",
            declarations=(
                AttributionDeclaration(
                    binding_id="b1",
                    instruments=frozenset({"EURUSD", "GBPUSD"}),
                    attribution_instruments=frozenset({"EURUSD"}),
                ),
                AttributionDeclaration(
                    binding_id="b2",
                    instruments=frozenset({"EURUSD", "USDJPY"}),
                    attribution_instruments=frozenset({"USDJPY"}),
                ),
            ),
        )
    )
    assert no_sig.category is RefusalCategory.UNSUPPORTED_CAPABILITY

    ok = _ok(
        prove_attribution_partition(
            account_key="v::a",
            position_model="netting",
            declarations=(
                AttributionDeclaration(
                    binding_id="b1",
                    instruments=frozenset({"EURUSD"}),
                    attribution_instruments=frozenset({"EURUSD"}),
                    shared_flatten_signature="sig",
                ),
                AttributionDeclaration(
                    binding_id="b2",
                    instruments=frozenset({"GBPUSD"}),
                    attribution_instruments=frozenset({"GBPUSD"}),
                    shared_flatten_signature="sig",
                ),
            ),
        )
    )
    assert ok.covered == frozenset({"EURUSD", "GBPUSD"})


def test_virtual_quantity_sum_reconciles_to_venue() -> None:
    epoch_a = _fp("epoch-a")
    epoch_b = _fp("epoch-b")
    ledger_a = _seed_ledger(epoch_a)
    ledger_b = _seed_ledger(epoch_b)
    faces = _faces()
    for ledger, cmd in ((ledger_a, "c1"), (ledger_b, "c2")):
        _ok(
            ledger.fold_fill(
                fill=AttributedFill(
                    command_identity=_fp(cmd),
                    venue_native_id=cmd,
                    instrument="EURUSD",
                    quantity=_qty(1),
                    realized_cash=None,
                    recorded_at=_instant(2),
                ),
                bot_id="bot",
                admission_identity=_fp(f"adm-{cmd}"),
                faces=faces,
                admitted_quantity=_qty(1),
            )
        )
    fold = VenuePositionFold()
    venue = _ok(
        fold_venue_observation(
            fold,
            account_id="acct",
            instrument="EURUSD",
            quantity=_qty(2),
            position_model="netting",
            observed_at=_instant(3),
        )
    )
    result = _ok(
        reconcile_virtual_to_venue_quantity(
            ledgers=(ledger_a, ledger_b),
            venue_position=venue,
        )
    )
    assert result.reconciled is True
    assert result.virtual_quantity == _qty(2)
    assert result.residual.as_fraction() == 0


# --- AC4: treasury boundary acts ---------------------------------------------


def test_treasury_boundary_never_touches_positions_or_r() -> None:
    ledger = _seed_ledger()
    faces = _faces()
    _ok(
        ledger.fold_fill(
            fill=AttributedFill(
                command_identity=_fp("cmd"),
                venue_native_id="d1",
                instrument="EURUSD",
                quantity=_qty(1),
                realized_cash=None,
                recorded_at=_instant(2),
            ),
            bot_id="bot",
            admission_identity=_fp("adm"),
            faces=faces,
            admitted_quantity=_qty(1),
        )
    )
    open_pos = ledger.position_for("EURUSD")
    assert open_pos is not None
    journal = TreasuryBoundaryJournal(binding_epoch=ledger.binding_epoch)
    act = _ok(
        mint_treasury_boundary_act(
            kind=TreasuryBoundaryActKind.SWEEP,
            binding_epoch=ledger.binding_epoch,
            cash_delta=_money(-1_000),
            operator_signature="operator-sig",
            dated_at=_instant(3),
        )
    )
    assert act.touches_positions is False
    assert act.rebases_frozen_r is False
    applied = _ok(
        apply_treasury_boundary(
            ledger=ledger,
            journal=journal,
            act=act,
            open_faces=(open_pos.faces,),
        )
    )
    assert applied.kind is TreasuryBoundaryActKind.SWEEP
    after = ledger.position_for("EURUSD")
    assert after is not None
    assert after.position_ref == open_pos.position_ref
    assert after.faces == open_pos.faces
    assert ledger.book_capital() == _money(99_000)
    assert is_ok(refuse_boundary_rebase_of_r(faces_before=faces, faces_after=faces))
    mutated = _faces(amount=9_000)
    assert _refusal(
        refuse_boundary_rebase_of_r(faces_before=faces, faces_after=mutated)
    ).category is RefusalCategory.POLICY_REJECTION


def test_missed_rollover_reconstructed_as_correction() -> None:
    ledger = _seed_ledger()
    journal = TreasuryBoundaryJournal(binding_epoch=ledger.binding_epoch)
    intended = _ok(
        mint_treasury_boundary_act(
            kind=TreasuryBoundaryActKind.ACCOUNTING_ROLLOVER,
            binding_epoch=ledger.binding_epoch,
            cash_delta=_money(0),
            operator_signature="op",
            dated_at=_instant(2),
        )
    )
    correction = _ok(
        journal_missed_rollover_correction(
            journal=journal,
            ledger=ledger,
            missed_act=intended,
            operator_signature="op-catchup",
            dated_at=_instant(3),
        )
    )
    assert correction.is_correction is True
    assert correction.corrects == intended.act_fingerprint
    assert len(journal.acts) == 1


def test_paper_pnl_never_becomes_treasury_cash() -> None:
    refused = refuse_paper_pnl_to_treasury(_money(500))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


# --- AC5: state_carry at epoch transition ------------------------------------


def test_state_carry_absence_and_carry_requires_signed_edge() -> None:
    absent = _refusal(validate_state_carry_declaration(None))
    assert absent.category is RefusalCategory.INVALID_INPUT

    partial = _refusal(validate_state_carry_declaration({"ledger": "reset"}))
    assert partial.category is RefusalCategory.INVALID_INPUT

    all_reset = {
        "ledger": "reset",
        "cycle": "reset",
        "budget": "reset",
        "bench_counter": "reset",
        "exposure": "reset",
    }
    ok_reset = _ok(require_epoch_state_carry(state_carry=all_reset))
    assert ok_reset.carried_counters() == frozenset()
    assert ok_reset.continues_performance_signature is None

    carrying = {**all_reset, "ledger": "carry", "budget": "carry"}
    no_edge = _refusal(require_epoch_state_carry(state_carry=carrying))
    assert no_edge.category is RefusalCategory.INVALID_INPUT
    assert no_edge.context["field"] == "carries_ledger_signature"

    # continues-performance alone never gates carry.
    still_no = _refusal(
        require_epoch_state_carry(
            state_carry=carrying,
            continues_performance_signature="perf-sig",
        )
    )
    assert still_no.category is RefusalCategory.INVALID_INPUT

    with_edge = _ok(
        require_epoch_state_carry(
            state_carry=carrying,
            carries_ledger_signature="ledger-sig",
            continues_performance_signature="perf-sig",
        )
    )
    assert with_edge.carried_counters() == frozenset({"ledger", "budget"})
    assert with_edge.carries_ledger_signature == "ledger-sig"
    assert with_edge.continues_performance_signature == "perf-sig"

    # StateCarry value object also accepted.
    sc = _ok(
        StateCarry.try_create(
            dict.fromkeys(StateCarryCounter, StateCarryChoice.RESET)
        )
    )
    assert is_ok(require_epoch_state_carry(state_carry=sc))
