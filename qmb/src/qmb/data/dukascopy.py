"""Dukascopy provider adapter #1 for ``qmb data download`` (B-11, AR-54).

Thin front over :class:`qmf.data.dukascopy.DukascopyAdapter` / CT-15. Shapes
follow the dukascopy-node reference only — no third-party downloader code is
vendored. Transport bytes stay injected; this module never opens a network
socket (qmb bans ``http`` / ``urllib``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from qmf.core.identity import Instrument
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.dukascopy import (
    DUKASCOPY_SOURCE,
    PERSONAL_USE_LICENSE,
    DukascopyAdapter,
    DukascopyTransport,
    LicenseTag,
    parse_license_tag,
)
from qmf.data.ingest import ProviderRecord, SourceRequest

from qmb._refuse import invalid
from qmb.data.convert import provider_price_to_exact
from qmb.data.ports import DownloadSide, ProviderFetchRequest

__all__ = [
    "DUKASCOPY_BATCH_COUNT",
    "DUKASCOPY_PROVIDER",
    "DukascopyProviderAdapter",
]

DUKASCOPY_PROVIDER: Final[str] = DUKASCOPY_SOURCE
# One Dukascopy bi5 hour file is the natural fetch unit (provider-native batch).
DUKASCOPY_BATCH_COUNT: Final[int] = 1


class DukascopyProviderAdapter:
    """QMB-facing Dukascopy adapter implementing :class:`~qmb.data.ports.ProviderAdapter`."""

    def __init__(
        self,
        transport: DukascopyTransport,
        *,
        instruments: Mapping[str, Instrument],
        price_scales: Mapping[str, int] | None = None,
        default_license: LicenseTag | str = LicenseTag.INTERNAL_ONLY,
        rate_limit_per_second: int | None = None,
        earliest_by_symbol: Mapping[str, int] | None = None,
    ) -> None:
        self._inner = DukascopyAdapter(
            transport,
            instruments=instruments,
            price_scales=price_scales,
            default_license=parse_license_tag(default_license),
        )
        self._instruments = {
            symbol.strip().upper(): instrument for symbol, instrument in instruments.items()
        }
        self._price_scales = {
            symbol.strip().upper(): scale for symbol, scale in (price_scales or {}).items()
        }
        self._rate_limit = rate_limit_per_second
        self._earliest = {
            symbol.strip().upper(): instant
            for symbol, instant in (earliest_by_symbol or {}).items()
        }

    @property
    def source(self) -> str:
        return DUKASCOPY_PROVIDER

    @property
    def batch_count(self) -> int:
        return DUKASCOPY_BATCH_COUNT

    @property
    def rate_limit_per_second(self) -> int | None:
        return self._rate_limit

    @property
    def inner(self) -> DukascopyAdapter:
        """The underlying CT-15 Dukascopy adapter (qmf-data)."""
        return self._inner

    def list_symbols(self) -> Result[tuple[str, ...]]:
        return Ok(tuple(sorted(self._instruments)))

    def earliest_available(self, symbol: object, /) -> Result[int | None]:
        token = symbol if isinstance(symbol, str) and symbol.strip() != "" else None
        if token is None:
            return invalid(
                "symbol",
                "earliest_available names a non-empty provider symbol",
                given=repr(symbol),
            )
        key = token.strip().upper()
        if key not in self._instruments:
            return invalid(
                "symbol",
                "symbol is not in the injected Dukascopy instrument map",
                given=key,
            )
        # Unknown earliest is a value (None), never an invented instant (SC-07).
        return Ok(self._earliest.get(key))

    def fetch(self, request: ProviderFetchRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        if request.source != DUKASCOPY_PROVIDER:
            return invalid(
                "source",
                "DukascopyProviderAdapter serves source 'dukascopy' only",
                given=request.source,
            )
        if request.resolution != "tick":
            return invalid(
                "resolution",
                "Dukascopy adapter #1 serves tick resolution only; higher "
                "resolutions are derived later, never invented at fetch",
                given=request.resolution,
            )
        if request.side not in DownloadSide:
            return invalid(
                "side",
                "side is one of bid, ask, both",
                given=repr(request.side),
                legal=list(DownloadSide),
            )
        symbol = request.symbol.strip().upper()
        instrument = self._instruments.get(symbol)
        if instrument is None:
            return invalid(
                "symbol",
                "Dukascopy symbol cannot map to a CT-03 Instrument",
                given=symbol,
            )
        scale = self._price_scales.get(symbol, 5)
        bounds: dict[str, object] = {
            "symbol": symbol,
            "start_ns": request.start_ns,
            "end_ns": request.end_ns,
            "revision": request.revision,
            "license_tag": request.license_tag or PERSONAL_USE_LICENSE,
        }
        bounds.update(dict(request.bounds))
        fetched = self._inner.fetch(
            SourceRequest(source=DUKASCOPY_PROVIDER, bounds=bounds)
        )
        if is_refusal(fetched):
            return fetched
        records: list[ProviderRecord] = []
        for record in fetched.value:
            converted = self._convert_sides(record, instrument=instrument, scale=scale)
            if is_refusal(converted):
                return converted
            filtered = self._filter_side(converted.value, request.side)
            if is_refusal(filtered):
                return filtered
            if filtered.value is not None:
                records.append(filtered.value)
        return Ok(tuple(records))

    def _convert_sides(
        self,
        record: ProviderRecord,
        *,
        instrument: Instrument,
        scale: int,
    ) -> Result[ProviderRecord]:
        """Ensure bid/ask cross the named AD-22 conversion when present."""
        bid = record.bid
        ask = record.ask
        if bid is None and ask is None:
            return Ok(record)
        bid_money = None
        ask_money = None
        if isinstance(bid, Mapping):
            bid_body = cast("Mapping[str, object]", bid)
            bid_money = provider_price_to_exact(
                bid_body.get("verbatim"),
                instrument=instrument,
                scale=bid_body.get("scale", scale),
            )
            if is_refusal(bid_money):
                return bid_money
        elif bid is not None:
            bid_money = provider_price_to_exact(bid, instrument=instrument, scale=scale)
            if is_refusal(bid_money):
                return bid_money
        if isinstance(ask, Mapping):
            ask_body = cast("Mapping[str, object]", ask)
            ask_money = provider_price_to_exact(
                ask_body.get("verbatim"),
                instrument=instrument,
                scale=ask_body.get("scale", scale),
            )
            if is_refusal(ask_money):
                return ask_money
        elif ask is not None:
            ask_money = provider_price_to_exact(ask, instrument=instrument, scale=scale)
            if is_refusal(ask_money):
                return ask_money
        if bid_money is None or ask_money is None:
            return Ok(record)
        return Ok(
            ProviderRecord(
                source=record.source,
                source_native_id=record.source_native_id,
                revision=record.revision,
                event_time=record.event_time,
                known_at=record.known_at,
                instrument=record.instrument,
                foreign_timestamp=record.foreign_timestamp,
                foreign_money=record.foreign_money,
                correction_of=record.correction_of,
                bid={"verbatim": bid_money.value.verbatim, "scale": bid_money.value.scale},
                ask={"verbatim": ask_money.value.verbatim, "scale": ask_money.value.scale},
                bid_timestamp=record.bid_timestamp,
                ask_timestamp=record.ask_timestamp,
                mid=record.mid,
            )
        )

    def _filter_side(
        self,
        record: ProviderRecord,
        side: DownloadSide,
    ) -> Result[ProviderRecord | None]:
        """Keep bid/ask distinct; never collapse to mid. ``both`` keeps both."""
        if side is DownloadSide.BOTH:
            return Ok(record)
        # Dukascopy ticks always carry both sides as provider facts. Requesting a
        # single side still preserves both on the CT-15 record (never mid-merge);
        # the request side rides as window metadata for catalog (Story 18.3).
        if record.bid is None or record.ask is None:
            return invalid(
                "side",
                "Dukascopy ticks require both bid and ask on the provider record; "
                "a missing side is invalid input, never silently filled",
                requested=side.value,
            )
        return Ok(record)
