"""Epic 18 · L3 — contract conformance across the CT-* boundaries.

T18-1e  provider error ⇒ CT-04 refusal, NO partial ingest            (RQ4 / R-007)
T18-1h  persisted rows are shape-conformant CT-10 observations       (RQ6/RQ7)
        + FINDING: the CT-10 row carries no money-path (foreign_money)
T18-2e  passing tag ⇒ CT-07 entitlement lineage edge; gate writes nothing (RQ17)
T18-3e  door parity: CLI door payload == Python API door payload     (RQ22)
T18-4c  verify defect ⇒ CT-04 typed refusal, never a silent pass     (RQ25 / R-007)
T18-4e  verdict journaled as CT-13 data quality, correlation propagated (RQ27)
T18-5f  unresolvable calendar ⇒ 'unavailable dependency' refusal     (RQ33 / R-007)
T18-6a  every refusal is a valid RETURNED CT-04 value                (RQ34)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

from _e18 import (
    NS,
    ControlledCalendar,
    FakeAdapter,
    RecordingJournal,
    calendar_identity,
    download_resources,
    ok,
    provider_record,
    scan_raw_observations,
    store_at,
    writer,
)

from qmb.data.download import download
from qmb.data.gap_check import gap_check
from qmb.data.licensing import (
    AuthorityKind,
    SourceWindowRef,
    VenueLicensePolicy,
    admit_governed_evidence,
    entitlement_lineage_edge,
)
from qmb.data.verify import verify
from qmf.data.dukascopy import LicenseTag

_SEVEN = {c.value for c in RefusalCategory}
_RETRY = {r.value for r in Retryability}


def _assert_valid_ct04(ref: object) -> None:
    assert isinstance(ref, TypedRefusal), f"a refusal must be a RETURNED TypedRefusal: {ref!r}"
    assert ref.category.value in _SEVEN
    assert ref.retryability.value in _RETRY
    assert ref.context is not None
    assert len(ref.context) > 0, "CT-04 context must be present (non-empty)"


# --- T18-1e  provider error ⇒ refusal, no partial ingest (RQ4 / R-007) --------
def test_t18_1e_provider_error_refuses_without_partial_ingest() -> None:
    arms = {
        "geo-block-451": TypedRefusal(
            RefusalCategory.UNAVAILABLE_DEPENDENCY, Retryability.NO, {"http": 451, "field": "geo"}
        ),
        "maintenance": TypedRefusal(
            RefusalCategory.TRANSIENT_VENUE_FAILURE,
            Retryability.AFTER_CONDITION,
            {"field": "provider"},
            "retry-after",
        ),
        "missing-entitlement": TypedRefusal(
            RefusalCategory.POLICY_REJECTION, Retryability.NO, {"field": "entitlement"}
        ),
    }
    for name, ref in arms.items():
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "rooms"
            res = download(
                download_resources(dest),
                adapter=FakeAdapter((), fetch_refusal=ref),
                store=store_at(dest),
            )
            _assert_valid_ct04(res)
            assert res.category is ref.category, name
            # Observed through the store: nothing was ingested on the refusal path.
            assert scan_raw_observations(store_at(dest)) == (), f"{name}: partial ingest occurred"
            assert not (dest / "replay").exists(), f"{name}: wrote a world namespace on refusal"


def test_t18_1e_real_dukascopy_adapter_translates_bad_bytes() -> None:
    """Fault realism: the QMX adapter over a transport returning corrupt (non-LZMA)
    bytes yields an ``invalid input`` refusal, not a silent ingest."""
    from qmf.core.identity import Instrument
    from qmf.core import VenueId
    from qmb.data.dukascopy import DukascopyProviderAdapter
    from qmb.data.ports import DownloadSide, ProviderFetchRequest

    class _BadTransport:
        def fetch_hour(self, key, /):
            return Ok(b"not-lzma-bytes")

    v = ok(VenueId.try_create("dukascopy"))
    adapter = DukascopyProviderAdapter(
        _BadTransport(), instruments={"EURUSD": ok(Instrument.try_create(v, "EURUSD"))}
    )
    req = ProviderFetchRequest(
        source="dukascopy",
        symbol="EURUSD",
        start_ns=NS,
        end_ns=NS + 3_600_000_000_000,
        resolution="tick",
        side=DownloadSide.BOTH,
        revision="r1",
        license_tag="internal-only",
    )
    res = adapter.fetch(req)
    _assert_valid_ct04(res)
    assert res.category is RefusalCategory.INVALID_INPUT


# --- T18-1h  CT-10 shape (pass) + money-path (FINDING) ------------------------
def test_t18_1h_persisted_rows_are_ct10_shape_conformant() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = download(
            download_resources(dest),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS),)),
            store=store_at(dest),
        )
        assert is_ok(res), res
        rows = scan_raw_observations(store_at(dest))
        assert rows
        required = {
            "event_time_ns",
            "known_at_ns",
            "source",
            "source_native_id",
            "revision",
            "writer",
            "sequence",
            "world",
            "fingerprint",
        }
        for row in rows:
            assert required <= set(row), sorted(row)
            assert isinstance(row["event_time_ns"], int)
            assert row["world"] == "replay"
            assert row["source"] == "dukascopy"


def test_t18_1h_ct10_row_carries_money_path_FINDING() -> None:
    """18.1 AC3 / CT-01 / AR-15: prices are exact scaled integers written as CT-10
    observations. EXPECTED FAIL — the persisted observation carries no
    ``foreign_money`` (the tick prices are dropped by ``download``)."""
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = download(
            download_resources(dest),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS, bid=110_000, ask=110_020),)),
            store=store_at(dest),
        )
        assert is_ok(res), res
        rows = scan_raw_observations(store_at(dest))
        assert rows
        assert any("foreign_money" in row for row in rows), (
            "no CT-10 observation carries a scaled-integer price — download-once tick "
            "prices are not written to the raw archive (RQ6/RQ7)"
        )


def test_t18_1h_ct10_money_reads_back_exact_at_declared_scale() -> None:
    """18.1 AC3 / CT-01 / CT-10: archived price evidence is an exact
    integer at the provider-declared scale, never a float or silent rescale."""
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = download(
            download_resources(dest, side="bid"),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS, bid=110_000, ask=110_020),)),
            store=store_at(dest),
        )
        assert is_ok(res), res
        rows = scan_raw_observations(store_at(dest))
        assert rows
        money = rows[0].get("foreign_money")
        assert money == {"verbatim": 110_000, "scale": 5}
        assert isinstance(money["verbatim"], int) and not isinstance(money["verbatim"], bool)
        assert isinstance(money["scale"], int) and not isinstance(money["scale"], bool)


# --- T18-2e  entitlement lineage edge; gate writes nothing (RQ17) -------------
def test_t18_2e_passing_tag_rides_into_ct07_lineage_gate_writes_nothing() -> None:
    policy = {
        "dukascopy-fx": VenueLicensePolicy(
            "dukascopy-fx", LicenseTag.INTERNAL_ONLY, "DEC-0170", AuthorityKind.OPERATOR_RULING
        )
    }
    window = SourceWindowRef("dukascopy-fx", "EURUSD", NS, NS + 10, license_tag="internal-only")
    admission = admit_governed_evidence(window, policies=policy)
    assert is_ok(admission), admission
    payload = admission.value.lineage_payload()
    assert payload["license_tag"] == "internal-only"
    assert payload["granting_authority"] == "DEC-0170"

    citing = ok(fingerprint({"kind": "ct32", "run": 1}))
    edge = entitlement_lineage_edge(admission.value, citing_ref=citing, writer=writer("cite"))
    assert is_ok(edge), edge
    assert edge.value.edge_type.value == "occurrence-of"
    # The gate takes NO store/boundary/sink — it structurally cannot persist; and
    # it is pure: two calls yield identical admissions.
    again = admit_governed_evidence(window, policies=policy)
    assert is_ok(again)
    assert again.value.lineage_payload() == payload


# --- T18-3e  door parity: CLI door payload == Python API door payload (RQ22) ---
def test_t18_3e_cli_and_api_door_return_identical_catalog_payload() -> None:
    from qmb.doors.api import list_data as api_list_data
    from qmb.doors.cli.tree import invoke_data

    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        seeded = download(
            download_resources(dest),
            adapter=FakeAdapter((provider_record("EURUSD#1", NS),)),
            store=store_at(dest),
        )
        assert is_ok(seeded), seeded
        resources = {"destination": str(dest), "world": "replay"}
        api_report = api_list_data(resources)
        assert is_ok(api_report), api_report
        api_payload = api_report.value.as_mapping()

        cli_payload = invoke_data("list", resources)
        assert is_ok(cli_payload), cli_payload
        cli = cli_payload.value
        # The CLI door renders the SAME machine-readable coverage the API returns
        # verbatim: entries and view payload are byte-identical.
        assert cli["entries"] == api_payload["entries"]
        assert cli["view"] == api_payload["view"]
        assert cli["command"] == api_payload["command"] == "list"


# --- T18-4c  verify defect ⇒ CT-04 refusal, never a silent pass (RQ25/R-007) --
def test_t18_4c_verify_defects_refuse() -> None:
    cases = {
        "float-taint": [{"t_ns": NS, "bid": 1.5, "ask": 2}],
        "missing-side": [{"t_ns": NS, "bid": 1}],
        "empty-return": [],
    }
    for name, ticks in cases.items():
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "rooms"
            res = verify(
                {
                    "archive": str(dest),
                    "venue": "dukascopy",
                    "symbol": "EURUSD",
                    "start_ns": NS,
                    "end_ns": NS + 100,
                    "side": "both",
                    "ticks": ticks,
                    "world": "replay",
                },
                store=store_at(dest),
            )
            _assert_valid_ct04(res)
            assert res.category is RefusalCategory.POLICY_REJECTION, name
            assert res.context["result"]["verdict"] == "fail", name


# --- T18-4e  verdict journaled as CT-13; correlation propagated (RQ27) --------
def test_t18_4e_verdict_journaled_ct13_with_correlation() -> None:
    journal = RecordingJournal()
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = verify(
            {
                "archive": str(dest),
                "venue": "dukascopy",
                "symbol": "EURUSD",
                "start_ns": NS,
                "end_ns": NS + 100,
                "side": "both",
                "ticks": [{"t_ns": NS, "bid": 1, "ask": 2}],
                "world": "replay",
                "correlation_id": "corr-XYZ",
            },
            store=store_at(dest),
            journal_writer=journal,
        )
        assert is_ok(res), res
        assert res.value.journaled is True
        # Independently observed through the test-owned journal sink.
        assert len(journal.records) == 1
        rec = journal.records[0]
        assert rec["correlation_id"] == "corr-XYZ"
        payload = rec["payload"]
        assert payload["event_type_wire"] == "data quality"
        assert payload["is_edge_claim"] is False
        assert payload["kind"] == "qmb-data-window-integrity"


# --- T18-5f  unresolvable calendar ⇒ unavailable dependency (RQ33/R-007) ------
def test_t18_5f_unresolvable_calendar_refuses_unavailable_dependency() -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        res = gap_check(
            {
                "archive": str(dest),
                "venue": "nyse-equities",  # non-FX, no rule set → unresolvable
                "symbol": "AAPL",
                "start_ns": NS,
                "end_ns": NS + 10,
                "side": "both",
                "bar_step_ns": 1,
                "rows": [{"t_ns": NS}],
                "world": "replay",
            },
            store=store_at(dest),
        )
        _assert_valid_ct04(res)
        assert res.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
        assert res.context.get("signal") == "unavailable-calendar"


# --- T18-6a  every refusal is a valid RETURNED CT-04 value (RQ34) -------------
def test_t18_6a_all_epic18_refusals_are_valid_ct04_values() -> None:
    refusals: list[object] = []
    # bad download parse (missing venue)
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        refusals.append(
            download({"symbol": "EURUSD", "start_ns": NS, "end_ns": NS + 1, "destination": str(dest)},
                     adapter=FakeAdapter((provider_record("x", NS),)), store=store_at(dest))
        )
        # provider error
        refusals.append(
            download(
                download_resources(dest),
                adapter=FakeAdapter(
                    (), fetch_refusal=TypedRefusal(RefusalCategory.TRANSIENT_VENUE_FAILURE, Retryability.YES, {"field": "rate"})
                ),
                store=store_at(dest),
            )
        )
        # verify defect
        refusals.append(
            verify(
                {"archive": str(dest), "venue": "v", "symbol": "s", "start_ns": NS, "end_ns": NS + 5,
                 "side": "both", "ticks": [{"t_ns": NS, "bid": 1.5, "ask": 2}], "world": "replay"},
                store=store_at(dest),
            )
        )
        # licence denied
        refusals.append(
            admit_governed_evidence(SourceWindowRef("v", "s", NS, NS + 1, license_tag="denied"))
        )
        # unresolvable calendar
        refusals.append(
            gap_check(
                {"archive": str(dest), "venue": "nyse", "symbol": "AAPL", "start_ns": NS,
                 "end_ns": NS + 5, "side": "both", "bar_step_ns": 1, "rows": [{"t_ns": NS}], "world": "replay"},
                store=store_at(dest),
            )
        )
        # interior-fill request
        refusals.append(
            gap_check(
                {"archive": str(dest), "venue": "v", "symbol": "s", "start_ns": NS, "end_ns": NS + 5,
                 "side": "both", "bar_step_ns": 1, "always_open": True, "fill": True, "world": "replay"},
                store=store_at(dest),
            )
        )
    assert len(refusals) == 6
    for ref in refusals:
        _assert_valid_ct04(ref)
