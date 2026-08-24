"""Thin fronts over qmf-data contracts (B-11).

Download, verify, catalog, and generate are fronts over the ratified data
contracts. Runs read qmf-data rooms; they never fetch from a provider.
Every ingested window carries a license tag (DEC-0166).
"""

from __future__ import annotations

from typing import Final

from qmf.data import LicenseTag, SplitManifest

__all__ = ["DATA_COMMANDS", "data_front_identity"]

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
    }
