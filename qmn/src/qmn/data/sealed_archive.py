"""One-way watermarked copy of hot rooms into sealed-archive (Story 27.4).

The evidence tier is a second directory tree. Committed hot-room prefixes copy
into the eighth AD-19 room role ``sealed-archive`` per world: watermarked,
idempotent, resumable, verify-before-purge. The copy is never a second writer
of the original observations and never runs on the slice loop (TN-3/13,
DEC-0188, DEC-0253). Off-host backup infrastructure is not stood up here —
purge consumes a verified off-host proof, and Story 27.6 owns the bucket push.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    World,
    fingerprint_bytes,
    is_ok,
    is_refusal,
)

from qmn.data._refuse import clean_token, invalid, policy, unavailable

__all__ = [
    "EIGHTH_ROOM_ROLE",
    "HOT_ROOM_ROLES",
    "KEEP_FOREVER_KINDS",
    "OFF_HOST_BACKUP_INFRA_TONIGHT",
    "SEALED_ARCHIVE_IS_SECOND_WRITER",
    "SEALED_ARCHIVE_ROLE",
    "SYNC_BLOCKS_LOOP",
    "CommittedHotPrefix",
    "HotRoomPurgeCandidate",
    "OffHostCopyProof",
    "PurgeDecision",
    "SealedArchive",
    "SyncReceipt",
    "SyncWatermark",
    "attach_sync_to_loop",
    "evaluate_hot_room_purge",
    "evaluate_sealed_deletion",
    "refuse_loop_blocking_sync",
    "refuse_off_host_backup_infra",
    "refuse_second_writer",
    "refuse_uncommitted_prefix",
]


SEALED_ARCHIVE_ROLE: Final[str] = "sealed-archive"
EIGHTH_ROOM_ROLE: Final[str] = SEALED_ARCHIVE_ROLE
SYNC_BLOCKS_LOOP: Final[bool] = False
SEALED_ARCHIVE_IS_SECOND_WRITER: Final[bool] = False
OFF_HOST_BACKUP_INFRA_TONIGHT: Final[bool] = False

HOT_ROOM_ROLES: Final[frozenset[str]] = frozenset(
    {
        "ingest door",
        "immutable raw archive",
        "processed",
        "journal",
    }
)
KEEP_FOREVER_KINDS: Final[frozenset[str]] = frozenset(
    {
        "immutable raw archive",
        "journal",
        "registry room",
        "cited-research",
        "lineage",
    }
)

_ROLE_DIRS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "ingest door": "ingest-door",
        "immutable raw archive": "immutable-raw-archive",
        "processed": "processed",
        "journal": "journal",
    }
)
_FORBIDDEN_OFF_HOST: Final[frozenset[str]] = frozenset(
    {
        "rclone",
        "boto3",
        "b2sdk",
        "backblaze",
        "backblaze-b2",
        "s3",
        "wasabi",
        "r2",
    }
)
_MAX_PREFIX_BYTES: Final[int] = 1 << 20
_WATERMARK_NAME: Final[str] = "watermark.json"
_UNCOMMITTED_ID: Final[str] = "data.sealed.uncommitted"
_SECOND_WRITER_ID: Final[str] = "data.sealed.second_writer"
_LOOP_BLOCKING_ID: Final[str] = "data.sealed.loop_blocking"
_VERIFY_ID: Final[str] = "data.sealed.verify_mismatch"
_WORLD_ID: Final[str] = "data.sealed.world"
_OFF_HOST_INFRA_ID: Final[str] = "data.sealed.off_host_infra"
_MISSING_SEALED_ID: Final[str] = "data.purge.missing_sealed"
_MISSING_OFF_HOST_ID: Final[str] = "data.purge.missing_off_host"
_WINDOW_ID: Final[str] = "data.purge.retention_window"
_RETAINED_ID: Final[str] = "data.purge.retained_forever"
_MONITORING_ID: Final[str] = "data.purge.monitoring_is_not_restore"
_JOURNAL_ID: Final[str] = "data.purge.journal"
_RESTORE_PROOF_KINDS: Final[frozenset[str]] = frozenset(
    {
        "restore-verification",
        "nightly-sample-restore",
        "monthly-full-restore",
        "host-loss-rehearsal",
    }
)


class PurgeJournalSink(Protocol):
    """Append-only journal for hot-room purge verdicts (Story 27.9)."""

    def append(self, record: Mapping[str, object], /) -> Result[None]: ...


def refuse_uncommitted_prefix(*, prefix_id: object) -> TypedRefusal:
    """Refuse a prefix that is not sealed at a committed sequence boundary."""
    return policy(
        "prefix",
        "evidence sync copies only committed hot-room prefixes of a real stream "
        "(DEC-0198, DEC-0253)",
        failure_id=_UNCOMMITTED_ID,
        prefix_id=repr(prefix_id),
    )


def refuse_second_writer(*, target: object = None) -> TypedRefusal:
    """Refuse using sealed-archive as a second writer of inbound observations."""
    return policy(
        "writer",
        "sealed-archive is a one-way copy target, never a second writer of the "
        "same observation (TN-3, DEC-0188)",
        failure_id=_SECOND_WRITER_ID,
        given=repr(target),
        second_writer=SEALED_ARCHIVE_IS_SECOND_WRITER,
    )


def refuse_loop_blocking_sync(*, target: object = None) -> TypedRefusal:
    """Refuse attaching evidence sync to the command-stream slice loop."""
    return policy(
        "loop",
        "the node loop does not block on the sealed-archive copy; sync is a "
        "detached duty (TN-3, DEC-0188)",
        failure_id=_LOOP_BLOCKING_ID,
        given=repr(type(target).__name__),
        blocks_loop=SYNC_BLOCKS_LOOP,
    )


def attach_sync_to_loop(loop: object) -> Result[None]:
    """Always refuse — evidence sync is never a slice-loop callback."""
    return refuse_loop_blocking_sync(target=loop)


def refuse_off_host_backup_infra(*, provider: object) -> TypedRefusal:
    """Refuse standing up off-host backup infrastructure in this story."""
    token = clean_token(provider)
    return policy(
        "provider",
        "Story 27.4 does not stand up off-host backup infrastructure; purge "
        "consumes a verified off-host proof and Story 27.6 owns the bucket push",
        failure_id=_OFF_HOST_INFRA_ID,
        given=repr(token),
        infra_tonight=OFF_HOST_BACKUP_INFRA_TONIGHT,
        forbidden=sorted(_FORBIDDEN_OFF_HOST),
    )


@dataclass(frozen=True, slots=True)
class CommittedHotPrefix:
    """One committed hot-room prefix that may copy into sealed-archive."""

    world: World
    room_role: str
    prefix_id: str
    start: int
    end: int
    payload: bytes
    content_fp1: Fingerprint
    committed: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "world": self.world.value,
                "room_role": self.room_role,
                "prefix_id": self.prefix_id,
                "start": self.start,
                "end": self.end,
                "content_fp1": self.content_fp1.value,
                "committed": self.committed,
                "payload_bytes": len(self.payload),
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        world: object,
        room_role: object,
        prefix_id: object,
        start: object,
        end: object,
        payload: object,
        committed: object,
    ) -> Result[CommittedHotPrefix]:
        resolved = _as_world(world)
        if is_refusal(resolved):
            return resolved
        role = _as_hot_role(room_role)
        if is_refusal(role):
            return role
        ident = _segment(prefix_id, field="prefix_id")
        if is_refusal(ident):
            return ident
        start_ns = _as_nonneg_int(start, field="start")
        if is_refusal(start_ns):
            return start_ns
        end_ns = _as_nonneg_int(end, field="end")
        if is_refusal(end_ns):
            return end_ns
        if end_ns.value <= start_ns.value:
            return invalid(
                "window",
                "a committed prefix is a non-empty [start, end) sequence window",
                start=start_ns.value,
                end=end_ns.value,
            )
        if not isinstance(payload, (bytes, bytearray)):
            return invalid(
                "payload",
                "a hot-room prefix carries raw committed bytes",
                given=repr(type(payload).__name__),
            )
        body = bytes(payload)
        if len(body) > _MAX_PREFIX_BYTES:
            return policy(
                "payload",
                "a hot-room prefix exceeds the sealed-archive size cap",
                size=len(body),
                cap=_MAX_PREFIX_BYTES,
            )
        if committed is not True:
            return refuse_uncommitted_prefix(prefix_id=ident.value)
        digest = fingerprint_bytes(body)
        return Ok(
            cls(
                world=resolved.value,
                room_role=role.value,
                prefix_id=ident.value,
                start=start_ns.value,
                end=end_ns.value,
                payload=body,
                content_fp1=digest,
                committed=True,
            )
        )


@dataclass(frozen=True, slots=True)
class SyncWatermark:
    """Highest verified prefix end copied into sealed-archive for one room."""

    world: str
    room_role: str
    prefix_end: int
    content_fp1: str
    verified: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "world": self.world,
                "room_role": self.room_role,
                "prefix_end": self.prefix_end,
                "content_fp1": self.content_fp1,
                "verified": self.verified,
            }
        )


@dataclass(frozen=True, slots=True)
class SyncReceipt:
    """Outcome of one one-way copy into sealed-archive."""

    world: str
    room_role: str
    prefix_id: str
    copied: bool
    resumed: bool
    verified: bool
    watermark: SyncWatermark
    second_writer: bool = False
    blocks_loop: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "world": self.world,
                "room_role": self.room_role,
                "prefix_id": self.prefix_id,
                "copied": self.copied,
                "resumed": self.resumed,
                "verified": self.verified,
                "watermark": dict(self.watermark.as_mapping()),
                "second_writer": self.second_writer,
                "blocks_loop": self.blocks_loop,
            }
        )


@dataclass(frozen=True, slots=True)
class OffHostCopyProof:
    """Verified off-host copy claim. Not a bucket client (Story 27.6)."""

    prefix_id: str
    verified: bool
    copy_version: str
    verification_kind: str = "restore-verification"

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "prefix_id": self.prefix_id,
                "verified": self.verified,
                "copy_version": self.copy_version,
                "verification_kind": self.verification_kind,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        prefix_id: object,
        verified: object,
        copy_version: object,
        verification_kind: object = "restore-verification",
    ) -> Result[OffHostCopyProof]:
        ident = _segment(prefix_id, field="prefix_id")
        if is_refusal(ident):
            return ident
        version = clean_token(copy_version)
        if version is None:
            return invalid(
                "copy_version",
                "an off-host proof names a non-empty copy version",
                given=repr(copy_version),
            )
        if not isinstance(verified, bool):
            return invalid(
                "verified",
                "an off-host proof is a boolean verified claim",
                given=repr(verified),
            )
        kind = clean_token(verification_kind)
        if kind is None:
            return invalid(
                "verification_kind",
                "an off-host proof names the verification kind that produced it",
                given=repr(verification_kind),
            )
        return Ok(
            cls(
                prefix_id=ident.value,
                verified=verified,
                copy_version=version,
                verification_kind=kind,
            )
        )


@dataclass(frozen=True, slots=True)
class HotRoomPurgeCandidate:
    """One hot-room prefix asking to drop after the retention window."""

    world: World
    room_role: str
    prefix_id: str
    prefix_end: int
    now_ns: int
    sealed_at_ns: int
    retention_window_ns: int
    sealed_verified: bool
    off_host: OffHostCopyProof | None
    cited: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        off_host = None if self.off_host is None else dict(self.off_host.as_mapping())
        return MappingProxyType(
            {
                "world": self.world.value,
                "room_role": self.room_role,
                "prefix_id": self.prefix_id,
                "prefix_end": self.prefix_end,
                "now_ns": self.now_ns,
                "sealed_at_ns": self.sealed_at_ns,
                "retention_window_ns": self.retention_window_ns,
                "sealed_verified": self.sealed_verified,
                "off_host": off_host,
                "cited": self.cited,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        world: object,
        room_role: object,
        prefix_id: object,
        prefix_end: object,
        now_ns: object,
        sealed_at_ns: object,
        retention_window_ns: object,
        sealed_verified: object,
        off_host: object,
        cited: object = False,
    ) -> Result[HotRoomPurgeCandidate]:
        resolved = _as_world(world)
        if is_refusal(resolved):
            return resolved
        role = _as_hot_role(room_role)
        if is_refusal(role):
            return role
        ident = _segment(prefix_id, field="prefix_id")
        if is_refusal(ident):
            return ident
        end = _as_nonneg_int(prefix_end, field="prefix_end")
        if is_refusal(end):
            return end
        now = _as_nonneg_int(now_ns, field="now_ns")
        if is_refusal(now):
            return now
        sealed_at = _as_nonneg_int(sealed_at_ns, field="sealed_at_ns")
        if is_refusal(sealed_at):
            return sealed_at
        window = _as_nonneg_int(retention_window_ns, field="retention_window_ns")
        if is_refusal(window):
            return window
        if not isinstance(sealed_verified, bool):
            return invalid(
                "sealed_verified",
                "sealed-archive verification is a boolean",
                given=repr(sealed_verified),
            )
        if off_host is not None and not isinstance(off_host, OffHostCopyProof):
            return invalid(
                "off_host",
                "off-host proof is OffHostCopyProof or None",
                given=repr(type(off_host).__name__),
            )
        if not isinstance(cited, bool):
            return invalid("cited", "cited is a boolean", given=repr(cited))
        return Ok(
            cls(
                world=resolved.value,
                room_role=role.value,
                prefix_id=ident.value,
                prefix_end=end.value,
                now_ns=now.value,
                sealed_at_ns=sealed_at.value,
                retention_window_ns=window.value,
                sealed_verified=sealed_verified,
                off_host=off_host,
                cited=cited,
            )
        )


@dataclass(frozen=True, slots=True)
class PurgeDecision:
    """Hot-room purge is allowed only after dual verified copies exist."""

    allowed: bool
    prefix_id: str
    reason: str
    journaled: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "allowed": self.allowed,
                "prefix_id": self.prefix_id,
                "reason": self.reason,
                "journaled": self.journaled,
            }
        )


class SealedArchive:
    """Per-root sealed-archive tree under ``evidence/<world>/sealed-archive``."""

    def __init__(self, evidence_root: Path) -> None:
        self._root = evidence_root

    def sync(self, prefix: object) -> Result[SyncReceipt]:
        """Copy one committed prefix one-way, then advance the watermark."""
        if not isinstance(prefix, CommittedHotPrefix):
            return invalid(
                "prefix",
                "evidence sync copies a CommittedHotPrefix",
                given=repr(type(prefix).__name__),
            )
        if prefix.world is World.SIMULATED:
            return policy(
                "world",
                "world = simulated is reserved-unusable; sealed-archive is not "
                "instantiated for it (DEC-0110, DEC-0253)",
                failure_id=_WORLD_ID,
                world=prefix.world.value,
            )
        dest = self._prefix_path(prefix.world, prefix.room_role, prefix.prefix_id)
        if is_refusal(dest):
            return dest
        existing = self._read_existing(dest.value)
        if is_ok(existing) and existing.value == prefix.content_fp1.value:
            mark = self._advance_watermark(prefix, verified=True)
            if is_refusal(mark):
                return mark
            return Ok(
                SyncReceipt(
                    world=prefix.world.value,
                    room_role=prefix.room_role,
                    prefix_id=prefix.prefix_id,
                    copied=False,
                    resumed=True,
                    verified=True,
                    watermark=mark.value,
                    second_writer=SEALED_ARCHIVE_IS_SECOND_WRITER,
                    blocks_loop=SYNC_BLOCKS_LOOP,
                )
            )
        if is_ok(existing) and existing.value != prefix.content_fp1.value:
            return policy(
                "prefix_id",
                "a true fp1 collision on differing sealed-archive bytes is refused "
                "and never overwritten (DEC-0108)",
                failure_id=_VERIFY_ID,
                prefix_id=prefix.prefix_id,
                existing_fp1=existing.value,
                given_fp1=prefix.content_fp1.value,
            )
        written = _atomic_write(dest.value, prefix.payload)
        if is_refusal(written):
            return written
        verified = self._verify_dest(dest.value, prefix.content_fp1)
        if is_refusal(verified):
            return verified
        mark = self._advance_watermark(prefix, verified=True)
        if is_refusal(mark):
            return mark
        return Ok(
            SyncReceipt(
                world=prefix.world.value,
                room_role=prefix.room_role,
                prefix_id=prefix.prefix_id,
                copied=True,
                resumed=False,
                verified=True,
                watermark=mark.value,
                second_writer=SEALED_ARCHIVE_IS_SECOND_WRITER,
                blocks_loop=SYNC_BLOCKS_LOOP,
            )
        )

    def watermark(self, world: object, room_role: object) -> Result[SyncWatermark | None]:
        """The durable verified watermark for one world's hot room, if any."""
        resolved = _as_world(world)
        if is_refusal(resolved):
            return resolved
        role = _as_hot_role(room_role)
        if is_refusal(role):
            return role
        path = self._watermark_path(resolved.value, role.value)
        if is_refusal(path):
            return path
        if not path.value.is_file() or path.value.is_symlink():
            return Ok(None)
        loaded = _read_capped(path.value)
        if is_refusal(loaded):
            return loaded
        try:
            body = json.loads(loaded.value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return unavailable("watermark", "sealed-archive watermark is not readable JSON")
        if not isinstance(body, dict):
            return unavailable("watermark", "sealed-archive watermark is an object")
        parsed = _watermark_from_mapping(cast("Mapping[str, object]", body))
        if is_refusal(parsed):
            return parsed
        mark: SyncWatermark | None = parsed.value
        return Ok(mark)

    def has_verified_copy(self, prefix: CommittedHotPrefix) -> bool:
        """Whether ``prefix`` is durably present and content-verified."""
        dest = self._prefix_path(prefix.world, prefix.room_role, prefix.prefix_id)
        if is_refusal(dest):
            return False
        existing = self._read_existing(dest.value)
        if is_refusal(existing) or existing.value != prefix.content_fp1.value:
            return False
        return self.covers(
            world=prefix.world,
            room_role=prefix.room_role,
            prefix_id=prefix.prefix_id,
            prefix_end=prefix.end,
        )

    def covers(
        self,
        *,
        world: object,
        room_role: object,
        prefix_id: object,
        prefix_end: object,
    ) -> bool:
        """Whether a verified sealed copy covers ``prefix_end`` for ``prefix_id``."""
        resolved = _as_world(world)
        if is_refusal(resolved):
            return False
        role = _as_hot_role(room_role)
        if is_refusal(role):
            return False
        ident = _segment(prefix_id, field="prefix_id")
        if is_refusal(ident):
            return False
        end = _as_nonneg_int(prefix_end, field="prefix_end")
        if is_refusal(end):
            return False
        dest = self._prefix_path(resolved.value, role.value, ident.value)
        if is_refusal(dest):
            return False
        existing = self._read_existing(dest.value)
        if is_refusal(existing):
            return False
        mark = self.watermark(resolved.value, role.value)
        if is_refusal(mark) or mark.value is None:
            return False
        return mark.value.verified and mark.value.prefix_end >= end.value

    def read_prefix(
        self,
        *,
        world: object,
        room_role: object,
        prefix_id: object,
    ) -> Result[bytes]:
        """Read-only payload fetch. Never writes (TN-21 replay import)."""
        resolved = _as_world(world)
        if is_refusal(resolved):
            return resolved
        role = _as_hot_role(room_role)
        if is_refusal(role):
            return role
        ident = _segment(prefix_id, field="prefix_id")
        if is_refusal(ident):
            return ident
        dest = self._prefix_path(resolved.value, role.value, ident.value)
        if is_refusal(dest):
            return dest
        if dest.value.is_symlink() or not dest.value.is_file():
            return unavailable(
                "prefix",
                "sealed-archive does not hold this prefix",
                prefix_id=ident.value,
            )
        return _read_capped(dest.value)

    def _role_dir(self, world: World, room_role: str) -> Result[Path]:
        dirname = _ROLE_DIRS[room_role]
        world_seg = _segment(world.value, field="world")
        if is_refusal(world_seg):
            return world_seg
        path = self._root / world_seg.value / SEALED_ARCHIVE_ROLE / dirname
        contained = _contained_dir(self._root, path)
        if is_refusal(contained):
            return contained
        return Ok(path)

    def _prefix_path(self, world: World, room_role: str, prefix_id: str) -> Result[Path]:
        directory = self._role_dir(world, room_role)
        if is_refusal(directory):
            return directory
        ident = _segment(prefix_id, field="prefix_id")
        if is_refusal(ident):
            return ident
        path = directory.value / ident.value
        return _contained_file(self._root, path)

    def _watermark_path(self, world: World, room_role: str) -> Result[Path]:
        directory = self._role_dir(world, room_role)
        if is_refusal(directory):
            return directory
        path = directory.value / _WATERMARK_NAME
        return _contained_file(self._root, path)

    def _read_existing(self, path: Path) -> Result[str]:
        if not path.exists():
            return unavailable("prefix", "sealed-archive does not yet hold this prefix")
        loaded = _read_capped(path)
        if is_refusal(loaded):
            return loaded
        return Ok(fingerprint_bytes(loaded.value).value)

    def _verify_dest(self, path: Path, expected: Fingerprint) -> Result[None]:
        loaded = _read_capped(path)
        if is_refusal(loaded):
            return loaded
        actual = fingerprint_bytes(loaded.value)
        if actual.value != expected.value:
            return policy(
                "content_fp1",
                "sealed-archive verify-before-purge refused a content mismatch; "
                "the watermark does not advance (DEC-0253)",
                failure_id=_VERIFY_ID,
                expected=expected.value,
                actual=actual.value,
            )
        return Ok(None)

    def _advance_watermark(
        self, prefix: CommittedHotPrefix, *, verified: bool
    ) -> Result[SyncWatermark]:
        current = self.watermark(prefix.world, prefix.room_role)
        if is_refusal(current):
            return current
        prefix_end = prefix.end
        content_fp1 = prefix.content_fp1.value
        if current.value is not None and current.value.prefix_end > prefix_end:
            prefix_end = current.value.prefix_end
            content_fp1 = current.value.content_fp1
        mark = SyncWatermark(
            world=prefix.world.value,
            room_role=prefix.room_role,
            prefix_end=prefix_end,
            content_fp1=content_fp1,
            verified=verified,
        )
        path = self._watermark_path(prefix.world, prefix.room_role)
        if is_refusal(path):
            return path
        payload = (json.dumps(dict(mark.as_mapping()), sort_keys=True) + "\n").encode("utf-8")
        written = _atomic_write(path.value, payload)
        if is_refusal(written):
            return written
        return Ok(mark)


def evaluate_hot_room_purge(
    candidate: object,
    *,
    archive: object | None = None,
    journal: object | None = None,
) -> Result[PurgeDecision]:
    """Hot-room purge requires a verified sealed copy AND a verified off-host copy."""
    if not isinstance(candidate, HotRoomPurgeCandidate):
        return invalid(
            "candidate",
            "purge eligibility evaluates a HotRoomPurgeCandidate",
            given=repr(type(candidate).__name__),
        )
    sealed_ok = candidate.sealed_verified
    if isinstance(archive, SealedArchive):
        sealed_ok = archive.covers(
            world=candidate.world,
            room_role=candidate.room_role,
            prefix_id=candidate.prefix_id,
            prefix_end=candidate.prefix_end,
        )
    if candidate.now_ns - candidate.sealed_at_ns < candidate.retention_window_ns:
        refused = policy(
            "retention_window",
            "a hot room may be purged only after hot_room_retention_window elapses "
            "(DEC-0198, DEC-0253)",
            failure_id=_WINDOW_ID,
            prefix_id=candidate.prefix_id,
            elapsed_ns=candidate.now_ns - candidate.sealed_at_ns,
            window_ns=candidate.retention_window_ns,
        )
        journaled = _journal_purge(journal, candidate, allowed=False, reason=_WINDOW_ID)
        if is_refusal(journaled):
            return journaled
        return refused
    if not sealed_ok:
        refused = policy(
            "sealed-archive",
            "hot-room purge requires a verified copy in the sealed-archive room role "
            "(DEC-0188, DEC-0253)",
            failure_id=_MISSING_SEALED_ID,
            prefix_id=candidate.prefix_id,
        )
        journaled = _journal_purge(journal, candidate, allowed=False, reason=_MISSING_SEALED_ID)
        if is_refusal(journaled):
            return journaled
        return refused
    off_host = candidate.off_host
    if off_host is None or not off_host.verified or off_host.prefix_id != candidate.prefix_id:
        refused = policy(
            "off-host",
            "hot-room purge requires a verified off-host copy; a same-disk sealed "
            "copy frees nothing by itself (DEC-0188, DEC-0198)",
            failure_id=_MISSING_OFF_HOST_ID,
            prefix_id=candidate.prefix_id,
        )
        journaled = _journal_purge(journal, candidate, allowed=False, reason=_MISSING_OFF_HOST_ID)
        if is_refusal(journaled):
            return journaled
        return refused
    if off_host.verification_kind not in _RESTORE_PROOF_KINDS:
        refused = policy(
            "off-host",
            "hot-room purge requires restore verification; a monitoring result "
            "or provider default is not a restore proof (FR-065, CT-14)",
            failure_id=_MONITORING_ID,
            prefix_id=candidate.prefix_id,
            verification_kind=off_host.verification_kind,
        )
        journaled = _journal_purge(journal, candidate, allowed=False, reason=_MONITORING_ID)
        if is_refusal(journaled):
            return journaled
        return refused
    journaled = _journal_purge(
        journal,
        candidate,
        allowed=True,
        reason="verified-sealed-and-restore-verified-off-host",
    )
    if is_refusal(journaled):
        return journaled
    return Ok(
        PurgeDecision(
            allowed=True,
            prefix_id=candidate.prefix_id,
            reason=(
                "verified sealed-archive and restore-verified off-host copies both "
                "exist past hot_room_retention_window"
            ),
            journaled=journal is not None,
        )
    )


def _journal_purge(
    journal: object | None,
    candidate: HotRoomPurgeCandidate,
    *,
    allowed: bool,
    reason: str,
) -> Result[None]:
    if journal is None:
        return Ok(None)
    if not hasattr(journal, "append"):
        return invalid(
            "journal",
            "hot-room purge journals the unmet proof; a journal sink is required",
            given=repr(type(journal).__name__),
        )
    off_host = None if candidate.off_host is None else dict(candidate.off_host.as_mapping())
    record = MappingProxyType(
        {
            "event_type": "data quality",
            "allowed": allowed,
            "reason": reason,
            "prefix_id": candidate.prefix_id,
            "world": candidate.world.value,
            "room_role": candidate.room_role,
            "sealed_verified": candidate.sealed_verified,
            "off_host": off_host,
        }
    )
    sink = cast("PurgeJournalSink", journal)
    written = sink.append(record)
    if is_refusal(written):
        return unavailable(
            "journal",
            "hot-room purge journals the unmet proof; the journal rejected the verdict (FR-065)",
            failure_id=_JOURNAL_ID,
            prefix_id=candidate.prefix_id,
            unmet_reason=reason,
        )
    return Ok(None)


def evaluate_sealed_deletion(candidate: object) -> Result[PurgeDecision]:
    """Sealed/off-host copies of evidence stay under the keep-forever retention law."""
    if not isinstance(candidate, HotRoomPurgeCandidate):
        return invalid(
            "candidate",
            "retention evaluates a HotRoomPurgeCandidate",
            given=repr(type(candidate).__name__),
        )
    kind = candidate.room_role
    if candidate.cited:
        kind = "cited-research"
    if kind in KEEP_FOREVER_KINDS:
        return policy(
            "retention",
            "raw evidence, journals, registry, cited research artifacts, and lineage "
            "remain under their keep-forever retention law (DEC-0117, NFR-15)",
            failure_id=_RETAINED_ID,
            prefix_id=candidate.prefix_id,
            kind=kind,
        )
    return Ok(
        PurgeDecision(
            allowed=True,
            prefix_id=candidate.prefix_id,
            reason="rebuildable uncited artifact is deletion-licensed under retention law",
        )
    )


def _as_world(value: object) -> Result[World]:
    if isinstance(value, World):
        resolved = value
    elif isinstance(value, str):
        try:
            resolved = World(value)
        except ValueError:
            return invalid(
                "world",
                "world is one of the closed set live | replay | simulated",
                given=value,
            )
    else:
        return invalid(
            "world",
            "world is a World or one of the closed set live | replay | simulated",
            given=repr(value),
        )
    if resolved is World.SIMULATED:
        return policy(
            "world",
            "world = simulated is reserved-unusable; sealed-archive is not "
            "instantiated for it (DEC-0110, DEC-0253)",
            failure_id=_WORLD_ID,
            world=resolved.value,
        )
    return Ok(resolved)


def _as_hot_role(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None or token not in HOT_ROOM_ROLES:
        return invalid(
            "room_role",
            "a hot-room prefix names one of ingest door, immutable raw archive, "
            "processed, or journal",
            given=repr(value),
            allowed=sorted(HOT_ROOM_ROLES),
        )
    return Ok(token)


def _as_nonneg_int(value: object, *, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, f"{field} is a non-negative int64", given=repr(value))
    return Ok(value)


def _segment(value: object, *, field: str) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(field, f"{field} is a non-empty path segment", given=repr(value))
    if token in {".", ".."} or "/" in token or "\\" in token or ":" in token:
        return policy(
            field,
            f"{field} is a single confined path segment",
            given=token,
        )
    return Ok(token)


def _contained_dir(root: Path, path: Path) -> Result[Path]:
    try:
        resolved_root = root.resolve()
        resolved = path.resolve()
    except OSError:
        return unavailable("path", "sealed-archive path could not be resolved")
    if path.is_symlink() or resolved.is_symlink():
        return policy("path", "refusing to follow a symlink in the evidence tier")
    if not resolved.is_relative_to(resolved_root):
        return policy("path", "sealed-archive path escaped the evidence root")
    return Ok(path)


def _contained_file(root: Path, path: Path) -> Result[Path]:
    contained = _contained_dir(root, path.parent)
    if is_refusal(contained):
        return contained
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink in the evidence tier")
    try:
        resolved_root = root.resolve()
        resolved = path.resolve()
    except OSError:
        return unavailable("path", "sealed-archive path could not be resolved")
    if not resolved.is_relative_to(resolved_root):
        return policy("path", "sealed-archive path escaped the evidence root")
    return Ok(path)


def _read_capped(path: Path) -> Result[bytes]:
    if path.is_symlink() or not path.is_file():
        return unavailable("path", "sealed-archive object is missing")
    data = path.read_bytes()
    if len(data) > _MAX_PREFIX_BYTES:
        return policy("payload", "sealed-archive object exceeds the size cap")
    return Ok(data)


def _atomic_write(path: Path, payload: bytes) -> Result[None]:
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink at the sealed-archive dest")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return unavailable("path", "sealed-archive directory could not be created")
    tmp = path.parent / f".{path.name}.tmp-{os.getpid()}"
    if tmp.is_symlink():
        return policy("path", "refusing to follow a symlink at the sealed-archive temp")
    flags = (
        os.O_CREAT
        | os.O_EXCL
        | os.O_WRONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        fd = os.open(tmp, flags, 0o600)  # skylos: ignore[SKY-D215] contained sealed copy
    except OSError:
        return unavailable("path", "sealed-archive rejected the new prefix")
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            offset += os.write(fd, view[offset:])
    except OSError:
        os.close(fd)
        tmp.unlink(missing_ok=True)
        return unavailable("path", "sealed-archive rejected the new prefix")
    os.close(fd)
    try:
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        return unavailable("path", "sealed-archive rejected the new prefix")
    return Ok(None)


def _watermark_from_mapping(body: Mapping[str, object]) -> Result[SyncWatermark]:
    world = clean_token(body.get("world"))
    role = clean_token(body.get("room_role"))
    end = body.get("prefix_end")
    digest = clean_token(body.get("content_fp1"))
    verified = body.get("verified")
    if world is None or role is None or digest is None:
        return unavailable("watermark", "sealed-archive watermark is missing fields")
    if not isinstance(end, int) or isinstance(end, bool) or end < 0:
        return unavailable("watermark", "sealed-archive watermark prefix_end is invalid")
    if not isinstance(verified, bool):
        return unavailable("watermark", "sealed-archive watermark verified is invalid")
    return Ok(
        SyncWatermark(
            world=world,
            room_role=role,
            prefix_end=end,
            content_fp1=digest,
            verified=verified,
        )
    )
