"""Shared fixtures / fakes for the INDEPENDENT Epic 18 (qmb-data-management) audit.

Assertions in the test modules assert what the RATIFIED requirements demand
(epics.md Epic-18 ACs + the QMB spine B-11/B-1/B-7 + the CT-* contracts, per
this epic's PLAN.md), never what the source happens to do. This module supplies
only *construction mechanics* and TEST-OWNED observers (a fake provider adapter,
a recording progress sink, a recording journal, controlled calendars, and an
independent raw-archive reader) so the requirement-level assertions run against
public surfaces. A failing test is a FINDING — never a licence to soften an
assertion or edit source.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import TypeVar

from qmf.core.chrono import CalendarIdentity, Instant, SessionWindow, WriterId
from qmf.core.fingerprint import World
from qmf.core.identity import Instrument
from qmf.core import VenueId
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.data.ingest import ProviderRecord
from qmf.data.store import EvidenceStore, ParquetColumnarEngine, StoreEngineError
from qmf.data.store.rooms import namespace_for_write

T = TypeVar("T")

# A fixed replay instant well inside int64 UTC-ns (≈ 2023-11-14).
NS: int = 1_700_000_000_000_000_000
HOUR_NS: int = 3_600_000_000_000


def ok(result: Result[T]) -> T:
    """Unwrap an ``Ok`` or fail loudly with the refusal context."""
    assert is_ok(result), f"expected Ok, got refusal: {getattr(result, 'context', result)!r}"
    return result.value


def refusal(result: object) -> TypedRefusal:
    """Assert ``result`` is a RETURNED CT-04 refusal and hand it back."""
    assert is_refusal(result), f"expected a returned TypedRefusal, got {result!r}"
    return result


def instrument(venue: str = "dukascopy", symbol: str = "EURUSD") -> Instrument:
    return ok(Instrument.try_create(ok(VenueId.try_create(venue)), symbol))


def writer(stream: str = "test") -> WriterId:
    return ok(WriterId.try_create("qmb", "data", stream, "boot-1"))


def provider_record(
    native_id: str,
    event_ns: int,
    *,
    revision: str = "r1",
    bid: int | None = 110_000,
    ask: int | None = 110_020,
    scale: int = 5,
    source: str = "dukascopy",
    instr: Instrument | None = None,
) -> ProviderRecord:
    """One CT-15 provider record with distinct bid/ask scaled integers.

    Mirrors what the QMX Dukascopy adapter emits (verbatim/scale dicts) so the
    record flows through the real CT-15 intake exactly as production does.
    """
    kw: dict[str, object] = {}
    if bid is not None:
        kw["bid"] = {"verbatim": bid, "scale": scale}
    if ask is not None:
        kw["ask"] = {"verbatim": ask, "scale": scale}
    return ProviderRecord(
        source=source,
        source_native_id=native_id,
        revision=revision,
        event_time=event_ns,
        known_at=event_ns,
        instrument=instr if instr is not None else instrument(),
        **kw,
    )


class FakeAdapter:
    """A TEST-OWNED provider adapter implementing the ``ProviderAdapter`` port.

    ``fetch`` returns the scripted records (or a scripted CT-04 refusal) and
    RECORDS every request it saw, so a test observes the fetch call through a
    sink it owns — never through the SUT's own report.
    """

    def __init__(
        self,
        records: tuple[ProviderRecord, ...] = (),
        *,
        source: str = "dukascopy",
        fetch_refusal: TypedRefusal | None = None,
        symbols: tuple[str, ...] = ("EURUSD",),
    ) -> None:
        self._records = records
        self._source = source
        self._fetch_refusal = fetch_refusal
        self._symbols = symbols
        self.fetch_calls: list[object] = []

    @property
    def source(self) -> str:
        return self._source

    @property
    def batch_count(self) -> int:
        return 1

    @property
    def rate_limit_per_second(self) -> int | None:
        return None

    def list_symbols(self) -> Result[tuple[str, ...]]:
        return Ok(self._symbols)

    def earliest_available(self, symbol: object, /) -> Result[int | None]:
        return Ok(None)

    def fetch(self, request: object, /) -> Result[tuple[ProviderRecord, ...]]:
        self.fetch_calls.append(request)
        if self._fetch_refusal is not None:
            return self._fetch_refusal
        return Ok(self._records)


class RecordingProgressSink:
    """A TEST-OWNED ProgressSink that records every emitted progress sample."""

    def __init__(self) -> None:
        self.samples: list[object] = []

    def on_progress(self, progress: object, /) -> None:
        self.samples.append(progress)


class RecordingJournal:
    """A TEST-OWNED journal writer that records CT-13 data-quality payloads.

    Duck-typed to the surface ``verify`` calls on an explicit ``journal_writer``:
    ``record_data_quality(payload, instant=..., correlation_id=...)`` returning a
    receipt whose ``.event.sequence`` is read back. The recorded payload is the
    independent observation of what was journaled.
    """

    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def record_data_quality(
        self, payload: object, *, instant: object = None, correlation_id: object = None
    ) -> Result[object]:
        self.records.append(
            {"payload": payload, "instant": instant, "correlation_id": correlation_id}
        )
        seq = len(self.records) - 1
        return Ok(SimpleNamespace(event=SimpleNamespace(sequence=seq)))


@dataclass(frozen=True)
class ControlledCalendar:
    """A TEST-OWNED CT-02 market-hours calendar over explicit open spans.

    ``session_window`` returns the open :class:`SessionWindow` that contains the
    probe instant, or ``None`` when the venue is closed there — so the SUT's
    closed-vs-gap classification is exercised against a calendar the test fully
    controls, not the real FX session data (Epic 4).
    """

    identity: CalendarIdentity
    open_spans: tuple[tuple[int, int], ...]

    def session_window(self, instant: object) -> Result[SessionWindow | None]:
        if not isinstance(instant, Instant):
            return TypedRefusal.try_create("invalid input", "no").value  # pragma: no cover
        ns = instant.value_ns
        for open_ns, close_ns in self.open_spans:
            if open_ns <= ns < close_ns:
                built = SessionWindow.try_create(
                    ok(Instant.try_create(open_ns)),
                    ok(Instant.try_create(close_ns)),
                    "UTC",
                )
                return Ok(ok_or_self(built))
        return Ok(None)


def ok_or_self(result: Result[T]) -> T:
    return ok(result)


def calendar_identity(
    rule_set: str = "forex-17NY", version: str = "v3", tzdata: str = "2024a"
) -> CalendarIdentity:
    return ok(CalendarIdentity.try_create(rule_set, version, tzdata))


def store_at(path: Path) -> EvidenceStore:
    return EvidenceStore(Path(path))


def scan_raw_observations(
    store: EvidenceStore, *, world: World = World.REPLAY
) -> tuple[dict[str, object], ...]:
    """INDEPENDENT read of the CT-10 raw archive: every non-coverage row.

    Reads straight through the qmf-data columnar engine — the sink the test owns
    for observing what ``download`` actually persisted, so absence-of-effect is
    stated by observing the store, never by trusting a returned count.
    """
    namespace = ok(namespace_for_write(world))
    raw = store.root / namespace / "immutable-raw-archive"
    engine = ParquetColumnarEngine(raw)
    rows: list[dict[str, object]] = []
    for key in engine.stored_keys():
        try:
            artifact = engine.read(key)
        except StoreEngineError:  # pragma: no cover - defensive
            continue
        for item in artifact:
            if item.get("kind") == "qmb-data-coverage":
                continue
            if "event_time_ns" in item and "fingerprint" in item:
                rows.append(dict(item))
    return tuple(rows)


def raw_observation_fingerprints(
    store: EvidenceStore, *, world: World = World.REPLAY
) -> frozenset[str]:
    return frozenset(str(row["fingerprint"]) for row in scan_raw_observations(store, world=world))


def download_resources(dest: Path, **overrides: object) -> dict[str, object]:
    """A complete ``data download`` resource mapping with an EXPLICIT window.

    An explicit ``end_ns`` keeps the golden/idempotence walks reproducible and
    keeps FIND-001 (the ambient-clock defect) isolated to its own regression.
    """
    resources: dict[str, object] = {
        "venue": "dukascopy",
        "symbol": "EURUSD",
        "start_ns": NS,
        "end_ns": NS + 10,
        "resolution": "tick",
        "side": "both",
        "destination": str(dest),
        "world": "replay",
    }
    resources.update(overrides)
    return resources
