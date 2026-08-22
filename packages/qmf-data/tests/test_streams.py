"""Tier-1 tests for the shared stream helpers (writer token, segment, HeldStreams)."""

from __future__ import annotations

from pathlib import Path

from qmf.core import WriterId, is_ok, is_refusal
from qmf.data.store.engines.jsonl import jsonl_opener
from qmf.data.store.streams import HeldStreams, hold_token, safe_segment, writer_token


def _writer(machine: str = "node-a", boot: str = "boot-1") -> WriterId:
    built = WriterId.try_create(machine, "role", "stream", boot)
    assert is_ok(built)
    return built.value


def _held(tmp_path: Path) -> HeldStreams:
    return HeldStreams(tmp_path / "streams", open_stream=jsonl_opener())


def test_writer_token_excludes_boot_epoch() -> None:
    first = _writer(boot="boot-1")
    restarted = _writer(boot="boot-2")
    assert writer_token(first) == writer_token(restarted)
    other = _writer(machine="node-b")
    assert writer_token(first) != writer_token(other)


def test_hold_token_is_injective_over_separator_bearing_parts() -> None:
    # M1: the old unescaped \x1f join let these two triples alias; the JSON encoding
    # keeps them distinct.
    assert hold_token("m", "role\x1fA", "s") != hold_token("m", "role", "A\x1fs")
    assert hold_token("m", "r", "s") != hold_token("m", "r", "s2")


def test_safe_segment_accepts_plain_token_and_refuses_traversal() -> None:
    assert is_ok(safe_segment("data-quality"))
    assert is_refusal(safe_segment("../escape"))
    assert is_refusal(safe_segment("a/b"))
    assert is_refusal(safe_segment(""))
    assert is_refusal(safe_segment(123))


def test_held_streams_acquire_and_second_writer(tmp_path: Path) -> None:
    held = _held(tmp_path)
    first = held.acquire("s", _writer())
    assert is_ok(first)
    same = held.acquire("s", _writer(boot="boot-2"))  # same writer identity, new boot
    assert is_ok(same)
    other = held.acquire("s", _writer(machine="node-b"))
    assert is_refusal(other)
    assert other.category.value == "policy rejection"


def test_held_streams_reader_none_when_absent(tmp_path: Path) -> None:
    held = _held(tmp_path)
    assert held.reader("never") is None
    assert is_ok(held.acquire("s", _writer()))
    assert held.reader("s") is not None


def test_held_streams_case_folds_to_one_handle(tmp_path: Path) -> None:
    # H2: two casings of one name must be one cache entry (one physical directory).
    held = _held(tmp_path)
    first = held.acquire("Orders", _writer())
    assert is_ok(first)
    same = held.acquire("orders", _writer())
    assert is_ok(same)
    assert first.value is same.value  # the SAME live handle, not a second one


def test_hold_token_names_the_acquired_stream_not_the_writer_stream(tmp_path: Path) -> None:
    # M2: a writer whose own .stream is "stream" that acquires "alpha" and "beta" gets
    # distinct hold tokens naming each acquired stream, not one shared token.
    held = _held(tmp_path)
    assert is_ok(held.acquire("alpha", _writer()))
    assert is_ok(held.acquire("beta", _writer()))
    alpha_lock = (tmp_path / "streams" / "alpha" / ".writer").read_text(encoding="utf-8")
    beta_lock = (tmp_path / "streams" / "beta" / ".writer").read_text(encoding="utf-8")
    assert alpha_lock != beta_lock
    assert "alpha" in alpha_lock
    assert "beta" in beta_lock
