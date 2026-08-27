"""L4 — scenario / participation tests for Epic 6. Oracle = the SCN prose.

Cross-package journeys over the ingest seam + a real CT-10 boundary + the CT-07 edge
value + the CT-13 journal (light for T2). Effects observed through the real store sink.
"""

from __future__ import annotations

from qmf.core import Ok, World, is_ok
from qmf.data import calendar_feed as cal
from qmf.data.ingest import ExternalSourceIngest, SourceRequest
from qmf.data.source_boundary import SourceObservationBoundary
from qmf.data.ticks import EDGE_SUPERSEDES, link_revision

import helpers as H

_RECV = H.RECV_NS


# --- QA-E06-L4-001 — SCN-0002 late source correction preserves earlier -------


def test_l4_001_source_correction_preserves_original(tmp_path) -> None:
    """QA-E06-L4-001 (SCN-0002; Story 6.1 AC2/AC3): an original observation and a later
    correction to the SAME provider-native occurrence produce two distinct fp1 artifacts
    joined by an append-only supersedes lineage edge, with the original preserved unmutated
    end-to-end over the ingest seam + a real CT-10 boundary.
    """
    ing = ExternalSourceIngest(port=None)
    store = H.make_store(tmp_path)
    boundary = SourceObservationBoundary(store)

    original = H.unwrap(ing.normalize(
        H.provider_record(source_native_id="occ-42", revision="r1",
                          foreign_money=H.foreign_money_block(100, 2)),
        writer=H.writer(), sequence=0, world=World.LIVE, receive_wall_time=_RECV))[0]
    original_receipt = H.unwrap(ing.submit(original, boundary))

    correction = H.unwrap(ing.normalize(
        H.provider_record(source_native_id="occ-42", revision="r2",
                          foreign_money=H.foreign_money_block(101, 2),
                          correction_of=original.fingerprint),
        writer=H.writer(), sequence=1, world=World.LIVE, receive_wall_time=_RECV))[0]
    correction_receipt = H.unwrap(ing.submit(correction, boundary))

    # two distinct fp1 artifacts
    assert original.fingerprint.value != correction.fingerprint.value
    assert correction.is_correction and correction.correction_of.value == original.fingerprint.value

    # joined by an append-only supersedes edge (newer -> earlier)
    edge = H.unwrap(link_revision(correction, original, writer=H.writer()))
    assert edge.edge_type == EDGE_SUPERSEDES
    assert edge.from_ref.value == correction.fingerprint.value
    assert edge.to_ref.value == original.fingerprint.value

    # the original remains preserved, unmutated, and independently readable
    read_back = H.unwrap(boundary.read(original_receipt.archive.fingerprint,
                                       in_world=World.LIVE, for_world=World.LIVE))
    assert read_back.fingerprint.value == original.fingerprint.value
    assert read_back.foreign_money.verbatim == 100  # original evidence untouched by the correction
    assert correction_receipt.archive.fingerprint.value != original_receipt.archive.fingerprint.value


# --- QA-E06-L4-002 — SCN-0008 intake half: verbatim, append-only, fail-closed -


def test_l4_002_news_intake_verbatim_append_only_and_fail_closed(tmp_path) -> None:
    """QA-E06-L4-002 (SCN-0008 intake-side half; Story 6.4): the recorder ingests events
    and revisions keeping provider evidence verbatim and append-only (no read-time widening
    at intake), and a failed refresh journals 'data quality' + alarms. The CT-31 window
    resolution/enforcement is Epic 10's and is excluded here.
    """
    # Successful import: impact stored verbatim, no window/permission minted at intake.
    events_json = H.calendar_json([H.sample_calendar_event(country="USD", impact="High"),
                                   H.sample_calendar_event(country="EUR", impact="Low",
                                                           title="ECB", date="2026-08-16T08:15:00+02:00")])
    imp_ok, ws_ok = H.calendar_harness(tmp_path / "ok", Ok(events_json))
    result = H.run_calendar_import(imp_ok)
    receipt = H.unwrap(result)
    assert isinstance(receipt, cal.CalendarImportReceipt)
    # verbatim impact labels; no synthesized severity; append-only intake
    assert [e.impact_label for e in receipt.events] == ["High", "Low"]
    journal_ok = H.read_journal(ws_ok)
    assert journal_ok[0].event_type.value == "data quality"
    assert journal_ok[0].payload.get("defines_window") is False
    assert journal_ok[0].payload.get("holds_permission") is False
    # no read-time widening at intake — the recorded event carries no window/permission field
    for ev in receipt.events:
        assert not hasattr(ev, "window") and not hasattr(ev, "permission")

    # Failed refresh: fail-closed data-quality journal + alarm.
    imp_fail, ws_fail = H.calendar_harness(tmp_path / "fail", H.unavailable_refusal(reason="down"))
    signal = H.unwrap(H.run_calendar_import(imp_fail))
    assert isinstance(signal, cal.FailClosedSignal) and signal.alarm is True
    journal_fail = H.read_journal(ws_fail)
    assert journal_fail[0].event_type.value == "data quality"
    assert journal_fail[0].payload.get("reason") == "failed-refresh"
