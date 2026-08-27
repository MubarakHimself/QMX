"""L4 scenario test — SCN-0005 Uncertain Venue Submission Resolves to UNKNOWN.

Oracle: docs/scenarios/SCN-0005-uncertain-venue-submission.md (the prose walkthrough).
The cross-package journey over qmf-core nouns, injected core sinks, and a fake cTrader
transport (the CommandOutcomeResolver stands in for the wire) — no live host.

Covers QA-E08-L4-001.
"""

from __future__ import annotations

from qmf.core import RefusalCategory, Retryability, is_ok, is_refusal
from qmf.venue import (
    AdmissionDisposition,
    EventRecorder,
    InboundVenueEvent,
    ObservationKind,
    Reconciliation,
    ReconciliationVerdict,
    ResolveResolution,
    StandingIntentDisposition,
    StreamBlockCause,
    SubmissionOutcome,
    TransactionBoundary,
    UnknownGate,
    VenueNativeIdentity,
)

import _helpers as H


def test_l4_001_uncertain_submission_end_to_end_journey():
    """SCN-0005 end to end: a lost-certainty submission resolves UNKNOWN, records before
    interpretation, blocks its (venue, account) command stream, keeps the sensing pipe
    flowing, preserves a refused protection act as a standing intent, and clears only on
    an explicit resolve_unknown — after which a reconciled verdict lets the standing
    intent dispatch (re-decided, never retried)."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)

    obs_sink = H.RecordingSink()
    jnl_sink = H.RecordingSink()
    rec_sink = H.RecordingSink()
    cm = H.build_connection_manager(
        v, a, observation_sink=obs_sink, journal_sink=jnl_sink, record_sink=rec_sink
    )
    resolver = H.build_resolver()
    gate = H.ok(UnknownGate.try_create(cm))
    recorder = H.ok(EventRecorder.try_create(cm))

    # (Given) recording precedes interpretation — an inbound submission-ack is stored
    # verbatim and journaled before any state evaluation.
    ack = H.ok(
        InboundVenueEvent.try_create(
            ObservationKind.SUBMISSION_ACKNOWLEDGEMENT,
            H.ok(VenueNativeIdentity.try_create("ctrader", "oid-1", 0)),
            H.mk_instant(500), H.mk_mono(5), H.SESSION_EPOCH, {"raw": "ack-wire"},
        )
    )
    committed = recorder.record(
        ack, registry_record={"kind": "order-record"}, boundary=TransactionBoundary.ORDERED_WITH_RECOVERY
    )
    assert is_ok(committed) and committed.value.committed is True

    # (When) a submission loses transport certainty before a final outcome.
    place = H.build_place_order(v, a, ins, ordinal=0)
    unknown = H.ok(
        resolver.transport_unknown(
            place,
            trigger="timeout",
            monotonic_elapsed=H.mk_duration(900),
            receive_instant=H.mk_instant(1000),
            submission_deadline=H.mk_instant(5000),  # injected; existence mandatory
        )
    )
    # (Then) it resolves to UNKNOWN — a state, not an error — carrying its trigger.
    assert unknown.outcome is SubmissionOutcome.UNKNOWN
    assert unknown.observation.unknown_trigger.value == "timeout"

    # The command stream blocks on the outstanding UNKNOWN.
    assert is_ok(gate.record_unknown(unknown))
    assert gate.stream_open is False

    # A new command on that stream is refused (transient venue failure, after = resolution).
    refused = gate.admit(H.build_place_order(v, a, ins, ordinal=1), receive_instant=H.mk_instant(1100))
    assert is_ok(refused)
    assert refused.value.disposition is AdmissionDisposition.REFUSED
    assert refused.value.block_cause is StreamBlockCause.OUTSTANDING_UNKNOWN
    assert refused.value.refusal.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert refused.value.refusal.retryability is Retryability.AFTER_CONDITION

    # A refused protection act never evaporates — held as a standing intent, journaled.
    held = gate.admit(H.build_close_position(v, a, ordinal=2), receive_instant=H.mk_instant(1200))
    assert is_ok(held)
    assert held.value.disposition is AdmissionDisposition.HELD_AS_STANDING_INTENT
    intent = held.value.standing_intent
    assert intent is not None

    # Throughout, the sensing pipe never blocks — market data keeps flowing.
    assert cm.sensing_pipe_open is True
    assert is_ok(cm.emit_sensing_observation({"tick": "EURUSD 1.10010"}))

    # While the block stands, even a reconciled verdict holds the intent open (never opens
    # a position against state it cannot see).
    reconciled = Reconciliation(verdict=ReconciliationVerdict.RECONCILED, detail="agree")
    held_open = gate.redecide_standing_intent(intent, reconciled)
    assert is_ok(held_open)
    assert held_open.value.disposition is StandingIntentDisposition.HOLD_OPEN

    # The block clears ONLY on an explicit resolve_unknown, itself recorded as an
    # observation — never on a reconciliation verdict alone.
    cleared = gate.resolve_unknown(
        unknown.command_fp1, ResolveResolution.OBSERVED_ABSENT, receive_instant=H.mk_instant(2000)
    )
    assert is_ok(cleared)
    assert gate.stream_open is True

    # Now — block cleared and reconciled — the standing protection intent dispatches afresh
    # (a re-decision, explicitly never a retry).
    dispatched = gate.redecide_standing_intent(intent, reconciled)
    assert is_ok(dispatched)
    assert dispatched.value.disposition is StandingIntentDisposition.DISPATCH
    assert dispatched.value.alarm is False
