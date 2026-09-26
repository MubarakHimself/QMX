"""Encrypt, put, fetch, and decrypt one CT-14 off-machine copy."""

from __future__ import annotations

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    is_refusal,
)
from qmf.data.backup_frame import unframe_plaintext
from qmf.data.backup_gate import RestoreCopySpec
from qmf.data.backup_storage import remapped_adapter_context, storage_failure
from qmf.data.backup_types import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    ObjectStorage,
    OffMachineCopy,
    PayloadCipher,
    StoragePutAck,
)
from qmf.data.store.backup_input import RoomExport
from qmf.data.store.refusals import policy_rejection
from qmf.data.store.rooms import RoomRole


def encrypt_backup_payload(
    cipher: PayloadCipher, plaintext: bytes, *, copy_version: int
) -> Result[bytes]:
    """Encrypt framed export bytes; empty ciphertext is a corrupt copy."""
    try:
        encrypted = cipher.encrypt(plaintext)
    except Exception as exc:
        return storage_failure(
            "payload cipher raised while encrypting the backup copy; completion "
            "is not claimed (DEC-0109, DEC-0118)",
            retryable=False,
            context={"signal": "cipher-raised", "error_type": type(exc).__name__},
        )
    if is_refusal(encrypted):
        return encrypted
    ciphertext = encrypted.value
    if not ciphertext:
        return storage_failure(
            "payload cipher returned empty ciphertext; encryption is required and "
            "an empty payload is treated as a corrupt copy — completion is not "
            "claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "copy_version": copy_version},
        )
    return Ok(ciphertext)


def put_encrypted_copy(storage: ObjectStorage, artifact: OffMachineCopy) -> Result[StoragePutAck]:
    """Put one versioned ciphertext; remap non-storage-failure adapter refusals (AC4)."""
    try:
        put = storage.put(
            world=artifact.world.value,
            copy_version=artifact.copy_version,
            source_room_role=artifact.source_room_role.value,
            payload=artifact.payload,
            format_version=artifact.format_version,
        )
    except Exception as exc:
        return storage_failure(
            "object storage raised during the off-machine put; completion is not "
            "claimed (DEC-0109, DEC-0118)",
            retryable=True,
            context={
                "signal": "storage-raised",
                "error_type": type(exc).__name__,
                "copy_version": artifact.copy_version,
            },
        )
    if not is_refusal(put):
        return put
    # AC4: unreachable / rejected / corrupt object storage is always a
    # storage-failure refusal at this boundary, even if a miswired adapter
    # returned a different category.
    if put.category is RefusalCategory.STORAGE_FAILURE:
        return put
    remapped = remapped_adapter_context(put, copy_version=artifact.copy_version)
    return storage_failure(
        "object storage refused the off-machine put; completion is not claimed "
        "(DEC-0109, DEC-0118)",
        retryable=put.retryability is Retryability.YES,
        context=remapped,
    )


def fetch_copy_ciphertext(
    storage: ObjectStorage, *, world: World, copy_version: int, role: RoomRole
) -> Result[bytes]:
    """Fetch one versioned ciphertext; empty payload is a corrupt copy."""
    try:
        fetched = storage.get(
            world=world.value,
            copy_version=copy_version,
            source_room_role=role.value,
            format_version=BACKUP_CONTRACT_FORMAT_VERSION,
        )
    except Exception as exc:
        return storage_failure(
            "object storage raised during the off-machine get; completion is not "
            "claimed (DEC-0109, DEC-0118)",
            retryable=True,
            context={
                "signal": "storage-raised",
                "error_type": type(exc).__name__,
                "copy_version": copy_version,
            },
        )
    if is_refusal(fetched):
        return remap_get_refusal(fetched, copy_version=copy_version)
    ciphertext = fetched.value
    if not ciphertext:
        return storage_failure(
            "object storage returned an empty payload; a missing or corrupt copy "
            "yields no restore completion (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "copy_version": copy_version},
        )
    return Ok(ciphertext)


def decrypt_framed_export(
    cipher: PayloadCipher, ciphertext: bytes, *, world: World, role: RoomRole
) -> Result[RoomExport]:
    """Decrypt and unframe a copy; refuse world/role mismatch on the envelope."""
    try:
        decrypted = cipher.decrypt(ciphertext)
    except Exception as exc:
        return storage_failure(
            "payload cipher raised while decrypting the backup copy; completion "
            "is not claimed (DEC-0109, DEC-0118)",
            retryable=False,
            context={"signal": "cipher-raised", "error_type": type(exc).__name__},
        )
    if is_refusal(decrypted):
        return decrypted
    export = unframe_plaintext(decrypted.value)
    if is_refusal(export):
        return export
    return _match_export_identity(export.value, world=world, role=role)


def load_copy_export(
    storage: ObjectStorage, cipher: PayloadCipher, spec: RestoreCopySpec
) -> Result[RoomExport]:
    """Fetch, decrypt, and unframe one bound off-machine copy."""
    fetched = fetch_copy_ciphertext(
        storage, world=spec.world, copy_version=spec.copy_version, role=spec.role
    )
    if is_refusal(fetched):
        return fetched
    return decrypt_framed_export(cipher, fetched.value, world=spec.world, role=spec.role)


def remap_get_refusal(fetched: TypedRefusal, *, copy_version: int) -> Result[bytes]:
    """AC4: a non-storage-failure adapter get is remapped at this boundary."""
    if fetched.category is RefusalCategory.STORAGE_FAILURE:
        return fetched
    remapped = remapped_adapter_context(fetched, copy_version=copy_version)
    return storage_failure(
        "object storage refused the off-machine get; completion is not claimed "
        "(DEC-0109, DEC-0118)",
        retryable=fetched.retryability is Retryability.YES,
        context=remapped,
    )


def _match_export_identity(
    export: RoomExport, *, world: World, role: RoomRole
) -> Result[RoomExport]:
    """Refuse a decrypted copy whose world or room-role does not match the request."""
    if export.world is not world:
        return policy_rejection(
            "world",
            "the decrypted copy's world does not match the requested restore world; "
            "storage separation delivers world isolation (DEC-0117)",
            requested=world.value,
            export_world=export.world.value,
        )
    if export.source_room_role is not role:
        return policy_rejection(
            "source_room_role",
            "the decrypted copy's room-role does not match the requested restore role",
            requested=role.value,
            export_role=export.source_room_role.value,
        )
    return Ok(export)
