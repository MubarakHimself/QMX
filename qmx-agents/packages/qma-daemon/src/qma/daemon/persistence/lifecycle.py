"""Daemon store lifecycle: migration, backup, and controlled restore (FR-Q37; AD-27).

Migrations for journal, SQLite, ledger, Task Graph, mailbox, staging, and
artifact stores run the parent five steps — preflight → backup first → dry-run →
migrate → verify — with a documented restore path and never an in-place mutation
of the only copy. Backup covers the seven daemon-owned durable stores as
encrypted, versioned, off-machine copies on ``registry:store.backup_cadence``.
Sample-restore and full-restore rehearsal restore into isolated scratch and
record verified results as evidence on their registry cadence keys. A restore of
the live store is a recorded ``operator``-principal act
(``store.restore_live``), never a background job. GAP-0088 deferred decisions
(backup destination, encryption-key custody, restore-cadence values) stay
explicit exclusions — this module never invents a real B2 bucket or fills those
values.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary import PrincipalClass
from qma.daemon.journal.variables import (
    STORE_BACKUP_CADENCE_KEY,
    STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
    STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
    cite_store_lifecycle_key,
)
from qma.daemon.persistence.schema import refuse_unknown_store_schema
from qma.wire.principals import authorize_wire_command
from qmf.core import Ok, Result, Retryability, is_refusal, unpersistable
from qmf.data.backup import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    ENCRYPTION_REQUIRED,
    ObjectStorage,
    PayloadCipher,
    StoragePutAck,
)
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.verify import MIGRATION_SEQUENCE, MigrationStage

if TYPE_CHECKING:
    from qma.daemon.journal.authoritative import AuthoritativeJournal, JournalAppendReceipt

__all__ = [
    "DAEMON_OWNED_DURABLE_BACKUP_STORES",
    "GAP_0088_DEFERRED",
    "LIVE_RESTORE_COMMAND",
    "LIVE_RESTORE_EVENT",
    "MIGRATABLE_STORES",
    "BackupCopyEvidence",
    "DaemonBackupReport",
    "DaemonMigrationReport",
    "DaemonStoreLifecycle",
    "LiveRestoreReceipt",
    "RestoreRehearsalEvidence",
    "StoreSnapshot",
    "fixture_memory_storage",
    "fixture_xor_cipher",
]


# Migration targets named by FR-Q37 / AD-27 (DEC-0326).
MIGRATABLE_STORES: Final[frozenset[str]] = frozenset(
    {
        "journal",
        "sqlite",
        "ledger",
        "task_graph",
        "mailbox",
        "staging",
        "artifact",
    }
)

# Seven daemon-owned durable stores backed up under AD-27 (DEC-0326).
# MemoryProvider stores are provider-owned and outside this obligation.
DAEMON_OWNED_DURABLE_BACKUP_STORES: Final[tuple[str, ...]] = (
    "event_journal",
    "task_ledger",
    "quant_ledger",
    "experiment_ledger",
    "artifact_store",
    "staging_store",
    "telemetry_store",
)

LIVE_RESTORE_COMMAND: Final[str] = "store.restore_live"
LIVE_RESTORE_EVENT: Final[str] = "store.restore_live"

# Explicit exclusions from this story (FR-Q37; GAP-0088; DEC-0326).
GAP_0088_DEFERRED: Final[frozenset[str]] = frozenset(
    {
        "backup_destination",
        "encryption_key_custody",
        "sample_restore_test_cadence_value",
        "full_restore_rehearsal_cadence_value",
    }
)


@dataclass(frozen=True, slots=True)
class StoreSnapshot:
    """One daemon-owned store payload for migration / backup fixtures."""

    store: str
    schema_version: int
    records: tuple[Mapping[str, object], ...]

    def to_bytes(self) -> bytes:
        body = {
            "store": self.store,
            "schema_version": self.schema_version,
            "records": [dict(row) for row in self.records],
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_bytes(cls, payload: bytes) -> StoreSnapshot:
        body = json.loads(payload.decode("utf-8"))
        records = tuple(MappingProxyType(dict(row)) for row in body.get("records", ()))
        return cls(
            store=str(body["store"]),
            schema_version=int(body["schema_version"]),
            records=records,
        )


@dataclass(frozen=True, slots=True)
class DaemonMigrationReport:
    """Outcome of a five-step daemon-store migration — never in-place."""

    store: str
    stages_completed: tuple[MigrationStage, ...]
    restore_path: str
    destination_root: str
    backup_copy_version: int
    backed_up: bool
    dry_run_record_count: int
    migrated_record_count: int
    verified: bool


@dataclass(frozen=True, slots=True)
class BackupCopyEvidence:
    """One encrypted, versioned off-machine copy of a daemon-owned store."""

    store: str
    copy_version: int
    ciphertext_bytes: int
    format_version: int = BACKUP_CONTRACT_FORMAT_VERSION
    encryption_required: bool = ENCRYPTION_REQUIRED


@dataclass(frozen=True, slots=True)
class DaemonBackupReport:
    """Evidence that the registered backup lifecycle covered all seven stores."""

    cadence_key: str
    copies: tuple[BackupCopyEvidence, ...]
    stores: tuple[str, ...]
    encryption_required: bool = ENCRYPTION_REQUIRED
    format_version: int = BACKUP_CONTRACT_FORMAT_VERSION


@dataclass(frozen=True, slots=True)
class RestoreRehearsalEvidence:
    """Verified sample-restore or full-restore rehearsal into scratch."""

    kind: str
    cadence_key: str
    scratch_root: str
    live_root: str
    stores_verified: tuple[str, ...]
    record_count: int
    verified: bool


@dataclass(frozen=True, slots=True)
class LiveRestoreReceipt:
    """Recorded operator-principal live-store restore act."""

    command: str
    principal_class: str
    live_root: str
    source_copy_version: int
    stores_restored: tuple[str, ...]
    journal: JournalAppendReceipt | None = None


class _XorCipher:
    """Test/fixture cipher — key custody stays GAP-0088 deferred."""

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in plaintext))

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return self.encrypt(ciphertext)


class _MemoryStorage:
    """In-process off-machine destination — never a real B2 bucket (GAP-0088)."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, int, str], bytes] = {}

    def put(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        payload: bytes,
        format_version: int,
    ) -> Result[StoragePutAck]:
        del format_version
        self.objects[(world, copy_version, source_room_role)] = payload
        return Ok(StoragePutAck())

    def get(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        format_version: int,
    ) -> Result[bytes]:
        del format_version
        payload = self.objects.get((world, copy_version, source_room_role))
        if payload is None:
            return unpersistable(
                "fixture off-machine storage has no such versioned copy",
                retryability=Retryability.NO,
                context={"signal": "missing-copy", "copy_version": copy_version},
            )
        return Ok(payload)


def fixture_xor_cipher() -> PayloadCipher:
    """Return a fixture PayloadCipher (encryption required; custody deferred)."""
    return _XorCipher()


def fixture_memory_storage() -> ObjectStorage:
    """Return an in-memory ObjectStorage — not a real off-machine provider."""
    return _MemoryStorage()


def _write_snapshot(root: Path, snapshot: StoreSnapshot) -> Path:
    path = root / snapshot.store / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snapshot.to_bytes())
    return path


def _read_snapshot(root: Path, store: str) -> Result[StoreSnapshot]:
    path = root / store / "snapshot.json"
    if not path.is_file():
        return invalid_input(
            "store",
            "migration / restore requires a durable store snapshot under the root",
            store=store,
            root=str(root),
        )
    return Ok(StoreSnapshot.from_bytes(path.read_bytes()))


@dataclass
class DaemonStoreLifecycle:
    """Application-owned AD-27 migration, backup, and controlled restoration."""

    storage: ObjectStorage = field(default_factory=fixture_memory_storage)
    cipher: PayloadCipher = field(default_factory=fixture_xor_cipher)
    world: str = "live"
    _next_copy_version: int = 1

    def migrate(
        self,
        *,
        store: object,
        source_root: Path | str,
        destination_root: Path | str,
        known_schema_version: int = 1,
    ) -> Result[DaemonMigrationReport]:
        """Run preflight → backup first → dry-run → migrate → verify (FR-Q37).

        Never mutates the only copy in place. ``source_root`` remains the
        documented restore path.
        """
        if not isinstance(store, str) or store not in MIGRATABLE_STORES:
            return policy_rejection(
                "migration_store",
                "daemon migrations name journal, sqlite, ledger, task_graph, "
                "mailbox, staging, or artifact (FR-Q37; AD-27)",
                given=repr(store),
                allowed=sorted(MIGRATABLE_STORES),
            )
        source = Path(source_root).resolve()
        destination = Path(destination_root).resolve()
        if destination == source:
            return policy_rejection(
                "migration",
                "migrations never mutate the only copy in place; destination "
                "must be a distinct documented migrate root (FR-Q37; AD-27)",
                signal="refuse-in-place-migration",
                restore_path=str(source),
            )

        # --- preflight ---
        preflight = _read_snapshot(source, store)
        if is_refusal(preflight):
            return preflight
        snap = preflight.value
        if snap.schema_version != known_schema_version:
            return refuse_unknown_store_schema(
                store=store,
                expected_schema_version=known_schema_version,
                store_schema_version=snap.schema_version,
            )
        stages: list[MigrationStage] = [MigrationStage.PREFLIGHT]

        # --- backup first ---
        plaintext = snap.to_bytes()
        encrypted = self.cipher.encrypt(plaintext)
        if is_refusal(encrypted):
            return encrypted
        copy_version = self._next_copy_version
        self._next_copy_version += 1
        put = self.storage.put(
            world=self.world,
            copy_version=copy_version,
            source_room_role=store,
            payload=encrypted.value,
            format_version=BACKUP_CONTRACT_FORMAT_VERSION,
        )
        if is_refusal(put):
            return put
        stages.append(MigrationStage.BACKUP_FIRST)

        # --- dry-run ---
        dry_records = tuple(MappingProxyType(dict(row)) for row in snap.records)
        stages.append(MigrationStage.DRY_RUN)

        # --- migrate (into destination only) ---
        migrated = StoreSnapshot(
            store=store,
            schema_version=known_schema_version,
            records=dry_records,
        )
        _write_snapshot(destination, migrated)
        stages.append(MigrationStage.MIGRATE)

        # --- verify ---
        verified = _read_snapshot(destination, store)
        if is_refusal(verified):
            return verified
        if verified.value.to_bytes() != migrated.to_bytes():
            return policy_rejection(
                "migration_verify",
                "migrate verify failed: destination snapshot does not match "
                "the migrated payload (FR-Q37; AD-27)",
                store=store,
                destination=str(destination),
            )
        # Confirm backup is restorable (documented restore path = source).
        fetched = self.storage.get(
            world=self.world,
            copy_version=copy_version,
            source_room_role=store,
            format_version=BACKUP_CONTRACT_FORMAT_VERSION,
        )
        if is_refusal(fetched):
            return fetched
        decrypted = self.cipher.decrypt(fetched.value)
        if is_refusal(decrypted):
            return decrypted
        if decrypted.value != plaintext:
            return policy_rejection(
                "migration_verify",
                "backup-first copy failed round-trip verify against the "
                "documented restore path (FR-Q37; AD-27)",
                store=store,
                restore_path=str(source),
            )
        stages.append(MigrationStage.VERIFY)

        if tuple(stages) != MIGRATION_SEQUENCE:
            return policy_rejection(
                "migration",
                "migration must complete all five parent steps in order (FR-Q37; AD-27)",
                stages=tuple(stage.value for stage in stages),
            )

        return Ok(
            DaemonMigrationReport(
                store=store,
                stages_completed=tuple(stages),
                restore_path=str(source),
                destination_root=str(destination),
                backup_copy_version=copy_version,
                backed_up=True,
                dry_run_record_count=len(dry_records),
                migrated_record_count=len(migrated.records),
                verified=True,
            )
        )

    def run_backup(
        self,
        *,
        snapshots: Mapping[str, StoreSnapshot],
        cadence_key: object = STORE_BACKUP_CADENCE_KEY,
    ) -> Result[DaemonBackupReport]:
        """Create encrypted, versioned off-machine copies of all seven stores.

        Cadence is cited only through ``registry:store.backup_cadence`` — never
        by copying a registry value (FR-Q37; AD-26, AD-27).
        """
        cited = cite_store_lifecycle_key(cadence_key)
        if is_refusal(cited):
            return cited
        if cited.value != STORE_BACKUP_CADENCE_KEY:
            return policy_rejection(
                "backup_cadence",
                "backup cadence is read only through registry:store.backup_cadence (FR-Q37; AD-27)",
                given=cited.value,
            )
        if set(snapshots) != set(DAEMON_OWNED_DURABLE_BACKUP_STORES):
            return policy_rejection(
                "backup_stores",
                "backup covers exactly the seven daemon-owned durable stores; "
                "MemoryProvider stores are outside this obligation (FR-Q37; AD-27)",
                required=list(DAEMON_OWNED_DURABLE_BACKUP_STORES),
                given=sorted(snapshots),
            )
        if not ENCRYPTION_REQUIRED:
            return policy_rejection(
                "encryption",
                "off-machine backup copies require encryption (FR-Q37; AD-27)",
            )

        copies: list[BackupCopyEvidence] = []
        for store in DAEMON_OWNED_DURABLE_BACKUP_STORES:
            snap = snapshots[store]
            encrypted = self.cipher.encrypt(snap.to_bytes())
            if is_refusal(encrypted):
                return encrypted
            copy_version = self._next_copy_version
            self._next_copy_version += 1
            put = self.storage.put(
                world=self.world,
                copy_version=copy_version,
                source_room_role=store,
                payload=encrypted.value,
                format_version=BACKUP_CONTRACT_FORMAT_VERSION,
            )
            if is_refusal(put):
                return put
            copies.append(
                BackupCopyEvidence(
                    store=store,
                    copy_version=copy_version,
                    ciphertext_bytes=len(encrypted.value),
                )
            )
        return Ok(
            DaemonBackupReport(
                cadence_key=cited.value,
                copies=tuple(copies),
                stores=DAEMON_OWNED_DURABLE_BACKUP_STORES,
            )
        )

    def run_sample_restore(
        self,
        *,
        backup: DaemonBackupReport,
        expected: Mapping[str, StoreSnapshot],
        scratch_root: Path | str,
        live_root: Path | str,
        cadence_key: object = STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
        sample_store: str = "event_journal",
    ) -> Result[RestoreRehearsalEvidence]:
        """Sample-restore into isolated scratch; never the live store."""
        return self._run_restore_rehearsal(
            kind="sample-restore",
            cadence_key=cadence_key,
            required_cadence=STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
            backup=backup,
            expected=expected,
            scratch_root=scratch_root,
            live_root=live_root,
            stores=(sample_store,),
        )

    def run_full_restore_rehearsal(
        self,
        *,
        backup: DaemonBackupReport,
        expected: Mapping[str, StoreSnapshot],
        scratch_root: Path | str,
        live_root: Path | str,
        cadence_key: object = STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
    ) -> Result[RestoreRehearsalEvidence]:
        """Full-restore rehearsal into isolated scratch; never the live store."""
        return self._run_restore_rehearsal(
            kind="full-restore-rehearsal",
            cadence_key=cadence_key,
            required_cadence=STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
            backup=backup,
            expected=expected,
            scratch_root=scratch_root,
            live_root=live_root,
            stores=DAEMON_OWNED_DURABLE_BACKUP_STORES,
        )

    def _run_restore_rehearsal(
        self,
        *,
        kind: str,
        cadence_key: object,
        required_cadence: str,
        backup: DaemonBackupReport,
        expected: Mapping[str, StoreSnapshot],
        scratch_root: Path | str,
        live_root: Path | str,
        stores: tuple[str, ...],
    ) -> Result[RestoreRehearsalEvidence]:
        cited = cite_store_lifecycle_key(cadence_key)
        if is_refusal(cited):
            return cited
        if cited.value != required_cadence:
            return policy_rejection(
                "restore_cadence",
                f"{kind} cadence is read only through {required_cadence} (FR-Q37; AD-27)",
                given=cited.value,
            )
        scratch = Path(scratch_root).resolve()
        live = Path(live_root).resolve()
        if scratch == live:
            return policy_rejection(
                "restore_scratch",
                f"{kind} restores into an isolated scratch location that is "
                "never the live store (FR-Q37; AD-27)",
                signal="refuse-live-scratch-overlap",
                scratch=str(scratch),
                live=str(live),
            )

        by_store = {copy.store: copy for copy in backup.copies}
        total = 0
        verified_stores: list[str] = []
        for store in stores:
            copy = by_store.get(store)
            if copy is None:
                return invalid_input(
                    "backup",
                    f"{kind} requires a backed-up copy of {store}",
                    store=store,
                )
            exp = expected.get(store)
            if exp is None:
                return invalid_input(
                    "expected",
                    f"{kind} requires an expected snapshot for {store}",
                    store=store,
                )
            fetched = self.storage.get(
                world=self.world,
                copy_version=copy.copy_version,
                source_room_role=store,
                format_version=BACKUP_CONTRACT_FORMAT_VERSION,
            )
            if is_refusal(fetched):
                return fetched
            decrypted = self.cipher.decrypt(fetched.value)
            if is_refusal(decrypted):
                return decrypted
            restored = StoreSnapshot.from_bytes(decrypted.value)
            _write_snapshot(scratch, restored)
            if restored.to_bytes() != exp.to_bytes():
                return policy_rejection(
                    "restore_verify",
                    f"{kind} verification failed for {store} (FR-Q37; AD-27)",
                    store=store,
                    scratch=str(scratch),
                )
            total += len(restored.records)
            verified_stores.append(store)

        return Ok(
            RestoreRehearsalEvidence(
                kind=kind,
                cadence_key=cited.value,
                scratch_root=str(scratch),
                live_root=str(live),
                stores_verified=tuple(verified_stores),
                record_count=total,
                verified=True,
            )
        )

    def restore_live(
        self,
        *,
        principal_class: object,
        backup: DaemonBackupReport,
        expected: Mapping[str, StoreSnapshot],
        live_root: Path | str,
        journal: AuthoritativeJournal | None = None,
        scope_path: object = (),
        as_background_job: bool = False,
    ) -> Result[LiveRestoreReceipt]:
        """Restore the live store only as a recorded operator-principal act.

        Never accepted as a background job (FR-Q37; AD-24, AD-27).
        """
        if as_background_job:
            return policy_rejection(
                "live_restore",
                "a restore of the live store is a recorded operator-principal "
                "act and never a background job (FR-Q37; AD-27)",
                signal="refuse-background-live-restore",
                command=LIVE_RESTORE_COMMAND,
            )

        authorized = authorize_wire_command(LIVE_RESTORE_COMMAND, principal_class)
        if is_refusal(authorized):
            return authorized
        if authorized.value.principal_class is not PrincipalClass.OPERATOR:
            return OperatorPrincipalRequired.of(
                command=LIVE_RESTORE_COMMAND,
                principal_class=str(principal_class),
            )

        live = Path(live_root).resolve()
        by_store = {copy.store: copy for copy in backup.copies}
        restored_names: list[str] = []
        max_version = 0
        for store in DAEMON_OWNED_DURABLE_BACKUP_STORES:
            copy = by_store[store]
            max_version = max(max_version, copy.copy_version)
            fetched = self.storage.get(
                world=self.world,
                copy_version=copy.copy_version,
                source_room_role=store,
                format_version=BACKUP_CONTRACT_FORMAT_VERSION,
            )
            if is_refusal(fetched):
                return fetched
            decrypted = self.cipher.decrypt(fetched.value)
            if is_refusal(decrypted):
                return decrypted
            snap = StoreSnapshot.from_bytes(decrypted.value)
            exp = expected[store]
            if snap.to_bytes() != exp.to_bytes():
                return policy_rejection(
                    "live_restore",
                    "live restore payload does not match expected snapshot (FR-Q37; AD-27)",
                    store=store,
                )
            _write_snapshot(live, snap)
            restored_names.append(store)

        append: JournalAppendReceipt | None = None
        if journal is not None:
            recorded = journal.append_event(
                LIVE_RESTORE_EVENT,
                scope_path=scope_path,
                payload={
                    "command": LIVE_RESTORE_COMMAND,
                    "principal_class": PrincipalClass.OPERATOR.value,
                    "live_root": str(live),
                    "source_copy_version": max_version,
                    "stores_restored": list(restored_names),
                    "gap_0088_deferred": sorted(GAP_0088_DEFERRED),
                },
            )
            if is_refusal(recorded):
                return recorded
            append = recorded.value

        return Ok(
            LiveRestoreReceipt(
                command=LIVE_RESTORE_COMMAND,
                principal_class=PrincipalClass.OPERATOR.value,
                live_root=str(live),
                source_copy_version=max_version,
                stores_restored=tuple(restored_names),
                journal=append,
            )
        )
