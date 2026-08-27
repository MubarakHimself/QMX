"""Epic 3 — L5 acceptance scenarios (golden end-to-end chains).

ACC-1 = SCN-0002 (late source correction preserves earlier evidence).
ACC-2 = SCN-0003 (default research access excludes the sealed holdout).

These assert lineage + chain integrity end-to-end; the component-level refusals they rely on
are already covered at L1/L2, so here the focus is the whole chain. Refusal assertions check
the CT-04 category.
"""

from __future__ import annotations

from pathlib import Path

from qmf.core import World, is_ok
from qmf.data import EvidenceStore, ReadBoundary
from qmf.data.journal import CausalEdge, JournalEventType
from qmf.data.partitions import SeriesPartition
from qmf.data.rooms import RebuildPins, WorldRooms
from qmf.data.seal import FINAL_LOOK_SUBTYPE, SEAL_CONTROL_STREAM
from qmf.data.source_boundary import SourceObservationBoundary
from qmf.data.splits import KnowledgeKind, KnowledgeRecord, SegmentRole
from qmf.data.store import RoomRole

import _epic3_helpers as H


# --- ACC-1 (SCN-0002): late source correction preserves earlier evidence -------


def test_acc_1_scn_0002_correction_preserves_evidence(tmp_path: Path) -> None:
    """SCN-0002: an original + a later correction to the same occurrence -> two distinct fp1 artifacts,
    joined by an append-only typed lineage edge; the original is preserved; the pair is complete."""
    store = H.make_store(tmp_path)
    boundary = SourceObservationBoundary(store)

    # original observation (source-native occurrence, revision r1) with verbatim foreign evidence
    original = H.unwrap(
        H.observation(
            source="dukascopy",
            source_native_id="EURUSD/2025-06-01T09:30",
            revision="r1",
            sequence=0,
            foreign_timestamp=H.foreign_timestamp(),
            foreign_money=H.foreign_money(verbatim=110235, scale=5),
        )
    )
    r_orig = H.unwrap(boundary.admit(original))

    # a later correction: SAME provider-native occurrence, new revision r2, correction_of set
    correction = H.unwrap(
        H.observation(
            source="dukascopy",
            source_native_id="EURUSD/2025-06-01T09:30",
            revision="r2",
            sequence=1,
            foreign_money=H.foreign_money(verbatim=110240, scale=5),
            correction_of=original.fingerprint,
        )
    )
    r_corr = H.unwrap(boundary.admit(correction))

    # two DISTINCT fp1 artifacts, never a fingerprint collision, never a rewrite
    assert original.fingerprint.value != correction.fingerprint.value
    assert r_orig.archive.fingerprint.value != r_corr.archive.fingerprint.value
    assert r_corr.is_correction is True and r_corr.correction_of.value == original.fingerprint.value

    # the original evidence remains preserved (reads back byte-identical, never annotated in place)
    read_orig = H.unwrap(boundary.read(r_orig.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE))
    assert read_orig.fingerprint.value == original.fingerprint.value
    assert read_orig.correction_of is None
    # foreign evidence stored verbatim (never rescaled)
    assert read_orig.foreign_money.verbatim == 110235 and read_orig.foreign_money.scale == 5

    # the relationship rides an append-only TYPED lineage edge referencing the two fp1s (never a header rewrite)
    ws = H.unwrap(store.for_world(World.LIVE))
    edge = H.unwrap(
        CausalEdge.try_create(
            edge_type="supersedes",
            from_ref=correction.fingerprint,
            to_ref=original.fingerprint,
            writer=H.writer(role="registry", stream="lineage"),
        )
    )
    edge_receipt = H.unwrap(
        ws.registry_room.append_lineage_edge("source-lineage", edge.writer, edge.to_row())
    )
    assert edge_receipt.room_role is RoomRole.REGISTRY_ROOM
    assert edge.from_ref.value == correction.fingerprint.value
    assert edge.to_ref.value == original.fingerprint.value

    # CT-11 preserves the complete pair: BOTH artifacts are independently readable
    assert is_ok(boundary.read(r_orig.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE))
    assert is_ok(boundary.read(r_corr.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE))


# --- ACC-2 (SCN-0003): default research access excludes the sealed holdout ------


def test_acc_2_scn_0003_sealed_holdout_excluded_everywhere(tmp_path: Path) -> None:
    """SCN-0003: a CT-12 release; sealed identities are excludable from default research; every read into
    the sealed period is a policy rejection (raw/processed/research-door/restored-backup); one journaled
    final look; underlying evidence stays retained."""
    seal_ns = 1_000_000
    seal = H.unwrap(H.instant_seal(world=World.LIVE, seal_ns=seal_ns))
    store = EvidenceStore(tmp_path / "release", seal=seal)
    ws = H.unwrap(store.for_world(World.LIVE))
    rooms = H.unwrap(WorldRooms.for_world(store, World.LIVE, seal=seal))

    # (a) the CT-12 manifest identifies sealed vs open identities (default release = train+validation)
    manifest = H.unwrap(
        H.instant_manifest(
            world=World.LIVE, train_end_ns=500_000, validation_end_ns=seal_ns,
            sealed_end_ns=2_000_000, seal_boundary_ns=seal_ns,
        )
    )
    open_record = H.unwrap(
        KnowledgeRecord.try_create(observed_at=300_000, knowledge_time=300_000, kind=KnowledgeKind.STRUCTURE)
    )
    sealed_record = H.unwrap(
        KnowledgeRecord.try_create(observed_at=1_500_000, knowledge_time=1_500_000, kind=KnowledgeKind.STRUCTURE)
    )
    assert H.unwrap(manifest.partition_record(open_record)) is SegmentRole.TRAIN
    assert H.unwrap(manifest.partition_record(sealed_record)) is SegmentRole.SEALED_TEST  # a sealed identity

    # (b) archive an artifact in the sealed period; the evidence is retained (kept regardless)
    sealed_artifact = H.unwrap(ws.append_store.append_raw([{"t": 1_500_000, "px": 1}]))
    view = H.unwrap(ws.append_store.materialize_view([{"t": 1_500_000, "px": 1}], rebuild_calendar_identity="c", rebuild_tzdata_version="z"))

    # (c) every read INTO the sealed period is a policy rejection, never a silent empty result
    H.assert_refusal(
        ws.append_store.read_raw(sealed_artifact.fingerprint, for_world=World.LIVE, at=1_500_000),
        "policy rejection",
    )  # raw archive
    H.assert_refusal(
        ws.append_store.read_view(view.fingerprint, for_world=World.LIVE, at=1_500_000),
        "policy rejection",
    )  # processed room

    # research door: place a series whose window reaches into the sealed period; resolution refuses
    partition = H.unwrap(SeriesPartition.try_create("dukascopy", H.instrument(), H.interval(1_400_000, 1_600_000)))
    placement = H.unwrap(rooms.place_series(partition, [{"t": 1_500_000, "px": 1}]))
    H.assert_refusal(
        rooms.resolve_series(placement.archive.fingerprint, for_world=World.LIVE), "policy rejection"
    )  # split-governed research door

    # restored-backup boundary: the seal refuses a sealed position there too (see 3.4-I1 for the real restore)
    sealed_position = H.instant_boundary(1_500_000)
    H.assert_refusal(seal.guard(sealed_position, boundary=ReadBoundary.RESTORED_BACKUP), "policy rejection")

    # (d) exactly one authorized final look, journaled as a control-action subtype; a second is refused
    look_writer = H.writer(role="data", stream=SEAL_CONTROL_STREAM)
    H.unwrap(seal.authorize_final_look(ws.journal, look_writer, at=9_999))
    events = H.unwrap(ws.journal.read_stream(SEAL_CONTROL_STREAM, for_world=World.LIVE))
    assert any(
        e.get("event_type") == "control action" and e.get("control_action_subtype") == FINAL_LOOK_SUBTYPE
        for e in events
    )
    H.assert_refusal(seal.authorize_final_look(ws.journal, look_writer, at=10_000), "policy rejection")

    # (e) underlying evidence stays RETAINED: a read at an OPEN position returns the artifact intact
    assert is_ok(ws.append_store.read_raw(sealed_artifact.fingerprint, for_world=World.LIVE, at=100_000))
