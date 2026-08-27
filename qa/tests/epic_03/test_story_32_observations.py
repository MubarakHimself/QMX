"""Epic 3 — Story 3.2: bitemporal source observations, append-only corrections (FR-010 / CT-10).

Independent tests from Story 3.2 AC1-AC5 and PLAN Section 4 (3.2-U1..U5, P1, P2, P3, C1, C2).
SCN-0002 (original + correction) is exercised end-to-end in the L5 acceptance suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import Instant, VenueId, World, is_ok, is_refusal
from qmf.data.observation import ForeignMoney, ForeignTimestamp, SourceObservation
from qmf.data.source_boundary import SourceObservationBoundary

import _epic3_helpers as H


# --- 3.2-U1 (L1): source is opaque and orthogonal to VenueId ------------------


def test_3_2_u1_source_opaque_and_orthogonal_to_venue() -> None:
    """AC1: `source` is a verbatim opaque provenance string, never parsed, not a VenueId."""
    obs = H.unwrap(H.observation(source="Dukascopy/DEMO feed #7"))
    assert obs.source == "Dukascopy/DEMO feed #7"  # stored verbatim, never parsed/cased
    assert isinstance(obs.source, str)
    assert not isinstance(obs.source, VenueId)  # a source is a provenance noun, not a venue
    # A source token that would NOT be a valid tradeable VenueId is still admitted verbatim:
    # source and VenueId are orthogonal identity spaces (DEC-0117).
    weird_source = "a source that is not a venue !!"
    obs2 = H.unwrap(H.observation(source=weird_source))
    assert obs2.source == weird_source


# --- 3.2-U2 (L1): foreign timestamp stored verbatim with zone/offset/resolution


def test_3_2_u2_foreign_timestamp_verbatim(tmp_path: Path) -> None:
    """AC2: the foreign timestamp is kept byte-for-byte with its declared zone/offset/resolution."""
    ft = H.foreign_timestamp(
        verbatim="2025-06-01T09:30:00.000123", zone="America/New_York", offset="-04:00", resolution="microseconds"
    )
    obs = H.unwrap(H.observation(foreign_timestamp=ft, receive_wall_time=5_000))
    assert obs.foreign_timestamp is not None
    assert obs.foreign_timestamp.verbatim == "2025-06-01T09:30:00.000123"
    assert obs.foreign_timestamp.zone == "America/New_York"
    assert obs.foreign_timestamp.offset == "-04:00"
    assert obs.foreign_timestamp.resolution == "microseconds"
    # receive_wall_time is a separate local Instant (int64 UTC ns), not the foreign string
    assert isinstance(obs.receive_wall_time, Instant)
    assert obs.receive_wall_time.value_ns == 5_000
    # round-trips through the row without reformatting
    row = obs.to_row()
    assert row["foreign_timestamp"] == {
        "verbatim": "2025-06-01T09:30:00.000123",
        "zone": "America/New_York",
        "offset": "-04:00",
        "resolution": "microseconds",
    }


# --- 3.2-U3 (L1): foreign money stored verbatim as scaled integers ------------


def test_3_2_u3_foreign_money_verbatim_scaled_integer() -> None:
    """AC2/DEC-0105: foreign money is a verbatim scaled integer at the source's scale; a float is refused."""
    fm = H.foreign_money(verbatim=110235, scale=5)
    obs = H.unwrap(H.observation(foreign_money=fm))
    assert obs.foreign_money is not None
    assert obs.foreign_money.verbatim == 110235
    assert obs.foreign_money.scale == 5
    # a binary float amount is refused — money never rides a float
    H.assert_refusal(ForeignMoney.try_create(1.10235, 5), "invalid input")
    # a bool is refused (bool is not an int amount here)
    H.assert_refusal(ForeignMoney.try_create(True, 5), "invalid input")
    # a negative scale is refused
    H.assert_refusal(ForeignMoney.try_create(100, -1), "invalid input")


# --- 3.2-U4 (L1): a correction is a distinct fp1 artifact; original unchanged --


def test_3_2_u4_correction_is_distinct_artifact(tmp_path: Path) -> None:
    """AC3/FM-2: a correction keyed on (source, id, revision) is a distinct fp1 with correction_of set."""
    original = H.unwrap(H.observation(revision="r1", sequence=0))
    correction = H.unwrap(
        H.observation(revision="r2", sequence=1, correction_of=original.fingerprint)
    )
    assert correction.is_correction is True
    assert correction.correction_of is not None
    assert correction.correction_of.value == original.fingerprint.value
    # a correction is a DISTINCT artifact (its own fp1), never the original
    assert correction.fingerprint.value != original.fingerprint.value
    # admit both to the archive: the original artifact's bytes are unchanged by the correction
    store = H.make_store(tmp_path)
    boundary = SourceObservationBoundary(store)
    r_orig = H.unwrap(boundary.admit(original))
    r_corr = H.unwrap(boundary.admit(correction))
    assert r_corr.is_correction is True
    assert r_orig.archive.fingerprint.value != r_corr.archive.fingerprint.value
    read_back = H.unwrap(
        boundary.read(r_orig.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE)
    )
    assert read_back.fingerprint.value == original.fingerprint.value
    assert read_back.correction_of is None  # the original was never annotated in place


# --- 3.2-U5 (L1): a record missing a required bitemporal field is refused ------


@pytest.mark.parametrize(
    "missing",
    ["event_time", "known_at", "source", "source_native_id", "revision", "sequence", "writer", "world"],
)
def test_3_2_u5_missing_required_field_refused(missing: str) -> None:
    """AC4/FM-1: an observation missing a required identity field is `invalid input`, never admitted."""
    kwargs: dict[str, object] = {}
    if missing == "writer":
        kwargs["writer_id"] = "not-a-writer"
    elif missing == "world":
        kwargs[missing] = "not-a-world"
    else:
        kwargs[missing] = None
    result = H.observation(**kwargs)
    H.assert_refusal(result, "invalid input")


def test_3_2_u5_incomplete_never_reaches_boundary(tmp_path: Path) -> None:
    """AC4: the boundary refuses a value that is not a complete SourceObservation (never stores it)."""
    boundary = SourceObservationBoundary(H.make_store(tmp_path))
    H.assert_refusal(boundary.admit({"event_time": 1}), "invalid input")
    H.assert_refusal(boundary.admit(None), "invalid input")


# --- 3.2-P1 (L2 property): a coarser source resolution is never presented finer


@settings(max_examples=60, deadline=None)
@given(
    verbatim=st.text(min_size=1, max_size=40).filter(lambda s: s.strip() != ""),
    zone=st.sampled_from(["UTC", "Europe/Zurich", "America/New_York", "Asia/Tokyo"]),
    offset=st.sampled_from(["+00:00", "+01:00", "-04:00", "+09:00"]),
    resolution=st.sampled_from(["seconds", "milliseconds", "microseconds", "nanoseconds", "minutes"]),
)
def test_3_2_p1_resolution_never_reformatted(verbatim: str, zone: str, offset: str, resolution: str) -> None:
    """AC2: the source's declared verbatim string and resolution are preserved exactly (never finer)."""
    built = ForeignTimestamp.try_create(verbatim, zone, offset, resolution)
    if is_refusal(built):
        return  # blank-ish verbatim rejected up front; nothing to compare
    ft = built.value
    assert ft.verbatim == verbatim  # never reformatted
    assert ft.resolution == resolution  # coarse resolution kept as-is, never presented finer
    assert ft.zone == zone and ft.offset == offset


# --- 3.2-P2 (L2 property, evidence integrity): corrections only append ---------


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(n=st.integers(min_value=1, max_value=6))
def test_3_2_p2_corrections_never_overwrite_original(tmp_path: Path, n: int) -> None:
    """AC3/FM-2: across a chain of corrections, the original raw record is never mutated or overwritten."""
    store = H.make_store(tmp_path)
    boundary = SourceObservationBoundary(store)
    original = H.unwrap(H.observation(revision="r0", sequence=0))
    r_orig = H.unwrap(boundary.admit(original))
    original_row = H.unwrap(
        boundary.read(r_orig.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE)
    )
    prev_fp = original.fingerprint
    seen = {original.fingerprint.value}
    for i in range(1, n + 1):
        corr = H.unwrap(
            H.observation(revision=f"r{i}", sequence=i, correction_of=prev_fp)
        )
        # every correction has its OWN distinct fp1
        assert corr.fingerprint.value not in seen
        seen.add(corr.fingerprint.value)
        H.unwrap(boundary.admit(corr))
        prev_fp = corr.fingerprint
    # after the whole chain the original raw evidence reads back byte-identical
    still = H.unwrap(
        boundary.read(r_orig.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE)
    )
    assert still.fingerprint.value == original.fingerprint.value
    assert still.to_row() == original_row.to_row()


# --- 3.2-P3 (L2 property, R-007): fuzzed malformed observations always refuse --


@settings(max_examples=120, deadline=None)
@given(
    event_time=st.one_of(st.none(), st.text(max_size=5), st.floats(), st.integers()),
    known_at=st.one_of(st.none(), st.text(max_size=5), st.integers()),
    source=st.one_of(st.none(), st.just(""), st.just("   "), st.text(min_size=1, max_size=6)),
    revision=st.one_of(st.none(), st.just(""), st.text(min_size=1, max_size=6)),
    sequence=st.one_of(st.none(), st.text(max_size=3), st.integers(min_value=-5, max_value=5), st.booleans()),
    world=st.one_of(st.none(), st.just("bogus"), st.sampled_from(["live", "replay", "simulated"])),
)
def test_3_2_p3_malformed_never_admitted_as_ok(
    event_time: object, known_at: object, source: object, revision: object, sequence: object, world: object
) -> None:
    """R-007/FM-1: an incomplete/adversarial observation is either a typed CT-04 refusal or a fully valid Ok.

    It must never yield an admitted-but-incomplete record: any Ok must carry every required
    bitemporal field, and any missing/invalid field must produce an `invalid input` refusal.
    """
    result = SourceObservation.try_create(
        event_time=event_time,
        known_at=known_at,
        source=source,
        source_native_id="occ",
        revision=revision,
        receive_wall_time=9_999,
        writer=H.writer(),
        sequence=sequence,
        world=world,
    )
    if is_ok(result):
        obs = result.value
        # an Ok is fully-formed: every required identity field present and typed
        assert isinstance(obs.event_time, Instant)
        assert isinstance(obs.known_at, Instant)
        assert isinstance(obs.source, str) and obs.source.strip() != ""
        assert isinstance(obs.revision, str) and obs.revision.strip() != ""
        assert isinstance(obs.sequence, int) and not isinstance(obs.sequence, bool) and obs.sequence >= 0
        assert isinstance(obs.world, World)
        assert obs.fingerprint is not None
    else:
        H.assert_refusal(result, "invalid input")


# --- 3.2-C1 (L3 contract): full field roster round-trip; identity = fp1 only ---


def test_3_2_c1_round_trip_full_roster() -> None:
    """CT-10: the full field roster round-trips (to_row/from_row) to fp1-equal evidence."""
    obs = H.unwrap(
        H.observation(
            event_time=1_000,
            known_at=2_000,
            source="dukascopy",
            source_native_id="EURUSD/2025-06-01",
            revision="r3",
            receive_wall_time=2_500,
            sequence=7,
            foreign_timestamp=H.foreign_timestamp(),
            foreign_money=H.foreign_money(),
        )
    )
    row = obs.to_row()
    rebuilt = H.unwrap(SourceObservation.from_row(row))
    assert rebuilt.fingerprint.value == obs.fingerprint.value  # identity = fp1, round-trips
    assert rebuilt.event_time.value_ns == 1_000
    assert rebuilt.known_at.value_ns == 2_000
    assert rebuilt.source == "dukascopy"
    assert rebuilt.source_native_id == "EURUSD/2025-06-01"
    assert rebuilt.revision == "r3"
    assert rebuilt.sequence == 7


def test_3_2_c1_identity_is_fp1_not_ordering_key() -> None:
    """CT-10: (instant, writer, sequence) is an ordering key, never identity — fp1 is identity.

    Two observations that differ ONLY in the (writer, sequence) ordering position carry
    DIFFERENT fp1s (every field is identity-by-default), so identity can never collapse to
    the ordering key. Conversely, the boot-scoped diagnostic is excluded from identity.
    """
    a = H.unwrap(H.observation(sequence=0))
    b = H.unwrap(H.observation(sequence=1))
    assert a.fingerprint.value != b.fingerprint.value
    # the receive-monotonic diagnostic is excluded from identity: two obs differing only in it
    # deduplicate to the same fp1 and the same persisted row.
    assert a.to_row() == H.unwrap(H.observation(sequence=0)).to_row()


def test_3_2_c1_tampered_row_refused() -> None:
    """CT-10: a stored row that no longer re-fingerprints to its fp1 is refused, never read back valid."""
    obs = H.unwrap(H.observation())
    row = obs.to_row()
    tampered = dict(row, revision="TAMPERED")  # change a field but keep the old fingerprint
    H.assert_refusal(SourceObservation.from_row(tampered), "invalid input")


# --- 3.2-C2 (L3 contract): world enum + foreign-money optionality --------------


def test_3_2_c2_world_enum_and_optional_foreign_money() -> None:
    """CT-10: world is the closed enum; foreign money is optional (present only when money-bearing)."""
    # world must be one of the closed set
    H.assert_refusal(H.observation(world="mainnet"), "invalid input")
    for w in (World.LIVE, World.REPLAY):
        assert is_ok(H.observation(world=w))
    # simulated is a valid enum value at the value layer (it is world-scoped evidence);
    # the boundary refuses WRITING it (tested in Story 3.3). Here it constructs.
    assert is_ok(H.observation(world=World.SIMULATED))
    # a non-money observation carries no foreign money
    obs = H.unwrap(H.observation(foreign_money=None))
    assert obs.foreign_money is None
    assert "foreign_money" not in obs.to_row()
