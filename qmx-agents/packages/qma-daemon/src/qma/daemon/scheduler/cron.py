"""Deterministic Routine schedule evaluation against qmf-core Instants (CT-49).

Cron and interval matching uses the trigger's declared IANA zone. No component
below the composition root reads the host local clock (AD-6; FR-Q62).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from qma.core.ontology.routine import RoutineSchedule
from qmf.core import Instant, Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input

__all__ = [
    "due_instants",
    "next_occurrence_after",
    "slot_end_ns",
    "validate_schedule_zone",
]


_NS_PER_SECOND: Final[int] = 1_000_000_000
_NS_PER_MINUTE: Final[int] = 60 * _NS_PER_SECOND
_MAX_CRON_SCAN_MINUTES: Final[int] = 366 * 24 * 60

_MONTH_NAMES: Final[dict[str, int]] = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_DOW_NAMES: Final[dict[str, int]] = {
    "sun": 0,
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
}


def validate_schedule_zone(iana_zone: object) -> Result[ZoneInfo]:
    """Resolve the schedule IANA zone at evaluation time — never host local."""
    if not isinstance(iana_zone, str) or iana_zone.strip() == "":
        return invalid_input(
            "iana_zone",
            "a Routine schedule carries an explicit IANA zone resolved at "
            "evaluation time (CT-49; AD-6; FR-Q62)",
            given=repr(iana_zone),
        )
    try:
        return Ok(ZoneInfo(iana_zone))
    except ZoneInfoNotFoundError:
        return invalid_input(
            "iana_zone",
            "Routine schedule IANA zone must resolve in the tz database at "
            "evaluation time (CT-49; AD-6; FR-Q62)",
            given=iana_zone,
        )
    except Exception as exc:
        return invalid_input(
            "iana_zone",
            f"Routine schedule IANA zone could not be resolved: {exc}",
            given=iana_zone,
        )


def _as_int64_instant(value_ns: int) -> Result[Instant]:
    return Instant.try_create(value_ns)


def _utc_datetime(instant: Instant) -> datetime:
    seconds, _nano = divmod(instant.value_ns, _NS_PER_SECOND)
    return datetime.fromtimestamp(seconds, tz=UTC)


def _aware_to_instant(dt: datetime) -> Result[Instant]:
    utc = dt.astimezone(UTC)
    return Instant.try_create(int(utc.timestamp()) * _NS_PER_SECOND)


def _token_to_int(token: str, names: dict[str, int] | None) -> int | None:
    folded = token.strip().lower()
    if names is not None and folded in names:
        return names[folded]
    if folded.isdigit():
        return int(folded)
    return None


def _expand_cron_field(
    raw: str,
    *,
    minimum: int,
    maximum: int,
    names: dict[str, int] | None = None,
    wrap_seven: bool = False,
) -> Result[frozenset[int]]:
    if raw.strip() == "":
        return invalid_input(
            "schedule.expression",
            "cron field is non-empty (CT-49; FR-Q62)",
            given=raw,
        )
    values: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if token == "":
            return invalid_input(
                "schedule.expression",
                "cron field list members are non-empty (CT-49; FR-Q62)",
                given=raw,
            )
        step = 1
        span = token
        if "/" in token:
            span, step_raw = token.split("/", 1)
            if not step_raw.isdigit() or int(step_raw) < 1:
                return invalid_input(
                    "schedule.expression",
                    "cron step is a positive integer (CT-49; FR-Q62)",
                    given=token,
                )
            step = int(step_raw)
        if span in {"*", ""}:
            start, end = minimum, maximum
        elif "-" in span:
            left, right = span.split("-", 1)
            start_n = _token_to_int(left, names)
            end_n = _token_to_int(right, names)
            if start_n is None or end_n is None:
                return invalid_input(
                    "schedule.expression",
                    "cron range bounds are integers or names (CT-49; FR-Q62)",
                    given=token,
                )
            start, end = start_n, end_n
        else:
            single = _token_to_int(span, names)
            if single is None:
                return invalid_input(
                    "schedule.expression",
                    "cron field members are integers, names, ranges, or '*' (CT-49; FR-Q62)",
                    given=token,
                )
            start, end = single, single
        field_max = 7 if wrap_seven else maximum
        if start > end or start < minimum or end > field_max:
            return invalid_input(
                "schedule.expression",
                "cron field values lie in the field's closed range (CT-49; FR-Q62)",
                given=token,
                minimum=minimum,
                maximum=maximum,
            )
        cursor = start
        while cursor <= end:
            mapped = 0 if wrap_seven and cursor == 7 else cursor
            if mapped < minimum or mapped > maximum:
                return invalid_input(
                    "schedule.expression",
                    "cron field values lie in the field's closed range (CT-49; FR-Q62)",
                    given=token,
                    minimum=minimum,
                    maximum=maximum,
                )
            values.add(mapped)
            cursor += step
    return Ok(frozenset(values))


def _parse_cron_expression(
    expression: str,
) -> Result[tuple[frozenset[int], frozenset[int], frozenset[int], frozenset[int], frozenset[int]]]:
    fields = expression.split()
    if len(fields) != 5:
        return invalid_input(
            "schedule.expression",
            "a cron expression is five fields: minute hour day-of-month month "
            "day-of-week (CT-49; FR-Q62)",
            given=expression,
        )
    minute = _expand_cron_field(fields[0], minimum=0, maximum=59)
    if is_refusal(minute):
        return minute
    hour = _expand_cron_field(fields[1], minimum=0, maximum=23)
    if is_refusal(hour):
        return hour
    dom = _expand_cron_field(fields[2], minimum=1, maximum=31)
    if is_refusal(dom):
        return dom
    month = _expand_cron_field(fields[3], minimum=1, maximum=12, names=_MONTH_NAMES)
    if is_refusal(month):
        return month
    dow = _expand_cron_field(
        fields[4],
        minimum=0,
        maximum=7,
        names=_DOW_NAMES,
        wrap_seven=True,
    )
    if is_refusal(dow):
        return dow
    return Ok((minute.value, hour.value, dom.value, month.value, dow.value))


def _cron_matches(
    local: datetime,
    minute: frozenset[int],
    hour: frozenset[int],
    dom: frozenset[int],
    month: frozenset[int],
    dow: frozenset[int],
    *,
    dom_restricted: bool,
    dow_restricted: bool,
) -> bool:
    if local.minute not in minute or local.hour not in hour or local.month not in month:
        return False
    day_of_week = (local.weekday() + 1) % 7  # Monday=0 -> Sunday=0
    dom_ok = local.day in dom
    dow_ok = day_of_week in dow
    if dom_restricted and dow_restricted:
        return dom_ok or dow_ok
    return dom_ok and dow_ok


def next_occurrence_after(schedule: RoutineSchedule, after: Instant) -> Result[Instant]:
    """Exclusive next fire instant after ``after`` in the schedule's IANA zone."""
    zone = validate_schedule_zone(schedule.iana_zone)
    if is_refusal(zone):
        return zone
    if schedule.kind == "interval":
        every = schedule.every_ns
        if every is None:
            return invalid_input(
                "schedule.every_ns",
                "interval schedule requires every_ns (CT-49; FR-Q62)",
            )
        nxt = after.value_ns + every
        return _as_int64_instant(nxt)

    expression = schedule.expression
    if expression is None:
        return invalid_input(
            "schedule.expression",
            "cron schedule requires an expression (CT-49; FR-Q62)",
        )
    parsed = _parse_cron_expression(expression)
    if is_refusal(parsed):
        return parsed
    minute, hour, dom, month, dow = parsed.value
    dom_restricted = "*" not in expression.split()[2]
    dow_restricted = "*" not in expression.split()[4]
    local = _utc_datetime(after).astimezone(zone.value)
    cursor = local.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(_MAX_CRON_SCAN_MINUTES):
        if _cron_matches(
            cursor,
            minute,
            hour,
            dom,
            month,
            dow,
            dom_restricted=dom_restricted,
            dow_restricted=dow_restricted,
        ):
            return _aware_to_instant(cursor)
        cursor = cursor + timedelta(minutes=1)
    return invalid_input(
        "schedule.expression",
        "cron expression produced no occurrence within a year (CT-49; FR-Q62)",
        given=expression,
    )


def due_instants(
    schedule: RoutineSchedule,
    *,
    after_ns: int,
    until_ns: int,
    first_due_ns: int | None = None,
) -> Result[tuple[int, ...]]:
    """Scheduled fire instants in ``(after_ns, until_ns]``.

    ``first_due_ns`` is the first interval due (created_at + every_ns). Cron
    ignores it and walks from ``after_ns``.
    """
    if until_ns <= after_ns:
        return Ok(())
    if schedule.kind == "interval":
        every = schedule.every_ns
        if every is None or every <= 0:
            return invalid_input(
                "schedule.every_ns",
                "interval schedule requires a positive every_ns (CT-49; FR-Q62)",
            )
        origin = first_due_ns if first_due_ns is not None else after_ns + every
        if origin > until_ns:
            return Ok(())
        if origin <= after_ns:
            steps = (after_ns - origin) // every + 1
            candidate = origin + steps * every
        else:
            candidate = origin
        dues: list[int] = []
        while candidate <= until_ns:
            dues.append(candidate)
            candidate += every
        return Ok(tuple(dues))

    after = Instant.try_create(after_ns)
    if is_refusal(after):
        return after
    until = Instant.try_create(until_ns)
    if is_refusal(until):
        return until
    dues_cron: list[int] = []
    cursor = after.value
    while True:
        nxt = next_occurrence_after(schedule, cursor)
        if is_refusal(nxt):
            return nxt
        if nxt.value.value_ns > until_ns:
            return Ok(tuple(dues_cron))
        dues_cron.append(nxt.value.value_ns)
        cursor = nxt.value


def slot_end_ns(schedule: RoutineSchedule, scheduled_at_ns: int) -> Result[int]:
    """Exclusive end of the fire slot that starts at ``scheduled_at_ns``."""
    if schedule.kind == "interval":
        every = schedule.every_ns
        if every is None:
            return invalid_input(
                "schedule.every_ns",
                "interval schedule requires every_ns (CT-49; FR-Q62)",
            )
        return Ok(scheduled_at_ns + every)
    return Ok(scheduled_at_ns + _NS_PER_MINUTE)
