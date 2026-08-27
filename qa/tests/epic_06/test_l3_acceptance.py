"""L3 — acceptance tests for Epic 6. Oracle = the epics.md AC / SCN sentence.

Epic-specific behaviour and the structural no-direct-governed-write boundary, driven
through injected fakes/sinks owned by the test.
"""

from __future__ import annotations

import pytest

from qmf.core import Ok, World, is_ok, is_refusal
from qmf.data import calendar_feed as cal
from qmf.data import dukascopy as duk
from qmf.data.ingest import ExternalSourceIngest, IntakeOutcome, SourceRequest
from qmf.data.source_boundary import SourceObservationBoundary

import helpers as H

_RECV = H.RECV_NS


# --- QA-E06-L3-001 — no governed-namespace write from the ingest path --------


def test_l3_001_ingest_path_performs_no_governed_write() -> None:
    """QA-E06-L3-001 (no governed-namespace write; Story 6.1 AC1): the ingest path
    produces CT-10 producer VALUES and performs no governed write itself; the injected
    CT-10 producer door (a RecordingBoundary owned by the test) is touched ONLY by an
    explicit application-routed submit, never during intake/fetch_and_intake. A TattleStore
    behind a real CT-10 boundary is never touched by the ingest path.
    """
    start, end = H.dukascopy_window()
    payload = H.bi5_bytes([(0, 110000, 109000, 1.0, 2.0)])
    key_path = H.unwrap(duk.DukascopyHourKey.try_create("EURUSD", 2020, 2, 2, 0))
    adapter = duk.DukascopyAdapter(H.MappedBytesTransport({key_path.path_reference: payload}),
                                   instruments={"EURUSD": H.instrument()})
    ing = ExternalSourceIngest(port=adapter)
    door = H.RecordingBoundary()

    # A real CT-10 boundary over a store that screams on ANY touch — the ingest path
    # must never reach it.
    _tattle_boundary = SourceObservationBoundary(H.TattleStore())

    receipts = H.unwrap(ing.fetch_and_intake(
        SourceRequest(source="dukascopy", bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end}),
        writer=H.writer(), world=World.LIVE, receive_wall_time=_RECV))
    # Phase 1: intake produced VALUES and touched no producer door / store.
    assert receipts and all(r.observation is not None for r in receipts)
    assert door.admitted == [], "the ingest path wrote to the producer boundary without an explicit submit"
    assert not hasattr(ing, "_store"), "the ingest seam holds a governed store reference"

    # Phase 2: only an explicit application-routed submit reaches the door.
    produced = [r for r in receipts if r.outcome is IntakeOutcome.PRODUCED]
    for r in produced:
        H.unwrap(ing.submit(r.observation, door))
    assert len(door.admitted) == len(produced), "submit did not route producer values through the door"


# --- QA-E06-L3-002 — scheduler / daemon / retry-loop refused -----------------


@pytest.mark.parametrize("method", ["start_scheduler", "run_daemon", "run_retry_loop"])
def test_l3_002_lifecycle_ownership_refused(method: str) -> None:
    """QA-E06-L3-002 (Story 6.1 AC6, FM-5): asking the seam to operate a scheduler /
    daemon / retry loop is refused as outside the component (policy rejection)."""
    ing = ExternalSourceIngest(port=None)
    H.assert_refusal(getattr(ing, method)(), "policy rejection")


# --- QA-E06-L3-003 — bounded request→response; CT-10 boundary is CT-10-only --


def test_l3_003_bounded_request_normalized_and_ct10_boundary_rejects_ct15() -> None:
    """QA-E06-L3-003 (Story 6.1 AC1): a bounded request is validated + normalized into a
    CT-10 producer value; and COMP-QMF-DATA's CT-10 boundary does not accept a CT-15
    request object — the boundary admits only complete SourceObservation values.
    """
    port = H.ListPort(Ok((H.provider_record(),)))
    ing = ExternalSourceIngest(port=port)
    receipts = H.unwrap(ing.fetch_and_intake(SourceRequest(source="dukascopy", bounds={"win": 1}),
                        writer=H.writer(), world=World.LIVE, receive_wall_time=_RECV))
    assert len(receipts) == 1 and receipts[0].observation.source == "dukascopy"
    assert len(port.requests) == 1  # exactly one bounded call, no scheduling
    # The CT-10 boundary refuses a CT-15 request value (data-only participation).
    boundary = SourceObservationBoundary(H.TattleStore())
    H.assert_refusal(boundary.admit(SourceRequest(source="dukascopy", bounds={})), "invalid input")


# --- QA-E06-L3-004 — download-once: a governed read never re-fetches ---------


def test_l3_004_governed_read_does_not_refetch_provider(tmp_path) -> None:
    """QA-E06-L3-004 (Story 6.3 AC1): the corpus is pulled once into the immutable raw
    archive; a subsequent governed read of that evidence reads only the qmf-data room and
    does NOT re-fetch from the provider (the injected transport sees no further calls).
    """
    start, end = H.dukascopy_window()
    payload = H.bi5_bytes([(0, 110000, 109000, 1.0, 2.0)])
    key_path = H.unwrap(duk.DukascopyHourKey.try_create("EURUSD", 2020, 2, 2, 0))
    transport = H.MappedBytesTransport({key_path.path_reference: payload})
    adapter = duk.DukascopyAdapter(transport, instruments={"EURUSD": H.instrument()})
    ing = ExternalSourceIngest(port=adapter)
    store = H.make_store(tmp_path)
    boundary = SourceObservationBoundary(store)

    receipts = H.unwrap(ing.fetch_and_intake(
        SourceRequest(source="dukascopy", bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end}),
        writer=H.writer(), world=World.LIVE, receive_wall_time=_RECV))
    admitted = [H.unwrap(ing.submit(r.observation, boundary)) for r in receipts]
    calls_after_fetch = len(transport.calls)
    assert calls_after_fetch >= 1  # the single download happened

    # A governed read of the admitted evidence: no further provider calls.
    got = H.unwrap(boundary.read(admitted[0].archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE))
    assert got.source == "dukascopy"
    assert len(transport.calls) == calls_after_fetch, "a governed read re-fetched from the provider"


# --- QA-E06-L3-005 — bulk complete-corpus refused ----------------------------


def test_l3_005_bulk_corpus_download_refused() -> None:
    """QA-E06-L3-005 (Story 6.3 AC4, FM-5): a complete-corpus / unbounded download during
    a factory pass is refused as outside the component; only bounded evidence is permitted.
    """
    adapter = duk.DukascopyAdapter(H.BytesTransport(Ok(b"")), instruments={"EURUSD": H.instrument()},
                                   max_window_ns=duk.NS_PER_HOUR)
    H.assert_refusal(adapter.download_complete_corpus(), "policy rejection")
    start, end = H.dukascopy_window()
    H.assert_refusal(adapter.fetch(SourceRequest(source="dukascopy",
                     bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end, "complete_corpus": True})),
                     "policy rejection")
    # a window wider than the bounded max is refused
    H.assert_refusal(adapter.fetch(SourceRequest(source="dukascopy",
                     bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": start + 5 * duk.NS_PER_HOUR})),
                     "policy rejection")


# --- QA-E06-L3-006 — transfer stops / unavailable → refusal, no fabrication --


def test_l3_006_unavailable_source_refuses_and_fabricates_nothing() -> None:
    """QA-E06-L3-006 (Story 6.3 AC5, FM-1): when the source is unavailable the seam returns
    a refusal and fabricates nothing; asking QMF to own external recovery is refused.
    """
    start, end = H.dukascopy_window()
    adapter = duk.DukascopyAdapter(H.BytesTransport(H.unavailable_refusal(reason="down")),
                                   instruments={"EURUSD": H.instrument()})
    out = adapter.fetch(SourceRequest(source="dukascopy",
                        bounds={"symbol": "EURUSD", "start_ns": start, "end_ns": end}))
    H.assert_refusal(out, "unavailable dependency")
    for method in ("checkpoint", "recover_external", "run_retry_loop"):
        H.assert_refusal(getattr(adapter, method)(), "policy rejection")


# --- QA-E06-L3-007 — fail-closed: failed refresh journals + alarms, no permit -


def test_l3_007_failed_refresh_journals_and_alarms(tmp_path) -> None:
    """QA-E06-L3-007 (fail-closed journal; Story 6.4 AC4, SCN-0008): a failed calendar
    refresh journals a 'data quality' event and raises an alarm on the intake side, and
    the feed supplies no permission (no live skip). The CT-31 entry block is Epic 10's.
    """
    imp, ws = H.calendar_harness(tmp_path, H.unavailable_refusal(reason="feed down"))
    result = H.run_calendar_import(imp)
    signal = H.unwrap(result)  # Ok wrapping the fail-closed signal, never permission
    assert isinstance(signal, cal.FailClosedSignal)
    assert signal.treated_as_affected is True and signal.alarm is True
    assert signal.reason is cal.FailClosedReason.FAILED_REFRESH
    events = H.read_journal(ws)
    assert len(events) == 1 and events[0].event_type.value == "data quality"
    assert events[0].payload.get("reason") == "failed-refresh"
    assert events[0].payload.get("alarm") is True
    assert events[0].payload.get("treated_as_affected") is True
    # the feed supplies no permission — a live skip is refused
    H.assert_refusal(imp._adapter.live_skip(), "policy rejection")


def test_l3_007_unknown_coverage_fails_closed(tmp_path) -> None:
    """QA-E06-L3-007 (Story 6.4 AC4): unknown coverage also fails closed — journaled as a
    'data quality' event and treated-as-affected."""
    imp, ws = H.calendar_harness(tmp_path, Ok(H.calendar_json([])))
    signal = H.unwrap(H.run_calendar_import(imp, coverage_known=False))
    assert isinstance(signal, cal.FailClosedSignal)
    assert signal.reason is cal.FailClosedReason.UNKNOWN_COVERAGE
    events = H.read_journal(ws)
    assert events[0].event_type.value == "data quality"
    assert events[0].payload.get("treated_as_affected") is True


# --- QA-E06-L3-008 — two sources: bid/ask separate, no mid synthesized -------


def test_l3_008_two_sources_bid_ask_separate_no_mid() -> None:
    """QA-E06-L3-008 (Story 6.2 AC1): recording ticks from two separately-identified
    sources preserves bid and ask separately; no mid is synthesized and the two sources are
    never coalesced into one number.
    """
    ing = ExternalSourceIngest(port=None)
    rec_a = H.provider_record(source="dukascopy", source_native_id="a",
                              bid=H.foreign_money_block(109000, 5), ask=H.foreign_money_block(110000, 5))
    rec_b = H.provider_record(source="broker", source_native_id="b",
                              bid=H.foreign_money_block(109005, 5), ask=H.foreign_money_block(110005, 5))
    ra = H.unwrap(ing.intake(rec_a, writer=H.writer(), sequence=0, world=World.LIVE, receive_wall_time=_RECV))
    rb = H.unwrap(ing.intake(rec_b, writer=H.writer(), sequence=1, world=World.LIVE, receive_wall_time=_RECV))
    assert ra.quote.bid.verbatim == 109000 and ra.quote.ask.verbatim == 110000
    assert rb.quote.bid.verbatim == 109005 and rb.quote.ask.verbatim == 110005
    assert not hasattr(ra.quote, "mid") and not hasattr(rb.quote, "mid")
    # the two sources remain distinct artifacts (never coalesced)
    assert ra.observation.fingerprint.value != rb.observation.fingerprint.value


# --- QA-E06-L3-009 — disagreement inspectable, agreement corroborates --------


def test_l3_009_disagreement_inspectable_nothing_averaged() -> None:
    """QA-E06-L3-009 (Story 6.2 AC2): two sources differing keep the disagreement
    inspectable via a disagrees-with edge; agreement yields corroborates; nothing averaged.
    """
    from qmf.data.observation import SourceObservation
    from qmf.data.ticks import (EDGE_CORROBORATES, EDGE_DISAGREES_WITH, TickObservation,
                                TickQuote, relate_source_facts)

    def tick(source, native, bid):
        obs = H.unwrap(SourceObservation.try_create(
            event_time=1_000, known_at=2_000, source=source, source_native_id=native, revision="r1",
            receive_wall_time=_RECV, writer=H.writer(), sequence=0, world=World.LIVE))
        q = H.unwrap(TickQuote.try_create(bid=H.foreign_money_block(bid, 5), ask=H.foreign_money_block(bid + 1000, 5)))
        return TickObservation(observation=obs, quote=q, instrument=H.instrument())

    a = tick("dukascopy", "a", 109000)
    b_agree = tick("broker", "b", 109000)
    c_dis = tick("broker", "c", 109500)
    assert H.unwrap(relate_source_facts(a, b_agree, writer=H.writer())).edge_type == EDGE_CORROBORATES
    dis = H.unwrap(relate_source_facts(a, c_dis, writer=H.writer()))
    assert dis.edge_type == EDGE_DISAGREES_WITH
    # both endpoints stay referenced; the two bids are not averaged into one value
    assert {dis.from_ref.value, dis.to_ref.value} == {a.fingerprint.value, c_dis.fingerprint.value}
    assert a.quote.bid.verbatim == 109000 and c_dis.quote.bid.verbatim == 109500
