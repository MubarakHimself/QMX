"""Tests for the CT-10 source-observation boundary over the store seam (Story 3.2).

Exercises admission, verbatim round-trip through the immutable raw archive, the
append-only correction rule, and the world/refusal gates against a real
filesystem-backed :class:`EvidenceStore`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from qmf.core import RefusalCategory, World, WriterId, is_ok, is_refusal
from qmf.data import (
    EvidenceStore,
    ForeignMoney,
    ForeignTimestamp,
    SourceObservation,
    SourceObservationBoundary,
)
from qmf.data.store import RoomRole

_EVENT_NS = 1_700_000_000_000_000_000
_KNOWN_NS = 1_700_000_001_000_000_000
_RECEIVE_NS = 1_700_000_002_000_000_000


@pytest.fixture
def boundary(tmp_path: Path) -> SourceObservationBoundary:
    return SourceObservationBoundary(EvidenceStore(tmp_path / "store", rotation_bytes=256))


def _writer() -> WriterId:
    built = WriterId.try_create("node-a", "ingest", "dukascopy", "boot-1")
    assert is_ok(built)
    return built.value


def _observation(**overrides: object) -> SourceObservation:
    parts: dict[str, object] = {
        "event_time": _EVENT_NS,
        "known_at": _KNOWN_NS,
        "source": "dukascopy",
        "source_native_id": "EURUSD#42",
        "revision": "r1",
        "receive_wall_time": _RECEIVE_NS,
        "writer": _writer(),
        "sequence": 0,
        "world": World.LIVE,
    }
    parts.update(overrides)
    built = SourceObservation.try_create(**parts)  # type: ignore[arg-type]
    assert is_ok(built), built
    return built.value


# --- admit ------------------------------------------------------------------


def test_admit_non_observation_is_invalid_input(boundary: SourceObservationBoundary) -> None:
    refused = boundary.admit({"event_time": _EVENT_NS})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "observation"


def test_admit_lands_in_raw_archive_evidence_bearing(boundary: SourceObservationBoundary) -> None:
    observation = _observation()
    receipt = boundary.admit(observation)
    assert is_ok(receipt)
    admitted = receipt.value
    assert admitted.observation_fingerprint.value == observation.fingerprint.value
    assert admitted.archive.room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE
    assert admitted.archive.engine == "parquet"
    assert admitted.archive.is_evidence_bearing is True
    assert admitted.archive.retained_forever is True
    assert admitted.archive.outcome.value == "stored"
    assert admitted.is_correction is False
    assert admitted.correction_of is None


def test_re_admit_is_idempotent(boundary: SourceObservationBoundary) -> None:
    observation = _observation()
    first = boundary.admit(observation)
    second = boundary.admit(observation)
    assert is_ok(first)
    assert is_ok(second)
    assert first.value.archive.fingerprint.value == second.value.archive.fingerprint.value
    assert second.value.archive.outcome.value == "idempotent"


def test_admit_simulated_world_is_policy_rejection(boundary: SourceObservationBoundary) -> None:
    simulated = _observation(world=World.SIMULATED, source_native_id="EURUSD#sim")
    refused = boundary.admit(simulated)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_admit_engine_failure_is_translated_to_storage_failure(tmp_path: Path) -> None:
    # Root the store at a *file*, so the raw archive cannot create its room directory and
    # the engine failure is translated to a storage-failure refusal at the boundary —
    # never propagated as an exception across the seam.
    blocking_file = tmp_path / "not-a-dir"
    blocking_file.write_text("x", encoding="utf-8")
    boundary = SourceObservationBoundary(EvidenceStore(blocking_file))
    refused = boundary.admit(_observation())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE


# --- read + verbatim round-trip ---------------------------------------------


def test_admit_then_read_round_trips_verbatim(boundary: SourceObservationBoundary) -> None:
    ts = ForeignTimestamp.try_create("2026-08-21T12:00:00.123", "Europe/Zurich", "+02:00", "ms")
    money = ForeignMoney.try_create(110250, 5)
    assert is_ok(ts)
    assert is_ok(money)
    observation = _observation(foreign_timestamp=ts.value, foreign_money=money.value)
    receipt = boundary.admit(observation)
    assert is_ok(receipt)
    read = boundary.read(
        receipt.value.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE
    )
    assert is_ok(read)
    got = read.value
    assert got.fingerprint.value == observation.fingerprint.value
    assert got.event_time.value_ns == _EVENT_NS
    assert got.known_at.value_ns == _KNOWN_NS
    assert got.foreign_timestamp is not None
    assert got.foreign_timestamp.verbatim == "2026-08-21T12:00:00.123"
    assert got.foreign_timestamp.zone == "Europe/Zurich"
    assert got.foreign_money is not None
    assert got.foreign_money.verbatim == 110250
    assert got.foreign_money.scale == 5


def test_read_by_fingerprint_string_key(boundary: SourceObservationBoundary) -> None:
    receipt = boundary.admit(_observation())
    assert is_ok(receipt)
    read = boundary.read(
        receipt.value.archive.fingerprint.value, in_world=World.LIVE, for_world=World.LIVE
    )
    assert is_ok(read)


# --- world isolation (AC5) --------------------------------------------------


def test_cross_world_read_is_policy_rejection(boundary: SourceObservationBoundary) -> None:
    receipt = boundary.admit(_observation())
    assert is_ok(receipt)
    cross = boundary.read(
        receipt.value.archive.fingerprint, in_world=World.LIVE, for_world=World.REPLAY
    )
    assert is_refusal(cross)
    assert cross.category is RefusalCategory.POLICY_REJECTION


def test_read_from_simulated_room_is_policy_rejection(
    boundary: SourceObservationBoundary,
) -> None:
    receipt = boundary.admit(_observation())
    assert is_ok(receipt)
    refused = boundary.read(
        receipt.value.archive.fingerprint, in_world=World.SIMULATED, for_world=World.SIMULATED
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_replay_world_is_isolated_from_live(boundary: SourceObservationBoundary) -> None:
    live_receipt = boundary.admit(_observation(world=World.LIVE))
    assert is_ok(live_receipt)
    # The same fingerprint does not resolve inside the replay room — storage separation.
    miss = boundary.read(
        live_receipt.value.archive.fingerprint, in_world=World.REPLAY, for_world=World.REPLAY
    )
    assert is_refusal(miss)
    assert miss.category is RefusalCategory.STALE_EVIDENCE


# --- missing / corrupt reads ------------------------------------------------


def test_read_unknown_fingerprint_is_stale_evidence(boundary: SourceObservationBoundary) -> None:
    absent = "fp1:sha256:" + "0" * 64
    refused = boundary.read(absent, in_world=World.LIVE, for_world=World.LIVE)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE


def test_read_corrupt_multi_row_artifact_is_storage_failure(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "store")
    boundary = SourceObservationBoundary(store)
    world_store = store.for_world(World.LIVE)
    assert is_ok(world_store)
    # Store a two-row artifact directly — a source observation must be exactly one row,
    # so reading it back through the boundary surfaces a corrupt-evidence storage failure.
    receipt = world_store.value.append_store.append_raw([{"a": 1}, {"b": 2}])
    assert is_ok(receipt)
    refused = boundary.read(receipt.value.fingerprint, in_world=World.LIVE, for_world=World.LIVE)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert refused.retryability.value == "no"


# --- corrections (AC3) ------------------------------------------------------


def test_correction_is_distinct_and_preserves_original(
    boundary: SourceObservationBoundary,
) -> None:
    original = _observation(foreign_money=ForeignMoney.try_create(110250, 5).value)  # type: ignore[union-attr]
    original_receipt = boundary.admit(original)
    assert is_ok(original_receipt)

    correction = _observation(
        known_at=1_700_000_099_000_000_000,
        revision="r2",
        receive_wall_time=1_700_000_100_000_000_000,
        sequence=1,
        foreign_money=ForeignMoney.try_create(110255, 5).value,  # type: ignore[union-attr]
        correction_of=original.fingerprint,
    )
    correction_receipt = boundary.admit(correction)
    assert is_ok(correction_receipt)

    # Distinct artifact, distinct fp1, correction_of pins the original.
    assert correction_receipt.value.observation_fingerprint.value != original.fingerprint.value
    assert (
        correction_receipt.value.archive.fingerprint.value
        != original_receipt.value.archive.fingerprint.value
    )
    assert correction_receipt.value.is_correction is True
    assert correction_receipt.value.correction_of is not None
    assert correction_receipt.value.correction_of.value == original.fingerprint.value

    # Original evidence preserved unchanged, still with its original revision + amount.
    still = boundary.read(
        original_receipt.value.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE
    )
    assert is_ok(still)
    assert still.value.revision == "r1"
    assert still.value.correction_of is None
    assert still.value.foreign_money is not None
    assert still.value.foreign_money.verbatim == 110250
