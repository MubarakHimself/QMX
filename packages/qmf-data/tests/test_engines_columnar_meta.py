"""Tier-1 tests for the Parquet, SQLite, and DuckDB engines (AC1, AC4)."""

from __future__ import annotations

from pathlib import Path

import pytest
from qmf.core import canonical_bytes, fingerprint, is_ok
from qmf.data.store.engines import StoreEngineError
from qmf.data.store.engines import duckdb_views as duckdb_views_module
from qmf.data.store.engines.duckdb_views import DuckDbAnalyticsEngine
from qmf.data.store.engines.parquet import ParquetColumnarEngine
from qmf.data.store.engines.sqlite_meta import SqliteMetadataEngine


def _identity(obj: object) -> tuple[str, bytes]:
    canonical = canonical_bytes(obj)
    fp = fingerprint(obj)
    assert is_ok(canonical)
    assert is_ok(fp)
    return fp.value.digest, canonical.value


# --- Parquet ----------------------------------------------------------------


def test_parquet_round_trip_and_embedded_canonical(tmp_path: Path) -> None:
    engine = ParquetColumnarEngine(tmp_path / "raw")
    rows = [{"t": 1, "px": 100, "sym": "EURUSD"}, {"t": 2, "px": 101, "sym": "EURUSD"}]
    key, canonical = _identity(rows)
    engine.write(key, rows, canonical)
    assert engine.has(key)
    assert engine.read(key) == rows
    assert engine.read_canonical(key) == canonical
    assert engine.stored_keys() == [key]


def test_parquet_read_canonical_none_for_absent(tmp_path: Path) -> None:
    engine = ParquetColumnarEngine(tmp_path / "raw")
    assert engine.read_canonical("0" * 64) is None
    assert engine.has("0" * 64) is False
    assert engine.stored_keys() == []


def test_parquet_empty_rows(tmp_path: Path) -> None:
    engine = ParquetColumnarEngine(tmp_path / "raw")
    key, canonical = _identity([])
    engine.write(key, [], canonical)
    assert engine.read(key) == []
    assert engine.read_canonical(key) == canonical


def test_parquet_heterogeneous_and_big_int_round_trip(tmp_path: Path) -> None:
    """H4/H5: heterogeneous rows and an arbitrary-precision int round-trip exactly and
    re-fingerprint to the same fp1 (no None backfill, no int64 overflow)."""
    engine = ParquetColumnarEngine(tmp_path / "raw")
    rows = [{"a": 1}, {"b": 2}, {"big": 2**70}]
    key, canonical = _identity(rows)
    engine.write(key, rows, canonical)  # must not overflow
    back = engine.read(key)
    assert back == rows  # exact, not [{"a":1},{"a":None},...]
    again = fingerprint(back)
    assert is_ok(again)
    assert again.value.digest == key  # re-fingerprints to the same fp1


def test_parquet_read_raises_on_corrupt_file(tmp_path: Path) -> None:
    engine = ParquetColumnarEngine(tmp_path / "raw")
    key, canonical = _identity([{"t": 1}])
    engine.write(key, [{"t": 1}], canonical)
    (tmp_path / "raw" / f"{key}.parquet").write_bytes(b"not a parquet file")
    with pytest.raises(StoreEngineError):
        engine.read(key)
    with pytest.raises(StoreEngineError):
        engine.read_canonical(key)


# --- SQLite -----------------------------------------------------------------


def test_sqlite_put_get_meta_digests(tmp_path: Path) -> None:
    engine = SqliteMetadataEngine(tmp_path / "reg" / "records.sqlite")
    record = {"kind": "producer", "id": "sma-20"}
    key, canonical = _identity(record)
    engine.put(key, canonical, kind="producer", format_version=1)
    assert engine.get(key) == canonical
    meta = engine.meta(key)
    assert meta == {"kind": "producer", "format_version": 1}
    assert engine.digests() == [key]


def test_sqlite_absent_reads_return_none(tmp_path: Path) -> None:
    engine = SqliteMetadataEngine(tmp_path / "reg" / "records.sqlite")
    assert engine.get("0" * 64) is None
    assert engine.meta("0" * 64) is None
    assert engine.digests() == []


def test_sqlite_duplicate_insert_raises(tmp_path: Path) -> None:
    engine = SqliteMetadataEngine(tmp_path / "reg" / "records.sqlite")
    key, canonical = _identity({"kind": "x"})
    engine.put(key, canonical, kind="x", format_version=1)
    with pytest.raises(StoreEngineError):
        engine.put(key, canonical, kind="x", format_version=1)


def test_sqlite_corrupt_database_raises(tmp_path: Path) -> None:
    db = tmp_path / "reg" / "records.sqlite"
    engine = SqliteMetadataEngine(db)
    key, canonical = _identity({"kind": "seed"})
    engine.put(key, canonical, kind="seed", format_version=1)
    db.write_bytes(b"this is not a sqlite database at all, definitely corrupt")
    with pytest.raises(StoreEngineError):
        engine.get("0" * 64)


def test_sqlite_duplicate_insert_is_not_retryable(tmp_path: Path) -> None:
    """L3: a constraint violation (IntegrityError) is permanent — never retryable,
    so it can never invite an infinite retry (classified by exception type, not by
    string-matching the message)."""
    engine = SqliteMetadataEngine(tmp_path / "reg" / "records.sqlite")
    key, canonical = _identity({"kind": "x"})
    engine.put(key, canonical, kind="x", format_version=1)
    with pytest.raises(StoreEngineError) as caught:
        engine.put(key, canonical, kind="x", format_version=1)
    assert caught.value.retryable is False


def test_sqlite_corrupt_database_is_not_retryable(tmp_path: Path) -> None:
    """L3: a corrupt/malformed database is permanent — not a retryable failure."""
    db = tmp_path / "reg" / "records.sqlite"
    engine = SqliteMetadataEngine(db)
    key, canonical = _identity({"kind": "seed"})
    engine.put(key, canonical, kind="seed", format_version=1)
    db.write_bytes(b"this is definitely not a sqlite database")
    with pytest.raises(StoreEngineError) as caught:
        engine.get("0" * 64)
    assert caught.value.retryable is False


# --- DuckDB -----------------------------------------------------------------


def test_duckdb_materialize_query_and_identity(tmp_path: Path) -> None:
    engine = DuckDbAnalyticsEngine(tmp_path / "proc" / "views.duckdb")
    rows = [{"t": 1, "v": 10}, {"t": 2, "v": 20}]
    key, canonical = _identity(rows)
    engine.materialize(key, rows, canonical)
    assert engine.has(key)
    assert engine.query(key) == rows
    assert engine.read_canonical(key) == canonical
    assert engine.engine_major().startswith("duckdb-")


def test_duckdb_rebuild_is_licensed(tmp_path: Path) -> None:
    engine = DuckDbAnalyticsEngine(tmp_path / "proc" / "views.duckdb")
    rows = [{"t": 1, "v": 10}]
    key, canonical = _identity(rows)
    engine.materialize(key, rows, canonical)
    engine.materialize(key, rows, canonical)  # rebuild, no error
    assert engine.query(key) == rows


def test_duckdb_query_absent_raises(tmp_path: Path) -> None:
    engine = DuckDbAnalyticsEngine(tmp_path / "proc" / "views.duckdb")
    with pytest.raises(StoreEngineError):
        engine.query("0" * 64)


def test_duckdb_read_canonical_none_and_drop(tmp_path: Path) -> None:
    engine = DuckDbAnalyticsEngine(tmp_path / "proc" / "views.duckdb")
    rows = [{"t": 1, "v": 10}]
    key, canonical = _identity(rows)
    assert engine.read_canonical(key) is None
    engine.materialize(key, rows, canonical)
    engine.drop(key)
    assert engine.has(key) is False


def test_duckdb_corrupt_payload_decode_is_storage_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L2: a payload that fails to JSON-decode is a storage failure raised inside the
    guarded block, never a raw ValueError escaping query()."""
    engine = DuckDbAnalyticsEngine(tmp_path / "proc" / "views.duckdb")
    rows = [{"t": 1, "v": 10}]
    key, canonical = _identity(rows)
    engine.materialize(key, rows, canonical)

    def _boom(_text: str) -> object:
        raise ValueError("corrupt payload")

    monkeypatch.setattr(duckdb_views_module.json, "loads", _boom)
    with pytest.raises(StoreEngineError):
        engine.query(key)
