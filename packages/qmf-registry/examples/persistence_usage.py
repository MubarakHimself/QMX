"""Reference usage — CT-09 registry persistence through the qmf-data store-seam
(COMP-QMF-REGISTRY).

Executable::

    python packages/qmf-registry/examples/persistence_usage.py

Shows the six things CT-09 pins down, all against the REAL CT-11 store-seam
(``qmf.data.store.EvidenceStore``) over the single ratified edge ``qmf-registry →
qmf-data`` — no database server, stdlib-typed at the boundary:

1. A CT-06 record persists into the per-world registry room, content-addressed on its
   fp1 stable id (never a timestamp or minted id), and reads back with its identity —
   the recomputed stable id equals the original's.
2. A byte-identical re-write is accepted silently (idempotent); identical work from two
   sandboxes deduplicates on identity, with occurrence facts excluded.
3. A CT-07 lineage edge persists into a one-writer JSONL stream keyed on its own fp1 edge
   fingerprint, and reads back as the same typed edge.
4. A read that crosses worlds is a `policy rejection`, and a `world = simulated` room is
   a `policy rejection` — a non-live world never writes the live evidence namespace.
5. An underlying store failure is a `storage failure` typed refusal translated at the
   qmf-data boundary, never an exception across the package seam.
6. A schema/format change runs preflight → backup-first → dry-run → migrate → verify to a
   distinct destination store — never mutating the only copy in place — and every
   migrated artifact stamps its new contract format version.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Instant,
    Result,
    TypedRefusal,
    World,
    WriterId,
    is_ok,
)
from qmf.data.store import (
    EvidenceStore,
    RegistryRoom,
    StoreEngineError,
    WorldStore,
    jsonl_opener,
)
from qmf.registry import (
    EdgeType,
    LineageEdge,
    RegistrationRecord,
    RegistryPersistence,
    migrate_registry_format,
    persistence_fingerprint,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _writer(machine: str) -> WriterId:
    return _unwrap(WriterId.try_create(machine, "authoring", "producer", "boot-1"), "writer")


def _record(body: Mapping[str, object], *, version: int = 1) -> RegistrationRecord:
    """A per-kind CT-06 record; occurrence facts differ between callers, identity does not."""
    return _unwrap(
        RegistrationRecord.try_create(
            "producer",
            version,
            [],
            body,
            _writer("node-a"),
            0,
            _unwrap(Instant.try_create(1_700_000_000_000_000_000), "created-at"),
        ),
        "record",
    )


def _persistence(root: Path) -> RegistryPersistence:
    store = EvidenceStore(root)
    return _unwrap(RegistryPersistence.open(store, World.LIVE), "live persistence")


def record_round_trips_content_addressed(root: Path) -> RegistrationRecord:
    """A record persists fp1-keyed and reads back with its identity intact."""
    persistence = _persistence(root)
    record = _record({"id": "sma-20", "period": 20})
    receipt = _unwrap(persistence.persist_record(record), "persist record")
    # Content-addressed: the storage key IS the record's own fp1 stable id (never a second
    # fingerprint wrapping it), so the receipt key, persistence_fingerprint, and stable_id
    # all coincide (CT-09 record_stable_id is the storage key).
    assert receipt.fingerprint == _unwrap(persistence_fingerprint(record), "persistence key")
    assert receipt.fingerprint == record.stable_id
    assert receipt.fingerprint.value.startswith("fp1:sha256:")
    assert receipt.outcome.value == "stored"
    loaded = _unwrap(persistence.load_record(record.stable_id, for_world=World.LIVE), "load")
    # The recomputed CT-06 stable id equals the original's — a faithful round trip.
    assert loaded.stable_id == record.stable_id
    assert loaded.kind == "producer"
    assert dict(loaded.body) == {"id": "sma-20", "period": 20}
    # The display-only occurrence facts (writer, per-writer sequence) round-trip too, from a
    # sidecar keyed by the same digest and OUTSIDE identity (who wrote it, in what order).
    assert loaded.writer == record.writer
    assert loaded.sequence == record.sequence
    return record


def idempotent_re_write_dedups(root: Path) -> str:
    """A byte-identical re-write (even from another sandbox) is idempotent."""
    persistence = _persistence(root)
    body = {"id": "sma-20", "period": 20}
    first = _unwrap(persistence.persist_record(_record(body)), "first write")
    assert first.outcome.value == "stored"
    # A second record with the SAME identity but a different writer/sequence dedups.
    twin = _unwrap(
        RegistrationRecord.try_create(
            "producer",
            1,
            [],
            body,
            _writer("node-b"),
            99,
            _unwrap(Instant.try_create(1_700_000_500_000_000_000), "later created-at"),
        ),
        "twin record",
    )
    again = _unwrap(persistence.persist_record(twin), "idempotent re-write")
    assert again.outcome.value == "idempotent"
    assert again.fingerprint == first.fingerprint
    return again.outcome.value


def edge_round_trips_on_its_fp1(root: Path) -> LineageEdge:
    """A lineage edge persists keyed on its own fp1 edge fingerprint and reads back."""
    persistence = _persistence(root)
    parent = _record({"id": "sma-20", "period": 20})
    child = _record({"id": "sma-20-v2", "period": 20})
    edge = _unwrap(
        LineageEdge.try_create(
            EdgeType.SUPERSEDES, child.stable_id, parent.stable_id, _writer("node-a")
        ),
        "supersedes edge",
    )
    receipt = _unwrap(
        persistence.persist_edge(edge, edge_stream="producer-lineage"), "persist edge"
    )
    # The storage key IS the edge's own fp1 edge fingerprint, exactly.
    assert receipt.fingerprint == edge.edge_fingerprint
    read = _unwrap(persistence.read_edges("producer-lineage", for_world=World.LIVE), "read edges")
    assert len(read) == 1
    assert read[0].edge_fingerprint == edge.edge_fingerprint
    assert read[0].edge_type is EdgeType.SUPERSEDES
    return read[0]


def cross_world_and_simulated_refuse(root: Path) -> tuple[TypedRefusal, TypedRefusal]:
    """A cross-world read and a simulated-world room are both policy rejections."""
    persistence = _persistence(root)
    receipt = _unwrap(persistence.persist_record(_record({"id": "x"})), "persist for cross-world")
    crossed = persistence.load_record(receipt.fingerprint, for_world=World.REPLAY)
    assert isinstance(crossed, TypedRefusal)
    assert crossed.category.value == "policy rejection"
    store = EvidenceStore(root)
    simulated = RegistryPersistence.open(store, World.SIMULATED)
    assert isinstance(simulated, TypedRefusal)
    assert simulated.category.value == "policy rejection"
    return crossed, simulated


class _RaisingMetadata:
    """A MetadataEngine that fails every write — the swappable-engine failure proof."""

    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        raise StoreEngineError("insert failed", engine="sqlite", detail={"digest": digest})

    def get(self, digest: str, /) -> bytes | None:  # pragma: no cover - unused in this demo
        raise StoreEngineError("read failed", engine="sqlite", detail={"digest": digest})

    def meta(self, digest: str, /) -> Mapping[str, object] | None:  # pragma: no cover - unused
        return None

    def digests(self) -> list[str]:  # pragma: no cover - unused in this demo
        return []


def store_failure_is_a_typed_refusal(root: Path) -> TypedRefusal:
    """An engine failure is a `storage failure` refusal, never an exception at the seam."""
    room = RegistryRoom(
        World.LIVE,
        record_engine=_RaisingMetadata(),
        lineage_dir=root / "lineage",
        open_stream=jsonl_opener(),
    )
    store = EvidenceStore(root)
    world_store = _unwrap(store.for_world(World.LIVE), "world store")
    # Swap the raising engine's room in behind the boundary (engines are swappable).
    swapped: WorldStore = replace(world_store, registry_room=room)
    persistence = RegistryPersistence(store, swapped)
    refused = persistence.persist_record(_record({"id": "will-not-land"}))
    assert isinstance(refused, TypedRefusal)
    assert refused.category.value == "storage failure"
    return refused


def _bump_to_v2(record: RegistrationRecord) -> Result[RegistrationRecord]:
    """A format transform: re-mint the record under contract format version 2."""
    return RegistrationRecord.try_create(
        record.kind,
        2,
        list(record.at_birth_parent_refs),
        dict(record.body),
        record.writer,
        record.sequence,
        record.created_at,
    )


def migration_is_staged_and_never_in_place(source_root: Path, dest_root: Path) -> tuple[str, int]:
    """A format change runs preflight→backup-first→dry-run→migrate→verify, never in-place."""
    source = _persistence(source_root)
    records: Sequence[RegistrationRecord] = [
        _record({"id": "sma-20", "period": 20}),
        _record({"id": "ema-50", "period": 50}),
    ]
    for record in records:
        _unwrap(source.persist_record(record), "seed source")
    destination = _persistence(dest_root)
    report = _unwrap(
        migrate_registry_format(
            records,
            source=source,
            destination=destination,
            transform=_bump_to_v2,
            to_format_version=2,
        ),
        "migration",
    )
    # The source is the intact restore path; the migration wrote only to the destination.
    assert report.restore_path == str(source_root)
    # backed_up reflects a REAL written backup artifact (not a hard-coded constant), and the
    # procedure states plainly that it migrates records only (CT-07 edges are not migrated).
    assert report.backed_up is True
    assert Path(report.backup_path).is_file()
    assert report.records_only is True
    assert report.migrated_count == 2
    assert report.verified_count == 2
    assert report.to_format_version == 2
    # A same-root migration is refused — the only copy is never mutated in place.
    in_place = migrate_registry_format(
        records, source=source, destination=source, transform=_bump_to_v2, to_format_version=2
    )
    assert isinstance(in_place, TypedRefusal)
    assert in_place.category.value == "invalid input"
    return report.restore_path, report.verified_count


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        record = record_round_trips_content_addressed(base / "round-trip")
        print(f"record persisted, content-addressed on fp1: {record.stable_id.value[:19]}...")

        outcome = idempotent_re_write_dedups(base / "idempotent")
        print(f"byte-identical re-write deduplicates: {outcome}")

        edge = edge_round_trips_on_its_fp1(base / "edges")
        print(f"lineage edge persisted on its own fp1: {edge.edge_type.value}")

        crossed, simulated = cross_world_and_simulated_refuse(base / "worlds")
        print(f"cross-world read refused: {crossed.category.value}")
        print(f"simulated world refused: {simulated.category.value}")

        refused = store_failure_is_a_typed_refusal(base / "failure")
        print(f"store failure is a typed refusal: {refused.category.value}")

        restore_path, verified = migration_is_staged_and_never_in_place(
            base / "migrate-src", base / "migrate-dst"
        )
        print(f"migration staged and never in-place: verified {verified}, restore path preserved")
        assert restore_path.endswith("migrate-src")


if __name__ == "__main__":
    main()
