"""Reference usage — ``qmb data gap-check`` calendar-aware gaps (Story 18.5).

Executable::

    python qmb/examples/data_gap_check_usage.py

Shows the things B-11 / CT-02 pin down for gap detection:

1. Expected sessions come from the versioned CT-02 calendar (forex-17NY for FX).
2. Weekend / holiday closure is not a gap; venue-open absence is a genuine gap.
3. Always-open calendars treat every non-present interior interval as a gap.
4. The calendar version used is recorded; same window + version => same gap set.
5. Gaps are reported only — never filled (Epic 23 / GAP-0048 policy rejection).
6. Unresolvable calendar is unavailable-dependency, never guessed always-open.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.data import AlwaysOpenCalendar, gap_check, gap_check_identity
from qmf.calendar_forex import get_provider
from qmf.core import RefusalCategory, Result, World, is_ok, is_refusal
from qmf.core.chrono import CalendarIdentity
from qmf.data import EvidenceStore

T = TypeVar("T")

_OPEN_START = 1_787_140_800_000_000_000  # mid-session Wed 2026-08-19 UTC
_STEP = 1_000_000_000
_OPEN_END = _OPEN_START + (8 * _STEP)
_WEEKEND_START = 1_787_346_000_000_000_000
_WEEKEND_END = _WEEKEND_START + (8 * _STEP)


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


def main() -> None:
    identity = gap_check_identity()
    _require(identity["fills_gaps"] is False, "never fills")
    _require(identity["never_guess_always_open"] is True, "no silent always-open")
    _require(identity["synthetic_fill_deferred_to"] == "GAP-0048", "fill deferred")
    print(
        "gap-check identity: "
        f"kind={identity['gap_check_kind']} "
        f"fills={identity['fills_gaps']} "
        f"calendar={identity['calendar_authority']}"
    )

    calendar = _unwrap(get_provider(), "forex-17NY provider")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = EvidenceStore(root)

        # Open session with a hole at slots 2..3.
        ticks = tuple(
            {"t_ns": _OPEN_START + (i * _STEP)} for i in range(8) if i not in {2, 3}
        )
        base: dict[str, object] = {
            "archive": str(root),
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "start": _OPEN_START,
            "end": _OPEN_END,
            "bar_step_ns": _STEP,
            "world": World.REPLAY,
            "store": store,
            "calendar": calendar,
            "ticks": ticks,
        }
        report = _unwrap(gap_check(base), "open-session gap-check")
        _require(len(report.gaps) == 1, "one contiguous open-session gap")
        _require(report.gaps[0].expected == 2, "two missing expected bars")
        _require(report.gaps[0].present == 0, "present count on the hole is zero")
        _require(report.fills_gaps is False, "report never fills")
        _require(report.calendar["rule_set"] == "forex-17NY", "records CT-02 rule set")
        print(
            f"open-session gaps={len(report.gaps)} "
            f"calendar={report.calendar} "
            f"gap={report.gaps[0].as_mapping()}"
        )

        # Weekend closed → no open sessions → no gaps.
        weekend = _unwrap(
            gap_check(
                {
                    **base,
                    "start": _WEEKEND_START,
                    "end": _WEEKEND_END,
                    "ticks": (),
                }
            ),
            "weekend gap-check",
        )
        _require(weekend.open_session_count == 0, "weekend has no open sessions")
        _require(weekend.gaps == (), "closure is not a gap")
        print(f"weekend closure: open_sessions={weekend.open_session_count} gaps=0")

        # 24/7 always-open: every hole is a gap.
        always_id = _unwrap(
            CalendarIdentity.try_create("always-open", "v1", "none"), "always-open id"
        )
        always = AlwaysOpenCalendar(identity=always_id)
        start = 1_700_000_000_000_000_000
        end = start + (4 * _STEP)
        crypto = _unwrap(
            gap_check(
                {
                    "archive": str(root),
                    "venue": "crypto-24x7",
                    "symbol": "BTCUSD",
                    "start": start,
                    "end": end,
                    "bar_step_ns": _STEP,
                    "calendar": always,
                    "ticks": ({"t_ns": start}, {"t_ns": start + (3 * _STEP)}),
                    "store": store,
                }
            ),
            "always-open gap-check",
        )
        _require(len(crypto.gaps) == 1, "always-open reports interior hole")
        _require(crypto.gaps[0].expected == 2, "two missing interior slots")
        print(
            f"always-open gaps={len(crypto.gaps)} expected={crypto.gaps[0].expected}"
        )

        # Determinism: same window + same calendar version → identical gap set.
        again = _unwrap(gap_check(base), "deterministic re-run")
        _require(again.calendar == report.calendar, "same calendar version recorded")
        _require(
            [g.as_mapping() for g in again.gaps] == [g.as_mapping() for g in report.gaps],
            "identical gap set",
        )
        print("determinism: same window + calendar version -> identical gap set")

        # Fill attempt refused until GAP-0048.
        filled = gap_check({**base, "fill": True})
        assert is_refusal(filled)
        _require(filled.category is RefusalCategory.POLICY_REJECTION, "fill is policy")
        _require(filled.context["gap"] == "GAP-0048", "deferred to GAP-0048")
        print(f"interior fill refused category={filled.category.value} gap=GAP-0048")

        # Unknown venue calendar → unavailable dependency, never always-open.
        missing = gap_check(
            {
                "archive": str(root),
                "venue": "unknown-equity-venue",
                "symbol": "AAPL",
                "start": _OPEN_START,
                "end": _OPEN_END,
                "bar_step_ns": _STEP,
                "ticks": (),
                "store": store,
            }
        )
        assert is_refusal(missing)
        _require(
            missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY,
            "missing calendar is unavailable dependency",
        )
        print(
            f"unresolvable calendar refused category={missing.category.value} "
            f"field={missing.context.get('field')}"
        )

    print("qmb data gap-check ok")


if __name__ == "__main__":
    main()
