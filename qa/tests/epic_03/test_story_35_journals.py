"""Epic 3 — Story 3.5: durable journals, seven event types, gapless streams (FR-013 / CT-13).

Independent tests from Story 3.5 AC1-AC5 and PLAN Section 4 (3.5-U1..U6, P1, P2, C1, I1).
Refusal assertions check the CT-04 category.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from qmf.core import Ok, Result, World, is_ok
from qmf.data.journal import (
    CausalEdge,
    DecisionOutcome,
    JournalEvent,
    JournalEventType,
    detect_sequence_gaps,
    select_decisions,
    veto_ledger,
)
from qmf.data.journal_producer import JournalReader, JournalWriter
from qmf.data.store import EvidenceStore
from qmf.data.store.engines import AppendLocation, StoreEngineError
from qmf.data.store.journal import JournalStore

import _epic3_helpers as H

_SEVEN = {
    "decision",
    "order",
    "fill",
    "risk transition",
    "promotion",
    "data quality",
    "control action",
}


def _event(**over: object) -> Result[JournalEvent]:
    base: dict[str, object] = dict(
        event_type=JournalEventType.DATA_QUALITY,
        writer=H.writer(),
        sequence=0,
        instant=1_000,
        world=World.LIVE,
    )
    base.update(over)
    return JournalEvent.try_create(**base)


# --- 3.5-U1 (L1): only the seven event types are journal events ---------------


def test_3_5_u1_only_seven_event_types() -> None:
    """AC1: the seven ratified types build; a type outside the set is an invalid input refusal."""
    assert {t.value for t in JournalEventType} == _SEVEN
    for t in JournalEventType:
        payload = None
        outcome = None
        if t is JournalEventType.DECISION:
            outcome = DecisionOutcome.AUTHORIZED
        assert is_ok(_event(event_type=t, outcome=outcome, payload=payload)), t
    # a type outside the seven is refused
    H.assert_refusal(_event(event_type="liquidation"), "invalid input")


# --- 3.5-U2 (L1): a detected gap surfaces loss --------------------------------


def test_3_5_u2_sequence_gap_surfaces_loss() -> None:
    """AC2: a gap in a per-(writer, boot-epoch) sequence surfaces as a storage-failure loss signal."""
    w = H.writer()
    events = [
        H.unwrap(_event(writer=w, sequence=0)),
        H.unwrap(_event(writer=w, sequence=1)),
        H.unwrap(_event(writer=w, sequence=3)),  # 2 is missing
    ]
    gap = detect_sequence_gaps(events, expected_start=0)
    H.assert_refusal(gap, "storage failure")
    assert gap.context.get("signal") == "loss"
    # a contiguous stream is gapless
    contiguous = [H.unwrap(_event(writer=w, sequence=i)) for i in range(3)]
    assert is_ok(detect_sequence_gaps(contiguous, expected_start=0))


# --- 3.5-U3 (L1): a second writer to a held stream does not proceed -----------


def test_3_5_u3_second_writer_refused(tmp_path: Path) -> None:
    """AC2/DEC-0113: a second distinct WriterId writing a held stream does not proceed."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    w1 = H.writer(machine="a", stream="s")
    w2 = H.writer(machine="b", stream="s")
    H.unwrap(ws.journal.append("stream", w1, {"event_type": "data quality", "n": 1}))
    H.assert_refusal(ws.journal.append("stream", w2, {"event_type": "data quality", "n": 2}), "policy rejection")


# --- 3.5-U4 (L1): decision outcome is a closed field; projection selects on it -


def test_3_5_u4_decision_outcome_closed_field() -> None:
    """AC3/DEC-0158: a decision without its closed outcome is invalid; projections select on the declared field."""
    # a decision event with no outcome is refused
    H.assert_refusal(_event(event_type=JournalEventType.DECISION, outcome=None), "invalid input")
    # a refused-by-door decision must carry its refusing-door reference
    H.assert_refusal(
        _event(event_type=JournalEventType.DECISION, outcome=DecisionOutcome.REFUSED_BY_DOOR, payload={}),
        "invalid input",
    )
    # a well-formed refused-by-door decision builds
    refused = H.unwrap(
        _event(
            event_type=JournalEventType.DECISION,
            outcome=DecisionOutcome.REFUSED_BY_DOOR,
            payload={"refusing_door": "risk-door-7"},
        )
    )
    authorized = H.unwrap(
        _event(event_type=JournalEventType.DECISION, outcome=DecisionOutcome.AUTHORIZED)
    )
    non_decision = H.unwrap(_event(event_type=JournalEventType.DATA_QUALITY))
    events = [refused, authorized, non_decision]
    # veto_ledger selects on outcome=refused-by-door (the declared field), never key presence
    assert veto_ledger(events) == [refused]
    assert select_decisions(events, outcome=DecisionOutcome.AUTHORIZED) == [authorized]
    # a non-decision event carrying an outcome is refused (only a decision carries one)
    H.assert_refusal(
        _event(event_type=JournalEventType.ORDER, outcome=DecisionOutcome.AUTHORIZED), "invalid input"
    )


# --- 3.5-U5 (L1): correlation_id/display_time out of fp1; causality by edges ---


def test_3_5_u5_correlation_and_causality() -> None:
    """AC4/DEC-0112: correlation_id/display_time are excluded from fp1; causal linkage rides typed edges only."""
    base = H.unwrap(_event(correlation_id=None))
    with_corr = H.unwrap(_event(correlation_id="corr-1"))
    # two events differing only in correlation_id share one fp1 identity
    assert base.fingerprint.value == with_corr.fingerprint.value
    # a causal edge references two events by fp1, never by timestamp or the ordering key
    other = H.unwrap(_event(sequence=1))
    edge = H.unwrap(CausalEdge.link("supersedes", with_corr, other))
    assert edge.from_ref.value == with_corr.fingerprint.value
    assert edge.to_ref.value == other.fingerprint.value
    row = edge.to_row()
    assert row["from_ref"] == with_corr.fingerprint.value
    assert "instant" not in row and "sequence" not in row  # never rides a time/ordering key


# --- 3.5-U6 (L1): an unpersistable event blocks the stream, never silent loss --


class _RaisingAppendStream:
    """An append-stream engine whose append raises (an unpersistable journal write)."""

    def acquire(self) -> Result[None]:
        return Ok(None)

    def append(self, canonical: bytes, /) -> AppendLocation:
        raise StoreEngineError("disk full", engine="jsonl", detail={"len": len(canonical)})

    def find(self, digest: str, /) -> bytes | None:
        return None

    def location_of(self, digest: str, /) -> AppendLocation | None:
        return None

    def read_all(self) -> list[bytes]:
        return []

    def rebuild_index(self) -> None:
        return None

    def release(self) -> None:
        return None


def _raising_opener(stream_dir: Path, writer_token: str, /) -> _RaisingAppendStream:
    return _RaisingAppendStream()


def test_3_5_u6_unpersistable_blocks_stream(tmp_path: Path) -> None:
    """AC5/FM-6: an unpersistable event is a storage-failure that blocks the command stream, never silent loss."""
    journal = JournalStore(World.LIVE, journal_dir=tmp_path / "j", open_stream=_raising_opener)
    writer = JournalWriter(journal, H.writer(stream="dq"), stream_name="dq")
    first = writer.record_data_quality({"n": 1}, instant=1_000)
    H.assert_refusal(first, "storage failure")
    assert writer.is_blocked is True
    assert writer.blocked_event is not None  # the event is retained, never lost
    # while blocked, a later append does not proceed and consumes no sequence
    blocked = writer.record_data_quality({"n": 2}, instant=2_000)
    H.assert_refusal(blocked, "storage failure")
    assert writer.next_sequence == 0  # the sequence was not advanced on the failed append


# --- 3.5-P1 (L2 property): each stream is strictly increasing and gapless -------


@settings(max_examples=60, deadline=None)
@given(
    per_writer=st.lists(st.integers(min_value=1, max_value=6), min_size=1, max_size=3),
    drop=st.booleans(),
)
def test_3_5_p1_gapless_per_writer(per_writer: list[int], drop: bool) -> None:
    """AC2: a contiguous per-(writer, boot-epoch) sequence is gapless; an interior hole surfaces loss."""
    events: list[JournalEvent] = []
    for wi, count in enumerate(per_writer):
        w = H.writer(machine=f"m{wi}", boot=f"boot-{wi}")
        for seq in range(count):
            events.append(H.unwrap(_event(writer=w, sequence=seq)))
    # a fully contiguous multi-writer stream is gapless
    assert is_ok(detect_sequence_gaps(events, expected_start=0))
    # removing an INTERIOR event (seq 1 from a writer with >=3 events, leaving [0, 2, ...])
    # leaves a true hole between 0 and 2 that must surface as loss. (A truncated tail is, by
    # design, undetectable — only interior gaps and duplicates are surfaced.)
    if drop and any(c >= 3 for c in per_writer):
        target_machine = f"m{next(i for i, c in enumerate(per_writer) if c >= 3)}"
        holed = [e for e in events if not (e.writer.machine == target_machine and e.sequence == 1)]
        H.assert_refusal(detect_sequence_gaps(holed, expected_start=0), "storage failure")


# --- 3.5-P2 (L2 property): correlation/display differences share one fp1 --------


@settings(max_examples=60, deadline=None)
@given(
    a=st.one_of(st.none(), st.text(min_size=1, max_size=8).filter(lambda s: s.strip())),
    b=st.one_of(st.none(), st.text(min_size=1, max_size=8).filter(lambda s: s.strip())),
)
def test_3_5_p2_correlation_never_in_identity(a: str | None, b: str | None) -> None:
    """AC4: two events differing ONLY in correlation_id always share the same fp1 identity."""
    ea = _event(correlation_id=a)
    eb = _event(correlation_id=b)
    # both build (a non-blank or None correlation is valid) and share identity
    if is_ok(ea) and is_ok(eb):
        assert ea.value.fingerprint.value == eb.value.fingerprint.value


# --- 3.5-C1 (L3 contract): N-stream journal, one stream per writer -------------


def test_3_5_c1_n_stream_journal_round_trip(tmp_path: Path) -> None:
    """CT-13: N append-only streams, one per producing component; the two wired qmf-data types persist."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    # qmf-data's own wired producers: data quality + control action
    dq = JournalWriter(ws.journal, H.writer(role="data", stream="dq"), stream_name="dq")
    ca = JournalWriter(ws.journal, H.writer(role="data", stream="ca"), stream_name="ca")
    H.unwrap(dq.record_data_quality({"n": 1}, instant=1_000))
    H.unwrap(dq.record_data_quality({"n": 2}, instant=2_000))
    H.unwrap(ca.record_control_action("adapter-restart", instant=1_500))
    reader = JournalReader(ws.journal)
    dq_events = H.unwrap(reader.read_checked("dq", for_world=World.LIVE))
    assert [e.sequence for e in dq_events] == [0, 1]  # gapless, one stream per writer
    assert all(e.event_type is JournalEventType.DATA_QUALITY for e in dq_events)
    ca_events = H.unwrap(reader.read("ca", for_world=World.LIVE))
    assert ca_events[0].event_type is JournalEventType.CONTROL_ACTION
    assert ca_events[0].payload.get("control_action_subtype") == "adapter-restart"


# --- 3.5-I1 (L4 integration): partial multi-room write blocks; recovery replays -


def test_3_5_i1_partial_multiroom_blocks_and_recovers(tmp_path: Path) -> None:
    """AC5: a partial multi-room write (event landed, edge failed) blocks the stream; recovery replays it gaplessly."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    writer = JournalWriter(ws.journal, H.writer(role="data", stream="dq"), stream_name="dq")

    calls = {"n": 0}

    def flaky_edge(fp: object) -> Result[object]:
        # fail the FIRST edge write (partial multi-room), succeed on retry
        calls["n"] += 1
        if calls["n"] == 1:
            return _storage_fail()
        return Ok(_edge_receipt(ws))

    # a normal first event
    H.unwrap(writer.record_data_quality({"n": 0}, instant=500))
    # a multi-room event whose secondary edge write fails -> stream blocks, whole op retained
    partial = writer.record_multiroom(
        JournalEventType.DATA_QUALITY, {"n": 1}, instant=1_000, extra_writes=[flaky_edge]
    )
    H.assert_refusal(partial, "storage failure")
    assert writer.is_blocked is True
    # recovery: retry re-runs the retained operation idempotently and unblocks the stream
    recovered = writer.retry_blocked()
    assert is_ok(recovered)
    assert writer.is_blocked is False
    # the stream replays to a gapless reconstruction (0, 1)
    events = H.unwrap(JournalReader(ws.journal).read_checked("dq", for_world=World.LIVE, expected_start=0))
    assert [e.sequence for e in events] == [0, 1]


def _storage_fail() -> Result[object]:
    from qmf.data.store.refusals import storage_failure

    return storage_failure("edge write failed", context={"room": "lineage"})


def _edge_receipt(ws: object) -> object:
    # a real store receipt from a genuine lineage-edge append (idempotent on retry)
    room = ws.registry_room
    return H.unwrap(
        room.append_lineage_edge(
            "lineage", H.writer(role="registry", stream="lineage"),
            {"edge_type": "enacts", "from_ref": H.fp("a").value, "to_ref": H.fp("b").value},
        )
    )
