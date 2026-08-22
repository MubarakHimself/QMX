"""Tier-1 tests for the CT-26 store-to-backup input boundary (AC1, AC5)."""

from __future__ import annotations

from qmf.core import World, WriterId, canonical_bytes, is_ok, is_refusal
from qmf.data.store import EvidenceStore, RoomRole, WorldStore


def _world(store: EvidenceStore) -> WorldStore:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return world.value


def _writer() -> WriterId:
    built = WriterId.try_create("node-a", "registry", "lineage", "boot-1")
    assert is_ok(built)
    return built.value


def _populate(w: WorldStore) -> None:
    assert is_ok(w.append_store.append_raw([{"t": 1, "px": 100}]))
    jw = WriterId.try_create("node-a", "data", "dq", "boot-1")
    assert is_ok(jw)
    assert is_ok(w.journal.append("dq", jw.value, {"event_type": "data quality", "n": 0}))
    assert is_ok(
        w.registry_room.put_record({"kind": "producer"}, kind="producer", format_version=1)
    )
    assert is_ok(w.registry_room.append_lineage_edge("lineage", _writer(), {"edge": "a"}))


def test_backup_reads_raw_archive_verbatim(store: EvidenceStore) -> None:
    w = _world(store)
    _populate(w)
    result = w.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE)
    assert is_ok(result)
    export = result.value
    assert export.record_count == 1
    assert export.source_room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE
    record = export.records[0]
    assert record.fingerprint.startswith("fp1:sha256:")
    expected = canonical_bytes([{"t": 1, "px": 100}])
    assert is_ok(expected)
    assert record.canonical == expected.value


def test_backup_reads_journal_lines(store: EvidenceStore) -> None:
    w = _world(store)
    _populate(w)
    result = w.backup_input.read_room("journal", for_world=World.LIVE)
    assert is_ok(result)
    assert result.value.record_count == 1


def test_backup_reads_registry_records_and_edges(store: EvidenceStore) -> None:
    w = _world(store)
    _populate(w)
    result = w.backup_input.read_room(RoomRole.REGISTRY_ROOM, for_world=World.LIVE)
    assert is_ok(result)
    # one SQLite record + one JSONL lineage edge
    assert result.value.record_count == 2


def test_backup_unpopulated_room_is_empty(store: EvidenceStore) -> None:
    w = _world(store)
    result = w.backup_input.read_room(RoomRole.PROCESSED, for_world=World.LIVE)
    assert is_ok(result)
    assert result.value.record_count == 0


def test_backup_cross_world_read_is_policy_rejection(store: EvidenceStore) -> None:
    w = _world(store)
    _populate(w)
    result = w.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.REPLAY)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_backup_invalid_role_is_invalid_input(store: EvidenceStore) -> None:
    w = _world(store)
    result = w.backup_input.read_room("not a room", for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category.value == "invalid input"
