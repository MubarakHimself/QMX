"""CT-10 contract test — bitemporal source observations (Story 3.2).

The Tier-1 contract test for the CT-10 boundary, exercised by **both sides**: a
producer (the Data-Ingest door / a venue market-data feed) constructs observation
VALUES, and the consumer (COMP-QMF-DATA, the boundary's only ratified reader) admits
and reads them. Each of the five acceptance criteria is asserted against a real
filesystem-backed store, so the contract is demonstrated end-to-end, not mocked.

* AC1 — the admitted observation carries event-time AND known-at (int64 UTC ns), a
  source orthogonal to VenueId, a revision, an AD-8 WriterId + sequence, its world, and
  an fp1 identity computed only by qmf-core.
* AC2 — foreign timestamp and foreign money ride verbatim; conversions are never done
  silently on this boundary.
* AC3 — a correction of the same provider-native occurrence is a distinct artifact with
  its own fp1 carrying correction_of; the original is preserved.
* AC4 — an incomplete record is an invalid-input refusal (FM-1).
* AC5 — writing world=simulated, and a cross-world read, are policy rejections.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from qmf.core import (
    Fingerprint,
    Instant,
    RefusalCategory,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.data import (
    EvidenceStore,
    ForeignMoney,
    ForeignTimestamp,
    SourceObservation,
    SourceObservationBoundary,
)

_EVENT_NS = 1_700_000_000_000_000_000
_KNOWN_NS = 1_700_000_001_000_000_000
_RECEIVE_NS = 1_700_000_002_000_000_000


@pytest.fixture
def boundary(tmp_path: Path) -> SourceObservationBoundary:
    """The consumer side: COMP-QMF-DATA over a real store."""
    return SourceObservationBoundary(EvidenceStore(tmp_path / "store"))


def _produce(**overrides: object) -> SourceObservation:
    """The producer side: build a CT-10 observation value the way ingest/venue would."""
    writer = WriterId.try_create("vps-1", "ingest", "dukascopy", "boot-7")
    assert is_ok(writer)
    parts: dict[str, object] = {
        "event_time": _EVENT_NS,
        "known_at": _KNOWN_NS,
        "source": "dukascopy",
        "source_native_id": "EURUSD#42",
        "revision": "r1",
        "receive_wall_time": _RECEIVE_NS,
        "writer": writer.value,
        "sequence": 0,
        "world": World.LIVE,
    }
    parts.update(overrides)
    built = SourceObservation.try_create(**parts)  # type: ignore[arg-type]
    assert is_ok(built), built
    return built.value


# --- AC1 --------------------------------------------------------------------


def test_ac1_admitted_observation_carries_the_bitemporal_shape(
    boundary: SourceObservationBoundary,
) -> None:
    observation = _produce()
    # Bitemporal: two distinct times, both int64 UTC ns.
    assert isinstance(observation.event_time, Instant)
    assert isinstance(observation.known_at, Instant)
    assert observation.event_time.value_ns != observation.known_at.value_ns
    # Source orthogonal to VenueId (an opaque provenance string), a revision, a writer
    # with a boot/epoch id, a per-writer sequence, and a world.
    assert observation.source == "dukascopy"
    assert observation.revision == "r1"
    assert observation.writer.boot_epoch_id == "boot-7"
    assert observation.sequence == 0
    assert observation.world is World.LIVE
    # fp1 identity computed only by qmf-core.
    assert isinstance(observation.fingerprint, Fingerprint)
    recomputed = fingerprint(observation.fp1_identity())
    assert is_ok(recomputed)
    assert recomputed.value.value == observation.fingerprint.value
    # And it admits.
    assert is_ok(boundary.admit(observation))


# --- AC2 --------------------------------------------------------------------


def test_ac2_foreign_timestamp_and_money_are_verbatim(
    boundary: SourceObservationBoundary,
) -> None:
    ts = ForeignTimestamp.try_create("1692619200123", "UTC", "+00:00", "milliseconds")
    money = ForeignMoney.try_create(110250, 5)
    assert is_ok(ts)
    assert is_ok(money)
    observation = _produce(foreign_timestamp=ts.value, foreign_money=money.value)
    receipt = boundary.admit(observation)
    assert is_ok(receipt)
    read = boundary.read(
        receipt.value.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE
    )
    assert is_ok(read)
    got = read.value
    # Stored exactly as received — no zone rewrite, no rescale of the amount.
    assert got.foreign_timestamp is not None
    assert got.foreign_timestamp.verbatim == "1692619200123"
    assert got.foreign_timestamp.resolution == "milliseconds"
    assert got.foreign_money is not None
    assert got.foreign_money.verbatim == 110250
    assert got.foreign_money.scale == 5


# --- AC3 --------------------------------------------------------------------


def test_ac3_correction_is_distinct_and_never_masquerades(
    boundary: SourceObservationBoundary,
) -> None:
    original = _produce()
    original_receipt = boundary.admit(original)
    assert is_ok(original_receipt)

    # Same provider-native occurrence (source + source-native id) under a new revision.
    correction = _produce(
        revision="r2",
        known_at=1_700_000_050_000_000_000,
        receive_wall_time=1_700_000_051_000_000_000,
        sequence=1,
        correction_of=original.fingerprint,
    )
    correction_receipt = boundary.admit(correction)
    assert is_ok(correction_receipt)

    assert correction.source == original.source
    assert correction.source_native_id == original.source_native_id
    assert correction.fingerprint.value != original.fingerprint.value
    assert correction.correction_of is not None
    assert correction.correction_of.value == original.fingerprint.value

    # The original still reads back as itself — the correction did not overwrite it.
    still = boundary.read(
        original_receipt.value.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE
    )
    assert is_ok(still)
    assert still.value.revision == "r1"
    assert still.value.correction_of is None


# --- AC4 --------------------------------------------------------------------


def test_ac4_incomplete_record_is_invalid_input(boundary: SourceObservationBoundary) -> None:
    # Each named-missing field is an invalid-input refusal at construction (FM-1).
    for missing in ("event_time", "known_at", "source", "revision"):
        parts: dict[str, object] = {
            "event_time": _EVENT_NS,
            "known_at": _KNOWN_NS,
            "source": "dukascopy",
            "source_native_id": "EURUSD#42",
            "revision": "r1",
            "receive_wall_time": _RECEIVE_NS,
            "writer": WriterId.try_create("vps-1", "ingest", "dukascopy", "boot-7").value,  # type: ignore[union-attr]
            "sequence": 0,
            "world": World.LIVE,
        }
        parts[missing] = None
        refused = SourceObservation.try_create(**parts)  # type: ignore[arg-type]
        assert is_refusal(refused), missing
        assert refused.category is RefusalCategory.INVALID_INPUT

    # A missing writer is likewise refused.
    no_writer = SourceObservation.try_create(
        event_time=_EVENT_NS,
        known_at=_KNOWN_NS,
        source="dukascopy",
        source_native_id="EURUSD#42",
        revision="r1",
        receive_wall_time=_RECEIVE_NS,
        writer=None,
        sequence=0,
        world=World.LIVE,
    )
    assert is_refusal(no_writer)
    assert no_writer.context["field"] == "writer"

    # And the boundary refuses a value that is not a complete observation outright.
    at_boundary = boundary.admit({"source": "dukascopy"})
    assert is_refusal(at_boundary)
    assert at_boundary.category is RefusalCategory.INVALID_INPUT


# --- AC5 --------------------------------------------------------------------


def test_ac5_simulated_write_and_cross_world_read_are_policy_rejections(
    boundary: SourceObservationBoundary,
) -> None:
    # A world=simulated write has no governed namespace in V1.
    simulated = _produce(world=World.SIMULATED, source_native_id="EURUSD#sim")
    write_refusal = boundary.admit(simulated)
    assert is_refusal(write_refusal)
    assert write_refusal.category is RefusalCategory.POLICY_REJECTION

    # A cross-world read is refused — world isolation is storage separation.
    receipt = boundary.admit(_produce())
    assert is_ok(receipt)
    cross = boundary.read(
        receipt.value.archive.fingerprint, in_world=World.LIVE, for_world=World.REPLAY
    )
    assert is_refusal(cross)
    assert cross.category is RefusalCategory.POLICY_REJECTION
