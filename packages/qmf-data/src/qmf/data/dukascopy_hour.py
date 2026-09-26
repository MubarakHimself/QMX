"""Dukascopy hourly file identity, injected transport port, and window hour walk."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, cast

from qmf.core import Ok, Result, is_refusal
from qmf.data.dukascopy_types import NS_PER_HOUR
from qmf.data.store.refusals import invalid_input

__all__ = [
    "DukascopyHourKey",
    "DukascopyTransport",
    "hour_keys_for_window",
]


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


def hour_keys_for_window(
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
