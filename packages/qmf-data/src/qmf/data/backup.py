"""CT-14 — encrypted, versioned off-machine backup and restore (COMP-QMF-DATA-BACKUP).

Consumes the CT-26 :class:`~qmf.data.store.backup_input.RoomExport` input and produces
a **new** encrypted, versioned off-machine artifact through an injected
:class:`ObjectStorage` port. The restore primitive fetches that artifact, decrypts it,
and writes into a **replacement** :class:`~qmf.data.store.EvidenceStore` — never rewriting
the only local copy in place. QMF owns the backup/restore/verify *primitives*; the
nightly cadence and its execution stay application/ops-owned (DEC-0118).

Hard rules this seam enforces:

* Encryption is **required** — a :class:`PayloadCipher` is injected at the composition
  root; key custody and the crypto dependency are node/ops-sitting items (AC5).
* Every successful copy is a distinct ``copy_version``; the primitive never mutates
  an earlier artifact or the only local evidence copy (AC2).
* Restore always targets a replacement store root; an in-place rewrite of the source
  store is a ``policy rejection``, and discarding the only local raw copy is refused
  under this component's authority (FM-5, DEC-0118).
* Restored int64 UTC-ns timestamps pass through verbatim from the framed canonical
  bytes — never re-derived under a later calendar identity or tzdata version (DEC-0106).
* Restored reads still enforce the 12-month seal when a :class:`~qmf.data.seal.HoldoutSeal`
  is wired into the replacement store (FM-4, DEC-0119).
* Cross-world copy/restore and ``world = simulated`` are ``policy rejection`` refusals
  (AC3, DEC-0117, DEC-0110).
* Unreachable storage, a rejected upload/download, or a corrupt copy yields a ``storage
  failure`` typed refusal — never raised across the boundary, and never reported as
  completion (AC4).
* Object-key layout, provider selection, numeric RPO/RTO/retention, and credentials
  are **not** baked in; no credential enters the receipt or evidence (AC5, DEC-0045).

Stdlib + qmf-core + the store's CT-26 types only (default-deny; L30).
"""

from __future__ import annotations

import json
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Protocol, TypedDict, cast

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    World,
    WriterId,
    fingerprint_bytes,
    is_refusal,
    unpersistable,
)
from qmf.data.store.backup_input import RecordExport, RoomExport
from qmf.data.store.facade import EvidenceStore, WorldStore
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.store.rooms import RoomRole

__all__ = [
    "BACKUP_CONTRACT_FORMAT_VERSION",
    "ENCRYPTION_REQUIRED",
    "BackupCopyReceipt",
    "ObjectStorage",
    "OffMachineBackup",
    "OffMachineCopy",
    "OffMachineRestore",
    "PayloadCipher",
    "RestoreReceipt",
    "StoragePutAck",
]

# CT-14's first minted format version (DEC-0103; versioning-from-birth L15).
BACKUP_CONTRACT_FORMAT_VERSION: Final[int] = 1

# Encryption is required; key custody is named at the node/ops sitting (DEC-0118).
ENCRYPTION_REQUIRED: Final[bool] = True

# Framing magic so restore can recognize the plaintext envelope.
_PLAINTEXT_MAGIC: Final[bytes] = b"QMFB1\0"

# Writer identity used when re-appending journal / lineage lines during restore.
# The acquired stream name (not this token's stream field) owns the one-writer hold.
_RESTORE_MACHINE: Final[str] = "qmf-restore"
_RESTORE_ROLE: Final[str] = "backup"
_RESTORE_BOOT: Final[str] = "restore-1"


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
        gate = _governed_world(export.world, for_world, field_label="export_world")
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
            remapped = _remapped_adapter_context(put, copy_version=copy_version)
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


class OffMachineRestore:
    """The CT-14 restore primitive: fetch + decrypt + write into a replacement store.

    Constructed with the same :class:`ObjectStorage` / :class:`PayloadCipher` ports as
    backup. Every restore lands in a **replacement** :class:`EvidenceStore` root; the
    source store is never rewritten or deleted under this component's authority
    (DEC-0118). Restored reads enforce the wired seal and world isolation exactly as
    live reads do (DEC-0119, DEC-0117).
    """

    def __init__(self, storage: ObjectStorage, cipher: PayloadCipher) -> None:
        self._storage = storage
        self._cipher = cipher

    def restore_copy(
        self,
        *,
        world: object,
        copy_version: int,
        source_room_role: object,
        into: EvidenceStore,
        for_world: object,
        source_store: EvidenceStore | None = None,
    ) -> Result[RestoreReceipt]:
        """Fetch one versioned off-machine copy and restore it into ``into`` (AC1–AC4).

        ``for_world`` must match the copy's world. ``into`` must be a distinct store
        root from ``source_store`` when the source is supplied — an in-place rewrite
        of the only copy is a ``policy rejection``.
        """
        role = _coerce_role(source_room_role)
        if role is None:
            return invalid_input(
                "source_room_role",
                "source_room_role is one of the seven room-roles",
                given=repr(source_room_role),
                allowed=[member.value for member in RoomRole],
            )
        if isinstance(copy_version, bool) or copy_version < 1:
            return invalid_input(
                "copy_version",
                "copy_version is a positive ordinal identifying one off-machine artifact",
                given=repr(copy_version),
            )
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return invalid_input(
                "world",
                "world is a World or one of the closed set live | replay | simulated",
                given=repr(world),
            )
        gate = _governed_world(resolved_world, for_world, field_label="copy_world")
        if is_refusal(gate):
            return gate

        blocked = _refuse_in_place(into, source_store)
        if blocked is not None:
            return blocked

        try:
            fetched = self._storage.get(
                world=resolved_world.value,
                copy_version=copy_version,
                source_room_role=role.value,
                format_version=BACKUP_CONTRACT_FORMAT_VERSION,
            )
        except Exception as exc:
            return _storage_failure(
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
            if fetched.category is RefusalCategory.STORAGE_FAILURE:
                return fetched
            remapped = _remapped_adapter_context(fetched, copy_version=copy_version)
            return _storage_failure(
                "object storage refused the off-machine get; completion is not claimed "
                "(DEC-0109, DEC-0118)",
                retryable=fetched.retryability is Retryability.YES,
                context=remapped,
            )
        ciphertext = fetched.value
        if not ciphertext:
            return _storage_failure(
                "object storage returned an empty payload; a missing or corrupt copy "
                "yields no restore completion (DEC-0118)",
                retryable=False,
                context={"signal": "corrupt-copy", "copy_version": copy_version},
            )

        try:
            decrypted = self._cipher.decrypt(ciphertext)
        except Exception as exc:
            return _storage_failure(
                "payload cipher raised while decrypting the backup copy; completion "
                "is not claimed (DEC-0109, DEC-0118)",
                retryable=False,
                context={"signal": "cipher-raised", "error_type": type(exc).__name__},
            )
        if is_refusal(decrypted):
            return decrypted
        plaintext = decrypted.value
        export = _unframe_plaintext(plaintext)
        if is_refusal(export):
            return export
        if export.value.world is not resolved_world:
            return policy_rejection(
                "world",
                "the decrypted copy's world does not match the requested restore world; "
                "storage separation delivers world isolation (DEC-0117)",
                requested=resolved_world.value,
                export_world=export.value.world.value,
            )
        if export.value.source_room_role is not role:
            return policy_rejection(
                "source_room_role",
                "the decrypted copy's room-role does not match the requested restore role",
                requested=role.value,
                export_role=export.value.source_room_role.value,
            )
        return self.restore_export(
            export.value,
            into=into,
            for_world=for_world,
            source_store=source_store,
            copy_version=copy_version,
        )

    def restore_export(
        self,
        export: RoomExport,
        *,
        into: EvidenceStore,
        for_world: object,
        source_store: EvidenceStore | None = None,
        copy_version: int | None = None,
    ) -> Result[RestoreReceipt]:
        """Write ``export`` into a replacement store without touching the source (AC1–AC4).

        Timestamps stay the verbatim CT-26 canonical bytes. Cross-world /
        ``world = simulated`` is a ``policy rejection``. When ``source_store`` is given,
        ``into`` must resolve to a different filesystem root.
        """
        gate = _governed_world(export.world, for_world, field_label="export_world")
        if is_refusal(gate):
            return gate
        world = gate.value

        blocked = _refuse_in_place(into, source_store)
        if blocked is not None:
            return blocked

        target = into.for_world(world)
        if is_refusal(target):
            return target

        written = _write_export(export, target.value)
        if is_refusal(written):
            return written

        return Ok(
            RestoreReceipt(
                world=world,
                copy_version=copy_version,
                source_room_role=export.source_room_role,
                record_count=written.value,
                replacement_root=str(into.root.resolve()),
            )
        )

    def discard_local_raw(self, store: EvidenceStore) -> Result[None]:
        """Refuse any attempt to delete the only local raw evidence copy (FM-5).

        Raw originals and lineage are kept forever under this component's authority;
        retention deletion of the only local copy does not proceed (DEC-0118).
        """
        del store
        return policy_rejection(
            "local_raw",
            "discarding the only local raw evidence copy is refused under "
            "COMP-QMF-DATA-BACKUP authority; raw originals and lineage are kept "
            "forever (DEC-0118)",
            signal="refuse-delete-only-copy",
        )


def _refuse_in_place(
    into: EvidenceStore, source_store: EvidenceStore | None
) -> TypedRefusal | None:
    """A policy rejection when restore would rewrite the only local store in place."""
    if source_store is None:
        return None
    if into is source_store or into.root.resolve() == source_store.root.resolve():
        return policy_rejection(
            "replacement_store",
            "a restore must target a replacement store root; rewriting the only local "
            "copy in place is refused (DEC-0118)",
            signal="refuse-in-place-restore",
            replacement_root=str(into.root.resolve()),
            source_root=str(source_store.root.resolve()),
        )
    return None


def _write_export(export: RoomExport, bundle: WorldStore) -> Result[int]:
    """Persist every record of ``export`` into ``bundle``; return the written count."""
    role = export.source_room_role
    if role is RoomRole.IMMUTABLE_RAW_ARCHIVE:
        return _restore_raw(export.records, bundle)
    if role is RoomRole.REGISTRY_ROOM:
        return _restore_registry(export.records, bundle)
    if role is RoomRole.JOURNAL:
        return _restore_journal(export.records, bundle)
    # Rebuildable / unpopulated rooms export empty in V1 — nothing to write.
    if export.record_count == 0:
        return Ok(0)
    return invalid_input(
        "source_room_role",
        "this room-role has no restore writer in V1; only the immutable raw archive, "
        "journal, and registry room are restored from a CT-26 export",
        given=role.value,
    )


def _restore_raw(records: tuple[RecordExport, ...], bundle: WorldStore) -> Result[int]:
    """Re-admit raw-archive artifacts from verbatim canonical bytes."""
    count = 0
    for record in records:
        rows = _decode_rows(record.canonical)
        if is_refusal(rows):
            return rows
        result = bundle.append_store.append_raw(
            rows.value, presented_fingerprint=record.fingerprint
        )
        if is_refusal(result):
            return result
        count += 1
    return Ok(count)


def _restore_registry(records: tuple[RecordExport, ...], bundle: WorldStore) -> Result[int]:
    """Re-admit registry records and lineage edges from verbatim canonical bytes."""
    count = 0
    for record in records:
        decoded = _decode_mapping(record.canonical)
        if is_refusal(decoded):
            return decoded
        payload = decoded.value
        if _is_registry_envelope(payload):
            body = payload["body"]
            if not isinstance(body, Mapping):
                return invalid_input(
                    "canonical",
                    "a registry record envelope's body must be a mapping",
                    given=repr(body),
                )
            result = bundle.registry_room.put_record(
                cast("Mapping[str, object]", body),
                kind=payload["kind"],
                format_version=payload["format_version"],
                presented_fingerprint=record.fingerprint,
            )
        else:
            stream = record.stream if record.stream is not None else "restored-lineage"
            writer = _restore_writer(stream)
            if is_refusal(writer):
                return writer
            result = bundle.registry_room.append_lineage_edge(
                stream, writer.value, payload, presented_fingerprint=record.fingerprint
            )
        if is_refusal(result):
            return result
        count += 1
    return Ok(count)


def _restore_journal(records: tuple[RecordExport, ...], bundle: WorldStore) -> Result[int]:
    """Re-admit journal events from verbatim canonical bytes into their streams."""
    count = 0
    for record in records:
        decoded = _decode_mapping(record.canonical)
        if is_refusal(decoded):
            return decoded
        stream = record.stream if record.stream is not None else "restored"
        writer = _restore_writer(stream)
        if is_refusal(writer):
            return writer
        result = bundle.journal.append(
            stream, writer.value, decoded.value, presented_fingerprint=record.fingerprint
        )
        if is_refusal(result):
            return result
        count += 1
    return Ok(count)


def _restore_writer(stream: str) -> Result[WriterId]:
    """A WriterId for restore re-appends under ``stream``."""
    return WriterId.try_create(_RESTORE_MACHINE, _RESTORE_ROLE, stream, _RESTORE_BOOT)


def _is_registry_envelope(payload: Mapping[str, object]) -> bool:
    """Whether ``payload`` is the CT-09 full-record envelope (kind/format_version/body)."""
    return (
        "kind" in payload
        and "format_version" in payload
        and "body" in payload
        and isinstance(payload["kind"], str)
        and isinstance(payload["format_version"], int)
        and not isinstance(payload["format_version"], bool)
    )


def _decode_rows(canonical: bytes) -> Result[list[dict[str, object]]]:
    """Decode raw-archive canonical bytes to the ordered row list."""
    try:
        decoded: object = json.loads(canonical)
    except ValueError as exc:
        return _storage_failure(
            "restored raw-archive canonical bytes are corrupt JSON; completion is not "
            "claimed (DEC-0109, DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "error": str(exc)},
        )
    if not isinstance(decoded, list):
        return invalid_input(
            "canonical",
            "raw-archive canonical bytes must decode to a non-empty list of row mappings",
            given=repr(decoded)[:200],
        )
    decoded_rows = cast("list[object]", decoded)
    if not decoded_rows:
        return invalid_input(
            "canonical",
            "raw-archive canonical bytes must decode to a non-empty list of row mappings",
            given=repr(decoded_rows)[:200],
        )
    rows: list[dict[str, object]] = []
    for item in decoded_rows:
        if not isinstance(item, Mapping):
            return invalid_input(
                "canonical",
                "each raw-archive row must be a mapping",
                given=repr(item)[:200],
            )
        rows.append(dict(cast("Mapping[str, object]", item)))
    return Ok(rows)


def _decode_mapping(canonical: bytes) -> Result[dict[str, object]]:
    """Decode journal / registry / lineage canonical bytes to a mapping."""
    try:
        decoded: object = json.loads(canonical)
    except ValueError as exc:
        return _storage_failure(
            "restored record canonical bytes are corrupt JSON; completion is not "
            "claimed (DEC-0109, DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "error": str(exc)},
        )
    if not isinstance(decoded, Mapping):
        return invalid_input(
            "canonical",
            "journal / registry / lineage canonical bytes must decode to a mapping",
            given=repr(decoded)[:200],
        )
    return Ok(dict(cast("Mapping[str, object]", decoded)))


def _governed_world(expected: World, for_world: object, *, field_label: str) -> Result[World]:
    """Resolve and gate ``for_world`` against ``expected``; refuse simulated/cross-world."""
    if for_world is None:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "for_world",
                "reason": (
                    "a backup/restore must declare the world it operates as; there is "
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
                    "world = simulated has no governed namespace in V1; a backup/restore "
                    "into governed evidence is refused (DEC-0110, DEC-0117)"
                ),
                "requested": resolved.value,
            },
        )
    if resolved is not expected:
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": (
                    "a backup/restore that crosses worlds is refused; storage separation "
                    "delivers world isolation (DEC-0117)"
                ),
                "requested": resolved.value,
                field_label: expected.value,
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


def _coerce_role(value: object) -> RoomRole | None:
    """Resolve a :class:`RoomRole` or its string value, or ``None``."""
    if isinstance(value, RoomRole):
        return value
    if isinstance(value, str):
        try:
            return RoomRole(value)
        except ValueError:
            return None
    return None


def _frame_plaintext(export: RoomExport) -> bytes:
    """Frame one room export so record canonical bytes (timestamps) pass through verbatim.

    Metadata is length-prefixed UTF-8; each record's fingerprint, optional stream
    segment, and canonical bytes follow as length-prefixed blobs. The canonical payload
    is never re-serialized, so int64 UTC-ns timestamps remain exactly the stored bytes
    (DEC-0106).
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
    """Append one verbatim record frame (fingerprint, stream, canonical) to ``chunks``."""
    fp = record.fingerprint.encode("utf-8")
    chunks.append(struct.pack(">I", len(fp)))
    chunks.append(fp)
    stream = (record.stream or "").encode("utf-8")
    chunks.append(struct.pack(">I", len(stream)))
    chunks.append(stream)
    chunks.append(struct.pack(">Q", len(record.canonical)))
    chunks.append(record.canonical)


def _unframe_plaintext(plaintext: bytes) -> Result[RoomExport]:
    """Parse a framed plaintext envelope back into a :class:`RoomExport`."""
    if not plaintext.startswith(_PLAINTEXT_MAGIC):
        return _storage_failure(
            "decrypted payload is not a CT-14 backup envelope; the copy is corrupt "
            "and restore completion is not claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "detail": "bad-magic"},
        )
    offset = len(_PLAINTEXT_MAGIC)
    try:
        meta_len, offset = _read_u32(plaintext, offset)
        meta_raw = plaintext[offset : offset + meta_len]
        offset += meta_len
        if len(meta_raw) != meta_len:
            raise ValueError("truncated meta")
        meta = _parse_meta(meta_raw.decode("utf-8"))
        records: list[RecordExport] = []
        for _ in range(meta["count"]):
            record, offset = _read_record(plaintext, offset)
            records.append(record)
        if offset != len(plaintext):
            raise ValueError("trailing bytes after framed records")
    except (ValueError, KeyError, UnicodeDecodeError, struct.error) as exc:
        return _storage_failure(
            "decrypted backup envelope is corrupt or truncated; restore completion "
            "is not claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "error": str(exc)},
        )
    world = _coerce_world(meta["world"])
    if world is None:
        return _storage_failure(
            "decrypted backup envelope carries an unknown world; restore completion "
            "is not claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "world": meta["world"]},
        )
    role = _coerce_role(meta["role"])
    if role is None:
        return _storage_failure(
            "decrypted backup envelope carries an unknown room-role; restore "
            "completion is not claimed (DEC-0118)",
            retryable=False,
            context={"signal": "corrupt-copy", "role": meta["role"]},
        )
    return Ok(
        RoomExport(
            world=world,
            source_room_role=role,
            format_version=meta["format_version"],
            records=tuple(records),
        )
    )


class _BackupMeta(TypedDict):
    """Typed fields from the framed UTF-8 backup meta block."""

    format_version: int
    world: str
    role: str
    count: int


def _parse_meta(text: str) -> _BackupMeta:
    """Parse the framed UTF-8 meta block into typed fields."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key] = value
    return {
        "format_version": int(fields["v"]),
        "world": fields["world"],
        "role": fields["role"],
        "count": int(fields["count"]),
    }


def _read_record(buf: bytes, offset: int) -> tuple[RecordExport, int]:
    """Read one framed record starting at ``offset``; return it and the new offset."""
    fp_len, offset = _read_u32(buf, offset)
    fp = buf[offset : offset + fp_len].decode("utf-8")
    offset += fp_len
    stream_len, offset = _read_u32(buf, offset)
    stream_raw = buf[offset : offset + stream_len].decode("utf-8")
    offset += stream_len
    can_len, offset = _read_u64(buf, offset)
    canonical = buf[offset : offset + can_len]
    offset += can_len
    if len(canonical) != can_len:
        raise ValueError("truncated canonical")
    return (
        RecordExport(
            fingerprint=fp,
            canonical=canonical,
            stream=stream_raw or None,
        ),
        offset,
    )


def _read_u32(buf: bytes, offset: int) -> tuple[int, int]:
    """Read a big-endian uint32 from ``buf`` at ``offset``."""
    end = offset + 4
    if end > len(buf):
        raise ValueError("truncated u32")
    return struct.unpack(">I", buf[offset:end])[0], end


def _read_u64(buf: bytes, offset: int) -> tuple[int, int]:
    """Read a big-endian uint64 from ``buf`` at ``offset``."""
    end = offset + 8
    if end > len(buf):
        raise ValueError("truncated u64")
    return struct.unpack(">Q", buf[offset:end])[0], end


def _fp1_of(payload: bytes) -> str:
    """The self-describing fp1 string for ciphertext bytes."""
    return fingerprint_bytes(payload).value


def _remapped_adapter_context(refusal: TypedRefusal, *, copy_version: int) -> dict[str, object]:
    """Remap a miswired adapter's refusal context for the CT-14 storage-failure remap (AC4; R-007).

    The adapter returned a non-``storage failure`` category; AC4 remaps it to a *returned*
    ``storage failure`` at this boundary. The adapter's own ``reason`` context key — which
    every qmf refusal builder (``policy_rejection`` / ``invalid_input`` / ``unpersistable``)
    sets unconditionally — is namespaced to ``adapter_reason`` so it never collides with the
    reserved ``reason`` key :func:`qmf.core.unpersistable` sets from its own argument. Handing
    that reserved key through would be refused as a programmer error and *raise* across the
    boundary, which R-007/DEC-0109 forbids.
    """
    remapped: dict[str, object] = dict(refusal.context)
    adapter_reason = remapped.pop("reason", None)
    if adapter_reason is not None:
        remapped["adapter_reason"] = adapter_reason
    remapped["signal"] = "storage-refused"
    remapped["adapter_category"] = refusal.category.value
    remapped["copy_version"] = copy_version
    return remapped


def _storage_failure(reason: str, *, retryable: bool, context: dict[str, object]) -> TypedRefusal:
    """Build a CT-04 ``storage failure`` refusal for a CT-14 boundary fault (AC4)."""
    return unpersistable(
        reason,
        retryability=Retryability.YES if retryable else Retryability.NO,
        context=context,
    )
