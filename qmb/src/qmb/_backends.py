"""QMB consumes the six backend QMF packages in workspace lockstep (B-13).

Never ``qmf-venue`` — live adapters are trading-node territory (DEC-0169).
Roster SemVer rides as display-only provenance on QMB occurrence records,
never identity (DEC-0167).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from qmf.core import __version__ as _CORE_VERSION
from qmf.data import __version__ as _DATA_VERSION
from qmf.indicators import __version__ as _INDICATORS_VERSION
from qmf.registry import __version__ as _REGISTRY_VERSION
from qmf.risk import __version__ as _RISK_VERSION
from qmf.structure import __version__ as _STRUCTURE_VERSION

__all__ = ["BACKEND_PACKAGES", "VENUE_PACKAGE", "backend_display_versions"]

BACKEND_PACKAGES: Final[tuple[str, ...]] = (
    "qmf-core",
    "qmf-registry",
    "qmf-data",
    "qmf-indicators",
    "qmf-structure",
    "qmf-risk",
)

VENUE_PACKAGE: Final[str] = "qmf-venue"

_DISPLAY_VERSIONS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "qmf-core": _CORE_VERSION,
        "qmf-registry": _REGISTRY_VERSION,
        "qmf-data": _DATA_VERSION,
        "qmf-indicators": _INDICATORS_VERSION,
        "qmf-structure": _STRUCTURE_VERSION,
        "qmf-risk": _RISK_VERSION,
    }
)


def backend_display_versions() -> Mapping[str, str]:
    """Roster SemVer as display-only provenance. Never identity."""
    return _DISPLAY_VERSIONS
