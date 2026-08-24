"""Contained, no-follow file I/O for the impure orchestrator.

Reads resolve the path, refuse a leaf symlink, require a regular file inside
the intended root, cap the size, then open with ``O_NOFOLLOW`` where the
platform offers it. Exclusive writes use ``O_CREAT | O_EXCL | O_WRONLY``
plus the same containment and symlink refusal. JSONL append cannot use
``O_EXCL``; it still refuses a symlink, stays inside the fragment root, and
opens with ``O_APPEND | O_NOFOLLOW``.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import BinaryIO, Final

from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import storage

__all__ = [
    "MAX_BYTES",
    "MAX_JSONL_BYTES",
    "MAX_PROC_STATUS_BYTES",
    "append_bytes_no_follow",
    "open_write_handle",
    "read_contained_bytes",
    "read_contained_text",
    "write_bytes_exclusive_no_follow",
]

# Default ceiling on a single contained read (payload/result JSON). JSONL
# fragments and logs may be larger; /proc/<pid>/status is tiny.
MAX_BYTES: Final[int] = 1 << 20
MAX_JSONL_BYTES: Final[int] = 1 << 24
MAX_PROC_STATUS_BYTES: Final[int] = 1 << 16


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        offset += os.write(fd, view[offset:])


def _os_open_no_follow(
    path: Path,
    flags: int,
    *,
    contain_within: Path,
    field: str,
    must_exist: bool,
    mode: int = 0o600,
) -> Result[int]:
    """Open *path* after containment and a leaf-symlink refusal.

    Guards sit in this function with the ``os.open`` they protect: a symlink
    or an out-of-root realpath is refused, existing targets must be regular
    files, and the open always includes ``O_NOFOLLOW`` (and ``O_BINARY`` on
    Windows so JSONL stays LF-terminated). SKY-D215 is suppressed on the open
    only — it flags any tainted path at a filesystem sink with no guard
    escape, the same way registry persistence suppresses it at an equivalent
    bounded, no-follow open.
    """
    try:
        resolved = Path(os.path.realpath(path))
        root_real = Path(os.path.realpath(contain_within))
    except OSError as exc:
        return storage(
            field,
            "could not resolve a contained filesystem path",
            given=type(exc).__name__,
            path=str(path),
            root=str(contain_within),
        )
    if path.is_symlink() or not resolved.is_relative_to(root_real):
        return storage(
            field,
            "refusing to follow a symlink or a path that resolves outside the intended root",
            path=str(path),
            root=str(contain_within),
        )
    if must_exist and (path.is_symlink() or not path.is_file()):
        return storage(
            field,
            "refusing to read a path that is not a regular in-root file",
            path=str(path),
            root=str(contain_within),
        )
    if (must_exist or path.exists()) and not path.is_file():
        return storage(
            field,
            "refusing to open a path that is not a regular in-root file",
            path=str(path),
            root=str(contain_within),
        )
    try:
        # getattr keeps the "O_NOFOLLOW" token on this open so SKY-D324/D325
        # see the no-follow flag; Windows has no O_NOFOLLOW (value 0).
        fd = os.open(  # skylos: ignore[SKY-D215] contained, no-follow, exclusive-or-append
            path,
            flags | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
            mode,
        )
    except FileExistsError:
        return storage(
            field,
            "exclusive no-follow create found an existing path",
            given="FileExistsError",
            path=str(path),
            root=str(contain_within),
        )
    except OSError as exc:
        return storage(
            field,
            "contained no-follow open failed",
            given=type(exc).__name__,
            path=str(path),
            root=str(contain_within),
        )
    return Ok(fd)


def read_contained_bytes(
    path: Path,
    *,
    contain_within: Path,
    max_bytes: int = MAX_BYTES,
    field: str = "path",
) -> Result[bytes]:
    """Read a regular, in-root, non-symlink file, refusing an oversize read."""
    opened = _os_open_no_follow(
        path,
        os.O_RDONLY,
        contain_within=contain_within,
        field=field,
        must_exist=True,
    )
    if is_refusal(opened):
        return opened
    fd = opened.value
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return storage(
                field,
                "refusing to read a path that is not a regular in-root file",
                path=str(path),
                root=str(contain_within),
            )
        size = info.st_size
        if size > max_bytes:
            return storage(
                field,
                "refusing to read a file above the orchestrator size cap",
                path=str(path),
                size=size,
                max_bytes=max_bytes,
            )
        # /proc files often report st_size 0; read until EOF, still capped.
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
                return storage(
                    field,
                    "refusing to read a file above the orchestrator size cap",
                    path=str(path),
                    max_bytes=max_bytes,
                )
    except OSError as exc:
        return storage(
            field,
            "contained no-follow read failed",
            given=type(exc).__name__,
            path=str(path),
            root=str(contain_within),
        )
    finally:
        os.close(fd)
    return Ok(bytes(buf))


def read_contained_text(
    path: Path,
    *,
    contain_within: Path,
    max_bytes: int = MAX_BYTES,
    field: str = "path",
) -> Result[str]:
    """UTF-8 decode of :func:`read_contained_bytes`."""
    raw = read_contained_bytes(
        path, contain_within=contain_within, max_bytes=max_bytes, field=field
    )
    if is_refusal(raw):
        return raw
    try:
        return Ok(raw.value.decode("utf-8"))
    except UnicodeDecodeError:
        return storage(
            field,
            "contained file is not UTF-8 text",
            path=str(path),
        )


def write_bytes_exclusive_no_follow(
    path: Path,
    data: bytes,
    *,
    contain_within: Path,
    field: str = "path",
) -> Result[None]:
    """Create *path* exclusively and write *data*, never following a symlink."""
    opened = _os_open_no_follow(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        contain_within=contain_within,
        field=field,
        must_exist=False,
    )
    if is_refusal(opened):
        return opened
    fd = opened.value
    try:
        _write_all(fd, data)
        os.fsync(fd)
    except OSError as exc:
        return storage(
            field,
            "exclusive no-follow create of a contained file failed",
            given=type(exc).__name__,
            path=str(path),
            root=str(contain_within),
        )
    finally:
        os.close(fd)
    return Ok(None)


def append_bytes_no_follow(
    path: Path,
    data: bytes,
    *,
    contain_within: Path,
    field: str = "path",
) -> Result[None]:
    """Append *data* with fsync, refusing a symlink and an out-of-root path."""
    opened = _os_open_no_follow(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        contain_within=contain_within,
        field=field,
        must_exist=False,
    )
    if is_refusal(opened):
        return opened
    fd = opened.value
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return storage(
                field,
                "refusing to append through a path that is not a regular in-root file",
                path=str(path),
                root=str(contain_within),
            )
        _write_all(fd, data)
        os.fsync(fd)
    except OSError as exc:
        return storage(
            field,
            "contained no-follow append-with-fsync failed",
            given=type(exc).__name__,
            path=str(path),
            root=str(contain_within),
        )
    finally:
        os.close(fd)
    return Ok(None)


def open_write_handle(
    path: Path,
    *,
    contain_within: Path,
    append: bool,
    field: str = "path",
) -> Result[BinaryIO]:
    """Open a contained write handle. Exclusive create unless *append*."""
    flags = os.O_WRONLY | os.O_CREAT
    if append:
        flags |= os.O_APPEND
    else:
        flags |= os.O_EXCL
    opened = _os_open_no_follow(
        path,
        flags,
        contain_within=contain_within,
        field=field,
        must_exist=False,
    )
    if is_refusal(opened):
        return opened
    fd = opened.value
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            os.close(fd)
            return storage(
                field,
                "refusing to write a path that is not a regular in-root file",
                path=str(path),
                root=str(contain_within),
            )
        return Ok(os.fdopen(fd, "ab" if append else "wb"))
    except OSError as exc:
        os.close(fd)
        return storage(
            field,
            "contained no-follow write open failed",
            given=type(exc).__name__,
            path=str(path),
            root=str(contain_within),
        )
