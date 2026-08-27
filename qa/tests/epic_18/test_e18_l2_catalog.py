"""Epic 18 · L2 — ``data list`` / ``catalog`` coverage (Story 18.3).

T18-3a  reports [start,end], count, provenance, licence tag, revision   (RQ18)
T18-3b  rebuildable DuckDB view over Parquet rooms, never authoritative  (RQ19)
T18-3c  an absent window is a "not present" VALUE, not a refusal         (RQ20)
T18-3d  both requested, one present ⇒ missing side shown absent          (RQ21)
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from qmf.core.fingerprint import World
from qmf.core.refusal import is_ok, is_refusal

from _e18 import (
    NS,
    FakeAdapter,
    download_resources,
    provider_record,
    store_at,
)

from qmb.data.catalog import NOT_PRESENT, PRESENT, catalog, list_data, scan_coverage_rows
from qmb.data.download import download


def _seed(dest: Path, *, side: str = "both", symbol: str = "EURUSD") -> None:
    res = download(
        download_resources(dest, side=side, symbol=symbol),
        adapter=FakeAdapter((provider_record(f"{symbol}#1", NS),)),
        store=store_at(dest),
    )
    assert is_ok(res), res


# --- T18-3a  full coverage row (RQ18) -----------------------------------------
def test_t18_3a_reports_full_coverage_fields() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        _seed(dest)
        listed = list_data({"destination": str(dest), "world": "replay"})
        assert is_ok(listed), listed
        by_side = {e.side: e for e in listed.value.entries}
        assert set(by_side) == {"bid", "ask"}
        for entry in by_side.values():
            assert entry.status == PRESENT
            assert entry.start_ns == NS and entry.end_ns == NS + 10
            assert isinstance(entry.observation_count, int)
            assert entry.provenance is not None
            assert entry.license_tag is not None
            assert entry.revision is not None


# --- T18-3b  rebuildable DuckDB view, never authoritative (RQ19) --------------
def test_t18_3b_view_is_rebuildable_not_authoritative() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        _seed(dest)
        first = list_data({"destination": str(dest), "world": "replay"})
        assert is_ok(first), first
        report = first.value
        assert report.view_engine == "duckdb"
        assert report.is_evidence_bearing is False
        assert report.view_fingerprint is not None  # a view was materialised

        payload = report.as_mapping()["view"]
        assert payload["is_evidence_bearing"] is False

        # Drop the processed view store entirely; the catalog must rebuild it from
        # the Parquet rooms (the authority) and return identical coverage.
        processed = dest / "replay" / "processed"
        if processed.exists():
            shutil.rmtree(processed)
        second = list_data({"destination": str(dest), "world": "replay"})
        assert is_ok(second), second
        assert [e.as_mapping() for e in second.value.entries] == [
            e.as_mapping() for e in report.entries
        ]
        # Coverage is served straight from the Parquet rooms.
        rooms = scan_coverage_rows(store_at(dest), world=World.REPLAY)
        assert is_ok(rooms) and len(rooms.value) == len(report.entries)


# --- T18-3c  absent window is a VALUE, not a refusal (RQ20) --------------------
def test_t18_3c_absent_window_is_not_present_value() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        _seed(dest)
        listed = list_data(
            {
                "destination": str(dest),
                "world": "replay",
                "venue": "dukascopy",
                "symbol": "USDJPY",  # never ingested
                "resolution": "tick",
                "side": "bid",
                "start_ns": NS,
                "end_ns": NS + 10,
            }
        )
        assert is_ok(listed), "an absent window must be a VALUE, not a refusal"
        assert not is_refusal(listed)
        statuses = {e.status for e in listed.value.entries}
        assert NOT_PRESENT in statuses
        for e in listed.value.entries:
            if e.symbol == "USDJPY":
                assert e.status == NOT_PRESENT


# --- T18-3d  missing side shown absent (RQ21) ---------------------------------
def test_t18_3d_missing_side_shown_absent() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        _seed(dest, side="bid")  # only bid coverage recorded
        listed = list_data(
            {
                "destination": str(dest),
                "world": "replay",
                "venue": "dukascopy",
                "symbol": "EURUSD",
                "resolution": "tick",
                "side": "both",
                "start_ns": NS,
                "end_ns": NS + 10,
            }
        )
        assert is_ok(listed), listed
        by_side = {e.side: e for e in listed.value.entries}
        assert by_side["bid"].status == PRESENT
        assert by_side["ask"].status == NOT_PRESENT


# --- catalog is an alias of list (RQ18 door) ----------------------------------
def test_catalog_aliases_list() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        _seed(dest)
        via_list = list_data({"destination": str(dest), "world": "replay"})
        via_catalog = catalog({"destination": str(dest), "world": "replay"})
        assert is_ok(via_list) and is_ok(via_catalog)
        assert [e.as_mapping() for e in via_list.value.entries] == [
            e.as_mapping() for e in via_catalog.value.entries
        ]
