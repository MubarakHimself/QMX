"""Story 26.12 / QMX-F068 — frozen R on the actual Book door path."""

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
    Ok,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    SinkAck,
    SinkResult,
    UnitKind,
    ValueFactor,
    VenueId,
    World,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.door import (
    CitedEvidence,
    Direction,
    EntryIntent,
    EvidenceSlot,
    ExitLogicRef,
    ReasonCode,
    refuse_no_full_loss_price,
)
from qmf.risk.exit_record import (
    CloseOutcome,
    CloseReason,
    ClosingAuthority,
    CostComponent,
    ExitResultLabel,
    realized_r_of,
)
from qmf.risk.paper import ExecutionTarget
from qmn.order import (
    BOT_SIZE_FIELDS,
    PARTIAL_ENTRY_REBASE_JOURNAL_KIND,
    POSITION_RISK_AMOUNT_FORMULA_ID,
    AuthorizedIntent,
    PartialEntryRebaseJournal,
    PostAdmissionKind,
    admit_entry_at_book_door,
    check_door_dimensional_units,
    journal_terminal_partial_entry_rebase,
    mint_ct29_from_frozen_r,
    mint_place_order_from_authorized,
    mint_virtual_from_authorized,
    preserve_frozen_r,
    refuse_command_mint_without_frozen_r,
    reject_bot_supplied_final_size,
)
from qmn.venue import CommandKind, OrderType

T = TypeVar("T")

_VENUE = VenueId(value="ctrader")
_SESSION = "session-door-26-12"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _instrument() -> Instrument:
    return Instrument(venue=_VENUE, symbol="EURUSD")


def _price(value: int) -> Price:
    return _ok(Price.try_create(value, _instrument(), 5))


def _delta(value: int) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), 5))


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE))


def _rate(numerator: int, denominator: int = 1) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, denominator, UnitKind.RATE))


def _qty(value: int, scale: int = 0) -> Quantity:
    return _ok(Quantity.try_create(value, "lot", scale))


def _value_factor() -> ValueFactor:
    return _ok(ValueFactor.try_create(100_000, 1, _instrument(), "USD"))


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _fp(seed: str) -> Fingerprint:
    return _ok(fingerprint({"seed": seed}))


def _account() -> Account:
    return _ok(Account.try_create("acct-1", _VENUE, AccountRole.LIVE))


def _execution_target() -> ExecutionTarget:
    return _ok(ExecutionTarget.try_create("live", _VENUE, "acct-1"))


def _reason() -> ReasonCode:
    return _ok(ReasonCode.try_create("momentum-break", "scalper-v1"))


def _cited() -> CitedEvidence:
    slot = _ok(EvidenceSlot.try_create("sqs", "sqs-ref-1", _instant()))
    return _ok(CitedEvidence.try_create(sqs_reading=slot))


def _entry(*, proposed_r: ExactRational | None = None) -> EntryIntent:
    return _ok(
        EntryIntent.try_create(
            _instrument(),
            Direction.LONG,
            _reason(),
            _execution_target(),
            proposed_r=proposed_r,
            cited_evidence=_cited(),
        )
    )


def _exit_logic_ref() -> ExitLogicRef:
    return _ok(ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}))


class _OffsetStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        del cited_evidence
        if direction is Direction.LONG:
            value = entry_price.value - 1_000
        else:
            value = entry_price.value + 1_000
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class _NoStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        del entry_price, direction, cited_evidence
        return refuse_no_full_loss_price(module="no-stop")


class RecordingSink:
    def __init__(self) -> None:
        self.events: list[object] = []

    def append(self, event: object, /) -> SinkResult:
        self.events.append(event)
        return Ok(SinkAck())


def _admit(**overrides: object) -> AuthorizedIntent:
    kwargs: dict[str, object] = {
        "intent": _entry(proposed_r=_r(1)),
        "entry_price": _price(110_000),
        "exit_logic_ref": _exit_logic_ref(),
        "module": _OffsetStopModule(),
        "book_resolved_requested_r": _r(1),
        "r_unit_price": _rate(1_000),
        "value_factor": _value_factor(),
        "money_scale": 2,
    }
    kwargs.update(overrides)
    return _ok(admit_entry_at_book_door(**kwargs))


def _position(authorized: AuthorizedIntent | None = None, filled: Quantity | None = None):
    auth = authorized or _admit()
    return _ok(
        mint_virtual_from_authorized(
            auth,
            binding_epoch=_fp("epoch"),
            bot_id="bot-a",
            command_identity=_fp("cmd"),
            filled_quantity=filled,
        )
    )


# --- AC1: Book door freezes R before command mint; bot never sizes ----------


def test_bot_size_fields_are_closed() -> None:
    assert "requested_r" in BOT_SIZE_FIELDS
    assert "quantity" in BOT_SIZE_FIELDS
    assert POSITION_RISK_AMOUNT_FORMULA_ID == "FORM-position-risk-amount"


def test_inbound_requested_r_and_quantity_refused() -> None:
    sized = _refusal(reject_bot_supplied_final_size({"requested_r": _r(2)}))
    assert sized.category is RefusalCategory.INVALID_INPUT
    assert sized.context["field"] == "requested_r"
    qty = _refusal(reject_bot_supplied_final_size({"quantity": _qty(3)}))
    assert qty.context["field"] == "quantity"


def test_admit_freezes_three_faces_and_book_resolves_requested_r() -> None:
    authorized = _admit()
    assert authorized.requested_r == _r(1)
    assert authorized.admitted.declared_full_loss_price == _price(109_000)
    assert authorized.faces.original_risk_distance == _delta(1_000)
    assert authorized.original_risk_amount == _ok(Money.try_create(100_000, "USD", 2))
    assert authorized.faces.original_risk_amount == authorized.original_risk_amount
    assert authorized.admitted_quantity == _qty(1)
    assert not hasattr(authorized.admitted, "bot_quantity")


def test_full_loss_absent_refuses_before_command_mint() -> None:
    refused = _refusal(
        admit_entry_at_book_door(
            intent=_entry(),
            entry_price=_price(110_000),
            exit_logic_ref=_exit_logic_ref(),
            module=_NoStopModule(),
            book_resolved_requested_r=_r(1),
            r_unit_price=_rate(1_000),
            value_factor=_value_factor(),
            money_scale=2,
        )
    )
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "declared_full_loss_price"


def test_dimensional_unit_mismatch_refuses() -> None:
    count = _ok(ExactRational.try_create(1, 1, UnitKind.COUNT))
    refused = _refusal(check_door_dimensional_units(requested_r=count, r_unit_price=_rate(1_000)))
    assert refused.category is RefusalCategory.INVALID_INPUT
    money_rate = _refusal(check_door_dimensional_units(requested_r=_r(1), r_unit_price=_r(1_000)))
    assert money_rate.context["field"] == "r_unit_price"


def test_inbound_mapping_with_bot_size_never_reaches_mint() -> None:
    refused = _refusal(
        admit_entry_at_book_door(
            intent={
                "intent_family": "entry",
                "entry": _entry(),
                "quantity": _qty(9),
            },
            entry_price=_price(110_000),
            exit_logic_ref=_exit_logic_ref(),
            module=_OffsetStopModule(),
            book_resolved_requested_r=_r(1),
            r_unit_price=_rate(1_000),
            value_factor=_value_factor(),
            money_scale=2,
        )
    )
    assert refused.context["field"] == "quantity"


def test_scale_in_refuses_at_door() -> None:
    refused = _refusal(
        admit_entry_at_book_door(
            intent=_entry(),
            entry_price=_price(110_000),
            exit_logic_ref=_exit_logic_ref(),
            module=_OffsetStopModule(),
            book_resolved_requested_r=_r(1),
            r_unit_price=_rate(1_000),
            value_factor=_value_factor(),
            money_scale=2,
            has_open_virtual_position=True,
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_place_order_quantity_is_book_derived_not_bot() -> None:
    authorized = _admit()
    command = _ok(
        mint_place_order_from_authorized(
            authorized,
            venue_id=_VENUE,
            account=_account(),
            session_epoch=_SESSION,
            ordering_ordinal=1,
        )
    )
    assert command.kind is CommandKind.PLACE_ORDER
    assert command.order_parameters is not None
    assert command.order_parameters.quantity == authorized.admitted_quantity
    assert command.order_parameters.order_type is OrderType.MARKET
    assert (
        command.order_parameters.protective_stop_distance == authorized.faces.original_risk_distance
    )
    bot_qty = _refusal(
        mint_place_order_from_authorized(
            authorized,
            venue_id=_VENUE,
            account=_account(),
            session_epoch=_SESSION,
            ordering_ordinal=2,
            bot_quantity=_qty(99),
        )
    )
    assert bot_qty.context["field"] == "quantity"


def test_command_mint_without_frozen_r_refuses() -> None:
    refused = refuse_command_mint_without_frozen_r(_entry())
    assert refused.category is RefusalCategory.INVALID_INPUT
    mint = _refusal(
        mint_place_order_from_authorized(
            _entry(),
            venue_id=_VENUE,
            account=_account(),
            session_epoch=_SESSION,
            ordering_ordinal=1,
        )
    )
    assert mint.context["field"] == "authorized"


# --- AC2: frozen R survives post-admission events except one rebase ----------


def test_partial_entry_rebase_is_journaled_and_idempotent() -> None:
    fat = _admit(book_resolved_requested_r=_r(2), r_unit_price=_rate(1_000))
    assert fat.admitted_quantity == _qty(2)
    position = _position(fat, filled=_qty(1))
    sink = RecordingSink()
    journal = PartialEntryRebaseJournal(sink=sink)
    first = _ok(
        journal_terminal_partial_entry_rebase(
            position,
            filled_quantity=_qty(1),
            journal=journal,
            journaled_at=_instant(),
        )
    )
    updated, outcome, record = first
    assert updated.rebased is True
    assert record.kind == PARTIAL_ENTRY_REBASE_JOURNAL_KIND
    assert len(sink.events) == 1
    assert updated.faces.original_risk_distance == fat.faces.original_risk_distance
    assert updated.admission_faces.original_risk_amount == fat.faces.original_risk_amount
    assert updated.faces.original_risk_amount == _ok(Money.try_create(100_000, "USD", 2))
    assert outcome.admission_plan_edge == "admission-plan"

    second = _ok(
        journal_terminal_partial_entry_rebase(
            updated,
            filled_quantity=_qty(1),
            journal=journal,
            journaled_at=_instant(2),
        )
    )
    assert second[0].faces.fp1_identity() == updated.faces.fp1_identity()
    assert len(journal.records) == 1
    assert len(sink.events) == 1


def test_second_distinct_rebase_refused() -> None:
    fat = _admit(book_resolved_requested_r=_r(2), r_unit_price=_rate(1_000))
    position = _position(fat, filled=_qty(1))
    journal = PartialEntryRebaseJournal()
    updated, _, _ = _ok(
        journal_terminal_partial_entry_rebase(
            position,
            filled_quantity=_qty(1),
            journal=journal,
            journaled_at=_instant(),
        )
    )
    refused = _refusal(
        journal_terminal_partial_entry_rebase(
            updated,
            filled_quantity=_qty(2),
            journal=journal,
            journaled_at=_instant(),
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_fills_amendments_rollover_config_treasury_do_not_rebase_r() -> None:
    position = _position()
    frozen = position.faces.fp1_identity()
    fill = _ok(preserve_frozen_r(position, kind=PostAdmissionKind.FILL))
    assert fill.rebased is False
    assert fill.faces.fp1_identity() == frozen

    amend = _ok(
        preserve_frozen_r(
            position,
            kind="protection-amendment",
            proposed_stop_distance=_delta(500),
        )
    )
    assert amend.faces.fp1_identity() == frozen

    for kind in (
        PostAdmissionKind.ROLLOVER,
        PostAdmissionKind.CONFIGURATION_CHANGE,
        PostAdmissionKind.TREASURY_ACT,
    ):
        kept = _ok(preserve_frozen_r(position, kind=kind))
        assert kept.rebased is False
        assert kept.faces.fp1_identity() == frozen


def test_preserve_partial_entry_fill_journals_the_rebase() -> None:
    fat = _admit(book_resolved_requested_r=_r(2), r_unit_price=_rate(1_000))
    position = _position(fat, filled=_qty(1))
    sink = RecordingSink()
    journal = PartialEntryRebaseJournal(sink=sink)
    kept = _ok(
        preserve_frozen_r(
            position,
            kind=PostAdmissionKind.PARTIAL_ENTRY_FILL,
            filled_quantity=_qty(1),
            journal=journal,
            journaled_at=_instant(),
        )
    )
    assert kept.rebased is True
    assert kept.journaled is True
    assert kept.faces.original_risk_distance == fat.faces.original_risk_distance
    assert len(sink.events) == 1
    again = _ok(
        preserve_frozen_r(
            kept.position,
            kind=PostAdmissionKind.PARTIAL_ENTRY_FILL,
            filled_quantity=_qty(1),
            journal=journal,
            journaled_at=_instant(3),
        )
    )
    assert again.faces.fp1_identity() == kept.faces.fp1_identity()
    assert len(sink.events) == 1


def test_widen_stop_refused_and_leaves_frozen_r() -> None:
    position = _position()
    refused = _refusal(
        preserve_frozen_r(
            position,
            kind=PostAdmissionKind.PROTECTION_AMENDMENT,
            proposed_stop_distance=_delta(2_000),
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert position.faces.original_risk_distance == _delta(1_000)


def test_ct29_realized_r_recomputes_from_persisted_original_risk() -> None:
    fat = _admit(book_resolved_requested_r=_r(2), r_unit_price=_rate(1_000))
    position = _position(fat, filled=_qty(1))
    journal = PartialEntryRebaseJournal()
    updated, _, _ = _ok(
        journal_terminal_partial_entry_rebase(
            position,
            filled_quantity=_qty(1),
            journal=journal,
            journaled_at=_instant(),
        )
    )
    label = _ok(ExitResultLabel.try_create(AccountRole.LIVE, World.LIVE))
    cost = _ok(CostComponent.try_create("commission", _ok(Money.try_create(0, "USD", 2)), "broker"))
    # Full original loss on the rebased amount: -1000.00 against 1000.00 → -1R.
    record = _ok(
        mint_ct29_from_frozen_r(
            updated,
            realized_pnl=_ok(Money.try_create(-100_000, "USD", 2)),
            fill_references=(_fp("fill-1"),),
            cost_components=(cost,),
            close_reason=CloseReason.PROTECTIVE_STOP_FILL,
            mechanism=CloseReason.PROTECTIVE_STOP_FILL,
            outcome=CloseOutcome.LOSS,
            closing_authority=ClosingAuthority.BOOK_POLICY,
            close_reason_mapping_version=1,
            result_label=label,
            loss_predicate_format_version=1,
            recorded_at=_instant(),
            arbitration_record_ref=_fp("arb-1"),
        )
    )
    realized = _ok(realized_r_of(record))
    from_faces = _ok(updated.faces.r_multiple_of(_ok(Money.try_create(-100_000, "USD", 2))))
    assert realized.fp1_identity() == from_faces.fp1_identity()
    assert realized.as_fraction() == _r(-1).as_fraction()
    assert record.original_risk_amount == updated.faces.original_risk_amount
    assert record.original_risk_distance == updated.admission_faces.original_risk_distance
