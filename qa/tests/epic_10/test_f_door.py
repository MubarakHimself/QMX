"""Epic 10 independent audit — Cluster F (Story 10.6).

The CT-23 risk-evaluation door: two typed families, no inbound sizing, the
Book-derived full-loss price stamped exactly as requested_r is resolved, the V1
exit kinds, the risk-monotonic law, the ExitLogicRef mode gate, and forward
compatibility. Authored from Story 10.6 ACs, CT-23, and the P0-8 gate.

Planned IDs: F1-F7.
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
    CT23_ADVISORY_STOP_FORMAT_VERSION,
    CT23_FORMAT_VERSION_1,
    EXIT_LOGIC_MODE_REGISTRY,
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
    StopMoveDirection,
    TightenProtectiveStop,
    admit_entry_intent,
    check_exit_logic_mode_available,
    check_no_reopen,
    check_no_size_increase,
    check_stop_not_widened,
    check_target_within_envelope,
    derive_full_loss_price_at_door,
    parse_inbound_intent,
    refuse_no_full_loss_price,
    reject_close_partial,
    reject_inbound_requested_r,
)
from qmf.risk.paper import ExecutionTarget


def _instrument() -> Instrument:
    return Instrument(venue=VenueId(value="ctrader"), symbol="EURUSD")


def _price(value: int) -> Price:
    result = Price.try_create(value, _instrument(), 5)
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


def _rate(num: int) -> ExactRational:
    result = ExactRational.try_create(num, 1, UnitKind.RATE)
    assert is_ok(result)
    return result.value


def _qty(value: int) -> Quantity:
    result = Quantity.try_create(value, "lot", 2)
    assert is_ok(result)
    return result.value


def _instant() -> Instant:
    result = Instant.try_create(1_700_000_000_000_000_000)
    assert is_ok(result)
    return result.value


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _target() -> ExecutionTarget:
    from qmf.core import AccountRole

    result = ExecutionTarget.try_create(AccountRole.LIVE, VenueId(value="ctrader"), "acct-1")
    assert is_ok(result)
    return result.value


def _reason() -> ReasonCode:
    result = ReasonCode.try_create("momentum-break", "scalper-v1")
    assert is_ok(result)
    return result.value


def _cited() -> CitedEvidence:
    slot = EvidenceSlot.try_create("sqs", "sqs-ref-1", _instant())
    assert is_ok(slot)
    result = CitedEvidence.try_create(sqs_reading=slot.value)
    assert is_ok(result)
    return result.value


def _entry(*, proposed_r: ExactRational | None = None,
           advisory_stop_proposal: object = None) -> EntryIntent:
    result = EntryIntent.try_create(
        _instrument(), Direction.LONG, _reason(), _target(),
        proposed_r=proposed_r, cited_evidence=_cited(),
        advisory_stop_proposal=advisory_stop_proposal,
    )
    assert is_ok(result)
    return result.value


def _ref(module_id: str = "book.default.evidence_stop") -> ExitLogicRef:
    result = ExitLogicRef.try_create(module_id, {"style": "structure"})
    assert is_ok(result)
    return result.value


class _OffsetStopModule:
    """A door-side ExitLogicModule fake deriving a fixed-offset loss-side price."""

    def __init__(self, offset: int = 500) -> None:
        self.offset = offset
        self.seen_evidence: list[CitedEvidence] = []

    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        self.seen_evidence.append(cited_evidence)
        value = entry_price.value - self.offset if direction is Direction.LONG else entry_price.value + self.offset
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class _NoStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        return refuse_no_full_loss_price(module="no-stop")


# --- F1 [P0-8]: two families, nothing else, and no inbound sizing -------------


def test_F1_door_two_families_and_no_inbound_requested_r() -> None:
    entry_req = RiskEvaluationRequest.try_create(entry=_entry())
    assert is_ok(entry_req)
    assert entry_req.value.family is IntentFamily.ENTRY
    exit_intent = ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), _fp("vp-1"))
    assert is_ok(exit_intent)
    exit_req = RiskEvaluationRequest.try_create(exit=exit_intent.value)
    assert is_ok(exit_req)
    assert exit_req.value.family is IntentFamily.EXIT
    # Both families or neither -> invalid input.
    assert is_refusal(RiskEvaluationRequest.try_create(entry=_entry(), exit=exit_intent.value))
    assert is_refusal(RiskEvaluationRequest.try_create())
    # An inbound requested_r -> invalid input (the bot may not size).
    sized = reject_inbound_requested_r({"intent_family": "entry", "requested_r": _r(2)})
    assert is_refusal(sized)
    assert sized.category is RefusalCategory.INVALID_INPUT
    assert sized.context["field"] == "requested_r"
    # And an EntryIntent structurally carries no requested_r field.
    assert not hasattr(_entry(), "requested_r")


# --- F2: an entry intent carries the format-1 advisory declaration -----------


def test_F2_entry_intent_carries_format1_declaration() -> None:
    intent = _entry(proposed_r=_r(3))
    assert intent.instrument == _instrument()
    assert intent.direction is Direction.LONG
    assert intent.proposed_r == _r(3)  # advisory, optional
    assert intent.reason_code.code == "momentum-break"
    assert intent.execution_target.role.value == "live"
    assert intent.cited_evidence is not None
    # proposed_r is optional and advisory.
    assert _entry().proposed_r is None
    # A non-r-multiple proposed_r is refused.
    assert is_refusal(EntryIntent.try_create(
        _instrument(), Direction.LONG, _reason(), _target(), proposed_r=_rate(5)
    ))


# --- F3 [P0-8]: the Book derives + stamps the full-loss price at the door -----


def test_F3_full_loss_price_derived_at_door_requested_r_book_resolved() -> None:
    module = _OffsetStopModule(offset=500)
    result = admit_entry_intent(
        intent=_entry(proposed_r=_r(3)), entry_price=_price(105000),
        exit_logic_ref=_ref(), module=module, book_resolved_requested_r=_r(2),
    )
    assert is_ok(result)
    admitted = result.value
    # The Book DERIVED the price at the door (105000 - 500), consuming the cited evidence.
    assert admitted.declared_full_loss_price == _price(104500)
    assert admitted.original_risk_distance == _delta(500)
    assert len(module.seen_evidence) == 1
    # requested_r is Book-resolved and stamped, never bot-supplied; proposed_r rides through.
    assert admitted.requested_r == _r(2)
    assert admitted.proposed_r == _r(3)
    assert admitted.requested_r != admitted.proposed_r
    # No Book module is injected into bot logic: EntryIntent references no ref/module.
    fields = {f.name for f in dataclasses.fields(_entry())}
    assert "exit_logic_ref" not in fields
    assert "module" not in fields
    # No full-loss price derivable -> invalid input, no admission.
    no_stop = admit_entry_intent(
        intent=_entry(), entry_price=_price(105000), exit_logic_ref=_ref(),
        module=_NoStopModule(), book_resolved_requested_r=_r(2),
    )
    assert is_refusal(no_stop)
    assert no_stop.category is RefusalCategory.INVALID_INPUT


# --- F4: the V1 exit kinds; close_partial unsupported; tighten never a price ---


def test_F4_v1_exit_kinds_and_tighten_names_no_price() -> None:
    close_full = ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), _fp("vp-1"))
    assert is_ok(close_full)
    tighten = TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, _delta(300))
    assert is_ok(tighten)
    tighten_intent = ExitIntent.try_create(
        ExitKind.TIGHTEN_PROTECTIVE_STOP, _reason(), _fp("vp-1"), tighten=tighten.value
    )
    assert is_ok(tighten_intent)
    # close_partial is an unsupported-capability refusal.
    partial = ExitIntent.try_create("close_partial", _reason(), _fp("vp-1"))
    assert is_refusal(partial)
    assert partial.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert reject_close_partial(caller="bot").category is RefusalCategory.UNSUPPORTED_CAPABILITY
    # A tighten names a direction and a bound (a PriceDelta), never a price.
    named_price = TightenProtectiveStop.try_create(StopMoveDirection.TIGHTEN, _price(104500))
    assert is_refusal(named_price)
    assert named_price.context["field"] == "bound"


# --- F5: the risk-monotonic law ----------------------------------------------


def test_F5_risk_monotonic_violations_are_policy_rejections() -> None:
    widen = check_stop_not_widened(original_risk_distance=_delta(500), proposed_risk_distance=_delta(700))
    assert is_refusal(widen)
    assert widen.category is RefusalCategory.POLICY_REJECTION
    extend = check_target_within_envelope(proposed_target_distance=_delta(1500), envelope_bound=_delta(1000))
    assert is_refusal(extend)
    assert extend.category is RefusalCategory.POLICY_REJECTION
    reopen = check_no_reopen(position_is_closed=True)
    assert is_refusal(reopen)
    assert reopen.category is RefusalCategory.POLICY_REJECTION
    grow = check_no_size_increase(current_quantity=_qty(100), proposed_quantity=_qty(150))
    assert is_refusal(grow)
    assert grow.category is RefusalCategory.POLICY_REJECTION
    # A ratchet (tighter stop) and a same-or-smaller size are allowed.
    assert is_ok(check_stop_not_widened(original_risk_distance=_delta(500), proposed_risk_distance=_delta(300)))
    assert is_ok(check_no_size_increase(current_quantity=_qty(100), proposed_quantity=_qty(60)))


# --- F6: the adopt-bot's-advisory-stop mode gate; R frozen in every mode ------


def test_F6_adopt_mode_gated_by_format_and_r_stays_frozen() -> None:
    assert ADOPT_BOT_ADVISORY_STOP_MODE_ID in EXIT_LOGIC_MODE_REGISTRY
    mode = EXIT_LOGIC_MODE_REGISTRY[ADOPT_BOT_ADVISORY_STOP_MODE_ID]
    assert mode is ADOPT_BOT_ADVISORY_STOP_MODE
    assert mode.input_field == "entry.advisory_stop_proposal"
    assert mode.required_ct23_format_version == CT23_ADVISORY_STOP_FORMAT_VERSION == 2
    # At CT-23 format 1 the mode is an unavailable-dependency refusal.
    at_1 = check_exit_logic_mode_available(ADOPT_BOT_ADVISORY_STOP_MODE_ID, ct23_format_version=1)
    assert is_refusal(at_1)
    assert at_1.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    admit_at_1 = admit_entry_intent(
        intent=_entry(), entry_price=_price(105000),
        exit_logic_ref=_ref(ADOPT_BOT_ADVISORY_STOP_MODE_ID), module=_OffsetStopModule(),
        book_resolved_requested_r=_r(2), ct23_format_version=CT23_FORMAT_VERSION_1,
    )
    assert is_refusal(admit_at_1)
    assert admit_at_1.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # At format 2 the mode derives the price; requested_r stays Book-resolved, R frozen.
    admitted = admit_entry_intent(
        intent=_entry(advisory_stop_proposal=_price(104500)), entry_price=_price(105000),
        exit_logic_ref=_ref(ADOPT_BOT_ADVISORY_STOP_MODE_ID), module=_OffsetStopModule(),
        book_resolved_requested_r=_r(2), ct23_format_version=2,
    )
    assert is_ok(admitted)
    assert admitted.value.requested_r == _r(2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        admitted.value.requested_r = _r(9)  # type: ignore[misc]


# --- F7: format-1 artifacts stay readable; unknown optional field is ignored ---


def test_F7_format1_readable_forever_unknown_field_ignored() -> None:
    raw = {
        "intent_family": "entry", "entry": _entry(),
        "advisory_stop_proposal": _price(104000),  # a format-2 field on a format-1 artifact
        "some_future_field": "whatever", "contract_format_version": 1,
    }
    result = parse_inbound_intent(raw)
    assert is_ok(result)
    assert result.value.entry is not None
    # The unknown optional field never breaks the format-1 consumer (it is ignored).
    assert result.value.entry.advisory_stop_proposal is None
    # An unknown contract format version is an unsupported-capability refusal.
    bad = parse_inbound_intent({"intent_family": "entry", "entry": _entry(), "contract_format_version": 99})
    assert is_refusal(bad)
    assert bad.category is RefusalCategory.UNSUPPORTED_CAPABILITY
