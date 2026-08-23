"""Story 10.10 — CT-32 performance-result container, publish-never-act."""

from __future__ import annotations

from qmf.core import (
    AccountRole,
    CalendarIdentity,
    EvidenceClass,
    ExactRational,
    Instant,
    Interval,
    RefusalCategory,
    ResultLabel,
    UnitKind,
    World,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.binding import ContinuesPerformanceEdge
from qmf.risk.control_action import AuthorityKind
from qmf.risk.exit_record import BenchDisposition, BenchFoldResult
from qmf.risk.performance import (
    CT32_CONTRACT_FORMAT_VERSION,
    FORBIDDEN_COMPOSITE_EXPRESSIONS,
    BenchCrossingPublication,
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
    require_baseline_for_decay,
)


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
    producer = _fp("producer-ct32")
    result = ResultLabel.try_create(
        producer,
        CT32_CONTRACT_FORMAT_VERSION,
        (_fp("input-1"),),
        _interval(),
        EvidenceClass.CONFIRMED,
        world,
    )
    assert is_ok(result)
    return result.value


def _population(
    *,
    roles: tuple[AccountRole, ...] = (AccountRole.LIVE,),
    edges: tuple[ContinuesPerformanceEdge, ...] = (),
) -> PopulationDeclaration:
    result = PopulationDeclaration.try_create(
        _fp("bot-1"),
        (_fp("epoch-in"),),
        (),
        roles,
        ("EURUSD",),
        _fp("cohort-1"),
        edges,
    )
    assert is_ok(result), result
    return result.value


def _period() -> ResultPeriod:
    result = ResultPeriod.try_create(_interval(), _calendar(), _instant(2_500_000_000))
    assert is_ok(result)
    return result.value


def _measure(identity: str = "realized_r_mean", num: int = 1, den: int = 2) -> PerformanceMeasure:
    qty = ExactRational.try_create(num, den, UnitKind.R_MULTIPLE)
    assert is_ok(qty)
    result = PerformanceMeasure.try_create(identity, qty.value, 1)
    assert is_ok(result), result
    return result.value


def test_contract_version() -> None:
    assert CT32_CONTRACT_FORMAT_VERSION == 1
    assert "composite-score" in FORBIDDEN_COMPOSITE_EXPRESSIONS


def test_mint_performance_result_with_accounting() -> None:
    suppression = SuppressionCount.try_create(AuthorityKind.OPERATOR, "kill_switch", 2)
    assert is_ok(suppression)
    veto = VetoCount.try_create("ct-23-door", 3)
    assert is_ok(veto)
    minted = mint_performance_result(
        result_label=_label(),
        account_binding_role=AccountRole.LIVE,
        population=_population(),
        period=_period(),
        measure_set=(_measure(),),
        suppression_accounting=(suppression.value,),
        veto_accounting=(veto.value,),
        baseline_pointer=_fp("baseline"),
    )
    assert is_ok(minted)
    assert minted.value.account_binding_role is AccountRole.LIVE
    assert minted.value.suppression_accounting[0].count == 2
    assert minted.value.veto_accounting[0].count == 3
    assert minted.value.baseline_pointer == _fp("baseline")
    fp = minted.value.fingerprint()
    assert is_ok(fp)


def test_quiet_period_defaults_accounting_to_empty_not_omitted() -> None:
    minted = mint_performance_result(
        result_label=_label(),
        account_binding_role=AccountRole.LIVE,
        population=_population(),
        period=_period(),
        measure_set=(_measure(),),
    )
    assert is_ok(minted)
    assert minted.value.suppression_accounting == ()
    assert minted.value.veto_accounting == ()


def test_every_measure_requires_unit_kind_no_composite() -> None:
    assert is_refusal(PerformanceMeasure.try_create("alpha_score", "not-rational", 1))
    for bad in ("composite-score", "tier-band", "weighted-aggregate", "rating"):
        refused = PerformanceMeasure.try_create(
            bad,
            ExactRational.try_create(1, 1, UnitKind.DIMENSIONLESS_RATIO).value,  # type: ignore[union-attr]
            1,
        )
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
    direct = reject_composite_expression("score")
    assert direct.category is RefusalCategory.POLICY_REJECTION


def test_multi_role_result_is_policy_rejection() -> None:
    multi = _population(roles=(AccountRole.LIVE, AccountRole.DEMO))
    refused = reject_multi_role_result(
        account_binding_role=AccountRole.LIVE, population=multi
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    minted = mint_performance_result(
        result_label=_label(),
        account_binding_role=AccountRole.LIVE,
        population=multi,
        period=_period(),
        measure_set=(_measure(),),
    )
    assert is_refusal(minted)


def test_publish_never_act() -> None:
    for act in PublishAct:
        refused = check_publish_never_act(act)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
    assert is_refusal(check_publish_never_act("bench"))
    assert is_refusal(check_publish_never_act("change_mode"))


def test_replay_never_gates_live() -> None:
    replay = mint_performance_result(
        result_label=_label(world=World.REPLAY),
        account_binding_role=AccountRole.LIVE,
        population=_population(),
        period=_period(),
        measure_set=(_measure(),),
    )
    assert is_ok(replay)
    refused = check_replay_never_gates_live(replay.value, gating_live=True)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert is_ok(check_replay_never_gates_live(replay.value, gating_live=False))

    live = mint_performance_result(
        result_label=_label(world=World.LIVE),
        account_binding_role=AccountRole.LIVE,
        population=_population(),
        period=_period(),
        measure_set=(_measure(),),
    )
    assert is_ok(live)
    assert is_ok(check_replay_never_gates_live(live.value, gating_live=True))


def test_bench_crossing_is_governed_producer_consumed_by_door() -> None:
    fold = BenchFoldResult(
        qualifying_loss_count=3,
        breakeven_count=0,
        scratch_or_partial_count=1,
        gain_count=0,
        threshold=3,
        threshold_crossed=True,
        dispositions=(
            BenchDisposition.QUALIFYING_LOSS_EXIT,
            BenchDisposition.QUALIFYING_LOSS_EXIT,
            BenchDisposition.QUALIFYING_LOSS_EXIT,
        ),
        considered=(),
    )
    epoch = _fp("epoch-1")
    published = publish_bench_crossing(fold, binding_epoch=epoch)
    assert is_ok(published)
    assert isinstance(published.value, BenchCrossingPublication)
    assert published.value.threshold_crossed is True
    # Measurement still may not act.
    assert is_refusal(check_publish_never_act(PublishAct.BENCH))
    consumed = consume_bench_crossing_at_door(published.value, door_identity="book-door")
    assert is_ok(consumed)
    pub_fp = published.value.fingerprint()
    con_fp = consumed.value.fingerprint()
    assert is_ok(pub_fp) and is_ok(con_fp)
    assert pub_fp.value == con_fp.value


def test_population_consumes_continues_performance_only() -> None:
    edge = ContinuesPerformanceEdge.try_create(_fp("prior-epoch"))
    assert is_ok(edge)
    pop = _population(edges=(edge.value,))
    assert len(pop.continues_performance_edges) == 1
    assert is_refusal(
        PopulationDeclaration.try_create(
            _fp("bot"),
            (),
            (),
            (AccountRole.LIVE,),
            (),
            _fp("cohort"),
            ("not-an-edge",),
        )
    )


def test_baseline_required_for_decay() -> None:
    without = mint_performance_result(
        result_label=_label(),
        account_binding_role=AccountRole.LIVE,
        population=_population(),
        period=_period(),
        measure_set=(_measure(),),
    )
    assert is_ok(without)
    refused = require_baseline_for_decay(without.value, for_decay_judgment=True)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    with_baseline = mint_performance_result(
        result_label=_label(),
        account_binding_role=AccountRole.LIVE,
        population=_population(),
        period=_period(),
        measure_set=(_measure(),),
        baseline_pointer=_fp("baseline"),
    )
    assert is_ok(with_baseline)
    assert is_ok(require_baseline_for_decay(with_baseline.value, for_decay_judgment=True))


def test_period_carries_knowledge_time_bound() -> None:
    period = _period()
    assert period.knowledge_time_bound == _instant(2_500_000_000)
    assert period.calendar.rule_set == "forex-17NY"
