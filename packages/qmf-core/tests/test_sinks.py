"""Tier-1 tests for the injected persistence seams: ObservationSink, JournalSink,
RecordSink — and the block-on-unpersistable helpers (AD-15, AR-47; CT-04).

These pin the seam contract: every sink returns ``Result[SinkAck]``, an
unpersistable write is a CT-04 ``storage failure`` typed refusal carrying category,
context, and retryability, and :func:`is_unpersistable` is the predicate a writer
branches on to block its command stream.
"""

from __future__ import annotations

import pytest
from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_ok
from qmf.core.sinks import (
    JournalSink,
    ObservationSink,
    RecordSink,
    SinkAck,
    SinkResult,
    is_unpersistable,
    unpersistable,
)

# --- SinkAck ----------------------------------------------------------------


def test_sink_ack_default_detail_is_empty_and_read_only() -> None:
    ack = SinkAck()
    assert dict(ack.detail) == {}


def test_sink_ack_snapshots_detail() -> None:
    source: dict[str, object] = {"stored_count": 1}
    ack = SinkAck(detail=source)
    # A later mutation of the caller's dict cannot reach back into the frozen ack.
    source["stored_count"] = 999
    assert ack.detail["stored_count"] == 1


# --- unpersistable() --------------------------------------------------------


def test_unpersistable_builds_a_storage_failure_refusal() -> None:
    refusal = unpersistable("disk full")
    assert isinstance(refusal, TypedRefusal)
    assert refusal.category is RefusalCategory.STORAGE_FAILURE
    assert refusal.retryability is Retryability.NO
    assert refusal.context["reason"] == "disk full"


def test_unpersistable_merges_context_and_after_condition() -> None:
    refusal = unpersistable(
        "journal store is full",
        retryability=Retryability.AFTER_CONDITION,
        context={"capacity": 2},
        after_condition_descriptor="free space in the journal store",
    )
    assert refusal.retryability is Retryability.AFTER_CONDITION
    assert refusal.context["capacity"] == 2
    assert refusal.context["reason"] == "journal store is full"
    assert refusal.after_condition_descriptor == "free space in the journal store"


def test_unpersistable_only_ever_mints_a_ct04_valid_refusal() -> None:
    # Regression (M5): both valid pairings round-trip through the validating
    # TypedRefusal.try_create without being rejected — the helper never mints a
    # value the typed envelope itself would refuse.
    for refusal in (
        unpersistable("disk full"),
        unpersistable(
            "rotation store failed",
            retryability=Retryability.AFTER_CONDITION,
            after_condition_descriptor="successful store or operator re-provision",
        ),
    ):
        revalidated = TypedRefusal.try_create(
            refusal.category,
            refusal.retryability,
            context=refusal.context,
            after_condition_descriptor=refusal.after_condition_descriptor,
        )
        assert is_ok(revalidated)


def test_unpersistable_raises_on_descriptor_without_after_condition() -> None:
    # Regression (M5): a descriptor with the default NO retryability is a CT-04
    # mis-pairing (TypedRefusal.try_create rejects it); the helper must not mint it.
    with pytest.raises(ValueError, match="after-condition"):
        unpersistable("disk full", after_condition_descriptor="free space")


def test_unpersistable_raises_on_after_condition_without_descriptor() -> None:
    # Regression (M5): the other direction — after-condition retryability with no
    # descriptor is equally a CT-04 mis-pairing.
    with pytest.raises(ValueError, match="after-condition"):
        unpersistable("disk full", retryability=Retryability.AFTER_CONDITION)


# --- is_unpersistable() -----------------------------------------------------


def test_is_unpersistable_true_only_for_storage_failure() -> None:
    assert is_unpersistable(unpersistable("full")) is True
    # A successful acknowledgment is persistable.
    assert is_unpersistable(Ok(SinkAck())) is False
    # A different refusal category is not an unpersistable-write signal.
    other = TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
    )
    assert is_unpersistable(other) is False
    # A non-result value is never unpersistable.
    assert is_unpersistable(None) is False
    assert is_unpersistable("nope") is False


# --- protocol conformance ---------------------------------------------------


class _ObsSink:
    def emit(self, observation: object, /) -> SinkResult:
        return Ok(SinkAck())


class _JournalSink:
    def append(self, event: object, /) -> SinkResult:
        return Ok(SinkAck())


class _RecordSink:
    def write(self, record: object, /) -> SinkResult:
        return Ok(SinkAck())


class _NotASink:
    def store(self, thing: object, /) -> None:
        return None


def test_sink_protocols_are_distinct_and_runtime_checkable() -> None:
    assert isinstance(_ObsSink(), ObservationSink)
    assert isinstance(_JournalSink(), JournalSink)
    assert isinstance(_RecordSink(), RecordSink)
    # The three seams are non-interchangeable: distinct method names mean an
    # observation sink is not a journal sink, and an arbitrary object is neither.
    assert not isinstance(_ObsSink(), JournalSink)
    assert not isinstance(_JournalSink(), RecordSink)
    assert not isinstance(_NotASink(), ObservationSink)


# --- block-on-unpersistable end to end --------------------------------------


class _CapacityJournal:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self.events: list[object] = []

    def append(self, event: object, /) -> SinkResult:
        if len(self.events) >= self._capacity:
            return unpersistable(
                "journal store is full",
                retryability=Retryability.AFTER_CONDITION,
                after_condition_descriptor="free space",
            )
        self.events.append(event)
        return Ok(SinkAck())


def test_writer_blocks_on_unpersistable() -> None:
    journal: JournalSink[str] = _CapacityJournal(capacity=2)
    written = 0
    blocked: TypedRefusal | None = None
    for event in ["e1", "e2", "e3", "e4"]:
        outcome = journal.append(event)
        if is_unpersistable(outcome):
            assert isinstance(outcome, TypedRefusal)
            blocked = outcome
            break
        written += 1
    # The writer stopped at capacity — the intent is neither dropped nor advanced.
    assert written == 2
    assert blocked is not None
    assert blocked.category is RefusalCategory.STORAGE_FAILURE


def test_successful_write_returns_ack() -> None:
    sink: ObservationSink[object] = _ObsSink()
    result: Result[SinkAck] = sink.emit({"kind": "quote"})
    assert is_ok(result)
    assert isinstance(result.value, SinkAck)
