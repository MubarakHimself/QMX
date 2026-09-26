"""CT-14 verify value types: kinds, claims, and migration reports.

Split from :mod:`qmf.data.verify` so the public module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.verify`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qmf.core import Result, World
from qmf.data.backup import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    BackupCopyReceipt,
    RestoreReceipt,
)
from qmf.data.store.backup_input import RoomExport
from qmf.data.store.refusals import policy_rejection
from qmf.data.store.rooms import RoomRole

__all__ = [
    "MIGRATION_SEQUENCE",
    "NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE",
    "NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE",
    "NODE_OPS_BACKUP_RETENTION_PERIOD",
    "NODE_OPS_RESTORE_VERIFICATION_CADENCE",
    "RESTORABLE_ROOM_ROLES",
    "MigrationStage",
    "RecoverabilityClaim",
    "RoomTransform",
    "StoreMigrationReport",
    "VerifiedRoom",
    "VerifyKind",
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
    _ = (world, copy_version, source_room_role)
    return policy_rejection(
        "recoverability",
        "recoverability is claimed only through the ratified verify primitives — "
        "automated sample-restore tests plus a periodic full-restore rehearsal — "
        "and is never asserted from a snapshot alone (SCN-0004, DEC-0118)",
        signal="refuse-snapshot-alone-claim",
    )
