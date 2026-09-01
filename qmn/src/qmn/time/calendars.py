"""Three named calendar kinds and the activation day-boundary seam (TN-14).

Never a bare ``calendar``. Market-hours, account-scoped day-boundary (accounting),
and news calendars are distinct identities; local time and broker server time
never substitute for them (DEC-0106, DEC-0199). Activation takes effect at the
next day boundary of the account-scoped day-boundary calendar (DEC-0261) — the
full period runner is Epic 26 / TN-25; this module owns the named seam.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import CalendarIdentity, Instant, Ok, Result, TradingDate
from qmf.core.refusal import is_refusal

from qmn.time._refuse import clean_token, invalid, policy

__all__ = [
    "BANNED_BARE_CALENDAR",
    "BANNED_TIME_SUBSTITUTES",
    "CALENDAR_IDENTITIES",
    "CALENDAR_TIMER_KINDS",
    "NAMED_TIME_RULES",
    "ActivationSchedule",
    "CalendarKind",
    "DayBoundaryCalendarPort",
    "activation_effective_trading_date",
    "calendar_identities",
    "calendar_kind_from_token",
    "named_time_rules",
    "refuse_bare_calendar_token",
    "refuse_time_substitute",
]

BANNED_BARE_CALENDAR: Final[str] = "calendar"
BANNED_TIME_SUBSTITUTES: Final[frozenset[str]] = frozenset(
    {
        "local time",
        "local-time",
        "local_time",
        "broker server time",
        "broker-server-time",
        "broker_server_time",
        "host local time",
        "host-local-time",
    }
)

CALENDAR_IDENTITIES: Final[tuple[str, ...]] = (
    "market_hours_calendar",
    "day_boundary_calendar",
    "news_calendar",
)

# Qualified timer names — never a bare "calendar timer" without its kind.
CALENDAR_TIMER_KINDS: Final[tuple[str, ...]] = (
    "news_calendar_timer",
    "accounting_calendar_timer",
    "trading_calendar_timer",
    "market_hours_calendar_timer",
)

NAMED_TIME_RULES: Final[tuple[str, ...]] = (
    "news calendar",
    "accounting calendar",
    "trading calendar",
    "market-hours calendar",
    "calendar timer",
    "day-boundary calendar",
)


class CalendarKind(StrEnum):
    """The three TN-14 / AD-8 calendar kinds — never conflated."""

    MARKET_HOURS = "market_hours_calendar"
    DAY_BOUNDARY = "day_boundary_calendar"
    NEWS = "news_calendar"


class DayBoundaryCalendarPort(Protocol):
    """Account-scoped day-boundary calendar — Epic 26 fills the period runner."""

    def trading_date_for(self, instant: Instant) -> Result[TradingDate]:
        """Map an Instant onto the account day-boundary TradingDate."""
        ...

    def next_boundary_after(self, instant: Instant) -> Result[Instant]:
        """Next day-boundary Instant after ``instant`` (activation effective-at)."""
        ...

    @property
    def identity(self) -> CalendarIdentity:
        """In-band calendar identity carried on every TradingDate."""
        ...


@dataclass(frozen=True, slots=True)
class ActivationSchedule:
    """Activation deferred to the next account day-boundary (DEC-0261).

    A mid-day promote/activate does not trade until the next trading day under
    the account-scoped day-boundary calendar. Epic 26 consumes this seam.
    """

    binding_id: str
    signed_at: Instant
    effective_at: Instant
    day_boundary_calendar: CalendarIdentity
    calendar_kind: CalendarKind = CalendarKind.DAY_BOUNDARY

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_id": self.binding_id,
                "signed_at_ns": self.signed_at.value_ns,
                "effective_at_ns": self.effective_at.value_ns,
                "calendar_kind": self.calendar_kind.value,
                "day_boundary_rule_set": self.day_boundary_calendar.rule_set,
                "day_boundary_rule_set_version": self.day_boundary_calendar.rule_set_version,
                "tzdata_version": self.day_boundary_calendar.tzdata_version,
            }
        )


def calendar_identities() -> tuple[str, ...]:
    """The three named calendar identities; never a bare calendar."""
    return CALENDAR_IDENTITIES


def named_time_rules() -> tuple[str, ...]:
    """Qualified time-rule names allowed in configuration and prose."""
    return NAMED_TIME_RULES


def refuse_bare_calendar_token(token: object) -> Result[str]:
    """Refuse a bare ``calendar``; accept only a named calendar kind."""
    raw = clean_token(token)
    if raw is None:
        return invalid(
            "token",
            "a calendar kind token is a non-empty named identity",
            given=repr(token),
        )
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {BANNED_BARE_CALENDAR, "calendars"}:
        return policy(
            "calendar",
            "never a bare calendar — name market-hours, day-boundary/accounting, "
            "or news (DEC-0106)",
            given=raw,
            allowed=list(CALENDAR_IDENTITIES),
        )
    return Ok(raw)


def refuse_time_substitute(label: object) -> Result[str]:
    """Refuse local time / broker server time as a calendar or stamp substitute."""
    raw = clean_token(label)
    if raw is None:
        return invalid("label", "a time-rule label is a non-empty string", given=repr(label))
    normalized = raw.strip().lower().replace("_", " ").replace("-", " ")
    # Collapse repeated spaces for matching.
    collapsed = " ".join(normalized.split())
    banned_collapsed = {
        " ".join(item.replace("_", " ").replace("-", " ").split())
        for item in BANNED_TIME_SUBSTITUTES
    }
    if collapsed in banned_collapsed:
        return policy(
            "time_substitute",
            "local time and broker server time never substitute for a named "
            "calendar or the injected VPS clock (DEC-0199)",
            given=raw,
        )
    return Ok(raw)


def calendar_kind_from_token(token: object) -> Result[CalendarKind]:
    """Map a named token onto one of the three calendar kinds."""
    checked = refuse_bare_calendar_token(token)
    if is_refusal(checked):
        return checked
    raw = checked.value
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    aliases: dict[str, CalendarKind] = {
        "market_hours_calendar": CalendarKind.MARKET_HOURS,
        "market_hours": CalendarKind.MARKET_HOURS,
        "trading_calendar": CalendarKind.MARKET_HOURS,
        "trading": CalendarKind.MARKET_HOURS,
        "day_boundary_calendar": CalendarKind.DAY_BOUNDARY,
        "day_boundary": CalendarKind.DAY_BOUNDARY,
        "accounting_calendar": CalendarKind.DAY_BOUNDARY,
        "accounting": CalendarKind.DAY_BOUNDARY,
        "news_calendar": CalendarKind.NEWS,
        "news": CalendarKind.NEWS,
    }
    kind = aliases.get(normalized)
    if kind is None:
        return invalid(
            "token",
            "calendar kind is market_hours_calendar | day_boundary_calendar | news_calendar",
            given=raw,
            allowed=list(CALENDAR_IDENTITIES),
        )
    return Ok(kind)


def activation_effective_trading_date(
    *,
    binding_id: object,
    signed_at: object,
    day_boundary: object,
) -> Result[ActivationSchedule]:
    """Schedule activation at the next account day-boundary (DEC-0261 / FR-073).

    ``day_boundary`` is a :class:`DayBoundaryCalendarPort`. Epic 26 owns the
    period runner; this story only disciplines the named seam.
    """
    bid = clean_token(binding_id)
    if bid is None:
        return invalid(
            "binding_id",
            "activation is scoped to a non-empty binding id",
            given=repr(binding_id),
        )
    if not isinstance(signed_at, Instant):
        return invalid(
            "signed_at",
            "activation signs at an Instant from the injected clock",
            given=repr(type(signed_at).__name__),
        )
    if not _looks_like_day_boundary(day_boundary):
        return invalid(
            "day_boundary",
            "activation uses the account-scoped day-boundary calendar port "
            "(never market-hours or news)",
            given=repr(type(day_boundary).__name__),
        )
    port = cast("DayBoundaryCalendarPort", day_boundary)
    identity = port.identity
    effective: Result[Instant] = port.next_boundary_after(signed_at)
    if is_refusal(effective):
        return effective
    boundary = effective.value
    if boundary.value_ns <= signed_at.value_ns:
        return policy(
            "effective_at",
            "activation effective_at must be strictly after signed_at at the "
            "next day-boundary of the account-scoped day-boundary calendar",
            signed_at_ns=signed_at.value_ns,
            effective_at_ns=boundary.value_ns,
        )
    return Ok(
        ActivationSchedule(
            binding_id=bid,
            signed_at=signed_at,
            effective_at=boundary,
            day_boundary_calendar=identity,
            calendar_kind=CalendarKind.DAY_BOUNDARY,
        )
    )


def _looks_like_day_boundary(port: object) -> bool:
    return (
        hasattr(port, "trading_date_for")
        and hasattr(port, "next_boundary_after")
        and hasattr(port, "identity")
        and callable(getattr(port, "trading_date_for", None))
        and callable(getattr(port, "next_boundary_after", None))
    )
