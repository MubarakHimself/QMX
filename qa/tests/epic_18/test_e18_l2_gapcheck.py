"""Epic 18 · L2 — ``data gap-check`` calendar-aware gap detection (Story 18.5).

T18-5a  resolves sessions from a CT-02 calendar; gaps (start,end,expected,present);
        records the calendar version                                        (RQ28/RQ31)
T18-5b  calendar decides closure-vs-gap: closed absence ≠ gap; open absence = gap (RQ29)
T18-5c  a 24/7 always-open calendar: every interior absence is a gap        (RQ30)
T18-5e  gap-check only reports; an explicit fill request is refused         (RQ32)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from qmf.core.refusal import is_ok, is_refusal

from _e18 import (
    NS,
    ControlledCalendar,
    calendar_identity,
    store_at,
)

from qmb.data.gap_check import AlwaysOpenCalendar, gap_check


def _req(dest, **kw):
    base = {
        "archive": str(dest),
        "venue": "dukascopy",
        "symbol": "EURUSD",
        "start_ns": NS,
        "end_ns": NS + 10,
        "side": "both",
        "bar_step_ns": 1,
        "world": "replay",
    }
    base.update(kw)
    return base


# --- T18-5a  session resolution + gap shape + recorded version (RQ28/RQ31) -----
def test_t18_5a_reports_gaps_and_records_calendar_version() -> None:
    cal = ControlledCalendar(identity=calendar_identity(version="v9"), open_spans=((NS, NS + 10),))
    rows = [{"t_ns": NS + i} for i in range(10) if i != 4]  # one hole at NS+4
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = gap_check(_req(dest, rows=rows), store=store_at(dest), calendar=cal)
    assert is_ok(res), res
    report = res.value
    assert report.calendar["rule_set_version"] == "v9"
    assert report.gaps, "the interior hole must be reported"
    g = report.gaps[0].as_mapping()
    assert set(g) >= {"start", "end", "expected", "present"}
    assert g["present"] == 0 and g["expected"] >= 1
    assert g["start"] == NS + 4


# --- T18-5b  calendar decides closure-vs-gap (RQ29) ---------------------------
def test_t18_5b_closed_absence_is_not_a_gap_open_absence_is() -> None:
    # Open only on [NS, NS+10); [NS+10, NS+20) is CLOSED.
    cal = ControlledCalendar(identity=calendar_identity(), open_spans=((NS, NS + 10),))
    # Bars present across the open session EXCEPT one hole at NS+5; nothing in the
    # closed region [NS+10, NS+20).
    rows = [{"t_ns": NS + i} for i in range(10) if i != 5]
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = gap_check(
            _req(dest, end_ns=NS + 20, rows=rows), store=store_at(dest), calendar=cal
        )
    assert is_ok(res), res
    gaps = res.value.gaps
    # Exactly the open-session hole is a gap; the closed region is NOT reported.
    assert len(gaps) == 1, [g.as_mapping() for g in gaps]
    assert gaps[0].start_ns == NS + 5
    assert all(g.start_ns < NS + 10 for g in gaps), "closed-session absence misclassified as a gap"


# --- T18-5c  24/7 venue: every interior absence is a gap (RQ30) ---------------
def test_t18_5c_always_open_every_interior_absence_is_a_gap() -> None:
    rows = [{"t_ns": NS}, {"t_ns": NS + 3}]  # holes at NS+1, NS+2 across [NS, NS+4)
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = gap_check(
            _req(dest, end_ns=NS + 4, always_open=True, rows=rows, rule_set="always-open",
                 rule_set_version="v1", tzdata_version="none"),
            store=store_at(dest),
        )
    assert is_ok(res), res
    gaps = res.value.gaps
    assert len(gaps) == 1
    g = gaps[0]
    assert g.start_ns == NS + 1 and g.end_ns == NS + 3 and g.expected == 2


def test_t18_5c_always_open_calendar_type() -> None:
    # The always-open path uses the SUT's AlwaysOpenCalendar (no closure exemption).
    cal = AlwaysOpenCalendar(identity=calendar_identity(rule_set="always-open", version="v1"))
    assert cal.always_open is True


# --- T18-5e  gap-check refuses to fill (RQ32) ---------------------------------
def test_t18_5e_fill_request_is_policy_rejection() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = gap_check(
            _req(dest, always_open=True, rows=[{"t_ns": NS}], fill=True),
            store=store_at(dest),
        )
    assert is_refusal(res), "asking gap-check to write interior fill must be refused"
    assert res.category.value == "policy rejection"
    assert res.context.get("gap") == "GAP-0048"


def test_t18_5e_report_never_marks_fills() -> None:
    rows = [{"t_ns": NS}, {"t_ns": NS + 3}]
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = gap_check(
            _req(dest, end_ns=NS + 4, always_open=True, rows=rows), store=store_at(dest)
        )
    assert is_ok(res), res
    assert res.value.fills_gaps is False
    for g in res.value.as_mapping()["gaps"]:
        assert g["filled"] is False
