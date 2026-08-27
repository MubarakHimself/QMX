"""L2 — contract-conformance tests for Epic 6. Oracle = the CT-15 / CT-10 / CT-07 clause.

Primary deliverable: one test per acceptance-criterion family. Each boundary RETURNS
value-or-refusal; refusals are checked by CT-04 category, never a parsed string.
"""

from __future__ import annotations

import pytest

from qmf.core import Ok, World, is_ok, is_refusal
from qmf.data import calendar_feed as cal
from qmf.data import dukascopy as duk
from qmf.data.ingest import ExternalSourceIngest, IntakeKey, IntakeOutcome, SourceRequest
from qmf.data.journal_producer import JournalReader, JournalWriter
from qmf.data.observation import ForeignMoney, ForeignTimestamp, SourceObservation
from qmf.data.ticks import (
    EDGE_CORROBORATES,
    EDGE_DISAGREES_WITH,
    EDGE_SUPERSEDES,
    TickObservation,
    TickQuote,
    link_revision,
    relate_source_facts,
)

import helpers as H

_KNOWN = 1_600_000_000_000_000_000
_RECV = 1_600_000_000_500_000_000
_JINSTANT = 1_600_000_001_000_000_000


# --- QA-E06-L2-001 — valid response normalizes + round-trips -----------------


def test_l2_001_valid_response_normalizes_and_round_trips() -> None:
    """QA-E06-L2-001 (FR-015, CT-15; Story 6.1 AC1): a valid provider response normalizes
    to a CT-10 producer value carrying the required identity/bitemporal fields and, when
    price-bearing, separate bid/ask; the observation to_row/from_row round-trips exactly.
    """
    ing = ExternalSourceIngest(port=None)
    rec = H.provider_record(
        foreign_timestamp=H.foreign_timestamp_block(),
        foreign_money=H.foreign_money_block(),
        bid=H.foreign_money_block(109000, 5),
        ask=H.foreign_money_block(110000, 5),
    )
    obs, key, inst, quote = H.unwrap(
        ing.normalize(rec, writer=H.writer(), sequence=3, world=World.LIVE, receive_wall_time=_RECV))
    assert obs.source == "dukascopy" and obs.source_native_id == "occ-1" and obs.revision == "r1"
    assert obs.event_time.value_ns == 1_000 and obs.known_at.value_ns == 2_000
    assert quote is not None and quote.bid.verbatim == 109000 and quote.ask.verbatim == 110000
    # encode/decode semantic equality (fp1 survives the round-trip)
    rebuilt = H.unwrap(SourceObservation.from_row(obs.to_row()))
    assert rebuilt.fingerprint.value == obs.fingerprint.value
    # Counter-case: a tampered row fails to re-fingerprint (from_row refuses).
    row = obs.to_row()
    row["revision"] = "tampered"
    H.assert_refusal(SourceObservation.from_row(row), "invalid input")


# --- QA-E06-L2-002 — idempotent intake, revision = new artifact --------------


def test_l2_002_idempotent_key_revision_new_artifact() -> None:
    """QA-E06-L2-002 (CT-15 idempotent-intake; Story 6.1 AC2): a duplicate keys on
    (source, native id, revision) and is idempotent; a new revision is a NEW artifact with
    its own fp1 — never a collision — and earlier evidence is not erased or merged.
    """
    ing = ExternalSourceIngest(port=None)
    r1 = H.unwrap(ing.intake(H.provider_record(revision="r1"), writer=H.writer(), sequence=0,
                             world=World.LIVE, receive_wall_time=_RECV))
    dup = H.unwrap(ing.intake(H.provider_record(revision="r1"), writer=H.writer(), sequence=5,
                              world=World.LIVE, receive_wall_time=9_999))
    r2 = H.unwrap(ing.intake(H.provider_record(revision="r2"), writer=H.writer(), sequence=1,
                             world=World.LIVE, receive_wall_time=_RECV))
    assert r1.outcome is IntakeOutcome.PRODUCED
    assert dup.outcome is IntakeOutcome.IDEMPOTENT
    assert dup.observation.fingerprint.value == r1.observation.fingerprint.value
    assert r2.outcome is IntakeOutcome.PRODUCED
    assert r2.observation.fingerprint.value != r1.observation.fingerprint.value


# --- QA-E06-L2-003 — missing required field → invalid input, no CT-10 --------


@pytest.mark.parametrize("field", ["event_time", "known_at", "source", "revision", "instrument"])
def test_l2_003_missing_required_field_refuses(field: str) -> None:
    """QA-E06-L2-003 (CT-15 refusal enum; Story 6.1 AC4): a record missing any of
    {event-time, known-at, source, revision, CT-03 instrument mapping} is an invalid-input
    refusal and emits NO CT-10 value.
    """
    ing = ExternalSourceIngest(port=None)
    result = ing.normalize(H.provider_record(**{field: None}), writer=H.writer(), sequence=0,
                           world=World.LIVE, receive_wall_time=_RECV)
    H.assert_refusal(result, "invalid input")


# --- QA-E06-L2-004 — provider unavailable / rate-limited → returned refusal --


def test_l2_004_provider_unavailable_returns_refusal_no_fabrication() -> None:
    """QA-E06-L2-004 (CT-15 boundary_refusal_categories; Story 6.1 AC5): a provider that
    is unavailable / rate-limited yields a RETURNED transient/unavailable refusal and NO
    fabricated observation.
    """
    for refusal, cat in ((H.unavailable_refusal(reason="down"), "unavailable dependency"),
                         (H.transient_refusal(reason="429"), "transient venue failure")):
        port = H.ListPort(refusal)
        ing = ExternalSourceIngest(port=port)
        out = ing.fetch_and_intake(SourceRequest(source="dukascopy", bounds={}),
                                   writer=H.writer(), world=World.LIVE, receive_wall_time=_RECV)
        H.assert_refusal(out, cat)
    # And through the real Dukascopy adapter when its transport returns unavailable.
    start, end = H.dukascopy_window()
    adapter = duk.DukascopyAdapter(H.BytesTransport(H.unavailable_refusal(reason="down")),
                                   instruments={"EURUSD": H.instrument()})
    out = adapter.fetch(SourceRequest(source="dukascopy",
                                      bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end}))
    H.assert_refusal(out, "unavailable dependency")


# --- QA-E06-L2-005 — nullability: identity tokens required, never null --------


@pytest.mark.parametrize("triple", [
    (None, "occ", "r1"), ("dukascopy", None, "r1"), ("dukascopy", "occ", None),
    ("", "occ", "r1"), ("dukascopy", "   ", "r1"), ("dukascopy", "occ", ""),
])
def test_l2_005_intake_key_tokens_required(triple: tuple) -> None:
    """QA-E06-L2-005 (CT-15 nullability): source, source_native_id, revision are required;
    null/blank identity content is refused (an absent value is an omitted key, never null).
    """
    H.assert_refusal(IntakeKey.try_create(*triple), "invalid input")


def test_l2_005_valid_triple_accepted() -> None:
    """Falsifiability control for L2-005: a fully-present triple is accepted."""
    key = H.unwrap(IntakeKey.try_create("dukascopy", "occ", "r1"))
    assert (key.source, key.source_native_id, key.revision) == ("dukascopy", "occ", "r1")


# --- QA-E06-L2-006 — verbatim timestamp/money; float inadmissible ------------


def test_l2_006_foreign_evidence_stored_verbatim() -> None:
    """QA-E06-L2-006 (CT-15 units/verbatim; Story 6.1 AC3): foreign timestamp keeps its
    declared zone/offset/resolution and foreign money its scaled integer at the declared
    scale — unrewritten; a binary float on the money path is inadmissible.
    """
    ing = ExternalSourceIngest(port=None)
    ts = H.foreign_timestamp_block(verbatim="2025-03-02T09:30:00.5", zone="America/New_York",
                                   offset="-05:00", resolution="deciseconds")
    obs, *_ = H.unwrap(ing.normalize(H.provider_record(foreign_timestamp=ts,
                                                       foreign_money=H.foreign_money_block(77, 2)),
                                     writer=H.writer(), sequence=0, world=World.LIVE,
                                     receive_wall_time=_RECV))
    assert obs.foreign_timestamp.verbatim == "2025-03-02T09:30:00.5"
    assert obs.foreign_timestamp.zone == "America/New_York"
    assert obs.foreign_timestamp.offset == "-05:00"
    assert obs.foreign_timestamp.resolution == "deciseconds"
    assert obs.foreign_money.verbatim == 77 and obs.foreign_money.scale == 2
    # float on the money path → refusal
    H.assert_refusal(ing.normalize(H.provider_record(foreign_money={"verbatim": 1.5, "scale": 2}),
                                   writer=H.writer(), sequence=0, world=World.LIVE,
                                   receive_wall_time=_RECV), "invalid input")


# --- QA-E06-L2-007 — CT-10 producer schema (producer-obligation only) --------


def test_l2_007_producer_value_satisfies_ct10_shape() -> None:
    """QA-E06-L2-007 (CT-10 producer clause; Story 6.1 AC1): the ingest-produced value
    carries distinct event-time/known-at, writer + boot-epoch + a non-negative sequence,
    a closed-set world, and an fp1 identity. (CT-10 cross-world/seal refusals are Epic 3's.)
    """
    ing = ExternalSourceIngest(port=None)
    obs, *_ = H.unwrap(ing.normalize(H.provider_record(), writer=H.writer(boot="boot-9"),
                                     sequence=7, world=World.REPLAY, receive_wall_time=_RECV))
    assert obs.event_time.value_ns != obs.known_at.value_ns
    assert obs.writer.boot_epoch_id == "boot-9"
    assert isinstance(obs.sequence, int) and obs.sequence == 7
    assert obs.world.value in {"live", "replay", "simulated"}
    assert obs.fingerprint.value.startswith("fp1:sha256:")


# --- QA-E06-L2-008 — bid/ask preserved separately, never a mid ---------------


def test_l2_008_bid_ask_never_merged_to_mid() -> None:
    """QA-E06-L2-008 (CT-15 bid/ask; Story 6.2 AC1): a tick preserves bid and ask
    separately (distinct values, no mid field); presenting a mid is a policy rejection.
    """
    quote = H.unwrap(TickQuote.try_create(bid=H.foreign_money_block(109000, 5),
                                          ask=H.foreign_money_block(110000, 5)))
    assert quote.bid.verbatim == 109000 and quote.ask.verbatim == 110000
    assert not hasattr(quote, "mid")
    H.assert_refusal(
        TickQuote.try_create(bid=H.foreign_money_block(1, 5), ask=H.foreign_money_block(2, 5),
                             mid=H.foreign_money_block(15, 5)), "policy rejection")
    # a record presenting a mid to the seam is refused
    ing = ExternalSourceIngest(port=None)
    H.assert_refusal(ing.normalize(H.provider_record(mid=H.foreign_money_block(15, 5)),
                                   writer=H.writer(), sequence=0, world=World.LIVE,
                                   receive_wall_time=_RECV), "policy rejection")


# --- QA-E06-L2-009 — corroborates / disagrees-with edges ---------------------


def _tick(source: str, native: str, quote: TickQuote, *, event_ns: int = 1_000) -> TickObservation:
    obs = H.unwrap(SourceObservation.try_create(
        event_time=event_ns, known_at=2_000, source=source, source_native_id=native,
        revision="r1", receive_wall_time=_RECV, writer=H.writer(), sequence=0, world=World.LIVE))
    return TickObservation(observation=obs, quote=quote, instrument=H.instrument())


def test_l2_009_agreement_corroborates_disagreement_visible() -> None:
    """QA-E06-L2-009 (CT-07 edge types; Story 6.2 AC2): two sources reporting the same fact
    select a corroborates edge on agreement and a disagrees-with edge on disagreement; the
    disagreement stays visible (both endpoints referenced) and is never averaged/merged.
    """
    q_same = H.foreign_money_block
    a = _tick("dukascopy", "a", H.unwrap(TickQuote.try_create(bid=q_same(109000, 5), ask=q_same(110000, 5))))
    b = _tick("broker", "b", H.unwrap(TickQuote.try_create(bid=q_same(109000, 5), ask=q_same(110000, 5))))
    c = _tick("broker", "c", H.unwrap(TickQuote.try_create(bid=q_same(109500, 5), ask=q_same(110500, 5))))
    agree = H.unwrap(relate_source_facts(a, b, writer=H.writer()))
    disagree = H.unwrap(relate_source_facts(a, c, writer=H.writer()))
    assert agree.edge_type == EDGE_CORROBORATES
    assert disagree.edge_type == EDGE_DISAGREES_WITH
    # disagreement stays visible: the edge references BOTH source fingerprints, not a merge
    assert disagree.from_ref.value == a.fingerprint.value
    assert disagree.to_ref.value == c.fingerprint.value
    assert a.quote.bid.verbatim == 109000 and c.quote.bid.verbatim == 109500  # neither averaged


# --- QA-E06-L2-010 — later revision linked, never overwriting ----------------


def test_l2_010_revision_linked_new_artifact() -> None:
    """QA-E06-L2-010 (CT-15 revision linkage; Story 6.2 AC3): a later revision keys as a
    new artifact linked to the earlier one via a supersedes edge (newer -> earlier), never
    overwriting it.
    """
    ing = ExternalSourceIngest(port=None)
    earlier = H.unwrap(ing.normalize(H.provider_record(revision="r1"), writer=H.writer(),
                                     sequence=0, world=World.LIVE, receive_wall_time=_RECV))[0]
    newer = H.unwrap(ing.normalize(H.provider_record(revision="r2"), writer=H.writer(),
                                   sequence=1, world=World.LIVE, receive_wall_time=_RECV))[0]
    edge = H.unwrap(link_revision(newer, earlier, writer=H.writer()))
    assert edge.edge_type == EDGE_SUPERSEDES
    assert edge.from_ref.value == newer.fingerprint.value
    assert edge.to_ref.value == earlier.fingerprint.value
    assert newer.fingerprint.value != earlier.fingerprint.value


# --- QA-E06-L2-011 — Dukascopy once into archive, source identity, CT-10 -----


def test_l2_011_dukascopy_records_retain_source_identity_and_convert() -> None:
    """QA-E06-L2-011 (Story 6.3 AC1): Dukascopy fetch emits provider records that retain
    external source identity 'dukascopy' and convert through the ingest seam into CT-10.
    """
    start, end = H.dukascopy_window()
    payload = H.bi5_bytes([(0, 110000, 109000, 1.0, 2.0), (1000, 110010, 109010, 1.0, 2.0)])
    key_path = duk.DukascopyHourKey.try_create("EURUSD", 2020, 2, 2, 0)  # month_0=2 → March
    transport = H.MappedBytesTransport({H.unwrap(key_path).path_reference: payload})
    adapter = duk.DukascopyAdapter(transport, instruments={"EURUSD": H.instrument()})
    records = H.unwrap(adapter.fetch(SourceRequest(source="dukascopy",
                       bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end})))
    assert len(records) == 2
    assert all(r.source == "dukascopy" for r in records)
    ing = ExternalSourceIngest(port=None)
    obs, *_ = H.unwrap(ing.normalize(records[0], writer=H.writer(), sequence=0, world=World.LIVE,
                                     receive_wall_time=_RECV))
    assert obs.source == "dukascopy"


# --- QA-E06-L2-012 — provenance + license gate -------------------------------


def test_l2_012_unlicensed_window_cannot_become_governed_evidence() -> None:
    """QA-E06-L2-012 (Story 6.3 AC2): every window records provenance + a license tag; a
    window without a recorded usage right offered for governed-evidence use is a typed
    refusal — an unlicensed window can never silently become governed evidence.
    """
    part = H.series_partition(source="dukascopy")
    unlicensed = H.unwrap(duk.LicensedSourceWindow.try_create(
        partition=part, license_tag="unknown", provenance={"tool": "acq"}))
    assert unlicensed.license_tag == duk.LicenseTag.UNKNOWN
    assert dict(unlicensed.provenance) == {"tool": "acq"}
    H.assert_refusal(duk.offer_for_governed_evidence(unlicensed), "policy rejection")
    H.assert_refusal(duk.offer_for_governed_evidence(H.unwrap(
        duk.LicensedSourceWindow.try_create(partition=part, license_tag="denied"))), "policy rejection")
    # Counter-case: a licensed window IS admitted.
    licensed = H.unwrap(duk.LicensedSourceWindow.try_create(partition=part, license_tag="internal-only"))
    assert is_ok(duk.offer_for_governed_evidence(licensed))


# --- QA-E06-L2-013 — malformed Dukascopy record → invalid input --------------


def test_l2_013_malformed_dukascopy_record_refused() -> None:
    """QA-E06-L2-013 (R-007; Story 6.3 AC3): a malformed bi5 payload or an unmappable
    symbol is an invalid-input refusal from the seven-category taxonomy — not admitted.
    """
    start, end = H.dukascopy_window()
    # malformed (non-LZMA) payload
    bad_transport = H.BytesTransport(Ok(b"\x00\x01not-lzma-bytes"))
    adapter = duk.DukascopyAdapter(bad_transport, instruments={"EURUSD": H.instrument()})
    H.assert_refusal(adapter.fetch(SourceRequest(source="dukascopy",
                     bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end})), "invalid input")
    # unmappable symbol (no CT-03 instrument)
    good = duk.DukascopyAdapter(H.BytesTransport(Ok(b"")), instruments={"EURUSD": H.instrument()})
    H.assert_refusal(good.fetch(SourceRequest(source="dukascopy",
                     bounds={"symbol": "GBPJPY", "start_ns": start, "end_ns": end})), "invalid input")


# --- QA-E06-L2-014 — keep-forever partition identity -------------------------


def test_l2_014_acquired_window_partitioned_by_source_instrument_window() -> None:
    """QA-E06-L2-014 (Story 6.3 AC5): an acquired window is keyed by its
    (source, instrument, time-window) partition and stamps download-once provenance.
    (Retention 'kept forever' is the Epic-3 store's L18 property — see RESULTS.md.)
    """
    start, end = H.dukascopy_window()
    payload = H.bi5_bytes([(0, 110000, 109000, 1.0, 2.0)])
    key_path = H.unwrap(duk.DukascopyHourKey.try_create("EURUSD", 2020, 2, 2, 0))
    adapter = duk.DukascopyAdapter(H.MappedBytesTransport({key_path.path_reference: payload}),
                                   instruments={"EURUSD": H.instrument()})
    H.unwrap(adapter.fetch(SourceRequest(source="dukascopy",
             bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end})))
    window = adapter.last_window
    assert window is not None
    assert window.partition.source == "dukascopy"
    assert window.partition.instrument.symbol == "EURUSD"
    assert window.partition.window.start.value_ns == start
    assert window.partition.window.end.value_ns == end
    assert window.provenance["acquisition"] == "download-once"


# --- QA-E06-L2-015 — calendar recorder keeps identity + revisions ------------


def test_l2_015_calendar_keeps_native_identity_and_revisions() -> None:
    """QA-E06-L2-015 (Story 6.4 AC1): the news-calendar recorder keeps provider-native
    identity and revisions through (source, native id, revision); each revision is a new
    artifact, corrections appended, never overwriting.
    """
    snap = H.calendar_json([H.sample_calendar_event(country="USD", impact="High")])
    r1 = H.unwrap(cal.decode_calendar_snapshot(snap, known_at_ns=_KNOWN, revision="r1"))
    r2 = H.unwrap(cal.decode_calendar_snapshot(snap, known_at_ns=_KNOWN, revision="r2"))
    assert r1[0].source == "news-calendar" and r1[0].revision == "r1"
    assert r1[0].source_native_id == r2[0].source_native_id  # same occurrence
    ing = ExternalSourceIngest(port=None)
    inst = H.instrument(H.venue("news-calendar"), "USD")
    o1 = H.unwrap(ing.normalize(r1[0].to_provider_record(inst), writer=H.writer(), sequence=0,
                                world=World.LIVE, receive_wall_time=_RECV))[0]
    o2 = H.unwrap(ing.normalize(r2[0].to_provider_record(inst), writer=H.writer(), sequence=1,
                                world=World.LIVE, receive_wall_time=_RECV))[0]
    assert o1.fingerprint.value != o2.fingerprint.value  # revision → new artifact


# --- QA-E06-L2-016 — impact verbatim, no severity, no window/permission ------


def test_l2_016_impact_verbatim_no_severity_no_permission() -> None:
    """QA-E06-L2-016 (Story 6.4 AC2): provider impact labels are stored verbatim; QMX
    mints no severity scale; the feed defines no window and holds no permission.
    """
    snap = H.calendar_json([H.sample_calendar_event(impact="Medium-Custom-Label")])
    events = H.unwrap(cal.decode_calendar_snapshot(snap, known_at_ns=_KNOWN))
    assert events[0].impact_label == "Medium-Custom-Label"  # verbatim, not remapped
    adapter = cal.CalendarFeedAdapter(H.SnapshotTransport(Ok(snap)))
    H.assert_refusal(adapter.mint_severity_scale(), "policy rejection")
    H.assert_refusal(adapter.live_skip(), "policy rejection")


# --- QA-E06-L2-017 — every import journaled as 'data quality' ----------------


def _run_calendar_import(tmp_path, snapshot_result, **run_kw):
    store = H.make_store(tmp_path)
    ws = H.unwrap(store.for_world(World.LIVE))
    jwriter = JournalWriter(ws.journal, H.writer(role="data", stream="calendar"), stream_name="calendar")
    adapter = cal.CalendarFeedAdapter(H.SnapshotTransport(snapshot_result))
    ingest = ExternalSourceIngest(port=adapter)
    imp = cal.CalendarFeedImport(adapter, ingest, jwriter,
                                 currency_exposures=run_kw.pop("exposures", None))
    req = SourceRequest(source="news-calendar", bounds={"known_at_ns": _KNOWN, "revision": "r1"})
    result = imp.run(req, writer=H.writer(role="data", stream="obs"), world=World.LIVE,
                     receive_wall_time=_RECV, journal_instant=_JINSTANT, **run_kw)
    events = H.unwrap(JournalReader(ws.journal).read("calendar", for_world=World.LIVE))
    return result, events


def test_l2_017_import_journaled_as_data_quality(tmp_path) -> None:
    """QA-E06-L2-017 (Story 6.4 AC3; CT-13 event types): every import is journaled as a
    'data quality' event in the ratified CT-13 journal (one of the seven types), read back
    through the real journal store.
    """
    snap = H.calendar_json([H.sample_calendar_event(country="USD")])
    result, events = _run_calendar_import(tmp_path, Ok(snap))
    assert is_ok(result)
    assert len(events) == 1
    assert events[0].event_type.value == "data quality"
    assert events[0].payload.get("signal") == "calendar-import"


# --- QA-E06-L2-018 — retention posture recorded, not claimed authorized ------


def test_l2_018_no_authorized_retention_claim(tmp_path) -> None:
    """QA-E06-L2-018 (Story 6.4 AC5): the recorder claims no operational-retention
    authorization; the legal archiving posture rides through as recorded-not-resolved.
    """
    adapter = cal.CalendarFeedAdapter(H.SnapshotTransport(Ok(H.calendar_json([]))))
    H.assert_refusal(adapter.claim_retention_authorized(), "policy rejection")
    assert cal.LEGAL_ARCHIVING_POSTURE == "open-operator-item"
    snap = H.calendar_json([H.sample_calendar_event(country="USD")])
    _result, events = _run_calendar_import(tmp_path, Ok(snap))
    payload = events[0].payload
    assert payload.get("legal_archiving_posture") == "open-operator-item"
    assert payload.get("defines_window") is False and payload.get("holds_permission") is False
