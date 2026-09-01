"""Story 42.1 — single-process sole-writer persistence substrate (FR-Q22)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from qma.daemon import PersistenceSubstrate
from qma.daemon.persistence import (
    DAEMON_LOCK_NAME,
    DUCKDB_IS_EVIDENCE,
    FoldSqliteReader,
    FoldViewEngine,
)
from qmf.core import RefusalCategory, World, is_ok, is_refusal
from qmf.data.store.append_store import AppendStore
from qmf.data.store.journal import JournalStore


def _open(tmp_path: Path, *, boot: str = "boot-1") -> PersistenceSubstrate:
    result = PersistenceSubstrate.open(tmp_path, machine="test-host", boot_epoch_id=boot)
    assert is_ok(result), result
    return result.value


def test_open_establishes_sole_writer_and_qmf_data_sinks(tmp_path: Path) -> None:
    substrate = _open(tmp_path)
    try:
        assert isinstance(substrate.journal, JournalStore)
        assert isinstance(substrate.artifact_store, AppendStore)
        assert substrate.world_store.world is World.LIVE
        assert (tmp_path / DAEMON_LOCK_NAME).is_file()
        assert substrate.sqlite.connection_count_evidence() == 1
        assert substrate.sqlite.db_path.is_file()
    finally:
        substrate.close()


def test_startup_records_sqlite_version_as_evidence(tmp_path: Path) -> None:
    substrate = _open(tmp_path)
    try:
        evidence = substrate.startup_evidence
        assert evidence.sqlite_version == sqlite3.sqlite_version
        assert evidence.journal_mode.lower() == "wal"
        assert evidence.sqlite_thread_name == "qma-daemon-sqlite"
        assert substrate.sqlite.recorded_sqlite_version() == sqlite3.sqlite_version
    finally:
        substrate.close()


def test_checkpoints_run_only_on_sole_writable_connection(tmp_path: Path) -> None:
    substrate = _open(tmp_path)
    try:
        substrate.sqlite.execute(
            "CREATE TABLE IF NOT EXISTS fold_probe (id INTEGER PRIMARY KEY, note TEXT)"
        )
        substrate.sqlite.execute("INSERT INTO fold_probe (note) VALUES (?)", ("alpha",))
        busy, log, checkpointed = substrate.sqlite.checkpoint("PASSIVE")
        assert busy in (0, 1)
        assert log >= 0
        assert checkpointed >= 0
        assert substrate.sqlite.connection_count_evidence() == 1
    finally:
        substrate.close()


def test_fold_reader_is_read_only_and_never_checkpoints(tmp_path: Path) -> None:
    substrate = _open(tmp_path)
    try:
        substrate.sqlite.execute(
            "CREATE TABLE IF NOT EXISTS fold_probe (id INTEGER PRIMARY KEY, note TEXT)"
        )
        substrate.sqlite.execute("INSERT INTO fold_probe (note) VALUES (?)", ("fold-me",))
        substrate.sqlite.checkpoint("TRUNCATE")

        fold = substrate.open_fold_reader()
        assert is_ok(fold)
        reader: FoldSqliteReader = fold.value
        rows = reader.execute("SELECT note FROM fold_probe")
        assert rows == [("fold-me",)]

        refused = reader.checkpoint()
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        reason = str(refused.context.get("reason", "")).lower()
        assert "never checkpoint" in reason
        reader.close()
    finally:
        substrate.close()


def test_duckdb_fold_views_are_never_evidence(tmp_path: Path) -> None:
    substrate = _open(tmp_path)
    try:
        views = substrate.open_fold_views()
        assert isinstance(views, FoldViewEngine)
        assert views.is_evidence_bearing is False
        assert DUCKDB_IS_EVIDENCE is False
    finally:
        substrate.close()


def test_second_daemon_in_process_is_refused(tmp_path: Path) -> None:
    first = _open(tmp_path)
    try:
        second = PersistenceSubstrate.open(
            tmp_path / "other", machine="test-host", boot_epoch_id="boot-2"
        )
        assert is_refusal(second)
        assert second.category is RefusalCategory.POLICY_REJECTION
        assert "second daemon" in str(second.context.get("reason", "")).lower()
    finally:
        first.close()


def test_second_writer_on_same_root_is_refused(tmp_path: Path) -> None:
    """Cross-process-shaped refusal: lock file held by a distinct token."""
    from qma.daemon.persistence.lock import DaemonWriterLock, WriterLockToken

    holder = DaemonWriterLock(
        tmp_path,
        WriterLockToken(machine="host-a", role="qma-daemon", boot_epoch_id="b1", pid=1),
    )
    assert is_ok(holder.acquire())
    try:
        refused = PersistenceSubstrate.open(tmp_path, machine="host-b", boot_epoch_id="b2")
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        reason = str(refused.context.get("reason", "")).lower()
        assert "second" in reason and "writer" in reason
    finally:
        holder.release()


def test_no_alternate_durable_write_path_outside_substrate(tmp_path: Path) -> None:
    """Writable SQLite and journal sinks are only reachable through the substrate."""
    substrate = _open(tmp_path)
    try:
        assert substrate.journal is substrate.world_store.journal
        assert substrate.artifact_store is substrate.world_store.append_store
        fold_result = substrate.open_fold_reader()
        assert is_ok(fold_result)
        fold = fold_result.value
        assert is_refusal(fold.checkpoint("FULL"))
        fold.close()
    finally:
        substrate.close()


def test_reopen_after_close_succeeds(tmp_path: Path) -> None:
    first = _open(tmp_path, boot="boot-a")
    version = first.startup_evidence.sqlite_version
    first.close()
    second = _open(tmp_path, boot="boot-b")
    try:
        assert second.startup_evidence.sqlite_version == version
    finally:
        second.close()
