"""Tier-1 tests for the CT-09 registry-room boundary (AC1, AC2, AC5)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from qmf.core import World, WriterId, canonical_bytes, fingerprint, is_ok, is_refusal
from qmf.data.store import EvidenceStore, RegistryRoom, jsonl_opener
from qmf.data.store.engines.sqlite_meta import SqliteMetadataEngine

_RECORD = {"kind": "producer", "id": "sma-20"}


def _envelope(record: Mapping[str, object], *, kind: str, format_version: int) -> dict[str, object]:
    """The full stored record (H6): kind + format_version + body, fingerprinted whole."""
    return {"kind": kind, "format_version": format_version, "body": dict(record)}


def _writer() -> WriterId:
    built = WriterId.try_create("node-a", "registry", "lineage", "boot-1")
    assert is_ok(built)
    return built.value


def _registry(store: EvidenceStore) -> RegistryRoom:
    world = store.for_world(World.LIVE)
    assert is_ok(world)
    return world.value.registry_room


def test_put_record_stores_via_sqlite(store: EvidenceStore) -> None:
    room = _registry(store)
    result = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_ok(result)
    receipt = result.value
    assert receipt.engine == "sqlite"
    assert receipt.room_role.value == "registry room"
    assert receipt.is_evidence_bearing is True


def test_get_record_returns_canonical_bytes(store: EvidenceStore) -> None:
    room = _registry(store)
    receipt = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_ok(receipt)
    got = room.get_record(receipt.value.fingerprint.value, for_world=World.LIVE)
    assert is_ok(got)
    # The stored artifact is the FULL record (kind + format_version + body), H6.
    expected = canonical_bytes(_envelope(_RECORD, kind="producer", format_version=1))
    assert is_ok(expected)
    assert got.value == expected.value


def test_put_record_idempotent(store: EvidenceStore) -> None:
    room = _registry(store)
    first = room.put_record(_RECORD, kind="producer", format_version=1)
    second = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_ok(first)
    assert is_ok(second)
    assert second.value.outcome.value == "idempotent"


def test_get_missing_record_is_stale_evidence(store: EvidenceStore) -> None:
    room = _registry(store)
    fp = fingerprint({"absent": True})
    assert is_ok(fp)
    # M5: a well-formed fingerprint that names nothing is a not-found (stale evidence)
    # refusal, never an invalid-input caller error.
    result = room.get_record(fp.value.value, for_world=World.LIVE)
    assert is_refusal(result)
    assert result.category.value == "stale evidence"


def test_put_record_invalid_kind_and_version(store: EvidenceStore) -> None:
    room = _registry(store)
    bad_kind = room.put_record(_RECORD, kind="", format_version=1)
    assert is_refusal(bad_kind)
    assert bad_kind.context.get("field") == "kind"
    bad_version = room.put_record(_RECORD, kind="producer", format_version=0)
    assert is_refusal(bad_version)
    assert bad_version.context.get("field") == "format_version"


def test_lineage_edge_appends_via_jsonl(store: EvidenceStore) -> None:
    room = _registry(store)
    edge = {"edge": "derived_from", "to": "x"}
    result = room.append_lineage_edge("lineage", _writer(), edge)
    assert is_ok(result)
    assert result.value.engine == "jsonl"
    read = room.read_lineage("lineage", for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == [edge]


def test_lineage_stream_names_enumerates_every_stream(store: EvidenceStore) -> None:
    room = _registry(store)
    # No stream written yet: an empty enumeration (never a failure), even before any dir exists.
    empty = room.lineage_stream_names(for_world=World.LIVE)
    assert is_ok(empty)
    assert empty.value == ()
    assert is_ok(room.append_lineage_edge("alpha", _writer(), {"edge": "a"}))
    assert is_ok(room.append_lineage_edge("beta", _writer(), {"edge": "b"}))
    names = room.lineage_stream_names(for_world=World.LIVE)
    assert is_ok(names)
    # A room-wide scan sees every stream, so a caller enforcing a room-wide invariant can read
    # each one rather than only a single named stream.
    assert set(names.value) == {"alpha", "beta"}


def test_lineage_stream_names_cross_world_refuses(store: EvidenceStore) -> None:
    room = _registry(store)
    assert is_ok(room.append_lineage_edge("alpha", _writer(), {"edge": "a"}))
    refused = room.lineage_stream_names(for_world=World.REPLAY)
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"


def test_cross_world_get_is_policy_rejection(store: EvidenceStore) -> None:
    room = _registry(store)
    receipt = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_ok(receipt)
    result = room.get_record(receipt.value.fingerprint.value, for_world=World.REPLAY)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_cross_world_read_lineage_is_policy_rejection(store: EvidenceStore) -> None:
    room = _registry(store)
    assert is_ok(room.append_lineage_edge("lineage", _writer(), {"edge": "a"}))
    result = room.read_lineage("lineage", for_world=World.REPLAY)
    assert is_refusal(result)
    assert result.category.value == "policy rejection"


def test_simulated_writes_are_policy_rejections(tmp_path: Path) -> None:
    room = RegistryRoom(
        World.SIMULATED,
        record_engine=SqliteMetadataEngine(tmp_path / "records.sqlite"),
        lineage_dir=tmp_path / "lineage",
        open_stream=jsonl_opener(),
    )
    rec = room.put_record(_RECORD, kind="producer", format_version=1)
    assert is_refusal(rec)
    assert rec.category.value == "policy rejection"
    edge = room.append_lineage_edge("lineage", _writer(), {"edge": "a"})
    assert is_refusal(edge)
    assert edge.category.value == "policy rejection"


# --- M2: put_identity_record keys on the presented identity, no wrapping ------

_IDENTITY: dict[str, object] = {"class": "x", "kind": "producer", "body": {"id": "sma-20"}}


def test_put_identity_record_keys_on_the_presented_identity(store: EvidenceStore) -> None:
    room = _registry(store)
    fp = fingerprint(_IDENTITY)
    assert is_ok(fp)
    receipt = room.put_identity_record(
        _IDENTITY, kind="producer", format_version=1, presented_fingerprint=fp.value
    )
    assert is_ok(receipt)
    # The storage key IS the fingerprint of the identity content — no wrapping envelope (M2).
    assert receipt.value.fingerprint == fp.value
    assert receipt.value.engine == "sqlite"
    got = room.get_record(fp.value.value, for_world=World.LIVE)
    assert is_ok(got)
    expected = canonical_bytes(_IDENTITY)
    assert is_ok(expected)
    assert got.value == expected.value


def test_put_identity_record_invalid_kind_and_version(store: EvidenceStore) -> None:
    room = _registry(store)
    assert is_refusal(room.put_identity_record(_IDENTITY, kind="", format_version=1))
    bad_version = room.put_identity_record(_IDENTITY, kind="producer", format_version=0)
    assert is_refusal(bad_version)
    assert bad_version.context.get("field") == "format_version"


def test_put_identity_record_simulated_is_policy_rejection(tmp_path: Path) -> None:
    room = RegistryRoom(
        World.SIMULATED,
        record_engine=SqliteMetadataEngine(tmp_path / "records.sqlite"),
        lineage_dir=tmp_path / "lineage",
        open_stream=jsonl_opener(),
    )
    refused = room.put_identity_record(_IDENTITY, kind="producer", format_version=1)
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"


# --- M5: the display-only occurrence sidecar, first-write-wins ---------------


def test_occurrence_sidecar_stores_reads_and_is_first_write_wins(store: EvidenceStore) -> None:
    room = _registry(store)
    occurrence: dict[str, object] = {"writer": {"machine": "node-a"}, "sequence": 7}
    receipt = room.put_identity_record(
        _IDENTITY, kind="producer", format_version=1, occurrence=occurrence
    )
    assert is_ok(receipt)
    read = room.get_record_occurrence(receipt.value.fingerprint, for_world=World.LIVE)
    assert is_ok(read)
    assert read.value == occurrence
    # A second put of the same identity with a different occurrence keeps the FIRST (M5).
    again = room.put_identity_record(
        _IDENTITY,
        kind="producer",
        format_version=1,
        occurrence={"writer": {"machine": "node-b"}, "sequence": 99},
    )
    assert is_ok(again)
    assert again.value.outcome.value == "idempotent"
    read_again = room.get_record_occurrence(receipt.value.fingerprint, for_world=World.LIVE)
    assert is_ok(read_again)
    assert read_again.value == occurrence


def test_get_record_occurrence_absent_is_none(store: EvidenceStore) -> None:
    room = _registry(store)
    receipt = room.put_identity_record(_IDENTITY, kind="producer", format_version=1)
    assert is_ok(receipt)
    read = room.get_record_occurrence(receipt.value.fingerprint, for_world=World.LIVE)
    assert is_ok(read)
    assert read.value is None


def test_get_record_occurrence_cross_world_refuses(store: EvidenceStore) -> None:
    room = _registry(store)
    receipt = room.put_identity_record(
        _IDENTITY, kind="producer", format_version=1, occurrence={"sequence": 1}
    )
    assert is_ok(receipt)
    refused = room.get_record_occurrence(receipt.value.fingerprint, for_world=World.REPLAY)
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"


class _PlainMetadata:
    """A MetadataEngine WITHOUT the OccurrenceSink capability (occurrence is optional)."""

    def __init__(self) -> None:
        self._rows: dict[str, bytes] = {}

    def put(self, digest: str, canonical: bytes, /, *, kind: str, format_version: int) -> None:
        self._rows[digest] = canonical

    def get(self, digest: str, /) -> bytes | None:
        return self._rows.get(digest)

    def meta(self, digest: str, /) -> Mapping[str, object] | None:  # pragma: no cover - unused
        return None

    def digests(self) -> list[str]:  # pragma: no cover - unused
        return sorted(self._rows)


def test_identity_record_without_occurrence_capability_skips_the_sidecar(tmp_path: Path) -> None:
    # The occurrence sidecar is an optional capability: an engine that is not an OccurrenceSink
    # simply carries no occurrence facts, and the record still persists.
    room = RegistryRoom(
        World.LIVE,
        record_engine=_PlainMetadata(),
        lineage_dir=tmp_path / "lineage",
        open_stream=jsonl_opener(),
    )
    receipt = room.put_identity_record(
        _IDENTITY, kind="producer", format_version=1, occurrence={"sequence": 1}
    )
    assert is_ok(receipt)
    read = room.get_record_occurrence(receipt.value.fingerprint, for_world=World.LIVE)
    assert is_ok(read)
    assert read.value is None
