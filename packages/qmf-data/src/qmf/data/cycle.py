"""Application-owned nightly off-machine cycle helper (Story 5.4).

QMF ships the CT-14 / CT-26 backup, restore, and verify *primitives*; this module
is the composition-root helper that runs **one** cycle when the *application*
decides the ratified ``registry:backup_cadence`` = nightly moment has arrived
(AR-34, DEC-0118). It owns **no** threads, cron, daemon, or scheduler — those
stay outside ``qmf-data`` (FM-6, FM-9, DEC-0051). Asking this boundary to own the
schedule or a numeric RPO/RTO is a typed ``policy rejection``.

One cycle, per world:

1. CT-26-export **every** room-role (including the registry room).
2. CT-14 encrypt + put each export as a new versioned off-machine copy.
3. Automated sample-restore (always).
4. Periodic full-restore rehearsal when the application asks for it this cycle
   (numeric verification cadence stays a null node/ops pointer — AC2 / Story 5.3).

Cross-world / ``world = simulated`` remains a ``policy rejection``. Encryption is
required as a pointer; no credential enters the cycle report (AC4, AR-37).

Stdlib + qmf-core + the CT-14 backup/verify types only (default-deny; L30).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from qmf.core import Ok, Result, TypedRefusal, World, is_refusal
from qmf.data.backup import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    ENCRYPTION_REQUIRED,
    BackupCopyReceipt,
    ObjectStorage,
    OffMachineBackup,
    OffMachineRestore,
    PayloadCipher,
)
from qmf.data.store.backup_input import RoomExport
from qmf.data.store.facade import EvidenceStore, WorldStore
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.store.rooms import ROOM_ROLE_VALUES, RoomRole
from qmf.data.verify import (
    NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE,
    NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE,
    NODE_OPS_BACKUP_RETENTION_PERIOD,
    NODE_OPS_RESTORE_VERIFICATION_CADENCE,
    RESTORABLE_ROOM_ROLES,
    OffMachineVerify,
    RecoverabilityClaim,
    VerifyKind,
)

__all__ = [
    "BACKUP_CADENCE",
    "CYCLE_ROOM_ROLES",
    "NightlyCycleReport",
    "OffMachineCycle",
    "refuse_numeric_rpo_rto",
    "refuse_schedule_ownership",
]

# Ratified design cadence (registry:backup_cadence). The application owns when
# run_once is invoked; this constant is a design pointer, never a scheduler.
BACKUP_CADENCE: Final[str] = "nightly"

# Every room-role including the registry room — one retention/backup law (AC3).
CYCLE_ROOM_ROLES: Final[tuple[RoomRole, ...]] = tuple(RoomRole)


@dataclass(frozen=True, slots=True)
class NightlyCycleReport:
    """Evidence that one application-driven off-machine cycle completed (AC1, AC4).

    No credential fields. ``encryption_required`` is the standing pointer.
    ``cadence`` cites the ratified design cadence; it does not imply QMF scheduled
    the run. ``full_restore`` is ``None`` when the application skipped the
    periodic full-restore rehearsal this cycle.
    """

    world: World
    backup_receipts: tuple[BackupCopyReceipt, ...]
    sample_restore: RecoverabilityClaim
    full_restore: RecoverabilityClaim | None
    rooms_backed_up: tuple[RoomRole, ...]
    cadence: str = BACKUP_CADENCE
    format_version: int = BACKUP_CONTRACT_FORMAT_VERSION
    encryption_required: bool = ENCRYPTION_REQUIRED


def refuse_schedule_ownership(
    *,
    request: str | None = None,
) -> Result[NightlyCycleReport]:
    """Refuse any ask that QMF own the nightly schedule or run a daemon (AC2).

    FM-6 / FM-9 / DEC-0118 / DEC-0051: the boundary provides the one-cycle
    primitive only; cron, threads, supervision, and cadence execution stay
    application/ops-owned.
    """
    context: dict[str, object] = {
        "signal": "refuse-schedule-ownership",
        "cadence_pointer": BACKUP_CADENCE,
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "schedule",
        "COMP-QMF-DATA / COMP-QMF-DATA-BACKUP provide the backup/restore/verify "
        "primitives only; owning the nightly schedule, cron, threads, or a daemon "
        "is outside the component boundary — the application drives each cycle "
        "(FM-6, FM-9, DEC-0118, DEC-0051)",
        **context,
    )


def refuse_numeric_rpo_rto(
    *,
    target: str | None = None,
) -> Result[NightlyCycleReport]:
    """Refuse any ask that QMF own a numeric RPO, RTO, or retention target (AC2).

    Those numbers stay null node/ops-sitting pointers (Story 5.3 / DEC-0118).
    """
    context: dict[str, object] = {
        "signal": "refuse-numeric-rpo-rto",
        "backup_recovery_point_objective": NODE_OPS_BACKUP_RECOVERY_POINT_OBJECTIVE,
        "backup_recovery_time_objective": NODE_OPS_BACKUP_RECOVERY_TIME_OBJECTIVE,
        "backup_retention_period": NODE_OPS_BACKUP_RETENTION_PERIOD,
        "restore_verification_cadence": NODE_OPS_RESTORE_VERIFICATION_CADENCE,
    }
    if target is not None:
        context["target"] = target
    return policy_rejection(
        "recovery_target",
        "numeric RPO/RTO/retention/verification-cadence targets are node/ops-sitting "
        "items; COMP-QMF-DATA-BACKUP exposes null pointers only and never owns or "
        "fills them (FM-6, DEC-0118)",
        **context,
    )


class _CycleRun:
    """One-cycle CT-26 → CT-14 → verify runner. Owns backup/verify ports only."""

    def __init__(self, backup: OffMachineBackup, verify: OffMachineVerify) -> None:
        self._backup = backup
        self._verify = verify

    def run_once(
        self,
        *,
        store: EvidenceStore,
        world: object,
        sample_into: EvidenceStore,
        full_into: EvidenceStore | None = None,
        include_full_rehearsal: bool = False,
        room_roles: Sequence[object] | None = None,
        sample_role: object | None = None,
    ) -> Result[NightlyCycleReport]:
        bound = _bind_cycle_run(
            store=store,
            world=world,
            sample_into=sample_into,
            full_into=full_into,
            include_full_rehearsal=include_full_rehearsal,
            room_roles=room_roles,
        )
        if is_refusal(bound):
            return bound
        copied = _backup_cycle_rooms(self._backup, bound.value)
        if is_refusal(copied):
            return copied
        return _finish_cycle_verify(
            self._verify,
            bind=bound.value,
            copies=copied.value,
            sample_into=sample_into,
            sample_role=sample_role,
            store=store,
        )


class _CycleScheduleBoundary:
    """Schedule/daemon asks that this composition-root never owns (AC2 / FM-9)."""

    def __init__(self) -> None:
        self._refuse = refuse_schedule_ownership

    def own_schedule(self, *args: object, **kwargs: object) -> Result[NightlyCycleReport]:
        _ = (args, kwargs)
        return self._refuse(request="own_schedule")

    def start_daemon(self, *args: object, **kwargs: object) -> Result[NightlyCycleReport]:
        _ = (args, kwargs)
        return self._refuse(request="start_daemon")


class _CycleRecoveryBoundary:
    """Numeric RPO/RTO asks that stay node/ops-sitting pointers (AC2)."""

    def __init__(self) -> None:
        self._refuse = refuse_numeric_rpo_rto

    def set_recovery_point_objective(
        self, *args: object, **kwargs: object
    ) -> Result[NightlyCycleReport]:
        _ = (args, kwargs)
        return self._refuse(target="backup_recovery_point_objective")

    def set_recovery_time_objective(
        self, *args: object, **kwargs: object
    ) -> Result[NightlyCycleReport]:
        _ = (args, kwargs)
        return self._refuse(target="backup_recovery_time_objective")


@dataclass(frozen=True, slots=True)
class _CycleCollaborators:
    """Run primitive plus the schedule and recovery refusal boundaries."""

    run: _CycleRun
    schedule: _CycleScheduleBoundary
    recovery: _CycleRecoveryBoundary


class OffMachineCycle:
    """Composition-root helper: run **one** nightly encrypted off-machine cycle.

    Constructed with the same :class:`ObjectStorage` / :class:`PayloadCipher` ports
    as backup and verify. Call :meth:`run_once` from the application when the
    nightly cadence arrives — never from a library-owned timer, thread, or cron.
    """

    def __init__(
        self,
        storage: ObjectStorage,
        cipher: PayloadCipher,
        *,
        backup: OffMachineBackup | None = None,
        restore: OffMachineRestore | None = None,
        verify: OffMachineVerify | None = None,
    ) -> None:
        owned_backup = backup if backup is not None else OffMachineBackup(storage, cipher)
        owned_restore = restore if restore is not None else OffMachineRestore(storage, cipher)
        owned_verify = (
            verify
            if verify is not None
            else OffMachineVerify(storage, cipher, restore=owned_restore)
        )
        self._collaborators = _CycleCollaborators(
            run=_CycleRun(owned_backup, owned_verify),
            schedule=_CycleScheduleBoundary(),
            recovery=_CycleRecoveryBoundary(),
        )

    def run_once(
        self,
        *,
        store: EvidenceStore,
        world: object,
        sample_into: EvidenceStore,
        full_into: EvidenceStore | None = None,
        include_full_rehearsal: bool = False,
        room_roles: Sequence[object] | None = None,
        sample_role: object | None = None,
    ) -> Result[NightlyCycleReport]:
        """Run one CT-26 → CT-14 → verify cycle for ``world`` (AC1, AC3, AC4).

        Backs up every named room-role (default: all seven, including the registry
        room). Always runs sample-restore into ``sample_into``. When
        ``include_full_rehearsal`` is true, also runs full-restore rehearsal into
        ``full_into`` (required in that case) — the application decides the
        periodic cadence because the numeric target stays a node/ops null pointer.
        Cross-world / ``simulated`` requests refuse as ``policy rejection``.
        """
        return self._collaborators.run.run_once(
            store=store,
            world=world,
            sample_into=sample_into,
            full_into=full_into,
            include_full_rehearsal=include_full_rehearsal,
            room_roles=room_roles,
            sample_role=sample_role,
        )

    def own_schedule(self, *args: object, **kwargs: object) -> Result[NightlyCycleReport]:
        """Always refuse — QMF never owns the nightly schedule (AC2 / FM-9)."""
        return self._collaborators.schedule.own_schedule(*args, **kwargs)

    def start_daemon(self, *args: object, **kwargs: object) -> Result[NightlyCycleReport]:
        """Always refuse — no daemon, cron, or thread lives in qmf-data (AC2)."""
        return self._collaborators.schedule.start_daemon(*args, **kwargs)

    def set_recovery_point_objective(
        self, *args: object, **kwargs: object
    ) -> Result[NightlyCycleReport]:
        """Always refuse — numeric RPO is a node/ops-sitting item (AC2)."""
        return self._collaborators.recovery.set_recovery_point_objective(*args, **kwargs)

    def set_recovery_time_objective(
        self, *args: object, **kwargs: object
    ) -> Result[NightlyCycleReport]:
        """Always refuse — numeric RTO is a node/ops-sitting item (AC2)."""
        return self._collaborators.recovery.set_recovery_time_objective(*args, **kwargs)


@dataclass(frozen=True, slots=True)
class _CycleBind:
    """Resolved world, roles, bundle, and optional full-rehearsal target."""

    world: World
    roles: tuple[RoomRole, ...]
    bundle: WorldStore
    rehearsal_target: EvidenceStore | None


@dataclass(frozen=True, slots=True)
class _CycleCopies:
    """Per-role exports, receipts, and copy versions from one cycle backup pass."""

    exports: dict[RoomRole, RoomExport]
    receipts: tuple[BackupCopyReceipt, ...]
    copies: dict[RoomRole, int]


def _resolve_cycle_world(world: object) -> Result[World]:
    """Resolve the cycle world; refuse unknown or simulated."""
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
            "world = simulated has no governed namespace in V1; a nightly cycle "
            "into governed evidence is refused (DEC-0110, DEC-0117)",
            requested=resolved.value,
        )
    return Ok(resolved)


def _bind_cycle_run(
    *,
    store: EvidenceStore,
    world: object,
    sample_into: EvidenceStore,
    full_into: EvidenceStore | None,
    include_full_rehearsal: bool,
    room_roles: Sequence[object] | None,
) -> Result[_CycleBind]:
    """Resolve world/roles and refuse overlapping or simulated cycle targets."""
    resolved = _resolve_cycle_world(world)
    if is_refusal(resolved):
        return resolved
    roles = _resolve_cycle_roles(room_roles)
    if is_refusal(roles):
        return roles
    blocked = _refuse_overlapping_cycle_roots(
        store, sample_into, full_into if include_full_rehearsal else None
    )
    if blocked is not None:
        return blocked
    if include_full_rehearsal and full_into is None:
        return invalid_input(
            "full_into",
            "include_full_rehearsal requires a distinct full_into replacement store "
            "root for the periodic full-restore rehearsal",
        )
    bundle = store.for_world(resolved.value)
    if is_refusal(bundle):
        return bundle
    return Ok(
        _CycleBind(
            world=resolved.value,
            roles=roles.value,
            bundle=bundle.value,
            rehearsal_target=full_into if include_full_rehearsal else None,
        )
    )


def _backup_cycle_rooms(backup: OffMachineBackup, bind: _CycleBind) -> Result[_CycleCopies]:
    """CT-26 export + CT-14 copy every named room-role; encryption is required."""
    exports: dict[RoomRole, RoomExport] = {}
    receipts: list[BackupCopyReceipt] = []
    copies: dict[RoomRole, int] = {}
    for role in bind.roles:
        export = bind.bundle.backup_input.read_room(role, for_world=bind.world)
        if is_refusal(export):
            return export
        # Encryption-required pointer: cipher is injected; empty ciphertext refused
        # inside OffMachineBackup.copy_export (AC4 / FM-7).
        copied = backup.copy_export(export.value, for_world=bind.world)
        if is_refusal(copied):
            return copied
        gated = _require_encrypted_receipt(copied.value, role)
        if is_refusal(gated):
            return gated
        exports[role] = export.value
        receipts.append(gated.value)
        copies[role] = gated.value.copy_version
    return Ok(_CycleCopies(exports=exports, receipts=tuple(receipts), copies=copies))


def _require_encrypted_receipt(
    receipt: BackupCopyReceipt, role: RoomRole
) -> Result[BackupCopyReceipt]:
    """Refuse a copy receipt that dropped the encryption-required pointer (FM-7)."""
    if receipt.encryption_required is not True:
        return policy_rejection(
            "encryption_required",
            "encryption is required for every off-machine copy; a receipt "
            "without the encryption-required pointer is refused (FM-7, DEC-0118)",
            signal="encryption-required",
            copy_version=receipt.copy_version,
            role=role.value,
        )
    return Ok(receipt)


def _sample_cycle_claim(
    verify: OffMachineVerify,
    *,
    bind: _CycleBind,
    copies: _CycleCopies,
    sample_into: EvidenceStore,
    sample_role: object | None,
    store: EvidenceStore,
) -> Result[RecoverabilityClaim]:
    """Automated sample-restore against one V1-restorable backed-up room."""
    sample = _resolve_sample_role(sample_role, bind.roles, copies.copies)
    if is_refusal(sample):
        return sample
    claim = verify.sample_restore(
        world=bind.world,
        copy_version=copies.copies[sample.value],
        source_room_role=sample.value,
        into=sample_into,
        for_world=bind.world,
        expected=copies.exports[sample.value],
        source_store=store,
        documented_restore_path=str(store.root.resolve()),
    )
    if is_refusal(claim):
        return claim
    return Ok(claim.value)


def _full_cycle_rehearsal(
    verify: OffMachineVerify,
    *,
    bind: _CycleBind,
    copies: _CycleCopies,
    store: EvidenceStore,
) -> Result[RecoverabilityClaim | None]:
    """Optional full-restore rehearsal into the bound replacement root."""
    if bind.rehearsal_target is None:
        return Ok(None)
    # Full rehearsal covers the V1-restorable subset; empty rebuildable rooms
    # were still backed up above but have no restore writer in V1.
    rehearsal_copies = {
        role: copies.copies[role] for role in RESTORABLE_ROOM_ROLES if role in copies.copies
    }
    rehearsed = verify.full_restore_rehearsal(
        world=bind.world,
        copies=rehearsal_copies,
        into=bind.rehearsal_target,
        for_world=bind.world,
        expected={role: copies.exports[role] for role in rehearsal_copies},
        source_store=store,
        documented_restore_path=str(store.root.resolve()),
    )
    if is_refusal(rehearsed):
        return rehearsed
    if rehearsed.value.kind is not VerifyKind.FULL_RESTORE_REHEARSAL:
        return policy_rejection(
            "full_restore",
            "full-restore rehearsal must issue a full-restore-rehearsal claim",
            signal="unexpected-verify-kind",
            kind=rehearsed.value.kind.value,
        )
    return Ok(rehearsed.value)


def _finish_cycle_verify(
    verify: OffMachineVerify,
    *,
    bind: _CycleBind,
    copies: _CycleCopies,
    sample_into: EvidenceStore,
    sample_role: object | None,
    store: EvidenceStore,
) -> Result[NightlyCycleReport]:
    """Sample-restore, optional full rehearsal, then the cycle report."""
    claim = _sample_cycle_claim(
        verify,
        bind=bind,
        copies=copies,
        sample_into=sample_into,
        sample_role=sample_role,
        store=store,
    )
    if is_refusal(claim):
        return claim
    full_claim = _full_cycle_rehearsal(verify, bind=bind, copies=copies, store=store)
    if is_refusal(full_claim):
        return full_claim
    return Ok(
        NightlyCycleReport(
            world=bind.world,
            backup_receipts=copies.receipts,
            sample_restore=claim.value,
            full_restore=full_claim.value,
            rooms_backed_up=bind.roles,
        )
    )


def _resolve_cycle_roles(
    room_roles: Sequence[object] | None,
) -> Result[tuple[RoomRole, ...]]:
    """Resolve the room-roles one cycle covers; default to every room-role."""
    if room_roles is None:
        return Ok(CYCLE_ROOM_ROLES)
    resolved: list[RoomRole] = []
    for raw in room_roles:
        role = _coerce_role(raw)
        if role is None:
            return invalid_input(
                "room_roles",
                "each room_role is one of the seven room-roles",
                given=repr(raw),
                allowed=list(ROOM_ROLE_VALUES),
            )
        if role not in resolved:
            resolved.append(role)
    if not resolved:
        return invalid_input(
            "room_roles",
            "a nightly cycle names at least one room-role",
            given=repr(room_roles),
        )
    return Ok(tuple(resolved))


def _resolve_sample_role(
    sample_role: object | None,
    backed_up: tuple[RoomRole, ...],
    copies: dict[RoomRole, int],
) -> Result[RoomRole]:
    """Pick the room-role the automated sample-restore will confirm."""
    if sample_role is not None:
        role = _coerce_role(sample_role)
        if role is None:
            return invalid_input(
                "sample_role",
                "sample_role is one of the seven room-roles",
                given=repr(sample_role),
                allowed=list(ROOM_ROLE_VALUES),
            )
        if role not in copies:
            return invalid_input(
                "sample_role",
                "sample_role must be among the room-roles this cycle backed up",
                given=role.value,
                backed_up=[member.value for member in backed_up],
            )
        if role not in RESTORABLE_ROOM_ROLES:
            return invalid_input(
                "sample_role",
                "sample-restore requires a V1-restorable room-role (immutable raw "
                "archive, journal, or registry room)",
                given=role.value,
            )
        return Ok(role)
    for candidate in RESTORABLE_ROOM_ROLES:
        if candidate in copies:
            return Ok(candidate)
    return invalid_input(
        "sample_role",
        "a nightly cycle must back up at least one V1-restorable room-role so "
        "sample-restore can run",
        backed_up=[member.value for member in backed_up],
    )


def _refuse_overlapping_cycle_roots(
    store: EvidenceStore,
    sample_into: EvidenceStore,
    full_into: EvidenceStore | None,
) -> TypedRefusal | None:
    """Refuse when verify targets would rewrite the only local copy."""
    source = store.root.resolve()
    sample = sample_into.root.resolve()
    if sample == source:
        return policy_rejection(
            "sample_into",
            "sample-restore must target a replacement store root; rewriting the only "
            "local copy in place is refused (DEC-0118)",
            signal="refuse-in-place-restore",
            source_root=str(source),
            sample_root=str(sample),
        )
    if full_into is None:
        return None
    full = full_into.root.resolve()
    if full in (source, sample):
        return policy_rejection(
            "full_into",
            "the full-restore rehearsal target must be a distinct store root from both "
            "the source archive and the sample-restore replacement (DEC-0118)",
            signal="refuse-overlapping-verify-root",
            source_root=str(source),
            sample_root=str(sample),
            full_root=str(full),
        )
    return None


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
