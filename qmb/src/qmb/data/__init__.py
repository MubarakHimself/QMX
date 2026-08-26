"""Thin fronts over qmf-data contracts (B-11).

Download, verify, catalog, and generate are fronts over the ratified data
contracts. Runs read qmf-data rooms; they never fetch from a provider.
Every ingested window carries a license tag (DEC-0166).
"""

from __future__ import annotations

from typing import Final

from qmf.data import LicenseTag, SplitManifest

from qmb.data.convert import (
    CONVERSION_BOUNDARY,
    CONVERSION_ROUNDING,
    conversion_identity,
    fingerprint_conversion,
    provider_price_to_exact,
)
from qmb.data.download import (
    DownloadReceipt,
    DownloadRequest,
    download,
    parse_download_request,
    resolve_end_ns,
)
from qmb.data.dukascopy import (
    DUKASCOPY_BATCH_COUNT,
    DUKASCOPY_PROVIDER,
    DukascopyProviderAdapter,
)
from qmb.data.policy import refuse_run_provider_fetch
from qmb.data.ports import (
    DOWNLOAD_SIDES,
    PROVIDER_ADAPTER_METHODS,
    DownloadProgress,
    DownloadSide,
    ProgressSink,
    ProviderAdapter,
    ProviderFetchRequest,
)

__all__ = [
    "CONVERSION_BOUNDARY",
    "CONVERSION_ROUNDING",
    "DATA_COMMANDS",
    "DOWNLOAD_SIDES",
    "DUKASCOPY_BATCH_COUNT",
    "DUKASCOPY_PROVIDER",
    "PROVIDER_ADAPTER_METHODS",
    "DownloadProgress",
    "DownloadReceipt",
    "DownloadRequest",
    "DownloadSide",
    "DukascopyProviderAdapter",
    "ProgressSink",
    "ProviderAdapter",
    "ProviderFetchRequest",
    "conversion_identity",
    "data_front_identity",
    "download",
    "fingerprint_conversion",
    "parse_download_request",
    "provider_price_to_exact",
    "refuse_run_provider_fetch",
    "resolve_end_ns",
]

DATA_COMMANDS: Final[tuple[str, ...]] = (
    "download",
    "verify",
    "catalog",
    "generate",
)


def data_front_identity() -> dict[str, object]:
    """Identity-bearing data-front fields. Package SemVer is omitted."""
    return {
        "commands": DATA_COMMANDS,
        "license_tag": f"{LicenseTag.__module__}.{LicenseTag.__qualname__}",
        "split_manifest": f"{SplitManifest.__module__}.{SplitManifest.__qualname__}",
        "provider_adapter_methods": PROVIDER_ADAPTER_METHODS,
        "conversion_boundary": CONVERSION_BOUNDARY,
        "download_sides": DOWNLOAD_SIDES,
        "dukascopy_provider": DUKASCOPY_PROVIDER,
    }
