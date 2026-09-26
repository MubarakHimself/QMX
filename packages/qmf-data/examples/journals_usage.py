"""Reference usage — durable journals, seven event types in gapless streams (Story 3.5).

Executable::

    python packages/qmf-data/examples/journals_usage.py

Shows the six things Story 3.5 pins down:

1. Journal evidence is N append-only streams, one per producing component, each under one
   ``WriterId`` — qmf-data's own wired producers are the data-quality and control-action
   types, appended at a strictly-increasing gapless sequence.
2. A ``decision`` event carries a mandatory closed outcome (authorized | refused-by-door |
   suppressed) with its reference, and a projection (the legacy ``veto_ledger``) selects on
   that declared field, never on key presence.
3. Journal identity is fp1-canonical with ``correlation_id`` and ``display_time`` excluded:
   two events differing only in correlation_id share one identity, and the journal stores
   the int64-ns instant while the operator log renders the ISO-8601-Z display time.
4. Cross-stream causal linkage rides only typed edge records referencing fp1 fingerprints —
   never a timestamp or the (instant, writer, sequence) ordering key.
5. A detected sequence gap signals loss and is surfaced, never swallowed.
6. Block-on-unpersistable: an event that cannot be durably persisted blocks the command
   stream, is retained, and is journaled on recovery — never silently lost.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Result,
    World,
    WriterId,
    is_ok,
    is_refusal,
    is_unpersistable,
)
from qmf.data import (
    CausalEdge,
    DecisionOutcome,
    EvidenceStore,
    JournalEvent,
    JournalReader,
    JournalWriter,
    detect_sequence_gaps,
    veto_ledger,
)
from qmf.data.store import JournalStore, StoreEngineError
from qmf.data.store.engines import AppendLocation, AppendStreamEngine
from qmf.data.store.engines.jsonl import jsonl_opener

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a call we require to succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    """A real check (not a bare ``assert``, which ``-O`` strips) for a demonstrated fact."""
    if not condition:
        raise AssertionError(f"expected {what}")


def _writer(store_stream: str) -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "data", store_stream, "boot-1"), "writer")


def gapless_wired_producer(store: EvidenceStore) -> list[int]:
    """qmf-data appends its data-quality events under one WriterId, gapless."""
    journal = _unwrap(store.for_world(World.LIVE), "live journal").journal
    writer = JournalWriter(journal, _writer("dq"), stream_name="dq")
    for i in range(3):
        _unwrap(writer.record_data_quality({"metric": "spread", "n": i}, instant=1_000 + i), "dq")
    events = _unwrap(JournalReader(journal).read_checked("dq", for_world=World.LIVE), "read")
    return [event.sequence for event in events]


def decision_outcome_projection(store: EvidenceStore) -> list[str]:
    """A decision carries a closed outcome; veto_ledger selects on that declared field."""
    journal = _unwrap(store.for_world(World.LIVE), "live journal").journal
    writer = JournalWriter(journal, _writer("decisions"), stream_name="decisions")
    _unwrap(
        writer.record(
            "decision",
            {"bot": "b1"},
            instant=2_000,
            outcome=DecisionOutcome.AUTHORIZED,
        ),
        "authorized",
    )
    _unwrap(
        writer.record(
            "decision",
            {"refusing_door": "spread-door"},
            instant=2_001,
            outcome=DecisionOutcome.REFUSED_BY_DOOR,
        ),
        "refused",
    )
    events = _unwrap(JournalReader(journal).read("decisions", for_world=World.LIVE), "read")
    refused = veto_ledger(events)
    _require(len(refused) == 1, "veto_ledger selects the one refused-by-door decision")
    return [str(dict(event.payload).get("refusing_door", "")) for event in refused if event.payload]


def identity_excludes_correlation_and_display() -> tuple[bool, str]:
    """Two events differing only in correlation_id share one fp1; display is ISO-8601-Z."""
    writer = _writer("dq")
    a = _unwrap(
        JournalEvent.try_create(
            event_type="data quality",
            writer=writer,
            sequence=0,
            instant=1_000_000_000,
            world=World.LIVE,
            payload={"metric": "spread"},
            correlation_id="corr-A",
        ),
        "event a",
    )
    b = _unwrap(
        JournalEvent.try_create(
            event_type="data quality",
            writer=writer,
            sequence=0,
            instant=1_000_000_000,
            world=World.LIVE,
            payload={"metric": "spread"},
            correlation_id="corr-B",
        ),
        "event b",
    )
    same_identity = a.fingerprint.value == b.fingerprint.value
    _require(same_identity, "correlation_id is excluded from fp1 identity")
    _require(a.to_row()["instant_ns"] == 1_000_000_000, "the journal stores the int64-ns instant")
    display = _unwrap(a.render_display_time(), "display time")
    return same_identity, display.text


def causal_edge_links_by_fp1() -> str:
    """Cross-stream causal linkage is a typed edge referencing fp1s, not the ordering key."""
    writer = _writer("dq")
    decision = _unwrap(
        JournalEvent.try_create(
            event_type="decision",
            writer=writer,
            sequence=0,
            instant=3_000,
            world=World.LIVE,
            payload={"bot": "b1"},
            outcome=DecisionOutcome.AUTHORIZED,
        ),
        "decision",
    )
    order = _unwrap(
        JournalEvent.try_create(
            event_type="order",
            writer=writer,
            sequence=1,
            instant=3_001,
            world=World.LIVE,
            payload={"client_id": "c-1"},
        ),
        "order",
    )
    edge = _unwrap(CausalEdge.link("enacts", order, decision), "causal edge")
    row = edge.to_row()
    _require(row["from_ref"] == order.fingerprint.value, "edge references the order's fp1")
    _require(row["to_ref"] == decision.fingerprint.value, "edge references the decision's fp1")
    return str(row["edge_type"])


def gap_signals_loss() -> str:
    """A missing sequence in a stream is surfaced as loss, never swallowed."""
    writer = _writer("dq")
    events = [
        _unwrap(
            JournalEvent.try_create(
                event_type="data quality",
                writer=writer,
                sequence=seq,
                instant=4_000 + seq,
                world=World.LIVE,
                payload={"n": seq},
            ),
            "event",
        )
        for seq in (0, 1, 3)  # sequence 2 was lost
    ]
    result = detect_sequence_gaps(events)
    _require(is_refusal(result), "a gap is surfaced as a refusal")
    return result.category.value if is_refusal(result) else "unexpected-ok"


def block_on_unpersistable(tmp: Path) -> tuple[bool, list[int]]:
    """An unpersistable event blocks the stream and is journaled on recovery."""
    fail = [False]

    def opener(stream_dir: Path, writer_token: str, /) -> AppendStreamEngine:
        return _FlakyStream(jsonl_opener()(stream_dir, writer_token), fail)

    journal = JournalStore(World.LIVE, journal_dir=tmp / "journal", open_stream=opener)
    writer = JournalWriter(journal, _writer("dq"), stream_name="dq")
    _unwrap(writer.record_data_quality({"n": 0}, instant=1), "first event")

    fail[0] = True
    blocked = writer.record_data_quality({"n": 1}, instant=2)
    _require(is_unpersistable(blocked), "the unpersistable event is a storage failure")
    _require(writer.is_blocked, "the command stream is blocked")
    _require(writer.next_sequence == 1, "the sequence does not advance on failure")

    fail[0] = False
    recovered = _unwrap(writer.retry_blocked(), "recovery")
    _require(not writer.is_blocked, "the stream resumes after recovery")

    events = _unwrap(JournalReader(journal).read_checked("dq", for_world=World.LIVE), "read")
    return recovered.event.sequence == 1, [event.sequence for event in events]


class _FlakyStream:
    """An AppendStreamEngine wrapper whose ``append`` raises while ``fail[0]`` is set."""

    def __init__(self, inner: AppendStreamEngine, fail: list[bool]) -> None:
        self._inner = inner
        self._fail = fail

    def acquire(self) -> Result[None]:
        return self._inner.acquire()

    def append(self, canonical: bytes, /) -> AppendLocation:
        if self._fail[0]:
            raise StoreEngineError("disk full", engine="jsonl", retryable=True)
        return self._inner.append(canonical)

    def find(self, digest: str, /) -> bytes | None:
        return self._inner.find(digest)

    def location_of(self, digest: str, /) -> AppendLocation | None:
        return self._inner.location_of(digest)

    def read_all(self) -> list[bytes]:
        return self._inner.read_all()

    def rebuild_index(self) -> None:
        self._inner.rebuild_index()

    def release(self) -> None:
        self._inner.release()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qmf-journals-") as tmp:
        store = EvidenceStore(Path(tmp) / "store")

        sequences = gapless_wired_producer(store)
        print(f"gapless data-quality stream: sequences={sequences}")

        refusing_doors = decision_outcome_projection(store)
        print(f"veto_ledger (refused-by-door) selects on the declared outcome: {refusing_doors}")

        same_identity, display = identity_excludes_correlation_and_display()
        print(f"correlation_id excluded from fp1: {same_identity}; display time (log): {display}")

        edge_type = causal_edge_links_by_fp1()
        print(f"cross-stream causal linkage is a typed edge: {edge_type} (references fp1s)")

        loss = gap_signals_loss()
        print(f"a sequence gap is surfaced as loss: {loss}")

        landed, resumed = block_on_unpersistable(Path(tmp) / "flaky")
        print(
            f"block-on-unpersistable: recovered event landed={landed}, stream sequences={resumed}"
        )


if __name__ == "__main__":
    main()
