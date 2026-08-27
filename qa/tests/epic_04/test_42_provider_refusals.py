"""Story 4.2 — provider refusals and session schedule as data (FR-021, CT-02).

4.2-U1 (L1, FM-3): a trading date is never derived by formatting an instant.
4.2-U2 (L1): session schedule models weekend gaps + pinned holidays as DATA;
             session bounds are the rule-derived rollover instants (not a constant).
4.2-U3 (L1, FM-2): cross-calendar-identity comparison RETURNS a typed refusal.
4.2-U4 (L1, FM-4): day-boundary and news questions are out-of-authority refusals.

Every refusal is asserted as a RETURNED TypedRefusal whose category is checked;
never a parsed exception string. Where a category is not pinned by the spine
(cross-calendar, CT-02 line 109), the hard assertion is 'a refusal, not an answer'
and the observed category is recorded as evidence only.
"""

from __future__ import annotations

from datetime import date, datetime

from qmf.core.chrono import (
    CalendarIdentity,
    CivilDate,
    Instant,
    SessionWindow,
    TradingDate,
)
from qmf.core.refusal import Ok, RefusalCategory, TypedRefusal, is_ok

from _epic4_helpers import NY, ny_wall_ns, rollover_ns

_NS = 1_000_000_000


# --- 4.2-U1 : FM-3 format-an-instant is unsupported -------------------------


def test_42_u1_fm3_formatted_inputs_are_refused_only_instant_is_accepted(provider):
    """A trading date derives only from applying the rule set to an Instant. Every
    formatted stand-in (an ISO string, a date, a datetime, a CivilDate) is RETURNED
    a typed refusal. Counter-case: any formatted value yielding an Ok(TradingDate)."""
    formatted_inputs = [
        "2026-02-04",
        date(2026, 2, 4),
        datetime(2026, 2, 4, 12, tzinfo=NY),
        CivilDate(year=2026, month=2, day=4),
        1_700_000_000_000_000_000,  # a bare int is not an Instant either
    ]
    for bad in formatted_inputs:
        result = provider.trading_date_of(bad)
        assert isinstance(result, TypedRefusal), f"formatted input {bad!r} must be refused, got {result!r}"
        assert result.category is RefusalCategory.INVALID_INPUT
        assert dict(result.context).get("field") == "instant"

    # Positive control: the ONLY accepted path applies the rule set to an Instant.
    ok = provider.trading_date_of(Instant(value_ns=rollover_ns(2026, 2, 4)))
    assert is_ok(ok)


def test_42_u1_fm3_no_format_an_instant_constructor_exists():
    """Structural corollary: there is deliberately NO from_instant / from_local_date
    / from_string path on TradingDate — the format-an-instant operation does not
    exist. Counter-case: any such constructor being present."""
    for forbidden in ("from_instant", "from_local_date", "from_string", "of_instant"):
        assert not hasattr(TradingDate, forbidden), (
            f"TradingDate must expose no {forbidden}: a trading date is never derived by "
            "formatting an instant (CT-02 nullability.trading_date_source)"
        )


# --- 4.2-U2 : session schedule as data (weekend gaps + holidays) ------------


def test_42_u2_weekend_gap_is_closed_and_sunday_reopens(provider):
    """Weekend gap: an instant whose trading date falls on Sat/Sun is closed
    (a successful None, a schedule fact), and Sunday post-17:00 NY reopens (rolls to
    Monday -> an open SessionWindow). Counter-case: a weekend instant returning an
    open window, or the Sunday reopen staying closed."""
    # Friday 18:00 NY -> rolls to Saturday trading date -> closed.
    fri_evening = provider.session_window(Instant(value_ns=ny_wall_ns(2026, 2, 6, 18)))
    assert isinstance(fri_evening, Ok) and fri_evening.value is None
    # Sunday 12:00 NY -> Sunday trading date -> closed.
    sun_midday = provider.session_window(Instant(value_ns=ny_wall_ns(2026, 2, 8, 12)))
    assert isinstance(sun_midday, Ok) and sun_midday.value is None
    # Sunday 18:00 NY -> rolls to Monday -> OPEN.
    sun_evening = provider.session_window(Instant(value_ns=ny_wall_ns(2026, 2, 8, 18)))
    assert is_ok(sun_evening) and isinstance(sun_evening.value, SessionWindow)


def test_42_u2_holiday_is_data_closed_while_neighbouring_non_holiday_is_open(provider):
    """A pinned holiday (New Year's Day) is a full-day closure, driven by the
    holiday DATA set, while a non-holiday weekday at the same time is open.
    Counter-case: the holiday resolving to an open session (holiday not modelled)."""
    import qmf.calendar_forex as cf

    # Jan 1 is in the pinned recurring holiday set (as data), so a midday Jan-1
    # instant is closed.
    assert (1, 1) in cf.RECURRING_HOLIDAYS
    jan1 = provider.session_window(Instant(value_ns=ny_wall_ns(2026, 1, 1, 12)))
    assert isinstance(jan1, Ok) and jan1.value is None
    # A neighbouring non-holiday weekday (Fri Jan 2 2026) midday is open.
    assert (1, 2) not in cf.RECURRING_HOLIDAYS
    jan2 = provider.session_window(Instant(value_ns=ny_wall_ns(2026, 1, 2, 12)))
    assert is_ok(jan2) and isinstance(jan2.value, SessionWindow)


def test_42_u2_session_bounds_are_rule_derived_rollover_instants_not_a_constant(provider):
    """Session/trading-day length is DATA: the open session's bounds are exactly the
    rule's rollover instants — [prev-day 17:00 NY, trading-day 17:00 NY) — computed
    from the versioned rule, never a baked constant. Counter-case: bounds that do not
    match the independently-computed 17:00-NY rollover instants."""
    # Wednesday 2026-02-04 midday -> open; trading date is Feb 4 (before 17:00).
    window = provider.session_window(Instant(value_ns=ny_wall_ns(2026, 2, 4, 12)))
    assert is_ok(window) and isinstance(window.value, SessionWindow)
    win = window.value
    # Independently: open == prev-day (Feb 3) 17:00 NY, close == Feb 4 17:00 NY.
    assert win.open_instant.value_ns == rollover_ns(2026, 2, 3)
    assert win.close_instant.value_ns == rollover_ns(2026, 2, 4)
    assert win.zone == "America/New_York"


# --- 4.2-U3 : FM-2 cross-calendar comparison refuses ------------------------


def test_42_u3_fm2_cross_calendar_comparison_returns_a_typed_refusal(provider):
    """Two TradingDates under DIFFERENT calendar identities compared for equality
    RETURN a typed refusal; equality is defined only within one identity. The
    spine does not pin the CT-04 category (CT-02 line 109), so the hard assertion
    is 'a refusal, not an equal/False answer'. Counter-case: Ok(True/False)."""
    forex_td = provider.trading_date_of(Instant(value_ns=rollover_ns(2026, 2, 4)))
    assert is_ok(forex_td)
    forex_td = forex_td.value

    other_identity = CalendarIdentity.try_create("other-cal", "v1", "2025b")
    assert is_ok(other_identity)
    other_td = TradingDate.try_create(other_identity.value, forex_td.date_value)
    assert is_ok(other_td)
    other_td = other_td.value

    cross_compare = forex_td.compare(other_td)
    cross_equals = forex_td.equals(other_td)
    assert isinstance(cross_compare, TypedRefusal), f"cross-calendar compare must refuse: {cross_compare!r}"
    assert isinstance(cross_equals, TypedRefusal), f"cross-calendar equals must refuse: {cross_equals!r}"
    # Observed (not spine-pinned) category for the record.
    assert cross_compare.category is RefusalCategory.INVALID_INPUT

    # Control: within one identity, equality is a real answer, not a refusal —
    # so the refusal above is specifically the cross-identity case.
    same_td = provider.trading_date_of(Instant(value_ns=rollover_ns(2026, 2, 4)))
    assert is_ok(same_td)
    within = forex_td.equals(same_td.value)
    assert is_ok(within) and within.value is True


# --- 4.2-U4 : FM-4 authority-boundary refusals ------------------------------


def test_42_u4_fm4_day_boundary_and_news_questions_are_out_of_authority(provider):
    """A market-hours calendar answers ONLY market-hours questions. A day-boundary
    (evaluation-day) question AND a news-event question EACH return an
    out-of-authority typed refusal (unsupported capability). This is Epic 4's only
    correct relationship to the CT-31 dead-zone / news surface: it REFUSES.
    Counter-case: either returning an Ok answer (answering out of authority)."""
    instant = Instant(value_ns=rollover_ns(2026, 2, 4))

    day_boundary = provider.evaluation_day_of(instant, account="acct-1")
    news = provider.news_events(instant)

    assert isinstance(day_boundary, TypedRefusal), f"day-boundary must refuse: {day_boundary!r}"
    assert day_boundary.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert dict(day_boundary.context).get("requested") == "day-boundary"

    assert isinstance(news, TypedRefusal), f"news must refuse: {news!r}"
    assert news.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert dict(news.context).get("requested") == "news"

    # Control: a market-hours question (trading date) IS answered — proving the
    # refusals above are specifically the out-of-authority kinds.
    assert is_ok(provider.trading_date_of(instant))
