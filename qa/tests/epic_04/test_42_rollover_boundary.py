"""Story 4.2 — the 17:00 America/New_York rollover boundary (FR-021, CT-02).

4.2-C1 (L2, headline, R-CAL-ROLLOVER): at 16:59:59.999999999 NY the trading date
is D; at 17:00:00.000000000 NY it is D+1; the returned TradingDate carries
forex-17NY identity + rule-set version in-band; and the boundary tracks the
America/New_York zone (shifts one hour across a US DST change), not a fixed UTC
offset.

Also a hypothesis property (L1): across many civil dates and times, the provider's
trading date equals the independent 17:00-NY oracle. Both rollover arms (D and D+1)
are reachable in the generator.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from qmf.core.chrono import Instant, TradingDate
from qmf.core.refusal import is_ok

from _epic4_helpers import NY, expected_trading_civil, ny_wall_ns, rollover_ns

_NS = 1_000_000_000

# A winter (EST, UTC-5) and a summer (EDT, UTC-4) weekday. Both far from any DST
# transition and from midnight, so the only boundary in play is 17:00 NY.
_WINTER = (2026, 2, 4)  # Wednesday
_SUMMER = (2026, 7, 8)  # Wednesday


def _civil_tuple(td: TradingDate) -> tuple[int, int, int]:
    return (td.date_value.year, td.date_value.month, td.date_value.day)


@pytest.mark.parametrize("day", [_WINTER, _SUMMER], ids=["winter-EST", "summer-EDT"])
def test_42_c1_nanosecond_rollover_boundary(provider, day):
    """One nanosecond BEFORE 17:00 NY is trading date D; exactly 17:00 NY is D+1.
    Counter-case: a rollover at a different hour, a fixed-UTC boundary, or an
    off-by-one at the nanosecond edge would land one of these on the wrong day."""
    y, mo, d = day
    boundary = rollover_ns(y, mo, d)

    before = provider.trading_date_of(Instant(value_ns=boundary - 1))
    at = provider.trading_date_of(Instant(value_ns=boundary))
    assert is_ok(before) and is_ok(at)

    expected_before = expected_trading_civil(y, mo, d, at_or_after_rollover=False)
    expected_at = expected_trading_civil(y, mo, d, at_or_after_rollover=True)
    assert _civil_tuple(before.value) == (expected_before.year, expected_before.month, expected_before.day)
    assert _civil_tuple(at.value) == (expected_at.year, expected_at.month, expected_at.day)
    # The two instants are 1 ns apart yet resolve to different trading dates.
    assert before.value.date_value != at.value.date_value


@pytest.mark.parametrize("day", [_WINTER, _SUMMER], ids=["winter-EST", "summer-EDT"])
def test_42_c1_trading_date_carries_forex_identity_in_band(provider, day):
    """The returned TradingDate carries calendar identity forex-17NY + rule-set
    version in-band. Counter-case: an identity-free civil date, or the wrong rule
    set / a missing version."""
    y, mo, d = day
    td = provider.trading_date_of(Instant(value_ns=rollover_ns(y, mo, d)))
    assert is_ok(td)
    ident = td.value.calendar
    assert ident.rule_set == "forex-17NY"
    assert isinstance(ident.rule_set_version, str) and ident.rule_set_version.strip()
    assert isinstance(ident.tzdata_version, str) and ident.tzdata_version.strip()


def test_42_c1_boundary_tracks_ny_zone_across_dst_not_a_fixed_utc_offset(provider):
    """The 17:00-NY boundary shifts exactly one hour in UTC between EST and EDT —
    proving it tracks the America/New_York zone, not a hardcoded UTC offset.

    Falsifiability witness: a fixed-offset implementation pinned to the winter
    boundary (22:00 UTC) would classify the SUMMER 17:00-NY instant (21:00 UTC) as
    'before rollover' -> D. The provider returns D+1, so this discriminates."""
    wy, wmo, wd = _WINTER
    sy, smo, sd = _SUMMER
    winter_offset = datetime(wy, wmo, wd, 17, tzinfo=NY).utcoffset()
    summer_offset = datetime(sy, smo, sd, 17, tzinfo=NY).utcoffset()
    assert winter_offset != summer_offset, "the pinned tzdb must model US DST for New York"

    # UTC seconds-past-midnight of each 17:00-NY boundary differ by exactly one hour.
    winter_sod = (rollover_ns(wy, wmo, wd) // _NS) % 86_400
    summer_sod = (rollover_ns(sy, smo, sd) // _NS) % 86_400
    assert abs(winter_sod - summer_sod) == 3600

    # And the summer boundary genuinely rolls to D+1 at its own (EDT) 17:00 instant,
    # which is one hour earlier in UTC than the winter boundary would be.
    summer_boundary = rollover_ns(sy, smo, sd)
    at = provider.trading_date_of(Instant(value_ns=summer_boundary))
    assert is_ok(at)
    assert (at.value.date_value.year, at.value.date_value.month, at.value.date_value.day) == (sy, smo, sd + 1)


# --- L1 property: oracle agreement across many dates/times ------------------

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

_MIN_NS = ny_wall_ns(2000, 1, 1, 0, 0, 0)
_MAX_NS = ny_wall_ns(2060, 12, 31, 23, 59, 59)


@settings(max_examples=250, deadline=None)
@given(second=st.integers(min_value=_MIN_NS // _NS, max_value=_MAX_NS // _NS))
def test_42_c1_property_matches_independent_17ny_oracle(provider, second):
    """For a whole-second instant anywhere in 2000..2060, the provider's trading
    date equals the independent oracle: the NY civil date of the instant, advanced
    by one day iff the instant is at/after that day's 17:00-NY boundary.

    Both arms are reachable: the generated range spans all times of day, so
    at/after-17:00 and before-17:00 both occur."""
    ns = second * _NS
    result = provider.trading_date_of(Instant(value_ns=ns))
    assert is_ok(result)

    ny_dt = (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=second)).astimezone(NY)
    day = ny_dt.date()
    at_or_after = ns >= rollover_ns(day.year, day.month, day.day)
    oracle = day + timedelta(days=1) if at_or_after else day

    got = result.value.date_value
    assert (got.year, got.month, got.day) == (oracle.year, oracle.month, oracle.day)
