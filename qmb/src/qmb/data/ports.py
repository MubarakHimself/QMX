"""QMX-authored provider-adapter port for ``qmb data download`` (B-11, AR-54).

Jesse ``CandleExchange``-shaped surface: ``fetch``, ``earliest_available``,
``list_symbols``, batch ``count``, and rate-limit. Dukascopy is adapter #1.
Persistence stays in qmf-data CT-10/CT-15 — this port fetches only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, runtime_checkable

from qmf.core.refusal import Result
from qmf.data.ingest import ProviderRecord

__all__ = [
    "DOWNLOAD_SIDES",
    "PROVIDER_ADAPTER_METHODS",
    "DownloadProgress",
    "DownloadSide",
    "ProgressSink",
    "ProviderAdapter",
    "ProviderFetchRequest",
]

PROVIDER_ADAPTER_METHODS: Final[tuple[str, ...]] = (
    "fetch",
    "earliest_available",
    "list_symbols",
    "batch_count",
    "rate_limit_per_second",
)


class DownloadSide(StrEnum):
    """Requested quote-side streams for one acquisition window."""

    BID = "bid"
    ASK = "ask"
    BOTH = "both"


DOWNLOAD_SIDES: Final[tuple[str, ...]] = tuple(member.value for member in DownloadSide)


@dataclass(frozen=True, slots=True)
class ProviderFetchRequest:
    """One bounded provider fetch — opaque bounds stay provider-specific."""

    source: str
    symbol: str
    start_ns: int
    end_ns: int
    resolution: str
    side: DownloadSide
    revision: str
    license_tag: str
    bounds: Mapping[str, object] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class DownloadProgress:
    """Machine-observable long-import progress (percent, date-reached, ETA)."""

    percent: int
    date_reached_ns: int
    eta_ns: int | None
    symbol: str
    produced: int
    total_batches: int
    completed_batches: int


@runtime_checkable
class ProgressSink(Protocol):
    """Supervising-agent channel for import progress — not a human-only bar."""

    def on_progress(self, progress: DownloadProgress, /) -> None:
        """Receive one progress sample."""
        ...


@runtime_checkable
class ProviderAdapter(Protocol):
    """Swappable market-data provider port (dossier R6 / AR-54).

    Implementations return provider records or a typed CT-04 refusal. Rate-limits
    are ``transient venue failure`` with retryability as the provider states; an
    unreachable provider is ``unavailable dependency``. The port never fabricates
    observations and never persists — qmf-data CT-15/CT-10 owns intake.
    """

    @property
    def source(self) -> str:
        """Read-only provenance identity of this provider (never a VenueId)."""
        ...

    @property
    def batch_count(self) -> int:
        """Provider-native batch size (e.g. one Dukascopy hour file)."""
        ...

    @property
    def rate_limit_per_second(self) -> int | None:
        """Declared rate-limit when the operator has ruled one; else ``None``."""
        ...

    def list_symbols(self) -> Result[tuple[str, ...]]:
        """Symbols this adapter can serve under the injected instrument map."""
        ...

    def earliest_available(self, symbol: object, /) -> Result[int | None]:
        """Earliest available event-time (int64 UTC-ns), or ``None`` if unknown.

        Unknown is a value, never an invented instant (SC-07).
        """
        ...

    def fetch(self, request: ProviderFetchRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        """Fetch one bounded window as CT-15 provider records."""
        ...
