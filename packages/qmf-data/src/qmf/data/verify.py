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

Value types, restore primitives, comparison helpers, and migration live in sibling
modules; this module re-exports the public names so existing import paths keep
working.
"""

from __future__ import annotations

from qmf.data.verify_migrate import migrate_evidence
from qmf.data.verify_restore import OffMachineVerify
from qmf.data.verify_types import (
    MIGRATION_SEQUENCE,
    NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE,
    NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE,
    NODE_OPS_BACKUP_RETENTION_PERIOD,
    NODE_OPS_RESTORE_VERIFICATION_CADENCE,
    RESTORABLE_ROOM_ROLES,
    MigrationStage,
    RecoverabilityClaim,
    StoreMigrationReport,
    VerifiedRoom,
    VerifyKind,
    refuse_snapshot_alone_claim,
)

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
    "StoreMigrationReport",
    "VerifiedRoom",
    "VerifyKind",
    "migrate_evidence",
    "refuse_snapshot_alone_claim",
]
