"""Reference usage — Dukascopy download-once historical tick adapter (COMP-DUKASCOPY).

Executable::

    python packages/qmf-data/examples/dukascopy_usage.py

Shows the five things Story 6.3 pins down:

1. Bounded bi5 evidence decodes into CT-15 ProviderRecords with source identity
   ``dukascopy``, then converts through ExternalSourceIngest into CT-10 (AC1).
2. Every acquired window carries provenance plus a license tag; personal-use
   ``internal-only`` grants governed-evidence use, while unknown/denied refuse (AC2).
3. Malformed bi5 / missing window bounds / unmappable symbols are invalid input (AC3).
4. Complete-corpus and oversized windows are refused — no donor dukascopy-node
   code, bounded adapter evidence only (AC4).
5. Checkpoint / external recovery / retry-loop ownership are application-owned (AC5).
"""

from __future__ import annotations

import lzma
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data import (
    DUKASCOPY_SOURCE,
    PERSONAL_USE_LICENSE,
    DukascopyAdapter,
    DukascopyHourKey,
    EvidenceStore,
    ExternalSourceIngest,
    LicensedSourceWindow,
    LicenseTag,
    SourceObservationBoundary,
    SourceRequest,
    decode_bi5_ticks,
    offer_for_governed_evidence,
)

T = TypeVar("T")

_HOUR = datetime(2024, 1, 15, 10, tzinfo=timezone.utc)
_HOUR_NS = int(_HOUR.timestamp() * 1_000_000_000)
_END_NS = _HOUR_NS + 3_600 * 1_000_000_000
_RECEIVE_NS = _END_NS + 1_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "ingest", "dukascopy", "boot-1"), "writer")


def _instrument() -> Instrument:
    venue = _unwrap(VenueId.try_create("broker-a"), "venue")
    return _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")


def _bi5() -> bytes:
    raw = struct.pack("!IIIff", 0, 110260, 110250, 1.0, 1.0)
    raw += struct.pack("!IIIff", 250, 110265, 110255, 1.0, 1.0)
    return lzma.compress(raw)


class _DemoTransport:
    """Fixture transport — production injects HTTPS; this never leaves process."""

    def __init__(self) -> None:
        self._payload = _bi5()

    def fetch_hour(self, key: DukascopyHourKey, /) -> Result[bytes]:
        if key.symbol == "EURUSD" and key.hour == 10:
            return Ok(self._payload)
        return Ok(b"")


def main() -> None:
    transport = _DemoTransport()
    adapter = DukascopyAdapter(transport, instruments={"EURUSD": _instrument()})
    bounds = {
        "symbol": "EURUSD",
        "start_ns": _HOUR_NS,
        "end_ns": _END_NS,
        "known_at_ns": _END_NS,
        "revision": "r1",
        "license_tag": PERSONAL_USE_LICENSE,
    }
    request = SourceRequest(source=DUKASCOPY_SOURCE, bounds=bounds)

    # AC1 — bounded fetch → CT-15 records → CT-10 via ingest seam.
    ingest = ExternalSourceIngest(adapter)
    receipts = _unwrap(
        ingest.fetch_and_intake(
            request,
            writer=_writer(),
            world=World.LIVE,
            receive_wall_time=_RECEIVE_NS,
        ),
        "fetch_and_intake",
    )
    _require(len(receipts) == 2, "two ticks decoded")
    first = receipts[0]
    quote = first.quote
    if quote is None:
        raise AssertionError("expected bid/ask preserved on tick")
    _require(first.observation.source == DUKASCOPY_SOURCE, "source identity dukascopy")
    print(
        f"download-once CT-10: source={first.observation.source} "
        f"ticks={len(receipts)} bid={quote.bid.verbatim} ask={quote.ask.verbatim}"
    )

    with tempfile.TemporaryDirectory() as tmp:
        boundary = SourceObservationBoundary(EvidenceStore(Path(tmp) / "store"))
        admitted = _unwrap(
            ingest.submit(first.observation, boundary),
            "CT-10 admit",
        )
        print(f"admitted to raw archive: {admitted.archive.outcome.value}")

    # AC2 — license-tagged window; unlicensed refuses governed evidence.
    window = adapter.last_window
    if window is None:
        raise AssertionError("expected window recorded")
    offered = _unwrap(offer_for_governed_evidence(window), "personal-use governed offer")
    print(
        f"license-tagged window: tag={offered.license_tag.value} "
        f"partition={offered.partition.partition_key}"
    )

    unknown = _unwrap(
        LicensedSourceWindow.try_create(
            partition=window.partition,
            license_tag=LicenseTag.UNKNOWN,
        ),
        "unknown window",
    )
    refused_license = offer_for_governed_evidence(unknown)
    if not is_refusal(refused_license):
        raise AssertionError("expected unknown tag refused")
    _require(
        refused_license.category is RefusalCategory.POLICY_REJECTION,
        "unlicensed is policy rejection",
    )
    print("unlicensed window refused for governed evidence")

    # AC3 — malformed bi5 / unmappable symbol.
    bad = decode_bi5_ticks(b"not-compressed", hour_start_ns=_HOUR_NS)
    if not is_refusal(bad) or bad.category is not RefusalCategory.INVALID_INPUT:
        raise AssertionError("expected bad bi5 invalid input")
    unmapped = adapter.fetch(
        SourceRequest(
            source=DUKASCOPY_SOURCE,
            bounds={**bounds, "symbol": "NOSUCH"},
        )
    )
    if not is_refusal(unmapped) or unmapped.category is not RefusalCategory.INVALID_INPUT:
        raise AssertionError("expected unmappable instrument invalid input")
    print("malformed / unmappable -> invalid input")

    # AC4 — complete corpus refused.
    corpus = adapter.download_complete_corpus()
    _require(is_refusal(corpus), "complete corpus refused")
    print("complete-corpus download refused (bounded adapter only)")

    # AC5 — recovery ownership refused.
    recovery = adapter.recover_external()
    _require(is_refusal(recovery), "external recovery refused")
    print("external recovery / checkpoint ownership refused (application-owned)")


if __name__ == "__main__":
    main()
