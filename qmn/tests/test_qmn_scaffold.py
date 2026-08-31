"""Tier-1 scaffold gates for the qmn distribution (Story 24.1)."""

from __future__ import annotations

import ast
from pathlib import Path

import tomllib

import qmn

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_VENUE = _SRC / "venue"


def test_version_is_display_only_semver_0x() -> None:
    assert qmn.__version__ == "0.1.0"


def test_no_console_scripts() -> None:
    data = tomllib.loads((_QMN_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    assert not project.get("scripts"), "qmn ships no operator CLI entry point"
    entry = project.get("entry-points", {})
    assert "console_scripts" not in entry


def test_declared_dependencies_include_qmf_venue() -> None:
    data = tomllib.loads((_QMN_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = set(data["project"]["dependencies"])
    assert "qmf-core" in deps
    assert "qmf-venue" in deps


def test_only_venue_subpackage_imports_qmf_venue() -> None:
    violations: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        relative = path.relative_to(_SRC)
        under_venue = relative.parts and relative.parts[0] == "venue"
        for imported in _imported_modules(path):
            is_venue = imported == "qmf.venue" or imported.startswith("qmf.venue.")
            if is_venue and not under_venue:
                violations.append(f"{relative}: imports {imported}")
    assert violations == [], f"qmf.venue imports outside qmn.venue: {violations}"


def test_venue_subpackage_does_import_qmf_venue() -> None:
    imported: set[str] = set()
    for path in sorted(_VENUE.rglob("*.py")):
        imported |= _imported_modules(path)
    assert any(name == "qmf.venue" or name.startswith("qmf.venue.") for name in imported)


def test_no_spotware_or_twisted_imports() -> None:
    banned = ("twisted", "ctrader_open_api", "openapi_client", "spotware")
    violations: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        for imported in _imported_modules(path):
            root = imported.split(".", 1)[0].lower()
            if root in banned or any(token in imported.lower() for token in banned):
                violations.append(f"{path.relative_to(_SRC)}: {imported}")
    assert violations == [], f"banned SDK imports: {violations}"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names
