"""Contained filesystem reads for qml research tests (SKY-D324 / SKY-D325)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

_MAX_READ_BYTES = 1 << 20  # 1 MiB


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
