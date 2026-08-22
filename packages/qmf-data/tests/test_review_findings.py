"""Regression tests for the Story 3.1 store-seam review findings (H/M/L).

Each test pins the corrected behavior of one verified finding so the bug cannot
return. Engine-level regressions live beside the engines they test (H1/H3/L4/M6 in
`test_jsonl_engine`, H4/H5/L2/L3 in `test_engines_columnar_meta`, M1/M2/H2-at-streams
in `test_streams`); the boundary- and facade-level regressions live here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from qmf.core import World, WriterId, fingerprint, is_ok, is_refusal
from qmf.data.store import EvidenceStore, JournalStore, RoomRole, jsonl_opener
from qmf.data.store.engines import AppendStreamEngine, StoreEngineError
from qmf.data.store.engines.jsonl import JsonlAppendStream


@pytest.fixture
def store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path / "store", rotation_bytes=256)


def _writer(machine: str = "node-a", role: str = "data", stream: str = "dq") -> WriterId:
    built = WriterId.try_create(machine, role, stream, "boot-1")
    assert is_ok(built)
    return built.value


def _sole_journal_file(store: EvidenceStore, stream: str) -> Path:
    matches = sorted(store.root.glob(f"**/journal/{stream}/*.jsonl"))
    assert len(matches) == 1, matches
    return matches[0]


# --- H2 (journal level): a case-alias never duplicates an append-only line ---


def test_case_alias_journal_appends_no_duplicate(store: EvidenceStore) -> None:
    ws = store.for_world(World.LIVE)
    assert is_ok(ws)
    journal = ws.value.journal
    writer = _writer(role="role", stream="s")
    e1 = {"event_type": "data quality", "n": 1}
    e2 = {"event_type": "data quality", "n": 2}
    first = journal.append("Orders", writer, e1)
    second = journal.append("orders", writer, e2)
    third = journal.append("Orders", writer, e2)  # e2 again, via the other casing
    assert is_ok(first)
    assert is_ok(second)
    assert is_ok(third)
    assert first.value.outcome.value == "stored"
    assert second.value.outcome.value == "stored"
    # AC2: the third is a byte-identical re-append — idempotent, no second physical write.
    assert third.value.outcome.value == "idempotent"
    read = journal.read_stream("orders", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == [e1, e2]  # exactly two lines, no duplicate


# --- H2 (boundary level): a torn journal tail recovers read, append, backup ---


def test_torn_journal_tail_recovers_read_append_backup(store: EvidenceStore) -> None:
    # A crash mid-write leaves a torn (no-LF) trailing line. Previously every subsequent
    # open — read_stream, append, AND backup — refused forever and the committed prefix was
    # unreachable. WAL tail handling now keeps the committed prefix readable and appendable
    # and lets backup succeed, matching FAILURES.md's recovery story (H2).
    ws = store.for_world(World.LIVE)
    assert is_ok(ws)
    journal = ws.value.journal
    writer = _writer(role="data", stream="dq")
    assert is_ok(journal.append("dq", writer, {"event_type": "data quality", "n": 0}))

    # Simulate a crash mid-write: append a torn (no-LF) partial line to the stream file.
    journal_file = _sole_journal_file(store, "dq")
    assert journal_file.is_file(), "the journal rotation file must exist before tampering"
    with journal_file.open("ab") as handle:
        handle.write(b'{"event_type":"data quality","n":1}')  # no trailing LF

    # The committed prefix is still readable (the torn tail is quarantined, not fatal).
    read = journal.read_stream("dq", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == [{"event_type": "data quality", "n": 0}]

    # Backup no longer refuses forever — it reads the committed record.
    backup = ws.value.backup_input.read_room(RoomRole.JOURNAL, for_world=World.LIVE)
    assert is_ok(backup)
    assert backup.value.record_count == 1

    # And a fresh append resumes on the committed prefix.
    assert is_ok(journal.append("dq", writer, {"event_type": "data quality", "n": 2}))
    resumed = journal.read_stream("dq", for_world=World.LIVE)
    assert is_ok(resumed)
    assert resumed.value == [
        {"event_type": "data quality", "n": 0},
        {"event_type": "data quality", "n": 2},
    ]


# --- H4 (money path): an arbitrary-precision int survives the raw archive ----


def test_append_raw_big_int_round_trips_and_refingerprints(store: EvidenceStore) -> None:
    ws = store.for_world(World.LIVE)
    assert is_ok(ws)
    boundary = ws.value.append_store
    rows = [{"n": 2**70}]
    receipt = boundary.append_raw(rows)
    assert is_ok(receipt)  # no OverflowError across the seam
    back = boundary.read_raw(receipt.value.fingerprint.value, for_world=World.LIVE)
    assert is_ok(back)
    assert back.value == rows
    again = fingerprint(back.value)
    assert is_ok(again)
    assert again.value == receipt.value.fingerprint


# --- H6: kind and format_version are inside the fingerprinted identity --------


def test_kind_and_format_version_are_identity_bearing(store: EvidenceStore) -> None:
    ws = store.for_world(World.LIVE)
    assert is_ok(ws)
    room = ws.value.registry_room
    body = {"id": "X", "n": 1}
    a = room.put_record(body, kind="instrument", format_version=1)
    b = room.put_record(body, kind="account", format_version=7)
    assert is_ok(a)
    assert is_ok(b)
    # Same body, different kind/format_version → two DISTINCT records, not idempotent.
    assert a.value.outcome.value == "stored"
    assert b.value.outcome.value == "stored"
    assert a.value.fingerprint != b.value.fingerprint
    # The receipt echoes the actual stored format_version.
    assert a.value.format_version == 1
    assert b.value.format_version == 7
    # Both are genuinely stored and retrievable.
    assert is_ok(room.get_record(a.value.fingerprint.value, for_world=World.LIVE))
    assert is_ok(room.get_record(b.value.fingerprint.value, for_world=World.LIVE))
    # The truly-identical write (same body + kind + fv) is idempotent.
    again = room.put_record(body, kind="instrument", format_version=1)
    assert is_ok(again)
    assert again.value.outcome.value == "idempotent"
    assert again.value.fingerprint == a.value.fingerprint


# --- M3: the append boundary depends on the injected opener, not a hard wire --


def test_journal_uses_the_injected_append_stream_opener(tmp_path: Path) -> None:
    opened: list[Path] = []
    base_opener = jsonl_opener()

    def spy_opener(stream_dir: Path, writer_token: str, /) -> AppendStreamEngine:
        opened.append(stream_dir)
        return base_opener(stream_dir, writer_token)

    journal = JournalStore(World.LIVE, journal_dir=tmp_path / "j", open_stream=spy_opener)
    result = journal.append("dq", _writer(), {"event_type": "data quality", "n": 0})
    assert is_ok(result)
    assert opened  # the injected opener was used, proving the engine is swappable (M3)
    read = journal.read_stream("dq", for_world=World.LIVE)
    assert is_ok(read)
    assert len(read.value) == 1


# --- M5: a never-written stream reads as Ok([]) (documented lazy creation) ----


def test_never_written_streams_read_empty_ok(store: EvidenceStore) -> None:
    ws = store.for_world(World.LIVE)
    assert is_ok(ws)
    journal_read = ws.value.journal.read_stream("never", for_world=World.LIVE)
    assert is_ok(journal_read)
    assert journal_read.value == []
    lineage_read = ws.value.registry_room.read_lineage("never", for_world=World.LIVE)
    assert is_ok(lineage_read)
    assert lineage_read.value == []


# --- L1: a filesystem error while enumerating streams for backup is refused ---


def test_backup_stream_enumeration_oserror_is_storage_failure(
    store: EvidenceStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = store.for_world(World.LIVE)
    assert is_ok(ws)
    assert is_ok(ws.value.journal.append("dq", _writer(), {"event_type": "data quality", "n": 0}))

    def _boom(_self: Path) -> object:
        raise OSError("iterdir denied")

    monkeypatch.setattr(Path, "iterdir", _boom)
    result = ws.value.backup_input.read_room(RoomRole.JOURNAL, for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category.value == "storage failure"


# --- L5: an empty raw artifact is refused, never stored as evidence ----------


def test_append_raw_empty_is_invalid_input(store: EvidenceStore) -> None:
    ws = store.for_world(World.LIVE)
    assert is_ok(ws)
    result = ws.value.append_store.append_raw([])
    assert is_refusal(result)
    assert result.category.value == "invalid input"


# --- M6 (boundary level): closing a journal releases its held stream ----------


def test_journal_close_releases_stream_for_a_new_writer(tmp_path: Path) -> None:
    journal = JournalStore(World.LIVE, journal_dir=tmp_path / "j", open_stream=jsonl_opener())
    first = _writer(machine="node-a", role="data", stream="dq")
    assert is_ok(journal.append("dq", first, {"event_type": "data quality", "n": 0}))
    # A distinct writer is refused while the first holds the stream.
    other = _writer(machine="node-b", role="data", stream="dq")
    assert is_refusal(journal.append("dq", other, {"event_type": "data quality", "n": 1}))
    journal.close()
    assert not (tmp_path / "j" / "dq" / ".writer").exists()
    # After release, the other writer (a fresh JournalStore over the same dir) may hold it.
    reopened = JournalStore(World.LIVE, journal_dir=tmp_path / "j", open_stream=jsonl_opener())
    assert is_ok(reopened.append("dq", other, {"event_type": "data quality", "n": 2}))


def test_reader_and_backup_handles_cannot_write(tmp_path: Path) -> None:
    # A reader/backup handle never acquires, so it cannot append (M6).
    holder = JsonlAppendStream(tmp_path / "s", writer_token="holder")
    assert is_ok(holder.acquire())
    reader = JsonlAppendStream(tmp_path / "s", writer_token="<reader>")
    reader.rebuild_index()  # readers may read
    with pytest.raises(StoreEngineError):
        reader.append(b'{"x":1}')
