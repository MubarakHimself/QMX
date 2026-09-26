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

License types, bi5 decode, hour keys, and fetch collaborators live in sibling
modules; this module keeps the public adapter and re-exports the public types.
"""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core import Instrument, Result
from qmf.data.dukascopy_decode import DecodedTick, decode_bi5_ticks
from qmf.data.dukascopy_fetch import bind_dukascopy_adapter
from qmf.data.dukascopy_hour import DukascopyHourKey, DukascopyTransport
from qmf.data.dukascopy_types import (
    CONTRACT_FORMAT_VERSION,
    DEFAULT_PRICE_SCALE,
    DUKASCOPY_SOURCE,
    FACTORY_MAX_WINDOW_NS,
    NS_PER_HOUR,
    NS_PER_MS,
    PERSONAL_USE_LICENSE,
    TICK_RECORD_BYTES,
    LicensedSourceWindow,
    LicenseTag,
    offer_for_governed_evidence,
    parse_license_tag,
    refuse_complete_corpus_download,
    refuse_external_recovery,
)
from qmf.data.ingest_types import ProviderRecord, SourceRequest

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
    "parse_license_tag",
    "refuse_complete_corpus_download",
    "refuse_external_recovery",
]


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
        mapped = {
            symbol.strip().upper(): instrument for symbol, instrument in instruments.items()
        }
        scales = {
            symbol.strip().upper(): scale for symbol, scale in (price_scales or {}).items()
        }
        self._collaborators = bind_dukascopy_adapter(
            transport,
            instruments=mapped,
            price_scales=scales,
            default_license=default_license,
            max_window_ns=max_window_ns,
        )

    @property
    def source(self) -> str:
        return self._collaborators.window.source

    @property
    def last_window(self) -> LicensedSourceWindow | None:
        """The most recently acquired licensed window, if any."""
        return self._collaborators.window.last_window

    def download_complete_corpus(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — bulk complete-corpus download is outside this pass (AC4)."""
        return self._collaborators.corpus.download_complete_corpus(*_args, **_kwargs)

    def checkpoint(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — checkpoint ownership is application-owned (AC5)."""
        return self._collaborators.recovery.checkpoint(*_args, **_kwargs)

    def recover_external(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — QMF cannot require external recovery (AC5)."""
        return self._collaborators.recovery.recover_external(*_args, **_kwargs)

    def run_retry_loop(self, *_args: object, **_kwargs: object) -> Result[object]:
        """Always refuse — retries are application-owned (AC5)."""
        return self._collaborators.recovery.run_retry_loop(*_args, **_kwargs)

    def fetch(self, request: SourceRequest, /) -> Result[tuple[ProviderRecord, ...]]:
        """Fetch one bounded window and emit CT-15 :class:`ProviderRecord` values (AC1).

        Required bounds keys: ``symbol``, ``start_ns``, ``end_ns``. Optional:
        ``known_at_ns``, ``revision``, ``license_tag``, ``complete_corpus``.
        """
        return self._collaborators.window.fetch(request)
