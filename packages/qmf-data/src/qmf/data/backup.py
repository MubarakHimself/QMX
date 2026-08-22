"""CT-14 — encrypted, versioned off-machine backup copy (COMP-QMF-DATA-BACKUP).

Consumes the CT-26 :class:`~qmf.data.store.backup_input.RoomExport` input and produces
a **new** encrypted, versioned off-machine artifact through an injected
:class:`ObjectStorage` port. QMF owns the backup/restore/verify *primitives*; the
nightly cadence and its execution stay application/ops-owned (DEC-0118).

Hard rules this seam enforces:

* Encryption is **required** — a :class:`PayloadCipher` is injected at the composition
  root; key custody and the crypto dependency are node/ops-sitting items (AC5).
* Every successful copy is a distinct ``copy_version``; the primitive never mutates
  an earlier artifact or the only local evidence copy (AC2).
* Cross-world copy and ``world = simulated`` are ``policy rejection`` refusals (AC3).
* Unreachable storage, a rejected upload, or a corrupt copy yields a ``storage
  failure`` typed refusal — never raised across the boundary, and never reported as
  completion (AC4).
* Object-key layout, provider selection, numeric RPO/RTO/retention, and credentials
  are **not** baked in; no credential enters the receipt or evidence (AC5, DEC-0045).

Stdlib + qmf-core + the store's CT-26 types only (default-deny; L30).
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import Final, Protocol

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    is_refusal,
    unpersistable,
)
from qmf.data.store.backup_input import RecordExport, RoomExport
from qmf.data.store.rooms import RoomRole

__all__ = [
    "BACKUP_CONTRACT_FORMAT_VERSION",
    "ENCRYPTION_REQUIRED",
    "BackupCopyReceipt",
    "ObjectStorage",
    "OffMachineBackup",
    "OffMachineCopy",
    "PayloadCipher",
    "StoragePutAck",
]

# CT-14's first minted format version (DEC-0103; versioning-from-birth L15).
BACKUP_CONTRACT_FORMAT_VERSION: Final[int] = 1

# Encryption is required; key custody is named at the node/ops sitting (DEC-0118).
ENCRYPTION_REQUIRED: Final[bool] = True

# Framing magic so a future restore can recognize the plaintext envelope.
_PLAINTEXT_MAGIC: Final[bytes] = b"QMFB1\0"


@dataclass(frozen=True, slots=True)
class StoragePutAck:
    """Acknowledgement that object storage accepted one versioned encrypted object.

    ``detail`` is optional provider-neutral confirmation (e.g. an opaque object id).
    It must never carry credentials or secret material (DEC-0045, AR-37).
    """

    detail: tuple[tuple[str, str], ...] = ()


class PayloadCipher(Protocol):
    """Encryption-required pointer — the crypto dependency is node/ops-owned (AC5).

    Injected at the composition root. This package never selects an algorithm or
    holds key material; the adapter encrypts plaintext to opaque ciphertext and
    returns value-or-refusal so a missing key or crypto failure stays a typed
    refusal, never an exception across the CT-14 boundary (DEC-0109, DEC-0118).
    """

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:  # pragma: no cover - protocol
        """Return ciphertext for ``plaintext``, or a typed refusal."""
        ...


class ObjectStorage(Protocol):
    """Provider-neutral destination for encrypted, versioned off-machine copies (AC5).

    Injected at the composition root. Object-key layout, provider selection, and
    credentials stay outside QMF — this port accepts an already-encrypted payload
    identified by world, ordinal version, and room-role, and returns value-or-refusal
    (DEC-0118, DEC-0045). An unreachable bucket, rejected upload, or corrupt copy is
    a ``storage failure`` refusal; the port never raises across the package seam.
    """

    def put(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        payload: bytes,
        format_version: int,
    ) -> Result[StoragePutAck]:  # pragma: no cover - protocol
        """Store one new versioned encrypted object (value-or-refusal)."""
        ...


@dataclass(frozen=True, slots=True)
class OffMachineCopy:
    """The CT-14 artifact: one encrypted, versioned off-machine copy (AC2).

    ``payload`` is opaque ciphertext. Stored int64 UTC-ns timestamps live inside the
    encrypted envelope as the verbatim CT-26 canonical record bytes — never
    re-derived under a later calendar identity or tzdata version (DEC-0106).
    ``encryption_required`` is the standing pointer (always ``True``).
    """

    world: World
    copy_version: int
    source_room_role: RoomRole
    payload: bytes
    format_version: int = BACKUP_CONTRACT_FORMAT_VERSION
    encryption_required: bool = ENCRYPTION_REQUIRED


@dataclass(frozen=True, slots=True)
class BackupCopyReceipt:
    """Completion evidence for one CT-14 off-machine copy — no credentials (AC2, AC5).

    Returned only after object storage accepts the encrypted payload. A storage
    failure never yields this receipt. ``payload_fingerprint`` is the fp1 of the
    *ciphertext*, so the receipt identifies the off-machine artifact without
    embedding plaintext or secrets.
    """

    world: World
    copy_version: int
    source_room_role: RoomRole
    payload_fingerprint: str
    record_count: int
    format_version: int = BACKUP_CONTRACT_FORMAT_VERSION
    encryption_required: bool = ENCRYPTION_REQUIRED


class OffMachineBackup:
    """The CT-14 backup primitive: encrypt + version + put, never mutate the only copy.

    Constructed with an :class:`ObjectStorage` and a :class:`PayloadCipher` at the
    composition root. Each successful :meth:`copy_export` allocates a new ordinal
    ``copy_version`` and uploads a fresh artifact; failed attempts do not claim
    completion and still advance the version counter so a later retry never overwrites
    a prior ordinal (AC2, AC4).
    """

    def __init__(self, storage: ObjectStorage, cipher: PayloadCipher) -> None:
        self._storage = storage
        self._cipher = cipher
        self._next_version = 1

    @property
    def next_copy_version(self) -> int:
        """The ordinal the next successful or attempted copy will use."""
        return self._next_version

    def copy_export(self, export: RoomExport, *, for_world: object) -> Result[BackupCopyReceipt]:
        """Encrypt ``export`` and put a new versioned off-machine copy (AC2–AC5).

        ``for_world`` must match ``export.world``; a cross-world request or
        ``world = simulated`` is a ``policy rejection``. The CT-26 record bytes
        (including int64 UTC-ns timestamps) are framed verbatim, encrypted through
        the injected cipher, and handed to object storage as a **new** version —
        the local evidence and any earlier off-machine copy are left untouched.
        """
        gate = _governed_world(export, for_world)
        if is_refusal(gate):
            return gate
        world = gate.value

        copy_version = self._next_version
        # Advance before the put so a failed attempt never reuses the ordinal on retry
        # (each off-machine copy is a distinct versioned artifact — AC2).
        self._next_version = copy_version + 1

        plaintext = _frame_plaintext(export)
        try:
            encrypted = self._cipher.encrypt(plaintext)
        except Exception as exc:
            return _storage_failure(
                "payload cipher raised while encrypting the backup copy; completion "
                "is not claimed (DEC-0109, DEC-0118)",
                retryable=False,
                context={"signal": "cipher-raised", "error_type": type(exc).__name__},
            )
        if is_refusal(encrypted):
            return encrypted
        ciphertext = encrypted.value
        if not ciphertext:
            return _storage_failure(
                "payload cipher returned empty ciphertext; encryption is required and "
                "an empty payload is treated as a corrupt copy — completion is not "
                "claimed (DEC-0118)",
                retryable=False,
                context={"signal": "corrupt-copy", "copy_version": copy_version},
            )

        artifact = OffMachineCopy(
            world=world,
            copy_version=copy_version,
            source_room_role=export.source_room_role,
            payload=ciphertext,
        )
        try:
            put = self._storage.put(
                world=artifact.world.value,
                copy_version=artifact.copy_version,
                source_room_role=artifact.source_room_role.value,
                payload=artifact.payload,
                format_version=artifact.format_version,
            )
        except Exception as exc:
            return _storage_failure(
                "object storage raised during the off-machine put; completion is not "
                "claimed (DEC-0109, DEC-0118)",
                retryable=True,
                context={
                    "signal": "storage-raised",
                    "error_type": type(exc).__name__,
                    "copy_version": copy_version,
                },
            )
        if is_refusal(put):
            # AC4: unreachable / rejected / corrupt object storage is always a
            # storage-failure refusal at this boundary, even if a miswired adapter
            # returned a different category.
            if put.category is RefusalCategory.STORAGE_FAILURE:
                return put
            remapped: dict[str, object] = dict(put.context)
            remapped["signal"] = "storage-refused"
            remapped["adapter_category"] = put.category.value
            remapped["copy_version"] = copy_version
            return _storage_failure(
                "object storage refused the off-machine put; completion is not claimed "
                "(DEC-0109, DEC-0118)",
                retryable=put.retryability is Retryability.YES,
                context=remapped,
            )

        return Ok(
            BackupCopyReceipt(
                world=world,
                copy_version=copy_version,
                source_room_role=export.source_room_role,
                payload_fingerprint=_fp1_of(ciphertext),
                record_count=export.record_count,
            )
        )


def _governed_world(export: RoomExport, for_world: object) -> Result[World]:
    """Resolve and gate ``for_world`` against the export; refuse simulated/cross-world."""
    if for_world is None:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "for_world",
                "reason": (
                    "a backup copy must declare the world it is copying as; there is "
                    "no implicit same-world default (M4)"
                ),
            },
        )
    resolved = _coerce_world(for_world)
    if resolved is None:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": "world is a World or one of the closed set live | replay | simulated",
                "given": repr(for_world),
            },
        )
    if resolved is World.SIMULATED:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": (
                    "world = simulated has no governed namespace in V1; a backup copy "
                    "into governed off-machine evidence is refused (DEC-0110, DEC-0117)"
                ),
                "requested": resolved.value,
            },
        )
    if resolved is not export.world:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": (
                    "a backup copy that crosses worlds is refused; storage separation "
                    "delivers world isolation (DEC-0117)"
                ),
                "requested": resolved.value,
                "export_world": export.world.value,
            },
        )
    return Ok(resolved)


def _coerce_world(value: object) -> World | None:
    """Resolve a :class:`World` or its string value, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def _frame_plaintext(export: RoomExport) -> bytes:
    """Frame one room export so record canonical bytes (timestamps) pass through verbatim.

    Metadata is length-prefixed UTF-8; each record's fingerprint and canonical bytes
    follow as length-prefixed blobs. The canonical payload is never re-serialized, so
    int64 UTC-ns timestamps remain exactly the stored bytes (DEC-0106).
    """
    chunks: list[bytes] = [_PLAINTEXT_MAGIC]
    meta = (
        f"v={export.format_version}\n"
        f"world={export.world.value}\n"
        f"role={export.source_room_role.value}\n"
        f"count={export.record_count}\n"
    ).encode()
    chunks.append(struct.pack(">I", len(meta)))
    chunks.append(meta)
    for record in export.records:
        _append_record(chunks, record)
    return b"".join(chunks)


def _append_record(chunks: list[bytes], record: RecordExport) -> None:
    """Append one verbatim record frame to ``chunks``."""
    fp = record.fingerprint.encode("utf-8")
    chunks.append(struct.pack(">I", len(fp)))
    chunks.append(fp)
    chunks.append(struct.pack(">Q", len(record.canonical)))
    chunks.append(record.canonical)


def _fp1_of(payload: bytes) -> str:
    """The self-describing fp1 string for ciphertext bytes."""
    digest = hashlib.sha256(payload).hexdigest()
    return f"fp1:sha256:{digest}"


def _storage_failure(reason: str, *, retryable: bool, context: dict[str, object]) -> TypedRefusal:
    """Build a CT-04 ``storage failure`` refusal for a CT-14 boundary fault (AC4)."""
    return unpersistable(
        reason,
        retryability=Retryability.YES if retryable else Retryability.NO,
        context=context,
    )
