"""Application-owned time surface (TN-14): three calendars stay distinct.

Never a bare ``calendar``. Market-hours, account-scoped day-boundary, and news
calendars are separate identities; local time and broker server time never
substitute for them (DEC-0106).
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "CALENDAR_IDENTITIES",
    "TIME_SURFACE",
    "calendar_identities",
]

TIME_SURFACE: Final[str] = "qmn.time"
CALENDAR_IDENTITIES: Final[tuple[str, ...]] = (
    "market_hours_calendar",
    "day_boundary_calendar",
    "news_calendar",
)


def calendar_identities() -> tuple[str, ...]:
    """The three named calendar identities; never a bare calendar."""
    return CALENDAR_IDENTITIES
