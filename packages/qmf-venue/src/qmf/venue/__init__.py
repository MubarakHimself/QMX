"""qmf.venue — the venue seam (edge module nothing imports).

Roster package of the QMF V1 uv workspace. It imports only ``qmf-core`` and nothing
imports it — the default-deny dependency direction (L30/DEC-0120) holds by
construction.

Story 8.1 lands the first work unit: the cTrader capability probe and the
per-(VenueId, account) venue-observation profile it records. The probe connects to a
demo venue through a throwaway :class:`~qmf.venue.probe.ProbeTransport` seam, runs the
first-connection verify-or-refuse suite (spot-timestamp unit, daily boundary, bar
basis, pip formula, money exponent), and returns its recorded profile plus a findings
note surfacing contradictions with upstream assumptions (FR-022, FR-026, SC-02,
AR-45/AR-46; DEC-0135, DEC-0138). The port contracts CT-18..CT-21 and the connection
manager land in later stories; the probe deliberately depends on none of them.
"""

from __future__ import annotations

from qmf.venue.observation import (
    MeasuredFact,
    ProbeCheck,
    ProbeVerdict,
    VenueEvidenceClass,
    VenueObservationProfile,
)
from qmf.venue.probe import (
    AccountMoneyRecord,
    CapabilityProbe,
    Finding,
    FindingsNote,
    ProbeReport,
    ProbeTransport,
    SpotSample,
    SymbolMetadataRecord,
    Tick,
    TickHistorySample,
    Trendbar,
    TrendbarSample,
    UpstreamAssumption,
)

__all__ = [
    "AccountMoneyRecord",
    "CapabilityProbe",
    "Finding",
    "FindingsNote",
    "MeasuredFact",
    "ProbeCheck",
    "ProbeReport",
    "ProbeTransport",
    "ProbeVerdict",
    "SpotSample",
    "SymbolMetadataRecord",
    "Tick",
    "TickHistorySample",
    "Trendbar",
    "TrendbarSample",
    "UpstreamAssumption",
    "VenueEvidenceClass",
    "VenueObservationProfile",
    "__version__",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
