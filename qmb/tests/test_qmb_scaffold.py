"""Tier-1 tests for the qmb distribution scaffold (Story 13.1)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import tomllib

import qmb

_QMB_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMB_ROOT / "src" / "qmb"
_HOMES = (
    "runloop",
    "config",
    "registryread",
    "execution",
    "data",
    "optimize",
    "robustness",
    "results",
    "ledger",
    "orchestrator",
    "doors/cli",
    "doors/api",
    "doors/mcp",
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
        "optuna",
        "qmf.venue",
    }
)
_BANNED_WORDS = re.compile(r"\b(engine|kernel|exam|plugin|snapshot)s?\b", re.IGNORECASE)
_QMF_BACKENDS = (
    "qmf-core",
    "qmf-registry",
    "qmf-data",
    "qmf-indicators",
    "qmf-structure",
    "qmf-risk",
)


def test_version_is_display_only_semver_0x() -> None:
    assert qmb.__version__ == "0.1.0"


def test_module_homes_exist() -> None:
    for home in _HOMES:
        path = _QMB_ROOT / home if home in {"examples", "tests"} else _SRC / home
        assert path.is_dir(), f"missing module home {home}: {path}"
    assert _HOMES[:-2] == qmb.STRUCTURAL_SEED


def test_one_wheel_declares_cli_script_and_pins() -> None:
    data = tomllib.loads((_QMB_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["scripts"] == {"qmb": "qmb.doors.cli:main"}
    deps = tuple(project["dependencies"])
    assert deps[:6] == _QMF_BACKENDS
    assert "qml" in deps
    assert "click==8.4.2" in deps
    assert "optuna==4.9.0" in deps
    assert "qmf-venue" not in deps
    entry = project.get("entry-points", {})
    assert "console_scripts" not in entry or "mcp" not in str(entry)


def test_mcp_door_is_scaffolded_not_shipped() -> None:
    assert qmb.MCP_SHIPPED is False
    from qmb.doors import mcp

    assert mcp.is_shipped() is False
    assert mcp.SHIPPED is False
    data = tomllib.loads((_QMB_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"].get("scripts", {})
    assert all("mcp" not in name for name in scripts)
    assert "mcp" not in qmb.__all__


def test_source_never_imports_banned_modules() -> None:
    violations: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        relative = path.relative_to(_SRC)
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
                banned = name in _BANNED_IMPORTS or any(
                    name.startswith(banned + ".") for banned in _BANNED_IMPORTS
                )
                if banned:
                    violations.append(f"{path}: imports {name}")
                if (name == "click" or name.startswith("click.")) and relative.parts[:2] != (
                    "doors",
                    "cli",
                ):
                    violations.append(f"{path}: click is CLI-door only")
    assert violations == []


def test_library_has_no_module_global_mutable_state() -> None:
    violations: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            targets: list[ast.expr] = []
            value: ast.expr | None = None
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
                value = node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets = [node.target]
                value = node.value
            if value is None:
                continue
            if any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
                continue
            if _is_mutable_literal(value):
                violations.append(f"{path}: module-global mutable {value.__class__.__name__}")
    assert violations == []


def test_source_avoids_banned_vocabulary() -> None:
    offenders: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if _BANNED_WORDS.search(text):
            offenders.append(str(path.relative_to(_SRC)))
    assert offenders == []


def _is_mutable_literal(value: ast.expr) -> bool:
    if isinstance(value, (ast.List, ast.Dict, ast.Set)):
        return True
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in {"list", "dict", "set"}
    )
