"""Free Forex Factory weekly news-calendar ingest (Story 27.3 / DEC-0214).

``qmn-news-calendar.timer`` drives this application path. Forex Factory's free
weekly JSON file is the sole V1 source: no paid provider, no second free source,
no live skip. Scheduling, retries, and the provider budget live here — CT-15 is
the called ingest seam (CalendarFeedAdapter / CalendarFeedImport). A failed
refresh or ``news_calendar_max_staleness`` breach fails entries closed while
exits, protection, and recording continue, and the failure is a silent-
degradation alert.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Duration,
    Instant,
    Ok,
    Result,
    Retryability,
    TypedRefusal,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data.calendar_feed import (
    CALENDAR_FEED_SOURCE,
    CalendarFeedAdapter,
    CalendarFeedImport,
    CalendarImportReceipt,
    FailClosedReason,
    FailClosedSignal,
    fail_closed,
    journal_fail_closed,
)
from qmf.data.ingest import ExternalSourceIngest, IntakeOutcome, SourceRequest
from qmf.data.journal_producer import JournalWriter
from qmf.risk.control_window import FailClosedCause, ProposedWindowAct

from qmn.data._refuse import clean_token, invalid, policy, transient, unavailable
from qmn.protection.windows import (
    BookDoorWindowGate,
    allow_protective_act_under_windows,
    enforce_entry_at_book_door,
    stale_news_calendar_blocks_entries,
)

__all__ = [
    "BUDGET_FAILURE_ID",
    "FAILED_REFRESH_FAILURE_ID",
    "FOREX_FACTORY_WEEKLY_JSON",
    "FREE_FEED_BUDGET_DOWNLOADS",
    "FREE_FEED_BUDGET_WINDOW_NS",
    "LIVE_SKIP_FAILURE_ID",
    "NEWS_CALENDAR_ALARM_CLASS",
    "NEWS_CALENDAR_WRITER_ROLE",
    "NEWS_CALENDAR_WRITER_STREAM",
    "NS_PER_SECOND",
    "PAID_PROVIDER_FAILURE_ID",
    "PAID_PROVIDER_TOKENS",
    "SECOND_SOURCE_FAILURE_ID",
    "SOLE_V1_PROVIDER",
    "STALE_FAILURE_ID",
    "BytesSnapshotTransport",
    "NewsCalendarFiringReceipt",
    "NewsCalendarFrontier",
    "NewsCalendarRecorder",
    "NewsCalendarSettings",
    "allow_exit_under_stale_news_calendar",
    "evaluate_news_calendar_precondition",
    "fetch_unavailable_refusal",
    "gate_entry_under_news_calendar",
    "rate_limited_refusal",
    "refuse_feed_budget_breach",
    "refuse_news_calendar_live_skip",
    "refuse_paid_news_provider",
    "refuse_second_news_source",
    "require_sole_free_provider",
    "require_weekly_file_url",
    "validate_news_calendar_settings",
]


NS_PER_SECOND: Final[int] = 1_000_000_000
FREE_FEED_BUDGET_DOWNLOADS: Final[int] = 2
FREE_FEED_BUDGET_WINDOW_NS: Final[int] = 5 * 60 * NS_PER_SECOND

# FairEconomy CDN weekly file — the only V1 URL (DEC-0214). JSON only; XML is
# a second download against the same 2-per-5-minutes budget.
FOREX_FACTORY_WEEKLY_JSON: Final[str] = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
SOLE_V1_PROVIDER: Final[str] = "forex-factory-free-weekly"
NEWS_CALENDAR_WRITER_ROLE: Final[str] = "news-calendar-recorder"
NEWS_CALENDAR_WRITER_STREAM: Final[str] = "news-calendar"
NEWS_CALENDAR_ALARM_CLASS: Final[str] = "silent-degradation"

PAID_PROVIDER_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "fmp",
        "financial-modeling-prep",
        "financialmodelingprep",
        "trading-economics",
        "tradingeconomics",
        "forex-factory-premium",
        "forexfactory-premium",
        "paid",
        "paid-fallback",
        "news_calendar_provider_fallback",
        "provider-fallback",
    }
)

STALE_FAILURE_ID: Final[str] = "data.news_calendar.stale"
FAILED_REFRESH_FAILURE_ID: Final[str] = "data.news_calendar.failed_refresh"
PAID_PROVIDER_FAILURE_ID: Final[str] = "data.news_calendar.paid_provider"
SECOND_SOURCE_FAILURE_ID: Final[str] = "data.news_calendar.second_source"
BUDGET_FAILURE_ID: Final[str] = "data.news_calendar.budget_breach"
LIVE_SKIP_FAILURE_ID: Final[str] = "data.news_calendar.live_skip"

_RATE_LIMIT_SIGNALS: Final[frozenset[str]] = frozenset({"rate-limited", "provider-blocked"})


@dataclass(frozen=True, slots=True)
class NewsCalendarSettings:
    """Resolved recorder settings — no invented cadence or attempt defaults."""

    provider: str
    cadence_ns: int
    max_attempts: int
    backoff_ns: int
    weekly_file_url: str = FOREX_FACTORY_WEEKLY_JSON

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "provider": self.provider,
                "cadence_ns": self.cadence_ns,
                "max_attempts": self.max_attempts,
                "backoff_ns": self.backoff_ns,
                "weekly_file_url": self.weekly_file_url,
            }
        )


@dataclass(frozen=True, slots=True)
class NewsCalendarFrontier:
    """Newest successful ingest instant — decision-cycle staleness reads this."""

    last_ingest_at: Instant
    revision: str
    event_count: int

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "last_ingest_at_ns": self.last_ingest_at.value_ns,
                "revision": self.revision,
                "event_count": self.event_count,
            }
        )


@dataclass(frozen=True, slots=True)
class NewsCalendarFiringReceipt:
    """One timer firing: append-only intake plus the data-quality journal outcome."""

    outcome: str
    writer_id: WriterId
    attempts_used: int
    event_count: int = 0
    produced_count: int = 0
    idempotent_count: int = 0
    revision: str | None = None
    ingest_at: Instant | None = None
    alarm_class: str | None = None
    fail_closed: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "outcome": self.outcome,
                "writer": list(self.writer_id.order_tuple()),
                "attempts_used": self.attempts_used,
                "event_count": self.event_count,
                "produced_count": self.produced_count,
                "idempotent_count": self.idempotent_count,
                "revision": self.revision,
                "ingest_at_ns": (None if self.ingest_at is None else self.ingest_at.value_ns),
                "alarm_class": self.alarm_class,
                "fail_closed": self.fail_closed,
            }
        )


class BytesSnapshotTransport:
    """CalendarFeedTransport over already-fetched bytes — tests never hit the CDN."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls: list[Mapping[str, object]] = []

    def fetch_snapshot(self, bounds: Mapping[str, object], /) -> Result[bytes]:
        self.calls.append(MappingProxyType(dict(bounds)))
        return Ok(self.body)


def refuse_paid_news_provider(*, provider: object) -> TypedRefusal:
    """Refuse any paid news-calendar provider — none is minted in V1 (R4)."""
    token = clean_token(provider)
    return policy(
        "provider",
        "Forex Factory's free weekly file is the sole V1 news-calendar source; "
        "no paid fallback slot exists anywhere (DEC-0214, R4)",
        failure_id="data.news_calendar.paid_provider",
        given=token if token is not None else repr(provider),
        sole=SOLE_V1_PROVIDER,
    )


def refuse_second_news_source(*, provider: object) -> TypedRefusal:
    """Refuse a second free source — this story implements neither (R4)."""
    token = clean_token(provider)
    return policy(
        "provider",
        "a later second free source or agent-produced JSON must use the CT-15 "
        "intake shape and a future ruled config row; this story implements neither",
        failure_id="data.news_calendar.second_source",
        given=token if token is not None else repr(provider),
        sole=SOLE_V1_PROVIDER,
    )


def refuse_news_calendar_live_skip(*, request: object = None) -> TypedRefusal:
    """There is no live skip around a stale or failed news calendar."""
    extra: dict[str, object] = {
        "failure_id": "data.news_calendar.live_skip",
        "treated_as_affected": True,
        "signal": "refuse-live-skip",
    }
    token = clean_token(request)
    if token is not None:
        extra["request"] = token
    return policy(
        "skip",
        "a failed news-calendar refresh or news_calendar_max_staleness breach "
        "fails entries closed with no live skip button (TN-13, DEC-0198)",
        **extra,
    )


def require_sole_free_provider(provider: object) -> Result[str]:
    """Accept only ``forex-factory-free-weekly``."""
    token = clean_token(provider)
    if token is None:
        return invalid(
            "provider",
            "news_calendar_provider_primary names the sole V1 source",
            given=repr(provider),
            sole=SOLE_V1_PROVIDER,
        )
    folded = token.strip().lower().replace("_", "-")
    if folded == SOLE_V1_PROVIDER:
        return Ok(SOLE_V1_PROVIDER)
    if folded in PAID_PROVIDER_TOKENS or "paid" in folded:
        return refuse_paid_news_provider(provider=token)
    return refuse_second_news_source(provider=token)


def require_weekly_file_url(url: object) -> Result[str]:
    """Pin the FairEconomy weekly JSON; any other URL is a second/paid source."""
    token = clean_token(url)
    if token is None:
        return invalid(
            "url",
            "the news-calendar recorder fetches Forex Factory's free weekly JSON file",
            given=repr(url),
            sole=FOREX_FACTORY_WEEKLY_JSON,
        )
    if token == FOREX_FACTORY_WEEKLY_JSON:
        return Ok(token)
    folded = token.lower()
    if any(paid in folded for paid in PAID_PROVIDER_TOKENS):
        return refuse_paid_news_provider(provider=token)
    return refuse_second_news_source(provider=token)


def refuse_feed_budget_breach(
    *,
    cadence_ns: object,
    max_attempts: object,
    backoff_ns: object = 0,
) -> Result[None]:
    """Refuse a cadence/attempts pair that would breach 2 downloads / 5 minutes."""
    cadence = _as_ns(cadence_ns, "news_calendar_refresh_cadence")
    if is_refusal(cadence):
        return cadence
    backoff = _as_ns(backoff_ns, "news_recorder_backoff")
    if is_refusal(backoff):
        return backoff
    attempts = _as_count(max_attempts, "news_recorder_max_attempts")
    if is_refusal(attempts):
        return attempts
    if cadence.value <= 0:
        return invalid(
            "news_calendar_refresh_cadence",
            "refresh cadence is a positive duration",
            given=cadence.value,
        )
    if backoff.value < 0:
        return invalid(
            "news_recorder_backoff",
            "recorder backoff is a non-negative duration",
            given=backoff.value,
        )
    if attempts.value > FREE_FEED_BUDGET_DOWNLOADS:
        return policy(
            "news_recorder_max_attempts",
            "per-firing attempts cannot exceed the free feed's "
            "2-downloads-per-5-minutes budget; refused at compile, not throttled",
            failure_id="data.news_calendar.budget_breach",
            max_attempts=attempts.value,
            budget_downloads=FREE_FEED_BUDGET_DOWNLOADS,
            budget_window_ns=FREE_FEED_BUDGET_WINDOW_NS,
        )
    min_cadence = (FREE_FEED_BUDGET_WINDOW_NS * attempts.value) // FREE_FEED_BUDGET_DOWNLOADS
    if cadence.value < min_cadence:
        return policy(
            "news_calendar_refresh_cadence",
            "a configured cadence that would breach the free feed's "
            "2-downloads-per-5-minutes limit is refused at config compile, "
            "not silently throttled (DEC-0198)",
            failure_id="data.news_calendar.budget_breach",
            cadence_ns=cadence.value,
            min_cadence_ns=min_cadence,
            max_attempts=attempts.value,
            budget_downloads=FREE_FEED_BUDGET_DOWNLOADS,
            budget_window_ns=FREE_FEED_BUDGET_WINDOW_NS,
        )
    return Ok(None)


def validate_news_calendar_settings(
    *,
    provider: object,
    cadence_ns: object,
    max_attempts: object,
    backoff_ns: object,
    weekly_file_url: object = FOREX_FACTORY_WEEKLY_JSON,
) -> Result[NewsCalendarSettings]:
    """Validate sole source, weekly file URL, and the free-feed request budget."""
    sole = require_sole_free_provider(provider)
    if is_refusal(sole):
        return sole
    url = require_weekly_file_url(weekly_file_url)
    if is_refusal(url):
        return url
    budget = refuse_feed_budget_breach(
        cadence_ns=cadence_ns, max_attempts=max_attempts, backoff_ns=backoff_ns
    )
    if is_refusal(budget):
        return budget
    cadence = _as_ns(cadence_ns, "news_calendar_refresh_cadence")
    if is_refusal(cadence):
        return cadence
    backoff = _as_ns(backoff_ns, "news_recorder_backoff")
    if is_refusal(backoff):
        return backoff
    attempts = _as_count(max_attempts, "news_recorder_max_attempts")
    if is_refusal(attempts):
        return attempts
    return Ok(
        NewsCalendarSettings(
            provider=sole.value,
            cadence_ns=cadence.value,
            max_attempts=attempts.value,
            backoff_ns=backoff.value,
            weekly_file_url=url.value,
        )
    )


def evaluate_news_calendar_precondition(
    *,
    last_ingest_at: object,
    decision_at: object,
    max_staleness: object,
    skip_requested: object = False,
) -> Result[None]:
    """Per-decision-cycle staleness: a dead timer fails closed with no signal."""
    if skip_requested is True:
        return refuse_news_calendar_live_skip(request="live-skip")
    if last_ingest_at is None:
        return policy(
            "last_ingest_at",
            "a silently dead news-calendar timer fails entries closed by "
            "precondition; there is no live skip (DEC-0198)",
            failure_id="data.news_calendar.stale",
            cause=FailClosedCause.FAILED_CALENDAR_REFRESH.value,
            alarm_class=NEWS_CALENDAR_ALARM_CLASS,
        )
    blocked = stale_news_calendar_blocks_entries(
        last_refresh_at=last_ingest_at,
        decision_at=decision_at,
        max_staleness=max_staleness,
    )
    if is_refusal(blocked):
        return policy(
            "fail_closed",
            "a failed calendar refresh, unknown coverage, or an uncertain window "
            "blocks; there is no live skip button — the operator's control is "
            "upstream configuration exercised between sessions",
            failure_id="data.news_calendar.stale",
            alarm_class=NEWS_CALENDAR_ALARM_CLASS,
            cause=blocked.context.get("cause"),
        )
    return Ok(None)


def gate_entry_under_news_calendar(
    *,
    instrument: object,
    book_mode: object,
    decision_at: object,
    windows: object,
    would_have_been_action: object,
    last_ingest_at: object,
    max_staleness: object,
    skip_requested: object = False,
) -> Result[BookDoorWindowGate]:
    """Fail entries closed on staleness; never a live skip."""
    pre = evaluate_news_calendar_precondition(
        last_ingest_at=last_ingest_at,
        decision_at=decision_at,
        max_staleness=max_staleness,
        skip_requested=skip_requested,
    )
    if is_refusal(pre) and pre.context.get("failure_id") == "data.news_calendar.live_skip":
        return pre
    return enforce_entry_at_book_door(
        instrument=instrument,
        book_mode=book_mode,
        decision_at=decision_at,
        windows=windows,
        would_have_been_action=would_have_been_action,
        news_calendar_fresh=is_ok(pre),
    )


def allow_exit_under_stale_news_calendar() -> Result[None]:
    """Exits, protection, and recording continue through a stale news calendar."""
    return allow_protective_act_under_windows(proposed_act=ProposedWindowAct.EXIT)


@dataclass
class NewsCalendarRecorder:
    """One timer firing: budgeted fetch → CT-15 intake → data-quality journal.

    Transport is injected. Factory tests never open the live FairEconomy CDN.
    Rate-limit or block responses are not retried inside the same firing.
    """

    journal: JournalWriter
    writer: WriterId
    fetch_snapshot: Callable[[Mapping[str, object]], Result[bytes]]
    settings: NewsCalendarSettings
    world: World = World.LIVE
    clock_ns: Callable[[], int] = field(default=lambda: 0)
    sleep_ns: Callable[[int], None] = field(default=lambda _ns: None)
    publish_alert: Callable[[str, str], object] | None = None
    frontier: NewsCalendarFrontier | None = None
    _bytes: BytesSnapshotTransport = field(init=False, repr=False)
    _importer: CalendarFeedImport = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._bytes = BytesSnapshotTransport(b"[]")
        adapter = CalendarFeedAdapter(self._bytes)
        ingest = ExternalSourceIngest(adapter)
        self._importer = CalendarFeedImport(adapter, ingest, self.journal)

    def fire(self) -> Result[NewsCalendarFiringReceipt]:
        """Run one ``qmn-news-calendar.timer`` firing."""
        settings = validate_news_calendar_settings(
            provider=self.settings.provider,
            cadence_ns=self.settings.cadence_ns,
            max_attempts=self.settings.max_attempts,
            backoff_ns=self.settings.backoff_ns,
            weekly_file_url=self.settings.weekly_file_url,
        )
        if is_refusal(settings):
            return settings
        known_at = self.clock_ns()
        ingest_at = Instant.try_create(known_at)
        if is_refusal(ingest_at):
            return ingest_at
        bounds = MappingProxyType({"known_at_ns": known_at})
        fetched, attempts_used, rate_limited = self._budgeted_fetch(bounds)
        if is_refusal(fetched):
            return self._fail_refresh(
                fetched,
                ingest_at=ingest_at.value,
                attempts_used=attempts_used,
                rate_limited=rate_limited,
            )
        body = fetched.value
        revision = hashlib.sha256(body).hexdigest()
        imported = self._intake_snapshot(body, known_at_ns=known_at, revision=revision)
        if is_refusal(imported):
            return self._fail_refresh(
                imported,
                ingest_at=ingest_at.value,
                attempts_used=attempts_used,
                rate_limited=False,
            )
        outcome_value = imported.value
        if isinstance(outcome_value, FailClosedSignal):
            alarmed = self._alarm(
                "data.news_calendar.failed_refresh",
                "news-calendar refresh failed closed",
            )
            if is_refusal(alarmed):
                return alarmed
            return Ok(
                NewsCalendarFiringReceipt(
                    outcome="failed-refresh",
                    writer_id=self.writer,
                    attempts_used=attempts_used,
                    ingest_at=ingest_at.value,
                    alarm_class=NEWS_CALENDAR_ALARM_CLASS,
                    fail_closed=True,
                )
            )
        receipt = cast("CalendarImportReceipt", outcome_value)
        produced = 0
        idempotent = 0
        for item in receipt.intake_receipts:
            if item.outcome is IntakeOutcome.PRODUCED:
                produced += 1
            else:
                idempotent += 1
        self.frontier = NewsCalendarFrontier(
            last_ingest_at=ingest_at.value,
            revision=revision,
            event_count=len(receipt.events),
        )
        return Ok(
            NewsCalendarFiringReceipt(
                outcome="imported" if produced else "idempotent",
                writer_id=self.writer,
                attempts_used=attempts_used,
                event_count=len(receipt.events),
                produced_count=produced,
                idempotent_count=idempotent,
                revision=revision,
                ingest_at=ingest_at.value,
                fail_closed=False,
            )
        )

    def _budgeted_fetch(self, bounds: Mapping[str, object]) -> tuple[Result[bytes], int, bool]:
        last: Result[bytes] | None = None
        used = 0
        for attempt in range(self.settings.max_attempts):
            used = attempt + 1
            last = self.fetch_snapshot(bounds)
            if is_ok(last):
                return last, used, False
            if is_refusal(last) and _is_rate_limit_or_block(last):
                return last, used, True
            if used < self.settings.max_attempts and self.settings.backoff_ns > 0:
                self.sleep_ns(self.settings.backoff_ns)
        if last is None:
            return fetch_unavailable_refusal(retryable=False), used, False
        return last, used, False

    def _intake_snapshot(
        self, body: bytes, *, known_at_ns: int, revision: str
    ) -> Result[CalendarImportReceipt | FailClosedSignal]:
        self._bytes.body = body
        return self._importer.run(
            SourceRequest(
                source=CALENDAR_FEED_SOURCE,
                bounds=MappingProxyType({"known_at_ns": known_at_ns, "revision": revision}),
            ),
            writer=self.writer,
            world=self.world,
            receive_wall_time=known_at_ns,
            journal_instant=known_at_ns,
        )

    def _fail_refresh(
        self,
        refusal: TypedRefusal,
        *,
        ingest_at: Instant,
        attempts_used: int,
        rate_limited: bool,
    ) -> Result[NewsCalendarFiringReceipt]:
        detail: dict[str, object] = {
            "refusal_category": refusal.category.value,
            "retryability": refusal.retryability.value,
            "provider_context": dict(refusal.context),
            "rate_limited": rate_limited,
        }
        signal = fail_closed(FailClosedReason.FAILED_REFRESH, detail=detail)
        if is_refusal(signal):
            return signal
        journaled = journal_fail_closed(self.journal, signal.value, instant=ingest_at.value_ns)
        if is_refusal(journaled):
            return journaled
        alarmed = self._alarm(
            "data.news_calendar.failed_refresh",
            "news-calendar rate-limited; not retried"
            if rate_limited
            else "news-calendar refresh failed; entries fail closed",
        )
        if is_refusal(alarmed):
            return alarmed
        return Ok(
            NewsCalendarFiringReceipt(
                outcome="rate-limited" if rate_limited else "failed-refresh",
                writer_id=self.writer,
                attempts_used=attempts_used,
                ingest_at=ingest_at,
                alarm_class=NEWS_CALENDAR_ALARM_CLASS,
                fail_closed=True,
            )
        )

    def _alarm(self, failure_id: str, summary: str) -> Result[None]:
        if self.publish_alert is None:
            return Ok(None)
        published = self.publish_alert(failure_id, summary)
        if isinstance(published, TypedRefusal):
            return published
        return Ok(None)


def _is_rate_limit_or_block(refusal: TypedRefusal) -> bool:
    signal = refusal.context.get("signal")
    if isinstance(signal, str) and signal in _RATE_LIMIT_SIGNALS:
        return True
    http = refusal.context.get("http_status")
    return http in {429, 403}


def _as_ns(value: object, field: str) -> Result[int]:
    if isinstance(value, Duration):
        return Ok(value.value_ns)
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            field,
            "a news-calendar duration is int64 nanoseconds (or a Duration)",
            given=repr(value),
        )
    return Ok(value)


def _as_count(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(field, "attempt count is a positive integer", given=repr(value))
    if value < 1:
        return invalid(field, "attempt count is a positive integer", given=value)
    return Ok(value)


def rate_limited_refusal(*, http_status: int = 429) -> TypedRefusal:
    """Provider 429/403 — journalled, alarmed, never retried this firing."""
    signal = "rate-limited" if http_status == 429 else "provider-blocked"
    return transient(
        "transport",
        "provider rate-limit or block is journaled as data quality and never "
        "retried inside the same firing (DEC-0198)",
        retryability=Retryability.NO,
        failure_id="data.news_calendar.failed_refresh",
        signal=signal,
        http_status=http_status,
        alarm_class=NEWS_CALENDAR_ALARM_CLASS,
    )


def fetch_unavailable_refusal(*, retryable: bool = True) -> TypedRefusal:
    """Unreachable or 5xx provider — may retry inside the firing budget."""
    return unavailable(
        "transport",
        "news-calendar provider is unavailable",
        retryability=Retryability.YES if retryable else Retryability.NO,
        failure_id="data.news_calendar.failed_refresh",
        signal="source-unavailable",
    )
