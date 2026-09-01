"""Story 26.3 — news windows, dead zones, and Book-door veto journaling."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    Duration,
    Instant,
    Instrument,
    RefusalCategory,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import Result
from qmf.risk.control_window import (
    AnchorSide,
    ControlWindowRevisionLog,
    CurrencyExposureRecord,
    FeedQuadruple,
    ProposedWindowAct,
    WindowBounds,
    WindowKind,
    mint_control_window,
    resolve_instrument_scope,
)
from qmf.risk.paper import BookMode
from qmn.protection import (
    DEAD_ZONE_KINDS,
    NEWS_CALENDAR_MAX_STALENESS_VARIABLE,
    PROTECTION_SURFACE,
    WINDOW_DOOR,
    WINDOW_EFFECT,
    DeadZoneKind,
    NewsRevisionDisposition,
    WindowActDisposition,
    allow_protective_act_under_windows,
    apply_news_revision,
    assert_calendars_distinct,
    dead_zone_kinds,
    enforce_entry_at_book_door,
    journal_would_have_been,
    refuse_invented_window_minutes,
    refuse_live_skip_at_door,
    refuse_symbol_currency_parse_at_door,
    require_resolved_window_settings,
    stale_news_calendar_blocks_entries,
)

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return _ok(Instrument.try_create(VenueId(value="ctrader"), symbol))


def _calendar(rule: str = "forex-17NY") -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create(rule, "v3", "2024a"))


def _bounds(start: int, end: int) -> WindowBounds:
    return _ok(WindowBounds.try_create(_instant(start), _instant(end)))


def _exposure(
    instrument: Instrument, *currencies: str, record_id: str = "exp-1"
) -> CurrencyExposureRecord:
    return _ok(
        CurrencyExposureRecord.try_create(instrument, currencies, _instant(500), record_id)
    )


def _scope(currencies: tuple[str, ...] = ("USD",)):
    candidate = _instrument("EURUSD")
    return _ok(
        resolve_instrument_scope(
            affected_currencies=currencies,
            candidate_instruments=(candidate,),
            exposure_records=(_exposure(candidate, *currencies),),
        )
    )


def _feed(revision: str = "r1", known_at: int = 900_000_000) -> FeedQuadruple:
    return _ok(
        FeedQuadruple.try_create("calendar-feed", "nfp-2024-08", revision, _instant(known_at))
    )


def _news_window(
    *,
    start: int = 1_000_000_000,
    end: int = 2_000_000_000,
    revision: str = "r1",
    known_at: int = 900_000_000,
    scope=None,
    window_id: str = "win-nfp-1",
):
    return _ok(
        mint_control_window(
            _bounds(start, end),
            WindowKind.NEWS,
            scope if scope is not None else _scope(),
            "high-impact-news",
            _calendar(),
            window_id,
            feed_quadruple=_feed(revision, known_at),
        )
    )


def _dead_zone(*, kind: WindowKind = WindowKind.DAILY_DEAD_ZONE, anchor: AnchorSide | None = None):
    kwargs: dict[str, object] = {}
    if kind is WindowKind.SESSION_HANDOVER_BUFFER:
        kwargs["anchor_side"] = anchor or AnchorSide.BOTH
    return _ok(
        mint_control_window(
            _bounds(1_000_000_000, 2_000_000_000),
            kind,
            _scope(),
            kind.value,
            _calendar("market-hours-forex"),
            f"win-{kind.value}",
            **kwargs,
        )
    )


def _settings():
    return _ok(
        require_resolved_window_settings(
            news_blackout_before=_duration(900_000_000_000),
            news_blackout_after=_duration(900_000_000_000),
            daily_dead_zone_width=_duration(3_600_000_000_000),
            session_handover_buffer_width=_duration(2_700_000_000_000),
            session_handover_buffer_anchor=AnchorSide.BOTH,
            news_calendar_max_staleness=_duration(86_400_000_000_000),
        )
    )


# --- surface / settings -------------------------------------------------------


def test_protection_surface_still_named() -> None:
    assert PROTECTION_SURFACE == "qmn.protection"
    assert WINDOW_DOOR == "control-window"
    assert WINDOW_EFFECT.value == "entries-only"


def test_both_dead_zone_kinds_exist_and_differ() -> None:
    kinds = dead_zone_kinds()
    assert kinds == (DeadZoneKind.DAILY_DEAD_ZONE, DeadZoneKind.SESSION_HANDOVER_BUFFER)
    assert frozenset(
        {WindowKind.DAILY_DEAD_ZONE, WindowKind.SESSION_HANDOVER_BUFFER}
    ) == DEAD_ZONE_KINDS
    daily = _dead_zone(kind=WindowKind.DAILY_DEAD_ZONE)
    handover = _dead_zone(kind=WindowKind.SESSION_HANDOVER_BUFFER, anchor=AnchorSide.PRE_CLOSE)
    assert daily.window_kind is not handover.window_kind
    assert handover.anchor_side is AnchorSide.PRE_CLOSE


def test_resolved_settings_refuse_invented_minutes() -> None:
    blank = require_resolved_window_settings(
        news_blackout_before=None,
        news_blackout_after=_duration(1),
        daily_dead_zone_width=_duration(1),
        session_handover_buffer_width=_duration(1),
        session_handover_buffer_anchor=AnchorSide.BOTH,
        news_calendar_max_staleness=_duration(1),
    )
    assert is_refusal(blank)
    assert blank.category is RefusalCategory.INVALID_INPUT

    invented = require_resolved_window_settings(
        news_blackout_before=15,  # bare minutes — forbidden
        news_blackout_after=_duration(1),
        daily_dead_zone_width=_duration(1),
        session_handover_buffer_width=_duration(1),
        session_handover_buffer_anchor=AnchorSide.BOTH,
        news_calendar_max_staleness=_duration(1),
    )
    assert is_refusal(invented)
    assert "invented" in str(invented.context["reason"]).lower() or "bare" in str(
        invented.context["reason"]
    ).lower()

    assert refuse_invented_window_minutes(15).category is RefusalCategory.INVALID_INPUT
    settings = _settings()
    assert settings.news_calendar_max_staleness.value_ns > 0
    assert NEWS_CALENDAR_MAX_STALENESS_VARIABLE in settings.fp1_identity()


def test_calendars_remain_distinct() -> None:
    mh = _calendar("market-hours-forex")
    db = _calendar("day-boundary-acct")
    news = _calendar("news-ff-weekly")
    distinct = _ok(assert_calendars_distinct(market_hours=mh, day_boundary=db, news=news))
    assert set(distinct) == {
        "market_hours_calendar",
        "day_boundary_calendar",
        "news_calendar",
    }
    collapsed = assert_calendars_distinct(market_hours=mh, day_boundary=mh, news=news)
    assert is_refusal(collapsed)
    assert collapsed.category is RefusalCategory.POLICY_REJECTION


# --- entry blackout live + paper; exits pass ---------------------------------


def test_news_window_blocks_live_and_paper_entries_and_journals_veto() -> None:
    window = _news_window()
    instrument = _instrument()
    decision = _instant(1_500_000_000)
    action = {"class": "would-have-been-entry", "symbol": "EURUSD"}
    for mode in (BookMode.LIVE, BookMode.PAPER):
        gate = _ok(
            enforce_entry_at_book_door(
                instrument=instrument,
                book_mode=mode,
                decision_at=decision,
                windows=[window],
                would_have_been_action=action,
            )
        )
        assert gate.blocked is True
        assert gate.disposition is WindowActDisposition.VETO_JOURNALED
        veto = _ok(journal_would_have_been(gate))
        assert veto.refusing_door == WINDOW_DOOR
        assert veto.book_mode is mode
        assert veto.fp1_identity()["path"] == "veto"


def test_exits_and_protection_never_blocked_by_windows() -> None:
    for act in (
        ProposedWindowAct.EXIT,
        ProposedWindowAct.AMEND_PROTECTION,
        ProposedWindowAct.PROTECTION_ACTION,
        ProposedWindowAct.RECORD_EVIDENCE,
    ):
        assert _ok(allow_protective_act_under_windows(proposed_act=act)) is None

    # Asking the entry enforcer to block an exit is a policy refusal.
    refused = enforce_entry_at_book_door(
        instrument=_instrument(),
        book_mode=BookMode.LIVE,
        decision_at=_instant(1_500_000_000),
        windows=[_news_window()],
        would_have_been_action={"class": "exit"},
        proposed_act=ProposedWindowAct.EXIT,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_dead_zones_pause_entries_only() -> None:
    for kind in (WindowKind.DAILY_DEAD_ZONE, WindowKind.SESSION_HANDOVER_BUFFER):
        window = _dead_zone(kind=kind)
        gate = _ok(
            enforce_entry_at_book_door(
                instrument=_instrument(),
                book_mode=BookMode.PAPER,
                decision_at=_instant(1_500_000_000),
                windows=[window],
                would_have_been_action={"class": "entry", "kind": kind.value},
            )
        )
        assert gate.blocked is True
        assert _ok(allow_protective_act_under_windows(proposed_act=ProposedWindowAct.EXIT)) is None


def test_currency_never_parsed_from_symbol_missing_scope_fail_closed() -> None:
    assert (
        refuse_symbol_currency_parse_at_door("EURUSD").category
        is RefusalCategory.POLICY_REJECTION
    )
    eurusd = _instrument("EURUSD")
    xauusd = _instrument("XAUUSD")
    scope = _ok(
        resolve_instrument_scope(
            affected_currencies={"USD"},
            candidate_instruments=[eurusd, xauusd],
            exposure_records=[_exposure(eurusd, "EUR", "USD")],
        )
    )
    assert xauusd in scope.treated_as_affected_missing_exposure
    window = _news_window(scope=scope)
    gate = _ok(
        enforce_entry_at_book_door(
            instrument=xauusd,
            book_mode=BookMode.LIVE,
            decision_at=_instant(1_500_000_000),
            windows=[window],
            would_have_been_action={"class": "entry", "symbol": "XAUUSD"},
        )
    )
    assert gate.blocked is True
    assert gate.evaluation is not None
    assert gate.evaluation.data_quality_alarm is True


def test_stale_news_and_no_live_skip_fail_closed() -> None:
    assert refuse_live_skip_at_door().category is RefusalCategory.POLICY_REJECTION
    settings = _settings()
    stale = stale_news_calendar_blocks_entries(
        last_refresh_at=_instant(0),
        decision_at=_instant(settings.news_calendar_max_staleness.value_ns + 1),
        max_staleness=settings.news_calendar_max_staleness,
    )
    assert is_refusal(stale)
    assert stale.category is RefusalCategory.POLICY_REJECTION

    gate = _ok(
        enforce_entry_at_book_door(
            instrument=_instrument(),
            book_mode=BookMode.LIVE,
            decision_at=_instant(1_500_000_000),
            windows=[_news_window()],
            would_have_been_action={"class": "entry"},
            news_calendar_fresh=False,
        )
    )
    assert gate.disposition is WindowActDisposition.FAIL_CLOSED
    assert gate.blocked is True


# --- widen-never-shrink revisions --------------------------------------------


def test_narrowing_revision_held_through_prior_end_without_operator_cite() -> None:
    wide = _news_window(start=800, end=2_500, revision="r1", known_at=100)
    narrow = _news_window(start=1_200, end=1_800, revision="r2", known_at=200)
    log = ControlWindowRevisionLog(window_id="win-nfp-1")
    first = _ok(apply_news_revision(log, wide, decision_at=_instant(300)))
    new_log, effective, disposition = first
    assert disposition is NewsRevisionDisposition.WIDENED_OR_ADDED
    assert effective.bounds.start.value_ns == 800

    held = _ok(
        apply_news_revision(
            new_log,
            narrow,
            decision_at=_instant(1_000),
            prior_in_force=wide,
        )
    )
    _log2, effective2, disposition2 = held
    assert disposition2 is NewsRevisionDisposition.NARROWING_HELD
    # Prior block stays effective through declared end via widen-never-shrink union.
    assert effective2.bounds.start.value_ns == 800
    assert effective2.bounds.end.value_ns == 2_500

    cited = _ok(
        apply_news_revision(
            new_log,
            narrow,
            decision_at=_instant(1_000),
            prior_in_force=wide,
            operator_cites_revisions=("r1", "r2"),
        )
    )
    assert cited[2] is NewsRevisionDisposition.OPERATOR_CITED
    # Even with citation, the fold remains the widen-never-shrink union.
    assert cited[1].bounds.end.value_ns == 2_500


def test_entry_outside_window_passes() -> None:
    window = _news_window(start=1_000_000_000, end=2_000_000_000)
    gate = _ok(
        enforce_entry_at_book_door(
            instrument=_instrument(),
            book_mode=BookMode.LIVE,
            decision_at=_instant(3_000_000_000),
            windows=[window],
            would_have_been_action={"class": "entry"},
        )
    )
    assert gate.disposition is WindowActDisposition.PASSED
    assert gate.blocked is False
    assert is_refusal(journal_would_have_been(gate))
