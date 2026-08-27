"""Epic 3 — Story 3.1: dependency-free store seam over swappable engines (FR-016 / CT-11).

Independent tests authored from Story 3.1 AC1-AC5 and PLAN Section 4 (3.1-U1..U6, P1, P2,
C1, C2, I1, I2). Refusal assertions check the CT-04 category, never a message string.
Source is read-only evidence; a failing assertion is a FINDING.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qmf.core import World, WriteOutcome, is_ok
from qmf.data.store import AppendStore, EvidenceStore, RegistryRoom
from qmf.data.store.engines import StoreEngineError
from qmf.data.store.rooms import EVIDENCE_BEARING_ROLES, ROOM_ROLE_VALUES, RoomRole

import _epic3_helpers as H

_ROWS = [{"t": 1, "px": 100}]


# --- fault-injection engines (alternate impls behind the owned contracts) ----


class _RaisingColumnar:
    """A ColumnarEngine whose every physical op raises the normalized StoreEngineError."""

    def __init__(self, *, retryable: bool = True) -> None:
        self._retryable = retryable

    def write(self, key: str, rows: Sequence[Mapping[str, object]], canonical: bytes, /) -> None:
        raise StoreEngineError("disk full", engine="parquet", retryable=self._retryable, detail={"key": key})

    def read(self, key: str, /) -> list[dict[str, object]]:
        raise StoreEngineError("truncated", engine="parquet", retryable=self._retryable, detail={"key": key})

    def read_canonical(self, key: str, /) -> bytes | None:
        return None

    def has(self, key: str, /) -> bool:
        return True

    def stored_keys(self) -> list[str]:
        return []


class _RaisingAnalytics:
    def materialize(self, key: str, rows: Sequence[Mapping[str, object]], canonical: bytes, /) -> None:
        raise StoreEngineError("locked", engine="duckdb", detail={"key": key})

    def query(self, key: str, /) -> list[dict[str, object]]:
        raise StoreEngineError("corrupt", engine="duckdb", retryable=False, detail={"key": key})

    def read_canonical(self, key: str, /) -> bytes | None:
        return None

    def drop(self, key: str, /) -> None:  # pragma: no cover
        raise StoreEngineError("drop failed", engine="duckdb")

    def has(self, key: str, /) -> bool:
        return True

    def engine_major(self) -> str:
        return "duckdb-0"


def _raising_append_store(*, retryable: bool = True) -> AppendStore:
    return AppendStore(
        World.LIVE, raw_engine=_RaisingColumnar(retryable=retryable), view_engine=_RaisingAnalytics()
    )


# --- 3.1-U1 (L1): each artifact class routes to exactly one ratified engine ---


def test_3_1_u1_engine_routing_and_room_roles(tmp_path: Path) -> None:
    """AC1: raw->Parquet, view->DuckDB, records->SQLite, journal/lineage->JSONL; 7 roles."""
    store = H.make_store(tmp_path)
    ws = H.unwrap(store.for_world(World.LIVE))

    raw = H.unwrap(ws.append_store.append_raw(_ROWS))
    assert raw.engine == "parquet"
    assert raw.room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE

    view = H.unwrap(
        ws.append_store.materialize_view(
            _ROWS, rebuild_calendar_identity="forex-17NY:v3", rebuild_tzdata_version="2025a"
        )
    )
    assert view.engine == "duckdb"
    assert view.room_role is RoomRole.PROCESSED

    rec = H.unwrap(ws.registry_room.put_record({"a": 1}, kind="thing", format_version=1))
    assert rec.engine == "sqlite"
    assert rec.room_role is RoomRole.REGISTRY_ROOM

    jr = H.unwrap(
        ws.journal.append("s1", H.writer(), {"event_type": "data quality", "n": 1})
    )
    assert jr.engine == "jsonl"
    assert jr.room_role is RoomRole.JOURNAL

    # The room-role vocabulary is exactly the ratified seven.
    assert len(ROOM_ROLE_VALUES) == 7
    assert set(ROOM_ROLE_VALUES) == {r.value for r in RoomRole}


# --- 3.1-U2 / 3.1-U3 (L1): idempotent re-write vs true collision --------------


def test_3_1_u2_byte_identical_rewrite_is_idempotent(tmp_path: Path) -> None:
    """AC2: a byte-identical re-write under an existing fp1 is accepted silently."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    first = H.unwrap(ws.append_store.append_raw(_ROWS))
    assert first.outcome is WriteOutcome.STORED
    second = H.unwrap(ws.append_store.append_raw(list(_ROWS)))
    assert second.outcome is WriteOutcome.IDEMPOTENT
    assert second.fingerprint.value == first.fingerprint.value


def test_3_1_u3_true_collision_refused_and_original_unchanged(tmp_path: Path) -> None:
    """AC2/FM-7: same fp1 presented for differing bytes is refused; original never overwritten.

    A *presented* fingerprint that does not match the presented bytes is the store's guard
    against admitting bytes under the wrong fp1 — refused before anything is stored, so a
    false collision can never overwrite the genuine artifact.
    """
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    stored = H.unwrap(ws.append_store.append_raw(_ROWS))
    # Present the genuine fp1 for a DIFFERENT payload -> refused, nothing stored.
    refusal = ws.append_store.append_raw(
        [{"t": 2, "px": 999}], presented_fingerprint=stored.fingerprint
    )
    H.assert_refusal(refusal, "invalid input")
    # The original bytes read back unchanged.
    rows = H.unwrap(ws.append_store.read_raw(stored.fingerprint, for_world=World.LIVE))
    assert rows == _ROWS


# --- 3.1-U4 (L1): JSONL append is one fp1-canonical object per line -----------


def test_3_1_u4_jsonl_one_object_per_line(tmp_path: Path) -> None:
    """AC3: journal/lineage streams write exactly one canonical JSON object per LF line."""
    store = H.make_store(tmp_path, rotation_bytes=10_000)
    ws = H.unwrap(store.for_world(World.LIVE))
    for i in range(3):
        H.unwrap(ws.journal.append("s1", H.writer(), {"event_type": "data quality", "n": i}))
    # Locate the physical stream file(s) and assert one JSON object per LF-terminated line.
    import json

    journal_files = sorted((store.root).rglob("*.jsonl"))
    assert journal_files, "expected a physical JSONL stream file"
    total_lines = 0
    for f in journal_files:
        data = f.read_bytes()
        if not data:
            continue
        assert data.endswith(b"\n"), "each JSONL record is LF-terminated"
        for line in data.splitlines():
            obj = json.loads(line)  # each line parses as exactly one object
            assert isinstance(obj, dict)
            total_lines += 1
    assert total_lines == 3


# --- 3.1-U5 (L1): one writer per stream --------------------------------------


def test_3_1_u5_second_writer_refused(tmp_path: Path) -> None:
    """AC3/DEC-0113: a second distinct WriterId reaching for a held stream does not proceed."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    w1 = H.writer(machine="node-a", role="data", stream="s1", boot="boot-1")
    w2 = H.writer(machine="node-b", role="data", stream="s1", boot="boot-2")
    H.unwrap(ws.journal.append("stream", w1, {"event_type": "data quality", "n": 1}))
    refusal = ws.journal.append("stream", w2, {"event_type": "data quality", "n": 2})
    H.assert_refusal(refusal, "policy rejection")


# --- 3.1-U6 (L1): every store fault -> returned storage-failure refusal --------


@pytest.mark.parametrize("op", ["write", "read", "view"])
def test_3_1_u6_engine_faults_returned_as_storage_failure(op: str) -> None:
    """AC4/FM-6: an engine fault is a RETURNED `storage failure` refusal, never raised, never success."""
    boundary = _raising_append_store()
    if op == "write":
        result = boundary.append_raw(_ROWS)
    elif op == "read":
        result = boundary.read_raw(H.fp("a"), for_world=World.LIVE)
    else:
        result = boundary.materialize_view(
            _ROWS, rebuild_calendar_identity="c", rebuild_tzdata_version="z"
        )
    H.assert_refusal(result, "storage failure")
    assert not is_ok(result), "no persistence success is reported on failure"


# --- 3.1-P1 (L2 property): idempotent iff bytes identical; mutation never mutates store


@settings(max_examples=60, deadline=None)
@given(
    rows=st.lists(
        st.fixed_dictionaries({"t": st.integers(-1_000, 1_000), "px": st.integers(0, 1_000_000)}),
        min_size=1,
        max_size=4,
    ),
    tweak=st.integers(1, 9),
)
def test_3_1_p1_idempotent_iff_identical(tmp_path_factory: pytest.TempPathFactory, rows: list[dict], tweak: int) -> None:
    """AC2: a re-write is idempotent iff bytes are identical; a mutated re-write never mutates the store."""
    root = tmp_path_factory.mktemp("p1")
    ws = H.unwrap(H.make_store(root).for_world(World.LIVE))
    first = H.unwrap(ws.append_store.append_raw(rows))
    # identical re-write -> idempotent, same fp
    again = H.unwrap(ws.append_store.append_raw([dict(r) for r in rows]))
    assert again.outcome is WriteOutcome.IDEMPOTENT
    assert again.fingerprint.value == first.fingerprint.value
    # a genuinely different payload -> a DISTINCT fp1 artifact (never an overwrite of the first)
    mutated = [dict(rows[0], px=rows[0]["px"] + tweak), *rows[1:]]
    stored_mut = H.unwrap(ws.append_store.append_raw(mutated))
    assert stored_mut.fingerprint.value != first.fingerprint.value
    # the original still reads back byte-identical (never mutated by the second write)
    back = H.unwrap(ws.append_store.read_raw(first.fingerprint, for_world=World.LIVE))
    assert back == [dict(r) for r in rows]


# --- 3.1-P2 (L2 property, R-007): no store-lib exception escapes the seam ------


@settings(max_examples=40, deadline=None)
@given(retryable=st.booleans(), which=st.sampled_from(["write", "read"]))
def test_3_1_p2_no_engine_exception_escapes(retryable: bool, which: str) -> None:
    """R-007/AC4: across the fault matrix, every fault surfaces as a returned `storage failure`."""
    boundary = _raising_append_store(retryable=retryable)
    try:
        if which == "write":
            result = boundary.append_raw(_ROWS)
        else:
            result = boundary.read_raw(H.fp("b"), for_world=World.LIVE)
    except StoreEngineError as exc:  # pragma: no cover - a raised exception is the FINDING
        raise AssertionError(
            f"a store-library exception escaped the CT-11 boundary (R-007 breach): {exc!r}"
        ) from exc
    H.assert_refusal(result, "storage failure")
    # retryability is carried through from the engine's transient/permanent distinction
    assert result.retryability.value in ("yes", "no")


# --- 3.1-C1 (L3 contract): evidence round-trip + receipt enum/nullability ------


def test_3_1_c1_round_trip_and_receipt_shape(tmp_path: Path) -> None:
    """CT-11: raw round-trips semantically; receipt carries room_role/world/evidence/version."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    receipt = H.unwrap(ws.append_store.append_raw(_ROWS))
    # round-trip: rows read back equal to what was written
    back = H.unwrap(ws.append_store.read_raw(receipt.fingerprint, for_world=World.LIVE))
    assert back == _ROWS
    # receipt enum/nullability boundary
    assert receipt.world is World.LIVE
    assert receipt.is_evidence_bearing is True  # raw archive is evidence-bearing
    assert receipt.retained_forever is True
    assert receipt.format_version == 1  # format-version stamp present
    # a rebuildable view is NOT evidence-bearing and records its engine major
    view = H.unwrap(
        ws.append_store.materialize_view(
            _ROWS, rebuild_calendar_identity="forex-17NY:v3", rebuild_tzdata_version="2025a"
        )
    )
    assert view.is_evidence_bearing is False
    assert view.retained_forever is False
    assert view.engine_major is not None
    assert view.rebuild_calendar_identity == "forex-17NY:v3"
    assert view.rebuild_tzdata_version == "2025a"


def test_3_1_c1_evidence_bearing_roles_are_exactly_two() -> None:
    """CT-11: only the immutable raw archive and the journal are evidence-bearing."""
    assert EVIDENCE_BEARING_ROLES == frozenset({RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL})


# --- 3.1-C2 (L3 contract): invalid / refusal boundary -------------------------


def test_3_1_c2_empty_artifact_refused(tmp_path: Path) -> None:
    """CT-11: an empty evidence artifact (no rows) is an `invalid input` refusal, never stored."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    H.assert_refusal(ws.append_store.append_raw([]), "invalid input")
    H.assert_refusal(ws.append_store.materialize_view([], rebuild_calendar_identity="c", rebuild_tzdata_version="z"), "invalid input")


def test_3_1_c2_read_requires_declared_world_and_missing_is_stale(tmp_path: Path) -> None:
    """CT-11: a read must declare its world (M4); a well-formed key with no artifact is stale evidence (M5)."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    # missing for_world -> invalid input (a read must state its world)
    H.assert_refusal(ws.append_store.read_raw(H.fp("c"), for_world=None), "invalid input")
    # well-formed fp that names nothing -> stale evidence (not invalid input)
    H.assert_refusal(ws.append_store.read_raw(H.fp("d"), for_world=World.LIVE), "stale evidence")
    # a malformed fingerprint string -> invalid input
    H.assert_refusal(ws.append_store.read_raw("not-a-fingerprint", for_world=World.LIVE), "invalid input")


# --- 3.1-I1 (L4 integration): JSONL rotation + index rebuild recovers the stream


def test_3_1_i1_rotation_and_index_rebuild_recovers_full_stream(tmp_path: Path) -> None:
    """AC3: under a small rotation size the full append stream is recovered gaplessly from disk."""
    # A tiny rotation size forces multiple physical files; the locally-rebuilt index must
    # still recover every appended record in order.
    store = H.make_store(tmp_path, rotation_bytes=200)
    ws = H.unwrap(store.for_world(World.LIVE))
    w = H.writer(stream="rot")
    n = 40
    for i in range(n):
        H.unwrap(ws.journal.append("rotstream", w, {"event_type": "data quality", "seq": i}))
    # Re-open a fresh store over the same root (forces an index rebuild by scanning files).
    reopened = EvidenceStore(store.root, rotation_bytes=200)
    ws2 = H.unwrap(reopened.for_world(World.LIVE))
    rows = H.unwrap(ws2.journal.read_stream("rotstream", for_world=World.LIVE))
    assert len(rows) == n, "every appended record is recovered after rotation + index rebuild"
    assert [r["seq"] for r in rows] == list(range(n)), "records recovered in append order"
    # rotation actually occurred: more than one physical stream file exists
    files = sorted(store.root.rglob("*.jsonl"))
    assert len(files) >= 2, "a small rotation size must produce multiple rotated files"


# --- 3.1-I2 (L4 integration): registry-room persistence via the seam ----------


def test_3_1_i2_registry_room_append_only_records_and_lineage(tmp_path: Path) -> None:
    """AC5: registry records are fp1-keyed per-kind; lineage rides pinned JSONL, append-only, never rewritten."""
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    room: RegistryRoom = ws.registry_room
    rec = H.unwrap(room.put_record({"symbol": "EURUSD"}, kind="instrument", format_version=1))
    assert rec.room_role is RoomRole.REGISTRY_ROOM
    # a byte-identical re-put is idempotent (never a second physical write / never a rewrite)
    again = H.unwrap(room.put_record({"symbol": "EURUSD"}, kind="instrument", format_version=1))
    assert again.outcome is WriteOutcome.IDEMPOTENT
    assert again.fingerprint.value == rec.fingerprint.value
    # the same body under a different kind is a DISTINCT record (identity-by-default), never an alias
    other = H.unwrap(room.put_record({"symbol": "EURUSD"}, kind="other-kind", format_version=1))
    assert other.fingerprint.value != rec.fingerprint.value
    # lineage edges are append-only JSONL under one writer
    w = H.writer(role="registry", stream="lineage")
    edge = {"edge_type": "supersedes", "from_ref": H.fp("a").value, "to_ref": H.fp("b").value}
    e1 = H.unwrap(room.append_lineage_edge("lineage", w, edge))
    assert e1.engine == "jsonl"
    # idempotent re-append of the identical edge (append-only, never rewritten in place)
    e2 = H.unwrap(room.append_lineage_edge("lineage", w, dict(edge)))
    assert e2.outcome is WriteOutcome.IDEMPOTENT
