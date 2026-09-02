"""Story 48.2 — Migrate reversible and forward-only plugin data (FR-Q69)."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.core.plugins import ManifestError, PluginContext, parse_plugin_manifest
from qma.core.plugins.manifest import validate_migration_rollback_contract
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.persistence.lifecycle import DaemonStoreLifecycle
from qma.daemon.plugins import (
    CHECKPOINT_IS_RECOVERY_COPY,
    DAEMON_CORE_MIGRATION_TARGETS,
    JOURNAL_CHECKPOINT_EVENT,
    PLUGIN_INSTALL_PREFLIGHT_QUERY,
    REVERSIBLE_BY_DOWN,
    DaemonCoreMigrationDeclaration,
    DaemonPluginContext,
    PluginDataSnapshot,
    PluginLoader,
    PluginMigrationRunner,
    rollback_mode_for_manifest,
)
from qma.wire.vocabulary import WireQuery
from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.data.verify import MIGRATION_SEQUENCE


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "dependencies": [],
        "contributions": [{"point": "tool", "local_id": "search"}],
        "permissions": [],
        "migrations": [],
    }
    base.update(overrides)
    return base


def _activate(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("search", {"name": "search"})


def _write_plugin_data(root: Path, plugin_id: str) -> PluginDataSnapshot:
    snap = PluginDataSnapshot(
        plugin_id=plugin_id,
        schema_version=1,
        records=({"k": "v", "n": 1}, {"k": "v", "n": 2}),
    )
    path = root / plugin_id / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snap.to_bytes())
    return snap


# --- rollback contract --------------------------------------------------------


def test_empty_migrations_omit_rollback() -> None:
    manifest = parse_plugin_manifest(_manifest(migrations=[]))
    assert manifest.migrations == ()
    assert manifest.rollback is None
    assert rollback_mode_for_manifest(manifest) == REVERSIBLE_BY_DOWN


def test_empty_migrations_must_not_declare_rollback() -> None:
    with pytest.raises(ManifestError, match="empty migration set must not declare rollback"):
        parse_plugin_manifest(_manifest(migrations=[], rollback="forward_only"))


def test_reversible_migrations_require_down() -> None:
    with pytest.raises(ManifestError, match="declares a 'down'"):
        parse_plugin_manifest(
            _manifest(migrations=[{"id": "m1", "up": {"add": "col"}}])
        )
    validate_migration_rollback_contract(
        ({"id": "m1", "up": {"add": "col"}, "down": {"drop": "col"}},),
        None,
    )


def test_forward_only_migrations_skip_down_requirement() -> None:
    manifest = parse_plugin_manifest(
        _manifest(
            migrations=[{"id": "m1", "up": {"rewrite": True}}],
            rollback="forward_only",
        )
    )
    assert manifest.rollback == "forward_only"
    assert rollback_mode_for_manifest(manifest) == "forward_only"


# --- install preflight query --------------------------------------------------


def test_install_preflight_returns_rollback_mode_over_wire() -> None:
    runner = PluginMigrationRunner()
    reversible = runner.install_preflight(
        _manifest(
            migrations=[{"id": "m1", "up": {"a": 1}, "down": {"a": 0}}],
        )
    )
    assert is_ok(reversible)
    assert reversible.value.query == PLUGIN_INSTALL_PREFLIGHT_QUERY
    assert reversible.value.query == WireQuery.PLUGIN_INSTALL_PREFLIGHT.value
    assert reversible.value.rollback_mode == REVERSIBLE_BY_DOWN
    assert reversible.value.requires_operator_confirmation is False
    payload = reversible.value.to_payload()
    assert payload["family"] == "query"
    assert payload["name"] == "plugin_install_preflight"

    forward = runner.install_preflight(
        _manifest(
            migrations=[{"id": "m1", "up": {"a": 1}}],
            rollback="forward_only",
        )
    )
    assert is_ok(forward)
    assert forward.value.rollback_mode == "forward_only"
    assert forward.value.requires_operator_confirmation is True


# --- five-step path + journal checkpoint --------------------------------------


def test_reversible_migration_runs_ordered_path_with_checkpoint(tmp_path: Path) -> None:
    source = tmp_path / "src"
    dest = tmp_path / "dst"
    original = _write_plugin_data(source, "research-corpus")
    runner = PluginMigrationRunner()
    manifest = parse_plugin_manifest(
        _manifest(
            migrations=[{"id": "m1", "up": {"add": "x"}, "down": {"drop": "x"}}],
        )
    )
    report = runner.run_plugin_migrations(
        manifest,
        source_root=source,
        destination_root=dest,
        correlation_id="corr-migrate-1",
    )
    assert is_ok(report), report
    assert report.value.stages_completed == MIGRATION_SEQUENCE
    assert report.value.backed_up is True
    assert report.value.verified is True
    assert report.value.restore_path == str(source.resolve())
    assert report.value.checkpoint.correlation_id == "corr-migrate-1"
    assert report.value.checkpoint.fingerprint.startswith("fp1:sha256:")
    assert report.value.checkpoint.is_recovery_copy is False
    assert report.value.checkpoint.is_recovery_copy is CHECKPOINT_IS_RECOVERY_COPY
    assert (source / "research-corpus" / "snapshot.json").read_bytes() == original.to_bytes()
    assert (dest / "research-corpus" / "snapshot.json").is_file()


def test_failed_preflight_refuses_without_treating_checkpoint_as_recovery(
    tmp_path: Path,
) -> None:
    runner = PluginMigrationRunner()
    manifest = parse_plugin_manifest(
        _manifest(
            migrations=[{"id": "m1", "up": {"add": "x"}, "down": {"drop": "x"}}],
        )
    )
    refused = runner.run_plugin_migrations(
        manifest,
        source_root=tmp_path / "missing-src",
        destination_root=tmp_path / "dst",
        correlation_id="corr-fail-preflight",
    )
    assert is_refusal(refused)
    assert refused.context.get("checkpoint_is_recovery_copy") is False
    assert refused.context.get("field") == "preflight"


def test_journal_checkpoint_event_name() -> None:
    assert JOURNAL_CHECKPOINT_EVENT == "migration.checkpoint"


# --- forward-only confirmation + disable --------------------------------------


def test_forward_only_refused_without_operator_confirmation(tmp_path: Path) -> None:
    source = tmp_path / "src"
    dest = tmp_path / "dst"
    _write_plugin_data(source, "research-corpus")
    loader = PluginLoader(
        migration_source_root=source,
        migration_destination_root=dest,
    )
    raw = _manifest(
        migrations=[{"id": "m1", "up": {"rewrite": True}}],
        rollback="forward_only",
    )
    refused = loader.install(raw, activator=_activate)
    assert is_refusal(refused)
    assert refused.context.get("field") == "forward_only_confirmation"


def test_forward_only_accepts_after_operator_confirm_and_disable_keeps_data(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src"
    dest = tmp_path / "dst"
    _write_plugin_data(source, "research-corpus")
    loader = PluginLoader(
        migration_source_root=source,
        migration_destination_root=dest,
    )
    raw = _manifest(
        migrations=[{"id": "m1", "up": {"rewrite": True}}],
        rollback="forward_only",
    )
    preflight = loader.install_preflight(raw)
    assert is_ok(preflight)
    assert preflight.value.rollback_mode == "forward_only"

    machine = loader.confirm_forward_only(
        plugin_id="research-corpus",
        correlation_id="corr-fo-1",
        principal=PrincipalClass.MACHINE,
    )
    assert is_refusal(machine)

    confirmed = loader.confirm_forward_only(
        plugin_id="research-corpus",
        correlation_id="corr-fo-1",
        principal=PrincipalClass.OPERATOR,
    )
    assert is_ok(confirmed)
    assert confirmed.value.correlation_id == "corr-fo-1"
    assert confirmed.value.fingerprint.startswith("fp1:sha256:")

    installed = loader.install(
        raw, activator=_activate, correlation_id="corr-install-fo"
    )
    assert is_ok(installed), installed
    assert installed.value.migration_report is not None
    assert installed.value.migration_report.rollback_mode == "forward_only"
    assert installed.value.migration_report.checkpoint.is_recovery_copy is False

    disabled = loader.disable("research-corpus")
    assert is_ok(disabled)
    assert disabled.value.scope_disposed is True
    assert disabled.value.data_intact is True
    assert disabled.value.rolled_back is False
    assert loader.get("research-corpus") is None

    refused_rollback = loader.rollback_plugin("research-corpus")
    assert is_refusal(refused_rollback)
    assert refused_rollback.context.get("signal") == "refuse-forward-only-rollback"


# --- daemon-core same rules ---------------------------------------------------


def test_daemon_core_targets_and_declared_down_path(tmp_path: Path) -> None:
    assert "journal" in DAEMON_CORE_MIGRATION_TARGETS
    assert "ledger" in DAEMON_CORE_MIGRATION_TARGETS
    assert "task_graph" in DAEMON_CORE_MIGRATION_TARGETS
    assert "mailbox" in DAEMON_CORE_MIGRATION_TARGETS
    assert "staging" in DAEMON_CORE_MIGRATION_TARGETS

    source = tmp_path / "src"
    dest = tmp_path / "dst"
    # Runner keys daemon-core snapshots by target name.
    snap = PluginDataSnapshot(
        plugin_id="journal",
        schema_version=1,
        records=({"row": 1},),
    )
    path = source / "journal" / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snap.to_bytes())

    declaration = DaemonCoreMigrationDeclaration(
        target="journal",
        migrations=({"id": "j1", "up": {"v": 2}, "down": {"v": 1}},),
    )
    runner = PluginMigrationRunner()
    report = runner.run_daemon_core_migration(
        declaration,
        source_root=source,
        destination_root=dest,
        correlation_id="corr-daemon-core-1",
    )
    assert is_ok(report), report
    assert report.value.owner == "daemon_core"
    assert report.value.stages_completed == MIGRATION_SEQUENCE
    assert report.value.checkpoint.is_recovery_copy is False


def test_daemon_core_forward_only_needs_confirm(tmp_path: Path) -> None:
    source = tmp_path / "src"
    dest = tmp_path / "dst"
    snap = PluginDataSnapshot(plugin_id="mailbox", schema_version=1, records=({"x": 1},))
    path = source / "mailbox" / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snap.to_bytes())

    declaration = DaemonCoreMigrationDeclaration(
        target="mailbox",
        migrations=({"id": "mb1", "up": {"rewrite": True}},),
        rollback="forward_only",
    )
    runner = PluginMigrationRunner()
    refused = runner.run_daemon_core_migration(
        declaration,
        source_root=source,
        destination_root=dest,
        correlation_id="corr-mb",
    )
    assert is_refusal(refused)
    assert refused.context.get("signal") == "unconfirmed-forward-only"

    confirm_key = "daemon-core:mailbox"
    confirmed = runner.confirm_forward_only(
        plugin_id=confirm_key,
        correlation_id="corr-mb-confirm",
        principal=PrincipalClass.OPERATOR,
    )
    assert is_ok(confirmed)
    report = runner.run_daemon_core_migration(
        declaration,
        source_root=source,
        destination_root=dest,
        correlation_id="corr-mb",
        plugin_id_alias=confirm_key,
    )
    assert is_ok(report), report


def test_lifecycle_migrate_enforces_down_or_forward_only(tmp_path: Path) -> None:
    source = tmp_path / "src"
    dest = tmp_path / "dst"
    from qma.daemon.persistence.lifecycle import StoreSnapshot

    snap = StoreSnapshot(store="journal", schema_version=1, records=({"a": 1},))
    path = source / "journal" / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snap.to_bytes())

    lifecycle = DaemonStoreLifecycle()
    # Without declaration args the legacy five-step path still runs.
    legacy = lifecycle.migrate(
        store="journal",
        source_root=source,
        destination_root=dest / "legacy",
    )
    assert is_ok(legacy), legacy

    bad_mode = lifecycle.migrate(
        store="journal",
        source_root=source,
        destination_root=dest / "b",
        rollback="not-a-mode",
    )
    assert is_refusal(bad_mode)

    with_down = lifecycle.migrate(
        store="journal",
        source_root=source,
        destination_root=dest / "c",
        down={"revert": True},
        correlation_id="corr-life-1",
    )
    assert is_ok(with_down), with_down
    assert with_down.value.stages_completed == MIGRATION_SEQUENCE


def test_lifecycle_failed_preflight_marks_checkpoint_not_recovery(tmp_path: Path) -> None:
    lifecycle = DaemonStoreLifecycle()
    refused = lifecycle.migrate(
        store="staging",
        source_root=tmp_path / "absent",
        destination_root=tmp_path / "dst",
        down={"ok": True},
        correlation_id="corr-life-fail",
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context.get("checkpoint_is_recovery_copy") is False


def test_reference_usage_example_runs() -> None:
    import runpy

    path = Path(__file__).resolve().parents[1] / "examples" / "plugin_migrations_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()

