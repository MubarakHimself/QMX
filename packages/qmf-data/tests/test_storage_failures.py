"""Tier-1 tests: engine failures translate to storage-failure refusals (AC4).

The raising fakes are alternate implementations injected behind the owned engine
Protocols, so these tests double as proof that each engine is swappable (AC1).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from qmf.core import World, WriterId, is_ok, is_refusal
from qmf.data.store import AppendStore, EvidenceStore, RegistryRoom, jsonl_opener
from qmf.data.store.engines import StoreEngineError

_ROWS = [{"t": 1, "px": 100}]


class _RaisingColumnar:
    def write(self, key: str, rows: Sequence[Mapping[str, object]], canonical: bytes, /) -> None:
        raise StoreEngineError("write failed", engine="parquet", detail={"key": key})

    def read(self, key: str, /) -> list[dict[str, object]]:
        raise StoreEngineError("read failed", engine="parquet", detail={"key": key})

    def read_canonical(self, key: str, /) -> bytes | None:
        return None

    def has(self, key: str, /) -> bool:
        return True

    def stored_keys(self) -> list[str]:
        return []


class _RaisingAnalytics:
    def materialize(
        self, key: str, rows: Sequence[Mapping[str, object]], canonical: bytes, /
    ) -> None:
        raise StoreEngineError("materialize failed", engine="duckdb", detail={"key": key})

    def query(self, key: str, /) -> list[dict[str, object]]:
        raise StoreEngineError("query failed", engine="duckdb", detail={"key": key})

    def read_canonical(self, key: str, /) -> bytes | None:
        return None

    def drop(self, key: str, /) -> None:  # pragma: no cover - unused
        raise StoreEngineError("drop failed", engine="duckdb")

    def has(self, key: str, /) -> bool:
        return True

    def engine_major(self) -> str:
        return "duckdb-0"


class _RaisingMetadata:
    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        raise StoreEngineError("insert failed", engine="sqlite", detail={"digest": digest})

    def get(self, digest: str, /) -> bytes | None:
        raise StoreEngineError("read failed", engine="sqlite", detail={"digest": digest})

    def meta(self, digest: str, /) -> Mapping[str, object] | None:  # pragma: no cover - unused
        return None

    def digests(self) -> list[str]:  # pragma: no cover - unused
        return []


def _append_store() -> AppendStore:
    return AppendStore(World.LIVE, raw_engine=_RaisingColumnar(), view_engine=_RaisingAnalytics())


def test_raw_write_failure_translates_to_storage_failure() -> None:
    result = _append_store().append_raw(_ROWS)
    assert is_refusal(result)
    assert result.category.value == "storage failure"
    assert result.context.get("engine") == "parquet"


def test_raw_read_failure_translates_to_storage_failure() -> None:
    result = _append_store().read_raw("fp1:sha256:" + "0" * 64, for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category.value == "storage failure"


def test_view_materialize_failure_translates() -> None:
    result = _append_store().materialize_view(_ROWS)
    assert is_refusal(result)
    assert result.category.value == "storage failure"


def test_view_query_failure_translates() -> None:
    result = _append_store().read_view("fp1:sha256:" + "0" * 64, for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category.value == "storage failure"


def test_record_put_and_get_failures_translate(tmp_path: Path) -> None:
    room = RegistryRoom(
        World.LIVE,
        record_engine=_RaisingMetadata(),
        lineage_dir=tmp_path / "lineage",
        open_stream=jsonl_opener(),
    )
    put = room.put_record({"kind": "x"}, kind="x", format_version=1)
    assert is_refusal(put)
    assert put.category.value == "storage failure"
    get = room.get_record("fp1:sha256:" + "0" * 64, for_world=World.LIVE)
    assert is_refusal(get)
    assert get.category.value == "storage failure"


def test_journal_read_failure_on_corrupt_stream(store: EvidenceStore) -> None:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    journal = world.value.journal
    writer = WriterId.try_create("node-a", "data", "dq", "boot-1")
    assert is_ok(writer)
    assert is_ok(journal.append("dq", writer.value, {"event_type": "data quality", "n": 0}))
    # Corrupt the underlying stream file with a partial (unterminated) trailing line.
    corrupt = store.root / "live" / "journal" / "dq" / "000000.jsonl"
    corrupt.write_bytes(b'{"partial": ')
    read = journal.read_stream("dq", for_world=World.LIVE)
    assert is_refusal(read)
    assert read.category.value == "storage failure"
