"""Reference usage — the injected persistence seams (COMP-QMF-CORE).

Executable::

    python packages/qmf-core/examples/sinks_usage.py

Shows what AD-15 / AR-47 pin down for the three sink seams:

1. An outer package persists an observation, a journal event, or a record **only**
   through the matching core-defined :class:`typing.Protocol` — ``ObservationSink``,
   ``JournalSink``, ``RecordSink`` — injected at the composition root. ``qmf-core``
   performs no I/O; these reference sinks stand in for the wired ones.
2. A successful write returns ``Ok(SinkAck)``; the writer proceeds.
3. An **unpersistable** write returns a CT-04 ``storage failure`` typed refusal
   (built with :func:`unpersistable`). The writer that holds the ``WriterId`` sees
   it, and :func:`is_unpersistable` is the predicate it branches on to **block its
   command stream** — never dropping the intent, never assuming success.

The reference sinks here are pure in-memory stand-ins for examples and tests, not
the platform's stores.
"""

from __future__ import annotations

from qmf.core.refusal import Ok, Retryability, TypedRefusal, is_ok
from qmf.core.sinks import (
    JournalSink,
    ObservationSink,
    RecordSink,
    SinkAck,
    SinkResult,
    is_unpersistable,
    unpersistable,
)


class ListObservationSink:
    """A reference :class:`ObservationSink` that records observations in memory."""

    def __init__(self) -> None:
        self.stored: list[object] = []

    def emit(self, observation: object, /) -> SinkResult:
        self.stored.append(observation)
        return Ok(SinkAck(detail={"stored_count": len(self.stored)}))


class CapacityJournalSink:
    """A reference :class:`JournalSink` whose store fills after ``capacity`` events.

    Once full, an append is **unpersistable**: it returns a ``storage failure``
    refusal rather than silently dropping the event, so a writer can block on it.
    """

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self.events: list[object] = []

    def append(self, event: object, /) -> SinkResult:
        if len(self.events) >= self._capacity:
            return unpersistable(
                "journal store is full",
                retryability=Retryability.AFTER_CONDITION,
                context={"capacity": self._capacity},
                after_condition_descriptor="free space in the journal store",
            )
        self.events.append(event)
        return Ok(SinkAck())


class ListRecordSink:
    """A reference :class:`RecordSink` that writes records in memory."""

    def __init__(self) -> None:
        self.written: list[object] = []

    def write(self, record: object, /) -> SinkResult:
        self.written.append(record)
        return Ok(SinkAck())


def a_write_that_lands(sink: ObservationSink[object], observation: object) -> SinkAck:
    """A successful write returns an acknowledgment; the writer proceeds."""
    result = sink.emit(observation)
    assert is_ok(result)
    return result.value


def block_on_unpersistable(
    journal: JournalSink[str], events: list[str]
) -> tuple[int, TypedRefusal | None]:
    """Emit events until one is unpersistable, then block the command stream.

    Returns how many landed and the blocking refusal (or ``None`` if all landed).
    On a ``storage failure`` the writer stops — it does not drop the event or
    advance past it — exactly the block-on-unpersistable rule (AR-47).
    """
    written = 0
    for event in events:
        outcome = journal.append(event)
        if is_unpersistable(outcome):
            assert isinstance(outcome, TypedRefusal)
            return written, outcome
        written += 1
    return written, None


def main() -> None:
    # The composition root injects each concrete sink AS its port — the static
    # conformance the type checker proves, exactly how a real root wires them.
    observations: ObservationSink[object] = ListObservationSink()
    records: RecordSink[object] = ListRecordSink()
    journal: JournalSink[str] = CapacityJournalSink(capacity=2)

    ack = a_write_that_lands(observations, {"kind": "quote", "bid": "1.10", "ask": "1.11"})
    print(f"observation persisted: {ack.detail['stored_count'] == 1}")

    record_result = records.write({"kind": "promotion-card", "fp": "fp1:sha256:demo"})
    print(f"record persisted: {is_ok(record_result)}")

    landed, block = block_on_unpersistable(journal, ["e1", "e2", "e3", "e4"])
    assert block is not None
    print(f"journal blocked after {landed} events on unpersistable: {landed == 2}")
    print(f"block refusal category: {block.category.value}")
    print(f"block retryable after: {block.after_condition_descriptor}")


if __name__ == "__main__":
    main()
