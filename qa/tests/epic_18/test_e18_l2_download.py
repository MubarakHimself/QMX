"""Epic 18 · L2 — ``data download`` download-once acquisition (Story 18.1).

T18-1a  thin front: CT-10 evidence lands through the qmf-data boundary   (RQ1)
        + FINDING: a qmb-authored durable ledger is a second data layer   (RQ1/B-11)
T18-1b  request assembled from (venue, symbol[list], start, end, side)    (RQ2)
T18-1d  fetch flows through the QMX-authored provider-adapter port        (RQ3)
T18-1f  bid + ask preserved as distinct scaled-int streams                (RQ5) — EXPECTED FAIL
T18-1i  idempotent re-download writes no duplicate observation            (RQ8)
T18-1j  --overwrite appends a NEW CT-10 revision, retains the original    (RQ9)
T18-1k  a long import emits machine-observable progress to an injected sink (RQ10)
T18-1l  read commands reach only rooms — no provider port                 (RQ12)
T18-1m  each window records provenance + a licence tag (gate input)       (RQ11)
"""

from __future__ import annotations

import ast
import inspect
import tempfile
from pathlib import Path

from qmf.core.refusal import is_ok, is_refusal

from _e18 import (
    NS,
    FakeAdapter,
    RecordingProgressSink,
    download_resources,
    ok,
    provider_record,
    raw_observation_fingerprints,
    scan_raw_observations,
    store_at,
)

from qmb.data.catalog import list_data
from qmb.data.download import download, parse_download_request
from qmb.data.gap_check import gap_check
from qmb.data.ports import PROVIDER_ADAPTER_METHODS, ProviderAdapter
from qmb.data.verify import verify

_DATA = Path(__file__).resolve().parents[3] / "qmb" / "src" / "qmb" / "data"


def _download_ok(dest: Path, records=None, **over):
    recs = records if records is not None else (provider_record(f"EURUSD#{NS}", NS),)
    adapter = FakeAdapter(tuple(recs))
    res = download(download_resources(dest, **over), adapter=adapter, store=store_at(dest))
    return res, adapter


# --- T18-1a  persistence routes through the CT-10 boundary (RQ1) --------------
def test_t18_1a_ct10_evidence_lands_through_qmf_data_boundary() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res, _ = _download_ok(dest)
        assert is_ok(res), res
        # Observed independently: the raw archive under the world namespace holds
        # the observation, i.e. the write went through the qmf-data store.
        rows = scan_raw_observations(store_at(dest))
        assert len(rows) == 1
        assert (dest / "replay" / "immutable-raw-archive").is_dir()


def test_t18_1a_no_qmb_authored_second_data_layer_FINDING() -> None:
    """B-11: qmb-data mints no second data layer — qmf.data owns all persistence.

    EXPECTED FAIL — ``download`` writes its own durable ``.qmb_intake_keys.jsonl``
    dedup ledger (via ``qmb.orchestrator.paths``, outside the qmf.data contracts),
    even though the content-addressed CT-10 store already makes re-admits
    idempotent. That file is a persistence side-channel qmb authored itself.
    """
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res, _ = _download_ok(dest)
        assert is_ok(res), res
        ledger = dest / ".qmb_intake_keys.jsonl"
        assert not ledger.exists(), (
            "download persisted a qmb-authored durable ledger outside qmf.data "
            f"(second data layer, B-11): {ledger}"
        )


# --- T18-1b  request assembly + explicit reproducible end (RQ2) ---------------
def test_t18_1b_request_assembled_from_fields() -> None:
    parsed = parse_download_request(
        {
            "venue": "dukascopy",
            "symbol": "EURUSD, GBPUSD",
            "start_ns": NS,
            "end_ns": NS + 500,
            "resolution": "tick",
            "side": "both",
            "destination": "rooms",
        }
    )
    assert is_ok(parsed), parsed
    req = parsed.value
    assert req.venue == "dukascopy"
    assert req.symbols == ("EURUSD", "GBPUSD")
    assert req.start_ns == NS
    assert req.end_ns == NS + 500  # explicit end honoured verbatim → reproducible
    assert req.side.value == "both"


def test_t18_1b_symbol_list_form_accepted() -> None:
    parsed = parse_download_request(
        {
            "venue": "dukascopy",
            "symbol": ["EURUSD", "GBPUSD", "USDJPY"],
            "start_ns": NS,
            "end_ns": NS + 1,
            "destination": "rooms",
        }
    )
    assert is_ok(parsed), parsed
    assert parsed.value.symbols == ("EURUSD", "GBPUSD", "USDJPY")


# --- T18-1d  fetch flows through the QMX-authored port (RQ3) -------------------
def test_t18_1d_port_surface_and_fetch_is_called() -> None:
    assert PROVIDER_ADAPTER_METHODS == (
        "fetch",
        "earliest_available",
        "list_symbols",
        "batch_count",
        "rate_limit_per_second",
    )
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res, adapter = _download_ok(dest)
        assert is_ok(res), res
        # The provider fetch actually flowed through the injected port.
        assert len(adapter.fetch_calls) == 1
        req = adapter.fetch_calls[0]
        assert req.symbol == "EURUSD" and req.side.value == "both"


def test_t18_1d_dukascopy_adapter_one_is_a_provider_adapter() -> None:
    from qmf.core.identity import Instrument
    from qmf.core import VenueId
    from qmb.data.dukascopy import DukascopyProviderAdapter

    class _NullTransport:
        def fetch_hour(self, key, /):
            from qmf.core.refusal import Ok

            return Ok(b"")

    v = ok(VenueId.try_create("dukascopy"))
    adapter = DukascopyProviderAdapter(
        _NullTransport(), instruments={"EURUSD": ok(Instrument.try_create(v, "EURUSD"))}
    )
    assert isinstance(adapter, ProviderAdapter)
    assert adapter.source == "dukascopy"
    # The port surface is real, not just a declared constant: every named method /
    # property is present on the QMX adapter #1.
    for name in PROVIDER_ADAPTER_METHODS:
        assert hasattr(adapter, name), f"Dukascopy adapter missing port member {name}"
    assert callable(adapter.fetch) and callable(adapter.list_symbols)
    assert callable(adapter.earliest_available)
    assert isinstance(adapter.batch_count, int)


# --- T18-1f  bid + ask preserved as distinct streams (RQ5, AR-46) -------------
def test_t18_1f_bid_and_ask_preserved_in_ct10_evidence_FINDING() -> None:
    """AR-46 / 18.1 AC3: bid and ask land as distinct scaled-integer streams,
    written as CT-10 observations and retained forever.

    EXPECTED FAIL — the CT-15 intake builds a TickQuote from bid/ask, but
    ``download`` submits only the bare ``SourceObservation`` (``foreign_money``
    absent) and DISCARDS the quote. No bid/ask price is ever persisted to the raw
    archive, so a governed reader recovers timestamps with no prices.
    """
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        rec = provider_record("EURUSD#1", NS, bid=110_000, ask=110_020)
        res = download(download_resources(dest), adapter=FakeAdapter((rec,)), store=store_at(dest))
        assert is_ok(res), res
        rows = scan_raw_observations(store_at(dest))
        assert rows, "no observation persisted at all"
        recovered = {"foreign_money" in row or "bid" in row or "ask" in row for row in rows}
        assert recovered == {True}, (
            "persisted CT-10 evidence carries neither bid/ask nor foreign_money — the "
            "download-once tick prices are dropped (RQ5/RQ6/RQ7); persisted keys were "
            f"{sorted(rows[0].keys())}"
        )


# --- T18-1i  idempotent re-download (RQ8) -------------------------------------
def test_t18_1i_rerun_writes_no_duplicate() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        recs = tuple(provider_record(f"EURUSD#{NS + i}", NS + i) for i in range(3))
        r1 = download(download_resources(dest), adapter=FakeAdapter(recs), store=store_at(dest))
        assert is_ok(r1), r1
        fps1 = raw_observation_fingerprints(store_at(dest))
        r2 = download(download_resources(dest), adapter=FakeAdapter(recs), store=store_at(dest))
        assert is_ok(r2), r2
        fps2 = raw_observation_fingerprints(store_at(dest))
        assert fps1 == fps2 and len(fps1) == 3


# --- T18-1j  --overwrite appends a new revision, retains the original (RQ9) ----
def test_t18_1j_overwrite_appends_new_revision() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        r1 = download(
            download_resources(dest, revision="r1"),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS, revision="r1"),)),
            store=store_at(dest),
        )
        assert is_ok(r1), r1
        fps1 = raw_observation_fingerprints(store_at(dest))
        r2 = download(
            download_resources(dest, overwrite=True, revision="r2"),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS, revision="r2"),)),
            store=store_at(dest),
        )
        assert is_ok(r2), r2
        fps2 = raw_observation_fingerprints(store_at(dest))
        # A new revision is a distinct artifact; the original is retained (append,
        # never overwrite the only copy).
        assert fps1 <= fps2 and len(fps2) == 2, (fps1, fps2)


# --- T18-1k  machine-observable progress to an injected sink (RQ10) -----------
def test_t18_1k_progress_emitted_to_injected_sink() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        sink = RecordingProgressSink()
        res = download(
            download_resources(dest, symbol="EURUSD, GBPUSD"),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS),)),
            store=store_at(dest),
            progress=sink,
        )
        assert is_ok(res), res
        assert sink.samples, "no progress emitted to the injected sink"
        last = sink.samples[-1]
        assert last.percent == 100
        assert isinstance(last.date_reached_ns, int)
        assert last.completed_batches == last.total_batches


# --- T18-1l  read commands reach only rooms, no provider port (RQ12) -----------
def test_t18_1l_read_commands_hold_no_provider_port() -> None:
    # The read entrypoints take no provider adapter in their signature.
    for fn in (list_data, verify, gap_check):
        params = set(inspect.signature(fn).parameters)
        assert "adapter" not in params, f"{fn.__name__} exposes a provider adapter seam"
    # And no read module imports the ProviderAdapter port at all.
    offenders: list[str] = []
    for name in ("catalog.py", "verify.py", "gap_check.py"):
        tree = ast.parse((_DATA / name).read_text(encoding="utf-8"), filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "qmb.data.ports":
                imported = {a.name for a in node.names}
                if "ProviderAdapter" in imported:
                    offenders.append(f"{name}: imports ProviderAdapter")
    assert offenders == [], offenders


# --- T18-1m  provenance + licence tag recorded per window (RQ11) --------------
def test_t18_1m_window_records_provenance_and_license_tag() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = download(
            download_resources(dest, license_tag="internal-only"),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS),)),
            store=store_at(dest),
        )
        assert is_ok(res), res
        listed = list_data({"destination": str(dest), "world": "replay"})
        assert is_ok(listed), listed
        entries = listed.value.entries
        assert entries, "no catalog coverage recorded for the ingested window"
        for entry in entries:
            assert entry.license_tag == "internal-only", entry.as_mapping()
            assert entry.provenance is not None and dict(entry.provenance), entry.as_mapping()
