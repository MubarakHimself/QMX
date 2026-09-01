"""Cross-process sole-writer lock for the daemon persistence root (FR-Q22; AD-6).

Uses an atomic ``O_CREAT | O_EXCL`` lock file — the same discipline as qmf-data's
JSONL ``.writer`` hold — so a second daemon or writer is refused before it can
open a writable SQLite connection or append path.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from qmf.core import Ok, Result
from qmf.data.store.refusals import policy_rejection, storage_failure

__all__ = ["DAEMON_LOCK_NAME", "DaemonWriterLock", "WriterLockToken"]

DAEMON_LOCK_NAME = ".daemon_writer"


@dataclass(frozen=True, slots=True)
class WriterLockToken:
    """Identity stamped into the sole-writer lock file."""

    machine: str
    role: str
    boot_epoch_id: str
    pid: int

    def encode(self) -> str:
        return json.dumps(
            {
                "machine": self.machine,
                "role": self.role,
                "boot_epoch_id": self.boot_epoch_id,
                "pid": self.pid,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def decode(cls, raw: str) -> WriterLockToken | None:
        try:
            payload_obj: object = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload_obj, dict):
            return None
        payload = cast("dict[str, object]", payload_obj)
        machine = payload.get("machine")
        role = payload.get("role")
        boot = payload.get("boot_epoch_id")
        pid = payload.get("pid")
        if (
            not isinstance(machine, str)
            or not isinstance(role, str)
            or not isinstance(boot, str)
            or not isinstance(pid, int)
        ):
            return None
        return cls(machine=machine, role=role, boot_epoch_id=boot, pid=pid)


class DaemonWriterLock:
    """Exclusive hold over one persistence root; second writer is refused."""

    def __init__(self, root: Path, token: WriterLockToken) -> None:
        self._root = root
        self._token = token
        self._path = root / DAEMON_LOCK_NAME
        self._held = False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def token(self) -> WriterLockToken:
        return self._token

    @property
    def held(self) -> bool:
        return self._held

    def acquire(self) -> Result[None]:
        """Take the sole-writer hold, or refuse a distinct second writer."""
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            encoded = self._token.encode().encode("utf-8")
            try:
                fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                holder_raw = self._path.read_text(encoding="utf-8")
                holder = WriterLockToken.decode(holder_raw)
                if holder is not None and holder.encode() == self._token.encode():
                    self._held = True
                    return Ok(None)
                return policy_rejection(
                    "daemon_writer",
                    "a second daemon or writer may not hold a persistence root already "
                    "owned by another sole writer; the second write does not proceed "
                    "(FR-Q22; AD-4, AD-6)",
                    root=str(self._root),
                    holder=holder_raw,
                    attempted=self._token.encode(),
                )
            try:
                os.write(fd, encoded)
            finally:
                os.close(fd)
        except OSError as exc:
            return storage_failure(
                f"could not acquire the daemon sole-writer lock: {exc}",
                context={"field": "daemon_writer", "root": str(self._root)},
            )
        self._held = True
        return Ok(None)

    def release(self) -> None:
        """Drop the hold if this token owns it. Idempotent."""
        if not self._held:
            return
        try:
            if (
                self._path.is_file()
                and self._path.read_text(encoding="utf-8") == self._token.encode()
            ):
                self._path.unlink()
        except OSError:
            pass
        self._held = False
