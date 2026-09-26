"""Backup numerics, payload-key custody, and copy-retention contract (Story 27.5).

Governed configuration compiles the distinct RPO / integrity-RTO / full-DR-RTO /
retention / verification-cadence / provider / custody rows. RPO is derived from
the actual schedule; the two RTOs come from their drills and are never
conflated. The CT-14 payload cipher is ``cryptography`` ChaCha20Poly1305 under
the workstation-escrowed key. This story codes the contract: no real payload
key is generated, no escrow ceremony runs, and no live Backblaze bucket opens
(DEC-0197, DEC-0198, DEC-0217, DEC-0252).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Protocol, cast

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from qmf.core import Duration, Fingerprint, Ok, Result, TypedRefusal, is_refusal
from qmf.core.secret import SecretValue

from qmn.config.compiler import ResolvedNodeConfig, ResolvedValueRow
from qmn.config.registry_catalog import BLANK_EFFECT_SOAK, rows_by_name
from qmn.data._refuse import clean_token, invalid, policy, unavailable
from qmn.secrets.holders import (
    BACKUP_UNIT,
    CONNECTION_MANAGER,
    NEVER_VPS_MINTED_SLOTS,
    VENUE_SESSION_SLOTS,
)

__all__ = [
    "BACKUP_CONFIG_ROW_NAMES",
    "BACKUP_PAYLOAD_KEY_SLOT",
    "CREDENTIAL_MANAGER_ESCROW",
    "CRYPTO_ALGORITHM",
    "CRYPTO_DEPENDENCY",
    "CRYPTO_VERSION",
    "INTEGRITY_DRILL_NAMES",
    "LIVE_BUCKET_TONIGHT",
    "NIGHTLY_CADENCE",
    "PAYLOAD_KEY_CEREMONY_TONIGHT",
    "PAYLOAD_KEY_CUSTODY_RULE",
    "PAYLOAD_KEY_SIZE",
    "BackupConfig",
    "BackupCopyPurgeCandidate",
    "BackupPayloadCipher",
    "BackupPurgeDecision",
    "DrillMeasurement",
    "RecordingBackupJournal",
    "compile_backup_config",
    "derive_rpo_from_schedule",
    "evaluate_backup_copy_purge",
    "os_payload_nonce",
    "refuse_destructive_restore_fallback",
    "refuse_live_bucket_tonight",
    "refuse_payload_key_ceremony",
    "refuse_provider_default_retention",
    "refuse_venue_shared_custody",
    "refuse_vps_minted_payload_key",
    "restore_decrypt",
    "try_bind_payload_cipher",
]


BACKUP_CONFIG_ROW_NAMES: Final[tuple[str, ...]] = (
    "backup_recovery_point_objective",
    "backup_recovery_time_objective_integrity",
    "backup_recovery_time_objective_full_dr",
    "backup_retention_period",
    "restore_verification_cadence",
    "backup_object_storage_provider",
    "backup_payload_key_custody",
)

NIGHTLY_CADENCE: Final[str] = "nightly"
NS_PER_HOUR: Final[int] = 3_600 * 1_000_000_000
NIGHTLY_RPO_NS: Final[int] = 24 * NS_PER_HOUR

PAYLOAD_KEY_CUSTODY_RULE: Final[str] = "workstation-escrowed"
CREDENTIAL_MANAGER_ESCROW: Final[str] = "qmx/backup-payload-key"
BACKUP_PAYLOAD_KEY_SLOT: Final[str] = "backup-payload-key"
PAYLOAD_KEY_SIZE: Final[int] = 32
AEAD_NONCE_SIZE: Final[int] = 12
_PAYLOAD_MAGIC: Final[bytes] = b"QMNB1\0"

CRYPTO_DEPENDENCY: Final[str] = "cryptography"
CRYPTO_VERSION: Final[str] = "50.0.1"
CRYPTO_ALGORITHM: Final[str] = "ChaCha20Poly1305"

PAYLOAD_KEY_CEREMONY_TONIGHT: Final[bool] = False
LIVE_BUCKET_TONIGHT: Final[bool] = False

INTEGRITY_DRILL_NAMES: Final[frozenset[str]] = frozenset(
    {"qmn-restore-full.timer", "monthly-full-restore"}
)
FULL_DR_DRILL_NAMES: Final[frozenset[str]] = frozenset({"restore_drill_run", "host-loss-rehearsal"})
SAMPLE_DRILL_NAMES: Final[frozenset[str]] = frozenset(
    {"qmn-restore-sample.timer", "nightly-sample-restore"}
)
LIVE_BUCKET_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "backblaze",
        "backblaze-b2",
        "b2",
        "rclone",
        "wasabi",
        "r2",
        "cloudflare-r2",
    }
)

_BLANK_ID: Final[str] = "data.backup.blank_row"
_RPO_ID: Final[str] = "data.backup.rpo_not_derived"
_RTO_ID: Final[str] = "data.backup.rto_not_from_drill"
_CONFLATE_ID: Final[str] = "data.backup.rto_conflated"
_CUSTODY_ID: Final[str] = "data.backup.custody"
_VPS_MINT_ID: Final[str] = "data.backup.vps_minted_key"
_VENUE_SHARE_ID: Final[str] = "data.backup.venue_shared_custody"
_MISSING_KEY_ID: Final[str] = "data.backup.missing_key"
_WRONG_KEY_ID: Final[str] = "data.backup.wrong_key"
_DESTRUCTIVE_ID: Final[str] = "data.backup.destructive_fallback"
_PROVIDER_DEFAULT_ID: Final[str] = "data.backup.provider_default_retention"
_UNVERIFIED_ID: Final[str] = "data.backup.unverified_purge"
_TWO_COPY_ID: Final[str] = "data.backup.two_copy"
_RETENTION_ID: Final[str] = "data.backup.retention_window"
_RESTORE_PROOF_KINDS: Final[frozenset[str]] = frozenset(
    {
        "restore-verification",
        "nightly-sample-restore",
        "monthly-full-restore",
        "host-loss-rehearsal",
    }
)
_CEREMONY_ID: Final[str] = "data.backup.ceremony_tonight"
_BUCKET_ID: Final[str] = "data.backup.backblaze_tonight"
_JOURNAL_ID: Final[str] = "data.backup.journal"


class NonceSource(Protocol):
    """Injected AEAD nonce factory (entropy is not read at import)."""

    def __call__(self, size: int) -> bytes: ...


class BackupJournalSink(Protocol):
    """Append-only journal for backup retention/purge verdicts (TN-13)."""

    def append(self, record: Mapping[str, object], /) -> Result[None]: ...


def os_payload_nonce(size: int = AEAD_NONCE_SIZE) -> bytes:
    """Production nonce source, injected at the composition root."""
    return os.urandom(size)  # ambient-scan: allow — AEAD nonce for CT-14 payload cipher (TN-13)


@dataclass(frozen=True, slots=True)
class DrillMeasurement:
    """One restore-drill measurement that may fill an RTO row (DEC-0198)."""

    kind: str
    drill: str
    measured_ns: int
    evidence_fp1: Fingerprint

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": self.kind,
                "drill": self.drill,
                "measured_ns": self.measured_ns,
                "evidence_fp1": self.evidence_fp1.value,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        kind: object,
        drill: object,
        measured_ns: object,
        evidence_fp1: object,
    ) -> Result[DrillMeasurement]:
        rto_kind = clean_token(kind)
        if rto_kind not in {"integrity", "full_dr"}:
            return invalid(
                "kind",
                "an RTO drill kind is integrity | full_dr",
                given=repr(kind),
            )
        drill_name = clean_token(drill)
        if drill_name is None:
            return invalid("drill", "a drill measurement names its unit or power")
        if drill_name in SAMPLE_DRILL_NAMES:
            return policy(
                "drill",
                "the nightly sample restore does not measure either RTO (DEC-0198, DEC-0252)",
                failure_id=_RTO_ID,
                drill=drill_name,
            )
        if rto_kind == "integrity" and drill_name not in INTEGRITY_DRILL_NAMES:
            return policy(
                "drill",
                "the integrity-restore RTO is measured at the monthly full-restore "
                "rehearsal (DEC-0198)",
                failure_id=_RTO_ID,
                drill=drill_name,
                kind=rto_kind,
            )
        if rto_kind == "full_dr" and drill_name not in FULL_DR_DRILL_NAMES:
            return policy(
                "drill",
                "the full-DR RTO is measured at the host-loss rehearsal "
                "(restore_drill_run) (DEC-0198, DEC-0252)",
                failure_id=_RTO_ID,
                drill=drill_name,
                kind=rto_kind,
            )
        measured = _as_ns(measured_ns, "measured_ns")
        if is_refusal(measured):
            return measured
        if measured.value <= 0:
            return invalid(
                "measured_ns",
                "a drill measurement is a positive duration",
                given=measured.value,
            )
        parsed = _as_fingerprint(evidence_fp1)
        if is_refusal(parsed):
            return parsed
        return Ok(
            cls(
                kind=rto_kind,
                drill=drill_name,
                measured_ns=measured.value,
                evidence_fp1=parsed.value,
            )
        )


@dataclass(frozen=True, slots=True)
class BackupConfig:
    """Compiled backup numerics and custody — schema plus measured evidence."""

    cadence: str
    derived_rpo_ns: int
    integrity_rto_ns: int | None
    full_dr_rto_ns: int | None
    retention_period_ns: int | None
    verification_cadence_ns: int | None
    provider: str | None
    payload_key_custody: str | None
    rows: Mapping[str, ResolvedValueRow]
    soak_blocked: bool
    crypto_dependency: str = CRYPTO_DEPENDENCY
    crypto_version: str = CRYPTO_VERSION
    crypto_algorithm: str = CRYPTO_ALGORITHM
    credential_manager_escrow: str = CREDENTIAL_MANAGER_ESCROW
    offline_escrow_copies: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", MappingProxyType(dict(self.rows)))

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "cadence": self.cadence,
                "derived_rpo_ns": self.derived_rpo_ns,
                "integrity_rto_ns": self.integrity_rto_ns,
                "full_dr_rto_ns": self.full_dr_rto_ns,
                "retention_period_ns": self.retention_period_ns,
                "verification_cadence_ns": self.verification_cadence_ns,
                "provider": self.provider,
                "payload_key_custody": self.payload_key_custody,
                "soak_blocked": self.soak_blocked,
                "crypto_dependency": self.crypto_dependency,
                "crypto_version": self.crypto_version,
                "crypto_algorithm": self.crypto_algorithm,
                "credential_manager_escrow": self.credential_manager_escrow,
                "offline_escrow_copies": self.offline_escrow_copies,
                "row_names": list(BACKUP_CONFIG_ROW_NAMES),
            }
        )


class RecordingBackupJournal:
    """Test/in-process journal for backup purge verdicts."""

    def __init__(self, *, fail_write: bool = False) -> None:
        self.records: list[Mapping[str, object]] = []
        self.fail_write = fail_write

    def append(self, record: Mapping[str, object], /) -> Result[None]:
        if self.fail_write:
            return unavailable(
                "journal",
                "the backup purge journal rejected the verdict",
                failure_id=_JOURNAL_ID,
            )
        self.records.append(MappingProxyType(dict(record)))
        return Ok(None)


@dataclass(frozen=True, slots=True)
class BackupCopyPurgeCandidate:
    """One off-host backup copy asking to age out of the backup set."""

    copy_id: str
    copy_version: int
    created_at_ns: int
    now_ns: int
    retention_period_ns: int
    retention_source: str
    verified: bool
    sealed_verified_remaining: bool
    other_off_host_verified_remaining: bool
    verification_kind: str = "restore-verification"

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "copy_id": self.copy_id,
                "copy_version": self.copy_version,
                "created_at_ns": self.created_at_ns,
                "now_ns": self.now_ns,
                "retention_period_ns": self.retention_period_ns,
                "retention_source": self.retention_source,
                "verified": self.verified,
                "verification_kind": self.verification_kind,
                "sealed_verified_remaining": self.sealed_verified_remaining,
                "other_off_host_verified_remaining": self.other_off_host_verified_remaining,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        copy_id: object,
        copy_version: object,
        created_at_ns: object,
        now_ns: object,
        retention_period_ns: object,
        retention_source: object,
        verified: object,
        sealed_verified_remaining: object,
        other_off_host_verified_remaining: object,
        verification_kind: object = "restore-verification",
    ) -> Result[BackupCopyPurgeCandidate]:
        ident = clean_token(copy_id)
        if ident is None:
            return invalid("copy_id", "a backup copy names a non-empty id")
        version = _as_nonneg_int(copy_version, "copy_version")
        if is_refusal(version):
            return version
        created = _as_ns(created_at_ns, "created_at_ns")
        if is_refusal(created):
            return created
        now = _as_ns(now_ns, "now_ns")
        if is_refusal(now):
            return now
        retention = _as_ns(retention_period_ns, "retention_period_ns")
        if is_refusal(retention):
            return retention
        if retention.value <= 0:
            return invalid(
                "retention_period_ns",
                "declared backup-set retention is a positive duration",
                given=retention.value,
            )
        source = clean_token(retention_source)
        if source not in {"declared", "provider-default"}:
            return invalid(
                "retention_source",
                "retention source is declared | provider-default",
                given=repr(retention_source),
            )
        if not isinstance(verified, bool):
            return invalid("verified", "verified is a boolean", given=repr(verified))
        if not isinstance(sealed_verified_remaining, bool):
            return invalid(
                "sealed_verified_remaining",
                "sealed_verified_remaining is a boolean",
                given=repr(sealed_verified_remaining),
            )
        if not isinstance(other_off_host_verified_remaining, bool):
            return invalid(
                "other_off_host_verified_remaining",
                "other_off_host_verified_remaining is a boolean",
                given=repr(other_off_host_verified_remaining),
            )
        proof_kind = clean_token(verification_kind)
        if proof_kind is None:
            return invalid(
                "verification_kind",
                "backup-set purge names the verification kind that produced the proof",
                given=repr(verification_kind),
            )
        return Ok(
            cls(
                copy_id=ident,
                copy_version=version.value,
                created_at_ns=created.value,
                now_ns=now.value,
                retention_period_ns=retention.value,
                retention_source=source,
                verified=verified,
                sealed_verified_remaining=sealed_verified_remaining,
                other_off_host_verified_remaining=other_off_host_verified_remaining,
                verification_kind=proof_kind,
            )
        )


@dataclass(frozen=True, slots=True)
class BackupPurgeDecision:
    """Allowed only after declared retention, verification, and two-copy proof."""

    allowed: bool
    copy_id: str
    reason: str
    journaled: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "allowed": self.allowed,
                "copy_id": self.copy_id,
                "reason": self.reason,
                "journaled": self.journaled,
            }
        )


class BackupPayloadCipher:
    """CT-14 PayloadCipher over the workstation-escrowed payload key."""

    def __init__(self, key: bytes, nonce_source: NonceSource) -> None:
        self._aead = ChaCha20Poly1305(key)
        self._nonce_source = nonce_source

    def encrypt(self, plaintext: object, /) -> Result[bytes]:
        """Return AEAD ciphertext, or a typed refusal."""
        if not isinstance(plaintext, (bytes, bytearray)):
            return invalid(
                "plaintext",
                "payload cipher encrypts bytes",
                given=repr(type(plaintext).__name__),
            )
        nonce = self._nonce_source(AEAD_NONCE_SIZE)
        ciphertext = self._aead.encrypt(nonce, bytes(plaintext), _PAYLOAD_MAGIC)
        return Ok(_PAYLOAD_MAGIC + nonce + ciphertext)

    def decrypt(self, ciphertext: object, /) -> Result[bytes]:
        """Return plaintext, or refuse a missing/wrong key without fallback."""
        if not isinstance(ciphertext, (bytes, bytearray)):
            return invalid(
                "ciphertext",
                "payload cipher decrypts bytes",
                given=repr(type(ciphertext).__name__),
            )
        blob = bytes(ciphertext)
        prefix = _PAYLOAD_MAGIC
        if not blob.startswith(prefix) or len(blob) < len(prefix) + AEAD_NONCE_SIZE:
            return policy(
                "payload_key",
                "restore refused a missing or wrong payload key; the source copy "
                "is not rewritten (DEC-0217)",
                failure_id=_WRONG_KEY_ID,
            )
        nonce = blob[len(prefix) : len(prefix) + AEAD_NONCE_SIZE]
        body = blob[len(prefix) + AEAD_NONCE_SIZE :]
        try:
            return Ok(self._aead.decrypt(nonce, body, prefix))
        except (InvalidTag, ValueError):
            return policy(
                "payload_key",
                "restore refused a missing or wrong payload key; the source copy "
                "is not rewritten (DEC-0217)",
                failure_id=_WRONG_KEY_ID,
            )

    def __repr__(self) -> str:
        return (
            f"BackupPayloadCipher(algorithm={CRYPTO_ALGORITHM!r}, "
            f"dependency={CRYPTO_DEPENDENCY!r}, version={CRYPTO_VERSION!r})"
        )


def derive_rpo_from_schedule(cadence: object) -> Result[int]:
    """RPO is the schedule interval, never a declared constant (L38, DEC-0198)."""
    token = clean_token(cadence)
    if token is None:
        return invalid(
            "cadence",
            "backup cadence is the ratified nightly schedule pointer",
            given=repr(cadence),
        )
    if token != NIGHTLY_CADENCE:
        return policy(
            "cadence",
            "RPO is derived from the actual backup schedule; only the ratified "
            "nightly cadence is in V1 (DEC-0118, DEC-0198)",
            failure_id=_RPO_ID,
            cadence=token,
        )
    return Ok(NIGHTLY_RPO_NS)


def compile_backup_config(
    config: object,
    *,
    cadence: object = NIGHTLY_CADENCE,
    integrity_drill: object = None,
    full_dr_drill: object = None,
) -> Result[BackupConfig]:
    """Compile the seven governed backup rows from a resolved node-config."""
    if not isinstance(config, ResolvedNodeConfig):
        return invalid(
            "config",
            "backup configuration compiles from a ResolvedNodeConfig",
            given=repr(type(config).__name__),
        )
    schema = rows_by_name()
    rows: dict[str, ResolvedValueRow] = {}
    for name in BACKUP_CONFIG_ROW_NAMES:
        if name not in config.rows:
            return invalid(
                name,
                "backup configuration requires every governed row on the artifact",
            )
        catalog = schema.get(name)
        if catalog is None:
            return invalid(name, "backup row is missing from the registry catalog")
        row = config.rows[name]
        if catalog["units"] is None:
            return invalid(name, "backup rows are unit-kinded")
        if BLANK_EFFECT_SOAK not in row.blank_effect:
            return invalid(
                name,
                "backup rows carry a blocks-soak blank effect (DEC-0256)",
            )
        rows[name] = row
    if len(rows) != len(BACKUP_CONFIG_ROW_NAMES):
        return invalid(
            "rows",
            "backup rows are distinct; a collapsed or aliased set is refused",
        )

    derived = derive_rpo_from_schedule(cadence)
    if is_refusal(derived):
        return derived
    rpo_row = rows["backup_recovery_point_objective"]
    if not rpo_row.is_blank:
        rpo_value = _as_ns(rpo_row.value, "backup_recovery_point_objective")
        if is_refusal(rpo_value):
            return rpo_value
        if rpo_value.value != derived.value:
            return policy(
                "backup_recovery_point_objective",
                "RPO is derived from the actual nightly schedule and cannot be "
                "declared independently (DEC-0198)",
                failure_id=_RPO_ID,
                derived_ns=derived.value,
                given=rpo_value.value,
            )
        cited = _require_evidence(rpo_row)
        if is_refusal(cited):
            return cited

    integrity = _bind_rto_row(
        rows["backup_recovery_time_objective_integrity"],
        drill=integrity_drill,
        expected_kind="integrity",
    )
    if is_refusal(integrity):
        return integrity
    full_dr = _bind_rto_row(
        rows["backup_recovery_time_objective_full_dr"],
        drill=full_dr_drill,
        expected_kind="full_dr",
    )
    if is_refusal(full_dr):
        return full_dr
    if (
        integrity.value is not None
        and full_dr.value is not None
        and isinstance(integrity_drill, DrillMeasurement)
        and isinstance(full_dr_drill, DrillMeasurement)
        and integrity_drill.evidence_fp1 == full_dr_drill.evidence_fp1
    ):
        return policy(
            "rto",
            "the two RTOs are recorded apart and never conflated (DEC-0198)",
            failure_id=_CONFLATE_ID,
        )

    retention = _optional_duration(rows["backup_retention_period"])
    if is_refusal(retention):
        return retention
    cadence_ns = _optional_duration(rows["restore_verification_cadence"])
    if is_refusal(cadence_ns):
        return cadence_ns
    provider = _optional_token(rows["backup_object_storage_provider"])
    if is_refusal(provider):
        return provider
    custody = _bind_custody(rows["backup_payload_key_custody"])
    if is_refusal(custody):
        return custody

    soak_blocked = any(row.is_blank for row in rows.values())
    return Ok(
        BackupConfig(
            cadence=NIGHTLY_CADENCE,
            derived_rpo_ns=derived.value,
            integrity_rto_ns=integrity.value,
            full_dr_rto_ns=full_dr.value,
            retention_period_ns=retention.value,
            verification_cadence_ns=cadence_ns.value,
            provider=provider.value,
            payload_key_custody=custody.value,
            rows=rows,
            soak_blocked=soak_blocked,
        )
    )


def refuse_payload_key_ceremony(*, request: object = None) -> TypedRefusal:
    """No real payload key is generated tonight — the contract is coded only."""
    extra: dict[str, object] = {
        "failure_id": _CEREMONY_ID,
        "ceremony_tonight": PAYLOAD_KEY_CEREMONY_TONIGHT,
        "custody": PAYLOAD_KEY_CUSTODY_RULE,
        "escrow": CREDENTIAL_MANAGER_ESCROW,
    }
    token = clean_token(request)
    if token is not None:
        extra["request"] = token
    return policy(
        "payload_key",
        "Story 27.5 codes the payload-key custody contract; the workstation "
        "generation and escrow ceremony does not run tonight (DEC-0217)",
        **extra,
    )


def refuse_vps_minted_payload_key(*, minted_on: object) -> TypedRefusal:
    """The CT-14 payload key is never VPS-minted (DEC-0197, DEC-0217)."""
    return policy(
        "payload_key",
        "the backup payload key is workstation-generated and delivered as a "
        "bootstrap credential; the VPS-minted KEK protects rotated session "
        "material only (DEC-0197, DEC-0217)",
        failure_id=_VPS_MINT_ID,
        minted_on=repr(minted_on),
        never_vps_minted=sorted(NEVER_VPS_MINTED_SLOTS),
    )


def refuse_venue_shared_custody(*, holder: object, slot: object) -> TypedRefusal:
    """Backup payload-key custody never shares the venue-secret holder."""
    return policy(
        "payload_key",
        "the backup unit holds the payload key; it never shares venue-secret "
        "custody with the connection manager (DEC-0227, DEC-0217)",
        failure_id=_VENUE_SHARE_ID,
        holder=repr(holder),
        slot=repr(slot),
        backup_holder=BACKUP_UNIT,
        venue_holder=CONNECTION_MANAGER,
    )


def refuse_live_bucket_tonight(*, provider: object) -> TypedRefusal:
    """Real Backblaze B2 remains soak-local; factory tests use a local backend."""
    token = clean_token(provider)
    return policy(
        "provider",
        "a live Backblaze B2 bucket is soak-local acceptance; factory tests "
        "drive rclone against an isolated local backend and a generated test "
        "key (AR-87)",
        failure_id=_BUCKET_ID,
        given=token if token is not None else repr(provider),
        live_bucket_tonight=LIVE_BUCKET_TONIGHT,
        soak_local=False,
    )


def refuse_destructive_restore_fallback(*, source_root: object) -> TypedRefusal:
    """Restore never rewrites the only local copy on a missing/wrong key."""
    return policy(
        "restore",
        "a missing or wrong payload key refuses restore without a destructive "
        "fallback onto the source copy (DEC-0217, DEC-0118)",
        failure_id=_DESTRUCTIVE_ID,
        source_root=repr(source_root),
    )


def refuse_provider_default_retention(*, provider: object = None) -> TypedRefusal:
    """Backup-set retention is the declared row, never a provider lifecycle."""
    extra: dict[str, object] = {"failure_id": _PROVIDER_DEFAULT_ID}
    token = clean_token(provider)
    if token is not None:
        extra["provider"] = token
    return policy(
        "retention",
        "backup-set retention is the declared registry row; no value is "
        "inferred from a provider default (TN-13, DEC-0198)",
        **extra,
    )


def try_bind_payload_cipher(
    *,
    holder: object,
    slot: object,
    key_material: object,
    minted_on: object,
    nonce_source: NonceSource | None = None,
    ceremony: object = False,
) -> Result[BackupPayloadCipher]:
    """Bind the CT-14 cipher from backup-unit bootstrap material — never mint."""
    if ceremony is True or PAYLOAD_KEY_CEREMONY_TONIGHT:
        return refuse_payload_key_ceremony(request="ceremony")
    holder_token = clean_token(holder)
    slot_token = clean_token(slot)
    origin = clean_token(minted_on)
    if origin != "workstation":
        return refuse_vps_minted_payload_key(minted_on=minted_on)
    if holder_token == CONNECTION_MANAGER or slot_token in VENUE_SESSION_SLOTS:
        return refuse_venue_shared_custody(holder=holder, slot=slot)
    if holder_token != BACKUP_UNIT or slot_token != BACKUP_PAYLOAD_KEY_SLOT:
        return refuse_venue_shared_custody(holder=holder, slot=slot)
    if isinstance(key_material, SecretValue):
        return policy(
            "payload_key",
            "secret values never enter the backup cipher constructor as a "
            "logged value; bind raw bootstrap bytes from the backup unit "
            "(CT-21, L34)",
            failure_id=_MISSING_KEY_ID,
        )
    if key_material is None:
        return unavailable(
            "payload_key",
            "restore refused: the workstation-escrowed payload key is missing",
            failure_id=_MISSING_KEY_ID,
        )
    if not isinstance(key_material, (bytes, bytearray)):
        return invalid(
            "payload_key",
            "payload key material is 32 raw bytes",
            given=repr(type(key_material).__name__),
        )
    key = bytes(key_material)
    if len(key) != PAYLOAD_KEY_SIZE:
        return policy(
            "payload_key",
            "restore refused a missing or wrong payload key; the source copy "
            "is not rewritten (DEC-0217)",
            failure_id=_WRONG_KEY_ID,
            size=len(key),
        )
    source = nonce_source if nonce_source is not None else os_payload_nonce
    return Ok(BackupPayloadCipher(key, source))


def restore_decrypt(
    cipher: object,
    ciphertext: object,
    *,
    source_root: object,
    replacement_root: object,
) -> Result[bytes]:
    """Decrypt into a replacement root; never rewrite the source on failure."""
    if not isinstance(cipher, BackupPayloadCipher):
        return invalid(
            "cipher",
            "restore decrypts through BackupPayloadCipher",
            given=repr(type(cipher).__name__),
        )
    src = clean_token(source_root)
    dest = clean_token(replacement_root)
    if src is None or dest is None:
        return invalid(
            "restore",
            "restore names distinct source and replacement roots",
            source_root=repr(source_root),
            replacement_root=repr(replacement_root),
        )
    if src == dest:
        return refuse_destructive_restore_fallback(source_root=src)
    if not isinstance(ciphertext, (bytes, bytearray)):
        return invalid(
            "ciphertext",
            "restore decrypts ciphertext bytes",
            given=repr(type(ciphertext).__name__),
        )
    return cipher.decrypt(bytes(ciphertext))


def evaluate_backup_copy_purge(
    candidate: object,
    *,
    journal: object,
) -> Result[BackupPurgeDecision]:
    """Age-out checks declared retention, verification, and the two-copy rule."""
    if not isinstance(candidate, BackupCopyPurgeCandidate):
        return invalid(
            "candidate",
            "backup-set purge evaluates a BackupCopyPurgeCandidate",
            given=repr(type(candidate).__name__),
        )
    if not hasattr(journal, "append"):
        return invalid(
            "journal",
            "backup-set purge journals the verdict; a journal sink is required",
            given=repr(type(journal).__name__),
        )
    sink = cast("BackupJournalSink", journal)
    if candidate.retention_source == "provider-default":
        record = _purge_record(candidate, allowed=False, reason=_PROVIDER_DEFAULT_ID)
        written = sink.append(record)
        if is_refusal(written):
            return written
        return refuse_provider_default_retention()
    if candidate.now_ns - candidate.created_at_ns < candidate.retention_period_ns:
        record = _purge_record(candidate, allowed=False, reason=_RETENTION_ID)
        written = sink.append(record)
        if is_refusal(written):
            return written
        return policy(
            "retention",
            "a backup copy ages out only after the declared retention period (TN-13)",
            failure_id=_RETENTION_ID,
            copy_id=candidate.copy_id,
            elapsed_ns=candidate.now_ns - candidate.created_at_ns,
            window_ns=candidate.retention_period_ns,
        )
    if not candidate.verified or candidate.verification_kind not in _RESTORE_PROOF_KINDS:
        record = _purge_record(candidate, allowed=False, reason=_UNVERIFIED_ID)
        written = sink.append(record)
        if is_refusal(written):
            return written
        return policy(
            "verification",
            "backup-set purge requires successful restore verification; a "
            "monitoring result or provider default is not a restore proof (FR-065)",
            failure_id=_UNVERIFIED_ID,
            copy_id=candidate.copy_id,
            verification_kind=candidate.verification_kind,
        )
    if not candidate.sealed_verified_remaining or not candidate.other_off_host_verified_remaining:
        record = _purge_record(candidate, allowed=False, reason=_TWO_COPY_ID)
        written = sink.append(record)
        if is_refusal(written):
            return written
        return policy(
            "two_copy",
            "backup-set purge requires a verified sealed-archive copy and "
            "another verified off-host copy to remain (DEC-0253, DEC-0198)",
            failure_id=_TWO_COPY_ID,
            copy_id=candidate.copy_id,
            sealed_verified_remaining=candidate.sealed_verified_remaining,
            other_off_host_verified_remaining=candidate.other_off_host_verified_remaining,
        )
    record = _purge_record(
        candidate,
        allowed=True,
        reason="declared-retention-verified-two-copy",
    )
    written = sink.append(record)
    if is_refusal(written):
        return written
    return Ok(
        BackupPurgeDecision(
            allowed=True,
            copy_id=candidate.copy_id,
            reason=(
                "declared retention elapsed, verification succeeded, and the "
                "two-copy rule still holds"
            ),
            journaled=True,
        )
    )


def _purge_record(
    candidate: BackupCopyPurgeCandidate,
    *,
    allowed: bool,
    reason: str,
) -> Mapping[str, object]:
    body = dict(candidate.as_mapping())
    body["allowed"] = allowed
    body["reason"] = reason
    body["retention_source_declared"] = candidate.retention_source == "declared"
    return MappingProxyType(body)


def _bind_rto_row(
    row: ResolvedValueRow,
    *,
    drill: object,
    expected_kind: str,
) -> Result[int | None]:
    if row.is_blank:
        if drill is not None:
            return policy(
                row.name,
                "a drill measurement cannot fill a blank RTO row; the row carries "
                "the measured value plus its evidence citation (DEC-0198)",
                failure_id=_RTO_ID,
            )
        return Ok(None)
    cited = _require_evidence(row)
    if is_refusal(cited):
        return cited
    if not isinstance(drill, DrillMeasurement):
        return policy(
            row.name,
            "RTO is measured at its drill and never declared (DEC-0198, DEC-0252)",
            failure_id=_RTO_ID,
            kind=expected_kind,
        )
    if drill.kind != expected_kind:
        return policy(
            row.name,
            "the two RTOs come from their respective drills and are never "
            "swapped or conflated (DEC-0198)",
            failure_id=_CONFLATE_ID,
            kind=drill.kind,
            expected=expected_kind,
        )
    value = _as_ns(row.value, row.name)
    if is_refusal(value):
        return value
    if value.value != drill.measured_ns:
        return policy(
            row.name,
            "the RTO row must equal the drill measurement it cites (DEC-0198)",
            failure_id=_RTO_ID,
            row_ns=value.value,
            measured_ns=drill.measured_ns,
        )
    if row.evidence_fp1 != drill.evidence_fp1:
        return policy(
            row.name,
            "the RTO evidence citation must be the drill's evidence_fp1",
            failure_id=_RTO_ID,
        )
    return Ok(value.value)


def _bind_custody(row: ResolvedValueRow) -> Result[str | None]:
    if row.is_blank:
        return Ok(None)
    token = clean_token(row.value)
    if token != PAYLOAD_KEY_CUSTODY_RULE:
        return policy(
            row.name,
            "backup_payload_key_custody carries the workstation-escrowed rule, "
            "not a blank and not a VPS-minted descriptor (DEC-0252)",
            failure_id=_CUSTODY_ID,
            given=token if token is not None else repr(row.value),
            required=PAYLOAD_KEY_CUSTODY_RULE,
        )
    cited = _require_evidence(row)
    if is_refusal(cited):
        return cited
    return Ok(PAYLOAD_KEY_CUSTODY_RULE)


def _require_evidence(row: ResolvedValueRow) -> Result[None]:
    if row.is_blank:
        return Ok(None)
    if row.evidence_fp1 is None:
        return invalid(
            row.name,
            "a non-blank backup numeric or custody row carries an evidence citation",
            failure_id=_BLANK_ID,
            value_status=row.value_status,
        )
    return Ok(None)


def _optional_duration(row: ResolvedValueRow) -> Result[int | None]:
    if row.is_blank:
        return Ok(None)
    cited = _require_evidence(row)
    if is_refusal(cited):
        return cited
    parsed = _as_ns(row.value, row.name)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value)


def _optional_token(row: ResolvedValueRow) -> Result[str | None]:
    if row.is_blank:
        return Ok(None)
    cited = _require_evidence(row)
    if is_refusal(cited):
        return cited
    token = clean_token(row.value)
    if token is None:
        return invalid(row.name, "a provider token is a non-blank string")
    return Ok(token)


def _as_ns(value: object, field: str) -> Result[int]:
    if isinstance(value, Duration):
        return Ok(value.value_ns)
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            field,
            "a backup duration is int64 nanoseconds (or a Duration)",
            given=repr(value),
        )
    return Ok(value)


def _as_nonneg_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, f"{field} is a non-negative int64", given=repr(value))
    return Ok(value)


def _as_fingerprint(raw: object) -> Result[Fingerprint]:
    if isinstance(raw, Fingerprint):
        return Ok(raw)
    return Fingerprint.try_create(raw)
