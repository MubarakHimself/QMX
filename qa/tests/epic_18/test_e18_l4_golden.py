"""Epic 18 · L4 — golden data-lifecycle walk (proposed SCN; PLAN §7.4).

T18-6b  download (explicit window, licensed tag) → list shows it with tag +
        revision → verify returns a typed pass → gap-check classifies gap-vs-closure
        deterministically. One controlled corpus, one store, all stages composed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from qmf.core.refusal import is_ok

from _e18 import (
    NS,
    ControlledCalendar,
    FakeAdapter,
    calendar_identity,
    download_resources,
    provider_record,
    store_at,
)

from qmb.data.catalog import PRESENT, list_data
from qmb.data.download import download
from qmb.data.gap_check import gap_check
from qmb.data.verify import verify


def test_t18_6b_download_list_verify_gapcheck_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        # Five ticks one ns apart over [NS, NS+10), licensed internal-only.
        records = tuple(provider_record(f"EURUSD#{NS + i}", NS + i) for i in range(5))

        # 1) download-once (explicit, reproducible window)
        acquired = download(
            download_resources(dest, license_tag="internal-only"),
            adapter=FakeAdapter(records),
            store=store_at(dest),
        )
        assert is_ok(acquired), acquired

        # 2) list shows the window with its tag + revision
        listed = list_data({"destination": str(dest), "world": "replay"})
        assert is_ok(listed), listed
        entries = {e.side: e for e in listed.value.entries}
        assert set(entries) == {"bid", "ask"}
        for entry in entries.values():
            assert entry.status == PRESENT
            assert entry.license_tag == "internal-only"
            assert entry.revision == "r1"

        # 3) verify returns a typed pass over injected controlled ticks
        ticks = [{"t_ns": NS + i, "bid": 110_000 + i, "ask": 110_020 + i} for i in range(5)]
        verdict = verify(
            {
                "archive": str(dest),
                "venue": "dukascopy",
                "symbol": "EURUSD",
                "start_ns": NS,
                "end_ns": NS + 10,
                "side": "both",
                "ticks": ticks,
                "world": "replay",
                "correlation_id": "golden-1",
            },
            store=store_at(dest),
        )
        assert is_ok(verdict), verdict
        assert verdict.value.verdict == "pass"

        # 4) gap-check classifies closure-vs-gap deterministically against a
        #    controlled calendar: open [NS, NS+10), closed [NS+10, NS+20).
        cal = ControlledCalendar(identity=calendar_identity(version="v3"), open_spans=((NS, NS + 10),))
        present_rows = [{"t_ns": NS + i} for i in range(5)]  # holes at NS+5..NS+9
        gaps = gap_check(
            {
                "archive": str(dest),
                "venue": "dukascopy",
                "symbol": "EURUSD",
                "start_ns": NS,
                "end_ns": NS + 20,
                "side": "both",
                "bar_step_ns": 1,
                "rows": present_rows,
                "world": "replay",
            },
            store=store_at(dest),
            calendar=cal,
        )
        assert is_ok(gaps), gaps
        report = gaps.value
        assert report.calendar["rule_set_version"] == "v3"
        # Gaps only inside the open session; the closed region is never a gap.
        assert report.gaps, "the open-session holes must be reported"
        assert all(g.start_ns < NS + 10 for g in report.gaps)
