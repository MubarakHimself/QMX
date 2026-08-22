"""Tier-1 tests for the Dukascopy download-once historical tick adapter (Story 6.3)."""

from __future__ import annotations

import lzma
import struct
from datetime import datetime, timezone
from pathlib import Path

from qmf.core import (
    Instant,
    Instrument,
    Interval,
    Ok,
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
from qmf.data import (
    DUKASCOPY_SOURCE,
    FACTORY_MAX_WINDOW_NS,
    PERSONAL_USE_LICENSE,
    EvidenceStore,
    ExternalSourceIngest,
    IntakeOutcome,
    LicensedSourceWindow,
    LicenseTag,
    SeriesPartition,
    SourceObservationBoundary,
    SourceRequest,
    decode_bi5_ticks,
    offer_for_governed_evidence,
    refuse_complete_corpus_download,
    refuse_external_recovery,
)
from qmf.data.dukascopy import (
    CONTRACT_FORMAT_VERSION,
    NS_PER_HOUR,
    NS_PER_MS,
    DukascopyAdapter,
    DukascopyHourKey,
)
from qmf.data.ingest import IntakeKey

_HOUR_START = datetime(2024, 1, 15, 10, tzinfo=timezone.utc)
_HOUR_START_NS = int(_HOUR_START.timestamp() * 1_000_000_000)
_KNOWN_NS = _HOUR_START_NS + 3_600 * 1_000_000_000
_RECEIVE_NS = _KNOWN_NS + 1_000_000


def _writer() -> WriterId:
    built = WriterId.try_create("node-a", "ingest", "dukascopy", "boot-1")
    assert is_ok(built)
    return built.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    venue = VenueId.try_create("broker-a")
    assert is_ok(venue)
    built = Instrument.try_create(venue.value, symbol)
    assert is_ok(built)
    return built.value


def _pack_tick(ms: int, ask: int, bid: int) -> bytes:
    return struct.pack("!IIIff", ms, ask, bid, 1.0, 1.0)


def _bi5(*ticks: tuple[int, int, int]) -> bytes:
    raw = b"".join(_pack_tick(ms, ask, bid) for ms, ask, bid in ticks)
    return lzma.compress(raw)


class _FixtureTransport:
    """In-memory DukascopyTransport — never hits the live datafeed."""

    def __init__(self, hours: dict[str, bytes] | None = None) -> None:
        self.hours = hours or {}
        self.calls: list[DukascopyHourKey] = []
        self.mode = "ok"

    def fail_unavailable(self) -> None:
        self.mode = "unavailable"

    def fetch_hour(self, key: DukascopyHourKey, /) -> Result[bytes]:
        self.calls.append(key)
        if self.mode == "unavailable":
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.YES,
                context={"signal": "source-unavailable", "source": DUKASCOPY_SOURCE},
            )
        return Ok(self.hours.get(key.path_reference, b""))


def _adapter(
    transport: _FixtureTransport | None = None,
    *,
    instruments: dict[str, Instrument] | None = None,
) -> tuple[DukascopyAdapter, _FixtureTransport]:
    port = transport or _FixtureTransport()
    adapter = DukascopyAdapter(
        port,
        instruments=instruments or {"EURUSD": _instrument()},
    )
    return adapter, port


def _bounds(**overrides: object) -> dict[str, object]:
    parts: dict[str, object] = {
        "symbol": "EURUSD",
        "start_ns": _HOUR_START_NS,
        "end_ns": _HOUR_START_NS + NS_PER_HOUR,
        "known_at_ns": _KNOWN_NS,
        "revision": "r1",
        "license_tag": PERSONAL_USE_LICENSE,
    }
    parts.update(overrides)
    return parts


# --- AC1: download-once → CT-15 → CT-10 -------------------------------------


def test_format_version_and_source_identity() -> None:
    assert CONTRACT_FORMAT_VERSION == 1
    assert DUKASCOPY_SOURCE == "dukascopy"
    assert LicenseTag.INTERNAL_ONLY.value == PERSONAL_USE_LICENSE
    assert FACTORY_MAX_WINDOW_NS == 24 * NS_PER_HOUR


def test_fetch_decodes_bi5_and_preserves_source_identity() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    transport = _FixtureTransport({path: _bi5((0, 110260, 110250), (1_000, 110265, 110255))})
    adapter, port = _adapter(transport)
    result = adapter.fetch(SourceRequest(source=DUKASCOPY_SOURCE, bounds=_bounds()))
    assert is_ok(result)
    assert len(port.calls) == 1
    assert port.calls[0].path_reference == path
    records = result.value
    assert len(records) == 2
    assert all(r.source == DUKASCOPY_SOURCE for r in records)
    assert records[0].bid == {"verbatim": 110250, "scale": 5}
    assert records[0].ask == {"verbatim": 110260, "scale": 5}
    assert records[0].event_time == _HOUR_START_NS
    assert records[1].event_time == _HOUR_START_NS + 1_000 * NS_PER_MS
    assert adapter.last_window is not None
    assert adapter.last_window.license_tag is LicenseTag.INTERNAL_ONLY
    assert adapter.last_window.provenance["acquisition"] == "download-once"


def test_fetch_and_intake_converts_to_ct10(tmp_path: Path) -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    adapter, _port = _adapter(_FixtureTransport({path: _bi5((500, 110260, 110250))}))
    ingest = ExternalSourceIngest(adapter)
    result = ingest.fetch_and_intake(
        SourceRequest(source=DUKASCOPY_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_ok(result)
    receipt = result.value[0]
    assert receipt.outcome is IntakeOutcome.PRODUCED
    assert receipt.observation.source == DUKASCOPY_SOURCE
    assert receipt.quote is not None
    assert receipt.quote.bid.verbatim == 110250
    assert receipt.quote.ask.verbatim == 110260
    boundary = SourceObservationBoundary(EvidenceStore(tmp_path / "store"))
    admitted = ingest.submit(receipt.observation, boundary)
    assert is_ok(admitted)


# --- AC2: license tag + unlicensed refusal ----------------------------------


def test_personal_use_window_grants_governed_evidence() -> None:
    path = "EURUSD/2024/00/15/10h_ticks.bi5"
    adapter, _ = _adapter(_FixtureTransport({path: _bi5((0, 110260, 110250))}))
    fetched = adapter.fetch(SourceRequest(source=DUKASCOPY_SOURCE, bounds=_bounds()))
    assert is_ok(fetched)
    assert adapter.last_window is not None
    offered = offer_for_governed_evidence(adapter.last_window)
    assert is_ok(offered)
    assert offered.value.license_tag is LicenseTag.INTERNAL_ONLY


def test_unlicensed_window_refused_for_governed_evidence() -> None:
    start = Instant.try_create(_HOUR_START_NS)
    end = Instant.try_create(_HOUR_START_NS + NS_PER_HOUR)
    assert is_ok(start) and is_ok(end)
    window_iv = Interval.try_create(start.value, end.value)
    assert is_ok(window_iv)
    partition = SeriesPartition.try_create(DUKASCOPY_SOURCE, _instrument(), window_iv.value)
    assert is_ok(partition)
    for tag in (LicenseTag.UNKNOWN, LicenseTag.DENIED, None, ""):
        built = LicensedSourceWindow.try_create(partition=partition.value, license_tag=tag)
        assert is_ok(built)
        refused = offer_for_governed_evidence(built.value)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["signal"] == "refuse-unlicensed-window"


# --- AC3: malformed / missing / unmappable ----------------------------------


def test_malformed_bi5_is_invalid_input() -> None:
    refused = decode_bi5_ticks(b"not-lzma", hour_start_ns=_HOUR_START_NS)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_truncated_bi5_frame_is_invalid_input() -> None:
    # Valid LZMA wrapping a non-multiple-of-20 payload.
    compressed = lzma.compress(b"\x00" * 19)
    refused = decode_bi5_ticks(compressed, hour_start_ns=_HOUR_START_NS)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_missing_window_bounds_are_invalid_input() -> None:
    adapter, _ = _adapter()
    refused = adapter.fetch(
        SourceRequest(source=DUKASCOPY_SOURCE, bounds={"symbol": "EURUSD", "start_ns": 1})
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "end_ns"


def test_unmappable_instrument_is_invalid_input() -> None:
    adapter, _ = _adapter(instruments={"EURUSD": _instrument()})
    refused = adapter.fetch(
        SourceRequest(
            source=DUKASCOPY_SOURCE,
            bounds=_bounds(symbol="UNKNOWNPAIR"),
        )
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "instrument"


def test_bad_hour_start_ns_is_invalid_input() -> None:
    refused = decode_bi5_ticks(_bi5((0, 1, 1)), hour_start_ns="not-an-instant")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- AC4: no donor bulk corpus ----------------------------------------------


def test_complete_corpus_flag_is_refused() -> None:
    adapter, port = _adapter()
    refused = adapter.fetch(
        SourceRequest(
            source=DUKASCOPY_SOURCE,
            bounds=_bounds(complete_corpus=True),
        )
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["signal"] == "refuse-complete-corpus"
    assert port.calls == []


def test_download_complete_corpus_method_is_refused() -> None:
    adapter, _ = _adapter()
    refused = adapter.download_complete_corpus()
    assert is_refusal(refused)
    assert refused.context["signal"] == "refuse-complete-corpus"


def test_oversized_window_is_refused_as_corpus() -> None:
    adapter, port = _adapter()
    refused = adapter.fetch(
        SourceRequest(
            source=DUKASCOPY_SOURCE,
            bounds=_bounds(
                start_ns=_HOUR_START_NS,
                end_ns=_HOUR_START_NS + FACTORY_MAX_WINDOW_NS + NS_PER_HOUR,
            ),
        )
    )
    assert is_refusal(refused)
    assert refused.context["signal"] == "refuse-complete-corpus"
    assert port.calls == []


def test_refuse_complete_corpus_helper() -> None:
    refused = refuse_complete_corpus_download(request="bulk")
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["request"] == "bulk"


# --- AC5: application-owned recovery ----------------------------------------


def test_external_recovery_and_checkpoint_refused() -> None:
    adapter, _ = _adapter()
    for result in (
        adapter.checkpoint(),
        adapter.recover_external(),
        adapter.run_retry_loop(),
        refuse_external_recovery(request="manual"),
    ):
        assert is_refusal(result)
        assert result.category is RefusalCategory.POLICY_REJECTION
        assert result.context["signal"] == "refuse-external-recovery"


def test_unavailable_transport_propagates_no_fabricated_ticks() -> None:
    transport = _FixtureTransport()
    transport.fail_unavailable()
    adapter, _ = _adapter(transport)
    ingest = ExternalSourceIngest(adapter)
    refused = ingest.fetch_and_intake(
        SourceRequest(source=DUKASCOPY_SOURCE, bounds=_bounds()),
        writer=_writer(),
        world=World.LIVE,
        receive_wall_time=_RECEIVE_NS,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert ingest.known_key(IntakeKey(DUKASCOPY_SOURCE, "EURUSD#0", "r1")) is False


def test_empty_hour_is_ok_zero_ticks() -> None:
    # Weekend / missing hour → empty bytes → zero records, window still tagged.
    adapter, _ = _adapter(_FixtureTransport({}))
    result = adapter.fetch(SourceRequest(source=DUKASCOPY_SOURCE, bounds=_bounds()))
    assert is_ok(result)
    assert result.value == ()
    assert adapter.last_window is not None
    assert adapter.last_window.provenance["tick_count"] == 0


def test_hour_key_path_reference_shape() -> None:
    key = DukascopyHourKey.try_create("eurusd", 2024, 0, 15, 10)
    assert is_ok(key)
    assert key.value.path_reference == "EURUSD/2024/00/15/10h_ticks.bi5"
    start = key.value.hour_start_ns()
    assert is_ok(start)
    assert start.value == _HOUR_START_NS
