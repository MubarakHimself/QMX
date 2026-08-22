"""CT-09 producer contract test — registry persistence over the CT-11 store-seam.

The producer-side of the CT-09 contract test the story requires "by both producer and
consumer": these exercise ``qmf.registry.RegistryPersistence`` against the REAL
``qmf.data.store`` seam (the consumer-side lives in
``packages/qmf-data/tests/test_registry_room.py``). They prove the six ACs — persisted
through CT-11 into the per-world registry room with no database server (AC1),
content-addressed on fp1 with idempotent re-write and true-collision refusal (AC2),
cross-world reads and simulated writes refused (AC3), storage failures translated to
typed refusals never raised across the seam (AC4), the staged never-in-place migration
with format stamping (AC5), and the round-trip reference identity (AC6).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import TypeVar, cast

import pytest
from qmf.core import (
    Fingerprint,
    Instant,
    Ok,
    Result,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.data.store import EvidenceStore, RegistryRoom, RoomExport, StoreEngineError, jsonl_opener
from qmf.registry import (
    EdgeType,
    LineageEdge,
    PromotionCard,
    RecordTransform,
    RegistrationRecord,
    RegistryPersistence,
    migrate_registry_format,
    persistence_fingerprint,
)
from qmf.registry.persistence import LoadedRecord

T = TypeVar("T")

# --- fakes: swappable engines that fail or collide (double as AC1 swappability) ---


class _RaisingMetadata:
    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        raise StoreEngineError("insert failed", engine="sqlite", detail={"digest": digest})

    def get(self, digest: str, /) -> bytes | None:
        raise StoreEngineError("read failed", engine="sqlite", detail={"digest": digest})

    def meta(self, digest: str, /) -> Mapping[str, object] | None:  # pragma: no cover - unused
        return None

    def digests(self) -> list[str]:  # pragma: no cover - unused
        return []


class _CollidingMetadata:
    """Returns differing bytes under any digest, forcing a true-collision refusal."""

    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        raise AssertionError("put must never run on the collision path")  # pragma: no cover

    def get(self, digest: str, /) -> bytes | None:
        return b'{"already":"different-bytes-under-this-fp"}'

    def meta(self, digest: str, /) -> Mapping[str, object] | None:  # pragma: no cover - unused
        return None

    def digests(self) -> list[str]:  # pragma: no cover - unused
        return []


# --- builders ---------------------------------------------------------------


def _writer(machine: str = "node-a") -> WriterId:
    built = WriterId.try_create(machine, "authoring", "producer", "boot-1")
    assert is_ok(built)
    return built.value


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    built = Instant.try_create(ns)
    assert is_ok(built)
    return built.value


def _record(
    body: Mapping[str, object],
    *,
    version: int = 1,
    parents: list[Fingerprint] | None = None,
    writer: WriterId | None = None,
    sequence: int = 0,
) -> RegistrationRecord:
    built = RegistrationRecord.try_create(
        "producer",
        version,
        parents or [],
        body,
        writer or _writer(),
        sequence,
        _instant(),
    )
    assert is_ok(built)
    return built.value


def _live(tmp_path: Path) -> RegistryPersistence:
    store = EvidenceStore(tmp_path / "store")
    opened = RegistryPersistence.open(store, World.LIVE)
    assert is_ok(opened)
    return opened.value


def _with_room(tmp_path: Path, room: RegistryRoom) -> RegistryPersistence:
    """A live persistence whose registry room is swapped for a fake-engine one (AC1)."""
    store = EvidenceStore(tmp_path / "store")
    world_store = store.for_world(World.LIVE)
    assert is_ok(world_store)
    return RegistryPersistence(store, replace(world_store.value, registry_room=room))


def _unwrap(result: Result[T], what: str) -> T:
    assert is_ok(result), f"{what}: {result}"
    return result.value


# --- AC1/AC2/AC6: content-addressed persistence and round trip ---------------


def test_persist_record_is_content_addressed_on_fp1(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    record = _record({"id": "sma-20", "period": 20})
    receipt = persistence.persist_record(record)
    assert is_ok(receipt)
    # AC2: the store key is a pure function of the record's identity (never a timestamp).
    expected = persistence_fingerprint(record)
    assert is_ok(expected)
    assert receipt.value.fingerprint == expected.value
    assert receipt.value.fingerprint.value.startswith("fp1:sha256:")
    assert receipt.value.outcome.value == "stored"
    assert receipt.value.room_role.value == "registry room"
    assert receipt.value.engine == "sqlite"
    assert receipt.value.is_evidence_bearing is True


def test_record_round_trips_with_stable_id_preserved(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    parents = [_unwrap(fingerprint({"parent": 1}), "p")]
    assert isinstance(parents[0], Fingerprint)
    record = _record({"id": "sma-20", "period": 20}, parents=[parents[0]])
    receipt = persistence.persist_record(record)
    assert is_ok(receipt)
    loaded = persistence.load_record(receipt.value.fingerprint, for_world=World.LIVE)
    assert is_ok(loaded)
    got: LoadedRecord = loaded.value
    # AC6: the recomputed stable id equals the original — a faithful identity round trip.
    assert got.stable_id == record.stable_id
    assert got.kind == "producer"
    assert got.contract_format_version == 1
    assert dict(got.body) == {"id": "sma-20", "period": 20}
    assert got.at_birth_parent_refs == record.at_birth_parent_refs
    assert got.persisted_fingerprint == receipt.value.fingerprint


def test_distinct_parents_do_not_alias_in_the_store(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    p1 = _unwrap(fingerprint({"parent": 1}), "p1")
    p2 = _unwrap(fingerprint({"parent": 2}), "p2")
    assert isinstance(p1, Fingerprint)
    assert isinstance(p2, Fingerprint)
    body = {"id": "sma-20", "period": 20}
    a = persistence.persist_record(_record(body, parents=[p1]))
    b = persistence.persist_record(_record(body, parents=[p2]))
    assert is_ok(a)
    assert is_ok(b)
    # Same kind/version/body, different at-birth parents -> different store keys.
    assert a.value.fingerprint != b.value.fingerprint


def test_idempotent_re_write_dedups_across_occurrence_facts(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    body = {"id": "sma-20", "period": 20}
    first = persistence.persist_record(_record(body))
    # A twin with a different writer/sequence but identical identity dedups (AC2).
    twin = _record(body, writer=_writer("node-b"), sequence=99)
    again = persistence.persist_record(twin)
    assert is_ok(first)
    assert is_ok(again)
    assert again.value.outcome.value == "idempotent"
    assert again.value.fingerprint == first.value.fingerprint


def test_true_collision_is_refused_and_alarmed(tmp_path: Path) -> None:
    persistence = _with_room(
        tmp_path,
        RegistryRoom(
            World.LIVE,
            record_engine=_CollidingMetadata(),
            lineage_dir=tmp_path / "lineage",
            open_stream=jsonl_opener(),
        ),
    )
    refused = persistence.persist_record(_record({"id": "x"}))
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"
    assert refused.context.get("alarm") is True


def test_persistence_fingerprint_and_persist_reject_non_records(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    assert is_refusal(persistence.persist_record({"not": "a record"}))
    assert is_refusal(persistence_fingerprint({"not": "a record"}))
    assert is_refusal(persistence.persist_edge({"not": "an edge"}, edge_stream="s"))


# --- AC3: per-world rooms, cross-world reads, simulated writes ---------------


def test_open_simulated_is_policy_rejection(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    refused = RegistryPersistence.open(store, World.SIMULATED)
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"


def test_open_non_store_is_invalid_input(tmp_path: Path) -> None:
    refused = RegistryPersistence.open(object(), World.LIVE)
    assert is_refusal(refused)
    assert refused.category.value == "invalid input"


def test_open_replay_binds_the_replay_world(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    opened = RegistryPersistence.open(store, World.REPLAY)
    assert is_ok(opened)
    assert opened.value.world is World.REPLAY
    assert opened.value.root == store.root


def test_cross_world_record_read_is_policy_rejection(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    receipt = persistence.persist_record(_record({"id": "x"}))
    assert is_ok(receipt)
    crossed = persistence.load_record(receipt.value.fingerprint, for_world=World.REPLAY)
    assert is_refusal(crossed)
    assert crossed.category.value == "policy rejection"


def test_missing_record_is_stale_evidence(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    absent = _unwrap(fingerprint({"absent": True}), "absent")
    assert isinstance(absent, Fingerprint)
    got = persistence.load_record(absent, for_world=World.LIVE)
    assert is_refusal(got)
    assert got.category.value == "stale evidence"


def test_malformed_key_is_invalid_input(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    got = persistence.load_record("not-a-fingerprint", for_world=World.LIVE)
    assert is_refusal(got)
    assert got.category.value == "invalid input"


# --- AC1/AC2/AC6: lineage edges over JSONL ----------------------------------


def test_edge_persists_on_its_own_fp1_and_round_trips(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    parent = _record({"id": "sma-20"})
    child = _record({"id": "sma-20-v2"})
    edge = LineageEdge.try_create(EdgeType.SUPERSEDES, child.stable_id, parent.stable_id, _writer())
    assert is_ok(edge)
    receipt = persistence.persist_edge(edge.value, edge_stream="producer-lineage")
    assert is_ok(receipt)
    # AC2: the storage key IS the edge's own fp1 edge fingerprint, exactly.
    assert receipt.value.fingerprint == edge.value.edge_fingerprint
    assert receipt.value.engine == "jsonl"
    read = persistence.read_edges("producer-lineage", for_world=World.LIVE)
    assert is_ok(read)
    assert len(read.value) == 1
    assert read.value[0].edge_fingerprint == edge.value.edge_fingerprint
    assert read.value[0].edge_type is EdgeType.SUPERSEDES
    assert read.value[0].from_ref == child.stable_id
    assert read.value[0].writer == _writer()


def test_edge_re_append_is_idempotent(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    edge = LineageEdge.try_create(
        EdgeType.OCCURRENCE_OF,
        _unwrap(fingerprint({"a": 1}), "a"),
        _unwrap(fingerprint({"b": 2}), "b"),
        _writer(),
    )
    assert is_ok(edge)
    first = persistence.persist_edge(edge.value, edge_stream="s")
    again = persistence.persist_edge(edge.value, edge_stream="s")
    assert is_ok(first)
    assert is_ok(again)
    assert again.value.outcome.value == "idempotent"


def test_read_never_written_stream_is_empty(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    read = persistence.read_edges("never-written", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == ()


def test_cross_world_edge_read_is_policy_rejection(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    edge = LineageEdge.try_create(
        EdgeType.OCCURRENCE_OF,
        _unwrap(fingerprint({"a": 1}), "a"),
        _unwrap(fingerprint({"b": 2}), "b"),
        _writer(),
    )
    assert is_ok(edge)
    assert is_ok(persistence.persist_edge(edge.value, edge_stream="s"))
    crossed = persistence.read_edges("s", for_world=World.REPLAY)
    assert is_refusal(crossed)
    assert crossed.category.value == "policy rejection"


# --- AC4: storage failures translate to typed refusals ----------------------


def test_persist_record_storage_failure_is_typed_refusal(tmp_path: Path) -> None:
    persistence = _with_room(
        tmp_path,
        RegistryRoom(
            World.LIVE,
            record_engine=_RaisingMetadata(),
            lineage_dir=tmp_path / "lineage",
            open_stream=jsonl_opener(),
        ),
    )
    refused = persistence.persist_record(_record({"id": "will-not-land"}))
    assert is_refusal(refused)
    assert refused.category.value == "storage failure"


def test_load_record_storage_failure_is_typed_refusal(tmp_path: Path) -> None:
    persistence = _with_room(
        tmp_path,
        RegistryRoom(
            World.LIVE,
            record_engine=_RaisingMetadata(),
            lineage_dir=tmp_path / "lineage",
            open_stream=jsonl_opener(),
        ),
    )
    got = persistence.load_record("fp1:sha256:" + "0" * 64, for_world=World.LIVE)
    assert is_refusal(got)
    assert got.category.value == "storage failure"


# --- AC5: staged, never-in-place format migration ---------------------------


def _bump_to(version: int) -> RecordTransform:
    def transform(record: RegistrationRecord) -> Result[RegistrationRecord]:
        return RegistrationRecord.try_create(
            record.kind,
            version,
            list(record.at_birth_parent_refs),
            dict(record.body),
            record.writer,
            record.sequence,
            record.created_at,
        )

    return transform


def _seeded_source(tmp_path: Path) -> tuple[RegistryPersistence, list[RegistrationRecord]]:
    source = _live(tmp_path / "src")
    records = [_record({"id": "sma-20"}), _record({"id": "ema-50"})]
    for record in records:
        assert is_ok(source.persist_record(record))
    return source, records


def test_migration_runs_all_stages_and_never_in_place(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")
    report = migrate_registry_format(
        records,
        source=source,
        destination=destination,
        transform=_bump_to(2),
        to_format_version=2,
    )
    assert is_ok(report)
    assert report.value.restore_path == str(source.root)
    assert report.value.backed_up is True
    assert report.value.preflight_count == 2
    assert report.value.dry_run_count == 2
    assert report.value.migrated_count == 2
    assert report.value.verified_count == 2
    assert report.value.to_format_version == 2
    # Every migrated artifact stamps its new format version (AR-25).
    assert all(r.format_version == 2 for r in report.value.receipts)
    # The migrated records are readable from the destination under version 2.
    migrated = _bump_to(2)(records[0])
    assert is_ok(migrated)
    key = persistence_fingerprint(migrated.value)
    assert is_ok(key)
    loaded = destination.load_record(key.value, for_world=World.LIVE)
    assert is_ok(loaded)
    assert loaded.value.contract_format_version == 2


def test_migration_into_same_root_is_refused(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    refused = migrate_registry_format(
        records,
        source=source,
        destination=source,
        transform=_bump_to(2),
        to_format_version=2,
    )
    assert is_refusal(refused)
    assert refused.category.value == "invalid input"
    assert refused.context.get("field") == "destination"


def test_migration_rejects_bad_target_version(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")
    refused = migrate_registry_format(
        records,
        source=source,
        destination=destination,
        transform=_bump_to(2),
        to_format_version=0,
    )
    assert is_refusal(refused)
    assert refused.context.get("field") == "to_format_version"


def test_migration_preflight_fails_when_source_lacks_a_record(tmp_path: Path) -> None:
    source = _live(tmp_path / "src")  # empty source
    destination = _live(tmp_path / "dst")
    refused = migrate_registry_format(
        [_record({"id": "never-seeded"})],
        source=source,
        destination=destination,
        transform=_bump_to(2),
        to_format_version=2,
    )
    assert is_refusal(refused)
    assert refused.category.value == "stale evidence"


def test_migration_aborts_on_transform_refusal(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")

    def failing(record: RegistrationRecord) -> Result[RegistrationRecord]:
        # A blank kind is refused by the record factory -> the transform refuses.
        return RegistrationRecord.try_create(
            "", 2, [], dict(record.body), record.writer, record.sequence, record.created_at
        )

    refused = migrate_registry_format(
        records,
        source=source,
        destination=destination,
        transform=failing,
        to_format_version=2,
    )
    assert is_refusal(refused)


def test_migration_rejects_transform_with_wrong_version(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")
    # transform stamps version 3 but the migration targets 2 -> refused.
    refused = migrate_registry_format(
        records,
        source=source,
        destination=destination,
        transform=_bump_to(3),
        to_format_version=2,
    )
    assert is_refusal(refused)
    assert refused.context.get("field") == "transform"


def test_migration_rejects_non_record_transform_output(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")

    def wrong(record: RegistrationRecord) -> Result[RegistrationRecord]:
        # A transform that returns a non-record is a wiring mistake the migration catches.
        return cast("Result[RegistrationRecord]", Ok(cast("RegistrationRecord", "not a record")))

    refused = migrate_registry_format(
        records,
        source=source,
        destination=destination,
        transform=wrong,
        to_format_version=2,
    )
    assert is_refusal(refused)
    assert refused.context.get("field") == "transform"


# --- AC5: the restorable backup input the migration reads first --------------


def test_backup_export_presents_the_registry_room(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    assert is_ok(persistence.persist_record(_record({"id": "sma-20"})))
    export = persistence.backup_export()
    assert is_ok(export)
    assert export.value.source_room_role.value == "registry room"
    assert export.value.record_count >= 1


@pytest.mark.parametrize("world", [World.LIVE, World.REPLAY])
def test_each_writable_world_gets_its_own_room(tmp_path: Path, world: World) -> None:
    store = EvidenceStore(tmp_path / "store")
    opened = RegistryPersistence.open(store, world)
    assert is_ok(opened)
    receipt = opened.value.persist_record(_record({"id": "sma-20"}))
    assert is_ok(receipt)
    assert opened.value.world is world


# --- H2: the persist boundary refuses a forged reserved kind, accepts the genuine card ---


def _promotion_card() -> PromotionCard:
    card = PromotionCard.sign(
        signer="operator:mubarak",
        plain_words_summary="Promote strategy X to live with a 0.5% risk cap.",
        attested_fp1="fp1:sha256:" + "ab" * 32,
        writer=_writer(),
        sequence=0,
        signed_at=_instant(),
    )
    assert is_ok(card)
    return card.value


def test_persist_record_accepts_the_genuine_card_but_refuses_a_forgery(tmp_path: Path) -> None:
    # H2 (reserved-kind forgery): a reserved CT-06 kind persists only when it was minted
    # through the dedicated signing path. The genuine promotion card's record persists; a
    # byte-identical look-alike whose provenance was stripped is refused at this choke point,
    # never stored as if it were a signed card.
    persistence = _live(tmp_path)
    card = _promotion_card()
    genuine = persistence.persist_record(card.record)
    assert is_ok(genuine)
    forged = replace(card.record, _reserved_provenance=None)  # a look-alike, same stable id
    assert forged.stable_id == card.record.stable_id
    refused = persistence.persist_record(forged)
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"
    assert refused.context["reserved"] is True


# --- H3: a silently altered stored artifact reads back as a storage-failure refusal ------


def test_tampered_record_bytes_read_back_as_storage_failure(tmp_path: Path) -> None:
    # H3 (unverified read-back): the recomputed fingerprint of a persisted record is asserted
    # equal to its storage key, so tampering the stored canonical bytes (keeping the digest
    # key) is caught on read and refused, never served as a silently different record.
    # M2: the store keys a record on its OWN fp1 stable id, so the stored bytes ARE the CT-06
    # fp1 identity content directly (no second wrapping envelope); the body sits one level in.
    persistence = _live(tmp_path)
    record = _record({"max_risk_pct": 1})
    receipt = _unwrap(persistence.persist_record(record), "persist record")
    key = receipt.fingerprint
    # M2: the storage key IS the record's fp1 stable id.
    assert key == record.stable_id

    db = persistence.root / "live" / "registry-room" / "records.sqlite"
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("SELECT canonical FROM records WHERE digest=?", (key.digest,)).fetchone()
        assert row is not None
        identity = json.loads(row[0])
        identity["body"]["max_risk_pct"] = 99  # silent content tamper
        tampered = json.dumps(identity, separators=(",", ":"), sort_keys=True).encode()
        conn.execute("UPDATE records SET canonical=? WHERE digest=?", (tampered, key.digest))
        conn.commit()
    finally:
        conn.close()

    refused = persistence.load_record(key, for_world=World.LIVE)
    assert is_refusal(refused)
    assert refused.category.value == "storage failure"


def test_tampered_edge_line_read_back_as_storage_failure(tmp_path: Path) -> None:
    # H3 (unverified read-back): every persisted edge is anchored by a tamper-evident
    # integrity witness, so a silently altered JSONL line reconstructs to an edge fingerprint
    # with no witness and is refused on read, never served as a valid edge pointing elsewhere.
    persistence = _live(tmp_path)
    a = _unwrap(fingerprint({"a": 1}), "a")
    b = _unwrap(fingerprint({"b": 2}), "b")
    assert isinstance(a, Fingerprint)
    assert isinstance(b, Fingerprint)
    edge = _unwrap(LineageEdge.try_create(EdgeType.SUPERSEDES, b, a, _writer()), "edge")
    assert is_ok(persistence.persist_edge(edge, edge_stream="lineage"))
    # A clean read still round-trips.
    assert is_ok(persistence.read_edges("lineage", for_world=World.LIVE))

    evil = "fp1:sha256:" + "ee" * 32
    seg = list(
        (persistence.root / "live" / "registry-room" / "lineage" / "lineage").glob("*.jsonl")
    )
    assert seg
    data = seg[0].read_bytes()
    seg[0].write_bytes(data.replace(a.value.encode(), evil.encode()))

    refused = persistence.read_edges("lineage", for_world=World.LIVE)
    assert is_refusal(refused)
    assert refused.category.value == "storage failure"


# --- M2: the storage key IS the record's own fp1 stable id -------------------


def test_persistence_key_is_the_records_own_stable_id(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    record = _record({"id": "sma-20", "period": 20})
    # persistence_fingerprint IS the record's stable id (no second wrapping fingerprint).
    key = _unwrap(persistence_fingerprint(record), "key")
    assert key == record.stable_id
    receipt = _unwrap(persistence.persist_record(record), "persist")
    assert receipt.fingerprint == record.stable_id
    # A read keyed on the record's stable id directly (what CT-09 AC2 says the key is) works.
    loaded = _unwrap(persistence.load_record(record.stable_id, for_world=World.LIVE), "load")
    assert loaded.stable_id == record.stable_id
    assert loaded.persisted_fingerprint == record.stable_id


# --- M5: display-only occurrence facts round-trip ---------------------------


def test_occurrence_facts_round_trip_writer_and_sequence(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    writer = _writer("node-x")
    record = _record({"id": "occ"}, writer=writer, sequence=42)
    receipt = _unwrap(persistence.persist_record(record), "persist")
    loaded = _unwrap(persistence.load_record(receipt.fingerprint, for_world=World.LIVE), "load")
    # Who wrote the registration and in what order survives the round trip (M5).
    assert loaded.writer == writer
    assert loaded.sequence == 42
    assert loaded.created_at == record.created_at


def test_occurrence_sidecar_keeps_the_first_writers_facts_on_dedup(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    first_writer = _writer("node-a")
    record = _record({"id": "occ"}, writer=first_writer, sequence=1)
    assert is_ok(persistence.persist_record(record))
    # A twin with the SAME identity but a different writer/sequence dedups; the occurrence
    # sidecar is first-write-wins, so the first writer's facts are kept (no collision).
    twin = _record({"id": "occ"}, writer=_writer("node-b"), sequence=99)
    again = _unwrap(persistence.persist_record(twin), "twin")
    assert again.outcome.value == "idempotent"
    loaded = _unwrap(persistence.load_record(again.fingerprint, for_world=World.LIVE), "load")
    assert loaded.writer == first_writer
    assert loaded.sequence == 1


# --- M1: supersedes is pinned linear on the durable path --------------------


def _sup(from_tag: str, to_tag: str) -> LineageEdge:
    a = _unwrap(fingerprint({"rec": from_tag}), from_tag)
    b = _unwrap(fingerprint({"rec": to_tag}), to_tag)
    return _unwrap(LineageEdge.try_create(EdgeType.SUPERSEDES, a, b, _writer()), "supersedes edge")


def test_durable_supersedes_refuses_a_second_superseder(tmp_path: Path) -> None:
    # M1: two records superseding the same record fork "current"; the durable path refuses
    # the second, so CT-07's one-resolvable-head invariant holds for persisted evidence.
    persistence = _live(tmp_path)
    assert is_ok(persistence.persist_edge(_sup("b", "a"), edge_stream="lineage"))
    forked = persistence.persist_edge(_sup("c", "a"), edge_stream="lineage")
    assert is_refusal(forked)
    assert forked.category.value == "policy rejection"
    assert forked.context["field"] == "supersedes"


def test_durable_supersedes_refuses_a_second_outgoing_edge(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    assert is_ok(persistence.persist_edge(_sup("a", "b"), edge_stream="out"))
    forked = persistence.persist_edge(_sup("a", "c"), edge_stream="out")
    assert is_refusal(forked)
    assert forked.context["field"] == "supersedes"


def test_durable_supersedes_refuses_self_loop_and_cycle(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    x = _unwrap(fingerprint({"rec": "x"}), "x")
    loop = _unwrap(LineageEdge.try_create(EdgeType.SUPERSEDES, x, x, _writer()), "self-loop")
    refused_loop = persistence.persist_edge(loop, edge_stream="loop")
    assert is_refusal(refused_loop)
    assert refused_loop.context["field"] == "supersedes"
    # A -> B, B -> C, then C -> A would close a cycle, leaving no resolvable head.
    assert is_ok(persistence.persist_edge(_sup("a", "b"), edge_stream="cyc"))
    assert is_ok(persistence.persist_edge(_sup("b", "c"), edge_stream="cyc"))
    cycle = persistence.persist_edge(_sup("c", "a"), edge_stream="cyc")
    assert is_refusal(cycle)
    assert cycle.context["field"] == "supersedes"


def test_durable_supersedes_idempotent_reappend_is_not_a_fork(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    edge = _sup("b", "a")
    assert is_ok(persistence.persist_edge(edge, edge_stream="s"))
    again = persistence.persist_edge(edge, edge_stream="s")
    assert is_ok(again)
    assert again.value.outcome.value == "idempotent"


def test_durable_supersedes_refuses_a_cross_stream_fork(tmp_path: Path) -> None:
    # Residual 7: CT-07's one-resolvable-head invariant is ROOM-WIDE, not per-stream. A
    # second outgoing supersedes from the same subject on a DIFFERENT edge stream still forks
    # "current", so the durable guard scans every stream in the room and refuses it — a fork
    # can never hide by landing on a second stream.
    persistence = _live(tmp_path)
    assert is_ok(persistence.persist_edge(_sup("a", "b"), edge_stream="stream-1"))
    forked = persistence.persist_edge(_sup("a", "c"), edge_stream="stream-2")
    assert is_refusal(forked)
    assert forked.category.value == "policy rejection"
    assert forked.context["field"] == "supersedes"
    # A second superseder of the same record on yet another stream is likewise refused.
    incoming_fork = persistence.persist_edge(_sup("d", "b"), edge_stream="stream-3")
    assert is_refusal(incoming_fork)
    assert incoming_fork.context["field"] == "supersedes"
    # A byte-identical re-append of the original edge stays idempotent-Ok: the same-fingerprint
    # edge is excluded from the fork test, so room-wide linearity never trips it.
    again = persistence.persist_edge(_sup("a", "b"), edge_stream="stream-1")
    assert is_ok(again)
    assert again.value.outcome.value == "idempotent"


# --- L3: the persisted edge line IS canonical_line() (single serializer) -----


def test_persisted_edge_line_equals_canonical_line(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    edge = _sup("newer", "older")
    assert is_ok(persistence.persist_edge(edge, edge_stream="lineage"))
    seg = list(
        (persistence.root / "live" / "registry-room" / "lineage" / "lineage").glob("*.jsonl")
    )
    assert seg
    assert seg[0].read_bytes() == _unwrap(edge.canonical_line(), "canonical line")


# --- L5: a read-back body is deep-frozen exactly like the write side ---------


def test_loaded_body_is_deep_frozen(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    record = _record({"id": "x", "cfg": {"nested": [1, 2]}})
    receipt = _unwrap(persistence.persist_record(record), "persist")
    loaded = _unwrap(persistence.load_record(receipt.fingerprint, for_world=World.LIVE), "load")
    with pytest.raises(TypeError):
        cast("dict[str, object]", loaded.body)["id"] = "tampered"
    nested = cast("dict[str, object]", loaded.body["cfg"])
    with pytest.raises(TypeError):
        nested["nested"] = "tampered"


# --- M6: close() releases the one-writer lock for a handoff ------------------


def _other_writer() -> WriterId:
    built = WriterId.try_create("node-a", "reviewer", "producer", "boot-1")
    assert is_ok(built)
    return built.value


def test_close_releases_the_writer_lock_for_a_handoff(tmp_path: Path) -> None:
    persistence = _live(tmp_path)
    a = _unwrap(fingerprint({"a": 1}), "a")
    b = _unwrap(fingerprint({"b": 2}), "b")
    e1 = _unwrap(LineageEdge.try_create(EdgeType.OCCURRENCE_OF, a, b, _writer()), "e1")
    assert is_ok(persistence.persist_edge(e1, edge_stream="s"))
    # A second writer is refused while the first holds the stream's on-disk lock.
    e2 = _unwrap(LineageEdge.try_create(EdgeType.OCCURRENCE_OF, b, a, _other_writer()), "e2")
    blocked = persistence.persist_edge(e2, edge_stream="s")
    assert is_refusal(blocked)
    assert blocked.category.value == "policy rejection"
    # After close() the lock is released, so the handoff to the second writer succeeds.
    persistence.close()
    assert is_ok(persistence.persist_edge(e2, edge_stream="s"))


def test_context_manager_releases_the_lock_on_exit(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "store")
    persistence = _unwrap(RegistryPersistence.open(store, World.LIVE), "open")
    a = _unwrap(fingerprint({"a": 1}), "a")
    b = _unwrap(fingerprint({"b": 2}), "b")
    with persistence as held:
        e1 = _unwrap(LineageEdge.try_create(EdgeType.OCCURRENCE_OF, a, b, _writer()), "e1")
        assert is_ok(held.persist_edge(e1, edge_stream="s"))
    # The block exit released the lock, so a different writer can now take the stream.
    e2 = _unwrap(LineageEdge.try_create(EdgeType.OCCURRENCE_OF, b, a, _other_writer()), "e2")
    assert is_ok(persistence.persist_edge(e2, edge_stream="s"))


# --- M4: migration guards, real backup artifact, records-only ---------------


def test_migration_across_worlds_is_refused(tmp_path: Path) -> None:
    source = _live(tmp_path / "src")
    dest_store = EvidenceStore(tmp_path / "dst")
    destination = _unwrap(RegistryPersistence.open(dest_store, World.REPLAY), "replay destination")
    record = _record({"id": "x"})
    assert is_ok(source.persist_record(record))
    refused = migrate_registry_format(
        [record],
        source=source,
        destination=destination,
        transform=_bump_to(2),
        to_format_version=2,
    )
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"
    assert refused.context.get("field") == "destination"


def test_migration_writes_a_real_backup_artifact_and_is_records_only(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")
    report = _unwrap(
        migrate_registry_format(
            records,
            source=source,
            destination=destination,
            transform=_bump_to(2),
            to_format_version=2,
        ),
        "migrate",
    )
    assert report.backed_up is True
    assert report.records_only is True
    backup = Path(report.backup_path)
    assert backup.is_file()  # backed_up reflects a REAL written artifact, not a constant
    payload = json.loads(backup.read_text(encoding="utf-8"))
    assert payload["world"] == "live"
    assert len(payload["records"]) >= 2


def test_migration_uses_a_supplied_backup_sink(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")
    seen: list[RoomExport] = []

    def sink(export: RoomExport) -> Result[str]:
        seen.append(export)
        return Ok("backup://written-elsewhere")

    report = _unwrap(
        migrate_registry_format(
            records,
            source=source,
            destination=destination,
            transform=_bump_to(2),
            to_format_version=2,
            backup_sink=sink,
        ),
        "migrate with sink",
    )
    assert report.backed_up is True
    assert report.backup_path == "backup://written-elsewhere"
    assert len(seen) == 1
    assert seen[0].record_count >= 2


def test_migration_aborts_when_the_backup_sink_refuses(tmp_path: Path) -> None:
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")

    def sink(_export: RoomExport) -> Result[str]:
        return unpersistable("the backup destination is unavailable")

    refused = migrate_registry_format(
        records,
        source=source,
        destination=destination,
        transform=_bump_to(2),
        to_format_version=2,
        backup_sink=sink,
    )
    assert is_refusal(refused)
    assert refused.category.value == "storage failure"
    # Nothing was migrated: the destination never received the record.
    key = _unwrap(persistence_fingerprint(_unwrap(_bump_to(2)(records[0]), "bumped")), "key")
    assert is_refusal(destination.load_record(key, for_world=World.LIVE))


# --- symlink-safe backup write (the Skylos symlink-following-write finding) --------


def test_migration_aborts_when_the_backup_target_already_exists(tmp_path: Path) -> None:
    # The default backup is created with an exclusive, no-follow open (O_CREAT | O_EXCL):
    # a pre-existing artifact at the target is refused rather than clobbered, so a
    # symlink swapped in for that path can never be followed and overwritten.
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")
    backup_dir = destination.root / "pre-migration-backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / "live-registry-room.backup.json"
    target.write_text("pre-existing", encoding="utf-8")
    refused = migrate_registry_format(
        records,
        source=source,
        destination=destination,
        transform=_bump_to(2),
        to_format_version=2,
    )
    assert is_refusal(refused)
    assert refused.category.value == "storage failure"
    # The pre-existing artifact was not clobbered, and nothing migrated to the destination.
    assert target.read_text(encoding="utf-8") == "pre-existing"
    key = _unwrap(persistence_fingerprint(_unwrap(_bump_to(2)(records[0]), "bumped")), "key")
    assert is_refusal(destination.load_record(key, for_world=World.LIVE))


def test_migration_refuses_a_symlinked_backup_target(tmp_path: Path) -> None:
    # An attacker who plants a symlink at the default backup path must not get the backup
    # write redirected onto the link's target; the migration refuses and aborts.
    source, records = _seeded_source(tmp_path)
    destination = _live(tmp_path / "dst")
    backup_dir = destination.root / "pre-migration-backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("do not clobber", encoding="utf-8")
    try:
        (backup_dir / "live-registry-room.backup.json").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this platform")
    refused = migrate_registry_format(
        records,
        source=source,
        destination=destination,
        transform=_bump_to(2),
        to_format_version=2,
    )
    assert is_refusal(refused)
    assert refused.category.value == "storage failure"
    # The symlink's target was not clobbered, and nothing migrated to the destination.
    assert outside.read_text(encoding="utf-8") == "do not clobber"
    key = _unwrap(persistence_fingerprint(_unwrap(_bump_to(2)(records[0]), "bumped")), "key")
    assert is_refusal(destination.load_record(key, for_world=World.LIVE))
