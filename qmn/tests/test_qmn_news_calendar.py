"""Story 27.3 — ingest only the free Forex Factory news calendar."""

from __future__ import annotations

import ast
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    Duration,
    Instant,
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.data import EvidenceStore, JournalEventType, JournalReader, JournalWriter
from qmf.risk.control_window import (
    CurrencyExposureRecord,
    FeedQuadruple,
    WindowBounds,
    WindowKind,
    mint_control_window,
    resolve_instrument_scope,
)
from qmf.risk.paper import BookMode
from qmn.config.registry_catalog import rows_by_name
from qmn.data.news_calendar import (
    FAILED_REFRESH_FAILURE_ID,
    FOREX_FACTORY_WEEKLY_JSON,
    FREE_FEED_BUDGET_DOWNLOADS,
    FREE_FEED_BUDGET_WINDOW_NS,
    LIVE_SKIP_FAILURE_ID,
    NEWS_CALENDAR_ALARM_CLASS,
    NEWS_CALENDAR_WRITER_ROLE,
    NEWS_CALENDAR_WRITER_STREAM,
    NS_PER_SECOND,
    PAID_PROVIDER_FAILURE_ID,
    SECOND_SOURCE_FAILURE_ID,
    SOLE_V1_PROVIDER,
    STALE_FAILURE_ID,
    NewsCalendarRecorder,
    NewsCalendarSettings,
    allow_exit_under_stale_news_calendar,
    evaluate_news_calendar_precondition,
    fetch_unavailable_refusal,
    gate_entry_under_news_calendar,
    rate_limited_refusal,
    refuse_feed_budget_breach,
    refuse_news_calendar_live_skip,
    require_sole_free_provider,
    require_weekly_file_url,
    validate_news_calendar_settings,
)
from qmn.data.news_calendar_recorder import (
    NEWS_CALENDAR_USER_AGENT,
    HttpsForexFactoryTransport,
)
from qmn.data.news_calendar_recorder import (
    main as recorder_main,
)
from qmn.observability import (
    AlertPublisher,
    RecordingNotificationChannel,
    load_alert_allow_list,
)
from qmn.protection.windows import WindowActDisposition

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_KNOWN_NS = 1_725_200_000 * NS_PER_SECOND
_TWO_HOURS_NS = 2 * 3_600 * NS_PER_SECOND
_ONE_MINUTE_NS = 60 * NS_PER_SECOND
_BACKOFF_NS = 20 * NS_PER_SECOND


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _writer() -> WriterId:
    return _ok(
        WriterId.try_create(
            "vps-fra-01",
            NEWS_CALENDAR_WRITER_ROLE,
            NEWS_CALENDAR_WRITER_STREAM,
            "boot-27-3",
        )
    )


def _journal(tmp_path: Path) -> JournalWriter:
    store = EvidenceStore(tmp_path / "store")
    world = _ok(store.for_world(World.LIVE))
    return JournalWriter(world.journal, _writer(), stream_name="news-calendar")


def _settings(*, max_attempts: int = 2) -> NewsCalendarSettings:
    return _ok(
        validate_news_calendar_settings(
            provider=SOLE_V1_PROVIDER,
            cadence_ns=_TWO_HOURS_NS,
            max_attempts=max_attempts,
            backoff_ns=_BACKOFF_NS,
        )
    )


def _snapshot(*events: dict[str, object]) -> bytes:
    return json.dumps(list(events)).encode("utf-8")


def _nfp(*, note: str = "r1") -> dict[str, object]:
    return {
        "title": "Non-Farm Payrolls",
        "country": "USD",
        "date": "2024-08-20T14:30:00+00:00",
        "impact": "High",
        "id": f"nfp-2024-08-20-{note}",
    }


def _alerts() -> tuple[Callable[[str, str], object], RecordingNotificationChannel]:
    allow = _ok(load_alert_allow_list())
    channel = RecordingNotificationChannel()
    publisher = AlertPublisher(allow_list=allow, channel=channel)

    def publish(failure_id: str, summary: str) -> object:
        return publisher.publish(failure_id=failure_id, summary=summary)

    return publish, channel


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _instrument() -> Instrument:
    return _ok(Instrument.try_create(VenueId(value="ctrader"), "EURUSD"))


def _window():
    instrument = _instrument()
    start = _instant(1_000)
    end = _instant(2_000)
    known = _instant(100)
    bounds = _ok(WindowBounds.try_create(start, end))
    exposure = _ok(CurrencyExposureRecord.try_create(instrument, ("USD",), start, "exp-1"))
    scope = _ok(
        resolve_instrument_scope(
            affected_currencies=("USD",),
            candidate_instruments=(instrument,),
            exposure_records=(exposure,),
        )
    )
    feed = _ok(FeedQuadruple.try_create("news-calendar", "nfp-1", "r1", known))
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2024a"))
    return _ok(
        mint_control_window(
            bounds,
            WindowKind.NEWS,
            scope,
            "high-impact-news",
            calendar,
            "win-nfp-1",
            feed_quadruple=feed,
        )
    )


# --- sole source / no paid / no second --------------------------------------


def test_sole_provider_is_forex_factory_free_weekly() -> None:
    assert _ok(require_sole_free_provider(SOLE_V1_PROVIDER)) == SOLE_V1_PROVIDER
    assert _ok(require_weekly_file_url(FOREX_FACTORY_WEEKLY_JSON)) == FOREX_FACTORY_WEEKLY_JSON
    assert FOREX_FACTORY_WEEKLY_JSON.endswith("ff_calendar_thisweek.json")
    assert "xml" not in FOREX_FACTORY_WEEKLY_JSON


def test_paid_provider_and_second_source_are_refused() -> None:
    paid = _refusal(require_sole_free_provider("trading-economics"))
    assert paid.category is RefusalCategory.POLICY_REJECTION
    assert paid.context["failure_id"] == PAID_PROVIDER_FAILURE_ID
    second = _refusal(require_sole_free_provider("investing-com-free"))
    assert second.context["failure_id"] == SECOND_SOURCE_FAILURE_ID
    paid_url = _refusal(require_weekly_file_url("https://api.tradingeconomics.com/calendar"))
    assert paid_url.context["failure_id"] == PAID_PROVIDER_FAILURE_ID
    other = _refusal(
        require_weekly_file_url("https://nfs.faireconomy.media/ff_calendar_nextweek.json")
    )
    assert other.context["failure_id"] == SECOND_SOURCE_FAILURE_ID


def test_no_paid_fallback_registry_row_or_package() -> None:
    catalog = rows_by_name()
    assert "news_calendar_provider_fallback" not in catalog
    assert catalog["news_calendar_provider_primary"]["name"] == ("news_calendar_provider_primary")
    banned = ("fmp", "financialmodelingprep", "tradingeconomics", "fxstreet")
    hits: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0].lower()
                    if root in banned:
                        hits.append(f"{path.name}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".", 1)[0].lower()
                if root in banned:
                    hits.append(f"{path.name}:{node.module}")
    assert hits == []


def test_news_calendar_core_does_not_import_urllib() -> None:
    path = _SRC / "data" / "news_calendar.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(name == "urllib" or name.startswith("urllib.") for name in imported)


# --- budget -----------------------------------------------------------------


def test_cadence_that_breaches_free_feed_budget_is_refused() -> None:
    assert FREE_FEED_BUDGET_DOWNLOADS == 2
    assert FREE_FEED_BUDGET_WINDOW_NS == 5 * 60 * NS_PER_SECOND
    ok = _ok(
        refuse_feed_budget_breach(cadence_ns=_TWO_HOURS_NS, max_attempts=2, backoff_ns=_BACKOFF_NS)
    )
    assert ok is None
    fast = _refusal(
        refuse_feed_budget_breach(cadence_ns=_ONE_MINUTE_NS, max_attempts=1, backoff_ns=0)
    )
    assert fast.context["failure_id"] == "data.news_calendar.budget_breach"
    too_many = _refusal(
        refuse_feed_budget_breach(cadence_ns=_TWO_HOURS_NS, max_attempts=3, backoff_ns=_BACKOFF_NS)
    )
    assert too_many.context["failure_id"] == "data.news_calendar.budget_breach"


# --- timer firing / CT-15 intake --------------------------------------------


def test_timer_firing_ingests_weekly_file_append_only(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    calls: list[int] = []
    body = _snapshot(_nfp())

    def fetch(_bounds: Mapping[str, object]) -> Result[bytes]:
        calls.append(1)
        return Ok(body)

    recorder = NewsCalendarRecorder(
        journal=journal,
        writer=_writer(),
        fetch_snapshot=fetch,
        settings=_settings(),
        clock_ns=lambda: _KNOWN_NS,
    )
    first = _ok(recorder.fire())
    assert first.outcome == "imported"
    assert first.writer_id.role == NEWS_CALENDAR_WRITER_ROLE
    assert first.produced_count == 1
    assert first.fail_closed is False
    assert first.alarm_class is None
    assert recorder.frontier is not None
    assert recorder.frontier.last_ingest_at.value_ns == _KNOWN_NS
    second = _ok(recorder.fire())
    assert second.outcome == "idempotent"
    assert second.idempotent_count == 1
    assert second.revision == first.revision
    assert len(calls) == 2

    world = _ok(EvidenceStore(tmp_path / "store").for_world(World.LIVE))
    events = _ok(JournalReader(world.journal).read("news-calendar", for_world=World.LIVE))
    assert events
    assert events[0].event_type is JournalEventType.DATA_QUALITY
    assert events[0].payload["signal"] == "calendar-import"
    assert events[0].writer == _writer()


def test_rate_limit_is_not_retried_and_alarms_silent_degradation(
    tmp_path: Path,
) -> None:
    journal = _journal(tmp_path)
    publish, channel = _alerts()
    sleeps: list[int] = []

    def fetch(_bounds: Mapping[str, object]) -> Result[bytes]:
        return rate_limited_refusal(http_status=429)

    recorder = NewsCalendarRecorder(
        journal=journal,
        writer=_writer(),
        fetch_snapshot=fetch,
        settings=_settings(max_attempts=2),
        clock_ns=lambda: _KNOWN_NS,
        sleep_ns=sleeps.append,
        publish_alert=publish,
    )
    receipt = _ok(recorder.fire())
    assert receipt.outcome == "rate-limited"
    assert receipt.attempts_used == 1
    assert receipt.fail_closed is True
    assert receipt.alarm_class == NEWS_CALENDAR_ALARM_CLASS
    assert sleeps == []
    assert recorder.frontier is None
    assert channel.delivered
    assert channel.delivered[0].alert_class == "silent-degradation"
    assert channel.delivered[0].failure_id == FAILED_REFRESH_FAILURE_ID

    world = _ok(EvidenceStore(tmp_path / "store").for_world(World.LIVE))
    events = _ok(JournalReader(world.journal).read("news-calendar", for_world=World.LIVE))
    assert events[0].event_type is JournalEventType.DATA_QUALITY
    assert events[0].payload["signal"] == "calendar-fail-closed"
    assert events[0].payload["reason"] == "failed-refresh"


def test_transient_failure_retries_with_backoff_then_imports(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    sleeps: list[int] = []
    body = _snapshot(_nfp(note="retry"))
    attempts = {"n": 0}

    def fetch(_bounds: Mapping[str, object]) -> Result[bytes]:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return fetch_unavailable_refusal(retryable=True)
        return Ok(body)

    recorder = NewsCalendarRecorder(
        journal=journal,
        writer=_writer(),
        fetch_snapshot=fetch,
        settings=_settings(max_attempts=2),
        clock_ns=lambda: _KNOWN_NS,
        sleep_ns=sleeps.append,
    )
    receipt = _ok(recorder.fire())
    assert receipt.outcome == "imported"
    assert receipt.attempts_used == 2
    assert sleeps == [_BACKOFF_NS]


# --- fail-closed decision cycle ---------------------------------------------


def test_stale_news_calendar_fails_entries_without_live_skip() -> None:
    skip = refuse_news_calendar_live_skip(request="operator-click")
    assert skip.category is RefusalCategory.POLICY_REJECTION
    assert skip.context["failure_id"] == LIVE_SKIP_FAILURE_ID

    dead = _refusal(
        evaluate_news_calendar_precondition(
            last_ingest_at=None,
            decision_at=_instant(_KNOWN_NS),
            max_staleness=_duration(_TWO_HOURS_NS),
        )
    )
    assert dead.context["failure_id"] == STALE_FAILURE_ID
    assert dead.context["alarm_class"] == NEWS_CALENDAR_ALARM_CLASS

    stale = _refusal(
        evaluate_news_calendar_precondition(
            last_ingest_at=_instant(0),
            decision_at=_instant(_TWO_HOURS_NS + 1),
            max_staleness=_duration(_TWO_HOURS_NS),
        )
    )
    assert stale.context["failure_id"] == STALE_FAILURE_ID

    skip_cycle = _refusal(
        evaluate_news_calendar_precondition(
            last_ingest_at=_instant(_KNOWN_NS),
            decision_at=_instant(_KNOWN_NS),
            max_staleness=_duration(_TWO_HOURS_NS),
            skip_requested=True,
        )
    )
    assert skip_cycle.context["failure_id"] == LIVE_SKIP_FAILURE_ID

    gate = _ok(
        gate_entry_under_news_calendar(
            instrument=_instrument(),
            book_mode=BookMode.LIVE,
            decision_at=_instant(_KNOWN_NS),
            windows=[_window()],
            would_have_been_action={"class": "entry"},
            last_ingest_at=_instant(0),
            max_staleness=_duration(1),
        )
    )
    assert gate.disposition is WindowActDisposition.FAIL_CLOSED
    assert gate.blocked is True

    skip_gate = gate_entry_under_news_calendar(
        instrument=_instrument(),
        book_mode=BookMode.LIVE,
        decision_at=_instant(_KNOWN_NS),
        windows=[_window()],
        would_have_been_action={"class": "entry"},
        last_ingest_at=_instant(_KNOWN_NS),
        max_staleness=_duration(_TWO_HOURS_NS),
        skip_requested=True,
    )
    assert is_refusal(skip_gate)

    exit_ok = allow_exit_under_stale_news_calendar()
    assert is_ok(exit_ok)


def test_fresh_news_calendar_does_not_fail_closed() -> None:
    fresh = evaluate_news_calendar_precondition(
        last_ingest_at=_instant(_KNOWN_NS),
        decision_at=_instant(_KNOWN_NS + 1),
        max_staleness=_duration(_TWO_HOURS_NS),
    )
    assert is_ok(fresh)


# --- HTTPS pin / systemd ----------------------------------------------------


def test_https_transport_refuses_non_weekly_url_without_network() -> None:
    transport = HttpsForexFactoryTransport(url="https://api.tradingeconomics.com/x")
    refused = transport.fetch_snapshot({})
    assert is_refusal(refused)
    opened: list[str] = []

    def opener(url: str) -> Result[bytes]:
        opened.append(url)
        return Ok(b"[]")

    pinned = HttpsForexFactoryTransport(opener=opener)
    body = _ok(pinned.fetch_snapshot({"known_at_ns": _KNOWN_NS}))
    assert body == b"[]"
    assert opened == [FOREX_FACTORY_WEEKLY_JSON]
    assert "Mozilla" in NEWS_CALENDAR_USER_AGENT
    assert recorder_main([]) == 1


def test_systemd_unit_invokes_news_calendar_recorder_module() -> None:
    unit = (
        _QMN_ROOT / "deploy" / "systemd" / "templates" / "qmn-news-calendar.service.in"
    ).read_text(encoding="utf-8")
    assert "python -m qmn.data.news_calendar_recorder" in unit
    assert "Forex Factory" in unit
    timer = (_QMN_ROOT / "deploy" / "systemd" / "templates" / "qmn-news-calendar.timer").read_text(
        encoding="utf-8"
    )
    assert "qmn-news-calendar.service" in timer
