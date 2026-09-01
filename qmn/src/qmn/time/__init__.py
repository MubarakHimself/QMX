"""Application-owned time surface (TN-14): live clock and three calendar kinds.

Never a bare ``calendar``. Market-hours, account-scoped day-boundary, and news
calendars are separate identities; local time and broker server time never
substitute for them (DEC-0106). The composition root injects :class:`VpsClock`;
nothing below the root reads host local time. Clock bands
``ok | warn | no-new-entry | halt`` are per-decision-cycle preconditions;
machine-versus-truth and node-versus-broker skew stay named apart (DEC-0199).
"""

from __future__ import annotations

from typing import Final

from qmn.time.calendars import (
    BANNED_BARE_CALENDAR,
    BANNED_TIME_SUBSTITUTES,
    CALENDAR_IDENTITIES,
    CALENDAR_TIMER_KINDS,
    NAMED_TIME_RULES,
    ActivationSchedule,
    CalendarKind,
    DayBoundaryCalendarPort,
    activation_effective_trading_date,
    calendar_identities,
    calendar_kind_from_token,
    named_time_rules,
    refuse_bare_calendar_token,
    refuse_time_substitute,
)
from qmn.time.clock import VPS_CLOCK_SURFACE, VpsClock
from qmn.time.discipline import (
    CLOCK_BAND_FAILURE_IDS,
    SILENT_DEGRADATION_ALARM_CLASS,
    STAND_DOWN_TRIGGER_CLOCK_HALT,
    ClockBand,
    ClockBandDecision,
    ClockDriftThresholds,
    MachineVersusTruth,
    NodeVersusBrokerSkew,
    SuspectWindow,
    SyncPosture,
    UnsynchronizedInterval,
    WallMonotonicDivergenceDetector,
    broker_skew_is_not_latency,
    clock_band_entry_side_refused,
    clock_band_preserves_protection,
    clock_band_requires_stand_down,
    evaluate_clock_band,
    evaluate_sync_posture,
    measurements_named_apart,
    record_unsynchronized_interval,
)

__all__ = [
    "BANNED_BARE_CALENDAR",
    "BANNED_TIME_SUBSTITUTES",
    "CALENDAR_IDENTITIES",
    "CALENDAR_TIMER_KINDS",
    "CLOCK_BAND_FAILURE_IDS",
    "NAMED_TIME_RULES",
    "SILENT_DEGRADATION_ALARM_CLASS",
    "STAND_DOWN_TRIGGER_CLOCK_HALT",
    "TIME_SURFACE",
    "VPS_CLOCK_SURFACE",
    "ActivationSchedule",
    "CalendarKind",
    "ClockBand",
    "ClockBandDecision",
    "ClockDriftThresholds",
    "DayBoundaryCalendarPort",
    "MachineVersusTruth",
    "NodeVersusBrokerSkew",
    "SuspectWindow",
    "SyncPosture",
    "UnsynchronizedInterval",
    "VpsClock",
    "WallMonotonicDivergenceDetector",
    "activation_effective_trading_date",
    "broker_skew_is_not_latency",
    "calendar_identities",
    "calendar_kind_from_token",
    "clock_band_entry_side_refused",
    "clock_band_preserves_protection",
    "clock_band_requires_stand_down",
    "evaluate_clock_band",
    "evaluate_sync_posture",
    "measurements_named_apart",
    "named_time_rules",
    "record_unsynchronized_interval",
    "refuse_bare_calendar_token",
    "refuse_time_substitute",
]

TIME_SURFACE: Final[str] = "qmn.time"
