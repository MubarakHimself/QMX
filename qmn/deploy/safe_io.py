"""Contained, no-follow file I/O for the deploy toolkit (SKY-D324 / SKY-D325).

Writes stay inside ``contain_within``, refuse a leaf symlink at the destination,
and create via a sibling temp with ``O_CREAT | O_EXCL | O_WRONLY`` plus
``O_NOFOLLOW`` where the platform offers it, then ``os.replace`` onto the
destination so a crash cannot delete a previous plan between unlink and create.
Reads open with ``O_RDONLY | O_NOFOLLOW``, require a regular in-root file under
a 1 MiB size cap, and UTF-8 decode the bytes.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Final

__all__ = [
    "MAX_READ_BYTES",
    "read_text_contained",
    "write_bytes_exclusive_no_follow",
    "write_text_exclusive_no_follow",
]

MAX_READ_BYTES: Final[int] = 1 << 20  # 1 MiB


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        offset += os.write(fd, view[offset:])


def write_bytes_exclusive_no_follow(
    path: Path,
    data: bytes,
    *,
    contain_within: Path,
) -> None:
    """Create *path* via a sibling temp and replace, never following a symlink."""
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(contain_within))
    except OSError as exc:
        raise OSError(
            f"could not resolve a contained filesystem path ({path}): {type(exc).__name__}"
        ) from exc
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        raise OSError(f"refusing to follow a symlink or write outside the intended root ({path})")
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise OSError(f"refusing to replace a non-regular in-root path ({path})")

    tmp = path.parent / f".{path.name}.write-{os.getpid()}"
    try:
        tmp_resolved = Path(os.path.realpath(tmp))
    except OSError as exc:
        raise OSError(
            f"could not resolve a contained filesystem path ({tmp}): {type(exc).__name__}"
        ) from exc
    if tmp.is_symlink() or not tmp_resolved.is_relative_to(root_real):
        raise OSError(f"refusing to follow a symlink or write outside the intended root ({tmp})")
    if tmp.exists() or tmp.is_symlink():
        if tmp.is_dir() and not tmp.is_symlink():
            raise OSError(f"refusing to replace a non-regular in-root path ({tmp})")
        tmp.unlink()
    try:
        # getattr keeps the "O_NOFOLLOW" token on this open so SKY-D324 sees
        # the no-follow flag; Windows has no O_NOFOLLOW (value 0).
        fd = os.open(  # skylos: ignore[SKY-D215] contained, no-follow, exclusive create
            tmp,
            os.O_CREAT
            | os.O_EXCL
            | os.O_WRONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_BINARY", 0),
            0o600,
        )
    except OSError as exc:
        raise OSError(
            f"exclusive no-follow create failed for {tmp} ({type(exc).__name__})"
        ) from exc
    try:
        try:
            _write_all(fd, data)
        finally:
            os.close(fd)
        if path.is_symlink():
            raise OSError(
                f"refusing to follow a symlink or write outside the intended root ({path})"
            )
        os.replace(tmp, path)
    except OSError:
        if tmp.exists() or tmp.is_symlink():
            tmp.unlink(missing_ok=True)
        raise


def write_text_exclusive_no_follow(
    path: Path,
    text: str,
    *,
    contain_within: Path,
) -> None:
    """UTF-8 wrapper around :func:`write_bytes_exclusive_no_follow`."""
    write_bytes_exclusive_no_follow(path, text.encode("utf-8"), contain_within=contain_within)


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
            f"could not resolve a contained filesystem path ({path}): {type(exc).__name__}"
        ) from exc
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        raise OSError(f"refusing to follow a symlink or read outside the intended root ({path})")
    try:
        # getattr keeps the "O_NOFOLLOW" token on this open so SKY-D324/D325
        # see the no-follow flag; Windows has no O_NOFOLLOW (value 0).
        fd = os.open(  # skylos: ignore[SKY-D215] contained, no-follow read
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
        )
    except OSError as exc:
        raise OSError(f"contained no-follow open failed for {path} ({type(exc).__name__})") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError(f"refusing to read a path that is not a regular in-root file ({path})")
        size = info.st_size
        if size > max_bytes:
            raise OSError(
                f"refusing to read a file above the size cap ({path}: {size} > {max_bytes})"
            )
        # st_size 0 can be a real empty file or a special file; still cap the read.
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
    finally:
        os.close(fd)
    try:
        return bytes(buf).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OSError(f"contained file is not UTF-8 text ({path})") from exc
