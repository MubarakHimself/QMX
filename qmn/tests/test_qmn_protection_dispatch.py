"""Story 26.2 — ranked control dispatcher and persistent protective intents."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import Instant, VenueId, is_ok, is_refusal, unpersistable
from qmf.core.refusal import Result
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    ControlActionRecord,
    EnforcementScope,
    ReconciliationVerdict,
    SatisfactionPredicate,
    StandingIntentStatus,
    SubjectScope,
    mint_control_action,
)
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable
from qmn.protection import (
    DISPATCHER_SURFACE,
    PROTECTION_SURFACE,
    RANKED_CONTROL_KINDS,
    UNDELIVERABLE_ALARM_CLASS,
    CandidateOrigin,
    IntentPersistDisposition,
    ProtectionIntentExtent,
    StreamProtectionDispatcher,
    check_dead_wire_satisfaction,
    command_outcome_never_satisfies,
    dispatch_ranked_controls,
    exclude_venue_resident_tier1,
    persist_protective_intent,
    redecide_protective_intent,
    require_total_unique_rank_table,
    stream_dispatcher_key,
)
from qmn.protection.dispatch import DispatchCandidate

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = 1_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _venue(token: str = "venue-a") -> VenueId:
    return _ok(VenueId.try_create(token))


def _stream(account: str = "acct-1") -> CommandStreamKey:
    return _ok(CommandStreamKey.try_create(_venue(), account))


def _rank_row(kind: ControlActionKind, rank: int) -> ControlRankRow:
    return _ok(ControlRankRow.try_create(kind, rank))


def _rank_table() -> ControlRankTable:
    # SCN-0010 class ordering: protection (suspend) outranks forced flats.
    rows = [
        _rank_row(ControlActionKind.SUSPEND_NEW, 0),
        _rank_row(ControlActionKind.FLATTEN, 1),
        _rank_row(ControlActionKind.DRAIN, 2),
        _rank_row(ControlActionKind.RESUME, 3),
    ]
    return _ok(ControlRankTable.try_create(rows))


def _enforcement(
    stream: CommandStreamKey | None = None,
    *,
    scope: SubjectScope = SubjectScope.BINDING,
    ref: str = "binding-1",
) -> EnforcementScope:
    return EnforcementScope(
        subject_scope=scope,
        scope_ref=ref,
        stream=stream or _stream(),
    )


def _action(
    kind: ControlActionKind,
    *,
    stream: CommandStreamKey | None = None,
    authority_kind: AuthorityKind = AuthorityKind.OPERATOR,
    authority: str = "op-1",
    rank: int = 0,
    scope: SubjectScope = SubjectScope.BINDING,
    scope_ref: str = "binding-1",
    reason: str = "test",
    trigger_class: str | None = None,
    issued_at: Instant | None = None,
    protection_declares_close_all: bool = False,
) -> ControlActionRecord:
    return _ok(
        mint_control_action(
            kind,
            authority,
            authority_kind,
            scope,
            scope_ref,
            rank,
            reason,
            stream or _stream(),
            issued_at or _instant(),
            trigger_class=trigger_class,
            protection_declares_close_all=protection_declares_close_all,
        )
    )


def _candidate(
    record: ControlActionRecord,
    *,
    enforcement: EnforcementScope | None = None,
    origin: CandidateOrigin = CandidateOrigin.CT30,
    arrival_ordinal: int = 0,
    mechanical_command: ControlActionKind | None = None,
) -> DispatchCandidate:
    return _ok(
        DispatchCandidate.try_create(
            record,
            enforcement or _enforcement(record.stream),
            origin=origin,
            mechanical_command=mechanical_command,
            arrival_ordinal=arrival_ordinal,
        )
    )


def _extent(capacity: int = 8) -> ProtectionIntentExtent:
    return _ok(ProtectionIntentExtent.try_create(capacity))


def _dispatcher() -> StreamProtectionDispatcher:
    return _ok(
        StreamProtectionDispatcher.try_create(
            stream=_stream(),
            rank_table=_rank_table(),
            extent=_extent(),
        )
    )


# --- surface / rank table -----------------------------------------------------


def test_dispatcher_surface_under_protection() -> None:
    assert PROTECTION_SURFACE == "qmn.protection"
    assert DISPATCHER_SURFACE == "qmn.protection.dispatch"
    assert frozenset(ControlActionKind) == RANKED_CONTROL_KINDS


def test_bms_rank_table_must_be_total_and_unique() -> None:
    assert is_ok(require_total_unique_rank_table(_rank_table()))

    partial = _ok(
        ControlRankTable.try_create(
            [
                _rank_row(ControlActionKind.SUSPEND_NEW, 0),
                _rank_row(ControlActionKind.FLATTEN, 1),
            ]
        )
    )
    refused = require_total_unique_rank_table(partial)
    assert is_refusal(refused)
    assert "missing" in refused.context

    dup = [
        _rank_row(ControlActionKind.SUSPEND_NEW, 0),
        _rank_row(ControlActionKind.FLATTEN, 0),
        _rank_row(ControlActionKind.DRAIN, 2),
        _rank_row(ControlActionKind.RESUME, 3),
    ]
    assert is_refusal(ControlRankTable.try_create(dup))


def test_stream_dispatcher_key_is_venue_account() -> None:
    key = _ok(stream_dispatcher_key(_venue(), "acct-1"))
    assert key.venue_id == _venue()
    assert key.account_id == "acct-1"
    assert is_refusal(stream_dispatcher_key(_venue(), ""))


# --- AC1: ranked dispatch, collapse, compose, no arrival order, Tier-1 --------


def test_compose_suspend_new_and_flatten_both_execute() -> None:
    stream = _stream()
    suspend = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        reason="kill-switch",
    )
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
        reason="kill-line",
        issued_at=_instant(2_000),
    )
    plan = _ok(
        dispatch_ranked_controls(
            [
                _candidate(suspend, arrival_ordinal=99),
                _candidate(flatten, arrival_ordinal=0),
            ],
            _rank_table(),
            stream=stream,
            arbitration_seed="compose",
        )
    )
    kinds = {p.record.action_kind for p in plan.emit}
    assert kinds == {ControlActionKind.SUSPEND_NEW, ControlActionKind.FLATTEN}
    assert plan.suppressed == ()
    assert plan.arrival_order_ignored is True
    assert plan.venue_resident_outside == ()


def test_collapse_identical_mechanical_commands_only() -> None:
    stream = _stream()
    kill_line = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
        reason="kill_line",
    )
    window = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="window_forced_flat",
        reason="window",
        issued_at=_instant(2_000),
    )
    bot_close = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="bot-exit",
        rank=1,
        reason="bot-close-full",
        trigger_class="hold_time_force_flat",
        issued_at=_instant(3_000),
    )
    # Different mechanical command composes rather than collapsing.
    suspend = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        reason="kill-switch",
        issued_at=_instant(4_000),
    )
    plan = _ok(
        dispatch_ranked_controls(
            [
                _candidate(kill_line, arrival_ordinal=0),
                _candidate(window, arrival_ordinal=1),
                _candidate(
                    bot_close,
                    origin=CandidateOrigin.RISK_NON_INCREASING,
                    arrival_ordinal=2,
                ),
                _candidate(suspend, arrival_ordinal=3),
            ],
            _rank_table(),
            stream=stream,
            arbitration_seed="collapse",
        )
    )
    emit_kinds = {p.record.action_kind for p in plan.emit}
    assert ControlActionKind.SUSPEND_NEW in emit_kinds
    assert ControlActionKind.FLATTEN in emit_kinds
    # Three flats collapsed to one emission + suspend.
    assert len(plan.emit) == 2
    assert len(plan.suppressed) == 2
    assert all(
        getattr(s, "reason_class", None) == "collapse-same-mechanical-command"
        for s in plan.suppressed
    )


def test_arrival_order_never_decides_arbitration() -> None:
    stream = _stream()
    suspend = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        reason="kill-switch",
    )
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
        reason="kill-line",
        issued_at=_instant(2_000),
    )
    forward = _ok(
        dispatch_ranked_controls(
            [
                _candidate(suspend, arrival_ordinal=0),
                _candidate(flatten, arrival_ordinal=1),
            ],
            _rank_table(),
            stream=stream,
            arbitration_seed="arrival-a",
        )
    )
    reverse = _ok(
        dispatch_ranked_controls(
            [
                _candidate(flatten, arrival_ordinal=0),
                _candidate(suspend, arrival_ordinal=1),
            ],
            _rank_table(),
            stream=stream,
            arbitration_seed="arrival-a",
        )
    )
    assert {p.record.action_kind for p in forward.emit} == {
        p.record.action_kind for p in reverse.emit
    }
    assert forward.arbitration is not None and reverse.arbitration is not None
    assert forward.arbitration.arbitration_record_ref == reverse.arbitration.arbitration_record_ref
    assert forward.arrival_order_ignored is True


def test_lower_rank_cannot_undo_higher_protection() -> None:
    # Higher-ranked resume (0) must not suppress lower-ranked flatten (1) —
    # that would reduce protection the flatten would have delivered.
    rows = [
        _rank_row(ControlActionKind.RESUME, 0),
        _rank_row(ControlActionKind.FLATTEN, 1),
        _rank_row(ControlActionKind.SUSPEND_NEW, 2),
        _rank_row(ControlActionKind.DRAIN, 3),
    ]
    table = _ok(ControlRankTable.try_create(rows))
    stream = _stream()
    resume = _action(ControlActionKind.RESUME, rank=0)
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
        issued_at=_instant(2_000),
    )
    plan = _ok(
        dispatch_ranked_controls(
            [_candidate(resume), _candidate(flatten)],
            table,
            stream=stream,
            arbitration_seed="invariant",
        )
    )
    kinds = {p.record.action_kind for p in plan.emit}
    assert kinds == {ControlActionKind.RESUME, ControlActionKind.FLATTEN}
    assert plan.suppressed == ()


def test_venue_resident_tier1_stays_outside_ordering() -> None:
    stream = _stream()
    suspend = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        reason="kill-switch",
    )
    # Venue-resident protective stop observation — tagged outside AD-37 ordering.
    # Authority may be book_policy (node mirror of the fill); origin alone excludes it.
    tier1 = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="venue-stop",
        rank=1,
        reason="venue-resident-stop",
        trigger_class="venue_resident_protective_stop",
        issued_at=_instant(2_000),
    )
    candidates = [
        _candidate(suspend, arrival_ordinal=0),
        _candidate(
            tier1,
            origin=CandidateOrigin.VENUE_RESIDENT_TIER1,
            arrival_ordinal=1,
        ),
    ]
    inside, outside = _ok(exclude_venue_resident_tier1(candidates))
    assert len(inside) == 1
    assert len(outside) == 1
    assert outside[0].origin is CandidateOrigin.VENUE_RESIDENT_TIER1

    plan = _ok(
        dispatch_ranked_controls(
            candidates,
            _rank_table(),
            stream=stream,
            arbitration_seed="tier1",
        )
    )
    assert {p.record.action_kind for p in plan.emit} == {ControlActionKind.SUSPEND_NEW}
    assert len(plan.venue_resident_outside) == 1
    assert plan.venue_resident_outside[0].origin is CandidateOrigin.VENUE_RESIDENT_TIER1


# --- AC2: dead-wire satisfaction ---------------------------------------------


def test_suspend_and_drain_are_never_auto_under_dead_wire() -> None:
    suspend = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        reason="kill-switch",
    )
    drain = _action(
        ControlActionKind.DRAIN,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=2,
        reason="drain",
        issued_at=_instant(2_000),
    )
    for record in (suspend, drain):
        for verdict in (
            ReconciliationVerdict.RECONCILED,
            ReconciliationVerdict.DRIFT,
            ReconciliationVerdict.UNKNOWN,
            ReconciliationVerdict.OUT_OF_LOOKBACK,
        ):
            checked = _ok(
                check_dead_wire_satisfaction(
                    record,
                    verdict=verdict,
                    scope_flat=True,
                    command_outcome_observed=True,
                )
            )
            assert checked.predicate is SatisfactionPredicate.NEVER_AUTO
            assert checked.status is StandingIntentStatus.OPEN or (
                checked.status is StandingIntentStatus.HELD_ALARM
            )
            if verdict is ReconciliationVerdict.RECONCILED:
                assert checked.status is StandingIntentStatus.OPEN
            else:
                # never-auto short-circuits before verdict branching in evaluate —
                # stays OPEN (not held-alarm) because never-auto ignores verdict.
                assert checked.status is StandingIntentStatus.OPEN
            assert checked.command_outcome_satisfies is False


def test_flatten_requires_scope_flat_at_reconciled_verdict() -> None:
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
    )
    # Command outcome alone — not enough.
    observed = _ok(
        check_dead_wire_satisfaction(
            flatten,
            verdict=ReconciliationVerdict.RECONCILED,
            scope_flat=False,
            command_outcome_observed=True,
        )
    )
    assert observed.status is StandingIntentStatus.OPEN
    assert observed.command_outcome_satisfies is False
    assert command_outcome_never_satisfies() is True

    satisfied = _ok(
        check_dead_wire_satisfaction(
            flatten,
            verdict=ReconciliationVerdict.RECONCILED,
            scope_flat=True,
            command_outcome_observed=True,
        )
    )
    assert satisfied.status is StandingIntentStatus.SATISFIED
    assert satisfied.command_outcome_satisfies is False


def test_drift_unknown_out_of_lookback_hold_and_alarm() -> None:
    dispatcher = _dispatcher()
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
    )
    for verdict in (
        ReconciliationVerdict.DRIFT,
        ReconciliationVerdict.UNKNOWN,
        ReconciliationVerdict.OUT_OF_LOOKBACK,
    ):
        checked = _ok(
            dispatcher.check_satisfaction(
                flatten,
                verdict=verdict,
                scope_flat=True,
                command_outcome_observed=True,
            )
        )
        assert checked.status is StandingIntentStatus.HELD_ALARM
        assert checked.alarm is True
        assert checked.command_outcome_satisfies is False
    assert len(dispatcher.alarms) == 3
    assert all(a["reason"] == "standing-intent-held-alarm" for a in dispatcher.alarms)


# --- AC3: journal refusal → extent → UNDELIVERABLE; re-decide never retry ----


def test_journal_success_persists_standing_intent() -> None:
    dispatcher = _dispatcher()
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
    )
    persisted = _ok(dispatcher.admit_protective_act(flatten, journal_result=True))
    assert persisted.disposition is IntentPersistDisposition.JOURNALED
    assert len(dispatcher.standing_intents) == 1
    assert dispatcher.undeliverable == ()


def test_journal_refusal_falls_back_to_reserved_extent() -> None:
    dispatcher = _dispatcher()
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
    )
    persisted = _ok(
        dispatcher.admit_protective_act(
            flatten,
            journal_result=unpersistable("evidence room full"),
        )
    )
    assert persisted.disposition is IntentPersistDisposition.EXTENT
    assert dispatcher.extent.used == 1
    assert len(dispatcher.standing_intents) == 1
    assert dispatcher.undeliverable == ()


def test_journal_and_extent_failure_is_undeliverable_and_alarmed() -> None:
    extent = _extent(capacity=1)
    # Fill the extent first.
    filler = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        reason="fill-extent",
    )
    _ok(
        persist_protective_intent(
            filler,
            journal_result=unpersistable("full"),
            extent=extent,
        )
    )
    assert extent.remaining == 0

    dispatcher = _ok(
        StreamProtectionDispatcher.try_create(
            stream=_stream(),
            rank_table=_rank_table(),
            extent=extent,
        )
    )
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
        issued_at=_instant(2_000),
    )
    persisted = _ok(
        dispatcher.admit_protective_act(
            flatten,
            journal_result=unpersistable("evidence room full"),
        )
    )
    assert persisted.disposition is IntentPersistDisposition.UNDELIVERABLE
    assert persisted.undeliverable is not None
    assert persisted.undeliverable.alarm_class == UNDELIVERABLE_ALARM_CLASS
    assert len(dispatcher.undeliverable) == 1
    assert dispatcher.alarms[0]["alarm_class"] == UNDELIVERABLE_ALARM_CLASS
    assert dispatcher.standing_intents == ()


def test_redecide_never_blind_retry() -> None:
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
    )
    held = _ok(
        redecide_protective_intent(
            flatten,
            verdict=ReconciliationVerdict.UNKNOWN,
            scope_flat=False,
        )
    )
    assert held.status is StandingIntentStatus.HELD_ALARM

    still_open = _ok(
        redecide_protective_intent(
            flatten,
            verdict=ReconciliationVerdict.RECONCILED,
            scope_flat=False,
        )
    )
    assert still_open.status is StandingIntentStatus.OPEN

    cleared = _ok(
        redecide_protective_intent(
            flatten,
            verdict=ReconciliationVerdict.RECONCILED,
            scope_flat=True,
        )
    )
    assert cleared.status is StandingIntentStatus.SATISFIED
    # Same record fingerprint — re-decide evaluates state; a later dispatch would
    # mint a new command identity (re-deciding ≠ retrying).
    assert held.record_fingerprint == cleared.record_fingerprint


def test_dispatcher_evaluate_wires_stream_table() -> None:
    dispatcher = _dispatcher()
    suspend = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        reason="kill-switch",
    )
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
        issued_at=_instant(2_000),
    )
    plan = _ok(
        dispatcher.evaluate(
            [_candidate(suspend), _candidate(flatten)],
            arbitration_seed="wired",
        )
    )
    assert {p.record.action_kind for p in plan.emit} == {
        ControlActionKind.SUSPEND_NEW,
        ControlActionKind.FLATTEN,
    }
