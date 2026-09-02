"""Story 27.4 — one-way watermarked copy into sealed-archive and verify-before-purge."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal
from qmn.data import (
    EIGHTH_ROOM_ROLE,
    HOT_ROOM_ROLES,
    KEEP_FOREVER_KINDS,
    OFF_HOST_BACKUP_INFRA_TONIGHT,
    SEALED_ARCHIVE_IS_SECOND_WRITER,
    SEALED_ARCHIVE_ROLE,
    SYNC_BLOCKS_LOOP,
    CommittedHotPrefix,
    HotRoomPurgeCandidate,
    OffHostCopyProof,
    SealedArchive,
    attach_sync_to_loop,
    evaluate_hot_room_purge,
    evaluate_sealed_deletion,
    refuse_loop_blocking_sync,
    refuse_off_host_backup_infra,
    refuse_second_writer,
    refuse_uncommitted_prefix,
)
from qmn.loop.driver import CommandStreamLoop

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_WINDOW_NS = 86_400_000_000_000
_BANNED_INFRA = frozenset({"rclone", "boto3", "b2sdk", "backblaze"})


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _prefix(
    *,
    prefix_id: str = "journal-100",
    payload: bytes = b"committed-journal-prefix",
    start: int = 0,
    end: int = 100,
    world: World = World.LIVE,
    room_role: str = "journal",
    committed: bool = True,
) -> Result[CommittedHotPrefix]:
    return CommittedHotPrefix.try_create(
        world=world,
        room_role=room_role,
        prefix_id=prefix_id,
        start=start,
        end=end,
        payload=payload,
        committed=committed,
    )


def _candidate(
    *,
    prefix_id: str = "journal-100",
    now_ns: int = _WINDOW_NS + 10,
    sealed_at_ns: int = 0,
    sealed_verified: bool = True,
    off_host_verified: bool = True,
    room_role: str = "journal",
    cited: bool = False,
    prefix_end: int = 100,
) -> HotRoomPurgeCandidate:
    proof = _ok(
        OffHostCopyProof.try_create(
            prefix_id=prefix_id,
            verified=off_host_verified,
            copy_version="v1",
        )
    )
    return _ok(
        HotRoomPurgeCandidate.try_create(
            world=World.LIVE,
            room_role=room_role,
            prefix_id=prefix_id,
            prefix_end=prefix_end,
            now_ns=now_ns,
            sealed_at_ns=sealed_at_ns,
            retention_window_ns=_WINDOW_NS,
            sealed_verified=sealed_verified,
            off_host=proof,
            cited=cited,
        )
    )


def test_eighth_room_role_is_sealed_archive() -> None:
    assert SEALED_ARCHIVE_ROLE == EIGHTH_ROOM_ROLE == "sealed-archive"
    assert {
        "ingest door",
        "immutable raw archive",
        "processed",
        "journal",
    } == HOT_ROOM_ROLES
    assert SYNC_BLOCKS_LOOP is False
    assert SEALED_ARCHIVE_IS_SECOND_WRITER is False
    assert OFF_HOST_BACKUP_INFRA_TONIGHT is False
    assert "journal" in KEEP_FOREVER_KINDS


def test_uncommitted_prefix_is_refused() -> None:
    refused = _refusal(_prefix(committed=False))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "data.sealed.uncommitted"
    explicit = _refusal(refuse_uncommitted_prefix(prefix_id="torn"))
    assert explicit.context["failure_id"] == "data.sealed.uncommitted"


def test_simulated_world_is_refused() -> None:
    refused = _refusal(_prefix(world=World.SIMULATED))
    assert refused.context["failure_id"] == "data.sealed.world"


def test_sync_is_one_way_watermarked_idempotent_and_resumable(tmp_path: Path) -> None:
    archive = SealedArchive(tmp_path / "evidence")
    first = _ok(archive.sync(_ok(_prefix())))
    assert first.copied is True
    assert first.verified is True
    assert first.resumed is False
    assert first.second_writer is False
    assert first.blocks_loop is False
    assert first.watermark.prefix_end == 100
    assert first.watermark.verified is True
    dest = tmp_path / "evidence" / "live" / "sealed-archive" / "journal" / "journal-100"
    assert dest.is_file() and not dest.is_symlink()
    assert dest.read_bytes() == b"committed-journal-prefix"

    again = _ok(archive.sync(_ok(_prefix())))
    assert again.copied is False
    assert again.resumed is True
    assert again.verified is True
    assert again.watermark.prefix_end == 100

    later = _ok(
        archive.sync(_ok(_prefix(prefix_id="journal-200", payload=b"next-prefix", end=200)))
    )
    assert later.copied is True
    assert later.watermark.prefix_end == 200
    mark = _ok(archive.watermark(World.LIVE, "journal"))
    assert mark is not None
    assert mark.prefix_end == 200


def test_collision_and_verify_mismatch_do_not_advance_watermark(tmp_path: Path) -> None:
    archive = SealedArchive(tmp_path / "evidence")
    _ok(archive.sync(_ok(_prefix())))
    collided = _refusal(archive.sync(_ok(_prefix(payload=b"different-bytes-under-same-id"))))
    assert collided.context["failure_id"] == "data.sealed.verify_mismatch"
    mark = _ok(archive.watermark(World.LIVE, "journal"))
    assert mark is not None
    assert mark.prefix_end == 100


def test_second_writer_and_loop_attachment_are_refused() -> None:
    writer = _refusal(refuse_second_writer(target="accumulator"))
    assert writer.context["failure_id"] == "data.sealed.second_writer"
    loop = _refusal(attach_sync_to_loop(CommandStreamLoop))
    assert loop.context["failure_id"] == "data.sealed.loop_blocking"
    blocked = _refusal(refuse_loop_blocking_sync(target="run_slice"))
    assert blocked.context["blocks_loop"] is False


def test_off_host_backup_infra_is_not_stood_up() -> None:
    refused = _refusal(refuse_off_host_backup_infra(provider="rclone"))
    assert refused.context["failure_id"] == "data.sealed.off_host_infra"
    assert refused.context["infra_tonight"] is False


def test_purge_requires_verified_sealed_and_off_host_copies(tmp_path: Path) -> None:
    missing_sealed = _refusal(evaluate_hot_room_purge(_candidate(sealed_verified=False)))
    assert missing_sealed.context["failure_id"] == "data.purge.missing_sealed"

    missing_off = _refusal(evaluate_hot_room_purge(_candidate(off_host_verified=False)))
    assert missing_off.context["failure_id"] == "data.purge.missing_off_host"

    early = _refusal(evaluate_hot_room_purge(_candidate(now_ns=_WINDOW_NS - 1)))
    assert early.context["failure_id"] == "data.purge.retention_window"

    flags = _ok(evaluate_hot_room_purge(_candidate()))
    assert flags.allowed is True

    archive = SealedArchive(tmp_path / "evidence")
    prefix = _ok(_prefix())
    _ok(archive.sync(prefix))
    allowed = _ok(
        evaluate_hot_room_purge(
            _candidate(sealed_verified=False),
            archive=archive,
        )
    )
    assert allowed.allowed is True
    assert prefix.prefix_id == allowed.prefix_id


def test_retention_law_keeps_evidence_journals_registry_cited_and_lineage() -> None:
    journal = _refusal(evaluate_sealed_deletion(_candidate(room_role="journal")))
    assert journal.context["failure_id"] == "data.purge.retained_forever"
    raw = _refusal(
        evaluate_sealed_deletion(_candidate(prefix_id="raw-1", room_role="immutable raw archive"))
    )
    assert raw.context["failure_id"] == "data.purge.retained_forever"
    cited = _refusal(
        evaluate_sealed_deletion(_candidate(prefix_id="view-1", room_role="processed", cited=True))
    )
    assert cited.context["failure_id"] == "data.purge.retained_forever"
    rebuildable = _ok(
        evaluate_sealed_deletion(_candidate(prefix_id="view-2", room_role="processed"))
    )
    assert rebuildable.allowed is True


def test_loop_and_sealed_archive_do_not_import_each_other() -> None:
    loop_imports: set[str] = set()
    for path in sorted((_SRC / "loop").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                loop_imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                loop_imports.add(node.module)
    assert not any("sealed_archive" in name for name in loop_imports)

    tree = ast.parse(
        (_SRC / "data" / "sealed_archive.py").read_text(encoding="utf-8"),
        filename="sealed_archive.py",
    )
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "qmn.loop" not in imported
    assert "qmn.loop.driver" not in imported
    assert "qmn.loop.accumulator" not in imported
    assert not any(name.split(".", 1)[0] in _BANNED_INFRA for name in imported)
