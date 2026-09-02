"""Live observation intake and history bootstrap (TN-13 / Story 27.2).

The recording accumulator is the single first writer. CT-10 identity persists
through governed intake; position/balance CT-20 mapping stays FTR-01-blocked.
History bootstrap is the operations-toolkit recipe, never an ad-hoc fetch.
"""

from __future__ import annotations

from typing import Final

from qmn.data.bootstrap import (
    BOOTSTRAP_CONTEXT,
    CHECKPOINT_NAME,
    DUKASCOPY_SOURCE,
    PERSONAL_USE_LICENSE,
    VENUE_HISTORICAL_RATE_PER_S,
    VENUE_SPAN_CAP_NS,
    BootstrapCheckpoint,
    BootstrapReceipt,
    HistoryBootstrap,
    RefusingLiveTransport,
    VenueContinuityBridge,
    VenueHistoryPage,
    refuse_ad_hoc_fetch,
    refuse_live_network,
    refuse_venue_span_cap,
)
from qmn.data.intake import (
    CANONICAL_LIVE_SOURCE,
    FORBIDDEN_FAILOVER_SOURCES,
    GovernedLiveIntake,
    IntakeIdentity,
    LiveIntakeOutcome,
    LiveIntakeReceipt,
    refuse_sibling_failover,
)
from qmn.data.mapping import (
    CT13_SEVEN_EVENT_TYPES,
    FTR01_BLOCKED_KINDS,
    OBSERVATION_JOURNAL_TYPE,
    assert_no_eighth_journal_type,
    journal_event_for_kind,
    refuse_ftr01_mapping,
    refuse_observation_journal_type,
)

__all__ = [
    "BOOTSTRAP_CONTEXT",
    "CANONICAL_LIVE_SOURCE",
    "CHECKPOINT_NAME",
    "CT13_SEVEN_EVENT_TYPES",
    "DATA_SURFACE",
    "DUKASCOPY_SOURCE",
    "FORBIDDEN_FAILOVER_SOURCES",
    "FTR01_BLOCKED_KINDS",
    "OBSERVATION_JOURNAL_TYPE",
    "PERSONAL_USE_LICENSE",
    "VENUE_HISTORICAL_RATE_PER_S",
    "VENUE_SPAN_CAP_NS",
    "BootstrapCheckpoint",
    "BootstrapReceipt",
    "GovernedLiveIntake",
    "HistoryBootstrap",
    "IntakeIdentity",
    "LiveIntakeOutcome",
    "LiveIntakeReceipt",
    "RefusingLiveTransport",
    "VenueContinuityBridge",
    "VenueHistoryPage",
    "assert_no_eighth_journal_type",
    "journal_event_for_kind",
    "refuse_ad_hoc_fetch",
    "refuse_ftr01_mapping",
    "refuse_live_network",
    "refuse_observation_journal_type",
    "refuse_sibling_failover",
    "refuse_venue_span_cap",
]

DATA_SURFACE: Final[str] = "qmn.data"
