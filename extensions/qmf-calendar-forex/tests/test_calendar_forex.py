"""Tier-1 tests for `qmf.calendar_forex`: tzdb pin, forex-17NY CT-02 provider."""

from __future__ import annotations

import zoneinfo
from pathlib import Path

import pytest
import qmf.calendar_forex
import tzdata
from qmf.calendar_forex import Forex17NYCalendar, _bench, _tzdb
from qmf.core.chrono import CalendarIdentity, CivilDate, Instant, TradingDate
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_ok, is_refusal


def _instant(value_ns: int) -> Instant:
    result = Instant.try_create(value_ns)
    assert is_ok(result)
    return result.value


def _ready_calendar() -> Forex17NYCalendar:
    result = qmf.calendar_forex.get_provider()
    assert is_ok(result)
    return result.value


def test_version_is_semver_0x() -> None:
    assert qmf.calendar_forex.__version__ == "0.1.0"


def test_tzdata_pin_constants_match_installed_package() -> None:
    assert qmf.calendar_forex.PINNED_TZDATA_PACKAGE == "2025.2"
    assert qmf.calendar_forex.PINNED_TZDB_VERSION == "2025b"
    assert tzdata.__version__ == qmf.calendar_forex.PINNED_TZDATA_PACKAGE
    assert tzdata.IANA_VERSION == qmf.calendar_forex.PINNED_TZDB_VERSION


def test_import_forces_tzpath_to_pinned_tzdata() -> None:
    zone_dir = Path(tzdata.__file__).resolve().parent / "zoneinfo"
    assert (str(zone_dir),) == zoneinfo.TZPATH
    assert Path(zoneinfo.TZPATH[0]) == zone_dir


def test_import_verification_ready_exposes_calendar_identity() -> None:
    assert qmf.calendar_forex.provider_ready is True
    identity = qmf.calendar_forex.calendar_identity
    assert isinstance(identity, CalendarIdentity)
    assert identity.rule_set == "forex-17NY"
    assert identity.rule_set_version == "v1"
    assert identity.tzdata_version == "2025b"
    assert qmf.calendar_forex.tzdata_version == "2025b"

    result = qmf.calendar_forex.get_calendar_identity()
    assert is_ok(result) and result.value is identity
    assert is_ok(qmf.calendar_forex.tzdb_verification)


def test_provider_state_clears_provider_on_refusal() -> None:
    refusal = _tzdb.verify_import_tzdb(pinned="1990a")
    assert is_refusal(refusal)
    identity, version, ready = _tzdb.provider_state(refusal)
    assert identity is None
    assert version is None
    assert ready is False


def test_verify_import_tzdb_refuses_mismatch() -> None:
    refusal = _tzdb.verify_import_tzdb(pinned="1990a")
    assert is_refusal(refusal)
    assert isinstance(refusal, TypedRefusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["pinned"] == "1990a"
    assert refusal.context["resolved"] == "2025b"


def test_verify_import_tzdb_refuses_unreadable_zone_dir(tmp_path: Path) -> None:
    empty = tmp_path / "empty-zoneinfo"
    empty.mkdir()
    refusal = _tzdb.verify_import_tzdb(zone_dir=empty)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["field"] == "tzdata_version"
    # Restore the process TZPATH to the real pin after the empty-dir force.
    _tzdb.force_tzpath()


def test_read_resolved_requires_tzdata_zi_on_forced_path(tmp_path: Path) -> None:
    bare = tmp_path / "bare-zoneinfo"
    bare.mkdir()
    # No tzdata.zi on the forced path — do not invent a version from metadata.
    assert _tzdb.read_resolved_tzdb_version(bare) is None
    zone_dir = Path(tzdata.__file__).resolve().parent / "zoneinfo"
    assert _tzdb.read_resolved_tzdb_version(zone_dir) == "2025b"


def test_rollover_constants_match_registry_forex_rollover() -> None:
    assert qmf.calendar_forex.ROLLOVER_ZONE == "America/New_York"
    assert qmf.calendar_forex.ROLLOVER_HOUR == 17
    assert qmf.calendar_forex.ROLLOVER_MINUTE == 0


def test_trading_date_before_rollover_stays_on_local_civil_day() -> None:
    # 2026-08-17 16:59:59 America/New_York → trading date 2026-08-17
    calendar = _ready_calendar()
    day = calendar.trading_date_of(_instant(1_787_000_399_000_000_000))
    assert is_ok(day)
    assert day.value.calendar is qmf.calendar_forex.calendar_identity
    assert day.value.date_value == CivilDate(2026, 8, 17)


def test_trading_date_at_rollover_advances() -> None:
    # 2026-08-17 17:00:00 America/New_York → trading date 2026-08-18
    calendar = _ready_calendar()
    day = calendar.trading_date_of(_instant(1_787_000_400_000_000_000))
    assert is_ok(day)
    assert day.value.date_value == CivilDate(2026, 8, 18)


def test_trading_date_refuses_non_instant_format_path() -> None:
    calendar = _ready_calendar()
    refusal = calendar.trading_date_of("2026-08-17")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "instant"
    assert "formatting" in str(refusal.context["reason"])


def test_session_window_refuses_non_instant() -> None:
    calendar = _ready_calendar()
    refusal = calendar.session_window("not-an-instant")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "instant"


def test_session_window_open_midweek() -> None:
    # 2026-08-19 12:00:00 UTC = 08:00 NY Wednesday → open trading date 2026-08-19
    calendar = _ready_calendar()
    instant = _instant(1_787_140_800_000_000_000)
    day = calendar.trading_date_of(instant)
    assert is_ok(day) and day.value.date_value == CivilDate(2026, 8, 19)
    window = calendar.session_window(instant)
    assert is_ok(window)
    assert window.value is not None
    assert window.value.zone == "America/New_York"
    contained = window.value.contains(instant)
    assert is_ok(contained)
    assert contained.value is True


def test_session_window_closed_on_weekend_gap() -> None:
    # Friday 17:00 NY → Saturday trading date → weekend gap
    calendar = _ready_calendar()
    window = calendar.session_window(_instant(1_787_346_000_000_000_000))
    assert is_ok(window) and window.value is None


def test_session_window_reopens_sunday_rollover() -> None:
    # Sunday 17:00 NY → Monday trading date → open
    calendar = _ready_calendar()
    instant = _instant(1_787_518_800_000_000_000)
    day = calendar.trading_date_of(instant)
    assert is_ok(day) and day.value.date_value == CivilDate(2026, 8, 24)
    window = calendar.session_window(instant)
    assert is_ok(window)
    assert window.value is not None
    contained = window.value.contains(instant)
    assert is_ok(contained)
    assert contained.value is True


def test_session_window_closed_on_christmas_holiday() -> None:
    # 2025-12-24 18:00 NY → trading date 2025-12-25 (Christmas) → closed
    calendar = _ready_calendar()
    instant = _instant(1_766_617_200_000_000_000)
    day = calendar.trading_date_of(instant)
    assert is_ok(day) and day.value.date_value == CivilDate(2025, 12, 25)
    assert qmf.calendar_forex.is_holiday(day.value.date_value)
    window = calendar.session_window(instant)
    assert is_ok(window) and window.value is None


def test_session_window_closed_on_new_years_holiday() -> None:
    # 2025-12-31 18:00 NY → trading date 2026-01-01 → closed
    calendar = _ready_calendar()
    instant = _instant(1_767_222_000_000_000_000)
    day = calendar.trading_date_of(instant)
    assert is_ok(day) and day.value.date_value == CivilDate(2026, 1, 1)
    window = calendar.session_window(instant)
    assert is_ok(window) and window.value is None


def test_cross_calendar_trading_date_equality_refuses() -> None:
    calendar = _ready_calendar()
    day = calendar.trading_date_of(_instant(1_787_140_800_000_000_000))
    assert is_ok(day)
    other_identity = CalendarIdentity.try_create("other-calendar", "v1", "2025b")
    assert is_ok(other_identity)
    other_day = TradingDate.try_create(other_identity.value, day.value.date_value)
    assert is_ok(other_day)
    # Equality lives on core TradingDate.equals — cross-calendar is a typed refusal.
    cross = day.value.equals(other_day.value)
    assert is_refusal(cross)
    assert cross.category is RefusalCategory.INVALID_INPUT


def test_day_boundary_and_news_are_out_of_authority() -> None:
    calendar = _ready_calendar()
    day_boundary = calendar.evaluation_day_of(_instant(0), account="acct-1")
    assert day_boundary.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert day_boundary.context["requested"] == "day-boundary"
    assert "out of authority" in str(day_boundary.context["reason"])

    news = calendar.news_events(_instant(0))
    assert news.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert news.context["requested"] == "news"
    assert "out of authority" in str(news.context["reason"])


def test_identity_fingerprint_uses_qmf_core_only() -> None:
    calendar = _ready_calendar()
    own = calendar.identity_fingerprint()
    via_core = fingerprint(calendar.identity)
    assert is_ok(own) and is_ok(via_core)
    assert own.value == via_core.value
    assert own.value.value.startswith("fp1:sha256:")
    # Identity content is rule set + tzdata only (CalendarIdentity.fp1_identity).
    content = calendar.identity.fp1_identity()
    assert content["rule_set"] == "forex-17NY"
    assert content["tzdata_version"] == "2025b"
    assert "binding" not in content


def test_get_provider_ready() -> None:
    result = qmf.calendar_forex.get_provider()
    assert is_ok(result)
    assert result.value.identity is qmf.calendar_forex.calendar_identity


def test_get_provider_refuses_when_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    refusal = TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={"field": "tzdata_version", "reason": "pin mismatch"},
    )
    monkeypatch.setattr(qmf.calendar_forex, "provider_ready", False)
    monkeypatch.setattr(qmf.calendar_forex, "calendar_identity", None)
    monkeypatch.setattr(qmf.calendar_forex, "tzdb_verification", refusal)
    result = qmf.calendar_forex.get_provider()
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_get_provider_defensive_unavailable_when_state_incoherent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # provider_ready False while verification is Ok — defensive unavailable path.
    assert is_ok(qmf.calendar_forex.tzdb_verification)
    monkeypatch.setattr(qmf.calendar_forex, "provider_ready", False)
    monkeypatch.setattr(qmf.calendar_forex, "calendar_identity", None)
    result = qmf.calendar_forex.get_provider()
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert result.context["field"] == "provider"


def test_bench_harness_runs_full_ladder() -> None:
    results = _bench.run(calendar=_ready_calendar())
    assert [result.load for result in results] == list(_bench.DEFAULT_LADDER)
    assert all(result.seconds >= 0.0 for result in results)
    assert all(result.peak_bytes >= 0 for result in results)
    assert all(result.module == "qmf.calendar_forex" for result in results)
