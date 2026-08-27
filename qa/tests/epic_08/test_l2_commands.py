"""L2 contract tests — CT-19 venue command + four-outcome law (Story 8.5).

Oracle: docs/contracts/ct-19-venue-command.yaml (verbatim invariants), constitution
L35, and the Story 8.5 acceptance criteria.

Covers QA-E08-L2-006..011.
"""

from __future__ import annotations

from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.venue import (
    FOUR_OUTCOME_LAW,
    BindingOutcome,
    Command,
    CommandIdBindingRegistry,
    CommandKind,
    CompoundCommand,
    OrderType,
    ProtectionAmendment,
    ProtectionSide,
    SubmissionOutcome,
    is_success,
    journal_event_type,
    meet_outcomes,
)

import _helpers as H


# --- QA-E08-L2-006 — command vocabulary (P1) --------------------------------


def test_l2_006_vocabulary_is_exactly_five_kinds():
    """CT-19/AR-44: the command vocabulary is exactly the five typed kinds."""
    assert {k.value for k in CommandKind} == {
        "place_order",
        "cancel_order",
        "close_position",
        "close_all",
        "amend_protection",
    }


def test_l2_006_fractional_or_partial_close_is_unsupported_capability():
    """CT-19: a fractional or partial close is an unsupported-capability refusal — no
    command kind expresses a fractional close."""
    v = H.mk_venue()
    a = H.mk_account(v)
    res = Command.close_position(
        v, a, H.SESSION_EPOCH, 0, "account-binding", "position-1", partial_quantity=H.mk_qty(50)
    )
    assert is_refusal(res)
    assert res.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_l2_006_kind_inappropriate_field_is_omitted_never_null():
    """CT-19 nullability: a kind-inappropriate field is an omitted key in identity,
    never a null (a cancel_order carries no order_parameters key)."""
    v = H.mk_venue()
    a = H.mk_account(v)
    cancel = H.build_cancel_order(v, a)
    content = cancel.fp1_identity()
    assert "order_parameters" not in content
    assert "protection_amendment" not in content
    assert cancel.order_parameters is None  # omitted, not a null value in identity


# --- QA-E08-L2-007 — four-outcome-law totality (P0) -------------------------


def test_l2_007_four_outcome_law_excludes_partially_executed():
    """CT-19: the four-outcome law is exactly {accepted, rejected, denied-locally,
    UNKNOWN}; partially-executed is compound-parent-only and never a single outcome."""
    assert {o.value for o in FOUR_OUTCOME_LAW} == {
        "accepted-by-venue",
        "rejected-by-venue",
        "denied-locally",
        "UNKNOWN",
    }
    assert SubmissionOutcome.PARTIALLY_EXECUTED not in FOUR_OUTCOME_LAW


def test_l2_007_every_outcome_resolves_to_one_law_member_and_mints_records():
    """CT-19: every well-formed submission resolves to exactly one four-outcome-law
    member; denied-locally is an OUTCOME not a refusal; every outcome mints exactly one
    observation record and one journal event."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    resolver = H.build_resolver()
    inst = H.mk_instant(1000)

    accepted = resolver.accepted(H.build_place_order(v, a, ins, ordinal=0), receive_instant=inst)
    denied = resolver.denied_locally(
        H.build_place_order(v, a, ins, ordinal=1), reason="risk cap", receive_instant=inst
    )
    rejected = resolver.venue_error(
        H.build_place_order(v, a, ins, ordinal=2), venue_code="ORDER-REJECTED", receive_instant=inst
    )
    unknown = resolver.transport_unknown(
        H.build_place_order(v, a, ins, ordinal=3),
        trigger="timeout",
        monotonic_elapsed=H.mk_duration(500),
        receive_instant=inst,
        submission_deadline=H.mk_instant(2000),
    )
    for res, expected in (
        (accepted, SubmissionOutcome.ACCEPTED_BY_VENUE),
        (denied, SubmissionOutcome.DENIED_LOCALLY),
        (rejected, SubmissionOutcome.REJECTED_BY_VENUE),
        (unknown, SubmissionOutcome.UNKNOWN),
    ):
        assert is_ok(res), res
        result = res.value
        assert result.outcome is expected
        assert result.outcome in FOUR_OUTCOME_LAW
        # Exactly one observation record and one journal event per outcome.
        assert result.observation is not None
        assert result.journal_event is not None
        assert result.journal_event.event_type == journal_event_type(result.kind, expected)

    # denied-locally is an OUTCOME, never a refusal.
    assert is_ok(denied)
    assert denied.value.outcome is SubmissionOutcome.DENIED_LOCALLY


# --- QA-E08-L2-008 — UNKNOWN trigger; a timeout is never a rejection (P0) ----


def test_l2_008_transport_triggers_resolve_unknown_never_rejection():
    """CT-19/L35: a transport error, timeout, or disconnect resolves UNKNOWN — a state,
    not an error — and a timeout is never read as a rejection."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    resolver = H.build_resolver()
    for trigger in ("timeout", "transport-error", "disconnect"):
        res = resolver.transport_unknown(
            H.build_place_order(v, a, ins),
            trigger=trigger,
            monotonic_elapsed=H.mk_duration(750),
            receive_instant=H.mk_instant(1),
            submission_deadline=H.mk_instant(2),
        )
        assert is_ok(res)
        assert res.value.outcome is SubmissionOutcome.UNKNOWN
        # The UNKNOWN observation carries its trigger; the outcome is never a rejection.
        assert res.value.observation.unknown_trigger.value == trigger
        assert res.value.outcome is not SubmissionOutcome.REJECTED_BY_VENUE


def test_l2_008_unmapped_venue_error_is_unknown_not_rejection():
    """CT-19/CT-18: a venue-returned error resolves rejected-by-venue only where the
    CT-18 table declares that class; every other venue code fails closed to UNKNOWN."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    resolver = H.build_resolver()
    res = resolver.venue_error(
        H.build_place_order(v, a, ins), venue_code="UNLISTED-CODE", receive_instant=H.mk_instant(1)
    )
    assert is_ok(res)
    assert res.value.outcome is SubmissionOutcome.UNKNOWN


# --- QA-E08-L2-009 — amend_protection risk-non-increasing (P0) --------------


def test_l2_009_stop_side_risk_increasing_amendment_is_refused():
    """CT-19: a stop-side change may not increase the loss-direction distance measured
    against the frozen original_risk_distance — a risk-increasing change is refused."""
    v = H.mk_venue()
    ins = H.mk_instrument(v)
    # new distance 60 > original 50 on the stop side: risk-INCREASING -> refused.
    res = ProtectionAmendment.try_create(
        ProtectionSide.STOP,
        H.mk_delta(60, ins),
        H.mk_price(110000, ins),
        original_risk_distance=H.mk_delta(50, ins),
    )
    assert is_refusal(res)
    # A risk-NON-increasing change (40 <= 50) is accepted.
    ok_res = ProtectionAmendment.try_create(
        ProtectionSide.STOP,
        H.mk_delta(40, ins),
        H.mk_price(110000, ins),
        original_risk_distance=H.mk_delta(50, ins),
    )
    assert is_ok(ok_res)


def test_l2_009_stop_check_binds_stop_side_only():
    """CT-19: the contract-level risk test binds the STOP side only — a target-side
    change carries no original_risk_distance (that field is stop-side)."""
    v = H.mk_venue()
    ins = H.mk_instrument(v)
    # Target side must not carry an original_risk_distance (stop-side field).
    bad_target = ProtectionAmendment.try_create(
        ProtectionSide.TARGET,
        H.mk_delta(80, ins),
        H.mk_price(110000, ins),
        original_risk_distance=H.mk_delta(50, ins),
    )
    assert is_refusal(bad_target)
    # A target-side change with no risk test is accepted even when "wide".
    good_target = ProtectionAmendment.try_create(
        ProtectionSide.TARGET, H.mk_delta(500, ins), H.mk_price(110000, ins)
    )
    assert is_ok(good_target)


def test_l2_009_amend_protection_is_its_own_kind_not_widened():
    """CT-19: amend_protection carries a typed ProtectionAmendment and is never widened
    into a general amend_order (there is no general-amend kind in the vocabulary)."""
    assert "amend_order" not in {k.value for k in CommandKind}
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    amend = H.build_amend_protection(v, a, ins)
    assert amend.kind is CommandKind.AMEND_PROTECTION
    assert amend.protection_amendment is not None
    # A free-form payload (not a typed ProtectionAmendment) is refused.
    bad = Command.amend_protection(v, a, H.SESSION_EPOCH, 0, {"raw": "payload"}, "position-1")
    assert is_refusal(bad)


# --- QA-E08-L2-010 — compound meet (P1) -------------------------------------


def test_l2_010_compound_meet_is_never_a_success_when_a_child_fails():
    """CT-19: the parent outcome is the meet of its children — any child UNKNOWN makes
    the parent UNKNOWN; any child rejected makes it partially-executed, which is never a
    success."""
    # any UNKNOWN -> UNKNOWN
    r_unknown = meet_outcomes(
        [SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.UNKNOWN,
         SubmissionOutcome.REJECTED_BY_VENUE]
    )
    assert is_ok(r_unknown) and r_unknown.value is SubmissionOutcome.UNKNOWN

    # a rejected child (no UNKNOWN) -> partially-executed, never a success
    r_partial = meet_outcomes(
        [SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.REJECTED_BY_VENUE]
    )
    assert is_ok(r_partial) and r_partial.value is SubmissionOutcome.PARTIALLY_EXECUTED
    assert is_success(r_partial.value) is False

    # all accepted -> accepted
    r_all = meet_outcomes([SubmissionOutcome.ACCEPTED_BY_VENUE, SubmissionOutcome.ACCEPTED_BY_VENUE])
    assert is_ok(r_all) and r_all.value is SubmissionOutcome.ACCEPTED_BY_VENUE
    assert is_success(r_all.value) is True


def test_l2_010_compound_children_have_distinct_derived_identity():
    """CT-19: each child of a compound command carries a derived identity distinct from
    its siblings and its parent."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    parent = H.build_place_order(v, a, ins)
    compound = CompoundCommand.fan_out(parent, [0, 1, 2])
    assert is_ok(compound)
    children = compound.value.children
    identities = [c.identity.value for c in children]
    assert len(set(identities)) == 3  # all distinct
    assert compound.value.parent_fp1.value not in identities


# --- QA-E08-L2-011 — command-id binding (P1) --------------------------------


def test_l2_011_binding_idempotent_accept_and_collision_alarm():
    """CT-19/AR-48: where the CT-18 mapping is not injective-and-total, a durable
    command-id-binding persists before submission; re-presenting the same command is an
    idempotent accept, and differing content under a reused venue client id is refused
    and alarmed."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    sink = H.RecordingSink()
    registry = H.ok(CommandIdBindingRegistry.try_create(sink))

    cmd = H.build_place_order(v, a, ins, ordinal=0)
    first = registry.bind_before_submission(cmd, venue_client_id="cid-1", injective_total=False)
    assert is_ok(first) and first.value is BindingOutcome.BOUND
    assert len(sink.calls) == 1  # persisted BEFORE submission through the injected sink

    # Re-presenting the SAME command under the same client id is an idempotent accept.
    again = registry.bind_before_submission(cmd, venue_client_id="cid-1", injective_total=False)
    assert is_ok(again) and again.value is BindingOutcome.IDEMPOTENT

    # DIFFERENT content under the reused client id is a true collision: refused + alarmed.
    other = H.build_place_order(v, a, ins, ordinal=99)
    collision = registry.bind_before_submission(other, venue_client_id="cid-1", injective_total=False)
    assert is_refusal(collision)
    assert collision.context.get("alarm") is True


def test_l2_011_injective_total_mapping_needs_no_binding():
    """CT-19: when the CT-18 mapping is injective-and-total the venue client id suffices
    alone — no durable binding is persisted."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    sink = H.RecordingSink()
    registry = H.ok(CommandIdBindingRegistry.try_create(sink))
    res = registry.bind_before_submission(
        H.build_place_order(v, a, ins), venue_client_id="cid-1", injective_total=True
    )
    assert is_ok(res) and res.value is BindingOutcome.MAPPING_INJECTIVE_TOTAL
    assert len(sink.calls) == 0  # nothing persisted


def test_l2_011_storage_failure_before_submission_is_surfaced():
    """CT-19/AR-47: a storage failure persisting the durable binding is surfaced (the
    command is NOT submitted), never swallowed."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    failing = H.RecordingSink(fail=True)
    registry = H.ok(CommandIdBindingRegistry.try_create(failing))
    res = registry.bind_before_submission(
        H.build_place_order(v, a, ins), venue_client_id="cid-1", injective_total=False
    )
    assert is_refusal(res)
    assert res.category is RefusalCategory.STORAGE_FAILURE
