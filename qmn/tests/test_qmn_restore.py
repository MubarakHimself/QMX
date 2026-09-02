"""Story 27.9 — three restore drills and verify-before-purge."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core import Result, World, WriterId, is_ok, is_refusal
from qmn.data import (
    BACKUP_PAYLOAD_KEY_SLOT,
    CLEAN_HOST_REHEARSAL_TONIGHT,
    FULL_DRILL,
    FULL_OBJECTIVE,
    FULL_WRITER_ROLE,
    FULL_WRITER_STREAM,
    HOST_LOSS_DRILL,
    HOST_LOSS_OBJECTIVE,
    HOST_LOSS_WRITER_ROLE,
    HOST_LOSS_WRITER_STREAM,
    LOCAL_TEST_BACKEND,
    RESTORE_ALARM_CLASS,
    RESTORE_AUTO_CUTOVER,
    SAMPLE_DRILL,
    SAMPLE_OBJECTIVE,
    SAMPLE_WRITER_ROLE,
    SAMPLE_WRITER_STREAM,
    BackupCommittedPrefix,
    BackupCopyPurgeCandidate,
    BackupPayloadCipher,
    HotRoomPurgeCandidate,
    LocalFilesystemRcloneRunner,
    OffHostCopyProof,
    RecordingBackupJournal,
    RecordingRcloneRunner,
    RecordingRestoreJournal,
    RestoreDrillReport,
    drill_measurement_from_report,
    evaluate_backup_copy_purge,
    evaluate_hot_room_purge,
    generate_test_payload_key,
    push_committed_prefixes,
    refuse_automatic_cutover,
    refuse_clean_host_rehearsal_tonight,
    refuse_silent_retry,
    restore_writer_id,
    run_restore_drill,
    try_bind_payload_cipher,
)
from qmn.data.restore import DATA_QUALITY_EVENT_TYPE
from qmn.data.restore_full import main as restore_full_main
from qmn.data.restore_sample import main as restore_sample_main
from qmn.observability import (
    AlertPublisher,
    RecordingNotificationChannel,
    load_alert_allow_list,
)
from qmn.secrets.holders import BACKUP_UNIT

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_WINDOW_NS = 86_400_000_000_000
_RPO_NS = 24 * 3_600 * 1_000_000_000
_BANNED_INFRA = frozenset({"boto3", "b2sdk", "keyring"})
_BANNED_TRADE = frozenset({"qmn.order", "qmn.venue", "qmn.host", "qmn.doors", "qmn.seats"})
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


class _Clock:
    def __init__(self, start: int = 1_000_000_000) -> None:
        self.n = start

    def __call__(self) -> int:
        self.n += 50_000_000
        return self.n


def _cipher() -> BackupPayloadCipher:
    key = _ok(generate_test_payload_key(backend=LOCAL_TEST_BACKEND))
    return _ok(
        try_bind_payload_cipher(
            holder=BACKUP_UNIT,
            slot=BACKUP_PAYLOAD_KEY_SLOT,
            key_material=key,
            minted_on="workstation",
            nonce_source=_Nonces(),
        )
    )


def _prefix(
    *,
    prefix_id: str = "journal-100",
    payload: bytes = b"committed-journal-prefix-bytes",
    start: int = 0,
    end: int = 100,
    room_role: str = "journal",
) -> BackupCommittedPrefix:
    return _ok(
        BackupCommittedPrefix.try_create(
            world=World.LIVE,
            room_role=room_role,
            prefix_id=prefix_id,
            start=start,
            end=end,
            payload=payload,
            committed=True,
        )
    )


def _push(
    tmp_path: Path, prefixes: tuple[BackupCommittedPrefix, ...]
) -> tuple[object, BackupPayloadCipher, Path]:
    cipher = _cipher()
    staging = tmp_path / "staging"
    remote = tmp_path / "remote"
    runner = RecordingRcloneRunner(LocalFilesystemRcloneRunner(remote))
    report = _ok(
        push_committed_prefixes(
            prefixes,
            cipher=cipher,
            staging=staging,
            remote_root=remote,
            runner=runner,
            backend=LOCAL_TEST_BACKEND,
        )
    )
    return report, cipher, remote


def _writer(kind: str, *, boot: str = "boot-27-9") -> WriterId:
    return _ok(restore_writer_id(kind=kind, machine="vps-fra-01", boot_epoch_id=boot))


def _alerts() -> tuple[Callable[[str, str], object], RecordingNotificationChannel]:
    allow = _ok(load_alert_allow_list())
    channel = RecordingNotificationChannel()
    publisher = AlertPublisher(allow_list=allow, channel=channel)

    def publish(failure_id: str, summary: str) -> object:
        return publisher.publish(failure_id=failure_id, summary=summary)

    return publish, channel


def _run(
    tmp_path: Path,
    *,
    kind: str,
    prefixes: tuple[BackupCommittedPrefix, ...] | None = None,
    retry: bool = False,
    clean_host: bool = False,
    cutover: bool = False,
    backend: str = LOCAL_TEST_BACKEND,
    writer: WriterId | None = None,
    journal: RecordingRestoreJournal | None = None,
    publish_alert: Callable[[str, str], object] | None = None,
    cipher: BackupPayloadCipher | None = None,
    remote: Path | None = None,
) -> tuple[
    Result[RestoreDrillReport],
    RecordingRestoreJournal,
    BackupPayloadCipher,
    Path,
]:
    items = prefixes if prefixes is not None else (_prefix(),)
    if remote is None or cipher is None:
        _report, cipher, remote = _push(tmp_path, items)
    sink = journal if journal is not None else RecordingRestoreJournal()
    return (
        run_restore_drill(
            kind=kind,
            writer=writer if writer is not None else _writer(kind),
            cipher=cipher,
            backend_root=remote,
            scratch=tmp_path / "scratch" / kind,
            source_root=str(tmp_path / "rooms"),
            journal=sink,
            backend=backend,
            clean_host=clean_host,
            cutover=cutover,
            retry=retry,
            clock_ns=_Clock(),
            publish_alert=publish_alert,
        ),
        sink,
        cipher,
        remote,
    )


def test_three_restore_drills_use_distinct_writer_ids() -> None:
    sample = _writer("sample")
    full = _writer("full")
    host = _writer("host_loss")
    assert sample.role == SAMPLE_WRITER_ROLE
    assert sample.stream == SAMPLE_WRITER_STREAM
    assert full.role == FULL_WRITER_ROLE
    assert full.stream == FULL_WRITER_STREAM
    assert host.role == HOST_LOSS_WRITER_ROLE
    assert host.stream == HOST_LOSS_WRITER_STREAM
    assert len({sample.order_tuple(), full.order_tuple(), host.order_tuple()}) == 3
    colliding = _refusal(
        run_restore_drill(
            kind="sample",
            writer=full,
            cipher=_cipher(),
            backend_root=Path("."),
            scratch=Path("scratch"),
            source_root="rooms",
            journal=RecordingRestoreJournal(),
        )
    )
    assert colliding.context["failure_id"] == "data.restore.wrong_writer"


def test_sample_restore_verifies_one_decrypted_identity(tmp_path: Path) -> None:
    prefixes = (
        _prefix(prefix_id="journal-1", payload=b"alpha-prefix", end=10),
        _prefix(prefix_id="journal-2", payload=b"beta-prefix", start=10, end=20),
    )
    result, journal, _cipher, _remote = _run(tmp_path, kind="sample", prefixes=prefixes)
    report = _ok(result)
    assert report.kind == "sample"
    assert report.drill == SAMPLE_DRILL
    assert report.objective == SAMPLE_OBJECTIVE
    assert report.outcome == "verified"
    assert report.verified_count == 1
    assert report.event_type == DATA_QUALITY_EVENT_TYPE
    assert report.original_authoritative is True
    assert report.cutover is False
    assert report.duration_ns > 0
    assert report.journaled is True
    assert journal.records[-1]["event_type"] == "data quality"
    assert journal.records[-1]["outcome"] == "verified"
    proof = report.proofs[0]
    assert proof.verified is True
    assert proof.verification_kind == "nightly-sample-restore"
    off_host = _ok(proof.to_off_host_proof())
    assert off_host.verified is True
    sample_rto = _refusal(drill_measurement_from_report(report))
    assert sample_rto.context["failure_id"] == "data.restore.sample_rto"


def test_full_restore_verifies_all_and_measures_integrity_rto(tmp_path: Path) -> None:
    prefixes = (
        _prefix(prefix_id="journal-1", payload=b"alpha-prefix", end=10),
        _prefix(
            prefix_id="raw-1",
            payload=b"raw-archive-prefix",
            end=20,
            room_role="immutable raw archive",
        ),
    )
    result, _journal, _cipher, _remote = _run(tmp_path, kind="full", prefixes=prefixes)
    report = _ok(result)
    assert report.kind == "full"
    assert report.drill == FULL_DRILL
    assert report.objective == FULL_OBJECTIVE
    assert report.verified_count == 2
    assert report.cutover is RESTORE_AUTO_CUTOVER
    measurement = _ok(drill_measurement_from_report(report))
    assert measurement.kind == "integrity"
    assert measurement.drill == FULL_DRILL
    assert measurement.measured_ns == report.duration_ns


def test_host_loss_local_fixture_never_cutovers(tmp_path: Path) -> None:
    result, journal, _cipher, _remote = _run(tmp_path, kind="host_loss")
    report = _ok(result)
    assert report.kind == "host_loss"
    assert report.drill == HOST_LOSS_DRILL
    assert report.objective == HOST_LOSS_OBJECTIVE
    assert report.original_authoritative is True
    assert report.cutover is False
    assert journal.records[-1]["original_authoritative"] is True
    measurement = _ok(drill_measurement_from_report(report))
    assert measurement.kind == "full_dr"
    assert measurement.drill == HOST_LOSS_DRILL
    cutover = _refusal(_run(tmp_path / "cut", kind="host_loss", cutover=True)[0])
    assert cutover.context["failure_id"] == "data.restore.cutover"
    explicit = refuse_automatic_cutover(source_root="/var/lib/qmx/rooms")
    assert explicit.context["original_authoritative"] is True
    assert CLEAN_HOST_REHEARSAL_TONIGHT is False


def test_real_clean_host_and_live_b2_are_refused(tmp_path: Path) -> None:
    clean = _refusal(_run(tmp_path, kind="host_loss", clean_host=True)[0])
    assert clean.context["failure_id"] == "data.restore.clean_host_tonight"
    explicit = refuse_clean_host_rehearsal_tonight(backend="backblaze-b2")
    assert explicit.context["clean_host_rehearsal_tonight"] is False
    live = _refusal(_run(tmp_path / "b2", kind="sample", backend="backblaze-b2")[0])
    assert live.context["failure_id"] == "data.backup.backblaze_tonight"
    assert restore_sample_main([]) == 1
    assert restore_full_main(["--backend", "backblaze-b2"]) == 1


def test_failure_is_journaled_and_never_silently_retried(tmp_path: Path) -> None:
    retry = _refusal(_run(tmp_path, kind="sample", retry=True)[0])
    assert retry.context["failure_id"] == "data.restore.silent_retry"
    assert refuse_silent_retry(drill=SAMPLE_DRILL).context["failure_id"] == (
        "data.restore.silent_retry"
    )
    publish, channel = _alerts()
    missing = _refusal(
        run_restore_drill(
            kind="sample",
            writer=_writer("sample"),
            cipher=_cipher(),
            backend_root=tmp_path / "empty-backend",
            scratch=tmp_path / "scratch",
            source_root=str(tmp_path / "rooms"),
            journal=RecordingRestoreJournal(),
            clock_ns=_Clock(),
            publish_alert=publish,
        )
    )
    assert missing.context["failure_id"] == "data.restore.missing_copy"
    assert channel.delivered
    assert channel.delivered[-1].alert_class == RESTORE_ALARM_CLASS
    assert channel.delivered[-1].failure_id == "data.restore.missing_copy"


def test_identity_mismatch_refuses_before_purge_claim(tmp_path: Path) -> None:
    prefixes = (_prefix(payload=b"original-identity-bytes"),)
    _report, cipher, remote = _push(tmp_path, prefixes)
    enc = next(remote.joinpath("objects").rglob("*.enc"))
    tampered = bytearray(enc.read_bytes())
    tampered[-1] ^= 0xFF
    enc.write_bytes(bytes(tampered))
    journal = RecordingRestoreJournal()
    refused = _refusal(
        run_restore_drill(
            kind="sample",
            writer=_writer("sample"),
            cipher=cipher,
            backend_root=remote,
            scratch=tmp_path / "scratch",
            source_root=str(tmp_path / "rooms"),
            journal=journal,
            clock_ns=_Clock(),
        )
    )
    assert refused.context["failure_id"] in {
        "data.restore.verify_mismatch",
        "data.backup.wrong_key",
    }
    assert journal.records[-1]["outcome"] == "failed"
    assert journal.records[-1]["event_type"] == "data quality"
    rooms = tmp_path / "rooms"
    assert not rooms.exists()


def test_purge_refuses_without_restore_verified_copies_and_journals() -> None:
    journal = RecordingRestoreJournal()
    missing_sealed = _refusal(
        evaluate_hot_room_purge(
            _hot_candidate(sealed_verified=False),
            journal=journal,
        )
    )
    assert missing_sealed.context["failure_id"] == "data.purge.missing_sealed"
    assert journal.records[-1]["allowed"] is False
    assert journal.records[-1]["event_type"] == "data quality"
    assert journal.records[-1]["reason"] == "data.purge.missing_sealed"

    missing_off = _refusal(
        evaluate_hot_room_purge(
            _hot_candidate(off_host_verified=False),
            journal=journal,
        )
    )
    assert missing_off.context["failure_id"] == "data.purge.missing_off_host"

    monitoring = _refusal(
        evaluate_hot_room_purge(
            _hot_candidate(verification_kind="monitoring"),
            journal=journal,
        )
    )
    assert monitoring.context["failure_id"] == "data.purge.monitoring_is_not_restore"
    assert journal.records[-1]["reason"] == "data.purge.monitoring_is_not_restore"

    heartbeat = _refusal(
        evaluate_hot_room_purge(
            _hot_candidate(verification_kind="provider-default"),
            journal=journal,
        )
    )
    assert heartbeat.context["failure_id"] == "data.purge.monitoring_is_not_restore"

    allowed = _ok(evaluate_hot_room_purge(_hot_candidate(), journal=journal))
    assert allowed.allowed is True
    assert allowed.journaled is True
    assert journal.records[-1]["allowed"] is True

    failing = RecordingRestoreJournal(fail_write=True)
    journal_fail = _refusal(evaluate_hot_room_purge(_hot_candidate(), journal=failing))
    assert journal_fail.context["failure_id"] == "data.purge.journal"


def test_backup_copy_purge_rejects_monitoring_as_restore_proof() -> None:
    journal = RecordingBackupJournal()
    monitoring = _refusal(
        evaluate_backup_copy_purge(
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
                    verification_kind="monitoring",
                )
            ),
            journal=journal,
        )
    )
    assert monitoring.context["failure_id"] == "data.backup.unverified_purge"
    assert journal.records[-1]["allowed"] is False


def test_restore_verified_proof_unlocks_hot_room_purge(tmp_path: Path) -> None:
    result, _journal, _cipher, _remote = _run(tmp_path, kind="sample")
    report = _ok(result)
    proof = _ok(report.proofs[0].to_off_host_proof())
    allowed = _ok(
        evaluate_hot_room_purge(
            _hot_candidate(
                prefix_id=proof.prefix_id,
                verification_kind=proof.verification_kind,
                off_host=proof,
            ),
            journal=RecordingRestoreJournal(),
        )
    )
    assert allowed.allowed is True


def test_systemd_units_invoke_restore_modules_without_trading_power() -> None:
    sample = (
        _QMN_ROOT / "deploy" / "systemd" / "templates" / "qmn-restore-sample.service.in"
    ).read_text(encoding="utf-8")
    full = (
        _QMN_ROOT / "deploy" / "systemd" / "templates" / "qmn-restore-full.service.in"
    ).read_text(encoding="utf-8")
    assert "python -m qmn.data.restore_sample" in sample
    assert "python -m qmn.data.restore_full" in full
    for unit in (sample, full):
        assert "LoadCredentialEncrypted=backup-payload-key" in unit
        lowered = unit.lower()
        for token in _TRADE_TOKENS:
            assert token not in lowered
    timer = (_QMN_ROOT / "deploy" / "systemd" / "templates" / "qmn-restore-sample.timer").read_text(
        encoding="utf-8"
    )
    assert "qmn-restore-sample.service" in timer
    full_timer = (
        _QMN_ROOT / "deploy" / "systemd" / "templates" / "qmn-restore-full.timer"
    ).read_text(encoding="utf-8")
    assert "qmn-restore-full.service" in full_timer


def test_restore_modules_import_no_live_sdk_or_trading_surface() -> None:
    for name in ("restore.py", "restore_sample.py", "restore_full.py"):
        path = _SRC / "data" / name
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
                imported.add(node.module)
        assert imported.isdisjoint(_BANNED_INFRA)
        for imported_name in imported:
            assert imported_name not in _BANNED_TRADE
            assert not any(
                imported_name == banned or imported_name.startswith(f"{banned}.")
                for banned in _BANNED_TRADE
            )


def _hot_candidate(
    *,
    prefix_id: str = "journal-100",
    sealed_verified: bool = True,
    off_host_verified: bool = True,
    verification_kind: str = "restore-verification",
    off_host: OffHostCopyProof | None = None,
) -> HotRoomPurgeCandidate:
    proof = off_host
    if proof is None:
        proof = _ok(
            OffHostCopyProof.try_create(
                prefix_id=prefix_id,
                verified=off_host_verified,
                copy_version="v1",
                verification_kind=verification_kind,
            )
        )
    return _ok(
        HotRoomPurgeCandidate.try_create(
            world=World.LIVE,
            room_role="journal",
            prefix_id=prefix_id,
            prefix_end=100,
            now_ns=_WINDOW_NS + 10,
            sealed_at_ns=0,
            retention_window_ns=_WINDOW_NS,
            sealed_verified=sealed_verified,
            off_host=proof,
        )
    )


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


def test_restore_report_has_no_plaintext_or_key_material(tmp_path: Path) -> None:
    prefixes = (_prefix(payload=b"unique-plaintext-marker-27-9"),)
    result, _journal, _cipher, _remote = _run(tmp_path, kind="full", prefixes=prefixes)
    blob = " ".join(_walk_strings(_ok(result).as_mapping())).lower()
    assert "unique-plaintext-marker-27-9" not in blob
    assert "password" not in blob
    assert "backup-payload-key" not in blob
