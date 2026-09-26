"""CT-14 public value types for off-machine backup and restore.

Split from :mod:`qmf.data.backup` so the primitive module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.backup`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol

from qmf.core import Result, World
from qmf.data.store.rooms import RoomRole

__all__ = [
    "BACKUP_CONTRACT_FORMAT_VERSION",
    "ENCRYPTION_REQUIRED",
    "BackupCopyReceipt",
    "ObjectStorage",
    "OffMachineCopy",
    "PayloadCipher",
    "RestoreReceipt",
    "StoragePutAck",
]

# CT-14's first minted format version (DEC-0103; versioning-from-birth L15).
BACKUP_CONTRACT_FORMAT_VERSION: Final[int] = 1

# Encryption is required; key custody is named at the node/ops sitting (DEC-0118).
ENCRYPTION_REQUIRED: Final[bool] = True


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
    holds key material; the adapter encrypts plaintext to opaque ciphertext (and
    decrypts on restore) and returns value-or-refusal so a missing key or crypto
    failure stays a typed refusal, never an exception across the CT-14 boundary
    (DEC-0109, DEC-0118).
    """

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:  # pragma: no cover - protocol
        """Return ciphertext for ``plaintext``, or a typed refusal."""
        ...

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:  # pragma: no cover - protocol
        """Return plaintext for ``ciphertext``, or a typed refusal."""
        ...


class ObjectStorage(Protocol):
    """Provider-neutral destination for encrypted, versioned off-machine copies (AC5).

    Injected at the composition root. Object-key layout, provider selection, and
    credentials stay outside QMF — this port accepts an already-encrypted payload
    identified by world, ordinal version, and room-role, and returns value-or-refusal
    (DEC-0118, DEC-0045). An unreachable bucket, rejected upload/download, or corrupt
    copy is a ``storage failure`` refusal; the port never raises across the package seam.
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

    def get(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        format_version: int,
    ) -> Result[bytes]:  # pragma: no cover - protocol
        """Fetch one versioned encrypted object as opaque ciphertext (value-or-refusal)."""
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


@dataclass(frozen=True, slots=True)
class RestoreReceipt:
    """Completion evidence for one CT-14 restore into a replacement store (AC1).

    Returned only after every exported record lands in the replacement store.
    ``replacement_root`` names the target store's root so the caller can prove the
    restore did not rewrite the source path. No credential fields are carried.
    """

    world: World
    copy_version: int | None
    source_room_role: RoomRole
    record_count: int
    replacement_root: str
    format_version: int = BACKUP_CONTRACT_FORMAT_VERSION
    encryption_required: bool = ENCRYPTION_REQUIRED
