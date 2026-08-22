"""Tier-1 tests for the CT-13 journal boundary (AC1, AC3, AC5)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import World, WriterId, is_ok, is_refusal
from qmf.data.store import EvidenceStore, JournalStore, jsonl_opener


def _writer(role: str = "data", stream: str = "dq", boot: str = "boot-1") -> WriterId:
    built = WriterId.try_create("node-a", role, stream, boot)
    assert is_ok(built)
    return built.value


def _journal(store: EvidenceStore) -> JournalStore:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return world.value.journal


def test_append_stores_journal_evidence(store: EvidenceStore) -> None:
    journal = _journal(store)
    result = journal.append("dq", _writer(), {"event_type": "data quality", "n": 0})
    assert is_ok(result)
    receipt = result.value
    assert receipt.engine == "jsonl"
    assert receipt.room_role.value == "journal"
    assert receipt.is_evidence_bearing is True
    assert receipt.sequence == 0


def test_second_distinct_writer_refused(store: EvidenceStore) -> None:
    journal = _journal(store)
    assert is_ok(journal.append("dq", _writer(), {"event_type": "data quality", "n": 0}))
    other = WriterId.try_create("node-b", "data", "dq", "boot-1")
    assert is_ok(other)
    result = journal.append("dq", other.value, {"event_type": "data quality", "n": 1})
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_idempotent_reappend_does_not_duplicate(store: EvidenceStore) -> None:
    journal = _journal(store)
    writer = _writer()
    event = {"event_type": "control action", "note": "flatten"}
    first = journal.append("ca", writer, event)
    second = journal.append("ca", writer, event)
    assert is_ok(first)
    assert is_ok(second)
    assert second.value.outcome.value == "idempotent"
    read = journal.read_stream("ca", for_world=World.LIVE)
    assert is_ok(read)
    assert len(read.value) == 1


def test_sequences_increase_and_read_in_order(store: EvidenceStore) -> None:
    journal = _journal(store)
    writer = _writer()
    for i in range(5):
        assert is_ok(journal.append("dq", writer, {"event_type": "data quality", "n": i}))
    read = journal.read_stream("dq", for_world=World.LIVE)
    assert is_ok(read)
    assert [event["n"] for event in read.value] == [0, 1, 2, 3, 4]


def test_read_unknown_stream_is_empty(store: EvidenceStore) -> None:
    journal = _journal(store)
    read = journal.read_stream("never-written", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == []


def test_cross_world_read_is_policy_rejection(store: EvidenceStore) -> None:
    journal = _journal(store)
    assert is_ok(journal.append("dq", _writer(), {"event_type": "data quality", "n": 0}))
    read = journal.read_stream("dq", for_world=World.REPLAY)
    assert is_refusal(read)
    assert read.category.value == "policy rejection"


def test_invalid_stream_name_is_invalid_input(store: EvidenceStore) -> None:
    journal = _journal(store)
    result = journal.append("../escape", _writer(), {"event_type": "data quality"})
    assert is_refusal(result)
    assert result.category.value == "invalid input"


def test_simulated_append_is_policy_rejection(tmp_path: Path) -> None:
    journal = JournalStore(
        World.SIMULATED, journal_dir=tmp_path / "journal", open_stream=jsonl_opener()
    )
    result = journal.append("dq", _writer(), {"event_type": "data quality"})
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


# --- H1: the write is routed on the EVENT's own declared world ---------------


def test_event_declaring_mismatched_world_is_policy_rejection(store: EvidenceStore) -> None:
    # A LIVE journal store: an event that DECLARES world = simulated or world = replay must
    # not land in the live journal room (DEC-0110, DEC-0117). Both mismatch directions.
    journal = _journal(store)  # LIVE
    simulated = journal.append(
        "dq", _writer(), {"event_type": "data quality", "world": "simulated"}
    )
    assert is_refusal(simulated)
    assert simulated.category.value == "policy rejection"
    assert simulated.context.get("field") == "world"
    replay = journal.append("dq", _writer(), {"event_type": "data quality", "world": "replay"})
    assert is_refusal(replay)
    assert replay.category.value == "policy rejection"
    # Nothing landed: the stream is still empty (a never-written stream reads Ok([])).
    read = journal.read_stream("dq", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == []


def test_event_declaring_matching_world_stores(store: EvidenceStore) -> None:
    # The matching-world happy path: an event declaring the room's own world stores.
    journal = _journal(store)  # LIVE
    event = {"event_type": "data quality", "world": "live", "n": 0}
    result = journal.append("dq", _writer(), event)
    assert is_ok(result)
    read = journal.read_stream("dq", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == [event]


def test_event_declaring_malformed_world_is_invalid_input(store: EvidenceStore) -> None:
    journal = _journal(store)
    bad = journal.append("dq", _writer(), {"event_type": "data quality", "world": "nowhere"})
    assert is_refusal(bad)
    assert bad.category.value == "invalid input"
    assert bad.context.get("field") == "world"
