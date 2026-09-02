"""Deterministic WakePolicy evaluation at delivery time (CT-48; FR-Q61).

Quiet hours suppress wakes only. Delivery still proceeds. Routine firing,
an already-running Agent, and an ``approval_request`` reply are not suppressed.
The scheduler evaluates the operator-authored Quant policy; it never authors,
alters, or overrides it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from qma.core.ontology.wake_policy import (
    MAX_WAKES_PER_WINDOW_REGISTRY_KEY,
    QUIET_HOURS_REGISTRY_KEY,
    QuietHours,
    WakePolicy,
)
from qma.core.vocabulary.enums import DeliveryState, MessageKind
from qmf.core import Instant, Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input

__all__ = [
    "WAKE_EXEMPTIONS",
    "WakeDecision",
    "WakeExemption",
    "civil_window_id",
    "evaluate_delivery_wake",
    "in_quiet_hours",
    "next_quiet_hours_end",
    "resolve_iana_zone",
    "routine_fire_suppressed_by_quiet_hours",
    "running_agent_paused_by_quiet_hours",
]


WakeExemption = Literal["routine_fire", "running_agent", "approval_request_reply"]

WAKE_EXEMPTIONS: Final[frozenset[str]] = frozenset(
    {
        "routine_fire",
        "running_agent",
        "approval_request_reply",
    }
)

_UTC: Final[str] = "UTC"


@dataclass(frozen=True, slots=True)
class WakeDecision:
    """Deterministic delivery-time wake verdict (CT-48; FR-Q61)."""

    state: DeliveryState
    wake: bool
    wake_at: int | None
    reason: str
    quiet_hours_key: str = QUIET_HOURS_REGISTRY_KEY
    max_wakes_key: str = MAX_WAKES_PER_WINDOW_REGISTRY_KEY

    def to_payload(self) -> dict[str, object]:
        return {
            "delivery_state": self.state.value,
            "wake": self.wake,
            "wake_at": self.wake_at,
            "reason": self.reason,
            "quiet_hours_registry_key": self.quiet_hours_key,
            "max_wakes_per_window_registry_key": self.max_wakes_key,
        }


def resolve_iana_zone(iana_zone: object) -> Result[ZoneInfo]:
    """Resolve an explicit IANA zone at evaluation time — never host local."""
    if not isinstance(iana_zone, str) or iana_zone.strip() == "":
        return invalid_input(
            "iana_zone",
            "quiet hours carry an explicit IANA zone resolved at evaluation time "
            "(CT-48; AD-6; FR-Q61)",
            given=repr(iana_zone),
            registry_key=QUIET_HOURS_REGISTRY_KEY,
        )
    try:
        return Ok(ZoneInfo(iana_zone))
    except ZoneInfoNotFoundError:
        return invalid_input(
            "iana_zone",
            "quiet hours IANA zone must resolve in the tz database at evaluation "
            "time (CT-48; AD-6; FR-Q61)",
            given=iana_zone,
            registry_key=QUIET_HOURS_REGISTRY_KEY,
        )
    except Exception as exc:
        return invalid_input(
            "iana_zone",
            f"quiet hours IANA zone could not be resolved: {exc}",
            given=iana_zone,
            registry_key=QUIET_HOURS_REGISTRY_KEY,
        )


def _utc_datetime(instant: Instant) -> datetime:
    seconds, _nano = divmod(instant.value_ns, 1_000_000_000)
    return datetime.fromtimestamp(seconds, tz=UTC)


def _local_datetime(instant: Instant, zone: ZoneInfo) -> datetime:
    return _utc_datetime(instant).astimezone(zone)


def _instant_from_aware(dt: datetime) -> Result[Instant]:
    utc = dt.astimezone(UTC)
    return Instant.try_create(int(utc.timestamp()) * 1_000_000_000)


def _minute_of_day(local: datetime) -> int:
    return local.hour * 60 + local.minute


def in_quiet_hours(quiet: QuietHours, at: Instant) -> Result[bool]:
    """True when ``at`` falls inside the daily interval in the policy IANA zone."""
    zone = resolve_iana_zone(quiet.iana_zone)
    if is_refusal(zone):
        return zone
    local = _local_datetime(at, zone.value)
    return Ok(quiet.contains_minute(_minute_of_day(local)))


def next_quiet_hours_end(quiet: QuietHours, at: Instant) -> Result[Instant]:
    """UTC instant of the next exclusive end of the quiet-hours interval."""
    zone = resolve_iana_zone(quiet.iana_zone)
    if is_refusal(zone):
        return zone
    local = _local_datetime(at, zone.value)
    end_hour, end_minute = divmod(quiet.end_minute, 60)
    candidate = local.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    if candidate <= local:
        candidate = candidate + timedelta(days=1)
    return _instant_from_aware(candidate)


def civil_window_id(policy: WakePolicy | None, at: Instant) -> Result[str]:
    """Civil date in the quiet-hours IANA zone, or UTC when none is authored."""
    zone_name = _UTC
    if policy is not None and policy.quiet_hours is not None:
        zone_name = policy.quiet_hours.iana_zone
    zone = resolve_iana_zone(zone_name)
    if is_refusal(zone):
        return zone
    local = _local_datetime(at, zone.value)
    return Ok(local.date().isoformat())


def routine_fire_suppressed_by_quiet_hours(
    policy: WakePolicy | None,
    *,
    at: Instant,
) -> Result[bool]:
    """Quiet hours never suppress a Routine firing (CT-48; AD-29; FR-Q61)."""
    _ = (policy, at)
    return Ok(False)


def running_agent_paused_by_quiet_hours(
    policy: WakePolicy | None,
    *,
    at: Instant,
) -> Result[bool]:
    """Quiet hours never pause a run already under way (CT-48; FR-Q61)."""
    _ = (policy, at)
    return Ok(False)


def evaluate_delivery_wake(
    policy: WakePolicy | None,
    *,
    kind: MessageKind,
    at: Instant,
    wakes_in_window: int,
    exemption: WakeExemption | None = None,
) -> Result[WakeDecision]:
    """Evaluate the stored operator-authored policy at delivery time.

    No caller-supplied override is accepted: the only policy is the Quant
    record's. A wake cap that is hit never becomes a write of that policy.
    """
    if policy is None:
        return Ok(
            WakeDecision(
                state=DeliveryState.DELIVERED,
                wake=False,
                wake_at=None,
                reason="unauthored",
            )
        )

    would_wake = policy.matches(kind)
    skip_quiet = exemption == "approval_request_reply"

    if would_wake and not skip_quiet and policy.quiet_hours is not None:
        quiet = in_quiet_hours(policy.quiet_hours, at)
        if is_refusal(quiet):
            return quiet
        if quiet.value:
            wake_at = next_quiet_hours_end(policy.quiet_hours, at)
            if is_refusal(wake_at):
                return wake_at
            return Ok(
                WakeDecision(
                    state=DeliveryState.DEFERRED,
                    wake=False,
                    wake_at=wake_at.value.value_ns,
                    reason="quiet_hours",
                )
            )

    if not would_wake:
        return Ok(
            WakeDecision(
                state=DeliveryState.DELIVERED,
                wake=False,
                wake_at=None,
                reason="no_matching_condition",
            )
        )

    cap = policy.max_wakes_per_window
    if cap is not None and wakes_in_window >= cap:
        return Ok(
            WakeDecision(
                state=DeliveryState.DELIVERED,
                wake=False,
                wake_at=None,
                reason="max_wakes_per_window",
            )
        )

    return Ok(
        WakeDecision(
            state=DeliveryState.WOKE,
            wake=True,
            wake_at=None,
            reason="woke" if not skip_quiet else "approval_request_reply",
        )
    )
