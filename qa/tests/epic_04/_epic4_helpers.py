"""Shared INDEPENDENT oracles and path constants for Epic 4 (qmf-calendar-forex).

Imported as a top-level module (pytest prepend import-mode puts this directory on
sys.path), matching the sibling epics' `_epicN_helpers` convention. The underscore
prefix keeps pytest from collecting it as a test module.

The rollover oracle is derived ONLY from the requirement "the trading date rolls at
17:00 America/New_York" using the Python standard library (datetime + zoneinfo). It
never calls the source's own rollover helpers, so it is an independent check, not a
mirror of the implementation under test.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Importing the extension forces TZPATH to its pinned tzdata, so this stdlib
# ZoneInfo resolves the SAME (pinned) America/New_York rules the provider uses.
import qmf.calendar_forex as _cf  # noqa: F401  (import side effect: pin TZPATH)

NY = ZoneInfo("America/New_York")
_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)
NS = 1_000_000_000

# Repo/worktree root: qa/tests/epic_04/_epic4_helpers.py -> parents[3] == root.
WORKTREE_ROOT = Path(__file__).resolve().parents[3]
EXT_ROOT = WORKTREE_ROOT / "extensions" / "qmf-calendar-forex"
EXT_SRC = EXT_ROOT / "src" / "qmf" / "calendar_forex"


def ny_wall_ns(y: int, mo: int, d: int, h: int = 0, mi: int = 0, s: int = 0) -> int:
    """int64 UTC ns of the given America/New_York wall-clock time (independent oracle)."""
    local = datetime(y, mo, d, h, mi, s, tzinfo=NY)
    delta = local.astimezone(timezone.utc) - _EPOCH_UTC
    return (delta.days * 86_400 + delta.seconds) * NS


def rollover_ns(y: int, mo: int, d: int) -> int:
    """int64 UTC ns of 17:00 America/New_York on civil date (y, mo, d)."""
    return ny_wall_ns(y, mo, d, 17, 0, 0)


def expected_trading_civil(y: int, mo: int, d: int, *, at_or_after_rollover: bool) -> date:
    """Independent oracle: the 17:00-NY rollover advances the civil date by one iff
    the instant is at or after 17:00 New-York on that civil day."""
    base = date(y, mo, d)
    return base + timedelta(days=1) if at_or_after_rollover else base
