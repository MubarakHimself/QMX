"""Tier-1 tests for the JSONL append-stream engine (AC3, AC4; DEC-0113, DEC-0114)."""

from __future__ import annotations

import hashlib
import threading
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


# --- H2: a torn trailing line (crash mid-write) is recovered, not fatal ------


def test_torn_trailing_line_is_quarantined_and_prefix_kept(tmp_path: Path) -> None:
    # A crash mid-write can leave the final line without its LF (fsync incomplete). WAL
    # tail handling: the committed prefix stays readable, the torn tail is quarantined to a
    # .torn sidecar, and the whole stream is never made unreadable forever (H2).
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    committed = _canon({"n": 1}) + b"\n" + _canon({"n": 2}) + b"\n"
    torn = _canon({"n": 3})  # the interrupted write: no trailing LF
    (stream_dir / "000000.jsonl").write_bytes(committed + torn)

    reader = JsonlAppendStream(stream_dir, writer_token="<reader>")
    reader.rebuild_index()  # must NOT raise
    assert reader.read_all() == [_canon({"n": 1}), _canon({"n": 2})]
    assert reader.record_count == 2
    # the torn bytes are preserved for evidence and the data file truncated to the prefix
    assert (stream_dir / "000000.jsonl.torn").read_bytes() == torn
    assert (stream_dir / "000000.jsonl").read_bytes() == committed


def test_append_resumes_after_torn_tail(tmp_path: Path) -> None:
    # After the torn tail is quarantined on acquire, a writer appends cleanly onto the
    # durable committed prefix, and the new line reads back with no corruption.
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    (stream_dir / "000000.jsonl").write_bytes(_canon({"n": 1}) + b"\n" + _canon({"n": 2}))
    writer = JsonlAppendStream(stream_dir, writer_token="w")
    assert is_ok(writer.acquire())  # rebuild + quarantine the torn tail
    fresh = _canon({"n": 9})
    writer.append(fresh)
    reader = JsonlAppendStream(stream_dir, writer_token="<reader>")
    reader.rebuild_index()
    assert reader.read_all() == [_canon({"n": 1}), fresh]


def test_torn_line_in_non_tail_file_is_refused(tmp_path: Path) -> None:
    # A torn (no-LF) line in an EARLIER rotation file is real corruption, not a crash tail:
    # a rotation file is only left behind once complete, so a missing LF there is a refusal.
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    (stream_dir / "000000.jsonl").write_bytes(_canon({"n": 1}) + b"\n" + _canon({"n": 2}))
    (stream_dir / "000001.jsonl").write_bytes(_canon({"n": 3}) + b"\n")
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


# --- H1: the acquire lock is atomic (O_EXCL), never TOCTOU -------------------


def _race_one_trial(stream_dir: Path) -> int:
    """Two distinct writers race to acquire ``stream_dir``; return how many won."""
    barrier = threading.Barrier(2)
    guard = threading.Lock()
    oks: list[str] = []

    def run(token: str) -> None:
        engine = JsonlAppendStream(stream_dir, writer_token=token)
        barrier.wait()
        result = engine.acquire()
        if is_ok(result):
            with guard:
                oks.append(token)

    threads = [threading.Thread(target=run, args=(name,)) for name in ("writer-1", "writer-2")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return len(oks)


def test_racing_distinct_writers_never_both_acquire(tmp_path: Path) -> None:
    """H1: two distinct writers racing to acquire a fresh stream — exactly one wins.

    The old ``exists()``-then-``write_text`` acquire let both threads pass the check
    and both stamp the lock; the atomic ``O_CREAT | O_EXCL`` create makes exactly one
    create succeed. Repeated trials keep this deterministic in outcome regardless of
    timing.
    """
    for trial in range(120):
        winners = _race_one_trial(tmp_path / f"s{trial}")
        assert winners == 1, f"trial {trial}: {winners} writers acquired one fresh stream"


# --- H3: a corrupt (non-JSON) line is store corruption, never a decode leak --


def test_rebuild_raises_on_corrupt_non_json_line(tmp_path: Path) -> None:
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    (stream_dir / "000000.jsonl").write_bytes(b'{"n":1}\nthis is not json\n')
    reader = JsonlAppendStream(stream_dir, writer_token="<reader>")
    with pytest.raises(StoreEngineError):
        reader.rebuild_index()


# --- L4: a physically duplicated line is deduped, never read twice -----------


def test_duplicate_disk_line_is_deduped_on_rebuild(tmp_path: Path) -> None:
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    line = _canon({"n": 1}) + b"\n"
    (stream_dir / "000000.jsonl").write_bytes(line + line)  # the same line twice
    reader = JsonlAppendStream(stream_dir, writer_token="<reader>")
    reader.rebuild_index()
    assert reader.record_count == 1
    assert reader.read_all() == [line[:-1]]


# --- M6: hold discipline — release, and reader/backup handles cannot write ---


def test_release_frees_the_lock_for_a_new_writer(tmp_path: Path) -> None:
    first = JsonlAppendStream(tmp_path / "s", writer_token="writer-a")
    assert is_ok(first.acquire())
    first.release()
    assert first.held is False
    assert not (tmp_path / "s" / ".writer").exists()
    # A different writer may now take the freed stream.
    second = JsonlAppendStream(tmp_path / "s", writer_token="writer-b")
    assert is_ok(second.acquire())


def test_release_only_removes_its_own_lock(tmp_path: Path) -> None:
    holder = JsonlAppendStream(tmp_path / "s", writer_token="writer-a")
    assert is_ok(holder.acquire())
    # A reader handle (never acquired) must not be able to unlock another writer.
    reader = JsonlAppendStream(tmp_path / "s", writer_token="<reader>")
    reader.release()
    assert (tmp_path / "s" / ".writer").read_text(encoding="utf-8") == "writer-a"


def test_append_without_hold_raises(tmp_path: Path) -> None:
    reader = JsonlAppendStream(tmp_path / "s", writer_token="<reader>")
    with pytest.raises(StoreEngineError):
        reader.append(_canon({"n": 1}))


# --- symlink-safe I/O: a stream file is a regular, in-root, non-symlink file only ----


def _try_symlink(link: Path, target: Path) -> None:
    """Create a symlink or skip the test where the platform forbids it (Windows dev)."""
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this platform")


def test_find_refuses_a_vanished_rotation_file(tmp_path: Path) -> None:
    # The read guard requires a regular in-root file: if the indexed rotation file is gone
    # (deleted or swapped for a non-file), find refuses rather than opening a stray path.
    stream = _stream(tmp_path)
    canonical = _canon({"n": 1})
    stream.append(canonical)
    digest = hashlib.sha256(canonical).hexdigest()
    (tmp_path / "s" / "000000.jsonl").unlink()
    with pytest.raises(StoreEngineError):
        stream.find(digest)


def test_scan_refuses_an_oversize_rotation_file(tmp_path: Path) -> None:
    # A whole-file scan refuses above the size cap rather than reading unbounded bytes.
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    (stream_dir / "000000.jsonl").write_bytes(_canon({"n": 1}) + b"\n")
    reader = JsonlAppendStream(stream_dir, writer_token="<reader>", max_scan_bytes=1)
    with pytest.raises(StoreEngineError):
        reader.rebuild_index()


def test_rebuild_refuses_a_symlinked_rotation_file(tmp_path: Path) -> None:
    # A rotation file that is a symlink could redirect the read off the evidence tree; the
    # scan refuses it rather than following the link.
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    outside = tmp_path / "outside.jsonl"
    outside.write_bytes(_canon({"n": 1}) + b"\n")
    _try_symlink(stream_dir / "000000.jsonl", outside)
    reader = JsonlAppendStream(stream_dir, writer_token="<reader>")
    with pytest.raises(StoreEngineError):
        reader.rebuild_index()


def test_quarantine_refuses_a_symlinked_torn_sidecar(tmp_path: Path) -> None:
    # A torn tail triggers quarantine to a .torn sidecar; a symlink pre-planted there must
    # not be followed (a symlink-following write could clobber another file).
    stream_dir = tmp_path / "s"
    stream_dir.mkdir(parents=True)
    (stream_dir / "000000.jsonl").write_bytes(_canon({"n": 1}) + b"\n" + _canon({"n": 2}))
    outside = tmp_path / "outside-target.txt"
    outside.write_text("do not clobber", encoding="utf-8")
    _try_symlink(stream_dir / "000000.jsonl.torn", outside)
    reader = JsonlAppendStream(stream_dir, writer_token="<reader>")
    with pytest.raises(StoreEngineError):
        reader.rebuild_index()
    assert outside.read_text(encoding="utf-8") == "do not clobber"
