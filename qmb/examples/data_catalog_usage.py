"""Reference usage — ``qmb data list`` coverage catalog (Story 18.3).

Executable::

    python qmb/examples/data_catalog_usage.py

Shows the things B-11 / AR-30 / AR-58 pin down for discovery:

1. ``data list`` reports coverage per ``(venue, symbol, resolution, side)``
   with covered ``[start, end]``, observation count, provenance, licence
   tag, and current bitemporal revision.
2. The catalog is a rebuildable DuckDB view over Parquet rooms — never an
   authoritative second store.
3. An absent window is the explicit ``not present`` value, not a refusal.
4. Requesting both sides when only one is present marks the missing side
   absent.
5. ``catalog`` aliases ``list``; CLI and Python API share the same
   machine-readable coverage payload (Tier-2 door-parity).
"""

from __future__ import annotations

import lzma
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from qmb.data import (
    NOT_PRESENT,
    PRESENT,
    DukascopyProviderAdapter,
    catalog,
    catalog_identity,
    download,
    list_data,
)
from qmb.doors.cli import invoke_data
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
    return _unwrap(WriterId.try_create("node-a", "qmb", "list", "boot-1"), "writer")


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


def main() -> None:
    identity = catalog_identity()
    _require(identity["view_engine"] == "duckdb", "DuckDB rebuildable view")
    _require(identity["view_is_evidence_bearing"] is False, "view never evidence")
    _require(identity["catalog_aliases_list"] is True, "catalog aliases list")
    print(
        f"catalog identity: kind={identity['coverage_kind']} "
        f"engine={identity['view_engine']} evidence={identity['view_is_evidence_bearing']}"
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = EvidenceStore(root)
        adapter = DukascopyProviderAdapter(
            _DemoTransport(),
            instruments={"EURUSD": _instrument()},
            earliest_by_symbol={"EURUSD": _HOUR_NS},
        )
        resources = {
            "destination": str(root),
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "start": _HOUR_NS,
            "end": _END_NS,
            "resolution": "tick",
            "side": "bid",
            "adapter": adapter,
            "store": store,
            "writer": _writer(),
            "receive_wall_time": _END_NS + 1,
            "license_tag": PERSONAL_USE_LICENSE,
            "world": World.REPLAY,
        }
        receipt = _unwrap(download(resources), "download")
        print(
            f"downloaded: produced={receipt.produced} side={receipt.side} "
            f"license={receipt.license_tag}"
        )

        present = _unwrap(
            list_data(
                {
                    "destination": str(root),
                    "store": store,
                    "venue": "dukascopy-fx",
                    "symbol": "EURUSD",
                    "side": "both",
                    "start": _HOUR_NS,
                    "end": _END_NS,
                }
            ),
            "list both sides",
        )
        by_side = {entry.side: entry for entry in present.entries}
        _require(by_side["bid"].status == PRESENT, "bid present after bid-only download")
        _require(by_side["ask"].status == NOT_PRESENT, "ask absent when only bid downloaded")
        _require(present.view_fingerprint is not None, "DuckDB view fingerprint stamped")
        print(
            f"list both: bid={by_side['bid'].status} ask={by_side['ask'].status} "
            f"view={present.view_engine} fp={present.view_fingerprint[:24]}..."
        )

        missing = _unwrap(
            list_data(
                {
                    "destination": str(root),
                    "store": store,
                    "venue": "dukascopy-fx",
                    "symbol": "GBPUSD",
                    "side": "ask",
                    "start": _HOUR_NS,
                    "end": _END_NS,
                }
            ),
            "list absent symbol",
        )
        _require(len(missing.entries) == 1, "one absent row")
        _require(missing.entries[0].status == NOT_PRESENT, "absent is a value")
        print(f"absent window: status={missing.entries[0].status} (not a refusal)")

        aliased = _unwrap(catalog({"destination": str(root), "store": store}), "catalog alias")
        listed = _unwrap(list_data({"destination": str(root), "store": store}), "list all")
        _require(aliased.command == "catalog", "alias keeps catalog command name")
        _require(listed.command == "list", "list keeps list command name")
        _require(
            [entry.as_mapping() for entry in aliased.entries]
            == [entry.as_mapping() for entry in listed.entries],
            "catalog aliases list coverage rows",
        )
        print(f"catalog aliases list: entries={len(listed.entries)}")

        door = _unwrap(
            invoke_data(
                "list",
                {
                    "destination": str(root),
                    "store": store,
                    "venue": "dukascopy-fx",
                    "symbol": "EURUSD",
                    "side": "bid",
                },
            ),
            "CLI/API door list",
        )
        _require(door["command"] == "list", "door command")
        _require(door["view"]["engine"] == "duckdb", "door view engine")
        _require(door["view"]["is_evidence_bearing"] is False, "door view never evidence")
        print(
            f"CLI and Python API share coverage: command={door['command']} "
            f"entries={len(door['entries'])} engine={door['view']['engine']}"
        )

    print("data catalog ok")


if __name__ == "__main__":
    main()
