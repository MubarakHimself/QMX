"""Story S1 — contained, no-follow orchestrator file I/O."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

import pytest
from qmb.config import ResolvedRunConfig
from qmb.orchestrator import watch as watch_mod
from qmb.orchestrator.paths import (
    MAX_BYTES,
    append_bytes_no_follow,
    open_write_handle,
    read_contained_bytes,
    read_contained_text,
    write_bytes_exclusive_no_follow,
)
from qmb.runloop import STREAM_SET_KEY, SliceObservation
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _linux_vmhwm(status: Path, pid: int) -> Result[int]:
    result: Result[int] = watch_mod._linux_vmhwm(status, pid)  # pyright: ignore[reportPrivateUsage]
    return result


def _try_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip where the platform forbids it (Windows dev)."""
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this platform")


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    first = _ok(SliceObservation.try_create("eurusd", _instant(), True))
    second = _ok(SliceObservation.try_create("eurusd", _instant(_NS + 1), True))
    return ((first,), (second,))


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "orch-paths", "tag": tag}))
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def test_exclusive_write_and_contained_read_round_trip(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    path = root / "payload.json"
    payload = b'{"ok":true}'
    _ok(write_bytes_exclusive_no_follow(path, payload, contain_within=root))
    assert path.is_file()
    assert not path.is_symlink()
    assert _ok(read_contained_bytes(path, contain_within=root)) == payload
    assert _ok(read_contained_text(path, contain_within=root)) == '{"ok":true}'


def test_read_refuses_a_path_that_escapes_the_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("nope", encoding="utf-8")
    refused = read_contained_bytes(root / ".." / "secret.txt", contain_within=root)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert outside.read_text(encoding="utf-8") == "nope"


def test_write_refuses_a_path_that_escapes_the_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("keep", encoding="utf-8")
    refused = write_bytes_exclusive_no_follow(
        root / ".." / "secret.txt", b"clobber", contain_within=root
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert outside.read_text(encoding="utf-8") == "keep"


def test_read_refuses_an_oversize_file(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    path = root / "big.bin"
    path.write_bytes(b"x" * 32)
    refused = read_contained_bytes(path, contain_within=root, max_bytes=8)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert refused.context.get("max_bytes") == 8


def test_read_refuses_a_symlinked_file(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = root / "payload.json"
    _try_symlink(link, outside)
    refused = read_contained_bytes(link, contain_within=root)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert outside.read_text(encoding="utf-8") == "secret"


def test_write_refuses_a_symlinked_target(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")
    link = root / "payload.json"
    _try_symlink(link, outside)
    refused = write_bytes_exclusive_no_follow(link, b"clobber", contain_within=root)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert outside.read_text(encoding="utf-8") == "keep"


def test_write_refuses_a_target_detected_as_a_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "payload.json"
    real_is_symlink = Path.is_symlink

    def detects_the_target_as_a_link(self: Path) -> bool:
        return True if self == target else real_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", detects_the_target_as_a_link)
    refused = write_bytes_exclusive_no_follow(target, b"{}", contain_within=root)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert not target.exists()


def test_append_refuses_a_symlinked_fragment(tmp_path: Path) -> None:
    root = tmp_path / "ledger"
    root.mkdir()
    outside = tmp_path / "outside.jsonl"
    outside.write_bytes(b"keep\n")
    fragment = root / "ledger.jsonl"
    _try_symlink(fragment, outside)
    refused = append_bytes_no_follow(fragment, b"line\n", contain_within=root)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert outside.read_bytes() == b"keep\n"


def test_append_then_read_a_contained_fragment(tmp_path: Path) -> None:
    root = tmp_path / "ledger"
    root.mkdir()
    fragment = root / "ledger.jsonl"
    _ok(append_bytes_no_follow(fragment, b'{"n":1}\n', contain_within=root))
    _ok(append_bytes_no_follow(fragment, b'{"n":2}\n', contain_within=root))
    raw = _ok(read_contained_bytes(fragment, contain_within=root))
    assert raw == b'{"n":1}\n{"n":2}\n'


def test_log_sink_refuses_a_symlinked_log_file(tmp_path: Path) -> None:
    path = tmp_path / qmb.LOG_FILENAME
    outside = tmp_path / "outside.log"
    outside.write_bytes(b"keep\n")
    _try_symlink(path, outside)
    refused = qmb.LogSink.try_create(
        path,
        run_id="fp1:sha256:" + "ab" * 32,
        correlation_id="cd" * 16,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert outside.read_bytes() == b"keep\n"


def test_log_sink_exclusive_create_then_append(tmp_path: Path) -> None:
    path = tmp_path / qmb.LOG_FILENAME
    first = _ok(open_write_handle(path, contain_within=tmp_path, append=False, field="log_path"))
    first.write(b'{"event":"spawned"}\n')
    first.flush()
    first.close()
    second = _ok(open_write_handle(path, contain_within=tmp_path, append=True, field="log_path"))
    second.write(b'{"event":"run-started"}\n')
    second.flush()
    second.close()
    raw = _ok(read_contained_bytes(path, contain_within=tmp_path, max_bytes=MAX_BYTES))
    assert raw.split(b"\n")[0] == b'{"event":"spawned"}'
    assert b"run-started" in raw


def test_linux_vmhwm_reads_a_contained_regular_status(tmp_path: Path) -> None:
    status = tmp_path / "status"
    status.write_text("Name:\tpython\nVmHWM:\t2048 kB\n", encoding="utf-8")
    assert _ok(_linux_vmhwm(status, pid=1)) == 2048 * 1024


def test_linux_vmhwm_refuses_a_symlinked_status(tmp_path: Path) -> None:
    outside = tmp_path / "outside.status"
    outside.write_text("VmHWM:\t9999 kB\n", encoding="utf-8")
    status = tmp_path / "status"
    _try_symlink(status, outside)
    refused = _linux_vmhwm(status, pid=1)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert outside.read_text(encoding="utf-8") == "VmHWM:\t9999 kB\n"


def test_worker_main_refuses_a_symlinked_payload(tmp_path: Path) -> None:
    from qmb.orchestrator import worker_main

    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    _try_symlink(tmp_path / qmb.PAYLOAD_NAME, outside)
    assert worker_main([str(tmp_path)]) == 0
    envelope = json.loads((tmp_path / qmb.RESULT_NAME).read_text(encoding="utf-8"))
    assert envelope["ok"] is False
    assert envelope["category"] == RefusalCategory.STORAGE_FAILURE.value
    assert outside.read_text(encoding="utf-8") == "{}"


def test_ledger_append_refuses_a_symlinked_fragment(tmp_path: Path) -> None:
    config = _config(tag="symlink-ledger")
    sink = _ok(
        qmb.LedgerSink.try_create(
            tmp_path / "ledger",
            machine="test-machine",
            worker_slot=0,
            boot_epoch_id="boot-1",
        )
    )
    writer = _ok(sink.writer_id(qmb.ROLE_CONFIRMATION))
    path = _ok(qmb.fragment_path(sink.root, writer, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION))
    path.parent.mkdir(parents=True)
    outside = tmp_path / "outside.jsonl"
    outside.write_bytes(b"keep\n")
    _try_symlink(path, outside)
    live = _ok(qmb.start_run(config=config, slices=_slices(), output_root=tmp_path))
    refused = qmb.finish_run(live, config=config, ledger=sink, role=qmb.ROLE_CONFIRMATION)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert outside.read_bytes() == b"keep\n"
