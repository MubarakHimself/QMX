"""Epic 3 — Story 3.3: seven room-roles per world, cross-world refusal (FR-011 / CT-11).

Independent tests from Story 3.3 AC1-AC5 and PLAN Section 4 (3.3-U1..U6, P1, P2).
Carries P0-6 (cross-world read refuses at EVERY read path) and P0-7 (world=simulated write
refuses). Refusal assertions check the CT-04 category.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import Fingerprint, World, WriteOutcome, is_ok, is_refusal
from qmf.data.partitions import SeriesPartition
from qmf.data.retention import CitationIndex, RetentionPolicy
from qmf.data.rooms import RebuildPins, WorldRooms
from qmf.data.source_boundary import SourceObservationBoundary
from qmf.data.store import RoomRole
from qmf.data.store.receipts import StoreReceipt

import _epic3_helpers as H

_ROWS = [{"t": 1500, "px": 100}]


# --- citation-index fakes (the injected registry seam) -----------------------


class _NoCitations:
    """A citation index that cites nothing (an uncited-view world)."""

    def cites(self, fingerprint: Fingerprint, /) -> bool:
        return False


class _CitesAll:
    """A citation index under which every artifact is cited by some result label."""

    def cites(self, fingerprint: Fingerprint, /) -> bool:
        return True


# --- 3.3-U1 (L1): seven roles per world; storage separation -------------------


def test_3_3_u1_seven_roles_instantiated_per_world(tmp_path: Path) -> None:
    """AC1: live and replay each instantiate all seven room-roles independently (storage separation)."""
    store = H.make_store(tmp_path)
    live = H.unwrap(WorldRooms.for_world(store, World.LIVE))
    replay = H.unwrap(WorldRooms.for_world(store, World.REPLAY))
    assert live.world is World.LIVE
    assert replay.world is World.REPLAY
    # each world owns the full seven room-roles
    assert len(live.roles) == 7
    assert set(live.roles) == set(RoomRole)
    assert set(replay.roles) == set(RoomRole)
    # storage separation: an artifact archived in LIVE is absent from REPLAY's own room
    receipt = H.unwrap(live.append_store.append_raw(_ROWS))
    # reading REPLAY's raw archive (declaring for_world=REPLAY) for that fp finds nothing —
    # a separate physical store, not merely a refused cross-world read.
    miss = replay.append_store.read_raw(receipt.fingerprint, for_world=World.REPLAY)
    H.assert_refusal(miss, "stale evidence")


# --- 3.3-U2 (L1, P0-7): a write into world=simulated is refused ---------------


def test_3_3_u2_simulated_write_refused(tmp_path: Path) -> None:
    """AC1/FM-5 (P0-7): world=simulated is reserved-unusable; requesting/ writing it is a policy rejection."""
    store = H.make_store(tmp_path)
    # requesting the simulated world's rooms is itself refused (no governed namespace)
    H.assert_refusal(store.for_world(World.SIMULATED), "policy rejection")
    H.assert_refusal(WorldRooms.for_world(store, World.SIMULATED), "policy rejection")
    # admitting a simulated observation through the CT-10 boundary is a policy rejection
    boundary = SourceObservationBoundary(store)
    sim_obs = H.unwrap(H.observation(world=World.SIMULATED))
    H.assert_refusal(boundary.admit(sim_obs), "policy rejection")


# --- 3.3-U3 (L1): evidence-bearing only raw+journal; views record rebuild pins -


def test_3_3_u3_evidence_bearing_and_rebuild_pins(tmp_path: Path) -> None:
    """AC2: only raw archive + journal are evidence-bearing; a view pins engine major + calendar + tzdata."""
    live = H.unwrap(WorldRooms.for_world(H.make_store(tmp_path), World.LIVE))
    # is_evidence_bearing true only for the two evidence rooms
    for role in RoomRole:
        expected = role in (RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL)
        assert live.is_evidence_bearing(role) is expected
    # a rebuildable view records its pins and is never evidence-bearing
    pins = H.unwrap(RebuildPins.try_create(H.calendar()))
    view = H.unwrap(live.materialize_view(_ROWS, pins=pins))
    assert view.room_role is RoomRole.PROCESSED
    assert view.is_evidence_bearing is False
    assert view.engine_major is not None
    assert view.rebuild_calendar_identity == "forex-17NY:v3"
    assert view.rebuild_tzdata_version == "2025a"
    # a governed view without pins is refused (a rebuild must always know what to pin)
    H.assert_refusal(live.materialize_view(_ROWS, pins=None), "invalid input")


# --- 3.3-U4 (L1): deletion refused for evidence + cited views; licensed only uncited


def test_3_3_u4_deletion_licensing(tmp_path: Path) -> None:
    """AC3: raw evidence deletion refused; a cited rebuildable view refused; only an uncited view is licensed."""
    live = H.unwrap(WorldRooms.for_world(H.make_store(tmp_path), World.LIVE))
    raw = H.unwrap(live.append_store.append_raw(_ROWS))
    pins = H.unwrap(RebuildPins.try_create(H.calendar()))
    view = H.unwrap(live.materialize_view(_ROWS, pins=pins))

    # raw evidence: never deletion-licensed under any citation index
    policy_none = RetentionPolicy(_NoCitations())
    raw_verdict = H.unwrap(policy_none.verdict_for(raw))
    assert raw_verdict.retained_forever is True
    assert raw_verdict.deletion_licensed is False

    # an uncited rebuildable view: deletion licensed
    uncited = H.unwrap(policy_none.verdict_for(view))
    assert uncited.deletion_licensed is True

    # a cited rebuildable view: retained forever, deletion refused
    cited = H.unwrap(RetentionPolicy(_CitesAll()).verdict_for(view))
    assert cited.retained_forever is True
    assert cited.deletion_licensed is False


def test_3_3_u4_citation_index_failure_fails_closed(tmp_path: Path) -> None:
    """AC3/AR-13: a raising citation index is an unavailable-dependency refusal and never licenses deletion."""

    class _RaisingIndex:
        def cites(self, fingerprint: Fingerprint, /) -> bool:
            raise ConnectionError("registry unreachable")

    live = H.unwrap(WorldRooms.for_world(H.make_store(tmp_path), World.LIVE))
    pins = H.unwrap(RebuildPins.try_create(H.calendar()))
    view = H.unwrap(live.materialize_view(_ROWS, pins=pins))
    policy = RetentionPolicy(_RaisingIndex())
    verdict = policy.verdict_for(view)
    H.assert_refusal(verdict, "unavailable dependency")
    assert policy.may_delete(view) is False  # fail closed: no deletion on a failed read


# --- 3.3-U5 (L1, P0-6 core): a cross-world read refuses -----------------------


def test_3_3_u5_cross_world_read_refused(tmp_path: Path) -> None:
    """AC4/FM-4: a read declaring a world other than the room's is a policy rejection."""
    live = H.unwrap(WorldRooms.for_world(H.make_store(tmp_path), World.LIVE))
    receipt = H.unwrap(live.append_store.append_raw(_ROWS))
    # the LIVE room asked to serve as REPLAY -> policy rejection
    H.assert_refusal(
        live.append_store.read_raw(receipt.fingerprint, for_world=World.REPLAY), "policy rejection"
    )


# --- 3.3-U6 (L1): a series resolves within its (source, instrument, window) ----


def test_3_3_u6_series_resolves_within_partition(tmp_path: Path) -> None:
    """AC5: a time-series artifact resolves back to exactly its (source, instrument, window) partition."""
    live = H.unwrap(WorldRooms.for_world(H.make_store(tmp_path), World.LIVE))
    partition = H.unwrap(
        SeriesPartition.try_create("dukascopy", H.instrument(), H.interval(1000, 2000))
    )
    placement = H.unwrap(live.place_series(partition, [{"t": 1500, "px": 100}]))
    assert placement.archive.room_role is RoomRole.IMMUTABLE_RAW_ARCHIVE
    assert placement.archive.is_evidence_bearing is True
    resolved = H.unwrap(live.resolve_series(placement.archive.fingerprint, for_world=World.LIVE))
    assert resolved.partition.source == "dukascopy"
    assert resolved.partition.window.start.value_ns == 1000
    assert resolved.partition.window.end.value_ns == 2000
    assert resolved.partition.instrument.symbol == partition.instrument.symbol
    # the same series bytes under a different window are a DISTINCT artifact
    other = H.unwrap(
        SeriesPartition.try_create("dukascopy", H.instrument(), H.interval(2000, 3000))
    )
    other_placement = H.unwrap(live.place_series(other, [{"t": 2500, "px": 100}]))
    assert other_placement.archive.fingerprint.value != placement.archive.fingerprint.value


# --- 3.3-P1 (L2 property, evidence integrity): no deletion of evidence/cited ----


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    role=st.sampled_from(list(RoomRole)),
    is_evidence=st.booleans(),
    cited=st.booleans(),
)
def test_3_3_p1_no_deletion_path_removes_evidence_or_cited(role: RoomRole, is_evidence: bool, cited: bool) -> None:
    """AC3: deletion is NEVER licensed for an evidence/lineage artifact, nor for any cited artifact.

    Enumerates the receipt space: for an evidence-bearing (retained_forever) receipt, and for
    any receipt a result label cites, `may_delete` must be False.
    """
    receipt = StoreReceipt(
        outcome=WriteOutcome.STORED,
        fingerprint=H.fp("a"),
        world=World.LIVE,
        room_role=role,
        engine="parquet",
        is_evidence_bearing=is_evidence,
        retained_forever=is_evidence,
    )
    index: CitationIndex = _CitesAll() if cited else _NoCitations()
    policy = RetentionPolicy(index)
    verdict = H.unwrap(policy.verdict_for(receipt))
    if is_evidence or cited:
        assert verdict.deletion_licensed is False, "evidence or a cited artifact must never be deletion-licensed"
        assert policy.may_delete(receipt) is False
    else:
        # only an uncited, non-evidence (rebuildable) artifact may be licensed
        assert verdict.deletion_licensed is True


# --- 3.3-P2 (L2 property, R-012/P0-6): cross-world refuses at EVERY read path ---


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(other=st.sampled_from([World.REPLAY]))
def test_3_3_p2_cross_world_refused_at_every_read_path(tmp_path: Path, other: World) -> None:
    """R-012/P0-6/FM-4: a cross-world read is a policy rejection at every enumerated read path.

    Enumerated paths: raw archive, processed view, journal stream, registry record, and the
    split-governed research door (series resolution). A single leaking path is the FINDING.
    """
    store = H.make_store(tmp_path)
    live = H.unwrap(WorldRooms.for_world(store, World.LIVE))
    ws = H.unwrap(store.for_world(World.LIVE))

    raw = H.unwrap(live.append_store.append_raw(_ROWS))
    pins = H.unwrap(RebuildPins.try_create(H.calendar()))
    view = H.unwrap(live.materialize_view(_ROWS, pins=pins))
    H.unwrap(ws.journal.append("s1", H.writer(), {"event_type": "data quality", "n": 1}))
    rec = H.unwrap(ws.registry_room.put_record({"a": 1}, kind="k", format_version=1))
    partition = H.unwrap(SeriesPartition.try_create("dukascopy", H.instrument(), H.interval(1000, 2000)))
    placement = H.unwrap(live.place_series(partition, [{"t": 1500, "px": 1}]))

    read_paths = {
        "raw archive": live.append_store.read_raw(raw.fingerprint, for_world=other),
        "processed view": live.append_store.read_view(view.fingerprint, for_world=other),
        "journal stream": ws.journal.read_stream("s1", for_world=other),
        "registry record": ws.registry_room.get_record(rec.fingerprint, for_world=other),
        "research door series": live.resolve_series(placement.archive.fingerprint, for_world=other),
    }
    leaks = {name: r for name, r in read_paths.items() if not is_refusal(r) or r.category.value != "policy rejection"}
    assert leaks == {}, f"cross-world read must refuse at EVERY read path; leaking paths: {list(leaks)}"
