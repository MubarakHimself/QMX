"""Workspace-root tier-1 scaffold checks (AR-Q06, AR-Q07, AR-Q08)."""

from __future__ import annotations

import json
from pathlib import Path

from qma.core.plugins import DESK_PLUGIN_PACK_DESKS, DESK_PLUGIN_PACK_IDS, parse_plugin_manifest

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
PACKS = DESK_PLUGIN_PACK_IDS
HALF_DIRS = ("daemon", "worker", "ui", "skills", "graphs", "migrations")


def test_desk_plugin_topology() -> None:
    assert sorted(p.name for p in PLUGINS.iterdir() if p.is_dir()) == sorted(PACKS)
    for pack in PACKS:
        root = PLUGINS / pack
        assert (root / "manifest.json").is_file()
        for half in HALF_DIRS:
            assert (root / half).is_dir()
        assert (root / "daemon" / "plugin.py").is_file()
        raw = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        manifest = parse_plugin_manifest(raw)
        assert manifest.id == pack
        assert manifest.desk == DESK_PLUGIN_PACK_DESKS[pack]
        assert manifest.entrypoint == "daemon.plugin:activate"
        assert manifest.contributions


def test_qma_ui_contract_is_deferred_stub_only() -> None:
    stub = ROOT / "packages" / "qma-ui-contract"
    assert stub.is_dir()
    assert (stub / "STUB.md").is_file()
    # Deferred exclusion: not a workspace member and ships no UI package source.
    assert not (stub / "src").exists()
    assert not (stub / "pyproject.toml").exists()


def test_examples_and_tests_roots_exist() -> None:
    assert (ROOT / "examples").is_dir()
    assert (ROOT / "tests").is_dir()
