"""Story 26.3 — immutable environment-keyed signal snapshot at the Book door."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Duration,
    ExactRational,
    Instant,
    Instrument,
    RefusalCategory,
    UnitKind,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import Result
from qmn.mis import (
    DECISION_FRESHNESS_BOUND_VARIABLE,
    GOVERNED_CONSUMERS,
    MIS_SURFACE,
    SIGNAL_SNAPSHOT_SURFACE,
    SQS_PRODUCER_ID,
    CanonicalFeedState,
    GovernedConsumer,
    ProducerReadiness,
    ProducerSlot,
    check_snapshot_freshness,
    consume_signal_snapshot,
    mint_signal_snapshot,
    refuse_bot_consumer,
    sqs_baseline_key,
)
from qmn.mis.signal_snapshot import SqsReading

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return _ok(Instrument.try_create(_ok(VenueId.try_create("ctrader")), symbol))


def _score(num: int = 1, den: int = 1) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


def _sqs(*, environment: str = "live", readiness: ProducerReadiness = ProducerReadiness.OK):
    key = _ok(sqs_baseline_key(_ok(VenueId.try_create("ctrader")), environment, _instrument()))
    if readiness is ProducerReadiness.OK:
        return _ok(
            SqsReading.try_create(
                key,
                readiness=readiness,
                labeler_version="sqs-v1",
                score=_score(5, 4),
                hard_block=False,
            )
        )
    return _ok(
        SqsReading.try_create(
            key,
            readiness=readiness,
            labeler_version="sqs-v1",
        )
    )


def _sqs_slot(*, environment: str = "live", readiness: ProducerReadiness = ProducerReadiness.OK):
    reading = _sqs(environment=environment, readiness=readiness)
    return _ok(
        ProducerSlot.try_create(
            SQS_PRODUCER_ID,
            readiness=readiness,
            labeler_version=reading.labeler_version,
            sqs=reading,
        )
    )


def _snapshot(
    *,
    frontier: int = 1_000_000_000,
    bound: int = 5_000_000_000,
    environment: str = "live",
    readiness: ProducerReadiness = ProducerReadiness.OK,
):
    feed_slot = _ok(
        ProducerSlot.try_create(
            "feed_state",
            readiness=ProducerReadiness.OK,
            labeler_version="feed-v1",
            marker_detail="canonical",
        )
    )
    return _ok(
        mint_signal_snapshot(
            frontier_instant=_instant(frontier),
            environment=environment,
            feed_state=CanonicalFeedState.LIVE,
            producers=(_sqs_slot(environment=environment, readiness=readiness), feed_slot),
            decision_freshness_bound=_duration(bound),
            degraded_sensors=(),
        )
    )


def test_mis_surface_and_governed_consumers() -> None:
    assert MIS_SURFACE == "qmn.mis"
    assert SIGNAL_SNAPSHOT_SURFACE == "qmn.mis.signal_snapshot"
    assert frozenset(
        {GovernedConsumer.BOOK_DOOR, GovernedConsumer.KSA}
    ) == GOVERNED_CONSUMERS


def test_snapshot_carries_exactly_one_sqs_value_per_instant() -> None:
    snap = _snapshot()
    assert SQS_PRODUCER_ID in snap.producers
    reading = snap.sqs_for(_instrument())
    assert reading is not None
    assert reading.hard_block is False
    assert reading.score is not None
    assert reading.baseline_key.environment == "live"

    dup = mint_signal_snapshot(
        frontier_instant=_instant(1),
        environment="live",
        feed_state=CanonicalFeedState.LIVE,
        producers=(_sqs_slot(), _sqs_slot()),
        decision_freshness_bound=_duration(10),
    )
    assert is_refusal(dup)
    assert "exactly one" in str(dup.context["reason"])


def test_environment_key_separates_demo_and_live_baselines() -> None:
    live_key = _ok(
        sqs_baseline_key(_ok(VenueId.try_create("ctrader")), "live", _instrument())
    )
    demo_key = _ok(
        sqs_baseline_key(_ok(VenueId.try_create("ctrader")), "demo", _instrument())
    )
    assert live_key.environment != demo_key.environment
    assert live_key.fp1_identity() != demo_key.fp1_identity()

    live_snap = _snapshot(environment="live")
    demo_snap = _snapshot(environment="demo")
    assert live_snap.environment == "live"
    assert demo_snap.environment == "demo"
    assert live_snap.fp1_identity() != demo_snap.fp1_identity()


def test_freshness_bound_is_decision_freshness_bound_only() -> None:
    snap = _snapshot(frontier=1_000, bound=100)
    assert DECISION_FRESHNESS_BOUND_VARIABLE in snap.fp1_identity()
    fresh = check_snapshot_freshness(snap, decision_at=_instant(1_050))
    assert is_ok(fresh)
    stale = check_snapshot_freshness(snap, decision_at=_instant(1_101))
    assert is_refusal(stale)
    assert stale.category is RefusalCategory.STALE_EVIDENCE


def test_book_door_and_ksa_consume_bots_refused() -> None:
    snap = _snapshot()
    for consumer in (GovernedConsumer.BOOK_DOOR, GovernedConsumer.KSA, "book_door", "ksa"):
        consumed = _ok(
            consume_signal_snapshot(
                snap, consumer=consumer, decision_at=_instant(1_000_000_000)
            )
        )
        assert consumed is snap

    bot = consume_signal_snapshot(
        snap, consumer="bot", decision_at=_instant(1_000_000_000)
    )
    assert is_refusal(bot)
    assert bot.category is RefusalCategory.POLICY_REJECTION
    assert refuse_bot_consumer("bot").category is RefusalCategory.POLICY_REJECTION


def test_non_ok_sqs_is_hard_block_never_last_known_good() -> None:
    for marker in (
        ProducerReadiness.NOT_READY,
        ProducerReadiness.UNAVAILABLE,
        ProducerReadiness.STALE,
        ProducerReadiness.REFUSED,
    ):
        reading = _sqs(readiness=marker)
        assert reading.hard_block is True
        assert reading.score is None

    key = _ok(sqs_baseline_key(_ok(VenueId.try_create("ctrader")), "live", _instrument()))
    refused = SqsReading.try_create(
        key,
        readiness=ProducerReadiness.STALE,
        labeler_version="sqs-v1",
        hard_block=False,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_snapshot_is_immutable_and_fingerprinted() -> None:
    snap = _snapshot()
    fp = _ok(snap.fingerprint())
    assert fp.value
    # MappingProxyType producers — assignment must fail.
    try:
        snap.producers["extra"] = _sqs_slot()  # type: ignore[index]
        raised = False
    except TypeError:
        raised = True
    assert raised


def test_missing_freshness_bound_refuses_mint() -> None:
    refused = mint_signal_snapshot(
        frontier_instant=_instant(1),
        environment="live",
        feed_state=CanonicalFeedState.LIVE,
        producers=(_sqs_slot(),),
        decision_freshness_bound=None,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == DECISION_FRESHNESS_BOUND_VARIABLE
