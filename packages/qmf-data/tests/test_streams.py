"""Tier-1 tests for the shared stream helpers (writer token, segment, HeldStreams)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import WriterId, is_ok, is_refusal
from qmf.data.store.streams import HeldStreams, safe_segment, writer_token


def _writer(machine: str = "node-a", boot: str = "boot-1") -> WriterId:
    built = WriterId.try_create(machine, "role", "stream", boot)
    assert is_ok(built)
    return built.value


def test_writer_token_excludes_boot_epoch() -> None:
    first = _writer(boot="boot-1")
    restarted = _writer(boot="boot-2")
    assert writer_token(first) == writer_token(restarted)
    other = _writer(machine="node-b")
    assert writer_token(first) != writer_token(other)


def test_safe_segment_accepts_plain_token_and_refuses_traversal() -> None:
    assert is_ok(safe_segment("data-quality"))
    assert is_refusal(safe_segment("../escape"))
    assert is_refusal(safe_segment("a/b"))
    assert is_refusal(safe_segment(""))
    assert is_refusal(safe_segment(123))


def test_held_streams_acquire_and_second_writer(tmp_path: Path) -> None:
    held = HeldStreams(tmp_path / "streams")
    first = held.acquire("s", _writer())
    assert is_ok(first)
    same = held.acquire("s", _writer(boot="boot-2"))  # same writer identity, new boot
    assert is_ok(same)
    other = held.acquire("s", _writer(machine="node-b"))
    assert is_refusal(other)
    assert other.category.value == "policy rejection"


def test_held_streams_reader_none_when_absent(tmp_path: Path) -> None:
    held = HeldStreams(tmp_path / "streams")
    assert held.reader("never") is None
    assert is_ok(held.acquire("s", _writer()))
    assert held.reader("s") is not None
