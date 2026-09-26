"""CT-14 never-in-place evidence migration (preflight → verify).

Split from :mod:`qmf.data.verify` so the public module stays under the Skylos
god-file limits. Callers keep importing :func:`migrate_evidence` from
:mod:`qmf.data.verify`.
"""

from __future__ import annotations

from collections.abc import Sequence

from qmf.core import Ok, Result, TypedRefusal, World, is_refusal
from qmf.data.backup import BackupCopyReceipt, OffMachineBackup, OffMachineRestore
from qmf.data.backup_gate import coerce_world
from qmf.data.backup_storage import storage_failure
from qmf.data.store.backup_input import RoomExport
from qmf.data.store.facade import EvidenceStore, WorldStore
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.store.rooms import RoomRole
from qmf.data.verify_match import exports_match, resolve_roles
from qmf.data.verify_restore import OffMachineVerify
from qmf.data.verify_types import (
    MigrationStage,
    RecoverabilityClaim,
    RoomTransform,
    StoreMigrationReport,
)

__all__ = ["migrate_evidence"]


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
    setup = _migration_setup(world, room_roles, source, destination, verify_into)
    if is_refusal(setup):
        return setup
    resolved, roles = setup.value
    preflight = _migration_preflight(source, resolved, roles)
    if is_refusal(preflight):
        return preflight
    expected, source_bundle, preflight_count = preflight.value
    backed = _migration_backup_first(backup, expected, resolved, roles)
    if is_refusal(backed):
        return backed
    receipts, copies = backed.value
    dry = _migration_dry_run(expected, roles, resolved, transform)
    if is_refusal(dry):
        return dry
    migrated_exports, dry_run_count = dry.value
    migrated_count = _migration_write(restore, migrated_exports, destination, resolved, source)
    if is_refusal(migrated_count):
        return migrated_count
    landed = _migration_confirm_destination(destination, resolved, migrated_exports)
    if is_refusal(landed):
        return landed
    intact = _migration_confirm_source(source_bundle, resolved, expected)
    if is_refusal(intact):
        return intact
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
    return Ok(
        _migration_report(
            source=source,
            destination=destination,
            receipts=receipts,
            preflight_count=preflight_count,
            dry_run_count=dry_run_count,
            migrated_count=migrated_count.value,
            recoverability=claim.value,
        )
    )


def _migration_report(
    *,
    source: EvidenceStore,
    destination: EvidenceStore,
    receipts: list[BackupCopyReceipt],
    preflight_count: int,
    dry_run_count: int,
    migrated_count: int,
    recoverability: RecoverabilityClaim,
) -> StoreMigrationReport:
    return StoreMigrationReport(
        restore_path=str(source.root.resolve()),
        backed_up=True,
        backup_receipts=tuple(receipts),
        stages_completed=(
            MigrationStage.PREFLIGHT,
            MigrationStage.BACKUP_FIRST,
            MigrationStage.DRY_RUN,
            MigrationStage.MIGRATE,
            MigrationStage.VERIFY,
        ),
        preflight_count=preflight_count,
        dry_run_count=dry_run_count,
        migrated_count=migrated_count,
        destination_root=str(destination.root.resolve()),
        recoverability=recoverability,
    )


def _migration_setup(
    world: object,
    room_roles: Sequence[object] | None,
    source: EvidenceStore,
    destination: EvidenceStore,
    verify_into: EvidenceStore,
) -> Result[tuple[World, tuple[RoomRole, ...]]]:
    resolved = coerce_world(world)
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
    roles = resolve_roles(room_roles)
    if is_refusal(roles):
        return roles
    blocked = _refuse_overlapping_roots(source, destination, verify_into)
    if isinstance(blocked, TypedRefusal):
        return blocked
    return Ok((resolved, roles.value))


def _migration_preflight(
    source: EvidenceStore, resolved: World, roles: tuple[RoomRole, ...]
) -> Result[tuple[dict[RoomRole, RoomExport], WorldStore, int]]:
    expected: dict[RoomRole, RoomExport] = {}
    source_bundle = source.for_world(resolved)
    if is_refusal(source_bundle):
        return source_bundle
    for role in roles:
        export = source_bundle.value.backup_input.read_room(role, for_world=resolved)
        if is_refusal(export):
            return export
        expected[role] = export.value
    preflight_count = sum(exp.record_count for exp in expected.values())
    return Ok((expected, source_bundle.value, preflight_count))


def _migration_backup_first(
    backup: OffMachineBackup,
    expected: dict[RoomRole, RoomExport],
    resolved: World,
    roles: tuple[RoomRole, ...],
) -> Result[tuple[list[BackupCopyReceipt], dict[RoomRole, int]]]:
    receipts: list[BackupCopyReceipt] = []
    copies: dict[RoomRole, int] = {}
    for role in roles:
        copied = backup.copy_export(expected[role], for_world=resolved)
        if is_refusal(copied):
            return copied
        receipts.append(copied.value)
        copies[role] = copied.value.copy_version
    return Ok((receipts, copies))


def _migration_dry_run(
    expected: dict[RoomRole, RoomExport],
    roles: tuple[RoomRole, ...],
    resolved: World,
    transform: RoomTransform | None,
) -> Result[tuple[list[RoomExport], int]]:
    migrated_exports: list[RoomExport] = []
    for role in roles:
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
    return Ok((migrated_exports, dry_run_count))


def _migration_write(
    restore: OffMachineRestore,
    migrated_exports: list[RoomExport],
    destination: EvidenceStore,
    resolved: World,
    source: EvidenceStore,
) -> Result[int]:
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
    return Ok(migrated_count)


def _migration_confirm_destination(
    destination: EvidenceStore, resolved: World, migrated_exports: list[RoomExport]
) -> Result[None]:
    dest_bundle = destination.for_world(resolved)
    if is_refusal(dest_bundle):
        return dest_bundle
    for export in migrated_exports:
        landed = dest_bundle.value.backup_input.read_room(
            export.source_room_role, for_world=resolved
        )
        if is_refusal(landed):
            return landed
        if not exports_match(export, landed.value):
            return storage_failure(
                "migrated destination evidence does not match the dry-run transform; "
                "migration completion is not claimed (DEC-0109, DEC-0118)",
                retryable=False,
                context={
                    "signal": "migrate-mismatch",
                    "role": export.source_room_role.value,
                },
            )
    return Ok(None)


def _migration_confirm_source(
    source_bundle: WorldStore,
    resolved: World,
    expected: dict[RoomRole, RoomExport],
) -> Result[None]:
    for role, original in expected.items():
        again = source_bundle.backup_input.read_room(role, for_world=resolved)
        if is_refusal(again):
            return again
        if not exports_match(original, again.value):
            return storage_failure(
                "source evidence changed during migration; the only copy must stay "
                "intact as the documented restore path (AR-32, DEC-0118)",
                retryable=False,
                context={"signal": "source-mutated", "role": role.value},
            )
    return Ok(None)


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
