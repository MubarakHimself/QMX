"""Pinned holiday set for the forex-17NY market-hours calendar (CT-02 extension data).

Holiday closures are calendar-extension data, pinned and versioned with this
package and its tzdata — not core-contract schema (CT-02 ``forex_holiday_set``).
A trading date whose ``(month, day)`` matches a recurring entry is fully closed;
Swap-Wednesday is not modeled (V1 accounts are swap-free).
"""

from __future__ import annotations

from qmf.core.chrono import CivilDate

# Recurring civil-date holidays observed as full-day market closures under the
# America/New_York session schedule. Bumping this set is a rule-set change.
RECURRING_HOLIDAYS: frozenset[tuple[int, int]] = frozenset(
    {
        (1, 1),  # New Year's Day
        (12, 25),  # Christmas Day
    }
)


def is_holiday(date_value: CivilDate) -> bool:
    """Whether ``date_value`` is a pinned full-day holiday under this rule set."""
    return (date_value.month, date_value.day) in RECURRING_HOLIDAYS
