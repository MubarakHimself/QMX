"""Story 10.6 — the CT-23 risk-evaluation door (Book-resolved sizing, risk-monotonic intents).

Verifies the one inbound bot-to-Book door: exactly two typed intent families plus
declared evidence slots and nothing else, an inbound requested_r an invalid-input refusal
because the bot may not size (AC1); an admitted entry carrying the advisory declaration
with its declared full-loss price DERIVED at the Book door by the per-family ExitLogicRef
consuming the cited evidence and stamped exactly as requested_r is Book-resolved, no Book
module injected into bot logic (AC2); the V1 exit kinds close_full and
tighten_protective_stop with close_partial an unsupported-capability refusal and a tighten
naming a direction and a bound never a price (AC3); the four risk-monotonic violation
policy rejections (AC4); the adopt-the-bot's-advisory-stop ExitLogicRef mode present in the
mode registry with its format-2 input contract, an unavailable-dependency refusal while
CT-23 sits at format 1, requested_r Book-resolved and R frozen in every mode (AC5); and
forward compatibility — format-1 artifacts readable forever and an unknown optional field
never breaking a format-1 consumer (AC6) (FR-028, FR-032; CT-23; DEC-0147, DEC-0177,
DEC-0185).
"""

from __future__ import annotations

import dataclasses

import pytest
from qmf.core import (
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Price,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    UnitKind,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.door import (
    ADOPT_BOT_ADVISORY_STOP_MODE,
    ADOPT_BOT_ADVISORY_STOP_MODE_ID,
    CT23_ACTIVE_FORMAT_VERSION,
    CT23_ADVISORY_STOP_FORMAT_VERSION,
    CT23_KNOWN_FORMAT_VERSIONS,
    EXIT_LOGIC_MODE_REGISTRY,
    AdmittedEntry,
    CitedEvidence,
    Direction,
    EntryIntent,
    EvidenceSlot,
    ExitIntent,
    ExitKind,
    ExitLogicRef,
    IntentFamily,
    ReasonCode,
    RiskEvaluationRequest,
    RiskMonotonicViolation,
    StopMoveDirection,
    TightenProtectiveStop,
    admit_entry_intent,
    check_exit_logic_mode_available,
    check_no_reopen,
    check_no_size_increase,
    check_stop_not_widened,
    check_target_within_envelope,
    derive_full_loss_price_at_door,
    evaluate_exit_intent,
    parse_inbound_intent,
    refuse_no_full_loss_price,
    reject_close_partial,
    reject_inbound_requested_r,
    reject_risk_monotonic_violation,
)
from qmf.risk.paper import ExecutionTarget

_DEFAULT_MODULE_ID = "book.default.evidence_stop"


# --- builders ----------------------------------------------------------------


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _other_instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="GBPUSD")


def _price(value: int) -> Price:
    result = Price.try_create(value, _instrument(), 5)
    assert is_ok(result)
    return result.value


def _delta(value: int, instrument: Instrument | None = None) -> PriceDelta:
    result = PriceDelta.try_create(value, instrument or _instrument(), 5)
    assert is_ok(result)
    return result.value


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    result = ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE)
    assert is_ok(result)
    return result.value


def _rate(numerator: int, denominator: int = 1) -> ExactRational:
    result = ExactRational.try_create(numerator, denominator, UnitKind.RATE)
    assert is_ok(result)
    return result.value


def _qty(value: int, unit: str = "lot") -> Quantity:
    result = Quantity.try_create(value, unit, 2)
    assert is_ok(result)
    return result.value


def _instant(value_ns: int = 1_700_000_000_000_000_000) -> Instant:
    result = Instant.try_create(value_ns)
    assert is_ok(result)
    return result.value


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _execution_target() -> ExecutionTarget:
    result = ExecutionTarget.try_create("live", VenueId(value="ctrader"), "acct-1")
    assert is_ok(result)
    return result.value


def _reason(code: str = "momentum-break", family: str = "scalper-v1") -> ReasonCode:
    result = ReasonCode.try_create(code, family)
    assert is_ok(result)
    return result.value


def _evidence_slot(label: str = "sqs") -> EvidenceSlot:
    result = EvidenceSlot.try_create(label, "sqs-ref-1", _instant())
    assert is_ok(result)
    return result.value


def _cited_evidence() -> CitedEvidence:
    result = CitedEvidence.try_create(sqs_reading=_evidence_slot())
    assert is_ok(result)
    return result.value


def _entry_intent(*, proposed_r: ExactRational | None = None) -> EntryIntent:
    result = EntryIntent.try_create(
        _instrument(),
        Direction.LONG,
        _reason(),
        _execution_target(),
        proposed_r=proposed_r,
        cited_evidence=_cited_evidence(),
    )
    assert is_ok(result)
    return result.value


def _exit_logic_ref(module_id: str = _DEFAULT_MODULE_ID) -> ExitLogicRef:
    result = ExitLogicRef.try_create(module_id, {"style": "structure"})
    assert is_ok(result)
    return result.value


class _OffsetStopModule:
    """A fake ExitLogicModule: derives a full-loss price a fixed offset on the loss side."""

    def __init__(self, offset: int = 500) -> None:
        self.offset = offset
        self.seen_evidence: list[CitedEvidence] = []

    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        self.seen_evidence.append(cited_evidence)
        if direction is Direction.LONG:
            value = entry_price.value - self.offset
        else:
            value = entry_price.value + self.offset
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class _NoStopModule:
    """A fake ExitLogicModule whose evidence yields no planned loss point."""

    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        return refuse_no_full_loss_price(module="no-stop")


class _WrongSideModule:
    """A fake ExitLogicModule that derives a price on the WRONG (non-loss) side of entry."""

    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        # A long's full-loss must be below entry; return ABOVE entry — not a loss point.
        return Price.try_create(entry_price.value + 500, entry_price.instrument, entry_price.scale)


# --- AC1: the door — two families, nothing else, and no inbound sizing --------


def test_request_carries_exactly_one_entry_family() -> None:
    result = RiskEvaluationRequest.try_create(entry=_entry_intent())
    assert is_ok(result)
    assert result.value.family is IntentFamily.ENTRY
    assert result.value.entry is not None
    assert result.value.exit is None


def test_request_carries_exactly_one_exit_family() -> None:
    exit_intent = ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), _fp("vp-1"))
    assert is_ok(exit_intent)
    result = RiskEvaluationRequest.try_create(exit=exit_intent.value)
    assert is_ok(result)
    assert result.value.family is IntentFamily.EXIT
    assert result.value.exit is not None
    assert result.value.entry is None


def test_request_with_both_families_is_invalid_input() -> None:
    exit_intent = ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), _fp("vp-1"))
    assert is_ok(exit_intent)
    result = RiskEvaluationRequest.try_create(entry=_entry_intent(), exit=exit_intent.value)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_request_with_neither_family_is_invalid_input() -> None:
    result = RiskEvaluationRequest.try_create()
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_request_with_wrong_typed_entry_is_invalid_input() -> None:
    result = RiskEvaluationRequest.try_create(entry="not-an-entry")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_request_with_wrong_typed_exit_is_invalid_input() -> None:
    result = RiskEvaluationRequest.try_create(exit="not-an-exit")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_inbound_requested_r_is_invalid_input_the_bot_may_not_size() -> None:
    result = reject_inbound_requested_r({"intent_family": "entry", "requested_r": _r(2)})
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "requested_r"


def test_inbound_without_requested_r_passes_the_sizing_guard() -> None:
    result = reject_inbound_requested_r({"intent_family": "entry"})
    assert is_ok(result)


def test_inbound_sizing_guard_needs_a_mapping() -> None:
    result = reject_inbound_requested_r(["requested_r"])
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_entry_intent_carries_no_requested_r_field_structurally() -> None:
    # The bot's inbound entry can never carry a sized requested_r — it is not a field.
    assert not hasattr(_entry_intent(), "requested_r")


# --- AC2: entry admission and the Book-derived full-loss price ----------------


def test_entry_intent_carries_the_advisory_declaration() -> None:
    intent = _entry_intent(proposed_r=_r(3))
    assert intent.instrument == _instrument()
    assert intent.direction is Direction.LONG
    assert intent.proposed_r == _r(3)
    assert intent.reason_code.code == "momentum-break"
    assert intent.execution_target.role.value == "live"
    assert intent.cited_evidence is not None


def test_entry_intent_proposed_r_is_optional_and_advisory() -> None:
    intent = _entry_intent()
    assert intent.proposed_r is None


def test_entry_intent_rejects_a_non_r_multiple_proposed_r() -> None:
    result = EntryIntent.try_create(
        _instrument(), Direction.LONG, _reason(), _execution_target(), proposed_r=_rate(5)
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_entry_intent_field_type_refusals() -> None:
    good_target = _execution_target()
    assert is_refusal(EntryIntent.try_create("nope", Direction.LONG, _reason(), good_target))
    assert is_refusal(EntryIntent.try_create(_instrument(), "sideways", _reason(), good_target))
    assert is_refusal(EntryIntent.try_create(_instrument(), Direction.LONG, "reason", good_target))
    assert is_refusal(EntryIntent.try_create(_instrument(), Direction.LONG, _reason(), "target"))
    assert is_refusal(
        EntryIntent.try_create(
            _instrument(), Direction.LONG, _reason(), good_target, cited_evidence="ev"
        )
    )


def test_admit_entry_derives_and_stamps_the_full_loss_price_at_the_door() -> None:
    module = _OffsetStopModule(offset=500)
    result = admit_entry_intent(
        intent=_entry_intent(proposed_r=_r(3)),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(),
        module=module,
        book_resolved_requested_r=_r(2),
    )
    assert is_ok(result)
    admitted = result.value
    assert isinstance(admitted, AdmittedEntry)
    # The Book DERIVED the price at the door (105000 - 500), consuming the cited evidence.
    assert admitted.declared_full_loss_price == _price(104500)
    assert admitted.original_risk_distance == _delta(500)
    # requested_r is Book-resolved and stamped, never bot-supplied.
    assert admitted.requested_r == _r(2)
    # the bot's advisory proposed_r rides through unchanged, never becoming requested_r.
    assert admitted.proposed_r == _r(3)
    assert admitted.requested_r != admitted.proposed_r
    # the Book door executed the ExitLogicRef module to derive the price at the door.
    assert len(module.seen_evidence) == 1


def test_admit_entry_short_direction_derives_loss_price_above_entry() -> None:
    result = EntryIntent.try_create(_instrument(), Direction.SHORT, _reason(), _execution_target())
    assert is_ok(result)
    admitted = admit_entry_intent(
        intent=result.value,
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(),
        module=_OffsetStopModule(offset=500),
        book_resolved_requested_r=_r(1),
    )
    assert is_ok(admitted)
    assert admitted.value.declared_full_loss_price == _price(105500)


def test_admit_entry_no_full_loss_price_is_invalid_input_no_admission() -> None:
    result = admit_entry_intent(
        intent=_entry_intent(),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(),
        module=_NoStopModule(),
        book_resolved_requested_r=_r(2),
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_admit_entry_wrong_side_derived_price_is_refused() -> None:
    result = admit_entry_intent(
        intent=_entry_intent(),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(),
        module=_WrongSideModule(),
        book_resolved_requested_r=_r(2),
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_admit_entry_rejects_bot_supplied_requested_r_shape() -> None:
    result = admit_entry_intent(
        intent=_entry_intent(),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_rate(2),  # not an r-multiple
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_admit_entry_refuses_a_scale_in() -> None:
    result = admit_entry_intent(
        intent=_entry_intent(),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_r(2),
        has_open_position=True,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_admit_entry_field_type_refusals() -> None:
    assert is_refusal(
        admit_entry_intent(
            intent="nope",
            entry_price=_price(105000),
            exit_logic_ref=_exit_logic_ref(),
            module=_OffsetStopModule(),
            book_resolved_requested_r=_r(2),
        )
    )
    assert is_refusal(
        admit_entry_intent(
            intent=_entry_intent(),
            entry_price="nope",
            exit_logic_ref=_exit_logic_ref(),
            module=_OffsetStopModule(),
            book_resolved_requested_r=_r(2),
        )
    )


def test_admitted_entry_is_fingerprintable() -> None:
    result = admit_entry_intent(
        intent=_entry_intent(proposed_r=_r(3)),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_r(2),
    )
    assert is_ok(result)
    fp = fingerprint(result.value.fp1_identity())
    assert is_ok(fp)


def test_no_book_module_is_injected_into_bot_logic() -> None:
    # The bot's EntryIntent never references an ExitLogicRef or a module — the module is a
    # door-side seam only.
    intent = _entry_intent()
    fields = {f.name for f in dataclasses.fields(intent)}
    assert "exit_logic_ref" not in fields
    assert "module" not in fields


# --- the derive-at-door function directly ------------------------------------


def test_derive_full_loss_price_at_door_consumes_evidence() -> None:
    module = _OffsetStopModule(offset=250)
    evidence = _cited_evidence()
    result = derive_full_loss_price_at_door(
        exit_logic_ref=_exit_logic_ref(),
        module=module,
        entry_price=_price(105000),
        direction=Direction.LONG,
        cited_evidence=evidence,
    )
    assert is_ok(result)
    assert result.value == _price(104750)
    assert module.seen_evidence[0] is evidence


def test_derive_full_loss_price_at_door_defaults_empty_evidence() -> None:
    result = derive_full_loss_price_at_door(
        exit_logic_ref=_exit_logic_ref(),
        module=_OffsetStopModule(),
        entry_price=_price(105000),
        direction=Direction.LONG,
    )
    assert is_ok(result)


def test_derive_full_loss_price_at_door_field_type_refusals() -> None:
    assert is_refusal(
        derive_full_loss_price_at_door(
            exit_logic_ref="nope",
            module=_OffsetStopModule(),
            entry_price=_price(105000),
            direction=Direction.LONG,
        )
    )
    assert is_refusal(
        derive_full_loss_price_at_door(
            exit_logic_ref=_exit_logic_ref(),
            module=object(),
            entry_price=_price(105000),
            direction=Direction.LONG,
        )
    )
    assert is_refusal(
        derive_full_loss_price_at_door(
            exit_logic_ref=_exit_logic_ref(),
            module=_OffsetStopModule(),
            entry_price="nope",
            direction=Direction.LONG,
        )
    )
    assert is_refusal(
        derive_full_loss_price_at_door(
            exit_logic_ref=_exit_logic_ref(),
            module=_OffsetStopModule(),
            entry_price=_price(105000),
            direction="sideways",
        )
    )
    assert is_refusal(
        derive_full_loss_price_at_door(
            exit_logic_ref=_exit_logic_ref(),
            module=_OffsetStopModule(),
            entry_price=_price(105000),
            direction=Direction.LONG,
            cited_evidence="ev",
        )
    )


# --- AC3: exit intents — kinds, close_partial, tighten never a price ----------


def test_exit_close_full_is_a_v1_kind() -> None:
    result = ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), _fp("vp-1"))
    assert is_ok(result)
    assert result.value.kind is ExitKind.CLOSE_FULL
    assert result.value.tighten is None


def test_exit_tighten_names_a_direction_and_a_bound() -> None:
    tighten = TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, _delta(300))
    assert is_ok(tighten)
    result = ExitIntent.try_create(
        ExitKind.TIGHTEN_PROTECTIVE_STOP, _reason(), _fp("vp-1"), tighten=tighten.value
    )
    assert is_ok(result)
    assert result.value.tighten is not None
    assert result.value.tighten.bound == _delta(300)


def test_close_partial_is_an_unsupported_capability_refusal() -> None:
    result = ExitIntent.try_create("close_partial", _reason(), _fp("vp-1"))
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_reject_close_partial_helper() -> None:
    refusal = reject_close_partial(caller="bot-x")
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_exit_unknown_kind_is_invalid_input() -> None:
    result = ExitIntent.try_create("teleport", _reason(), _fp("vp-1"))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_tighten_never_names_a_price() -> None:
    result = TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, _price(104500))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "bound"


def test_tighten_bound_must_be_a_positive_price_delta() -> None:
    assert is_refusal(TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, "300"))
    assert is_refusal(TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, _delta(0)))
    assert is_refusal(TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, _delta(-5)))


def test_tighten_unknown_direction_is_invalid_input() -> None:
    result = TightenProtectiveStop.try_create("sideways", _delta(300))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_exit_reason_code_must_be_typed() -> None:
    result = ExitIntent.try_create(ExitKind.CLOSE_FULL, "reason", _fp("vp-1"))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_exit_virtual_position_ref_must_be_a_fingerprint() -> None:
    result = ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), "vp-1")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_tighten_requires_its_direction_and_bound() -> None:
    result = ExitIntent.try_create(ExitKind.TIGHTEN_PROTECTIVE_STOP, _reason(), _fp("vp-1"))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_close_full_carries_no_tighten() -> None:
    tighten = TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, _delta(300))
    assert is_ok(tighten)
    result = ExitIntent.try_create(
        ExitKind.CLOSE_FULL, _reason(), _fp("vp-1"), tighten=tighten.value
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_evaluate_exit_intent_passes_a_validated_intent() -> None:
    exit_intent = ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), _fp("vp-1"))
    assert is_ok(exit_intent)
    result = evaluate_exit_intent(exit_intent.value)
    assert is_ok(result)
    assert result.value is exit_intent.value


def test_evaluate_exit_intent_refuses_a_non_exit_intent() -> None:
    result = evaluate_exit_intent("nope")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_exit_intent_is_fingerprintable() -> None:
    tighten = TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, _delta(300))
    assert is_ok(tighten)
    result = ExitIntent.try_create(
        ExitKind.TIGHTEN_PROTECTIVE_STOP, _reason(), _fp("vp-1"), tighten=tighten.value
    )
    assert is_ok(result)
    assert is_ok(fingerprint(result.value.fp1_identity()))


# --- AC4: the risk-monotonic law ---------------------------------------------


def test_widen_stop_via_tighten_direction_is_a_policy_rejection() -> None:
    result = TightenProtectiveStop.try_create(StopMoveDirection.WIDEN, _delta(300))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context["violation"] == RiskMonotonicViolation.WIDEN_STOP.value


def test_check_stop_not_widened_refuses_a_wider_distance() -> None:
    result = check_stop_not_widened(
        original_risk_distance=_delta(500), proposed_risk_distance=_delta(700)
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_check_stop_not_widened_allows_a_ratchet() -> None:
    assert is_ok(
        check_stop_not_widened(
            original_risk_distance=_delta(500), proposed_risk_distance=_delta(300)
        )
    )
    assert is_ok(
        check_stop_not_widened(
            original_risk_distance=_delta(500), proposed_risk_distance=_delta(500)
        )
    )


def test_check_stop_not_widened_field_refusals() -> None:
    assert is_refusal(
        check_stop_not_widened(original_risk_distance="d", proposed_risk_distance=_delta(300))
    )
    assert is_refusal(
        check_stop_not_widened(original_risk_distance=_delta(500), proposed_risk_distance="d")
    )
    # different instrument
    other = _delta(300, _other_instrument())
    assert is_refusal(
        check_stop_not_widened(original_risk_distance=_delta(500), proposed_risk_distance=other)
    )


def test_check_target_within_envelope() -> None:
    assert is_ok(
        check_target_within_envelope(
            proposed_target_distance=_delta(900), envelope_bound=_delta(1000)
        )
    )
    result = check_target_within_envelope(
        proposed_target_distance=_delta(1500), envelope_bound=_delta(1000)
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context["violation"] == RiskMonotonicViolation.EXTEND_TARGET_BEYOND_ENVELOPE.value


def test_check_target_within_envelope_needs_a_bound() -> None:
    result = check_target_within_envelope(
        proposed_target_distance=_delta(900), envelope_bound="1000"
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_check_target_within_envelope_refuses_a_cross_instrument_compare() -> None:
    result = check_target_within_envelope(
        proposed_target_distance=_delta(900, _other_instrument()), envelope_bound=_delta(1000)
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_check_no_reopen() -> None:
    assert is_ok(check_no_reopen(position_is_closed=False))
    result = check_no_reopen(position_is_closed=True)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context["violation"] == RiskMonotonicViolation.RE_OPEN.value


def test_check_no_reopen_needs_a_bool() -> None:
    result = check_no_reopen(position_is_closed="yes")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_check_no_size_increase() -> None:
    assert is_ok(check_no_size_increase(current_quantity=_qty(100), proposed_quantity=_qty(100)))
    assert is_ok(check_no_size_increase(current_quantity=_qty(100), proposed_quantity=_qty(60)))
    result = check_no_size_increase(current_quantity=_qty(100), proposed_quantity=_qty(150))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context["violation"] == RiskMonotonicViolation.INCREASE_SIZE.value


def test_check_no_size_increase_field_refusals() -> None:
    assert is_refusal(check_no_size_increase(current_quantity="100", proposed_quantity=_qty(150)))
    assert is_refusal(check_no_size_increase(current_quantity=_qty(100), proposed_quantity="150"))
    assert is_refusal(
        check_no_size_increase(
            current_quantity=_qty(100, "lot"), proposed_quantity=_qty(150, "share")
        )
    )


def test_reject_risk_monotonic_violation_each_class() -> None:
    for violation in RiskMonotonicViolation:
        refusal = reject_risk_monotonic_violation(violation)
        assert refusal.category is RefusalCategory.POLICY_REJECTION
        assert refusal.context["violation"] == violation.value


def test_reject_risk_monotonic_violation_unknown_is_invalid_input() -> None:
    refusal = reject_risk_monotonic_violation("teleport")
    assert refusal.category is RefusalCategory.INVALID_INPUT


# --- AC5: the ExitLogicRef mode registry and format gating -------------------


def test_adopt_bot_advisory_stop_mode_is_registered_with_format_2_input() -> None:
    assert ADOPT_BOT_ADVISORY_STOP_MODE_ID in EXIT_LOGIC_MODE_REGISTRY
    mode = EXIT_LOGIC_MODE_REGISTRY[ADOPT_BOT_ADVISORY_STOP_MODE_ID]
    assert mode is ADOPT_BOT_ADVISORY_STOP_MODE
    assert mode.input_field == "entry.advisory_stop_proposal"
    assert mode.required_ct23_format_version == CT23_ADVISORY_STOP_FORMAT_VERSION == 2


def test_ct23_active_format_version_is_one() -> None:
    assert CT23_ACTIVE_FORMAT_VERSION == 1


def test_adopt_mode_is_unavailable_dependency_at_format_1() -> None:
    result = check_exit_logic_mode_available(ADOPT_BOT_ADVISORY_STOP_MODE_ID, ct23_format_version=1)
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_adopt_mode_is_available_at_format_2() -> None:
    result = check_exit_logic_mode_available(ADOPT_BOT_ADVISORY_STOP_MODE_ID, ct23_format_version=2)
    assert is_ok(result)
    assert result.value is ADOPT_BOT_ADVISORY_STOP_MODE


def test_unregistered_module_is_not_gated() -> None:
    result = check_exit_logic_mode_available("book.default.evidence_stop", ct23_format_version=1)
    assert is_ok(result)
    assert result.value is None


def test_mode_gate_field_refusals() -> None:
    assert is_refusal(check_exit_logic_mode_available("", ct23_format_version=1))
    assert is_refusal(
        check_exit_logic_mode_available(ADOPT_BOT_ADVISORY_STOP_MODE_ID, ct23_format_version="1")
    )
    assert is_refusal(
        check_exit_logic_mode_available(ADOPT_BOT_ADVISORY_STOP_MODE_ID, ct23_format_version=True)
    )


def test_admit_with_adopt_mode_at_format_1_is_unavailable_dependency() -> None:
    result = admit_entry_intent(
        intent=_entry_intent(),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(ADOPT_BOT_ADVISORY_STOP_MODE_ID),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_r(2),
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_admit_with_adopt_mode_at_format_2_derives_the_price() -> None:
    result = admit_entry_intent(
        intent=_entry_intent(),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(ADOPT_BOT_ADVISORY_STOP_MODE_ID),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_r(2),
        ct23_format_version=2,
    )
    assert is_ok(result)
    # requested_r stays Book-resolved in every mode.
    assert result.value.requested_r == _r(2)


def test_admitted_entry_r_stays_frozen_in_every_mode() -> None:
    result = admit_entry_intent(
        intent=_entry_intent(),
        entry_price=_price(105000),
        exit_logic_ref=_exit_logic_ref(),
        module=_OffsetStopModule(),
        book_resolved_requested_r=_r(2),
    )
    assert is_ok(result)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.value.requested_r = _r(9)  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.value.original_risk_distance = _delta(1)  # type: ignore[misc]


def test_refuse_no_full_loss_price_is_invalid_input() -> None:
    refusal = refuse_no_full_loss_price(module="x")
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "declared_full_loss_price"


# --- AC6: forward compatibility (AD-5) ---------------------------------------


def test_ct23_known_format_versions_is_exactly_one() -> None:
    assert frozenset({1}) == CT23_KNOWN_FORMAT_VERSIONS


def test_parse_format_1_entry_artifact_stays_readable() -> None:
    raw = {"intent_family": "entry", "entry": _entry_intent(), "contract_format_version": 1}
    result = parse_inbound_intent(raw)
    assert is_ok(result)
    assert result.value.family is IntentFamily.ENTRY


def test_parse_format_1_exit_artifact() -> None:
    exit_intent = ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), _fp("vp-1"))
    assert is_ok(exit_intent)
    result = parse_inbound_intent({"intent_family": "exit", "exit": exit_intent.value})
    assert is_ok(result)
    assert result.value.family is IntentFamily.EXIT


def test_parse_ignores_unknown_optional_field_never_breaks_format_1_consumer() -> None:
    raw = {
        "intent_family": "entry",
        "entry": _entry_intent(),
        # a future format-2 field on a format-1 artifact — ignored, never a refusal.
        "advisory_stop_proposal": _price(104000),
        "some_future_field": "whatever",
    }
    result = parse_inbound_intent(raw)
    assert is_ok(result)
    assert result.value.entry is not None


def test_parse_unknown_contract_format_version_is_unsupported_capability() -> None:
    raw = {"intent_family": "entry", "entry": _entry_intent(), "contract_format_version": 2}
    result = parse_inbound_intent(raw)
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_parse_rejects_inbound_requested_r() -> None:
    raw = {"intent_family": "entry", "entry": _entry_intent(), "requested_r": _r(2)}
    result = parse_inbound_intent(raw)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_parse_field_and_family_refusals() -> None:
    assert is_refusal(parse_inbound_intent("not-a-mapping"))
    assert is_refusal(parse_inbound_intent({"intent_family": "entry"}, ct23_format_version="1"))
    assert is_refusal(parse_inbound_intent({"intent_family": "flip"}))
    assert is_refusal(parse_inbound_intent({"intent_family": "entry", "entry": "nope"}))
    assert is_refusal(parse_inbound_intent({"intent_family": "exit", "exit": "nope"}))


def test_parse_bad_declared_version_type_is_unsupported_capability() -> None:
    raw = {"intent_family": "entry", "entry": _entry_intent(), "contract_format_version": "two"}
    result = parse_inbound_intent(raw)
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- supporting value types ---------------------------------------------------


def test_reason_code_requires_typed_tokens() -> None:
    assert is_refusal(ReasonCode.try_create("", "fam"))
    assert is_refusal(ReasonCode.try_create("code", "  "))
    good = ReasonCode.try_create("code", "fam")
    assert is_ok(good)
    assert is_ok(fingerprint(good.value.fp1_identity()))


def test_evidence_slot_requires_its_as_of_time() -> None:
    result = EvidenceSlot.try_create("sqs", "ref", None)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert is_refusal(EvidenceSlot.try_create("", "ref", _instant()))
    assert is_refusal(EvidenceSlot.try_create("sqs", "", _instant()))
    good = EvidenceSlot.try_create("sqs", "ref", _instant())
    assert is_ok(good)
    assert is_ok(fingerprint(good.value.fp1_identity()))


def test_cited_evidence_named_slots() -> None:
    empty = CitedEvidence.try_create()
    assert is_ok(empty)
    assert empty.value.is_empty()
    both = CitedEvidence.try_create(
        sqs_reading=_evidence_slot("sqs"), cohort_correlation=_evidence_slot("cohort")
    )
    assert is_ok(both)
    assert not both.value.is_empty()
    assert is_ok(fingerprint(both.value.fp1_identity()))
    assert is_refusal(CitedEvidence.try_create(sqs_reading="not-a-slot"))
    assert is_refusal(CitedEvidence.try_create(cohort_correlation="not-a-slot"))


def test_exit_logic_ref_construction() -> None:
    good = ExitLogicRef.try_create("mod", {"k": "v"})
    assert is_ok(good)
    assert good.value.module_id == "mod"
    assert good.value.config["k"] == "v"
    assert is_ok(fingerprint(good.value.fp1_identity()))
    assert is_ok(ExitLogicRef.try_create("mod"))  # config optional
    assert is_refusal(ExitLogicRef.try_create(""))
    assert is_refusal(ExitLogicRef.try_create("mod", "not-a-mapping"))
    assert is_refusal(ExitLogicRef.try_create("mod", {"k": 5}))


def test_entry_intent_is_fingerprintable() -> None:
    assert is_ok(fingerprint(_entry_intent(proposed_r=_r(3)).fp1_identity()))
