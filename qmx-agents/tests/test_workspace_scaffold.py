"""Workspace-root tier-1 scaffold checks (AR-Q06, AR-Q07, AR-Q08)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
PACKS = (
    "research-corpus",
    "analysis-backtest",
    "dev-factory",
    "trading-readonly",
    "pm-coordination",
)
HALF_DIRS = ("daemon", "worker", "ui", "skills", "graphs", "migrations")


def test_desk_plugin_topology() -> None:
    assert sorted(p.name for p in PLUGINS.iterdir() if p.is_dir()) == sorted(PACKS)
    for pack in PACKS:
        root = PLUGINS / pack
        assert (root / "manifest.json").is_file()
        for half in HALF_DIRS:
            assert (root / half).is_dir()


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
