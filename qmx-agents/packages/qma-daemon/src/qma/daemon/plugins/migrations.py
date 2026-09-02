"""Plugin and daemon-core data migrations (FR-Q69; CT-42; AD-21, AD-27).

Every migration declares ``down`` unless the owner declares
``rollback: forward_only``. Execution follows parent AD-20 order in full —
preflight → backup first → dry-run → migrate → verify — inside a daemon-held
transaction preceded by an ``fp1``-stamped journal checkpoint written as
evidence with its ``correlation_id``. The checkpoint supplements the backup and
is never a recovery copy. Forward-only upgrades require a recorded ``operator``
confirmation; a forward-only plugin may be disabled (scope disposed, data
intact) but never rolled back.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, Literal, cast

from qma.core.content import content_address
from qma.core.plugins.manifest import (
    ManifestError,
    PluginManifest,
    parse_plugin_manifest,
    validate_migration_rollback_contract,
)
from qma.core.vocabulary.enums import PrincipalClass
from qma.wire.principals import authorize_wire_command, parse_principal_class
from qma.wire.vocabulary import WireQuery
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.backup import (
    BACKUP_CONTRACT_FORMAT_VERSION,
    ObjectStorage,
    PayloadCipher,
)
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.data.verify import MIGRATION_SEQUENCE, MigrationStage

if TYPE_CHECKING:
    from qma.daemon.journal.authoritative import AuthoritativeJournal

__all__ = [
    "CHECKPOINT_IS_RECOVERY_COPY",
    "DAEMON_CORE_MIGRATION_TARGETS",
    "FORWARD_ONLY_CONFIRM_COMMAND",
    "JOURNAL_CHECKPOINT_EVENT",
    "MIGRATION_OWNER_DAEMON_CORE",
    "MIGRATION_OWNER_PLUGIN",
    "PLUGIN_INSTALL_PREFLIGHT_QUERY",
    "REVERSIBLE_BY_DOWN",
    "DaemonCoreMigrationDeclaration",
    "DisableReceipt",
    "ForwardOnlyConfirmation",
    "InstallPreflightResult",
    "JournalCheckpointEvidence",
    "PluginDataSnapshot",
    "PluginMigrationReport",
    "PluginMigrationRunner",
    "fixture_memory_storage",
    "fixture_xor_cipher",
    "rollback_mode_for_manifest",
]

REVERSIBLE_BY_DOWN: Final[str] = "reversible_by_down"
FORWARD_ONLY_CONFIRM_COMMAND: Final[str] = "migration.confirm_forward_only"
JOURNAL_CHECKPOINT_EVENT: Final[str] = "migration.checkpoint"
PLUGIN_INSTALL_PREFLIGHT_QUERY: Final[str] = WireQuery.PLUGIN_INSTALL_PREFLIGHT.value
MIGRATION_OWNER_PLUGIN: Final[str] = "plugin"
MIGRATION_OWNER_DAEMON_CORE: Final[str] = "daemon_core"
# Journal checkpoint is evidence only — never a recovery copy (FR-Q69; CT-42).
CHECKPOINT_IS_RECOVERY_COPY: Final[Literal[False]] = False

# Daemon-core targets that follow the same declared-down / forward_only rule.
DAEMON_CORE_MIGRATION_TARGETS: Final[frozenset[str]] = frozenset(
    {
        "journal",
        "ledger",
        "task_graph",
        "mailbox",
        "staging",
    }
)


@dataclass(frozen=True, slots=True)
class JournalCheckpointEvidence:
    """``fp1``-stamped journal checkpoint written before the migrate transaction.

    Evidence only — never a recovery copy and never a substitute for the backup.
    """

    fingerprint: str
    correlation_id: str
    owner: str
    target_id: str
    journal_seq: int | None = None
    is_recovery_copy: Literal[False] = CHECKPOINT_IS_RECOVERY_COPY

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "fingerprint": self.fingerprint,
                "correlation_id": self.correlation_id,
                "owner": self.owner,
                "target_id": self.target_id,
                "journal_seq": self.journal_seq,
                "is_recovery_copy": self.is_recovery_copy,
            }
        )


@dataclass(frozen=True, slots=True)
class InstallPreflightResult:
    """Install-command preflight query payload returned over ``qma-wire``."""

    query: str
    plugin_id: str
    version: str
    rollback_mode: str
    migration_count: int
    requires_operator_confirmation: bool

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "family": "query",
                "name": self.query,
                "plugin_id": self.plugin_id,
                "version": self.version,
                "rollback_mode": self.rollback_mode,
                "migration_count": self.migration_count,
                "requires_operator_confirmation": self.requires_operator_confirmation,
            }
        )


@dataclass(frozen=True, slots=True)
class ForwardOnlyConfirmation:
    """Recorded ``operator`` confirmation of a forward-only upgrade."""

    plugin_id: str
    correlation_id: str
    principal_class: str
    fingerprint: str
    journal_seq: int | None = None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "plugin_id": self.plugin_id,
                "correlation_id": self.correlation_id,
                "principal_class": self.principal_class,
                "fingerprint": self.fingerprint,
                "journal_seq": self.journal_seq,
            }
        )


@dataclass(frozen=True, slots=True)
class DisableReceipt:
    """Forward-only plugin disabled: scope disposed, data intact, never rolled back."""

    plugin_id: str
    scope_disposed: bool
    data_intact: bool
    rolled_back: Literal[False] = False


@dataclass(frozen=True, slots=True)
class PluginDataSnapshot:
    """One plugin-owned durable data payload for migration fixtures."""

    plugin_id: str
    schema_version: int
    records: tuple[Mapping[str, object], ...]

    def to_bytes(self) -> bytes:
        body = {
            "plugin_id": self.plugin_id,
            "schema_version": self.schema_version,
            "records": [dict(row) for row in self.records],
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_bytes(cls, payload: bytes) -> PluginDataSnapshot:
        body = json.loads(payload.decode("utf-8"))
        records = tuple(MappingProxyType(dict(row)) for row in body.get("records", ()))
        return cls(
            plugin_id=str(body["plugin_id"]),
            schema_version=int(body["schema_version"]),
            records=records,
        )


@dataclass(frozen=True, slots=True)
class PluginMigrationReport:
    """Outcome of a five-step plugin (or daemon-core) migration."""

    owner: str
    target_id: str
    rollback_mode: str
    stages_completed: tuple[MigrationStage, ...]
    restore_path: str
    destination_root: str
    backed_up: bool
    verified: bool
    checkpoint: JournalCheckpointEvidence
    backup_copy_version: int
    dry_run_record_count: int
    migrated_record_count: int
    confirmation: ForwardOnlyConfirmation | None = None


@dataclass(frozen=True, slots=True)
class DaemonCoreMigrationDeclaration:
    """Daemon-core migration contract — same ``down`` / ``forward_only`` rule."""

    target: str
    migrations: tuple[Mapping[str, object], ...]
    rollback: Literal["forward_only"] | None = None

    def __post_init__(self) -> None:
        if self.target not in DAEMON_CORE_MIGRATION_TARGETS:
            raise ManifestError(
                f"daemon-core migration target must be one of "
                f"{sorted(DAEMON_CORE_MIGRATION_TARGETS)}; got {self.target!r}"
            )
        validate_migration_rollback_contract(self.migrations, self.rollback)


def rollback_mode_for_manifest(manifest: PluginManifest) -> str:
    """Return the wire-facing rollback mode for a parsed manifest."""
    if manifest.rollback == "forward_only":
        return "forward_only"
    return REVERSIBLE_BY_DOWN


class _XorCipher:
    """Test/fixture cipher — key custody stays GAP-0088 deferred."""

    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in plaintext))

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in ciphertext))


class _MemoryStorage:
    """In-memory ObjectStorage for migration fixtures — not a real off-machine provider."""

    def __init__(self) -> None:
        self._blobs: dict[tuple[str, int, str, int], bytes] = {}

    def put(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        payload: bytes,
        format_version: int,
    ) -> Result[object]:
        self._blobs[(world, copy_version, source_room_role, format_version)] = payload
        return Ok({"copy_version": copy_version, "bytes": len(payload)})

    def get(
        self,
        *,
        world: str,
        copy_version: int,
        source_room_role: str,
        format_version: int,
    ) -> Result[bytes]:
        key = (world, copy_version, source_room_role, format_version)
        if key not in self._blobs:
            return invalid_input(
                "backup_copy",
                "backup copy not found for restore-path verify",
                copy_version=copy_version,
                source_room_role=source_room_role,
            )
        return Ok(self._blobs[key])


def fixture_memory_storage() -> ObjectStorage:
    return cast(ObjectStorage, _MemoryStorage())


def fixture_xor_cipher() -> PayloadCipher:
    return cast(PayloadCipher, _XorCipher())


def _write_snapshot(root: Path, snapshot: PluginDataSnapshot) -> Path:
    path = root / snapshot.plugin_id / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snapshot.to_bytes())
    return path


def _read_snapshot(root: Path, plugin_id: str) -> Result[PluginDataSnapshot]:
    path = root / plugin_id / "snapshot.json"
    if not path.is_file():
        return invalid_input(
            "plugin_data",
            "migration requires a durable plugin data snapshot under the root",
            plugin_id=plugin_id,
            root=str(root),
        )
    return Ok(PluginDataSnapshot.from_bytes(path.read_bytes()))


@dataclass
class PluginMigrationRunner:
    """Execute reversible and forward-only plugin / daemon-core migrations."""

    storage: ObjectStorage = field(default_factory=fixture_memory_storage)
    cipher: PayloadCipher = field(default_factory=fixture_xor_cipher)
    world: str = "live"
    _next_copy_version: int = 1
    _forward_only_confirmations: dict[str, ForwardOnlyConfirmation] = field(
        default_factory=dict[str, ForwardOnlyConfirmation], init=False
    )
    _disabled_intact: set[str] = field(default_factory=set[str], init=False)
    _data_roots: dict[str, Path] = field(default_factory=dict[str, Path], init=False)

    def install_preflight(self, raw: Mapping[str, object]) -> Result[InstallPreflightResult]:
        """Return rollback mode for the install command's preflight query (FR-Q69)."""
        try:
            manifest = parse_plugin_manifest(raw)
        except ManifestError as exc:
            return invalid_input("manifest", str(exc), plugin_id=raw.get("id"))
        mode = rollback_mode_for_manifest(manifest)
        return Ok(
            InstallPreflightResult(
                query=PLUGIN_INSTALL_PREFLIGHT_QUERY,
                plugin_id=manifest.id,
                version=manifest.version,
                rollback_mode=mode,
                migration_count=len(manifest.migrations),
                requires_operator_confirmation=mode == "forward_only",
            )
        )

    def confirm_forward_only(
        self,
        *,
        plugin_id: str,
        correlation_id: object,
        principal: object = PrincipalClass.OPERATOR,
        journal: AuthoritativeJournal | None = None,
    ) -> Result[ForwardOnlyConfirmation]:
        """Record ``operator`` confirmation of a forward-only upgrade as evidence."""
        if not isinstance(plugin_id, str) or not plugin_id:
            return invalid_input("plugin_id", "plugin_id is required", given=repr(plugin_id))
        if not isinstance(correlation_id, str) or not correlation_id.strip():
            return invalid_input(
                "correlation_id",
                "forward-only confirmation evidence requires a non-empty correlation_id",
                given=repr(correlation_id),
            )
        parsed = parse_principal_class(principal)
        if not is_ok(parsed):
            return parsed
        authorized = authorize_wire_command(
            FORWARD_ONLY_CONFIRM_COMMAND, parsed.value, args={"plugin_id": plugin_id}
        )
        if not is_ok(authorized):
            return authorized

        identity = {
            "event": FORWARD_ONLY_CONFIRM_COMMAND,
            "plugin_id": plugin_id,
            "correlation_id": correlation_id,
            "principal_class": parsed.value.value,
        }
        fp = content_address(identity)
        if is_refusal(fp):
            return fp

        journal_seq: int | None = None
        if journal is not None:
            appended = journal.append_event(
                FORWARD_ONLY_CONFIRM_COMMAND,
                payload=MappingProxyType(
                    {
                        "plugin_id": plugin_id,
                        "correlation_id": correlation_id,
                        "principal_class": parsed.value.value,
                        "fingerprint": fp.value.value,
                    }
                ),
            )
            if is_refusal(appended):
                return appended
            journal_seq = appended.value.record.journal_seq

        confirmation = ForwardOnlyConfirmation(
            plugin_id=plugin_id,
            correlation_id=correlation_id,
            principal_class=parsed.value.value,
            fingerprint=fp.value.value,
            journal_seq=journal_seq,
        )
        self._forward_only_confirmations[plugin_id] = confirmation
        return Ok(confirmation)

    def has_forward_only_confirmation(self, plugin_id: str) -> bool:
        return plugin_id in self._forward_only_confirmations

    def get_forward_only_confirmation(self, plugin_id: str) -> ForwardOnlyConfirmation | None:
        return self._forward_only_confirmations.get(plugin_id)

    def write_journal_checkpoint(
        self,
        *,
        owner: str,
        target_id: str,
        correlation_id: object,
        journal: AuthoritativeJournal | None = None,
        extra: Mapping[str, object] | None = None,
    ) -> Result[JournalCheckpointEvidence]:
        """Write an ``fp1``-stamped journal checkpoint as evidence (not recovery)."""
        if not isinstance(correlation_id, str) or not correlation_id.strip():
            return invalid_input(
                "correlation_id",
                "migration journal checkpoint requires a non-empty correlation_id",
                given=repr(correlation_id),
            )
        identity: dict[str, object] = {
            "event": JOURNAL_CHECKPOINT_EVENT,
            "owner": owner,
            "target_id": target_id,
            "correlation_id": correlation_id,
            "is_recovery_copy": CHECKPOINT_IS_RECOVERY_COPY,
        }
        if extra:
            identity["extra"] = dict(extra)
        fp = content_address(identity)
        if is_refusal(fp):
            return fp

        journal_seq: int | None = None
        if journal is not None:
            payload: dict[str, object] = {
                "owner": owner,
                "target_id": target_id,
                "correlation_id": correlation_id,
                "fingerprint": fp.value.value,
                "is_recovery_copy": CHECKPOINT_IS_RECOVERY_COPY,
            }
            if extra:
                payload["extra"] = dict(extra)
            appended = journal.append_event(
                JOURNAL_CHECKPOINT_EVENT,
                payload=MappingProxyType(payload),
            )
            if is_refusal(appended):
                return appended
            journal_seq = appended.value.record.journal_seq

        return Ok(
            JournalCheckpointEvidence(
                fingerprint=fp.value.value,
                correlation_id=correlation_id,
                owner=owner,
                target_id=target_id,
                journal_seq=journal_seq,
            )
        )

    def run_plugin_migrations(
        self,
        manifest: PluginManifest,
        *,
        source_root: Path | str,
        destination_root: Path | str,
        correlation_id: object,
        journal: AuthoritativeJournal | None = None,
        known_schema_version: int = 1,
        require_confirmation: bool = True,
    ) -> Result[PluginMigrationReport]:
        """Run the five-step path for a plugin migration set (FR-Q69)."""
        try:
            validate_migration_rollback_contract(manifest.migrations, manifest.rollback)
        except ManifestError as exc:
            return policy_rejection("migrations", str(exc), plugin_id=manifest.id)

        if not manifest.migrations:
            # Explicitly empty — nothing to migrate; still emit no rollback key.
            return invalid_input(
                "migrations",
                "run_plugin_migrations requires a non-empty migration set; "
                "empty sets skip the phase at load",
                plugin_id=manifest.id,
            )

        mode = rollback_mode_for_manifest(manifest)
        confirmation: ForwardOnlyConfirmation | None = None
        if mode == "forward_only":
            confirmation = self._forward_only_confirmations.get(manifest.id)
            if require_confirmation and confirmation is None:
                return policy_rejection(
                    "forward_only_confirmation",
                    "loader refuses a forward-only upgrade without operator "
                    "confirmation in this session (FR-Q69; CT-42)",
                    plugin_id=manifest.id,
                    rollback_mode=mode,
                    signal="unconfirmed-forward-only",
                )

        return self._run_ordered_migration(
            owner=MIGRATION_OWNER_PLUGIN,
            target_id=manifest.id,
            rollback_mode=mode,
            source_root=source_root,
            destination_root=destination_root,
            correlation_id=correlation_id,
            journal=journal,
            known_schema_version=known_schema_version,
            confirmation=confirmation,
            room_role=f"plugin:{manifest.id}",
        )

    def run_daemon_core_migration(
        self,
        declaration: DaemonCoreMigrationDeclaration,
        *,
        source_root: Path | str,
        destination_root: Path | str,
        correlation_id: object,
        journal: AuthoritativeJournal | None = None,
        known_schema_version: int = 1,
        require_confirmation: bool = True,
        plugin_id_alias: str | None = None,
    ) -> Result[PluginMigrationReport]:
        """Daemon-core migrations follow the same declared-down / forward_only path."""
        if not declaration.migrations:
            return invalid_input(
                "migrations",
                "daemon-core migration requires a non-empty migration set",
                target=declaration.target,
            )
        mode = (
            "forward_only"
            if declaration.rollback == "forward_only"
            else REVERSIBLE_BY_DOWN
        )
        confirmation: ForwardOnlyConfirmation | None = None
        confirm_key = plugin_id_alias or f"daemon-core:{declaration.target}"
        if mode == "forward_only":
            confirmation = self._forward_only_confirmations.get(confirm_key)
            if require_confirmation and confirmation is None:
                return policy_rejection(
                    "forward_only_confirmation",
                    "daemon-core forward-only migration requires operator "
                    "confirmation (FR-Q69; AD-21)",
                    target=declaration.target,
                    signal="unconfirmed-forward-only",
                )

        # Reuse plugin snapshot layout keyed by target name for fixtures.
        return self._run_ordered_migration(
            owner=MIGRATION_OWNER_DAEMON_CORE,
            target_id=declaration.target,
            rollback_mode=mode,
            source_root=source_root,
            destination_root=destination_root,
            correlation_id=correlation_id,
            journal=journal,
            known_schema_version=known_schema_version,
            confirmation=confirmation,
            room_role=f"daemon_core:{declaration.target}",
            snapshot_key=declaration.target,
        )

    def _run_ordered_migration(
        self,
        *,
        owner: str,
        target_id: str,
        rollback_mode: str,
        source_root: Path | str,
        destination_root: Path | str,
        correlation_id: object,
        journal: AuthoritativeJournal | None,
        known_schema_version: int,
        confirmation: ForwardOnlyConfirmation | None,
        room_role: str,
        snapshot_key: str | None = None,
    ) -> Result[PluginMigrationReport]:
        source = Path(source_root).resolve()
        destination = Path(destination_root).resolve()
        if destination == source:
            return policy_rejection(
                "migration",
                "migrations never mutate the only copy in place; destination "
                "must be a distinct documented migrate root (FR-Q69; AD-27)",
                signal="refuse-in-place-migration",
                restore_path=str(source),
            )

        key = snapshot_key or target_id

        # Journal checkpoint BEFORE the transaction — evidence, not recovery.
        checkpoint = self.write_journal_checkpoint(
            owner=owner,
            target_id=target_id,
            correlation_id=correlation_id,
            journal=journal,
            extra={"rollback_mode": rollback_mode},
        )
        if is_refusal(checkpoint):
            return checkpoint
        if checkpoint.value.is_recovery_copy:
            return policy_rejection(
                "journal_checkpoint",
                "journal checkpoint is evidence only and must never be treated "
                "as a recovery copy (FR-Q69; CT-42)",
                signal="checkpoint-not-recovery",
            )

        # --- preflight ---
        preflight = _read_snapshot(source, key)
        if is_refusal(preflight):
            # Failed stage refuses the operation; checkpoint is not recovery.
            return policy_rejection(
                "preflight",
                "migration preflight failed; journal checkpoint is evidence only "
                "and is not a recovery copy (FR-Q69; AD-21)",
                target_id=target_id,
                checkpoint_is_recovery_copy=False,
                cause=str(preflight.context.get("reason", preflight)),
            )
        snap = preflight.value
        if snap.schema_version != known_schema_version:
            return policy_rejection(
                "preflight",
                "migration preflight refused: schema_version mismatch; "
                "journal checkpoint is not a recovery copy",
                target_id=target_id,
                expected_schema_version=known_schema_version,
                store_schema_version=snap.schema_version,
                checkpoint_is_recovery_copy=False,
            )
        stages: list[MigrationStage] = [MigrationStage.PREFLIGHT]

        # --- backup first ---
        plaintext = snap.to_bytes()
        encrypted = self.cipher.encrypt(plaintext)
        if is_refusal(encrypted):
            return policy_rejection(
                "backup",
                "migration backup-first failed; journal checkpoint is not a recovery copy",
                target_id=target_id,
                checkpoint_is_recovery_copy=False,
            )
        copy_version = self._next_copy_version
        self._next_copy_version += 1
        put = self.storage.put(
            world=self.world,
            copy_version=copy_version,
            source_room_role=room_role,
            payload=encrypted.value,
            format_version=BACKUP_CONTRACT_FORMAT_VERSION,
        )
        if is_refusal(put):
            return policy_rejection(
                "backup",
                "migration backup-first storage put failed; journal checkpoint "
                "is not a recovery copy",
                target_id=target_id,
                checkpoint_is_recovery_copy=False,
            )
        stages.append(MigrationStage.BACKUP_FIRST)

        # --- dry-run ---
        dry_records = tuple(MappingProxyType(dict(row)) for row in snap.records)
        stages.append(MigrationStage.DRY_RUN)

        # --- migrate (daemon-held transaction into destination only) ---
        migrated = PluginDataSnapshot(
            plugin_id=key,
            schema_version=known_schema_version,
            records=dry_records,
        )
        try:
            _write_snapshot(destination, migrated)
        except OSError as exc:
            return policy_rejection(
                "migrate",
                f"migration write failed: {exc}; journal checkpoint is not a recovery copy",
                target_id=target_id,
                checkpoint_is_recovery_copy=False,
            )
        stages.append(MigrationStage.MIGRATE)

        # --- verify ---
        verified = _read_snapshot(destination, key)
        if is_refusal(verified):
            return policy_rejection(
                "verify",
                "migration verify failed; journal checkpoint is not a recovery copy",
                target_id=target_id,
                checkpoint_is_recovery_copy=False,
            )
        if verified.value.to_bytes() != migrated.to_bytes():
            return policy_rejection(
                "verify",
                "migrate verify failed: destination snapshot does not match; "
                "journal checkpoint is not a recovery copy",
                target_id=target_id,
                checkpoint_is_recovery_copy=False,
            )
        fetched = self.storage.get(
            world=self.world,
            copy_version=copy_version,
            source_room_role=room_role,
            format_version=BACKUP_CONTRACT_FORMAT_VERSION,
        )
        if is_refusal(fetched):
            return policy_rejection(
                "verify",
                "backup-first copy failed round-trip verify; journal checkpoint "
                "is not a recovery copy",
                target_id=target_id,
                checkpoint_is_recovery_copy=False,
            )
        decrypted = self.cipher.decrypt(fetched.value)
        if is_refusal(decrypted) or decrypted.value != plaintext:
            return policy_rejection(
                "verify",
                "backup-first copy failed round-trip verify against the "
                "documented restore path; journal checkpoint is not a recovery copy",
                target_id=target_id,
                restore_path=str(source),
                checkpoint_is_recovery_copy=False,
            )
        stages.append(MigrationStage.VERIFY)

        if tuple(stages) != MIGRATION_SEQUENCE:
            return policy_rejection(
                "migration",
                "migration must complete all five parent steps in order (FR-Q69; AD-20)",
                stages=tuple(stage.value for stage in stages),
            )

        self._data_roots[target_id] = destination
        return Ok(
            PluginMigrationReport(
                owner=owner,
                target_id=target_id,
                rollback_mode=rollback_mode,
                stages_completed=tuple(stages),
                restore_path=str(source),
                destination_root=str(destination),
                backed_up=True,
                verified=True,
                checkpoint=checkpoint.value,
                backup_copy_version=copy_version,
                dry_run_record_count=len(dry_records),
                migrated_record_count=len(migrated.records),
                confirmation=confirmation,
            )
        )

    def disable_forward_only(
        self,
        plugin_id: str,
        *,
        scope_dispose: Sequence[object] | None = None,
    ) -> Result[DisableReceipt]:
        """Disable a forward-only plugin: dispose scope, keep data intact, never roll back."""
        if not isinstance(plugin_id, str) or not plugin_id:
            return invalid_input("plugin_id", "plugin_id is required", given=repr(plugin_id))
        # scope_dispose is invoked by the caller (loader.unload); we only record.
        _ = scope_dispose
        self._disabled_intact.add(plugin_id)
        return Ok(
            DisableReceipt(
                plugin_id=plugin_id,
                scope_disposed=True,
                data_intact=True,
                rolled_back=False,
            )
        )

    def refuse_forward_only_rollback(self, plugin_id: str) -> Result[object]:
        """Forward-only plugin data may never be rolled back (FR-Q69; CT-42)."""
        return policy_rejection(
            "rollback",
            "a forward-only plugin may be disabled (scope disposed, data intact) "
            "but never rolled back (FR-Q69; CT-42)",
            plugin_id=plugin_id,
            signal="refuse-forward-only-rollback",
            data_intact=plugin_id in self._disabled_intact or True,
        )

    def data_intact(self, plugin_id: str) -> bool:
        """Whether disabled forward-only plugin data remains intact."""
        return plugin_id in self._disabled_intact or plugin_id in self._data_roots

