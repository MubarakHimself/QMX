"""Epic 3 — Story 3.4: dataset splits + the 12-month no-peek seal (FR-012 / CT-12).

Independent tests from Story 3.4 AC1-AC6 and PLAN Section 4 (3.4-U1..U7, P1, P2, P3, C1, I1).
Carries P0-6 (sealed holdout excluded at EVERY read boundary) and R-012 (seal/split refusals
hold at every enumerated read path). Refusal assertions check the CT-04 category.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import (
    Ok,
    Result,
    Retryability,
    World,
    fingerprint,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.data import (
    EvidenceStore,
    HoldoutSeal,
    OffMachineBackup,
    OffMachineRestore,
    ReadBoundary,
    StoragePutAck,
)
from qmf.data.seal import FINAL_LOOK_SUBTYPE, SEAL_CONTROL_STREAM
from qmf.data.splits import (
    DEFAULT_SPLIT_ROLES,
    KnowledgeKind,
    KnowledgeRecord,
    ProducerHorizon,
    SegmentRole,
    SplitBoundary,
    SplitManifest,
)
from qmf.data.store import RoomRole

import _epic3_helpers as H


# --- backup/restore fakes (for the 3.4-I1 restored-backup integration) --------


class _XorCipher:
    def encrypt(self, plaintext: bytes, /) -> Result[bytes]:
        return Ok(bytes(b ^ 0x5A for b in plaintext))

    def decrypt(self, ciphertext: bytes, /) -> Result[bytes]:
        return self.encrypt(ciphertext)


class _MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, int, str], bytes] = {}

    def put(self, *, world: str, copy_version: int, source_room_role: str, payload: bytes, format_version: int) -> Result[StoragePutAck]:
        del format_version
        self.objects[(world, copy_version, source_room_role)] = payload
        return Ok(StoragePutAck())

    def get(self, *, world: str, copy_version: int, source_room_role: str, format_version: int) -> Result[bytes]:
        del format_version
        payload = self.objects.get((world, copy_version, source_room_role))
        if payload is None:
            return unpersistable("no such copy", retryability=Retryability.NO, context={"copy_version": copy_version})
        return Ok(payload)


# --- 3.4-U1 (L1): boundaries are TradingDates or Instants, never civil dates ---


def test_3_4_u1_civil_date_boundary_refused() -> None:
    """AC1/DEC-0106: a split/seal boundary is a TradingDate or Instant; a civil date is invalid input."""
    H.assert_refusal(SplitBoundary.try_create(H.civil(2025, 1, 1)), "invalid input")
    # a TradingDate and an Instant both build
    assert is_ok(SplitBoundary.try_create(H.trading_date(H.calendar(), 2025, 1, 1)))
    assert is_ok(SplitBoundary.try_create(H.instant(1000)))


# --- 3.4-U2 (L1): a manifest omitting purge/embargo width is refused ----------


def test_3_4_u2_missing_widths_refused() -> None:
    """AC2/DEC-0131: purge_width and embargo_width are required fields; omitting either is invalid input."""
    cal = H.calendar()
    segments = H.unwrap(
        SplitManifest.default_split_segments(
            [H.instant_boundary(1000), H.instant_boundary(2000), H.instant_boundary(3000)]
        )
    )
    base = dict(
        calendar_identity=cal,
        segments=segments,
        seal_boundary=H.instant_boundary(2000),
        world=World.REPLAY,
    )
    H.assert_refusal(
        SplitManifest.try_create(**base, purge_width=None, embargo_width=H.duration(0)), "invalid input"
    )
    H.assert_refusal(
        SplitManifest.try_create(**base, purge_width=H.duration(0), embargo_width=None), "invalid input"
    )


# --- 3.4-U3 (L1): widths enter the fingerprint; split_id is fp1-derived --------


def test_3_4_u3_widths_change_fingerprint_and_id_is_derived() -> None:
    """AC1/AC2: changing purge/embargo width changes the split fp1; split_id == the manifest's fp1."""
    m0 = H.unwrap(H.instant_manifest(purge_ns=0, embargo_ns=0))
    m_purge = H.unwrap(H.instant_manifest(purge_ns=500, embargo_ns=0))
    m_embargo = H.unwrap(H.instant_manifest(purge_ns=0, embargo_ns=500))
    assert m0.split_id != m_purge.split_id  # purge_width enters the fingerprint
    assert m0.split_id != m_embargo.split_id  # embargo_width enters the fingerprint
    # split_id is derived from fp1, never minted, and re-fingerprints identically
    assert m0.split_id == m0.fingerprint.value
    recomputed = fingerprint(m0.fp1_identity())
    assert is_ok(recomputed)
    assert recomputed.value.value == m0.fingerprint.value


# --- 3.4-U4 (L1): a straddling record refused unless the embargo covers the gap


def test_3_4_u4_straddle_refused_unless_embargo_covers() -> None:
    """AC3/DEC-0131: observed-at before a boundary while knowledge-time follows it is refused unless embargo covers."""
    # manifest segment boundaries are at 1_000_000 / 2_000_000 / 3_000_000 (helper defaults).
    # observed-at 900_000 is in segment 0; knowledge-time 1_500_000 is in segment 1 -> straddle,
    # gap = 600_000.
    straddler = H.unwrap(
        KnowledgeRecord.try_create(
            observed_at=900_000, knowledge_time=1_500_000, kind=KnowledgeKind.STRUCTURE
        )
    )
    # embargo 0 does NOT cover the 600_000 gap -> policy rejection
    m_tight = H.unwrap(H.instant_manifest(purge_ns=0, embargo_ns=0))
    H.assert_refusal(m_tight.partition_record(straddler), "policy rejection")
    # embargo 600_000 DOES cover the gap -> placed by knowledge time (validation segment)
    m_wide = H.unwrap(H.instant_manifest(purge_ns=0, embargo_ns=600_000))
    placed = H.unwrap(m_wide.partition_record(straddler))
    assert placed is SegmentRole.VALIDATION


# --- 3.4-U5 (L1, P0-6): sealed-period read is a policy rejection, never empty ---


def test_3_4_u5_sealed_read_refused_never_silent_empty(tmp_path: Path) -> None:
    """AC4/FM-3 (P0-6): a sealed-period read is a policy rejection at the store boundary, never a silent empty."""
    seal = H.unwrap(H.instant_seal(world=World.LIVE, seal_ns=1_000_000))
    store = EvidenceStore(tmp_path / "sealed", seal=seal)
    ws = H.unwrap(store.for_world(World.LIVE))
    receipt = H.unwrap(ws.append_store.append_raw([{"t": 1_500_000, "px": 1}]))
    # a read declaring a knowledge position INSIDE the sealed window -> policy rejection
    sealed_read = ws.append_store.read_raw(receipt.fingerprint, for_world=World.LIVE, at=1_500_000)
    H.assert_refusal(sealed_read, "policy rejection")
    # fail-closed: a positionless read while a seal is wired is ALSO refused (never fail-open)
    positionless = ws.append_store.read_raw(receipt.fingerprint, for_world=World.LIVE, at=None)
    H.assert_refusal(positionless, "policy rejection")
    # a read positioned OUTSIDE the sealed window proceeds
    open_read = ws.append_store.read_raw(receipt.fingerprint, for_world=World.LIVE, at=500_000)
    assert is_ok(open_read)


# --- 3.4-U6 (L1): a foreign calendar identity is refused, never rescaled -------


def test_3_4_u6_calendar_mismatch_refused() -> None:
    """AC5/DEC-0106: a row/seal carrying a different calendar identity is a policy rejection, never rescaled."""
    manifest = H.unwrap(H.instant_manifest(cal=H.calendar("v3")))
    # a different calendar identity offered to the split -> policy rejection
    H.assert_refusal(manifest.admits_calendar(H.calendar("v4")), "policy rejection")
    # the pinned identity is admitted
    assert is_ok(manifest.admits_calendar(H.calendar("v3")))
    # the seal, too, refuses a position of a foreign calendar identity
    seal = H.unwrap(H.trading_seal(cal=H.calendar("v3")))
    foreign_pos = H.trading_boundary(H.calendar("v4"), 2025, 6, 1)
    H.assert_refusal(seal.is_sealed(foreign_pos), "policy rejection")


# --- 3.4-U7 (L1): exactly one journaled final look; a second is refused --------


def test_3_4_u7_single_final_look_journaled(tmp_path: Path) -> None:
    """AC6/DEC-0119: the one authorized final look is journaled as a control-action subtype; a second is refused."""
    seal = H.unwrap(H.trading_seal(world=World.LIVE))
    ws = H.unwrap(H.make_store(tmp_path).for_world(World.LIVE))
    writer = H.writer(role="data", stream=SEAL_CONTROL_STREAM)
    first = H.unwrap(seal.authorize_final_look(ws.journal, writer, at=10_000))
    assert first.room_role is RoomRole.JOURNAL
    # the look is journaled as the named control-action subtype (read via the raw stream reader,
    # the access path the seal itself uses for these lean control-action records)
    events = H.unwrap(ws.journal.read_stream(SEAL_CONTROL_STREAM, for_world=World.LIVE))
    assert any(
        e.get("event_type") == "control action"
        and e.get("control_action_subtype") == FINAL_LOOK_SUBTYPE
        for e in events
    )
    # a SECOND look at the same seal is refused — the sealed set is never silently recycled
    H.assert_refusal(
        seal.authorize_final_look(ws.journal, writer, at=20_000), "policy rejection"
    )


# --- 3.4-P1 (L2 property, R-012/P0-6): sealed read refuses at EVERY boundary ----


@settings(max_examples=80, deadline=None)
@given(
    seal_ns=st.integers(min_value=1, max_value=5_000_000),
    delta=st.integers(min_value=0, max_value=1_000_000),
)
def test_3_4_p1_sealed_read_refused_at_every_boundary(seal_ns: int, delta: int) -> None:
    """R-012/P0-6: for arbitrary seal boundaries, a position at/after the seal is a policy rejection at EVERY ReadBoundary."""
    seal = H.unwrap(H.instant_seal(world=World.REPLAY, seal_ns=seal_ns))
    sealed_position = H.instant_boundary(seal_ns + delta)  # at or after the frozen boundary => sealed
    leaks = []
    for boundary in ReadBoundary:  # raw archive, processed, research door, restored backup
        guarded = seal.guard(sealed_position, boundary=boundary)
        if not is_refusal(guarded) or guarded.category.value != "policy rejection":
            leaks.append(boundary.value)
    assert leaks == [], f"a sealed read must refuse at EVERY read boundary; leaking: {leaks}"
    # a position strictly BEFORE the seal is admitted at every boundary (no false refusal)
    if seal_ns >= 2:
        open_position = H.instant_boundary(seal_ns - 1)
        for boundary in ReadBoundary:
            assert is_ok(seal.guard(open_position, boundary=boundary))


# --- 3.4-P2 (L2 property): the seal boundary is frozen; a re-derivation mints new


def test_3_4_p2_seal_boundary_frozen_new_derivation_mints_new_manifest() -> None:
    """AC5: re-deriving under a newer tzdata mints a NEW manifest fp1 and never rewrites the frozen boundary."""
    old_cal = H.calendar("v3", tzdata="2025a")
    new_cal = H.calendar("v3", tzdata="2026b")
    m_old = H.unwrap(H.instant_manifest(cal=old_cal))
    m_new = H.unwrap(H.instant_manifest(cal=new_cal))
    # a newer tzdata mints a distinct manifest id (new manifest + lineage edge upstream)
    assert m_old.split_id != m_new.split_id
    # the original manifest's pinned calendar identity is unchanged (frozen), never re-derived
    assert m_old.calendar_identity.tzdata_version == "2025a"
    # a frozen trading-date seal boundary keeps its own calendar identity verbatim
    seal_old = H.unwrap(H.trading_seal(cal=old_cal))
    assert seal_old.seal_boundary.calendar_identity is not None
    assert seal_old.seal_boundary.calendar_identity.tzdata_version == "2025a"


# --- 3.4-P3 (L2 property): a longer-horizon producer reuse refuses, never leaks -


@settings(max_examples=60, deadline=None)
@given(width_ns=st.integers(min_value=0, max_value=1_000), excess=st.integers(min_value=1, max_value=1_000))
def test_3_4_p3_longer_horizon_producer_refused(width_ns: int, excess: int) -> None:
    """AC2/DEC-0131: reusing a split with a producer whose horizon exceeds the widths refuses rather than leaks."""
    manifest = H.unwrap(H.instant_manifest(purge_ns=width_ns, embargo_ns=width_ns))
    over = H.unwrap(ProducerHorizon.try_create("indicator:slow", H.duration(width_ns + excess)))
    H.assert_refusal(manifest.admits_producer(over), "policy rejection")
    # a producer within the widths is admitted
    within = H.unwrap(ProducerHorizon.try_create("indicator:fast", H.duration(width_ns)))
    assert is_ok(manifest.admits_producer(within))


# --- 3.4-C1 (L3 contract): fingerprinted, ordered, default 3-way split ---------


def test_3_4_c1_manifest_contract_shape() -> None:
    """CT-12: default {train, validation, sealed-test}, time-ordered non-overlapping, one pinned calendar."""
    manifest = H.unwrap(H.instant_manifest())
    roles = [seg.role for seg in manifest.segments]
    assert roles == list(DEFAULT_SPLIT_ROLES)
    assert roles == [SegmentRole.TRAIN, SegmentRole.VALIDATION, SegmentRole.SEALED_TEST]
    # segments strictly increasing (time-ordered, non-overlapping)
    starts = [seg.boundary.instant.value_ns for seg in manifest.segments]
    assert starts == sorted(starts) and len(set(starts)) == len(starts)
    # exactly one calendar identity pinned in-band
    assert manifest.calendar_identity == H.calendar()
    # non-strictly-increasing segments are refused
    bad = SplitManifest.default_split_segments(
        [H.instant_boundary(2000), H.instant_boundary(2000), H.instant_boundary(3000)]
    )
    bad_manifest = SplitManifest.try_create(
        calendar_identity=H.calendar(),
        segments=bad.value,
        seal_boundary=H.instant_boundary(2000),
        purge_width=H.duration(0),
        embargo_width=H.duration(0),
        world=World.REPLAY,
    )
    H.assert_refusal(bad_manifest, "invalid input")


# --- 3.4-I1 (L4 integration, R-012): a sealed read survives a restore ----------


def test_3_4_i1_seal_survives_restore(tmp_path: Path) -> None:
    """AC4/R-012: after a real backup+restore into a replacement store, a sealed-period read still refuses."""
    seal = H.unwrap(H.instant_seal(world=World.LIVE, seal_ns=1_000_000))
    # source store has NO seal wired, so its evidence can be read for backup (a seal-wired
    # positionless backup read is itself fail-closed refused); the seal is store configuration
    # applied at the RESTORED store, which is exactly what "seal survives restore" means.
    source = EvidenceStore(tmp_path / "source")
    src_ws = H.unwrap(source.for_world(World.LIVE))
    receipt = H.unwrap(src_ws.append_store.append_raw([{"t": 1_500_000, "px": 1}]))
    export = H.unwrap(src_ws.backup_input.read_room(RoomRole.IMMUTABLE_RAW_ARCHIVE, for_world=World.LIVE))

    storage, cipher = _MemoryStorage(), _XorCipher()
    copied = H.unwrap(OffMachineBackup(storage, cipher).copy_export(export, for_world=World.LIVE))

    # restore into a REPLACEMENT store that also has the seal wired
    replacement = EvidenceStore(tmp_path / "replacement", seal=seal)
    restore = OffMachineRestore(storage, cipher)
    restored = restore.restore_copy(
        world=World.LIVE,
        copy_version=copied.copy_version,
        source_room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE,
        into=replacement,
        for_world=World.LIVE,
        source_store=source,
    )
    assert is_ok(restored)
    # reading the restored artifact INTO the sealed period is a policy rejection (seal survived restore)
    rep_ws = H.unwrap(replacement.for_world(World.LIVE))
    sealed_read = rep_ws.append_store.read_raw(receipt.fingerprint, for_world=World.LIVE, at=1_500_000)
    H.assert_refusal(sealed_read, "policy rejection")
    # and a non-sealed read of the same restored artifact succeeds (the evidence is genuinely present)
    open_read = rep_ws.append_store.read_raw(receipt.fingerprint, for_world=World.LIVE, at=500_000)
    assert is_ok(open_read)
