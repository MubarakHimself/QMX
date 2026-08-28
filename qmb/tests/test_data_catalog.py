"""Tier-1 tests for ``qmb data list`` / catalog coverage (Story 18.3, B-11)."""

from __future__ import annotations

import json
import lzma
import struct
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar, cast

from click.testing import CliRunner
from qmb.data import (
    COVERAGE_KIND,
    NOT_PRESENT,
    PRESENT,
    DukascopyProviderAdapter,
    catalog,
    catalog_identity,
    data_front_identity,
    download,
    list_data,
)
from qmb.doors import api
from qmb.doors.cli import invoke_data, main
from qmf.core import (
    Instrument,
    Result,
    VenueId,
    World,
    WriterId,
    is_ok,
)
from qmf.core.refusal import Ok
from qmf.data import EvidenceStore
from qmf.data.dukascopy import PERSONAL_USE_LICENSE, DukascopyHourKey

T = TypeVar("T")

_HOUR = datetime(2024, 1, 15, 10, tzinfo=timezone.utc)
_HOUR_NS = int(_HOUR.timestamp() * 1_000_000_000)
_END_NS = _HOUR_NS + 3_600 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    venue = _ok(VenueId.try_create("dukascopy-fx"))
    return _ok(Instrument.try_create(venue, symbol))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "qmb", "catalog", "boot-1"))


def _bi5(*ticks: tuple[int, int, int]) -> bytes:
    raw = b"".join(struct.pack("!IIIff", ms, ask, bid, 1.0, 1.0) for ms, ask, bid in ticks)
    return lzma.compress(raw)


class _FixtureTransport:
    def __init__(self, hours: dict[str, bytes] | None = None) -> None:
        self.hours = hours or {}

    def fetch_hour(self, key: DukascopyHourKey, /):
        return Ok(self.hours.get(key.path_reference, b""))


def _resources(tmp: Path, transport: _FixtureTransport, **extra: object) -> dict[str, object]:
    adapter = DukascopyProviderAdapter(
        transport,
        instruments={"EURUSD": _instrument(), "GBPUSD": _instrument("GBPUSD")},
        earliest_by_symbol={"EURUSD": _HOUR_NS},
    )
    store = EvidenceStore(tmp)
    body: dict[str, object] = {
        "destination": str(tmp),
        "venue": "dukascopy-fx",
        "symbol": ["EURUSD"],
        "start": _HOUR_NS,
        "end": _END_NS,
        "resolution": "tick",
        "side": "both",
        "adapter": adapter,
        "store": store,
        "writer": _writer(),
        "receive_wall_time": _END_NS + 1_000_000,
        "license_tag": PERSONAL_USE_LICENSE,
        "world": World.REPLAY,
    }
    body.update(extra)
    return body


def test_catalog_identity_names_rebuildable_view() -> None:
    identity = catalog_identity()
    assert identity["coverage_kind"] == COVERAGE_KIND
    assert identity["present_status"] == PRESENT
    assert identity["absent_status"] == NOT_PRESENT
    assert identity["view_engine"] == "duckdb"
    assert identity["view_is_evidence_bearing"] is False
    assert identity["catalog_aliases_list"] is True
    front = data_front_identity()
    assert front["coverage_kind"] == COVERAGE_KIND
    front_commands = cast("tuple[str, ...]", front["commands"])
    assert "list" in front_commands
    assert "catalog" in front_commands


def test_list_reports_observed_side_with_duckdb_view() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250), (1_000, 110265, 110255))})
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = _resources(root, transport)
        _ok(download(resources))
        report = _ok(list_data({"destination": str(root), "store": resources["store"]}))
        assert report.command == "list"
        assert report.view_engine == "duckdb"
        assert report.is_evidence_bearing is False
        assert report.view_fingerprint is not None
        sides = {entry.side: entry for entry in report.entries}
        assert set(sides) == {"bid"}
        for entry in report.entries:
            assert entry.status == PRESENT
            assert entry.venue == "dukascopy-fx"
            assert entry.symbol == "EURUSD"
            assert entry.resolution == "tick"
            assert entry.start_ns == _HOUR_NS
            assert entry.end_ns == _HOUR_NS + 1_000_000_001
            assert entry.observation_count == 2
            assert entry.license_tag == PERSONAL_USE_LICENSE
            assert entry.revision == "r1"
            assert entry.provenance is not None


def test_absent_window_is_not_present_value_not_refusal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = EvidenceStore(root)
        result = list_data(
            {
                "destination": str(root),
                "store": store,
                "venue": "dukascopy-fx",
                "symbol": "EURUSD",
                "resolution": "tick",
                "side": "both",
                "start": _HOUR_NS,
                "end": _END_NS,
            }
        )
        assert is_ok(result), result
        report = result.value
        assert len(report.entries) == 2
        assert {entry.side for entry in report.entries} == {"bid", "ask"}
        for entry in report.entries:
            assert entry.status == NOT_PRESENT
            assert entry.observation_count is None


def test_missing_side_shown_absent_when_both_requested() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250))})
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = _resources(root, transport, side="bid")
        _ok(download(resources))
        report = _ok(
            list_data(
                {
                    "destination": str(root),
                    "store": resources["store"],
                    "venue": "dukascopy-fx",
                    "symbol": "EURUSD",
                    "side": "both",
                }
            )
        )
        by_side = {entry.side: entry for entry in report.entries}
        assert by_side["bid"].status == PRESENT
        assert by_side["ask"].status == NOT_PRESENT


def test_catalog_aliases_list_same_coverage_shape() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250))})
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = _resources(root, transport)
        _ok(download(resources))
        listed = _ok(list_data({"destination": str(root), "store": resources["store"]}))
        aliased = _ok(catalog({"destination": str(root), "store": resources["store"]}))
        assert listed.command == "list"
        assert aliased.command == "catalog"
        assert [entry.as_mapping() for entry in listed.entries] == [
            entry.as_mapping() for entry in aliased.entries
        ]
        assert listed.view_engine == aliased.view_engine
        assert listed.is_evidence_bearing is False


def test_cli_and_api_door_parity_for_coverage_payload() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250))})
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = _resources(root, transport)
        _ok(download(resources))
        query = {
            "destination": str(root),
            "store": resources["store"],
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "side": "both",
            "start": _HOUR_NS,
            "end": _END_NS,
        }
        api_payload = _ok(invoke_data("list", query))
        catalog_payload = _ok(invoke_data("catalog", query))
        api_view = cast("Mapping[str, object]", api_payload["view"])
        api_entries = cast("Sequence[object]", api_payload["entries"])
        catalog_entries = cast("Sequence[object]", catalog_payload["entries"])
        assert api_payload["command"] == "list"
        assert catalog_payload["command"] == "catalog"
        assert api_payload["entries"] == catalog_payload["entries"]
        assert api_view["engine"] == "duckdb"
        assert api_view["is_evidence_bearing"] is False
        assert api.list_data is list_data
        assert api.catalog is catalog

        runner = CliRunner()
        clicked = runner.invoke(
            main,
            [
                "data",
                "list",
                "--destination",
                str(root),
                "--venue",
                "dukascopy-fx",
                "--symbol",
                "EURUSD",
                "--side",
                "both",
                "--start",
                str(_HOUR_NS),
                "--end",
                str(_END_NS),
            ],
            obj={"store": resources["store"]},
        )
        assert clicked.exit_code == 0, clicked.output
        assert clicked.stderr.strip() == ""
        rendered = json.loads(clicked.stdout)
        assert rendered["command"] == "list"
        assert rendered["entries"] == list(api_entries)
        assert rendered["view"]["engine"] == "duckdb"

        click_catalog = runner.invoke(
            main,
            [
                "data",
                "catalog",
                "--destination",
                str(root),
                "--venue",
                "dukascopy-fx",
                "--symbol",
                "EURUSD",
                "--side",
                "both",
                "--start",
                str(_HOUR_NS),
                "--end",
                str(_END_NS),
            ],
            obj={"store": resources["store"]},
        )
        assert click_catalog.exit_code == 0, click_catalog.output
        catalog_rendered = json.loads(click_catalog.stdout)
        assert catalog_rendered["command"] == "catalog"
        assert catalog_rendered["entries"] == list(catalog_entries)


def test_free_catalog_without_rooms_stays_ok_with_empty_entries() -> None:
    payload = _ok(invoke_data("catalog"))
    assert payload["command"] == "catalog"
    assert payload["entries"] == ()
    assert payload["commands"] == data_front_identity()["commands"]
    runner = CliRunner()
    clicked = runner.invoke(main, ["data", "catalog"])
    assert clicked.exit_code == 0, clicked.output
    body = json.loads(clicked.stdout)
    assert body["command"] == "catalog"
    assert body["entries"] == []
    for name in cast("tuple[str, ...]", payload["commands"]):
        assert name in clicked.stdout
