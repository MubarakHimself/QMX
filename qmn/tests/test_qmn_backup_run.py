"""Story 27.6 — encrypted rclone push through the ruled contract."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal
from qmn.data import (
    BACKED_UP_ROOM_ROLES,
    BACKUP_PAYLOAD_KEY_SLOT,
    BACKUP_PUSH_SURFACE,
    EXCLUDED_UNLESS_CITED_ROLES,
    LOCAL_TEST_BACKEND,
    PAYLOAD_KEY_SIZE,
    RCLONE_BINARY,
    RCLONE_REMOTE_NAME,
    BackupCommittedPrefix,
    BackupCopyPurgeCandidate,
    LocalFilesystemRcloneRunner,
    RecordingBackupJournal,
    RecordingRcloneRunner,
    apply_backup_retention,
    generate_test_payload_key,
    push_committed_prefixes,
    refuse_live_b2_without_soak,
    refuse_processed_room,
    refuse_secret_in_evidence,
    refuse_uncommitted_backup_prefix,
    try_bind_payload_cipher,
    validate_rclone_argv,
)
from qmn.data.backup_run import main as backup_main
from qmn.secrets.holders import BACKUP_UNIT

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_NS_HOUR = 3_600 * 1_000_000_000
_RPO_NS = 24 * _NS_HOUR
_BANNED_INFRA = frozenset({"boto3", "b2sdk", "keyring"})
_BANNED_TRADE = frozenset(
    {"qmn.order", "qmn.venue", "qmn.host", "qmn.doors", "qmn.seats"}
)
_TRADE_TOKENS = (
    "place_order",
    "cancel_order",
    "close_position",
    "close_all",
    "amend_protection",
    "flatten",
    "promote",
    "activate",
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


class _Nonces:
    def __init__(self) -> None:
        self.n = 0

    def __call__(self, size: int) -> bytes:
        self.n += 1
        return self.n.to_bytes(size, "big")


def _cipher():
    key = _ok(generate_test_payload_key(backend=LOCAL_TEST_BACKEND))
    assert len(key) == PAYLOAD_KEY_SIZE
    return _ok(
        try_bind_payload_cipher(
            holder=BACKUP_UNIT,
            slot=BACKUP_PAYLOAD_KEY_SLOT,
            key_material=key,
            minted_on="workstation",
            nonce_source=_Nonces(),
        )
    ), key


def _prefix(
    *,
    prefix_id: str = "journal-100",
    payload: bytes = b"committed-journal-prefix-bytes",
    start: int = 0,
    end: int = 100,
    world: World = World.LIVE,
    room_role: str = "journal",
    committed: bool = True,
    cited: bool = False,
) -> Result[BackupCommittedPrefix]:
    return BackupCommittedPrefix.try_create(
        world=world,
        room_role=room_role,
        prefix_id=prefix_id,
        start=start,
        end=end,
        payload=payload,
        committed=committed,
        cited=cited,
    )


def _push(
    tmp_path: Path,
    prefixes: tuple[BackupCommittedPrefix, ...],
    *,
    fail: bool = False,
    backend: str = LOCAL_TEST_BACKEND,
    soak_local: bool = False,
    has_account: bool = False,
):
    cipher, key = _cipher()
    staging = tmp_path / "staging"
    remote = tmp_path / "remote"
    inner = LocalFilesystemRcloneRunner(remote, fail=fail)
    runner = RecordingRcloneRunner(inner, fail=fail)
    result = push_committed_prefixes(
        prefixes,
        cipher=cipher,
        staging=staging,
        remote_root=remote,
        runner=runner,
        backend=backend,
        soak_local=soak_local,
        has_account=has_account,
    )
    return result, cipher, key, staging, remote, runner


def _named_set() -> tuple[BackupCommittedPrefix, ...]:
    rooms = (
        ("immutable raw archive", "raw-1", b"raw-archive-prefix"),
        ("journal", "journal-1", b"journal-prefix-bytes"),
        ("registry room", "registry-1", b"registry-prefix-bytes"),
        ("sealed-archive", "sealed-1", b"sealed-archive-prefix"),
        ("split-governed research door", "research-1", b"research-door-prefix"),
    )
    out: list[BackupCommittedPrefix] = []
    for index, (role, ident, payload) in enumerate(rooms, start=1):
        out.append(
            _ok(
                _prefix(
                    prefix_id=ident,
                    payload=payload,
                    start=0,
                    end=index * 10,
                    room_role=role,
                )
            )
        )
        out.append(
            _ok(
                _prefix(
                    prefix_id=f"{ident}-replay",
                    payload=payload + b"-replay",
                    start=0,
                    end=index * 10,
                    room_role=role,
                    world=World.REPLAY,
                )
            )
        )
    return tuple(out)


def test_named_room_set_excludes_processed_by_default() -> None:
    assert {
        "immutable raw archive",
        "journal",
        "registry room",
        "sealed-archive",
        "split-governed research door",
    } == BACKED_UP_ROOM_ROLES
    assert {"processed"} == EXCLUDED_UNLESS_CITED_ROLES
    assert BACKUP_PUSH_SURFACE == "qmn.data.backup_run"
    processed = _refusal(_prefix(room_role="processed", prefix_id="proc-1"))
    assert processed.context["failure_id"] == "data.backup.processed_excluded"
    cited = _ok(_prefix(room_role="processed", prefix_id="proc-cited", cited=True))
    assert cited.room_role == "processed"
    explicit = _refusal(refuse_processed_room(room_role="processed"))
    assert explicit.context["failure_id"] == "data.backup.processed_excluded"


def test_uncommitted_prefix_is_refused() -> None:
    refused = _refusal(_prefix(committed=False))
    assert refused.context["failure_id"] == "data.backup.uncommitted"
    explicit = _refusal(refuse_uncommitted_backup_prefix(prefix_id="open-seg"))
    assert explicit.context["failure_id"] == "data.backup.uncommitted"
    simulated = _refusal(_prefix(world=World.SIMULATED, prefix_id="sim-1"))
    assert simulated.context["failure_id"] == "data.backup.world"


def test_local_backend_pushes_encrypted_versioned_ciphertext(
    tmp_path: Path,
) -> None:
    prefixes = _named_set()
    result, cipher, _key, staging, remote, runner = _push(tmp_path, prefixes)
    report = _ok(result)
    assert report.backend == LOCAL_TEST_BACKEND
    assert report.soak_local is False
    assert len(report.receipts) == len(prefixes)
    assert runner.calls
    argv = report.rclone_argv
    assert argv[0] == RCLONE_BINARY
    assert "--checksum" in argv
    assert "--ignore-existing" in argv
    assert f"{RCLONE_REMOTE_NAME}:objects" in argv
    _ok(validate_rclone_argv(argv))
    for receipt in report.receipts:
        manifest = dict(receipt.manifest)
        assert manifest["encryption_required"] is True
        assert manifest["committed"] is True
        assert "payload" not in manifest
        assert "plaintext" not in manifest
        staged = staging / "objects" / receipt.object_key
        remote_obj = remote / "objects" / receipt.object_key
        assert staged.is_file()
        assert remote_obj.is_file()
        ciphertext = remote_obj.read_bytes()
        assert ciphertext != prefixes[0].payload
        assert b"committed-journal-prefix-bytes" not in ciphertext
        plaintext = _ok(cipher.decrypt(ciphertext))
        assert plaintext in {item.payload for item in prefixes}
        man_path = remote_obj.with_name(remote_obj.name.replace(".enc", ".manifest.json"))
        if not man_path.is_file():
            man_path = remote_obj.with_suffix(".manifest.json")
        assert man_path.is_file()
        text = man_path.read_text(encoding="utf-8").lower()
        assert "password" not in text
        assert "credential" not in text
        assert "applicationkey" not in text


def test_credentials_and_plaintext_never_enter_manifest_or_argv() -> None:
    leaked = _refusal(refuse_secret_in_evidence(field="manifest"))
    assert leaked.context["failure_id"] == "data.backup.secret_in_evidence"
    bad = (
        RCLONE_BINARY,
        "copy",
        "--b2-account",
        "akid",
        "src",
        f"{RCLONE_REMOTE_NAME}:objects",
    )
    refused = _refusal(validate_rclone_argv(bad))
    assert refused.context["failure_id"] == "data.backup.secret_in_evidence"
    trade = (
        RCLONE_BINARY,
        "copy",
        "src",
        f"{RCLONE_REMOTE_NAME}:objects",
        "place_order",
    )
    power = _refusal(validate_rclone_argv(trade))
    assert power.context["failure_id"] == "data.backup.trading_power"


def test_push_is_idempotent_on_retry(tmp_path: Path) -> None:
    prefix = _ok(_prefix())
    first, cipher, _key, staging, remote, _runner = _push(tmp_path, (prefix,))
    report = _ok(first)
    version = report.receipts[0].copy_version
    digest = report.receipts[0].payload_fingerprint
    remote_obj = remote / "objects" / report.receipts[0].object_key
    first_bytes = remote_obj.read_bytes()
    inner = LocalFilesystemRcloneRunner(remote)
    runner = RecordingRcloneRunner(inner)
    retry = _ok(
        push_committed_prefixes(
            (prefix,),
            cipher=cipher,
            staging=staging,
            remote_root=remote,
            runner=runner,
            backend=LOCAL_TEST_BACKEND,
        )
    )
    assert retry.receipts[0].copy_version == version
    assert retry.receipts[0].payload_fingerprint == digest
    assert retry.receipts[0].resumed is True
    assert remote_obj.read_bytes() == first_bytes
    assert runner.calls


def test_rclone_failure_is_storage_failure_not_completion(tmp_path: Path) -> None:
    prefix = _ok(_prefix())
    result, _cipher, _key, _staging, _remote, _runner = _push(
        tmp_path, (prefix,), fail=True
    )
    refused = _refusal(result)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert refused.context["failure_id"] == "data.backup.rclone_transfer"


def test_retention_uses_declared_law_not_provider_default() -> None:
    journal = RecordingBackupJournal()
    allowed = _ok(
        apply_backup_retention(
            _ok(
                BackupCopyPurgeCandidate.try_create(
                    copy_id="copy-1",
                    copy_version=1,
                    created_at_ns=0,
                    now_ns=40 * _RPO_NS,
                    retention_period_ns=30 * _RPO_NS,
                    retention_source="declared",
                    verified=True,
                    sealed_verified_remaining=True,
                    other_off_host_verified_remaining=True,
                )
            ),
            journal=journal,
        )
    )
    assert allowed.allowed is True
    provider = _refusal(
        apply_backup_retention(
            _ok(
                BackupCopyPurgeCandidate.try_create(
                    copy_id="copy-2",
                    copy_version=1,
                    created_at_ns=0,
                    now_ns=40 * _RPO_NS,
                    retention_period_ns=30 * _RPO_NS,
                    retention_source="provider-default",
                    verified=True,
                    sealed_verified_remaining=True,
                    other_off_host_verified_remaining=True,
                )
            ),
            journal=journal,
        )
    )
    assert provider.context["failure_id"] == "data.backup.provider_default_retention"


def test_live_b2_is_soak_local_and_missing_accounts_do_not_block_local(
    tmp_path: Path,
) -> None:
    live = _refusal(refuse_live_b2_without_soak(backend="backblaze-b2"))
    assert live.context["failure_id"] == "data.backup.backblaze_tonight"
    assert live.context["live_bucket_tonight"] is False
    soak = _refusal(
        refuse_live_b2_without_soak(
            backend="backblaze-b2", soak_local=True, has_account=False
        )
    )
    assert soak.context["failure_id"] == "data.backup.missing_bucket_account"
    ceremony = _refusal(generate_test_payload_key(backend="backblaze-b2"))
    assert ceremony.context["failure_id"] == "data.backup.ceremony_tonight"
    prefix = _ok(_prefix())
    blocked = _refusal(
        _push(tmp_path, (prefix,), backend="backblaze-b2")[0]
    )
    assert blocked.context["failure_id"] == "data.backup.backblaze_tonight"
    local = _ok(_push(tmp_path / "local", (prefix,))[0])
    assert local.backend == LOCAL_TEST_BACKEND
    assert backup_main([]) == 1
    assert backup_main(["--backend", "backblaze-b2"]) == 1


def test_systemd_unit_invokes_backup_run_without_trading_power() -> None:
    unit = (
        _QMN_ROOT / "deploy" / "systemd" / "templates" / "qmn-backup.service.in"
    ).read_text(encoding="utf-8")
    assert "python -m qmn.data.backup_run" in unit
    assert "LoadCredentialEncrypted=backup-payload-key" in unit
    assert "LoadCredentialEncrypted=object-storage" in unit
    assert "venue-client-id" not in unit
    assert "venue-refresh-token" not in unit
    lowered = unit.lower()
    for token in _TRADE_TOKENS:
        assert token not in lowered
    timer = (_QMN_ROOT / "deploy" / "systemd" / "templates" / "qmn-backup.timer").read_text(
        encoding="utf-8"
    )
    assert "qmn-backup.service" in timer
    assert "OnCalendar=" in timer


def test_backup_run_module_imports_no_live_sdk_or_trading_surface() -> None:
    path = _SRC / "data" / "backup_run.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
            imported.add(node.module)
    assert imported.isdisjoint(_BANNED_INFRA)
    for name in imported:
        assert name not in _BANNED_TRADE
        assert not any(name == banned or name.startswith(f"{banned}.") for banned in _BANNED_TRADE)
    source = path.read_text(encoding="utf-8")
    for token in _TRADE_TOKENS:
        assert f'"{token}"' in source or f"'{token}'" in source
    assert "subprocess" in imported


def _walk_strings(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        for key, item in mapping.items():
            found.append(str(key))
            found.extend(_walk_strings(item))
    elif isinstance(value, (list, tuple)):
        sequence = cast("tuple[object, ...] | list[object]", value)
        for item in sequence:
            found.extend(_walk_strings(item))
    return found


def test_receipt_mapping_has_no_secret_or_plaintext_fields(tmp_path: Path) -> None:
    prefix = _ok(_prefix(payload=b"unique-plaintext-marker-27-6"))
    report = _ok(_push(tmp_path, (prefix,))[0])
    blob = " ".join(_walk_strings(report.as_mapping())).lower()
    assert "unique-plaintext-marker-27-6" not in blob
    assert "password" not in blob
    assert "applicationkey" not in blob
    assert "backup-payload-key" not in blob
