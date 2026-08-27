"""L4 — integration against the real qmf-data store seam (restart, tamper, migration).

E2-L4-01  (P0) persist, RESTART the process (reopen), read back — semantic equality
E2-L4-02  (P0) READ-BACK INTEGRITY — tampered record bytes never read back valid
E2-L4-03  (P0) tampered / canonical-preserving-swapped edge line is tamper-evident
E2-L4-04  a store-library failure is a `storage failure` refusal, never raised (FM-8)
E2-L4-05  world isolation — cross-world read is a policy rejection; simulated write refused
E2-L4-06  a dropped edge index costs only a rebuild — identical edge view, no evidence lost
E2-L4-07  (P0) idempotent persistence + differing-bytes same-fp1 refused at the store boundary
E2-L4-08  migration — preflight->backup->dry-run->migrate->verify, never in-place
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from qmf.core import Fingerprint, Result, World, fingerprint, is_ok, is_refusal
from qmf.data.store import EvidenceStore, RegistryRoom, StoreEngineError, jsonl_opener
from qmf.registry import (
    EdgeType,
    LineageEdge,
    RegistrationRecord,
    RegistryPersistence,
    migrate_registry_format,
    persistence_fingerprint,
)

import helpers as h


# --- fake engines (swappable; double as AC1 swappability proof) ----------------


class _RaisingMetadata:
    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        raise StoreEngineError("insert failed", engine="sqlite", detail={"digest": digest})

    def get(self, digest: str, /) -> bytes | None:
        raise StoreEngineError("read failed", engine="sqlite", detail={"digest": digest})

    def meta(self, digest: str, /) -> Mapping[str, object] | None:
        return None

    def digests(self) -> list[str]:
        return []


class _CollidingMetadata:
    """Returns differing bytes under any digest, forcing a true-collision refusal."""

    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        raise AssertionError("put must never run on the collision path")

    def get(self, digest: str, /) -> bytes | None:
        return b'{"already":"different-bytes-under-this-fp"}'

    def meta(self, digest: str, /) -> Mapping[str, object] | None:
        return None

    def digests(self) -> list[str]:
        return []


def _with_room(root: Path, room: RegistryRoom) -> RegistryPersistence:
    store = EvidenceStore(root / "store")
    world_store = h.unwrap(store.for_world(World.LIVE), "world store")
    return RegistryPersistence(store, replace(world_store, registry_room=room))


# --- E2-L4-01 (P0) : survive a process restart --------------------------------


def test_e2_l4_01_record_survives_a_process_restart(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    rec = h.record({"id": "sma-20", "period": 20}, parents=[h.fp("p1")])
    # First "process": open, persist, close (release locks).
    p1 = h.unwrap(RegistryPersistence.open(EvidenceStore(store_root), World.LIVE), "open-1")
    receipt = h.unwrap(p1.persist_record(rec), "persist")
    p1.close()
    # Second "process": a fresh store handle over the same root reads the record back.
    p2 = h.unwrap(RegistryPersistence.open(EvidenceStore(store_root), World.LIVE), "open-2")
    loaded = h.unwrap(p2.load_record(receipt.fingerprint, for_world=World.LIVE), "load")
    assert loaded.stable_id == rec.stable_id
    assert dict(loaded.body) == {"id": "sma-20", "period": 20}


# --- E2-L4-02 (P0) : read-back integrity for records --------------------------


def test_e2_l4_02_tampered_record_bytes_do_not_read_back_valid(tmp_path: Path) -> None:
    p = h.live_persistence(tmp_path)
    rec = h.record({"max_risk_pct": 1})
    receipt = h.unwrap(p.persist_record(rec), "persist")
    key = receipt.fingerprint
    assert key == rec.stable_id  # M2: the storage key IS the record's fp1 stable id

    db = p.root / "live" / "registry-room" / "records.sqlite"
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("SELECT canonical FROM records WHERE digest=?", (key.digest,)).fetchone()
        assert row is not None
        identity = json.loads(row[0])
        identity["body"]["max_risk_pct"] = 99  # silent content tamper, key unchanged
        tampered = json.dumps(identity, separators=(",", ":"), sort_keys=True).encode()
        conn.execute("UPDATE records SET canonical=? WHERE digest=?", (tampered, key.digest))
        conn.commit()
    finally:
        conn.close()

    refused = p.load_record(key, for_world=World.LIVE)
    assert is_refusal(refused)  # recomputed fp1 != stored key => never served
    assert refused.category.value == "storage failure"


# --- E2-L4-03 (P0) : read-back integrity for edges (tamper + valid-line swap) --


def _jsonl_segments(p: RegistryPersistence, stream: str) -> list[Path]:
    return list((p.root / "live" / "registry-room" / "lineage" / stream).glob("*.jsonl"))


def test_e2_l4_03_tampered_edge_endpoint_is_tamper_evident(tmp_path: Path) -> None:
    p = h.live_persistence(tmp_path)
    a, b = h.fp("A"), h.fp("B")
    edge = h.unwrap(LineageEdge.try_create(EdgeType.OCCURRENCE_OF, b, a, h.writer()), "edge")
    assert is_ok(p.persist_edge(edge, edge_stream="lineage"))
    assert is_ok(p.read_edges("lineage", for_world=World.LIVE))  # clean read round-trips
    seg = _jsonl_segments(p, "lineage")
    assert seg
    data = seg[0].read_bytes()
    # A canonical-preserving byte edit of an endpoint re-derives a self-consistent edge
    # fingerprint whose integrity witness is absent => refused, never served.
    seg[0].write_bytes(data.replace(a.value.encode(), ("fp1:sha256:" + "ee" * 32).encode()))
    refused = p.read_edges("lineage", for_world=World.LIVE)
    assert is_refusal(refused)
    assert refused.category.value == "storage failure"


def test_e2_l4_03_swap_to_another_valid_edge_line_is_tamper_evident(tmp_path: Path) -> None:
    p = h.live_persistence(tmp_path)
    stored_edge = h.unwrap(
        LineageEdge.try_create(EdgeType.OCCURRENCE_OF, h.fp("A"), h.fp("B"), h.writer()), "stored"
    )
    assert is_ok(p.persist_edge(stored_edge, edge_stream="lineage"))
    # A DIFFERENT, fully valid CT-07 edge — never persisted, so it has no integrity witness.
    other_edge = h.unwrap(
        LineageEdge.try_create(EdgeType.OCCURRENCE_OF, h.fp("C"), h.fp("D"), h.writer()), "other"
    )
    swap_line = h.unwrap(other_edge.canonical_line(), "swap line")
    seg = _jsonl_segments(p, "lineage")
    assert seg
    seg[0].write_bytes(swap_line)  # swap the stored line for another valid edge's line
    refused = p.read_edges("lineage", for_world=World.LIVE)
    assert is_refusal(refused)  # the witness makes the swap tamper-evident
    assert refused.category.value == "storage failure"


# --- E2-L4-04 : store-library failure is a typed refusal (FM-8) ----------------


def test_e2_l4_04_store_failure_translates_to_typed_refusal(tmp_path: Path) -> None:
    p = _with_room(
        tmp_path,
        RegistryRoom(World.LIVE, record_engine=_RaisingMetadata(),
                     lineage_dir=tmp_path / "lineage", open_stream=jsonl_opener()),
    )
    refused = p.persist_record(h.record({"id": "will-not-land"}))
    assert is_refusal(refused)
    assert refused.category.value == "storage failure"  # never raised across the seam


# --- E2-L4-05 : world isolation at storage (FM-7) -----------------------------


def test_e2_l4_05_cross_world_read_is_policy_rejection(tmp_path: Path) -> None:
    p = h.live_persistence(tmp_path)
    receipt = h.unwrap(p.persist_record(h.record({"id": "x"})), "persist")
    crossed = p.load_record(receipt.fingerprint, for_world=World.REPLAY)
    assert is_refusal(crossed)
    assert crossed.category.value == "policy rejection"


def test_e2_l4_05_simulated_world_never_opens(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    refused = RegistryPersistence.open(store, World.SIMULATED)
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"  # non-live world never writes live ns


# --- E2-L4-06 : a dropped index costs only a rebuild --------------------------


def test_e2_l4_06_dropped_index_reproduced_by_rebuild(tmp_path: Path) -> None:
    # In-memory edge view: dropping and rebuilding the derived indexes reproduces the
    # identical edge view (evidence is the source of truth; indexes are rebuildable).
    from qmf.registry import EdgeLog

    log = EdgeLog(h.writer())
    a, b, c = h.fp("A"), h.fp("B"), h.fp("C")
    h.unwrap(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=b, to_ref=a), "b>a")
    h.unwrap(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=c, to_ref=b), "c>b")
    head_before = h.unwrap(log.current_head(a), "head")
    edges_before = log.edges()
    log.rebuild_indexes()
    assert log.edges() == edges_before
    assert h.unwrap(log.current_head(a), "head-after") == head_before
    # Durable: reading a persisted stream twice reconstructs the identical view from lines.
    p = h.live_persistence(tmp_path)
    edge = h.unwrap(LineageEdge.try_create(EdgeType.OCCURRENCE_OF, a, b, h.writer()), "edge")
    assert is_ok(p.persist_edge(edge, edge_stream="s"))
    r1 = h.unwrap(p.read_edges("s", for_world=World.LIVE), "r1")
    r2 = h.unwrap(p.read_edges("s", for_world=World.LIVE), "r2")
    assert [e.edge_fingerprint for e in r1] == [e.edge_fingerprint for e in r2]


# --- E2-L4-07 (P0) : idempotent persistence + true collision at the store ------


def test_e2_l4_07_idempotent_persist_yields_one_record(tmp_path: Path) -> None:
    p = h.live_persistence(tmp_path)
    body = {"id": "sma-20"}
    first = h.unwrap(p.persist_record(h.record(body)), "first")
    twin = h.record(body, writer_id=h.writer("node-b"), sequence=99)  # same identity
    again = h.unwrap(p.persist_record(twin), "again")
    assert again.outcome.value == "idempotent"
    assert again.fingerprint == first.fingerprint


def test_e2_l4_07_differing_bytes_same_fp1_refused_and_alarmed(tmp_path: Path) -> None:
    p = _with_room(
        tmp_path,
        RegistryRoom(World.LIVE, record_engine=_CollidingMetadata(),
                     lineage_dir=tmp_path / "lineage", open_stream=jsonl_opener()),
    )
    refused = p.persist_record(h.record({"id": "x"}))
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"
    assert refused.context.get("alarm") is True  # refused and alarmed, never overwritten


# --- E2-L4-08 : staged, never-in-place migration ------------------------------


def _bump_to(version: int):
    def transform(record: RegistrationRecord) -> Result[RegistrationRecord]:
        return RegistrationRecord.try_create(
            record.kind, version, list(record.at_birth_parent_refs), dict(record.body),
            record.writer, record.sequence, record.created_at,
        )
    return transform


def test_e2_l4_08_migration_is_staged_and_never_in_place(tmp_path: Path) -> None:
    source = h.live_persistence(tmp_path / "src")
    dest = h.live_persistence(tmp_path / "dst")
    records = [h.record({"id": "sma-20"}), h.record({"id": "ema-50"})]
    for r in records:
        assert is_ok(source.persist_record(r))
    report = h.unwrap(
        migrate_registry_format(records, source=source, destination=dest,
                                transform=_bump_to(2), to_format_version=2),
        "migrate",
    )
    assert report.backed_up is True
    assert Path(report.backup_path).is_file()  # a REAL backup artifact, not a constant
    assert report.records_only is True
    assert report.verified_count == 2
    # Old evidence stays readable at the source (never mutated in place).
    key0 = h.unwrap(persistence_fingerprint(records[0]), "key0")
    assert is_ok(source.load_record(key0, for_world=World.LIVE))
    # Migrated evidence reads at the destination under the new stamped version.
    bumped = h.unwrap(_bump_to(2)(records[0]), "bumped")
    keyd = h.unwrap(persistence_fingerprint(bumped), "keyd")
    loaded = h.unwrap(dest.load_record(keyd, for_world=World.LIVE), "load dst")
    assert loaded.contract_format_version == 2
