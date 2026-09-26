"""Reference usage — the dependency-free store seam (COMP-QMF-DATA-STORE).

Executable::

    python packages/qmf-data/examples/store_usage.py

Shows the five things Story 3.1 pins down:

1. Four boundaries over four engines — CT-11 raw archive (Parquet) and rebuildable
   view (DuckDB), CT-13 journal (JSONL), CT-09 registry record (SQLite) and lineage
   edge (JSONL) — each keyed on its fp1 fingerprint, with no database server.
2. Content-addressing: a byte-identical re-write is accepted silently (idempotent),
   never a duplicate.
3. World policy: a ``world = simulated`` store is refused, and a cross-world read is a
   policy rejection — world isolation is storage separation.
4. One writer per journal stream: a second, distinct WriterId does not proceed.
5. The CT-26 backup input presents a room's records verbatim to the backup primitive.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import Result, World, WriterId, is_ok, is_refusal
from qmf.data.store import EvidenceStore, RoomRole, WorldStore

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


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "data", "dq", "boot-1"), "writer")


def four_boundaries_over_four_engines(world: WorldStore) -> None:
    """One artifact through each of the four boundaries, each on its own engine."""
    raw = _unwrap(world.append_store.append_raw([{"t": 1, "px": 100}]), "raw append")
    view = _unwrap(world.append_store.materialize_view([{"t": 1, "px": 100}]), "view")
    journal = _unwrap(
        world.journal.append("dq", _writer(), {"event_type": "data quality", "n": 0}),
        "journal append",
    )
    record = _unwrap(
        world.registry_room.put_record({"kind": "producer"}, kind="producer", format_version=1),
        "registry record",
    )
    _require(raw.engine == "parquet", "raw archive on parquet")
    _require(view.engine == "duckdb", "view on duckdb")
    _require(journal.engine == "jsonl", "journal on jsonl")
    _require(record.engine == "sqlite", "registry record on sqlite")


def idempotent_rewrite(world: WorldStore) -> str:
    """A byte-identical re-write is idempotent, not a collision or a duplicate."""
    rows = [{"t": 9, "px": 200}]
    first = _unwrap(world.append_store.append_raw(rows), "first raw")
    again = _unwrap(world.append_store.append_raw(rows), "idempotent raw")
    _require(first.fingerprint == again.fingerprint, "same fingerprint on re-write")
    return again.outcome.value


def simulated_and_cross_world_refused(store: EvidenceStore, world: WorldStore) -> None:
    """A simulated store is refused; a cross-world read is a policy rejection."""
    simulated = store.for_world(World.SIMULATED)
    _require(is_refusal(simulated), "simulated store refused")
    _require(
        is_refusal(simulated) and simulated.category.value == "policy rejection",
        "simulated is a policy rejection",
    )

    receipt = _unwrap(world.append_store.append_raw([{"t": 2, "px": 300}]), "raw")
    # The caller declares it is reading the replay world, but the store is live —
    # a cross-world read is refused (the world declaration is required, M4).
    cross = world.append_store.read_raw(receipt.fingerprint.value, for_world=World.REPLAY)
    _require(is_refusal(cross), "cross-world read refused")
    _require(
        is_refusal(cross) and cross.category.value == "policy rejection",
        "cross-world read is a policy rejection",
    )


def one_writer_per_stream(world: WorldStore) -> str:
    """A second, distinct writer may not hold a stream another writer holds."""
    first = _unwrap(WriterId.try_create("node-a", "data", "ctrl", "boot-1"), "writer a")
    second = _unwrap(WriterId.try_create("node-b", "data", "ctrl", "boot-1"), "writer b")
    _unwrap(world.journal.append("ctrl", first, {"event_type": "control action"}), "first append")
    refusal = world.journal.append("ctrl", second, {"event_type": "control action"})
    _require(is_refusal(refusal), "second writer refused")
    return refusal.category.value if is_refusal(refusal) else "unexpected-ok"


def backup_reads_verbatim(world: WorldStore) -> int:
    """The CT-26 backup input presents the raw archive verbatim."""
    export = _unwrap(
        world.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=world.world),
        "backup export",
    )
    return export.record_count


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qmf-store-usage-") as tmp:
        store = EvidenceStore(Path(tmp))
        world = _unwrap(store.for_world(World.LIVE), "live world store")

        four_boundaries_over_four_engines(world)
        print("four boundaries over four engines: parquet, duckdb, jsonl, sqlite")

        outcome = idempotent_rewrite(world)
        print(f"byte-identical re-write is: {outcome}")

        simulated_and_cross_world_refused(store, world)
        print("simulated store and cross-world read: both policy rejection")

        writer_outcome = one_writer_per_stream(world)
        print(f"second writer on a held stream: {writer_outcome}")

        count = backup_reads_verbatim(world)
        print(f"backup input read raw-archive records verbatim: {count}")


if __name__ == "__main__":
    main()
