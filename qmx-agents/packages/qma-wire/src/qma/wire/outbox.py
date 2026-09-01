"""Remote worker durable dial-out spool (CT-40; AD-5, AD-6; FR-Q18).

A remote or partitioned worker holds an ordered, fsynced local outbox — never a
journal — that replays in order on reconnect. The daemon dedups on
``producer_id`` + ``id``. Depth and spool bytes are registry-homed
(``registry:wire.remote_outbox_depth``, ``registry:wire.remote_spool_bytes``).
Acknowledgement removes an entry only after the daemon ack. On bound exhaustion
the worker blocks new dispatch rather than discarding a pending evidence append;
telemetry is discarded before evidence. An environment lost with a non-empty
outbox records ``unknown_tail`` at the last acknowledged ``id`` and never
manufactures a terminal outcome from the lost connection.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal, cast

from qma.wire.idempotency import IdempotencyKey
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "REMOTE_OUTBOX_DEPTH_REGISTRY_KEY",
    "REMOTE_SPOOL_BYTES_REGISTRY_KEY",
    "UNKNOWN_TAIL_KIND",
    "OutboxBounds",
    "OutboxEntry",
    "OutboxEntryKind",
    "RemoteOutbox",
    "UnknownTailRecord",
]


REMOTE_OUTBOX_DEPTH_REGISTRY_KEY: Final[str] = "wire.remote_outbox_depth"
REMOTE_SPOOL_BYTES_REGISTRY_KEY: Final[str] = "wire.remote_spool_bytes"
UNKNOWN_TAIL_KIND: Final[str] = "unknown_tail"

OutboxEntryKind = Literal["evidence", "telemetry", "command"]

_SPOOL_NAME: Final[str] = "outbox.jsonl"
_META_NAME: Final[str] = "outbox.meta.json"


class OutboxError(ValueError):
    """Raised when outbox bounds or paths cannot be constructed."""


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _storage(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.STORAGE_FAILURE,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class OutboxBounds:
    """Installation-resolved outbox bounds from the registry keys."""

    max_depth: int
    max_spool_bytes: int
    depth_registry_key: str = REMOTE_OUTBOX_DEPTH_REGISTRY_KEY
    spool_registry_key: str = REMOTE_SPOOL_BYTES_REGISTRY_KEY

    @classmethod
    def try_create(cls, *, max_depth: object, max_spool_bytes: object) -> Result[OutboxBounds]:
        if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth <= 0:
            return _invalid(
                REMOTE_OUTBOX_DEPTH_REGISTRY_KEY,
                "remote_outbox_depth must be a positive int",
                given=repr(max_depth),
            )
        if (
            not isinstance(max_spool_bytes, int)
            or isinstance(max_spool_bytes, bool)
            or max_spool_bytes <= 0
        ):
            return _invalid(
                REMOTE_SPOOL_BYTES_REGISTRY_KEY,
                "remote_spool_bytes must be a positive int",
                given=repr(max_spool_bytes),
            )
        return Ok(cls(max_depth=max_depth, max_spool_bytes=max_spool_bytes))


@dataclass(frozen=True, slots=True)
class OutboxEntry:
    """One ordered outbox record keyed by the idempotency pair."""

    producer_id: str
    id: str
    kind: OutboxEntryKind
    payload: Mapping[str, object]
    ordinal: int
    byte_size: int

    @property
    def idempotency_key(self) -> IdempotencyKey:
        return IdempotencyKey(producer_id=self.producer_id, id=self.id)

    def to_dict(self) -> dict[str, object]:
        return {
            "producer_id": self.producer_id,
            "id": self.id,
            "kind": self.kind,
            "payload": dict(self.payload),
            "ordinal": self.ordinal,
            "byte_size": self.byte_size,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> OutboxEntry:
        kind = raw["kind"]
        if kind not in ("evidence", "telemetry", "command"):
            raise OutboxError(f"unknown outbox entry kind: {kind!r}")
        payload_obj = raw["payload"]
        if not isinstance(payload_obj, Mapping):
            raise OutboxError("outbox entry payload must be an object")
        payload_map = cast("Mapping[str, object]", payload_obj)
        ordinal_obj = raw["ordinal"]
        size_obj = raw["byte_size"]
        if not isinstance(ordinal_obj, int) or isinstance(ordinal_obj, bool):
            raise OutboxError("outbox entry ordinal must be an int")
        if not isinstance(size_obj, int) or isinstance(size_obj, bool):
            raise OutboxError("outbox entry byte_size must be an int")
        return cls(
            producer_id=str(raw["producer_id"]),
            id=str(raw["id"]),
            kind=kind,  # type: ignore[arg-type]
            payload={str(k): v for k, v in payload_map.items()},
            ordinal=ordinal_obj,
            byte_size=size_obj,
        )


@dataclass(frozen=True, slots=True)
class UnknownTailRecord:
    """Daemon-authored ledger mark when the environment is lost mid-spool.

    Records ``unknown_tail`` at the last acknowledged ``id``. Never invents a
    terminal Task outcome from the lost connection.
    """

    kind: str
    last_acknowledged_id: str | None
    pending_count: int
    authored_by: Literal["daemon"] = "daemon"
    manufactures_terminal_outcome: Literal[False] = False

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "last_acknowledged_id": self.last_acknowledged_id,
            "pending_count": self.pending_count,
            "authored_by": self.authored_by,
            "manufactures_terminal_outcome": self.manufactures_terminal_outcome,
        }


@dataclass
class RemoteOutbox:
    """Durable ordered fsynced local outbox for a remote dial-out worker.

    Entries are JSONL-appended with ``fsync``. Replay yields pending entries in
    ordinal order. ``acknowledge`` removes an entry only after daemon ack.
    """

    directory: Path
    bounds: OutboxBounds
    _entries: list[OutboxEntry] = field(
        default_factory=list[OutboxEntry],
        init=False,
        repr=False,
    )
    _spool_bytes: int = field(default=0, init=False, repr=False)
    _next_ordinal: int = field(default=0, init=False, repr=False)
    _last_acknowledged_id: str | None = field(default=None, init=False, repr=False)
    _dispatch_blocked: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self.directory = Path(self.directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._load()

    @property
    def depth(self) -> int:
        return len(self._entries)

    @property
    def spool_bytes(self) -> int:
        return self._spool_bytes

    @property
    def dispatch_blocked(self) -> bool:
        return self._dispatch_blocked

    @property
    def last_acknowledged_id(self) -> str | None:
        return self._last_acknowledged_id

    @property
    def depth_registry_key(self) -> str:
        return self.bounds.depth_registry_key

    @property
    def spool_registry_key(self) -> str:
        return self.bounds.spool_registry_key

    def _spool_path(self) -> Path:
        return self.directory / _SPOOL_NAME

    def _meta_path(self) -> Path:
        return self.directory / _META_NAME

    def _load(self) -> None:
        path = self._spool_path()
        entries: list[OutboxEntry] = []
        spool_bytes = 0
        next_ordinal = 0
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if not line.strip():
                    continue
                raw_obj: object = json.loads(line)
                if not isinstance(raw_obj, dict):
                    raise OutboxError("corrupt outbox spool line")
                raw = cast(dict[str, object], raw_obj)
                entry = OutboxEntry.from_dict(raw)
                entries.append(entry)
                spool_bytes += entry.byte_size
                next_ordinal = max(next_ordinal, entry.ordinal + 1)
        last_acked: str | None = None
        meta_path = self._meta_path()
        if meta_path.is_file():
            meta_obj: object = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(meta_obj, dict):
                meta = cast(dict[str, object], meta_obj)
                raw_acked = meta.get("last_acknowledged_id")
                if isinstance(raw_acked, str) or raw_acked is None:
                    last_acked = raw_acked
        self._entries = entries
        self._spool_bytes = spool_bytes
        self._next_ordinal = next_ordinal
        self._last_acknowledged_id = last_acked
        self._dispatch_blocked = self._at_bound()

    def _at_bound(self) -> bool:
        return (
            len(self._entries) >= self.bounds.max_depth
            or self._spool_bytes >= self.bounds.max_spool_bytes
        )

    def _fsync_write(self, path: Path, data: bytes, *, append: bool) -> None:
        mode = "ab" if append else "wb"
        with path.open(mode) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

    def _persist_all(self) -> None:
        lines = [
            (json.dumps(entry.to_dict(), separators=(",", ":"), sort_keys=True) + "\n").encode(
                "utf-8"
            )
            for entry in self._entries
        ]
        payload = b"".join(lines)
        tmp = self._spool_path().with_suffix(".jsonl.tmp")
        self._fsync_write(tmp, payload, append=False)
        os.replace(tmp, self._spool_path())
        # fsync the directory entry after replace where the OS allows it
        try:
            dir_fd = os.open(str(self.directory), os.O_RDONLY)
        except OSError:
            pass
        else:
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        meta = json.dumps(
            {"last_acknowledged_id": self._last_acknowledged_id},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        meta_tmp = self._meta_path().with_suffix(".json.tmp")
        self._fsync_write(meta_tmp, meta, append=False)
        os.replace(meta_tmp, self._meta_path())

    def enqueue(
        self,
        *,
        producer_id: object,
        id: object,
        kind: object,
        payload: object,
    ) -> Result[OutboxEntry]:
        """Append one record. Blocks when bounds would force discarding evidence."""
        key = IdempotencyKey.try_create(producer_id=producer_id, id=id)
        if not isinstance(key, Ok):
            return key
        if kind not in ("evidence", "telemetry", "command"):
            return _invalid(
                "kind",
                "outbox kind must be evidence|telemetry|command",
                given=repr(kind),
            )
        if not isinstance(payload, Mapping):
            return _invalid("payload", "outbox payload must be an object", given=repr(payload))
        payload_map = cast("Mapping[str, object]", payload)
        payload_dict = {str(k): v for k, v in payload_map.items()}

        encoded = json.dumps(
            {
                "producer_id": key.value.producer_id,
                "id": key.value.id,
                "kind": kind,
                "payload": payload_dict,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        byte_size = len(encoded) + 1  # account for LF in spool

        # Same-pair pending entry is a no-op accept (idempotent local enqueue).
        for existing in self._entries:
            if existing.idempotency_key == key.value:
                return Ok(existing)

        would_exceed = (
            len(self._entries) + 1 > self.bounds.max_depth
            or self._spool_bytes + byte_size > self.bounds.max_spool_bytes
        )
        if would_exceed:
            if kind == "telemetry":
                # Discard telemetry under back-pressure before touching evidence.
                return _policy(
                    "telemetry_discarded",
                    "telemetry discarded under outbox back-pressure before evidence",
                    depth_registry_key=REMOTE_OUTBOX_DEPTH_REGISTRY_KEY,
                    spool_registry_key=REMOTE_SPOOL_BYTES_REGISTRY_KEY,
                )
            # Evidence / command: block new work rather than discard.
            self._dispatch_blocked = True
            return _policy(
                "dispatch_blocked",
                "outbox bound reached; block new work rather than discard pending evidence",
                kind=kind,
                depth=len(self._entries),
                spool_bytes=self._spool_bytes,
                depth_registry_key=REMOTE_OUTBOX_DEPTH_REGISTRY_KEY,
                spool_registry_key=REMOTE_SPOOL_BYTES_REGISTRY_KEY,
            )

        entry = OutboxEntry(
            producer_id=key.value.producer_id,
            id=key.value.id,
            kind=kind,  # type: ignore[arg-type]
            payload=payload_dict,
            ordinal=self._next_ordinal,
            byte_size=byte_size,
        )
        line = (
            json.dumps(entry.to_dict(), separators=(",", ":"), sort_keys=True) + "\n"
        ).encode("utf-8")
        try:
            self._fsync_write(self._spool_path(), line, append=True)
        except OSError as exc:
            return _storage("outbox", "failed to fsync outbox append", os_error=str(exc))

        self._entries.append(entry)
        self._spool_bytes += byte_size
        self._next_ordinal += 1
        if self._at_bound():
            self._dispatch_blocked = True
        return Ok(entry)

    def pending(self) -> tuple[OutboxEntry, ...]:
        """Pending entries in durable ordinal order."""
        return tuple(sorted(self._entries, key=lambda e: e.ordinal))

    def replay(self) -> Sequence[OutboxEntry]:
        """Replay pending records in order against the producer_id+id pair."""
        return self.pending()

    def acknowledge(self, *, producer_id: object, id: object) -> Result[OutboxEntry]:
        """Remove an entry only after daemon acknowledgement of the pair."""
        key = IdempotencyKey.try_create(producer_id=producer_id, id=id)
        if not isinstance(key, Ok):
            return key
        for index, entry in enumerate(self._entries):
            if entry.idempotency_key == key.value:
                removed = self._entries.pop(index)
                self._spool_bytes = max(0, self._spool_bytes - removed.byte_size)
                self._last_acknowledged_id = removed.id
                try:
                    self._persist_all()
                except OSError as exc:
                    # Restore in-memory on persist failure.
                    self._entries.insert(index, removed)
                    self._spool_bytes += removed.byte_size
                    return _storage(
                        "outbox",
                        "failed to persist outbox after acknowledgement",
                        os_error=str(exc),
                    )
                if not self._at_bound():
                    self._dispatch_blocked = False
                return Ok(removed)
        return _invalid(
            "acknowledgement",
            "no pending outbox entry matches the acknowledged producer_id+id pair",
            producer_id=key.value.producer_id,
            id=key.value.id,
        )

    def on_environment_lost(self) -> UnknownTailRecord:
        """Mark unknown_tail at last acked id; never manufacture a terminal outcome."""
        return UnknownTailRecord(
            kind=UNKNOWN_TAIL_KIND,
            last_acknowledged_id=self._last_acknowledged_id,
            pending_count=len(self._entries),
            authored_by="daemon",
            manufactures_terminal_outcome=False,
        )

    def prefer_discard_telemetry(self) -> list[OutboxEntry]:
        """Under back-pressure, drop pending telemetry before any evidence."""
        kept: list[OutboxEntry] = []
        discarded: list[OutboxEntry] = []
        for entry in self._entries:
            if entry.kind == "telemetry":
                discarded.append(entry)
                self._spool_bytes = max(0, self._spool_bytes - entry.byte_size)
            else:
                kept.append(entry)
        if discarded:
            self._entries = kept
            self._persist_all()
            if not self._at_bound():
                self._dispatch_blocked = False
        return discarded
