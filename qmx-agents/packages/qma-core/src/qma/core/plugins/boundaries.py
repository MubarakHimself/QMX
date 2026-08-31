"""Import and definitions-only boundary checks (FR-Q03; DEC-0335, DEC-0347).

``qma-core`` stays definitions only — no running or writing. Desk packages
import contribution types from ``qma-core`` and never from ``qma-daemon``.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path
from typing import Final

__all__ = [
    "FORBIDDEN_ATTR_CALLS",
    "FORBIDDEN_IMPORT_MODULES",
    "FORBIDDEN_NAME_CALLS",
    "BoundaryError",
    "assert_core_definitions_only",
    "assert_no_daemon_import",
    "scan_daemon_imports",
    "scan_forbidden_runtime_calls",
]

FORBIDDEN_IMPORT_MODULES: Final[frozenset[str]] = frozenset(
    {
        "subprocess",
        "socket",
        "asyncio",
        "http.client",
        "urllib.request",
        "pathlib",
        "tempfile",
        "shutil",
        "mmap",
        "multiprocessing",
        "selectors",
    }
)

FORBIDDEN_NAME_CALLS: Final[frozenset[str]] = frozenset({"open"})

FORBIDDEN_ATTR_CALLS: Final[frozenset[str]] = frozenset(
    {
        "write_text",
        "write_bytes",
        "writelines",
        "mkdir",
        "touch",
        "unlink",
        "symlink_to",
        "hardlink_to",
        "Popen",
        "urlopen",
        "create_connection",
        "system",
        "execv",
        "execve",
        "fork",
        "listen",
        "bind",
        "connect",
    }
)


class BoundaryError(ValueError):
    """Raised when an import or definitions-only boundary is violated."""


def _iter_py_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix == ".py":
        yield root
        return
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def scan_daemon_imports(root: Path) -> tuple[str, ...]:
    """Return source paths under ``root`` that import ``qma.daemon``."""
    hits: list[str] = []
    for path in _iter_py_files(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "qma.daemon" or alias.name.startswith("qma.daemon."):
                        hits.append(str(path))
                        break
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                from_daemon = module == "qma.daemon" or module.startswith("qma.daemon.")
                from_qma_daemon = module == "qma" and any(
                    alias.name == "daemon" for alias in node.names
                )
                if from_daemon or from_qma_daemon:
                    hits.append(str(path))
    return tuple(dict.fromkeys(hits))


def assert_no_daemon_import(root: Path) -> None:
    """Reject a desk package (or any tree) that imports ``qma-daemon``."""
    hits = scan_daemon_imports(root)
    if hits:
        raise BoundaryError(
            f"desk package must not import qma-daemon; offending files: {', '.join(hits)}"
        )


def scan_forbidden_runtime_calls(root: Path) -> tuple[str, ...]:
    """Return ``qma-core`` source paths that appear to run or write."""
    hits: list[str] = []
    for path in _iter_py_files(root):
        # Boundary scanners hold the forbidden sets / path walks themselves.
        if path.name in {"boundaries.py", "dependencies.py"}:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".", 1)[0]
                    full = alias.name
                    if full in FORBIDDEN_IMPORT_MODULES or top in FORBIDDEN_IMPORT_MODULES:
                        hits.append(f"{path}:{node.lineno}:import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                top = module.split(".", 1)[0] if module else ""
                if module in FORBIDDEN_IMPORT_MODULES or top in FORBIDDEN_IMPORT_MODULES:
                    hits.append(f"{path}:{node.lineno}:from {module}")
            elif isinstance(node, ast.Call):
                func = node.func
                name: str | None = None
                if isinstance(func, ast.Name):
                    name = func.id
                    if name in FORBIDDEN_NAME_CALLS:
                        hits.append(f"{path}:{node.lineno}:{name}")
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                    if name in FORBIDDEN_ATTR_CALLS:
                        hits.append(f"{path}:{node.lineno}:{name}")
    return tuple(hits)


def assert_core_definitions_only(root: Path) -> None:
    """Reject a ``qma-core`` tree that runs or writes."""
    hits = scan_forbidden_runtime_calls(root)
    if hits:
        raise BoundaryError(
            "qma-core must stay definitions only (no running or writing); "
            f"offending sites: {', '.join(hits)}"
        )
