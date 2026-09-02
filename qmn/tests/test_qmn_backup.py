"""Story 27.5 — backup numerics, crypto, cadence, and custody contract."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.core.secret import SecretRef, SecretValue
from qmn.config import compile_node_config, config_init, rows_by_name
from qmn.data import (
    BACKUP_CONFIG_ROW_NAMES,
    BACKUP_PAYLOAD_KEY_SLOT,
    CREDENTIAL_MANAGER_ESCROW,
    CRYPTO_ALGORITHM,
    CRYPTO_DEPENDENCY,
    CRYPTO_VERSION,
    LIVE_BUCKET_TONIGHT,
    NIGHTLY_CADENCE,
    PAYLOAD_KEY_CEREMONY_TONIGHT,
    PAYLOAD_KEY_CUSTODY_RULE,
    PAYLOAD_KEY_SIZE,
    BackupCopyPurgeCandidate,
    DrillMeasurement,
    RecordingBackupJournal,
    compile_backup_config,
    derive_rpo_from_schedule,
    evaluate_backup_copy_purge,
    refuse_destructive_restore_fallback,
    refuse_live_bucket_tonight,
    refuse_payload_key_ceremony,
    refuse_provider_default_retention,
    refuse_venue_shared_custody,
    refuse_vps_minted_payload_key,
    restore_decrypt,
    try_bind_payload_cipher,
)
from qmn.secrets.holders import BACKUP_UNIT, CONNECTION_MANAGER

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_WORKSPACE = _QMN_ROOT.parent
_NS_HOUR = 3_600 * 1_000_000_000
_RPO_NS = 24 * _NS_HOUR
_FIXTURE_KEY = bytes(range(PAYLOAD_KEY_SIZE))
_OTHER_KEY = bytes(reversed(range(PAYLOAD_KEY_SIZE)))
_BANNED_INFRA = frozenset({"rclone", "boto3", "b2sdk", "keyring"})


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "backup-cite", "label": label}))


def _entry(
    value: object,
    *,
    status: str = "provisional-evidence",
    evidence: Fingerprint | None = None,
) -> dict[str, object]:
    body: dict[str, object] = {"value": value, "value_status": status}
    if status != "blank":
        body["evidence_fp1"] = evidence if evidence is not None else _fp("default")
    return body


def _filled_layers(
    *,
    rpo_fp: Fingerprint | None = None,
    integrity_fp: Fingerprint | None = None,
    full_fp: Fingerprint | None = None,
    integrity_ns: int = 90 * 1_000_000_000,
    full_ns: int = 48 * _NS_HOUR,
    retention_ns: int = 30 * _RPO_NS,
    verify_ns: int = 30 * _RPO_NS,
    provider: str = "local-test",
) -> dict[str, dict[str, object]]:
    return {
        "backup_recovery_point_objective": _entry(
            _RPO_NS, evidence=rpo_fp or _fp("nightly-schedule")
        ),
        "backup_recovery_time_objective_integrity": _entry(
            integrity_ns, evidence=integrity_fp or _fp("integrity-drill")
        ),
        "backup_recovery_time_objective_full_dr": _entry(
            full_ns, evidence=full_fp or _fp("full-dr-drill")
        ),
        "backup_retention_period": _entry(retention_ns, evidence=_fp("retention")),
        "restore_verification_cadence": _entry(verify_ns, evidence=_fp("verify-cadence")),
        "backup_object_storage_provider": _entry(provider, evidence=_fp("provider")),
        "backup_payload_key_custody": _entry(
            PAYLOAD_KEY_CUSTODY_RULE, evidence=_fp("custody")
        ),
    }


def _node_config(layers: Mapping[str, dict[str, object]] | None = None):
    return _ok(compile_node_config(node_defaults=dict(layers or _filled_layers())))


def _integrity(*, ns: int, evidence: Fingerprint) -> DrillMeasurement:
    return _ok(
        DrillMeasurement.try_create(
            kind="integrity",
            drill="qmn-restore-full.timer",
            measured_ns=ns,
            evidence_fp1=evidence,
        )
    )


def _full_dr(*, ns: int, evidence: Fingerprint) -> DrillMeasurement:
    return _ok(
        DrillMeasurement.try_create(
            kind="full_dr",
            drill="restore_drill_run",
            measured_ns=ns,
            evidence_fp1=evidence,
        )
    )


class _Nonces:
    def __init__(self) -> None:
        self.n = 0

    def __call__(self, size: int) -> bytes:
        self.n += 1
        return self.n.to_bytes(size, "big")


def _candidate(
    *,
    now_ns: int = 40 * _RPO_NS,
    created_at_ns: int = 0,
    retention_ns: int = 30 * _RPO_NS,
    retention_source: str = "declared",
    verified: bool = True,
    sealed_remaining: bool = True,
    other_off_host: bool = True,
) -> BackupCopyPurgeCandidate:
    return _ok(
        BackupCopyPurgeCandidate.try_create(
            copy_id="copy-1",
            copy_version=1,
            created_at_ns=created_at_ns,
            now_ns=now_ns,
            retention_period_ns=retention_ns,
            retention_source=retention_source,
            verified=verified,
            sealed_verified_remaining=sealed_remaining,
            other_off_host_verified_remaining=other_off_host,
        )
    )


def test_seven_governed_rows_are_distinct_unit_kinded_and_soak_blocking() -> None:
    catalog = rows_by_name()
    assert len(BACKUP_CONFIG_ROW_NAMES) == 7
    assert len(set(BACKUP_CONFIG_ROW_NAMES)) == 7
    expected_units = {
        "backup_recovery_point_objective": "duration",
        "backup_recovery_time_objective_integrity": "duration",
        "backup_recovery_time_objective_full_dr": "duration",
        "backup_retention_period": "duration",
        "restore_verification_cadence": "duration",
        "backup_object_storage_provider": "string",
        "backup_payload_key_custody": "string",
    }
    for name in BACKUP_CONFIG_ROW_NAMES:
        row = catalog[name]
        assert row["units"] == expected_units[name]
        assert "blocks-soak" in row["blank_effect"]
        assert row["configurable"] is True
        assert row["owner_scope"] == "node-and-ops"


def test_blank_backup_config_derives_rpo_and_blocks_soak() -> None:
    artifact = _ok(config_init())
    compiled = _ok(compile_backup_config(artifact))
    assert compiled.cadence == NIGHTLY_CADENCE
    assert compiled.derived_rpo_ns == _RPO_NS
    assert compiled.integrity_rto_ns is None
    assert compiled.full_dr_rto_ns is None
    assert compiled.soak_blocked is True
    assert compiled.payload_key_custody is None
    assert compiled.crypto_dependency == CRYPTO_DEPENDENCY
    assert compiled.crypto_version == CRYPTO_VERSION
    assert compiled.crypto_algorithm == CRYPTO_ALGORITHM
    assert compiled.credential_manager_escrow == CREDENTIAL_MANAGER_ESCROW
    assert compiled.offline_escrow_copies == 1
    assert PAYLOAD_KEY_CEREMONY_TONIGHT is False
    assert LIVE_BUCKET_TONIGHT is False


def test_rpo_is_derived_from_nightly_schedule_not_declared() -> None:
    derived = _ok(derive_rpo_from_schedule("nightly"))
    assert derived == _RPO_NS
    refused = _refusal(derive_rpo_from_schedule("hourly"))
    assert refused.context["failure_id"] == "data.backup.rpo_not_derived"

    layers = _filled_layers()
    layers["backup_recovery_point_objective"] = _entry(
        12 * _NS_HOUR, evidence=_fp("wrong-rpo")
    )
    mismatch = _refusal(compile_backup_config(_node_config(layers)))
    assert mismatch.context["failure_id"] == "data.backup.rpo_not_derived"


def test_rtos_come_from_distinct_drills_with_evidence() -> None:
    integrity_fp = _fp("integrity-drill")
    full_fp = _fp("full-dr-drill")
    integrity_ns = 120 * 1_000_000_000
    full_ns = 72 * _NS_HOUR
    layers = _filled_layers(
        integrity_fp=integrity_fp,
        full_fp=full_fp,
        integrity_ns=integrity_ns,
        full_ns=full_ns,
    )
    compiled = _ok(
        compile_backup_config(
            _node_config(layers),
            integrity_drill=_integrity(ns=integrity_ns, evidence=integrity_fp),
            full_dr_drill=_full_dr(ns=full_ns, evidence=full_fp),
        )
    )
    assert compiled.derived_rpo_ns == _RPO_NS
    assert compiled.integrity_rto_ns == integrity_ns
    assert compiled.full_dr_rto_ns == full_ns
    assert compiled.soak_blocked is False
    assert compiled.payload_key_custody == PAYLOAD_KEY_CUSTODY_RULE
    assert compiled.provider == "local-test"

    missing_drill = _refusal(compile_backup_config(_node_config(layers)))
    assert missing_drill.context["failure_id"] == "data.backup.rto_not_from_drill"

    sample = _refusal(
        DrillMeasurement.try_create(
            kind="integrity",
            drill="qmn-restore-sample.timer",
            measured_ns=integrity_ns,
            evidence_fp1=integrity_fp,
        )
    )
    assert sample.context["failure_id"] == "data.backup.rto_not_from_drill"

    swapped = _refusal(
        compile_backup_config(
            _node_config(layers),
            integrity_drill=_full_dr(ns=full_ns, evidence=full_fp),
            full_dr_drill=_integrity(ns=integrity_ns, evidence=integrity_fp),
        )
    )
    assert swapped.context["failure_id"] == "data.backup.rto_conflated"

    same = _fp("one-drill-for-both")
    aliased = _filled_layers(
        integrity_fp=same,
        full_fp=same,
        integrity_ns=integrity_ns,
        full_ns=full_ns,
    )
    conflated = _refusal(
        compile_backup_config(
            _node_config(aliased),
            integrity_drill=_integrity(ns=integrity_ns, evidence=same),
            full_dr_drill=_full_dr(ns=full_ns, evidence=same),
        )
    )
    assert conflated.context["failure_id"] == "data.backup.rto_conflated"


def test_custody_rule_is_workstation_escrowed_not_vps() -> None:
    integrity_fp = _fp("integrity-drill")
    full_fp = _fp("full-dr-drill")
    layers = _filled_layers(integrity_fp=integrity_fp, full_fp=full_fp)
    layers["backup_payload_key_custody"] = _entry("vps-minted", evidence=_fp("bad"))
    refused = _refusal(
        compile_backup_config(
            _node_config(layers),
            integrity_drill=_integrity(ns=90 * 1_000_000_000, evidence=integrity_fp),
            full_dr_drill=_full_dr(ns=48 * _NS_HOUR, evidence=full_fp),
        )
    )
    assert refused.context["failure_id"] == "data.backup.custody"
    vps = refuse_vps_minted_payload_key(minted_on="vps")
    assert vps.context["failure_id"] == "data.backup.vps_minted_key"
    shared = refuse_venue_shared_custody(
        holder=CONNECTION_MANAGER, slot="venue-refresh-token"
    )
    assert shared.context["failure_id"] == "data.backup.venue_shared_custody"
    ceremony = refuse_payload_key_ceremony(request="generate")
    assert ceremony.context["failure_id"] == "data.backup.ceremony_tonight"
    assert ceremony.context["ceremony_tonight"] is False
    bucket = refuse_live_bucket_tonight(provider="backblaze-b2")
    assert bucket.context["failure_id"] == "data.backup.backblaze_tonight"
    assert bucket.context["live_bucket_tonight"] is False


def test_payload_cipher_round_trip_and_wrong_key_refuses_without_fallback() -> None:
    cipher = _ok(
        try_bind_payload_cipher(
            holder=BACKUP_UNIT,
            slot=BACKUP_PAYLOAD_KEY_SLOT,
            key_material=_FIXTURE_KEY,
            minted_on="workstation",
            nonce_source=_Nonces(),
        )
    )
    assert CRYPTO_ALGORITHM in repr(cipher)
    assert "range(32)" not in repr(cipher)
    plaintext = b"sealed-archive-prefix-bytes"
    sealed = _ok(cipher.encrypt(plaintext))
    assert sealed != plaintext
    assert _ok(cipher.decrypt(sealed)) == plaintext

    other = _ok(
        try_bind_payload_cipher(
            holder=BACKUP_UNIT,
            slot=BACKUP_PAYLOAD_KEY_SLOT,
            key_material=_OTHER_KEY,
            minted_on="workstation",
            nonce_source=_Nonces(),
        )
    )
    wrong = _refusal(other.decrypt(sealed))
    assert wrong.category is RefusalCategory.POLICY_REJECTION
    assert wrong.context["failure_id"] == "data.backup.wrong_key"

    inplace = _refusal(
        restore_decrypt(
            cipher,
            sealed,
            source_root="/var/lib/qmx/rooms",
            replacement_root="/var/lib/qmx/rooms",
        )
    )
    assert inplace.context["failure_id"] == "data.backup.destructive_fallback"
    restored = _ok(
        restore_decrypt(
            cipher,
            sealed,
            source_root="/var/lib/qmx/rooms",
            replacement_root="/var/lib/qmx/staging/restore",
        )
    )
    assert restored == plaintext
    explicit = refuse_destructive_restore_fallback(source_root="/var/lib/qmx/rooms")
    assert explicit.context["failure_id"] == "data.backup.destructive_fallback"


def test_bind_refuses_vps_mint_venue_share_missing_key_and_ceremony() -> None:
    vps = _refusal(
        try_bind_payload_cipher(
            holder=BACKUP_UNIT,
            slot=BACKUP_PAYLOAD_KEY_SLOT,
            key_material=_FIXTURE_KEY,
            minted_on="vps",
        )
    )
    assert vps.context["failure_id"] == "data.backup.vps_minted_key"

    venue = _refusal(
        try_bind_payload_cipher(
            holder=CONNECTION_MANAGER,
            slot="venue-refresh-token",
            key_material=_FIXTURE_KEY,
            minted_on="workstation",
        )
    )
    assert venue.context["failure_id"] == "data.backup.venue_shared_custody"

    missing = _refusal(
        try_bind_payload_cipher(
            holder=BACKUP_UNIT,
            slot=BACKUP_PAYLOAD_KEY_SLOT,
            key_material=None,
            minted_on="workstation",
        )
    )
    assert missing.context["failure_id"] == "data.backup.missing_key"

    ceremony = _refusal(
        try_bind_payload_cipher(
            holder=BACKUP_UNIT,
            slot=BACKUP_PAYLOAD_KEY_SLOT,
            key_material=_FIXTURE_KEY,
            minted_on="workstation",
            ceremony=True,
        )
    )
    assert ceremony.context["failure_id"] == "data.backup.ceremony_tonight"

    ref = _ok(SecretRef.try_create("cred-ref-backupk"))
    secret = _ok(SecretValue.try_create(ref, "fixture-not-used"))
    leaked = _refusal(
        try_bind_payload_cipher(
            holder=BACKUP_UNIT,
            slot=BACKUP_PAYLOAD_KEY_SLOT,
            key_material=secret,
            minted_on="workstation",
        )
    )
    assert leaked.context["failure_id"] == "data.backup.missing_key"


def test_backup_copy_purge_checks_retention_verification_two_copy_and_journals() -> None:
    journal = RecordingBackupJournal()
    allowed = _ok(evaluate_backup_copy_purge(_candidate(), journal=journal))
    assert allowed.allowed is True
    assert allowed.journaled is True
    assert journal.records[-1]["allowed"] is True
    assert journal.records[-1]["retention_source_declared"] is True

    provider = _refusal(
        evaluate_backup_copy_purge(
            _candidate(retention_source="provider-default"),
            journal=journal,
        )
    )
    assert provider.context["failure_id"] == "data.backup.provider_default_retention"
    assert journal.records[-1]["allowed"] is False
    explicit = refuse_provider_default_retention(provider="backblaze-b2")
    assert explicit.context["failure_id"] == "data.backup.provider_default_retention"

    early = _refusal(
        evaluate_backup_copy_purge(_candidate(now_ns=_RPO_NS), journal=journal)
    )
    assert early.context["failure_id"] == "data.backup.retention_window"

    unverified = _refusal(
        evaluate_backup_copy_purge(_candidate(verified=False), journal=journal)
    )
    assert unverified.context["failure_id"] == "data.backup.unverified_purge"

    two_copy = _refusal(
        evaluate_backup_copy_purge(
            _candidate(other_off_host=False),
            journal=journal,
        )
    )
    assert two_copy.context["failure_id"] == "data.backup.two_copy"

    sealed_missing = _refusal(
        evaluate_backup_copy_purge(
            _candidate(sealed_remaining=False),
            journal=journal,
        )
    )
    assert sealed_missing.context["failure_id"] == "data.backup.two_copy"

    failing = RecordingBackupJournal(fail_write=True)
    journal_fail = _refusal(evaluate_backup_copy_purge(_candidate(), journal=failing))
    assert journal_fail.context["failure_id"] == "data.backup.journal"


def test_crypto_pin_and_payload_cipher_are_declared() -> None:
    pyproject = (_QMN_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "cryptography==50.0.1" in pyproject
    deps = (_WORKSPACE / "DEPENDENCIES.md").read_text(encoding="utf-8")
    assert "`==50.0.1`" in deps
    assert "cryptography" in deps
    assert "ChaCha20Poly1305" in deps
    assert "payload cipher" in deps.lower() or "PayloadCipher" in deps


def test_backup_module_does_not_stand_up_live_infra_or_ceremony() -> None:
    path = _SRC / "data" / "backup.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint(_BANNED_INFRA)
    assert "os" in imported
    assert PAYLOAD_KEY_CEREMONY_TONIGHT is False
    assert LIVE_BUCKET_TONIGHT is False
    compiled = _ok(
        compile_backup_config(
            _node_config(_filled_layers(provider="backblaze-b2")),
            integrity_drill=_integrity(ns=90 * 1_000_000_000, evidence=_fp("integrity-drill")),
            full_dr_drill=_full_dr(ns=48 * _NS_HOUR, evidence=_fp("full-dr-drill")),
        )
    )
    assert compiled.provider == "backblaze-b2"
    live = refuse_live_bucket_tonight(provider=compiled.provider)
    assert live.context["live_bucket_tonight"] is False
    assert live.context["failure_id"] == "data.backup.backblaze_tonight"
