"""Bounded hourly fetch, window stamping, and corpus/recovery refusal collaborators."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from qmf.core import (
    Instant,
    Instrument,
    Interval,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)
from qmf.data.dukascopy_decode import DecodedTick, decode_bi5_ticks
from qmf.data.dukascopy_hour import DukascopyHourKey, DukascopyTransport, hour_keys_for_window
from qmf.data.dukascopy_types import (
    DEFAULT_PRICE_SCALE,
    DUKASCOPY_SOURCE,
    PERSONAL_USE_LICENSE,
    LicensedSourceWindow,
    LicenseTag,
    parse_license_tag,
    refuse_complete_corpus_download,
    refuse_external_recovery,
)
from qmf.data.ingest_types import ProviderRecord, SourceRequest
from qmf.data.partitions import SeriesPartition
from qmf.data.store.refusals import invalid_input


def clean_bound_str(value: object) -> str | None:
    """Return a stripped non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    return None


def require_fetch_span(
    start_raw: object, end_raw: object, max_window_ns: int
) -> Result[tuple[int, int]]:
    if isinstance(start_raw, bool) or not isinstance(start_raw, int):
        return invalid_input(
            "start_ns",
            "bounds.start_ns is required: int64 UTC-ns window start",
            given=repr(start_raw),
        )
    if isinstance(end_raw, bool) or not isinstance(end_raw, int):
        return invalid_input(
            "end_ns",
            "bounds.end_ns is required: int64 UTC-ns half-open window end — "
            "unbounded / complete-corpus downloads are refused (FM-5)",
            given=repr(end_raw),
        )
    if end_raw <= start_raw:
        return invalid_input(
            "window",
            "a Dukascopy fetch window is a non-empty half-open [start_ns, end_ns)",
            start_ns=start_raw,
            end_ns=end_raw,
        )
    span = end_raw - start_raw
    if span > max_window_ns:
        return refuse_complete_corpus_download(request=f"window_ns={span}>max={max_window_ns}")
    return Ok((start_raw, end_raw))


class DukascopyFetchWindow:
    """Bounded hourly fetch plus license-tagged last window."""

    def __init__(
        self,
        transport: DukascopyTransport,
        *,
        instruments: Mapping[str, Instrument],
        price_scales: Mapping[str, int],
        default_license: LicenseTag,
        max_window_ns: int,
    ) -> None:
        self._transport = transport
        self._instruments = dict(instruments)
        self._price_scales = dict(price_scales)
        self._default_license = default_license
        self._max_window_ns = max_window_ns
        self._last_window: LicensedSourceWindow | None = None
        self._source = DUKASCOPY_SOURCE

    @property
    def source(self) -> str:
        return self._source

    @property
    def last_window(self) -> LicensedSourceWindow | None:
        return self._last_window

    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        window = self._parse_fetch_window(request)
        if is_refusal(window):
            return window
        symbol, start_raw, end_raw, known_at, revision, instrument, price_scale = window.value
        hour_keys = hour_keys_for_window(start_raw, end_raw, symbol)
        if is_refusal(hour_keys):
            return hour_keys
        records = self._records_for_hours(
            hour_keys.value,
            symbol=symbol,
            instrument=instrument,
            start_ns=start_raw,
            end_ns=end_raw,
            known_at_ns=known_at,
            revision=revision,
            price_scale=price_scale,
        )
        if is_refusal(records):
            return records
        bounds = dict(request.bounds)
        license_tag = parse_license_tag(bounds.get("license_tag", self._default_license))
        stamped = self._record_window(
            instrument=instrument,
            start_ns=start_raw,
            end_ns=end_raw,
            license_tag=license_tag,
            symbol=symbol,
            revision=revision,
            tick_count=len(records.value),
        )
        if is_refusal(stamped):
            return stamped
        self._last_window = stamped.value
        return Ok(tuple(records.value))

    def _parse_fetch_window(
        self, request: SourceRequest
    ) -> Result[tuple[str, int, int, int, str, Instrument, int]]:
        if request.source != self._source:
            return invalid_input(
                "source",
                "DukascopyAdapter serves source 'dukascopy' only",
                given=request.source,
            )
        bounds = dict(request.bounds)
        if bounds.get("complete_corpus") is True:
            return refuse_complete_corpus_download(request="complete_corpus=true")
        symbol = clean_bound_str(bounds.get("symbol"))
        if symbol is None:
            return invalid_input(
                "symbol",
                "a Dukascopy fetch names a non-empty provider symbol in bounds",
                given=repr(bounds.get("symbol")),
            )
        symbol = symbol.upper()
        span = require_fetch_span(
            bounds.get("start_ns"), bounds.get("end_ns"), self._max_window_ns
        )
        if is_refusal(span):
            return span
        start_raw, end_raw = span.value
        instrument = self._instruments.get(symbol)
        if instrument is None:
            return invalid_input(
                "instrument",
                "Dukascopy symbol cannot map to a source-qualified CT-03 Instrument; "
                "no evidence is emitted (FM-2, DEC-0107)",
                symbol=symbol,
            )
        known_at = bounds.get("known_at_ns", end_raw)
        if isinstance(known_at, bool) or not isinstance(known_at, int):
            return invalid_input(
                "known_at_ns",
                "known_at_ns must be an int64 UTC-ns instant when present",
                given=repr(known_at),
            )
        revision = clean_bound_str(bounds.get("revision")) or "r1"
        price_scale = self._price_scales.get(symbol, DEFAULT_PRICE_SCALE)
        return Ok((symbol, start_raw, end_raw, known_at, revision, instrument, price_scale))

    def _records_for_hours(
        self,
        hour_keys: tuple[DukascopyHourKey, ...],
        *,
        symbol: str,
        instrument: Instrument,
        start_ns: int,
        end_ns: int,
        known_at_ns: int,
        revision: str,
        price_scale: int,
    ) -> Result[list[ProviderRecord]]:
        records: list[ProviderRecord] = []
        for key in hour_keys:
            hour_records = self._records_for_hour(
                key,
                symbol=symbol,
                instrument=instrument,
                start_ns=start_ns,
                end_ns=end_ns,
                known_at_ns=known_at_ns,
                revision=revision,
                price_scale=price_scale,
            )
            if is_refusal(hour_records):
                return hour_records
            records.extend(hour_records.value)
        return Ok(records)

    def _records_for_hour(
        self,
        key: DukascopyHourKey,
        *,
        symbol: str,
        instrument: Instrument,
        start_ns: int,
        end_ns: int,
        known_at_ns: int,
        revision: str,
        price_scale: int,
    ) -> Result[list[ProviderRecord]]:
        hour_start = key.hour_start_ns()
        if is_refusal(hour_start):
            return hour_start
        fetched = self._fetch_hour_bytes(key)
        if is_refusal(fetched):
            return fetched
        decoded = decode_bi5_ticks(
            fetched.value,
            hour_start_ns=hour_start.value,
            price_scale=price_scale,
        )
        if is_refusal(decoded):
            return decoded
        return self._records_from_ticks(
            decoded.value,
            symbol=symbol,
            instrument=instrument,
            start_ns=start_ns,
            end_ns=end_ns,
            known_at_ns=known_at_ns,
            revision=revision,
            price_scale=price_scale,
        )

    def _fetch_hour_bytes(self, key: DukascopyHourKey) -> Result[bytes]:
        try:
            fetched = self._transport.fetch_hour(key)
        except Exception as exc:  # R-007: returned, never raised across CT-15
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.YES,
                context={
                    "field": "transport",
                    "reason": (
                        "the injected Dukascopy transport raised instead of returning; "
                        "a boundary failure is returned as a typed refusal, never raised "
                        "across the CT-15 boundary (R-007, CT-04)"
                    ),
                    "hour_key": repr(key),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
        return fetched

    def _records_from_ticks(
        self,
        ticks: tuple[DecodedTick, ...],
        *,
        symbol: str,
        instrument: Instrument,
        start_ns: int,
        end_ns: int,
        known_at_ns: int,
        revision: str,
        price_scale: int,
    ) -> Result[list[ProviderRecord]]:
        records: list[ProviderRecord] = []
        for tick in ticks:
            if tick.event_time_ns < start_ns or tick.event_time_ns >= end_ns:
                continue
            built = self._tick_to_record(
                tick,
                symbol=symbol,
                instrument=instrument,
                known_at_ns=known_at_ns,
                revision=revision,
                price_scale=price_scale,
            )
            if is_refusal(built):
                return built
            records.append(built.value)
        return Ok(records)

    def _tick_to_record(
        self,
        tick: DecodedTick,
        *,
        symbol: str,
        instrument: Instrument,
        known_at_ns: int,
        revision: str,
        price_scale: int,
    ) -> Result[ProviderRecord]:
        """Map one decoded tick to a CT-15 :class:`ProviderRecord` (AC1, AC3)."""
        # Provider-native opaque id: symbol + event-time ns (never parsed by QMF).
        native_id = f"{symbol}#{tick.event_time_ns}"
        ts_verbatim = (
            datetime.fromtimestamp(tick.event_time_ns / 1_000_000_000, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        foreign_ts = {
            "verbatim": ts_verbatim,
            "zone": "UTC",
            "offset": "+00:00",
            "resolution": "ms",
        }
        return Ok(
            ProviderRecord(
                source=self._source,
                source_native_id=native_id,
                revision=revision,
                event_time=tick.event_time_ns,
                known_at=known_at_ns,
                instrument=instrument,
                foreign_timestamp=foreign_ts,
                bid={"verbatim": tick.bid_verbatim, "scale": price_scale},
                ask={"verbatim": tick.ask_verbatim, "scale": price_scale},
                bid_timestamp=foreign_ts,
                ask_timestamp=foreign_ts,
            )
        )

    def _record_window(
        self,
        *,
        instrument: Instrument,
        start_ns: int,
        end_ns: int,
        license_tag: LicenseTag,
        symbol: str,
        revision: str,
        tick_count: int,
    ) -> Result[LicensedSourceWindow]:
        """Stamp provenance + license tag onto the acquired window (AC2)."""
        start = Instant.try_create(start_ns)
        if is_refusal(start):
            return start
        end = Instant.try_create(end_ns)
        if is_refusal(end):
            return end
        interval = Interval.try_create(start.value, end.value)
        if is_refusal(interval):
            return interval
        partition = SeriesPartition.try_create(self._source, instrument, interval.value)
        if is_refusal(partition):
            return partition
        provenance: dict[str, object] = {
            "source": self._source,
            "acquisition": "download-once",
            "provider_symbol": symbol,
            "revision": revision,
            "tick_count": tick_count,
            "personal_use_posture": PERSONAL_USE_LICENSE,
            "component": "COMP-DUKASCOPY",
        }
        return LicensedSourceWindow.try_create(
            partition=partition.value,
            license_tag=license_tag,
            provenance=provenance,
        )


class DukascopyCorpusBoundary:
    """Complete-corpus asks this adapter never owns (AC4 / FM-5)."""

    def __init__(self) -> None:
        self._refuse = refuse_complete_corpus_download

    def download_complete_corpus(self, *_args: object, **_kwargs: object) -> Result[object]:
        return self._refuse(request="download_complete_corpus")


class DukascopyRecoveryBoundary:
    """Checkpoint/retry/recovery asks that stay application-owned (AC5)."""

    def __init__(self) -> None:
        self._refuse = refuse_external_recovery

    def checkpoint(self, *_args: object, **_kwargs: object) -> Result[object]:
        return self._refuse(request="checkpoint")

    def recover_external(self, *_args: object, **_kwargs: object) -> Result[object]:
        return self._refuse(request="recover_external")

    def run_retry_loop(self, *_args: object, **_kwargs: object) -> Result[object]:
        return self._refuse(request="run_retry_loop")


@dataclass(frozen=True, slots=True)
class DukascopyCollaborators:
    """Fetch window plus corpus and recovery refusal boundaries."""

    window: DukascopyFetchWindow
    corpus: DukascopyCorpusBoundary
    recovery: DukascopyRecoveryBoundary


def bind_dukascopy_adapter(
    transport: DukascopyTransport,
    *,
    instruments: Mapping[str, Instrument],
    price_scales: Mapping[str, int],
    default_license: LicenseTag,
    max_window_ns: int,
) -> DukascopyCollaborators:
    """Wire the fetch-window, corpus, and recovery collaborators."""
    return DukascopyCollaborators(
        window=DukascopyFetchWindow(
            transport,
            instruments=instruments,
            price_scales=price_scales,
            default_license=default_license,
            max_window_ns=max_window_ns,
        ),
        corpus=DukascopyCorpusBoundary(),
        recovery=DukascopyRecoveryBoundary(),
    )
