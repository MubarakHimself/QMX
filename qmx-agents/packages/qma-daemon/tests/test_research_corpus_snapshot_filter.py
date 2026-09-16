"""Story 49.2 — AD-4 snapshot include/exclude is research-corpus plugin config."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.daemon.knowledge import PlainFileLibrarySource
from qma.daemon.plugins import DeskPluginRoster, research_corpus_plugin_load_config
from qmf.core import is_ok

PLUGIN = (
    Path(__file__).resolve().parents[3] / "plugins" / "research-corpus" / "daemon" / "plugin.py"
)
ADAPTER = (
    Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "knowledge" / "plain_file.py"
)
QMA_CORE = Path(__file__).resolve().parents[2] / "qma-core" / "src" / "qma" / "core"
OPERATOR_SEED = Path(r"C:/Users/Mubarak/Desktop/Stats")

AD4_INCLUDE = (
    "README.md",
    "STRATS-BUILD-STATE.md",
    "schema/",
    "dictionary/",
    "strategies/",
    "sources/",
    "knowledge/",
    "lineage/",
    "catalog/",
    "IDEA.md",
)
AD4_EXCLUDE = (
    ".hermes/",
    ".obsidian/",
    "backend/strats.sqlite",
    "__pycache__/",
    "backend/*.py",
)

_LAYOUT_TOKENS = (
    "STRATS-BUILD-STATE.md",
    "backend/strats.sqlite",
    "backend/*.py",
)


def _ad4_tree(tmp_path: Path) -> Path:
    root = tmp_path / "seed-corpus"
    root.mkdir()
    (root / "README.md").write_text("seed readme\n", encoding="utf-8")
    (root / "STRATS-BUILD-STATE.md").write_text("build state\n", encoding="utf-8")
    (root / "IDEA.md").write_text("idea\n", encoding="utf-8")
    (root / "STRATS-GROUND-STATE.md").write_text("ground state\n", encoding="utf-8")
    for folder in (
        "schema",
        "dictionary",
        "strategies",
        "sources",
        "knowledge",
        "lineage",
        "catalog",
    ):
        (root / folder).mkdir()
        (root / folder / "note.md").write_text(f"{folder} note\n", encoding="utf-8")
    (root / "schema" / "__pycache__").mkdir()
    (root / "schema" / "__pycache__" / "mod.pyc").write_bytes(b"pyc")
    backend = root / "backend"
    backend.mkdir()
    (backend / "strats.sqlite").write_bytes(b"sqlite-bytes")
    (backend / "rebuild.py").write_text("print('derived')\n", encoding="utf-8")
    (backend / "README.md").write_text("backend readme\n", encoding="utf-8")
    (root / ".obsidian").mkdir()
    (root / ".obsidian" / "workspace.json").write_text("{}\n", encoding="utf-8")
    (root / ".hermes").mkdir()
    (root / ".hermes" / "cache.bin").write_bytes(b"cache")
    (root / "notes").mkdir()
    (root / "notes" / "extra.md").write_text("outside include\n", encoding="utf-8")
    return root


def _activate(root: Path, **extra: object) -> PlainFileLibrarySource:
    config: dict[str, object] = {"root_path": str(root)}
    config.update(extra)
    roster = DeskPluginRoster(plugin_load_configs={"research-corpus": config})
    result = roster.activate()
    assert is_ok(result), result
    loaded = roster.loader.get("research-corpus")
    assert loaded is not None
    source = loaded.context.snapshot()["singletons"][("KnowledgeSource", "strats")]
    assert isinstance(source, PlainFileLibrarySource)
    return source


def test_plugin_config_carries_ad4_include_exclude(tmp_path: Path) -> None:
    source = _activate(_ad4_tree(tmp_path))
    assert source.include == AD4_INCLUDE
    assert source.exclude == AD4_EXCLUDE
    assert source.declaration()["hardcoded_layout"] is False
    plugin_text = PLUGIN.read_text(encoding="utf-8")
    for token in AD4_INCLUDE + AD4_EXCLUDE:
        assert token in plugin_text


def test_load_config_include_exclude_override_defaults(tmp_path: Path) -> None:
    root = _ad4_tree(tmp_path)
    source = _activate(root, include=["README.md"], exclude=["IDEA.md"])
    assert source.include == ("README.md",)
    snapped = source.snapshot()
    assert is_ok(snapped), snapped
    assert set(snapped.value.file_digests) == {"README.md"}


def test_snapshot_hashes_include_set_and_skips_derived(tmp_path: Path) -> None:
    source = _activate(_ad4_tree(tmp_path))
    snapped = source.snapshot()
    assert is_ok(snapped), snapped
    digests = snapped.value.file_digests
    assert "README.md" in digests
    assert "STRATS-BUILD-STATE.md" in digests
    assert "IDEA.md" in digests
    assert "schema/note.md" in digests
    assert "dictionary/note.md" in digests
    assert "strategies/note.md" in digests
    assert "sources/note.md" in digests
    assert "knowledge/note.md" in digests
    assert "lineage/note.md" in digests
    assert "catalog/note.md" in digests
    assert "backend/strats.sqlite" not in digests
    assert "backend/rebuild.py" not in digests
    assert "backend/README.md" not in digests
    assert "schema/__pycache__/mod.pyc" not in digests
    assert "STRATS-GROUND-STATE.md" not in digests
    assert "notes/extra.md" not in digests
    assert all(".obsidian" not in path for path in digests)
    assert all(".hermes" not in path for path in digests)
    assert all("__pycache__" not in path for path in digests)


def test_plain_file_stays_layout_agnostic_without_plugin_lists(tmp_path: Path) -> None:
    root = _ad4_tree(tmp_path)
    unfiltered = PlainFileLibrarySource(root_path=root, source_id="strats")
    assert unfiltered.include == ()
    assert unfiltered.exclude == ()
    snapped = unfiltered.snapshot()
    assert is_ok(snapped), snapped
    digests = snapped.value.file_digests
    assert "notes/extra.md" in digests
    assert "backend/strats.sqlite" in digests
    assert "backend/rebuild.py" in digests
    assert "schema/__pycache__/mod.pyc" in digests
    assert "STRATS-GROUND-STATE.md" in digests
    assert all(".obsidian" not in path for path in digests)
    assert all(".hermes" not in path for path in digests)


def test_one_production_adapter_sqlite_does_not_enter_snapshot_ref(tmp_path: Path) -> None:
    root = _ad4_tree(tmp_path)
    production = _activate(root)
    unfiltered = PlainFileLibrarySource(root_path=root, source_id="strats")
    produced = production.snapshot()
    other = unfiltered.snapshot()
    assert is_ok(produced), produced
    assert is_ok(other), other
    assert "backend/strats.sqlite" not in produced.value.file_digests
    assert "backend/strats.sqlite" in other.value.file_digests
    assert produced.value.id != other.value.id
    assert isinstance(production, PlainFileLibrarySource)
    assert isinstance(unfiltered, PlainFileLibrarySource)


def test_stats_include_list_is_not_hardcoded_in_core_or_adapter() -> None:
    adapter = ADAPTER.read_text(encoding="utf-8")
    for token in _LAYOUT_TOKENS:
        assert token not in adapter
    hits: list[str] = []
    for path in QMA_CORE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in _LAYOUT_TOKENS):
            hits.append(str(path.relative_to(QMA_CORE)))
    assert hits == []


def test_operator_seed_sqlite_and_obsidian_are_outside_snapshot_ref() -> None:
    if not OPERATOR_SEED.is_dir():
        pytest.skip("operator seed tree not present")
    roster = DeskPluginRoster(plugin_load_configs=research_corpus_plugin_load_config(OPERATOR_SEED))
    result = roster.activate()
    assert is_ok(result), result
    loaded = roster.loader.get("research-corpus")
    assert loaded is not None
    source = loaded.context.snapshot()["singletons"][("KnowledgeSource", "strats")]
    assert isinstance(source, PlainFileLibrarySource)
    snapped = source.snapshot()
    assert is_ok(snapped), snapped
    digests = snapped.value.file_digests
    assert "README.md" in digests
    assert "STRATS-BUILD-STATE.md" in digests
    assert "IDEA.md" in digests
    assert "backend/strats.sqlite" not in digests
    assert "STRATS-GROUND-STATE.md" not in digests
    assert all(not path.startswith("backend/") or not path.endswith(".py") for path in digests)
    assert all(".obsidian" not in path for path in digests)
    assert all(".hermes" not in path for path in digests)
    assert all("__pycache__" not in path for path in digests)
