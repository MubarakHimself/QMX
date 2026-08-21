"""Tier-1 tests for the JSONL append-stream engine (AC3, AC4; DEC-0113, DEC-0114)."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

import pytest
from qmf.core import canonical_bytes, is_ok, is_refusal
from qmf.data.store.engines import StoreEngineError
from qmf.data.store.engines.jsonl import JsonlAppendStream


def _canon(obj: Mapping[str, object]) -> bytes:
    result = canonical_bytes(obj)
    assert is_ok(result)
    return result.value


def _stream(tmp_path: Path, *, token: str = "m|r|s", rotation: int = 8 * 1024) -> JsonlAppendStream:
    stream = JsonlAppendStream(tmp_path / "s", writer_token=token, rotation_bytes=rotation)
    assert is_ok(stream.acquire())
    return stream


def test_append_writes_one_lf_terminated_object_per_line(tmp_path: Path) -> None:
    stream = _stream(tmp_path)
    a = _canon({"n": 1})
    b = _canon({"n": 2})
    stream.append(a)
    stream.append(b)
    data = (tmp_path / "s" / "000000.jsonl").read_bytes()
    assert data == a + b"\n" + b + b"\n"


def test_append_assigns_gapless_increasing_sequence(tmp_path: Path) -> None:
    stream = _stream(tmp_path)
    locations = [stream.append(_canon({"n": i})) for i in range(4)]
    assert [loc.sequence for loc in locations] == [0, 1, 2, 3]


def test_digest_matches_fp1_digest(tmp_path: Path) -> None:
    stream = _stream(tmp_path)
    obj = {"event": "x"}
    canonical = _canon(obj)
    stream.append(canonical)
    digest = hashlib.sha256(canonical).hexdigest()
    assert stream.find(digest) == canonical


def test_rotation_rolls_under_monotonic_ordinal(tmp_path: Path) -> None:
    stream = _stream(tmp_path, rotation=1)  # every line after the first rotates
    for i in range(3):
        stream.append(_canon({"n": i}))
    assert stream.current_ordinal == 2
    names = sorted(p.name for p in (tmp_path / "s").glob("*.jsonl"))
    assert names == ["000000.jsonl", "000001.jsonl", "000002.jsonl"]


def test_rebuild_index_reconstructs_from_files(tmp_path: Path) -> None:
    stream = _stream(tmp_path, rotation=1)
    payloads = [_canon({"n": i}) for i in range(3)]
    for payload in payloads:
        stream.append(payload)
    reader = JsonlAppendStream(tmp_path / "s", writer_token="<reader>")
    reader.rebuild_index()
    assert reader.read_all() == payloads
    assert reader.record_count == 3


def test_find_returns_none_for_absent_digest(tmp_path: Path) -> None:
    stream = _stream(tmp_path)
    assert stream.find("0" * 64) is None


def test_location_of_reports_sequence(tmp_path: Path) -> None:
    stream = _stream(tmp_path)
    canonical = _canon({"n": 7})
    loc = stream.append(canonical)
    digest = hashlib.sha256(canonical).hexdigest()
    assert stream.location_of(digest) == loc
    assert stream.location_of("f" * 64) is None


def test_second_distinct_writer_is_refused(tmp_path: Path) -> None:
    first = JsonlAppendStream(tmp_path / "s", writer_token="writer-a")
    assert is_ok(first.acquire())
    second = JsonlAppendStream(tmp_path / "s", writer_token="writer-b")
    refusal = second.acquire()
    assert is_refusal(refusal)
    assert refusal.category.value == "policy rejection"


def test_same_writer_reacquires(tmp_path: Path) -> None:
    first = JsonlAppendStream(tmp_path / "s", writer_token="writer-a")
    assert is_ok(first.acquire())
    again = JsonlAppendStream(tmp_path / "s", writer_token="writer-a")
    assert is_ok(again.acquire())


def test_held_flag(tmp_path: Path) -> None:
    stream = JsonlAppendStream(tmp_path / "s", writer_token="w")
    assert stream.held is False
    stream.acquire()
    assert stream.held is True


def test_rebuild_raises_on_partial_trailing_line(tmp_path: Path) -> None:
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    (stream_dir / "000000.jsonl").write_bytes(b'{"n":1}\n{"n":2}')  # no trailing LF
    reader = JsonlAppendStream(stream_dir, writer_token="<reader>")
    with pytest.raises(StoreEngineError):
        reader.rebuild_index()


def test_find_raises_on_truncated_file(tmp_path: Path) -> None:
    stream = _stream(tmp_path)
    canonical = _canon({"n": 1})
    stream.append(canonical)
    digest = hashlib.sha256(canonical).hexdigest()
    # Truncate the file below the length the index recorded.
    (tmp_path / "s" / "000000.jsonl").write_bytes(b"{")
    with pytest.raises(StoreEngineError):
        stream.find(digest)
