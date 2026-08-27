"""Independent test helpers for the Epic 6 (qmf-data source intake) verification lane.

Builders, fakes, and the CT-04 refusal harness the epic_06 suite drives its assertions
through. Effects are observed only through injected fakes/sinks owned by the TEST; the
refusal helpers assert the CT-04 ``category`` value and never a parsed message string.

Authored to exercise CT-15 / CT-10 / CT-07 obligations from the requirements side.
Nothing here edits or weakens a production assertion; a failing planned test is a FINDING.
"""

from __future__ import annotations

import json
import lzma
import struct
from datetime import datetime, timezone
from pathlib import Path

from qmf.core import (
    Fingerprint,
    Instant,
    Instrument,
    Interval,
    MonotonicReading,
    Ok,
    RefusalCategory,
    Retryability,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data import calendar_feed as _cal
from qmf.data.ingest import ExternalSourceIngest, ProviderRecord, SourceRequest
from qmf.data.journal_producer import JournalReader, JournalWriter
from qmf.data.observation import ForeignMoney, ForeignTimestamp, SourceObservation
from qmf.data.partitions import SeriesPartition
from qmf.data.store import EvidenceStore

# Shared bitemporal constants for the calendar / journal harness.
KNOWN_NS = 1_600_000_000_000_000_000
RECV_NS = 1_600_000_000_500_000_000
JOURNAL_NS = 1_600_000_001_000_000_000

# --- packed bi5 layout (matches decode_bi5_ticks: "!IIIff") ------------------
_TICK_STRUCT = struct.Struct("!IIIff")
NS_PER_HOUR = 3_600 * 1_000_000_000


# --- result / refusal harness (CT-04 category, never a parsed string) --------


def unwrap(result: object) -> object:
    """Assert ``result`` is Ok and return its value, with a helpful message on refusal."""
    if is_refusal(result):
        raise AssertionError(
            f"expected Ok, got refusal category={result.category.value!r} "
            f"context={dict(result.context)!r}"
        )
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def assert_refusal(result: object, category: str | None = None) -> object:
    """Assert ``result`` is a typed refusal (optionally of ``category``); return it.

    Checks the CT-04 ``category`` value, never a parsed exception/message string.
    """
    if is_ok(result):
        raise AssertionError(f"expected a typed refusal, got Ok({result.value!r})")
    assert is_refusal(result), f"expected a typed refusal, got {result!r}"
    if category is not None:
        assert result.category.value == category, (
            f"expected refusal category {category!r}, got {result.category.value!r}; "
            f"context={dict(result.context)!r}"
        )
    return result


# --- core value-type builders ------------------------------------------------


def writer(
    machine: str = "node-a",
    role: str = "data",
    stream: str = "dq",
    boot: str = "boot-1",
) -> WriterId:
    return unwrap(WriterId.try_create(machine, role, stream, boot))


def instant(value_ns: int) -> Instant:
    return unwrap(Instant.try_create(value_ns))


def venue(value: str = "cTrader") -> VenueId:
    return unwrap(VenueId.try_create(value))


def instrument(venue_id: VenueId | None = None, symbol: str = "EURUSD") -> Instrument:
    return unwrap(Instrument.try_create(venue_id if venue_id is not None else venue(), symbol))


def interval(start_ns: int, end_ns: int) -> Interval:
    return unwrap(Interval.try_create(instant(start_ns), instant(end_ns)))


def series_partition(source: str = "dukascopy", inst: Instrument | None = None,
                     start_ns: int = 1_000, end_ns: int = 2_000) -> SeriesPartition:
    return unwrap(SeriesPartition.try_create(
        source, inst if inst is not None else instrument(), interval(start_ns, end_ns)))


def monotonic(value_ns: int = 999, boot: str = "boot-1") -> MonotonicReading:
    return MonotonicReading(value_ns=value_ns, boot_epoch_id=boot)


def foreign_timestamp_block(verbatim: str = "2025-01-02T03:04:05.123",
                            zone: str = "Europe/Zurich", offset: str = "+01:00",
                            resolution: str = "milliseconds") -> dict:
    return {"verbatim": verbatim, "zone": zone, "offset": offset, "resolution": resolution}


def foreign_money_block(verbatim: int = 123456, scale: int = 5) -> dict:
    return {"verbatim": verbatim, "scale": scale}


# --- CT-15 provider record ---------------------------------------------------


def provider_record(**over: object) -> ProviderRecord:
    """A complete valid ProviderRecord; override any field (or set to _OMIT to drop)."""
    fields: dict[str, object] = {
        "source": "dukascopy",
        "source_native_id": "occ-1",
        "revision": "r1",
        "event_time": 1_000,
        "known_at": 2_000,
        "instrument": instrument(),
    }
    fields.update(over)
    return ProviderRecord(**fields)  # type: ignore[arg-type]


# --- typed refusal builders for provider/transport fakes (CT-04 categories) --


def transient_refusal(**ctx: object) -> TypedRefusal:
    return TypedRefusal(category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
                        retryability=Retryability.YES, context=dict(ctx))


def unavailable_refusal(**ctx: object) -> TypedRefusal:
    return TypedRefusal(category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                        retryability=Retryability.YES, context=dict(ctx))


def storage_refusal(**ctx: object) -> TypedRefusal:
    return TypedRefusal(category=RefusalCategory.STORAGE_FAILURE,
                        retryability=Retryability.NO, context=dict(ctx))


# --- injected fakes owned by the test ----------------------------------------


class ListPort:
    """An injected ExternalSourcePort returning a preset Result; records requests."""

    def __init__(self, result: object) -> None:
        self._result = result
        self.requests: list[object] = []

    def fetch(self, request: object, /) -> object:
        self.requests.append(request)
        return self._result


class RaisingPort:
    """An ExternalSourcePort whose fetch RAISES a real exception (fault realism)."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.requests: list[object] = []

    def fetch(self, request: object, /) -> object:
        self.requests.append(request)
        raise self._exc


class BytesTransport:
    """A DukascopyTransport returning a preset Result[bytes] for every hour."""

    def __init__(self, result: object) -> None:
        self._result = result
        self.calls: list[object] = []

    def fetch_hour(self, key: object, /) -> object:
        self.calls.append(key)
        return self._result


class MappedBytesTransport:
    """A DukascopyTransport returning bytes per hour-key.path_reference (else empty)."""

    def __init__(self, by_path: dict[str, bytes]) -> None:
        self._by_path = by_path
        self.calls: list[object] = []

    def fetch_hour(self, key: object, /) -> object:
        self.calls.append(key)
        return Ok(self._by_path.get(key.path_reference, b""))


class RaisingTransport:
    """A DukascopyTransport / CalendarFeedTransport that RAISES a real exception."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.calls: list[object] = []

    def fetch_hour(self, key: object, /) -> object:
        self.calls.append(key)
        raise self._exc

    def fetch_snapshot(self, bounds: object, /) -> object:
        self.calls.append(bounds)
        raise self._exc


class SnapshotTransport:
    """A CalendarFeedTransport returning a preset Result for fetch_snapshot."""

    def __init__(self, result: object) -> None:
        self._result = result
        self.calls: list[object] = []

    def fetch_snapshot(self, bounds: object, /) -> object:
        self.calls.append(dict(bounds))
        return self._result


class RecordingBoundary:
    """A CT-10 producer boundary standing in for SourceObservationBoundary.

    Owned by the test: records every ``admit`` call so a test observes whether the
    ingest path performed a governed write, and through which door.
    """

    def __init__(self) -> None:
        self.admitted: list[object] = []

    def admit(self, observation: object) -> object:
        self.admitted.append(observation)
        return Ok(observation)


class TattleStore:
    """A governed store that fails LOUDLY on ANY attribute access.

    Injected where a test asserts the ingest path never reaches into a store; any
    touch is an AssertionError naming the accessed attribute.
    """

    def __init__(self) -> None:
        object.__setattr__(self, "_touched", [])

    def __getattr__(self, name: str) -> object:  # pragma: no cover - only on violation
        raise AssertionError(f"governed store was touched by the ingest path: .{name}")


# --- real store (truthful CT-13 journal sink for producer-obligation reads) --


def make_store(root: Path, *, rotation_bytes: int = 4096) -> EvidenceStore:
    return EvidenceStore(root / "store", rotation_bytes=rotation_bytes, seal=None)


# --- byte builders -----------------------------------------------------------


def bi5_bytes(ticks: list[tuple[int, int, int, float, float]]) -> bytes:
    """LZMA-compress a valid bi5 payload from (ms_offset, ask_i, bid_i, ask_vol, bid_vol)."""
    raw = b"".join(_TICK_STRUCT.pack(*t) for t in ticks)
    return lzma.compress(raw)


def dukascopy_window(year: int = 2020, month: int = 3, day: int = 2, hour: int = 0) -> tuple[int, int]:
    start = int(datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
    return start, start + NS_PER_HOUR


def calendar_json(events: list[dict]) -> bytes:
    return json.dumps(events).encode("utf-8")


def sample_calendar_event(title: str = "Non-Farm Payrolls", country: str = "USD",
                          impact: str = "High",
                          date: str = "2026-08-16T18:30:00-04:00", **extra: object) -> dict:
    ev = {"title": title, "country": country, "impact": impact, "date": date}
    ev.update(extra)
    return ev


# --- calendar-import harness over a real store (truthful CT-13 journal sink) --


def calendar_harness(tmp_path: Path, snapshot_result: object, *,
                     exposures: dict | None = None, instruments: dict | None = None):
    """Wire a CalendarFeedImport over a real EvidenceStore; return (import, world_store)."""
    store = make_store(tmp_path)
    ws = unwrap(store.for_world(World.LIVE))
    jwriter = JournalWriter(ws.journal, writer(role="data", stream="calendar"), stream_name="calendar")
    adapter = _cal.CalendarFeedAdapter(SnapshotTransport(snapshot_result), instruments=instruments)
    ingest = ExternalSourceIngest(port=adapter)
    imp = _cal.CalendarFeedImport(adapter, ingest, jwriter, currency_exposures=exposures)
    return imp, ws


def run_calendar_import(imp: object, **run_kw: object) -> object:
    """Drive one CalendarFeedImport.run with the shared bitemporal constants."""
    req = SourceRequest(source="news-calendar", bounds={"known_at_ns": KNOWN_NS, "revision": "r1"})
    return imp.run(req, writer=writer(role="data", stream="obs"), world=World.LIVE,
                   receive_wall_time=RECV_NS, journal_instant=JOURNAL_NS, **run_kw)


def read_journal(ws: object, stream: str = "calendar") -> list:
    return unwrap(JournalReader(ws.journal).read(stream, for_world=World.LIVE))
