"""Tier-1 tests for ``qmb data download`` (Story 18.1, B-11)."""

from __future__ import annotations

import lzma
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from click.testing import CliRunner
from qmb.data import (
    CONVERSION_BOUNDARY,
    CONVERSION_ROUNDING,
    DOWNLOAD_SIDES,
    DUKASCOPY_BATCH_COUNT,
    DUKASCOPY_PROVIDER,
    PROVIDER_ADAPTER_METHODS,
    DownloadProgress,
    DownloadSide,
    DukascopyProviderAdapter,
    conversion_identity,
    data_front_identity,
    download,
    parse_download_request,
    provider_price_to_exact,
    refuse_run_provider_fetch,
    resolve_end_ns,
)
from qmb.doors.cli import invoke_data, main
from qmf.core import (
    Instrument,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.core.exact import RoundingMode
from qmf.data import DUKASCOPY_SOURCE, EvidenceStore
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
    return _ok(WriterId.try_create("node-a", "qmb", "download", "boot-1"))


def _bi5(*ticks: tuple[int, int, int]) -> bytes:
    raw = b"".join(struct.pack("!IIIff", ms, ask, bid, 1.0, 1.0) for ms, ask, bid in ticks)
    return lzma.compress(raw)


class _FixtureTransport:
    def __init__(self, hours: dict[str, bytes] | None = None) -> None:
        self.hours = hours or {}
        self.calls: list[DukascopyHourKey] = []
        self.mode = "ok"

    def fail_rate_limit(self) -> None:
        self.mode = "rate-limit"

    def fail_geo_block(self) -> None:
        self.mode = "geo-block"

    def fetch_hour(self, key: DukascopyHourKey, /):
        self.calls.append(key)
        if self.mode == "rate-limit":
            return TypedRefusal(
                category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
                retryability=Retryability.YES,
                context={"signal": "rate-limit", "source": DUKASCOPY_SOURCE},
            )
        if self.mode == "geo-block":
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.NO,
                context={"signal": "http-451", "source": DUKASCOPY_SOURCE},
            )
        from qmf.core import Ok

        return Ok(self.hours.get(key.path_reference, b""))


class _ProgressLog:
    def __init__(self) -> None:
        self.samples: list[DownloadProgress] = []

    def on_progress(self, progress: DownloadProgress, /) -> None:
        self.samples.append(progress)


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


def test_data_front_identity_names_provider_port() -> None:
    identity = data_front_identity()
    assert identity["provider_adapter_methods"] == PROVIDER_ADAPTER_METHODS
    assert identity["conversion_boundary"] == CONVERSION_BOUNDARY
    assert identity["download_sides"] == DOWNLOAD_SIDES
    assert identity["dukascopy_provider"] == DUKASCOPY_PROVIDER
    assert conversion_identity()["rounding"] == CONVERSION_ROUNDING.value
    assert CONVERSION_ROUNDING is RoundingMode.HALF_EVEN


def test_provider_adapter_surface_and_dukascopy_batch() -> None:
    transport = _FixtureTransport()
    adapter = DukascopyProviderAdapter(
        transport,
        instruments={"EURUSD": _instrument()},
        earliest_by_symbol={"EURUSD": _HOUR_NS},
    )
    assert adapter.source == DUKASCOPY_PROVIDER
    assert adapter.batch_count == DUKASCOPY_BATCH_COUNT
    assert adapter.rate_limit_per_second is None
    assert _ok(adapter.list_symbols()) == ("EURUSD",)
    assert _ok(adapter.earliest_available("EURUSD")) == _HOUR_NS
    missing = adapter.earliest_available("GBPUSD")
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT


def test_provider_price_to_exact_named_boundary() -> None:
    instrument = _instrument()
    exact = _ok(provider_price_to_exact(110250, instrument=instrument, scale=5))
    assert exact.verbatim == 110250
    assert exact.scale == 5
    from_float = _ok(provider_price_to_exact(1.10250, instrument=instrument, scale=5))
    assert from_float.verbatim == 110250
    refused = provider_price_to_exact("not-a-price", instrument=instrument, scale=5)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["boundary"] == CONVERSION_BOUNDARY


def test_download_once_admits_ct10_bid_ask_and_license() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250), (1_000, 110265, 110255))})
    progress = _ProgressLog()
    with tempfile.TemporaryDirectory() as tmp:
        resources = _resources(Path(tmp), transport, progress=progress)
        receipt = _ok(download(resources))
        assert receipt.command == "download"
        assert receipt.produced == 2
        assert receipt.admitted == 2
        assert receipt.idempotent == 0
        assert receipt.license_tag == PERSONAL_USE_LICENSE
        assert receipt.side == DownloadSide.BOTH.value
        assert receipt.windows[0]["license_tag"] == PERSONAL_USE_LICENSE
        assert "provenance" in receipt.windows[0]
        assert progress.samples
        assert progress.samples[-1].percent == 100
        assert progress.samples[-1].date_reached_ns == _END_NS


def test_overlapping_rerun_is_idempotent_overwrite_appends_revision() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250))})
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = _ok(download(_resources(root, transport)))
        assert first.produced == 1
        second = _ok(download(_resources(root, transport)))
        assert second.produced == 0
        assert second.idempotent == 1
        third = _ok(download(_resources(root, transport, overwrite=True)))
        assert third.overwrite is True
        assert third.revision.startswith("r-")
        assert third.produced == 1


def test_provider_rate_limit_and_geo_block_are_typed_refusals() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250))})
    with tempfile.TemporaryDirectory() as tmp:
        transport.fail_rate_limit()
        rate = download(_resources(Path(tmp), transport))
        assert is_refusal(rate)
        assert rate.category is RefusalCategory.TRANSIENT_VENUE_FAILURE
        assert rate.retryability is Retryability.YES
        transport.fail_geo_block()
        blocked = download(_resources(Path(tmp), transport))
        assert is_refusal(blocked)
        assert blocked.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
        assert blocked.context["signal"] == "http-451"


def test_run_provider_fetch_is_policy_rejection() -> None:
    refused = refuse_run_provider_fetch(request="runloop.fetch")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["sole_fetch_surface"] == "qmb data download"


def test_end_defaults_to_today_explicit_end_is_reproducible() -> None:
    fixed = datetime(2024, 6, 1, 15, tzinfo=timezone.utc)
    end = _ok(resolve_end_ns(None, now=fixed))
    assert end == int(datetime(2024, 6, 2, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
    explicit = _ok(resolve_end_ns(_END_NS))
    assert explicit == _END_NS
    parsed = _ok(
        parse_download_request(
            {
                "venue": "dukascopy-fx",
                "symbol": "EURUSD",
                "start": _HOUR_NS,
                "end": _END_NS,
                "destination": "archive",
            }
        )
    )
    assert parsed.end_ns == _END_NS
    assert parsed.side is DownloadSide.BOTH


def test_invoke_data_download_through_door() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250))})
    with tempfile.TemporaryDirectory() as tmp:
        resources = _resources(Path(tmp), transport)
        result = _ok(invoke_data("download", resources))
        assert result["command"] == "download"
        assert result["produced"] == 1
        assert result["commands"]
        runner = CliRunner()
        clicked = runner.invoke(
            main,
            [
                "data",
                "download",
                "--destination",
                str(tmp),
                "--venue",
                "dukascopy-fx",
                "--symbol",
                "EURUSD",
                "--start",
                str(_HOUR_NS),
                "--end",
                str(_END_NS),
            ],
            obj=resources,
        )
        assert clicked.exit_code == 0, clicked.output
        assert "download" in clicked.output


def test_missing_adapter_is_unavailable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        refused = download(
            {
                "destination": tmp,
                "venue": "dukascopy-fx",
                "symbol": "EURUSD",
                "start": _HOUR_NS,
                "end": _END_NS,
            }
        )
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
