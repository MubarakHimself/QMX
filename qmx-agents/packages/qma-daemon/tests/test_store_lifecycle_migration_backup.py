"""Story 42.5 — versioned-store migration, backup, and controlled restoration (FR-Q37)."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.core.refusals import OperatorPrincipalRequired, StoreVersionMismatch
from qma.daemon import AuthoritativeJournal, DaemonStoreLifecycle, PersistenceSubstrate
from qma.daemon.journal import (
    STORE_BACKUP_CADENCE_KEY,
    STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
    STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
)
from qma.daemon.persistence.lifecycle import (
    DAEMON_OWNED_DURABLE_BACKUP_STORES,
    GAP_0088_DEFERRED,
    LIVE_RESTORE_COMMAND,
    MIGRATABLE_STORES,
    StoreSnapshot,
)
from qma.daemon.persistence.schema import (
    JOURNAL_SCHEMA_MARKER_NAME,
    JOURNAL_STORE_NAME,
    KNOWN_STORE_SCHEMA_VERSION,
    SQLITE_META_SCHEMA_KEY,
    SQLITE_STORE_NAME,
    ensure_journal_schema_version,
    stamp_journal_schema_version,
    validate_store_schema_version,
)
from qmf.core import DataDrivenClock, Instant, RefusalCategory, is_ok, is_refusal
from qmf.data.verify import MIGRATION_SEQUENCE


def _test_clock(*, boot: str = "boot-42-5", n: int = 64) -> DataDrivenClock:
    base = 1_720_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    monos = tuple(i * 1_000 for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=monos)


def _open_journal(tmp_path: Path, *, boot: str = "boot-42-5") -> tuple[
    PersistenceSubstrate, AuthoritativeJournal
]:
    substrate_result = PersistenceSubstrate.open(
        tmp_path, machine="test-host", boot_epoch_id=boot
    )
    assert is_ok(substrate_result), substrate_result
    substrate = substrate_result.value
    journal_result = AuthoritativeJournal.bind(substrate, clock=_test_clock(boot=boot))
    assert is_ok(journal_result), journal_result
    return substrate, journal_result.value


def _fixture_snapshots() -> dict[str, StoreSnapshot]:
    return {
        name: StoreSnapshot(
            store=name,
            schema_version=KNOWN_STORE_SCHEMA_VERSION,
            records=(
                {"id": name, "n": 1, "body": f"fixture-{name}"},
                {"id": name, "n": 2, "body": f"fixture-{name}-b"},
            ),
        )
        for name in DAEMON_OWNED_DURABLE_BACKUP_STORES
    }


def _write_migratable(root: Path, store: str) -> StoreSnapshot:
    snap = StoreSnapshot(
        store=store,
        schema_version=KNOWN_STORE_SCHEMA_VERSION,
        records=({"k": store, "v": 1}, {"k": store, "v": 2}),
    )
    path = root / store / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snap.to_bytes())
    return snap


# --- store_schema_version gate -------------------------------------------------


def test_validate_store_schema_version_accepts_known() -> None:
    ok = validate_store_schema_version(
        store=JOURNAL_STORE_NAME,
        stamped=KNOWN_STORE_SCHEMA_VERSION,
    )
    assert is_ok(ok)
    assert ok.value == KNOWN_STORE_SCHEMA_VERSION


def test_unknown_or_newer_schema_refuses_naming_store_and_both_versions() -> None:
    refused = validate_store_schema_version(
        store=SQLITE_STORE_NAME,
        stamped=KNOWN_STORE_SCHEMA_VERSION + 7,
    )
    assert is_refusal(refused)
    assert StoreVersionMismatch.matches(refused)
    assert refused.context["store"] == SQLITE_STORE_NAME
    assert refused.context["expected_schema_version"] == KNOWN_STORE_SCHEMA_VERSION
    assert refused.context["store_schema_version"] == KNOWN_STORE_SCHEMA_VERSION + 7
    assert refused.category is RefusalCategory.STORAGE_FAILURE


def test_substrate_stamps_journal_and_sqlite_schema_on_open(tmp_path: Path) -> None:
    substrate = PersistenceSubstrate.open(
        tmp_path, machine="test-host", boot_epoch_id="boot-schema"
    )
    assert is_ok(substrate), substrate
    try:
        marker = tmp_path / "daemon" / JOURNAL_SCHEMA_MARKER_NAME
        assert marker.is_file()
        assert marker.read_text(encoding="utf-8").strip() == str(KNOWN_STORE_SCHEMA_VERSION)
        assert substrate.value.sqlite.recorded_store_schema_version() == KNOWN_STORE_SCHEMA_VERSION
        assert (
            substrate.value.startup_evidence.sqlite_version
            == substrate.value.sqlite.recorded_sqlite_version()
        )
        rows = substrate.value.sqlite.execute(
            "SELECT value FROM daemon_meta WHERE key = ?",
            (SQLITE_META_SCHEMA_KEY,),
        )
        assert rows == [(str(KNOWN_STORE_SCHEMA_VERSION),)]
    finally:
        substrate.value.close()


def test_substrate_refuses_unknown_journal_schema_before_reading(tmp_path: Path) -> None:
    daemon_dir = tmp_path / "daemon"
    stamp_journal_schema_version(daemon_dir, version=99)
    refused = PersistenceSubstrate.open(
        tmp_path, machine="test-host", boot_epoch_id="boot-bad-journal"
    )
    assert is_refusal(refused)
    assert StoreVersionMismatch.matches(refused)
    assert refused.context["store"] == JOURNAL_STORE_NAME
    assert refused.context["expected_schema_version"] == KNOWN_STORE_SCHEMA_VERSION
    assert refused.context["store_schema_version"] == 99


def test_substrate_refuses_unknown_sqlite_schema(tmp_path: Path) -> None:
    # First open stamps v1, then close and rewrite the meta stamp to a newer version.
    first = PersistenceSubstrate.open(
        tmp_path, machine="test-host", boot_epoch_id="boot-sql-1"
    )
    assert is_ok(first), first
    db_path = first.value.sqlite.db_path
    first.value.close()

    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO daemon_meta (key, value) VALUES (?, ?)",
        (SQLITE_META_SCHEMA_KEY, "42"),
    )
    conn.commit()
    conn.close()

    refused = PersistenceSubstrate.open(
        tmp_path, machine="test-host", boot_epoch_id="boot-sql-2"
    )
    assert is_refusal(refused)
    assert StoreVersionMismatch.matches(refused)
    assert refused.context["store"] == SQLITE_STORE_NAME
    assert refused.context["store_schema_version"] == 42
    assert refused.context["expected_schema_version"] == KNOWN_STORE_SCHEMA_VERSION


def test_ensure_journal_schema_never_silently_upgrades(tmp_path: Path) -> None:
    stamp_journal_schema_version(tmp_path, version=2)
    refused = ensure_journal_schema_version(tmp_path, known=1)
    assert is_refusal(refused)
    assert refused.context["store_schema_version"] == 2
    assert refused.context["expected_schema_version"] == 1
    # Marker unchanged — no silent upgrade.
    assert (tmp_path / JOURNAL_SCHEMA_MARKER_NAME).read_text(encoding="utf-8").strip() == "2"


# --- five-step migration ------------------------------------------------------


@pytest.mark.parametrize("store", sorted(MIGRATABLE_STORES))
def test_five_step_migration_never_in_place(tmp_path: Path, store: str) -> None:
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    original = _write_migratable(source, store)
    lifecycle = DaemonStoreLifecycle()
    report = lifecycle.migrate(
        store=store,
        source_root=source,
        destination_root=dest,
    )
    assert is_ok(report), report
    assert report.value.stages_completed == MIGRATION_SEQUENCE
    assert report.value.backed_up is True
    assert report.value.verified is True
    assert report.value.restore_path == str(source.resolve())
    assert report.value.destination_root == str(dest.resolve())
    assert report.value.migrated_record_count == len(original.records)
    # Source (documented restore path) untouched.
    assert (source / store / "snapshot.json").read_bytes() == original.to_bytes()
    # Destination received the migrate write.
    assert (dest / store / "snapshot.json").read_bytes() == original.to_bytes()


def test_in_place_migration_refused(tmp_path: Path) -> None:
    _write_migratable(tmp_path, "journal")
    lifecycle = DaemonStoreLifecycle()
    refused = lifecycle.migrate(
        store="journal",
        source_root=tmp_path,
        destination_root=tmp_path,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context.get("signal") == "refuse-in-place-migration"


# --- backup + sample/full restore ---------------------------------------------


def test_backup_covers_seven_stores_on_registry_cadence_key() -> None:
    lifecycle = DaemonStoreLifecycle()
    snaps = _fixture_snapshots()
    report = lifecycle.run_backup(snapshots=snaps, cadence_key=STORE_BACKUP_CADENCE_KEY)
    assert is_ok(report), report
    assert report.value.cadence_key == STORE_BACKUP_CADENCE_KEY
    assert report.value.stores == DAEMON_OWNED_DURABLE_BACKUP_STORES
    assert len(report.value.copies) == 7
    assert report.value.encryption_required is True
    assert all(copy.encryption_required for copy in report.value.copies)
    # Cadence cited by key — never a copied schedule value.
    assert report.value.cadence_key.startswith("registry:")


def test_backup_refuses_non_registry_cadence_citation() -> None:
    lifecycle = DaemonStoreLifecycle()
    refused = lifecycle.run_backup(
        snapshots=_fixture_snapshots(),
        cadence_key="nightly",
    )
    assert is_refusal(refused)


def test_sample_and_full_restore_into_scratch_not_live(tmp_path: Path) -> None:
    lifecycle = DaemonStoreLifecycle()
    snaps = _fixture_snapshots()
    backup = lifecycle.run_backup(snapshots=snaps)
    assert is_ok(backup), backup

    live = tmp_path / "live"
    sample_scratch = tmp_path / "sample-scratch"
    full_scratch = tmp_path / "full-scratch"
    live.mkdir()

    sample = lifecycle.run_sample_restore(
        backup=backup.value,
        expected=snaps,
        scratch_root=sample_scratch,
        live_root=live,
        cadence_key=STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
    )
    assert is_ok(sample), sample
    assert sample.value.kind == "sample-restore"
    assert sample.value.verified is True
    assert sample.value.cadence_key == STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY
    assert sample.value.scratch_root != sample.value.live_root
    assert (sample_scratch / "event_journal" / "snapshot.json").is_file()
    assert not (live / "event_journal").exists()

    full = lifecycle.run_full_restore_rehearsal(
        backup=backup.value,
        expected=snaps,
        scratch_root=full_scratch,
        live_root=live,
        cadence_key=STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
    )
    assert is_ok(full), full
    assert full.value.kind == "full-restore-rehearsal"
    assert full.value.verified is True
    assert full.value.cadence_key == STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY
    assert set(full.value.stores_verified) == set(DAEMON_OWNED_DURABLE_BACKUP_STORES)
    assert not any((live / name).exists() for name in DAEMON_OWNED_DURABLE_BACKUP_STORES)


def test_sample_restore_into_live_root_refused(tmp_path: Path) -> None:
    lifecycle = DaemonStoreLifecycle()
    snaps = _fixture_snapshots()
    backup = lifecycle.run_backup(snapshots=snaps)
    assert is_ok(backup)
    refused = lifecycle.run_sample_restore(
        backup=backup.value,
        expected=snaps,
        scratch_root=tmp_path / "same",
        live_root=tmp_path / "same",
    )
    assert is_refusal(refused)
    assert refused.context.get("signal") == "refuse-live-scratch-overlap"


# --- live restore is operator-only --------------------------------------------


def test_live_restore_requires_operator_and_records_journal(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path / "daemon-root")
    try:
        lifecycle = DaemonStoreLifecycle()
        snaps = _fixture_snapshots()
        backup = lifecycle.run_backup(snapshots=snaps)
        assert is_ok(backup)

        live = tmp_path / "live-target"
        receipt = lifecycle.restore_live(
            principal_class="operator",
            backup=backup.value,
            expected=snaps,
            live_root=live,
            journal=journal,
        )
        assert is_ok(receipt), receipt
        assert receipt.value.command == LIVE_RESTORE_COMMAND
        assert receipt.value.principal_class == "operator"
        assert receipt.value.journal is not None
        assert receipt.value.journal.record.event == "store.restore_live"
        assert set(receipt.value.stores_restored) == set(DAEMON_OWNED_DURABLE_BACKUP_STORES)
        assert all((live / name / "snapshot.json").is_file() for name in snaps)
    finally:
        substrate.close()


def test_live_restore_refuses_machine_principal(tmp_path: Path) -> None:
    lifecycle = DaemonStoreLifecycle()
    snaps = _fixture_snapshots()
    backup = lifecycle.run_backup(snapshots=snaps)
    assert is_ok(backup)
    refused = lifecycle.restore_live(
        principal_class="machine",
        backup=backup.value,
        expected=snaps,
        live_root=tmp_path / "live",
    )
    assert is_refusal(refused)
    assert OperatorPrincipalRequired.matches(refused)
    assert refused.context["command"] == LIVE_RESTORE_COMMAND


def test_live_restore_refuses_background_job(tmp_path: Path) -> None:
    lifecycle = DaemonStoreLifecycle()
    snaps = _fixture_snapshots()
    backup = lifecycle.run_backup(snapshots=snaps)
    assert is_ok(backup)
    refused = lifecycle.restore_live(
        principal_class="operator",
        backup=backup.value,
        expected=snaps,
        live_root=tmp_path / "live",
        as_background_job=True,
    )
    assert is_refusal(refused)
    assert refused.context.get("signal") == "refuse-background-live-restore"


def test_gap_0088_exclusions_remain_explicit() -> None:
    assert "backup_destination" in GAP_0088_DEFERRED
    assert "encryption_key_custody" in GAP_0088_DEFERRED
    assert "sample_restore_test_cadence_value" in GAP_0088_DEFERRED
    assert "full_restore_rehearsal_cadence_value" in GAP_0088_DEFERRED
    # No real B2 / provider selection is shipped by the lifecycle fixtures.
    storage = DaemonStoreLifecycle().storage
    assert storage.__class__.__name__ == "_MemoryStorage"
