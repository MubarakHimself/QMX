"""Forex-17NY CT-02 market-hours calendar provider.

Implements the two market-hours facts for rule set ``forex-17NY``:

* accounting rollover at 17:00 America/New_York (``registry:forex_rollover``)
* session schedule with weekend gaps and the pinned holiday set

Shared nouns (``TradingDate``, ``SessionWindow``, ``CivilDate``, ``Instant``) are
consumed from ``qmf-core`` only — never redefined here. Fingerprints go through
``qmf.core.fingerprint``; this module computes none of its own. Day-boundary and
news questions are out-of-authority ``unsupported capability`` refusals (FM-4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from qmf.calendar_forex._holidays import is_holiday
from qmf.calendar_forex._tzdb import RULE_SET
from qmf.core.chrono import (
    CalendarIdentity,
    CivilDate,
    Instant,
    SessionWindow,
    TradingDate,
)
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

# registry:forex_rollover — "17:00 America/New_York"; never hardcode a different zone.
ROLLOVER_ZONE: str = "America/New_York"
ROLLOVER_HOUR: int = 17
ROLLOVER_MINUTE: int = 0

_EPOCH_UTC: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
_NANOS_PER_SECOND: int = 1_000_000_000
_NY: ZoneInfo = ZoneInfo(ROLLOVER_ZONE)

# Python date.weekday(): Monday=0 … Sunday=6. Weekend trading dates are closed.
_SATURDAY: int = 5
_SUNDAY: int = 6


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


def _civil_from_date(d: date) -> Result[CivilDate]:
    return CivilDate.try_create(d.year, d.month, d.day)


def _ny_local_date(instant: Instant) -> date:
    """America/New_York civil date of ``instant``'s whole-second UTC floor.

    An intermediate for the rollover rule only — never returned as a trading date.
    Sub-second remainder cannot cross a civil day boundary.
    """
    secs = instant.value_ns // _NANOS_PER_SECOND
    utc = _EPOCH_UTC + timedelta(seconds=secs)
    return utc.astimezone(_NY).date()


def _rollover_instant_on(d: date) -> Result[Instant]:
    """The Instant of 17:00 America/New_York on civil date ``d``."""
    local = datetime(d.year, d.month, d.day, ROLLOVER_HOUR, ROLLOVER_MINUTE, 0, tzinfo=_NY)
    utc = local.astimezone(timezone.utc)
    delta = utc - _EPOCH_UTC
    ns = ((delta.days * 86_400) + delta.seconds) * _NANOS_PER_SECOND + delta.microseconds * 1000
    return Instant.try_create(ns)


def _trading_civil_of(instant: Instant) -> Result[CivilDate]:
    """Apply the 17:00 NY rollover rule; never treat the local date as the answer."""
    local_d = _ny_local_date(instant)
    boundary = _rollover_instant_on(local_d)
    if isinstance(boundary, TypedRefusal):
        return boundary
    if instant.value_ns >= boundary.value.value_ns:
        trading = local_d + timedelta(days=1)
    else:
        trading = local_d
    return _civil_from_date(trading)


def _session_bounds_for(trading: CivilDate) -> Result[tuple[Instant, Instant]]:
    """Half-open ``[prev 17:00 NY, trading-date 17:00 NY)`` for an open trading day."""
    end_date = date(trading.year, trading.month, trading.day)
    start_date = end_date - timedelta(days=1)
    open_instant = _rollover_instant_on(start_date)
    if isinstance(open_instant, TypedRefusal):
        return open_instant
    close_instant = _rollover_instant_on(end_date)
    if isinstance(close_instant, TypedRefusal):
        return close_instant
    return Ok((open_instant.value, close_instant.value))


@dataclass(frozen=True, slots=True)
class Forex17NYCalendar:
    """CT-02 market-hours calendar provider for rule set ``forex-17NY``.

    Answers only market-hours questions: which trading date an instant belongs to
    under the 17:00 America/New_York rollover, and which ``SessionWindow`` (if any)
    contains an instant under weekend gaps plus the pinned holiday set. Session and
    trading-day length are data — never assumed constant. Swap-Wednesday is not
    modeled.
    """

    identity: CalendarIdentity

    def trading_date_of(self, instant: object) -> Result[TradingDate]:
        """Trading date of ``instant`` under the forex-17NY rollover rule.

        Applies ``registry:forex_rollover`` (17:00 America/New_York) and returns a
        ``TradingDate`` via ``TradingDate.try_create``. There is no path that
        formats an Instant to a local date and treats that as the trading date
        (FM-3).
        """
        if not isinstance(instant, Instant):
            return _invalid(
                "instant",
                "trading_date_of takes an Instant; a TradingDate is never derived "
                "by formatting an instant to a local date (FM-3)",
                given=repr(instant),
            )
        civil = _trading_civil_of(instant)
        if isinstance(civil, TypedRefusal):
            return civil
        return TradingDate.try_create(self.identity, civil.value)

    def session_window(self, instant: object) -> Result[SessionWindow | None]:
        """Open ``SessionWindow`` containing ``instant``, or ``None`` when closed.

        Models weekend gaps (Friday 17:00 NY through Sunday 17:00 NY) and the
        pinned holiday set. A closed instant is a successful ``None``, not a
        refusal — closed is a schedule fact. Session length is whatever the
        bounds say; callers must not assume a constant trading-day length.
        """
        if not isinstance(instant, Instant):
            return _invalid(
                "instant",
                "session_window takes an Instant",
                given=repr(instant),
            )
        trading = self.trading_date_of(instant)
        if isinstance(trading, TypedRefusal):
            return trading
        day = trading.value.date_value
        weekday = date(day.year, day.month, day.day).weekday()
        if weekday in (_SATURDAY, _SUNDAY) or is_holiday(day):
            return Ok(None)
        bounds = _session_bounds_for(day)
        if isinstance(bounds, TypedRefusal):
            return bounds
        open_instant, close_instant = bounds.value
        window_result = SessionWindow.try_create(open_instant, close_instant, ROLLOVER_ZONE)
        if isinstance(window_result, TypedRefusal):
            return window_result
        window = window_result.value
        contains = window.contains(instant)
        if isinstance(contains, TypedRefusal):
            return contains
        if not contains.value:
            return _invalid(
                "instant",
                "instant's trading date is open but falls outside its session bounds",
                instant_ns=instant.value_ns,
            )
        return Ok(window)

    def evaluation_day_of(self, instant: object = None, account: object = None) -> TypedRefusal:
        """Day-boundary (evaluation-day) questions are out of authority (FM-4)."""
        return _unsupported(
            "calendar_kind",
            "out of authority: forex-17NY is a market-hours calendar only; "
            "day-boundary calendars are a separate named kind (FM-4)",
            requested="day-boundary",
            rule_set=RULE_SET,
            instant=repr(instant),
            account=repr(account),
        )

    def news_events(self, instant: object = None) -> TypedRefusal:
        """News-calendar questions are out of authority (FM-4)."""
        return _unsupported(
            "calendar_kind",
            "out of authority: forex-17NY is a market-hours calendar only; "
            "news calendars are a separate named kind (FM-4)",
            requested="news",
            rule_set=RULE_SET,
            instant=repr(instant),
        )

    def identity_fingerprint(self) -> Result[Fingerprint]:
        """Fingerprint of this calendar's rule-set identity via ``qmf.core.fingerprint``.

        Only the rule set plus pinned tzdata version participate — computed by the
        single canonical ``fp1`` implementation in qmf-core; this extension
        computes no fingerprint of its own.
        """
        return fingerprint(self.identity)
