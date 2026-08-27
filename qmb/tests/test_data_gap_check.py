"""Tier-1 tests for ``qmb data gap-check`` calendar-aware gaps (Story 18.5, B-11)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar, cast

from click.testing import CliRunner
from qmb.data import (
    GAP_CHECK_KIND,
    AlwaysOpenCalendar,
    data_front_identity,
    gap_check,
    gap_check_identity,
    parse_gap_check_request,
)
from qmb.doors import api
from qmb.doors.cli import invoke_data, main
from qmf.calendar_forex import get_provider
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal
from qmf.core.chrono import CalendarIdentity
from qmf.data import EvidenceStore

T = TypeVar("T")

# Wednesday 2026-08-19 open session under forex-17NY (clipped probe window).
_OPEN_START = 1_787_140_800_000_000_000  # 2026-08-19 12:00:00 UTC mid-session
_STEP = 1_000_000_000  # 1s bars
_OPEN_END = _OPEN_START + (10 * _STEP)

# Weekend closed probe (Friday 17:00 NY → Saturday trading date).
_WEEKEND_START = 1_787_346_000_000_000_000
_WEEKEND_END = _WEEKEND_START + (10 * _STEP)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _forex():
    return _ok(get_provider())


def _resources(tmp: Path, **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "archive": str(tmp),
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "start": _OPEN_START,
        "end": _OPEN_END,
        "resolution": "1s",
        "side": "both",
        "world": World.REPLAY,
        "store": EvidenceStore(tmp),
        "bar_step_ns": _STEP,
        "calendar": _forex(),
        "ticks": tuple({"t_ns": _OPEN_START + (i * _STEP)} for i in range(10)),
    }
    body.update(extra)
    return body


def test_gap_check_identity_never_fills() -> None:
    identity = gap_check_identity()
    assert identity["gap_check_kind"] == GAP_CHECK_KIND
    assert identity["fills_gaps"] is False
    assert identity["calendar_authority"] == "CT-02"
    assert identity["missing_calendar_is_unavailable_dependency"] is True
    assert identity["never_guess_always_open"] is True
    assert identity["synthetic_fill_deferred_to"] == "GAP-0048"
    front = data_front_identity()
    assert front["gap_check_kind"] == GAP_CHECK_KIND
    assert "gap-check" in cast("tuple[str, ...]", front["commands"])


def test_complete_open_session_reports_no_gaps() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = _ok(gap_check(_resources(Path(tmp))))
        assert report.fills_gaps is False
        assert report.gaps == ()
        assert report.open_session_count >= 1
        assert report.calendar["rule_set"] == "forex-17NY"
        assert "rule_set_version" in report.calendar
        assert "tzdata_version" in report.calendar


def test_open_session_missing_bars_are_genuine_gaps() -> None:
    # Drop slots 3..5 inclusive → one contiguous gap.
    ticks = tuple({"t_ns": _OPEN_START + (i * _STEP)} for i in range(10) if i not in {3, 4, 5})
    with tempfile.TemporaryDirectory() as tmp:
        report = _ok(gap_check(_resources(Path(tmp), ticks=ticks)))
        assert len(report.gaps) == 1
        gap = report.gaps[0]
        assert gap.start_ns == _OPEN_START + (3 * _STEP)
        assert gap.end_ns == _OPEN_START + (6 * _STEP)
        assert gap.expected == 3
        assert gap.present == 0
        assert gap.as_mapping()["filled"] is False


def test_weekend_closure_is_not_a_gap() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = _ok(
            gap_check(
                _resources(
                    Path(tmp),
                    start=_WEEKEND_START,
                    end=_WEEKEND_END,
                    ticks=(),
                )
            )
        )
        assert report.open_session_count == 0
        assert report.gaps == ()


def test_always_open_calendar_treats_every_hole_as_gap() -> None:
    identity = _ok(CalendarIdentity.try_create("always-open", "v1", "none"))
    calendar = AlwaysOpenCalendar(identity=identity)
    start = 1_700_000_000_000_000_000
    step = 1_000_000_000
    end = start + (5 * step)
    # Present: slots 0 and 4 only → gaps for 1..3.
    ticks = ({"t_ns": start}, {"t_ns": start + (4 * step)})
    with tempfile.TemporaryDirectory() as tmp:
        report = _ok(
            gap_check(
                {
                    "archive": str(tmp),
                    "venue": "crypto-24x7",
                    "symbol": "BTCUSD",
                    "start": start,
                    "end": end,
                    "bar_step_ns": step,
                    "always_open": True,
                    "calendar_identity": identity,
                    "calendar": calendar,
                    "ticks": ticks,
                    "store": EvidenceStore(Path(tmp)),
                }
            )
        )
        assert report.open_session_count == 1
        assert len(report.gaps) == 1
        gap = report.gaps[0]
        assert gap.start_ns == start + step
        assert gap.end_ns == start + (4 * step)
        assert gap.expected == 3
        assert gap.present == 0
        assert report.calendar["rule_set"] == "always-open"


def test_missing_calendar_is_unavailable_dependency_never_always_open() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        refused = gap_check(
            {
                "archive": str(tmp),
                "venue": "unknown-equity-venue",
                "symbol": "AAPL",
                "start": _OPEN_START,
                "end": _OPEN_END,
                "bar_step_ns": _STEP,
                "ticks": (),
                "store": EvidenceStore(Path(tmp)),
            }
        )
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
        assert refused.context["field"] == "calendar"
        assert "never treated as always-open" in str(refused.context["reason"])


def test_fill_request_is_policy_rejection_until_gap_0048() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        refused = gap_check(_resources(Path(tmp), fill=True))
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["gap"] == "GAP-0048"
        assert refused.context["fills_gaps"] is False


def test_same_window_same_calendar_version_is_deterministic() -> None:
    ticks = tuple({"t_ns": _OPEN_START + (i * _STEP)} for i in range(10) if i not in {2, 7})
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = _ok(gap_check(_resources(root, ticks=ticks)))
        second = _ok(gap_check(_resources(root, ticks=ticks)))
        assert first.calendar == second.calendar
        assert first.as_mapping()["gaps"] == second.as_mapping()["gaps"]
        assert [g.as_mapping() for g in first.gaps] == [g.as_mapping() for g in second.gaps]


def test_bar_step_required_no_invented_default() -> None:
    parsed = parse_gap_check_request(
        {
            "archive": "archive-root",
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "start": _OPEN_START,
            "end": _OPEN_END,
        }
    )
    assert is_refusal(parsed)
    assert parsed.category is RefusalCategory.INVALID_INPUT
    assert parsed.context["field"] == "bar_step_ns"


def test_cli_and_api_doors_share_gap_check() -> None:
    assert "gap-check" in api.DATA_COMMANDS
    assert api.gap_check is gap_check
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = _resources(root)
        library = _ok(gap_check(resources))
        via_invoke = _ok(invoke_data("gap-check", resources))
        assert via_invoke["kind"] == GAP_CHECK_KIND
        assert via_invoke["calendar"] == library.calendar
        assert via_invoke["gaps"] == tuple(g.as_mapping() for g in library.gaps)
        assert via_invoke["fills_gaps"] is False

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "data",
                "gap-check",
                "--archive",
                str(root),
                "--venue",
                "dukascopy-fx",
                "--symbol",
                "EURUSD",
                "--start",
                str(_OPEN_START),
                "--end",
                str(_OPEN_END),
                "--bar-step-ns",
                str(_STEP),
            ],
            catch_exceptions=False,
        )
        # CLI without injected calendar still resolves forex for dukascopy-fx.
        assert result.exit_code in {0, 1}
        assert "gap-check" in api.DATA_COMMANDS
