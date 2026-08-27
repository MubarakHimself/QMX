"""Epic 18 · L2 — ``data verify`` window integrity (Story 18.4).

T18-4a  checks both-present + monotonic int64 + exact ints; typed counts   (RQ23)
T18-4b  edge tolerance configurable; blank ⇒ un-armed, raw offsets reported (RQ24)
T18-4d  interior gaps reported, never filled                                (RQ26)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from qmf.core.refusal import is_ok, is_refusal

from _e18 import NS, store_at

from qmb.data.verify import verify


def _verify(ticks, *, dest, **kw):
    base = {
        "archive": str(dest),
        "venue": "dukascopy",
        "symbol": "EURUSD",
        "start_ns": NS,
        "end_ns": NS + 1000,
        "side": "both",
        "ticks": ticks,
        "world": "replay",
    }
    base.update(kw)
    return verify(base, store=store_at(dest))


# --- T18-4a  clean window: typed pass with counts (RQ23) ----------------------
def test_t18_4a_clean_window_passes_with_counts() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        ticks = [{"t_ns": NS + i, "bid": 110_000 + i, "ask": 110_020 + i} for i in range(5)]
        res = _verify(ticks, dest=dest)
        assert is_ok(res), res
        v = res.value
        assert v.verdict == "pass"
        assert v.counts.observation_count == 5
        assert v.counts.bid_present == 5 and v.counts.ask_present == 5
        assert v.counts.defect_count == 0
        assert v.is_edge_claim is False


def test_t18_4a_non_monotonic_and_missing_side_are_defects() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        # decreasing timestamp
        res = _verify(
            [{"t_ns": NS + 5, "bid": 1, "ask": 2}, {"t_ns": NS, "bid": 1, "ask": 2}], dest=dest
        )
        assert is_refusal(res), "a non-monotonic window must not silently pass"
        codes = {d["code"] for d in res.context["result"]["defects"]}
        assert "non_monotonic_timestamp" in codes
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = _verify([{"t_ns": NS, "bid": 110_000}], dest=dest)  # ask missing
        assert is_refusal(res)
        codes = {d["code"] for d in res.context["result"]["defects"]}
        assert "missing_requested_side" in codes


# --- T18-4b  edge tolerance is a configurable, un-armed-by-default interface ---
def test_t18_4b_blank_tolerance_leaves_guard_unarmed_reports_raw_offsets() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        # ticks far inside the window edges; NO edge_tolerance supplied.
        ticks = [{"t_ns": NS + 500, "bid": 1, "ask": 2}, {"t_ns": NS + 600, "bid": 1, "ask": 2}]
        res = _verify(ticks, dest=dest)
        assert is_ok(res), "an un-armed edge guard must not fail against a fabricated threshold"
        v = res.value
        assert v.edge_guard_armed is False
        assert v.edge_tolerance_ns is None
        # Raw offsets are reported, not judged.
        assert v.edge_start_offset_ns == 500
        assert v.edge_end_offset_ns == 400
        assert all(dft.code != "edge_offset_beyond_tolerance" for dft in v.defects)


def test_t18_4b_armed_tolerance_exceeded_is_a_defect() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        ticks = [{"t_ns": NS + 500, "bid": 1, "ask": 2}]
        res = _verify(ticks, dest=dest, edge_tolerance_ns=10)  # 500 > 10
        assert is_refusal(res)
        codes = {dft["code"] for dft in res.context["result"]["defects"]}
        assert "edge_offset_beyond_tolerance" in codes


# --- T18-4d  interior gaps reported, never filled (RQ26) ----------------------
def test_t18_4d_interior_gaps_reported_never_filled() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        # step=10ns; a 100ns hole between the two ticks.
        ticks = [{"t_ns": NS, "bid": 1, "ask": 2}, {"t_ns": NS + 100, "bid": 1, "ask": 2}]
        res = _verify(ticks, dest=dest, expected_step_ns=10)
        # Interior gaps do not by themselves fail the verdict; but they are
        # reported and NEVER filled.
        report = res.value.as_mapping() if is_ok(res) else res.context["result"]
        gaps = report["interior_gaps"]
        assert gaps, "an interior hole must be reported"
        for gap in gaps:
            assert gap["filled"] is False
        assert report["fills_gaps"] is False
        # Observing the store: verify wrote no synthetic observations.
        from _e18 import scan_raw_observations

        assert scan_raw_observations(store_at(dest)) == ()
