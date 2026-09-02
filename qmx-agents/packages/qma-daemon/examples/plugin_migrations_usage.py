"""L27 reference usage: reversible and forward-only plugin migrations (FR-Q69)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from qma.core.plugins import PluginContext, parse_plugin_manifest
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.plugins import (
    CHECKPOINT_IS_RECOVERY_COPY,
    PLUGIN_INSTALL_PREFLIGHT_QUERY,
    REVERSIBLE_BY_DOWN,
    DaemonPluginContext,
    PluginDataSnapshot,
    PluginLoader,
    PluginMigrationRunner,
)
from qmf.core import is_ok, is_refusal
from qmf.data.verify import MIGRATION_SEQUENCE


def _activate(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("search", {"name": "search"})


def main() -> None:
    empty = parse_plugin_manifest(
        {
            "id": "research-corpus",
            "version": "0.1.0",
            "qma_api": "0.1.0",
            "desk": "research",
            "entrypoint": "research_corpus.activate",
            "migrations": [],
        }
    )
    assert empty.migrations == ()
    assert empty.rollback is None

    runner = PluginMigrationRunner()
    preflight = runner.install_preflight(
        {
            "id": "research-corpus",
            "version": "0.2.0",
            "qma_api": "0.1.0",
            "desk": "research",
            "entrypoint": "research_corpus.activate",
            "contributions": [{"point": "tool", "local_id": "search"}],
            "migrations": [{"id": "m1", "up": {"add": "col"}, "down": {"drop": "col"}}],
        }
    )
    assert is_ok(preflight)
    assert preflight.value.query == PLUGIN_INSTALL_PREFLIGHT_QUERY
    assert preflight.value.rollback_mode == REVERSIBLE_BY_DOWN

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "src"
        dest = root / "dst"
        snap = PluginDataSnapshot(
            plugin_id="research-corpus",
            schema_version=1,
            records=({"n": 1},),
        )
        path = source / "research-corpus" / "snapshot.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(snap.to_bytes())

        manifest = parse_plugin_manifest(
            {
                "id": "research-corpus",
                "version": "0.2.0",
                "qma_api": "0.1.0",
                "desk": "research",
                "entrypoint": "research_corpus.activate",
                "contributions": [{"point": "tool", "local_id": "search"}],
                "migrations": [
                    {"id": "m1", "up": {"add": "col"}, "down": {"drop": "col"}}
                ],
            }
        )
        report = runner.run_plugin_migrations(
            manifest,
            source_root=source,
            destination_root=dest,
            correlation_id="corr-demo",
        )
        assert is_ok(report)
        assert report.value.stages_completed == MIGRATION_SEQUENCE
        assert report.value.checkpoint.is_recovery_copy is CHECKPOINT_IS_RECOVERY_COPY

        fo_raw = {
            "id": "research-corpus",
            "version": "0.3.0",
            "qma_api": "0.1.0",
            "desk": "research",
            "entrypoint": "research_corpus.activate",
            "contributions": [{"point": "tool", "local_id": "search"}],
            "migrations": [{"id": "m2", "up": {"rewrite": True}}],
            "rollback": "forward_only",
        }
        loader = PluginLoader(
            migration_source_root=dest,
            migration_destination_root=root / "dst2",
        )
        assert (dest / "research-corpus" / "snapshot.json").is_file()
        assert is_ok(
            loader.confirm_forward_only(
                plugin_id="research-corpus",
                correlation_id="corr-fo-demo",
                principal=PrincipalClass.OPERATOR,
            )
        )
        installed = loader.install(
            fo_raw, activator=_activate, correlation_id="corr-fo-install"
        )
        assert is_ok(installed)
        disabled = loader.disable("research-corpus")
        assert is_ok(disabled)
        assert disabled.value.data_intact is True
        assert disabled.value.rolled_back is False
        assert is_refusal(loader.rollback_plugin("research-corpus"))


if __name__ == "__main__":
    main()
