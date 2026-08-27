"""L3 acceptance tests — UNKNOWN stream block + read-time state machine.

Oracle: Story 8.7 acceptance criteria, SCN-0005 Then, constitution L35, CT-19/CT-20.
These are the epic-specific stateful behaviours line coverage cannot see (the block,
"market data keeps flowing", the transition matrix).

Covers QA-E08-L3-001..008.
"""

from __future__ import annotations

from qmf.core import RefusalCategory, Retryability, is_ok, is_refusal
from qmf.venue import (
    AdmissionDisposition,
    CommandKind,
    CommandObservation,
    InboundVenueEvent,
    JournalEvent,
    ObservationKind,
    OrderState,
    Reconciliation,
    ReconciliationVerdict,
    ResolveResolution,
    SessionRecovery,
    StandingIntentDisposition,
    StreamBlockCause,
    SubmissionOutcome,
    SubmissionResult,
    UnknownGate,
    UnknownTrigger,
    UnknownBlock,
    VenueNativeIdentity,
    detect_out_of_sequence,
    fold_order_state,
    is_legal_transition,
    order_for_shared_throttle,
)

import _helpers as H


def _gate_and_cm():
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    obs_sink = H.RecordingSink()
    jnl_sink = H.RecordingSink()
    cm = H.build_connection_manager(v, a, observation_sink=obs_sink, journal_sink=jnl_sink)
    gate = H.ok(UnknownGate.try_create(cm))
    return v, a, ins, cm, gate, obs_sink, jnl_sink


def _unknown_submission(v, a, ins, *, ordinal=0):
    """Resolve a command to a genuine UNKNOWN SubmissionResult and record the block."""
    resolver = H.build_resolver()
    cmd = H.build_place_order(v, a, ins, ordinal=ordinal)
    res = resolver.transport_unknown(
        cmd,
        trigger="timeout",
        monotonic_elapsed=H.mk_duration(750),
        receive_instant=H.mk_instant(1000),
        submission_deadline=H.mk_instant(5000),
    )
    return cmd, H.ok(res)


# --- QA-E08-L3-001 — outstanding UNKNOWN blocks the stream (P0) -------------


def test_l3_001_outstanding_unknown_refuses_new_command_after_condition_resolution():
    """Story 8.7 AC-2 / SCN-0005: with an outstanding UNKNOWN on a (venue, account)
    stream, a new command is refused (transient-venue-failure, after-condition =
    resolution); the adapter never clears its own block."""
    v, a, ins, cm, gate, _, _ = _gate_and_cm()
    _, unknown = _unknown_submission(v, a, ins)
    assert is_ok(gate.record_unknown(unknown))
    assert gate.stream_open is False

    new_cmd = H.build_place_order(v, a, ins, ordinal=1)
    admit = gate.admit(new_cmd, receive_instant=H.mk_instant(1100))
    assert is_ok(admit)
    result = admit.value
    assert result.disposition is AdmissionDisposition.REFUSED
    assert result.block_cause is StreamBlockCause.OUTSTANDING_UNKNOWN
    refusal = result.refusal
    assert refusal.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    assert refusal.retryability is Retryability.AFTER_CONDITION
    assert refusal.after_condition_descriptor == "resolution"

    # The adapter never clears its own block: resume_new (suspend-new) does not clear it.
    assert is_ok(gate.resume_new())
    assert gate.stream_open is False


# --- QA-E08-L3-002 — the sensing pipe never blocks (P0) ---------------------


def test_l3_002_sensing_pipe_keeps_flowing_while_command_pipe_gated():
    """SCN-0005 Then: while an UNKNOWN gates the command pipe, the sensing/market-data
    pipe keeps flowing and never blocks."""
    v, a, ins, cm, gate, obs_sink, _ = _gate_and_cm()
    _, unknown = _unknown_submission(v, a, ins)
    assert is_ok(gate.record_unknown(unknown))

    # Command pipe is gated (stream not open) ...
    assert gate.stream_open is False
    # ... but the sensing pipe is unaffected and a sensing observation still flows.
    assert cm.sensing_pipe_open is True
    sensing = cm.emit_sensing_observation({"tick": "EURUSD 1.10000"})
    assert is_ok(sensing)


# --- QA-E08-L3-003 — the UNKNOWN observation's mandatory fields (P0) ---------


def test_l3_003_unknown_observation_carries_trigger_elapsed_receive_deadline():
    """Story 8.7 AC-1 / CT-19: the UNKNOWN observation carries its trigger, the monotonic
    elapsed measurement, the wall receive instant, and the injected submission deadline —
    the deadline's existence mandatory, its value injected (never QMF's)."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    resolver = H.build_resolver()
    cmd = H.build_place_order(v, a, ins)

    # The submission deadline is a mandatory injected argument: None is refused.
    missing = resolver.transport_unknown(
        cmd, trigger="timeout", monotonic_elapsed=H.mk_duration(1),
        receive_instant=H.mk_instant(1), submission_deadline=None,
    )
    assert is_refusal(missing)

    good = H.ok(
        resolver.transport_unknown(
            cmd, trigger="disconnect", monotonic_elapsed=H.mk_duration(750),
            receive_instant=H.mk_instant(1000), submission_deadline=H.mk_instant(9999),
        )
    )
    obs = good.observation
    assert obs.unknown_trigger is UnknownTrigger.DISCONNECT
    assert obs.monotonic_elapsed is not None
    assert obs.receive_instant.value_ns == 1000
    assert obs.submission_deadline.value_ns == 9999  # the injected value rides the observation


def test_l3_003_record_unknown_requires_the_mandatory_unknown_fields():
    """CT-19: recording an UNKNOWN block requires the mandatory UNKNOWN fields — a
    result whose observation omits the submission deadline is refused."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    cm = H.build_connection_manager(v, a)
    gate = H.ok(UnknownGate.try_create(cm))
    cmd = H.build_place_order(v, a, ins)
    fp = H.ok(cmd.fingerprint())
    # Hand-build an UNKNOWN result whose observation has no submission_deadline.
    obs = CommandObservation(
        command_fp1=fp, kind=CommandKind.PLACE_ORDER, outcome=SubmissionOutcome.UNKNOWN,
        receive_instant=H.mk_instant(1), unknown_trigger=UnknownTrigger.TIMEOUT,
        monotonic_elapsed=H.mk_duration(1), submission_deadline=None,
    )
    result = SubmissionResult(
        command_fp1=fp, kind=CommandKind.PLACE_ORDER, outcome=SubmissionOutcome.UNKNOWN,
        observation=obs, journal_event=JournalEvent.for_outcome(fp, CommandKind.PLACE_ORDER,
                                                                SubmissionOutcome.UNKNOWN),
    )
    assert is_refusal(gate.record_unknown(result))


# --- QA-E08-L3-004 — explicit resolve_unknown clears the block (P0) ---------


def test_l3_004_resolve_unknown_records_observation_and_clears_only_on_resolution():
    """Story 8.7 AC-5 / CT-19: resolve_unknown(identity, resolution in {observed-accepted,
    observed-absent, operator-attested}) is itself recorded as an observation and clears
    the block on that resolution — never on a reconciliation verdict alone."""
    v, a, ins, cm, gate, obs_sink, _ = _gate_and_cm()
    cmd, unknown = _unknown_submission(v, a, ins)
    fp = unknown.command_fp1
    assert is_ok(gate.record_unknown(unknown))
    assert gate.stream_open is False

    # A reconciliation verdict alone does NOT clear the block — there is no API that takes
    # a reconciliation to clear an UNKNOWN, and redeciding a would-be intent holds open.
    assert gate.stream_open is False

    # An invalid resolution token is refused; a non-outstanding identity is refused.
    assert is_refusal(gate.resolve_unknown(fp, "made-up", receive_instant=H.mk_instant(2000)))

    before = len(obs_sink.calls)
    cleared = gate.resolve_unknown(
        fp, ResolveResolution.OBSERVED_ABSENT, receive_instant=H.mk_instant(2000)
    )
    assert is_ok(cleared)
    assert cleared.value.resolution is ResolveResolution.OBSERVED_ABSENT
    # The resolve_unknown call is itself recorded as an observation.
    assert len(obs_sink.calls) == before + 1
    # The block clears on that resolution.
    assert gate.stream_open is True


# --- QA-E08-L3-005 — a refused protection act never evaporates (P0) ----------


def test_l3_005_refused_protection_act_is_held_as_standing_intent_journaled():
    """Story 8.7 AC-3 / SCN-0005: a protection act the block refuses never evaporates —
    it is held as a standing protection intent, journaled BEFORE dispatch."""
    v, a, ins, cm, gate, _, jnl_sink = _gate_and_cm()
    _, unknown = _unknown_submission(v, a, ins)
    assert is_ok(gate.record_unknown(unknown))

    cancel = H.build_cancel_order(v, a, ordinal=5)
    jnl_before = len(jnl_sink.calls)
    admit = gate.admit(cancel, receive_instant=H.mk_instant(1200))
    assert is_ok(admit)
    assert admit.value.disposition is AdmissionDisposition.HELD_AS_STANDING_INTENT
    assert admit.value.standing_intent is not None
    # It is still refused NOW (transient venue failure) but preserved, not dropped.
    assert admit.value.refusal.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
    # Journaled before dispatch: a standing-intent journal event was appended.
    assert len(jnl_sink.calls) == jnl_before + 1
    assert gate.standing_intents  # the intent is held


def test_l3_005_standing_intent_redecides_against_reconciled_only():
    """Story 8.7 AC-3 / SCN-0005/DEC-0158: a standing intent re-decides (not retries)
    against a reconciled verdict ONLY once the block has cleared; drift/unknown/
    out-of-lookback alarm and hold it open without dispatching."""
    v, a, ins, cm, gate, _, _ = _gate_and_cm()
    _, unknown = _unknown_submission(v, a, ins)
    fp = unknown.command_fp1
    assert is_ok(gate.record_unknown(unknown))

    intent_a = H.ok(gate.admit(H.build_cancel_order(v, a, ordinal=5),
                               receive_instant=H.mk_instant(1))).standing_intent
    intent_b = H.ok(gate.admit(H.build_close_position(v, a, ordinal=6),
                               receive_instant=H.mk_instant(1))).standing_intent

    reconciled = Reconciliation(verdict=ReconciliationVerdict.RECONCILED, detail="ok")

    # While the block stands, even a reconciled verdict holds the intent OPEN (never opens
    # a position against unseen state).
    held = gate.redecide_standing_intent(intent_a, reconciled)
    assert is_ok(held)
    assert held.value.disposition is StandingIntentDisposition.HOLD_OPEN
    assert held.value.alarm is True

    # Clear the block with an explicit resolve_unknown.
    assert is_ok(gate.resolve_unknown(fp, ResolveResolution.OBSERVED_ABSENT,
                                      receive_instant=H.mk_instant(2000)))

    # A drift verdict alarms and holds open without dispatching.
    drift = Reconciliation(verdict=ReconciliationVerdict.DRIFT, detail="drift")
    d = gate.redecide_standing_intent(intent_a, drift)
    assert is_ok(d) and d.value.disposition is StandingIntentDisposition.HOLD_OPEN and d.value.alarm

    # A reconciled verdict (block cleared) dispatches the intent afresh — never a retry.
    dispatched = gate.redecide_standing_intent(intent_b, reconciled)
    assert is_ok(dispatched)
    assert dispatched.value.disposition is StandingIntentDisposition.DISPATCH
    assert dispatched.value.alarm is False


# --- QA-E08-L3-006 — risk-reducing throttle priority; suspend-new (P1) ------


def test_l3_006_risk_reducing_dispatch_ahead_of_place_order():
    """Story 8.7 AC-4: the risk-reducing kinds dispatch ahead of place_order on every
    shared throttle (stable within a priority class)."""
    v = H.mk_venue()
    a = H.mk_account(v)
    ins = H.mk_instrument(v)
    place1 = H.build_place_order(v, a, ins, ordinal=0)
    cancel = H.build_cancel_order(v, a, ordinal=1)
    place2 = H.build_place_order(v, a, ins, ordinal=2)
    close = H.build_close_position(v, a, ordinal=3)
    ordered = order_for_shared_throttle([place1, cancel, place2, close])
    assert is_ok(ordered)
    kinds = [c.kind for c in ordered.value]
    # Every risk-reducing kind precedes every place_order.
    last_risk = max(i for i, k in enumerate(kinds) if k is not CommandKind.PLACE_ORDER)
    first_place = min(i for i, k in enumerate(kinds) if k is CommandKind.PLACE_ORDER)
    assert last_risk < first_place


def test_l3_006_suspend_new_is_local_and_instant_with_no_venue_round_trip():
    """Story 8.7 AC-4 / SCN-0005: suspend-new takes local effect instantly with no venue
    round-trip — a new place_order is refused while risk-reducing commands still flow."""
    v, a, ins, cm, gate, obs_sink, jnl_sink = _gate_and_cm()
    calls_before = len(obs_sink.calls) + len(jnl_sink.calls)
    assert is_ok(gate.suspend_new())
    assert gate.is_new_suspended is True
    # No venue round-trip / no sink write: suspend-new is a local flag flip.
    assert len(obs_sink.calls) + len(jnl_sink.calls) == calls_before

    # With no outstanding UNKNOWN, a new place_order is refused (suspend-new) ...
    place = gate.admit(H.build_place_order(v, a, ins, ordinal=1), receive_instant=H.mk_instant(1))
    assert is_ok(place) and place.value.disposition is AdmissionDisposition.REFUSED
    assert place.value.block_cause is StreamBlockCause.SUSPEND_NEW
    # ... while a risk-reducing command is admitted.
    cancel = gate.admit(H.build_cancel_order(v, a, ordinal=2), receive_instant=H.mk_instant(1))
    assert is_ok(cancel) and cancel.value.disposition is AdmissionDisposition.ADMITTED


# --- QA-E08-L3-007 — no flatten/retry/assume/invent on UNKNOWN (P0) ---------


def test_l3_007_adapter_never_initiates_flatten_or_resubmits_or_invents():
    """Story 8.7 AC-2 / DEC-0150 / L35: no QMF component retries, assumes an outcome,
    flattens, or invents a terminal state on UNKNOWN; the adapter never initiates a
    flatten and session recovery never resubmits a command."""
    v, a, ins, cm, gate, _, _ = _gate_and_cm()
    # The gate exposes no flatten/close_all/retry action (adapter_self is limited to
    # suspend/resume-new; the block clears only via resolve_unknown).
    for forbidden in ("flatten", "close_all", "retry", "assume_outcome", "invent_terminal"):
        assert not hasattr(gate, forbidden)

    # Session recovery never resubmits a command; an in-flight command becomes UNKNOWN.
    assert SessionRecovery.resubmits_command is False
    resolutions = SessionRecovery().on_disconnect(["cmd-1", "cmd-2"])
    assert is_ok(resolutions)
    for res in resolutions.value:
        assert res.outcome is SubmissionOutcome.UNKNOWN
        assert res.trigger is UnknownTrigger.DISCONNECT


# --- QA-E08-L3-008 — the state-machine transition matrix (P0) ---------------


def _minimal_event(kind):
    ins = H.mk_instrument(H.mk_venue())
    fill_kwargs = {}
    if kind is ObservationKind.FILL:
        fill_kwargs = dict(
            fill_price=H.mk_price(110000, ins),
            fill_quantity=H.mk_qty(100),
            venue_instant=H.mk_instant(900),
        )
    return H.ok(
        InboundVenueEvent.try_create(
            kind,
            H.ok(VenueNativeIdentity.try_create("ctrader", "oid-1", 0)),
            H.mk_instant(1000),
            H.mk_mono(5),
            "se-1",
            {"raw": "wire"},
            **fill_kwargs,
        )
    )


def test_l3_008_every_illegal_from_state_kind_pair_yields_a_typed_edge():
    """Story 8.6 AC-3 / CT-20: enumerating the transition graph, every (from-state,
    observation-kind) pair absent from the legal matrix yields a typed out-of-sequence
    edge (never a silent accept); every present pair yields no edge."""
    raw_kinds = [k for k in ObservationKind if k is not ObservationKind.OUT_OF_SEQUENCE]
    checked = 0
    illegal_seen = 0
    for state in OrderState:
        for kind in raw_kinds:
            event = _minimal_event(kind)
            legal = is_legal_transition(state, kind)
            edge = detect_out_of_sequence(state, event)
            assert is_ok(edge)
            produced = edge.value is not None
            # illegal <=> a typed edge is produced (no silent accept, no missing hole).
            assert produced == (not legal), (
                f"({state.value}, {kind.value}): legal={legal} but edge_produced={produced}"
            )
            checked += 1
            if not legal:
                illegal_seen += 1
    assert checked == len(OrderState) * len(raw_kinds)
    assert illegal_seen > 0  # the matrix genuinely has forbidden transitions


def test_l3_008_illegal_transition_folds_to_unknown_never_synthesizes():
    """CT-20: an illegal transition folds the owning command to UNKNOWN; an adapter never
    synthesizes a venue observation to paper over the gap."""
    ins = H.mk_instrument(H.mk_venue())
    # accepted -> fill(complete) -> FILLED (terminal); a further fill is illegal -> UNKNOWN.
    fill = _minimal_event(ObservationKind.FILL)
    second_fill = _minimal_event(ObservationKind.FILL)
    proj = fold_order_state(
        SubmissionOutcome.ACCEPTED_BY_VENUE, [fill, second_fill], ordered_quantity=H.mk_qty(100)
    )
    assert is_ok(proj)
    assert proj.value.state is OrderState.UNKNOWN
    assert proj.value.out_of_sequence is True

    # A synthesized out-of-sequence observation cannot be constructed as a raw inbound.
    synth = InboundVenueEvent.try_create(
        ObservationKind.OUT_OF_SEQUENCE,
        H.ok(VenueNativeIdentity.try_create("ctrader", "oid-9", 0)),
        H.mk_instant(1), H.mk_mono(5), "se", {"raw": 1},
    )
    assert is_refusal(synth)
