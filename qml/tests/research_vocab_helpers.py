"""Shared helpers for qml research vocabulary tests."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

import pytest
from qmf.core.refusal import Result, is_ok
from qml.research import DictionaryEntry, resolve_dictionary_entry

T = TypeVar("T")

FIXTURE_SEED = Path(__file__).resolve().parent / "fixtures" / "research-seed"
SWING_HIGH_PATH = "dictionary/market-structure-and-location/locations-and-structure.md"
_QML_RESEARCH = Path(__file__).resolve().parents[1] / "src" / "qml" / "research"


def ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def cited_bytes(relative: str) -> bytes:
    src = FIXTURE_SEED / relative
    if not src.is_file():
        pytest.fail(
            "AR-RES-10 requires fixtures/research-seed bytes copied from the "
            f"operator Stats tree — missing {relative}"
        )
    return src.read_bytes()


def path_of(locator: str) -> str:
    return locator.split("#", 1)[0]


def resolve(cited: bytes, file_path: str, entry_id: str | None = None) -> DictionaryEntry:
    if entry_id is None:
        return ok(resolve_dictionary_entry(cited, file_path=file_path))
    return ok(resolve_dictionary_entry(cited, file_path=file_path, entry_id=entry_id))


def swing_high() -> DictionaryEntry:
    return resolve(cited_bytes(SWING_HIGH_PATH), SWING_HIGH_PATH, "swing-high")


def import_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        return [node.module]
    return []


def is_open_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"


def name_is_banned(name: str, banned: frozenset[str]) -> bool:
    return name in banned or any(name.startswith(item + ".") for item in banned)


def node_ban_hits(path: Path, node: ast.AST, banned: frozenset[str]) -> list[str]:
    if is_open_call(node):
        return [f"{path}: open()"]
    return [
        f"{path}: imports {name}" for name in import_names(node) if name_is_banned(name, banned)
    ]


def file_ban_violations(path: Path, banned: frozenset[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        found.extend(node_ban_hits(path, node, banned))
    return found


def research_ban_violations(banned: frozenset[str]) -> list[str]:
    found: list[str] = []
    for path in sorted(_QML_RESEARCH.rglob("*.py")):
        found.extend(file_ban_violations(path, banned))
    return found


def class_names_in_research() -> list[str]:
    names: list[str] = []
    for path in _QML_RESEARCH.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names.extend(node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    return names
