"""Story 49.1 — bind the seed corpus via PlainFileLibrarySource at root_path."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from qma.core.plugins import assert_no_daemon_import
from qma.daemon.knowledge import PlainFileLibrarySource, qmx_worktree_root, validate_seed_root_path
from qma.daemon.plugins import (
    DaemonPluginContext,
    DeskPluginRoster,
    PluginContextError,
    research_corpus_plugin_load_config,
)
from qmf.core import is_ok, is_refusal

PLUGIN = (
    Path(__file__).resolve().parents[3] / "plugins" / "research-corpus" / "daemon" / "plugin.py"
)
OPERATOR_SEED = Path(r"C:/Users/Mubarak/Desktop/Stats")
QMX_ROOT = Path(__file__).resolve().parents[4]


def _seed_tree(tmp_path: Path) -> Path:
    root = tmp_path / "seed-corpus"
    root.mkdir()
    (root / "README.md").write_text("seed corpus readme\n", encoding="utf-8")
    (root / "notes").mkdir()
    (root / "notes" / "layout.md").write_text("entry hypothesis hole F\n", encoding="utf-8")
    return root


def test_activate_binds_plain_file_library_source_not_two_file_stub(tmp_path: Path) -> None:
    seed = _seed_tree(tmp_path)
    roster = DeskPluginRoster(plugin_load_configs=research_corpus_plugin_load_config(seed))
    result = roster.activate()
    assert is_ok(result), result
    research = roster.loader.get("research-corpus")
    assert research is not None
    snap = research.context.snapshot()
    source = snap["singletons"][("KnowledgeSource", "strats")]
    assert isinstance(source, PlainFileLibrarySource)
    assert source.source_id == "strats"
    assert source.kind == "plain_file_library"
    assert source.root_path == seed
    assert snap["load_config"]["root_path"] == str(seed)

    plugin_text = PLUGIN.read_text(encoding="utf-8")
    assert "notes/liquidity.md" not in plugin_text
    assert "notes/session.md" not in plugin_text
    assert "StratsCorpus" not in plugin_text
    assert "class StratsCorpus" not in plugin_text
    assert "os.environ" not in plugin_text
    assert "getenv" not in plugin_text
    assert "STRATS" not in plugin_text


def test_root_path_homes_on_plugin_daemon_load_config(tmp_path: Path) -> None:
    seed = _seed_tree(tmp_path)
    os.environ["QMA_SEED_ROOT"] = str(seed)
    try:
        missing = DeskPluginRoster()
        refused = missing.activate()
        assert is_refusal(refused)
        assert "root_path" in str(refused.context.get("reason", refused))

        roster = DeskPluginRoster(plugin_load_configs=research_corpus_plugin_load_config(seed))
        result = roster.activate()
        assert is_ok(result), result
        loaded = roster.loader.get("research-corpus")
        assert loaded is not None
        source = loaded.context.snapshot()["singletons"][("KnowledgeSource", "strats")]
        assert isinstance(source, PlainFileLibrarySource)
        assert source.root_path == seed
    finally:
        os.environ.pop("QMA_SEED_ROOT", None)


def test_root_path_refuses_env_git_secret_and_qmb_homes(tmp_path: Path) -> None:
    ctx = DaemonPluginContext("research-corpus")
    with pytest.raises(PluginContextError, match="environment variable"):
        ctx.plain_file_library_source(root_path="$STATS_ROOT", source_id="strats")
    with pytest.raises(PluginContextError, match="venue secret"):
        ctx.plain_file_library_source(root_path="cred://seed/stats", source_id="strats")
    with pytest.raises(PluginContextError, match="qmb setting"):
        ctx.plain_file_library_source(root_path="qmb.seed_root", source_id="strats")

    worktree = qmx_worktree_root()
    assert worktree is not None
    git_path = worktree / "docs" / "AGENTS.md"
    refused_git = validate_seed_root_path(str(git_path))
    assert is_refusal(refused_git)
    assert "git path" in str(refused_git.context.get("reason", ""))

    seed = _seed_tree(tmp_path)
    accepted = validate_seed_root_path(str(seed))
    assert is_ok(accepted)
    assert accepted.value == seed


def test_snapshot_reads_configured_tree_and_does_not_copy_into_qmx(tmp_path: Path) -> None:
    seed = _seed_tree(tmp_path)
    roster = DeskPluginRoster(plugin_load_configs=research_corpus_plugin_load_config(seed))
    result = roster.activate()
    assert is_ok(result), result
    loaded = roster.loader.get("research-corpus")
    assert loaded is not None
    source = loaded.context.snapshot()["singletons"][("KnowledgeSource", "strats")]
    assert isinstance(source, PlainFileLibrarySource)
    snapped = source.snapshot()
    assert is_ok(snapped), snapped
    assert "README.md" in snapped.value.file_digests
    assert "notes/layout.md" in snapped.value.file_digests
    assert "notes/liquidity.md" not in snapped.value.file_digests
    assert "notes/session.md" not in snapped.value.file_digests
    assert not (QMX_ROOT / "Stats").exists()
    assert "Stats" not in {path.name for path in QMX_ROOT.iterdir()}


def test_write_is_refused_and_plugin_does_not_import_daemon(tmp_path: Path) -> None:
    seed = _seed_tree(tmp_path)
    ctx = DaemonPluginContext(
        "research-corpus",
        load_config={"root_path": str(seed)},
    )
    source = ctx.plain_file_library_source(
        root_path=str(seed),
        source_id="strats",
        kind="plain_file_library",
    )
    assert isinstance(source, PlainFileLibrarySource)
    refused = source.write({"hypothesis": "invented"})
    assert is_refusal(refused)
    assert refused.context["field"] == "write"
    assert (
        "read-only" in str(refused.context.get("reason", "")).lower()
        or "write" in str(refused.context.get("reason", "")).lower()
    )
    assert_no_daemon_import(PLUGIN.parent.parent)


def test_operator_seed_tree_snapshots_when_present() -> None:
    if not OPERATOR_SEED.is_dir():
        pytest.skip("operator seed tree not present")
    source = PlainFileLibrarySource(root_path=OPERATOR_SEED, source_id="strats")
    snapped = source.snapshot()
    assert is_ok(snapped), snapped
    assert snapped.value.source_id == "strats"
    assert "README.md" in snapped.value.file_digests
    assert not (QMX_ROOT / "Stats").exists()
