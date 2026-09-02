"""``qmn-backup.timer`` oneshot — encrypted rclone push of committed prefixes.

ExecStart: ``python -m qmn.data.backup_run``. The V1 ObjectStorage path is
local staging plus rclone. Factory tests inject a local-filesystem rclone
runner, an isolated backend root, and a generated test key. A live Backblaze
B2 bucket is soak-local and refused without human accounts (AR-87, DEC-0198).
The unit holds no trading power.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    World,
    fingerprint_bytes,
    is_refusal,
)
from qmf.core.refusal import Retryability

from qmn.data._refuse import clean_token, invalid, policy, storage
from qmn.data.backup import (
    BACKUP_PAYLOAD_KEY_SLOT,
    CRYPTO_ALGORITHM,
    LIVE_BUCKET_TOKENS,
    LIVE_BUCKET_TONIGHT,
    PAYLOAD_KEY_SIZE,
    BackupPayloadCipher,
    BackupPurgeDecision,
    evaluate_backup_copy_purge,
    refuse_live_bucket_tonight,
    refuse_payload_key_ceremony,
)
from qmn.secrets.holders import BACKUP_UNIT

__all__ = [
    "BACKED_UP_ROOM_ROLES",
    "BACKUP_PUSH_SURFACE",
    "EXCLUDED_UNLESS_CITED_ROLES",
    "LOCAL_TEST_BACKEND",
    "RCLONE_BINARY",
    "RCLONE_REMOTE_NAME",
    "BackupCommittedPrefix",
    "BackupManifest",
    "BackupPushReceipt",
    "BackupPushReport",
    "LocalFilesystemRcloneRunner",
    "RcloneCommand",
    "RcloneExecution",
    "RecordingRcloneRunner",
    "apply_backup_retention",
    "build_rclone_command",
    "generate_test_payload_key",
    "main",
    "push_committed_prefixes",
    "refuse_live_b2_without_soak",
    "refuse_processed_room",
    "refuse_secret_in_evidence",
    "refuse_uncommitted_backup_prefix",
    "validate_rclone_argv",
]


BACKUP_PUSH_SURFACE: Final[str] = "qmn.data.backup_run"
LOCAL_TEST_BACKEND: Final[str] = "local-test"
RCLONE_BINARY: Final[str] = "rclone"
RCLONE_REMOTE_NAME: Final[str] = "qmx-backup"
RCLONE_PINNED_VERSION: Final[str] = "v1.75.0"
STAGING_DEFAULT: Final[str] = "/var/lib/qmx/staging"
INDEX_NAME: Final[str] = "backup-index.json"
RCLONE_CONFIG_NAME: Final[str] = "rclone.conf"
CIPHERTEXT_SUFFIX: Final[str] = ".enc"
MANIFEST_SUFFIX: Final[str] = ".manifest.json"

BACKED_UP_ROOM_ROLES: Final[frozenset[str]] = frozenset(
    {
        "immutable raw archive",
        "journal",
        "registry room",
        "sealed-archive",
        "split-governed research door",
    }
)
EXCLUDED_UNLESS_CITED_ROLES: Final[frozenset[str]] = frozenset({"processed"})
BACKUP_WORLDS: Final[frozenset[str]] = frozenset({World.LIVE.value, World.REPLAY.value})

_UNCOMMITTED_ID: Final[str] = "data.backup.uncommitted"
_PROCESSED_ID: Final[str] = "data.backup.processed_excluded"
_LEAK_ID: Final[str] = "data.backup.secret_in_evidence"
_RCLONE_ID: Final[str] = "data.backup.rclone_transfer"
_ACCOUNT_ID: Final[str] = "data.backup.missing_bucket_account"
_MUTATE_ID: Final[str] = "data.backup.mutate_existing"
_WORLD_ID: Final[str] = "data.backup.world"
_MAX_PREFIX_BYTES: Final[int] = 1 << 20

_ROLE_SLUGS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "immutable raw archive": "immutable-raw-archive",
        "journal": "journal",
        "registry room": "registry-room",
        "sealed-archive": "sealed-archive",
        "split-governed research door": "research-door",
        "processed": "processed",
    }
)
_MANIFEST_KEYS: Final[frozenset[str]] = frozenset(
    {
        "contract_format_version",
        "world",
        "room_role",
        "copy_version",
        "prefix_id",
        "start",
        "last_committed_sequence",
        "open_segment_boundary",
        "payload_fingerprint",
        "content_fp1",
        "encryption_required",
        "encryption_algorithm",
        "committed",
        "cited",
    }
)
_RECEIPT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "argv",
        "remote",
        "source",
        "dest",
        "binary",
        "pinned_version",
        "returncode",
        "copied",
        "resumed",
    }
)
_FORBIDDEN_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset(
    {"payload", "plaintext", "key", "ciphertext"}
)
_SECRET_TOKENS: Final[tuple[str, ...]] = (
    "password",
    "secret",
    "credential",
    "applicationkey",
    "accountid",
    "authorization",
    "bearer",
    "backup-payload-key",
    "object-storage",
    "plaintext",
)
_FORBIDDEN_RCLONE_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "--b2-account",
        "--b2-key",
        "--s3-access-key-id",
        "--s3-secret-access-key",
        "--password",
        "--ask-password",
        "--crypt-password",
        "--crypt-password2",
    }
)
_TRADING_POWER_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "place_order",
        "cancel_order",
        "close_position",
        "close_all",
        "amend_protection",
        "flatten",
        "promote",
        "activate",
    }
)


class RcloneRunner(Protocol):
    """Executes one constructed rclone argv. Tests inject a local copier."""

    def run(self, argv: Sequence[str], /) -> Result[RcloneExecution]: ...


@dataclass(frozen=True, slots=True)
class RcloneCommand:
    """Pinned rclone copy argv — credentials never appear as flags."""

    argv: tuple[str, ...]
    remote: str
    source: str
    dest: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "argv": list(self.argv),
                "remote": self.remote,
                "source": self.source,
                "dest": self.dest,
                "binary": RCLONE_BINARY,
                "pinned_version": RCLONE_PINNED_VERSION,
            }
        )


@dataclass(frozen=True, slots=True)
class RcloneExecution:
    """Outcome of one rclone argv, with the argv retained for evidence."""

    argv: tuple[str, ...]
    returncode: int
    copied: bool
    resumed: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "argv": list(self.argv),
                "returncode": self.returncode,
                "copied": self.copied,
                "resumed": self.resumed,
            }
        )


@dataclass(frozen=True, slots=True)
class BackupManifest:
    """Ciphertext-only off-host descriptor. No credentials, no plaintext."""

    world: str
    room_role: str
    copy_version: int
    prefix_id: str
    start: int
    last_committed_sequence: int
    open_segment_boundary: int
    payload_fingerprint: str
    content_fp1: str
    committed: bool
    cited: bool
    contract_format_version: int = 1
    encryption_required: bool = True
    encryption_algorithm: str = CRYPTO_ALGORITHM

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "contract_format_version": self.contract_format_version,
                "world": self.world,
                "room_role": self.room_role,
                "copy_version": self.copy_version,
                "prefix_id": self.prefix_id,
                "start": self.start,
                "last_committed_sequence": self.last_committed_sequence,
                "open_segment_boundary": self.open_segment_boundary,
                "payload_fingerprint": self.payload_fingerprint,
                "content_fp1": self.content_fp1,
                "encryption_required": self.encryption_required,
                "encryption_algorithm": self.encryption_algorithm,
                "committed": self.committed,
                "cited": self.cited,
            }
        )


@dataclass(frozen=True, slots=True)
class BackupPushReceipt:
    """One successful (or idempotent) encrypted prefix push."""

    world: str
    room_role: str
    prefix_id: str
    copy_version: int
    payload_fingerprint: str
    object_key: str
    copied: bool
    resumed: bool
    rclone: Mapping[str, object]
    manifest: Mapping[str, object]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "world": self.world,
                "room_role": self.room_role,
                "prefix_id": self.prefix_id,
                "copy_version": self.copy_version,
                "payload_fingerprint": self.payload_fingerprint,
                "object_key": self.object_key,
                "copied": self.copied,
                "resumed": self.resumed,
                "rclone": dict(self.rclone),
                "manifest": dict(self.manifest),
            }
        )


@dataclass(frozen=True, slots=True)
class BackupPushReport:
    """One backup-unit firing across the named room set."""

    backend: str
    soak_local: bool
    receipts: tuple[BackupPushReceipt, ...]
    rclone_argv: tuple[str, ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "backend": self.backend,
                "soak_local": self.soak_local,
                "receipt_count": len(self.receipts),
                "receipts": [dict(item.as_mapping()) for item in self.receipts],
                "rclone_argv": list(self.rclone_argv),
            }
        )


@dataclass(frozen=True, slots=True)
class BackupCommittedPrefix:
    """One committed prefix the backup unit may encrypt and push."""

    world: World
    room_role: str
    prefix_id: str
    start: int
    end: int
    payload: bytes
    content_fp1: Fingerprint
    committed: bool
    cited: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "world": self.world.value,
                "room_role": self.room_role,
                "prefix_id": self.prefix_id,
                "start": self.start,
                "last_committed_sequence": self.end,
                "open_segment_boundary": self.end,
                "content_fp1": self.content_fp1.value,
                "committed": self.committed,
                "cited": self.cited,
                "payload_bytes": len(self.payload),
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        world: object,
        room_role: object,
        prefix_id: object,
        start: object,
        end: object,
        payload: object,
        committed: object,
        cited: object = False,
    ) -> Result[BackupCommittedPrefix]:
        resolved = _as_world(world)
        if is_refusal(resolved):
            return resolved
        role = _as_backup_role(room_role, cited=cited)
        if is_refusal(role):
            return role
        ident = _segment(prefix_id, field="prefix_id")
        if is_refusal(ident):
            return ident
        start_n = _as_nonneg_int(start, "start")
        if is_refusal(start_n):
            return start_n
        end_n = _as_nonneg_int(end, "end")
        if is_refusal(end_n):
            return end_n
        if end_n.value <= start_n.value:
            return invalid(
                "window",
                "a backup prefix is a non-empty [start, end) committed sequence",
                start=start_n.value,
                end=end_n.value,
            )
        if committed is not True:
            return refuse_uncommitted_backup_prefix(prefix_id=ident.value)
        if not isinstance(payload, (bytes, bytearray)):
            return invalid(
                "payload",
                "a backup prefix carries raw committed bytes",
                given=repr(type(payload).__name__),
            )
        body = bytes(payload)
        if len(body) > _MAX_PREFIX_BYTES:
            return policy(
                "payload",
                "a backup prefix exceeds the size cap",
                size=len(body),
                cap=_MAX_PREFIX_BYTES,
            )
        if not isinstance(cited, bool):
            return invalid("cited", "cited is a boolean", given=repr(cited))
        return Ok(
            cls(
                world=resolved.value,
                room_role=role.value,
                prefix_id=ident.value,
                start=start_n.value,
                end=end_n.value,
                payload=body,
                content_fp1=fingerprint_bytes(body),
                committed=True,
                cited=cited,
            )
        )


class LocalFilesystemRcloneRunner:
    """Interprets the production rclone copy argv against a local dest root."""

    def __init__(self, backend_root: Path, *, fail: bool = False) -> None:
        self.backend_root = backend_root
        self.fail = fail
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: Sequence[str], /) -> Result[RcloneExecution]:
        checked = validate_rclone_argv(argv)
        if is_refusal(checked):
            return checked
        argv_t = tuple(str(part) for part in argv)
        self.calls.append(argv_t)
        if self.fail:
            return refuse_rclone_transfer(returncode=1, argv=argv_t)
        source, dest = _copy_endpoints(argv_t)
        dest_rel = dest.split(":", 1)[1] if ":" in dest else dest
        dest_root = self.backend_root / dest_rel
        src_path = Path(source)
        ignore_existing = "--ignore-existing" in argv_t
        copied = False
        resumed = False
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
            for src_file in _iter_files(src_path):
                relative = src_file.relative_to(src_path)
                target = dest_root / relative
                if target.exists():
                    if target.read_bytes() != src_file.read_bytes():
                        return policy(
                            "object",
                            "rclone must never mutate an existing versioned copy (DEC-0118)",
                            failure_id=_MUTATE_ID,
                            object_key=relative.as_posix(),
                        )
                    resumed = True
                    if ignore_existing:
                        continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, target)
                copied = True
        except OSError:
            return refuse_rclone_transfer(returncode=1, argv=argv_t)
        return Ok(
            RcloneExecution(
                argv=argv_t,
                returncode=0,
                copied=copied,
                resumed=resumed and not copied,
            )
        )


class RecordingRcloneRunner:
    """Test double that records argv and optionally fails the transfer."""

    def __init__(self, inner: RcloneRunner, *, fail: bool = False) -> None:
        self.inner = inner
        self.fail = fail
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: Sequence[str], /) -> Result[RcloneExecution]:
        argv_t = tuple(str(part) for part in argv)
        self.calls.append(argv_t)
        if self.fail:
            return refuse_rclone_transfer(returncode=2, argv=argv_t)
        return self.inner.run(argv)


class SubprocessRcloneRunner:
    """Production runner. Tests never invoke this against a live bucket."""

    def run(self, argv: Sequence[str], /) -> Result[RcloneExecution]:
        checked = validate_rclone_argv(argv)
        if is_refusal(checked):
            return checked
        argv_t = tuple(str(part) for part in argv)
        try:
            proc = subprocess.run(
                argv_t,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired):
            return refuse_rclone_transfer(returncode=1, argv=argv_t)
        if proc.returncode != 0:
            return refuse_rclone_transfer(returncode=proc.returncode, argv=argv_t)
        return Ok(RcloneExecution(argv=argv_t, returncode=0, copied=True, resumed=False))


def refuse_uncommitted_backup_prefix(*, prefix_id: object) -> TypedRefusal:
    """Refuse a prefix that is not sealed at a committed sequence boundary."""
    return policy(
        "prefix",
        "the backup unit copies only journal segments sealed at a committed "
        "sequence boundary (DEC-0198, DEC-0253)",
        failure_id=_UNCOMMITTED_ID,
        prefix_id=repr(prefix_id),
    )


def refuse_processed_room(*, room_role: object, cited: object = False) -> TypedRefusal:
    """Processed/rebuildable rooms stay excluded unless a result label cites them."""
    return policy(
        "room_role",
        "processed and rebuildable rooms are excluded from the off-host copy "
        "unless a result label cites them (DEC-0198, DEC-0253)",
        failure_id=_PROCESSED_ID,
        room_role=repr(room_role),
        cited=bool(cited),
    )


def refuse_secret_in_evidence(*, field: object = "manifest") -> TypedRefusal:
    """Credentials and plaintext never enter backup metadata or logs."""
    return policy(
        "evidence",
        "credentials and plaintext never enter backup metadata or logs (CT-14, DEC-0045)",
        failure_id=_LEAK_ID,
        evidence_field=repr(field),
    )


def refuse_live_b2_without_soak(
    *,
    backend: object,
    soak_local: object = False,
    has_account: object = False,
) -> Result[None]:
    """Live B2 is soak-local; missing human accounts do not block local tests."""
    token = clean_token(backend) or ""
    if token not in LIVE_BUCKET_TOKENS:
        return Ok(None)
    if soak_local is not True:
        return refuse_live_bucket_tonight(provider=token)
    if has_account is not True:
        return policy(
            "provider",
            "soak-local Backblaze B2 push requires a human bucket account; "
            "missing accounts block no local-test or unrelated branch (AR-87)",
            failure_id=_ACCOUNT_ID,
            backend=token,
            soak_local=True,
            live_bucket_tonight=LIVE_BUCKET_TONIGHT,
        )
    return refuse_live_bucket_tonight(provider=token)


def refuse_rclone_transfer(*, returncode: object, argv: Sequence[str]) -> TypedRefusal:
    """Unreachable or rejected rclone copy is a storage failure, never completion."""
    return storage(
        "rclone",
        "rclone did not accept the ciphertext copy; completion is not claimed (DEC-0109, DEC-0118)",
        failure_id=_RCLONE_ID,
        returncode=repr(returncode),
        argv=_public_argv(argv),
        retryability=Retryability.YES,
    )


def generate_test_payload_key(*, backend: object) -> Result[bytes]:
    """Mint a 32-byte test key only for the isolated local-test backend."""
    token = clean_token(backend)
    if token != LOCAL_TEST_BACKEND:
        return refuse_payload_key_ceremony(request="generate")
    key = os.urandom(PAYLOAD_KEY_SIZE)  # ambient-scan: allow — local-test key
    return Ok(key)


def build_rclone_command(
    *,
    staging: Path,
    config_path: Path,
    dest_spec: str,
) -> Result[RcloneCommand]:
    """Construct the pinned rclone copy argv (checksum, ignore-existing, no secrets)."""
    dest_token = clean_token(dest_spec)
    if dest_token is None or not dest_token.startswith(f"{RCLONE_REMOTE_NAME}:"):
        return invalid(
            "dest",
            "rclone dest is qmx-backup:<prefix> against the configured backend",
            given=repr(dest_spec),
        )
    argv = (
        RCLONE_BINARY,
        "--config",
        str(config_path),
        "copy",
        "--checksum",
        "--ignore-existing",
        str(staging),
        dest_token,
    )
    checked = validate_rclone_argv(argv)
    if is_refusal(checked):
        return checked
    return Ok(
        RcloneCommand(
            argv=argv,
            remote=RCLONE_REMOTE_NAME,
            source=str(staging),
            dest=dest_token,
        )
    )


def validate_rclone_argv(argv: Sequence[str]) -> Result[None]:
    """Refuse credential flags, trading-power tokens, or a non-rclone binary."""
    if not argv or argv[0] != RCLONE_BINARY:
        return invalid("argv", "backup transfer argv starts with the pinned rclone binary")
    lowered = [part.lower() for part in argv]
    for flag in _FORBIDDEN_RCLONE_FLAGS:
        if any(part.startswith(flag) for part in lowered):
            return refuse_secret_in_evidence(field="rclone-argv")
    joined = " ".join(lowered)
    for token in _SECRET_TOKENS:
        if token in joined.replace("_", "").replace("-", ""):
            return refuse_secret_in_evidence(field="rclone-argv")
    for power in _TRADING_POWER_TOKENS:
        if power in joined:
            return policy(
                "argv",
                "the backup unit invokes no trading power",
                failure_id="data.backup.trading_power",
                power=power,
            )
    if "copy" not in argv:
        return invalid("argv", "rclone backup transfer is copy, never sync-delete")
    return Ok(None)


def push_committed_prefixes(
    prefixes: Sequence[object],
    *,
    cipher: object,
    staging: Path,
    remote_root: Path,
    runner: RcloneRunner,
    backend: object = LOCAL_TEST_BACKEND,
    soak_local: object = False,
    has_account: object = False,
    dest_name: str = "objects",
) -> Result[BackupPushReport]:
    """Encrypt committed prefixes, stage ciphertext, rclone copy, journal retention."""
    gated = refuse_live_b2_without_soak(
        backend=backend, soak_local=soak_local, has_account=has_account
    )
    if is_refusal(gated):
        return gated
    if not isinstance(cipher, BackupPayloadCipher):
        return invalid(
            "cipher",
            "backup push encrypts through BackupPayloadCipher",
            given=repr(type(cipher).__name__),
        )
    backend_token = clean_token(backend) or LOCAL_TEST_BACKEND
    parsed: list[BackupCommittedPrefix] = []
    for item in prefixes:
        if not isinstance(item, BackupCommittedPrefix):
            return invalid(
                "prefix",
                "backup push copies a BackupCommittedPrefix",
                given=repr(type(item).__name__),
            )
        parsed.append(item)

    prepared = _ensure_dir(staging)
    if is_refusal(prepared):
        return prepared
    staging_dir = _contained_dir(staging, staging)
    if is_refusal(staging_dir):
        return staging_dir
    objects_dir = staging_dir.value / "objects"
    created = _ensure_dir(objects_dir)
    if is_refusal(created):
        return created
    config_path = staging_dir.value / RCLONE_CONFIG_NAME
    written_cfg = _write_local_rclone_config(config_path)
    if is_refusal(written_cfg):
        return written_cfg
    index = _load_index(staging_dir.value)
    staged_rows: list[tuple[BackupCommittedPrefix, bytes, BackupManifest, str, int, bool]] = []
    for prefix in parsed:
        one = _push_one(
            prefix,
            cipher=cipher,
            objects_dir=objects_dir,
            index=index,
        )
        if is_refusal(one):
            return one
        staged_rows.append(one.value)
        _prefix, ciphertext, manifest, object_key, _version, _reused = one.value
        written = _stage_pair(objects_dir, object_key, ciphertext, manifest)
        if is_refusal(written):
            return written
        leaked = _refuse_if_leaked(manifest.as_mapping())
        if is_refusal(leaked):
            return leaked

    command = build_rclone_command(
        staging=objects_dir,
        config_path=config_path,
        dest_spec=f"{RCLONE_REMOTE_NAME}:{dest_name}",
    )
    if is_refusal(command):
        return command
    leaked_cmd = _refuse_if_leaked(command.value.as_mapping())
    if is_refusal(leaked_cmd):
        return leaked_cmd
    transferred = runner.run(command.value.argv)
    if is_refusal(transferred):
        return transferred
    execution = transferred.value
    receipts: list[BackupPushReceipt] = []
    for prefix, _ciphertext, manifest, object_key, copy_version, reused in staged_rows:
        receipt = BackupPushReceipt(
            world=prefix.world.value,
            room_role=prefix.room_role,
            prefix_id=prefix.prefix_id,
            copy_version=copy_version,
            payload_fingerprint=manifest.payload_fingerprint,
            object_key=object_key,
            copied=execution.copied and not reused,
            resumed=reused or execution.resumed,
            rclone=execution.as_mapping(),
            manifest=manifest.as_mapping(),
        )
        receipts.append(receipt)
        index[_index_key(prefix)] = {
            "copy_version": copy_version,
            "object_key": object_key,
            "payload_fingerprint": manifest.payload_fingerprint,
            "content_fp1": prefix.content_fp1.value,
        }

    persisted = _save_index(staging_dir.value, index)
    if is_refusal(persisted):
        return persisted
    return Ok(
        BackupPushReport(
            backend=backend_token,
            soak_local=bool(soak_local),
            receipts=tuple(receipts),
            rclone_argv=command.value.argv,
        )
    )


def apply_backup_retention(
    candidate: object,
    *,
    journal: object,
) -> Result[BackupPurgeDecision]:
    """Retention uses the Story 27.5 declared-law path, never a provider default."""
    return evaluate_backup_copy_purge(candidate, journal=journal)


def main(argv: list[str] | None = None) -> int:
    """Systemd oneshot. Factory tests drive :func:`push_committed_prefixes`."""
    args = list(sys.argv[1:] if argv is None else argv)
    backend = LOCAL_TEST_BACKEND if "--backend" in args else "backblaze-b2"
    if "--backend" in args:
        idx = args.index("--backend")
        if idx + 1 < len(args):
            backend = args[idx + 1]
    soak = "--soak-local" in args
    if backend in LIVE_BUCKET_TOKENS:
        refused = refuse_live_b2_without_soak(backend=backend, soak_local=soak, has_account=False)
        if is_refusal(refused):
            return 1
    # Unbound oneshot refuses rather than inventing a live bucket.
    _ = (STAGING_DEFAULT, BACKUP_UNIT, BACKUP_PAYLOAD_KEY_SLOT)
    return 1


def _push_one(
    prefix: BackupCommittedPrefix,
    *,
    cipher: BackupPayloadCipher,
    objects_dir: Path,
    index: dict[str, dict[str, object]],
) -> Result[tuple[BackupCommittedPrefix, bytes, BackupManifest, str, int, bool]]:
    key = _index_key(prefix)
    existing = index.get(key)
    if existing is not None:
        object_key = str(existing["object_key"])
        raw_version = existing["copy_version"]
        if not isinstance(raw_version, int) or isinstance(raw_version, bool):
            copy_version = _next_version(index)
        else:
            copy_version = raw_version
        staged = objects_dir / object_key
        if staged.is_file() and not staged.is_symlink():
            ciphertext = staged.read_bytes()
            digest = fingerprint_bytes(ciphertext).value
            if digest == existing.get("payload_fingerprint"):
                manifest = _manifest_for(prefix, copy_version=copy_version, digest=digest)
                return Ok((prefix, ciphertext, manifest, object_key, copy_version, True))
    copy_version = _next_version(index)
    encrypted = cipher.encrypt(prefix.payload)
    if is_refusal(encrypted):
        return encrypted
    ciphertext = encrypted.value
    if not ciphertext or ciphertext == prefix.payload:
        return storage(
            "ciphertext",
            "encryption is required; plaintext must not be staged",
            failure_id=_LEAK_ID,
            retryability=Retryability.NO,
        )
    digest = fingerprint_bytes(ciphertext).value
    slug = _ROLE_SLUGS[prefix.room_role]
    object_key = f"{prefix.world.value}/{slug}/v{copy_version}{CIPHERTEXT_SUFFIX}"
    manifest = _manifest_for(prefix, copy_version=copy_version, digest=digest)
    return Ok((prefix, ciphertext, manifest, object_key, copy_version, False))


def _manifest_for(
    prefix: BackupCommittedPrefix, *, copy_version: int, digest: str
) -> BackupManifest:
    return BackupManifest(
        world=prefix.world.value,
        room_role=prefix.room_role,
        copy_version=copy_version,
        prefix_id=prefix.prefix_id,
        start=prefix.start,
        last_committed_sequence=prefix.end,
        open_segment_boundary=prefix.end,
        payload_fingerprint=digest,
        content_fp1=prefix.content_fp1.value,
        committed=True,
        cited=prefix.cited,
    )


def _stage_pair(
    objects_dir: Path,
    object_key: str,
    ciphertext: bytes,
    manifest: BackupManifest,
) -> Result[None]:
    dest = objects_dir / object_key
    contained = _contained_file(objects_dir, dest)
    if is_refusal(contained):
        return contained
    written = _atomic_write(contained.value, ciphertext)
    if is_refusal(written):
        return written
    man_path = contained.value.with_suffix(MANIFEST_SUFFIX)
    body = json.dumps(dict(manifest.as_mapping()), sort_keys=True) + "\n"
    return _atomic_write(man_path, body.encode("utf-8"))


def _write_local_rclone_config(path: Path) -> Result[None]:
    body = f"[{RCLONE_REMOTE_NAME}]\ntype = local\n"
    return _atomic_write(path, body.encode("utf-8"))


def _load_index(staging: Path) -> dict[str, dict[str, object]]:
    path = staging / INDEX_NAME
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(body, dict):
        return {}
    payload = cast("dict[str, object]", body)
    out: dict[str, dict[str, object]] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            inner = cast("dict[str, object]", value)
            out[key] = dict(inner)
    return out


def _save_index(staging: Path, index: Mapping[str, Mapping[str, object]]) -> Result[None]:
    path = staging / INDEX_NAME
    payload = json.dumps(index, sort_keys=True) + "\n"
    return _atomic_write(path, payload.encode("utf-8"))


def _index_key(prefix: BackupCommittedPrefix) -> str:
    return f"{prefix.world.value}/{prefix.room_role}/{prefix.prefix_id}/{prefix.start}-{prefix.end}"


def _next_version(index: Mapping[str, Mapping[str, object]]) -> int:
    highest = 0
    for row in index.values():
        raw = row.get("copy_version", 0)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw > highest:
            highest = raw
    return highest + 1


def _as_world(value: object) -> Result[World]:
    if isinstance(value, World):
        resolved = value
    elif isinstance(value, str):
        try:
            resolved = World(value)
        except ValueError:
            return invalid(
                "world",
                "world is one of the closed set live | replay | simulated",
                given=value,
            )
    else:
        return invalid(
            "world",
            "world is a World or one of the closed set live | replay | simulated",
            given=repr(value),
        )
    if resolved is World.SIMULATED:
        return policy(
            "world",
            "world = simulated is reserved-unusable; backup is not instantiated "
            "for it (DEC-0110, DEC-0198)",
            failure_id=_WORLD_ID,
            world=resolved.value,
        )
    if resolved.value not in BACKUP_WORLDS:
        return invalid("world", "backup worlds are live | replay", given=resolved.value)
    return Ok(resolved)


def _as_backup_role(value: object, *, cited: object) -> Result[str]:
    token = clean_token(value)
    if token in BACKED_UP_ROOM_ROLES:
        return Ok(token)
    if token in EXCLUDED_UNLESS_CITED_ROLES:
        if cited is True:
            return Ok(token)
        return refuse_processed_room(room_role=token, cited=cited)
    return invalid(
        "room_role",
        "backup copies immutable raw archive, journals, registry, sealed-archive, "
        "and the research door; processed is excluded unless cited",
        given=repr(value),
        allowed=sorted(BACKED_UP_ROOM_ROLES),
    )


def _as_nonneg_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, f"{field} is a non-negative int64", given=repr(value))
    return Ok(value)


def _segment(value: object, *, field: str) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(field, f"{field} is a non-empty path segment", given=repr(value))
    if token in {".", ".."} or "/" in token or "\\" in token or ":" in token:
        return policy(field, f"{field} is a single confined path segment", given=token)
    return Ok(token)


def _contained_dir(root: Path, path: Path) -> Result[Path]:
    try:
        resolved_root = root.resolve()
        resolved = path.resolve()
    except OSError:
        return storage("path", "backup staging path could not be resolved", failure_id=_RCLONE_ID)
    if path.is_symlink() or resolved.is_symlink():
        return policy("path", "refusing to follow a symlink in backup staging")
    if not resolved.is_relative_to(resolved_root):
        return policy("path", "backup path escaped the staging root")
    return Ok(path)


def _contained_file(root: Path, path: Path) -> Result[Path]:
    contained = _contained_dir(root, path.parent)
    if is_refusal(contained):
        return contained
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink in backup staging")
    try:
        resolved_root = root.resolve()
        resolved = path.resolve()
    except OSError:
        return storage("path", "backup object path could not be resolved", failure_id=_RCLONE_ID)
    if not resolved.is_relative_to(resolved_root):
        return policy("path", "backup object escaped the staging root")
    return Ok(path)


def _ensure_dir(path: Path) -> Result[None]:
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink at backup staging")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return storage(
            "path",
            "backup staging directory could not be created",
            failure_id=_RCLONE_ID,
        )
    return Ok(None)


def _atomic_write(path: Path, payload: bytes) -> Result[None]:
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink at the backup dest")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return storage("path", "backup directory could not be created", failure_id=_RCLONE_ID)
    tmp = path.parent / f".{path.name}.tmp-{os.getpid()}"
    if tmp.is_symlink():
        return policy("path", "refusing to follow a symlink at the backup temp")
    flags = (
        os.O_CREAT
        | os.O_EXCL
        | os.O_WRONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        fd = os.open(tmp, flags, 0o600)  # skylos: ignore[SKY-D215] contained backup stage
    except OSError:
        return storage("path", "backup staging rejected the new object", failure_id=_RCLONE_ID)
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            offset += os.write(fd, view[offset:])
    except OSError:
        os.close(fd)
        tmp.unlink(missing_ok=True)
        return storage("path", "backup staging rejected the new object", failure_id=_RCLONE_ID)
    os.close(fd)
    try:
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        return storage("path", "backup staging rejected the new object", failure_id=_RCLONE_ID)
    return Ok(None)


def _iter_files(root: Path) -> tuple[Path, ...]:
    if root.is_file():
        return (root,)
    if not root.is_dir():
        return ()
    found = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    return tuple(sorted(found))


def _copy_endpoints(argv: Sequence[str]) -> tuple[str, str]:
    copy_at = list(argv).index("copy")
    positional = [part for part in argv[copy_at + 1 :] if not part.startswith("-")]
    return positional[0], positional[1]


def _public_argv(argv: Sequence[str]) -> list[str]:
    return [part for part in argv if part.lower() not in _FORBIDDEN_RCLONE_FLAGS]


def _refuse_if_leaked(*bodies: Mapping[str, object]) -> Result[None]:
    allowed = _MANIFEST_KEYS | _RECEIPT_KEYS
    for body in bodies:
        for key, value in body.items():
            if key not in allowed and key in _FORBIDDEN_EVIDENCE_KEYS:
                return refuse_secret_in_evidence(field=key)
            blob = f"{key}={value}".lower()
            compact = blob.replace("_", "").replace("-", "")
            for token in _SECRET_TOKENS:
                if token in compact:
                    return refuse_secret_in_evidence(field=key)
            if isinstance(value, (bytes, bytearray)):
                return refuse_secret_in_evidence(field=key)
    return Ok(None)


if __name__ == "__main__":
    sys.exit(main())
