"""Shared helpers for qml research vocabulary tests."""

from __future__ import annotations

import ast
import os
import stat
from pathlib import Path
from typing import TypeVar

import pytest
from qmf.core.refusal import Result, is_ok
from qml.research import DictionaryEntry, resolve_dictionary_entry

T = TypeVar("T")

FIXTURE_SEED = Path(__file__).resolve().parent / "fixtures" / "research-seed"
SWING_HIGH_PATH = "dictionary/market-structure-and-location/locations-and-structure.md"
_QML_RESEARCH = Path(__file__).resolve().parents[1] / "src" / "qml" / "research"
_MAX_READ_BYTES = 1 << 20  # 1 MiB


def ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _resolve_contained_paths(path: Path, contain_within: Path) -> tuple[Path, Path]:
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(contain_within))
    except OSError as exc:
        raise OSError(
            f"could not resolve a contained filesystem path ({path}): {type(exc).__name__}"
        ) from exc
    return resolved, root_real


def _assert_in_root_regular(path: Path, resolved: Path, root_real: Path) -> None:
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        raise OSError(f"refusing to follow a symlink or read outside the intended root ({path})")
    if not path.is_file() or path.is_symlink():
        raise OSError(f"refusing to read a path that is not a regular in-root file ({path})")


def _open_nofollow(path: Path) -> int:
    try:
        # getattr keeps the "O_NOFOLLOW" token on this open so SKY-D324/D325
        # see the no-follow flag; Windows has no O_NOFOLLOW (value 0).
        return os.open(  # skylos: ignore[SKY-D215] contained, no-follow read
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
        )
    except OSError as exc:
        raise OSError(f"contained no-follow open failed for {path} ({type(exc).__name__})") from exc


def _read_fd_capped(fd: int, path: Path, max_bytes: int) -> bytes:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        raise OSError(f"refusing to read a path that is not a regular in-root file ({path})")
    size = info.st_size
    if size > max_bytes:
        raise OSError(
            f"refusing to read a file above the size cap ({path}: {size} > {max_bytes})"
        )
    limit = max_bytes if size <= 0 else min(size, max_bytes)
    buf = bytearray()
    while len(buf) < limit:
        chunk = os.read(fd, limit - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    if size <= 0 and len(buf) >= max_bytes:
        extra = os.read(fd, 1)
        if extra:
            raise OSError(f"refusing to read a file above the size cap ({path}: > {max_bytes})")
    return bytes(buf)


def read_contained_bytes(
    path: Path,
    *,
    contain_within: Path,
    max_bytes: int = _MAX_READ_BYTES,
) -> bytes:
    """Read bytes from a regular, in-root, non-symlink file under *max_bytes*."""
    resolved, root_real = _resolve_contained_paths(path, contain_within)
    _assert_in_root_regular(path, resolved, root_real)
    fd = _open_nofollow(path)
    try:
        return _read_fd_capped(fd, path, max_bytes)
    finally:
        os.close(fd)


def read_contained(
    path: Path,
    *,
    contain_within: Path,
    max_bytes: int = _MAX_READ_BYTES,
) -> str:
    """Read UTF-8 text from a regular, in-root, non-symlink file under *max_bytes*."""
    raw = read_contained_bytes(path, contain_within=contain_within, max_bytes=max_bytes)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OSError(f"contained file is not UTF-8 text ({path})") from exc


def cited_bytes(relative: str) -> bytes:
    src = FIXTURE_SEED / relative
    if not src.is_file():
        pytest.fail(
            "AR-RES-10 requires fixtures/research-seed bytes copied from the "
            f"operator Stats tree — missing {relative}"
        )
    return read_contained_bytes(src, contain_within=FIXTURE_SEED)


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
    tree = ast.parse(
        read_contained(path, contain_within=_QML_RESEARCH),
        filename=str(path),
    )
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
        tree = ast.parse(
            read_contained(path, contain_within=_QML_RESEARCH),
            filename=str(path),
        )
        names.extend(node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    return names
