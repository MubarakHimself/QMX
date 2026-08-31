"""qmn — the QMX trading node (code name only).

One uv-installable application-layer distribution (``import qmn``), built ON QMF
exactly as QMB and QML are. Never a roster package, never a framework, never an
engine, and never an operator CLI (DEC-0186, DEC-0211, DEC-0220).

``qmn.venue`` is the one sanctioned importer and wirer of ``qmf-venue`` (DEC-0241);
every other ``qmn`` module receives :class:`~qmn.venue.VenueClientPort` and the
CT-19/CT-20 shapes re-exported there. Nothing imports ``qmn``.

``__version__`` is display-only SemVer provenance and never enters ``fp1``
(DEC-0186).
"""

from __future__ import annotations

from qmn.venue import (
    ASYNC_EXEMPTION_MODULE,
    CONFORMANCE_CASES,
    FTR04_DISPOSITION,
    TRANSPORT_LOCUS,
    ConformanceCase,
    ConformanceDouble,
    ParentAsyncExemptionDisposition,
    PositionModel,
    VenueClientKind,
    VenueClientPort,
    VenueClientSelection,
    compound_command_acceptance_blocked,
    resolve_transport_locus,
    select_venue_client,
)

__all__ = [
    "ASYNC_EXEMPTION_MODULE",
    "CONFORMANCE_CASES",
    "FTR04_DISPOSITION",
    "TRANSPORT_LOCUS",
    "ConformanceCase",
    "ConformanceDouble",
    "ParentAsyncExemptionDisposition",
    "PositionModel",
    "VenueClientKind",
    "VenueClientPort",
    "VenueClientSelection",
    "__version__",
    "compound_command_acceptance_blocked",
    "resolve_transport_locus",
    "select_venue_client",
]

# Display-only provenance — never part of fp1 identity (DEC-0186).
__version__ = "0.1.0"
