"""CT-14 verify primitives — sample-restore and full-restore rehearsal (Story 5.3).

Recoverability is claimed **only** through these primitives (SCN-0004, DEC-0118) —
never from the mere existence of an off-machine snapshot. A corrupt or failed restore
yields a ``storage failure`` refusal and no claim. Migrations run the ratified
sequence ``preflight → backup-first → dry-run → migrate → verify`` against a
documented restore path and never mutate the only copy in place (AR-32, DEC-0118).

Numeric restore-verification cadence, RPO, RTO, and retention depth stay
node/ops-sitting items — this module exposes null pointers only and never fills
``registry:restore_verification_cadence``, ``registry:backup_recovery_point_objective``,
``registry:backup_recovery_time_objective``, or ``registry:backup_retention_period``
from a recommendation (AC4, SCN-0004).

Stdlib + qmf-core + the CT-14 backup/restore types only (default-deny; L30).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

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
from qmf.data.backup import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    BackupCopyReceipt,
    ObjectStorage,
    OffMachineBackup,
    OffMachineRestore,
    PayloadCipher,
    RestoreReceipt,
)
from qmf.data.store.backup_input import RecordExport, RoomExport
from qmf.data.store.facade import EvidenceStore
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.store.rooms import RoomRole

__all__ = [
    "MIGRATION_SEQUENCE",
    "NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE",
    "NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE",
    "NODE_OPS_BACKUP_RETENTION_PERIOD",
    "NODE_OPS_RESTORE_VERIFICATION_CADENCE",
    "RESTORABLE_ROOM_ROLES",
    "MigrationStage",
    "OffMachineVerify",
    "RecoverabilityClaim",
    "RoomTransform",
    "StoreMigrationReport",
    "VerifiedRoom",
    "VerifyKind",
    "migrate_evidence",
    "refuse_snapshot_alone_claim",
]

# Node/ops-sitting numeric targets — deliberately None; never filled here (AC4).
NODE_OPS_RESTORE_VERIFICATION_CADENCE: Final[None] = None
NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE: Final[None] = None
NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE: Final[None] = None
NODE_OPS_BACKUP_RETENTION_PERIOD: Final[None] = None

# Room-roles the V1 restore writer can re-admit from a CT-26 export.
RESTORABLE_ROOM_ROLES: Final[tuple[RoomRole, ...]] = (
    RoomRole.IMMUTABLE_RAW_ARCHIVE,
    RoomRole.JOURNAL,
    RoomRole.REGISTRY_ROOM,
)


class VerifyKind(StrEnum):
    """The two ratified verify primitives (DEC-0118) — never optional add-ons."""

    SAMPLE_RESTORE = "sample-restore"
    FULL_RESTORE_REHEARSAL = "full-restore-rehearsal"


class MigrationStage(StrEnum):
    """One stage of the ratified never-in-place migration sequence (AR-32)."""

    PREFLIGHT = "preflight"
    BACKUP_FIRST = "backup-first"
    DRY_RUN = "dry-run"
    MIGRATE = "migrate"
    VERIFY = "verify"


MIGRATION_SEQUENCE: Final[tuple[MigrationStage, ...]] = (
    MigrationStage.PREFLIGHT,
    MigrationStage.BACKUP_FIRST,
    MigrationStage.DRY_RUN,
    MigrationStage.MIGRATE,
    MigrationStage.VERIFY,
)

RoomTransform = Callable[[RoomExport], Result[RoomExport]]
"""A pure per-room migration step: an export in, its migrated form (or a refusal) out."""


@dataclass(frozen=True, slots=True)
class VerifiedRoom:
    """One room-role that a verify primitive restored and read back successfully."""

    source_room_role: RoomRole
    copy_version: int
    record_count: int
    restore_receipt: RestoreReceipt


@dataclass(frozen=True, slots=True)
class RecoverabilityClaim:
    """Recoverability evidence — issued **only** by the verify primitives (AC1).

    A snapshot's existence alone never yields this value. ``documented_restore_path``
    names the path the verification compared against (typically the source store root
    whose CT-26 export was the expected evidence).
    """

    kind: VerifyKind
    world: World
    rooms: tuple[VerifiedRoom, ...]
    record_count: int
    replacement_root: str
    documented_restore_path: str
    format_version: int = BACKUP_CONTRACT_FORMAT_VERSION


@dataclass(frozen=True, slots=True)
class StoreMigrationReport:
    """Outcome of a staged store migration — never in-place (AC3; AR-32).

    ``restore_path`` is the source store root (untouched); ``backup_receipts`` are the
    CT-14 off-machine copies taken before any migrate write; ``recoverability`` is the
    claim issued by the verify stage's full-restore rehearsal.
    """

    restore_path: str
    backed_up: bool
    backup_receipts: tuple[BackupCopyReceipt, ...]
    stages_completed: tuple[MigrationStage, ...]
    preflight_count: int
    dry_run_count: int
    migrated_count: int
    destination_root: str
    recoverability: RecoverabilityClaim


def refuse_snapshot_alone_claim(
    *,
    world: object | None = None,
    copy_version: int | None = None,
    source_room_role: object | None = None,
) -> Result[RecoverabilityClaim]:
    """Refuse any attempt to claim recoverability from a snapshot alone (AC1).

    SCN-0004 / DEC-0118: recoverability is claimed only through sample-restore and
    full-restore rehearsal — never asserted from an off-machine copy existing.
    """
    del world, copy_version, source_room_role
    return policy_rejection(
        "recoverability",
        "recoverability is claimed only through the ratified verify primitives — "
        "automated sample-restore tests plus a periodic full-restore rehearsal — "
        "and is never asserted from a snapshot alone (SCN-0004, DEC-0118)",
        signal="refuse-snapshot-alone-claim",
    )


class OffMachineVerify:
    """First-class CT-14 verify primitives (sample-restore + full-restore rehearsal).

    Constructed with the same :class:`ObjectStorage` / :class:`PayloadCipher` ports as
    backup and restore. Every successful verify restores into a **replacement** store,
    reads the restored evidence back, and compares it to the documented expected export
    — only then is a :class:`RecoverabilityClaim` returned (AC1, AC2).
    """

    def __init__(
        self,
        storage: ObjectStorage,
        cipher: PayloadCipher,
        *,
        restore: OffMachineRestore | None = None,
    ) -> None:
        self._storage = storage
        self._cipher = cipher
        self._restore = restore if restore is not None else OffMachineRestore(storage, cipher)

    def sample_restore(
        self,
        *,
        world: object,
        copy_version: int,
        source_room_role: object,
        into: EvidenceStore,
        for_world: object,
        expected: RoomExport,
        source_store: EvidenceStore | None = None,
        documented_restore_path: str | None = None,
    ) -> Result[RecoverabilityClaim]:
        """Restore one room-role sample and confirm it against ``expected`` (AC1, AC2).

        A corrupt or mismatched restore is a ``storage failure`` — no recoverability
        claim is issued. ``documented_restore_path`` defaults to ``source_store.root``
        when the source is supplied.
        """
        path = _documented_path(documented_restore_path, source_store)
        if is_refusal(path):
            return path

        restored = self._restore.restore_copy(
            world=world,
            copy_version=copy_version,
            source_room_role=source_room_role,
            into=into,
            for_world=for_world,
            source_store=source_store,
        )
        if is_refusal(restored):
            return _as_verify_storage_failure(restored)

        checked = _confirm_restored_room(
            into,
            expected=expected,
            for_world=for_world,
            copy_version=copy_version,
            restore_receipt=restored.value,
        )
        if is_refusal(checked):
            return checked

        room = checked.value
        return Ok(
            RecoverabilityClaim(
                kind=VerifyKind.SAMPLE_RESTORE,
                world=expected.world,
                rooms=(room,),
                record_count=room.record_count,
                replacement_root=restored.value.replacement_root,
                documented_restore_path=path.value,
            )
        )

    def full_restore_rehearsal(
        self,
        *,
        world: object,
        copies: object,
        into: EvidenceStore,
        for_world: object,
        expected: Mapping[RoomRole, RoomExport],
        source_store: EvidenceStore | None = None,
        documented_restore_path: str | None = None,
    ) -> Result[RecoverabilityClaim]:
        """Restore every listed room-role and confirm each against ``expected`` (AC1, AC2).

        ``copies`` is a ``{RoomRole: copy_version}`` mapping or a sequence of
        ``(room_role, copy_version)`` pairs. One corrupt room aborts the rehearsal with
        a ``storage failure`` and no claim.
        """
        path = _documented_path(documented_restore_path, source_store)
        if is_refusal(path):
            return path

        pairs = _normalize_copies(copies)
        if is_refusal(pairs):
            return pairs
        if not pairs.value:
            return invalid_input(
                "copies",
                "a full-restore rehearsal names at least one (room-role, copy_version) pair",
                given=repr(copies),
            )

        rooms: list[VerifiedRoom] = []
        total = 0
        claim_world: World | None = None
        claim_root: str | None = None
        for role, version in pairs.value:
            exp = expected.get(role)
            if exp is None:
                return invalid_input(
                    "expected",
                    "every rehearsed room-role must have an expected CT-26 export to "
                    "compare against the documented restore path",
                    missing_role=role.value,
                )
            restored = self._restore.restore_copy(
                world=world,
                copy_version=version,
                source_room_role=role,
                into=into,
                for_world=for_world,
                source_store=source_store,
            )
            if is_refusal(restored):
                return _as_verify_storage_failure(restored)
            checked = _confirm_restored_room(
                into,
                expected=exp,
                for_world=for_world,
                copy_version=version,
                restore_receipt=restored.value,
            )
            if is_refusal(checked):
                return checked
            rooms.append(checked.value)
            total += checked.value.record_count
            claim_world = exp.world
            claim_root = restored.value.replacement_root

        # pairs.value is non-empty (guarded above), so both claim fields are set.
        if claim_world is None or claim_root is None:
            return invalid_input(
                "copies",
                "a full-restore rehearsal names at least one (room-role, copy_version) pair",
                given=repr(copies),
            )
        return Ok(
            RecoverabilityClaim(
                kind=VerifyKind.FULL_RESTORE_REHEARSAL,
                world=claim_world,
                rooms=tuple(rooms),
                record_count=total,
                replacement_root=claim_root,
                documented_restore_path=path.value,
            )
        )


def migrate_evidence(
    *,
    source: EvidenceStore,
    destination: EvidenceStore,
    verify_into: EvidenceStore,
    world: object,
    backup: OffMachineBackup,
    restore: OffMachineRestore,
    verify: OffMachineVerify,
    room_roles: Sequence[object] | None = None,
    transform: RoomTransform | None = None,
) -> Result[StoreMigrationReport]:
    """Run preflight → backup-first → dry-run → migrate → verify, never in-place (AC3).

    ``source`` stays the documented restore path and is only read. ``destination`` receives
    the migrated rooms and must be a distinct root. ``verify_into`` is a third distinct
    root used by the full-restore rehearsal so recoverability is proven through the
    verify primitive, never from the backup snapshot alone. The off-machine copies taken
    at backup-first are of the **source** evidence; the verify stage rehearses those
    copies against the preflight exports.
    """
    resolved = _coerce_world(world)
    if resolved is None:
        return invalid_input(
            "world",
            "world is a World or one of the closed set live | replay | simulated",
            given=repr(world),
        )
    if resolved is World.SIMULATED:
        return policy_rejection(
            "world",
            "world = simulated has no governed namespace in V1; a migration into "
            "governed evidence is refused (DEC-0110, DEC-0117)",
            requested=resolved.value,
        )

    roles = _resolve_roles(room_roles)
    if is_refusal(roles):
        return roles

    blocked = _refuse_overlapping_roots(source, destination, verify_into)
    if blocked is not None:
        return blocked

    # --- preflight: every room must already read back from the source ---
    expected: dict[RoomRole, RoomExport] = {}
    source_bundle = source.for_world(resolved)
    if is_refusal(source_bundle):
        return source_bundle
    for role in roles.value:
        export = source_bundle.value.backup_input.read_room(role, for_world=resolved)
        if is_refusal(export):
            return export
        expected[role] = export.value
    preflight_count = sum(exp.record_count for exp in expected.values())
    stages: list[MigrationStage] = [MigrationStage.PREFLIGHT]

    # --- backup-first: CT-14 off-machine copy of each room before any migrate write ---
    receipts: list[BackupCopyReceipt] = []
    copies: dict[RoomRole, int] = {}
    for role in roles.value:
        copied = backup.copy_export(expected[role], for_world=resolved)
        if is_refusal(copied):
            return copied
        receipts.append(copied.value)
        copies[role] = copied.value.copy_version
    stages.append(MigrationStage.BACKUP_FIRST)

    # --- dry-run: transform in memory; write nothing ---
    migrated_exports: list[RoomExport] = []
    for role in roles.value:
        candidate = expected[role]
        if transform is not None:
            transformed = transform(candidate)
            if is_refusal(transformed):
                return transformed
            candidate = transformed.value
            if candidate.world is not resolved:
                return invalid_input(
                    "transform",
                    "a migration transform must keep the room export in the migration world",
                    expected_world=resolved.value,
                    given_world=candidate.world.value,
                )
            if candidate.source_room_role is not role:
                return invalid_input(
                    "transform",
                    "a migration transform must keep the room-role it was handed",
                    expected_role=role.value,
                    given_role=candidate.source_room_role.value,
                )
        migrated_exports.append(candidate)
    dry_run_count = sum(exp.record_count for exp in migrated_exports)
    stages.append(MigrationStage.DRY_RUN)

    # --- migrate: write transformed exports into the destination (never the source) ---
    migrated_count = 0
    for export in migrated_exports:
        written = restore.restore_export(
            export,
            into=destination,
            for_world=resolved,
            source_store=source,
        )
        if is_refusal(written):
            return written
        migrated_count += written.value.record_count

    dest_bundle = destination.for_world(resolved)
    if is_refusal(dest_bundle):
        return dest_bundle
    for export in migrated_exports:
        landed = dest_bundle.value.backup_input.read_room(
            export.source_room_role, for_world=resolved
        )
        if is_refusal(landed):
            return landed
        if not _exports_match(export, landed.value):
            return _storage_failure(
                "migrated destination evidence does not match the dry-run transform; "
                "migration completion is not claimed (DEC-0109, DEC-0118)",
                context={
                    "signal": "migrate-mismatch",
                    "role": export.source_room_role.value,
                },
            )
    stages.append(MigrationStage.MIGRATE)

    # Source must still match the preflight exports (never mutated).
    for role, original in expected.items():
        again = source_bundle.value.backup_input.read_room(role, for_world=resolved)
        if is_refusal(again):
            return again
        if not _exports_match(original, again.value):
            return _storage_failure(
                "source evidence changed during migration; the only copy must stay "
                "intact as the documented restore path (AR-32, DEC-0118)",
                context={"signal": "source-mutated", "role": role.value},
            )

    # --- verify: full-restore rehearsal of the backup-first off-machine copies ---
    claim = verify.full_restore_rehearsal(
        world=resolved,
        copies=copies,
        into=verify_into,
        for_world=resolved,
        expected=expected,
        source_store=source,
        documented_restore_path=str(source.root.resolve()),
    )
    if is_refusal(claim):
        return claim
    stages.append(MigrationStage.VERIFY)

    return Ok(
        StoreMigrationReport(
            restore_path=str(source.root.resolve()),
            backed_up=True,
            backup_receipts=tuple(receipts),
            stages_completed=tuple(stages),
            preflight_count=preflight_count,
            dry_run_count=dry_run_count,
            migrated_count=migrated_count,
            destination_root=str(destination.root.resolve()),
            recoverability=claim.value,
        )
    )


def _documented_path(
    documented_restore_path: str | None, source_store: EvidenceStore | None
) -> Result[str]:
    """Resolve the documented restore path the claim will cite."""
    if documented_restore_path is not None and documented_restore_path.strip():
        return Ok(documented_restore_path)
    if source_store is not None:
        return Ok(str(source_store.root.resolve()))
    return invalid_input(
        "documented_restore_path",
        "a verify primitive must name a documented restore path (or supply source_store "
        "so the source root can be cited) — recoverability is never asserted from a "
        "snapshot alone (SCN-0004, DEC-0118)",
    )


def _confirm_restored_room(
    into: EvidenceStore,
    *,
    expected: RoomExport,
    for_world: object,
    copy_version: int,
    restore_receipt: RestoreReceipt,
) -> Result[VerifiedRoom]:
    """Read the restored room back and compare fingerprints/canonical bytes to expected."""
    bundle = into.for_world(expected.world)
    if is_refusal(bundle):
        return _as_verify_storage_failure(bundle)
    reread = bundle.value.backup_input.read_room(expected.source_room_role, for_world=for_world)
    if is_refusal(reread):
        return _as_verify_storage_failure(reread)
    if not _exports_match(expected, reread.value):
        return _storage_failure(
            "restored evidence does not match the documented restore path; a corrupt "
            "or incomplete restore yields no recoverability claim (DEC-0109, DEC-0118)",
            context={
                "signal": "verify-mismatch",
                "role": expected.source_room_role.value,
                "copy_version": copy_version,
                "expected_count": expected.record_count,
                "actual_count": reread.value.record_count,
            },
        )
    return Ok(
        VerifiedRoom(
            source_room_role=expected.source_room_role,
            copy_version=copy_version,
            record_count=expected.record_count,
            restore_receipt=restore_receipt,
        )
    )


def _exports_match(expected: RoomExport, actual: RoomExport) -> bool:
    """Byte-faithful comparison of two CT-26 room exports (order-independent)."""
    if expected.world is not actual.world:
        return False
    if expected.source_room_role is not actual.source_room_role:
        return False
    if expected.record_count != actual.record_count:
        return False
    exp = {_record_key(record) for record in expected.records}
    act = {_record_key(record) for record in actual.records}
    return exp == act


def _record_key(record: RecordExport) -> tuple[str, bytes, str | None]:
    """Identity key for one exported record."""
    return (record.fingerprint, record.canonical, record.stream)


def _normalize_copies(copies: object) -> Result[tuple[tuple[RoomRole, int], ...]]:
    """Normalize a copies mapping/sequence into an ordered tuple of pairs."""
    raw_pairs: list[tuple[object, object]] = []
    if isinstance(copies, Mapping):
        mapping = cast("Mapping[object, object]", copies)
        raw_pairs.extend(mapping.items())
    elif isinstance(copies, Sequence) and not isinstance(copies, (str, bytes)):
        sequence = cast("Sequence[object]", copies)
        for item_obj in sequence:
            item: object = item_obj
            if not isinstance(item, tuple):
                return invalid_input(
                    "copies",
                    "each copies entry is a (room_role, copy_version) pair",
                    given=repr(item),
                )
            pair = cast("tuple[object, ...]", item)
            if len(pair) != 2:
                return invalid_input(
                    "copies",
                    "each copies entry is a (room_role, copy_version) pair",
                    given=f"tuple(len={len(pair)})",
                )
            raw_pairs.append((pair[0], pair[1]))
    else:
        return invalid_input(
            "copies",
            "copies is a {room_role: copy_version} mapping or a sequence of pairs",
            given=repr(copies),
        )
    pairs: list[tuple[RoomRole, int]] = []
    for role_raw, version_raw in raw_pairs:
        role = role_raw if isinstance(role_raw, RoomRole) else _coerce_role(role_raw)
        if role is None:
            return invalid_input(
                "copies",
                "each rehearsed room-role must be a RoomRole",
                given=repr(role_raw),
            )
        if not isinstance(version_raw, int) or isinstance(version_raw, bool) or version_raw < 1:
            return invalid_input(
                "copies",
                "each copy_version is a positive ordinal identifying one off-machine artifact",
                given=repr(version_raw),
                role=role.value,
            )
        pairs.append((role, version_raw))
    return Ok(tuple(pairs))


def _resolve_roles(room_roles: Sequence[object] | None) -> Result[tuple[RoomRole, ...]]:
    """Resolve the room-roles a migration covers; default to the V1 restorable set."""
    if room_roles is None:
        return Ok(RESTORABLE_ROOM_ROLES)
    resolved: list[RoomRole] = []
    for raw in room_roles:
        role = _coerce_role(raw)
        if role is None:
            return invalid_input(
                "room_roles",
                "each room_role is one of the seven room-roles",
                given=repr(raw),
                allowed=[member.value for member in RoomRole],
            )
        if role not in RESTORABLE_ROOM_ROLES:
            return invalid_input(
                "room_roles",
                "this room-role has no restore writer in V1; only the immutable raw "
                "archive, journal, and registry room are migratable from a CT-26 export",
                given=role.value,
            )
        if role not in resolved:
            resolved.append(role)
    if not resolved:
        return invalid_input(
            "room_roles",
            "a migration names at least one restorable room-role",
            given=repr(room_roles),
        )
    return Ok(tuple(resolved))


def _refuse_overlapping_roots(
    source: EvidenceStore, destination: EvidenceStore, verify_into: EvidenceStore
) -> Result[StoreMigrationReport] | None:
    """Refuse same-root source/destination/verify targets (never mutate the only copy)."""
    roots = {
        "source": source.root.resolve(),
        "destination": destination.root.resolve(),
        "verify_into": verify_into.root.resolve(),
    }
    if roots["source"] == roots["destination"]:
        return policy_rejection(
            "destination",
            "a migration never mutates the only copy in place; source and destination "
            "must be distinct roots so the source stays the documented restore path "
            "(AR-32, DEC-0118)",
            signal="refuse-in-place-migration",
            source_root=str(roots["source"]),
            destination_root=str(roots["destination"]),
        )
    if roots["verify_into"] in {roots["source"], roots["destination"]}:
        return policy_rejection(
            "verify_into",
            "the full-restore rehearsal target must be a distinct store root from both "
            "the source (documented restore path) and the migration destination "
            "(AR-32, DEC-0118)",
            signal="refuse-overlapping-verify-root",
            source_root=str(roots["source"]),
            destination_root=str(roots["destination"]),
            verify_root=str(roots["verify_into"]),
        )
    return None


def _as_verify_storage_failure(result: TypedRefusal) -> TypedRefusal:
    """Map a failed restore/read into a storage-failure with no recoverability claim.

    Policy / invalid-input refusals from the restore gate (cross-world, in-place) pass
    through unchanged — they are not corrupt-copy outcomes. Every other refusal category
    becomes ``storage failure`` so a corrupt restore never reports success (AC2).
    """
    if result.category in {
        RefusalCategory.POLICY_REJECTION,
        RefusalCategory.INVALID_INPUT,
    }:
        return result
    if result.category is RefusalCategory.STORAGE_FAILURE:
        return result
    remapped: dict[str, object] = dict(result.context)
    remapped["signal"] = remapped.get("signal", "verify-storage-failure")
    remapped["adapter_category"] = result.category.value
    return _storage_failure(
        "verify restore failed; no recoverability claim is issued (DEC-0109, DEC-0118)",
        context=remapped,
        retryable=result.retryability is Retryability.YES,
    )


def _storage_failure(
    reason: str, *, context: dict[str, object], retryable: bool = False
) -> TypedRefusal:
    """Build a CT-04 ``storage failure`` refusal — never a recoverability claim (AC2)."""
    return unpersistable(
        reason,
        retryability=Retryability.YES if retryable else Retryability.NO,
        context=context,
    )


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
