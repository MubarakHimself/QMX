"""Tier-1 tests for the CT-13 journal producer and reader (Story 3.5; AC1, AC2, AC5).

Covers gapless sequence minting, qmf-data's two wired producer types, the store seam's
inherited second-writer refusal, block-on-unpersistable (an unpersistable event and a
partial multi-room write both block the command stream, retain the event, and journal it
on recovery), and the reader's gap-as-loss signal.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from qmf.core import (
    Fingerprint,
    Result,
    World,
    WriterId,
    is_ok,
    is_refusal,
    is_unpersistable,
)
from qmf.data import (
    CausalEdge,
    EvidenceStore,
    JournalEvent,
    JournalReader,
    JournalWriter,
)
from qmf.data.store import JournalStore, StoreEngineError, StoreReceipt
from qmf.data.store.engines import AppendLocation, AppendStreamEngine
from qmf.data.store.engines.jsonl import jsonl_opener
from qmf.data.store.refusals import storage_failure


def _writer(machine: str = "node-a", role: str = "data", stream: str = "dq") -> WriterId:
    built = WriterId.try_create(machine, role, stream, "boot-1")
    assert is_ok(built)
    return built.value


def _live_journal(store: EvidenceStore) -> JournalStore:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return world.value.journal


def _sole_journal_file(store: EvidenceStore, stream: str) -> Path:
    matches = sorted(store.root.glob(f"**/journal/{stream}/*.jsonl"))
    assert len(matches) == 1, matches
    return matches[0]


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


def _flaky_journal(tmp_path: Path, fail: list[bool]) -> JournalStore:
    def opener(stream_dir: Path, writer_token: str, /) -> AppendStreamEngine:
        return _FlakyStream(jsonl_opener()(stream_dir, writer_token), fail)

    return JournalStore(World.LIVE, journal_dir=tmp_path / "journal", open_stream=opener)


# --- AC1 / AC2: gapless sequences and the wired producers -------------------


def test_record_advances_a_gapless_sequence(store: EvidenceStore) -> None:
    jw = JournalWriter(_live_journal(store), _writer(), stream_name="dq")
    for i in range(4):
        result = jw.record_data_quality({"n": i}, instant=1_000 + i)
        assert is_ok(result)
        assert result.value.event.sequence == i
    assert jw.next_sequence == 4
    events = JournalReader(_live_journal(store)).read_checked("dq", for_world=World.LIVE)
    assert is_ok(events)
    assert [e.sequence for e in events.value] == [0, 1, 2, 3]


def test_wired_control_action_carries_its_subtype(store: EvidenceStore) -> None:
    jw = JournalWriter(_live_journal(store), _writer(stream="ca"), stream_name="ca")
    result = jw.record_control_action("throttle engaged", instant=1)
    assert is_ok(result)
    payload = dict(result.value.event.payload)
    assert payload["control_action_subtype"] == "throttle engaged"
    assert result.value.event.event_type.value == "control action"


def test_blank_control_action_subtype_is_invalid_input(store: EvidenceStore) -> None:
    jw = JournalWriter(_live_journal(store), _writer(stream="ca"), stream_name="ca")
    result = jw.record_control_action("   ", instant=1)
    assert is_refusal(result)
    assert result.context.get("field") == "control_action_subtype"


def test_stream_name_defaults_to_the_writer_stream(store: EvidenceStore) -> None:
    jw = JournalWriter(_live_journal(store), _writer(stream="dq"))
    assert jw.stream_name == "dq"
    assert is_ok(jw.record_data_quality({"n": 0}, instant=1))


def test_invalid_event_changes_no_state(store: EvidenceStore) -> None:
    jw = JournalWriter(_live_journal(store), _writer(), stream_name="dq")
    bad = jw.record("heartbeat", instant=1)
    assert is_refusal(bad)
    assert not jw.is_blocked
    assert jw.next_sequence == 0  # no sequence consumed


# --- AC2: the store seam's second-writer refusal is inherited ---------------


def test_second_distinct_writer_does_not_proceed(store: EvidenceStore) -> None:
    journal = _live_journal(store)
    first = JournalWriter(journal, _writer(machine="node-a"), stream_name="dq")
    assert is_ok(first.record_data_quality({"n": 0}, instant=1))
    second = JournalWriter(journal, _writer(machine="node-b"), stream_name="dq")
    result = second.record_data_quality({"n": 0}, instant=2)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_simulated_world_write_is_policy_rejection_not_a_block() -> None:
    journal = JournalStore(World.SIMULATED, journal_dir=Path(), open_stream=jsonl_opener())
    jw = JournalWriter(journal, _writer(), stream_name="dq")
    result = jw.record_data_quality({"n": 0}, instant=1)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"
    # A permanent policy rejection never blocks the stream.
    assert not jw.is_blocked


# --- AC5: block-on-unpersistable --------------------------------------------


def test_unpersistable_event_blocks_and_is_journaled_on_recovery(tmp_path: Path) -> None:
    fail = [False]
    journal = _flaky_journal(tmp_path, fail)
    jw = JournalWriter(journal, _writer(), stream_name="dq")
    assert is_ok(jw.record_data_quality({"n": 0}, instant=1))

    fail[0] = True
    blocked = jw.record_data_quality({"n": 1}, instant=2)
    assert is_unpersistable(blocked)
    assert jw.is_blocked
    assert jw.next_sequence == 1  # not advanced on failure
    assert jw.blocked_event is not None
    assert jw.blocked_event.sequence == 1  # the event is retained, never lost

    # While blocked, a further record refuses and consumes no sequence.
    still = jw.record_data_quality({"n": 2}, instant=3)
    assert is_unpersistable(still)
    assert is_refusal(still)
    assert still.context.get("blocked_sequence") == 1
    assert jw.next_sequence == 1

    # On recovery the retained event is durably journaled and the stream resumes.
    fail[0] = False
    recovered = jw.retry_blocked()
    assert is_ok(recovered)
    assert recovered.value.event.sequence == 1
    assert not jw.is_blocked
    assert jw.next_sequence == 2

    # The stream continues gaplessly, and the retained event landed exactly once.
    assert is_ok(jw.record_data_quality({"n": 3}, instant=4))
    events = JournalReader(journal).read_checked("dq", for_world=World.LIVE)
    assert is_ok(events)
    assert [e.sequence for e in events.value] == [0, 1, 2]
    assert [dict(e.payload)["n"] for e in events.value] == [0, 1, 3]


def test_retry_still_failing_store_stays_blocked(tmp_path: Path) -> None:
    fail = [False]
    journal = _flaky_journal(tmp_path, fail)
    jw = JournalWriter(journal, _writer(), stream_name="dq")
    fail[0] = True
    assert is_unpersistable(jw.record_data_quality({"n": 0}, instant=1))
    # Store still down: retry stays blocked.
    again = jw.retry_blocked()
    assert is_unpersistable(again)
    assert jw.is_blocked
    # Now it recovers.
    fail[0] = False
    assert is_ok(jw.retry_blocked())
    assert not jw.is_blocked


def test_retry_with_nothing_blocked_is_invalid_input(store: EvidenceStore) -> None:
    jw = JournalWriter(_live_journal(store), _writer(), stream_name="dq")
    result = jw.retry_blocked()
    assert is_refusal(result)
    assert result.context.get("field") == "retry_blocked"


def test_retry_blocked_is_idempotent_after_a_double_recovery(tmp_path: Path) -> None:
    # A byte-identical re-append on retry does not duplicate the line.
    fail = [False]
    journal = _flaky_journal(tmp_path, fail)
    jw = JournalWriter(journal, _writer(), stream_name="dq")
    fail[0] = True
    assert is_unpersistable(jw.record_data_quality({"n": 0}, instant=1))
    fail[0] = False
    assert is_ok(jw.retry_blocked())
    events = JournalReader(journal).read("dq", for_world=World.LIVE)
    assert is_ok(events)
    assert len(events.value) == 1


# --- AC5: partial multi-room write blocks -----------------------------------


def test_partial_multi_room_write_blocks_and_recovers(store: EvidenceStore) -> None:
    journal = _live_journal(store)
    registry_room = store.for_world(World.LIVE)
    assert is_ok(registry_room)
    room = registry_room.value.registry_room
    edge_writer = _writer(role="lineage", stream="journal-edges")

    fail = [True]

    # A real secondary room write: append a CausalEdge from the new event to a target,
    # but return a storage failure while ``fail[0]`` is set (the edge room is down).
    def secondary(event_fp: Fingerprint) -> Result[StoreReceipt]:
        if fail[0]:
            return storage_failure("edge room unavailable")
        edge = CausalEdge.try_create(
            edge_type="enacts",
            from_ref=event_fp,
            to_ref=event_fp,
            writer=edge_writer,
        )
        assert is_ok(edge)
        return room.append_lineage_edge("journal-edges", edge_writer, edge.value.to_row())

    jw = JournalWriter(journal, _writer(), stream_name="dq")
    # The journal event lands but the edge fails: a partial multi-room write blocks.
    partial = jw.record_multiroom("data quality", {"n": 0}, instant=1, extra_writes=[secondary])
    assert is_unpersistable(partial)
    assert jw.is_blocked
    assert jw.next_sequence == 0  # not advanced on a partial write

    # The journal event physically landed (the partial half), but the operation is not
    # counted done until the edge lands too — recovery completes it idempotently.
    fail[0] = False
    recovered = jw.retry_blocked()
    assert is_ok(recovered)
    assert not jw.is_blocked
    assert jw.next_sequence == 1
    assert len(recovered.value.edge_receipts) == 1

    # The causal edge now exists in the registry room's lineage stream.
    edges = room.read_lineage("journal-edges", for_world=World.LIVE)
    assert is_ok(edges)
    assert len(edges.value) == 1
    assert edges.value[0]["edge_type"] == "enacts"


# --- AC2: reader gap detection ----------------------------------------------


def test_reader_surfaces_a_gap_as_loss(tmp_path: Path) -> None:
    # Write sequences 0 and 2 directly through the store (a lost sequence 1), then read.
    journal = JournalStore(World.LIVE, journal_dir=tmp_path / "journal", open_stream=jsonl_opener())
    writer = _writer()
    for seq, instant in ((0, 1), (2, 3)):
        event = JournalEvent.try_create(
            event_type="data quality",
            writer=writer,
            sequence=seq,
            instant=instant,
            world=World.LIVE,
            payload={"n": seq},
        )
        assert is_ok(event)
        assert is_ok(journal.append("dq", writer, event.value.to_row()))

    reader = JournalReader(journal)
    plain = reader.read("dq", for_world=World.LIVE)
    assert is_ok(plain)  # a plain read does not check for gaps
    checked = reader.read_checked("dq", for_world=World.LIVE)
    assert is_refusal(checked)
    assert checked.category.value == "storage failure"
    assert checked.context.get("signal") == "loss"


def test_reader_cross_world_read_is_policy_rejection(store: EvidenceStore) -> None:
    journal = _live_journal(store)
    jw = JournalWriter(journal, _writer(), stream_name="dq")
    assert is_ok(jw.record_data_quality({"n": 0}, instant=1))
    reader = JournalReader(journal)
    result = reader.read("dq", for_world=World.REPLAY)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_reader_corrupt_row_is_refused(tmp_path: Path) -> None:
    journal = JournalStore(World.LIVE, journal_dir=tmp_path / "journal", open_stream=jsonl_opener())
    writer = _writer()
    # A hand-written row whose stored fingerprint does not match its content.
    bad_row: Mapping[str, object] = {
        "event_type": "data quality",
        "writer": {
            "machine": writer.machine,
            "role": writer.role,
            "stream": writer.stream,
            "boot_epoch_id": writer.boot_epoch_id,
        },
        "sequence": 0,
        "instant_ns": 1,
        "world": "live",
        "payload": {"n": 0},
        "fingerprint": "fp1:sha256:" + "0" * 64,
        "format_version": 1,
    }
    assert is_ok(journal.append("dq", writer, bad_row))
    result = JournalReader(journal).read("dq", for_world=World.LIVE)
    assert is_refusal(result)
    assert result.context.get("field") == "fingerprint"


def test_reader_refuses_a_hand_planted_foreign_world_row(store: EvidenceStore) -> None:
    # Read-side world guard (defense in depth): the write-side guard already blocks a
    # cross-world event from ever landing, but a well-formed foreign-world row hand-planted
    # DIRECTLY into a live stream file must not be served either. read_stream re-checks every
    # stored row's declared world against the room's and refuses a mismatch as corrupt
    # evidence — world isolation holds on the stored bytes, not just the read's declared world.
    journal = _live_journal(store)
    writer = _writer()
    jw = JournalWriter(journal, writer, stream_name="dq")
    assert is_ok(jw.record_data_quality({"n": 0}, instant=1))  # a legitimate live row

    # A valid REPLAY event: its world is folded into fp1, so the row carries a valid
    # fingerprint and would pass from_row's tamper check — only the world guard catches it.
    foreign = JournalEvent.try_create(
        event_type="data quality",
        writer=writer,
        sequence=0,
        instant=2,
        world=World.REPLAY,
        payload={"n": 1},
    )
    assert is_ok(foreign)

    # Direct file tampering: append the replay row as an LF-terminated line to the live file.
    journal_file = _sole_journal_file(store, "dq")
    assert journal_file.is_file(), "the journal rotation file must exist before tampering"
    with journal_file.open("ab") as handle:
        handle.write(json.dumps(foreign.value.to_row()).encode("utf-8") + b"\n")

    result = JournalReader(journal).read("dq", for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category.value == "storage failure"
    assert result.retryability.value == "no"
    assert result.context.get("room_world") == "live"
    assert result.context.get("declared") == "replay"
    # The store-level read_stream is the choke point, so a plain read_stream refuses too.
    assert is_refusal(journal.read_stream("dq", for_world=World.LIVE))


# --- L10: restart-resume and stream-derived gap base ------------------------


def _seed_stream(journal: JournalStore, writer: WriterId, sequences: tuple[int, ...]) -> None:
    for seq in sequences:
        event = JournalEvent.try_create(
            event_type="data quality",
            writer=writer,
            sequence=seq,
            instant=1_000 + seq,
            world=World.LIVE,
            payload={"n": seq},
        )
        assert is_ok(event)
        assert is_ok(journal.append("dq", writer, event.value.to_row()))


def test_resume_derives_next_sequence_and_produces_no_duplicates(tmp_path: Path) -> None:
    # L10: a restart under the SAME boot_epoch_id must resume past the persisted tail, not
    # re-issue sequences already on disk (which detect_sequence_gaps reports as duplicate loss).
    journal_dir = tmp_path / "journal"
    writer = _writer()
    first = JournalStore(World.LIVE, journal_dir=journal_dir, open_stream=jsonl_opener())
    jw = JournalWriter(first, writer, stream_name="dq")
    for i in range(3):
        assert is_ok(jw.record_data_quality({"n": i}, instant=1_000 + i))
    assert jw.next_sequence == 3
    first.close()  # clean shutdown releases the one-writer hold

    # A true restart: a fresh store over the same directory, resuming the same writer.
    second = JournalStore(World.LIVE, journal_dir=journal_dir, open_stream=jsonl_opener())
    resumed = JournalWriter.resume(second, writer, stream_name="dq")
    assert is_ok(resumed)
    jw2 = resumed.value
    assert jw2.next_sequence == 3  # derived from the tail, not restarted at 0
    for i in range(3, 5):
        result = jw2.record_data_quality({"n": i}, instant=1_000 + i)
        assert is_ok(result)
        assert result.value.event.sequence == i

    checked = JournalReader(second).read_checked("dq", for_world=World.LIVE)
    assert is_ok(checked)  # no duplicate, no gap
    assert [e.sequence for e in checked.value] == [0, 1, 2, 3, 4]


def test_resume_on_empty_stream_starts_at_zero(store: EvidenceStore) -> None:
    resumed = JournalWriter.resume(_live_journal(store), _writer(), stream_name="fresh")
    assert is_ok(resumed)
    assert resumed.value.next_sequence == 0


def test_resume_new_boot_epoch_starts_its_own_run_at_zero(tmp_path: Path) -> None:
    # A resume under a DIFFERENT boot_epoch_id is a new gapless run: no matching events, so it
    # starts at 0 — its own per-(writer, boot-epoch) sequence, independent of the prior epoch.
    journal_dir = tmp_path / "journal"
    epoch_one = _writer()
    journal = JournalStore(World.LIVE, journal_dir=journal_dir, open_stream=jsonl_opener())
    _seed_stream(journal, epoch_one, (0, 1, 2))
    epoch_two = WriterId.try_create("node-a", "data", "dq", "boot-2")
    assert is_ok(epoch_two)
    resumed = JournalWriter.resume(journal, epoch_two.value, stream_name="dq")
    assert is_ok(resumed)
    assert resumed.value.next_sequence == 0


def test_resume_propagates_a_corrupt_stream_refusal(tmp_path: Path) -> None:
    # A corrupt stream surfaces as the reader's storage-failure refusal, never a silent
    # resume-at-zero that would then re-issue and manufacture duplicates.
    journal = JournalStore(World.LIVE, journal_dir=tmp_path / "journal", open_stream=jsonl_opener())
    writer = _writer()
    bad_row: Mapping[str, object] = {
        "event_type": "data quality",
        "writer": {
            "machine": writer.machine,
            "role": writer.role,
            "stream": writer.stream,
            "boot_epoch_id": writer.boot_epoch_id,
        },
        "sequence": 0,
        "instant_ns": 1,
        "world": "live",
        "payload": {"n": 0},
        "fingerprint": "fp1:sha256:" + "0" * 64,
        "format_version": 1,
    }
    assert is_ok(journal.append("dq", writer, bad_row))
    resumed = JournalWriter.resume(journal, writer, stream_name="dq")
    assert is_refusal(resumed)


def test_read_checked_derives_expected_start_from_stream(tmp_path: Path) -> None:
    # L10: a stream legitimately beginning at a non-zero sequence (a writer resumed from
    # start=N) must not trip a false "gap from 0" alarm; read_checked derives the base from
    # the stream's own minimum. An explicit expected_start still asserts a specific base.
    journal = JournalStore(World.LIVE, journal_dir=tmp_path / "journal", open_stream=jsonl_opener())
    writer = _writer()
    _seed_stream(journal, writer, (5, 6, 7))
    reader = JournalReader(journal)
    checked = reader.read_checked("dq", for_world=World.LIVE)
    assert is_ok(checked)  # 5,6,7 contiguous from its own base — no false alarm
    assert [e.sequence for e in checked.value] == [5, 6, 7]
    strict = reader.read_checked("dq", for_world=World.LIVE, expected_start=0)
    assert is_refusal(strict)  # an explicit from-zero assertion still surfaces the prefix gap


def test_read_checked_still_surfaces_interior_gap_with_derived_start(tmp_path: Path) -> None:
    journal = JournalStore(World.LIVE, journal_dir=tmp_path / "journal", open_stream=jsonl_opener())
    writer = _writer()
    _seed_stream(journal, writer, (5, 7))  # missing 6
    checked = JournalReader(journal).read_checked("dq", for_world=World.LIVE)
    assert is_refusal(checked)  # derived base 5, interior gap at 6 still surfaced as loss
    assert checked.context.get("signal") == "loss"
