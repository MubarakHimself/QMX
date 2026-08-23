"""Story 10.8 — CT-30 control actions, exit-preservation, kill switch vs kill line.

Covers the bounded action vocabulary, L39 exit-preservation, standing-intent fold,
kill-switch/kill-line split, flatten authority, scope resolution, and same-tick
rank arbitration (CT-30; DEC-0150, DEC-0151; SCN-0010).
"""

from __future__ import annotations

from qmf.core import (
    Instant,
    RefusalCategory,
    Result,
    VenueId,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.risk.binding import PositionModel
from qmf.risk.control_action import (
    ACTION_CLOSE_REASON_MAPPING,
    NEVER_AUTO_KINDS,
    RISK_REDUCING_ACTS,
    AuthorityKind,
    CommandStreamKey,
    ControlActionRecord,
    ControlActionStream,
    EnforcementScope,
    KillLine,
    KillSwitch,
    MoneyBoundaryKind,
    PendingControlAction,
    ReconciliationVerdict,
    RiskReducingAct,
    SatisfactionPredicate,
    SubjectScope,
    arbitrate_same_tick,
    check_exit_preservation,
    check_flatten_authority,
    close_reason_for,
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


def _venue() -> VenueId:
    result = VenueId.try_create("ctrader")
    assert is_ok(result)
    return result.value


def _stream() -> CommandStreamKey:
    result = CommandStreamKey.try_create(_venue(), "acct-1")
    assert is_ok(result)
    return result.value


def _rank_row(kind: ControlActionKind, rank: int) -> ControlRankRow:
    result = ControlRankRow.try_create(kind, rank)
    assert is_ok(result)
    return result.value


def _rank_table() -> ControlRankTable:
    # suspend_new (kill switch) outranks flatten (kill line), matching SCN-0010
    # class ordering: protection > forced flats.
    rows = [
        _rank_row(ControlActionKind.SUSPEND_NEW, 0),
        _rank_row(ControlActionKind.FLATTEN, 1),
        _rank_row(ControlActionKind.DRAIN, 2),
        _rank_row(ControlActionKind.RESUME, 3),
    ]
    result = ControlRankTable.try_create(rows)
    assert is_ok(result)
    return result.value


def _enforcement(
    scope: SubjectScope = SubjectScope.BINDING, ref: str = "binding-1"
) -> EnforcementScope:
    return EnforcementScope(subject_scope=scope, scope_ref=ref, stream=_stream())


def _action(
    kind: ControlActionKind,
    *,
    authority_kind: AuthorityKind = AuthorityKind.OPERATOR,
    authority: str = "op-1",
    rank: int = 0,
    scope: SubjectScope = SubjectScope.BINDING,
    scope_ref: str = "binding-1",
    reason: str = "test",
    trigger_class: str | None = None,
    protection_declares_close_all: bool = False,
    issued_at: Instant | None = None,
) -> Result[ControlActionRecord]:
    return mint_control_action(
        kind,
        authority,
        authority_kind,
        scope,
        scope_ref,
        rank,
        reason,
        _stream(),
        issued_at or _instant(),
        trigger_class=trigger_class,
        protection_declares_close_all=protection_declares_close_all,
    )


# --- vocabulary and exit-preservation ----------------------------------------


def test_action_kinds_are_exactly_four() -> None:
    assert {k.value for k in ControlActionKind} == {
        "suspend_new",
        "drain",
        "flatten",
        "resume",
    }


def test_exit_preservation_refuses_blocking_risk_reducing_acts() -> None:
    for act in RISK_REDUCING_ACTS:
        result = check_exit_preservation(blocked_act=act)
        assert is_refusal(result)
        assert result.category is RefusalCategory.POLICY_REJECTION
    assert is_ok(check_exit_preservation(blocked_act="entry"))
    assert is_ok(check_exit_preservation(blocked_act="new_entry"))
    assert is_refusal(check_exit_preservation(blocked_act="not-an-act"))


def test_blanket_command_pipe_block_kind_cannot_be_minted() -> None:
    assert is_ok(reject_blanket_command_pipe_block(ControlActionKind.SUSPEND_NEW))
    refused = reject_blanket_command_pipe_block("block_all_commands")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_suspend_new_and_drain_are_never_auto() -> None:
    assert {
        ControlActionKind.SUSPEND_NEW,
        ControlActionKind.DRAIN,
    } == NEVER_AUTO_KINDS
    for kind in NEVER_AUTO_KINDS:
        pred = default_satisfaction_predicate(kind)
        assert is_ok(pred)
        assert pred.value is SatisfactionPredicate.NEVER_AUTO
    bad = mint_control_action(
        ControlActionKind.SUSPEND_NEW,
        "adapter-1",
        AuthorityKind.ADAPTER_SELF,
        SubjectScope.ACCOUNT,
        "acct-1",
        2,
        "session",
        _stream(),
        _instant(),
        satisfaction_predicate=SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT,
    )
    assert is_refusal(bad)


def test_mint_control_action_carries_authority_scope_predicate() -> None:
    result = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        scope=SubjectScope.GLOBAL,
        scope_ref="global",
    )
    assert is_ok(result)
    record = result.value
    assert record.action_kind is ControlActionKind.SUSPEND_NEW
    assert record.authority_kind is AuthorityKind.PROTECTION_AUTHORITY
    assert record.subject_scope is SubjectScope.GLOBAL
    assert record.satisfaction_predicate is SatisfactionPredicate.NEVER_AUTO
    assert record.close_reason_ref is None


# --- flatten authority and close-reason mapping ------------------------------


def test_flatten_authority_closed_set() -> None:
    assert is_ok(check_flatten_authority(AuthorityKind.OPERATOR))
    assert is_refusal(
        check_flatten_authority(AuthorityKind.BOOK_POLICY, trigger_class_declared=False)
    )
    assert is_ok(check_flatten_authority(AuthorityKind.BOOK_POLICY, trigger_class_declared=True))
    assert is_refusal(
        check_flatten_authority(
            AuthorityKind.PROTECTION_AUTHORITY, protection_declares_close_all=False
        )
    )
    assert is_ok(
        check_flatten_authority(
            AuthorityKind.PROTECTION_AUTHORITY, protection_declares_close_all=True
        )
    )
    assert is_refusal(check_flatten_authority(AuthorityKind.ADAPTER_SELF))
    assert is_refusal(check_flatten_authority(AuthorityKind.VENUE_DELEGATED))


def test_adapter_self_cannot_flatten() -> None:
    result = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.ADAPTER_SELF,
        authority="adapter-1",
        rank=1,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_resume_is_operator_only() -> None:
    bad = _action(
        ControlActionKind.RESUME,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=3,
        trigger_class="kill_line_breach",
    )
    assert is_refusal(bad)
    good = _action(ControlActionKind.RESUME, rank=3)
    assert is_ok(good)


def test_money_boundaries_leave_positions_alone() -> None:
    for boundary in MoneyBoundaryKind:
        result = reject_money_boundary_flatten(boundary)
        assert is_refusal(result)
        assert result.category is RefusalCategory.POLICY_REJECTION


def test_close_reason_mapping_kills_apart() -> None:
    kill_line = close_reason_for(ControlActionKind.FLATTEN, AuthorityKind.BOOK_POLICY)
    kill_switch = close_reason_for(ControlActionKind.FLATTEN, AuthorityKind.PROTECTION_AUTHORITY)
    assert is_ok(kill_line) and is_ok(kill_switch)
    assert kill_line.value is CloseReason.KILL_LINE_FLAT
    assert kill_switch.value is CloseReason.PROTECTION_FORCED_FLAT
    assert kill_line.value is not kill_switch.value
    assert ACTION_CLOSE_REASON_MAPPING[("flatten", "book_policy")] is CloseReason.KILL_LINE_FLAT


# --- scope resolution --------------------------------------------------------


def test_scope_resolution_refuses_unresolvable_and_netting_widen() -> None:
    stream = _stream()
    ok = resolve_subject_scope(
        SubjectScope.BINDING,
        scope_ref="binding-1",
        stream=stream,
        position_model=PositionModel.HEDGING,
    )
    assert is_ok(ok)
    assert ok.value.table_version == 1

    unresolvable = resolve_subject_scope(
        "galaxy",
        scope_ref="x",
        stream=stream,
        position_model=PositionModel.HEDGING,
    )
    assert is_refusal(unresolvable)
    assert unresolvable.category is RefusalCategory.UNSUPPORTED_CAPABILITY

    netting = resolve_subject_scope(
        SubjectScope.BOOK,
        scope_ref="book-1",
        stream=stream,
        position_model=PositionModel.NETTING,
        netting_indistinguishable_from_wider=True,
    )
    assert is_refusal(netting)
    assert netting.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- standing intent ---------------------------------------------------------


def test_journal_before_dispatch_blocks_on_storage_failure() -> None:
    minted = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
    )
    assert is_ok(minted)
    blocked = journal_before_dispatch(minted.value, journal_result=unpersistable("disk full"))
    assert is_refusal(blocked)
    assert blocked.category is RefusalCategory.STORAGE_FAILURE
    ok = journal_before_dispatch(minted.value, journal_result=True)
    assert is_ok(ok)


def test_flatten_satisfaction_requires_reconciled_flat() -> None:
    held = evaluate_satisfaction(
        SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT,
        verdict=ReconciliationVerdict.DRIFT,
        scope_flat=True,
    )
    assert is_ok(held)
    assert held.value.value == "held-alarm"

    open_status = evaluate_satisfaction(
        SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT,
        verdict=ReconciliationVerdict.RECONCILED,
        scope_flat=False,
    )
    assert is_ok(open_status)
    assert open_status.value.value == "open"

    done = evaluate_satisfaction(
        SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT,
        verdict=ReconciliationVerdict.RECONCILED,
        scope_flat=True,
    )
    assert is_ok(done)
    assert done.value.value == "satisfied"


def test_standing_intent_fold_and_redecide() -> None:
    stream = ControlActionStream()
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
    )
    assert is_ok(flatten)
    assert is_ok(stream.mint(flatten.value))

    unknown = reevaluate_standing_intent(
        flatten.value,
        verdict=ReconciliationVerdict.UNKNOWN,
        scope_flat=False,
    )
    assert is_ok(unknown)
    assert unknown.value.status.value == "held-alarm"

    folds = fold_standing_intents(
        stream,
        _stream(),
        verdict=ReconciliationVerdict.RECONCILED,
        scope_flat_by_ref={"binding-1": True},
    )
    assert is_ok(folds)
    assert len(folds.value) == 1
    assert folds.value[0].status.value == "satisfied"


def test_never_auto_clears_only_by_operator_resume() -> None:
    stream = ControlActionStream()
    suspend = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        scope=SubjectScope.GLOBAL,
        scope_ref="global",
    )
    assert is_ok(suspend)
    assert is_ok(stream.mint(suspend.value))

    still_open = fold_standing_intents(stream, _stream())
    assert is_ok(still_open)
    assert still_open.value[0].status.value == "open"

    resume = _action(
        ControlActionKind.RESUME,
        rank=3,
        scope=SubjectScope.GLOBAL,
        scope_ref="global",
        issued_at=_instant(2_000),
    )
    assert is_ok(resume)
    assert is_ok(stream.mint(resume.value))
    cleared = fold_standing_intents(stream, _stream())
    assert is_ok(cleared)
    assert cleared.value[0].status.value == "satisfied"


# --- kill switch vs kill line ------------------------------------------------


def test_kill_switch_and_kill_line_are_distinct() -> None:
    stream = _stream()
    ks = KillSwitch.try_create("ksa-1", stream, 2, ControlActionKind.SUSPEND_NEW, "black-swan")
    kl = KillLine.try_create("book-1", "binding-1", stream, "capital-floor")
    assert is_ok(ks) and is_ok(kl)
    assert ks.value.fp1_identity()["class"] == "kill-switch"
    assert kl.value.fp1_identity()["class"] == "kill-line"
    assert ks.value.fp1_identity()["class"] != kl.value.fp1_identity()["class"]

    ks_action = mint_kill_switch_action(ks.value, rank=0, issued_at=_instant())
    kl_action = mint_kill_line_breach(kl.value, rank=1, issued_at=_instant())
    assert is_ok(ks_action) and is_ok(kl_action)
    assert ks_action.value.authority_kind is AuthorityKind.PROTECTION_AUTHORITY
    assert ks_action.value.subject_scope is SubjectScope.GLOBAL
    assert kl_action.value.authority_kind is AuthorityKind.BOOK_POLICY
    assert kl_action.value.close_reason_ref is CloseReason.KILL_LINE_FLAT
    assert kl_action.value.trigger_class == "kill_line_breach"


def test_kill_switch_flatten_requires_close_all_declaration() -> None:
    stream = _stream()
    ks = KillSwitch.try_create("ksa-1", stream, 4, ControlActionKind.FLATTEN, "severity")
    assert is_ok(ks)
    refused = mint_kill_switch_action(
        ks.value, rank=0, issued_at=_instant(), protection_declares_close_all=False
    )
    assert is_refusal(refused)
    ok = mint_kill_switch_action(
        ks.value, rank=0, issued_at=_instant(), protection_declares_close_all=True
    )
    assert is_ok(ok)
    assert ok.value.close_reason_ref is CloseReason.PROTECTION_FORCED_FLAT


# --- same-tick arbitration ---------------------------------------------------


def _pending(
    record_result: Result[ControlActionRecord],
    enforcement: EnforcementScope | None = None,
) -> PendingControlAction:
    assert is_ok(record_result)
    pending = PendingControlAction.try_create(record_result.value, enforcement or _enforcement())
    assert is_ok(pending)
    return pending.value


def test_arbitrate_collapse_same_mechanical_command() -> None:
    table = _rank_table()
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
    # Distinct reason/instant → distinct fingerprints; same kind+rank → collapse.
    # Give window a worse (higher) rank via a different table? Same rank collapses by
    # fingerprint order — mint a second flatten from operator at better rank.
    operator_flat = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.OPERATOR,
        authority="op-1",
        rank=1,
        reason="operator",
        issued_at=_instant(3_000),
    )
    # Same rank on two book_policy flats — collapse picks fingerprint order.
    pending = [
        _pending(kill_line),
        _pending(window),
        _pending(operator_flat),
    ]
    outcome = arbitrate_same_tick(pending, table, stream=stream, arbitration_seed="t1")
    assert is_ok(outcome)
    assert len(outcome.value.emit) == 1
    assert len(outcome.value.suppressed) == 2
    assert all(
        s.reason_class == "collapse-same-mechanical-command" for s in outcome.value.suppressed
    )


def test_arbitrate_compose_suspend_new_and_flatten() -> None:
    table = _rank_table()
    stream = _stream()
    suspend = _action(
        ControlActionKind.SUSPEND_NEW,
        authority_kind=AuthorityKind.PROTECTION_AUTHORITY,
        authority="ksa-1",
        rank=0,
        scope=SubjectScope.BINDING,
        scope_ref="binding-1",
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
    outcome = arbitrate_same_tick(
        [_pending(suspend), _pending(flatten)],
        table,
        stream=stream,
        arbitration_seed="compose",
    )
    assert is_ok(outcome)
    kinds = {p.record.action_kind for p in outcome.value.emit}
    assert kinds == {ControlActionKind.SUSPEND_NEW, ControlActionKind.FLATTEN}
    assert outcome.value.suppressed == ()


def test_arbitrate_conflict_higher_wins_when_not_reducing_protection() -> None:
    table = _rank_table()
    stream = _stream()
    # Higher-ranked flatten vs lower-ranked resume — resume would undo protection,
    # so invariant keeps both (higher must not reduce lower's protection... wait:
    # higher is flatten rank 1, resume rank 3 — flatten has more protection, so
    # higher wins and resume is suppressed).
    flatten = _action(
        ControlActionKind.FLATTEN,
        authority_kind=AuthorityKind.BOOK_POLICY,
        authority="book-1",
        rank=1,
        trigger_class="kill_line_breach",
    )
    resume = _action(
        ControlActionKind.RESUME,
        rank=3,
        issued_at=_instant(2_000),
    )
    outcome = arbitrate_same_tick(
        [_pending(flatten), _pending(resume)],
        table,
        stream=stream,
        arbitration_seed="conflict",
    )
    assert is_ok(outcome)
    assert len(outcome.value.emit) == 1
    assert outcome.value.emit[0].record.action_kind is ControlActionKind.FLATTEN
    assert len(outcome.value.suppressed) == 1
    assert outcome.value.suppressed[0].reason_class == "conflict-higher-rank-wins"


def test_arbitrate_higher_resume_cannot_suppress_lower_flatten() -> None:
    # Invert ranks: resume ranked higher (0) than flatten (1). Suppressing flatten
    # would reduce protection — both must execute.
    rows = [
        _rank_row(ControlActionKind.RESUME, 0),
        _rank_row(ControlActionKind.FLATTEN, 1),
        _rank_row(ControlActionKind.SUSPEND_NEW, 2),
        _rank_row(ControlActionKind.DRAIN, 3),
    ]
    table = ControlRankTable.try_create(rows)
    assert is_ok(table)
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
    outcome = arbitrate_same_tick(
        [_pending(resume), _pending(flatten)],
        table.value,
        stream=stream,
        arbitration_seed="invariant",
    )
    assert is_ok(outcome)
    kinds = {p.record.action_kind for p in outcome.value.emit}
    assert kinds == {ControlActionKind.RESUME, ControlActionKind.FLATTEN}
    assert outcome.value.suppressed == ()


def test_risk_reducing_act_enum_matches_l39() -> None:
    assert {a.value for a in RiskReducingAct} == {
        "cancel_order",
        "close_position",
        "close_all",
        "amend_protection_risk_non_increasing",
        "protection_action",
        "record_evidence",
    }
