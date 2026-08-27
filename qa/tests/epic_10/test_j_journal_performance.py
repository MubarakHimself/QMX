"""Epic 10 independent audit — Cluster J (Story 10.10).

CT-25 entity journals as read-time projections and the CT-32 publish-never-act
performance-result container. Authored from Story 10.10 ACs, CT-25, CT-32.

Planned IDs: J1-J7.
"""

from __future__ import annotations

from qmf.core import (
    AccountRole,
    CalendarIdentity,
    EvidenceClass,
    ExactRational,
    Instant,
    Interval,
    Money,
    RefusalCategory,
    ResultLabel,
    UnitKind,
    VenueId,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
    is_unpersistable,
    unpersistable,
)
from qmf.risk.binding import ContinuesPerformanceEdge
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    SubjectScope,
    mint_control_action,
)
from qmf.risk.control_rank import ControlActionKind
from qmf.risk.journal import (
    CT25_COMMAND_FINGERPRINT_JOIN_VERSION,
    LEGACY_PROJECTION_NAMES,
    RECORDS_STREAM_MAPPING,
    RISK_AUTHORED_EVENT_TYPES,
    VENUE_AUTHORED_EVENT_TYPES,
    DecisionOutcome,
    EntityKind,
    EntitySelector,
    EventClass,
    JournalEventType,
    LegacyProjectionName,
    RiskAuthoredEvent,
    RiskWriterUnit,
    VenueAuthoredEvent,
    WriterScopedStream,
    block_dispatch_on_journal_failure,
    join_via_command_fingerprint,
    map_legacy_projection,
    project_entity_journal,
    reject_book_identity_in_venue_payload,
    reject_cross_role_silent_union,
    reject_entity_as_writer,
)
from qmf.risk.performance import (
    FORBIDDEN_COMPOSITE_EXPRESSIONS,
    PerformanceMeasure,
    PopulationDeclaration,
    PublishAct,
    ResultPeriod,
    SuppressionCount,
    VetoCount,
    check_publish_never_act,
    check_replay_never_gates_live,
    consume_bench_crossing_at_door,
    mint_performance_result,
    publish_bench_crossing,
    reject_composite_expression,
    reject_multi_role_result,
)
from qmf.risk.exit_record import BenchDisposition, BenchFoldResult


def _fp(label: str):
    result = fingerprint({"label": label})
    assert is_ok(result)
    return result.value


def _instant(ns: int = 1_000_000_000) -> Instant:
    result = Instant.try_create(ns)
    assert is_ok(result)
    return result.value


def _interval() -> Interval:
    result = Interval.try_create(_instant(1_000_000_000), _instant(2_000_000_000))
    assert is_ok(result)
    return result.value


def _calendar() -> CalendarIdentity:
    result = CalendarIdentity.try_create("forex-17NY", "v3", "2024a")
    assert is_ok(result)
    return result.value


def _label(*, world: World = World.LIVE) -> ResultLabel:
    result = ResultLabel.try_create(_fp("producer-ct32"), 1, (_fp("input-1"),),
                                    _interval(), EvidenceClass.CONFIRMED, world)
    assert is_ok(result)
    return result.value


def _population(*, roles: tuple[AccountRole, ...] = (AccountRole.LIVE,)) -> PopulationDeclaration:
    result = PopulationDeclaration.try_create(
        _fp("bot-1"), (_fp("epoch-in"),), (), roles, ("EURUSD",), _fp("cohort-1"), ()
    )
    assert is_ok(result)
    return result.value


def _period() -> ResultPeriod:
    result = ResultPeriod.try_create(_interval(), _calendar(), _instant(2_500_000_000))
    assert is_ok(result)
    return result.value


def _measure(identity: str = "realized_r_mean") -> PerformanceMeasure:
    qty = ExactRational.try_create(1, 2, UnitKind.R_MULTIPLE)
    assert is_ok(qty)
    result = PerformanceMeasure.try_create(identity, qty.value, 1)
    assert is_ok(result)
    return result.value


def _risk_event(*, event_type: JournalEventType = JournalEventType.DECISION, book=None,
                binding=None, role: AccountRole = AccountRole.LIVE, sequence: int = 0,
                outcome: DecisionOutcome | None = DecisionOutcome.AUTHORIZED) -> RiskAuthoredEvent:
    result = RiskAuthoredEvent.try_create(
        event_type, _fp("book-v1") if book is None else book,
        _fp("binding-1") if binding is None else binding, role, sequence,
        _instant(1_000_000_000 + sequence), _fp(f"payload-{sequence}"),
        decision_outcome=outcome if event_type is JournalEventType.DECISION else None,
    )
    assert is_ok(result)
    return result.value


def _venue_event(*, command=None, sequence: int = 10) -> VenueAuthoredEvent:
    result = VenueAuthoredEvent.try_create(
        JournalEventType.ORDER, _fp("cmd-1") if command is None else command,
        AccountRole.LIVE, sequence, _instant(2_000_000_000 + sequence), _fp(f"venue-{sequence}")
    )
    assert is_ok(result)
    return result.value


# --- J1: entity journals are read-time projections; entity holds no WriterId --


def test_J1_entity_journals_are_projections_no_entity_writer() -> None:
    # An entity holds no WriterId (it is a selector, not a writer).
    selector = EntitySelector.try_create(EntityKind.BOOK, _fp("book-v1"))
    assert is_ok(selector)
    assert is_ok(reject_entity_as_writer(selector.value))
    writer = WriterId.try_create("m1", "risk", "decisions", "boot-1")
    assert is_ok(writer)
    assert is_refusal(reject_entity_as_writer(writer.value))
    # The legacy five Records names map onto the seven event types by one versioned table.
    assert set(LEGACY_PROJECTION_NAMES) == set(LegacyProjectionName)
    assert set(RECORDS_STREAM_MAPPING) == set(LegacyProjectionName)
    assert set(JournalEventType) == RISK_AUTHORED_EVENT_TYPES | VENUE_AUTHORED_EVENT_TYPES
    for name in LegacyProjectionName:
        mapped = map_legacy_projection(name)
        assert is_ok(mapped)
        assert mapped.value <= set(JournalEventType)


# --- J2: risk vs venue events; the command-fingerprint join ------------------


def test_J2_risk_and_venue_events_join_via_command_fingerprint() -> None:
    # A risk-authored event carries the Book-definition fingerprint + binding identity.
    risk = _risk_event()
    assert risk.book_definition_fingerprint == _fp("book-v1")
    assert risk.binding_identity == _fp("binding-1")
    assert risk.event_class is EventClass.RISK_AUTHORED
    # A venue-authored event NEVER carries a Book identity in its payload.
    refused = VenueAuthoredEvent.try_create(JournalEventType.ORDER, _fp("cmd-1"), AccountRole.LIVE,
                                            0, _instant(), _fp("p"), book_identity=_fp("book-v1"))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert reject_book_identity_in_venue_payload(_fp("book-v1")).category is RefusalCategory.POLICY_REJECTION
    # The join is through the pinned versioned command fingerprint, never Book identity.
    command, binding = _fp("cmd-join"), _fp("binding-1")
    joined = join_via_command_fingerprint(_venue_event(command=command), command_fingerprint=command,
                                          binding_identity=binding,
                                          risk_decision=_risk_event(binding=binding))
    assert is_ok(joined)
    assert joined.value.join_version == CT25_COMMAND_FINGERPRINT_JOIN_VERSION
    assert is_refusal(join_via_command_fingerprint(_venue_event(command=command),
                                                   command_fingerprint=_fp("other"),
                                                   binding_identity=binding,
                                                   risk_decision=_risk_event(binding=binding)))


# --- J3 [L3]: a control action is journaled before dispatch ------------------


def test_J3_control_action_journaled_before_dispatch_blocks_on_failure() -> None:
    stream = CommandStreamKey.try_create(VenueId(value="ctrader"), "acct-1")
    assert is_ok(stream)
    minted = mint_control_action(ControlActionKind.SUSPEND_NEW, "op-1", AuthorityKind.OPERATOR,
                                 SubjectScope.BOOK, "book-1", 0, "protection", stream.value, _instant())
    assert is_ok(minted)
    blocked = block_dispatch_on_journal_failure(minted.value, journal_result=unpersistable("disk full"))
    assert is_refusal(blocked)
    assert is_unpersistable(blocked)
    assert is_ok(block_dispatch_on_journal_failure(minted.value, journal_result=True))


# --- J4: role-scoped namespace; cross-role read explicitly declared ----------


def test_J4_role_scoped_projections_no_silent_cross_role_union() -> None:
    book, binding = _fp("book-v1"), _fp("binding-1")
    live = _risk_event(book=book, binding=binding, role=AccountRole.LIVE, sequence=0)
    paper = _risk_event(book=book, binding=binding, role=AccountRole.PAPER_VALIDATION, sequence=1)
    unit = RiskWriterUnit.try_create("m1", "risk", binding, "boot-1")
    assert is_ok(unit)
    writer = unit.value.as_writer_id("decisions")
    assert is_ok(writer)
    stream = WriterScopedStream.try_create(writer.value, (live, paper))
    assert is_ok(stream)
    selector = EntitySelector.try_create(EntityKind.BOOK, book)
    assert is_ok(selector)
    # A cross-role read that is NOT declared is refused (never a silent union).
    silent = project_entity_journal(selector.value, (stream.value,), role_scope=AccountRole.LIVE,
                                    cross_role_declared=False)
    assert is_refusal(silent)
    assert silent.category is RefusalCategory.INVALID_INPUT
    # A declared cross-role read is allowed, and role rides on every row.
    declared = project_entity_journal(selector.value, (stream.value,), role_scope=AccountRole.LIVE,
                                      cross_role_declared=True)
    assert is_ok(declared)
    assert {row.role for row in declared.value.rows} == {AccountRole.LIVE, AccountRole.PAPER_VALIDATION}
    # The helper enforces the same rule.
    assert is_refusal(reject_cross_role_silent_union(role_scope=AccountRole.LIVE,
                                                     observed_roles=(AccountRole.LIVE, AccountRole.DEMO),
                                                     cross_role_declared=False))


# --- J5: the performance-result container carries the mandated parts ---------


def test_J5_performance_result_container_shape() -> None:
    suppression = SuppressionCount.try_create(AuthorityKind.OPERATOR, "kill_switch", 2)
    assert is_ok(suppression)
    veto = VetoCount.try_create("ct-23-door", 3)
    assert is_ok(veto)
    minted = mint_performance_result(
        result_label=_label(), account_binding_role=AccountRole.LIVE, population=_population(),
        period=_period(), measure_set=(_measure(),),
        suppression_accounting=(suppression.value,), veto_accounting=(veto.value,),
        baseline_pointer=_fp("baseline"),
    )
    assert is_ok(minted)
    result = minted.value
    assert result.account_binding_role is AccountRole.LIVE
    # suppression accounting is by authority + reason; veto accounting is by door; both count.
    assert result.suppression_accounting[0].count == 2
    assert result.veto_accounting[0].count == 3
    assert result.suppression_accounting[0].fp1_identity()["unit_kind"] == UnitKind.COUNT.value
    assert result.veto_accounting[0].fp1_identity()["unit_kind"] == UnitKind.COUNT.value
    # A knowledge-time bound is carried on the period; every emitted quantity has a unit-kind.
    assert _period().knowledge_time_bound == _instant(2_500_000_000)
    assert result.measure_set[0].quantity.unit_kind is UnitKind.R_MULTIPLE


# --- J6: no composite; a result may never span roles; publish-never-act ------


def test_J6_no_composite_single_role_publish_never_act() -> None:
    assert "composite-score" in FORBIDDEN_COMPOSITE_EXPRESSIONS
    for bad in ("composite-score", "tier-band", "weighted-aggregate", "rating"):
        qty = ExactRational.try_create(1, 1, UnitKind.DIMENSIONLESS_RATIO)
        assert is_ok(qty)
        refused = PerformanceMeasure.try_create(bad, qty.value, 1)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
    assert reject_composite_expression("score").category is RefusalCategory.POLICY_REJECTION
    # A single result may never span account roles (multi-role -> policy rejection).
    multi = _population(roles=(AccountRole.LIVE, AccountRole.DEMO))
    assert reject_multi_role_result(account_binding_role=AccountRole.LIVE, population=multi).category is RefusalCategory.POLICY_REJECTION
    assert is_refusal(mint_performance_result(result_label=_label(), account_binding_role=AccountRole.LIVE,
                                              population=multi, period=_period(), measure_set=(_measure(),)))
    # Measurement publishes and never acts.
    for act in PublishAct:
        assert is_refusal(check_publish_never_act(act))


# --- J7: the bench fold is a governed producer; replay never gates live ------


def test_J7_bench_fold_governed_producer_replay_never_gates_live() -> None:
    fold = BenchFoldResult(
        qualifying_loss_count=3, breakeven_count=0, scratch_or_partial_count=1, gain_count=0,
        threshold=3, threshold_crossed=True,
        dispositions=(BenchDisposition.QUALIFYING_LOSS_EXIT,) * 3, considered=(),
    )
    published = publish_bench_crossing(fold, binding_epoch=_fp("epoch-1"))
    assert is_ok(published)
    assert published.value.threshold_crossed is True
    # Published once, consumed by the Book door — the same governed identity.
    consumed = consume_bench_crossing_at_door(published.value, door_identity="book-door")
    assert is_ok(consumed)
    pub_fp, con_fp = published.value.fingerprint(), consumed.value.fingerprint()
    assert is_ok(pub_fp) and is_ok(con_fp)
    assert pub_fp.value == con_fp.value
    # A replay-world result can never gate live money.
    replay = mint_performance_result(result_label=_label(world=World.REPLAY),
                                     account_binding_role=AccountRole.LIVE, population=_population(),
                                     period=_period(), measure_set=(_measure(),))
    assert is_ok(replay)
    gated = check_replay_never_gates_live(replay.value, gating_live=True)
    assert is_refusal(gated)
    assert gated.category is RefusalCategory.POLICY_REJECTION
    assert is_ok(check_replay_never_gates_live(replay.value, gating_live=False))
