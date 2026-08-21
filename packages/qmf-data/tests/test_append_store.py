"""Tier-1 tests for the CT-11 append-store boundary (AC1, AC2, AC5)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import World, fingerprint, is_ok, is_refusal
from qmf.data.store import AppendStore, EvidenceStore
from qmf.data.store.engines.duckdb_views import DuckDbAnalyticsEngine
from qmf.data.store.engines.parquet import ParquetColumnarEngine

_ROWS = [{"t": 1, "px": 100}, {"t": 2, "px": 101}]


def _append_store(store: EvidenceStore) -> AppendStore:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return world.value.append_store


def test_append_raw_stores_evidence(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    result = boundary.append_raw(_ROWS)
    assert is_ok(result)
    receipt = result.value
    assert receipt.outcome.value == "stored"
    assert receipt.engine == "parquet"
    assert receipt.room_role.value == "immutable raw archive"
    assert receipt.is_evidence_bearing is True
    assert receipt.retained_forever is True


def test_append_raw_idempotent_rewrite(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    first = boundary.append_raw(_ROWS)
    second = boundary.append_raw(_ROWS)
    assert is_ok(first)
    assert is_ok(second)
    assert second.value.outcome.value == "idempotent"
    assert first.value.fingerprint == second.value.fingerprint


def test_read_raw_round_trips(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    receipt = boundary.append_raw(_ROWS)
    assert is_ok(receipt)
    read = boundary.read_raw(receipt.value.fingerprint.value)
    assert is_ok(read)
    assert read.value == _ROWS


def test_read_raw_absent_is_invalid_input(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    fp = fingerprint({"nope": 1})
    assert is_ok(fp)
    result = boundary.read_raw(fp.value.value)
    assert is_refusal(result)
    assert result.category.value == "invalid input"


def test_read_raw_cross_world_is_policy_rejection(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    receipt = boundary.append_raw(_ROWS)
    assert is_ok(receipt)
    result = boundary.read_raw(receipt.value.fingerprint.value, for_world=World.REPLAY)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_append_raw_refuses_float(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    result = boundary.append_raw([{"px": 1.5}])
    assert is_refusal(result)
    assert result.category.value == "invalid input"


def test_append_raw_presented_fingerprint_match_and_mismatch(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    fp = fingerprint(_ROWS)
    assert is_ok(fp)
    ok = boundary.append_raw(_ROWS, presented_fingerprint=fp.value)
    assert is_ok(ok)
    wrong = fingerprint({"other": 1})
    assert is_ok(wrong)
    bad = boundary.append_raw(_ROWS, presented_fingerprint=wrong.value)
    assert is_refusal(bad)
    assert bad.category.value == "invalid input"


def test_materialize_view_is_rebuildable_not_evidence(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    result = boundary.materialize_view(_ROWS)
    assert is_ok(result)
    receipt = result.value
    assert receipt.engine == "duckdb"
    assert receipt.room_role.value == "processed"
    assert receipt.is_evidence_bearing is False
    assert receipt.retained_forever is False
    assert receipt.engine_major is not None


def test_read_view_round_trips_and_absent_refuses(store: EvidenceStore) -> None:
    boundary = _append_store(store)
    receipt = boundary.materialize_view(_ROWS)
    assert is_ok(receipt)
    read = boundary.read_view(receipt.value.fingerprint.value)
    assert is_ok(read)
    assert read.value == _ROWS
    fp = fingerprint({"absent": True})
    assert is_ok(fp)
    missing = boundary.read_view(fp.value.value)
    assert is_refusal(missing)


def test_simulated_write_is_policy_rejection(tmp_path: Path) -> None:
    boundary = AppendStore(
        World.SIMULATED,
        raw_engine=ParquetColumnarEngine(tmp_path / "raw"),
        view_engine=DuckDbAnalyticsEngine(tmp_path / "views.duckdb"),
    )
    result = boundary.append_raw(_ROWS)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"
    view = boundary.materialize_view(_ROWS)
    assert is_refusal(view)
    assert view.category.value == "policy rejection"
