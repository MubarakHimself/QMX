"""Tier-1 tests for the qml distribution scaffold (Story 11.1)."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import Any, cast

import tomllib

import qml

_QML_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QML_ROOT / "src" / "qml"
_HOMES = (
    "declaration",
    "families",
    "logic",
    "footprint",
    "protocol",
    "conformance",
    "examples",
    "tests",
)
_BANNED_IMPORTS = frozenset(
    {
        "subprocess",
        "threading",
        "multiprocessing",
        "socket",
        "asyncio",
        "concurrent",
        "http",
        "urllib",
        "qmf.venue",
    }
)


def test_version_is_display_only_semver_0x() -> None:
    assert qml.__version__ == "0.1.0"


def test_module_homes_exist() -> None:
    for home in _HOMES:
        path = _QML_ROOT / home if home in {"examples", "tests"} else _SRC / home
        assert path.is_dir(), f"missing module home {home}: {path}"


def test_no_console_scripts() -> None:
    data = tomllib.loads((_QML_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    assert not project.get("scripts"), "qml ships no CLI entry point"
    entry = project.get("entry-points", {})
    assert "console_scripts" not in entry


def test_no_qml_dsl_files() -> None:
    offenders = [p for p in _QML_ROOT.rglob("*.qml") if ".venv" not in p.parts]
    assert offenders == [], f".qml DSL must not be revived: {offenders}"


def test_declared_dependencies_are_qmf_core_registry_risk_only() -> None:
    data = tomllib.loads((_QML_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = tuple(data["project"]["dependencies"])
    assert deps == ("qmf-core", "qmf-registry", "qmf-risk")


def test_source_never_imports_banned_modules() -> None:
    violations: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        # Host-owned runner is impure by law (DEC-0178): stdlib process
        # management lives there, never in the pure library surface.
        if "host" in path.relative_to(_SRC).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.append(node.module)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "open"
            ):
                violations.append(f"{path}: open()")
                continue
            for name in names:
                if name in _BANNED_IMPORTS or any(
                    name.startswith(banned + ".") for banned in _BANNED_IMPORTS
                ):
                    violations.append(f"{path}: imports {name}")
    assert violations == []


def test_plain_python_bot_runs_with_zero_qml_imports() -> None:
    path = Path(__file__).with_name("plain_research_bot.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(name == "qml" or name.startswith("qml.") for name in imported)
    spec = importlib.util.spec_from_file_location("plain_research_bot", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bot_cls = cast(Any, module).PlainResearchBot
    assert bot_cls().on_instant(object()) == ()
