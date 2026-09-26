"""Stdlib LZMA + struct decoder for Dukascopy hourly ``.bi5`` tick files."""

from __future__ import annotations

import lzma
import struct
from dataclasses import dataclass
from typing import Final

from qmf.core import Instant, Ok, Result, is_refusal
from qmf.data.dukascopy_types import DEFAULT_PRICE_SCALE, NS_PER_MS, TICK_RECORD_BYTES
from qmf.data.store.refusals import invalid_input

__all__ = [
    "DecodedTick",
    "decode_bi5_ticks",
]

_TICK_STRUCT: Final[struct.Struct] = struct.Struct("!IIIff")


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
    _ = price_scale  # scale is applied by the caller when minting ForeignMoney
    raw = _decompress_bi5(compressed)
    if is_refusal(raw):
        return raw
    start = Instant.try_create(hour_start_ns)
    if is_refusal(start):
        return start
    return Ok(_unpack_bi5_ticks(raw.value, start.value.value_ns))


def _decompress_bi5(compressed: object) -> Result[bytes]:
    if not isinstance(compressed, (bytes, bytearray)):
        return invalid_input(
            "compressed",
            "a Dukascopy bi5 payload is raw bytes (LZMA-compressed hourly ticks)",
            given=repr(type(compressed)),
        )
    if len(compressed) == 0:
        return Ok(b"")
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
    return Ok(raw)


def _unpack_bi5_ticks(raw: bytes, base_ns: int) -> tuple[DecodedTick, ...]:
    ticks: list[DecodedTick] = []
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
    return tuple(ticks)
