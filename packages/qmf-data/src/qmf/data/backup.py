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

Framing, world gates, encrypt/put/get, and restore writers live in sibling modules;
this module keeps the public primitive classes and re-exports the public types.
"""

from __future__ import annotations

from qmf.core import Ok, Result, is_refusal
from qmf.data.backup_copy import encrypt_backup_payload, load_copy_export, put_encrypted_copy
from qmf.data.backup_frame import frame_plaintext
from qmf.data.backup_gate import bind_restore_copy, governed_world, refuse_in_place
from qmf.data.backup_storage import fp1_of
from qmf.data.backup_types import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    ENCRYPTION_REQUIRED,
    BackupCopyReceipt,
    ObjectStorage,
    OffMachineCopy,
    PayloadCipher,
    RestoreReceipt,
    StoragePutAck,
)
from qmf.data.backup_write import write_export
from qmf.data.store.backup_input import RoomExport
from qmf.data.store.facade import EvidenceStore
from qmf.data.store.refusals import policy_rejection

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
        gate = governed_world(export.world, for_world, field_label="export_world")
        if is_refusal(gate):
            return gate
        copy_version = self._next_version
        # Advance before the put so a failed attempt never reuses the ordinal on retry
        # (each off-machine copy is a distinct versioned artifact — AC2).
        self._next_version = copy_version + 1
        ciphertext = encrypt_backup_payload(
            self._cipher, frame_plaintext(export), copy_version=copy_version
        )
        if is_refusal(ciphertext):
            return ciphertext
        put = put_encrypted_copy(
            self._storage,
            OffMachineCopy(
                world=gate.value,
                copy_version=copy_version,
                source_room_role=export.source_room_role,
                payload=ciphertext.value,
            ),
        )
        if is_refusal(put):
            return put
        return Ok(
            BackupCopyReceipt(
                world=gate.value,
                copy_version=copy_version,
                source_room_role=export.source_room_role,
                payload_fingerprint=fp1_of(ciphertext.value),
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
        bound = bind_restore_copy(
            world=world,
            copy_version=copy_version,
            source_room_role=source_room_role,
            into=into,
            for_world=for_world,
            source_store=source_store,
        )
        if is_refusal(bound):
            return bound
        export = load_copy_export(self._storage, self._cipher, bound.value)
        if is_refusal(export):
            return export
        return self.restore_export(
            export.value,
            into=into,
            for_world=for_world,
            source_store=source_store,
            copy_version=bound.value.copy_version,
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
        gate = governed_world(export.world, for_world, field_label="export_world")
        if is_refusal(gate):
            return gate
        world = gate.value

        blocked = refuse_in_place(into, source_store)
        if blocked is not None:
            return blocked

        target = into.for_world(world)
        if is_refusal(target):
            return target

        written = write_export(export, target.value)
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
        _ = store
        return policy_rejection(
            "local_raw",
            "discarding the only local raw evidence copy is refused under "
            "COMP-QMF-DATA-BACKUP authority; raw originals and lineage are kept "
            "forever (DEC-0118)",
            signal="refuse-delete-only-copy",
        )
