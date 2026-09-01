"""Contained, no-follow file I/O for the deploy toolkit (SKY-D324 / SKY-D325).

Writes refuse a leaf symlink, stay inside ``contain_within``, and create with
``O_CREAT | O_EXCL | O_WRONLY`` plus ``O_NOFOLLOW`` where the platform offers
it. An existing regular file at the destination is unlinked first so plan and
record re-writes stay exclusive. Reads require a regular in-root non-symlink
file under a 1 MiB size cap.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

__all__ = [
    "MAX_READ_BYTES",
    "read_text_contained",
    "write_text_exclusive_no_follow",
]

MAX_READ_BYTES: Final[int] = 1 << 20  # 1 MiB


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        offset += os.write(fd, view[offset:])


def write_text_exclusive_no_follow(
    path: Path,
    text: str,
    *,
    contain_within: Path,
) -> None:
    """Create *path* exclusively and write UTF-8 *text*, never following a symlink."""
    data = text.encode("utf-8")
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(contain_within))
    except OSError as exc:
        raise OSError(
            f"could not resolve a contained filesystem path ({path}): "
            f"{type(exc).__name__}"
        ) from exc
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        raise OSError(
            "refusing to follow a symlink or write outside the intended root "
            f"({path})"
        )
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise OSError(
                f"refusing to replace a non-regular in-root path ({path})"
            )
        path.unlink()
    try:
        # getattr keeps the "O_NOFOLLOW" token on this open so SKY-D324 sees
        # the no-follow flag; Windows has no O_NOFOLLOW (value 0).
        fd = os.open(  # skylos: ignore[SKY-D215] contained, no-follow, exclusive create
            path,
            os.O_CREAT
            | os.O_EXCL
            | os.O_WRONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_BINARY", 0),
            0o600,
        )
    except OSError as exc:
        raise OSError(
            f"exclusive no-follow create failed for {path} ({type(exc).__name__})"
        ) from exc
    try:
        _write_all(fd, data)
    finally:
        os.close(fd)


def read_text_contained(
    path: Path,
    *,
    contain_within: Path,
    max_bytes: int = MAX_READ_BYTES,
) -> str:
    """Read UTF-8 text from a regular, in-root, non-symlink file under *max_bytes*."""
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(contain_within))
    except OSError as exc:
        raise OSError(
            f"could not resolve a contained filesystem path ({path}): "
            f"{type(exc).__name__}"
        ) from exc
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        raise OSError(
            "refusing to follow a symlink or read outside the intended root "
            f"({path})"
        )
    if not path.is_file():
        raise OSError(
            f"refusing to read a path that is not a regular in-root file ({path})"
        )
    size = path.stat().st_size
    if size > max_bytes:
        raise OSError(
            f"refusing to read a file above the size cap ({path}: {size} > {max_bytes})"
        )
    return path.read_text(encoding="utf-8")
