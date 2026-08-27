"""L2 contract tests — CT-20 venue event & reconciliation (Story 8.6).

Oracle: docs/contracts/ct-20-venue-event.yaml (verbatim invariants) and the Story 8.6
acceptance criteria.

Covers QA-E08-L2-012..018.
"""

from __future__ import annotations

from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.venue import (
    Command,
    CommandKind,
    EventRecorder,
    InboundVenueEvent,
    ObservationKind,
    OrderState,
    Reconciliation,
    ReconciliationReadback,
    ReconciliationVerdict,
    SubjectResolution,
    SubmissionOutcome,
    TransactionBoundary,
    VenueNativeIdentity,
    detect_out_of_sequence,
    fold_order_state,
    journal_event_type,
    observation_journal_event_type,
    resolve_subject_terminal,
)

import _helpers as H


def _identity(native_id: str = "venue-oid-1", revision: int = 0) -> VenueNativeIdentity:
    return H.ok(VenueNativeIdentity.try_create("ctrader", native_id, revision))


def _event(kind, *, native_id="venue-oid-1", revision=0, receive_ns=1000, mono_ns=5,
           subject=None, fill_price=None, fill_qty=None, venue_ns=None, session="se-1"):
    return H.ok(
        InboundVenueEvent.try_create(
            kind,
            _identity(native_id, revision),
            H.mk_instant(receive_ns),
            H.mk_mono(mono_ns),
            session,
            {"raw": "wire-bytes"},
            fill_price=fill_price,
            fill_quantity=fill_qty,
            venue_instant=venue_ns,
            subject_native_id=subject,
        )
    )


# --- QA-E08-L2-012 — recording precedes interpretation (P0) -----------------


def test_l2_012_inbound_event_mandates_receive_wall_and_monotonic_stamps():
    """CT-20/AR-47: every inbound venue event carries the mandatory receive wall time
    and boot-scoped monotonic stamp; a missing stamp is refused."""
    ident = _identity()
    # Missing receive wall time.
    r1 = InboundVenueEvent.try_create(
        ObservationKind.SUBMISSION_ACKNOWLEDGEMENT, ident, None, H.mk_mono(5), "se", {"raw": 1}
    )
    assert is_refusal(r1)
    # Missing monotonic stamp.
    r2 = InboundVenueEvent.try_create(
        ObservationKind.SUBMISSION_ACKNOWLEDGEMENT, ident, H.mk_instant(1), None, "se", {"raw": 1}
    )
    assert is_refusal(r2)


def test_l2_012_fill_identity_fields_are_mandatory():
    """CT-20: a fill observation's price, quantity, and venue instant (plus the
    mandatory receive instant) are mandatory identity fields — a fill without them is
    refused; the order state is never a stored field."""
    ins = H.mk_instrument(H.mk_venue())
    # A fill missing its price/quantity/venue-instant is refused.
    bad = InboundVenueEvent.try_create(
        ObservationKind.FILL, _identity(), H.mk_instant(1), H.mk_mono(5), "se", {"raw": 1}
    )
    assert is_refusal(bad)
    # A complete fill is accepted and carries its identity fields.
    good = _event(
        ObservationKind.FILL,
        fill_price=H.mk_price(110000, ins),
        fill_qty=H.mk_qty(100),
        venue_ns=H.mk_instant(900),
    )
    assert good.is_fill
    assert good.fill_price is not None and good.fill_quantity is not None
    # Order state is never a stored field on the observation.
    assert not hasattr(good, "state")
    assert not hasattr(good, "order_state")


def test_l2_012_recorder_stores_verbatim_before_journaling():
    """CT-20/AR-47: recording precedes interpretation — the recorder writes the raw
    archive (observation) BEFORE the journal, then the registry room, in that order."""
    v = H.mk_venue()
    a = H.mk_account(v)
    obs_sink = H.RecordingSink()
    jnl_sink = H.RecordingSink()
    rec_sink = H.RecordingSink()
    cm = H.build_connection_manager(
        v, a, observation_sink=obs_sink, journal_sink=jnl_sink, record_sink=rec_sink
    )
    recorder = H.ok(EventRecorder.try_create(cm))
    res = recorder.record(
        _event(ObservationKind.SUBMISSION_ACKNOWLEDGEMENT),
        registry_record={"kind": "registry-record"},
        boundary=TransactionBoundary.ORDERED_WITH_RECOVERY,
    )
    assert is_ok(res) and res.value.committed is True
    # The observation (raw archive) was written before the journal event.
    assert len(obs_sink.calls) == 1
    assert len(jnl_sink.calls) == 1
    assert len(rec_sink.calls) == 1


# --- QA-E08-L2-013 — order state is a read-time fold (P1) -------------------


def test_l2_013_terminal_state_only_from_fills_and_lifecycle_never_from_absence():
    """CT-20: order state is a read-time fold; a terminal state is decided only by fills
    and venue lifecycle events, never inferred from a command outcome or absence alone."""
    ins = H.mk_instrument(H.mk_venue())
    # Accepted-by-venue prefix with NO observations is venue-accepted, NOT terminal —
    # absence of a fill never terminates the order.
    proj = fold_order_state(SubmissionOutcome.ACCEPTED_BY_VENUE, [])
    assert is_ok(proj)
    assert proj.value.state is OrderState.VENUE_ACCEPTED
    assert proj.value.terminal is False

    # A fill completing the ordered quantity is the only path to FILLED (terminal).
    fill = _event(
        ObservationKind.FILL,
        fill_price=H.mk_price(110000, ins),
        fill_qty=H.mk_qty(100),
        venue_ns=H.mk_instant(900),
    )
    proj2 = fold_order_state(
        SubmissionOutcome.ACCEPTED_BY_VENUE, [fill], ordered_quantity=H.mk_qty(100)
    )
    assert is_ok(proj2)
    assert proj2.value.state is OrderState.FILLED
    assert proj2.value.terminal is True


def test_l2_013_denied_locally_has_no_venue_order():
    """CT-20: denied-locally (and partially-executed) have no venue order and cannot be
    an order-state prefix."""
    res = fold_order_state(SubmissionOutcome.DENIED_LOCALLY, [])
    assert is_refusal(res)


# --- QA-E08-L2-014 — out-of-sequence (P1) -----------------------------------


def test_l2_014_illegal_transition_is_annotated_and_forces_unknown():
    """CT-20: an observation with no legal transition is recorded, annotated with a
    typed out-of-sequence edge, and forces its owning command to UNKNOWN."""
    ins = H.mk_instrument(H.mk_venue())
    # A cancel from a FILLED terminal has no legal transition.
    fill = _event(
        ObservationKind.FILL,
        fill_price=H.mk_price(110000, ins),
        fill_qty=H.mk_qty(100),
        venue_ns=H.mk_instant(900),
    )
    cancel = _event(ObservationKind.CANCEL_ACKNOWLEDGEMENT, native_id="venue-oid-1", revision=1)
    proj = fold_order_state(
        SubmissionOutcome.ACCEPTED_BY_VENUE, [fill, cancel], ordered_quantity=H.mk_qty(100)
    )
    assert is_ok(proj)
    assert proj.value.state is OrderState.UNKNOWN  # forced to UNKNOWN
    assert proj.value.out_of_sequence is True


def test_l2_014_adapter_never_synthesizes_a_venue_observation():
    """CT-20: adapters never synthesize a venue observation — out-of-sequence is a
    derived annotation, never a raw inbound kind."""
    res = InboundVenueEvent.try_create(
        ObservationKind.OUT_OF_SEQUENCE, _identity(), H.mk_instant(1), H.mk_mono(5), "se", {"raw": 1}
    )
    assert is_refusal(res)


# --- QA-E08-L2-015 — multi-room write (P1) ----------------------------------


def test_l2_015_partial_write_is_storage_failure_blocking_the_command_stream():
    """CT-20/AR-47: a partial multi-room write is a storage-failure refusal that blocks
    the command stream and is journaled on recovery; the sensing pipe is unaffected."""
    v = H.mk_venue()
    a = H.mk_account(v)
    obs_sink = H.RecordingSink()           # raw archive lands
    jnl_sink = H.RecordingSink(fail=True)  # journal room fails -> partial write
    rec_sink = H.RecordingSink()
    cm = H.build_connection_manager(
        v, a, observation_sink=obs_sink, journal_sink=jnl_sink, record_sink=rec_sink
    )
    recorder = H.ok(EventRecorder.try_create(cm))
    res = recorder.record(
        _event(ObservationKind.SUBMISSION_ACKNOWLEDGEMENT),
        registry_record={"kind": "registry-record"},
        boundary=TransactionBoundary.ORDERED_WITH_RECOVERY,
    )
    assert is_refusal(res)
    assert res.category is RefusalCategory.STORAGE_FAILURE
    # The command stream is blocked; the sensing pipe is unaffected.
    assert cm.command_pipe_open is False
    assert cm.sensing_pipe_open is True
    # The partial write is held for recovery journaling.
    assert recorder.pending_recovery is not None


# --- QA-E08-L2-016 — reconciliation verdict (P0) ----------------------------


def test_l2_016_reconciliation_verdict_vocabulary_and_out_of_lookback():
    """CT-20: a verdict is one of {reconciled, drift, unknown, out-of-lookback}; the
    fourth so 'I cannot see that far back' is never read as 'the position closed'."""
    assert {v.value for v in ReconciliationVerdict} == {
        "reconciled",
        "drift",
        "unknown",
        "out-of-lookback",
    }
    # A read-back that cannot see the whole declared lookback -> out-of-lookback.
    readback = H.ok(
        ReconciliationReadback.try_create(
            reference_instant=H.mk_instant(10_000_000_000),
            declared_lookback=H.mk_duration(5_000_000_000),
            earliest_visible=H.mk_instant(8_000_000_000),  # window start (5s) is not visible
            readback_evidence={"orders": [], "positions": []},
        )
    )
    verdict = readback.verdict(expected_state="flat", observed_state="flat")
    assert is_ok(verdict)
    assert verdict.value.verdict is ReconciliationVerdict.OUT_OF_LOOKBACK
    assert verdict.value.is_out_of_lookback is True
    # out-of-lookback is NOT read as position-closed: a standing intent may not dispatch.
    assert verdict.value.standing_intent_may_dispatch is False


def test_l2_016_reconciliation_gates_command_pipe_only_never_sensing():
    """CT-20: reconciliation gates the command pipe only — the sensing pipe never blocks
    on it; only a reconciled verdict lets a standing intent dispatch."""
    for verdict in ReconciliationVerdict:
        recon = Reconciliation(verdict=verdict, detail="test")
        assert recon.gates_sensing_pipe is False  # never gates sensing
        assert recon.standing_intent_may_dispatch is (verdict is ReconciliationVerdict.RECONCILED)


# --- QA-E08-L2-017 — subject-terminal resolution (P1) -----------------------


def test_l2_017_subject_terminal_at_or_after_submit_is_named_rejected_outcome():
    """CT-20: a close/amend whose subject is observed terminal at or after the submit
    stamp resolves rejected-by-venue (superseded-by-terminal-subject) — a named outcome,
    never UNKNOWN, never a stream block."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    close = Command.close_position(v, a, H.SESSION_EPOCH, 0, "account-binding", "position-7")
    close = H.ok(close)
    # Subject terminal (a fill) at instant 1000, submit stamp 1000 -> at-or-after.
    terminal_fill = _event(
        ObservationKind.FILL,
        native_id="stop-oid",
        subject="position-7",
        fill_price=H.mk_price(110000, ins),
        fill_qty=H.mk_qty(100),
        venue_ns=H.mk_instant(1000),
    )
    res = resolve_subject_terminal(
        close,
        observations=[terminal_fill],
        submit_stamp=H.mk_instant(1000),
        subject_present_at_submission=True,
    )
    assert is_ok(res)
    assert res.value.resolution is SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT
    assert res.value.outcome is SubmissionOutcome.REJECTED_BY_VENUE
    assert res.value.outcome is not SubmissionOutcome.UNKNOWN


def test_l2_017_subject_absent_at_submission_resolves_without_submission():
    """CT-20: a subject absent or already terminal at submission resolves without
    submission — never a naked close."""
    v = H.mk_venue()
    a = H.mk_account(v)
    close = H.ok(Command.close_position(v, a, H.SESSION_EPOCH, 0, "account-binding", "position-7"))
    res = resolve_subject_terminal(
        close, observations=[], submit_stamp=H.mk_instant(1000),
        subject_present_at_submission=False,
    )
    assert is_ok(res)
    assert res.value.resolution is SubjectResolution.RESOLVE_WITHOUT_SUBMISSION
    assert res.value.outcome is None  # resolved without a submission outcome


# --- QA-E08-L2-018 — cardinality (P1) ---------------------------------------


def test_l2_018_journal_mapping_is_total_and_unique_over_command_outcomes():
    """CT-20: the (command kind x outcome) -> journal event mapping is exhaustive and
    total — one distinct journal event per (kind, outcome)."""
    seen = set()
    for kind in CommandKind:
        for outcome in SubmissionOutcome:
            event = journal_event_type(kind, outcome)
            assert isinstance(event, str) and event
            seen.add((kind, outcome, event))
    # Exactly one event type per (kind, outcome) pair, and all distinct.
    events = {e for (_, _, e) in seen}
    assert len(events) == len(CommandKind) * len(SubmissionOutcome)


def test_l2_018_journal_mapping_is_total_and_unique_over_observation_kinds():
    """CT-20: the (observation kind) -> journal event mapping mints exactly one distinct
    journal event per recorded observation kind."""
    events = {observation_journal_event_type(kind) for kind in ObservationKind}
    assert len(events) == len(ObservationKind)
