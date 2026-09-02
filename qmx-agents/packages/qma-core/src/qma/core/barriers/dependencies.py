"""QMA package dependency declarations and qmf-venue ban (FR-Q07; DEC-0347).

Static boundary constants for pyproject and import-graph checks. Unlisted
workspace edges are default-deny.
"""

from __future__ import annotations

import ast
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Final, cast

__all__ = [
    "FORBIDDEN_QMA_IMPORT_ROOTS",
    "FORBIDDEN_QMB_IMPORT_ROOTS",
    "QMA_CORE_ALLOWED_DEPS",
    "QMA_DAEMON_ALLOWED_DEPS",
    "QMA_PACKAGE_ALLOWED_DEPS",
    "QMA_WIRE_ALLOWED_DEPS",
    "DependencyBoundaryError",
    "assert_no_qmb_import",
    "assert_no_qmf_venue_import",
    "assert_package_deps_within",
    "declared_project_dependencies",
    "scan_forbidden_qma_imports",
    "scan_qmb_imports",
    "scan_qmf_venue_imports",
]


QMA_CORE_ALLOWED_DEPS: Final[frozenset[str]] = frozenset({"qmf-core"})

QMA_WIRE_ALLOWED_DEPS: Final[frozenset[str]] = frozenset({"qma-core", "qmf-core"})

QMA_DAEMON_ALLOWED_DEPS: Final[frozenset[str]] = frozenset(
    {
        "qma-core",
        "qma-wire",
        "qmf-core",
        "qmf-registry",
        "qmf-data",
        "qmf-risk",
        "tzdata",
    }
)

QMA_PACKAGE_ALLOWED_DEPS: Final[dict[str, frozenset[str]]] = {
    "qma-core": QMA_CORE_ALLOWED_DEPS,
    "qma-wire": QMA_WIRE_ALLOWED_DEPS,
    "qma-daemon": QMA_DAEMON_ALLOWED_DEPS,
}

# Import roots banned across every QMA package, worker half, and plugin tree.
FORBIDDEN_QMA_IMPORT_ROOTS: Final[frozenset[str]] = frozenset(
    {
        "qmf.venue",
        "qmf_venue",
        "qmb",
    }
)

# The QMB door is a runtime CLI/MCP interaction — no package-import edge (FR-Q55).
FORBIDDEN_QMB_IMPORT_ROOTS: Final[frozenset[str]] = frozenset({"qmb"})


class DependencyBoundaryError(ValueError):
    """Raised when a QMA dependency or import boundary is violated."""


def declared_project_dependencies(pyproject: Path) -> frozenset[str]:
    """Return the ``[project].dependencies`` package names from a pyproject."""
    data = cast(dict[str, object], tomllib.loads(pyproject.read_text(encoding="utf-8")))
    project = data.get("project")
    if not isinstance(project, dict):
        raise DependencyBoundaryError(f"{pyproject} has no [project] table")
    project_table = cast(dict[str, object], project)
    raw_obj: object = project_table.get("dependencies", [])
    if not isinstance(raw_obj, list):
        raise DependencyBoundaryError(f"{pyproject} dependencies must be a list")
    raw_list = cast(list[object], raw_obj)
    names: set[str] = set()
    for entry in raw_list:
        if not isinstance(entry, str):
            raise DependencyBoundaryError(f"non-string dependency entry in {pyproject}")
        name = entry.split(";", 1)[0].strip()
        for sep in ("==", ">=", "<=", "~=", "!=", ">", "<", "["):
            if sep in name:
                name = name.split(sep, 1)[0].strip()
                break
        names.add(name)
    return frozenset(names)


def assert_package_deps_within(package_name: str, pyproject: Path) -> None:
    """Refuse undeclared or out-of-allowlist project dependencies."""
    allowed = QMA_PACKAGE_ALLOWED_DEPS.get(package_name)
    if allowed is None:
        raise DependencyBoundaryError(f"unknown QMA package {package_name!r}")
    declared = declared_project_dependencies(pyproject)
    extras = declared - allowed
    missing = allowed - declared
    if extras or missing:
        raise DependencyBoundaryError(
            f"{package_name} dependency declaration must equal {sorted(allowed)}; "
            f"declared={sorted(declared)}; extras={sorted(extras)}; missing={sorted(missing)}"
        )


def _iter_py_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix == ".py":
        yield root
        return
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _import_is_forbidden(module: str, roots: frozenset[str]) -> bool:
    if module in roots:
        return True
    return any(module == root or module.startswith(f"{root}.") for root in roots)


def scan_forbidden_qma_imports(
    root: Path,
    *,
    roots: frozenset[str] = FORBIDDEN_QMA_IMPORT_ROOTS,
) -> tuple[str, ...]:
    """Return source paths under ``root`` that import a forbidden package root."""
    hits: list[str] = []
    for path in _iter_py_files(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _import_is_forbidden(alias.name, roots):
                        hits.append(f"{path}:{node.lineno}:import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if _import_is_forbidden(module, roots):
                    hits.append(f"{path}:{node.lineno}:from {module}")
                elif (
                    "qmf.venue" in roots
                    and module == "qmf"
                    and any(alias.name == "venue" for alias in node.names)
                ):
                    hits.append(f"{path}:{node.lineno}:from qmf import venue")
    return tuple(dict.fromkeys(hits))


def scan_qmf_venue_imports(root: Path) -> tuple[str, ...]:
    """Return source paths under ``root`` that import ``qmf.venue`` / ``qmf_venue``."""
    return scan_forbidden_qma_imports(
        root,
        roots=frozenset({"qmf.venue", "qmf_venue"}),
    )


def scan_qmb_imports(root: Path) -> tuple[str, ...]:
    """Return source paths under ``root`` that import the ``qmb`` package."""
    return scan_forbidden_qma_imports(root, roots=FORBIDDEN_QMB_IMPORT_ROOTS)


def assert_no_qmf_venue_import(root: Path) -> None:
    """Reject any QMA tree that imports ``qmf-venue``."""
    hits = scan_qmf_venue_imports(root)
    if hits:
        raise DependencyBoundaryError(
            "no QMA package, worker, or plugin may import qmf-venue; "
            f"offending sites: {', '.join(hits)}"
        )


def assert_no_qmb_import(root: Path) -> None:
    """Reject any QMA tree that imports ``qmb`` (the door is runtime-only)."""
    hits = scan_qmb_imports(root)
    if hits:
        raise DependencyBoundaryError(
            "no QMA package, worker, or plugin may import qmb; "
            "the qmb door is a runtime CLI or MCP interaction (CT-47; FR-Q55); "
            f"offending sites: {', '.join(hits)}"
        )
