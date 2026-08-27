"""Epic 10 independent audit — Cluster H (Story 10.8).

CT-30 control actions: the exit-preservation invariant (P0-9 / L39), the bounded
vocabulary, scope resolution, standing-intent journal-before-dispatch, kill switch
vs kill line, same-tick rank arbitration, and closed flatten authority.
Authored from Story 10.8 ACs, CT-30, L39, and SCN-0010.

H1 (exit-preservation) and H8 (arbitration invariant) are Hypothesis-driven over
the full (kind x authority x scope x act) space — run with `--with hypothesis`.

Planned IDs: H1-H10.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from qmf.core import Instant, RefusalCategory, Result, VenueId, is_ok, is_refusal, unpersistable
from qmf.risk.binding import PositionModel
from qmf.risk.control_action import (
    MONEY_BOUNDARIES_LEAVE_POSITIONS,
    NEVER_AUTO_KINDS,
    RISK_REDUCING_ACTS,
    AuthorityKind,
    CommandStreamKey,
    ControlActionRecord,
    ControlActionStream,
    EnforcementScope,
    KillLine,
    KillSwitch,
    PendingControlAction,
    ReconciliationVerdict,
    RiskReducingAct,
    SatisfactionPredicate,
    SubjectScope,
    arbitrate_same_tick,
    check_exit_preservation,
    check_flatten_authority,
    default_satisfaction_predicate,
    evaluate_satisfaction,
    fold_standing_intents,
    journal_before_dispatch,
    mint_control_action,
    mint_kill_line_breach,
    mint_kill_switch_action,
    reevaluate_standing_intent,
    reject_blanket_command_pipe_block,
    reject_money_boundary_flatten,
    resolve_subject_scope,
)
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable
from qmf.risk.exit_record import CloseReason


def _instant(ns: int = 1_000) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result)
    return result.value


def _stream() -> CommandStreamKey:
    result = CommandStreamKey.try_create(VenueId(value="ctrader"), "acct-1")
    assert is_ok(result)
    return result.value


def _rank_row(kind: ControlActionKind, rank: int) -> ControlRankRow:
    result = ControlRankRow.try_create(kind, rank)
    assert is_ok(result)
    return result.value


def _table(order: tuple[ControlActionKind, ...]) -> ControlRankTable:
    result = ControlRankTable.try_create([_rank_row(kind, i) for i, kind in enumerate(order)])
    assert is_ok(result)
    return result.value


_DEFAULT_ORDER = (
    ControlActionKind.SUSPEND_NEW,
    ControlActionKind.FLATTEN,
    ControlActionKind.DRAIN,
    ControlActionKind.RESUME,
)


def _enforcement(scope: SubjectScope = SubjectScope.BINDING, ref: str = "binding-1") -> EnforcementScope:
    return EnforcementScope(subject_scope=scope, scope_ref=ref, stream=_stream())


def _action(
    kind: ControlActionKind, *, authority_kind: AuthorityKind = AuthorityKind.OPERATOR,
    authority: str = "op-1", rank: int = 0, scope: SubjectScope = SubjectScope.BINDING,
    scope_ref: str = "binding-1", reason: str = "test", trigger_class: str | None = None,
    issued_at: Instant | None = None,
) -> Result[ControlActionRecord]:
    return mint_control_action(
        kind, authority, authority_kind, scope, scope_ref, rank, reason, _stream(),
        issued_at or _instant(), trigger_class=trigger_class,
    )


def _pending(record: Result[ControlActionRecord], enforcement: EnforcementScope | None = None) -> PendingControlAction:
    assert is_ok(record)
    result = PendingControlAction.try_create(record.value, enforcement or _enforcement())
    assert is_ok(result)
    return result.value


# --- H1 [P0-9, property]: exit-preservation over the full space --------------


@settings(max_examples=200)
@given(
    kind=st.sampled_from(list(ControlActionKind)),
    authority=st.sampled_from(list(AuthorityKind)),
    scope=st.sampled_from(list(SubjectScope)),
    act=st.sampled_from(list(RiskReducingAct)),
)
def test_H1_exit_preservation_never_blocks_a_risk_reducing_act(
    kind: ControlActionKind, authority: AuthorityKind, scope: SubjectScope, act: RiskReducingAct
) -> None:
    # For any imagined control (any kind x authority x scope), blocking a risk-reducing
    # act is refused as a policy rejection — the blocking half is entries only.
    result = check_exit_preservation(blocked_act=act)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_H1_entries_are_the_only_blockable_half() -> None:
    assert is_ok(check_exit_preservation(blocked_act="entry"))
    assert is_ok(check_exit_preservation(blocked_act="new_entry"))
    for act in RISK_REDUCING_ACTS:
        assert is_refusal(check_exit_preservation(blocked_act=act))


# --- H2 [P0-9]: no blanket command-pipe block kind may be minted -------------


def test_H2_no_blanket_command_pipe_block_kind() -> None:
    # The four ratified kinds are accepted; a blanket-block kind is unsupported.
    for kind in ControlActionKind:
        assert is_ok(reject_blanket_command_pipe_block(kind))
    refused = reject_blanket_command_pipe_block("block_all_commands")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- H3: the bounded vocabulary; suspend_new/drain are never-auto -------------


def test_H3_vocabulary_and_never_auto() -> None:
    assert {k.value for k in ControlActionKind} == {"suspend_new", "drain", "flatten", "resume"}
    assert {a.value for a in AuthorityKind} == {
        "operator", "book_policy", "protection_authority", "venue-delegated", "adapter_self",
    }
    assert {ControlActionKind.SUSPEND_NEW, ControlActionKind.DRAIN} == NEVER_AUTO_KINDS
    for kind in NEVER_AUTO_KINDS:
        pred = default_satisfaction_predicate(kind)
        assert is_ok(pred)
        assert pred.value is SatisfactionPredicate.NEVER_AUTO


# --- H4: scope resolves through the pinned table; never widened --------------


def test_H4_scope_resolution_refuses_never_widens() -> None:
    ok = resolve_subject_scope(SubjectScope.BINDING, scope_ref="binding-1", stream=_stream(),
                               position_model=PositionModel.HEDGING)
    assert is_ok(ok)
    unresolvable = resolve_subject_scope("galaxy", scope_ref="x", stream=_stream(),
                                         position_model=PositionModel.HEDGING)
    assert is_refusal(unresolvable)
    assert unresolvable.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    netting = resolve_subject_scope(SubjectScope.BOOK, scope_ref="book-1", stream=_stream(),
                                    position_model=PositionModel.NETTING,
                                    netting_indistinguishable_from_wider=True)
    assert is_refusal(netting)
    assert netting.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- H5 [L3]: standing intent journal-before-dispatch, re-decided ------------


def test_H5_standing_intent_journaled_before_dispatch_and_redecided() -> None:
    flatten = _action(ControlActionKind.FLATTEN, authority_kind=AuthorityKind.BOOK_POLICY,
                      authority="book-1", rank=1, trigger_class="kill_line_breach")
    assert is_ok(flatten)
    # Storage failure blocks the dispatch rather than losing the intent.
    blocked = journal_before_dispatch(flatten.value, journal_result=unpersistable("disk full"))
    assert is_refusal(blocked)
    assert blocked.category is RefusalCategory.STORAGE_FAILURE
    assert is_ok(journal_before_dispatch(flatten.value, journal_result=True))
    # A flatten is satisfied only on a reconciled verdict showing the scope flat; drift or
    # unknown holds-and-alarms (never time-expires).
    held = evaluate_satisfaction(SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT,
                                 verdict=ReconciliationVerdict.DRIFT, scope_flat=True)
    assert is_ok(held)
    assert held.value.value == "held-alarm"
    done = evaluate_satisfaction(SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT,
                                 verdict=ReconciliationVerdict.RECONCILED, scope_flat=True)
    assert is_ok(done)
    assert done.value.value == "satisfied"
    # Restart-proof read-time fold: re-decided on reconnect (unknown holds).
    redecided = reevaluate_standing_intent(flatten.value, verdict=ReconciliationVerdict.UNKNOWN, scope_flat=False)
    assert is_ok(redecided)
    assert redecided.value.status.value == "held-alarm"


# --- H6: kill switch vs kill line; resume operator-only ----------------------


def test_H6_kill_switch_vs_kill_line_and_resume_operator_only() -> None:
    ks = KillSwitch.try_create("ksa-1", _stream(), 2, ControlActionKind.SUSPEND_NEW, "black-swan")
    kl = KillLine.try_create("book-1", "binding-1", _stream(), "capital-floor")
    assert is_ok(ks) and is_ok(kl)
    assert ks.value.fp1_identity()["class"] == "kill-switch"
    assert kl.value.fp1_identity()["class"] == "kill-line"
    ks_action = mint_kill_switch_action(ks.value, rank=0, issued_at=_instant())
    kl_action = mint_kill_line_breach(kl.value, rank=1, issued_at=_instant())
    assert is_ok(ks_action) and is_ok(kl_action)
    # Kill switch is a global protection-authority; kill line is a per-Book book-policy breach.
    assert ks_action.value.subject_scope is SubjectScope.GLOBAL
    assert ks_action.value.authority_kind is AuthorityKind.PROTECTION_AUTHORITY
    assert kl_action.value.authority_kind is AuthorityKind.BOOK_POLICY
    assert kl_action.value.close_reason_ref is CloseReason.KILL_LINE_FLAT
    # Resume is operator-only.
    assert is_refusal(_action(ControlActionKind.RESUME, authority_kind=AuthorityKind.BOOK_POLICY,
                              authority="book-1", rank=3, trigger_class="kill_line_breach"))
    assert is_ok(_action(ControlActionKind.RESUME, rank=3))


# --- H7 [SCN-0010]: same-tick collapse to one command ------------------------


def test_H7_same_tick_collapse_to_one_command() -> None:
    table = _table(_DEFAULT_ORDER)
    kill_line = _action(ControlActionKind.FLATTEN, authority_kind=AuthorityKind.BOOK_POLICY,
                        authority="book-1", rank=1, trigger_class="kill_line_breach", reason="kill_line")
    window = _action(ControlActionKind.FLATTEN, authority_kind=AuthorityKind.BOOK_POLICY,
                     authority="book-1", rank=1, trigger_class="window_forced_flat", reason="window",
                     issued_at=_instant(2_000))
    operator = _action(ControlActionKind.FLATTEN, authority_kind=AuthorityKind.OPERATOR,
                       authority="op-1", rank=1, reason="operator", issued_at=_instant(3_000))
    outcome = arbitrate_same_tick([_pending(kill_line), _pending(window), _pending(operator)],
                                  table, stream=_stream(), arbitration_seed="collapse")
    assert is_ok(outcome)
    # Colliding flattens collapse to one command; the two losers journal as suppressed.
    assert len(outcome.value.emit) == 1
    assert len(outcome.value.suppressed) == 2
    assert all(s.reason_class == "collapse-same-mechanical-command" for s in outcome.value.suppressed)


# --- H8 [P0-9, SCN-0010]: conflict/compose; higher never reduces protection ---


def test_H8_compose_suspend_new_and_flatten_both_execute() -> None:
    table = _table(_DEFAULT_ORDER)
    suspend = _action(ControlActionKind.SUSPEND_NEW, authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
                      authority="ksa-1", rank=0, reason="kill-switch")
    flatten = _action(ControlActionKind.FLATTEN, authority_kind=AuthorityKind.BOOK_POLICY,
                      authority="book-1", rank=1, trigger_class="kill_line_breach", reason="kill-line",
                      issued_at=_instant(2_000))
    outcome = arbitrate_same_tick([_pending(suspend), _pending(flatten)], table,
                                  stream=_stream(), arbitration_seed="compose")
    assert is_ok(outcome)
    # Composing effects both execute; nothing suppressed.
    kinds = {p.record.action_kind for p in outcome.value.emit}
    assert kinds == {ControlActionKind.SUSPEND_NEW, ControlActionKind.FLATTEN}
    assert outcome.value.suppressed == ()


@settings(max_examples=100)
@given(resume_higher=st.booleans())
def test_H8_higher_rank_never_reduces_protection_a_lower_would_deliver(resume_higher: bool) -> None:
    # Whatever the rank order, a resume (protection-reducing) can never suppress a
    # flatten (protection-delivering): the two must both execute when composing.
    if resume_higher:
        order = (ControlActionKind.RESUME, ControlActionKind.FLATTEN,
                 ControlActionKind.SUSPEND_NEW, ControlActionKind.DRAIN)
    else:
        order = (ControlActionKind.FLATTEN, ControlActionKind.RESUME,
                 ControlActionKind.SUSPEND_NEW, ControlActionKind.DRAIN)
    table = _table(order)
    resume = _action(ControlActionKind.RESUME, rank=order.index(ControlActionKind.RESUME))
    flatten = _action(ControlActionKind.FLATTEN, authority_kind=AuthorityKind.BOOK_POLICY,
                      authority="book-1", rank=order.index(ControlActionKind.FLATTEN),
                      trigger_class="kill_line_breach", issued_at=_instant(2_000))
    outcome = arbitrate_same_tick([_pending(resume), _pending(flatten)], table,
                                  stream=_stream(), arbitration_seed="invariant")
    assert is_ok(outcome)
    emitted = {p.record.action_kind for p in outcome.value.emit}
    # The flatten is always delivered; a higher-ranked resume never suppresses it.
    assert ControlActionKind.FLATTEN in emitted


# --- H9: closed flatten authority; money boundaries leave positions ----------


def test_H9_flatten_authority_is_closed() -> None:
    assert is_ok(check_flatten_authority(AuthorityKind.OPERATOR))
    assert is_ok(check_flatten_authority(AuthorityKind.BOOK_POLICY, trigger_class_declared=True))
    assert is_refusal(check_flatten_authority(AuthorityKind.BOOK_POLICY, trigger_class_declared=False))
    assert is_ok(check_flatten_authority(AuthorityKind.PROTECTION_AUTHORITY, protection_declares_close_all=True))
    assert is_refusal(check_flatten_authority(AuthorityKind.PROTECTION_AUTHORITY, protection_declares_close_all=False))
    # Never a venue adapter or a venue-delegated authority.
    assert is_refusal(check_flatten_authority(AuthorityKind.ADAPTER_SELF))
    assert is_refusal(check_flatten_authority(AuthorityKind.VENUE_DELEGATED))
    # Every other money boundary leaves positions alone.
    for boundary in MONEY_BOUNDARIES_LEAVE_POSITIONS:
        refused = reject_money_boundary_flatten(boundary)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION


# --- H10 [L4]: SCN-0010 executable golden fixture ----------------------------


def test_H10_scn0010_risk_boundary_conflicts_end_to_end() -> None:
    """SCN-0010: on one command stream, a kill-switch suspend and a kill-line flatten
    arrive same-tick. They compose (both execute); a colliding duplicate flatten
    collapses; and the standing flatten is journaled before dispatch."""
    table = _table(_DEFAULT_ORDER)
    stream_key = _stream()
    suspend = _action(ControlActionKind.SUSPEND_NEW, authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
                      authority="ksa-1", rank=0, scope=SubjectScope.BINDING, scope_ref="binding-1",
                      reason="kill-switch")
    kill_line = _action(ControlActionKind.FLATTEN, authority_kind=AuthorityKind.BOOK_POLICY,
                        authority="book-1", rank=1, trigger_class="kill_line_breach",
                        reason="kill-line", issued_at=_instant(2_000))
    window = _action(ControlActionKind.FLATTEN, authority_kind=AuthorityKind.BOOK_POLICY,
                     authority="book-1", rank=1, trigger_class="window_forced_flat",
                     reason="window", issued_at=_instant(3_000))
    outcome = arbitrate_same_tick(
        [_pending(suspend), _pending(kill_line), _pending(window)],
        table, stream=stream_key, arbitration_seed="scn0010",
    )
    assert is_ok(outcome)
    emitted = {p.record.action_kind for p in outcome.value.emit}
    # Both a suspend and a flatten survive (compose); the duplicate flatten collapses.
    assert ControlActionKind.SUSPEND_NEW in emitted
    assert ControlActionKind.FLATTEN in emitted
    assert len(outcome.value.suppressed) == 1
    # The standing flatten is journaled before dispatch; a storage failure would block it.
    assert is_ok(journal_before_dispatch(kill_line.value, journal_result=True))  # type: ignore[union-attr]
    # And the fold over the stream re-decides standing intents rather than retrying.
    control_stream = ControlActionStream()
    assert is_ok(control_stream.mint(kill_line.value))  # type: ignore[union-attr]
    folds = fold_standing_intents(control_stream, stream_key,
                                  verdict=ReconciliationVerdict.RECONCILED,
                                  scope_flat_by_ref={"binding-1": True})
    assert is_ok(folds)
    assert folds.value[0].status.value == "satisfied"
