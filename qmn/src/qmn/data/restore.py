"""Three restore drills and restore-verification proofs (Story 27.9).

Nightly sample restore and monthly full-integrity restore run under distinct
WriterIds, decrypt into a scratch replacement root, and verify content identity
before any purge claim. Duration is recorded against each drill's own objective.
Failures journal as ``data quality``, alarm on silent-degradation, and are never
silently retried. Generated local-backend fixtures prove the mechanics; a live
Backblaze bucket or clean-host rehearsal is soak-local and refused tonight
(DEC-0198, DEC-0252, AR-87). Host-loss never auto-cutovers.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    WriterId,
    fingerprint_bytes,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import Retryability

from qmn.data._refuse import clean_token, invalid, policy, storage, unavailable
from qmn.data.backup import (
    LIVE_BUCKET_TOKENS,
    BackupPayloadCipher,
    DrillMeasurement,
    refuse_destructive_restore_fallback,
    restore_decrypt,
)
from qmn.data.backup_run import LOCAL_TEST_BACKEND, refuse_live_b2_without_soak
from qmn.data.sealed_archive import OffHostCopyProof

__all__ = [
    "CLEAN_HOST_REHEARSAL_TONIGHT",
    "DATA_QUALITY_EVENT_TYPE",
    "FULL_DRILL",
    "FULL_OBJECTIVE",
    "FULL_WRITER_ROLE",
    "FULL_WRITER_STREAM",
    "HOST_LOSS_DRILL",
    "HOST_LOSS_OBJECTIVE",
    "HOST_LOSS_WRITER_ROLE",
    "HOST_LOSS_WRITER_STREAM",
    "RESTORE_ALARM_CLASS",
    "RESTORE_AUTO_CUTOVER",
    "RESTORE_SURFACE",
    "RESTORE_VERIFICATION_KINDS",
    "SAMPLE_DRILL",
    "SAMPLE_OBJECTIVE",
    "SAMPLE_WRITER_ROLE",
    "SAMPLE_WRITER_STREAM",
    "RecordingRestoreJournal",
    "RestoreDrillReport",
    "RestoreVerificationProof",
    "drill_measurement_from_report",
    "main",
    "refuse_automatic_cutover",
    "refuse_clean_host_rehearsal_tonight",
    "refuse_silent_retry",
    "restore_writer_id",
    "run_restore_drill",
]


RESTORE_SURFACE: Final[str] = "qmn.data.restore"
DATA_QUALITY_EVENT_TYPE: Final[str] = "data quality"
RESTORE_ALARM_CLASS: Final[str] = "silent-degradation"
RESTORE_AUTO_CUTOVER: Final[bool] = False
CLEAN_HOST_REHEARSAL_TONIGHT: Final[bool] = False

SAMPLE_DRILL: Final[str] = "qmn-restore-sample.timer"
FULL_DRILL: Final[str] = "qmn-restore-full.timer"
HOST_LOSS_DRILL: Final[str] = "restore_drill_run"

SAMPLE_WRITER_ROLE: Final[str] = "restore-sample"
SAMPLE_WRITER_STREAM: Final[str] = "restore-sample"
FULL_WRITER_ROLE: Final[str] = "restore-full"
FULL_WRITER_STREAM: Final[str] = "restore-full"
HOST_LOSS_WRITER_ROLE: Final[str] = "restore-host-loss"
HOST_LOSS_WRITER_STREAM: Final[str] = "restore-host-loss"

SAMPLE_OBJECTIVE: Final[str] = "fingerprint-identity"
FULL_OBJECTIVE: Final[str] = "integrity"
HOST_LOSS_OBJECTIVE: Final[str] = "full_dr"

RESTORE_VERIFICATION_KINDS: Final[frozenset[str]] = frozenset(
    {
        "restore-verification",
        "nightly-sample-restore",
        "monthly-full-restore",
        "host-loss-rehearsal",
    }
)

_KIND_SPECS: Final[Mapping[str, Mapping[str, str]]] = MappingProxyType(
    {
        "sample": MappingProxyType(
            {
                "kind": "sample",
                "drill": SAMPLE_DRILL,
                "role": SAMPLE_WRITER_ROLE,
                "stream": SAMPLE_WRITER_STREAM,
                "objective": SAMPLE_OBJECTIVE,
                "proof_kind": "nightly-sample-restore",
            }
        ),
        "full": MappingProxyType(
            {
                "kind": "full",
                "drill": FULL_DRILL,
                "role": FULL_WRITER_ROLE,
                "stream": FULL_WRITER_STREAM,
                "objective": FULL_OBJECTIVE,
                "proof_kind": "monthly-full-restore",
            }
        ),
        "host_loss": MappingProxyType(
            {
                "kind": "host_loss",
                "drill": HOST_LOSS_DRILL,
                "role": HOST_LOSS_WRITER_ROLE,
                "stream": HOST_LOSS_WRITER_STREAM,
                "objective": HOST_LOSS_OBJECTIVE,
                "proof_kind": "host-loss-rehearsal",
            }
        ),
    }
)
_KIND_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "sample": "sample",
        "nightly-sample-restore": "sample",
        SAMPLE_DRILL: "sample",
        "full": "full",
        "monthly-full-restore": "full",
        FULL_DRILL: "full",
        "host_loss": "host_loss",
        "host-loss": "host_loss",
        "host-loss-rehearsal": "host_loss",
        HOST_LOSS_DRILL: "host_loss",
    }
)

_SILENT_RETRY_ID: Final[str] = "data.restore.silent_retry"
_VERIFY_ID: Final[str] = "data.restore.verify_mismatch"
_MISSING_ID: Final[str] = "data.restore.missing_copy"
_CUTOVER_ID: Final[str] = "data.restore.cutover"
_CLEAN_HOST_ID: Final[str] = "data.restore.clean_host_tonight"
_WRITER_ID: Final[str] = "data.restore.wrong_writer"
_SAMPLE_RTO_ID: Final[str] = "data.restore.sample_rto"
_PULL_ID: Final[str] = "data.restore.pull"
_JOURNAL_ID: Final[str] = "data.restore.journal"
_KIND_ID: Final[str] = "data.restore.kind"
_MAX_OBJECT_BYTES: Final[int] = 1 << 20
_CIPHERTEXT_SUFFIX: Final[str] = ".enc"


class RestoreJournalSink(Protocol):
    """Append-only data-quality journal for restore drills and purge proofs."""

    def append(self, record: Mapping[str, object], /) -> Result[None]: ...


class RecordingRestoreJournal:
    """Test/in-process journal for restore-drill and purge verdicts."""

    def __init__(self, *, fail_write: bool = False) -> None:
        self.records: list[Mapping[str, object]] = []
        self.fail_write = fail_write

    def append(self, record: Mapping[str, object], /) -> Result[None]:
        if self.fail_write:
            return unavailable(
                "journal",
                "the restore drill journal rejected the data-quality record",
                failure_id=_JOURNAL_ID,
            )
        self.records.append(MappingProxyType(dict(record)))
        return Ok(None)


@dataclass(frozen=True, slots=True)
class RestoreVerificationProof:
    """One decrypted, identity-verified off-host copy — the only purge proof."""

    prefix_id: str
    content_fp1: str
    copy_version: str
    verified: bool
    verification_kind: str
    object_key: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "prefix_id": self.prefix_id,
                "content_fp1": self.content_fp1,
                "copy_version": self.copy_version,
                "verified": self.verified,
                "verification_kind": self.verification_kind,
                "object_key": self.object_key,
            }
        )

    def to_off_host_proof(self) -> Result[OffHostCopyProof]:
        """Convert a verified restore proof into the purge off-host claim."""
        if not self.verified:
            return policy(
                "verification",
                "an unverified restore result is not an off-host purge proof",
                failure_id=_VERIFY_ID,
                prefix_id=self.prefix_id,
            )
        return OffHostCopyProof.try_create(
            prefix_id=self.prefix_id,
            verified=True,
            copy_version=self.copy_version,
            verification_kind=self.verification_kind,
        )


@dataclass(frozen=True, slots=True)
class RestoreDrillReport:
    """Outcome of one restore drill firing — never a cutover grant."""

    kind: str
    drill: str
    writer: Mapping[str, object]
    outcome: str
    duration_ns: int
    objective: str
    verified_count: int
    proofs: tuple[RestoreVerificationProof, ...]
    original_authoritative: bool
    cutover: bool
    backend: str
    journaled: bool
    alarm_class: str | None
    event_type: str = DATA_QUALITY_EVENT_TYPE

    def __post_init__(self) -> None:
        object.__setattr__(self, "writer", MappingProxyType(dict(self.writer)))

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": self.kind,
                "drill": self.drill,
                "writer": dict(self.writer),
                "outcome": self.outcome,
                "duration_ns": self.duration_ns,
                "objective": self.objective,
                "verified_count": self.verified_count,
                "proofs": [dict(item.as_mapping()) for item in self.proofs],
                "original_authoritative": self.original_authoritative,
                "cutover": self.cutover,
                "backend": self.backend,
                "journaled": self.journaled,
                "alarm_class": self.alarm_class,
                "event_type": self.event_type,
            }
        )


def restore_writer_id(
    *,
    kind: object,
    machine: object,
    boot_epoch_id: object,
) -> Result[WriterId]:
    """Mint the distinct WriterId that owns one restore-drill stream."""
    spec = _kind_spec(kind)
    if is_refusal(spec):
        return spec
    return WriterId.try_create(machine, spec.value["role"], spec.value["stream"], boot_epoch_id)


def refuse_silent_retry(*, drill: object = None) -> TypedRefusal:
    """A restore drill never retries inside the same firing (DEC-0198)."""
    extra: dict[str, object] = {"failure_id": _SILENT_RETRY_ID, "retryability": "no"}
    token = clean_token(drill)
    if token is not None:
        extra["drill"] = token
    return policy(
        "retry",
        "restore-drill failure is exposed and never silently retried inside "
        "the same firing (DEC-0198, DEC-0233)",
        **extra,
    )


def refuse_automatic_cutover(*, source_root: object = None) -> TypedRefusal:
    """A restore drill never cuts over; the original node stays authoritative."""
    extra: dict[str, object] = {
        "failure_id": _CUTOVER_ID,
        "cutover": RESTORE_AUTO_CUTOVER,
        "original_authoritative": True,
    }
    token = clean_token(source_root)
    if token is not None:
        extra["source_root"] = token
    return policy(
        "cutover",
        "restore drills never cut over automatically; the original node remains "
        "authoritative until the operator explicitly decides otherwise (TN-13)",
        **extra,
    )


def refuse_clean_host_rehearsal_tonight(*, backend: object = None) -> TypedRefusal:
    """Real bucket/key clean-host rehearsal is soak-local, not factory work."""
    extra: dict[str, object] = {
        "failure_id": _CLEAN_HOST_ID,
        "clean_host_rehearsal_tonight": CLEAN_HOST_REHEARSAL_TONIGHT,
        "soak_local": False,
    }
    token = clean_token(backend)
    if token is not None:
        extra["backend"] = token
    return policy(
        "clean_host",
        "the real bucket/key clean-host rehearsal is soak-local; factory tests "
        "prove restore mechanics against generated local-backend fixtures (AR-87)",
        **extra,
    )


def drill_measurement_from_report(report: object) -> Result[DrillMeasurement]:
    """Bind a successful full or host-loss report onto its distinct RTO row."""
    if not isinstance(report, RestoreDrillReport):
        return invalid(
            "report",
            "RTO measurement binds a RestoreDrillReport",
            given=repr(type(report).__name__),
        )
    if report.outcome != "verified":
        return policy(
            "outcome",
            "an unverified restore drill does not measure an RTO",
            failure_id=_VERIFY_ID,
            kind=report.kind,
        )
    if report.kind == "sample" or report.objective == SAMPLE_OBJECTIVE:
        return policy(
            "drill",
            "the nightly sample restore does not measure either RTO (DEC-0198, DEC-0252)",
            failure_id=_SAMPLE_RTO_ID,
            drill=report.drill,
        )
    rto_kind = "integrity" if report.kind == "full" else "full_dr"
    evidence = fingerprint_bytes(
        json.dumps(dict(report.as_mapping()), sort_keys=True).encode("utf-8")
    )
    return DrillMeasurement.try_create(
        kind=rto_kind,
        drill=report.drill,
        measured_ns=report.duration_ns,
        evidence_fp1=evidence,
    )


def run_restore_drill(
    *,
    kind: object,
    writer: object,
    cipher: object,
    backend_root: Path,
    scratch: Path,
    source_root: object,
    journal: object,
    backend: object = LOCAL_TEST_BACKEND,
    soak_local: object = False,
    has_account: object = False,
    clean_host: object = False,
    cutover: object = False,
    retry: object = False,
    clock_ns: Callable[[], int] | None = None,
    publish_alert: Callable[[str, str], object] | None = None,
) -> Result[RestoreDrillReport]:
    """Run one sample, full, or host-loss restore drill against a local backend."""
    spec = _kind_spec(kind)
    if is_refusal(spec):
        return spec
    kind_spec = spec.value
    if retry is True:
        return refuse_silent_retry(drill=kind_spec["drill"])
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "a restore drill journals under its own WriterId",
            given=repr(type(writer).__name__),
        )
    if writer.role != kind_spec["role"] or writer.stream != kind_spec["stream"]:
        return policy(
            "writer",
            "each restore drill uses its own WriterId; one timer never carries "
            "two cadences (DEC-0198, DEC-0252)",
            failure_id=_WRITER_ID,
            role=writer.role,
            stream=writer.stream,
            required_role=kind_spec["role"],
            required_stream=kind_spec["stream"],
        )
    if not isinstance(cipher, BackupPayloadCipher):
        return invalid(
            "cipher",
            "restore decrypts through BackupPayloadCipher",
            given=repr(type(cipher).__name__),
        )
    if not hasattr(journal, "append"):
        return invalid(
            "journal",
            "restore drills journal as data quality; a journal sink is required",
            given=repr(type(journal).__name__),
        )
    sink = cast("RestoreJournalSink", journal)
    gated = refuse_live_b2_without_soak(
        backend=backend, soak_local=soak_local, has_account=has_account
    )
    if is_refusal(gated):
        return gated
    if clean_host is True:
        return refuse_clean_host_rehearsal_tonight(backend=backend)
    if cutover is True:
        return refuse_automatic_cutover(source_root=source_root)
    src = str(source_root) if isinstance(source_root, Path) else clean_token(source_root)
    scratch_token = str(scratch)
    if src is None:
        return invalid("source_root", "restore names the original evidence root")
    if src == scratch_token:
        return refuse_destructive_restore_fallback(source_root=src)
    if not callable(clock_ns):
        return invalid(
            "clock_ns",
            "a restore drill records duration from an injected clock, never the host clock",
            given=repr(type(clock_ns).__name__),
        )

    started = _now_ns(clock_ns)
    pulled = _pull_objects(
        backend_root,
        scratch,
        sample=kind_spec["kind"] == "sample",
    )
    if is_refusal(pulled):
        return _fail_drill(
            kind_spec,
            writer=writer,
            backend=backend,
            duration_ns=_elapsed_ns(started, clock_ns),
            sink=sink,
            refusal=pulled,
            publish_alert=publish_alert,
        )
    proofs: list[RestoreVerificationProof] = []
    for enc_path, manifest in pulled.value:
        verified = _verify_one(
            enc_path,
            manifest,
            cipher=cipher,
            source_root=src,
            scratch=scratch,
            proof_kind=kind_spec["proof_kind"],
        )
        if is_refusal(verified):
            return _fail_drill(
                kind_spec,
                writer=writer,
                backend=backend,
                duration_ns=_elapsed_ns(started, clock_ns),
                sink=sink,
                refusal=verified,
                publish_alert=publish_alert,
            )
        proofs.append(verified.value)
    duration_ns = _elapsed_ns(started, clock_ns)
    if duration_ns <= 0:
        return invalid(
            "duration_ns",
            "a restore drill records a positive duration against its objective",
            given=duration_ns,
        )
    report = RestoreDrillReport(
        kind=kind_spec["kind"],
        drill=kind_spec["drill"],
        writer=_writer_map(writer),
        outcome="verified",
        duration_ns=duration_ns,
        objective=kind_spec["objective"],
        verified_count=len(proofs),
        proofs=tuple(proofs),
        original_authoritative=True,
        cutover=RESTORE_AUTO_CUTOVER,
        backend=clean_token(backend) or LOCAL_TEST_BACKEND,
        journaled=False,
        alarm_class=None,
    )
    written = sink.append(_success_record(report, writer))
    if is_refusal(written):
        return written
    return Ok(
        RestoreDrillReport(
            kind=report.kind,
            drill=report.drill,
            writer=report.writer,
            outcome=report.outcome,
            duration_ns=report.duration_ns,
            objective=report.objective,
            verified_count=report.verified_count,
            proofs=report.proofs,
            original_authoritative=True,
            cutover=RESTORE_AUTO_CUTOVER,
            backend=report.backend,
            journaled=True,
            alarm_class=None,
        )
    )


def main(argv: list[str] | None = None, *, kind: str = "sample") -> int:
    """Systemd oneshot. Factory tests drive :func:`run_restore_drill`."""
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
    _ = (kind, CLEAN_HOST_REHEARSAL_TONIGHT, RESTORE_AUTO_CUTOVER)
    return 1


def _kind_spec(kind: object) -> Result[Mapping[str, str]]:
    token = clean_token(kind)
    if token is None:
        return invalid("kind", "restore drill kind is sample | full | host_loss")
    resolved = _KIND_ALIASES.get(token)
    if resolved is None:
        return policy(
            "kind",
            "restore drills are the nightly sample, monthly full-integrity, "
            "and host-loss rehearsal (DEC-0252)",
            failure_id=_KIND_ID,
            given=token,
        )
    return Ok(_KIND_SPECS[resolved])


def _writer_map(writer: WriterId) -> Mapping[str, object]:
    return MappingProxyType(
        {
            "machine": writer.machine,
            "role": writer.role,
            "stream": writer.stream,
            "boot_epoch_id": writer.boot_epoch_id,
            "order_tuple": list(writer.order_tuple()),
        }
    )


def _now_ns(clock_ns: Callable[[], int]) -> int:
    return clock_ns()


def _elapsed_ns(started: int, clock_ns: Callable[[], int]) -> int:
    return clock_ns() - started


def _pull_objects(
    backend_root: Path,
    scratch: Path,
    *,
    sample: bool,
) -> Result[tuple[tuple[Path, Mapping[str, object]], ...]]:
    objects = backend_root / "objects"
    if objects.is_symlink() or not objects.is_dir():
        return unavailable(
            "backend",
            "local-backend fixtures hold no encrypted restore objects",
            failure_id=_MISSING_ID,
        )
    enc_files = [
        path
        for path in sorted(objects.rglob("*"))
        if path.is_file() and not path.is_symlink() and path.suffix == _CIPHERTEXT_SUFFIX
    ]
    if not enc_files:
        return unavailable(
            "backend",
            "local-backend fixtures hold no encrypted restore objects",
            failure_id=_MISSING_ID,
        )
    selected = enc_files[:1] if sample else enc_files
    prepared = _ensure_dir(scratch)
    if is_refusal(prepared):
        return prepared
    cipher_root = scratch / "ciphertext"
    created = _ensure_dir(cipher_root)
    if is_refusal(created):
        return created
    pulled: list[tuple[Path, Mapping[str, object]]] = []
    for src in selected:
        try:
            relative = src.relative_to(objects)
        except ValueError:
            return policy("path", "restore object escaped the local backend", failure_id=_PULL_ID)
        dest = cipher_root / relative
        contained = _contained_file(cipher_root, dest)
        if is_refusal(contained):
            return contained
        copied = _copy_file(src, contained.value)
        if is_refusal(copied):
            return copied
        manifest = _load_manifest(src)
        if is_refusal(manifest):
            return manifest
        pulled.append((contained.value, manifest.value))
    return Ok(tuple(pulled))


def _verify_one(
    enc_path: Path,
    manifest: Mapping[str, object],
    *,
    cipher: BackupPayloadCipher,
    source_root: str,
    scratch: Path,
    proof_kind: str,
) -> Result[RestoreVerificationProof]:
    ciphertext = _read_capped(enc_path)
    if is_refusal(ciphertext):
        return ciphertext
    body = ciphertext.value
    expected_cipher = clean_token(manifest.get("payload_fingerprint"))
    actual_cipher = fingerprint_bytes(body).value
    if expected_cipher is None or actual_cipher != expected_cipher:
        return policy(
            "payload_fingerprint",
            "restore refused a ciphertext identity mismatch before decrypt (DEC-0252)",
            failure_id=_VERIFY_ID,
            expected=expected_cipher,
            actual=actual_cipher,
        )
    replacement = str(scratch / "plaintext")
    decrypted = restore_decrypt(
        cipher,
        body,
        source_root=source_root,
        replacement_root=replacement,
    )
    if is_refusal(decrypted):
        return decrypted
    plaintext = decrypted.value
    actual_identity = fingerprint_bytes(plaintext)
    expected_identity = _as_fingerprint(manifest.get("content_fp1"))
    if is_refusal(expected_identity):
        return policy(
            "content_fp1",
            "restore verifies decrypted content identity before any purge claim (FR-065, DEC-0252)",
            failure_id=_VERIFY_ID,
        )
    expected_fp = expected_identity.value
    if actual_identity.value != expected_fp.value:
        return policy(
            "content_fp1",
            "restore refused a decrypted content/identity mismatch; no purge "
            "claim is minted (FR-065, DEC-0252)",
            failure_id=_VERIFY_ID,
            expected=expected_fp.value,
            actual=actual_identity.value,
        )
    verified_dir = scratch / "verified"
    created = _ensure_dir(verified_dir)
    if is_refusal(created):
        return created
    prefix_id = clean_token(manifest.get("prefix_id"))
    if prefix_id is None:
        return invalid("prefix_id", "a restore object names its prefix id")
    dest = verified_dir / prefix_id
    contained = _contained_file(verified_dir, dest)
    if is_refusal(contained):
        return contained
    written = _atomic_write(contained.value, plaintext)
    if is_refusal(written):
        return written
    copy_version = manifest.get("copy_version", 1)
    version = f"v{copy_version}" if isinstance(copy_version, int) else str(copy_version)
    object_key = enc_path.name
    return Ok(
        RestoreVerificationProof(
            prefix_id=prefix_id,
            content_fp1=actual_identity.value,
            copy_version=version,
            verified=True,
            verification_kind=proof_kind,
            object_key=object_key,
        )
    )


def _fail_drill(
    kind_spec: Mapping[str, str],
    *,
    writer: WriterId,
    backend: object,
    duration_ns: int,
    sink: RestoreJournalSink,
    refusal: TypedRefusal,
    publish_alert: Callable[[str, str], object] | None,
) -> Result[RestoreDrillReport]:
    failure_id = _failure_id_of(refusal)
    record = MappingProxyType(
        {
            "event_type": DATA_QUALITY_EVENT_TYPE,
            "kind": kind_spec["kind"],
            "drill": kind_spec["drill"],
            "outcome": "failed",
            "duration_ns": max(duration_ns, 0),
            "objective": kind_spec["objective"],
            "writer": list(writer.order_tuple()),
            "original_authoritative": True,
            "cutover": RESTORE_AUTO_CUTOVER,
            "backend": clean_token(backend) or LOCAL_TEST_BACKEND,
            "failure_id": failure_id,
            "alarm_class": RESTORE_ALARM_CLASS,
        }
    )
    written = sink.append(record)
    if is_refusal(written):
        return written
    alarmed = _alarm(publish_alert, failure_id)
    if is_refusal(alarmed):
        return alarmed
    return refusal


def _alarm(publish_alert: Callable[[str, str], object] | None, failure_id: str) -> Result[None]:
    if publish_alert is None:
        return Ok(None)
    published = publish_alert(failure_id, "restore drill failed; not retried")
    if isinstance(published, TypedRefusal):
        return published
    return Ok(None)


def _success_record(report: RestoreDrillReport, writer: WriterId) -> Mapping[str, object]:
    return MappingProxyType(
        {
            "event_type": DATA_QUALITY_EVENT_TYPE,
            "kind": report.kind,
            "drill": report.drill,
            "outcome": report.outcome,
            "duration_ns": report.duration_ns,
            "objective": report.objective,
            "verified_count": report.verified_count,
            "writer": list(writer.order_tuple()),
            "original_authoritative": True,
            "cutover": RESTORE_AUTO_CUTOVER,
            "backend": report.backend,
            "proofs": [dict(item.as_mapping()) for item in report.proofs],
        }
    )


def _failure_id_of(refusal: TypedRefusal) -> str:
    raw = refusal.context.get("failure_id")
    token = clean_token(raw)
    return token if token is not None else _VERIFY_ID


def _as_fingerprint(raw: object) -> Result[Fingerprint]:
    if isinstance(raw, Fingerprint):
        return Ok(raw)
    parsed = Fingerprint.try_create(raw)
    if is_ok(parsed):
        return parsed
    return invalid("content_fp1", "restore identity is an fp1 fingerprint")


def _load_manifest(enc: Path) -> Result[Mapping[str, object]]:
    path = enc.with_suffix(".manifest.json")
    if path.is_symlink() or not path.is_file():
        alt = enc.with_name(enc.name.replace(".enc", ".manifest.json"))
        if alt.is_symlink() or not alt.is_file():
            return unavailable(
                "manifest",
                "restore object is missing its ciphertext-only manifest",
                failure_id=_MISSING_ID,
            )
        path = alt
    loaded = _read_capped(path)
    if is_refusal(loaded):
        return loaded
    try:
        body = json.loads(loaded.value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return unavailable("manifest", "restore manifest is not readable JSON")
    if not isinstance(body, dict):
        return unavailable("manifest", "restore manifest is an object")
    mapping = cast("dict[str, object]", body)
    leaked = _refuse_if_leaked(mapping)
    if is_refusal(leaked):
        return leaked
    return Ok(MappingProxyType(dict(mapping)))


def _refuse_if_leaked(body: Mapping[str, object]) -> Result[None]:
    forbidden = frozenset({"payload", "plaintext", "key", "ciphertext"})
    secret_tokens = (
        "password",
        "secret",
        "credential",
        "applicationkey",
        "accountid",
        "backup-payload-key",
    )
    for key, value in body.items():
        if key in forbidden:
            return policy(
                "evidence",
                "credentials and plaintext never enter restore metadata",
                failure_id="data.backup.secret_in_evidence",
                evidence_field=key,
            )
        blob = f"{key}={value}".lower().replace("_", "").replace("-", "")
        for token in secret_tokens:
            if token in blob:
                return policy(
                    "evidence",
                    "credentials and plaintext never enter restore metadata",
                    failure_id="data.backup.secret_in_evidence",
                    evidence_field=key,
                )
        if isinstance(value, (bytes, bytearray)):
            return policy(
                "evidence",
                "credentials and plaintext never enter restore metadata",
                failure_id="data.backup.secret_in_evidence",
                evidence_field=key,
            )
    return Ok(None)


def _copy_file(src: Path, dest: Path) -> Result[None]:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    except OSError:
        return storage(
            "pull",
            "local-backend restore pull could not copy the ciphertext object",
            failure_id=_PULL_ID,
            retryability=Retryability.NO,
        )
    return Ok(None)


def _read_capped(path: Path) -> Result[bytes]:
    if path.is_symlink() or not path.is_file():
        return unavailable("object", "restore object is missing", failure_id=_MISSING_ID)
    try:
        size = path.stat().st_size
    except OSError:
        return storage("object", "restore object could not be read", failure_id=_PULL_ID)
    if size > _MAX_OBJECT_BYTES:
        return policy("object", "restore object exceeds the size cap", size=size)
    try:
        return Ok(path.read_bytes())
    except OSError:
        return storage("object", "restore object could not be read", failure_id=_PULL_ID)


def _ensure_dir(path: Path) -> Result[None]:
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink at restore scratch")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return storage(
            "path",
            "restore scratch directory could not be created",
            failure_id=_PULL_ID,
        )
    return Ok(None)


def _contained_file(root: Path, path: Path) -> Result[Path]:
    try:
        resolved_root = root.resolve()
        resolved_parent = path.parent.resolve()
    except OSError:
        return storage("path", "restore path could not be resolved", failure_id=_PULL_ID)
    if path.is_symlink() or path.parent.is_symlink():
        return policy("path", "refusing to follow a symlink in restore scratch")
    if not resolved_parent.is_relative_to(resolved_root):
        return policy("path", "restore path escaped the scratch root")
    return Ok(path)


def _atomic_write(path: Path, payload: bytes) -> Result[None]:
    if path.is_symlink():
        return policy("path", "refusing to follow a symlink at the restore dest")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return storage("path", "restore directory could not be created", failure_id=_PULL_ID)
    tmp = path.parent / f".{path.name}.tmp-{os.getpid()}"
    if tmp.is_symlink():
        return policy("path", "refusing to follow a symlink at the restore temp")
    flags = (
        os.O_CREAT
        | os.O_EXCL
        | os.O_WRONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        fd = os.open(tmp, flags, 0o600)  # skylos: ignore[SKY-D215] contained restore stage
    except OSError:
        return storage("path", "restore scratch rejected the verified object", failure_id=_PULL_ID)
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            offset += os.write(fd, view[offset:])
    except OSError:
        os.close(fd)
        tmp.unlink(missing_ok=True)
        return storage("path", "restore scratch rejected the verified object", failure_id=_PULL_ID)
    os.close(fd)
    try:
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        return storage("path", "restore scratch rejected the verified object", failure_id=_PULL_ID)
    return Ok(None)
