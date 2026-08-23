"""Reference usage — CT-25 journal projections and CT-32 publish-never-act.

Executable::

    python packages/qmf-risk/examples/journal_performance_usage.py

Shows entity journals as read-time projections (legacy Records names, command-
fingerprint join, storage-failure blocks dispatch, role-scoped reads) and the
CT-32 performance-result container (no composite score, multi-role refusal,
publish-never-act, replay never gates live, bench crossing as governed producer).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    AccountRole,
    CalendarIdentity,
    EvidenceClass,
    ExactRational,
    Instant,
    Interval,
    RefusalCategory,
    Result,
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
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    SubjectScope,
    mint_control_action,
)
from qmf.risk.control_rank import ControlActionKind
from qmf.risk.exit_record import BenchDisposition, BenchFoldResult
from qmf.risk.journal import (
    DecisionOutcome,
    EntityKind,
    EntitySelector,
    JournalEventType,
    LegacyProjectionName,
    RiskAuthoredEvent,
    VenueAuthoredEvent,
    WriterScopedStream,
    block_dispatch_on_journal_failure,
    join_via_command_fingerprint,
    map_legacy_projection,
    project_entity_journal,
    project_legacy,
    reject_entity_as_writer,
)
from qmf.risk.performance import (
    CT32_CONTRACT_FORMAT_VERSION,
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
)

T = TypeVar("T")


def _unwrap(result: Result[T], message: str) -> T:
    if is_ok(result):
        return result.value
    raise RuntimeError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _fp(label: str):
    return _unwrap(fingerprint({"label": label}), f"fingerprint {label}")


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant mint failed")


def main() -> None:
    book = _fp("book-v1")
    binding = _fp("binding-1")
    command = _fp("cmd-1")

    # Entity holds no WriterId.
    selector = _unwrap(EntitySelector.try_create(EntityKind.BOOK, book), "selector")
    writer = _unwrap(WriterId.try_create("m1", "risk", "decisions", "boot-1"), "writer")
    as_writer = reject_entity_as_writer(writer)
    _require(is_refusal(as_writer), "entity must not be a WriterId")
    print("entity journals: entity holds no WriterId (invalid input)")

    # Legacy Records names map onto the seven event types.
    veto_types = _unwrap(map_legacy_projection(LegacyProjectionName.VETO_LEDGER), "map")
    _require(JournalEventType.DECISION in veto_types, "veto_ledger maps to decision")
    mapped_names = [t.value for t in sorted(veto_types, key=lambda t: t.value)]
    print(f"legacy mapping: veto_ledger -> {mapped_names}")

    # Risk-authored vs venue-authored + command-fingerprint join.
    decision = _unwrap(
        RiskAuthoredEvent.try_create(
            JournalEventType.DECISION,
            book,
            binding,
            AccountRole.LIVE,
            0,
            _instant(1_000_000_000),
            _fp("decision-payload"),
            decision_outcome=DecisionOutcome.AUTHORIZED,
        ),
        "decision",
    )
    refused = _unwrap(
        RiskAuthoredEvent.try_create(
            JournalEventType.DECISION,
            book,
            binding,
            AccountRole.LIVE,
            1,
            _instant(1_100_000_000),
            _fp("refused-payload"),
            decision_outcome=DecisionOutcome.REFUSED_BY_DOOR,
            refusing_door_ref=_fp("door-ct23"),
        ),
        "refused decision",
    )
    venue_order = _unwrap(
        VenueAuthoredEvent.try_create(
            JournalEventType.ORDER,
            command,
            AccountRole.LIVE,
            10,
            _instant(1_200_000_000),
            _fp("order-payload"),
        ),
        "venue order",
    )
    joined = _unwrap(
        join_via_command_fingerprint(
            venue_order,
            command_fingerprint=command,
            binding_identity=binding,
            risk_decision=decision,
        ),
        "join",
    )
    print(
        f"command-fingerprint join: version={joined.join_version} "
        f"venue={joined.venue_event.event_type.value}"
    )

    stream = _unwrap(
        WriterScopedStream.try_create(writer, (decision, refused)),
        "stream",
    )
    veto = _unwrap(
        project_legacy(
            LegacyProjectionName.VETO_LEDGER,
            (stream,),
            selector=selector,
            role_scope=AccountRole.LIVE,
        ),
        "veto projection",
    )
    _require(len(veto.rows) == 1, "veto_ledger selects refused-by-door")
    print(f"veto_ledger rows: {len(veto.rows)} (outcome=refused-by-door)")

    live_proj = _unwrap(
        project_entity_journal(selector, (stream,), role_scope=AccountRole.LIVE),
        "live projection",
    )
    print(f"book journal live rows: {len(live_proj.rows)}")

    # Storage failure of a control action journaled before dispatch blocks dispatch.
    venue = _unwrap(VenueId.try_create("ctrader"), "venue")
    cmd_stream = _unwrap(CommandStreamKey.try_create(venue, "acct-1"), "cmd stream")
    action = _unwrap(
        mint_control_action(
            ControlActionKind.SUSPEND_NEW,
            "op-1",
            AuthorityKind.OPERATOR,
            SubjectScope.BOOK,
            "book-1",
            0,
            "protection",
            cmd_stream,
            _instant(1_300_000_000),
        ),
        "control action",
    )
    blocked = block_dispatch_on_journal_failure(
        action, journal_result=unpersistable("journal sink full")
    )
    _require(is_refusal(blocked) and is_unpersistable(blocked), "storage failure blocks")
    print("journal-before-dispatch: storage failure blocks dispatch")

    # CT-32 performance result — publish never act.
    interval = _unwrap(
        Interval.try_create(_instant(1_000_000_000), _instant(2_000_000_000)),
        "interval",
    )
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2024a"), "calendar")
    label = _unwrap(
        ResultLabel.try_create(
            _fp("producer-ct32"),
            CT32_CONTRACT_FORMAT_VERSION,
            (_fp("input-1"),),
            interval,
            EvidenceClass.CONFIRMED,
            World.REPLAY,
        ),
        "label",
    )
    population = _unwrap(
        PopulationDeclaration.try_create(
            _fp("bot-1"),
            (_fp("epoch-in"),),
            (),
            (AccountRole.LIVE,),
            ("EURUSD",),
            _fp("cohort-1"),
            (),
        ),
        "population",
    )
    period = _unwrap(
        ResultPeriod.try_create(interval, calendar, _instant(2_500_000_000)),
        "period",
    )
    measure = _unwrap(
        PerformanceMeasure.try_create(
            "realized_r_mean",
            _unwrap(ExactRational.try_create(1, 2, UnitKind.R_MULTIPLE), "qty"),
            1,
        ),
        "measure",
    )
    composite = PerformanceMeasure.try_create(
        "composite-score",
        _unwrap(ExactRational.try_create(1, 1, UnitKind.DIMENSIONLESS_RATIO), "qty"),
        1,
    )
    _require(
        is_refusal(composite) and composite.category is RefusalCategory.POLICY_REJECTION,
        "composite refused",
    )
    print("no composite score: composite-score refused (policy rejection)")

    multi = PopulationDeclaration.try_create(
        _fp("bot-1"),
        (_fp("epoch-in"),),
        (),
        (AccountRole.LIVE, AccountRole.DEMO),
        ("EURUSD",),
        _fp("cohort-1"),
        (),
    )
    multi_pop = _unwrap(multi, "multi pop")
    multi_result = mint_performance_result(
        result_label=label,
        account_binding_role=AccountRole.LIVE,
        population=multi_pop,
        period=period,
        measure_set=(measure,),
    )
    _require(is_refusal(multi_result), "multi-role result refused")
    print("multi-role result: refused (policy rejection)")

    suppression = _unwrap(
        SuppressionCount.try_create(AuthorityKind.OPERATOR, "kill_switch", 1),
        "suppression",
    )
    veto = _unwrap(VetoCount.try_create("ct-23-door", 2), "veto")
    result = _unwrap(
        mint_performance_result(
            result_label=label,
            account_binding_role=AccountRole.LIVE,
            population=population,
            period=period,
            measure_set=(measure,),
            suppression_accounting=(suppression,),
            veto_accounting=(veto,),
            baseline_pointer=_fp("baseline"),
        ),
        "result",
    )
    print(
        f"CT-32 result: world={result.result_label.world.value} "
        f"suppressions={result.suppression_accounting[0].count} "
        f"vetoes={result.veto_accounting[0].count}"
    )

    act = check_publish_never_act(PublishAct.BENCH)
    _require(is_refusal(act), "measurement must not bench")
    print("publish-never-act: bench refused (policy rejection)")

    gated = check_replay_never_gates_live(result, gating_live=True)
    _require(
        is_refusal(gated) and gated.category is RefusalCategory.POLICY_REJECTION,
        "replay must not gate live",
    )
    print("replay-world result: never gates live money")

    fold = BenchFoldResult(
        qualifying_loss_count=3,
        breakeven_count=0,
        scratch_or_partial_count=0,
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
    published = _unwrap(publish_bench_crossing(fold, binding_epoch=_fp("epoch-1")), "publish")
    consumed = _unwrap(
        consume_bench_crossing_at_door(published, door_identity="book-door"),
        "consume",
    )
    _require(consumed.threshold_crossed is True, "crossing published")
    print(
        f"bench crossing: governed producer threshold_crossed={consumed.threshold_crossed} "
        f"consumed by Book door"
    )


if __name__ == "__main__":
    main()
