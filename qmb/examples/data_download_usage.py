"""Reference usage — ``qmb data download`` thin front over CT-10/CT-15 (Story 18.1).

Executable::

    python qmb/examples/data_download_usage.py

Shows the things B-11 / AR-54 pin down:

1. Download is a thin door over qmf-data CT-15 intake and CT-10 raw rooms —
   no second data layer.
2. Fetch goes through a QMX-authored provider-adapter port (fetch,
   earliest_available, list_symbols, batch count, rate-limit) with Dukascopy
   as adapter #1 — shapes only, no vendored dukascopy-node code.
3. Bid and ask stay distinct; prices cross the named AD-22 conversion.
4. Overlapping re-run is idempotent; overwrite appends a CT-10 revision.
5. Long import emits machine-observable progress; each window carries
   provenance + licence tag.
6. A run that attempts a provider fetch is a policy rejection.
"""

from __future__ import annotations

import lzma
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from qmb.data import (
    CONVERSION_BOUNDARY,
    DownloadProgress,
    DukascopyProviderAdapter,
    download,
    provider_price_to_exact,
    refuse_run_provider_fetch,
)
from qmf.core import (
    Instrument,
    RefusalCategory,
    Result,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import Ok
from qmf.data import EvidenceStore
from qmf.data.dukascopy import PERSONAL_USE_LICENSE, DukascopyHourKey

T = TypeVar("T")

_HOUR = datetime(2024, 1, 15, 10, tzinfo=timezone.utc)
_HOUR_NS = int(_HOUR.timestamp() * 1_000_000_000)
_END_NS = _HOUR_NS + 3_600 * 1_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


def _instrument() -> Instrument:
    venue = _unwrap(VenueId.try_create("dukascopy-fx"), "venue")
    return _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "qmb", "download", "boot-1"), "writer")


def _bi5() -> bytes:
    raw = struct.pack("!IIIff", 0, 110260, 110250, 1.0, 1.0)
    raw += struct.pack("!IIIff", 500, 110265, 110255, 1.0, 1.0)
    return lzma.compress(raw)


class _DemoTransport:
    def __init__(self) -> None:
        self._payload = _bi5()

    def fetch_hour(self, key: DukascopyHourKey, /) -> Result[bytes]:
        if key.symbol == "EURUSD":
            return Ok(self._payload)
        return Ok(b"")


class _ProgressLog:
    def __init__(self) -> None:
        self.samples: list[DownloadProgress] = []

    def on_progress(self, progress: DownloadProgress, /) -> None:
        self.samples.append(progress)


def main() -> None:
    transport = _DemoTransport()
    adapter = DukascopyProviderAdapter(
        transport,
        instruments={"EURUSD": _instrument()},
        earliest_by_symbol={"EURUSD": _HOUR_NS},
    )
    _require(adapter.batch_count == 1, "Dukascopy batch is one hour file")
    symbols = _unwrap(adapter.list_symbols(), "list_symbols")
    earliest = _unwrap(adapter.earliest_available("EURUSD"), "earliest")
    print(
        f"provider port: source={adapter.source} symbols={symbols} "
        f"earliest={earliest} batch_count={adapter.batch_count}"
    )

    exact = _unwrap(
        provider_price_to_exact(110250, instrument=_instrument(), scale=5),
        "exact int",
    )
    print(f"AD-22 conversion boundary={CONVERSION_BOUNDARY} verbatim={exact.verbatim}")

    progress = _ProgressLog()
    with tempfile.TemporaryDirectory() as tmp:
        resources: dict[str, object] = {
            "destination": tmp,
            "venue": "dukascopy-fx",
            "symbol": ["EURUSD"],
            "start": _HOUR_NS,
            "end": _END_NS,
            "resolution": "tick",
            "side": "both",
            "adapter": adapter,
            "store": EvidenceStore(Path(tmp)),
            "writer": _writer(),
            "receive_wall_time": _END_NS + 1,
            "license_tag": PERSONAL_USE_LICENSE,
            "world": World.REPLAY,
            "progress": progress,
        }
        receipt = _unwrap(download(resources), "download")
        _require(receipt.produced == 2, "two ticks admitted")
        _require(receipt.license_tag == PERSONAL_USE_LICENSE, "licence tag recorded")
        _require(progress.samples[-1].percent == 100, "progress reached 100")
        print(
            f"download-once CT-10: produced={receipt.produced} "
            f"side={receipt.side} license={receipt.license_tag} "
            f"progress_percent={progress.samples[-1].percent}"
        )

        again = _unwrap(download(resources), "idempotent re-run")
        _require(again.idempotent == 2, "overlapping re-run skipped duplicates")
        print(f"idempotent re-run: produced={again.produced} idempotent={again.idempotent}")

        overwritten = _unwrap(download({**resources, "overwrite": True}), "overwrite")
        _require(overwritten.produced == 2, "overwrite appends a new revision")
        print(f"overwrite revision={overwritten.revision} produced={overwritten.produced}")

    refused = refuse_run_provider_fetch(request="backtest.run")
    assert is_refusal(refused)
    _require(refused.category is RefusalCategory.POLICY_REJECTION, "policy rejection")
    print("run provider fetch is policy rejection — rooms only")
    print("qmb data download ok")


if __name__ == "__main__":
    main()
