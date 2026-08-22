"""COMP-DUKASCOPY — download-once historical tick adapter (Story 6.3).

Dukascopy is CT-15 provider #1 under a **download-once**, personal-use posture
(DEC-0166, DEC-0170). This module is QMF-authored adapter surface — never
vendored ``dukascopy-node`` code (DEC-0013). Acquisition is a bounded, called
port: runs never fetch from providers; the application owns scheduling, retry,
checkpoint, and supervision (DEC-0119, DEC-0051).

What this adapter guarantees:

* **AC1** — a bounded fetch yields :class:`~qmf.data.ingest.ProviderRecord` values
  that retain source identity ``dukascopy`` and convert through
  :class:`~qmf.data.ingest.ExternalSourceIngest` into CT-10 producer values.
* **AC2** — every ingested window records provenance plus a :class:`LicenseTag`;
  offering a window without a recorded usage right for governed-evidence use is a
  typed refusal (DEC-0166, DEC-0170).
* **AC3** — malformed ticks, missing timestamps, or an unmappable instrument are
  ``invalid input`` (FM-2).
* **AC4** — a complete-corpus / unbounded factory download is refused; only
  bounded adapter evidence is permitted here (FM-5, DEC-0051).
* **AC5** — external recovery, checkpoint, and retry ownership stay
  application-owned; asking this adapter to own them is a ``policy rejection``.

Transport bytes are injected (:class:`DukascopyTransport`) so tests never hit the
live datafeed. The bi5 decoder is stdlib-only (``lzma`` + ``struct``) — build our
own, reference shape only.

Stdlib + qmf-core + the CT-15 ingest / partition types already in this package.
"""

from __future__ import annotations

import lzma
import struct
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    Instant,
    Instrument,
    Interval,
    Ok,
    Result,
    TypedRefusal,
    is_refusal,
)
from qmf.data.ingest import ProviderRecord, SourceRequest
from qmf.data.partitions import SeriesPartition
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "DEFAULT_PRICE_SCALE",
    "DUKASCOPY_SOURCE",
    "FACTORY_MAX_WINDOW_NS",
    "NS_PER_HOUR",
    "NS_PER_MS",
    "PERSONAL_USE_LICENSE",
    "TICK_RECORD_BYTES",
    "DecodedTick",
    "DukascopyAdapter",
    "DukascopyHourKey",
    "DukascopyTransport",
    "LicenseTag",
    "LicensedSourceWindow",
    "decode_bi5_ticks",
    "offer_for_governed_evidence",
    "refuse_complete_corpus_download",
    "refuse_external_recovery",
]

# Story 6.3 vocabulary format version — meaning never mutates in place (L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

# Read-only provenance noun for this provider (DEC-0117) — never a VenueId.
DUKASCOPY_SOURCE: Final[str] = "dukascopy"

# Personal-use posture ruled closed for own-strategy backtesting (DEC-0170).
PERSONAL_USE_LICENSE: Final[str] = "internal-only"

NS_PER_MS: Final[int] = 1_000_000
NS_PER_HOUR: Final[int] = 3_600 * 1_000_000_000
# Factory / documentation pass: only bounded adapter evidence (FM-5). One day.
FACTORY_MAX_WINDOW_NS: Final[int] = 24 * NS_PER_HOUR

TICK_RECORD_BYTES: Final[int] = 20
# Most FX majors: Dukascopy raw int / 100_000 → price; scale digits = 5.
DEFAULT_PRICE_SCALE: Final[int] = 5

_EMPTY_PROVENANCE: Final[Mapping[str, object]] = MappingProxyType({})
_TICK_STRUCT: Final[struct.Struct] = struct.Struct("!IIIff")


class LicenseTag(StrEnum):
    """Per-window usage-right tag recorded with provenance (DEC-0166, DEC-0170).

    Taxonomy mirrors the Story 18.2 gate input: a blank / unrecognized token is
    treated as :attr:`UNKNOWN` and blocks governed-evidence use. ``INTERNAL_ONLY``
    is the Dukascopy personal-use posture (DEC-0170).
    """

    REDISTRIBUTION_OK = "redistribution-ok"
    INTERNAL_ONLY = "internal-only"
    DENIED = "denied"
    UNKNOWN = "unknown"

    def grants_governed_evidence(self) -> bool:
        """Whether this tag authorizes governed-evidence citation."""
        return self in (LicenseTag.REDISTRIBUTION_OK, LicenseTag.INTERNAL_ONLY)


def parse_license_tag(value: object | None) -> LicenseTag:
    """Resolve a license token; blank / unrecognized → :attr:`LicenseTag.UNKNOWN`."""
    if value is None:
        return LicenseTag.UNKNOWN
    if isinstance(value, LicenseTag):
        return value
    if isinstance(value, str):
        token = value.strip()
        if token == "":
            return LicenseTag.UNKNOWN
        for tag in LicenseTag:
            if tag.value == token:
                return tag
        return LicenseTag.UNKNOWN
    return LicenseTag.UNKNOWN


@dataclass(frozen=True, slots=True)
class LicensedSourceWindow:
    """One acquired ``(source, instrument, time-window)`` with its license tag (AC2).

    Provenance is opaque application metadata (acquisition tool, operator, posture).
    The window may be catalogued regardless of tag; governed-evidence use is gated
    by :func:`offer_for_governed_evidence`.
    """

    partition: SeriesPartition
    license_tag: LicenseTag
    provenance: Mapping[str, object] = field(default_factory=lambda: _EMPTY_PROVENANCE)
    format_version: int = CONTRACT_FORMAT_VERSION

    @classmethod
    def try_create(
        cls,
        *,
        partition: object,
        license_tag: object | None = None,
        provenance: object | None = None,
    ) -> Result[LicensedSourceWindow]:
        """Build a licensed window; a missing / blank tag becomes ``unknown``."""
        if not isinstance(partition, SeriesPartition):
            return invalid_input(
                "partition",
                "a licensed source window is keyed by a SeriesPartition "
                "(source, instrument, time-window)",
                given=repr(partition),
            )
        if partition.source != DUKASCOPY_SOURCE:
            return invalid_input(
                "source",
                "COMP-DUKASCOPY windows carry source identity 'dukascopy'",
                given=partition.source,
            )
        tag = parse_license_tag(license_tag)
        prov: Mapping[str, object]
        if provenance is None:
            prov = _EMPTY_PROVENANCE
        elif isinstance(provenance, Mapping):
            prov = MappingProxyType(dict(cast("Mapping[str, object]", provenance)))
        else:
            return invalid_input(
                "provenance",
                "window provenance is a mapping of opaque acquisition metadata (or omitted)",
                given=repr(provenance),
            )
        return Ok(cls(partition=partition, license_tag=tag, provenance=prov))


def offer_for_governed_evidence(window: object) -> Result[LicensedSourceWindow]:
    """Admit a window for governed-evidence use, or refuse an unlicensed one (AC2).

    Tags that grant use (:attr:`LicenseTag.INTERNAL_ONLY`,
    :attr:`LicenseTag.REDISTRIBUTION_OK`) pass. ``denied``, ``unknown``, or a
    non-window value is a typed refusal — an unlicensed window never silently
    becomes governed evidence (DEC-0166, DEC-0170).
    """
    if not isinstance(window, LicensedSourceWindow):
        return invalid_input(
            "window",
            "governed-evidence use requires a LicensedSourceWindow with a recorded license tag",
            given=repr(window),
        )
    if not window.license_tag.grants_governed_evidence():
        return policy_rejection(
            "license_tag",
            "a source window without a recorded usage right cannot become governed "
            "evidence — record an authorizing license tag first (AC2, DEC-0166, "
            "DEC-0170)",
            signal="refuse-unlicensed-window",
            license_tag=window.license_tag.value,
            source=window.partition.source,
            instrument=(
                f"{window.partition.instrument.venue.value}/{window.partition.instrument.symbol}"
            ),
            window_start_ns=window.partition.window.start.value_ns,
            window_end_ns=window.partition.window.end.value_ns,
        )
    return Ok(window)


def refuse_complete_corpus_download(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse a bulk complete-corpus download during this factory pass (AC4 / FM-5).

    Only bounded adapter evidence is permitted until installation / runbook
    execution (DEC-0051, DEC-0166).
    """
    context: dict[str, object] = {
        "signal": "refuse-complete-corpus",
        "component": "COMP-DUKASCOPY",
        "contract": "CT-15",
        "posture": "download-once-bounded",
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "bounds",
        "a complete-corpus or unbounded Dukascopy download is outside this component "
        "pass — only bounded adapter evidence is permitted until installation/runbook "
        "execution (FM-5, DEC-0051, DEC-0166)",
        **context,
    )


def refuse_external_recovery(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse asking QMF to own external recovery / checkpoint / retry (AC5 / FM-1).

    When a bounded transfer stops or the source is unavailable, checkpoint, retry,
    and operator-visible refusal live in the standalone application (DEC-0051,
    DEC-0119).
    """
    context: dict[str, object] = {
        "signal": "refuse-external-recovery",
        "component": "COMP-DUKASCOPY",
        "contract": "CT-15",
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "recovery",
        "QMF cannot require external recovery; checkpoint, retry, and supervision "
        "are application-owned (FM-1, DEC-0051, DEC-0119)",
        **context,
    )


# --- bi5 decode -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DecodedTick:
    """One decoded Dukascopy tick before CT-15 :class:`ProviderRecord` minting."""

    event_time_ns: int
    bid_verbatim: int
    ask_verbatim: int
    bid_volume: float
    ask_volume: float
    source_timestamp_ms_offset: int


def decode_bi5_ticks(
    compressed: object,
    *,
    hour_start_ns: object,
    price_scale: int = DEFAULT_PRICE_SCALE,
) -> Result[tuple[DecodedTick, ...]]:
    """Decode an LZMA-compressed hourly ``.bi5`` payload into ticks (AC3).

    Record layout (big-endian, 20 bytes): ms-offset from hour start, ask int, bid
    int, ask volume float, bid volume float. Prices stay as provider scaled
    integers at ``price_scale`` — never binary floats on the money path.
    """
    del price_scale  # scale is applied by the caller when minting ForeignMoney
    if not isinstance(compressed, (bytes, bytearray)):
        return invalid_input(
            "compressed",
            "a Dukascopy bi5 payload is raw bytes (LZMA-compressed hourly ticks)",
            given=repr(type(compressed)),
        )
    start = Instant.try_create(hour_start_ns)
    if is_refusal(start):
        return start
    if len(compressed) == 0:
        # Missing hour / weekend: no ticks, not an error (provider convention).
        return Ok(())
    try:
        raw = lzma.decompress(bytes(compressed))
    except lzma.LZMAError:
        return invalid_input(
            "compressed",
            "Dukascopy bi5 payload must decompress as LZMA; malformed bytes are "
            "invalid input (FM-2)",
        )
    if len(raw) % TICK_RECORD_BYTES != 0:
        return invalid_input(
            "compressed",
            "decompressed Dukascopy bi5 length must be a multiple of 20 bytes; "
            "truncated or malformed tick frames are invalid input (FM-2)",
            byte_length=len(raw),
        )
    ticks: list[DecodedTick] = []
    base_ns = start.value.value_ns
    for offset in range(0, len(raw), TICK_RECORD_BYTES):
        ms_offset, ask_i, bid_i, ask_vol, bid_vol = _TICK_STRUCT.unpack_from(raw, offset)
        event_ns = base_ns + int(ms_offset) * NS_PER_MS
        ticks.append(
            DecodedTick(
                event_time_ns=event_ns,
                bid_verbatim=int(bid_i),
                ask_verbatim=int(ask_i),
                bid_volume=float(bid_vol),
                ask_volume=float(ask_vol),
                source_timestamp_ms_offset=int(ms_offset),
            )
        )
    return Ok(tuple(ticks))


# --- transport / hour key ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class DukascopyHourKey:
    """One Dukascopy hourly tick file identity (URL path shape reference).

    Month is **zero-indexed** in the provider path (January = 0), matching the
    public datafeed convention. This is a shape reference — not donor code.
    """

    symbol: str
    year: int
    month_0: int
    day: int
    hour: int

    @classmethod
    def try_create(
        cls,
        symbol: object,
        year: object,
        month_0: object,
        day: object,
        hour: object,
    ) -> Result[DukascopyHourKey]:
        """Validate hour-key parts."""
        if not isinstance(symbol, str) or symbol.strip() == "":
            return invalid_input(
                "symbol",
                "a Dukascopy hour key names a non-empty provider symbol",
                given=repr(symbol),
            )
        for name, value, lo, hi in (
            ("year", year, 1990, 2262),
            ("month_0", month_0, 0, 11),
            ("day", day, 1, 31),
            ("hour", hour, 0, 23),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < lo or value > hi:
                return invalid_input(
                    name,
                    f"{name} must be an int in [{lo}, {hi}]",
                    given=repr(value),
                )
        return Ok(
            cls(
                symbol=symbol.strip().upper(),
                year=cast("int", year),
                month_0=cast("int", month_0),
                day=cast("int", day),
                hour=cast("int", hour),
            )
        )

    @property
    def path_reference(self) -> str:
        """Provider path shape — documentation / logging only, never fetched here."""
        return (
            f"{self.symbol}/{self.year}/{self.month_0:02d}/{self.day:02d}/"
            f"{self.hour:02d}h_ticks.bi5"
        )

    def hour_start_ns(self) -> Result[int]:
        """UTC nanosecond instant of this hour's start."""
        try:
            # month_0 is zero-indexed; datetime wants 1-indexed months.
            dt = datetime(
                self.year,
                self.month_0 + 1,
                self.day,
                self.hour,
                tzinfo=timezone.utc,
            )
        except ValueError:
            return invalid_input(
                "hour_key",
                "Dukascopy hour key does not form a real UTC civil hour",
                path=self.path_reference,
            )
        return Ok(int(dt.timestamp() * 1_000_000_000))


class DukascopyTransport(Protocol):
    """Injected byte source for one hourly bi5 file (AC1, AC5).

    Production wires an HTTPS client; tests inject fixtures. An unreachable
    provider is ``unavailable dependency``; a rate-limit is
    ``transient venue failure``. Empty bytes mean "no ticks for this hour".
    """

    def fetch_hour(self, key: DukascopyHourKey, /) -> Result[bytes]:
        """Return compressed bi5 bytes for ``key``, or a typed refusal."""
        ...


# --- adapter ----------------------------------------------------------------


def _clean_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    return None


def _hour_keys_for_window(
    start_ns: int, end_ns: int, symbol: str
) -> Result[tuple[DukascopyHourKey, ...]]:
    """Enumerate whole UTC hours overlapping ``[start_ns, end_ns)``."""
    if end_ns <= start_ns:
        return invalid_input(
            "window",
            "a Dukascopy fetch window is a non-empty half-open [start_ns, end_ns)",
            start_ns=start_ns,
            end_ns=end_ns,
        )
    # Align down to hour boundary.
    first_hour = (start_ns // NS_PER_HOUR) * NS_PER_HOUR
    keys: list[DukascopyHourKey] = []
    cursor = first_hour
    while cursor < end_ns:
        dt = datetime.fromtimestamp(cursor / 1_000_000_000, tz=timezone.utc)
        key = DukascopyHourKey.try_create(symbol, dt.year, dt.month - 1, dt.day, dt.hour)
        if is_refusal(key):
            return key
        keys.append(key.value)
        cursor += NS_PER_HOUR
    return Ok(tuple(keys))


class DukascopyAdapter:
    """CT-15 Dukascopy historical tick adapter — download-once, license-tagged.

    Constructed with an injected :class:`DukascopyTransport` and a CT-03 instrument
    map keyed by Dukascopy symbol. Implements the ingest
    :class:`~qmf.data.ingest.ExternalSourcePort` ``fetch`` shape.
    """

    def __init__(
        self,
        transport: DukascopyTransport,
        *,
        instruments: Mapping[str, Instrument],
        price_scales: Mapping[str, int] | None = None,
        default_license: LicenseTag = LicenseTag.INTERNAL_ONLY,
        max_window_ns: int = FACTORY_MAX_WINDOW_NS,
    ) -> None:
        self._transport = transport
        self._instruments = {
            symbol.strip().upper(): instrument for symbol, instrument in instruments.items()
        }
        self._price_scales = {
            symbol.strip().upper(): scale for symbol, scale in (price_scales or {}).items()
        }
        self._default_license = default_license
        self._max_window_ns = max_window_ns
        self._last_window: LicensedSourceWindow | None = None

    @property
    def source(self) -> str:
        return DUKASCOPY_SOURCE

    @property
    def last_window(self) -> LicensedSourceWindow | None:
        """The most recently acquired licensed window, if any."""
        return self._last_window

    def download_complete_corpus(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — bulk complete-corpus download is outside this pass (AC4)."""
        return refuse_complete_corpus_download(request="download_complete_corpus")

    def checkpoint(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — checkpoint ownership is application-owned (AC5)."""
        return refuse_external_recovery(request="checkpoint")

    def recover_external(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — QMF cannot require external recovery (AC5)."""
        return refuse_external_recovery(request="recover_external")

    def run_retry_loop(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — retries are application-owned (AC5)."""
        return refuse_external_recovery(request="run_retry_loop")

    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        """Fetch one bounded window and emit CT-15 :class:`ProviderRecord` values (AC1).

        Required bounds keys: ``symbol``, ``start_ns``, ``end_ns``. Optional:
        ``known_at_ns``, ``revision``, ``license_tag``, ``complete_corpus``.
        """
        if request.source != DUKASCOPY_SOURCE:
            return invalid_input(
                "source",
                "DukascopyAdapter serves source 'dukascopy' only",
                given=request.source,
            )
        bounds = dict(request.bounds)
        if bounds.get("complete_corpus") is True:
            return refuse_complete_corpus_download(request="complete_corpus=true")

        symbol = _clean_str(bounds.get("symbol"))
        if symbol is None:
            return invalid_input(
                "symbol",
                "a Dukascopy fetch names a non-empty provider symbol in bounds",
                given=repr(bounds.get("symbol")),
            )
        symbol = symbol.upper()

        start_raw = bounds.get("start_ns")
        end_raw = bounds.get("end_ns")
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
        if span > self._max_window_ns:
            return refuse_complete_corpus_download(
                request=f"window_ns={span}>max={self._max_window_ns}"
            )

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
        revision = _clean_str(bounds.get("revision")) or "r1"
        license_tag = parse_license_tag(bounds.get("license_tag", self._default_license))
        price_scale = self._price_scales.get(symbol, DEFAULT_PRICE_SCALE)

        hour_keys = _hour_keys_for_window(start_raw, end_raw, symbol)
        if is_refusal(hour_keys):
            return hour_keys

        records: list[ProviderRecord] = []
        for key in hour_keys.value:
            hour_start = key.hour_start_ns()
            if is_refusal(hour_start):
                return hour_start
            fetched = self._transport.fetch_hour(key)
            if is_refusal(fetched):
                return fetched
            decoded = decode_bi5_ticks(
                fetched.value,
                hour_start_ns=hour_start.value,
                price_scale=price_scale,
            )
            if is_refusal(decoded):
                return decoded
            for tick in decoded.value:
                if tick.event_time_ns < start_raw or tick.event_time_ns >= end_raw:
                    continue
                built = self._tick_to_record(
                    tick,
                    symbol=symbol,
                    instrument=instrument,
                    known_at_ns=known_at,
                    revision=revision,
                    price_scale=price_scale,
                )
                if is_refusal(built):
                    return built
                records.append(built.value)

        window = self._record_window(
            instrument=instrument,
            start_ns=start_raw,
            end_ns=end_raw,
            license_tag=license_tag,
            symbol=symbol,
            revision=revision,
            tick_count=len(records),
        )
        if is_refusal(window):
            return window
        self._last_window = window.value
        return Ok(tuple(records))

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
                source=DUKASCOPY_SOURCE,
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
        partition = SeriesPartition.try_create(DUKASCOPY_SOURCE, instrument, interval.value)
        if is_refusal(partition):
            return partition
        provenance: dict[str, object] = {
            "source": DUKASCOPY_SOURCE,
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
