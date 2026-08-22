"""Tier-1 tests for the CT-09 registry-room boundary (AC1, AC2, AC5)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from qmf.core import World, WriterId, canonical_bytes, fingerprint, is_ok, is_refusal
from qmf.data.store import EvidenceStore, RegistryRoom, jsonl_opener
from qmf.data.store.engines.sqlite_meta import SqliteMetadataEngine

_RECORD = {"kind": "producer", "id": "sma-20"}


def _envelope(record: Mapping[str, object], *, kind: str, format_version: int) -> dict[str, object]:
    """The full stored record (H6): kind + format_version + body, fingerprinted whole."""
    return {"kind": kind, "format_version": format_version, "body": dict(record)}


def _writer() -> WriterId:
    built = WriterId.try_create("node-a", "registry", "lineage", "boot-1")
    assert is_ok(built)
    return built.value


def _registry(store: EvidenceStore) -> RegistryRoom:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return world.value.registry_room


def test_put_record_stores_via_sqlite(store: EvidenceStore) -> None:
    room = _registry(store)
    result = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_ok(result)
    receipt = result.value
    assert receipt.engine == "sqlite"
    assert receipt.room_role.value == "registry room"
    assert receipt.is_evidence_bearing is True


def test_get_record_returns_canonical_bytes(store: EvidenceStore) -> None:
    room = _registry(store)
    receipt = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_ok(receipt)
    got = room.get_record(receipt.value.fingerprint.value, for_world=World.LIVE)
    assert is_ok(got)
    # The stored artifact is the FULL record (kind + format_version + body), H6.
    expected = canonical_bytes(_envelope(_RECORD, kind="producer", format_version=1))
    assert is_ok(expected)
    assert got.value == expected.value


def test_put_record_idempotent(store: EvidenceStore) -> None:
    room = _registry(store)
    first = room.put_record(_RECORD, kind="producer", format_version=1)
    second = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_ok(first)
    assert is_ok(second)
    assert second.value.outcome.value == "idempotent"


def test_get_missing_record_is_stale_evidence(store: EvidenceStore) -> None:
    room = _registry(store)
    fp = fingerprint({"absent": True})
    assert is_ok(fp)
    # M5: a well-formed fingerprint that names nothing is a not-found (stale evidence)
    # refusal, never an invalid-input caller error.
    result = room.get_record(fp.value.value, for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category.value == "stale evidence"


def test_put_record_invalid_kind_and_version(store: EvidenceStore) -> None:
    room = _registry(store)
    bad_kind = room.put_record(_RECORD, kind="", format_version=1)
    assert is_refusal(bad_kind)
    assert bad_kind.context.get("field") == "kind"
    bad_version = room.put_record(_RECORD, kind="producer", format_version=0)
    assert is_refusal(bad_version)
    assert bad_version.context.get("field") == "format_version"


def test_lineage_edge_appends_via_jsonl(store: EvidenceStore) -> None:
    room = _registry(store)
    edge = {"edge": "derived_from", "to": "x"}
    result = room.append_lineage_edge("lineage", _writer(), edge)
    assert is_ok(result)
    assert result.value.engine == "jsonl"
    read = room.read_lineage("lineage", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == [edge]


def test_cross_world_get_is_policy_rejection(store: EvidenceStore) -> None:
    room = _registry(store)
    receipt = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_ok(receipt)
    result = room.get_record(receipt.value.fingerprint.value, for_world=World.REPLAY)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_cross_world_read_lineage_is_policy_rejection(store: EvidenceStore) -> None:
    room = _registry(store)
    assert is_ok(room.append_lineage_edge("lineage", _writer(), {"edge": "a"}))
    result = room.read_lineage("lineage", for_world=World.REPLAY)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_simulated_writes_are_policy_rejections(tmp_path: Path) -> None:
    room = RegistryRoom(
        World.SIMULATED,
        record_engine=SqliteMetadataEngine(tmp_path / "records.sqlite"),
        lineage_dir=tmp_path / "lineage",
        open_stream=jsonl_opener(),
    )
    rec = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_refusal(rec)
    assert rec.category.value == "policy rejection"
    edge = room.append_lineage_edge("lineage", _writer(), {"edge": "a"})
    assert is_refusal(edge)
    assert edge.category.value == "policy rejection"
